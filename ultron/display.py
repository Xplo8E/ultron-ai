# src/ultron/display.py
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text
from rich.padding import Padding
from rich.syntax import Syntax
from enum import Enum # Ensure Enum is imported if used in models for type checking

# Assuming models.py is in the same package (ultron)
from .models import ReviewData, ReviewIssueTypeEnum, HighConfidenceVulnerabilityIssue, ConfidenceScoreEnum, SeverityAssessmentEnum

def display_pretty_review(review_data: ReviewData, console: Console):
    """
    Displays the review data in a human-readable format using Rich.
    """
    if review_data.error:
        error_panel_content = Text(review_data.error, style="bold red")
        if review_data.summary and review_data.summary not in ("Review failed due to API error.", "API Key Error", "Critical review failure."):
             # Append summary attempt if it exists and isn't just a generic failure message
             error_panel_content.append(f"\n\nSummary attempt:\n{review_data.summary}", style="yellow")
        console.print(Panel(error_panel_content, title="[bold red]⚠️ Review Error[/bold red]", border_style="red", expand=False))
        return

    console.print(Panel(Markdown(f"## Review Summary\n\n{review_data.summary if review_data.summary else 'No summary provided.'}"), title="📊 Review Summary", border_style="green", expand=True))

    token_info_parts = []
    if review_data.input_code_tokens is not None:
        token_info_parts.append(f"Input Code Tokens: [bold cyan]{review_data.input_code_tokens}[/bold cyan]")
    if review_data.additional_context_tokens is not None:
        # This now represents all non-code prompt tokens
        token_info_parts.append(f"Prompt/Context Tokens: [bold cyan]{review_data.additional_context_tokens}[/bold cyan]")

    if token_info_parts:
        console.print(Padding(" | ".join(token_info_parts), (0, 1), expand=False))

    # --- High-Confidence Vulnerabilities ---
    if review_data.high_confidence_vulnerabilities:
        console.print(Padding("\n[bold red]🚨 High-Confidence Vulnerabilities & Exploitable Bugs[/bold red]", (1,0,0,0)))
        for i, vuln in enumerate(review_data.high_confidence_vulnerabilities):
            vuln_type_str = vuln.type.value if isinstance(vuln.type, Enum) else str(vuln.type)
            title_text = f"Issue #{i+1}: {vuln_type_str}"
            
            title_color = "red" # Default for SECURITY
            if vuln.type == ReviewIssueTypeEnum.BUG:
                title_color = "magenta"
            elif isinstance(vuln.type, str) and "bug" in vuln_type_str.lower(): # Fallback if string is "Bug"
                title_color = "magenta"


            content = Text()
            content.append(f"Type: {vuln_type_str}\n", style="bold")
            
            # Display Confidence and Severity
            meta_info_parts = []
            if vuln.confidence_score:
                confidence_str = vuln.confidence_score.value if isinstance(vuln.confidence_score, Enum) else str(vuln.confidence_score)
                meta_info_parts.append(f"Confidence: [bold]{confidence_str}[/bold]")
            if vuln.severity_assessment:
                severity_str = vuln.severity_assessment.value if isinstance(vuln.severity_assessment, Enum) else str(vuln.severity_assessment)
                meta_info_parts.append(f"Severity: [bold]{severity_str}[/bold]")
            
            if meta_info_parts:
                content.append(" | ".join(meta_info_parts) + "\n", style="dim")

            content.append(f"Line: {vuln.line}\n\n", style="bold")
            
            content.append("Description:\n", style="bold yellow")
            # Create a new console for capturing markdown output
            md_console = Console(record=True, force_terminal=False)
            md_console.print(Markdown(vuln.description, inline_code_theme="monokai"))
            content.append(md_console.export_text() + "\n")
            
            content.append("Impact:\n", style="bold yellow")
            md_console = Console(record=True, force_terminal=False)
            md_console.print(Markdown(vuln.impact, inline_code_theme="monokai"))
            content.append(md_console.export_text() + "\n")

            if vuln.proof_of_concept_code_or_command:
                content.append("\nProof of Concept (Code/Command):\n", style="bold yellow")
                # Use console to capture syntax highlighted output
                syntax_console = Console(record=True, force_terminal=False)
                syntax_console.print(Syntax(
                    vuln.proof_of_concept_code_or_command,
                    "bash",
                    theme="monokai",
                    line_numbers=False,
                    word_wrap=True,
                    background_color="default",
                    indent_guides=True
                ))
                content.append(syntax_console.export_text())
            
            if vuln.proof_of_concept_explanation:
                content.append("\nPOC Explanation:\n", style="bold yellow")
                md_console = Console(record=True, force_terminal=False)
                md_console.print(Markdown(vuln.proof_of_concept_explanation, inline_code_theme="monokai"))
                content.append(md_console.export_text() + "\n")

            if vuln.poc_actionability_tags:
                tags_str = ", ".join(vuln.poc_actionability_tags)
                content.append(f"\nPOC Tags: [{tags_str}]\n", style="italic dim")

            if vuln.suggestion:
                content.append("\nSuggested Fix:\n", style="bold yellow")
                # Use console to capture syntax highlighted output for suggestion
                syntax_console = Console(record=True, force_terminal=False)
                syntax_console.print(Syntax(
                    vuln.suggestion,
                    "diff",
                    theme="monokai",
                    line_numbers=False,
                    word_wrap=True,
                    background_color="default",
                    indent_guides=True
                ))
                content.append(syntax_console.export_text())
            
            console.print(Panel(content, title=f"[{title_color}]{title_text}[/{title_color}]", border_style=title_color, expand=True, padding=(1,2)))
    else:
        console.print(Panel("✅ No high-confidence exploitable vulnerabilities or critical bugs identified based on the provided code and context.", style="green", expand=False, title="[green]Security Check[/green]"))

    # --- Low-Priority Suggestions ---
    if review_data.low_priority_suggestions:
        console.print(Padding("\n[bold yellow]💡 Low-Priority Suggestions & Best Practices[/bold yellow]", (1,0,0,0)))
        for i, sug in enumerate(review_data.low_priority_suggestions):
            sug_type_str = sug.type.value if isinstance(sug.type, Enum) else str(sug.type)
            title_text = f"Suggestion #{i+1}: {sug_type_str}"
            
            border_color = "yellow" # Default for SUGGESTION or UNKNOWN string types
            if sug.type == ReviewIssueTypeEnum.BEST_PRACTICE: border_color = "blue"
            elif sug.type == ReviewIssueTypeEnum.PERFORMANCE: border_color = "magenta"
            elif sug.type == ReviewIssueTypeEnum.STYLE: border_color = "cyan"
            # Add more elif for string fallbacks if needed

            content = Text()
            content.append(f"Type: {sug_type_str}\n", style="bold")
            content.append(f"Line: {sug.line}\n\n", style="bold")
            content.append("Description:\n", style="bold")
            content.append(Markdown(sug.description, inline_code_theme="monokai")) # Render as Markdown
            content.append("\n")

            if sug.suggestion:
                content.append("\nSuggestion:\n", style="bold")
                content.append(Syntax(sug.suggestion, "diff", theme="monokai", line_numbers=False, word_wrap=True, background_color="default", indent_guides=True))
            
            console.print(Panel(content, title=f"[{border_color}]{title_text}[/{border_color}]", border_style=border_color, expand=True, padding=(1,2)))
    elif not review_data.high_confidence_vulnerabilities : # Only show if no major issues either
        console.print(Panel("👍 No low-priority suggestions noted.", style="green", expand=False, title="[green]Suggestions[/green]"))
    elif review_data.high_confidence_vulnerabilities and not review_data.low_priority_suggestions:
         console.print("\nNo further low-priority suggestions noted.", style="italic dim")

    # Create a centered footer text
    footer = Text("\nPowered by Google Gemini 🚀", style="dim italic")
    footer.justify = "center"
    # Add padding to the centered text
    console.print(Padding(footer, (1, 0)))