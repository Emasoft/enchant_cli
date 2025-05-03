#!/usr/bin/env python3
"""
Shell script analysis and fixing utilities.

This module provides functions to:
- Fix common shell script issues
- Ensure proper error handling
- Standardize script formats
- Improve cross-platform compatibility
- Detect common vulnerabilities
- Set up bump-my-version with proper uv integration

Usage:
    python -m helpers.shell.script_fixer --check <script.sh>
    python -m helpers.shell.script_fixer --fix <script.sh>
    python -m helpers.shell.script_fixer --setup-bumpversion [--no-uv] [--force]
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


def check_script_with_shellcheck(script_path):
    """
    Check a shell script with shellcheck to identify issues.
    
    Args:
        script_path: Path to the shell script
        
    Returns:
        tuple: (success, issues) - where issues is a list of identified problems
    """
    if not Path(script_path).exists():
        return False, ["Script file not found"]
    
    issues = []
    
    try:
        result = subprocess.run(
            ["shellcheck", "--format=json", script_path], 
            capture_output=True, 
            text=True
        )
        
        if result.returncode != 0:
            import json
            try:
                shellcheck_issues = json.loads(result.stdout)
                for issue in shellcheck_issues:
                    line_num = issue.get("line", "?")
                    level = issue.get("level", "?")
                    message = issue.get("message", "Unknown issue")
                    code = issue.get("code", "?")
                    issues.append(f"Line {line_num} [{level}] {message} (SC{code})")
            except json.JSONDecodeError:
                issues.append("Failed to parse shellcheck output")
        return result.returncode == 0, issues
    except FileNotFoundError:
        issues.append("shellcheck not installed - please install shellcheck")
        return False, issues


def ensure_script_has_set_e(script_path):
    """
    Ensure the script has set -e or equivalent error handling.
    
    Args:
        script_path: Path to the shell script
        
    Returns:
        tuple: (needs_fix, fixed_content) - whether fix is needed and fixed content if so
    """
    try:
        with open(script_path, 'r') as f:
            content = f.read()
            
        # Check for various forms of set -e
        has_set_e = re.search(r'set\s+-e', content) is not None
        has_set_eo = re.search(r'set\s+-eo', content) is not None
        has_set_eu = re.search(r'set\s+-eu', content) is not None
        
        if has_set_e or has_set_eo or has_set_eu:
            return False, content
            
        # Add set -eo pipefail after the shebang line
        shebang_match = re.search(r'^(#!.+)\n', content)
        if shebang_match:
            fixed_content = re.sub(
                r'^(#!.+)\n',
                r'\1\nset -eo pipefail\n\n',
                content
            )
        else:
            fixed_content = "#!/bin/bash\nset -eo pipefail\n\n" + content
            
        return True, fixed_content
    except Exception as e:
        print(f"Error ensuring set -e: {e}", file=sys.stderr)
        return False, None


def ensure_script_has_error_handling(script_path):
    """
    Ensure the script has proper error handling.
    
    Args:
        script_path: Path to the shell script
        
    Returns:
        tuple: (needs_fix, fixed_content) - whether fix is needed and fixed content if so
    """
    try:
        with open(script_path, 'r') as f:
            content = f.read()
            
        # Check for print_error function
        has_print_error = re.search(r'print_error\s*\(\)', content) is not None
        
        if has_print_error:
            # Check if print_error has exit handling
            print_error_func = re.search(r'print_error\s*\(\)\s*\{[^}]*\}', content)
            if print_error_func:
                func_body = print_error_func.group(0)
                has_exit_handling = re.search(r'exit\s+"\$', func_body) is not None
                
                if has_exit_handling:
                    return False, content
                    
                # Fix print_error function to include exit handling
                fixed_func = re.sub(
                    r'(print_error\s*\(\)\s*\{[^}]*)(})',
                    r'\1    # If error code provided as second parameter, exit with it\n    if [ -n "$2" ]; then\n        exit "$2"\n    fi\n\2',
                    func_body
                )
                fixed_content = content.replace(func_body, fixed_func)
                return True, fixed_content
            
        # If no print_error function, add a comprehensive one
        if not has_print_error:
            # Standard error handling function
            error_function = """
# Print error message and optionally exit
print_error() {
    printf "${RED}❌ %s${NC}\\n" "$1"
    # If error code provided as second parameter, exit with it
    if [ -n "$2" ]; then
        exit "$2"
    fi
}
"""
            
            # Find a good place to add the function
            # Look for other print functions first
            print_func_block = re.search(r'print_\w+\s*\(\)\s*\{[^}]*\}', content)
            if print_func_block:
                last_print_func = re.findall(r'(print_\w+\s*\(\)\s*\{[^}]*\})', content)[-1]
                fixed_content = content.replace(last_print_func, last_print_func + "\n" + error_function)
            elif "# Print " in content:
                fixed_content = re.sub(r'(# Print [^\n]+\n[^\n]+\n)', r'\1' + error_function, content)
            else:
                # Add after color definitions if they exist
                color_def = re.search(r'(?:RED|GREEN|YELLOW|BLUE|NC)=', content)
                if color_def:
                    # Find the block of color definitions
                    color_block = re.search(r'.*(?:RED|GREEN|YELLOW|BLUE|NC)=[^\n]+(?:\n[^\n]*=[^\n]+)*', content)
                    if color_block:
                        block_end = color_block.end()
                        fixed_content = content[:block_end] + "\n\n" + error_function + content[block_end:]
                    else:
                        fixed_content = content + "\n\n" + error_function
                else:
                    # Add standard color definitions and error function
                    color_definitions = """
# ANSI color codes
RED='\\033[0;31m'
GREEN='\\033[0;32m'
YELLOW='\\033[0;33m'
BLUE='\\033[0;34m'
NC='\\033[0m' # No Color
"""
                    fixed_content = content + "\n\n" + color_definitions + error_function
            
            return True, fixed_content
        
        return False, content
    except Exception as e:
        print(f"Error ensuring error handling: {e}", file=sys.stderr)
        return False, None


def fix_common_script_issues(script_path):
    """
    Fix common issues in shell scripts.
    
    Args:
        script_path: Path to the shell script
        
    Returns:
        bool: True if fixes were applied, False otherwise
    """
    path = Path(script_path)
    if not path.exists():
        print(f"Error: Script {script_path} not found", file=sys.stderr)
        return False
    
    fixes_applied = False
    
    # Apply each fix function
    needs_set_e, fixed_content = ensure_script_has_set_e(script_path)
    if needs_set_e and fixed_content:
        with open(script_path, 'w') as f:
            f.write(fixed_content)
        print(f"Added 'set -eo pipefail' to {script_path}")
        fixes_applied = True
    
    needs_error_handling, fixed_content = ensure_script_has_error_handling(script_path)
    if needs_error_handling and fixed_content:
        with open(script_path, 'w') as f:
            f.write(fixed_content)
        print(f"Added/fixed error handling in {script_path}")
        fixes_applied = True
    
    # Run shellcheck to find other issues
    success, issues = check_script_with_shellcheck(script_path)
    if not success:
        print("shellcheck found issues:")
        for issue in issues:
            print(f"  - {issue}")
        # Note: We don't auto-fix shellcheck issues as they need careful consideration
    
    return fixes_applied


def check_script_quality(script_path):
    """
    Check the quality of a shell script and report issues.
    
    Args:
        script_path: Path to the shell script
        
    Returns:
        int: Number of issues found
    """
    if not Path(script_path).exists():
        print(f"Error: Script {script_path} not found", file=sys.stderr)
        return 1
    
    issues_found = 0
    
    # Check for error handling
    needs_set_e, _ = ensure_script_has_set_e(script_path)
    if needs_set_e:
        print(f"Warning: {script_path} does not use 'set -e' or equivalent for error handling")
        issues_found += 1
    
    needs_error_handling, _ = ensure_script_has_error_handling(script_path)
    if needs_error_handling:
        print(f"Warning: {script_path} does not have proper error reporting with print_error function")
        issues_found += 1
    
    # Run shellcheck
    success, shellcheck_issues = check_script_with_shellcheck(script_path)
    if not success:
        issues_found += len(shellcheck_issues)
        print(f"shellcheck found {len(shellcheck_issues)} issues in {script_path}")
        for issue in shellcheck_issues[:5]:  # Show only the first 5 issues
            print(f"  - {issue}")
        if len(shellcheck_issues) > 5:
            print(f"  ... and {len(shellcheck_issues) - 5} more issues")
    
    # Check for script size
    try:
        with open(script_path, 'r') as f:
            lines = f.readlines()
            line_count = len(lines)
            if line_count > 500:
                print(f"Warning: {script_path} is very large ({line_count} lines). Consider splitting into modules.")
                issues_found += 1
            elif line_count > 300:
                print(f"Note: {script_path} is quite large ({line_count} lines). Consider refactoring.")
    except Exception as e:
        print(f"Error checking script size: {e}", file=sys.stderr)
    
    return issues_found


def extract_bash_functions(script_path):
    """
    Extract function names and their definitions from a bash script.
    
    Args:
        script_path: Path to the shell script
        
    Returns:
        dict: Function names mapped to their contents
    """
    try:
        with open(script_path, 'r') as f:
            content = f.read()
            
        functions = {}
        # Match function declarations like "function_name() {" or "function function_name {"
        function_matches = re.finditer(r'(?:function\s+)?(\w+)\s*\(\)\s*\{', content)
        
        for match in function_matches:
            func_name = match.group(1)
            start_pos = match.start()
            
            # Find closing brace with proper nesting
            bracket_level = 0
            end_pos = start_pos
            
            for i in range(start_pos, len(content)):
                if content[i] == '{':
                    bracket_level += 1
                elif content[i] == '}':
                    bracket_level -= 1
                    if bracket_level == 0:
                        end_pos = i + 1
                        break
            
            if end_pos > start_pos:
                functions[func_name] = content[start_pos:end_pos]
        
        return functions
    except Exception as e:
        print(f"Error extracting functions: {e}", file=sys.stderr)
        return {}


def find_duplicate_functions(scripts):
    """
    Find duplicated functions across shell scripts.
    
    Args:
        scripts: List of paths to shell scripts
        
    Returns:
        dict: Duplicated function names mapped to script paths
    """
    all_functions = {}  # Function name -> [(script_path, function_content), ...]
    
    for script in scripts:
        if not Path(script).exists():
            continue
            
        functions = extract_bash_functions(script)
        for func_name, func_content in functions.items():
            if func_name not in all_functions:
                all_functions[func_name] = []
            all_functions[func_name].append((script, func_content))
    
    # Find duplicates
    duplicated = {}
    for func_name, occurrences in all_functions.items():
        if len(occurrences) > 1:
            # Check if the function content is the same
            distinct_contents = set(content for _, content in occurrences)
            if len(distinct_contents) == 1:
                # Exact duplicates
                duplicated[func_name] = [script for script, _ in occurrences]
    
    return duplicated


def install_bump_my_version(use_uv=True, force=False):
    """
    Install bump-my-version using uv or pip, following best practices.
    
    Args:
        use_uv (bool): Whether to use uv tool run for installation
        force (bool): Force reinstall even if already installed
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        print("Checking for bump-my-version installation...")
        
        # Check if bump-my-version is already installed and we're not forcing reinstall
        if not force:
            # Try uv tool list first
            if use_uv:
                try:
                    result = subprocess.run(
                        ["uv", "tool", "list"],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        universal_newlines=True
                    )
                    if "bump-my-version" in result.stdout:
                        print("bump-my-version is already installed via uv")
                        return True
                except Exception:
                    pass
            
            # Try checking directly
            try:
                result = subprocess.run(
                    ["bump-my-version", "--version"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                if result.returncode == 0:
                    print("bump-my-version is already installed")
                    return True
            except Exception:
                # Not found or not in PATH, continue with installation
                pass
        
        # Try to install with uv (preferred method)
        if use_uv:
            print("Installing bump-my-version using uv tool...")
            try:
                result = subprocess.run(
                    ["uv", "tool", "install", "bump-my-version"],
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                if result.returncode == 0:
                    print("Successfully installed bump-my-version using uv tool")
                    return True
            except subprocess.CalledProcessError as e:
                print(f"Error installing with uv tool: {e.stderr.decode()}")
                print("Falling back to alternative installation methods...")
            except FileNotFoundError:
                print("uv not found in PATH, falling back to alternative installation methods...")
        
        # First fallback: Try with uv pip in current environment
        print("Trying to install bump-my-version using uv pip...")
        try:
            result = subprocess.run(
                [sys.executable, "-m", "uv", "pip", "install", "bump-my-version"],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            if result.returncode == 0:
                print("Successfully installed bump-my-version using uv pip")
                return True
        except subprocess.CalledProcessError as e:
            print(f"Error installing with uv pip: {e.stderr.decode()}")
        
        # Second fallback: regular pip (less preferred)
        print("Trying to install bump-my-version using pip...")
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "bump-my-version"],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            if result.returncode == 0:
                print("Successfully installed bump-my-version using pip")
                return True
        except subprocess.CalledProcessError as e:
            print(f"Error installing with pip: {e.stderr.decode()}")
        
        # Last fallback: pipx if available (not preferred due to isolation issues)
        print("Trying to install bump-my-version using pipx...")
        try:
            result = subprocess.run(
                ["pipx", "install", "bump-my-version"],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            if result.returncode == 0:
                print("Successfully installed bump-my-version using pipx")
                return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            # pipx not available or failed, final fallback
            pass
        
        print("Failed to install bump-my-version using available methods")
        print("Please install manually with one of these commands:")
        print("  uv tool install bump-my-version")
        print("  pip install bump-my-version")
        print("  pipx install bump-my-version")
        return False
    except Exception as e:
        print(f"Unexpected error installing bump-my-version: {str(e)}")
        return False


def create_bumpversion_config(force=False):
    """
    Create or update a proper .bumpversion.toml configuration file.
    
    This follows best practices from the blog post and README to:
    - Use the correct configuration structure
    - Configure pre-commit hooks for uv sync
    - Include additional git add for lock files
    - Set appropriate flags for bump-my-version
    
    Args:
        force (bool): Whether to overwrite existing configuration
        
    Returns:
        bool: True if successful, False otherwise
    """
    config_file = Path(".bumpversion.toml")
    
    # Check if file already exists and we're not forcing
    if config_file.exists() and not force:
        print(f"Configuration file {config_file} already exists")
        print("Use --force to overwrite")
        return True
    
    # Determine current version from various sources
    current_version = detect_current_version()
    if not current_version:
        current_version = "0.1.0"  # Default if not found
    
    # Create configuration file content
    config_content = f"""[tool.bumpversion]
current_version = "{current_version}"
parse = "(?P<major>\\\\d+)\\\\.(?P<minor>\\\\d+)\\\\.(?P<patch>\\\\d+)"
serialize = ["{{major}}.{{minor}}.{{patch}}"]
search = "__version__ = \\"{{current_version}}\\""
replace = "__version__ = \\"{{new_version}}\\""
regex = false
ignore_missing_version = false
tag = true
sign_tags = false
tag_name = "v{{new_version}}"
tag_message = "Bump version: {{current_version}} → {{new_version}}"
allow_dirty = true
commit = true
message = "Bump version: {{current_version}} → {{new_version}}"
commit_args = ""
pre_commit_hooks = ["uv sync", "git add uv.lock"]
"""
    
    # Write the configuration file
    try:
        with open(config_file, "w") as f:
            f.write(config_content)
        print(f"Created bump-my-version configuration file at {config_file}")
        return True
    except Exception as e:
        print(f"Error creating configuration file: {str(e)}")
        return False


def setup_precommit_hook(force=False):
    """
    Set up pre-commit hook for bump-my-version with proper uv integration.
    
    Args:
        force (bool): Whether to overwrite existing hooks
        
    Returns:
        bool: True if successful, False otherwise
    """
    # Ensure hooks directory exists
    hooks_dir = Path(".git/hooks")
    if not hooks_dir.exists():
        # Check if we're in a git repository
        try:
            subprocess.run(["git", "rev-parse", "--git-dir"], check=True, stdout=subprocess.DEVNULL)
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("Not in a git repository, cannot set up pre-commit hook")
            return False
        
        # Create hooks directory
        hooks_dir.mkdir(parents=True, exist_ok=True)
    
    # Define the pre-commit hook path
    pre_commit_hook = hooks_dir / "pre-commit"
    
    # Check if hook already exists and we're not forcing
    if pre_commit_hook.exists() and not force:
        # Check if it already contains bump-my-version
        with open(pre_commit_hook, "r") as f:
            content = f.read()
            if "bump-my-version" in content:
                print("pre-commit hook already contains bump-my-version")
                return True
    
    # Create or update the pre-commit hook
    pre_commit_content = """#!/bin/sh
# bump-my-version pre-commit hook

# Get the current branch name
BRANCH_NAME=$(git symbolic-ref --short HEAD 2>/dev/null)

# Skip version bump for certain branches like 'main' or if not on any branch
if [ "$BRANCH_NAME" = "" ] || [ "$BRANCH_NAME" = "HEAD" ]; then
    echo "Not on any branch, skipping version bump"
    exit 0
fi

# Run bump-my-version using uv (preferred) or directly
if command -v uv >/dev/null 2>&1; then
    echo "Running bump-my-version using uv..."
    uv tool run bump-my-version bump minor --commit --tag --allow-dirty
else
    echo "Running bump-my-version directly..."
    bump-my-version bump minor --commit --tag --allow-dirty
fi

# Exit code should be the exit code of the last command
exit $?
"""
    
    # Write the pre-commit hook
    try:
        with open(pre_commit_hook, "w") as f:
            f.write(pre_commit_content)
        
        # Make executable
        pre_commit_hook.chmod(0o755)
        print(f"Created pre-commit hook at {pre_commit_hook}")
        return True
    except Exception as e:
        print(f"Error creating pre-commit hook: {str(e)}")
        return False


def detect_current_version():
    """
    Detect the current version from various sources.
    
    Returns:
        str: Detected version or None if not found
    """
    # Try looking in src directory first (common pattern)
    version_files = [
        "src/enchant_cli/__init__.py",
        "src/enchant_cli/version.py",
        "src/__init__.py", 
        "__init__.py",
        "helpers/__init__.py"
    ]
    
    for file in version_files:
        if Path(file).exists():
            try:
                with open(file, "r") as f:
                    content = f.read()
                    # Look for common version patterns
                    match = re.search(r'__version__\s*=\s*["\']([0-9]+\.[0-9]+\.[0-9]+)["\']', content)
                    if match:
                        return match.group(1)
                    
                    match = re.search(r'VERSION\s*=\s*["\']([0-9]+\.[0-9]+\.[0-9]+)["\']', content)
                    if match:
                        return match.group(1)
            except Exception:
                continue
    
    # Try to extract from pyproject.toml
    try:
        if Path("pyproject.toml").exists():
            with open("pyproject.toml", "r") as f:
                content = f.read()
                match = re.search(r'version\s*=\s*["\']([0-9]+\.[0-9]+\.[0-9]+)["\']', content)
                if match:
                    return match.group(1)
    except Exception:
        pass
    
    # Try to extract from setup.py
    try:
        if Path("setup.py").exists():
            with open("setup.py", "r") as f:
                content = f.read()
                match = re.search(r'version\s*=\s*["\']([0-9]+\.[0-9]+\.[0-9]+)["\']', content)
                if match:
                    return match.group(1)
    except Exception:
        pass
    
    return None


def setup_bump_my_version(use_uv=True, force=False):
    """
    Set up bump-my-version with proper uv integration following best practices.
    
    This function:
    1. Installs bump-my-version using uv tool (or falls back to pip)
    2. Creates a proper .bumpversion.toml configuration file
    3. Sets up pre-commit hooks for version bumping
    4. Configures uv sync to be part of the pre-commit process
    
    Args:
        use_uv (bool): Whether to use uv for installation and running
        force (bool): Whether to force reinstallation and reconfiguration
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Step 1: Install bump-my-version using the appropriate method
        if not install_bump_my_version(use_uv, force):
            print("Failed to install bump-my-version", file=sys.stderr)
            return False
        
        # Step 2: Create or update .bumpversion.toml
        if not create_bumpversion_config(force):
            print("Failed to create bump-my-version configuration", file=sys.stderr)
            return False
        
        # Step 3: Set up pre-commit hooks
        if not setup_precommit_hook(force):
            print("Failed to set up pre-commit hook", file=sys.stderr)
            return False
        
        print("Successfully set up bump-my-version with proper uv integration")
        return True
    except Exception as e:
        print(f"Error setting up bump-my-version: {str(e)}", file=sys.stderr)
        return False


def create_bat_wrapper(script_name):
    """
    Create a Windows .bat wrapper for a shell script.
    
    Args:
        script_name (str): Name of the shell script (without extension)
        
    Returns:
        bool: True if successful, False otherwise
    """
    sh_path = f"{script_name}.sh"
    bat_path = f"{script_name}.bat"
    
    if not Path(sh_path).exists():
        print(f"Shell script {sh_path} does not exist")
        return False
    
    # Standard bat wrapper template
    bat_content = f"""@echo off
REM Windows wrapper script for {script_name}.sh

REM Check if we can use WSL
WHERE wsl >nul 2>&1
IF %ERRORLEVEL% EQU 0 (
    echo Using WSL to run the script...
    wsl ./{script_name}.sh %*
    exit /b %ERRORLEVEL%
)

REM Check if we can use Git Bash
WHERE bash >nul 2>&1
IF %ERRORLEVEL% EQU 0 (
    echo Using Git Bash to run the script...
    bash ./{script_name}.sh %*
    exit /b %ERRORLEVEL%
)

REM Fall back to Windows native commands
echo Using Windows native commands...

REM Ensure we're in the project virtual environment
if not exist .venv\\Scripts\\activate.bat (
    echo Virtual environment not found. Creating...
    python -m venv .venv
)

call .venv\\Scripts\\activate.bat

REM Install uv if not available
WHERE uv >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    pip install uv
)

REM Run bump-my-version via uv
uv tool run bump-my-version bump minor --commit --tag --allow-dirty

REM Deactivate environment
call deactivate
"""
    
    try:
        with open(bat_path, "w") as f:
            f.write(bat_content)
        print(f"Created Windows batch wrapper at {bat_path}")
        return True
    except Exception as e:
        print(f"Error creating batch wrapper: {str(e)}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Shell script analysis and fixing utilities")
    
    # Original functionality
    parser.add_argument("--check", metavar="SCRIPT", help="Check a shell script for issues")
    parser.add_argument("--fix", metavar="SCRIPT", help="Fix common issues in a shell script")
    parser.add_argument("--find-duplicates", action="store_true", 
                       help="Find duplicated functions across shell scripts")
    parser.add_argument("--scripts", nargs="+", help="List of scripts to analyze")
    
    # New bump-my-version functionality
    parser.add_argument("--setup-bumpversion", action="store_true", 
                      help="Set up bump-my-version with proper uv integration")
    parser.add_argument("--no-uv", action="store_true", 
                      help="Don't use uv for bump-my-version")
    parser.add_argument("--force", action="store_true", 
                      help="Force overwrite of existing files")
    parser.add_argument("--create-bat-wrapper", metavar="SCRIPT", 
                      help="Create a Windows .bat wrapper for a shell script")
    
    args = parser.parse_args()
    
    # If no specific action is requested, show help
    if not (args.check or args.fix or args.find_duplicates or args.setup_bumpversion or 
            args.create_bat_wrapper):
        parser.print_help()
        return 0
    
    if args.check:
        issues = check_script_quality(args.check)
        if issues == 0:
            print(f"✅ No issues found in {args.check}")
            return 0
        else:
            print(f"❌ Found {issues} issues in {args.check}")
            return 1
    
    if args.fix:
        fixed = fix_common_script_issues(args.fix)
        if fixed:
            print(f"✅ Applied fixes to {args.fix}")
        else:
            print(f"ℹ️ No fixes needed for {args.fix}")
        return 0
    
    if args.find_duplicates:
        if not args.scripts:
            print("Error: --scripts argument is required with --find-duplicates", file=sys.stderr)
            return 1
            
        duplicates = find_duplicate_functions(args.scripts)
        if duplicates:
            print(f"Found {len(duplicates)} duplicated functions:")
            for func_name, scripts in duplicates.items():
                print(f"  - {func_name} appears in: {', '.join(scripts)}")
        else:
            print("No duplicated functions found.")
        return 0
    
    # New functionality for bump-my-version
    if args.setup_bumpversion:
        if setup_bump_my_version(not args.no_uv, args.force):
            return 0
        else:
            return 1
    
    if args.create_bat_wrapper:
        if create_bat_wrapper(args.create_bat_wrapper):
            return 0
        else:
            return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())