#!/bin/bash

# Return error if executed directly - MUST BE PLACED AT THE BEGINNING
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    echo "Error: This script cannot be executed directly. All DHT scripts can only be called by the DHT Launcher in the project root. Please run dhtl.sh (or dhtl.bat) followed by the action you want to execute. For more informations use dhtl.sh --help"
    exit 1
fi

# Process Guardian Wrapper Script
# 
# This script provides a convenient way to run commands with the process guardian.
# It prevents processes from using too much memory or running indefinitely.
#
# Usage: 
#   ./guard-process.sh [options] -- command [args]
#
# Options:
#   --timeout SECONDS     Maximum runtime in seconds (default: 900s/15min)
#   --max-memory MB       Maximum memory usage in MB (default: 1024MB/1GB)
#   --max-concurrent N    Maximum number of concurrent processes (default: 3)
#   --max-total-memory MB Maximum total memory usage in MB (default: 3072MB/3GB)
#   --monitor PROCESS     Specific process name to monitor
#   --cmd-pattern PATTERN Command pattern to match (regex)
#   --no-kill-duplicates  Don't kill duplicate process instances
#   --log-file PATH       Path to log file
#
# Examples:
#   ./guard-process.sh -- npm install
#   ./guard-process.sh --timeout 300 --max-memory 1024 -- pytest tests/
#   ./guard-process.sh --monitor bump-my-version -- hooks/bump_version.sh

set -eo pipefail

# Get script directory

# Check if Python is available
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo "❌ Error: Python is not installed or not in PATH"
    exit 1
fi

# Check if psutil is installed
if ! $PYTHON_CMD -c "import psutil" &> /dev/null; then
    echo "📦 Installing required dependency: psutil"
    $PYTHON_CMD -m pip install psutil
fi

# Default values - reduced for better memory efficiency
TIMEOUT=900
MAX_MEMORY=512  # Reduced from 1024
MAX_CONCURRENT=3
MAX_TOTAL_MEMORY=2048  # Reduced from 3072
MONITOR=""
CMD_PATTERN=""
KILL_DUPLICATES=true
LOG_FILE="$HOME/.process_guardian/process_guardian.log"

# Enable memory optimizations based on process type
OPTIMIZE_MEMORY=true

# Process arguments
POSITIONAL_ARGS=()
while [[ $# -gt 0 ]]; do
    case $1 in
        --timeout)
            TIMEOUT="$2"
            shift 2
            ;;
        --max-memory)
            MAX_MEMORY="$2"
            shift 2
            ;;
        --max-concurrent)
            MAX_CONCURRENT="$2"
            shift 2
            ;;
        --max-total-memory)
            MAX_TOTAL_MEMORY="$2"
            shift 2
            ;;
        --monitor)
            MONITOR="$2"
            shift 2
            ;;
        --cmd-pattern)
            CMD_PATTERN="$2"
            shift 2
            ;;
        --no-kill-duplicates)
            KILL_DUPLICATES=false
            shift
            ;;
        --log-file)
            LOG_FILE="$2"
            shift 2
            ;;
        --no-optimize)
            OPTIMIZE_MEMORY=false
            shift
            ;;
        --)
            shift
            POSITIONAL_ARGS+=("$@")
            break
            ;;
        *)
            POSITIONAL_ARGS+=("$1")
            shift
            ;;
    esac
done

# Check if command is provided
if [ ${#POSITIONAL_ARGS[@]} -eq 0 ]; then
    echo "❌ Error: No command provided"
    echo "Usage: $0 [options] -- command [args]"
    exit 1
fi

# Build process guardian command
GUARDIAN_CMD=("$PYTHON_CMD" -m helpers.shell.process_guardian)

if [ -n "$MONITOR" ]; then
    GUARDIAN_CMD+=(--monitor "$MONITOR")
fi

if [ -n "$CMD_PATTERN" ]; then
    GUARDIAN_CMD+=(--cmd-pattern "$CMD_PATTERN")
fi

GUARDIAN_CMD+=(--timeout "$TIMEOUT" --max-memory "$MAX_MEMORY" --max-concurrent "$MAX_CONCURRENT" --max-total-memory "$MAX_TOTAL_MEMORY")

if [ "$KILL_DUPLICATES" = false ]; then
    GUARDIAN_CMD+=(--no-kill-duplicates)
fi

GUARDIAN_CMD+=(--log-file "$LOG_FILE")

# Add the command to execute
GUARDIAN_CMD+=("${POSITIONAL_ARGS[@]}")

# Apply memory optimizations based on process type if enabled
if [ "$OPTIMIZE_MEMORY" = true ]; then
    # Get the first command part to determine process type
    PROCESS_CMD="${POSITIONAL_ARGS[0]}"
    
    # Apply Node.js specific optimizations
    if [[ "$PROCESS_CMD" == "node" || "$PROCESS_CMD" == "npm" || "$PROCESS_CMD" == "npx" ]]; then
        # Set memory limit for Node.js processes
        export NODE_OPTIONS="--max-old-space-size=${MAX_MEMORY}"
        echo "🧠 Applied Node.js memory optimizations (--max-old-space-size=${MAX_MEMORY})"
    
    # Apply Python specific optimizations
    elif [[ "$PROCESS_CMD" == "python" || "$PROCESS_CMD" == "python3" || "$PROCESS_CMD" == *".py" ]]; then
        export PYTHONOPTIMIZE=1
        export PYTHONHASHSEED=0
        export PYTHONDONTWRITEBYTECODE=1
        echo "🧠 Applied Python memory optimizations"
    fi
fi

# Print summary
echo "🛡️  Process Guardian"
echo "   Command: ${POSITIONAL_ARGS[*]}"
echo "   Timeout: ${TIMEOUT}s"
echo "   Max Memory: ${MAX_MEMORY}MB per process"
echo "   Max Concurrent Processes: ${MAX_CONCURRENT}"
echo "   Max Total Memory: ${MAX_TOTAL_MEMORY}MB"
echo "   Memory Optimization: $([ "$OPTIMIZE_MEMORY" = true ] && echo "Enabled" || echo "Disabled")"
if [ -n "$MONITOR" ]; then
    echo "   Monitoring: $MONITOR"
fi
if [ -n "$CMD_PATTERN" ]; then
    echo "   Command Pattern: $CMD_PATTERN"
fi
echo "   Log: $LOG_FILE"
echo ""

# Run the process guardian
"${GUARDIAN_CMD[@]}"
EXIT_CODE=$?

# Clean up
if [ "$OPTIMIZE_MEMORY" = true ]; then
    if [[ "$PROCESS_CMD" == "node" || "$PROCESS_CMD" == "npm" || "$PROCESS_CMD" == "npx" ]]; then
        unset NODE_OPTIONS
    elif [[ "$PROCESS_CMD" == "python" || "$PROCESS_CMD" == "python3" || "$PROCESS_CMD" == *".py" ]]; then
        unset PYTHONOPTIMIZE
        unset PYTHONHASHSEED
        unset PYTHONDONTWRITEBYTECODE
    fi
fi

# Forward the exit code
exit $EXIT_CODE
