#!/bin/bash
# Helper CLI wrapper script for Unix-like systems

set -e

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    if command -v python &> /dev/null; then
        PYTHON_CMD="python"
    else
        echo "❌ Error: Python is not installed or not in PATH"
        exit 1
    fi
else
    PYTHON_CMD="python3"
fi

# Ensure the Python module is available in the path
export PYTHONPATH="$SCRIPT_DIR:$PYTHONPATH"

# Check if running in an activated environment already
if [ -n "$VIRTUAL_ENV" ]; then
    # Already in a virtual environment, just run the command
    $PYTHON_CMD -m helpers.cli "$@"
    exit $?
fi

# Check if the project has a virtual environment
if [ -d "$SCRIPT_DIR/.venv" ]; then
    # Activate the virtual environment and run the command
    source "$SCRIPT_DIR/.venv/bin/activate"
    python -m helpers.cli "$@"
    exit $?
fi

# If running directly with system Python, we still need to ensure proper environment
if command -v uv >/dev/null 2>&1; then
    # First try with global uv if available
    uv pip install -e "$SCRIPT_DIR"
    uv sync
    $PYTHON_CMD -m helpers.cli "$@"
else
    # Fall back to system Python
    $PYTHON_CMD -m pip install -e "$SCRIPT_DIR"
    $PYTHON_CMD -m helpers.cli "$@"
fi