#!/usr/bin/env python3
"""
CLAUDE HELPER SCRIPTS - Command-line interface

A unified command-line interface to access all helper scripts functionality.
This tool provides access to GitHub workflow management, log analysis, and
shell script compatibility fixes.

Usage:
    python -m helpers.cli [command] [options]

Commands:
    workflow    - GitHub workflow management commands
    logs        - Log analysis and error detection commands
    fix         - Fix shell script issues
    version     - Show version information
"""

import argparse
import sys
from pathlib import Path

from helpers import __version__
from helpers.errors import log_analyzer
from helpers.github import workflow_helper


def version_command(_):
    """Show version information."""
    print(f"CLAUDE HELPER SCRIPTS v{__version__}")
    print("A collection of portable Python utilities for enhancing shell scripts")
    print("\nModules:")
    print("  - github: Tools for GitHub workflow management and automation")
    print("  - errors: Tools for log analysis, error classification, and diagnostics")
    return 0


def logs_command(args):
    """Process logs analysis commands."""
    if args.analyze:
        # Run log analyzer on specified file
        return log_analyzer.main()
    elif args.latest:
        # Get the latest log file and analyze it
        log_dir = Path("logs")
        if not log_dir.exists():
            print("Error: logs directory not found", file=sys.stderr)
            return 1
            
        # Find the most recent log file
        log_files = list(log_dir.glob("*.log"))
        if not log_files:
            print("Error: No log files found in logs directory", file=sys.stderr)
            return 1
            
        # Sort by modification time (most recent first)
        log_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        latest_log = log_files[0]
        
        print(f"Analyzing most recent log file: {latest_log}")
        report, exit_code = log_analyzer.analyze_and_report(latest_log)
        print(report)
        return exit_code
    else:
        print("Error: Please specify a logs subcommand", file=sys.stderr)
        return 1


def workflow_command(args):
    """Process GitHub workflow commands."""
    if args.check:
        # Check workflow_dispatch events
        return workflow_helper.check_workflow_dispatch(args.path)
    elif args.fix:
        # Fix workflow_dispatch events
        return workflow_helper.fix_workflow_dispatch(args.path, args.dry_run)
    else:
        print("Error: Please specify a workflow subcommand", file=sys.stderr)
        return 1


def fix_command(args):
    """Process fix commands for shell scripts."""
    if args.workflow_script:
        # Fix publish_to_github.sh
        return workflow_helper.fix_workflow_script(args.path)
    elif args.shell_compat:
        # Fix shell compatibility issues
        return workflow_helper.fix_shell_compatibility(args.path)
    elif args.all:
        # Fix all issues
        result1 = workflow_helper.fix_workflow_script(
            Path.cwd() / "publish_to_github.sh"
        )
        result2 = workflow_helper.fix_shell_compatibility(
            Path.cwd() / "get_errorlogs.sh"
        )
        return max(result1, result2)  # Return non-zero if any fix failed
    else:
        print("Error: Please specify a fix subcommand", file=sys.stderr)
        return 1


def main():
    # Create the main parser
    parser = argparse.ArgumentParser(
        description="CLAUDE HELPER SCRIPTS - A unified command-line interface "
                    "for GitHub workflow management and log analysis"
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Version command
    version_parser = subparsers.add_parser("version", help="Show version information")
    
    # Logs command
    logs_parser = subparsers.add_parser("logs", help="Log analysis commands")
    logs_group = logs_parser.add_mutually_exclusive_group(required=True)
    logs_group.add_argument("--analyze", metavar="LOG_FILE", help="Analyze a log file")
    logs_group.add_argument("--latest", action="store_true", help="Analyze the most recent log file")
    
    # Workflow command
    workflow_parser = subparsers.add_parser("workflow", help="GitHub workflow commands")
    workflow_group = workflow_parser.add_mutually_exclusive_group(required=True)
    workflow_group.add_argument("--check", action="store_true", help="Check workflow_dispatch events")
    workflow_group.add_argument("--fix", action="store_true", help="Fix workflow_dispatch events")
    workflow_parser.add_argument("--path", help="Path to the workflow directory")
    workflow_parser.add_argument("--dry-run", action="store_true", help="Report issues but don't fix them")
    
    # Fix command
    fix_parser = subparsers.add_parser("fix", help="Fix shell script issues")
    fix_group = fix_parser.add_mutually_exclusive_group(required=True)
    fix_group.add_argument("--workflow-script", action="store_true", help="Fix publish_to_github.sh")
    fix_group.add_argument("--shell-compat", action="store_true", help="Fix shell compatibility issues")
    fix_group.add_argument("--all", action="store_true", help="Fix all issues")
    fix_parser.add_argument("--path", help="Path to the script to fix")
    
    # Parse arguments
    args = parser.parse_args()
    
    # Process commands
    if args.command == "version":
        return version_command(args)
    elif args.command == "logs":
        return logs_command(args)
    elif args.command == "workflow":
        return workflow_command(args)
    elif args.command == "fix":
        return fix_command(args)
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())