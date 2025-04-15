#!/bin/bash
# Script to completely reinitialize the environment without any external references
# This ensures a clean, isolated virtual environment for the project

set -euo pipefail

# Find script directory for relative paths
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
VENV_DIR="$SCRIPT_DIR/.venv"

echo "🧹 Cleaning up existing virtual environment..."
rm -rf "$VENV_DIR"
echo "✅ Removed existing environment"

# Ensure uv is available 
if ! command -v uv &> /dev/null; then
    echo "⚠️ Warning: 'uv' command not found. Trying to install it using pip..."
    
    # Find a system Python to install uv with
    if command -v python3 &> /dev/null; then
        SYSTEM_PYTHON="python3"
    elif command -v python &> /dev/null; then
        SYSTEM_PYTHON="python"
    else
        echo "❌ Error: Cannot find Python executable. Please install Python 3.9+ and try again."
        exit 1
    fi
    
    echo "🐍 Using system Python: $($SYSTEM_PYTHON --version)"
    $SYSTEM_PYTHON -m pip install uv
    
    # Verify uv was installed
    if ! command -v uv &> /dev/null; then
        echo "❌ Failed to install uv. Please install manually with: python -m pip install uv"
        exit 1
    fi
fi

echo "🔨 Creating fresh virtual environment with uv..."
uv venv "$VENV_DIR"
PYTHON_CMD="$VENV_DIR/bin/python"

echo "📦 Installing dependencies..."
$PYTHON_CMD -m pip install uv
$VENV_DIR/bin/uv pip install -e .
$PYTHON_CMD -m pip install pre-commit
$PYTHON_CMD -m pip install bump-my-version

echo "🔧 Setting up pre-commit hooks..."
$PYTHON_CMD -m pre_commit install

echo "🔍 Verifying environment..."
echo "Python version: $($PYTHON_CMD --version)"
echo "uv version: $($VENV_DIR/bin/uv --version)"
echo "bump-my-version version: $($VENV_DIR/bin/bump-my-version --version)"

echo "✅ Environment successfully reinitialized!"
echo ""
echo "Next steps:"
echo "1. Run source .venv/bin/activate to activate the environment"
echo "2. Use ./run_platform.sh to execute commands in the isolated environment"
echo ""
echo "The environment is now completely isolated and uses only relative paths."