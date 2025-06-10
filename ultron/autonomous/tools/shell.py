"""
Shell execution tools for dynamic analysis and interaction.
"""

import subprocess

def execute_shell_command(command: str, working_directory: str) -> str:
    """
    Executes a shell command in a specified directory and returns its output.
    This is the primary tool for all interactions with the environment.
    
    Args:
        command: The shell command to execute
        working_directory: The directory to execute the command in
        
    Returns:
        Formatted string containing exit code, stdout, and stderr
    """
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=120,  # Increased timeout for more complex operations
            cwd=working_directory,
            encoding='utf-8',
            errors='ignore'
        )
        
        output = f"Exit Code: {result.returncode}\n"
        if result.stdout:
            output += f"--- STDOUT ---\n{result.stdout.strip()}\n"
        if result.stderr:
            output += f"--- STDERR ---\n{result.stderr.strip()}\n"
            
        # Highlight common crash signatures for the agent to notice
        if "AddressSanitizer" in result.stderr or "Segmentation fault" in result.stderr or "panic:" in result.stderr:
            output += "\n*** POTENTIAL CRASH DETECTED in STDERR. Analyze the output carefully. ***"
            
        return output.strip()
        
    except subprocess.TimeoutExpired:
        return "Error: Command timed out after 120 seconds. It may be a long-running process or it may have hung."
    except Exception as e:
        return f"Error: An unexpected exception occurred while executing the command. Reason: {e}" 