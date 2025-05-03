#!/bin/bash

# Return error if executed directly - MUST BE PLACED AT THE BEGINNING
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    echo "Error: This script cannot be executed directly. All DHT scripts can only be called by the DHT Launcher in the project root. Please run dhtl.sh (or dhtl.bat) followed by the action you want to execute. For more informations use dhtl.sh --help"
    exit 1
fi

# Platform detection wrapper script
# Automatically detects the platform and runs the appropriate commands
# Uses only relative paths and project-isolated environment

set -euo pipefail

# Find script directory for relative paths

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

echo "Detected platform: $PLATFORM"

# Check for project-isolated Python environment
VENV_DIR="$SCRIPT_DIR/.venv"
PYTHON_CMD="$VENV_DIR/bin/python"

# Verify clean environment
if [ -f "$VENV_DIR/pyvenv.cfg" ]; then
    # Check for ComfyUI or other external references
    if grep -q "ComfyUI\|comfyui" "$VENV_DIR/pyvenv.cfg"; then
        echo "⚠️ Warning: Environment contains external references"
        echo "Consider running ./reinitialize_env.sh to create a clean environment"
    fi
fi

# Create environment if needed
if [ ! -f "$PYTHON_CMD" ]; then
    echo "⚠️ Project virtual environment not found at $VENV_DIR"
    echo "Creating a new virtual environment..."
    
    # Check if uv is installed
    if ! command -v uv &> /dev/null; then
        echo "⚠️ Warning: 'uv' command not found. Trying to install it..."
        # Find a system Python to install uv with
        if command -v python3 &> /dev/null; then
            SYSTEM_PYTHON="python3"
        elif command -v python &> /dev/null; then
            SYSTEM_PYTHON="python"
        else
            echo "❌ Error: Cannot find Python executable. Please install Python 3.9+ and try again."
            exit 1
        fi
        
        echo "🐍 Using system Python to install uv: $($SYSTEM_PYTHON --version)"
        $SYSTEM_PYTHON -m pip install uv
    fi
    
    echo "Creating virtual environment with uv..."
    uv venv "$VENV_DIR"
    
    echo "Installing dependencies..."
    "$VENV_DIR/bin/uv" pip install -e .
    
    echo "✅ Environment created and dependencies installed"
fi

# Get the command name from the first argument or default to "run_commands"
COMMAND=${1:-"run_commands"}
shift 2>/dev/null || true

echo "Running command: $COMMAND"

# Activate virtual environment for script execution
export VIRTUAL_ENV="$VENV_DIR"
export PATH="$VENV_DIR/bin:$PATH"

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
