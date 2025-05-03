#!/bin/bash

# Return error if executed directly - MUST BE PLACED AT THE BEGINNING
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    echo "Error: This script cannot be executed directly. All DHT scripts can only be called by the DHT Launcher in the project root. Please run dhtl.sh (or dhtl.bat) followed by the action you want to execute. For more informations use dhtl.sh --help"
    exit 1
fi

# Stop the Process Guardian Watchdog Service


# Check if the watchdog is running
if [ ! -f ~/.process_guardian/watchdog.pid ]; then
    echo "Process Guardian Watchdog is not running"
    exit 1
fi

PID=$(cat ~/.process_guardian/watchdog.pid)
if ! ps -p $PID > /dev/null; then
    echo "Process Guardian Watchdog is not running (removing stale PID file)"
    rm ~/.process_guardian/watchdog.pid
    exit 1
fi

# Kill the watchdog
echo "Stopping Process Guardian Watchdog (PID $PID)..."
kill $PID

# Wait for process to terminate
echo "Waiting for process to terminate..."
for i in {1..5}; do
    if ! ps -p $PID > /dev/null; then
        echo "Process Guardian Watchdog stopped"
        
        # Remove PID file
        if [ -f ~/.process_guardian/watchdog.pid ]; then
            rm ~/.process_guardian/watchdog.pid
        fi
        
        exit 0
    fi
    sleep 1
done

# Force kill if still running
if ps -p $PID > /dev/null; then
    echo "Process didn't terminate gracefully, sending KILL signal..."
    kill -9 $PID
    
    # Remove PID file
    if [ -f ~/.process_guardian/watchdog.pid ]; then
        rm ~/.process_guardian/watchdog.pid
    fi
    
    echo "Process Guardian Watchdog killed"
fi

exit 0
