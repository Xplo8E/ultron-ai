"""
Utility functions for the Ultron autonomous agent.
Contains helper functions for directory traversal, file analysis, etc.
"""

import os
from pathlib import Path

# Define common exclusion patterns for files and directories
# This is much more comprehensive
DIR_EXCLUSIONS = {'.git', '__pycache__', 'node_modules', 'venv', 'target', 'build', 'dist', '.vscode', '.idea', 'env', '.env'}
FILE_EXCLUSIONS = {'.DS_Store', 'package-lock.json', 'yarn.lock', 'Thumbs.db', '.gitignore'}

# Focus on file types that are likely to contain logic or be security-relevant
RELEVANT_EXTENSIONS = {
    '.py', '.js', '.ts', '.java', '.go', '.rs', '.rb', '.php', '.c', '.cpp', '.h',  # Code
    '.html', '.jsx', '.tsx', '.vue', '.svelte',  # Frontend
    '.sql', '.sh', '.bash', '.ps1', '.bat',  # Scripts
    '.json', '.yml', '.yaml', '.toml', '.xml', '.ini', '.conf', '.config',  # Config
    '.md', '.txt', 'Dockerfile', 'docker-compose.yml', 'Makefile', 'CMakeLists.txt',  # Docs & Build
    '.env', '.properties', '.cfg'  # Environment/Config files
}

def get_directory_tree(root_path: str, max_depth: int = 4, max_files_per_dir: int = 8) -> str:
    """
    Generates an intelligent, summarized string representation of the directory tree.
    Focuses on security-relevant files and excludes common noise.

    Args:
        root_path: Path to the root directory to analyze.
        max_depth: Maximum depth to traverse (default: 4).
        max_files_per_dir: Maximum number of files to list per directory (default: 8).
    
    Returns:
        A summarized string representation of the directory structure.
    """
    tree_lines = []
    root_path_obj = Path(root_path)
    
    # Track statistics for summary
    total_dirs_scanned = 0
    total_files_found = 0
    total_relevant_files = 0
    
    for root, dirs, files in os.walk(root_path, topdown=True):
        current_path = Path(root)
        depth = len(current_path.relative_to(root_path_obj).parts)
        total_dirs_scanned += 1

        # --- Pruning and Filtering Logic ---
        if depth >= max_depth:
            dirs[:] = []  # Don't go deeper
            continue

        # Exclude specified directories and hidden dirs
        dirs[:] = [d for d in dirs if d not in DIR_EXCLUSIONS and not d.startswith('.')]
        
        # Filter files for relevance and exclude common noise
        total_files_found += len(files)
        relevant_files = []
        for f in files:
            if f not in FILE_EXCLUSIONS:
                file_path = Path(f)
                # Include files with relevant extensions or special names (like Dockerfile)
                if (file_path.suffix.lower() in RELEVANT_EXTENSIONS or 
                    f in {'Dockerfile', 'Makefile', 'README.md', 'requirements.txt', 'package.json', 'setup.py'}):
                    relevant_files.append(f)
        
        total_relevant_files += len(relevant_files)
        
        # --- Tree Generation ---
        if current_path == root_path_obj:
            tree_lines.append(f"{os.path.basename(root)}/")
        else:
            indent = '  ' * (depth - 1)
            tree_lines.append(f"{indent}├── {os.path.basename(root)}/")

        # List relevant files, up to the limit
        if relevant_files:
            sub_indent = '  ' * depth
            sorted_files = sorted(relevant_files)
            for i, f in enumerate(sorted_files):
                if i >= max_files_per_dir:
                    remaining = len(sorted_files) - max_files_per_dir
                    tree_lines.append(f"{sub_indent}├── ... (+{remaining} more relevant files)")
                    break
                connector = "├──" if i < min(len(sorted_files), max_files_per_dir) - 1 else "└──"
                tree_lines.append(f"{sub_indent}{connector} {f}")

    # Add summary statistics
    if not tree_lines:
        return "The directory appears to be empty or contains only excluded file types."

    # Add a helpful summary at the end
    summary_lines = [
        "",
        "📊 **ANALYSIS SUMMARY:**",
        f"• Directories scanned: {total_dirs_scanned}",
        f"• Total files found: {total_files_found}",
        f"• Security-relevant files: {total_relevant_files}",
        f"• Max depth limit: {max_depth} levels",
        f"• Showing up to {max_files_per_dir} files per directory"
    ]
    
    return "\n".join(tree_lines + summary_lines) 