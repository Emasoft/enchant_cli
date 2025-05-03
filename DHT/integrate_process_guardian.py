#!/usr/bin/env python3
"""
Process Guardian Integration Script

This script automatically integrates the process guardian with existing scripts
in the project to prevent runaway processes, memory leaks, and duplicate processes.

Features:
- Updates shell scripts to use the guard-process.sh wrapper
- Modifies Python files to use the ProcessGuardian context manager
- Adds appropriate limits for different tools (bump-my-version, pytest, etc.)
- Preserves script functionality while adding safety limits

Usage:
    python -m helpers.shell.integrate_process_guardian
"""

import os
import re
import sys
from pathlib import Path
import subprocess
import shutil
from typing import List, Dict, Tuple, Optional

# Constants
SCRIPT_DIR = Path(__file__).parent.parent.parent
PROCESS_GUARDIAN_IMPORT = "from helpers.shell.process_guardian import ProcessGuardian"

# Tool-specific configurations
TOOL_CONFIGS = {
    "bump-my-version": {"timeout": 300, "memory": 512},   # 5 minutes, 512MB
    "pytest": {"timeout": 900, "memory": 1024},          # 15 minutes, 1GB
    "tox": {"timeout": 1800, "memory": 1536},            # 30 minutes, 1.5GB
    "pre-commit": {"timeout": 600, "memory": 768},       # 10 minutes, 768MB
    "uv": {"timeout": 600, "memory": 768},               # 10 minutes, 768MB
    "pip": {"timeout": 600, "memory": 768},              # 10 minutes, 768MB
    "npm": {"timeout": 600, "memory": 1024},             # 10 minutes, 1GB
    "gh": {"timeout": 300, "memory": 384},               # 5 minutes, 384MB
    "git": {"timeout": 300, "memory": 384},              # 5 minutes, 384MB
    "black": {"timeout": 300, "memory": 512},            # 5 minutes, 512MB
    "ruff": {"timeout": 300, "memory": 512},             # 5 minutes, 512MB
    "isort": {"timeout": 300, "memory": 512},            # 5 minutes, 512MB
    "mypy": {"timeout": 300, "memory": 768},             # 5 minutes, 768MB
    "default": {"timeout": 900, "memory": 1024}          # 15 minutes, 1GB
}

def make_file_executable(file_path: Path):
    """Make a file executable."""
    mode = file_path.stat().st_mode
    file_path.chmod(mode | 0o755)

def backup_file(file_path: Path):
    """Create a backup of a file."""
    backup_path = file_path.with_suffix(file_path.suffix + '.bak')
    shutil.copy2(file_path, backup_path)
    print(f"Created backup: {backup_path}")
    return backup_path

def check_and_install_psutil():
    """Check if psutil is installed, and install it if not."""
    try:
        import psutil
        print("✅ psutil is already installed")
    except ImportError:
        print("📦 Installing psutil...")
        subprocess.run([sys.executable, "-m", "pip", "install", "psutil"], check=True)
        print("✅ psutil installed successfully")

def find_shell_scripts() -> List[Path]:
    """Find all shell scripts in the project."""
    scripts = []
    for ext in ['.sh', '.bash']:
        scripts.extend(SCRIPT_DIR.glob(f"**/*{ext}"))
    
    # Filter out backup files
    scripts = [script for script in scripts if not script.name.endswith('.bak')]
    return scripts

def find_python_scripts() -> List[Path]:
    """Find Python scripts that might need process guardian integration."""
    scripts = []
    for ext in ['.py']:
        scripts.extend(SCRIPT_DIR.glob(f"**/*{ext}"))
    
    # Filter out backup files and the process guardian itself
    scripts = [
        script for script in scripts 
        if not script.name.endswith('.bak') 
        and 'process_guardian.py' not in str(script)
        and 'integrate_process_guardian.py' not in str(script)
    ]
    return scripts

def find_bat_scripts() -> List[Path]:
    """Find Windows batch scripts in the project."""
    scripts = []
    for ext in ['.bat', '.cmd']:
        scripts.extend(SCRIPT_DIR.glob(f"**/*{ext}"))
    
    # Filter out backup files
    scripts = [script for script in scripts if not script.name.endswith('.bak')]
    return scripts

def detect_tools_in_script(content: str) -> List[str]:
    """Detect which tools are used in a script."""
    tools = []
    for tool in TOOL_CONFIGS.keys():
        if tool == "default":
            continue
        # Look for the tool name followed by a space, newline, or as a command
        if re.search(rf"(^|\s|\"|'){tool}($|\s|\"|'|\.)", content):
            tools.append(tool)
    return tools

def get_tool_config(tools: List[str]) -> Dict[str, int]:
    """Get the configuration for a list of tools, using the most permissive values."""
    if not tools:
        return TOOL_CONFIGS["default"].copy()
    
    max_timeout = max(TOOL_CONFIGS[tool]["timeout"] for tool in tools)
    max_memory = max(TOOL_CONFIGS[tool]["memory"] for tool in tools)
    
    return {"timeout": max_timeout, "memory": max_memory}

def update_shell_script(script_path: Path, dry_run: bool = False) -> bool:
    """
    Update a shell script to use the process guardian.
    
    Args:
        script_path: Path to the shell script
        dry_run: Whether to actually modify the file
        
    Returns:
        bool: True if the script was updated, False otherwise
    """
    # Skip if the script is a backup
    if script_path.name.endswith('.bak'):
        return False
        
    # Skip process guardian scripts
    if script_path.name in ['guard-process.sh', 'guard-process.bat']:
        return False
    
    try:
        with open(script_path, 'r') as f:
            content = f.read()
            
        # If script already uses the process guardian, skip it
        if "guard-process.sh" in content:
            print(f"✅ {script_path.name} already uses process guardian")
            return False
            
        # Detect which tools are used in the script
        tools = detect_tools_in_script(content)
        
        if tools:
            tool_names = ', '.join(tools)
            print(f"📦 {script_path.name} uses tools: {tool_names}")
        else:
            print(f"📦 {script_path.name} doesn't use any known tools")
        
        # Get the appropriate configuration
        config = get_tool_config(tools)
        
        # Create a backup
        if not dry_run:
            backup_file(script_path)
            
        # Look for common command execution patterns
        replacements = []
        
        # Pattern: direct command execution
        for tool in tools:
            # Special case for 'uv' or 'pip' when calling other Python tools
            if tool in ['uv', 'pip']:
                for t in ['pytest', 'tox', 'black', 'ruff', 'isort', 'mypy']:
                    pattern = rf'(\$PYTHON_CMD -m |\./\.venv/bin/){tool} .*{t}'
                    for match in re.finditer(pattern, content, re.MULTILINE):
                        cmd = match.group(0)
                        replacement = f'"$SCRIPT_DIR/guard-process.sh" --timeout {config["timeout"]} --max-memory {config["memory"]} --monitor {t} -- {cmd}'
                        replacements.append((cmd, replacement))
            
            pattern = rf'(\$PYTHON_CMD -m |\./\.venv/bin/){tool}'
            for match in re.finditer(pattern, content, re.MULTILINE):
                cmd = match.group(0)
                replacement = f'"$SCRIPT_DIR/guard-process.sh" --timeout {config["timeout"]} --max-memory {config["memory"]} --monitor {tool} -- {cmd}'
                replacements.append((cmd, replacement))
                
            # Direct command
            pattern = rf'\b{tool}\b'
            for match in re.finditer(pattern, content, re.MULTILINE):
                # Skip if the pattern is part of a function name, variable, etc.
                if re.search(rf'(function|alias|export|PATH|=[^=]*){pattern}', match.string[max(0, match.start()-20):match.end()+20]):
                    continue
                cmd = match.group(0)
                # Make sure this is a command and not part of another word
                if (match.start() == 0 or content[match.start()-1] in " \t\n\"'") and (match.end() == len(content) or content[match.end()] in " \t\n\"'"):
                    replacement = f'"$SCRIPT_DIR/guard-process.sh" --timeout {config["timeout"]} --max-memory {config["memory"]} --monitor {tool} -- {cmd}'
                    replacements.append((cmd, replacement))
        
        # Add a general guard for subprocess calls
        updated_content = content
        
        # Apply replacements, careful not to replace inside comments
        for old, new in replacements:
            # Check if we're not in a comment
            pattern = rf'^[^#]*({re.escape(old)})'
            updated_content = re.sub(pattern, lambda m: m.string[:m.start(1)] + new + m.string[m.end(1):], updated_content, flags=re.MULTILINE)
        
        # Add default SCRIPT_DIR code if it doesn't exist
        if "SCRIPT_DIR=" not in updated_content and "#!" in updated_content:
            script_dir_code = """
# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
"""
            # Insert after shebang line
            updated_content = re.sub(r'(^#!.*\n)', r'\1' + script_dir_code, updated_content)
            
        # If the content changed, write it back
        if updated_content != content:
            if not dry_run:
                with open(script_path, 'w') as f:
                    f.write(updated_content)
                print(f"✅ Updated {script_path.name} to use process guardian")
                return True
            else:
                print(f"🔍 Would update {script_path.name} to use process guardian")
                return True
        else:
            print(f"ℹ️ No changes needed for {script_path.name}")
            return False
            
    except Exception as e:
        print(f"❌ Error updating {script_path.name}: {e}")
        return False

def update_bat_script(script_path: Path, dry_run: bool = False) -> bool:
    """
    Update a Windows batch script to use the process guardian.
    
    Args:
        script_path: Path to the batch script
        dry_run: Whether to actually modify the file
        
    Returns:
        bool: True if the script was updated, False otherwise
    """
    # Skip if the script is a backup or the guardian itself
    if script_path.name.endswith('.bak') or script_path.name == 'guard-process.bat':
        return False
    
    try:
        with open(script_path, 'r') as f:
            content = f.read()
            
        # If script already uses the process guardian, skip it
        if "guard-process.bat" in content:
            print(f"✅ {script_path.name} already uses process guardian")
            return False
            
        # Detect which tools are used in the script
        tools = detect_tools_in_script(content)
        
        if tools:
            tool_names = ', '.join(tools)
            print(f"📦 {script_path.name} uses tools: {tool_names}")
        else:
            print(f"📦 {script_path.name} doesn't use any known tools")
        
        # Get the appropriate configuration
        config = get_tool_config(tools)
        
        # Create a backup
        if not dry_run:
            backup_file(script_path)
            
        # Look for common command execution patterns
        replacements = []
        
        # Pattern: direct command execution
        for tool in tools:
            # Direct command
            pattern = rf'\b{tool}\b'
            for match in re.finditer(pattern, content, re.MULTILINE):
                # Skip if the pattern is part of a function name, variable, etc.
                if re.search(rf'(set |echo|call|goto|if|for|rem|::){pattern}', match.string[max(0, match.start()-20):match.end()+20], re.IGNORECASE):
                    continue
                cmd = match.group(0)
                # Make sure this is a command and not part of another word
                if (match.start() == 0 or content[match.start()-1] in " \t\n\"'") and (match.end() == len(content) or content[match.end()] in " \t\n\"'"):
                    replacement = f'%SCRIPT_DIR%\\guard-process.bat --timeout {config["timeout"]} --max-memory {config["memory"]} --monitor {tool} -- {cmd}'
                    replacements.append((cmd, replacement))
        
        # Add a general guard for subprocess calls
        updated_content = content
        
        # Apply replacements, careful not to replace inside comments
        for old, new in replacements:
            # Check if we're not in a comment
            pattern = rf'^[^:]*({re.escape(old)})'
            updated_content = re.sub(pattern, lambda m: m.string[:m.start(1)] + new + m.string[m.end(1):], updated_content, flags=re.MULTILINE)
        
        # Add default SCRIPT_DIR code if it doesn't exist
        if "SCRIPT_DIR=" not in updated_content:
            script_dir_code = """
REM Get script directory
SET SCRIPT_DIR=%~dp0
"""
            # Insert at the beginning of the file
            updated_content = script_dir_code + updated_content
            
        # If the content changed, write it back
        if updated_content != content:
            if not dry_run:
                with open(script_path, 'w') as f:
                    f.write(updated_content)
                print(f"✅ Updated {script_path.name} to use process guardian")
                return True
            else:
                print(f"🔍 Would update {script_path.name} to use process guardian")
                return True
        else:
            print(f"ℹ️ No changes needed for {script_path.name}")
            return False
            
    except Exception as e:
        print(f"❌ Error updating {script_path.name}: {e}")
        return False

def update_python_script(script_path: Path, dry_run: bool = False) -> bool:
    """
    Update a Python script to use the ProcessGuardian context manager.
    
    Args:
        script_path: Path to the Python script
        dry_run: Whether to actually modify the file
        
    Returns:
        bool: True if the script was updated, False otherwise
    """
    # Skip helper scripts
    if "helpers" in str(script_path) or "process_guardian.py" in str(script_path):
        return False
    
    try:
        with open(script_path, 'r') as f:
            content = f.read()
            
        # If script already uses the ProcessGuardian, skip it
        if "ProcessGuardian" in content:
            print(f"✅ {script_path.name} already uses ProcessGuardian")
            return False
            
        # Detect which tools are used in the script
        tools = detect_tools_in_script(content)
        
        if tools:
            tool_names = ', '.join(tools)
            print(f"📦 {script_path.name} uses tools: {tool_names}")
        else:
            print(f"📦 {script_path.name} doesn't use any known tools")
        
        # Get the appropriate configuration
        config = get_tool_config(tools)
        
        # Create a backup
        if not dry_run:
            backup_file(script_path)
            
        updated_content = content
        modified = False
        
        # Add import statement if needed
        if PROCESS_GUARDIAN_IMPORT not in content:
            import_pattern = r'(^import .*$|^from .*$)'
            match = re.search(import_pattern, content, re.MULTILINE)
            if match:
                # Add import after the last import statement
                last_import = list(re.finditer(import_pattern, content, re.MULTILINE))[-1]
                insert_pos = last_import.end()
                updated_content = content[:insert_pos] + "\n" + PROCESS_GUARDIAN_IMPORT + content[insert_pos:]
                modified = True
            else:
                # Add import at the beginning of the file, after any docstring
                docstring_match = re.search(r'""".*?"""', content, re.DOTALL)
                if docstring_match:
                    insert_pos = docstring_match.end()
                    updated_content = content[:insert_pos] + "\n\n" + PROCESS_GUARDIAN_IMPORT + content[insert_pos:]
                else:
                    # Add at the very beginning
                    updated_content = PROCESS_GUARDIAN_IMPORT + "\n\n" + content
                modified = True
                
        # Look for subprocess calls
        subprocess_patterns = [
            (r'subprocess\.(?:call|run|Popen)\s*\(([^)]*)\)', 'subprocess'),
            (r'os\.system\s*\(([^)]*)\)', 'os.system'),
            (r'os\.popen\s*\(([^)]*)\)', 'os.popen')
        ]
        
        for pattern, tool_type in subprocess_patterns:
            # Find all subprocess calls
            for match in re.finditer(pattern, updated_content, re.DOTALL):
                # Get the arguments to the call
                args = match.group(1)
                
                # Determine which tool is being called, if any
                tool_match = None
                detected_tool = None
                
                for tool in tools:
                    if re.search(rf'[\'"]{tool}[\'"]', args):
                        tool_match = True
                        detected_tool = tool
                        break
                
                # If we couldn't detect a specific tool, use default config
                if not detected_tool:
                    detected_tool = "default"
                    
                specific_config = TOOL_CONFIGS[detected_tool]
                
                # Full match to replace
                full_match = match.group(0)
                
                # Generate the replacement with ProcessGuardian context manager
                replacement = f"""with ProcessGuardian(process_name="{detected_tool}", timeout={specific_config['timeout']}, max_memory_mb={specific_config['memory']}):
    {full_match}"""
                
                # Replace the match
                updated_content = updated_content.replace(full_match, replacement)
                modified = True
        
        # If the content was modified, write it back
        if modified:
            if not dry_run:
                with open(script_path, 'w') as f:
                    f.write(updated_content)
                print(f"✅ Updated {script_path.name} to use ProcessGuardian")
                return True
            else:
                print(f"🔍 Would update {script_path.name} to use ProcessGuardian")
                return True
        else:
            print(f"ℹ️ No changes needed for {script_path.name}")
            return False
            
    except Exception as e:
        print(f"❌ Error updating {script_path.name}: {e}")
        return False

def update_bump_version_script(script_path: Path, dry_run: bool = False) -> bool:
    """
    Update bump_version.sh with special handling to prevent the issues we encountered.
    
    Args:
        script_path: Path to the bump_version.sh script
        dry_run: Whether to actually modify the file
        
    Returns:
        bool: True if the script was updated, False otherwise
    """
    if not script_path.exists():
        print(f"❌ {script_path} does not exist")
        return False
        
    try:
        with open(script_path, 'r') as f:
            content = f.read()
            
        # If script already uses the process guardian, skip it
        if "guard-process.sh" in content:
            print(f"✅ {script_path.name} already uses process guardian")
            return False
            
        # Create a backup
        if not dry_run:
            backup_file(script_path)
            
        # Special replacement for bump-my-version with strict limits
        updated_content = content
        
        # Replace direct uv tool run or bump-my-version calls
        patterns = [
            r'(uv\s+tool\s+run\s+bump-my-version.*?)',
            r'("\$UV_CMD"\s+tool\s+run\s+bump-my-version.*?)',
            r'(bump-my-version\s+.*?)'
        ]
        
        for pattern in patterns:
            for match in re.finditer(pattern, updated_content, re.DOTALL):
                cmd = match.group(1)
                # Make sure this is a command and not part of a string or comment
                if not re.search(r'(echo|printf|log|".*?"|#.*?)' + re.escape(cmd), match.string[max(0, match.start()-20):match.end()+20]):
                    replacement = f'"$SCRIPT_DIR/guard-process.sh" --timeout 300 --max-memory 1024 --monitor bump-my-version -- {cmd}'
                    updated_content = updated_content.replace(cmd, replacement)
        
        # If the content was modified, write it back
        if updated_content != content:
            if not dry_run:
                with open(script_path, 'w') as f:
                    f.write(updated_content)
                print(f"✅ Updated {script_path.name} with strict process guardian limits")
                return True
            else:
                print(f"🔍 Would update {script_path.name} with strict process guardian limits")
                return True
        else:
            print(f"ℹ️ No changes needed for {script_path.name}")
            return False
            
    except Exception as e:
        print(f"❌ Error updating {script_path.name}: {e}")
        return False

def create_watchdog_service():
    """Create a process guardian watchdog service script."""
    watchdog_path = SCRIPT_DIR / "process-guardian-watchdog.py"
    
    watchdog_content = """#!/usr/bin/env python3
\"\"\"
Process Guardian Watchdog Service

This script provides a background service that continuously monitors
for runaway processes and terminates them if they exceed limits.

Run this script in the background to provide an extra layer of protection
against memory leaks and infinite loops.

Usage:
    python process-guardian-watchdog.py &
\"\"\"

import os
import sys
import time
import signal
import psutil
from pathlib import Path

# Add the project root to Python path
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

# Import the ProcessGuardian
from helpers.shell.process_guardian import ProcessGuardian

def run_watchdog():
    \"\"\"Run the process guardian watchdog.\"\"\"
    print("Starting Process Guardian Watchdog Service")
    print(f"PID: {os.getpid()}")
    print("Monitoring for runaway processes...")
    
    # Create a guardian with default settings
    guardian = ProcessGuardian(
        timeout=900,  # 15 minutes
        max_memory_mb=2048,  # 2GB
        kill_duplicates=True,
        log_file=os.path.expanduser("~/.process_guardian/watchdog.log")
    )
    
    try:
        # Start monitoring in the current thread
        guardian.monitor_processes()
    except KeyboardInterrupt:
        print("Watchdog service stopped by user")
    finally:
        guardian.cleanup()

if __name__ == "__main__":
    # Check if we should daemonize
    if len(sys.argv) > 1 and sys.argv[1] == "--daemon":
        # Create a daemon process
        try:
            pid = os.fork()
            if pid > 0:
                # Exit parent process
                sys.exit(0)
        except OSError as e:
            print(f"Error forking process: {e}")
            sys.exit(1)
        
        # Decouple from parent environment
        os.chdir('/')
        os.setsid()
        os.umask(0)
        
        # Close standard file descriptors
        sys.stdout.flush()
        sys.stderr.flush()
        
        with open('/dev/null', 'r') as f:
            os.dup2(f.fileno(), sys.stdin.fileno())
        with open(os.path.expanduser('~/.process_guardian/watchdog.out'), 'a+') as f:
            os.dup2(f.fileno(), sys.stdout.fileno())
        with open(os.path.expanduser('~/.process_guardian/watchdog.err'), 'a+') as f:
            os.dup2(f.fileno(), sys.stderr.fileno())
            
        # Create PID file
        pid_file = os.path.expanduser('~/.process_guardian/watchdog.pid')
        with open(pid_file, 'w') as f:
            f.write(str(os.getpid()))
            
        run_watchdog()
    else:
        # Run in foreground
        run_watchdog()
"""
    
    with open(watchdog_path, 'w') as f:
        f.write(watchdog_content)
    
    # Make it executable
    make_file_executable(watchdog_path)
    
    print(f"✅ Created process guardian watchdog service: {watchdog_path}")
    return watchdog_path

def create_startup_integration():
    """Create scripts to start the process guardian on system startup."""
    # Create directory if it doesn't exist
    guardian_dir = Path.home() / ".process_guardian"
    guardian_dir.mkdir(exist_ok=True)
    
    # Create the startup script for Unix
    startup_path = SCRIPT_DIR / "start-process-guardian.sh"
    startup_content = """#!/bin/bash
# Start the Process Guardian Watchdog Service

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Create directory if it doesn't exist
mkdir -p ~/.process_guardian

# Check if the watchdog is already running
if [ -f ~/.process_guardian/watchdog.pid ]; then
    PID=$(cat ~/.process_guardian/watchdog.pid)
    if ps -p $PID > /dev/null; then
        echo "Process Guardian Watchdog is already running with PID $PID"
        exit 0
    else
        echo "Removing stale PID file"
        rm ~/.process_guardian/watchdog.pid
    fi
fi

# Start the watchdog in daemon mode
echo "Starting Process Guardian Watchdog..."
"$SCRIPT_DIR/process-guardian-watchdog.py" --daemon

# Check if it started successfully
sleep 1
if [ -f ~/.process_guardian/watchdog.pid ]; then
    PID=$(cat ~/.process_guardian/watchdog.pid)
    if ps -p $PID > /dev/null; then
        echo "Process Guardian Watchdog started with PID $PID"
        exit 0
    fi
fi

echo "Failed to start Process Guardian Watchdog"
exit 1
"""
    
    with open(startup_path, 'w') as f:
        f.write(startup_content)
    
    # Make it executable
    make_file_executable(startup_path)
    
    # Create the startup script for Windows
    startup_path_win = SCRIPT_DIR / "start-process-guardian.bat"
    startup_content_win = """@echo off
REM Start the Process Guardian Watchdog Service

SET SCRIPT_DIR=%~dp0

REM Create directory if it doesn't exist
if not exist "%USERPROFILE%\\.process_guardian" mkdir "%USERPROFILE%\\.process_guardian"

REM Check if the watchdog is already running
if exist "%USERPROFILE%\\.process_guardian\\watchdog.pid" (
    set /p PID=<"%USERPROFILE%\\.process_guardian\\watchdog.pid"
    wmic process where ProcessId=%PID% get ProcessId /value >nul 2>nul
    if %ERRORLEVEL% EQU 0 (
        echo Process Guardian Watchdog is already running with PID %PID%
        exit /b 0
    ) else (
        echo Removing stale PID file
        del "%USERPROFILE%\\.process_guardian\\watchdog.pid"
    )
)

REM Start the watchdog in daemon mode
echo Starting Process Guardian Watchdog...
start /b pythonw "%SCRIPT_DIR%\\process-guardian-watchdog.py" --daemon

REM Check if it started successfully
timeout /t 1 >nul
if exist "%USERPROFILE%\\.process_guardian\\watchdog.pid" (
    set /p PID=<"%USERPROFILE%\\.process_guardian\\watchdog.pid"
    wmic process where ProcessId=%PID% get ProcessId /value >nul 2>nul
    if %ERRORLEVEL% EQU 0 (
        echo Process Guardian Watchdog started with PID %PID%
        exit /b 0
    )
)

echo Failed to start Process Guardian Watchdog
exit /b 1
"""
    
    with open(startup_path_win, 'w') as f:
        f.write(startup_content_win)
    
    print(f"✅ Created startup scripts: {startup_path} and {startup_path_win}")
    return startup_path, startup_path_win

def main(dry_run: bool = False):
    """
    Main function to integrate process guardian with all scripts.
    
    Args:
        dry_run: If True, don't actually modify files
    """
    print("Process Guardian Integration")
    print("===========================")
    print(f"Project directory: {SCRIPT_DIR}")
    print(f"Dry run: {dry_run}")
    print()
    
    # Check and install psutil
    check_and_install_psutil()
    
    # Make sure the process guardian scripts are executable
    guard_script = SCRIPT_DIR / "guard-process.sh"
    if guard_script.exists():
        make_file_executable(guard_script)
    
    # Find and update scripts
    shell_scripts = find_shell_scripts()
    bat_scripts = find_bat_scripts()
    python_scripts = find_python_scripts()
    
    print(f"\nFound {len(shell_scripts)} shell scripts, {len(bat_scripts)} batch scripts, and {len(python_scripts)} Python scripts")
    print()
    
    # Special handling for bump_version.sh
    bump_version_scripts = [
        Path(SCRIPT_DIR / "hooks/bump_version.sh"),
        Path(SCRIPT_DIR / "bump_version.sh")
    ]
    
    for script in bump_version_scripts:
        if script.exists():
            print(f"\nUpdating {script.name} (special handling)...")
            update_bump_version_script(script, dry_run)
    
    # Update shell scripts
    print("\nUpdating shell scripts...")
    shell_updated = 0
    for script in shell_scripts:
        if update_shell_script(script, dry_run):
            shell_updated += 1
    
    # Update batch scripts
    print("\nUpdating batch scripts...")
    bat_updated = 0
    for script in bat_scripts:
        if update_bat_script(script, dry_run):
            bat_updated += 1
    
    # Update Python scripts
    print("\nUpdating Python scripts...")
    py_updated = 0
    for script in python_scripts:
        if update_python_script(script, dry_run):
            py_updated += 1
    
    # Create the watchdog service
    print("\nCreating watchdog service...")
    if not dry_run:
        create_watchdog_service()
        create_startup_integration()
    else:
        print("🔍 Would create watchdog service and startup scripts")
    
    # Summary
    print("\nSummary")
    print("=======")
    print(f"Updated {shell_updated} shell scripts")
    print(f"Updated {bat_updated} batch scripts")
    print(f"Updated {py_updated} Python scripts")
    print()
    print("Next steps:")
    print("1. Run './start-process-guardian.sh' to start the watchdog service")
    print("2. Test modified scripts to ensure they work correctly")
    print("3. Monitor the process guardian logs at ~/.process_guardian/process_guardian.log")

if __name__ == "__main__":
    # Parse arguments
    import argparse
    parser = argparse.ArgumentParser(description="Integrate Process Guardian with project scripts")
    parser.add_argument("--dry-run", action="store_true", help="Don't actually modify files")
    args = parser.parse_args()
    
    main(args.dry_run)