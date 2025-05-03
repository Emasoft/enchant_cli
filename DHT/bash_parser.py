#!/usr/bin/env python3
"""
bash_parser.py - A script to parse Bash files using tree-sitter

This script demonstrates how to use tree-sitter to parse Bash scripts,
extract functions, and identify dependencies between them.

Usage:
    python bash_parser.py <bash_file>

Example:
    python bash_parser.py ../dhtl.sh
"""

import sys
import os
import json
from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass, field

try:
    from tree_sitter import Language, Parser
except ImportError:
    print("Error: tree-sitter module not found. Please install it with:")
    print("pip install tree-sitter")
    sys.exit(1)

@dataclass
class BashFunction:
    """Class representing a Bash function with its details"""
    name: str
    start_line: int
    end_line: int
    content: str
    called_functions: Set[str] = field(default_factory=set)
    size_bytes: int = 0
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            "name": self.name,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "size_bytes": self.size_bytes,
            "called_functions": list(self.called_functions)
        }

def build_bash_language() -> Optional[Language]:
    """Build or load the Bash language for tree-sitter"""
    try:
        # Check if we've already built the language
        if os.path.exists("./build/languages.so"):
            Language.build_library(
                "./build/languages.so",
                ["./tree-sitter-bash"]
            )
            return Language("./build/languages.so", "bash")
        
        # Try to find tree-sitter-bash in npm global modules
        npm_modules = os.path.expanduser("~/.npm-global/lib/node_modules")
        if os.path.exists(os.path.join(npm_modules, "tree-sitter-bash")):
            Language.build_library(
                "./build/languages.so",
                [os.path.join(npm_modules, "tree-sitter-bash")]
            )
            return Language("./build/languages.so", "bash")
        
        print("Error: tree-sitter-bash grammar not found.")
        print("Please install it with: npm install -g tree-sitter-bash")
        return None
    except Exception as e:
        print(f"Error building Bash language: {e}")
        return None

def parse_bash_file(file_path: str) -> Tuple[Dict[str, BashFunction], List[str]]:
    """
    Parse a Bash file and extract functions and their relationships
    
    Args:
        file_path: Path to the Bash file
        
    Returns:
        Tuple containing:
            - Dictionary of function name -> BashFunction object
            - List of lines in the file
    """
    # Load the Bash language
    bash = build_bash_language()
    if not bash:
        return {}, []
    
    # Create parser
    parser = Parser()
    parser.set_language(bash)
    
    # Read the file
    with open(file_path, 'r', encoding='utf-8') as f:
        source_code = f.read()
        lines = source_code.split('\n')
    
    # Parse the file
    tree = parser.parse(bytes(source_code, 'utf8'))
    
    # Extract functions
    functions: Dict[str, BashFunction] = {}
    
    # Query to find function definitions
    function_query = bash.query("""
        (function_definition
          name: (word) @function_name
          body: (compound_statement) @function_body)
    """)
    
    # Query to find function calls
    function_call_query = bash.query("""
        (command_name) @function_call
    """)
    
    # Extract functions
    for match in function_query.captures(tree.root_node):
        node = match[0]
        if match[1] == 'function_name':
            function_name = node.text.decode('utf-8')
            function_body_node = None
            
            # Find corresponding function body
            for body_match in function_query.captures(tree.root_node):
                if body_match[1] == 'function_body' and body_match[0].start_point[0] > node.start_point[0]:
                    function_body_node = body_match[0]
                    break
            
            if function_body_node:
                start_line = node.start_point[0]
                end_line = function_body_node.end_point[0]
                
                # Extract function content
                function_content = '\n'.join(lines[start_line:end_line+1])
                function_size = len(function_content.encode('utf-8'))
                
                # Create function object
                func = BashFunction(
                    name=function_name,
                    start_line=start_line,
                    end_line=end_line,
                    content=function_content,
                    size_bytes=function_size
                )
                
                functions[function_name] = func
    
    # Find function calls within each function
    for func_name, func in functions.items():
        # Get the function node
        function_node = None
        for node in tree.root_node.children:
            if node.type == 'function_definition' and node.start_point[0] == func.start_line:
                function_node = node
                break
        
        if function_node:
            # Find all command names within this function
            for match in function_call_query.captures(function_node):
                call_name = match[0].text.decode('utf-8')
                
                # Check if this is a call to another function
                if call_name in functions and call_name != func_name:
                    func.called_functions.add(call_name)
    
    return functions, lines

def analyze_dependencies(functions: Dict[str, BashFunction]) -> Dict[str, Set[str]]:
    """
    Analyze function dependencies (which functions depend on a given function)
    
    Args:
        functions: Dictionary of function name -> BashFunction
        
    Returns:
        Dictionary of function name -> set of functions that depend on it
    """
    dependencies: Dict[str, Set[str]] = {name: set() for name in functions}
    
    # Build dependency graph
    for func_name, func in functions.items():
        for called_func in func.called_functions:
            if called_func in dependencies:
                dependencies[called_func].add(func_name)
    
    return dependencies

def suggest_function_groups(functions: Dict[str, BashFunction], dependencies: Dict[str, Set[str]]) -> Dict[str, List[str]]:
    """
    Suggest logical grouping of functions based on dependencies and naming patterns
    
    Args:
        functions: Dictionary of function name -> BashFunction
        dependencies: Dictionary of function name -> set of functions that depend on it
        
    Returns:
        Dictionary of group name -> list of function names
    """
    groups = {
        "environment": [],
        "guardian": [],
        "commands": [],
        "utils": [],
        "platform": [],
        "help": []
    }
    
    # Analyze function names and dependencies for grouping
    for func_name in functions:
        if any(x in func_name for x in ["env", "setup", "detect", "path"]):
            groups["environment"].append(func_name)
        elif any(x in func_name for x in ["guardian", "process", "monitor", "resources"]):
            groups["guardian"].append(func_name)
        elif any(x in func_name for x in ["command", "cmd", "exec", "run"]):
            groups["commands"].append(func_name)
        elif any(x in func_name for x in ["platform", "os", "windows", "linux", "macos"]):
            groups["platform"].append(func_name)
        elif any(x in func_name for x in ["help", "usage", "doc", "print", "show"]):
            groups["help"].append(func_name)
        else:
            groups["utils"].append(func_name)
    
    return groups

def extract_function_with_context(file_lines: List[str], func: BashFunction) -> str:
    """
    Extract a function with appropriate context (preserving loops/conditionals that might span it)
    
    Args:
        file_lines: List of lines in the file
        func: BashFunction object
        
    Returns:
        String containing the function with necessary context
    """
    # Simple implementation - just extract the function as-is
    # A more sophisticated implementation would analyze surrounding blocks
    return func.content

def main() -> None:
    """Main function"""
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <bash_file>")
        sys.exit(1)
    
    file_path = sys.argv[1]
    if not os.path.isfile(file_path):
        print(f"Error: File '{file_path}' not found.")
        sys.exit(1)
    
    # Parse the Bash file
    functions, lines = parse_bash_file(file_path)
    
    if not functions:
        print("No functions found or error parsing file.")
        sys.exit(1)
    
    print(f"Found {len(functions)} functions in {file_path}")
    
    # Analyze dependencies
    dependencies = analyze_dependencies(functions)
    
    # Suggest groupings
    groups = suggest_function_groups(functions, dependencies)
    
    # Print results
    for group_name, func_names in groups.items():
        if func_names:
            print(f"\n{group_name.upper()} GROUP ({len(func_names)} functions):")
            for func_name in sorted(func_names):
                func = functions[func_name]
                size_kb = func.size_bytes / 1024
                deps = len(func.called_functions)
                print(f"  {func_name} (L{func.start_line}-{func.end_line}, {size_kb:.2f}KB, calls {deps} functions)")
    
    # Generate detailed report
    report = {
        "file": file_path,
        "total_functions": len(functions),
        "functions": {name: func.to_dict() for name, func in functions.items()},
        "dependencies": {name: list(deps) for name, deps in dependencies.items()},
        "groups": groups
    }
    
    # Save report
    output_path = f"{os.path.basename(file_path)}_analysis.json"
    with open(output_path, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\nDetailed analysis saved to {output_path}")
    
    # Suggest next steps
    print("\nSuggested Next Steps:")
    print("1. Review the function groups and adjust if needed")
    print("2. Extract functions to separate files according to grouping")
    print("3. Create orchestrator script that sources these files")
    print("4. Test the refactored implementation")

if __name__ == "__main__":
    main()