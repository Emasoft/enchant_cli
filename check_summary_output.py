#!/usr/bin/env python3
"""
Create a final script to check and fix the full output of get_errorlogs.sh
"""

from pathlib import Path
import re


def fix_full_output():
    # Path to the script
    script_path = Path('/Users/emanuelesabetta/Code/ENCHANT_BOOK_MANAGER/enchant_cli/get_errorlogs.sh')
    
    # Read the file content
    content = script_path.read_text()
    
    # Fix the no-arguments handler
    if_block_pattern = r'if \[ \$# -eq 0 \]; then.*?print_warning "Found \$yaml_errors workflow files with YAML syntax errors".*?recent_failure_count=\$\(\(recent_failure_count \+ yaml_errors\)\))'
    
    # Define a function for replacement
    def if_block_replacement(match):
        return match.group(0) + '\n    # Show the summary\n    display_workflow_summary\n    exit 0'
    
    content = re.sub(if_block_pattern, if_block_replacement, content, flags=re.DOTALL)
    
    # Remove any duplicated summary at the end of the script
    end_script_pattern = r'# No summary at the end.*exit 0'
    content = re.sub(end_script_pattern, 'exit 0', content, flags=re.DOTALL)
    
    # Write the updated content back to the script
    script_path.write_text(content)
    
    return "Fixed final output to show the summary correctly"


if __name__ == "__main__":
    result = fix_full_output()
    print(result)