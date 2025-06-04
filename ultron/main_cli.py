# src/ultron/main_cli.py
import click
import sys
import os
import json
from rich.console import Console
from pathlib import Path
from typing import Optional, List, Dict, Tuple # For type hints

try:
    from .reviewer import get_gemini_review, GEMINI_API_KEY_LOADED
    from .models import BatchReviewData, FileReviewData # Using BatchReviewData now
    from .display import display_pretty_batch_review # Changed function name
    from .constants import (
        SUPPORTED_LANGUAGES, AVAILABLE_MODELS, DEFAULT_MODEL_KEY,
        LANGUAGE_EXTENSIONS_MAP # For file discovery
    )
    from .caching import get_cache_key, load_from_cache, save_to_cache
    from .ignorer import ReviewIgnorer
    from .sarif_converter import convert_batch_review_to_sarif # Changed function name
    from . import __version__ as cli_version
except ImportError:
    print("Warning: Running main_cli.py directly. Ensure PYTHONPATH or package installation.", file=sys.stderr)
    # Add fallbacks if necessary for direct script running, though it's not ideal
    sys.exit("Import errors. Please run as a module or install the package.")


LANGUAGE_DISPLAY_NAMES = SUPPORTED_LANGUAGES # Re-using for display

@click.group(context_settings=dict(help_option_names=['-h', '--help']))
@click.version_option(version=cli_version, prog_name="Ultron Code Reviewer")
def cli():
    """🤖 Ultron Code Reviewer 🤖\nAI-powered code analysis using Google Gemini."""
    if not GEMINI_API_KEY_LOADED:
        console = Console(stderr=True)
        console.print("🚨 [bold red]Error: GEMINI_API_KEY not found or not loaded.[/bold red]")
        console.print("Please create a [cyan].env[/cyan] file in your project root with:")
        console.print("   [green]GEMINI_API_KEY=\"YOUR_API_KEY_HERE\"[/green]")
        console.print("Alternatively, set it as an environment variable.")
        sys.exit(1)

def build_code_batch_string(files_to_process: List[Dict[str, Path]], project_root_for_relative_path: Path) -> Tuple[str, int]:
    """
    Constructs the single string for the batch API call from a list of file paths.
    Returns the batch string and the number of files included.
    """
    batch_content_parts = []
    files_included_count = 0
    for file_info in files_to_process:
        file_path_obj = file_info["path_obj"]
        try:
            with open(file_path_obj, 'r', encoding='utf-8') as f_content:
                content = f_content.read()
            if content.strip(): # Only include non-empty files
                relative_path = file_path_obj.relative_to(project_root_for_relative_path).as_posix()
                batch_content_parts.append(f"{relative_path}:\n========\n{content}\n")
                files_included_count += 1
            else:
                print(f"[dim yellow]Skipping empty file: {file_path_obj}[/dim yellow]")
        except Exception as e_read:
            print(f"[bold red]Error reading file {file_path_obj} for batch: {e_read}[/bold red]")
    return "\n".join(batch_content_parts), files_included_count


@cli.command("review")
@click.option('--path', '-p', type=click.Path(exists=True, resolve_path=True), help="Path to code file or folder.")
@click.option('--code', '-c', type=str, help="Direct code string to review (ignores --path).")
@click.option('--language', '-l', type=click.Choice(list(SUPPORTED_LANGUAGES.keys()), case_sensitive=False), required=True, 
              help="Primary language hint for the review. For folders with 'auto', Ultron attempts per-file detection based on extension for inclusion in batch.")
@click.option('--model-key', '-m', type=click.Choice(list(AVAILABLE_MODELS.keys())), default=DEFAULT_MODEL_KEY, show_default=True, help="Gemini model.")
@click.option('--context', '-ctx', default="", help="Additional context for the reviewer.")
@click.option('--frameworks', '--fw', default="", help="Comma-separated frameworks/libraries (e.g., 'Django,React').")
@click.option('--sec-reqs', '--sr', default="", help="Path to file or text of security requirements.")
@click.option('--output-format', '-o', type=click.Choice(['pretty', 'json', 'sarif'], case_sensitive=False), default='pretty', show_default=True, help="Output format.")
@click.option('--recursive', '-r', is_flag=True, default=False, help="Recursively find files in subdirectories if --path is a folder.")
@click.option('--exclude', '-e', multiple=True, help="Glob patterns for files/folders to exclude from folder scan.")
@click.option('--ignore-file-rule', '--ifr', multiple=True, help="Glob pattern for entire files to ignore findings from (e.g., 'tests/*').")
@click.option('--ignore-line-rule', '--ilr', multiple=True, help="Rule to ignore specific lines (e.g., 'path/file.py:10', 'path/file.py:VULN_TYPE').")
@click.option('--no-cache', is_flag=True, default=False, help="Disable caching for this run.")
@click.option('--clear-cache', is_flag=True, default=False, help="Clear the Ultron cache before running.")
def review_code_command(path, code, language, model_key, context, frameworks, sec_reqs,
                        output_format, recursive, exclude,
                        ignore_file_rule, ignore_line_rule, no_cache, clear_cache):
    """Analyzes code for issues using a batch approach for folders."""
    console = Console()

    if clear_cache:
        from .caching import CACHE_DIR # Local import for this specific action
        deleted_count = 0
        try:
            if CACHE_DIR.exists():
                for item in CACHE_DIR.iterdir():
                    if item.is_file(): # Ensure it's a file before unlinking
                        item.unlink()
                        deleted_count +=1
            console.print(f"[green]Cache cleared: {deleted_count} file(s) removed from {CACHE_DIR}[/green]")
        except Exception as e_cache_clear:
            console.print(f"[red]Error clearing cache: {e_cache_clear}[/red]")
        if not path and not code: return

    if not path and not code:
        console.print("[bold red]Error: Either --path/-p or --code/-c must be provided.[/bold red]"); sys.exit(1)
    if path and code:
        console.print("[bold red]Error: Cannot use both --path/-p and --code/-c simultaneously.[/bold red]"); sys.exit(1)

    actual_model_name = AVAILABLE_MODELS.get(model_key, AVAILABLE_MODELS[DEFAULT_MODEL_KEY])
    ignorer = ReviewIgnorer(ignore_file_rules=list(ignore_file_rule), ignore_line_rules=list(ignore_line_rule))
    
    security_requirements_content = sec_reqs
    if sec_reqs and Path(sec_reqs).is_file():
        try:
            with open(sec_reqs, 'r', encoding='utf-8') as f_sr: security_requirements_content = f_sr.read()
        except Exception as e_sr:
            console.print(f"[yellow]Warning: Could not read security requirements file {sec_reqs}: {e_sr}[/yellow]")

    code_batch_to_send = ""
    review_target_display = "direct code input"
    project_root_for_paths = Path.cwd() # Default, can be refined if path is absolute

    if code:
        # For direct code, we create a "pseudo" file entry for the batch string
        code_batch_to_send = f"direct_code_input.{language}:\n========\n{code}\n"
        review_target_display = f"direct code input ({language})"
        if not code.strip(): console.print("[bold red]Error: No code provided via --code.[/bold red]"); sys.exit(1)
    
    elif path:
        input_path_obj = Path(path)
        project_root_for_paths = input_path_obj.parent if input_path_obj.is_file() else input_path_obj
        review_target_display = str(input_path_obj.name)

        files_to_collect_info: List[Dict[str, Path]] = []
        if input_path_obj.is_file():
            files_to_collect_info.append({"path_obj": input_path_obj, "lang_to_use": language}) # lang_to_use for single file is just language
        elif input_path_obj.is_dir():
            console.print(f"Scanning folder: [cyan]{input_path_obj}[/cyan] for language hint: [magenta]{language}[/magenta]...")
            
            extensions_to_match = []
            if language != "auto":
                extensions_to_match = LANGUAGE_EXTENSIONS_MAP.get(language, [])
                if not extensions_to_match:
                    console.print(f"[yellow]Warning: No specific extensions defined for language '{language}'. Will include all files if language is not 'auto'.[/yellow]")
            # If 'auto', or no specific extensions, glob pattern will take care of it

            path_iterator = input_path_obj.rglob("*") if recursive else input_path_obj.glob("*")
            for item in path_iterator:
                is_excluded = any(item.match(ex_pattern) for ex_pattern in exclude)
                if is_excluded or not item.is_file():
                    continue
                
                # File filtering based on language
                item_lang = language # Assume specified language unless 'auto'
                if language == "auto":
                    detected_item_lang = None
                    for lang_code, exts in LANGUAGE_EXTENSIONS_MAP.items():
                        if item.suffix.lower() in exts:
                            detected_item_lang = lang_code
                            break
                    if detected_item_lang:
                        item_lang = detected_item_lang
                    else:
                        # If language is 'auto' and we can't detect, we might skip or include with a generic tag
                        # For batch mode, it's safer to include and let LLM try, or prompt LLM to identify language
                        console.print(f"[dim]Including file with auto-detected lang (or will let LLM try): {item.relative_to(input_path_obj)}[/dim]")
                        # No specific language for this file if auto and not detected, LLM has to figure it out
                elif item.suffix.lower() not in extensions_to_match: # if specific lang, filter by its extensions
                    continue
                
                files_to_collect_info.append({"path_obj": item, "lang_to_use": item_lang}) # lang_to_use might be refined per file by LLM
            
            if not files_to_collect_info:
                console.print(f"[yellow]No files found in {input_path_obj} matching criteria.[/yellow]"); sys.exit(0)
            
            code_batch_to_send, num_files_in_batch = build_code_batch_string(files_to_collect_info, project_root_for_paths)
            review_target_display += f" ({num_files_in_batch} file(s) in batch)"

        else:
            console.print(f"[bold red]Error: Path {path} is not a valid file or directory.[/bold red]"); sys.exit(1)
        
        if not code_batch_to_send.strip():
            console.print("[yellow]No non-empty code content found to review from the specified path.[/yellow]"); sys.exit(0)

    console.rule(f"[bold blue]🤖 Ultron Review: [cyan]{review_target_display}[/cyan][/bold blue]")

    batch_review_result: Optional[BatchReviewData] = None
    cache_key_str = ""

    if not no_cache:
        cache_key_str = get_cache_key(
            code_batch=code_batch_to_send, primary_language_hint=language, model_name=actual_model_name,
            additional_context=context, frameworks_libraries=frameworks, security_requirements=security_requirements_content
        )
        batch_review_result = load_from_cache(cache_key_str)
        if batch_review_result: console.print("   [dim green]Cache hit for batch![/dim green]")

    if not batch_review_result:
        if not no_cache: console.print("   [dim]Cache miss for batch, calling API...[/dim]")
        with console.status(f"[bold green]Consulting Gemini for the batch...[/bold green]", spinner="dots12"):
            batch_review_result = get_gemini_review(
                code_batch=code_batch_to_send, primary_language_hint=language, model_key=model_key,
                additional_context=context, frameworks_libraries=frameworks, security_requirements=security_requirements_content
            )
        if batch_review_result and not batch_review_result.error and not no_cache and cache_key_str:
            save_to_cache(cache_key_str, batch_review_result)
    
    if batch_review_result:
        # Apply ignore rules to the received batch data
        batch_review_result = ignorer.filter_batch_review_data(batch_review_result)
        
        if output_format == 'pretty':
            display_pretty_batch_review(batch_review_result, console)
        elif output_format == 'json':
            console.print(batch_review_result.model_dump_json(indent=2, by_alias=True, exclude_none=True))
        elif output_format == 'sarif':
            console.print("\nGenerating SARIF report for the batch...")
            # project_root_for_sarif needs to be defined correctly, likely the input path if it's a dir
            sarif_report_root_path = Path(path) if path and Path(path).is_dir() else Path.cwd()
            # The convert_batch_review_to_sarif will use file_path from FileReviewData which should be relative to project_root_for_paths
            # We might need to adjust SARIF URIs to be relative to a common root or provide absolute paths
            # For simplicity, we assume file_paths in FileReviewData are correctly relative for SARIF
            sarif_log = convert_batch_review_to_sarif(batch_review_result)
            console.print(sarif_log.model_dump_json(indent=2, by_alias=True, exclude_none=True))

        if batch_review_result.error: sys.exit(1) # Exit with error if batch processing itself had an error
    else:
        console.print("[bold red]❌ Batch review failed. No results to display.[/bold red]"); sys.exit(1)

    console.rule("[bold blue]🚀 Ultron Batch Review Session Complete[/bold blue]")
    # Consider overall_had_errors if ignorer or other steps flag issues even if LLM succeeded
    # if any(fr.error for fr in batch_review_result.file_reviews if batch_review_result): sys.exit(1)

if __name__ == '__main__':
    cli()