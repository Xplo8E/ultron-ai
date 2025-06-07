# ultron/engine/agent.py

import os
import json
import re
from typing import List, Dict, Optional

from google import genai
from google.genai import types
from rich.console import Console
from rich.markdown import Markdown

# Corrected relative imports for the new structure
from ..models.data_models import HighConfidenceVulnerability
from .code_analyzer import ProjectCodeAnalyzer
from ..core.constants import AVAILABLE_MODELS

console = Console()

class DeepDiveAgent:
    """
    An AI agent that performs a deep, multi-step investigation on a specific,
    potentially complex vulnerability using the ReAct framework.
    """

    def __init__(self,
                 initial_finding: HighConfidenceVulnerability,
                 file_path: str,
                 project_context: Dict[str, str],
                 analyzer: Optional[ProjectCodeAnalyzer] = None,
                 model_name: str = AVAILABLE_MODELS["2.0-flash"]):

        if not os.getenv("GEMINI_API_KEY"):
            raise ValueError("GEMINI_API_KEY not found in environment. The agent cannot be initialized.")

        self.initial_finding = initial_finding
        self.file_path = file_path
        self.project_context = project_context
        self.analyzer = analyzer
        self.model_name = model_name
        self.investigation_steps = []
        self._tools = self._define_tools()
        # The line that caused the error has been removed. We will call the API directly.

    def _tool_read_file_content(self, file_path: str) -> str:
        """Implementation of the 'read_file_content' tool."""
        self.investigation_steps.append(f"Tool Call: Reading file '{file_path}'")
        if file_path in self.project_context:
            return self.project_context[file_path][:10000]
        return f"Error: File '{file_path}' not found in the project context."

    def _tool_find_string_in_project(self, search_term: str) -> str:
        """Implementation of the 'find_string_in_project' tool."""
        self.investigation_steps.append(f"Tool Call: Searching for string '{search_term}'")
        results = []
        for path, content in self.project_context.items():
            lines = content.splitlines()
            for i, line in enumerate(lines, 1):
                if search_term in line:
                    results.append(f"- Found in '{path}' at line {i}: {line.strip()}")
        if not results:
            return f"String '{search_term}' not found in any file."
        summary = "\n".join(results[:15])
        if len(results) > 15:
            summary += f"\n... ({len(results) - 15} more matches found)"
        return summary

    def _tool_get_function_definition(self, qualified_function_name: str) -> str:
        """Tool to get the source code and documentation for a specific function."""
        self.investigation_steps.append(f"Tool Call: Getting definition for '{qualified_function_name}'")
        if not self.analyzer:
            return "Error: Project analyzer is not available for this run."
        if qualified_function_name in self.analyzer.function_definitions:
            _path, func_def = self.analyzer.function_definitions[qualified_function_name]
            return func_def.get_context_summary()
        return f"Error: Function '{qualified_function_name}' not found in the project index. Try searching for a substring."

    def _define_tools(self) -> List[types.Tool]:
        """Defines the function calling tools for the Gemini API."""
        return [
            types.Tool(
                function_declarations=[
                    types.FunctionDeclaration(
                        name='read_file_content',
                        description="Reads the full content of a specific file from the project.",
                        parameters=types.Schema(type=types.Type.OBJECT, properties={'file_path': types.Schema(type=types.Type.STRING)})
                    ),
                    types.FunctionDeclaration(
                        name='find_string_in_project',
                        description="Searches for a string or keyword across all files to find relationships.",
                        parameters=types.Schema(type=types.Type.OBJECT, properties={'search_term': types.Schema(type=types.Type.STRING)})
                    ),
                    types.FunctionDeclaration(
                        name='get_function_definition',
                        description="Gets the source code snippet, signature, and docstring for a fully-qualified function name from the code index.",
                        parameters=types.Schema(type=types.Type.OBJECT, properties={'qualified_function_name': types.Schema(type=types.Type.STRING)})
                    )
                ]
            )
        ]

    def run(self, max_steps: int = 7) -> Optional[HighConfidenceVulnerability]:
        """
        Runs the investigation loop using the ReAct framework. This version manually
        manages conversation history to be compatible with all library versions.
        """
        initial_prompt = f"""
        You are an expert security research agent. Your goal is to validate a potential vulnerability and generate a precise Proof of Concept (POC).
        Think step-by-step. Use the provided tools to gather evidence.

        **Initial Potential Finding:**
        - **File:** {self.file_path}
        - **Line:** {self.initial_finding.line}
        - **Description:** {self.initial_finding.description}

        Your task is to confirm if this is exploitable. For each step, explain your reasoning (Thought) and then choose an Action (Tool Call).
        When you have gathered enough evidence, provide your final answer as a single, valid JSON object that strictly follows the 'HighConfidenceVulnerability' Pydantic model structure.
        If you determine it is not a vulnerability, state that clearly in plain text. Begin your investigation.
        """
        self.investigation_steps.append(f"Agent initiated. Goal: Validate '{self.initial_finding.description}'")

        # Manually manage conversation history
        conversation_history = [types.Content(parts=[types.Part(text=initial_prompt)])]

        for step in range(max_steps):
            # Call the API directly using the compatible method
            response = genai.models.generate_content(
                model=self.model_name,
                contents=conversation_history,
                tools=self._tools,
            )

            # Defensive check in case of empty response
            if not response.candidates:
                console.print(Markdown(f"**❌ Agent Error:** The model returned no response. Aborting investigation."))
                return None

            part = response.candidates[0].content.parts[0]

            if part.function_call:
                # THOUGHT: The model's reasoning leading to the action.
                if part.text:
                    console.print(Markdown(f"**🤔 Agent Thought:** {part.text}"))
                    self.investigation_steps.append(f"**Thought:** {part.text}")
                # ACTION: The model wants to use a tool.
                function_call = part.function_call
                tool_name = function_call.name
                tool_args = {key: value for key, value in function_call.args.items()}
                console.print(f"**🛠️ Agent Action:** Calling tool `{tool_name}` with args: `{tool_args}`")
                self.investigation_steps.append(f"**Action:** Calling tool `{tool_name}` with args: `{tool_args}`")

                if tool_name == 'read_file_content':
                    tool_result = self._tool_read_file_content(**tool_args)
                elif tool_name == 'find_string_in_project':
                    tool_result = self._tool_find_string_in_project(**tool_args)
                elif tool_name == 'get_function_definition':
                    tool_result = self._tool_get_function_definition(**tool_args)
                else:
                    tool_result = f"Error: Unknown tool '{tool_name}'"
                
                self.investigation_steps.append(f"**Observation:** Result from `{tool_name}` was returned to the agent.")

                # OBSERVATION: Send the tool's result back to the model.
                conversation_history.append(types.Content(parts=[part], role='model')) # Append the model's function call request
                conversation_history.append(
                    types.Content(
                        role="tool",
                        parts=[
                            types.Part(
                                function_response=types.FunctionResponse(
                                    name=tool_name, response={'result': tool_result}
                                )
                            )
                        ],
                    )
                )
            else:
                # FINAL ANSWER: The agent has finished its reasoning.
                console.print(Markdown("**✅ Agent Conclusion:** The agent has completed its investigation. Final response received."))
                final_text = part.text
                try:
                    json_str_match = re.search(r'```json\n({.*?})\n```', final_text, re.DOTALL)
                    json_str = json_str_match.group(1) if json_str_match else final_text
                    json_blob = json.loads(json_str)
                    updated_vuln = HighConfidenceVulnerability(**json_blob)
                    updated_vuln.analysis_source = "deep_dive_agent" # Mark as enhanced.
                    return updated_vuln
                except (json.JSONDecodeError, TypeError, ValueError, AttributeError) as e:
                    self.investigation_steps.append(f"Agent's final response was not valid JSON. Error: {e}. Response: {final_text[:200]}...")
                    return None

        self.investigation_steps.append("Agent reached max steps. Investigation timed out.")
        return None