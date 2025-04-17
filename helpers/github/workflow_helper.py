#!/usr/bin/env python3
"""
GitHub workflow management and analysis utilities.

This module provides functions to:
- Detect, fix, and enhance GitHub workflow files
- Fix shell script issues related to workflow triggering
- Validate workflow YAML files
- Check for workflow_dispatch events
- Manage GitHub authentication and repository configuration

Usage:
    python -m helpers.github.workflow_helper --fix-scripts  # Fix script issues
    python -m helpers.github.workflow_helper --check        # Validate workflows
"""

import argparse
import re
import sys
from pathlib import Path


def fix_workflow_script(script_path=None):
    """
    Fix common issues in GitHub workflow scripts to ensure proper functionality.
    
    Args:
        script_path: Path to the script to fix (defaults to publish_to_github.sh)
        
    Returns:
        int: 0 on success, 1 on failure
    """
    if script_path is None:
        # Default to publish_to_github.sh in the current working directory
        cwd = Path.cwd()
        script_path = cwd / "publish_to_github.sh"
    elif isinstance(script_path, str):
        script_path = Path(script_path)
    
    # Ensure the script exists
    if not script_path.exists():
        print(f"Error: Script not found at {script_path}", file=sys.stderr)
        return 1
    
    # Read the file content
    try:
        content = script_path.read_text()
    except Exception as e:
        print(f"Error reading script: {e}", file=sys.stderr)
        return 1
    
    # Track changes made
    changes_made = 0
    
    # ===== FIX 1: Ensure the --wait-for-logs flag is properly implemented =====
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
    
    # ===== FIX 2: Fix exit calls to include error codes =====
    exit_calls = re.findall(r'print_error "[^"]+"\s+exit 1', content)
    exit_calls_fixed = 0
    
    for exit_call in exit_calls:
        if "print_error" in exit_call and "exit 1" in exit_call and '" 1' not in exit_call:
            new_exit_call = exit_call.replace('exit 1', '" 1\n    exit 1')
            content = content.replace(exit_call, new_exit_call)
            exit_calls_fixed += 1
    
    if exit_calls_fixed > 0:
        changes_made += exit_calls_fixed
        print(f"Fixed {exit_calls_fixed} exit calls to include error code in print_error")
    
    # ===== FIX 3: Ensure UV_CMD variable is properly used throughout the script =====
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
    
    # ===== FIX 4: Fix bump-my-version usage to follow best practices =====
    if "bump-my-version" in content:
        # Ensure all calls go through uv tool run
        global_calls = re.findall(r'bump-my-version\s+bump', content)
        for call in global_calls:
            if not re.search(r'\$UV_CMD tool run bump-my-version', content):
                fixed_call = '"$UV_CMD" tool run ' + call
                content = content.replace(call, fixed_call)
                changes_made += 1
                print("Fixed bump-my-version call to use UV_CMD tool run")
        
        # Fix direct installation calls
        pip_install_calls = re.findall(r'pip install bump-my-version', content)
        for call in pip_install_calls:
            fixed_call = 'uv tool install bump-my-version'
            content = content.replace(call, fixed_call)
            changes_made += 1
            print("Fixed pip install to use uv tool install for bump-my-version")
    
    # Write the updated content back to the script if changes were made
    if changes_made > 0:
        try:
            script_path.write_text(content)
            print(f"Made {changes_made} fixes to {script_path}")
            return 0
        except Exception as e:
            print(f"Error writing changes to script: {e}", file=sys.stderr)
            return 1
    else:
        print(f"No issues found in {script_path}")
        return 0


def fix_shell_compatibility(script_path=None):
    """
    Fix compatibility issues in shell scripts to ensure they work across platforms.
    
    Args:
        script_path: Path to the script to fix (defaults to get_errorlogs.sh)
        
    Returns:
        int: 0 on success, 1 on failure
    """
    if script_path is None:
        # Default to get_errorlogs.sh in the current working directory
        cwd = Path.cwd()
        script_path = cwd / "get_errorlogs.sh"
    elif isinstance(script_path, str):
        script_path = Path(script_path)
    
    # Ensure the script exists
    if not script_path.exists():
        print(f"Error: Script not found at {script_path}", file=sys.stderr)
        return 1
    
    # Read the file content
    try:
        content = script_path.read_text()
    except Exception as e:
        print(f"Error reading script: {e}", file=sys.stderr)
        return 1
    
    # Track changes made
    changes_made = 0
    
    # ===== FIX 1: Replace readarray with a more portable approach =====
    if "readarray -t" in content:
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
    
    # ===== FIX 2: Initialize variables before comparison (macOS Bash issues) =====
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
    
    # ===== FIX 3: Add PYTHON_CMD detection for cross-platform compatibility =====
    python_cmd_check = """
# Detect and validate Python interpreter
print_info "Detecting Python interpreter..."
if command -v python3 &>/dev/null; then
    PYTHON_CMD="python3"
elif command -v python &>/dev/null; then
    PYTHON_CMD="python"
else
    print_warning "No Python interpreter found. Enhanced analysis will not be available."
fi

# Verify Python version
if [ -n "$PYTHON_CMD" ]; then
    PY_VERSION=$($PYTHON_CMD --version 2>&1)
    print_success "Using Python: $PY_VERSION"
fi
"""
    
    if "PYTHON_CMD=" not in content:
        script_start_pattern = r'#=========================================================================\n# MAIN SCRIPT EXECUTION.*?#========================================================================='
        script_start_match = re.search(script_start_pattern, content, re.DOTALL)
        
        if script_start_match and "Detecting Python interpreter" not in content:
            content = content.replace(script_start_match.group(0), script_start_match.group(0) + python_cmd_check)
            changes_made += 1
            print("Added Python interpreter detection for cross-platform compatibility")
    
    # Write the updated content back to the script if changes were made
    if changes_made > 0:
        try:
            script_path.write_text(content)
            print(f"Made {changes_made} cross-platform compatibility fixes to {script_path}")
            return 0
        except Exception as e:
            print(f"Error writing changes to script: {e}", file=sys.stderr)
            return 1
    else:
        print(f"No compatibility issues found in {script_path}")
        return 0


def check_workflow_dispatch(workflow_path=None):
    """
    Check if workflow files have workflow_dispatch event triggers.
    
    Args:
        workflow_path: Path to the GitHub Actions workflow directory
        
    Returns:
        int: 0 on success, 1 on failure
    """
    if workflow_path is None:
        # Default to .github/workflows in the current working directory
        cwd = Path.cwd()
        workflow_path = cwd / ".github" / "workflows"
    elif isinstance(workflow_path, str):
        workflow_path = Path(workflow_path)
    
    # Ensure the directory exists
    if not workflow_path.exists() or not workflow_path.is_dir():
        print(f"Error: Workflow directory not found at {workflow_path}", file=sys.stderr)
        return 1
    
    # Find all workflow files
    workflow_files = list(workflow_path.glob("*.yml")) + list(workflow_path.glob("*.yaml"))
    
    if not workflow_files:
        print(f"No workflow files found in {workflow_path}", file=sys.stderr)
        return 1
    
    # Check each workflow file for workflow_dispatch event
    issues_found = 0
    fixes_needed = []
    
    for wf_file in workflow_files:
        try:
            content = wf_file.read_text()
            
            # Check if file has workflow_dispatch event
            if "on:" in content and "workflow_dispatch:" not in content:
                print(f"WARNING: {wf_file.name} does not have workflow_dispatch event")
                issues_found += 1
                fixes_needed.append(wf_file)
        except Exception as e:
            print(f"Error reading {wf_file}: {e}", file=sys.stderr)
            issues_found += 1
    
    # Report results
    if issues_found == 0:
        print(f"✅ All {len(workflow_files)} workflow files have workflow_dispatch event")
        return 0
    else:
        print(f"⚠️ {issues_found} of {len(workflow_files)} workflow files need workflow_dispatch event added")
        print("\nTo fix, add the following to each 'on:' section:")
        print("  workflow_dispatch:")
        print("\nAffected files:")
        for file in fixes_needed:
            print(f"  - {file.name}")
        return 1


def fix_workflow_dispatch(workflow_path=None, dry_run=False):
    """
    Add workflow_dispatch event to workflow files that don't have it.
    
    Args:
        workflow_path: Path to the GitHub Actions workflow directory
        dry_run: If True, only report issues without fixing
        
    Returns:
        int: 0 on success, 1 on failure
    """
    if workflow_path is None:
        # Default to .github/workflows in the current working directory
        cwd = Path.cwd()
        workflow_path = cwd / ".github" / "workflows"
    elif isinstance(workflow_path, str):
        workflow_path = Path(workflow_path)
    
    # Ensure the directory exists
    if not workflow_path.exists() or not workflow_path.is_dir():
        print(f"Error: Workflow directory not found at {workflow_path}", file=sys.stderr)
        return 1
    
    # Find all workflow files
    workflow_files = list(workflow_path.glob("*.yml")) + list(workflow_path.glob("*.yaml"))
    
    if not workflow_files:
        print(f"No workflow files found in {workflow_path}", file=sys.stderr)
        return 1
    
    # Check and potentially fix each workflow file
    files_fixed = 0
    
    for wf_file in workflow_files:
        try:
            content = wf_file.read_text()
            
            # Check if file has workflow_dispatch event
            if "on:" in content and "workflow_dispatch:" not in content:
                # Detect the on: section format and insert workflow_dispatch
                on_section_match = re.search(r'on:\s*(#[^\n]*)?(\n\s*)', content)
                
                if on_section_match:
                    # Handle the case where 'on:' is followed by key-value pairs on next line
                    indentation = on_section_match.group(2)
                    if re.search(r'on:\s*(#[^\n]*)?\n\s+\w+:', content):
                        # Add workflow_dispatch at the same indentation level as other events
                        new_content = content.replace(
                            on_section_match.group(0),
                            on_section_match.group(0) + "  workflow_dispatch:" + indentation
                        )
                    else:
                        # Handle the case where 'on:' is followed by a list
                        new_content = content.replace(
                            on_section_match.group(0),
                            on_section_match.group(0) + "  - workflow_dispatch" + indentation
                        )
                    
                    if dry_run:
                        print(f"Would fix: {wf_file.name} (add workflow_dispatch event)")
                    else:
                        wf_file.write_text(new_content)
                        print(f"Fixed: {wf_file.name} (added workflow_dispatch event)")
                        files_fixed += 1
                else:
                    print(f"Could not fix: {wf_file.name} (on: section format not recognized)")
        except Exception as e:
            print(f"Error processing {wf_file}: {e}", file=sys.stderr)
    
    # Report results
    if dry_run:
        print(f"Dry run completed. {files_fixed} files would be fixed.")
    else:
        print(f"Fix completed. {files_fixed} files were fixed.")
    
    return 0


def main():
    parser = argparse.ArgumentParser(description="GitHub workflow management utilities")
    parser.add_argument("--fix-workflow-script", action="store_true", help="Fix publish_to_github.sh")
    parser.add_argument("--fix-shell-compat", action="store_true", help="Fix shell script compatibility issues")
    parser.add_argument("--check-workflow-dispatch", action="store_true", help="Check for workflow_dispatch event")
    parser.add_argument("--fix-workflow-dispatch", action="store_true", help="Add workflow_dispatch to workflows")
    parser.add_argument("--path", help="Path to the script or directory to process")
    parser.add_argument("--dry-run", action="store_true", help="Report issues but don't fix them")
    
    args = parser.parse_args()
    
    # If no specific action is requested, show help
    if not (args.fix_workflow_script or args.fix_shell_compat or 
            args.check_workflow_dispatch or args.fix_workflow_dispatch):
        parser.print_help()
        return 0
    
    # Process each requested action
    exit_code = 0
    
    if args.fix_workflow_script:
        result = fix_workflow_script(args.path)
        if result != 0:
            exit_code = result
    
    if args.fix_shell_compat:
        result = fix_shell_compatibility(args.path)
        if result != 0:
            exit_code = result
    
    if args.check_workflow_dispatch:
        result = check_workflow_dispatch(args.path)
        if result != 0:
            exit_code = result
    
    if args.fix_workflow_dispatch:
        result = fix_workflow_dispatch(args.path, args.dry_run)
        if result != 0:
            exit_code = result
    
    return exit_code


if __name__ == "__main__":
    sys.exit(main())