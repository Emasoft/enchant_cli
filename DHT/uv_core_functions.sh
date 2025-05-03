#!/usr/bin/env bash

# Return error if executed directly - MUST BE PLACED AT THE BEGINNING
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    echo "Error: This script cannot be executed directly. All DHT scripts can only be called by the DHT Launcher in the project root. Please run dhtl.sh (or dhtl.bat) followed by the action you want to execute. For more informations use dhtl.sh --help"
    exit 1
fi

#
# This file provides standardized uv functions that should be 
# sourced by other scripts to ensure consistent uv usage.

# Get the directory of this script
if [[ -z "${UV_SCRIPT_DIR}" ]]; then
    true  # Added by fix_shellcheck_errors.sh
fi

# ANSI color codes for prettier output
UV_RED='\033[0;31m'
UV_GREEN='\033[0;32m'
UV_YELLOW='\033[0;33m'
UV_BLUE='\033[0;34m'
UV_MAGENTA='\033[0;35m'
UV_CYAN='\033[0;36m'
UV_RESET='\033[0m' # No Color
UV_BOLD='\033[1m'