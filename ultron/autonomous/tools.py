# ultron/autonomous/tools.py
import os
from pathlib import Path

# A simple dictionary to cache file contents during a single run.
_file_cache = {}

def get_directory_tree(root_path: str) -> str:
    """Generates a string representation of the directory tree."""
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
        for f in sorted(files): # Sort files for consistent output
            tree_lines.append(f"{sub_indent}└── {f}")
            
    return "\n".join(tree_lines)


def read_file_content(file_path: str) -> str:
    """
    Reads the full text content of a single file from the provided codebase.
    The file path must be relative to the project root.
    """
    # This function will be called by the agent, which lives in a class.
    # The class will hold the 'codebase_path' and pass it implicitly.
    # For now, we define the tool's logic. The class will handle the path joining.
    # This is a placeholder for the logic that will live inside the agent class.
    # The actual implementation needs the root path.
    # We will handle this inside the agent's execution logic.
    pass # The real logic will be in the agent class method that calls this.


# This function will return the list of tool functions the agent can use.
def get_available_tools():
    return [read_file_content]