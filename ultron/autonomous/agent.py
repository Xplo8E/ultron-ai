# ultron/autonomous/agent.py
import os
from pathlib import Path
from rich.console import Console
from rich.markdown import Markdown
from rich.pretty import pprint
from rich.panel import Panel
from rich.text import Text
from google.genai import Client, types

from .tools import (
    get_directory_tree,
    search_pattern_in_file,
    list_functions_in_file,
    find_taints_in_file,
)
from ..core.constants import AVAILABLE_MODELS, MODELS_SUPPORTING_THINKING  

console = Console()

class AutonomousAgent:
    def __init__(self, codebase_path: str, model_key: str, mission: str, verbose: bool = False):
        self.codebase_path = Path(codebase_path).resolve()
        self.model_key = AVAILABLE_MODELS[model_key]
        self.mission = mission
        self.verbose = verbose
        self.supports_thinking = self.model_key in MODELS_SUPPORTING_THINKING
        
        # --- MODIFIED: Define all tools for the model ---
        self.tools = [
            types.Tool(
                function_declarations=[
                    types.FunctionDeclaration(
                        name="read_file_content",
                        description="Reads the full text content of a single file. The file path must be relative to the project root.",
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={"file_path": types.Schema(type=types.Type.STRING, description="Relative path to the file from project root.")},
                            required=["file_path"]
                        )
                    ),
                    types.FunctionDeclaration(
                        name="search_pattern",
                        description="Searches for a regex pattern within a single file and returns matching lines with line numbers.",
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "file_path": types.Schema(type=types.Type.STRING, description="Relative path to the file."),
                                "regex_pattern": types.Schema(type=types.Type.STRING, description="The regex pattern to search for.")
                            },
                            required=["file_path", "regex_pattern"]
                        )
                    ),
                    types.FunctionDeclaration(
                        name="list_functions",
                        description="Lists all function and class method definitions in a Python (.py) file.",
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={"file_path": types.Schema(type=types.Type.STRING, description="Relative path to the Python file.")},
                            required=["file_path"]
                        )
                    ),
                    types.FunctionDeclaration(
                        name="find_taint_sources_and_sinks",
                        description="Scans a file to find lines containing potential sources (e.g., user input) and sinks (e.g., command execution).",
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "file_path": types.Schema(type=types.Type.STRING, description="Relative path to the file."),
                                "sources": types.Schema(type=types.Type.ARRAY, items=types.Schema(type=types.Type.STRING), description="Keywords for untrusted data sources (e.g., 'request.args', 'os.environ')."),
                                "sinks": types.Schema(type=types.Type.ARRAY, items=types.Schema(type=types.Type.STRING), description="Keywords for dangerous sinks (e.g., 'eval', 'subprocess.run').")
                            },
                            required=["file_path", "sources", "sinks"]
                        )
                    )
                ]
            )
        ]
        
        # --- MODIFIED: Map all tool handlers ---
        self.tool_handlers = {
            "read_file_content": self.read_file_content,
            "search_pattern": self.search_pattern,
            "list_functions": self.list_functions,
            "find_taint_sources_and_sinks": self.find_taint_sources_and_sinks,
        }

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set.")
        
        self.client = Client(api_key=api_key)

    def _resolve_and_validate_path(self, file_path: str) -> tuple[Path | None, str | None]:
        """Resolves a relative path to an absolute one and provides helpful errors."""
        if '..' in Path(file_path).parts or Path(file_path).is_absolute():
            return None, "Error: Path traversal or absolute paths are not allowed. Use relative paths from the project root."
        
        absolute_path = (self.codebase_path / file_path).resolve()
        
        if not str(absolute_path).startswith(str(self.codebase_path)):
            return None, "Error: Path traversal attempt detected. Access denied."

        if absolute_path.is_file():
            return absolute_path, None  # Success!

        # --- Enhanced Error Handling ---
        if absolute_path.is_dir():
            try:
                contents = [p.name for p in absolute_path.iterdir()]
                contents_str = ", ".join(sorted(contents)) if contents else "It is empty."
                return None, f"Error: Path '{file_path}' is a directory, not a file. Its contents are: [{contents_str}]."
            except Exception as e:
                return None, f"Error: Path '{file_path}' is a directory, but its contents could not be read. Reason: {e}"

        # If the path doesn't exist, check its parent for context.
        parent_dir = absolute_path.parent
        if parent_dir.is_dir():
            try:
                contents = [p.name for p in parent_dir.iterdir()]
                contents_str = ", ".join(sorted(contents)) if contents else "It is empty."
                relative_parent = parent_dir.relative_to(self.codebase_path)
                relative_parent_str = str(relative_parent) if str(relative_parent) != '.' else 'the root directory'
                return None, f"Error: File not found at path '{file_path}'. The parent directory '{relative_parent_str}' exists and contains: [{contents_str}]."
            except Exception as e:
                return None, f"Error: File not found at path '{file_path}'. The parent directory exists, but its contents could not be read. Reason: {e}"
        else:
            relative_parent = parent_dir.relative_to(self.codebase_path)
            return None, f"Error: Cannot access path '{file_path}' because its directory '{relative_parent}' does not exist."

    def read_file_content(self, file_path: str) -> str:
        """Handler for reading file content."""
        console.print(f"**[Tool Call]** `read_file_content(file_path='{file_path}')`")
        absolute_path, error = self._resolve_and_validate_path(file_path)
        if error:
            return error
        try:
            with open(absolute_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        except Exception as e:
            return f"Error: Could not read file '{file_path}'. Reason: {e}"

    # --- NEW TOOL HANDLER METHODS ---

    def search_pattern(self, file_path: str, regex_pattern: str) -> str:
        """Handler for searching a pattern in a file."""
        console.print(f"**[Tool Call]** `search_pattern(file_path='{file_path}', regex_pattern='{regex_pattern}')`")
        absolute_path, error = self._resolve_and_validate_path(file_path)
        if error:
            return error
        return search_pattern_in_file(str(absolute_path), regex_pattern)

    def list_functions(self, file_path: str) -> str:
        """Handler for listing functions in a Python file."""
        console.print(f"**[Tool Call]** `list_functions(file_path='{file_path}')`")
        absolute_path, error = self._resolve_and_validate_path(file_path)
        if error:
            return error
        return list_functions_in_file(str(absolute_path))

    def find_taint_sources_and_sinks(self, file_path: str, sources: list[str], sinks: list[str]) -> str:
        """Handler for finding taint sources and sinks."""
        console.print(f"**[Tool Call]** `find_taint_sources_and_sinks(file_path='{file_path}', sources={sources}, sinks={sinks})`")
        absolute_path, error = self._resolve_and_validate_path(file_path)
        if error:
            return error
        return find_taints_in_file(str(absolute_path), sources, sinks)
        
    def _create_initial_prompt(self):
        directory_tree = get_directory_tree(str(self.codebase_path))
        mission = self.mission or "Perform a deep static security audit to discover the most critical, practically exploitable vulnerabilities in the codebase and produce working Proofs of Concept."

        return f"""
    You are a specialized static analysis agent tasked with uncovering **high-confidence**, **practically exploitable** vulnerabilities. Use **chain-of-thought**: clearly articulate your hypothesis, then select the minimal tool call to validate it. Iterate this loop until you either confirm an exploit or exhaust relevant code paths.

    **MISSION**: {mission}

    **PROJECT STRUCTURE**:
    {directory_tree}

    ---

    ## TOOL USAGE GUIDELINES

    - **Recovery from Failure**: If a specialized tool like `list_functions` fails, it's likely not a valid Python file. Your next step should be to use `read_file_content` to understand its contents and purpose.
    - **`find_taint_sources_and_sinks` Strategy**: If this tool returns "No matches found," **DO NOT** assume the file is safe. This often means your source/sink keywords are wrong for the project's framework. Your next step must be to use `read_file_content` to identify the actual functions used for handling input and executing dangerous operations, then call `find_taint_sources_and_sinks` again with the correct keywords.
    - **File Not Found Errors**: If a tool returns a "File not found" or "Directory not found" error, carefully read the error message. It will often contain a list of files and directories that *do* exist, which you can use to correct the path in your next tool call.

    ---

    ## ANALYSIS PROCEDURE

    For each potential attack surface:

    1. 🧠 **Hypothesize**: Explain why this component or file may hold a vulnerability (e.g., handles untrusted input, uses deserialization, invokes system calls).

    2. 🔍 **Inspect**: Use precise tool calls, such as:
    - `read_file_content(file_path)`
    - `search_pattern(file_path, regex_pattern)`
    - `list_functions(file_path)`
    - `find_taint_sources_and_sinks(file_path, sources, sinks)`

    3. 📊 **Reason**: Analyze results. Confirm or refute your hypothesis with concrete evidence (e.g., code snippet, data flow trace).

    4. 🔄 **Iterate**: Based on evidence, form the next hypothesis and repeat.

    5. 🚩 **Exploit Confirmation**: Once you have a clear exploit chain and can construct a valid PoC, cease tool usage and prepare your final report.

    ---

    ## REPORT TEMPLATES

    ### If a vulnerability is found:
    ```markdown
    # ULTRON-AI Security Finding

    **Vulnerability:** [Concise title]
    **Severity:** [Critical | High | Medium | Low]
    **CWE:** [CWE-XX]

    ---

    ### Description
    [Detailed explanation of the flaw and its root cause.]

    ### Attack Chain
    [Step-by-step exploitation path from entry point to impact.]

    ### Proof of Concept (PoC)
    ```bash
    # Working PoC with necessary commands or script
    echo '<payload>' | exploit_tool --target /vulnerable_endpoint
    ```

    ### Remediation
    [Concrete code or config changes to fix the issue.]
    ```

    ### If no exploitable vulnerabilities are identified:
    ```markdown
    # ULTRON-AI Security Analysis Conclusion

    **Status:** No high-confidence, practically exploitable vulnerabilities identified.

    ---

    ### Analysis Summary
    - [File/Component A]: checks and evidence of safety.
    - [File/Component B]: ...

    ### Overall Conclusion
    The codebase is secure against the defined threat model.
    ```

    ---

    **RULES:**
    - **Do not** report style issues or unproven best practices.
    - **Do not** include any text beyond the specified templates.
    - **Stop** tool usage as soon as you have a confirmed exploit or final conclusion.

    Begin with your first hypothesis."""


    def run(self, max_turns=100) -> str:
        initial_prompt = self._create_initial_prompt()
        chat_history = [
            types.Content(role="user", parts=[types.Part(text=initial_prompt)])
        ]
        final_report = None

        for turn in range(max_turns):
            turn_text = Text(f"🤖 ULTRON TURN {turn + 1}/{max_turns}", style="bold white")
            console.print(Panel(turn_text, style="bold cyan", padding=(0, 1)))

            if self.verbose:
                console.print("[bold cyan]➡️ Sending Request to Model...[/bold cyan]")
                for message in chat_history:
                    console.print(f"Role: {message.role}")
                    text_content = ""
                    for part in message.parts:
                        if hasattr(part, 'text') and part.text:
                            text_content += part.text + "\n........................."
                    if text_content:
                        console.print(f"Content: {text_content}")
                console.print("-" * 20)
            
            config_args = {
                "tools": self.tools,
                "temperature": 0.1,
                "top_k": 20,
                "top_p": 0.8,
                "max_output_tokens": 8192,
            }
            if self.supports_thinking:
                config_args["thinking_config"] = types.ThinkingConfig(
                    include_thoughts=True,
                    thinking_budget=2048
                )
            
            config = types.GenerateContentConfig(**config_args)

            response = self.client.models.generate_content(
                model=self.model_key,
                contents=chat_history,
                config=config
            )
            
            # Extract and display token usage information
            if hasattr(response, 'usage_metadata') and response.usage_metadata:
                usage = response.usage_metadata
                prompt_tokens = getattr(usage, 'prompt_token_count', 0)
                output_tokens = getattr(usage, 'candidates_token_count', 0)
                thought_tokens = getattr(usage, 'thoughts_token_count', 0)
                total_tokens = getattr(usage, 'total_token_count', 0)
                
                token_text = Text(f"📊 Tokens: Prompt={prompt_tokens} | Output={output_tokens} | Thoughts={thought_tokens} | Total={total_tokens}", style="dim cyan")
                console.print(Panel(token_text, style="dim blue", padding=(0, 1)))

            if self.verbose:
                console.print("[bold magenta]⬅️ Received Raw Response From Model...[/bold magenta]")
                pprint(response)
                console.print("-" * 20)

            candidate = response.candidates[0]
            parts = candidate.content.parts
            
            all_text_parts = [p.text.strip() for p in parts if hasattr(p, 'text') and p.text and p.text.strip()]
            tool_call_part = next((p for p in parts if hasattr(p, "function_call") and p.function_call), None)
            
            # print thought count when printing the rhought for supported thinking models
            # print("Thoughts tokens:",response.usage_metadata.thoughts_token_count)
            if all_text_parts:
                reasoning_text = "\n".join(all_text_parts)
                if self.supports_thinking:
                    console.print(f"**💭 Thought Count:** {response.usage_metadata.thoughts_token_count}")
                label = "**💭 Thought:**" if self.supports_thinking else "**🧠 Reasoning:**"
                console.print(Markdown(f"{label}\n> {reasoning_text}"))
            
            if tool_call_part:
                fn = tool_call_part.function_call
                fn_name = fn.name
                fn_args = {key: value for key, value in fn.args.items()}

                console.print(f"**🛠️ Calling Tool:** `{fn_name}({fn_args})`")

                tool_func = self.tool_handlers.get(fn_name)
                if tool_func:
                    result = tool_func(**fn_args)
                else:
                    result = f"Tool {fn_name} not found."

                print("Output tokens:",response.usage_metadata.candidates_token_count)
                console.print(Markdown(f"**🔬 Observation:**\n```\n{result}\n```"))
                # print output tokens when printing the output everytime
                tool_response_part = types.Part.from_function_response(name=fn_name, response={"result": result})
                chat_history.append(candidate.content)
                chat_history.append(types.Content(role="tool", parts=[tool_response_part]))
            
            else:
                console.print(Markdown(f"**✅ Agent has concluded its investigation.**"))
                if len(all_text_parts) > 1:
                    final_report = all_text_parts[-1]
                elif all_text_parts:
                    final_report = all_text_parts[0]
                else:
                    final_report = "Agent finished without a textual report."
                break

        return final_report or "Agent reached maximum turns without providing a final report."
    