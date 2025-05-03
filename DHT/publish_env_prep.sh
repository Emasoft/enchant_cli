#!/usr/bin/env bash

# Return error if executed directly - MUST BE PLACED AT THE BEGINNING
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    echo "Error: This script cannot be executed directly. All DHT scripts can only be called by the DHT Launcher in the project root. Please run dhtl.sh (or dhtl.bat) followed by the action you want to execute. For more informations use dhtl.sh --help"
    exit 1
fi

set -eo pipefail
source "${SCRIPT_DIR}/publish_common.sh"

print_step "Checking for required tools..."

# Check for required system commands
check_command git
check_command curl

# Check for uv availability - explicit uv check is now required
check_command uv
print_success "Found uv: $(uv --version 2>&1 | head -n 1)"

# Check GitHub CLI
check_command gh
print_success "Found GitHub CLI: $(gh --version 2>&1 | head -n 1)"

# Validate uv installation and configuration before sourcing ensure_env.sh
print_step "Performing enhanced uv validation..."

# Validate uv installation is correct
UV_PATH=$(which uv)
print_info "Using uv from: $UV_PATH"

# Verify uv tool command works properly
if ! uv --help &>/dev/null; then
    print_error "uv installation appears to be broken. Reinstall uv via curl --proto '=https' --tlsv1.2 -sSf https://astral.sh/uv/install.sh | sh" 1
fi

# Verify uv tool command works for installing tools (critical for bump-my-version)
print_info "Verifying uv tool command functionality..."
if ! uv tool --help &>/dev/null; then
    print_error "uv tool command is not working. This is required for bump-my-version installation." 1
    print_info "Please see: https://www.andrlik.org/dispatches/til-bump-my-version-uv/"
    exit 1
fi
print_success "uv tool command is working correctly"

# Source the environment setup script which activates the virtual environment
print_step "Setting up isolated Python environment..."
source "$SCRIPT_DIR/ensure_env.sh"

# Double-check virtual environment activation
if [ -z "$VIRTUAL_ENV" ]; then
    print_error "Virtual environment activation failed in ensure_env.sh" 1
    exit 1
fi

# Set Python command variables
VENV_DIR="$VIRTUAL_ENV"
PYTHON_CMD="$VENV_DIR/bin/python"
print_info "Using virtual environment: $VENV_DIR"

# Verify Python command works
if ! $PYTHON_CMD --version &>/dev/null; then
    print_error "Python command $PYTHON_CMD not found in virtual environment." 1
    exit 1
fi

# Verify that Python is the correct version
PYTHON_VERSION=$($PYTHON_CMD --version 2>&1)
print_success "Using Python: $PYTHON_VERSION"

# Check if Python version meets minimum requirements (3.9+)
PY_MAJOR_VERSION=$(echo $PYTHON_VERSION | cut -d' ' -f2 | cut -d'.' -f1)
PY_MINOR_VERSION=$(echo $PYTHON_VERSION | cut -d' ' -f2 | cut -d'.' -f2)
if [ "$PY_MAJOR_VERSION" -lt 3 ] || ([ "$PY_MAJOR_VERSION" -eq 3 ] && [ "$PY_MINOR_VERSION" -lt 9 ]); then
    print_error "Python version must be at least 3.9. Found: $PYTHON_VERSION" 1
    exit 1
fi

# Validate pip installation in virtual environment
if ! $PYTHON_CMD -m pip --version &>/dev/null; then
    print_error "pip not found in virtual environment." 1
    exit 1
fi
print_success "pip is properly installed: $($PYTHON_CMD -m pip --version)"

# Check if uv is working inside the virtual environment
UV_VENV="$VENV_DIR/bin/uv"
if [ ! -f "$UV_VENV" ]; then
    print_warning "uv not found in virtual environment. Installing..."
    $PYTHON_CMD -m pip install uv || {
        print_error "Failed to install uv in virtual environment." 1
        exit 1
    }
    print_success "uv installed in virtual environment"
else
    print_success "uv is installed in virtual environment: $($UV_VENV --version 2>&1 | head -n 1)"
fi

# Validate uv sync functionality
print_info "Verifying uv sync functionality..."
if ! "$UV_VENV" sync --check &>/dev/null; then
    print_warning "uv sync --check failed. This might indicate environment inconsistencies."
    print_info "Attempting to sync dependencies..."
    "$UV_VENV" sync || {
        print_error "uv sync failed. Environment may be in an inconsistent state." 1
        exit 1
    }
else
    print_success "uv sync verification passed"
fi

# Validate bump-my-version installation via uv
