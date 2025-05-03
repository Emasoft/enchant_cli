#!/usr/bin/env python3
"""
extract_functions.py - Extract functions from Bash script to separate files

This script takes the analysis output from bash_parser.py and extracts
functions into separate files based on their grouping.

Usage:
    python extract_functions.py <analysis_json> <source_file>

Example:
    python extract_functions.py dhtl.sh_analysis.json ../dhtl.sh
"""

import sys
import os
import json
from typing import Dict, List, Set, Any

def read_analysis(analysis_path: str) -> Dict[str, Any]:
    """Read the analysis JSON file"""
    try:
        with open(analysis_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error reading analysis file: {e}")
        sys.exit(1)

def read_source_file(source_path: str) -> List[str]:
    """Read the source file into lines"""
    try:
        with open(source_path, 'r') as f:
            return f.readlines()
    except Exception as e:
        print(f"Error reading source file: {e}")
        sys.exit(1)

def extract_function(source_lines: List[str], start_line: int, end_line: int) -> str:
    """Extract a function from source lines"""
    # Add 1 to end_line to include it
    return ''.join(source_lines[start_line:end_line+1])

def create_module_file(
    output_dir: str,
    module_name: str,
    functions: Dict[str, Any],
    function_names: List[str],
    source_lines: List[str]
) -> None:
    """Create a module file with the specified functions"""
    output_path = os.path.join(output_dir, f"dhtl_{module_name}.sh")
    
    # Generate file header
    header = f"""#!/bin/bash
# dhtl_{module_name}.sh - {module_name.capitalize()} module for DHT Launcher
#
# This file contains functions related to {module_name} functionality.
# It is sourced by the main dhtl.sh orchestrator.
#
# DO NOT execute this file directly.

"""
    
    # Sort function names to maintain consistent order
    function_names = sorted(function_names)
    
    # Extract functions
    function_contents = []
    for func_name in function_names:
        if func_name in functions:
            func_info = functions[func_name]
            func_content = extract_function(
                source_lines, 
                func_info["start_line"], 
                func_info["end_line"]
            )
            function_contents.append(func_content)
    
    # Write the module file
    with open(output_path, 'w') as f:
        f.write(header)
        f.write('\n\n'.join(function_contents))
    
    print(f"Created {output_path} with {len(function_names)} functions")

def create_orchestrator(
    output_dir: str,
    modules: List[str],
    source_lines: List[str]
) -> None:
    """Create the orchestrator script"""
    output_path = os.path.join(output_dir, "dhtl_new.sh")
    
    # Extract shebang and file header from original
    header_lines = []
    for line in source_lines:
        header_lines.append(line)
        if not line.startswith('#') and line.strip():
            break
    
    header = ''.join(header_lines)
    
    # Generate module imports
    imports = """
# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

# Import modules
"""
    
    for module in sorted(modules):
        imports += f'source "$SCRIPT_DIR/dhtl_{module}.sh"\n'
    
    # Generate main script
    main = """
# Process command line arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --help|-h)
            show_help
            exit 0
            ;;
        --version|-v)
            show_version
            exit 0
            ;;
        --no-guardian)
            DISABLE_GUARDIAN=1
            shift
            ;;
        --quiet)
            QUIET_MODE=1
            shift
            ;;
        *)
            # Command or unknown option
            COMMAND="$1"
            shift
            break
            ;;
    esac
done

# Initialize environment
dhtl_init_environment

# Process command
if [[ -z "$COMMAND" ]]; then
    echo "❌ Error: No command specified"
    show_help
    exit 1
fi

# Execute command
dhtl_execute_command "$COMMAND" "$@"

# Clean up
dhtl_cleanup
"""
    
    # Write the orchestrator file
    with open(output_path, 'w') as f:
        f.write(header)
        f.write(imports)
        f.write(main)
    
    print(f"Created orchestrator at {output_path}")

def main() -> None:
    """Main function"""
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <analysis_json> <source_file>")
        sys.exit(1)
    
    analysis_path = sys.argv[1]
    source_path = sys.argv[2]
    
    if not os.path.isfile(analysis_path):
        print(f"Error: Analysis file '{analysis_path}' not found.")
        sys.exit(1)
    
    if not os.path.isfile(source_path):
        print(f"Error: Source file '{source_path}' not found.")
        sys.exit(1)
    
    # Read the analysis and source file
    analysis = read_analysis(analysis_path)
    source_lines = read_source_file(source_path)
    
    # Create output directory
    output_dir = os.path.dirname(source_path)
    
    # Extract functions to module files
    for module_name, function_names in analysis["groups"].items():
        if function_names:
            create_module_file(
                output_dir,
                module_name,
                analysis["functions"],
                function_names,
                source_lines
            )
    
    # Create the orchestrator
    create_orchestrator(
        output_dir,
        list(analysis["groups"].keys()),
        source_lines
    )
    
    print("\nRefactoring complete. Next steps:")
    print("1. Review the generated files to ensure correctness")
    print("2. Test the refactored implementation")
    print("3. Rename dhtl_new.sh to dhtl.sh once verified")

if __name__ == "__main__":
    main()