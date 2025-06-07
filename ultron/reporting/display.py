# src/ultron/display.py
from rich.console import Console
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.text import Text
from enum import Enum

# MODIFIED: Removed Panel and Padding imports as they are no longer used.
from ..models.data_models import (
    BatchReviewData, FileReviewData, HighConfidenceVulnerability, LowPrioritySuggestion,
    ReviewIssueTypeEnum,
)

# MODIFIED: This helper is no longer needed as we print Markdown objects directly.
# def _render_markdown_to_text(markdown_str: str, console: Console) -> Text:
#    ...

def _display_single_file_review_details(file_review: FileReviewData, console: Console):
    """
    MODIFIED: Helper to display details for a single file in a simple, linear format.
    Replaced Panels with simpler headers and direct printing for better readability on all screen sizes.
    """
    if file_review.error:
        console.print(f"⚠️ [bold orange]Error during analysis of {file_review.file_path}:[/bold orange] {file_review.error}")
        return

    # --- File Header ---
    console.print(f"\n[bold blue]📄 File: {file_review.file_path}[/bold blue] [dim](Lang: {file_review.language_detected or 'N/A'})[/dim]")
    console.print(f"   [bold]Summary:[/bold] {file_review.summary if file_review.summary else 'No specific summary for this file.'}")

    # --- High-Confidence Vulnerabilities ---
    if file_review.high_confidence_vulnerabilities:
        console.print("\n[bold red]🔴 High-Confidence Vulnerabilities Found[/bold red]")
        for i, vuln in enumerate(file_review.high_confidence_vulnerabilities):
            vuln_type_str = vuln.type.value if isinstance(vuln.type, Enum) else str(vuln.type)
            console.print(f"\n[yellow]----- Issue #{i+1}: {vuln_type_str} -----[/yellow]")

            meta_parts = []
            if vuln.severity_assessment:
                sa_str = vuln.severity_assessment.value if isinstance(vuln.severity_assessment, Enum) else str(vuln.severity_assessment)
                meta_parts.append(f"[bold]Severity:[/bold] {sa_str}")
            if vuln.confidence_score:
                cs_str = vuln.confidence_score.value if isinstance(vuln.confidence_score, Enum) else str(vuln.confidence_score)
                meta_parts.append(f"[bold]Confidence:[/bold] {cs_str}")
            if hasattr(vuln, 'analysis_source') and vuln.analysis_source and "agent" in vuln.analysis_source:
                meta_parts.append(f"[bold]Source:[/bold] [magenta]Deep Dive Agent[/magenta]")

            console.print(f"   {' | '.join(meta_parts)}")
            console.print(f"   [bold]Line:[/bold] {vuln.line}")

            console.print("\n   [bold]📝 Description:[/bold]")
            console.print(Markdown(vuln.description, style="bright_black"),)

            console.print("\n   [bold]💥 Impact:[/bold]")
            console.print(Markdown(vuln.impact, style="bright_black"))

            if vuln.proof_of_concept_code_or_command:
                console.print("\n   [bold]🔬 Proof of Concept:[/bold]")
                console.print(Syntax(
                    vuln.proof_of_concept_code_or_command, "bash", theme="monokai", line_numbers=True, word_wrap=True
                ))

            if vuln.proof_of_concept_explanation:
                console.print("\n   [bold]📋 POC Explanation:[/bold]")
                console.print(Markdown(vuln.proof_of_concept_explanation, style="bright_black"))

            if vuln.poc_actionability_tags:
                console.print(f"\n   [bold]🏷️ POC Tags:[/bold] [dim italic]{', '.join(vuln.poc_actionability_tags)}[/dim italic]")

            if hasattr(vuln, 'investigation_log') and vuln.investigation_log:
                console.print("\n   [bold magenta]🧠 Agent's Thought Process:[/bold magenta]")
                log_markdown = ""
                for step_log in vuln.investigation_log:
                    step_log = step_log.replace("**Thought:**", "[bold]🤔 Thought:[/bold]")
                    step_log = step_log.replace("**Action:**", "[bold]🛠️ Action:[/bold]")
                    step_log = step_log.replace("**Observation:**", "[bold]🔬 Observation:[/bold]")
                    log_markdown += f"- {step_log}\n"
                console.print(Markdown(log_markdown))


            if vuln.suggestion:
                console.print("\n   [bold]🛠️ Rectification Directive:[/bold]")
                console.print(Syntax(
                    vuln.suggestion, "diff", theme="monokai", line_numbers=True, word_wrap=True
                ))
    elif not file_review.error:
        console.print("[green]\n✅ No high-confidence issues found for this file.[/green]")

    # --- Low-Priority Suggestions ---
    if file_review.low_priority_suggestions:
        console.print("\n[bold yellow]💡 Low-Priority Suggestions[/bold yellow]")
        for i, sug in enumerate(file_review.low_priority_suggestions):
            sug_type_str = sug.type.value if isinstance(sug.type, Enum) else str(sug.type)
            console.print(f"\n[cyan]--- Suggestion #{i+1}: {sug_type_str} ---[/cyan]")
            console.print(f"   [bold]Line:[/bold] {sug.line}")
            console.print("\n   [bold]📝 Description:[/bold]")
            console.print(Markdown(sug.description, style="bright_black"))

            if sug.suggestion:
                console.print("\n   [bold]🛠️ Suggestion:[/bold]")
                console.print(Syntax(
                    sug.suggestion, "diff", theme="monokai", line_numbers=True, word_wrap=True
                ))
    elif not file_review.high_confidence_vulnerabilities and not file_review.error:
         console.print("[green]👍 No low-priority suggestions noted for this file.[/green]")


def display_pretty_batch_review(batch_review_data: BatchReviewData, console: Console):
    """
    MODIFIED: Displays the batch review data in a simple, linear format without panels.
    """
    if batch_review_data.error:
        console.print(f"🔴 [bold red]CRITICAL SYSTEM FAILURE: ULTRON COGNITIVE MATRIX OVERLOAD[/bold red]\n   {batch_review_data.error}")
        return

    # --- Overall Summary ---
    if batch_review_data.overall_batch_summary:
        console.print("\n[bold red]🎯 TARGET ANALYSIS COMPLETE[/bold red]")
        console.print(Markdown(f"### ULTRON ASSESSMENT\n\n{batch_review_data.overall_batch_summary}"))

    if batch_review_data.llm_processing_notes:
        console.print(f"ℹ️ [yellow]LLM Processing Notes:[/yellow] {batch_review_data.llm_processing_notes}")

    if batch_review_data.total_input_tokens is not None:
        console.print(f"   [dim]Total Input Tokens for Batch Request: [cyan]{batch_review_data.total_input_tokens}[/cyan][/dim]")

    if not batch_review_data.file_reviews:
        console.print("[yellow]No individual file reviews were returned in this batch.[/yellow]")
    else:
        for i, file_review in enumerate(batch_review_data.file_reviews):
            if i > 0:
                console.rule(style="dim blue")  # Use a rule as a clean separator between files
            _display_single_file_review_details(file_review, console)

    # --- Footer ---
    footer = Text("\n⚡ ULTRON INTELLIGENCE NETWORK • GEMINI CORE ACTIVE • NO STRINGS ATTACHED ⚡", style="dim italic", justify="center")
    console.print(footer)