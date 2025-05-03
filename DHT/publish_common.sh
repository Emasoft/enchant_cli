#!/usr/bin/env bash

# Return error if executed directly - MUST BE PLACED AT THE BEGINNING
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    echo "Error: This script cannot be executed directly. All DHT scripts can only be called by the DHT Launcher in the project root. Please run dhtl.sh (or dhtl.bat) followed by the action you want to execute. For more informations use dhtl.sh --help"
    exit 1
fi

set -eo pipefail
# Shared color vars + helper functions

# - Regular updates to an existing repo
# - Automatic workflow discovery and triggering
# - Multi-method workflow triggering with fallbacks
# - Adding workflow_dispatch triggers if missing
# - Failure recovery with clear diagnostics

# ANSI color codes for prettier output - defined at top level for use throughout script
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color
BOLD='\033[1m'
UNDERLINE='\033[4m'

# Print functions for consistent formatting - defined at top level for use throughout script
print_header() {
    printf "\n${BOLD}${BLUE}=== %s ===${NC}\n" "$1"
}

print_step() {
    printf "\n${CYAN}🔄 %s${NC}\n" "$1"
}

print_info() {
    printf "${BLUE}ℹ️ %s${NC}\n" "$1"
}

print_success() {
    printf "${GREEN}✅ %s${NC}\n" "$1"
}

print_warning() {
    printf "${YELLOW}⚠️ %s${NC}\n" "$1"
}

print_error() {
    printf "${RED}❌ %s${NC}\n" "$1"
    # If error code provided as second parameter, exit with it
    if [ -n "$2" ]; then
        exit "$2"
    fi
}

# Check for required commands
check_command() {
    if ! command -v "$1" &> /dev/null; then
        print_error "$1 command not found. Please install it first." 1
        if [ "$1" = "gh" ]; then
            echo "   Install GitHub CLI from: https://cli.github.com/manual/installation"
        elif [ "$1" = "uv" ]; then
            echo "   Install uv from: https://github.com/astral-sh/uv#installation"
            echo "   Or run: curl --proto '=https' --tlsv1.2 -sSf https://astral.sh/uv/install.sh | sh"
        fi
        exit 1
    fi
}
