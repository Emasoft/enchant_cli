#!/bin/bash

# Return error if executed directly - MUST BE PLACED AT THE BEGINNING
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    echo "Error: This script cannot be executed directly. All DHT scripts can only be called by the DHT Launcher in the project root. Please run dhtl.sh (or dhtl.bat) followed by the action you want to execute. For more informations use dhtl.sh --help"
    exit 1
fi

# uv_commands.sh - Helper script for common UV commands

set -eo pipefail

# Get script directory

# ANSI color codes for pretty output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color
BOLD='\033[1m'

print_header() {
    echo -e "${BOLD}${BLUE}=== $1 ===${NC}"
    echo ""
}

print_step() {
    echo -e "${CYAN}🔄 $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
    if [ -n "$2" ]; then
        exit "$2"
    fi
}

print_help() {
    print_header "UV Commands Helper"
    echo "Usage: ./uv_commands.sh [command]"
    echo ""
    echo "Available commands:"
    echo "  venv          - Create a virtual environment with uv"
    echo "  sync          - Sync dependencies from lock file"
    echo "  lock          - Update lock file from pyproject.toml"
    echo "  install-dev   - Install package in development mode"
    echo "  bump          - Bump version (minor by default)"
    echo "  bump-major    - Bump major version"
    echo "  bump-minor    - Bump minor version"
    echo "  bump-patch    - Bump patch version"
    echo "  test          - Run tests with tox-uv"
    echo "  lint          - Run linters with tox-uv"
    echo "  pre-commit    - Run pre-commit checks on all files"
    echo "  install-tools - Install common development tools"
    echo "  help          - Show this help message"
    echo ""
    echo "Examples:"
    echo "  ./uv_commands.sh venv      # Create a virtual environment"
    echo "  ./uv_commands.sh sync      # Sync dependencies"
    echo "  ./uv_commands.sh bump      # Bump minor version"
    echo ""
}

check_uv() {
    if ! command -v uv &> /dev/null; then
        print_error "uv not found. Please install it first with ./install_uv.sh" 1
    fi
}

cmd_venv() {
    print_step "Creating virtual environment with uv..."
    if [ -d "$SCRIPT_DIR/.venv" ]; then
        print_step "Removing existing virtual environment..."
        rm -rf "$SCRIPT_DIR/.venv"
    fi
    uv venv "$SCRIPT_DIR/.venv"
    print_success "Created virtual environment at $SCRIPT_DIR/.venv"
    print_step "Remember to activate it with: source .venv/bin/activate"
}

cmd_sync() {
    print_step "Syncing dependencies from lock file..."
    if [ ! -f "$SCRIPT_DIR/uv.lock" ]; then
        print_error "uv.lock not found. Run './uv_commands.sh lock' first." 1
    fi
    uv sync
    print_success "Dependencies synced from lock file"
}

cmd_lock() {
    print_step "Updating lock file from pyproject.toml..."
    uv lock
    print_success "Lock file updated"
}

cmd_install_dev() {
    print_step "Installing package in development mode..."
    uv pip install -e "$SCRIPT_DIR"
    print_success "Package installed in development mode"
}

cmd_bump() {
    local part="${1:-minor}"
    print_step "Bumping $part version..."
    uv tool run bump-my-version bump "$part" --commit --tag --allow-dirty
    print_success "Version bumped"
}

cmd_test() {
    local py_version="${1:-}"
    if [ -z "$py_version" ]; then
        # Get current Python version (e.g., py310)
        py_version=$(python -c "import sys; print(f'py{sys.version_info.major}{sys.version_info.minor}')")
    fi
    print_step "Running tests with tox-uv for $py_version..."
    tox -e "$py_version"
    print_success "Tests completed"
}

cmd_lint() {
    print_step "Running linters with tox-uv..."
    tox -e lint
    print_success "Linting completed"
}

cmd_pre_commit() {
    print_step "Running pre-commit checks on all files..."
    pre-commit run --all-files
    print_success "Pre-commit checks completed"
}

cmd_install_tools() {
    print_step "Installing common development tools..."
    uv tool install bump-my-version
    uv pip install pre-commit pre-commit-uv tox tox-uv ruff black
    print_success "Development tools installed"
}

# Main logic
if [ $# -eq 0 ]; then
    print_help
    exit 0
fi

# Check if uv is installed
check_uv

# Process command
case "$1" in
    "venv")
        cmd_venv
        ;;
    "sync")
        cmd_sync
        ;;
    "lock")
        cmd_lock
        ;;
    "install-dev")
        cmd_install_dev
        ;;
    "bump")
        cmd_bump "${2:-minor}"
        ;;
    "bump-major")
        cmd_bump "major"
        ;;
    "bump-minor")
        cmd_bump "minor"
        ;;
    "bump-patch")
        cmd_bump "patch"
        ;;
    "test")
        cmd_test "$2"
        ;;
    "lint")
        cmd_lint
        ;;
    "pre-commit")
        cmd_pre_commit
        ;;
    "install-tools")
        cmd_install_tools
        ;;
    "help"|"--help"|"-h")
        print_help
        ;;
    *)
        print_error "Unknown command: $1. Run './uv_commands.sh help' for usage." 1
        ;;
esac
