#!/bin/bash

# Return error if executed directly - MUST BE PLACED AT THE BEGINNING
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    echo "Error: This script cannot be executed directly. All DHT scripts can only be called by the DHT Launcher in the project root. Please run dhtl.sh (or dhtl.bat) followed by the action you want to execute. For more informations use dhtl.sh --help"
    exit 1
fi

# Python Development Script Wrapper
#
# This script wraps Python development-related scripts to provide memory management.
# It only applies to development helper scripts, not the main application.
# It starts the Process Guardian when needed and adds the process to the monitoring list.
#
# Usage:
#   ./python-dev-wrapper.sh <script_path> [args...]
#
# Examples:
#   ./python-dev-wrapper.sh get_errorlogs.sh --help
#   ./python-dev-wrapper.sh helpers/errors/log_analyzer.py analyze logs/test.log

set -e

# Get the script directory

# Command to run
if [ $# -eq 0 ]; then
    echo "Usage: $0 <script_path> [arguments...]"
    exit 1
fi

SCRIPT_PATH="$1"
shift

# Ensure script path is valid
if [ ! -f "$SCRIPT_PATH" ] && [ ! -f "$SCRIPT_DIR/$SCRIPT_PATH" ]; then
    echo "Error: Script not found: $SCRIPT_PATH"
    echo "Make sure to provide a valid script path."
    exit 1
fi

# If not an absolute path, make it relative to script dir
if [[ "$SCRIPT_PATH" != /* ]]; then
    SCRIPT_PATH="$SCRIPT_DIR/$SCRIPT_PATH"
fi

# Get the script name for display
SCRIPT_NAME=$(basename "$SCRIPT_PATH")

# Function to check for psutil
check_psutil() {
    python3 -c "import psutil" 2>/dev/null || {
        echo "Installing psutil..."
        python3 -m pip install psutil
    }
}

# Function to run the command and register it with the process guardian
run_with_guardian() {
    # Set Python optimization environment variables
    # These help reduce memory usage for Python processes
    export PYTHONOPTIMIZE=1        # Enable basic optimizations
    export PYTHONHASHSEED=0        # Fixed hash seed improves memory usage
    export PYTHONDONTWRITEBYTECODE=1  # Don't write .pyc files
    
    # Set Python GC configuration to be more aggressive
    export PYTHONGC="threshold=100,5,5"
    
    # Determine the command to run based on file extension
    if [[ "$SCRIPT_PATH" == *.py ]]; then
        COMMAND="python3 $SCRIPT_PATH"
        echo "Running Python script with memory optimizations"
        # Start the python process with GC optimization using a wrapper script
        python3 -c "
import gc, sys, os, importlib.util
# Configure aggressive garbage collection
gc.set_threshold(100,5,5)
gc.enable()
# Load the target script as a module to control execution
spec = importlib.util.spec_from_file_location('script', '$SCRIPT_PATH')
module = importlib.util.module_from_spec(spec)
sys.argv = ['$SCRIPT_PATH'] + sys.argv[1:]
# Execute the module with memory optimizations
spec.loader.exec_module(module)
# Force final garbage collection
gc.collect()
" "$@" &
    elif [[ "$SCRIPT_PATH" == *.sh ]]; then
        COMMAND="bash $SCRIPT_PATH"
        echo "Running shell script via guardian"
        # Start the bash process
        bash "$SCRIPT_PATH" "$@" &
    else
        echo "Unsupported script type. Only .py and .sh files are supported."
        exit 1
    fi
    
    SCRIPT_PID=$!
    
    # Register the process with the guardian as a Python script
    python3 "$SCRIPT_DIR/process-guardian-watchdog.py" register $SCRIPT_PID python
    
    # Wait for the process to complete
    wait $SCRIPT_PID
    EXIT_CODE=$?
    
    # Unregister the process from the guardian
    python3 "$SCRIPT_DIR/process-guardian-watchdog.py" unregister $SCRIPT_PID python
    
    # Clean up
    unset PYTHONOPTIMIZE
    unset PYTHONHASHSEED
    unset PYTHONDONTWRITEBYTECODE
    unset PYTHONGC
    
    return $EXIT_CODE
}

# Check if the script is a development helper script
is_dev_script() {
    # Helper functions that should be monitored
    if [[ "$SCRIPT_PATH" == *helper* || 
          "$SCRIPT_PATH" == *process* || 
          "$SCRIPT_PATH" == *guard* || 
          "$SCRIPT_PATH" == *get_errorlogs* || 
          "$SCRIPT_PATH" == *publish* || 
          "$SCRIPT_PATH" == *build* || 
          "$SCRIPT_PATH" == *analyze* ]]; then
        return 0
    fi
    
    # Skip wrapping if it's the main application code
    if [[ "$SCRIPT_PATH" == */src/* || 
          "$SCRIPT_PATH" == */enchant_cli.py ]]; then
        return 1
    fi
    
    # By default, consider it a dev script
    return 0
}

# Check for psutil
check_psutil

# Run the command, either with or without the guardian
if is_dev_script; then
    echo "Running $SCRIPT_NAME with Process Guardian (Python development script)..."
    run_with_guardian "$@"
    EXIT_CODE=$?
    
    # Check guardian status if terminal is interactive
    if [ -t 1 ]; then
        python3 "$SCRIPT_DIR/process-guardian-watchdog.py" status
    fi
else
    echo "Running $SCRIPT_NAME directly (not a development script)..."
    
    # Run the script directly based on extension
    if [[ "$SCRIPT_PATH" == *.py ]]; then
        python3 "$SCRIPT_PATH" "$@"
    elif [[ "$SCRIPT_PATH" == *.sh ]]; then
        bash "$SCRIPT_PATH" "$@"
    else
        echo "Unsupported script type. Only .py and .sh files are supported."
        exit 1
    fi
    
    EXIT_CODE=$?
fi

exit $EXIT_CODE
