# ultron/autonomous/agent.py
"""
Ultron Autonomous Agent - Refactored for modularity and clarity.
The main agent orchestration class that coordinates LLM interactions with tools.
"""

import os
import time
import re
from pathlib import Path
from datetime import datetime
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text
from google.genai import Client, types
from google.api_core import exceptions as google_exceptions
from pprint import pformat

from .config import AgentConfig
from .prompts import get_system_instruction_template, get_workflow_section, get_sandbox_section
from .tool_handler import ToolHandler
from .tools import get_directory_tree
from ..core.constants import AVAILABLE_MODELS, MODELS_SUPPORTING_THINKING

console = Console()

class AutonomousAgent:
    """
    The main autonomous agent class. Now lean and focused on orchestrating
    the conversation with the LLM while delegating tool execution and 
    configuration management to specialized components.
    """

    def __init__(self, codebase_path: str, model_key: str, mission: str, verification_target: str | None = None, sandbox_mode: bool = True, verbose: bool = False, log_dir: str = "logs", max_turns: int = 50):
        """
        Initialize the autonomous agent with modular components.
        
        Args:
            codebase_path: Path to the codebase to analyze
            model_key: Key identifying which model to use
            mission: The specific mission or goal for the agent
            verification_target: Optional target URL/service for dynamic verification
            sandbox_mode: Whether to enable sandbox mode
            verbose: Whether to enable verbose logging
            log_dir: Directory for log files
        """
        # --- 1. Configuration Setup ---
        log_dir_path = Path(log_dir)
        log_dir_path.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = log_dir_path / f"ultron_run_{timestamp}.log"
        
        self.config = AgentConfig(
            codebase_path=Path(codebase_path).resolve(),
            model_key=model_key,
            mission=mission,
            verification_target=verification_target,
            sandbox_mode=sandbox_mode,
            log_file_path=log_file,
            verbose=verbose,
            max_turns=max_turns
        )
        
        # --- 2. Model Configuration ---
        self.supports_thinking = self.config.model_key in MODELS_SUPPORTING_THINKING
        
        # --- 3. Tool Management ---
        self.tool_handler = ToolHandler(codebase_path=self.config.codebase_path)
        
        # Get the tools and handlers from the ToolHandler
        self.tools = [types.Tool(function_declarations=self.tool_handler.get_all_tool_definitions())]
        self.tool_map = self.tool_handler.get_tool_map()

        # --- 4. API Client Setup ---
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set.")
        
        self.found_vulnerabilities = []
        self.total_prompt_tokens_run = 0
        self.total_candidates_tokens_run = 0
        self.total_thoughts_tokens_run = 0
        self.total_tokens_run = 0

        self.client = Client(api_key=api_key)

        # --- 5. Initial Logging ---
        self._log(f"--- Ultron Run Initialized ---\n{self.config}")

    def _log(self, content: str):
        """
        Appends content to the run's log file.
        
        Args:
            content: Content to write to the log file
        """
        with open(self.config.log_file_path, "a", encoding="utf-8") as f:
            f.write(content + "\n")

    def run(self) -> str:
        """
        Main execution loop for the agent.
        
        Args:
            max_turns: Maximum number of conversation turns
            
        Returns:
            Final report from the agent
        """
        console.print(Panel(
            f"📝 Logging full transcript to [bold cyan]{self.config.log_file_path}[/bold cyan]", 
            style="blue"
        ))
        
        # Generate the directory tree (now much more efficient)
        directory_tree = get_directory_tree(str(self.config.codebase_path))
        max_turns = self.config.max_turns
        # Create the system instruction (static context)
        system_instruction_template = get_system_instruction_template()
        workflow_section = get_workflow_section(self.config.verification_target)
        sandbox_section = get_sandbox_section(self.config.sandbox_mode)

        system_instruction_content = system_instruction_template.format(
            mission=self.config.mission,
            workflow_section=workflow_section,
            directory_tree=directory_tree,
            sandbox_section=sandbox_section
        )
        
        # Create the first user message (dynamic context)
        initial_user_message = f"Your mission is set. Begin your analysis now by following the PHASE 1 guidelines. \n\n**MISSION**: {self.config.mission}"
        
        self._log(f"\n--- System Instruction ---\n{system_instruction_content}")
        self._log(f"\n--- Initial User Message ---\n{initial_user_message}")
        
        # Initialize conversation history with just the user message
        chat_history = [
            types.Content(role="user", parts=[types.Part(text=initial_user_message)])
        ]
        
        final_report = None

        # Main conversation loop
        for turn in range(max_turns):
            turn_text = Text(f"🤖 ULTRON TURN {turn + 1}/{max_turns}", style="bold white")
            console.print(Panel(turn_text, style="bold cyan", padding=(0, 1)))
            self._log(f"\n\n{'='*20} TURN {turn + 1}/{max_turns} {'='*20}")

            # Log the request being sent
            self._log("\n--- Request to Model ---")
            for message in chat_history:
                self._log(f"Role: {message.role}")
                for part in message.parts:
                    log_part_content = ""
                    if hasattr(part, 'text') and part.text:
                        log_part_content = f"Text: {part.text}"
                    elif hasattr(part, 'function_call'):
                        log_part_content = f"Function Call: {part.function_call}"
                    elif hasattr(part, 'function_response'):
                        log_part_content = f"Function Response: {part.function_response}"
                    self._log(log_part_content)
                self._log("-" * 10)

            # Verbose logging if enabled
            if self.config.verbose:
                console.print("[bold cyan]➡️ Sending Request to Model...[/bold cyan]")
                for message in chat_history:
                    console.print(f"Role: {message.role}")
                    text_content = ""
                    for part in message.parts:
                        if hasattr(part, 'text') and part.text:
                            text_content += part.text + "\n.........................\n"
                    if text_content:
                        console.print(f"Content: {text_content}")
                console.print("-" * 20)
            
            # Configure the API request
            config_args = {
                "tools": self.tools,
                "temperature": 0.2,
                "top_k": 10,
                "top_p": 0.7,
                "max_output_tokens": 8192,
                "system_instruction": system_instruction_content,
            }
            if self.supports_thinking:
                config_args["thinking_config"] = types.ThinkingConfig(
                    include_thoughts=True,
                    thinking_budget=8000
                )
                config_args["max_output_tokens"] = 30000
                config_args["temperature"] = 0.7
                config_args["top_k"] = 20
                config_args["top_p"] = 0.8
            
            config = types.GenerateContentConfig(**config_args)

            # Add delay before request
            console.print("[dim yellow]⏳ Waiting 4 seconds before request...[/dim yellow]")
            time.sleep(4)
            
            # Make the API request with retry logic
            response = self._make_api_request(chat_history, config, max_retries=3)
            if not response:
                self._log("Agent failed to get a response from the API after multiple retries.")
                return "Agent failed to get a response from the API after multiple retries."
            
            # Display token usage information
            self._display_token_usage(response, turn + 1, max_turns)
            
            # Log the raw response
            self._log(f"\n--- Raw Response from Model ---\n{pformat(response)}")

            if self.config.verbose:
                console.print("[bold magenta]⬅️ Received Raw Response From Model...[/bold magenta]")
                console.print(response)
                console.print("-" * 20)

            if not response.candidates:
                # Handle the rare case of no candidates
                console.print(Panel("⚠️ The API returned no candidates. This may be due to a prompt block. Skipping turn.", style="bold yellow"))
                self._log("\n--- API returned no candidates. Skipping turn. ---")
                continue # Skip to the next turn

            candidate = response.candidates[0]

            # --- NEW: GRACEFUL HANDLING OF BLOCKED RESPONSES ---
            if candidate.content is None:
                finish_reason = getattr(candidate, 'finish_reason', 'UNKNOWN')
                safety_ratings = getattr(candidate, 'safety_ratings', [])
                
                # Log and display the reason for the block
                error_panel = Panel(
                    f"🛑 Model response was blocked.\n"
                    f"Finish Reason: [bold]{finish_reason}[/bold]\n"
                    f"Safety Ratings: {safety_ratings}",
                    title="[bold red]Safety Filter Triggered[/bold red]",
                    border_style="red"
                )
                console.print(error_panel)
                self._log(f"\n--- SAFETY BLOCK ---\nFinish Reason: {finish_reason}\nRatings: {safety_ratings}\n")

                # Instruct the model to self-correct
                correction_text = "Your previous response was blocked by the safety filter. You MUST re-evaluate your strategy. Do not generate content that directly resembles a dangerous exploit. Instead, describe the vulnerability conceptually and try a different tool or approach. For example, use `read_file_content` to gather more context instead of attempting a direct action."
                chat_history.append(types.Content(role="user", parts=[types.Part(text=correction_text)]))
                
                continue # Skip the rest of this turn's logic and start the next loop


            # --- Existing Logic (now safe to run) ---
            parts = candidate.content.parts
            
            all_text_parts = [p.text.strip() for p in parts if hasattr(p, 'text') and p.text and p.text.strip()]
            tool_call_part = next((p for p in parts if hasattr(p, "function_call") and p.function_call), None)
            
            # Display reasoning/thinking
            if all_text_parts:
                reasoning_text = "\n".join(all_text_parts)
                label = "**💭 Thought:**" if self.supports_thinking else "**🧠 Reasoning:**"
                console.print(Markdown(f"{label}\n> {reasoning_text}"))
                self._log(f"\n--- Parsed Reasoning/Thought ---\n{reasoning_text}")
            
            # Handle tool calls
            if tool_call_part:
                fn = tool_call_part.function_call
                fn_name = fn.name
                fn_args = {key: value for key, value in fn.args.items()}

                # --- NEW LOGIC: Intercept the 'save_finding_and_continue' tool ---
                if fn_name == "save_finding_and_continue":

                    report_content = fn_args.get("report", "No report content provided.")
                    self.found_vulnerabilities.append(report_content)
                    console.print(Markdown("**✅ Finding saved!** Ultron will now continue searching for more vulnerabilities."))
                    self._log(f"\n--- VULNERABILITY FINDING SAVED ---\n{report_content}")
                    
                    result = "Your finding has been saved. You MUST now continue your analysis to find other, different vulnerabilities. Do not report the same finding again. Form a new hypothesis and call a new tool."
                    tool_response_part = types.Part.from_function_response(name=fn_name, response={"result": result})

                else:

                    console.print(f"**🛠️ Calling Tool:** `{fn_name}({fn_args})`")
                    self._log(f"\n--- Tool Call ---\n{fn_name}({pformat(fn_args)})")

                    # Execute the tool
                    tool_func = self.tool_map.get(fn_name)
                    if tool_func:
                        result = tool_func(**fn_args)
                    else:
                        result = f"Tool {fn_name} not found."

                    console.print(Markdown(f"**🔬 Observation:**\n```\n{result}\n```"))
                    self._log(f"\n--- Tool Observation ---\n{result}")
                    
                    # Add the tool response to conversation history
                    tool_response_part = types.Part.from_function_response(name=fn_name, response={"result": result})

                chat_history.append(candidate.content)
                if tool_response_part:
                    chat_history.append(types.Content(role="tool", parts=[tool_response_part]))
                
            else:
                # This case (no tool call) is now unexpected. Prompt the agent to continue.
                console.print(Markdown("**⚠️ Agent did not call a tool as required. Prompting to continue.**"))
                self._log("\n--- AGENT STALLED: No tool call detected. Injecting prompt to continue. ---")
                
                # Add the agent's (flawed) response to history
                chat_history.append(candidate.content)
                # Add a new user message to steer the agent back on track
                no_tool_response = types.Content(role="user", parts=[types.Part(text="You MUST end every turn with a tool call. Please continue your analysis by forming a hypothesis and calling a tool, or use 'save_finding_and_continue' if you have a complete report.")])
                chat_history.append(no_tool_response)

        # --- NEW LOGIC: Generate the final consolidated report AFTER the loop finishes ---
        console.print(Panel("🏁 **ANALYSIS COMPLETE** 🏁", style="bold green", padding=(0, 1)))
        
        if not self.found_vulnerabilities:
            final_summary = "# ULTRON-AI Security Analysis Conclusion\n\n**Status:** No high-confidence, practically exploitable vulnerabilities identified after the analysis."
        else:
            vuln_count = len(self.found_vulnerabilities)
            header = f"# ULTRON-AI Final Security Summary\n\nFound **{vuln_count}** vulnerabilities during this session.\n\n"
            # Join all the individual markdown reports with a separator
            all_reports = "\n\n---\n\n".join(self.found_vulnerabilities)
            final_summary = header + all_reports

        self._log(f"\n\n{'='*20} FINAL SUMMARY {'='*20}\n{final_summary}")
        return final_summary
    
    def _make_api_request(self, chat_history, config, max_retries: int = 3):
        """
        Make an API request with retry logic for rate limiting.
        
        Args:
            chat_history: The conversation history
            config: API configuration (includes system_instruction)
            max_retries: Maximum number of retry attempts
            
        Returns:
            API response or None if all retries failed
        """
        for attempt in range(max_retries):
            try:

                request_token_response = self.client.models.count_tokens(
                    model=AVAILABLE_MODELS[self.config.model_key],
                    contents=chat_history
                )
                request_tokens = request_token_response.total_tokens
                console.print(f"[dim cyan]📊 Pre-flight Check: Request contains {request_tokens} tokens.[/dim cyan]")

                response = self.client.models.generate_content(
                    model=AVAILABLE_MODELS[self.config.model_key],
                    contents=chat_history,
                    config=config
                )
                return response
                
            except google_exceptions.GoogleAPICallError as e:
                error_str = str(e).upper()
                console.print(f"[bold red]❌ An API error occurred. The failed request contained {request_tokens} tokens.[/bold red]")
                self._log_and_display_run_totals_on_error()
                if "RESOURCE_EXHAUSTED" in error_str or "429" in error_str:
                    wait_time = 60
                    
                    # Try to extract retry delay from error message
                    match = re.search(r"'retryDelay': '(\d+)s'", str(e))
                    if match:
                        wait_time = int(match.group(1)) + 2

                    panel_text = Text(
                        f"Rate limit hit. Waiting for {wait_time}s before retrying ({attempt + 1}/{max_retries}).", 
                        style="bold yellow"
                    )
                    console.print(Panel(panel_text, title="[yellow]Rate Limit Handler[/yellow]", border_style="yellow"))
                    
                    if attempt + 1 >= max_retries:
                        console.print("[bold red]❌ CRITICAL: Max retries reached. Aborting run.[/bold red]")
                        return None
                        
                    time.sleep(wait_time)
                else:
                    console.print(f"[bold red]❌ An unexpected, non-retriable API error occurred: {e}[/bold red]")
                    self._log(f"\n--- NON-RETRIABLE API ERROR ---\n{e}")
                    return None
                    
            except Exception as e:
                console.print(f"[bold red]❌ A critical unexpected error occurred: {e}[/bold red]")
                console.print(f"[dim red]The failed request contained approx. {request_tokens} tokens.[/dim red]")
                self._log(f"\n--- CRITICAL UNEXPECTED ERROR ---\n{e}")
                self._log_and_display_run_totals_on_error()
                return None
        
        return None
    
    def _display_token_usage(self, response, turn: int, max_turns: int):
        """
        Display token usage information from the API response.
        
        Args:
            response: API response object
            turn: Current turn number
            max_turns: Maximum number of turns
        """
        if hasattr(response, 'usage_metadata') and response.usage_metadata:
            usage = response.usage_metadata
            prompt_tokens = getattr(usage, 'prompt_token_count', 0) or 0
            output_tokens = getattr(usage, 'candidates_token_count', 0) or 0
            thought_tokens = getattr(usage, 'thoughts_token_count', 0) or 0
            total_tokens = getattr(usage, 'total_token_count', 0) or 0
            
            # --- NEW: Update the running totals for the session ---
            self.total_prompt_tokens_run += prompt_tokens
            self.total_candidates_tokens_run += output_tokens
            self.total_thoughts_tokens_run += thought_tokens
            self.total_tokens_run += total_tokens
            
            # MODIFIED: Update the panel to include the running total
            token_text = Text(
                f"📊 Turn: Prompt={prompt_tokens} | Output={output_tokens} | Thoughts={thought_tokens} | Total={total_tokens} | cumulatively: Total={self.total_tokens_run} | Model: {self.config.model_key} | Supports Thinking: {self.supports_thinking} | Turn: {turn}/{max_turns}",
                style="dim cyan"
            )
            console.print(Panel(token_text, style="dim blue", padding=(0, 1))) 

    def _log_and_display_run_totals_on_error(self):
        """
        Logs and prints the cumulative token usage for the run, intended for use on error.
        """
        error_summary = (
            f"**Cumulative Token Usage Summary (at time of error):**\n"
            f"- Total Prompt Tokens: {self.total_prompt_tokens_run}\n"
            f"- Total Output (Candidates) Tokens: {self.total_candidates_tokens_run}\n"
            f"- Total Thoughts Tokens: {self.total_thoughts_tokens_run}\n"
            f"- **Grand Total for Run:** {self.total_tokens_run}"
        )
        
        panel_text = Text(error_summary, style="bold yellow")
        console.print(Panel(panel_text, title="[yellow]Run Token Summary[/yellow]", border_style="yellow"))
        self._log(f"\n--- CUMULATIVE TOKEN USAGE ON ERROR ---\n{error_summary}")