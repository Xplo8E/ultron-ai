# ultron/engine/llm_code_analyzer.py

import os
from typing import Optional

# MODIFIED: Import the genai module and initialize the client, just like in reviewer.py
from google import genai
from rich.console import Console

from ..core.constants import LLM_ANALYZER_PROMPT_TEMPLATE, AVAILABLE_MODELS

console = Console()

# MODIFIED: Initialize the client to make compatible API calls
GEMINI_API_KEY_LOADED = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY_LOADED:
    genai_client = genai.Client(api_key=GEMINI_API_KEY_LOADED)
else:
    genai_client = None


class LLMCodeAnalyzer:
    """
    Uses a Large Language Model to perform a pre-analysis on a batch of code
    to generate a summary of functions, methods, and their call relationships.
    This is intended for non-Python code where a traditional AST parser is not used.
    """
# use model variable from constants.py, available models are in the constants.py file
    def __init__(self, model_name: str = AVAILABLE_MODELS["2.0-flash-lite"]):
        if not genai_client:
            raise ValueError("GEMINI_API_KEY not found. The LLM Analyzer cannot be initialized.")
        # We use a smaller, faster model for this pre-analysis task.
        self.model_name = model_name

    def analyze_batch(self, code_batch: str) -> Optional[str]:
        """
        Sends the code batch to the LLM to get a context summary.

        Args:
            code_batch: A single string containing all file contents to be analyzed.

        Returns:
            A string containing the AI-generated context, or None if an error occurs.
        """
        prompt = LLM_ANALYZER_PROMPT_TEMPLATE.format(code_batch_to_analyze=code_batch)

        try:
            with console.status("[bold blue]🤖 Performing LLM pre-analysis to build code context...[/bold blue]", spinner="earth"):
                # MODIFIED: Changed the API call to use the genai_client instance, which is compatible.
                response = genai_client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    # We want a deterministic, factual response, so temperature is low.
                    config=genai.types.GenerateContentConfig(
                        temperature=0.05,
                        max_output_tokens=4096,
                    )
                )

            if response.text:
                # We wrap the response in a clear header for the main prompt.
                return (
                    "# --- LLM-Generated Project Context ---\n"
                    f"{response.text}\n"
                    "# --- End of LLM-Generated Project Context ---\n"
                )
            else:
                console.print("[yellow]Warning: LLM-based context analyzer returned an empty response.[/yellow]")
                return None

        except Exception as e:
            console.print(f"[bold red]Error during LLM-based context analysis: {e}[/bold red]")
            return None