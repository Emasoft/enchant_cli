#!/bin/bash
# ensure_env.sh - Script to ensure a clean, isolated environment for the project
# Include this script at the beginning of all shell scripts with: source "$(dirname "${BASH_SOURCE[0]}")/ensure_env.sh"

# Get the script directory to use relative paths
if [ -z "$SCRIPT_DIR" ]; then
    SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
fi
VENV_DIR="$SCRIPT_DIR/.venv"

# Deactivate any active conda environments first
if [ -n "$CONDA_PREFIX" ]; then
    echo "🔄 Deactivating conda environment: $CONDA_PREFIX"
    conda deactivate 2>/dev/null || true
fi

# Deactivate any virtual environment
if [ -n "$VIRTUAL_ENV" ]; then
    echo "🔄 Deactivating virtual environment: $VIRTUAL_ENV"
    deactivate 2>/dev/null || true
fi

# Clean PATH from conflicting Python environments
echo "🔄 Cleaning PATH from external Python environments..."
PATH=$(echo $PATH | tr ":" "\n" | grep -v "site-packages" | grep -v "ComfyUI" | tr "\n" ":" | sed 's/:$//')

# Ensure the project's virtual environment exists
if [ ! -d "$VENV_DIR" ]; then
    echo "⚠️ Virtual environment not found. Creating with uv..."
    if ! command -v uv &> /dev/null; then
        echo "⚠️ uv not found. Installing..."
        pip install --user uv || { echo >&2 "❌ Failed to install uv."; exit 1; }
    fi
    uv venv "$VENV_DIR" || { echo >&2 "❌ Failed to create virtual environment."; exit 1; }
    echo "✅ Virtual environment created successfully."
fi

# Define the Python command path for use in scripts
PYTHON_CMD="$VENV_DIR/bin/python"
if [ ! -f "$PYTHON_CMD" ]; then
    echo >&2 "❌ Python not found in virtual environment. Something went wrong with environment setup."
    exit 1
fi

# Activate the project's virtual environment
echo "🔄 Activating project environment: $VENV_DIR"
source "$VENV_DIR/bin/activate"
if [ "$VIRTUAL_ENV" != "$VENV_DIR" ]; then
    echo "⚠️ Failed to activate project environment. Using explicit paths instead."
else
    echo "✅ Activated environment: $VIRTUAL_ENV"
    # Verify Python is the one from our environment
    ACTIVE_PYTHON=$(which python)
    if [[ "$ACTIVE_PYTHON" != "$VENV_DIR"* ]]; then
        echo "⚠️ Warning: Active Python ($ACTIVE_PYTHON) is not from our environment!"
        echo "   Using explicit paths as fallback."
    else
        echo "✅ Using Python: $ACTIVE_PYTHON"
    fi
fi

# Check which pip will be used
PIP_CMD=$(which pip)
echo "📦 Using pip: $PIP_CMD"

# Return clean environment success status
return 0