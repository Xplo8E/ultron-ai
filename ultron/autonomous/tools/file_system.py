"""
File system tools for creating PoCs and test files.
"""

from pathlib import Path

def write_to_file(file_path: str, content: str) -> str:
    """
    Writes or overwrites a file with the given string content.
    Creates parent directories if they do not exist.
    
    Args:
        file_path: Path to the file to write
        content: Content to write to the file
        
    Returns:
        Success or error message
    """
    try:
        path_obj = Path(file_path)
        path_obj.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path_obj, 'w', encoding='utf-8') as f:
            f.write(content)
            
        return f"Success: Wrote {len(content.encode('utf-8'))} bytes to '{file_path}'."
    except Exception as e:
        return f"Error: Failed to write to file '{file_path}'. Reason: {e}" 