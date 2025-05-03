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
cleanup_old_logs() {
    local max_age="$1"  # In days, defaults to MAX_LOG_AGE_DAYS if not specified
    local dry_run="$2"  # Set to "true" for dry run
    
    if [ -z "$max_age" ]; then
        max_age=$MAX_LOG_AGE_DAYS
    fi
    
    print_header "Log Maintenance"
    print_info "Cleaning up logs older than $max_age days"
    
    # Create logs directory if it doesn't exist
    mkdir -p logs
    
    local old_logs=()
    local total_size=0
    local current_date=$(date +%s)
    
    # Find log files older than max_age days
    for log_file in logs/workflow_*.log logs/workflow_*.log.errors logs/workflow_*.log.classified; do
        if [ -f "$log_file" ]; then
            # Extract timestamp from filename (format: workflow_ID_YYYYMMDD-HHMMSS.log)
            local log_timestamp
            log_timestamp=$(echo "$log_file" | grep -o "[0-9]\{8\}-[0-9]\{6\}")
            
            if [ -n "$log_timestamp" ]; then
                # Different date commands for macOS and Linux
                local log_date
                if [[ "$OSTYPE" == "darwin"* ]]; then
                    # macOS
                    log_date=$(date -j -f "%Y%m%d-%H%M%S" "$log_timestamp" +%s 2>/dev/null)
                else
                    # Linux
                    log_date=$(date -d "${log_timestamp:0:8} ${log_timestamp:9:2}:${log_timestamp:11:2}:${log_timestamp:13:2}" +%s 2>/dev/null)
                fi
                
                if [ -n "$log_date" ]; then
                    # Calculate age in days
                    local age_seconds=$((current_date - log_date))
                    local age_days=$((age_seconds / 86400))
                    
                    if [ "$age_days" -gt "$max_age" ]; then
                        old_logs+=("$log_file")
                        if [[ "$OSTYPE" == "darwin"* ]]; then
                            # macOS
                            total_size=$((total_size + $(stat -f %z "$log_file" 2>/dev/null)))
                        else
                            # Linux
                            total_size=$((total_size + $(stat -c %s "$log_file" 2>/dev/null)))
                        fi
                    fi
                fi
            fi
        fi
    done
    
    # Report findings
    local file_count=${#old_logs[@]}
    local size_mb=$(echo "scale=2; $total_size / 1048576" | bc 2>/dev/null || echo "unknown")
    
    if [ "$file_count" -gt 0 ]; then
        print_info "Found $file_count log files older than $max_age days (approx. ${size_mb}MB)"
        
        if [ "$dry_run" = "true" ]; then
            print_warning "Dry run mode, not deleting any files"
            for log_file in "${old_logs[@]}"; do
                echo "Would delete: $log_file"
            done
        else
            print_warning "Deleting $file_count old log files to free up space"
            for log_file in "${old_logs[@]}"; do
                rm -f "$log_file"
                echo "Deleted: $log_file"
            done
            print_success "Cleanup completed, freed approximately ${size_mb}MB"
        fi
    else
        print_success "No old log files to clean up"
    fi
    
    # Also maintain total log count - keep only the MAX_TOTAL_LOGS most recent
    local all_logs=()
    
    # Get all log files (not errors or classified)
    for log_file in logs/workflow_*.log; do
        if [ -f "$log_file" ] && ! [[ "$log_file" == *".errors" || "$log_file" == *".classified" ]]; then
            all_logs+=("$log_file")
        fi
    done
    
    # Sort by timestamp, oldest first
    IFS=$'\n' sorted_logs=($(sort <<< "${all_logs[*]}"))
    unset IFS
    
    # Calculate how many files to delete
    local total_log_count=${#sorted_logs[@]}
    local delete_count=$((total_log_count - MAX_TOTAL_LOGS))
    
    if [ "$delete_count" -gt 0 ]; then
        print_info "Maintaining maximum of $MAX_TOTAL_LOGS log files (currently have $total_log_count)"
        
        # Delete oldest files
        if [ "$dry_run" = "true" ]; then
            print_warning "Dry run mode, not deleting any files"
            for ((i=0; i<delete_count; i++)); do
                echo "Would delete: ${sorted_logs[$i]}"
                echo "Would delete: ${sorted_logs[$i]}.errors (if exists)"
                echo "Would delete: ${sorted_logs[$i]}.classified (if exists)"
            done
        else
            for ((i=0; i<delete_count; i++)); do
                rm -f "${sorted_logs[$i]}"
                rm -f "${sorted_logs[$i]}.errors"
                rm -f "${sorted_logs[$i]}.classified"
                echo "Deleted: ${sorted_logs[$i]}"
            done
            print_success "Removed $delete_count oldest log files"
        fi
    fi
    
    return 0
}

# Function to classify errors by severity
