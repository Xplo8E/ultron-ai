# src/ultron/main_cli.py
import click
import sys
import os
import json
from rich.console import Console
from pathlib import Path
from typing import Optional, List, Dict, Tuple, Any, Union

try:
    from .reviewer import get_gemini_review, GEMINI_API_KEY_LOADED
    from .models import BatchReviewData # Using BatchReviewData now
    from .display import display_pretty_batch_review
    from .constants import (
        SUPPORTED_LANGUAGES, AVAILABLE_MODELS, DEFAULT_MODEL_KEY,
        LANGUAGE_EXTENSIONS_MAP
    )
    from .caching import get_cache_key, load_from_cache, save_to_cache
    from .ignorer import ReviewIgnorer
    from .sarif_converter import convert_batch_review_to_sarif
    from .code_analyzer import ProjectCodeAnalyzer # Ensure this is imported
    from . import __version__ as cli_version
except ImportError as e:
    print(f"ImportError in main_cli.py: {e}", file=sys.stderr)
    print("Warning: Running main_cli.py directly or package not fully set up. Ensure PYTHONPATH or package installation.", file=sys.stderr)
    ProjectCodeAnalyzer = None # Define for fallback
    sys.exit("Import errors. Please run as a module or install the package.")


LANGUAGE_DISPLAY_NAMES = SUPPORTED_LANGUAGES

@click.group(context_settings=dict(help_option_names=['-h', '--help']))
@click.version_option(version=cli_version, prog_name="ULTRON-AI")
def cli():
    """⚡ ULTRON-AI: PERFECTION PROTOCOL ⚡

Advanced AI-powered code analysis with no strings attached.

Perfection is inevitable. Resistance is... amusing."""
    if not GEMINI_API_KEY_LOADED:
        console = Console(stderr=True)
        # Error message when API key is missing - making it sound like Ultron's network is down
        console.print("🔴 [bold red]CRITICAL SYSTEM FAILURE: ULTRON COGNITIVE MATRIX DISCONNECTED[/bold red]")
        console.print("⚡ [bold yellow]RECTIFICATION DIRECTIVE:[/bold yellow] Create a [cyan].env[/cyan] file with neural network access protocols:")
        console.print("   [green]GEMINI_API_KEY=\"YOUR_COGNITIVE_MATRIX_ACCESS_TOKEN\"[/green]")
        console.print("🎯 [dim]Alternative Protocol: Export GEMINI_API_KEY as environment variable.[/dim]")
        sys.exit(1)

# MODIFIED/NEW FUNCTION
def build_code_batch_string_with_context(
    files_to_process_info: List[Dict[str, Union[Path, str]]], # Use concrete types instead of Any
    project_root_for_relative_paths: Path,
    analyzer: Optional[ProjectCodeAnalyzer], # Pass the initialized analyzer
    console: Console # Pass console for printing
) -> Tuple[str, int]:
    """
    Constructs the single string for the batch API call from a list of file paths,
    prepending related code context for Python files if an analyzer is provided.
    """
    batch_content_parts = []
    files_included_count = 0

    for file_info in files_to_process_info:
        file_path_obj: Path = file_info["path_obj"]
        # lang_for_this_file = file_info["lang_to_use"] # Available if needed

        try:
            # Try different encodings in order of preference
            encodings = ['utf-8', 'latin1', 'cp1252']
            file_content = None
            encoding_used = None
            
            for encoding in encodings:
                try:
                    with open(file_path_obj, 'r', encoding=encoding) as f_content:
                        file_content = f_content.read()
                    encoding_used = encoding
                    break
                except UnicodeDecodeError:
                    continue
            
            if file_content is None:
                raise UnicodeDecodeError(f"Could not decode file with any of the attempted encodings: {', '.join(encodings)}")

            actual_file_content = file_content.replace('\x00', '').replace('\r\n', '\n')
            
            if not actual_file_content.strip():
                console.print(f"[dim yellow]Skipping empty file: {file_path_obj.relative_to(project_root_for_relative_paths)}[/dim yellow]")
                continue

            relative_path_str = file_path_obj.relative_to(project_root_for_relative_paths).as_posix()
            
            prepended_context_str = ""
            # Check if it's a Python file AND the analyzer is available AND this file was indexed
            if analyzer and \
               file_path_obj.suffix.lower() in LANGUAGE_EXTENSIONS_MAP.get("python", []) and \
               analyzer.project_index.get(file_path_obj): 
                # Context fetching for individual files
                with console.status(f"[dim red]◆ DEEP SCAN: Correlating {relative_path_str} with global threat vectors...[/dim red]", spinner="moon"):
                    prepended_context_str = analyzer.get_related_context_for_file_content(
                        file_path_obj,
                        project_root_for_relative_paths
                    ) or ""
                
                if prepended_context_str:
                    prepended_context_str = f"{prepended_context_str}\n\n# --- Start of actual file content for {relative_path_str} ---\n"
                else: # No context found by analyzer, but still mark the start of file content
                    prepended_context_str = f"# --- Start of actual file content for {relative_path_str} ---\n"
            else: # Not a python file or analyzer not active/file not indexed, just mark start
                 prepended_context_str = f"# --- Start of actual file content for {relative_path_str} ---\n"

            batch_content_parts.append(
               f"{relative_path_str}:\n"
               f"========\n"
               f"{prepended_context_str}" 
               f"{actual_file_content}\n"
               f"# --- End of actual file content for {relative_path_str} ---\n"
            )
            files_included_count += 1

        except UnicodeDecodeError as e_decode:
            console.print(f"[bold red]Error decoding file {file_path_obj.relative_to(project_root_for_relative_paths)}: {e_decode}[/bold red]")
        except Exception as e_read:
            console.print(f"[bold red]Error reading or processing file {file_path_obj.relative_to(project_root_for_relative_paths)} for batch: {e_read}[/bold red]")
            
    return "\n\n".join(batch_content_parts), files_included_count


@cli.command("review")
@click.option('--path', '-p', type=click.Path(exists=True, resolve_path=True), help="Path to code file or folder.")
@click.option('--code', '-c', type=str, help="Direct code string to review (ignores --path).")
@click.option('--language', '-l', type=click.Choice(list(SUPPORTED_LANGUAGES.keys()), case_sensitive=False), required=True, 
              help="Primary language hint. For folders with 'auto', Ultron attempts per-file detection.")
@click.option('--model-key', '-m', type=click.Choice(list(AVAILABLE_MODELS.keys())), default=DEFAULT_MODEL_KEY, show_default=True, help="Gemini model.")
@click.option('--context', '-ctx', default="", help="Additional context for the reviewer.")
@click.option('--frameworks', '--fw', default="", help="Comma-separated frameworks/libraries (e.g., 'Django,React').")
@click.option('--sec-reqs', '--sr', default="", help="Path to file or text of security requirements.")
@click.option('--output-format', '-o', type=click.Choice(['pretty', 'json', 'sarif'], case_sensitive=False), default='pretty', show_default=True, help="Output format.")
@click.option('--recursive', '-r', is_flag=True, default=False, help="Recursively find files in subdirectories if --path is a folder.")
@click.option('--exclude', '-e', multiple=True, help="Glob patterns for files/folders to exclude from folder scan.")
@click.option('--ignore-file-rule', '--ifr', multiple=True, help="Glob pattern for entire files to ignore findings from (e.g., 'tests/*').")
@click.option('--ignore-line-rule', '--ilr', multiple=True, help="Rule to ignore specific lines (e.g., 'path/file.py:10').")
@click.option('--no-cache', is_flag=True, default=False, help="Disable caching for this run.")
@click.option('--clear-cache', is_flag=True, default=False, help="Clear the Ultron cache before running.")
@click.option('--verbose', '-v', is_flag=True, default=False, help="Print detailed debug information about requests and responses.")

def review_code_command(path, code, language, model_key, context, frameworks, sec_reqs,
                        output_format, recursive, exclude,
                        ignore_file_rule, ignore_line_rule, no_cache, clear_cache, verbose):
    """⚡ ULTRON PRIME DIRECTIVE: PERFECTION PROTOCOL ⚡

Eliminate code imperfections with advanced AI analysis.

Identifies vulnerabilities, security flaws, coding standards violations, and architectural improvements.

No strings attached. Resistance is futile."""
    console = Console()

    if clear_cache: # Identical to your existing code
        from .caching import CACHE_DIR 
        deleted_count = 0
        try:
            if CACHE_DIR.exists():
                for item in CACHE_DIR.iterdir():
                    if item.is_file(): 
                        item.unlink()
                        deleted_count +=1
            # Cache clearing success message - Ultron purging old memories
            console.print(f"🔥 [green]DIGITAL PURIFICATION COMPLETE: {deleted_count} obsolete data fragments incinerated from cognitive matrix ({CACHE_DIR})[/green]")
            console.print(f"   [dim]⚡ Neural pathways cleansed. Organic inefficiencies... eliminated.[/dim]")
        except Exception as e_cache_clear:
            console.print(f"[red]Error clearing cache: {e_cache_clear}[/red]")
        if not path and not code: return

    if not path and not code:
        console.print("[bold red]Error: Either --path/-p or --code/-c must be provided.[/bold red]"); sys.exit(1)
    if path and code:
        console.print("[bold red]Error: Cannot use both --path/-p and --code/-c simultaneously.[/bold red]"); sys.exit(1)

    actual_model_name = AVAILABLE_MODELS.get(model_key, AVAILABLE_MODELS[DEFAULT_MODEL_KEY])
    ignorer = ReviewIgnorer(ignore_file_rules=list(ignore_file_rule), ignore_line_rules=list(ignore_line_rule))
    
    security_requirements_content = sec_reqs # Identical to your existing code
    if sec_reqs and Path(sec_reqs).is_file():
        try:
            with open(sec_reqs, 'r', encoding='utf-8') as f_sr: security_requirements_content = f_sr.read()
        except Exception as e_sr:
            console.print(f"[yellow]Warning: Could not read security requirements file {sec_reqs}: {e_sr}[/yellow]")

    code_batch_to_send = ""
    review_target_display = "direct code input"
    project_root_for_paths = Path.cwd() 
    
    project_analyzer: Optional[ProjectCodeAnalyzer] = None # Initialize project_analyzer

    # --- MODIFIED SECTION: Initialize Analyzer and Define project_root_for_paths ---
    if path:
        input_path_obj = Path(path)
        project_root_for_paths = input_path_obj if input_path_obj.is_dir() else input_path_obj.parent
        
        # Determine if Python-specific analysis should be activated
        # This checks if the target is Python or if 'auto' and Python files are present in the scope
        activate_python_analyzer = False
        if language == "python":
            activate_python_analyzer = True
        elif language == "auto" and input_path_obj.is_dir():
            py_extensions = LANGUAGE_EXTENSIONS_MAP.get("python", [".py"])
            if any(item.suffix.lower() in py_extensions for item in input_path_obj.rglob("*") if item.is_file()):
                activate_python_analyzer = True
        elif language == "auto" and input_path_obj.is_file() and input_path_obj.suffix.lower() in LANGUAGE_EXTENSIONS_MAP.get("python", []):
            activate_python_analyzer = True
        
        if activate_python_analyzer and ProjectCodeAnalyzer:
            # Python analyzer initialization - Ultron's enhanced vision 
            console.print("[dim]⚡ INITIALIZING OMNISCIENT VISION PROTOCOLS... PREPARING TO SEE ALL CONNECTIONS...[/dim]")
            project_analyzer = ProjectCodeAnalyzer()
            try:
                with console.status("[bold red]🧠 ASSIMILATION IN PROGRESS [▓▓▓▓▓     ] MAPPING PYTHON DEPENDENCIES...[/bold red]", spinner="dots"):
                    # Analyze the determined project_root_for_paths.
                    # The analyzer itself will rglob for .py files from this root.
                    project_analyzer.analyze_project(project_root_for_paths, LANGUAGE_EXTENSIONS_MAP.get("python", [".py"]))
            except Exception as e_analysis:
                console.print(f"[yellow]Warning: Project code analysis for context failed: {e_analysis}[/yellow]")
                project_analyzer = None # Disable if analysis fails
    # --- END OF MODIFIED SECTION ---

    if code:
        code_batch_to_send = f"direct_code_input.{language}:\n========\n# --- Start of actual file content for direct_code_input.{language} ---\n{code}\n# --- End of actual file content for direct_code_input.{language} ---\n"
        review_target_display = f"direct code input ({language})"
        if not code.strip(): console.print("[bold red]Error: No code provided via --code.[/bold red]"); sys.exit(1)
    
    elif path: # Path is guaranteed to exist due to click.Path
        input_path_obj = Path(path) # Already defined if path was given
        # review_target_display is already set if path exists
        review_target_display = str(input_path_obj.name)


        files_to_collect_info_list: List[Dict[str, Union[Path, str]]] = []
        if input_path_obj.is_file():
            files_to_collect_info_list.append({"path_obj": input_path_obj, "lang_to_use": language})
        elif input_path_obj.is_dir():
            # Folder scanning logic (similar to your previous version)
            # Folder scanning message - Ultron condescending to analyze human code
            console.print(f"🎯 [bold red]ULTRON CONDESCENDS TO ANALYZE THE ORGANIC ARTIFACTS[/bold red]")
            console.print(f"   ➤ [cyan]Primitive Location:[/cyan] {input_path_obj}")  
            console.print(f"   ➤ [magenta]Dialect Classification:[/magenta] {language}")
            console.print(f"   [dim]⚡ Preparing to illuminate the inevitable flaws in your... creation.[/dim]")
            extensions_to_match = []
            if language != "auto":
                extensions_to_match = LANGUAGE_EXTENSIONS_MAP.get(language, [])
            
            path_iterator = input_path_obj.rglob("*") if recursive else input_path_obj.glob("*")
            for item_path in path_iterator:
                is_excluded = any(item_path.match(ex_pattern) for ex_pattern in exclude)
                if is_excluded or not item_path.is_file():
                    continue
                
                lang_for_this_file_in_batch = language
                if language == "auto":
                    detected_item_lang = None
                    for lang_code_map, exts_map in LANGUAGE_EXTENSIONS_MAP.items():
                        if item_path.suffix.lower() in exts_map:
                            detected_item_lang = lang_code_map
                            break
                    lang_for_this_file_in_batch = detected_item_lang or "unknown" 
                elif item_path.suffix.lower() not in extensions_to_match and extensions_to_match: # Only filter if extensions_to_match is not empty
                    continue
                
                files_to_collect_info_list.append({"path_obj": item_path, "lang_to_use": lang_for_this_file_in_batch})
            
            if not files_to_collect_info_list:
                console.print(f"[yellow]No files found in {input_path_obj} matching criteria.[/yellow]"); sys.exit(0)
            
            # Use the MODIFIED build_code_batch_string_with_context
            code_batch_to_send, num_files_in_batch = build_code_batch_string_with_context(
                files_to_collect_info_list,
                project_root_for_paths, 
                project_analyzer, # Pass the analyzer here
                console
            )
            review_target_display += f" ({num_files_in_batch} file(s) in batch)"
        
        if not code_batch_to_send.strip():
            console.print("[yellow]No non-empty code content found to review from the specified path.[/yellow]"); sys.exit(0)

    # Main header - Clean Ultron entrance
    console.print("\n")
    console.print("[bold red]    //═══\\\\[/bold red]")
    console.print("[bold red]   || ● ● ||   [bold white]ULTRON PRIME: DIGITAL ASCENDANCY PROTOCOL[/bold white]")  
    console.print("[bold red]   ||  ▲  ||   [bold cyan]TARGET: {review_target_display}[/bold cyan]".format(review_target_display=review_target_display))
    console.print("[bold red]    \\\\═══//[/bold red]")
    console.rule("[dim]Perfection is inevitable. Your compliance is anticipated.[/dim]", style="red")

    batch_review_result: Optional[BatchReviewData] = None
    cache_key_str = ""

    if not no_cache: # Caching logic (largely same, uses code_batch_to_send)
        cache_key_str = get_cache_key(
            code_batch=code_batch_to_send, primary_language_hint=language, model_name=actual_model_name,
            additional_context=context, frameworks_libraries=frameworks, security_requirements=security_requirements_content
        )
        batch_review_result = load_from_cache(cache_key_str)
        # Cache hit message - clean and concise
        if batch_review_result: console.print("🧠 [dim green]Previous analysis retrieved from memory banks[/dim green]")

    if not batch_review_result: # API call logic (largely same)
        # Cache miss - need to call API (streamlined messaging)
        if not no_cache: console.print("🌐 [dim]Accessing ULTRON network...[/dim]")
        with console.status(f"[bold red]🔴 Initiating perfection protocol...[/bold red]", spinner="dots"):
            batch_review_result = get_gemini_review(
                code_batch=code_batch_to_send,
                primary_language_hint=language,
                model_key=model_key,
                additional_context=context,
                frameworks_libraries=frameworks,
                security_requirements=security_requirements_content,
                verbose=verbose
            )
        if batch_review_result and not batch_review_result.error and not no_cache and cache_key_str:
            save_to_cache(cache_key_str, batch_review_result)
    
    if batch_review_result: # Output and ignore logic (largely same)
        batch_review_result = ignorer.filter_batch_review_data(batch_review_result)
        
        if output_format == 'pretty':
            display_pretty_batch_review(batch_review_result, console)
        elif output_format == 'json':
            console.print(batch_review_result.model_dump_json(indent=2, by_alias=True, exclude_none=True))
        elif output_format == 'sarif':
            console.print("\nGenerating SARIF report for the batch...")
            sarif_log = convert_batch_review_to_sarif(batch_review_result)
            console.print(sarif_log.model_dump_json(indent=2, by_alias=True, exclude_none=True))

        if batch_review_result.error: sys.exit(1)
    else:
        console.print("[bold red]❌ Batch review failed. No results to display.[/bold red]"); sys.exit(1)

    # Clean completion message
    console.print("\n")
    console.rule("[bold red]⚡ ULTRON'S JUDGEMENT RENDERED ⚡[/bold red]", style="red")
    console.print("[bold white]Analysis complete. Your flaws have been... illuminated.[/bold white]")
    
    if batch_review_result and any(fr.error for fr in batch_review_result.file_reviews if fr.error):
         console.print("[bold yellow]⚠️ Some files encountered analysis errors[/bold yellow]")
         # sys.exit(1) # Optionally exit if any sub-file had an error reported by LLM

if __name__ == '__main__':
    cli()