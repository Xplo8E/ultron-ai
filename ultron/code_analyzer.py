# src/ultron/code_analyzer.py
import ast
import os
from pathlib import Path
from typing import Dict, List, Optional, Any, Set, Tuple

# --- Data Structures for our Index ---
class FunctionCall:
    def __init__(self, module: Optional[str], func_name: str, line: int):
        self.module = module # Name of the module if it's like module.function()
        self.func_name = func_name
        self.line = line
        self.full_call_name = f"{module}.{func_name}" if module else func_name

    def __repr__(self):
        return f"Call({self.full_call_name} at L{self.line})"

class FunctionDefinition:
    def __init__(self, name: str, signature: str, docstring: Optional[str], 
                 start_line: int, end_line: int, calls: List[FunctionCall], 
                 body_snippet: Optional[str] = None): # Added body_snippet
        self.name = name
        self.signature = signature
        self.docstring = docstring
        self.start_line = start_line
        self.end_line = end_line
        self.calls = calls # List of FunctionCall objects
        self.body_snippet = body_snippet # e.g., first few lines

    def __repr__(self):
        return f"Def({self.name}, Calls: {len(self.calls)})"

    def get_context_summary(self, max_snippet_lines=5) -> str:
        summary = f"Function: {self.signature}"
        if self.docstring:
            summary += f"\n  Docstring: \"{self.docstring.strip()}\""
        if self.body_snippet:
            snippet_lines = self.body_snippet.splitlines()
            if len(snippet_lines) > max_snippet_lines:
                summary += f"\n  Body Snippet (first {max_snippet_lines} lines):\n    " + "\n    ".join(snippet_lines[:max_snippet_lines]) + "\n    ..."
            else:
                summary += f"\n  Body Snippet:\n    " + "\n    ".join(snippet_lines)
        return summary


class FileAnalysis:
    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.functions: Dict[str, FunctionDefinition] = {} # name -> FunctionDefinition
        self.imports: Dict[str, str] = {} # alias -> full_module_name or name -> name (for from x import y)

    def __repr__(self):
        return f"FileAnalysis({self.file_path.name}, Funcs: {len(self.functions)})"

# --- AST Visitor ---
class PythonCodeVisitor(ast.NodeVisitor):
    def __init__(self, file_path: Path, source_code: str):
        self.file_path = file_path
        self.source_lines = source_code.splitlines()
        self.current_function_name: Optional[str] = None
        self.current_function_calls: List[FunctionCall] = []
        self.definitions: Dict[str, FunctionDefinition] = {}
        self.imports: Dict[str, str] = {} # alias -> full_name

    def _get_source_segment(self, node: ast.AST) -> str:
        """Extracts the original source code for the given AST node."""
        if hasattr(node, 'lineno') and hasattr(node, 'end_lineno'):
            # ast node line numbers are 1-based, list indices are 0-based
            start_line = node.lineno -1
            end_line = node.end_lineno # end_lineno is inclusive for slicing lines

            # Handle column offsets for more precise snippets if available
            # For now, just taking full lines for simplicity
            segment = self.source_lines[start_line:end_line]
            return "\n".join(segment)
        return ""
        
    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            self.imports[alias.asname or alias.name] = alias.name
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        module_name = node.module or ""
        for alias in node.names:
            # Store both alias (if present) and original name, mapping to full path if possible
            # For simplicity, mapping `name` to `module.name` if module exists
            imported_name = alias.name
            full_name = f"{module_name}.{imported_name}" if module_name else imported_name
            self.imports[alias.asname or imported_name] = full_name
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        func_name = node.name
        self.current_function_name = func_name
        self.current_function_calls = []

        # Reconstruct a simple signature
        args = [arg.arg for arg in node.args.args]
        signature = f"def {func_name}({', '.join(args)}):"
        docstring = ast.get_docstring(node)
        
        # Get body snippet
        body_start_line = node.body[0].lineno if node.body else node.lineno
        # end_lineno is the last line of the function including its body
        body_snippet = "\n".join(self.source_lines[body_start_line-1 : node.end_lineno])


        # Visit children to find calls within this function
        # Store current state before recursing into nested functions/classes
        outer_func_name = self.current_function_name
        outer_calls = self.current_function_calls
        
        self.generic_visit(node) # This will populate self.current_function_calls

        self.definitions[func_name] = FunctionDefinition(
            name=func_name,
            signature=signature,
            docstring=docstring,
            start_line=node.lineno,
            end_line=node.end_lineno,
            calls=self.current_function_calls, # Calls collected by generic_visit
            body_snippet=body_snippet
        )
        # Restore state for outer scope (if any)
        self.current_function_name = outer_func_name
        self.current_function_calls = outer_calls


    def visit_Call(self, node: ast.Call):
        # This is a simplified call detection. Real-world scenarios are more complex
        # (e.g., instance methods, calls on imported objects, etc.)
        func_node = node.func
        module_name = None
        func_name_str = ""

        if isinstance(func_node, ast.Name): # Direct function call like func()
            func_name_str = func_node.id
            # Check if it's an imported function/module usage
            if func_name_str in self.imports:
                 # Could be module.func() or just func() if from x import func
                 # For simplicity, let's assume if it's in imports, it's a full path or direct import
                 func_name_str = self.imports[func_name_str] # Use the imported full name
        elif isinstance(func_node, ast.Attribute): # Call like object.method() or module.function()
            # Try to resolve the module/object part
            value = func_node.value
            attr_name = func_node.attr
            
            # Trace back the attribute access chain
            obj_parts = []
            curr = value
            while isinstance(curr, ast.Attribute):
                obj_parts.insert(0, curr.attr)
                curr = curr.value
            if isinstance(curr, ast.Name):
                obj_parts.insert(0, curr.id)
            
            if obj_parts:
                # Heuristic: if first part is an import, consider it a module
                potential_module_or_obj = obj_parts[0]
                if potential_module_or_obj in self.imports:
                    # It's likely module.submodule.func or imported_obj.method
                    # For simplicity, let's assume the first part is the primary "module" context
                    module_name = self.imports[potential_module_or_obj] # Use the full imported name
                    if len(obj_parts) > 1: # e.g., imported_module.another_attr.method_call
                        func_name_str = ".".join(obj_parts[1:]) + "." + attr_name
                    else: # e.g. imported_module.method_call (where imported_module is an alias)
                         func_name_str = attr_name

                else: # Likely an instance method call, e.g. self.method() or obj.method()
                    module_name = ".".join(obj_parts) # The object/class path
                    func_name_str = attr_name
            else: # Fallback if not Name or Attribute (e.g., complex expression)
                func_name_str = "complex_call_target"

        else: # Other types of callable expressions
            func_name_str = "unknown_callable_type"

        if func_name_str and self.current_function_name: # Only record if we have a name and are inside a function
            call = FunctionCall(module=module_name, func_name=func_name_str, line=node.lineno)
            self.current_function_calls.append(call)
        
        self.generic_visit(node) # Continue visit


# --- Project Analyzer ---
class ProjectCodeAnalyzer:
    def __init__(self):
        self.project_index: Dict[Path, FileAnalysis] = {}
        # We will now create TWO indexes for lookups
        self.function_definitions: Dict[str, Tuple[Path, FunctionDefinition]] = {} # qname -> (path, def)
        self.function_callers: Dict[str, List[Tuple[Path, str]]] = {} # qname -> [(calling_file, calling_func)]

    def analyze_project(self, project_dir: Path, language_extensions: List[str] = None):
        """Analyzes all relevant files in a project directory."""
        if language_extensions is None:
            language_extensions = [".py"] # Default to Python

        print(f"Analyzing project at: {project_dir}")
        for ext in language_extensions:
            for file_path in project_dir.rglob(f"*{ext}"):
                if file_path.is_file():
                    self.analyze_file(file_path)
        
        self._build_indexes()
        print(f"Project analysis complete. Indexed {len(self.project_index)} files and built call graph.")

    def analyze_file(self, file_path: Path):
        """Parses a single Python file and stores its analysis."""
        if file_path in self.project_index: # Avoid re-analyzing
            return
        try:
            print(f"  Analyzing: {file_path.relative_to(file_path.parent.parent)}") # Assuming project_dir is parent of file_path.parent
            with open(file_path, 'r', encoding='utf-8') as f:
                source_code = f.read()
            tree = ast.parse(source_code, filename=str(file_path))
            
            visitor = PythonCodeVisitor(file_path, source_code)
            visitor.visit(tree)
            
            file_analysis_obj = FileAnalysis(file_path)
            file_analysis_obj.functions = visitor.definitions
            file_analysis_obj.imports = visitor.imports
            self.project_index[file_path] = file_analysis_obj
            
        except Exception as e:
            print(f"Error analyzing file {file_path}: {e}")

    def _get_qualified_name(self, file_path: Path, func_name: str, project_root: Path) -> str:
        """Helper to create a consistent fully qualified name for a function."""
        try:
            # Create a module-like path from the project root
            relative_path = file_path.relative_to(project_root)
            parts = list(relative_path.parts)
            if parts[-1].endswith('.py'):
                parts[-1] = parts[-1][:-3] # remove .py
            if parts[-1] == '__init__':
                parts.pop()
            return ".".join(parts) + f".{func_name}"
        except ValueError:
            # Fallback if not relative
            return func_name

    def _build_indexes(self):
        """Builds maps for fast lookups of function definitions and callers."""
        self.function_definitions = {}
        self.function_callers = {}
        
        # A bit of a guess for the project root, often the common parent
        # This part might need to be more robust in a real-world scenario
        all_paths = list(self.project_index.keys())
        if not all_paths: return
        project_root = Path(os.path.commonpath(all_paths))

        # First pass: Populate all function definitions
        for file_path, analysis in self.project_index.items():
            for func_name, func_def in analysis.functions.items():
                qname = self._get_qualified_name(file_path, func_name, project_root)
                self.function_definitions[qname] = (file_path, func_def)

        # Second pass: Populate the callers index (inverted call graph)
        for file_path, analysis in self.project_index.items():
            for func_name, func_def in analysis.functions.items():
                caller_qname = self._get_qualified_name(file_path, func_name, project_root)
                for call in func_def.calls:
                    # This is a simplification; resolving call.full_call_name to a qname is complex.
                    # For this example, we assume it matches a key in our definitions.
                    callee_qname = call.full_call_name # Heuristic
                    if callee_qname not in self.function_callers:
                        self.function_callers[callee_qname] = []
                    self.function_callers[callee_qname].append((file_path, caller_qname))


    def get_related_context_for_function(
        self,
        target_file_path: Path,
        target_function_name: str,
        max_callees_to_show=3,
        max_callers_to_show=2 # Callers are harder to resolve accurately
    ) -> Optional[str]:
        """
        Gets signatures and docstrings of functions called by target_function_name,
        and functions that call target_function_name.
        """
        if target_file_path not in self.project_index or \
           target_function_name not in self.project_index[target_file_path].functions:
            return None

        target_func_def = self.project_index[target_file_path].functions[target_function_name]
        target_file_analysis = self.project_index[target_file_path]
        
        context_parts = [f"Context for function `{target_function_name}` in `{target_file_path.name}`:"]

        # 1. Callees (functions called BY this function)
        if target_func_def.calls:
            context_parts.append("\n  Calls the following functions:")
            callee_count = 0
            unique_callees_shown: Set[str] = set()

            for call in target_func_def.calls:
                if callee_count >= max_callees_to_show:
                    context_parts.append("    ... and potentially others.")
                    break
                
                # Try to resolve the called function definition
                # Attempt 1: Direct import (e.g. from module import func_name)
                # Attempt 2: Module call (e.g. module.func_name)
                # Attempt 3: Local call within the same file
                
                # This is a simplified resolution logic
                # A real system would trace imports more rigorously
                resolved_callee_def: Optional[FunctionDefinition] = None
                resolved_callee_path: Optional[Path] = None

                # Check if call.full_call_name is in our project index (qualified or simple)
                if call.full_call_name in self.function_locations:
                    # Prefer definitions from explicitly imported modules if possible
                    # For now, take the first match (could be multiple if name is ambiguous)
                    loc_path, loc_func_name = self.function_locations[call.full_call_name][0]
                    if loc_path in self.project_index and loc_func_name in self.project_index[loc_path].functions:
                        resolved_callee_def = self.project_index[loc_path].functions[loc_func_name]
                        resolved_callee_path = loc_path
                elif call.func_name in target_file_analysis.functions: # local call in same file
                    resolved_callee_def = target_file_analysis.functions[call.func_name]
                    resolved_callee_path = target_file_path

                if resolved_callee_def and resolved_callee_def.name not in unique_callees_shown:
                    summary = resolved_callee_def.get_context_summary()
                    context_parts.append(f"    - `{call.full_call_name}` (defined in `{resolved_callee_path.name if resolved_callee_path else 'unknown'}`):\n      {summary.replace(chr(10), chr(10) + chr(32)*6)}") # Indent summary
                    unique_callees_shown.add(resolved_callee_def.name)
                    callee_count += 1
                elif call.full_call_name not in unique_callees_shown: # External or unresolved call
                    context_parts.append(f"    - Calls external/unresolved: `{call.full_call_name}` at L{call.line}")
                    unique_callees_shown.add(call.full_call_name) # To avoid repeating unresolved
                    # callee_count +=1 # Optionally count unresolved differently

        # 2. Callers (functions that call THIS function) - More complex to build accurately
        # For simplicity, we'll iterate through all functions in the project index
        # This is inefficient for large projects; a proper inverted call index is better.
        # For now, let's skip detailed caller context in this example to keep it simpler,
        # as accurate caller identification is harder with basic AST.
        # A more robust way would be to build an inverted index:
        # `callers_index: Dict[str (called_func_qname), List[Tuple[Path, str (caller_func_name)]]]`
        # For now, this section is omitted for brevity.

        if len(context_parts) == 1: # Only the initial context line
            return None # No relevant context found
            
        return "\n".join(context_parts)

    def get_context_for_file(self, file_path: Path, project_root: Path) -> str:
        """Generates the full context block for a single file to be prepended to the prompt."""
        if file_path not in self.project_index:
            return ""

        file_analysis = self.project_index[file_path]
        context_parts = [
            f"# --- Full Project Context for {file_path.relative_to(project_root).as_posix()} ---",
            "# This file defines the following functions:"
        ]

        # 1. List functions defined in THIS file and who calls them
        for func_name in sorted(file_analysis.functions.keys()):
            qname = self._get_qualified_name(file_path, func_name, project_root)
            context_parts.append(f"#   - Function: `{qname}`")
            if qname in self.function_callers:
                callers = self.function_callers[qname]
                context_parts.append(f"#     - Called By: {[c[1] for c in callers]}")
        
        context_parts.append("#\n# This file makes calls to the following functions defined elsewhere:")
        
        # 2. List functions called by THIS file and provide their definition summaries
        unique_callees_shown = set()
        for func_def in file_analysis.functions.values():
            for call in func_def.calls:
                callee_qname = call.full_call_name # Heuristic
                if callee_qname in self.function_definitions and callee_qname not in unique_callees_shown:
                    unique_callees_shown.add(callee_qname)
                    def_path, def_obj = self.function_definitions[callee_qname]
                    if def_path != file_path: # Only show context for functions in OTHER files
                        context_parts.append(f"#   - Function: `{callee_qname}` (defined in {def_path.relative_to(project_root).as_posix()})")
                        summary = def_obj.get_context_summary()
                        indented_summary = "      " + summary.replace("\n", "\n      ")
                        context_parts.append(indented_summary)

        context_parts.append("# --- End of Project Context ---")
        return "\n".join(context_parts)