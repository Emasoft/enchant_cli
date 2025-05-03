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
search_logs() {
    local search_pattern="$1"
    local case_sensitive="${2:-false}"
    local max_results="${3:-50}"
    
    print_header "Searching logs for pattern: '$search_pattern'"
    
    if [ -z "$search_pattern" ]; then
        print_error "Search pattern is required"
        return 1
    fi
    
    # Verify logs directory exists
    if [ ! -d "logs" ]; then
        print_info "No logs directory found - creating it"
        mkdir -p logs
        return 1
    fi
    
    # Setup grep options
    local grep_opts="-n"
    if [ "$case_sensitive" = "false" ]; then
        grep_opts="$grep_opts -i"
    fi
    
    # Get all log files
    local all_logs=()
    for log_file in logs/workflow_*.log; do
        if [ -f "$log_file" ] && ! [[ "$log_file" == *".errors" || "$log_file" == *".classified" ]]; then
            all_logs+=("$log_file")
        fi
    done
    
    # Sort by timestamp, newest first
    IFS=$'\n' sorted_logs=($(sort -r <<< "${all_logs[*]}"))
    unset IFS
    
    local total_matches=0
    local files_with_matches=0
    local results_file=$(mktemp)
    
    # Search each file
    for log_file in "${sorted_logs[@]}"; do
        local matches=$(grep $grep_opts -A 2 -B 2 -E "$search_pattern" "$log_file" | head -n "$max_results" 2>/dev/null)
        
        if [ -n "$matches" ]; then
            run_id=$(basename "$log_file" | cut -d '_' -f 2)
            timestamp=$(basename "$log_file" | cut -d '_' -f 3 | cut -d '.' -f 1)
            
            # Try to get workflow name
            local workflow_type="Unknown"
            if grep -q -i "Tests" "$log_file" 2>/dev/null; then
                workflow_type="Tests"
            elif grep -q -i "Auto Release" "$log_file" 2>/dev/null; then
                workflow_type="Auto Release"
            fi
            
            # Count matches
            local match_count=$(echo "$matches" | grep -c -E "$search_pattern")
            total_matches=$((total_matches + match_count))
            files_with_matches=$((files_with_matches + 1))
            
            # Output to temp file
            echo -e "\n\033[1;36m=== $workflow_type workflow ($timestamp) - Run ID: $run_id - $match_count matches ===\033[0m" >> "$results_file"
            echo "File: $log_file" >> "$results_file"
            echo "───────────────────────────────────────────────────────────────" >> "$results_file"
            echo "$matches" >> "$results_file"
            echo "───────────────────────────────────────────────────────────────" >> "$results_file"
            
            # Limit total files searched
            if [ "$files_with_matches" -ge 5 ]; then
                echo -e "\nMaximum number of files reached, stopping search." >> "$results_file"
                break
            fi
        fi
    done
    
    # Display results
    if [ "$total_matches" -gt 0 ]; then
        print_success "Found $total_matches matches in $files_with_matches files."
        cat "$results_file"
    else
        print_warning "No matches found for '$search_pattern'"
    fi
    
    rm -f "$results_file"
    return 0
}

# Function to generate statistics from log files
find_local_logs_after_last_commit() {
    local workflow_name="$1"  # Optional workflow name filter
    local target_count="${2:-1}"  # Number of logs to return (default 1)
    
    # Get the date of the last commit
    local last_commit_date
    last_commit_date=$(git log -1 --format="%cd" --date=format:"%Y%m%d-%H%M%S" 2>/dev/null)
    
    if [ -z "$last_commit_date" ]; then
        print_warning "Could not determine last commit date, using all logs"
        # List all log files
        # Check if logs directory exists first
        if [ -d "logs" ]; then
            find logs -name "workflow_*.log" -not -name "*.errors" -not -name "*.classified" | sort -n
        fi
        return
    fi
    
    print_info "Finding logs created after last commit ($last_commit_date)"
    
    # Verify logs directory exists
    if [ ! -d "logs" ]; then
        print_info "No logs directory found - creating it"
        mkdir -p logs
        return
    fi
    
    # Find all log files matching the workflow name if specified
    local all_logs=()
    
    if [ -n "$workflow_name" ]; then
        # Find logs that might contain the specified workflow name
        for log_file in logs/workflow_*.log; do
            if [ -f "$log_file" ] && ! [[ "$log_file" == *".errors" || "$log_file" == *".classified" ]]; then
                # Check if the log file contains the workflow name (case insensitive)
                if grep -q -i "$workflow_name" "$log_file" 2>/dev/null; then
                    all_logs+=("$log_file")
                fi
            fi
        done
    else
        # No workflow name specified, get all logs
        for log_file in logs/workflow_*.log; do
            if [ -f "$log_file" ] && ! [[ "$log_file" == *".errors" || "$log_file" == *".classified" ]]; then
                all_logs+=("$log_file")
            fi
        done
    fi
    
    # Sort logs by timestamp in filename
    IFS=$'\n' sorted_logs=($(sort -n <<< "${all_logs[*]}"))
    unset IFS
    
    # Filter logs created after the last commit
    local recent_logs=()
    for log_file in "${sorted_logs[@]}"; do
        # Extract timestamp from filename (format: workflow_ID_YYYYMMDD-HHMMSS.log)
        local log_timestamp
        log_timestamp=$(echo "$log_file" | grep -o "[0-9]\{8\}-[0-9]\{6\}")
        
        # Compare to last commit date, keep if newer
        if [[ "$log_timestamp" > "$last_commit_date" ]]; then
            recent_logs+=("$log_file")
        fi
    done
    
    # Return the most recent logs, limited by target_count
    if [ ${#recent_logs[@]} -gt 0 ]; then
        # Get the most recent logs
        local count=0
        for ((i=${#recent_logs[@]}-1; i>=0; i--)); do
            echo "${recent_logs[i]}"
            count=$((count + 1))
            if [ "$count" -eq "$target_count" ]; then
                break
            fi
        done
        return 0
    fi
    
    # If no logs after commit, return the most recent logs regardless of date
    if [ ${#sorted_logs[@]} -gt 0 ]; then
        print_warning "No logs found after last commit, using most recent logs instead"
        local count=0
        for ((i=${#sorted_logs[@]}-1; i>=0; i--)); do
            echo "${sorted_logs[i]}"
            count=$((count + 1))
            if [ "$count" -eq "$target_count" ]; then
                break
            fi
        done
        return 0
    fi
    
    return 1
}

# Function to search across all log files
