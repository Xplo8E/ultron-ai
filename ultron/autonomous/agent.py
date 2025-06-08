# ultron/autonomous/agent.py
import os
from pathlib import Path
from rich.console import Console
from rich.markdown import Markdown
from rich.pretty import pprint

# Correct, direct imports from the google.genai library
from google.genai import Client, types

from .tools import get_directory_tree

console = Console()

class AutonomousAgent:
    def __init__(self, codebase_path: str, model_key: str, mission: str, verbose: bool = False):
        self.codebase_path = Path(codebase_path).resolve()
        self.model_key = model_key
        self.mission = mission
        self.verbose = verbose
        
        # Define tools as function declarations for the model
        self.tools = [
            types.Tool(
                function_declarations=[
                    types.FunctionDeclaration(
                        name="read_file_content",
                        description="Reads the full text content of a single file from the provided codebase. The file path must be relative to the project root.",
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "file_path": types.Schema(type=types.Type.STRING, description="Relative path to the file from project root")
                            },
                            required=["file_path"]
                        )
                    )
                ]
            )
        ]
        
        self.tool_handlers = {
            "read_file_content": self.read_file_content,
        }

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set.")
        
        self.client = Client(api_key=api_key)

    def read_file_content(self, file_path: str) -> str:
        """Reads the full text content of a single file from the provided codebase."""
        console.print(f"**[Tool Call]** `read_file_content(file_path='{file_path}')`")
        try:
            # This logic is correct, but the agent needs to be prompted to use the right paths.
            absolute_path = (self.codebase_path / file_path).resolve()
            if not str(absolute_path).startswith(str(self.codebase_path)):
                return "Error: Path traversal attempt detected. Access denied."
            
            if absolute_path.exists() and absolute_path.is_file():
                with open(absolute_path, 'r', encoding='utf-8', errors='ignore') as f:
                    return f.read()
            else:
                # Provide a more helpful error message
                all_files = [str(p.relative_to(self.codebase_path)) for p in self.codebase_path.rglob("*") if p.is_file()]
                return f"Error: File not found at path: '{file_path}'. Available files are: {all_files}"
        except Exception as e:
            return f"Error: Could not read file '{file_path}'. Reason: {e}"

    def _create_initial_prompt(self):
        directory_tree = get_directory_tree(str(self.codebase_path))
        
        # The mission statement is now more focused.
        mission_statement = f"**Primary Objective:** {self.mission}" if self.mission else "**Primary Objective:** Perform a comprehensive security audit to find the most critical, practically exploitable vulnerability."

        return f"""
You are an expert-level autonomous security analysis agent. Your primary goal is to identify **valid, practically exploitable vulnerabilities** and generate a **verifiable Proof of Concept (PoC)**. Your analysis must be meticulous, with an exceptionally low false-positive rate.

**Core Directive: Chain-of-Thought and Action (CoT-A)**
For every step, you MUST first engage in a "thought" process where you reason about the situation, form a hypothesis, and decide on a course of action. Only after thinking should you select and call a tool. This thought process is critical for accuracy.

**Codebase Structure:**
{directory_tree}

**Tool Usage Protocol:**
- All file paths provided to tools must be relative to the project root, exactly as they appear in the directory structure above. Do not invent or assume paths.

{mission_statement}

**Universal Security Analysis Methodology (Zero Trust):**
1.  **Reconnaissance & Hypothesis:** Analyze the project structure to form a hypothesis about the most likely attack surface (e.g., components handling external input, complex authorization logic, use of dangerous libraries). State your hypothesis in your thought process.
2.  **Evidence Gathering:** Use tools to read the source code for the components you identified.
3.  **Taint Analysis:** Identify all data that crosses a trust boundary (e.g., API inputs, file contents, IPC messages) and treat it as "tainted." Trace this data to security-sensitive operations ("sinks").
4.  **Control Auditing:** Rigorously challenge every security control associated with a data flow. Do not trust them.
    -   **Input Validation:** Is it complete? Does it prevent canonicalization errors, encoding attacks, or type confusion?
    -   **Access Control:** Is it correctly enforced? Could a compromised but trusted caller (a "Confused Deputy") abuse its privileges?
5.  **Conclusion & Reporting:**
    -   Your final response MUST be a structured markdown report. Do not include any conversational filler (e.g., "Okay, here's my final report..."). Your response should begin directly with the report's first heading.
    -   When you have gathered sufficient evidence to confirm a **practically exploitable vulnerability**, you **must stop using tools**. Your final response MUST use the following markdown format:

        ```markdown
        # ULTRON-AI Security Finding

        **Vulnerability:** [Concise, one-line title of the vulnerability]
        **Severity:** [Critical | High | Medium | Low]
        **CWE:** [e.g., CWE-79: Improper Neutralization of Input During Web Page Generation ('Cross-site Scripting')]

        ---

        ### Description
        [Detailed but concise explanation of the vulnerability, the vulnerable component, and the root cause.]

        ### Attack Chain
        [A step-by-step explanation of how an attacker would exploit this vulnerability, from initial interaction to final impact.]

        ### Proof of Concept (PoC)
        [A complete, verifiable, and working Proof of Concept. This should be a self-contained code block.]
        ```
        **[PoC Code Block]**
        ```bash
        # Example: a curl command or a script
        curl ...
        ```

        ### Remediation
        [A clear, actionable recommendation on how to fix the vulnerability, including a code snippet of the corrected code if possible.]
        ```

    -   If, after a thorough investigation, you cannot find any high-confidence, exploitable vulnerabilities, you **must also stop using tools**. Your final response MUST use the following markdown format:

        ```markdown
        # ULTRON-AI Security Analysis Conclusion

        **Status:** No high-confidence, practically exploitable vulnerabilities were identified.

        ---

        ### Analysis Summary
        A security analysis was performed on the codebase, focusing on the following areas:
        -   **[Component/Area 1]:** [Brief summary of what was checked and why it was deemed secure, e.g., 'Reviewed SupportActionReceiver for intent redirection. Found that the use of `setPackage()` effectively mitigates the risk of unauthorized intent forwarding.']
        -   **[Component/Area 2]:** [Brief summary of what was checked and why it was deemed secure, e.g., 'Analyzed LogFileProvider. Confirmed it is not exported and is protected by a signature-level permission, preventing direct access from untrusted applications.']
        -   ...add more areas as needed...

        ### Overall Conclusion
        The key security controls, such as [mention 1-2 key controls like 'signature-level permissions', 'explicit intent targeting'], appear to be correctly implemented, making the analyzed attack vectors not feasible.
        ```
"""

    def run(self, max_turns=20) -> str:
        initial_prompt = self._create_initial_prompt()
        # This chat history management is exactly from your prototype
        chat_history = [
            types.Content(role="user", parts=[types.Part(text=initial_prompt)])
        ]
        final_report = None

        for turn in range(max_turns):
            console.print(f"\n[bold]================ TURN {turn + 1}/{max_turns} ================[/bold]\n")

            # ==================== CORRECTED VERBOSE LOGGING: REQUEST ====================
            if self.verbose:
                console.print("[bold cyan]➡️ Sending Request to Model...[/bold cyan]")
                # We send the entire history for context, but for logging,
                # showing the last two turns (model's request + tool response) is most useful.
                for message in chat_history: # Log the last 2 messages
                    console.print(f"Role: {message.role}")
                    text_content = ""
                    for part in message.parts:
                        if hasattr(part, 'text') and part.text:
                            text_content += part.text + "........................."
                    if text_content:
                        console.print(f"Content: {text_content}")
                console.print("-" * 20)
            # ==========================================================================

            response = self.client.models.generate_content(
                model=self.model_key,
                contents=chat_history,
                config=types.GenerateContentConfig(
                    tools=self.tools,
                    temperature=0.1,
                    top_k=20,
                    top_p=0.8,
                    max_output_tokens=8192,
                    thinking_config=types.ThinkingConfig(
                        include_thoughts=True,
                        thinking_budget=2048
                    )
                )
            )
            
            # ==================== VERBOSE LOGGING: RESPONSE ===================
            if self.verbose:
                console.print("[bold magenta]⬅️ Received Raw Response From Model...[/bold magenta]")
                # No change needed here, pprint handles the response object correctly.
                pprint(response)
                console.print("-" * 20)
            # ================================================================

            candidate = response.candidates[0]
            parts = candidate.content.parts
            
            # --- REFACTORED AGENT LOOP LOGIC ---
            all_text_parts = [p.text.strip() for p in parts if hasattr(p, 'text') and p.text and p.text.strip()]
            tool_call_part = next((p for p in parts if hasattr(p, "function_call") and p.function_call), None)
            
            # Display thought if present (usually the first text part)
            if all_text_parts:
                thought_text = all_text_parts[0]
                # If a tool is called, all text is part of the thought process
                if tool_call_part:
                    thought_text = "\n".join(all_text_parts)
                console.print(Markdown(f"**💭 Thought:**\n> {thought_text}"))
            
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

                console.print(Markdown(f"**🔬 Observation:**\n```\n{result}\n```"))

                tool_response_part = types.Part.from_function_response(name=fn_name, response={"result": result})
                chat_history.append(candidate.content)
                chat_history.append(types.Content(role="tool", parts=[tool_response_part]))
            
            else:
                # No tool call, this must be the final turn.
                console.print(Markdown(f"**✅ Agent has concluded its investigation.**"))
                if len(all_text_parts) > 1:
                    # If there's a thought and a final answer, the final answer is the last part
                    final_report = all_text_parts[-1]
                elif all_text_parts:
                    # If there's only one text part, it's the final answer
                    final_report = all_text_parts[0]
                else:
                    final_report = "Agent finished without a textual report."
                break # Exit the main 'for turn' loop

        return final_report or "Agent reached maximum turns without providing a final report."
    