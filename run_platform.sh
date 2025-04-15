#!/bin/bash
# Platform detection wrapper script
# Automatically detects the platform and runs the appropriate commands

set -euo pipefail

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

# Get the command name from the script name
SCRIPT_NAME=$(basename "$0" .sh)
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