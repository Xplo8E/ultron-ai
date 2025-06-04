# src/ultron/main_cli.py
import click
import sys
import os
import json
from rich.console import Console
from pathlib import Path
from typing import List, Optional, Tuple

try:
    from .reviewer import get_gemini_review, GEMINI_API_KEY_LOADED
    from .models import ReviewData
    from .display import display_pretty_review
    from .constants import SUPPORTED_LANGUAGES, AVAILABLE_MODELS, DEFAULT_MODEL_KEY
    from .caching import get_cache_key, load_from_cache, save_to_cache
    from .ignorer import ReviewIgnorer
    from .sarif_converter import convert_review_to_sarif
    from . import __version__ as cli_version
except ImportError:
    # Fallback for direct script execution (less ideal)
    print("Warning: Running main_cli.py directly. Ensure PYTHONPATH or package installation.", file=sys.stderr)
    from reviewer import get_gemini_review, GEMINI_API_KEY_LOADED
    from models import ReviewData
    from display import display_pretty_review
    from constants import SUPPORTED_LANGUAGES, AVAILABLE_MODELS, DEFAULT_MODEL_KEY
    from caching import get_cache_key, load_from_cache, save_to_cache
    from ignorer import ReviewIgnorer
    from sarif_converter import convert_review_to_sarif
    cli_version = "dev"


LANGUAGE_EXTENSIONS = {
    "python": [".py", ".pyw", ".pyi"],
    "javascript": [".js", ".jsx", ".mjs"],
    "typescript": [".ts", ".tsx"],
    "java": [".java"],
    "c++": [".cpp", ".hpp", ".cc", ".h", ".cxx"],
    "csharp": [".cs"],
    "go": [".go"],
    "rust": [".rs"],
    "php": [".php", ".phtml", ".php3", ".php4", ".php5", ".phps"],
    "ruby": [".rb", ".rbw"],
    "swift": [".swift"],
    "kotlin": [".kt", ".kts"],
    "html": [".html", ".htm"],
    "css": [".css"],
    "sql": [".sql"]
}
LANGUAGE_DISPLAY_NAMES = SUPPORTED_LANGUAGES


@click.group(context_settings=dict(help_option_names=['-h', '--help']))
@click.version_option(version=cli_version, prog_name="Ultron Code Reviewer")
def cli():
    """
    🤖 Ultron Code Reviewer 🤖

    AI-powered code analysis using Google Gemini.
    Identifies security vulnerabilities, bugs, and suggests improvements.
    Ensure your GEMINI_API_KEY is set in a .env file or as an environment variable.
    """
    if not GEMINI_API_KEY_LOADED:
        console = Console(stderr=True)
        console.print("🚨 [bold red]Error: GEMINI_API_KEY not found or not loaded.[/bold red]")
        console.print("Please create a [cyan].env[/cyan] file in your project root with:")
        console.print("   [green]GEMINI_API_KEY=\"YOUR_API_KEY_HERE\"[/green]")
        console.print("Alternatively, set it as an environment variable.")
        sys.exit(1)

@cli.command("review")
@click.option('--path', '-p', type=click.Path(exists=True, resolve_path=True), help="Path to code file or folder.")
@click.option('--code', '-c', type=str, help="Direct code string to review.")
@click.option('--language', '-l', type=click.Choice(list(SUPPORTED_LANGUAGES.keys()), case_sensitive=False), required=True, help="Programming language.")
@click.option('--model-key', '-m', type=click.Choice(list(AVAILABLE_MODELS.keys())), default=DEFAULT_MODEL_KEY, show_default=True, help="Gemini model to use.")
@click.option('--context', '-ctx', default="", help="Additional context for the reviewer.")
@click.option('--frameworks', '--fw', default="", help="Comma-separated list of frameworks/libraries used (e.g., 'Django,React').")
@click.option('--sec-reqs', '--sr', default="", help="Path to a file or text containing security requirements/policies.")
@click.option('--output-format', '-o', type=click.Choice(['pretty', 'json', 'sarif'], case_sensitive=False), default='pretty', show_default=True, help="Output format.")
@click.option('--recursive', '-r', is_flag=True, default=False, help="Recursively review files in subdirectories.")
@click.option('--exclude', '-e', multiple=True, help="Glob patterns for files/folders to exclude.")
@click.option('--ignore-file-rule', '--ifr', multiple=True, help="Glob pattern for entire files to ignore (e.g., 'tests/*').")
@click.option('--ignore-line-rule', '--ilr', multiple=True, help="Rule to ignore specific lines (e.g., 'path/to/file.py:10', 'path/to/file.py:CWE-79').")
@click.option('--no-cache', is_flag=True, default=False, help="Disable caching for this run.")
@click.option('--clear-cache', is_flag=True, default=False, help="Clear the Ultron cache before running.")

def review_code_command(path, code, language, model_key, context, frameworks, sec_reqs,
                        output_format, recursive, exclude,
                        ignore_file_rule, ignore_line_rule, no_cache, clear_cache):
    """Analyzes code for issues."""
    console = Console()

    if clear_cache:
        from .caching import CACHE_DIR
        try:
            for item in CACHE_DIR.iterdir():
                item.unlink()
            console.print(f"[green]Cache cleared from {CACHE_DIR}[/green]")
        except Exception as e:
            console.print(f"[red]Error clearing cache: {e}[/red]")
        if not path and not code: # If only clear-cache was passed, exit.
            return
        
    if not path and not code:
        console.print("[bold red]Error: Either --path/-p or --code/-c must be provided.[/bold red]")
        sys.exit(1)
    if path and code:
        console.print("[bold red]Error: Cannot use both --path/-p and --code/-c simultaneously.[/bold red]")
        sys.exit(1)

    actual_model_name = AVAILABLE_MODELS.get(model_key, AVAILABLE_MODELS[DEFAULT_MODEL_KEY])
    ignorer = ReviewIgnorer(ignore_file_rules=list(ignore_file_rule), ignore_line_rules=list(ignore_line_rule))
    
    # Process security requirements if path is given
    security_requirements_content = sec_reqs
    if sec_reqs and Path(sec_reqs).is_file():
        try:
            with open(sec_reqs, 'r', encoding='utf-8') as f_sr:
                security_requirements_content = f_sr.read()
        except Exception as e_sr:
            console.print(f"[yellow]Warning: Could not read security requirements file {sec_reqs}: {e_sr}[/yellow]")
            security_requirements_content = sec_reqs # Use as literal string if file read fails


    files_to_process_info = []

    if code:
        files_to_process_info.append({"path_obj": None, "content": code, "lang_to_use": language})
    elif path:
        input_path_obj = Path(path)
        if input_path_obj.is_file():
            files_to_process_info.append({"path_obj": input_path_obj, "content": None, "lang_to_use": language})
        elif input_path_obj.is_dir():
            # Simplified folder scanning for example, refer to previous detailed one
            console.print(f"Scanning folder: [cyan]{input_path_obj}[/cyan]...")
            target_extensions = LANGUAGE_EXTENSIONS.get(language, []) if language != "auto" else \
                                [ext for ext_list in LANGUAGE_EXTENSIONS.values() for ext in ext_list]
            
            path_iterator = input_path_obj.rglob("*") if recursive else input_path_obj.glob("*")
            for item in path_iterator:
                is_excluded_by_general_rule = any(item.match(ex_pattern) for ex_pattern in exclude)
                if is_excluded_by_general_rule:
                    continue
                if item.is_file() and (language == "auto" or item.suffix.lower() in target_extensions):
                     # Basic language auto-detection for 'auto'
                    current_lang = language
                    if language == "auto":
                        detected = False
                        for lang_code, exts in LANGUAGE_EXTENSIONS.items():
                            if item.suffix.lower() in exts:
                                current_lang = lang_code
                                detected = True
                                break
                        if not detected: continue # Skip if lang can't be auto-detected
                    
                    files_to_process_info.append({"path_obj": item, "content": None, "lang_to_use": current_lang})
        else:
            console.print(f"[bold red]Error: Path {path} is not a valid file or directory.[/bold red]")
            sys.exit(1)
    
    if not files_to_process_info:
        console.print("[yellow]No files found to review with the given criteria.[/yellow]")
        sys.exit(0)


    all_reviews_data: List[Tuple[Optional[Path], ReviewData]] = [] # For SARIF aggregation
    overall_had_errors = False

    for i, file_info in enumerate(files_to_process_info):
        file_path_obj = file_info["path_obj"]
        code_content_to_review = file_info["content"]
        lang_to_use = file_info["lang_to_use"]
        
        display_name = file_path_obj.name if file_path_obj else "direct code"
        lang_display = LANGUAGE_DISPLAY_NAMES.get(lang_to_use, lang_to_use)
        console.rule(f"[bold blue]File {i+1}/{len(files_to_process_info)}: [cyan]{display_name}[/cyan] ([magenta]{lang_display}[/magenta])[/bold blue]")

        if code_content_to_review is None and file_path_obj:
            try:
                with open(file_path_obj, 'r', encoding='utf-8') as f_content:
                    code_content_to_review = f_content.read()
            except Exception as e_read:
                console.print(f"   [bold red]Error reading file {file_path_obj}: {e_read}[/bold red]")
                all_reviews_data.append(
                    (file_path_obj, ReviewData(summary=f"Error reading file: {e_read}", error=str(e_read)))
                )
                overall_had_errors = True
                continue
        
        if not code_content_to_review or not code_content_to_review.strip():
            console.print("   [yellow]Skipping empty file or code input.[/yellow]")
            all_reviews_data.append(
                (file_path_obj, ReviewData(summary="Empty content skipped.", error="Empty content."))
            )
            continue

        review_result: Optional[ReviewData] = None
        cache_key_str = ""
        if not no_cache:
            cache_key_str = get_cache_key(
                code=code_content_to_review, language=lang_to_use, model_name=actual_model_name,
                additional_context=context, frameworks_libraries=frameworks,
                security_requirements=security_requirements_content
            )
            review_result = load_from_cache(cache_key_str)
            if review_result:
                console.print("   [dim green]Cache hit![/dim green]")

        if not review_result:
            if not no_cache: console.print("   [dim]Cache miss, calling API...[/dim]")
            with console.status(f"[bold green]Consulting Gemini for {display_name}...[/bold green]", spinner="dots12"):
                review_result = get_gemini_review(
                    code=code_content_to_review, language=lang_to_use, model_key=model_key,
                    additional_context=context, frameworks_libraries=frameworks,
                    security_requirements=security_requirements_content
                )
            if review_result and not review_result.error and not no_cache and cache_key_str:
                save_to_cache(cache_key_str, review_result)
        
        if review_result:
            # Apply ignore rules AFTER getting the review (whether from cache or API)
            review_result = ignorer.filter_review_data(review_result, file_path_obj)
            all_reviews_data.append((file_path_obj, review_result)) # Store for potential SARIF
            if output_format == 'pretty':
                display_pretty_review(review_result, console)
            elif output_format == 'json': # For JSON, print per file for now
                console.print(f"\n--- JSON Output for: {display_name} ---")
                console.print(review_result.model_dump_json(indent=2, by_alias=True))
            # SARIF is handled after all files
            if review_result.error:
                overall_had_errors = True
        else:
            console.print(f"   [bold red]❌ Review failed for {display_name}. No results.[/bold red]")
            all_reviews_data.append(
                (file_path_obj, ReviewData(summary="Critical review failure.", error="No data from review function."))
            )
            overall_had_errors = True
        
        if i < len(files_to_process_info) - 1: console.rule(style="dim blue")


    if output_format == 'sarif':
        console.print("\nGenerating SARIF report...")
        aggregated_results = []
        unique_rules_map = {}
        
        for file_p, review_d in all_reviews_data:
            if review_d.error: # Skip errored reviews for SARIF results, or represent them differently
                continue
            # This is a simplified conversion, actual SARIF generation should be more robust
            sarif_log_for_file = convert_review_to_sarif(review_d, file_p)
            if sarif_log_for_file.runs and sarif_log_for_file.runs[0].results:
                aggregated_results.extend(sarif_log_for_file.runs[0].results)
            if sarif_log_for_file.runs and sarif_log_for_file.runs[0].tool.driver.rules:
                for rule in sarif_log_for_file.runs[0].tool.driver.rules:
                    if rule.id not in unique_rules_map:
                        unique_rules_map[rule.id] = rule
        
        # Create a single SARIF log with all results
        if aggregated_results:
            final_sarif_tool_component = convert_review_to_sarif(ReviewData(summary=""), None).runs[0].tool.driver # Get a template
            final_sarif_tool_component.rules = list(unique_rules_map.values()) if unique_rules_map else None
            
            final_sarif_run = convert_review_to_sarif(ReviewData(summary=""), None).runs[0] # Get a template
            final_sarif_run.tool.driver = final_sarif_tool_component
            final_sarif_run.results = aggregated_results

            final_sarif_log = convert_review_to_sarif(ReviewData(summary=""), None) # Get a template
            final_sarif_log.runs = [final_sarif_run]
            
            console.print(final_sarif_log.model_dump_json(indent=2, by_alias=True, exclude_none=True))
        else:
            console.print("[yellow]No results to include in SARIF report.[/yellow]")

    console.rule("[bold blue]🚀 Ultron Review Session Complete[/bold blue]")
    if overall_had_errors:
        console.print("\n[bold yellow]Note: Some files encountered errors during review.[/bold yellow]")
        sys.exit(1)

if __name__ == '__main__':
    cli()