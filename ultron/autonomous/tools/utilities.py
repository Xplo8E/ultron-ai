"""
Utility functions for the Ultron autonomous agent.
Contains helper functions for directory traversal, file analysis, etc.
"""

import os
from pathlib import Path

def get_directory_tree(root_path: str) -> str:
    """
    Generates a string representation of the directory tree.
    
    Args:
        root_path: Path to the root directory to analyze
        
    Returns:
        String representation of the directory structure
    """
    tree_lines = []
    root_path_obj = Path(root_path)
    
    for root, dirs, files in os.walk(root_path, topdown=True):
        # Exclude common virtual environment and cache folders
        dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__' and d != 'venv']
        
        # Calculate depth relative to the initial root path
        current_path = Path(root)
        if current_path == root_path_obj:
            level = 0
            # Add the root directory name itself, but only once
            tree_lines.append(f"{os.path.basename(root)}/")
        else:
            level = len(current_path.relative_to(root_path_obj).parts)

        indent = '    ' * level
        
        # We already added the root, so just add subdirectories
        if level > 0:
            tree_lines.append(f"{indent}├── {os.path.basename(root)}/")

        sub_indent = '    ' * (level + 1)
        for f in sorted(files):  # Sort files for consistent output
            tree_lines.append(f"{sub_indent}└── {f}")
            
    return "\n".join(tree_lines) 