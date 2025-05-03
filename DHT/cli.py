#!/usr/bin/env python3
"""
CLAUDE HELPER SCRIPTS - Command-line interface

A unified command-line interface to access all helper scripts functionality.
This tool provides access to GitHub workflow management, log analysis, 
shell script compatibility fixes, and process monitoring.

Usage:
    python -m helpers.cli [command] [options]

Commands:
    repo        - GitHub repository management commands
    workflow    - GitHub workflow management commands
    logs        - Log analysis and error detection commands
    fix         - Fix shell script issues
    process     - Process monitoring and control commands
    version     - Show version information
"""

import argparse
import os
import sys
import time
from pathlib import Path

# Add the project root directory to the Python path
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from helpers import __version__
from helpers.errors import log_analyzer
from helpers.github import workflow_helper, repo_helper
from helpers.shell import script_fixer
try:
    from helpers.shell.process_guardian import ProcessGuardian
except ImportError:
    ProcessGuardian = None


def version_command(_):
    """Show version information."""
    print(f"CLAUDE HELPER SCRIPTS v{__version__}")
    print("A collection of portable Python utilities for enhancing shell scripts")
    print("\nModules:")
    print("  - github: Tools for GitHub workflow management and automation")
    print("  - errors: Tools for log analysis, error classification, and diagnostics")
    print("  - shell: Shell script portability and compatibility tools")
    return 0


def logs_command(args):
    """Process logs analysis commands."""
    # Use new log_analyzer functions for all log operations
    if args.analyze:
        # Analyze a specific log file
        if not os.path.exists(args.analyze):
            print(f"Error: Log file not found: {args.analyze}", file=sys.stderr)
            return 1
            
        result = log_analyzer.classify_log_errors(args.analyze, args.output, args.format)
        
        if "error" in result:
            print(f"Error: {result['error']}", file=sys.stderr)
            return 1
            
        if not args.output:
            # Print results to stdout based on format
            if args.format == "json":
                import json
                print(json.dumps(result, indent=2))
            elif args.format == "tsv":
                print(f"critical\t{result['counts']['critical']}")
                print(f"severe\t{result['counts']['severe']}")
                print(f"warning\t{result['counts']['warning']}")
                print(f"total\t{result['total_issues']}")
                print(f"root_causes\t{';'.join(result['root_causes'])}")
            else:
                # Text format with colors
                print(log_analyzer.format_output_for_terminal(result, not args.no_color))
        
        return 0
    
    elif args.latest:
        # Get and analyze the most recent log files
        latest_logs = log_analyzer.get_latest_logs(args.count)
        
        if not latest_logs:
            print("No log files found", file=sys.stderr)
            return 1
        
        print(f"Analyzing {len(latest_logs)} most recent log files...\n")
        
        for log_file in latest_logs:
            result = log_analyzer.classify_log_errors(log_file, format=args.format)
            
            if "error" in result:
                print(f"Error: {result['error']}", file=sys.stderr)
                continue
            
            print(f"Log File: {log_file}")
            print(f"Run ID: {result['run_id']}")
            print(f"Workflow Type: {result['workflow_type']}")
            print(f"Status: {result['status']}")
            print("Error Summary:")
            print(f"  Critical: {result['counts']['critical']}")
            print(f"  Severe: {result['counts']['severe']}")
            print(f"  Warning: {result['counts']['warning']}")
            
            if result['root_causes']:
                print("\nPotential Root Causes:")
                for cause in result['root_causes']:
                    print(f"  - {cause}")
            
            print("")
        
        return 0
    
    elif args.search:
        # Search through logs for specific patterns
        results = log_analyzer.search_log_files(
            args.logs_dir, args.search, args.case_sensitive, args.max_results
        )
        
        if "error" in results:
            print(f"Error: {results['error']}", file=sys.stderr)
            return 1
        
        print(f"Found {results['total_matches']} matches in {results['files_with_matches']} files")
        
        for log_file, data in results["results"].items():
            print(f"\nFile: {log_file}")
            print(f"Workflow: {data['workflow_name']}, Run ID: {data['run_id']}")
            print(f"Matches: {data['count']}")
            print("="*50)
            
            for i, match in enumerate(data["matches"]):
                print(f"{i+1}. {match}")
                print("-"*30)
        
        return 0
    
    elif args.stats:
        # Generate statistics about log files
        stats = log_analyzer.generate_log_statistics(args.logs_dir)
        
        if "error" in stats:
            print(f"Error: {stats['error']}", file=sys.stderr)
            return 1
        
        print("Log Files Statistics:")
        print("="*50)
        print(f"Total log files:        {stats['total_logs']}")
        print(f"Files with errors:      {stats['error_logs']}")
        print(f"Test workflow logs:     {stats['test_logs']}")
        print(f"Release workflow logs:  {stats['release_logs']}")
        print(f"Other workflow logs:    {stats['other_logs']}")
        print(f"Total log size:         {stats['total_size_mb']:.2f} MB")
        
        if stats.get('recent_logs'):
            print("\nMost recent logs:")
            for log in stats['recent_logs']:
                print(f"- {log}")
        
        if stats.get('logs_after_commit'):
            print("\nLogs after last commit:")
            for log in stats['logs_after_commit']:
                print(f"- {log}")
        
        return 0
    
    elif args.cleanup:
        # Clean up old logs
        results = log_analyzer.cleanup_old_logs(
            args.logs_dir, args.age, args.max_logs, args.dry_run
        )
        
        if "error" in results:
            print(f"Error: {results['error']}", file=sys.stderr)
            return 1
        
        print(f"Found {len(results['old_logs'])} log files older than {args.age} days")
        print(f"Total size: {results['total_size_mb']:.2f} MB")
        
        if results["dry_run"]:
            print("\nDry run mode - no files deleted")
            if results["old_logs"]:
                print("Would delete the following files:")
                for log in results["old_logs"]:
                    print(f"- {log}")
        else:
            print(f"\nDeleted {len(results['deleted_files'])} files")
            print(f"Kept {results['kept_files']} files")
        
        return 0
    
    else:
        print("Error: Please specify a logs subcommand", file=sys.stderr)
        return 1


def workflow_command(args):
    """Process GitHub workflow commands."""
    if args.check:
        # Check workflow_dispatch events with enhanced reporting
        workflow_path = args.path
        
        # Use repo_helper for more reliable workflow file checking
        workflow_checks = repo_helper.check_workflow_triggers(None)
        
        if workflow_checks["total"] == 0:
            print("No workflow files found", file=sys.stderr)
            return 1
        
        print(f"Workflow Files: {workflow_checks['total']}")
        print(f"With workflow_dispatch: {workflow_checks['with_dispatch']}")
        print(f"Missing workflow_dispatch: {workflow_checks['missing_dispatch']}")
        
        if workflow_checks["missing_dispatch"] > 0:
            print("\nFiles missing workflow_dispatch trigger:")
            for file in workflow_checks["files_missing_dispatch"]:
                print(f"  - {file}")
            return 1
        else:
            print("\n✅ All workflow files have workflow_dispatch trigger")
            return 0
    
    elif args.fix:
        # Fix workflow_dispatch events with enhanced handling
        results = repo_helper.fix_workflow_triggers(args.commit)
        
        print(f"Checked {results['checked']} workflow files")
        print(f"Already compliant: {results['already_ok']}")
        print(f"Fixed: {results['fixed']}")
        print(f"Failed: {results['failed']}")
        
        if results["fixed"] > 0:
            if args.commit:
                print(f"Fixed and committed changes to {results['fixed']} workflow files")
            else:
                print(f"Fixed {results['fixed']} workflow files")
                print("Use --commit to automatically commit the changes")
        
        return 0
    
    elif args.trigger:
        # Trigger a workflow with more robust handling
        workflow_name = args.workflow
        if not workflow_name:
            print("Error: Workflow name is required", file=sys.stderr)
            return 1
        
        inputs = {}
        if args.reason:
            inputs["reason"] = args.reason
        
        print(f"Triggering workflow {workflow_name} on branch {args.branch or 'default'}")
        
        result = repo_helper.trigger_workflow(workflow_name, args.branch, inputs)
        
        if not result:
            print("Failed to trigger workflow", file=sys.stderr)
            return 1
        
        run_id = result if isinstance(result, str) else None
        
        # Wait for logs if requested
        if args.wait_logs and run_id:
            print(f"Waiting for workflow logs (timeout: {args.timeout}s)")
            
            log_file = repo_helper.wait_for_workflow_logs(run_id, args.timeout)
            
            if log_file:
                print(f"Workflow logs saved to {log_file}")
                
                # Analyze logs if requested
                if args.analyze_logs:
                    print("\nAnalyzing workflow logs:")
                    result = log_analyzer.classify_log_errors(log_file)
                    print(log_analyzer.format_output_for_terminal(result))
            else:
                print("Failed to retrieve workflow logs", file=sys.stderr)
        
        return 0
    
    else:
        print("Error: Please specify a workflow subcommand", file=sys.stderr)
        return 1


def repo_command(args):
    """Process GitHub repository commands."""
    if args.info:
        # Show repository information
        repo_info = repo_helper.get_repo_info()
        
        print("Repository Information:")
        print(f"Name:           {repo_info['name'] or 'Unknown'}")
        print(f"Owner:          {repo_info['owner'] or 'Unknown'}")
        print(f"Full name:      {repo_info['full_name'] or 'Unknown'}")
        print(f"HTTPS URL:      {repo_info['https_url'] or 'Unknown'}")
        print(f"SSH URL:        {repo_info['ssh_url'] or 'Unknown'}")
        print(f"Default branch: {repo_info['default_branch']}")
        print(f"Initialized:    {'Yes' if repo_info['is_initialized'] else 'No'}")
        
        # Check if repository exists on GitHub
        if repo_info["full_name"]:
            exists = repo_helper.check_repo_exists(repo_info["full_name"])
            print(f"Exists on GitHub: {'Yes' if exists else 'No'}")
        
        return 0
        
    elif args.bump_version:
        # Bump version
        part = args.bump_version
        use_uv = not args.no_uv
        commit = not args.no_commit
        tag = not args.no_tag
        allow_dirty = not args.no_dirty
        
        print(f"Bumping {part} version...")
        if repo_helper.bump_version(part, allow_dirty, commit, tag, use_uv):
            print(f"Successfully bumped {part} version")
            return 0
        else:
            print(f"Failed to bump {part} version", file=sys.stderr)
            return 1
            
    elif args.install_bumpversion:
        # Install bump-my-version
        print("Installing bump-my-version...")
        if repo_helper.install_bump_my_version(not args.no_uv, force_reinstall=args.force):
            print("Successfully installed bump-my-version")
            return 0
        else:
            print("Failed to install bump-my-version", file=sys.stderr)
            return 1
    
    elif args.create:
        # Create repository with enhanced options
        repo_name = args.name
        if not repo_name:
            repo_info = repo_helper.get_repo_info()
            repo_name = repo_info["name"]
            if not repo_name:
                print("Error: Repository name is required", file=sys.stderr)
                return 1
        
        if repo_helper.create_repo(repo_name, args.private, args.description):
            print(f"Repository {repo_name} created successfully")
            
            # Configure remote if needed
            repo_info = repo_helper.get_repo_info()
            if repo_info["full_name"]:
                repo_helper.configure_remote(repo_info["full_name"])
            
            return 0
        else:
            print(f"Failed to create repository {repo_name}", file=sys.stderr)
            return 1
    
    elif args.secrets:
        # Set up repository secrets
        repo_info = repo_helper.get_repo_info()
        
        if not repo_info["full_name"]:
            print("Error: Could not determine repository name", file=sys.stderr)
            return 1
        
        if repo_helper.setup_repo_secrets(repo_info["full_name"]):
            print(f"Secrets set up successfully for {repo_info['full_name']}")
            return 0
        else:
            print("Failed to set up all secrets", file=sys.stderr)
            return 1
    
    elif args.check_branch:
        # Check branch setup and tracking
        branch_info = repo_helper.verify_branch_setup(args.branch)
        
        if branch_info["is_detached"]:
            print("Warning: Detached HEAD state detected", file=sys.stderr)
            return 1
        
        if branch_info["current_branch"]:
            print(f"Current branch: {branch_info['current_branch']}")
            
            if branch_info["has_upstream"]:
                print(f"Upstream tracking: {branch_info['upstream_branch']}")
            else:
                print("No upstream tracking configured")
        else:
            print("Could not determine current branch", file=sys.stderr)
            return 1
        
        return 0
    
    elif args.create_branch:
        # Create a new branch with tracking
        branch_name = args.branch
        if not branch_name:
            print("Error: Branch name is required", file=sys.stderr)
            return 1
        
        if repo_helper.create_branch(branch_name, args.base):
            print(f"Branch {branch_name} created and checked out")
            
            # Push if requested
            if args.push:
                if repo_helper.push_branch(branch_name, True, args.force):
                    print(f"Branch {branch_name} pushed to remote")
                else:
                    print(f"Failed to push branch {branch_name}", file=sys.stderr)
                    return 1
            
            return 0
        else:
            print(f"Failed to create branch {branch_name}", file=sys.stderr)
            return 1
    
    elif args.push:
        # Push branch to remote
        branch_name = args.branch
        if not branch_name:
            branch_info = repo_helper.verify_branch_setup()
            branch_name = branch_info["current_branch"]
        
        if repo_helper.push_branch(branch_name, True, args.force):
            print(f"Branch {branch_name or 'current'} pushed to remote")
            return 0
        else:
            print(f"Failed to push branch {branch_name or 'current'}", file=sys.stderr)
            return 1
    
    else:
        print("Error: Please specify a repo subcommand", file=sys.stderr)
        return 1


def process_command(args):
    """Process monitoring and control commands."""
    if ProcessGuardian is None:
        print("Error: Process Guardian module is not available. Please install psutil with 'pip install psutil'", file=sys.stderr)
        return 1
        
    if args.list:
        # List monitored processes
        processes = ProcessGuardian.list_monitored()
        if processes:
            print(f"Monitored Processes ({len(processes)}):")
            for i, proc in enumerate(processes, 1):
                print(f"{i}. PID: {proc['pid']} - {proc['name']}")
                print(f"   Command: {proc['cmdline']}")
                print(f"   Memory: {proc['memory_mb']:.2f} MB")
                print(f"   CPU: {proc['cpu_percent']:.1f}%")
                print(f"   Started: {proc['create_time']}")
                print(f"   Running for: {proc['run_time']}")
                print()
        else:
            print("No monitored processes found")
        return 0
        
    elif args.kill_all:
        # Kill all monitored processes
        count = ProcessGuardian.kill_all_monitored()
        print(f"Killed {count} monitored processes")
        return 0
        
    elif args.start_watchdog:
        # Start the process guardian watchdog
        script_dir = Path(__file__).parent.parent.parent
        watchdog_script = script_dir / "process-guardian-watchdog.py"
        
        if not watchdog_script.exists():
            print(f"Error: Watchdog script not found at {watchdog_script}", file=sys.stderr)
            return 1
            
        if args.daemon:
            print("Starting Process Guardian Watchdog as daemon...")
            import subprocess
            subprocess.Popen([sys.executable, str(watchdog_script), "--daemon"], 
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # Give it a moment to start
            time.sleep(1)
            
            # Check if it started
            pid_file = os.path.expanduser("~/.process_guardian/watchdog.pid")
            if os.path.exists(pid_file):
                with open(pid_file, 'r') as f:
                    pid = f.read().strip()
                print(f"Watchdog started with PID {pid}")
                return 0
            else:
                print("Failed to start watchdog daemon", file=sys.stderr)
                return 1
        else:
            print("Starting Process Guardian Watchdog in foreground (Ctrl+C to stop)...")
            print(f"Running script: {watchdog_script}")
            try:
                from subprocess import run
                run([sys.executable, str(watchdog_script)])
                return 0
            except KeyboardInterrupt:
                print("\nWatchdog stopped by user")
                return 0
            except Exception as e:
                print(f"Error running watchdog: {e}", file=sys.stderr)
                return 1
                
    elif args.status:
        # Check watchdog status
        pid_file = os.path.expanduser("~/.process_guardian/watchdog.pid")
        if not os.path.exists(pid_file):
            print("Process Guardian Watchdog is not running")
            return 1
            
        with open(pid_file, 'r') as f:
            pid = f.read().strip()
            
        try:
            import psutil
            if psutil.pid_exists(int(pid)):
                process = psutil.Process(int(pid))
                print(f"Process Guardian Watchdog is running with PID {pid}")
                print(f"   Memory: {process.memory_info().rss / (1024 * 1024):.2f} MB")
                print(f"   CPU: {process.cpu_percent(interval=0.1):.1f}%")
                print(f"   Started: {time.ctime(process.create_time())}")
                print(f"   Running for: {time.time() - process.create_time():.0f} seconds")
                
                # Check log file
                log_file = os.path.expanduser("~/.process_guardian/watchdog.log")
                if os.path.exists(log_file):
                    size = os.path.getsize(log_file)
                    print(f"   Log file: {log_file} ({size/1024:.1f} KB)")
                    
                    if args.show_log:
                        print("\nRecent log entries:")
                        try:
                            with open(log_file, 'r') as f:
                                # Get last 10 lines
                                lines = f.readlines()[-10:]
                                for line in lines:
                                    print(f"   {line.strip()}")
                        except Exception as e:
                            print(f"Error reading log file: {e}")
                            
                return 0
            else:
                print(f"Process Guardian Watchdog is not running (stale PID file: {pid})")
                return 1
        except Exception as e:
            print(f"Error checking watchdog status: {e}", file=sys.stderr)
            return 1
            
    elif args.stop_watchdog:
        # Stop the process guardian watchdog
        pid_file = os.path.expanduser("~/.process_guardian/watchdog.pid")
        if not os.path.exists(pid_file):
            print("Process Guardian Watchdog is not running")
            return 1
            
        with open(pid_file, 'r') as f:
            pid = f.read().strip()
            
        try:
            import psutil
            if psutil.pid_exists(int(pid)):
                process = psutil.Process(int(pid))
                print(f"Stopping Process Guardian Watchdog (PID {pid})...")
                process.terminate()
                
                # Wait for process to terminate
                try:
                    process.wait(timeout=5)
                    print("Process Guardian Watchdog stopped")
                    
                    # Remove PID file
                    os.remove(pid_file)
                    return 0
                except psutil.TimeoutExpired:
                    print("Process didn't terminate gracefully, sending KILL signal...")
                    process.kill()
                    print("Process Guardian Watchdog killed")
                    
                    # Remove PID file
                    os.remove(pid_file)
                    return 0
            else:
                print("Process Guardian Watchdog is not running (removing stale PID file)")
                os.remove(pid_file)
                return 1
        except Exception as e:
            print(f"Error stopping watchdog: {e}", file=sys.stderr)
            return 1
            
    elif args.monitor:
        # Run a command with process monitoring
        if not args.command:
            print("Error: Command to monitor is required", file=sys.stderr)
            return 1
            
        # Build and execute the command
        if sys.platform == "win32":
            cmd = ["guard-process.bat"]
        else:
            cmd = ["./guard-process.sh"]
            
        if args.timeout:
            cmd.extend(["--timeout", str(args.timeout)])
            
        if args.max_memory:
            cmd.extend(["--max-memory", str(args.max_memory)])
            
        if args.process_name:
            cmd.extend(["--monitor", args.process_name])
            
        cmd.append("--")
        cmd.extend(args.command)
        
        try:
            from subprocess import run
            print(f"Running command with Process Guardian: {' '.join(cmd)}")
            result = run(cmd)
            return result.returncode
        except Exception as e:
            print(f"Error running command: {e}", file=sys.stderr)
            return 1
    
    else:
        print("Error: Please specify a process subcommand", file=sys.stderr)
        return 1


def fix_command(args):
    """Process fix commands for shell scripts."""
    if args.workflow_script:
        # Fix publish_to_github.sh script
        script_path = args.path or Path.cwd() / "publish_to_github.sh"
        
        if workflow_helper.fix_workflow_script(script_path):
            print(f"Successfully fixed workflow script at {script_path}")
            return 0
        else:
            print(f"Failed to fix workflow script at {script_path}", file=sys.stderr)
            return 1
    
    elif args.shell_compat:
        # Fix shell compatibility issues
        script_path = args.path or Path.cwd() / "get_errorlogs.sh"
        
        if workflow_helper.fix_shell_compatibility(script_path):
            print(f"Successfully fixed shell compatibility in {script_path}")
            return 0
        else:
            print(f"Failed to fix shell compatibility in {script_path}", file=sys.stderr)
            return 1
    
    elif args.setup_bumpversion:
        # Set up bump-my-version with proper uv integration
        print("Setting up bump-my-version with proper uv integration...")
        if script_fixer.setup_bump_my_version(not args.no_uv, args.force):
            print("✅ Successfully set up bump-my-version")
            return 0
        else:
            print("❌ Failed to set up bump-my-version", file=sys.stderr)
            return 1
    
    elif args.create_bat_wrapper:
        # Create a Windows .bat wrapper for a shell script
        script_name = args.create_bat_wrapper
        if not script_name:
            print("Error: Script name is required", file=sys.stderr)
            return 1
            
        if script_fixer.create_bat_wrapper(script_name):
            print(f"✅ Created Windows batch wrapper for {script_name}")
            return 0
        else:
            print(f"❌ Failed to create Windows batch wrapper for {script_name}", file=sys.stderr)
            return 1
    
    elif args.all:
        # Fix all issues with improved handling
        print("Fixing all detected issues...")
        
        # Fix workflow scripts
        workflow_script = Path.cwd() / "publish_to_github.sh"
        if workflow_script.exists():
            print(f"\nFixing {workflow_script}...")
            result1 = workflow_helper.fix_workflow_script(workflow_script)
        else:
            print(f"{workflow_script} not found, skipping")
            result1 = 0
        
        # Fix shell compatibility
        shell_script = Path.cwd() / "get_errorlogs.sh"
        if shell_script.exists():
            print(f"\nFixing shell compatibility in {shell_script}...")
            result2 = workflow_helper.fix_shell_compatibility(shell_script)
        else:
            print(f"{shell_script} not found, skipping")
            result2 = 0
        
        # Fix workflow_dispatch triggers
        workflow_dir = Path.cwd() / ".github" / "workflows"
        if workflow_dir.exists():
            print("\nFixing workflow_dispatch triggers...")
            result3 = repo_helper.fix_workflow_triggers(args.commit).get("failed", 0) > 0
        else:
            print(f"{workflow_dir} not found, skipping")
            result3 = 0
        
        # Set up bump-my-version if requested
        if args.with_bumpversion:
            print("\nSetting up bump-my-version with proper uv integration...")
            result4 = not script_fixer.setup_bump_my_version(not args.no_uv, args.force)
        else:
            result4 = 0
        
        # Return non-zero if any fix failed
        return max(result1, result2, 1 if result3 else 0, result4)
    
    else:
        print("Error: Please specify a fix subcommand", file=sys.stderr)
        return 1


def main():
    # Create the main parser
    parser = argparse.ArgumentParser(
        description="CLAUDE HELPER SCRIPTS - A unified command-line interface "
                    "for GitHub workflow management and log analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m helpers.cli version                               # Show version info
  python -m helpers.cli logs --analyze logs/workflow_123.log  # Analyze a log file
  python -m helpers.cli logs --latest                         # Analyze latest logs
  python -m helpers.cli workflow --check                      # Check workflows
  python -m helpers.cli workflow --fix --commit               # Fix workflows
  python -m helpers.cli fix --all                             # Fix all issues
  python -m helpers.cli fix --setup-bumpversion               # Set up bump-my-version
  python -m helpers.cli fix --create-bat-wrapper bump_version # Create Windows batch wrapper
  python -m helpers.cli repo --info                           # Show repo info
  python -m helpers.cli repo --create --name my-repo          # Create a repo
  python -m helpers.cli repo --bump-version minor             # Bump minor version
  python -m helpers.cli repo --install-bumpversion            # Install bump-my-version
  python -m helpers.cli process --list                        # List monitored processes
  python -m helpers.cli process --kill-all                    # Kill all monitored processes
  python -m helpers.cli process --start-watchdog --daemon     # Start watchdog as daemon
  python -m helpers.cli process --status                      # Check watchdog status
  python -m helpers.cli process --monitor -- command args     # Run command with monitoring
"""
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Version command
    version_parser = subparsers.add_parser("version", help="Show version information")
    
    # Logs command - Enhanced with more functionality
    logs_parser = subparsers.add_parser("logs", help="Log analysis commands")
    logs_group = logs_parser.add_mutually_exclusive_group(required=True)
    logs_group.add_argument("--analyze", metavar="LOG_FILE", help="Analyze a log file")
    logs_group.add_argument("--latest", action="store_true", help="Analyze the most recent log files")
    logs_group.add_argument("--search", metavar="PATTERN", help="Search logs for a pattern")
    logs_group.add_argument("--stats", action="store_true", help="Show log statistics")
    logs_group.add_argument("--cleanup", action="store_true", help="Clean up old log files")
    
    # Common log options
    logs_parser.add_argument("--output", help="Output file for analysis results")
    logs_parser.add_argument("--format", choices=["text", "json", "tsv"], default="text", 
                         help="Output format (default: text)")
    logs_parser.add_argument("--no-color", action="store_true", help="Disable colored output")
    logs_parser.add_argument("--count", type=int, default=3, help="Number of logs to process")
    logs_parser.add_argument("--logs-dir", default="logs", help="Logs directory")
    logs_parser.add_argument("--case-sensitive", action="store_true", help="Case-sensitive search")
    logs_parser.add_argument("--max-results", type=int, default=50, help="Maximum results to show")
    logs_parser.add_argument("--age", type=int, default=30, help="Maximum age for log files in days")
    logs_parser.add_argument("--max-logs", type=int, default=50, help="Maximum number of logs to keep")
    logs_parser.add_argument("--dry-run", action="store_true", help="Don't actually delete files")
    
    # Workflow command - Enhanced with trigger functionality
    workflow_parser = subparsers.add_parser("workflow", help="GitHub workflow commands")
    workflow_group = workflow_parser.add_mutually_exclusive_group(required=True)
    workflow_group.add_argument("--check", action="store_true", help="Check workflow_dispatch events")
    workflow_group.add_argument("--fix", action="store_true", help="Fix workflow_dispatch events")
    workflow_group.add_argument("--trigger", action="store_true", help="Trigger a workflow")
    
    workflow_parser.add_argument("--path", help="Path to the workflow directory")
    workflow_parser.add_argument("--commit", action="store_true", help="Commit workflow fixes")
    workflow_parser.add_argument("--workflow", help="Workflow name or filename to trigger")
    workflow_parser.add_argument("--branch", help="Branch to run workflow on")
    workflow_parser.add_argument("--reason", help="Reason for workflow trigger")
    workflow_parser.add_argument("--wait-logs", action="store_true", help="Wait for workflow logs")
    workflow_parser.add_argument("--timeout", type=int, default=120, help="Timeout in seconds")
    workflow_parser.add_argument("--analyze-logs", action="store_true", help="Analyze workflow logs")
    
    # Repository command - New section for repo_helper functionality
    repo_parser = subparsers.add_parser("repo", help="GitHub repository management commands")
    repo_group = repo_parser.add_mutually_exclusive_group(required=True)
    repo_group.add_argument("--info", action="store_true", help="Show repository information")
    repo_group.add_argument("--create", action="store_true", help="Create a new repository")
    repo_group.add_argument("--secrets", action="store_true", help="Set up repository secrets")
    repo_group.add_argument("--check-branch", action="store_true", help="Check branch setup")
    repo_group.add_argument("--create-branch", action="store_true", help="Create a new branch")
    repo_group.add_argument("--push", action="store_true", help="Push a branch to remote")
    repo_group.add_argument("--bump-version", choices=["major", "minor", "patch"], 
                         help="Bump version (major, minor, or patch)")
    repo_group.add_argument("--install-bumpversion", action="store_true", 
                         help="Install bump-my-version tool")
    
    # Common repository options
    repo_parser.add_argument("--name", help="Repository name")
    repo_parser.add_argument("--private", action="store_true", help="Create private repository")
    repo_parser.add_argument("--description", help="Repository description")
    repo_parser.add_argument("--branch", help="Branch name")
    repo_parser.add_argument("--base", help="Base branch name")
    repo_parser.add_argument("--force", action="store_true", help="Force push branch or force reinstall")
    
    # Version management options
    repo_parser.add_argument("--no-uv", action="store_true", help="Don't use uv for bump-my-version")
    repo_parser.add_argument("--no-commit", action="store_true", help="Don't create a commit when bumping version")
    repo_parser.add_argument("--no-tag", action="store_true", help="Don't create a tag when bumping version")
    repo_parser.add_argument("--no-dirty", action="store_true", help="Don't allow dirty working directory")
    
    # Fix command - Enhanced with more options
    fix_parser = subparsers.add_parser("fix", help="Fix shell script and workflow issues")
    fix_group = fix_parser.add_mutually_exclusive_group(required=True)
    fix_group.add_argument("--workflow-script", action="store_true", help="Fix publish_to_github.sh")
    fix_group.add_argument("--shell-compat", action="store_true", help="Fix shell compatibility issues")
    fix_group.add_argument("--setup-bumpversion", action="store_true", 
                         help="Set up bump-my-version with proper uv integration")
    fix_group.add_argument("--create-bat-wrapper", metavar="SCRIPT", 
                         help="Create a Windows .bat wrapper for a shell script")
    fix_group.add_argument("--all", action="store_true", help="Fix all detected issues")
    
    fix_parser.add_argument("--path", help="Path to the script to fix")
    fix_parser.add_argument("--commit", action="store_true", help="Commit changes when fixing workflows")
    fix_parser.add_argument("--no-uv", action="store_true", help="Don't use uv for bump-my-version")
    fix_parser.add_argument("--force", action="store_true", help="Force overwrite of existing files")
    fix_parser.add_argument("--with-bumpversion", action="store_true", 
                         help="Include bump-my-version setup when using --all")
    
    # Process command - New section for process_guardian functionality
    process_parser = subparsers.add_parser("process", help="Process monitoring and control commands")
    process_group = process_parser.add_mutually_exclusive_group(required=True)
    process_group.add_argument("--list", action="store_true", help="List monitored processes")
    process_group.add_argument("--kill-all", action="store_true", help="Kill all monitored processes")
    process_group.add_argument("--start-watchdog", action="store_true", help="Start the process guardian watchdog")
    process_group.add_argument("--stop-watchdog", action="store_true", help="Stop the process guardian watchdog")
    process_group.add_argument("--status", action="store_true", help="Check status of the process guardian watchdog")
    process_group.add_argument("--monitor", action="store_true", help="Run a command with process monitoring")
    
    # Process monitor options
    process_parser.add_argument("--daemon", action="store_true", help="Run watchdog as daemon")
    process_parser.add_argument("--show-log", action="store_true", help="Show recent log entries")
    process_parser.add_argument("--timeout", type=int, help="Timeout in seconds")
    process_parser.add_argument("--max-memory", type=int, help="Maximum memory usage in MB")
    process_parser.add_argument("--process-name", help="Process name to monitor")
    process_parser.add_argument("command", nargs="*", help="Command to run with monitoring")
    
    # Parse arguments
    args = parser.parse_args()
    
    # Process commands
    if args.command == "version":
        return version_command(args)
    elif args.command == "logs":
        return logs_command(args)
    elif args.command == "workflow":
        return workflow_command(args)
    elif args.command == "repo":
        return repo_command(args)
    elif args.command == "process":
        return process_command(args)
    elif args.command == "fix":
        return fix_command(args)
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())