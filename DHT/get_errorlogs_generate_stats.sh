#!/usr/bin/env bash

# Return error if executed directly - MUST BE PLACED AT THE BEGINNING
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    echo "Error: This script cannot be executed directly. All DHT scripts can only be called by the DHT Launcher in the project root. Please run dhtl.sh (or dhtl.bat) followed by the action you want to execute. For more informations use dhtl.sh --help"
    exit 1
fi


# ------------------------------------------------------------------
# Ensure utility functions and constants are available
if ! declare -F print_info >/dev/null 2>&1; then
    if [ -f "$SCRIPT_DIR_LOCAL/get_errorlogs_utils.sh" ]; then
        # shellcheck disable=SC1090
        source "$SCRIPT_DIR_LOCAL/get_errorlogs_utils.sh"
    else
        echo "❌ Missing required helper: get_errorlogs_utils.sh" >&2
        exit 1
    fi
fi
# ------------------------------------------------------------------
# Auto-generated refactored helper script from get_errorlogs.sh
# Generated on 2025-04-19
generate_stats() {
    print_header "Workflow Logs Statistics"
    
    # Create logs directory if it doesn't exist
    mkdir -p logs
    
    # Count log files
    local total_logs=0
    local error_logs=0
    local test_logs=0
    local build_logs=0
    local other_logs=0
    local total_size=0
    
    # Get all log files
    for log_file in logs/workflow_*.log; do
        if [ -f "$log_file" ] && ! [[ "$log_file" == *".errors" || "$log_file" == *".classified" ]]; then
            total_logs=$((total_logs + 1))
            
            # Determine log type
            if grep -q -i "Tests" "$log_file" 2>/dev/null; then
                test_logs=$((test_logs + 1))
            elif grep -q -i "Auto Release" "$log_file" 2>/dev/null; then
                build_logs=$((build_logs + 1))
            else
                other_logs=$((other_logs + 1))
            fi
            
            # Check if it has errors
            if [ -f "${log_file}.errors" ] && [ -s "${log_file}.errors" ]; then
                error_logs=$((error_logs + 1))
            fi
            
            # Get file size
            if [[ "$OSTYPE" == "darwin"* ]]; then
                # macOS
                local file_size=$(stat -f %z "$log_file" 2>/dev/null)
            else
                # Linux
                local file_size=$(stat -c %s "$log_file" 2>/dev/null)
            fi
            total_size=$((total_size + file_size))
        fi
    done
    
    # Calculate size in MB
    local size_mb=$(echo "scale=2; $total_size / 1048576" | bc 2>/dev/null || echo "unknown")
    
    # Determine if there are logs after last commit
    local logs_after_commit=0
    # Using a more portable approach instead of readarray
    recent_logs=()
    while IFS= read -r line; do
        recent_logs+=("$line")
    done < <(find_local_logs_after_last_commit "" 50)
    logs_after_commit=${#recent_logs[@]}
    
    # Display statistics
    print_important "Log Files Summary"
    echo "───────────────────────────────────────────────────────────────"
    echo "Total log files:       $total_logs"
    echo "Files with errors:     $error_logs"
    echo "Test workflow logs:    $test_logs"
    echo "Build workflow logs:   $build_logs"
    echo "Other workflow logs:   $other_logs"
    echo "Logs after last commit: $logs_after_commit"
    echo "Total log size:        ${size_mb}MB"
    echo "───────────────────────────────────────────────────────────────"
    
    # Show latest logs
    if [ "$total_logs" -gt 0 ]; then
        print_info "Most recent logs:"
        echo "───────────────────────────────────────────────────────────────"
        
        # Get most recent logs
        local recent_logs=()
        for log_file in logs/workflow_*.log; do
            if [ -f "$log_file" ] && ! [[ "$log_file" == *".errors" || "$log_file" == *".classified" ]]; then
                recent_logs+=("$log_file")
            fi
        done
        
        # Sort by timestamp, newest first
        IFS=$'\n' sorted_logs=($(sort -r <<< "${recent_logs[*]}"))
        unset IFS
        
        # Display top 5 most recent logs
        for ((i=0; i<5 && i<${#sorted_logs[@]}; i++)); do
            log_file="${sorted_logs[$i]}"
            run_id=$(basename "$log_file" | cut -d '_' -f 2)
            timestamp=$(basename "$log_file" | cut -d '_' -f 3 | cut -d '.' -f 1)
            
            # Determine log type
            local workflow_type="Unknown"
            if grep -q -i "Tests" "$log_file" 2>/dev/null; then
                workflow_type="Tests"
            elif grep -q -i "Auto Release" "$log_file" 2>/dev/null; then
                workflow_type="Auto Release"
            fi
            
            # Check if it has errors
            local status="✓"
            if [ -f "${log_file}.errors" ] && [ -s "${log_file}.errors" ]; then
                status="✗"
            fi
            
            if [ "$status" = "✓" ]; then
                echo -e "\033[1;32m$status\033[0m $workflow_type ($timestamp) - Run ID: $run_id - $log_file"
            else
                echo -e "\033[1;31m$status\033[0m $workflow_type ($timestamp) - Run ID: $run_id - $log_file"
            fi
        done
        echo "───────────────────────────────────────────────────────────────"
    fi
    
    return 0
}

# Function to dynamically detect workflow information
