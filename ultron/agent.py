# ultron/agent.py

import os
import json
from pathlib import Path
import re
from typing import List, Dict, Optional, Any

from google import genai
from google.generativeai import protos

from .models import HighConfidenceVulnerability

class DeepDiveAgent:
    """
    An AI agent that performs a deep, multi-step investigation on a specific,
    potentially complex vulnerability using tools.
    """

    def __init__(self,
                 initial_finding: HighConfidenceVulnerability,
                 project_context: Dict[str, str], # Maps file_path -> file_content
                 model_name: str = "gemini-2.5-flash-preview-05-20"): # Use a powerful model for reasoning
        
        if not os.getenv("GEMINI_API_KEY"):
            raise ValueError("GEMINI_API_KEY not found in environment. The agent cannot be initialized.")

        self.initial_finding = initial_finding
        self.project_context = project_context
        self.model_name = model_name
        self.investigation_steps = []
        
        # Define the tools the agent can use
        self._tools = self._define_tools()
        
        # Instantiate the model with the tools. It will use the environment variable for the API key.
        self.model = genai.GenerativeModel(model_name=self.model_name, tools=self._tools)

    def _tool_read_file_content(self, file_path: str) -> str:
        """Implementation of the 'read_file_content' tool."""
        self.investigation_steps.append(f"Tool Call: Reading file '{file_path}'")
        if file_path in self.project_context:
            # Return first 10000 characters to avoid huge context windows
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
        
        # Return a concise summary to manage context size
        summary = "\n".join(results[:15])
        if len(results) > 15:
            summary += f"\n... ({len(results) - 15} more matches found)"
        return summary

    def _define_tools(self) -> List[protos.Tool]:
        """Defines the function calling tools for the Gemini API."""
        return [
            protos.Tool(
                function_declarations=[
                    protos.FunctionDeclaration(
                        name='read_file_content',
                        description="Reads the full content of a specific file from the project.",
                        parameters=protos.Schema(
                            type=protos.Type.OBJECT,
                            properties={
                                'file_path': protos.Schema(
                                    type=protos.Type.STRING, 
                                    description="The relative path of the file to read (e.g., 'src/main/AndroidManifest.xml')."
                                )
                            },
                            required=['file_path']
                        )
                    ),
                    protos.FunctionDeclaration(
                        name='find_string_in_project',
                        description="Searches for a specific string or keyword across all files in the project to find relationships.",
                        parameters=protos.Schema(
                            type=protos.Type.OBJECT,
                            properties={
                                'search_term': protos.Schema(
                                    type=protos.Type.STRING,
                                    description="The exact string to search for (e.g., a function name, variable, or log message)."
                                )
                            },
                            required=['search_term']
                        )
                    )
                ]
            )
        ]

    def run(self, max_steps: int = 7) -> Optional[HighConfidenceVulnerability]:
        """
        Runs the investigation loop.
        Returns an updated HighConfidenceVulnerability object or None if it fails.
        """
        # Start a chat session
        chat = self.model.start_chat()
        
        # The initial prompt that frames the agent's task
        initial_prompt = f"""
You are an expert security research agent. Your goal is to validate a potential vulnerability and generate a precise Proof of Concept (POC).
You must use the provided tools to gather evidence. Think step-by-step.

**Initial Potential Finding:**
- **File:** {self.initial_finding.file_path}
- **Line:** {self.initial_finding.line}
- **Description:** {self.initial_finding.description}

Your task is to confirm if this is exploitable. Trace data sources, check configurations in other files, and determine the exact conditions for exploitation.
When you have gathered enough information to be highly confident, provide your final answer as a single, valid JSON object that strictly follows the 'HighConfidenceVulnerability' Pydantic model structure.
Do not provide the final JSON until you are certain and have a full POC. If you determine it is not a vulnerability, state that clearly in plain text. Begin your investigation.
"""
        
        self.investigation_steps.append(f"Agent initiated. Goal: Validate '{self.initial_finding.description}'")
        try:
            response = chat.send_message(initial_prompt)

            for step in range(max_steps):
                part = response.candidates[0].content.parts[0]
                
                if part.function_call:
                    function_call = part.function_call
                    tool_name = function_call.name
                    tool_args = {key: value for key, value in function_call.args.items()}
                    
                    if tool_name == 'read_file_content':
                        tool_result = self._tool_read_file_content(**tool_args)
                    elif tool_name == 'find_string_in_project':
                        tool_result = self._tool_find_string_in_project(**tool_args)
                    else:
                        tool_result = f"Error: Unknown tool '{tool_name}'"

                    response = chat.send_message(
                        protos.Part(
                            function_response=protos.FunctionResponse(name=tool_name, response={'result': tool_result})
                        )
                    )
                else:
                    self.investigation_steps.append("Agent concluded investigation. Final response received.")
                    final_text = part.text
                    
                    try:
                        # Find and parse the JSON blob from the model's final text response
                        json_str_match = re.search(r'```json\n({.*?})\n```', final_text, re.DOTALL)
                        if json_str_match:
                            json_str = json_str_match.group(1)
                        else:
                             # Fallback for raw JSON without markdown
                            json_str = final_text
                        
                        json_blob = json.loads(json_str)
                        updated_vuln = HighConfidenceVulnerability(**json_blob)
                        # Mark as enhanced by the agent
                        updated_vuln.analysis_source = "deep_dive_agent"
                        return updated_vuln
                    except (json.JSONDecodeError, TypeError, ValueError, AttributeError):
                        # The investigation was inconclusive or model didn't return valid JSON
                        self.investigation_steps.append(f"Agent's final response was not a valid JSON object. Response: {final_text[:200]}...")
                        return None
            
            self.investigation_steps.append("Agent reached max steps. Investigation timed out.")
            return None # Return None if max steps are reached
        except Exception as e:
            self.investigation_steps.append(f"An error occurred during agent execution: {e}")
            return None