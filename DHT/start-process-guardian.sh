#!/bin/bash

# Return error if executed directly - MUST BE PLACED AT THE BEGINNING
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    echo "Error: This script cannot be executed directly. All DHT scripts can only be called by the DHT Launcher in the project root. Please run dhtl.sh (or dhtl.bat) followed by the action you want to execute. For more informations use dhtl.sh --help"
    exit 1
fi

# Start the Process Guardian Watchdog Service


# Create directory if it doesn't exist
mkdir -p ~/.process_guardian

# Check if the watchdog is already running
if [ -f ~/.process_guardian/watchdog.pid ]; then
    PID=$(cat ~/.process_guardian/watchdog.pid)
    if ps -p $PID > /dev/null; then
        echo "Process Guardian Watchdog is already running with PID $PID"
        exit 0
    else
        echo "Removing stale PID file"
        rm ~/.process_guardian/watchdog.pid
    fi
fi

# Start the watchdog in daemon mode with enhanced Node.js monitoring
echo "Starting Process Guardian Watchdog with enhanced Node.js monitoring..."
"$SCRIPT_DIR/process-guardian-watchdog.py" --daemon --node-monitor

# Check if it started successfully
sleep 1
if [ -f ~/.process_guardian/watchdog.pid ]; then
    PID=$(cat ~/.process_guardian/watchdog.pid)
    if ps -p $PID > /dev/null; then
        echo "Process Guardian Watchdog started with PID $PID"
        exit 0
    fi
fi

echo "Failed to start Process Guardian Watchdog"
exit 1
