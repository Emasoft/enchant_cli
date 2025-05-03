#!/bin/bash

# Return error if executed directly - MUST BE PLACED AT THE BEGINNING
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    echo "Error: This script cannot be executed directly. All DHT scripts can only be called by the DHT Launcher in the project root. Please run dhtl.sh (or dhtl.bat) followed by the action you want to execute. For more informations use dhtl.sh --help"
    exit 1
fi

# Script to completely reinitialize the environment without any external references
# This ensures a clean, isolated virtual environment for the project

set -euo pipefail

# Find script directory for relative paths
VENV_DIR="$SCRIPT_DIR/.venv"

echo "🧹 Cleaning up existing virtual environment..."
rm -rf "$VENV_DIR"
echo "✅ Removed existing environment"

# Find a system Python to bootstrap with
if command -v python3 &> /dev/null; then
    SYSTEM_PYTHON="python3"
elif command -v python &> /dev/null; then
    SYSTEM_PYTHON="python"
else
    echo "❌ Error: Cannot find Python executable. Please install Python 3.9+ and try again."
    exit 1
fi

echo "🐍 Using system Python to bootstrap environment: $($SYSTEM_PYTHON --version)"

# Ensure system Python has pip
$SYSTEM_PYTHON -m ensurepip --upgrade || true

# Ensure system Python has uv
if ! $SYSTEM_PYTHON -m pip show uv &> /dev/null; then
    echo "Installing uv package with system Python..."
    $SYSTEM_PYTHON -m pip install uv
fi

echo "🔨 Creating fresh virtual environment with venv module..."
$SYSTEM_PYTHON -m venv "$VENV_DIR"
PYTHON_CMD="$VENV_DIR/bin/python"

# Ensure and upgrade pip in the new environment
echo "📦 Installing and upgrading pip in new environment..."
$PYTHON_CMD -m ensurepip --upgrade
$PYTHON_CMD -m pip install --upgrade pip

echo "📦 Installing dependencies..."
$PYTHON_CMD -m pip install uv
$VENV_DIR/bin/uv pip install -e .
$PYTHON_CMD -m pip install pre-commit
$PYTHON_CMD -m pip install bump-my-version

echo "🔧 Setting up pre-commit hooks..."
$PYTHON_CMD -m pre_commit install

echo "🔍 Verifying environment..."
echo "Python version: $($PYTHON_CMD --version)"
echo "pip version: $($PYTHON_CMD -m pip --version)"
echo "uv version: $($VENV_DIR/bin/uv --version)"
echo "bump-my-version version: $($VENV_DIR/bin/bump-my-version --version)"

echo "✅ Environment successfully reinitialized!"
echo ""
echo "Next steps:"
echo "1. Run source .venv/bin/activate to activate the environment"
echo "2. Use ./run_platform.sh to execute commands in the isolated environment"
echo ""
echo "The environment is now completely isolated and uses only relative paths."
