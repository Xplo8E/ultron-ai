"""
Static analysis tools for Python code analysis.
Contains specialized tools for structured code analysis using AST parsing and pattern matching.
"""

import os
import re
import ast
from pathlib import Path

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
        return f"Error: Not a Python (.py) file. Use 'execute_shell_command' with 'cat' or 'grep' to inspect its type and content."

    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        tree = ast.parse(content)
        visitor = FunctionVisitor()
        visitor.visit(tree)
        
        if not visitor.functions:
            return f"No functions or methods found in {os.path.basename(file_path)}. The file might be for configuration, data, or initialization. Use 'execute_shell_command' with 'cat {file_path}' to verify its purpose."
            
        return "Found Functions:\n- " + "\n- ".join(sorted(visitor.functions))
    except SyntaxError as e:
        return f"Error: Invalid Python syntax in {file_path}. Cannot parse functions. Use 'execute_shell_command' with 'cat {file_path}' to inspect the syntax error. Details: {e}"
    except Exception as e:
        return f"Error parsing Python file {file_path}: {e}"

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
             return "No matches found for the provided keywords. This could mean the code is safe, OR the keywords are incorrect for this project's framework. Use 'execute_shell_command' with 'cat' on this file and relevant imported modules to discover the correct data input and execution function names, then try this tool again with better keywords."

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

def read_file_content(file_path: str) -> str:
    """
    Reads the full text content of a single file.
    
    Args:
        file_path: Path to the file to read
        
    Returns:
        File content or error message
    """
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
    except Exception as e:
        return f"Error: Could not read file '{file_path}'. Reason: {e}"

def get_project_type_and_tech_stack(root_path: str) -> str:
    """
    Analyzes key files to determine the project's type and technology stack.
    Returns a summary string for the agent to understand what kind of project it's analyzing.
    
    Args:
        root_path: Path to the project root directory
        
    Returns:
        Project type and technology summary
    """
    manifests = {
        # Web Applications
        'package.json': 'Node.js (Web/CLI)',
        'requirements.txt': 'Python (Generic/Web)',
        'pom.xml': 'Java (Maven)',
        'build.gradle': 'Java/Android (Gradle)',
        'composer.json': 'PHP (Composer)',
        'Gemfile': 'Ruby (Bundler)',
        'setup.py': 'Python (setuptools)',
        'pyproject.toml': 'Python (Modern)',
        'yarn.lock': 'Node.js (Yarn)',
        'package-lock.json': 'Node.js (npm)',
        
        # Mobile Applications
        'AndroidManifest.xml': 'Android App',
        'app/AndroidManifest.xml': 'Android App',
        'src/main/AndroidManifest.xml': 'Android App',
        'Podfile': 'iOS (CocoaPods)',
        'Package.swift': 'iOS (Swift Package Manager)',
        'pubspec.yaml': 'Flutter/Dart',
        
        # Compiled Languages
        'Makefile': 'C/C++ (or other compiled language)',
        'CMakeLists.txt': 'C/C++ (CMake)',
        'Cargo.toml': 'Rust',
        'go.mod': 'Go',
        'stack.yaml': 'Haskell (Stack)',
        'cabal.project': 'Haskell (Cabal)',
        
        # Configuration/Infrastructure
        'Dockerfile': 'Docker Container',
        'docker-compose.yml': 'Docker Compose',
        'main.tf': 'Terraform Infrastructure',
        'terraform.tf': 'Terraform Infrastructure',
        'ansible.cfg': 'Ansible Configuration',
        'playbook.yml': 'Ansible Playbook',
        'serverless.yml': 'Serverless Framework',
        'netlify.toml': 'Netlify Configuration',
        'vercel.json': 'Vercel Configuration',
        
        # Framework-specific
        'manage.py': 'Django (Python Web Framework)',
        'app.py': 'Flask (Python Web Framework)',
        'server.js': 'Node.js Server',
        'index.js': 'Node.js Application',
        'webpack.config.js': 'Webpack (Build Tool)',
        'vite.config.js': 'Vite (Build Tool)',
        'next.config.js': 'Next.js (React Framework)',
        'nuxt.config.js': 'Nuxt.js (Vue Framework)',
        'angular.json': 'Angular (Web Framework)'
    }
    
    found_tech = []
    additional_info = []
    root_path_obj = Path(root_path)
    
    # Check for manifest files
    for filename, tech in manifests.items():
        file_path = root_path_obj / filename
        if file_path.exists():
            found_tech.append(tech)
            
            # Try to extract additional information from key files
            try:
                if filename == 'package.json':
                    with open(file_path, 'r', encoding='utf-8') as f:
                        import json
                        data = json.load(f)
                        if 'scripts' in data and 'start' in data['scripts']:
                            additional_info.append(f"Start command: {data['scripts']['start']}")
                        if 'dependencies' in data:
                            key_deps = [dep for dep in data['dependencies'].keys() 
                                      if dep in ['express', 'react', 'vue', 'angular', 'fastify', 'koa']]
                            if key_deps:
                                additional_info.append(f"Key dependencies: {', '.join(key_deps)}")
                                
                elif filename == 'requirements.txt':
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        frameworks = []
                        if 'django' in content.lower():
                            frameworks.append('Django')
                        if 'flask' in content.lower():
                            frameworks.append('Flask')
                        if 'fastapi' in content.lower():
                            frameworks.append('FastAPI')
                        if frameworks:
                            additional_info.append(f"Python frameworks: {', '.join(frameworks)}")
                            
            except Exception:
                # If we can't parse the file, that's fine, we'll just skip the additional info
                pass
    
    # Check for common directory structures that indicate project types
    common_dirs = {
        'src/main/java': 'Java (Maven/Gradle structure)',
        'app/src/main': 'Android (Standard structure)',
        'lib': 'Library project',
        'bin': 'Binary/Executable project',
        'public': 'Web application (static assets)',
        'static': 'Web application (static assets)',
        'templates': 'Web application (templating)',
        'migrations': 'Database-backed application',
        'models': 'MVC-style application',
        'controllers': 'MVC-style application',
        'views': 'MVC-style application'
    }
    
    for dir_name, tech in common_dirs.items():
        if (root_path_obj / dir_name).is_dir():
            found_tech.append(tech)
    
    # Analyze file extensions for additional clues
    extensions = {}
    try:
        for file_path in root_path_obj.rglob('*'):
            if file_path.is_file() and not file_path.name.startswith('.'):
                ext = file_path.suffix.lower()
                if ext:
                    extensions[ext] = extensions.get(ext, 0) + 1
    except Exception:
        pass
    
    # Identify primary languages by file count
    language_extensions = {
        '.py': 'Python',
        '.js': 'JavaScript',
        '.ts': 'TypeScript',
        '.java': 'Java',
        '.kt': 'Kotlin',
        '.cpp': 'C++',
        '.c': 'C',
        '.rs': 'Rust',
        '.go': 'Go',
        '.php': 'PHP',
        '.rb': 'Ruby',
        '.swift': 'Swift',
        '.dart': 'Dart'
    }
    
    primary_languages = []
    for ext, count in sorted(extensions.items(), key=lambda x: x[1], reverse=True)[:3]:
        if ext in language_extensions and count > 2:  # Only include if there are multiple files
            primary_languages.append(f"{language_extensions[ext]} ({count} files)")
    
    # Build the final response
    result_parts = []
    
    if found_tech:
        unique_tech = list(dict.fromkeys(found_tech))  # Remove duplicates while preserving order
        result_parts.append(f"**Detected Project Types:** {', '.join(unique_tech)}")
    else:
        result_parts.append("**Project Type:** Could not automatically determine from manifest files")
    
    if primary_languages:
        result_parts.append(f"**Primary Languages:** {', '.join(primary_languages)}")
    
    if additional_info:
        result_parts.append(f"**Additional Info:** {', '.join(additional_info)}")
    
    if not found_tech and not primary_languages:
        result_parts.append("\n**Recommendation:** Use 'execute_shell_command' with 'ls -la' and 'find . -name \"*.ext\" | head -10' to investigate the project structure manually.")
    
    return "\n".join(result_parts) 