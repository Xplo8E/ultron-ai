"""
Tool handling and execution management for Ultron autonomous agent.
Manages the validation and execution of all tool calls from the agent.
"""

from pathlib import Path
from rich.console import Console
from google.genai import types

# Import the core tool functions
from .tools.shell import execute_shell_command
from .tools.file_system import write_to_file
from .tools.static_analysis import (
    search_codebase,
    search_pattern_in_file,
    list_functions_in_file,
    find_taints_in_file,
    read_file_content,
    get_project_type_and_tech_stack
)

console = Console()

class ToolHandler:
    """
    Manages the validation and execution of all tool calls from the agent.
    This class acts as the bridge between the agent's requests and the actual
    system-level tool functions, ensuring safety and proper context.
    """
    
    def __init__(self, codebase_path: Path):
        """
        Initialize the tool handler with the project's codebase path.
        
        Args:
            codebase_path: Path to the project root directory
        """
        self.codebase_path = Path(codebase_path).resolve()

    def _resolve_and_validate_path(self, relative_path: str) -> tuple[Path | None, str | None]:
        """
        Ensures the agent does not access files outside the codebase path.
        
        Args:
            relative_path: The relative path to validate
            
        Returns:
            Tuple of (resolved_path, error_message). If error_message is not None,
            the path is invalid and should not be used.
        """
        # Check for path traversal attempts
        if '..' in Path(relative_path).parts or Path(relative_path).is_absolute():
            return None, "Error: Path traversal or absolute paths are not allowed. Use relative paths from the project root."
        
        # Resolve the absolute path
        absolute_path = (self.codebase_path / relative_path).resolve()
        
        # Ensure the resolved path is still within the codebase
        if not str(absolute_path).startswith(str(self.codebase_path)):
            return None, "Error: Security violation. Attempted to access a path outside of the designated workspace."

        return absolute_path, None

    def handle_execute_shell_command(self, command: str) -> str:
        """
        Handler for executing a shell command within the project root.
        
        Args:
            command: The shell command to execute
            
        Returns:
            Formatted output from the command execution
        """
        console.print(f"**[Tool Call]** `execute_shell_command(command='{command}')`")
        return execute_shell_command(command, str(self.codebase_path))

    def handle_write_to_file(self, file_path: str, content: str) -> str:
        """
        Handler for writing a file. It allows writing within the project codebase
        or to a designated temporary directory (/tmp).
        """
        console.print(f"**[Tool Call]** `write_to_file(file_path='{file_path}', content_length={len(content)})`")
        
        # --- NEW LOGIC TO ALLOW WRITING TO /tmp ---
        # Sanitize the provided path to prevent any path traversal tricks.
        # For example, this prevents '/tmp/../etc/passwd'
        safe_file_path = Path(file_path).resolve()

        # Check if the agent is trying to write to the allowed temporary directory.
        if str(safe_file_path).startswith('/tmp/'):
            # If it's a safe temporary path, allow it directly.
            absolute_path = safe_file_path
            
        else:
            # Otherwise, enforce the original rule: path must be within the codebase.
            validated_path, error = self._resolve_and_validate_path(file_path)
            if error:
                return error # Return the security error from the validator.
            if not validated_path:
                # This should ideally not be reached if validator is correct.
                return f"Error: The path '{file_path}' is invalid or could not be resolved."
            absolute_path = validated_path

        # Proceed with the write operation using the determined safe absolute path.
        return write_to_file(str(absolute_path), content)

    # --- Static Analysis Tool Handlers ---

    def handle_read_file_content(self, file_path: str) -> str:
        """
        Handler for reading file content with security validation.
        
        Args:
            file_path: Relative path to the file to read
            
        Returns:
            File content or error message
        """
        console.print(f"**[Tool Call]** `read_file_content(file_path='{file_path}')`")
        absolute_path, error = self._resolve_and_validate_path(file_path)
        if error:
            return error
        
        # Enhanced error handling for file not found
        if not absolute_path.exists():
            # Check if it's a directory
            if absolute_path.is_dir():
                try:
                    contents = [p.name for p in absolute_path.iterdir()]
                    contents_str = ", ".join(sorted(contents)) if contents else "It is empty."
                    return f"Error: Path '{file_path}' is a directory, not a file. Its contents are: [{contents_str}]."
                except Exception as e:
                    return f"Error: Path '{file_path}' is a directory, but its contents could not be read. Reason: {e}"
            
            # Check parent directory for context
            parent_dir = absolute_path.parent
            if parent_dir.exists():
                try:
                    contents = [p.name for p in parent_dir.iterdir()]
                    contents_str = ", ".join(sorted(contents)) if contents else "It is empty."
                    relative_parent = parent_dir.relative_to(self.codebase_path)
                    relative_parent_str = str(relative_parent) if str(relative_parent) != '.' else 'the root directory'
                    return f"Error: File not found at path '{file_path}'. The parent directory '{relative_parent_str}' exists and contains: [{contents_str}]."
                except Exception as e:
                    return f"Error: File not found at path '{file_path}'. The parent directory exists, but its contents could not be read. Reason: {e}"
            else:
                relative_parent = parent_dir.relative_to(self.codebase_path)
                return f"Error: Cannot access path '{file_path}' because its directory '{relative_parent}' does not exist."
        
        return read_file_content(str(absolute_path))

    def handle_search_pattern(self, file_path: str, regex_pattern: str) -> str:
        """
        Handler for searching a pattern in a file.
        
        Args:
            file_path: Relative path to the file to search
            regex_pattern: The regex pattern to search for
            
        Returns:
            Search results or error message
        """
        console.print(f"**[Tool Call]** `search_pattern(file_path='{file_path}', regex_pattern='{regex_pattern}')`")
        absolute_path, error = self._resolve_and_validate_path(file_path)
        if error:
            return error
        return search_pattern_in_file(str(absolute_path), regex_pattern)

    def handle_list_functions(self, file_path: str) -> str:
        """
        Handler for listing functions in a Python file.
        
        Args:
            file_path: Relative path to the Python file
            
        Returns:
            List of functions or error message
        """
        console.print(f"**[Tool Call]** `list_functions(file_path='{file_path}')`")
        absolute_path, error = self._resolve_and_validate_path(file_path)
        if error:
            return error
        return list_functions_in_file(str(absolute_path))

    def handle_find_taint_sources_and_sinks(self, file_path: str, sources: list[str], sinks: list[str]) -> str:
        """
        Handler for finding taint sources and sinks.
        
        Args:
            file_path: Relative path to the file to analyze
            sources: List of source keywords to search for
            sinks: List of sink keywords to search for
            
        Returns:
            Taint analysis results or error message
        """
        console.print(f"**[Tool Call]** `find_taint_sources_and_sinks(file_path='{file_path}', sources={sources}, sinks={sinks})`")
        absolute_path, error = self._resolve_and_validate_path(file_path)
        if error:
            return error
        return find_taints_in_file(str(absolute_path), sources, sinks)

    def handle_search_codebase(self, regex_pattern: str) -> str:
        """
        Handler for searching the entire codebase.
        
        Args:
            regex_pattern: The regex pattern to search for
            
        Returns:
            Search results across the entire codebase
        """
        console.print(f"**[Tool Call]** `search_codebase(regex_pattern='{regex_pattern}')`")
        return search_codebase(str(self.codebase_path), regex_pattern)

    def handle_get_project_type(self) -> str:
        """
        Handler for analyzing the project type and technology stack.
        
        Returns:
            Project type and technology analysis
        """
        console.print(f"**[Tool Call]** `get_project_type()`")
        return get_project_type_and_tech_stack(str(self.codebase_path))

    def get_all_tool_definitions(self) -> list[types.FunctionDeclaration]:
        """
        Returns the list of FunctionDeclaration objects for the Gemini API.
        Defines all available tools with their parameters and descriptions.
        
        Returns:
            List of FunctionDeclaration objects for the API
        """
        return [
            # --- Primary, Low-Level Tools (High Flexibility) ---
            types.FunctionDeclaration(
                name="execute_shell_command",
                description="Executes any shell command and returns the output. This is the primary tool for all interactions with the environment - compilation, dynamic analysis, running binaries, package management, etc.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "command": types.Schema(type=types.Type.STRING, description="The shell command to execute.")
                    },
                    required=["command"]
                )
            ),
            types.FunctionDeclaration(
                name="write_to_file",
                description="Creates or overwrites a file with the given content. Use for creating PoCs, scripts, or patches.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "file_path": types.Schema(type=types.Type.STRING, description="Relative path from project root for the file to create/overwrite."),
                        "content": types.Schema(type=types.Type.STRING, description="The full string content to write to the file.")
                    },
                    required=["file_path", "content"]
                )
            ),
            
            # --- Specialized, High-Level Tools (High Reliability) ---
            types.FunctionDeclaration(
                name="read_file_content",
                description="Reads the full text content of a single file. The file path must be relative to the project root.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={"file_path": types.Schema(type=types.Type.STRING, description="Relative path to the file from project root.")},
                    required=["file_path"]
                )
            ),
            types.FunctionDeclaration(
                name="search_pattern",
                description="Searches for a regex pattern within a single file and returns matching lines with line numbers.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "file_path": types.Schema(type=types.Type.STRING, description="Relative path to the file."),
                        "regex_pattern": types.Schema(type=types.Type.STRING, description="The regex pattern to search for.")
                    },
                    required=["file_path", "regex_pattern"]
                )
            ),
            types.FunctionDeclaration(
                name="list_functions",
                description="Lists all function and class method definitions in a Python (.py) file using AST parsing. More reliable than grep for Python code.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={"file_path": types.Schema(type=types.Type.STRING, description="Relative path to the Python file.")},
                    required=["file_path"]
                )
            ),
            types.FunctionDeclaration(
                name="find_taint_sources_and_sinks",
                description="Scans a file to find lines containing potential sources (e.g., user input) and sinks (e.g., command execution). Useful for data flow analysis.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "file_path": types.Schema(type=types.Type.STRING, description="Relative path to the file."),
                        "sources": types.Schema(type=types.Type.ARRAY, items=types.Schema(type=types.Type.STRING), description="Keywords for untrusted data sources (e.g., 'request.args', 'os.environ')."),
                        "sinks": types.Schema(type=types.Type.ARRAY, items=types.Schema(type=types.Type.STRING), description="Keywords for dangerous sinks (e.g., 'eval', 'subprocess.run').")
                    },
                    required=["file_path", "sources", "sinks"]
                )
            ),
            types.FunctionDeclaration(
                name="search_codebase",
                description="Recursively searches the entire codebase for a regex pattern. Use this to find all occurrences of a function, setting, or keyword across all files.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "regex_pattern": types.Schema(type=types.Type.STRING, description="The regex pattern to search for globally.")
                    },
                    required=["regex_pattern"]
                )
            ),
            
            # --- Project Comprehension Tool ---
            types.FunctionDeclaration(
                name="get_project_type",
                description="PHASE 1 MANDATORY TOOL: Analyzes key manifest files (e.g., package.json, AndroidManifest.xml, requirements.txt) to identify the project type and technology stack. This should be one of the first tools you use to understand what kind of project you're analyzing.",
                parameters=types.Schema(type=types.Type.OBJECT, properties={})  # No parameters needed
            ),

            types.FunctionDeclaration(
                name="save_finding_and_continue",
                description="MUST be called after a vulnerability is fully verified and a complete report is written. Provide the full markdown report. After calling this, continue searching for other vulnerabilities.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "report": types.Schema(type=types.Type.STRING, description="The complete vulnerability report in markdown format, following the specified template.")
                    },
                    required=["report"]
                )
            ),
        ]

    def get_tool_map(self) -> dict[str, callable]:
        """
        Returns a dictionary mapping tool names to their handler methods.
        
        Returns:
            Dictionary mapping tool names to handler functions
        NOTE: 'save_finding_and_continue' is handled directly in the agent's main loop.
        """
        return {
            # Low-level tools
            "execute_shell_command": self.handle_execute_shell_command,
            "write_to_file": self.handle_write_to_file,
            
            # High-level static analysis tools
            "read_file_content": self.handle_read_file_content,
            "search_pattern": self.handle_search_pattern,
            "list_functions": self.handle_list_functions,
            "find_taint_sources_and_sinks": self.handle_find_taint_sources_and_sinks,
            "search_codebase": self.handle_search_codebase,
            
            # Project comprehension tool
            "get_project_type": self.handle_get_project_type,
        }