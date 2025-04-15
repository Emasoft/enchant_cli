#!/bin/bash
# run_publish.sh - Run publish_to_github.sh in background
# This script runs the publish_to_github.sh script in the background using nohup
# so that it continues running even if the terminal session is disconnected

set -eo pipefail

# Find script directory
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

echo "Starting publish_to_github.sh in background mode..."
echo "Output will be logged to nohup.out"
echo "This helps get around the 2-minute timeout limitation in Claude Code."

# Run publish_to_github.sh in background
nohup "$SCRIPT_DIR/publish_to_github.sh" "$@" > nohup.out 2>&1 &

# Get PID of background process
PID=$!
echo "Process started with PID: $PID"
echo "You can check the status with: cat nohup.out"
echo "To check if process is still running: ps -p $PID"

echo "Publishing process is running in the background."
echo "You can view progress with: tail -f nohup.out"