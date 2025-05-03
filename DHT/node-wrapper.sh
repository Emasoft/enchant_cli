#!/bin/bash

# Return error if executed directly - MUST BE PLACED AT THE BEGINNING
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    echo "Error: This script cannot be executed directly. All DHT scripts can only be called by the DHT Launcher in the project root. Please run dhtl.sh (or dhtl.bat) followed by the action you want to execute. For more informations use dhtl.sh --help"
    exit 1
fi

# Node.js Process Wrapper
#
# This script wraps Node.js commands to provide automatic memory management.
# It starts the Process Guardian when needed and stops it when all Node.js
# processes have completed.
#
# Usage:
#   ./node-wrapper.sh node [args...]
#   ./node-wrapper.sh npm [args...]
#   ./node-wrapper.sh npx [args...]

set -e

# Get the script directory

# Command to run
if [ $# -eq 0 ]; then
    echo "Usage: $0 node|npm|npx [arguments...]"
    exit 1
fi

COMMAND="$1"
shift

# Check if the command is a Node.js related command
if [[ "$COMMAND" != "node" && "$COMMAND" != "npm" && "$COMMAND" != "npx" ]]; then
    echo "Error: This wrapper only supports node, npm, and npx commands."
    exit 1
fi

# Function to check for psutil
check_psutil() {
    python3 -c "import psutil" 2>/dev/null || {
        echo "Installing psutil..."
        python3 -m pip install psutil
    }
}

# Function to run the command and register it with the process guardian
run_with_guardian() {
    # Set memory limit for Node.js processes using NODE_OPTIONS environment variable
    # This helps prevent Node.js from consuming too much memory
    export NODE_OPTIONS="--max-old-space-size=512"
    
    # Log what we're about to do
    echo "Running $COMMAND with NODE_OPTIONS=$NODE_OPTIONS"
    
    # Start the node process with memory optimization
    "$COMMAND" "$@" &
    NODE_PID=$!
    
    # Register the process with the guardian
    python3 "$SCRIPT_DIR/process-guardian-watchdog.py" register $NODE_PID
    
    # Wait for the process to complete
    wait $NODE_PID
    EXIT_CODE=$?
    
    # Unregister the process from the guardian
    python3 "$SCRIPT_DIR/process-guardian-watchdog.py" unregister $NODE_PID
    
    # Clean up
    unset NODE_OPTIONS
    
    return $EXIT_CODE
}

# Check for psutil
check_psutil

# Run the command with the guardian
echo "Running $COMMAND with Node.js Process Guardian..."
run_with_guardian "$@"
EXIT_CODE=$?

# Check guardian status
if [ -t 1 ]; then  # Only if terminal is interactive
    python3 "$SCRIPT_DIR/process-guardian-watchdog.py" status
fi

exit $EXIT_CODE
