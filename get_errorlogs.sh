#!/bin/bash
# get_errorlogs.sh - Tool to fetch error logs from GitHub Actions workflows
set -eo pipefail

# Repository information
REPO_OWNER="Emasoft"
REPO_NAME="enchant_cli"
REPO_FULL_NAME="$REPO_OWNER/$REPO_NAME"

# Print colored output
print_header() { echo -e "\033[1;33m🔶 $1\033[0m"; }
print_success() { echo -e "\033[1;32m✅ $1\033[0m"; }
print_error() { echo -e "\033[1;31m❌ $1\033[0m"; }
print_warning() { echo -e "\033[1;33m⚠️ $1\033[0m"; }
print_info() { echo -e "\033[1;34mℹ️ $1\033[0m"; }

# Check if gh CLI is installed
if ! command -v gh &> /dev/null; then
    print_error "GitHub CLI (gh) is not installed. Please install it from https://cli.github.com"
    exit 1
fi

# Check authentication status
if ! gh auth status &> /dev/null; then
    print_error "Not authenticated with GitHub CLI. Please run 'gh auth login' first."
    exit 1
fi

print_header "Fetching GitHub Actions Workflow Logs"

# Function to get and display workflow runs with status and ID
get_workflow_runs() {
    print_info "Recent workflow runs:"
    echo "───────────────────────────────────────────────────────────────"
    echo "ID        STATUS    WORKFLOW            CREATED             BRANCH"
    echo "───────────────────────────────────────────────────────────────"
    
    # Get recent workflow runs, focusing on failed ones first
    gh run list --repo "$REPO_FULL_NAME" --limit 10 --json databaseId,status,name,createdAt,headBranch | \
    jq -r '.[] | "\(.databaseId)    \(.status)    \(.name | .[0:15] | .)    \(.createdAt | .[0:16])    \(.headBranch)"' | sort -k 2
    
    echo "───────────────────────────────────────────────────────────────"
}

# Function to get and display job logs for a specific workflow run
get_workflow_logs() {
    local run_id=$1
    
    if [ -z "$run_id" ]; then
        # Get the ID of the most recent failed workflow run
        run_id=$(gh run list --repo "$REPO_FULL_NAME" --status failure --limit 1 --json databaseId -q '.[0].databaseId')
        
        if [ -z "$run_id" ]; then
            # Try to get any completed workflow run
            run_id=$(gh run list --repo "$REPO_FULL_NAME" --status completed --limit 1 --json databaseId -q '.[0].databaseId')
            
            if [ -z "$run_id" ]; then
                # Last resort - get any workflow run
                run_id=$(gh run list --repo "$REPO_FULL_NAME" --limit 1 --json databaseId -q '.[0].databaseId')
                
                if [ -z "$run_id" ]; then
                    print_error "No workflow runs found at all."
                    exit 1
                fi
            fi
            
            print_info "No failed runs found. Using most recent workflow run: $run_id"
        else
            print_info "Using most recent failed workflow run: $run_id"
        fi
    else
        print_info "Fetching logs for workflow run: $run_id"
    fi
    
    # Create a logs directory if it doesn't exist
    mkdir -p logs
    
    # Get workflow information 
    workflow_info=$(gh run view "$run_id" --repo "$REPO_FULL_NAME" --json name,url,status,conclusion,createdAt,displayTitle 2>/dev/null)
    
    if [ -z "$workflow_info" ]; then
        print_error "Could not get workflow information for run ID: $run_id"
        print_warning "This might be a permissions issue or the workflow has been deleted."
        return 1
    fi
    
    # Get and display workflow details
    workflow_name=$(echo "$workflow_info" | jq -r '.name // "Unknown"' | tr ' ' '_' | tr '/' '_')
    workflow_status=$(echo "$workflow_info" | jq -r '.status // "Unknown"')
    workflow_conclusion=$(echo "$workflow_info" | jq -r '.conclusion // "Unknown"')
    workflow_url=$(echo "$workflow_info" | jq -r '.url // "Unknown"')
    created_at=$(echo "$workflow_info" | jq -r '.createdAt // "Unknown"')
    
    print_info "Workflow: $workflow_name"
    print_info "Status: $workflow_status (Conclusion: $workflow_conclusion)"
    print_info "Created: $created_at"
    print_info "URL: $workflow_url"
    
    # Setup log file path
    timestamp=$(date +"%Y%m%d-%H%M%S")
    log_file="logs/workflow_${run_id}_${timestamp}.log"
    error_log_file="${log_file}.errors"
    
    print_info "Downloading logs to $log_file..."
    
    # Try to download the logs, but handle failure gracefully
    if ! gh run view "$run_id" --repo "$REPO_FULL_NAME" --log > "$log_file" 2>/dev/null; then
        print_error "Failed to download logs for workflow run: $run_id"
        print_warning "Likely causes:"
        print_warning "1. The workflow is still in progress"
        print_warning "2. The workflow did not generate any logs"
        print_warning "3. You don't have permissions to access the logs"
        print_warning "4. The logs have expired or been deleted"
        
        # Create a minimal log file with the information we have
        cat > "$log_file" << EOF
# Workflow Log Information
- **Run ID:** $run_id
- **Workflow:** $workflow_name
- **Status:** $workflow_status ($workflow_conclusion)
- **Created:** $created_at
- **URL:** $workflow_url

## Error
Failed to download the actual log content. 
Please check the workflow directly on GitHub: $workflow_url
EOF
        
        # Return but don't exit, so we can try other workflows
        return 1
    fi
    
    # Get just the failed jobs with better error detection
    print_info "Extracting errors from log..."
    
    # Create a temporary error file
    error_file="${log_file}.errors"
    > "$error_file"  # Clear or create the file
    
    # Get file size
    log_file_size=$(wc -c < "$log_file")
    
    # Only process if the log file is not empty
    if [ "$log_file_size" -gt 0 ]; then
        # Look for different types of errors with context
        grep -n -A 5 -B 2 "Error:" "$log_file" >> "$error_file" 2>/dev/null || true
        grep -n -A 5 -B 2 "error:" "$log_file" >> "$error_file" 2>/dev/null || true
        grep -n -A 5 -B 2 "ERROR:" "$log_file" >> "$error_file" 2>/dev/null || true
        grep -n -A 5 -B 2 "failed with exit code" "$log_file" >> "$error_file" 2>/dev/null || true
        grep -n -A 5 -B 2 "FAILED" "$log_file" >> "$error_file" 2>/dev/null || true
        grep -n -A 5 -B 2 "Process completed with exit code [1-9]" "$log_file" >> "$error_file" 2>/dev/null || true
        
        # Check if any errors were found
        if [ ! -s "$error_file" ]; then
            print_info "No specific errors found. Doing a broader search..."
            # Fallback to more generic error patterns
            grep -n -A 3 -B 1 "fail" "$log_file" >> "$error_file" 2>/dev/null || true
            grep -n -A 3 -B 1 "exception" "$log_file" >> "$error_file" 2>/dev/null || true 
            grep -n -A 3 -B 1 "fatal" "$log_file" >> "$error_file" 2>/dev/null || true
        fi
        
        # Show some statistics
        total_lines=$(wc -l < "$log_file")
        error_count=$(grep -c -v "^--$" "$error_file" 2>/dev/null || echo "0")
        
        print_success "Logs downloaded successfully: $log_file ($total_lines lines)"
        
        if [ -s "$error_file" ]; then
            print_info "Found potential errors in the log."
            print_info "Most significant errors:"
            echo "───────────────────────────────────────────────────────────────"
            # Show the first 20 lines of the error file
            head -n 20 "$error_file"
            echo "..."
            echo "───────────────────────────────────────────────────────────────"
            
            # Show the last errors as well - often the most important
            print_info "Last errors in the log (usually most relevant):"
            echo "───────────────────────────────────────────────────────────────"
            tail -n 20 "$error_file"
            echo "───────────────────────────────────────────────────────────────"
            
            print_info "Full error log written to: $error_file"
            print_info "For complete logs, see: $log_file"
        else
            print_info "No clear errors detected. Please check the full log file: $log_file"
        fi
    else
        print_warning "Log file is empty or contains no usable content."
        print_info "Please check directly on GitHub:"
        print_info "$workflow_url"
        
        # Create a basic error note
        echo "Log file was empty. Please check workflow directly on GitHub: $workflow_url" > "$error_file"
    fi
    
    # Return success even if we couldn't find errors, as we want to continue with other workflows
    return 0
}

# Get the latest run ID for a specific workflow
get_latest_workflow_run() {
    local workflow_name="$1"
    local run_id

    # List all recent runs and filter by workflow name (don't print to stdout during command)
    echo "Searching for $workflow_name workflow runs..." >&2
    
    # Try to find workflow by specific name first
    local runs_with_logs=()
    
    # Get all recent runs, with their IDs and log information
    local all_runs=$(gh run list --repo "$REPO_FULL_NAME" --limit 20 --json databaseId,name,url -q '.')
    
    # First, try to find runs that match the requested workflow name
    run_id=$(echo "$all_runs" | jq -r '.[] | select(.name | contains("'"$workflow_name"'")) | .databaseId' | head -n 1)
    
    if [ -z "$run_id" ]; then
        # Fallback to finding any run with logs available
        echo "No exact match found, searching for any workflows with logs..." >&2
        
        # Loop through all runs and check each one for log availability
        for run_data in $(echo "$all_runs" | jq -c '.[]'); do
            local id=$(echo "$run_data" | jq -r '.databaseId')
            
            # Try to check if logs exist without downloading them
            # Just check if we can download a small part of the log (first 10 lines)
            if gh run view "$id" --repo "$REPO_FULL_NAME" --log | head -n 10 &>/dev/null; then
                # Run has logs we can access
                runs_with_logs+=("$id")
                echo "Found workflow run with accessible logs: $id" >&2
            fi
        done
        
        # If we found any runs with logs, use the first one
        if [ ${#runs_with_logs[@]} -gt 0 ]; then
            run_id="${runs_with_logs[0]}"
            echo "Found workflow run with accessible logs: $run_id" >&2
        else
            # Final fallback - just get the latest run and hope for the best
            echo "No runs with confirmed logs found, trying latest run..." >&2
            run_id=$(echo "$all_runs" | jq -r '.[0].databaseId')
            
            if [ -z "$run_id" ]; then
                print_error "No recent workflow runs found."
                return 1
            fi
        fi
    fi
    
    # Only output the run ID to stdout for capture
    echo "$run_id"
}

# Main execution
case "$1" in
    list)
        get_workflow_runs
        ;;
    logs)
        get_workflow_logs "$2"
        ;;
    test|tests)
        # Get the latest Tests workflow run
        print_info "Finding the latest test workflow run..."
        test_run_id=$(get_latest_workflow_run "Tests")
        if [ -n "$test_run_id" ]; then
            get_workflow_logs "$test_run_id"
        else
            print_warning "No test workflow runs found with logs. Trying any workflow run..."
            any_run_id=$(get_latest_workflow_run "")
            if [ -n "$any_run_id" ]; then
                get_workflow_logs "$any_run_id"
            fi
        fi
        ;;
    build|release)
        # Get the latest Auto Release workflow run
        print_info "Finding the latest build/release workflow run..."
        release_run_id=$(get_latest_workflow_run "Auto Release")
        if [ -n "$release_run_id" ]; then
            get_workflow_logs "$release_run_id"
        else
            print_warning "No build/release workflow runs found with logs. Trying any workflow run..."
            any_run_id=$(get_latest_workflow_run "")
            if [ -n "$any_run_id" ]; then
                get_workflow_logs "$any_run_id"
            fi
        fi
        ;;
    *)
        # Default action - show help and then fetch logs for both tests and builds
        echo "Usage: $0 [command]"
        echo ""
        echo "Commands:"
        echo "  list               List recent workflow runs"
        echo "  logs [RUN_ID]      Get logs for a specific workflow run"
        echo "  tests              Get logs for the latest test workflow run"
        echo "  build              Get logs for the latest build/release workflow run"
        echo ""
        echo "Examples:"
        echo "  $0 list            List all recent workflow runs"
        echo "  $0 logs 123456789  Get logs for workflow run ID 123456789"
        echo "  $0 tests           Get logs for the latest test workflow run"
        echo ""
        
        # Show recent workflow runs
        get_workflow_runs
        
        # Get the latest test workflow run
        print_header "Fetching latest test workflow logs"
        test_run_id=$(get_latest_workflow_run "Tests")
        if [ -n "$test_run_id" ]; then
            get_workflow_logs "$test_run_id"
        fi
        
        # Get the latest build workflow run
        print_header "Fetching latest build/release workflow logs"
        build_run_id=$(get_latest_workflow_run "Auto Release")
        if [ -n "$build_run_id" ]; then
            get_workflow_logs "$build_run_id"
        fi
        
        # If none of the specific workflows had logs, try to get any workflow logs
        if [ -z "$test_run_id" ] && [ -z "$build_run_id" ]; then
            print_header "Fetching logs from any available workflow run"
            # Use empty string to force the fallback logic in get_latest_workflow_run
            any_run_id=$(get_latest_workflow_run "")
            if [ -n "$any_run_id" ]; then
                get_workflow_logs "$any_run_id"
            else
                print_error "Could not find any workflow runs with available logs."
                print_info "Try running 'gh run list' manually to see available workflow runs."
            fi
        fi
        ;;
esac

exit 0