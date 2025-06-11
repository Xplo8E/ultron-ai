"""
Shell execution tools for dynamic analysis and interaction.
"""

import subprocess
import re

def execute_shell_command(command: str, working_directory: str) -> str:
    """
    Executes a shell command in a specified directory and returns its output.
    This is the primary tool for all interactions with the environment.
    """
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=180,
            cwd=working_directory,
            encoding='utf-8',
            errors='ignore'
        )
        
        output = f"Exit Code: {result.returncode}\n"
        if result.stdout:
            output += f"--- STDOUT ---\n{result.stdout.strip()}\n"
        if result.stderr:
            output += f"--- STDERR ---\n{result.stderr.strip()}\n"
            
        return output.strip()
        
    except subprocess.TimeoutExpired:
        return "Error: Command timed out after 180 seconds."
    except Exception as e:
        return f"Error: An unexpected exception occurred while executing the command: {e}" 