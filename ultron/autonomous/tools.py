# ultron/autonomous/tools.py
import os
import re
import ast
from pathlib import Path

# A simple dictionary to cache file contents during a single run.
_file_cache = {}

# --- NEW TOOL LOGIC ---
def search_codebase(root_path: str, regex_pattern: str) -> str:
    """
    Recursively searches for a regex pattern in all files within the codebase,
    respecting common exclusions.
    """
    matches = []
    MAX_MATCHES = 100  # Prevent overwhelming the context window
    root_path_obj = Path(root_path)

    try:
        # Compile the regex for efficiency
        pattern = re.compile(regex_pattern)
    except re.error as e:
        return f"Error: Invalid regex pattern provided. Details: {e}"

    for current_root, dirs, files in os.walk(root_path, topdown=True):
        # Exclude common virtual environment, git, and cache folders
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['__pycache__', 'venv', 'node_modules', '.git']]

        for filename in files:
            file_path = Path(current_root) / filename
            # Skip binary files or other non-text files if possible
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    for i, line in enumerate(f):
                        if pattern.search(line):
                            relative_path = file_path.relative_to(root_path_obj)
                            matches.append(f"{relative_path}:{i+1}: {line.strip()}")
                            if len(matches) >= MAX_MATCHES:
                                matches.append(f"\n... (Search stopped after reaching {MAX_MATCHES} matches) ...")
                                return "\n".join(matches)
            except Exception:
                # Ignore files that can't be opened or read
                continue
    
    if not matches:
        return f"No matches found for pattern '{regex_pattern}' in the entire codebase."
    
    return "\n".join(matches)

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
    # This function is a placeholder. The real logic is implemented
    # as a method in the AutonomousAgent class.
    pass


# --- NEW CORE LOGIC FUNCTIONS ---

class FunctionVisitor(ast.NodeVisitor):
    """An AST visitor to find all function and method names."""
    def __init__(self):
        self.functions = []
        self._current_class = None

    def visit_ClassDef(self, node):
        self._current_class = node.name
        self.generic_visit(node)
        self._current_class = None

    def visit_FunctionDef(self, node):
        if self._current_class:
            self.functions.append(f"{self._current_class}.{node.name}")
        else:
            self.functions.append(node.name)
        # Do not call generic_visit to avoid capturing nested functions separately for simplicity.

def list_functions_in_file(file_path: str) -> str:
    """Parses a Python file and lists all function and class method definitions."""
    if not file_path.endswith('.py'):
        return f"Error: Not a Python (.py) file. Use 'read_file_content' to inspect its type and content."

    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        tree = ast.parse(content)
        visitor = FunctionVisitor()
        visitor.visit(tree)
        
        if not visitor.functions:
            return f"No functions or methods found in {os.path.basename(file_path)}. The file might be for configuration, data, or initialization. Use 'read_file_content' to verify its purpose."
            
        return "Found Functions:\n- " + "\n- ".join(sorted(visitor.functions))
    except SyntaxError as e:
        return f"Error: Invalid Python syntax in {file_path}. Cannot parse functions. Use 'read_file_content' to inspect the syntax error. Details: {e}"
    except Exception as e:
        return f"Error parsing Python file {file_path}: {e}"

def search_pattern_in_file(file_path: str, regex_pattern: str) -> str:
    """Searches for a regex pattern in a file and returns matching lines with line numbers."""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        
        matches = []
        for i, line in enumerate(lines):
            if re.search(regex_pattern, line):
                matches.append(f"L{i+1}: {line.strip()}")
        
        if not matches:
            return f"No matches found for pattern '{regex_pattern}'."
        
        return "\n".join(matches)
    except Exception as e:
        return f"Error searching in file {file_path}: {e}"

def find_taints_in_file(file_path: str, sources: list[str], sinks: list[str]) -> str:
    """Finds lines containing source and sink keywords to spot potential data flows."""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        
        found_sources = []
        found_sinks = []
        
        for i, line in enumerate(lines):
            for source in sources:
                if source in line:
                    found_sources.append(f"L{i+1} (Source: {source}): {line.strip()}")
                    break # Don't match same line for multiple sources
            
            for sink in sinks:
                if sink in line:
                    found_sinks.append(f"L{i+1} (Sink: {sink}): {line.strip()}")
                    break # Don't match same line for multiple sinks

        if not found_sources and not found_sinks:
             return "No matches found for the provided keywords. This could mean the code is safe, OR the keywords are incorrect for this project's framework. Use `read_file_content` on this file and relevant imported modules to discover the correct data input and execution function names, then try this tool again with better keywords."

        result_parts = []
        if found_sources:
            result_parts.append("---\nFound Potential Sources:\n" + "\n".join(found_sources))
        else:
            result_parts.append("---\nNo matching sources found. The sinks might still be exploitable if the source is in another file.")

        if found_sinks:
            result_parts.append("---\nFound Potential Sinks:\n" + "\n".join(found_sinks))
        else:
            result_parts.append("---\nNo matching sinks found.")
            
        return "\n".join(result_parts)
    except Exception as e:
        return f"Error during taint analysis of file {file_path}: {e}"

# This function will return the list of tool functions the agent can use.
def get_available_tools():
    return [read_file_content]