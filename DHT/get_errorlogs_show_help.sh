#!/usr/bin/env bash

# Return error if executed directly - MUST BE PLACED AT THE BEGINNING
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    echo "Error: This script cannot be executed directly. All DHT scripts can only be called by the DHT Launcher in the project root. Please run dhtl.sh (or dhtl.bat) followed by the action you want to execute. For more informations use dhtl.sh --help"
    exit 1
fi


# ------------------------------------------------------------------
# Ensure utility functions and constants are available
if ! declare -F print_info >/dev/null 2>&1; then
    if [ -f "$SCRIPT_DIR_LOCAL/get_errorlogs_utils.sh" ]; then
        # shellcheck disable=SC1090
        source "$SCRIPT_DIR_LOCAL/get_errorlogs_utils.sh"
    else
        echo "❌ Missing required helper: get_errorlogs_utils.sh" >&2
        exit 1
    fi
fi
# ------------------------------------------------------------------
# Auto-generated refactored helper script from get_errorlogs.sh
# Generated on 2025-04-19
show_help() {
    print_header "CLAUDE HELPER SCRIPT: GitHub Actions Workflow Logs Tool v$SCRIPT_VERSION"
    echo "Usage: $0 [global_options] <command> [command_options]"
    echo ""
    print_important "Global Options:"
    echo "  --truncate                Truncate output for readability (by default, full output is shown)"
    echo ""
    print_important "Commands:"
    echo "  list                      List recent workflow runs from GitHub"
    echo "  logs [RUN_ID]             Get logs for a specific workflow run"
    echo "  tests                     Get logs for the latest test workflow run"
    echo "  build|release             Get logs for the latest build/release workflow run"
    echo "  lint                      Get logs for the latest linting workflow run"
    echo "  docs                      Get logs for the latest documentation workflow run"
    echo "  saved                     List all saved log files"
    echo "  latest                    Get the 3 most recent logs after last commit"
    echo "  workflow|workflows        List detected workflows in the repository"
    echo "  search PATTERN [CASE_SENSITIVE] [MAX_RESULTS]"
    echo "                            Search all log files for a pattern"
    echo "  stats                     Show statistics about saved log files"
    echo "  cleanup [DAYS] [--dry-run] Clean up logs older than DAYS (default: $MAX_LOG_AGE_DAYS)"
    echo "  classify [LOG_FILE]       Classify errors in a specific log file"
    echo "  version|--version|-v      Show script version and configuration"
    echo "  help|--help|-h            Show this help message"
    echo "  (Running without arguments will auto-detect repository info and workflow status)"
    echo ""
    print_important "Features:"
    echo "  ✓ Auto-detection of repository info from git, project files, etc."
    echo "  ✓ Dynamic workflow detection and categorization by type (test, release, etc.)"
    echo "  ✓ Intelligent error classification with context and root cause analysis"
    echo "  ✓ Full output by default, with optional truncation via --truncate flag"
    echo "  ✓ Works across projects - fully portable with zero configuration"
    echo ""
    print_important "Examples:"
    echo "  $0 list                   List all recent workflow runs"
    echo "  $0 logs 123456789         Get logs for workflow run ID 123456789"
    echo "  $0 tests                  Get logs for the latest test workflow run"
    echo "  $0 saved                  List all saved log files"
    echo "  $0                        Detect repository info and available workflows"
    echo "  $0 --truncate latest      Get the 3 most recent logs with truncated output"
    echo "  $0 search \"error\"       Search all logs for 'error' (case insensitive)"
    echo "  $0 search \"Exception\" true  Search logs for 'Exception' (case sensitive)"
    echo "  $0 cleanup 10             Delete logs older than 10 days"
    echo "  $0 cleanup --dry-run      Show what logs would be deleted without deleting"
    echo "  $0 classify logs/workflow_12345.log  Classify errors in a specific log file"
    echo ""
}

# Function to list saved log files
