#!/bin/bash
# Platform detection wrapper script
# Automatically detects the platform and runs the appropriate commands

set -euo pipefail

# Find script directory for relative paths
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

# Detect platform
PLATFORM="unknown"
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    PLATFORM="linux"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    PLATFORM="macos"
elif [[ "$OSTYPE" == "freebsd"* ]]; then
    PLATFORM="bsd"
elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" || "$OSTYPE" == "win32" ]]; then
    PLATFORM="windows"
fi

# Check for Python environment
VENV_DIR="$SCRIPT_DIR/.venv"
if [ -d "$VENV_DIR" ] && [ -f "$VENV_DIR/bin/python" ]; then
    PYTHON_CMD="$VENV_DIR/bin/python"
    echo "🐍 Using project virtual environment Python: $PYTHON_CMD"
else
    echo "⚠️ Warning: Project virtual environment not found at $VENV_DIR"
    echo "Creating a new virtual environment..."
    
    # Check if uv is installed
    if ! command -v uv &> /dev/null; then
        echo "⚠️ Warning: 'uv' command not found. Trying to install it..."
        # Try to install uv using pip
        if command -v pip &> /dev/null; then
            pip install uv
        elif command -v pip3 &> /dev/null; then
            pip3 install uv
        else
            echo "❌ Error: Neither pip nor pip3 found. Cannot install uv."
            echo "Please install uv manually: https://github.com/astral-sh/uv"
            exit 1
        fi
    fi
    
    echo "Creating virtual environment with uv..."
    uv venv "$VENV_DIR"
    PYTHON_CMD="$VENV_DIR/bin/python"
    
    echo "Installing dependencies..."
    uv pip install -e .
    
    echo "✅ Environment created and dependencies installed"
fi

# Get the command name from the first argument or default to "run_commands"
COMMAND=${1:-"run_commands"}
shift 2>/dev/null || true

echo "Detected platform: $PLATFORM"
echo "Running command: $COMMAND"

# Run the appropriate platform-specific script if it exists
if [ -f "${COMMAND}_${PLATFORM}.sh" ]; then
    echo "Using platform-specific script: ${COMMAND}_${PLATFORM}.sh"
    bash "${COMMAND}_${PLATFORM}.sh" "$@"
elif [ -f "${COMMAND}.sh" ]; then
    echo "Using generic script: ${COMMAND}.sh"
    # For Windows compatibility with Git Bash or WSL
    if [ "$PLATFORM" = "windows" ]; then
        echo "Note: Running Unix shell script on Windows via Git Bash/WSL/Cygwin"
    fi
    bash "${COMMAND}.sh" "$@"
else
    echo "Error: No script found for command '$COMMAND'"
    echo "Neither ${COMMAND}_${PLATFORM}.sh nor ${COMMAND}.sh exists"
    exit 1
fi