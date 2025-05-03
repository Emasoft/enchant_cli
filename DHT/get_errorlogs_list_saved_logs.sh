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
list_saved_logs() {
    # List saved logs
    print_header "Listing saved workflow logs"
    
    # Check if logs directory exists
    if [ ! -d "logs" ]; then
        print_warning "No logs directory found. Creating one..."
        mkdir -p logs
        print_info "No saved logs yet. Use 'list' to see available workflows and 'logs [RUN_ID]' to fetch logs."
        return 0
    fi
    
    found_logs=0
    for log_file in logs/workflow_*.log; do
        if [ -f "$log_file" ] && ! [[ "$log_file" == *".errors" || "$log_file" == *".classified" ]]; then
            found_logs=$((found_logs + 1))
            run_id=$(basename "$log_file" | cut -d '_' -f 2)
            timestamp=$(basename "$log_file" | cut -d '_' -f 3 | cut -d '.' -f 1)
            
            # Determine workflow type by checking content of the file
            workflow_type="Unknown"
            for workflow in "${AVAILABLE_WORKFLOWS[@]}"; do
                if grep -q -i "$workflow" "$log_file" 2>/dev/null; then
                    workflow_type="$workflow"
                    break
                fi
            done
            
            # Check if it has errors
            status="✓"
            if [ -f "${log_file}.errors" ] && [ -s "${log_file}.errors" ]; then
                status="✗"
                echo -e "\033[1;31m$status\033[0m [$workflow_type] $log_file - Run ID: $run_id, Timestamp: $timestamp"
            else
                echo -e "\033[1;32m$status\033[0m [$workflow_type] $log_file - Run ID: $run_id, Timestamp: $timestamp"
            fi
        fi
    done
    
    if [ "$found_logs" -eq 0 ]; then
        print_warning "No saved log files found."
        print_info "Use 'list' to see available workflows and 'logs [RUN_ID]' to fetch logs."
    fi
    
    return 0
}

#=========================================================================
# MAIN SCRIPT EXECUTION
#=========================================================================

# Detect and validate Python interpreter
print_info "Detecting Python interpreter..."
if command -v python3 &>/dev/null; then
    PYTHON_CMD="python3"
elif command -v python &>/dev/null; then
    PYTHON_CMD="python"
else
    print_warning "No Python interpreter found. Enhanced analysis will not be available."
fi

# Verify Python version
if [ -n "$PYTHON_CMD" ]; then
    PY_VERSION=$($PYTHON_CMD --version 2>&1)
    print_success "Using Python: $PY_VERSION"
fi


# Check for global options
DO_TRUNCATE=false
for arg in "$@"; do
    if [ "$arg" = "--truncate" ]; then
        DO_TRUNCATE=true
        # Remove the --truncate option from arguments
        set -- "${@/$arg/}"
        print_info "Output will be truncated for readability"
    fi
done

# Check for help flags which don't need initialization
if [[ "$1" == "help" || "$1" == "--help" || "$1" == "-h" ]]; then
    show_help
    exit 0
fi

# Check for version flag which has minimal initialization
if [[ "$1" == "version" || "$1" == "--version" || "$1" == "-v" ]]; then
    print_header "CLAUDE HELPER SCRIPT: GitHub Actions Workflow Logs Tool v$SCRIPT_VERSION"
    echo "Configured settings:"
    echo "  - Max logs per workflow: $MAX_LOGS_PER_WORKFLOW"
    echo "  - Max log age (days): $MAX_LOG_AGE_DAYS"
    echo "  - Max total logs: $MAX_TOTAL_LOGS"
    echo "  - Default output lines: $DEFAULT_OUTPUT_LINES"
    echo "  - Truncation: $([ "$DO_TRUNCATE" = true ] && echo "Enabled" || echo "Disabled")"
    
    # Try to detect repository information if possible
    detect_repository_info >/dev/null 2>&1
    if [ -n "$REPO_FULL_NAME" ]; then
        echo "Repository: $REPO_FULL_NAME"
    fi
    
    exit 0
fi

# Initialize script environment
print_header "CLAUDE HELPER SCRIPT: GitHub Actions Workflow Logs Tool v$SCRIPT_VERSION"

# Make logs directory if it doesn't exist
mkdir -p logs

# Detect repository information
detect_repository_info

# Detect available workflows
detect_workflows

# Process command
if [ $# -eq 0 ]; then
    # Auto-detect repository and workflow status
    print_header "Automatic Workflow Analysis"
    
    # Get workflow statistics
    get_workflow_stats
    
    # Display workflow summary
    display_workflow_summary
    
    # Check for any failed workflows
    if [ "$recent_failure_count" -gt 0 ]; then
        print_warning "Found $recent_failure_count failed workflows. Checking for logs..."
        
        # Try to find saved logs for the latest failed workflow
        # Using a more portable approach instead of readarray
        recent_logs=()
        while IFS= read -r line; do
            recent_logs+=("$line")
        done < <(find_local_logs_after_last_commit "" 3)
        if [ ${#recent_logs[@]} -gt 0 ]; then
            # Process the most recent log file
            get_latest_logs
        else
            # Try to fetch failed workflows from GitHub
            print_info "No saved logs found. Fetching from GitHub..."
            
            # Look for failed workflow runs
            if command -v gh &>/dev/null && [ -n "$REPO_FULL_NAME" ]; then
                failed_run_id=$(gh run list --repo "$REPO_FULL_NAME" --status failure --limit 1 --json databaseId -q '.[0].databaseId' 2>/dev/null)
                
                if [ -n "$failed_run_id" ]; then
                    print_warning "Found failed workflow run with ID: $failed_run_id"
                    get_workflow_logs "$failed_run_id"
                else
                    print_info "No failed workflow runs found with GitHub CLI."
                    print_info "Showing workflow statistics:"
                    generate_stats
                fi
            else
                print_info "GitHub CLI not available or not authenticated."
                print_info "Showing local workflow statistics:"
                generate_stats
            fi
        fi
    else
        # No failures detected, show general workflow stats
        print_info "No recent workflow failures detected. Showing workflow statistics:"
        generate_stats
    fi
    
    exit 0
fi

# Process specific commands
case "$1" in
    list)
        get_workflow_runs
        ;;
    logs)
        if [ -z "$2" ]; then
            print_error "Run ID is required"
            print_info "Usage: $0 logs [RUN_ID]"
            exit 1
        fi
        get_workflow_logs "$2"
        ;;
    saved)
        list_saved_logs
        ;;
    search)
        if [ -z "$2" ]; then
            print_error "Search pattern is required"
            print_info "Usage: $0 search PATTERN [CASE_SENSITIVE] [MAX_RESULTS]"
            exit 1
        fi
        search_logs "$2" "${3:-false}" "${4:-50}"
        ;;
    stats)
        generate_stats
        ;;
    cleanup)
        max_age="${2:-$MAX_LOG_AGE_DAYS}"
        if [[ "$3" == "--dry-run" || "$2" == "--dry-run" ]]; then
            cleanup_old_logs "$max_age" "true"
        else
            cleanup_old_logs "$max_age" "false"
        fi
        ;;
    workflow|workflows)
        print_header "Detected GitHub Workflows"
        print_info "The following workflows were detected for $REPO_FULL_NAME:"
        
        # Print workflows categorized by type
        if [ ${#TEST_WORKFLOWS[@]} -gt 0 ]; then
            print_info "Testing Workflows:"
            for workflow in "${TEST_WORKFLOWS[@]}"; do
                echo "  - $workflow"
            done
            echo ""
        fi
        
        if [ ${#RELEASE_WORKFLOWS[@]} -gt 0 ]; then
            print_info "Release/Deployment Workflows:"
            for workflow in "${RELEASE_WORKFLOWS[@]}"; do
                echo "  - $workflow"
            done
            echo ""
        fi
        
        if [ ${#LINT_WORKFLOWS[@]} -gt 0 ]; then
            print_info "Linting/Quality Workflows:"
            for workflow in "${LINT_WORKFLOWS[@]}"; do
                echo "  - $workflow"
            done
            echo ""
        fi
        
        if [ ${#DOCS_WORKFLOWS[@]} -gt 0 ]; then
            print_info "Documentation Workflows:"
            for workflow in "${DOCS_WORKFLOWS[@]}"; do
                echo "  - $workflow"
            done
            echo ""
        fi
        
        if [ ${#OTHER_WORKFLOWS[@]} -gt 0 ]; then
            print_info "Other Workflows:"
            for workflow in "${OTHER_WORKFLOWS[@]}"; do
                echo "  - $workflow"
            done
            echo ""
        fi
        
        print_info "Total workflows detected: ${#AVAILABLE_WORKFLOWS[@]}"
        ;;
    classify)
        if [ -n "$2" ] && [ -f "$2" ]; then
            log_file="$2"
            classified_file="${log_file}.classified"
            
            print_header "Classifying Errors in Log File: $log_file"
            print_info "Analyzing log file and extracting errors by severity..."
            classify_errors "$log_file" "$classified_file"
            
            print_success "Classification completed. Results saved to: $classified_file"
            print_important "CLASSIFIED ERROR SUMMARY:"
            cat "$classified_file"
        else
            print_error "Please provide a valid log file to classify."
            print_info "Usage: $0 classify <log_file>"
            print_info "Example: $0 classify logs/workflow_12345678.log"
            exit 1
        fi
        ;;
    tests|test)
        process_workflow_logs "tests"
        ;;
    build|release)
        process_workflow_logs "build"
        ;;
    lint)
        process_workflow_logs "lint"
        ;;
    docs)
        process_workflow_logs "docs"
        ;;
    latest)
        get_latest_logs
        ;;
    *)
        print_error "Unknown command: $1"
        print_info "Run '$0 help' for usage information."
        exit 1
        ;;
esac

exit 0
