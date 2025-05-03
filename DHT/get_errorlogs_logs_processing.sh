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
find_local_logs() {
    local run_id="$1"
    local log_files=()
    
    # Find all matching log files
    for log_file in logs/workflow_${run_id}_*.log; do
        if [ -f "$log_file" ]; then
            log_files+=("$log_file")
        fi
    done
    
    # If logs found, return the most recent one
    if [ ${#log_files[@]} -gt 0 ]; then
        # Sort by timestamp in filename (most recent last)
        local newest_log
        newest_log=$(printf '%s\n' "${log_files[@]}" | sort -n | tail -n 1)
        echo "$newest_log"
        return 0
    fi
    
    # No local logs found
    return 1
}

# Function to perform log rotation/cleanup
process_workflow_logs() {
    local workflow_type="$1"
    local workflow_name=""
    
    # Dynamically detect workflow based on type
    workflow_name=$(detect_workflow_by_type "$workflow_type")
    print_info "Detected $workflow_type workflow: $workflow_name"
    
    # First check for saved logs
    print_info "Looking for saved logs for workflow: $workflow_name"
    # Using a more portable approach instead of readarray
    saved_logs=()
    while IFS= read -r line; do
        saved_logs+=("$line")
    done < <(find_local_logs_after_last_commit "$workflow_name" 1)
    
    if [ ${#saved_logs[@]} -gt 0 ]; then
        log_file="${saved_logs[0]}"
        run_id=$(basename "$log_file" | cut -d '_' -f 2)
        print_success "Using saved log file: $log_file (Run ID: $run_id)"
        
        # Process the saved log
        error_file="${log_file}.errors"
        classified_file="${log_file}.classified"
        
        # If we don't have the error files, create them
        if [ ! -f "$classified_file" ]; then
            print_info "Analyzing log file..."
            # Run classification
            classify_errors "$log_file" "$classified_file"
        fi
        
        # Display the error summary
        if [ -f "$classified_file" ] && [ -s "$classified_file" ]; then
            print_important "CLASSIFIED ERROR SUMMARY:"
            cat "$classified_file"
            echo ""
        fi
        
        # Display errors based on truncation
        if [ -f "$error_file" ] && [ -s "$error_file" ]; then
            print_info "Found potential errors in the log."
            
            if [ "$DO_TRUNCATE" = true ]; then
                # Truncated display
                print_info "Most significant errors (truncated, run without --truncate to see all):"
                echo "───────────────────────────────────────────────────────────────"
                head -n $DEFAULT_OUTPUT_LINES "$error_file"
                echo "..."
                echo "───────────────────────────────────────────────────────────────"
            else
                # Full display
                print_info "Full error details:"
                echo "───────────────────────────────────────────────────────────────"
                cat "$error_file"
                echo "───────────────────────────────────────────────────────────────"
            fi
        else
            print_info "No errors file found. Extracting errors now..."
            # Create an error file on the fly
            grep -n -B 5 -A 10 -E "$ERROR_PATTERN_CRITICAL" "$log_file" > "$error_file" 2>/dev/null || true
            grep -n -B 3 -A 8 -E "$ERROR_PATTERN_SEVERE" "$log_file" | grep -v -E "$ERROR_PATTERN_CRITICAL" >> "$error_file" 2>/dev/null || true
            
            if [ -s "$error_file" ]; then
                if [ "$DO_TRUNCATE" = true ]; then
                    # Truncated display
                    head -n $DEFAULT_OUTPUT_LINES "$error_file"
                    echo "..."
                else
                    # Full display
                    cat "$error_file"
                fi
            else
                print_info "No clear errors detected in $log_file"
                
                # Show a sample of the log
                if [ "$DO_TRUNCATE" = true ]; then
                    echo "───────────────────────────────────────────────────────────────"
                    head -n 20 "$log_file"
                    echo "..."
                    echo "───────────────────────────────────────────────────────────────"
                fi
            fi
        fi
    else
        # If no saved logs, try to fetch from GitHub
        print_info "No saved logs found for '$workflow_name'. Fetching from GitHub..."
        run_id=$(get_latest_workflow_run "$workflow_name")
        if [ -n "$run_id" ]; then
            get_workflow_logs "$run_id"
        else
            print_warning "No workflow runs found for '$workflow_name'. Trying any workflow..."
            run_id=$(get_latest_workflow_run "")
            if [ -n "$run_id" ]; then
                get_workflow_logs "$run_id"
            else
                print_error "No workflow runs found."
            fi
        fi
    fi
    
    return 0
}

# Function to get and analyze the latest logs
get_latest_logs() {
    print_header "Finding the 3 most recent workflow logs"
    
    # Create logs directory if it doesn't exist
    if [ ! -d "logs" ]; then
        mkdir -p logs
        print_info "Created logs directory"
    fi
    
    # Get recent logs
    # Using a more portable approach instead of readarray
    recent_logs=()
    while IFS= read -r line; do
        recent_logs+=("$line")
    done < <(find_local_logs_after_last_commit "" 3)
    
    if [ ${#recent_logs[@]} -gt 0 ]; then
        # Process each log file
        for log_file in "${recent_logs[@]}"; do
            # Skip if the log file doesn't exist
            if [ ! -f "$log_file" ]; then
                continue
            fi
            
            # Determine workflow type
            local workflow_type="Unknown"
            if grep -q -i "Tests" "$log_file" 2>/dev/null; then
                workflow_type="Tests"
            elif grep -q -i "Auto Release" "$log_file" 2>/dev/null; then
                workflow_type="Auto Release"
            elif grep -q -i "Lint" "$log_file" 2>/dev/null; then
                workflow_type="Lint"
            elif grep -q -i "Docs" "$log_file" 2>/dev/null; then
                workflow_type="Docs"
            fi
            
            print_header "Logs for workflow: $workflow_type"
            
            # Extract the run ID and timestamp from the filename
            run_id=$(basename "$log_file" | cut -d '_' -f 2)
            timestamp=$(basename "$log_file" | cut -d '_' -f 3 | cut -d '.' -f 1)
            
            print_success "Log file: $log_file (Run ID: $run_id, Timestamp: $timestamp)"
            
            # Process the saved log
            error_file="${log_file}.errors"
            classified_file="${log_file}.classified"
            
            # If we don't have the error files, create them
            if [ ! -f "$classified_file" ]; then
                print_info "Analyzing log file..."
                # Run classification
                classify_errors "$log_file" "$classified_file"
            fi
            
            # Display the error summary
            if [ -f "$classified_file" ] && [ -s "$classified_file" ]; then
                print_important "CLASSIFIED ERROR SUMMARY:"
                cat "$classified_file"
                echo ""
            else
                print_info "No classified error summary available."
            fi
            
            # Display a separator between logs
            echo "───────────────────────────────────────────────────────────────"
        done
    else
        print_error "No saved log files found after the last commit."
        print_info "Trying to fetch logs from GitHub instead..."
        
        # Fall back to fetching from GitHub
        get_workflow_runs
    fi
    
    return 0
}

# Function to show script help
