#!/usr/bin/env python3
"""
Helper script to fix common issues in the publish_to_github.sh script.
This ensures the script runs correctly with the new --wait-for-logs option.
"""

import re
import sys
from pathlib import Path


def fix_workflow_script():
    """
    Fix common issues in the publish_to_github.sh script to ensure compatibility
    with the --wait-for-logs option and other enhancements.
    """
    script_path = Path('/Users/emanuelesabetta/Code/ENCHANT_BOOK_MANAGER/enchant_cli/publish_to_github.sh')
    
    # Ensure the script exists
    if not script_path.exists():
        print("Error: publish_to_github.sh not found", file=sys.stderr)
        return 1
    
    # Read the file content
    content = script_path.read_text()
    
    # Fix any missing elements in the script
    changes_made = 0
    
    # Ensure the --wait-for-logs flag is properly handled when invoked
    if "--wait-for-logs" in content and "get_errorlogs.sh latest" not in content:
        # Find the section where workflow logs are waited for
        wait_logs_section = re.search(r'# \*\*\* STEP 10: Wait for workflow logs.*?fi', content, re.DOTALL)
        
        if wait_logs_section:
            original_section = wait_logs_section.group(0)
            
            # Find the part where get_errorlogs.sh is called
            if "if \"$SCRIPT_DIR/get_errorlogs.sh\"" in original_section:
                enhanced_section = original_section.replace(
                    'if "$SCRIPT_DIR/get_errorlogs.sh"',
                    'if "$SCRIPT_DIR/get_errorlogs.sh" latest'
                )
                content = content.replace(original_section, enhanced_section)
                changes_made += 1
                print("Added 'latest' parameter to get_errorlogs.sh call")
    
    # Fix any exit calls that don't include an error code
    exit_calls = re.findall(r'print_error "[^"]+"\s+exit 1', content)
    exit_calls_fixed = 0
    
    for exit_call in exit_calls:
        if "print_error" in exit_call and "exit 1" in exit_call and '" 1' not in exit_call:
            new_exit_call = exit_call.replace('exit 1', '" 1\n            exit 1')
            content = content.replace(exit_call, new_exit_call)
            exit_calls_fixed += 1
    
    if exit_calls_fixed > 0:
        changes_made += exit_calls_fixed
        print(f"Fixed {exit_calls_fixed} exit calls to include error code in print_error")
    
    # Ensure UV_CMD variable is properly used throughout the script
    if "UV_CMD=" in content:
        # Find places where "uv" is used directly instead of $UV_CMD
        direct_uv_calls = re.findall(r'command -v uv.*?uv tool', content, re.DOTALL)
        
        for direct_call in direct_uv_calls:
            if "UV_CMD" not in direct_call and "command -v uv" in direct_call:
                # Replace only the command call, not the check
                fixed_call = direct_call.replace("uv tool", '"$UV_CMD" tool')
                content = content.replace(direct_call, fixed_call)
                changes_made += 1
                print("Fixed direct uv tool call to use UV_CMD variable")
    
    # For macOS compatibility in get_errorlogs.sh 
    fix_get_errorlogs_mac_compatibility()
    
    # Write the updated content back to the script if changes were made
    if changes_made > 0:
        script_path.write_text(content)
        print(f"Made {changes_made} fixes to {script_path}")
        return 0
    else:
        print(f"No issues found in {script_path}")
        return 0


def fix_get_errorlogs_mac_compatibility():
    """Fix macOS compatibility issues in get_errorlogs.sh"""
    script_path = Path("/Users/emanuelesabetta/Code/ENCHANT_BOOK_MANAGER/enchant_cli/get_errorlogs.sh")
    
    if not script_path.exists():
        print("Warning: get_errorlogs.sh not found", file=sys.stderr)
        return 1
    
    content = script_path.read_text()
    changes_made = 0
    
    # Fix 1: Replace readarray with a more portable approach if needed
    if "readarray -t" in content:
        # This pattern may need refinement based on the actual content
        readarray_pattern = r'readarray -t (\w+) < <\(([^)]+)\)'
        for match in re.finditer(readarray_pattern, content):
            var_name = match.group(1)
            command = match.group(2)
            
            replacement = f"""# Use a more portable approach instead of readarray
{var_name}=()
while IFS= read -r line; do
    {var_name}+=("$line")
done < <({command})"""
            
            content = content.replace(match.group(0), replacement)
            changes_made += 1
            print(f"Replaced readarray for {var_name} with a more portable while-loop approach")
    
    # Fix 2: Initialize variables before comparison to fix MacOS Bash issues
    display_function_pattern = r'# Function to display workflow summary.*?^\}'
    display_function_match = re.search(display_function_pattern, content, re.DOTALL | re.MULTILINE)
    
    if display_function_match and "recent_failure_count=${recent_failure_count:-0}" not in content:
        new_display_function = """
# Function to display workflow summary
display_workflow_summary() {
    echo ""
    echo -e "\\033[1;33m🔶 WORKFLOW SUMMARY 🔶\\033[0m"
    
    # Ensure variables are initialized
    recent_failure_count=${recent_failure_count:-0}
    recent_success_count=${recent_success_count:-0}
    all_runs_count=${all_runs_count:-0}
    
    if [ "$recent_failure_count" -gt 0 ]; then
        echo -e "\\033[1;31m❌ GITHUB JOBS SUMMARY: $recent_success_count/$all_runs_count WORKFLOWS COMPLETED SUCCESSFULLY, $recent_failure_count WITH ERRORS\\033[0m"
    else
        echo -e "\\033[1;32m✅ GITHUB JOBS COMPLETED SUCCESSFULLY\\033[0m"
    fi
}
"""
        content = content.replace(display_function_match.group(0), new_display_function.strip())
        changes_made += 1
        print("Fixed display_workflow_summary function to initialize variables for macOS compatibility")
    
    # Write the updated content back if changes were made
    if changes_made > 0:
        script_path.write_text(content)
        print(f"Made {changes_made} macOS compatibility fixes to get_errorlogs.sh")
    
    return 0


if __name__ == "__main__":
    sys.exit(fix_workflow_script())