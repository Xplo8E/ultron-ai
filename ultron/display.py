# src/ultron/display.py
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text
from rich.padding import Padding
from rich.syntax import Syntax
from enum import Enum

from .models import (
    BatchReviewData, FileReviewData, HighConfidenceVulnerability, LowPrioritySuggestion,
    ReviewIssueTypeEnum, ConfidenceScoreEnum, SeverityAssessmentEnum
)

def _render_markdown_to_text(markdown_str: str, console: Console) -> Text:
    """Helper to render markdown to Text object."""
    temp_console = Console(record=True, force_terminal=False)
    temp_console.print(Markdown(markdown_str))
    return Text.from_ansi(temp_console.export_text())

def _display_single_file_review_details(file_review: FileReviewData, console: Console):
    """Helper to display details for a single file from a batch review."""
    if file_review.error:
        console.print(Panel(Text(file_review.error, style="bold orange"), title=f"⚠️ Error during analysis of {file_review.file_path}"))
        return

    console.print(Panel(Markdown(f"**Summary for `{file_review.file_path}`:**\n\n{file_review.summary if file_review.summary else 'No specific summary for this file.'}"),
                        title=f"📄 File: {file_review.file_path} (Lang: {file_review.language_detected or 'N/A'})",
                        border_style="blue", expand=True))

    # --- High-Confidence Vulnerabilities ---
    if file_review.high_confidence_vulnerabilities:
        console.print(Padding("[bold red]🚨 High-Confidence Vulnerabilities & Exploitable Bugs[/bold red]", (1,0,0,1)))
        for i, vuln in enumerate(file_review.high_confidence_vulnerabilities):
            vuln_type_str = vuln.type.value if isinstance(vuln.type, Enum) else str(vuln.type)
            title_text = f"Issue #{i+1}: {vuln_type_str}"
            title_color = "red" if vuln.type == ReviewIssueTypeEnum.SECURITY else "magenta"
            if isinstance(vuln.type, str) and "bug" in vuln_type_str.lower(): title_color = "magenta"

            content = Text()
            content.append(f"Type: {vuln_type_str}\n", style="bold")
            meta_info_parts = []
            if vuln.confidence_score:
                cs_str = vuln.confidence_score.value if isinstance(vuln.confidence_score, Enum) else str(vuln.confidence_score)
                meta_info_parts.append(f"Confidence: [bold]{cs_str}[/bold]")
            if vuln.severity_assessment:
                sa_str = vuln.severity_assessment.value if isinstance(vuln.severity_assessment, Enum) else str(vuln.severity_assessment)
                meta_info_parts.append(f"Severity: [bold]{sa_str}[/bold]")
            if meta_info_parts: 
                content.append(" | ".join(meta_info_parts) + "\n", style="dim")
            content.append(f"Line: {vuln.line}\n\n", style="bold")
            
            content.append("📝 Description:\n", style="bold yellow")
            content.append("─" * 50 + "\n", style="dim")
            content.append(_render_markdown_to_text(vuln.description, console))
            content.append("\n\n")
            
            content.append("💥 Impact:\n", style="bold yellow")
            content.append("─" * 50 + "\n", style="dim")
            content.append(_render_markdown_to_text(vuln.impact, console))
            content.append("\n\n")

            if vuln.proof_of_concept_code_or_command:
                content.append("🔬 Proof of Concept (Code/Command):\n", style="bold yellow")
                content.append("─" * 50 + "\n", style="dim")
                temp_console = Console(record=True, force_terminal=False)
                temp_console.print(Syntax(
                    vuln.proof_of_concept_code_or_command,
                    "bash",
                    theme="monokai",
                    line_numbers=False,
                    word_wrap=True,
                    background_color="default",
                    indent_guides=True
                ))
                content.append(Text.from_ansi(temp_console.export_text()))
                content.append("\n")
            
            if vuln.proof_of_concept_explanation:
                content.append("📋 POC Explanation:\n", style="bold yellow")
                content.append("─" * 50 + "\n", style="dim")
                content.append(_render_markdown_to_text(vuln.proof_of_concept_explanation, console))
                content.append("\n\n")
            
            if vuln.poc_actionability_tags:
                content.append("🏷️ POC Tags:\n", style="bold yellow")
                content.append("─" * 50 + "\n", style="dim")
                content.append(f"[{', '.join(vuln.poc_actionability_tags)}]\n\n", style="italic dim")
            
            if vuln.suggestion:
                content.append("🛠️ Suggested Fix:\n", style="bold yellow")
                content.append("─" * 50 + "\n", style="dim")
                temp_console = Console(record=True, force_terminal=False)
                temp_console.print(Syntax(
                    vuln.suggestion,
                    "diff",
                    theme="monokai",
                    line_numbers=False,
                    word_wrap=True,
                    background_color="default",
                    indent_guides=True
                ))
                content.append(Text.from_ansi(temp_console.export_text()))
                content.append("\n")
            
            console.print(Panel(content, title=f"[{title_color}]{title_text}[/{title_color}]", border_style=title_color, expand=True, padding=(1,2)))
    elif not file_review.error:
        console.print(Panel("✅ No high-confidence issues found for this file.", style="green", expand=False, title="[green]Security Check[/green]"))

    # --- Low-Priority Suggestions ---
    if file_review.low_priority_suggestions:
        console.print(Padding("[bold yellow]💡 Low-Priority Suggestions & Best Practices[/bold yellow]", (1,0,0,1)))
        for i, sug in enumerate(file_review.low_priority_suggestions):
            sug_type_str = sug.type.value if isinstance(sug.type, Enum) else str(sug.type)
            title_text = f"Suggestion #{i+1}: {sug_type_str}"
            border_color = "yellow"
            if sug.type == ReviewIssueTypeEnum.BEST_PRACTICE: border_color = "blue"
            elif sug.type == ReviewIssueTypeEnum.PERFORMANCE: border_color = "magenta"
            elif sug.type == ReviewIssueTypeEnum.STYLE: border_color = "cyan"
            
            content = Text()
            content.append(f"Type: {sug_type_str}\n", style="bold")
            content.append(f"Line: {sug.line}\n\n", style="bold")
            
            content.append("📝 Description:\n", style="bold")
            content.append("─" * 50 + "\n", style="dim")
            content.append(_render_markdown_to_text(sug.description, console))
            content.append("\n\n")
            
            if sug.suggestion:
                content.append("🛠️ Suggestion:\n", style="bold")
                content.append("─" * 50 + "\n", style="dim")
                temp_console = Console(record=True, force_terminal=False)
                temp_console.print(Syntax(
                    sug.suggestion,
                    "diff",
                    theme="monokai",
                    line_numbers=False,
                    word_wrap=True,
                    background_color="default",
                    indent_guides=True
                ))
                content.append(Text.from_ansi(temp_console.export_text()))
                content.append("\n")
            
            console.print(Panel(content, title=f"[{border_color}]{title_text}[/{border_color}]", border_style=border_color, expand=True, padding=(1,2)))
    elif not file_review.high_confidence_vulnerabilities and not file_review.error:
         console.print(Panel("👍 No low-priority suggestions noted for this file.", style="green", expand=False, title="[green]Suggestions[/green]"))

def display_pretty_batch_review(batch_review_data: BatchReviewData, console: Console):
    """
    Displays the batch review data, iterating through each file's review.
    """
    if batch_review_data.error:
        console.print(Panel(Text(batch_review_data.error, style="bold red"), title="[bold red]⚠️ Batch Review Error[/bold red]", border_style="red", expand=False))
        return

    if batch_review_data.overall_batch_summary:
        console.print(Panel(Markdown(f"## Overall Batch Summary\n\n{batch_review_data.overall_batch_summary}"), title="📦 Batch Overview", border_style="green", expand=True))
    
    if batch_review_data.llm_processing_notes:
        console.print(Panel(Markdown(f"**LLM Processing Notes:**\n{batch_review_data.llm_processing_notes}"), title="ℹ️ LLM Notes", border_style="yellow", expand=False))

    if batch_review_data.total_input_tokens is not None:
        console.print(Padding(f"Total Input Tokens for Entire Batch Request: [bold cyan]{batch_review_data.total_input_tokens}[/bold cyan]", (0,1), expand=False))

    if not batch_review_data.file_reviews:
        console.print(Panel("[yellow]No individual file reviews were returned in this batch.[/yellow]", title="File Reviews", border_style="yellow"))
    else:
        for i, file_review in enumerate(batch_review_data.file_reviews):
            if i > 0: console.rule(style="dim blue") # Separator between files
            _display_single_file_review_details(file_review, console)
    
    # Create a centered footer text
    footer = Text("\nPowered by Google Gemini 🚀", style="dim italic")
    footer.justify = "center"
    # Add padding to the centered text
    console.print(Padding(footer, (1, 0)))