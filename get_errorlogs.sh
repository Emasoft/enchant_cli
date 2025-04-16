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
            print_error "No failed workflow runs found."
            exit 1
        fi
        
        print_info "Using most recent failed workflow run: $run_id"
    else
        print_info "Fetching logs for workflow run: $run_id"
    fi
    
    # Create a logs directory if it doesn't exist
    mkdir -p logs
    
    # Get workflow name (sanitize it to avoid path issues)
    workflow_name=$(gh run view "$run_id" --repo "$REPO_FULL_NAME" --json name -q '.name' | tr ' ' '_' | tr '/' '_')
    timestamp=$(date +"%Y%m%d-%H%M%S")
    log_file="logs/workflow_${run_id}_${timestamp}.log"
    
    print_info "Downloading logs to $log_file..."
    
    # Download the logs
    gh run view "$run_id" --repo "$REPO_FULL_NAME" --log > "$log_file"
    
    # Get just the failed jobs with better error detection
    print_info "Extracting errors from log..."
    
    # Create a temporary error file
    error_file="${log_file}.errors"
    > "$error_file"  # Clear or create the file
    
    # Look for different types of errors with context
    grep -n -A 5 -B 2 "Error:" "$log_file" >> "$error_file" || true
    grep -n -A 5 -B 2 "error:" "$log_file" >> "$error_file" || true
    grep -n -A 5 -B 2 "ERROR:" "$log_file" >> "$error_file" || true
    grep -n -A 5 -B 2 "failed with exit code" "$log_file" >> "$error_file" || true
    grep -n -A 5 -B 2 "FAILED" "$log_file" >> "$error_file" || true
    grep -n -A 5 -B 2 "Process completed with exit code [1-9]" "$log_file" >> "$error_file" || true
    
    # Check if any errors were found
    if [ ! -s "$error_file" ]; then
        print_info "No specific errors found. Doing a broader search..."
        # Fallback to more generic error patterns
        grep -n -A 3 -B 1 "fail" "$log_file" >> "$error_file" || true
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
}

# Get the latest run ID for a specific workflow
get_latest_workflow_run() {
    local workflow_name="$1"
    local run_id

    # List all recent runs and filter by workflow name (don't print to stdout during command)
    echo "Searching for $workflow_name workflow runs..." >&2
    run_id=$(gh run list --repo "$REPO_FULL_NAME" --limit 20 --json databaseId,name -q '.[] | select(.name | contains("'"$workflow_name"'")) | .databaseId' | head -n 1)
    
    if [ -z "$run_id" ]; then
        # Fallback to just getting the latest run
        echo "No exact match found, getting latest workflow run..." >&2
        run_id=$(gh run list --repo "$REPO_FULL_NAME" --limit 1 --json databaseId -q '.[0].databaseId')
        
        if [ -z "$run_id" ]; then
            print_error "No recent workflow runs found."
            return 1
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
        fi
        ;;
    build|release)
        # Get the latest Auto Release workflow run
        print_info "Finding the latest build/release workflow run..."
        release_run_id=$(get_latest_workflow_run "Auto Release")
        if [ -n "$release_run_id" ]; then
            get_workflow_logs "$release_run_id"
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
        ;;
esac

exit 0