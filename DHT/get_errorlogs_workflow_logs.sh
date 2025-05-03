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
get_latest_workflow_run() {
    local workflow_name="$1"
    
    if ! command -v gh &>/dev/null || [ -z "$REPO_FULL_NAME" ]; then
        return 1
    fi
    
    local run_id
    
    if [ -n "$workflow_name" ]; then
        # Try to get latest run for specific workflow
        run_id=$(gh run list --repo "$REPO_FULL_NAME" --workflow "$workflow_name" --limit 1 --json databaseId -q '.[0].databaseId' 2>/dev/null)
    else
        # Get latest run of any workflow
        run_id=$(gh run list --repo "$REPO_FULL_NAME" --limit 1 --json databaseId -q '.[0].databaseId' 2>/dev/null)
    fi
    
    echo "$run_id"
    return 0
}

# Function to get workflow logs from GitHub
get_workflow_logs() {
    local run_id="$1"
    
    if [ -z "$run_id" ]; then
        print_error "Run ID is required"
        return 1
    fi
    
    print_info "Fetching logs for workflow run $run_id"
    
    # Create logs directory if it doesn't exist
    mkdir -p logs
    
    # Get current timestamp for log filename
    local timestamp
    timestamp=$(date "+%Y%m%d-%H%M%S")
    local log_file="logs/workflow_${run_id}_${timestamp}.log"
    
    # Try to fetch using GitHub CLI first
    if command -v gh &>/dev/null; then
        if gh auth status &>/dev/null; then
            print_info "Using GitHub CLI to fetch logs..."
            
            if gh run view "$run_id" --repo "$REPO_FULL_NAME" --log > "$log_file" 2>/dev/null; then
                print_success "Downloaded logs to $log_file"
                
                # Extract errors and classify
                classify_errors "$log_file" "${log_file}.classified"
                
                # Display logs based on truncation setting
                if [ "$DO_TRUNCATE" = true ]; then
                    # Show truncated view
                    print_info "Showing truncated logs (first $DEFAULT_OUTPUT_LINES lines):"
                    echo "───────────────────────────────────────────────────────────────"
                    head -n "$DEFAULT_OUTPUT_LINES" "$log_file"
                    echo "..."
                    echo "───────────────────────────────────────────────────────────────"
                    print_info "For full logs, run without --truncate or view the file directly: $log_file"
                else
                    # Show full logs
                    print_info "Showing full logs:"
                    echo "───────────────────────────────────────────────────────────────"
                    cat "$log_file"
                    echo "───────────────────────────────────────────────────────────────"
                fi
                
                return 0
            else
                print_error "Failed to download logs for run $run_id"
                return 1
            fi
        else
            print_warning "Not authenticated with GitHub CLI. Please run 'gh auth login'."
            return 1
        fi
    else
        print_warning "GitHub CLI is not installed. Install it from: https://cli.github.com"
        return 1
    fi
}

# Function to list all workflow runs from GitHub
get_workflow_runs() {
    print_header "Listing Recent GitHub Workflow Runs"
    
    if ! command -v gh &>/dev/null; then
        print_error "GitHub CLI (gh) is not installed. Install it from: https://cli.github.com"
        return 1
    fi
    
    if ! gh auth status &>/dev/null; then
        print_error "Not authenticated with GitHub CLI. Run 'gh auth login' first."
        return 1
    fi
    
    if [ -z "$REPO_FULL_NAME" ]; then
        print_error "Repository information not available."
        detect_repository_info
    fi
    
    # Get recent workflow runs
    print_info "Fetching recent workflow runs for $REPO_FULL_NAME..."
    
    # Define output format
    local format="%10s  %s  %15s  %s\\n"
    printf "$format" "RUN ID" "STATUS" "WORKFLOW" "CREATED"
    echo "───────────────────────────────────────────────────────────────"
    
    local runs
    runs=$(gh run list --repo "$REPO_FULL_NAME" --limit 10 2>/dev/null)
    
    if [ -n "$runs" ]; then
        echo "$runs" | while read -r line; do
            # Process each workflow run
            local run_id
            local status
            local workflow
            local created
            
            # Parse the line
            run_id=$(echo "$line" | awk '{print $1}')
            status=$(echo "$line" | awk '{print $2}')
            workflow=$(echo "$line" | awk '{print $3}')
            created=$(echo "$line" | awk '{print $4, $5, $6}')
            
            # Format the status with color
            local status_colored
            if [ "$status" = "completed" ]; then
                status_colored="\033[1;32m$status\033[0m"
            elif [ "$status" = "failure" ]; then
                status_colored="\033[1;31m$status\033[0m"
            else
                status_colored="\033[1;33m$status\033[0m"
            fi
            
            # Print the formatted line
            printf "$format" "$run_id" "$status_colored" "$workflow" "$created"
        done
    else
        print_warning "No workflow runs found for $REPO_FULL_NAME."
    fi
    
    return 0
}

# Function to find local logs for a workflow ID
