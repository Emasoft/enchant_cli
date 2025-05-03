#!/usr/bin/env bash

# Return error if executed directly - MUST BE PLACED AT THE BEGINNING
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    echo "Error: This script cannot be executed directly. All DHT scripts can only be called by the DHT Launcher in the project root. Please run dhtl.sh (or dhtl.bat) followed by the action you want to execute. For more informations use dhtl.sh --help"
    exit 1
fi

# Auto-generated refactored helper script from get_errorlogs.sh
# Generated on 2025-04-19
#!/bin/bash
# get_errorlogs.sh - GitHub Actions Workflow Log Analysis Tool
# Version: 1.1.0
# A portable tool for retrieving, analyzing, and classifying GitHub Actions workflow logs

# Enable strict mode for better error handling
set -o pipefail  # Fail if any command in a pipe fails

#=========================================================================
# Get script directory for relative paths

# CONFIGURATION
#=========================================================================

# Python command path - auto-detected
PYTHON_CMD="python3"


# Constants for log settings
SCRIPT_VERSION="1.0.0"
MAX_LOGS_PER_WORKFLOW=5       # Maximum number of log files to keep per workflow ID
MAX_LOG_AGE_DAYS=30           # Maximum age in days for log files before cleanup
MAX_TOTAL_LOGS=50             # Maximum total log files to keep
DEFAULT_OUTPUT_LINES=100      # Default number of lines to display in truncated mode
DO_TRUNCATE=false             # Default truncation setting

# Error pattern categories for classification
ERROR_PATTERN_CRITICAL="Process completed with exit code [1-9]|fatal error|fatal:|FATAL ERROR|Assertion failed|Segmentation fault|core dumped|killed|ERROR:|Connection refused|panic|PANIC|assert|ASSERT|terminated|abort|SIGSEGV|SIGABRT|SIGILL|SIGFPE"
ERROR_PATTERN_SEVERE="exit code [1-9]|failure:|failed with|FAILED|Exception|exception:|Error:|error:|undefined reference|Cannot find|not found|No such file|Permission denied|AccessDenied|Could not access|Cannot access|ImportError|ModuleNotFoundError|TypeError|ValueError|KeyError|AttributeError|AssertionError|UnboundLocalError|IndexError|SyntaxError|NameError|RuntimeError|unexpected|failed to|EACCES|EPERM|ENOENT|compilation failed|command failed|exited with code"
ERROR_PATTERN_WARNING="WARNING:|warning:|deprecated|Deprecated|DEPRECATED|fixme|FIXME|TODO|todo:|ignored|skipped|suspicious|insecure|unsafe|consider|recommended|inconsistent|possibly|PendingDeprecationWarning|FutureWarning|UserWarning|ResourceWarning"

# Initialize empty arrays for workflows
AVAILABLE_WORKFLOWS=()
TEST_WORKFLOWS=()
RELEASE_WORKFLOWS=()
LINT_WORKFLOWS=()
DOCS_WORKFLOWS=()
OTHER_WORKFLOWS=()

# Repository information
REPO_OWNER=""
REPO_NAME=""
REPO_FULL_NAME=""

#=========================================================================
# UTILITY FUNCTIONS
#=========================================================================

# Formatting functions for output
print_header() {
    echo -e "\033[1;36m=== $1 ===\033[0m"
}

print_info() {
    echo -e "\033[1;34mℹ️  $1\033[0m"
}

print_success() {
    echo -e "\033[1;32m✅ $1\033[0m"
}

print_warning() {
    echo -e "\033[1;33m⚠️  $1\033[0m"
}

print_error() {
    echo -e "\033[1;31m❌ $1\033[0m"
}

print_critical() {
    echo -e "\033[1;41m🔥 $1\033[0m"
}

print_severe() {
    echo -e "\033[1;35m⛔ $1\033[0m"
}

print_important() {
    echo -e "\033[1;37m👉 $1\033[0m"
}
