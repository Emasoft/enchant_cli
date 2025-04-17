#!/bin/bash
# get_errorlogs.sh - GitHub Actions Workflow Log Analysis Tool
# Version: 1.0.0
# A portable tool for retrieving, analyzing, and classifying GitHub Actions workflow logs

#=========================================================================
# CONFIGURATION
#=========================================================================

# Constants for log settings
SCRIPT_VERSION="1.0.0"
MAX_LOGS_PER_WORKFLOW=5       # Maximum number of log files to keep per workflow ID
MAX_LOG_AGE_DAYS=30           # Maximum age in days for log files before cleanup
MAX_TOTAL_LOGS=50             # Maximum total log files to keep
DEFAULT_OUTPUT_LINES=100      # Default number of lines to display in truncated mode
DO_TRUNCATE=false             # Default truncation setting

# Error pattern categories for classification
ERROR_PATTERN_CRITICAL="Process completed with exit code [1-9]|fatal error|fatal:|FATAL ERROR|Assertion failed|Segmentation fault|core dumped|killed|ERROR:|Connection refused|panic|PANIC|assert|ASSERT|terminated|abort|SIGSEGV|SIGABRT|SIGILL|SIGFPE"
ERROR_PATTERN_SEVERE="exit code [1-9]|failure:|failed with|FAILED|Exception|exception:|Error:|error:|undefined reference|Cannot find|not found|No such file|Permission denied|AccessDenied|Could not access|Cannot access|ImportError|ModuleNotFoundError|TypeError|ValueError|KeyError|AttributeError|AssertionError|UnboundLocalError|IndexError|SyntaxError|NameError|RuntimeError|unexpected|failed to|EACCES|EPERM|ENOENT|compilation failed|command failed|exited with code"
ERROR_PATTERN_WARNING="WARNING:|warning:|deprecated|Deprecated|DEPRECATED|fixme|FIXME|TODO|todo:|ignored|skipped|suspicious|insecure|unsafe|consider|recommended|inconsistent|possibly|PendingDeprecationWarning|FutureWarning|UserWarning|ResourceWarning"

# Initialize empty arrays for workflows
AVAILABLE_WORKFLOWS=()
TEST_WORKFLOWS=()
RELEASE_WORKFLOWS=()
LINT_WORKFLOWS=()
DOCS_WORKFLOWS=()
OTHER_WORKFLOWS=()

# Repository information
REPO_OWNER=""
REPO_NAME=""
REPO_FULL_NAME=""

#=========================================================================
# UTILITY FUNCTIONS
#=========================================================================

# Formatting functions for output
print_header() {
    echo -e "\033[1;36m=== $1 ===\033[0m"
}

print_info() {
    echo -e "\033[1;34mℹ️  $1\033[0m"
}

print_success() {
    echo -e "\033[1;32m✅ $1\033[0m"
}

print_warning() {
    echo -e "\033[1;33m⚠️  $1\033[0m"
}

print_error() {
    echo -e "\033[1;31m❌ $1\033[0m"
}

print_critical() {
    echo -e "\033[1;41m🔥 $1\033[0m"
}

print_severe() {
    echo -e "\033[1;35m⛔ $1\033[0m"
}

print_important() {
    echo -e "\033[1;37m👉 $1\033[0m"
}

# Function to detect repository information
detect_repository_info() {
    print_info "Detecting repository information..."
    
    # Try to get repository info from git config
    local origin_url
    origin_url=$(git config --get remote.origin.url 2>/dev/null)
    
    if [ -n "$origin_url" ]; then
        # Extract owner and repo from the URL
        if [[ "$origin_url" =~ github\.com[:/]([^/]+)/([^/.]+) ]]; then
            REPO_OWNER="${BASH_REMATCH[1]}"
            REPO_NAME="${BASH_REMATCH[2]}"
            REPO_FULL_NAME="$REPO_OWNER/$REPO_NAME"
            print_success "Detected repository: $REPO_FULL_NAME"
            return 0
        fi
    fi
    
    # Fallback: try to extract from pyproject.toml, package.json, etc.
    if [ -f "pyproject.toml" ]; then
        local homepage
        homepage=$(grep -o 'Homepage.*=.*"https://github.com/[^"]*"' pyproject.toml 2>/dev/null | cut -d'"' -f2)
        if [[ "$homepage" =~ github\.com/([^/]+)/([^/]+) ]]; then
            REPO_OWNER="${BASH_REMATCH[1]}"
            REPO_NAME="${BASH_REMATCH[2]}"
            REPO_FULL_NAME="$REPO_OWNER/$REPO_NAME"
            print_success "Detected repository from pyproject.toml: $REPO_FULL_NAME"
            return 0
        fi
    fi
    
    # Fallback: try GitHub CLI
    if command -v gh &>/dev/null; then
        local repo_info
        repo_info=$(gh repo view --json owner,name 2>/dev/null)
        if [ -n "$repo_info" ]; then
            REPO_OWNER=$(echo "$repo_info" | grep -o '"owner": *"[^"]*"' | cut -d'"' -f4)
            REPO_NAME=$(echo "$repo_info" | grep -o '"name": *"[^"]*"' | cut -d'"' -f4)
            if [ -n "$REPO_OWNER" ] && [ -n "$REPO_NAME" ]; then
                REPO_FULL_NAME="$REPO_OWNER/$REPO_NAME"
                print_success "Detected repository from GitHub CLI: $REPO_FULL_NAME"
                return 0
            fi
        fi
    fi
    
    # Last resort: use current directory name as repo name and prompt for owner
    REPO_NAME=$(basename "$(pwd)")
    print_warning "Could not automatically detect repository owner."
    print_info "Using current directory as repository name: $REPO_NAME"
    print_info "Please enter the repository owner (GitHub username or organization):"
    read -r REPO_OWNER
    
    if [ -n "$REPO_OWNER" ]; then
        REPO_FULL_NAME="$REPO_OWNER/$REPO_NAME"
        print_success "Set repository to: $REPO_FULL_NAME"
    else
        REPO_OWNER="unknown"
        REPO_FULL_NAME="$REPO_OWNER/$REPO_NAME"
        print_warning "No owner provided. Using $REPO_FULL_NAME"
    fi
    
    return 0
}

# Function to detect available workflows
detect_workflows() {
    print_info "Detecting available workflows..."
    
    # Clear previous workflow arrays
    AVAILABLE_WORKFLOWS=()
    TEST_WORKFLOWS=()
    RELEASE_WORKFLOWS=()
    LINT_WORKFLOWS=()
    DOCS_WORKFLOWS=()
    OTHER_WORKFLOWS=()
    
    # Try both API-based and file-based approaches to maximize detection success
    
    # Method 1: Use GitHub API if available (most accurate)
    if command -v gh &>/dev/null && [ -n "$REPO_FULL_NAME" ]; then
        if gh auth status &>/dev/null; then
            print_info "Using GitHub API to detect workflows..."
            
            # Get all workflows using the GitHub API with JQ for filtering
            local api_result
            api_result=$(gh api "repos/$REPO_FULL_NAME/actions/workflows" --jq '.workflows[]' 2>/dev/null)
            
            if [ -n "$api_result" ]; then
                # Get test workflows
                while IFS= read -r workflow_name; do
                    if [ -n "$workflow_name" ]; then
                        workflow_name="${workflow_name//\"/}"
                        TEST_WORKFLOWS+=("$workflow_name")
                        AVAILABLE_WORKFLOWS+=("$workflow_name")
                    fi
                done < <(gh api "repos/$REPO_FULL_NAME/actions/workflows" --jq '.workflows[] | select(.name | test("(?i)test|ci|check") or .path | test("(?i)test|ci|check")) | .name' 2>/dev/null)
                
                # Get release workflows
                while IFS= read -r workflow_name; do
                    if [ -n "$workflow_name" ]; then
                        workflow_name="${workflow_name//\"/}"
                        RELEASE_WORKFLOWS+=("$workflow_name")
                        # Only add to AVAILABLE_WORKFLOWS if not already there
                        if ! [[ " ${AVAILABLE_WORKFLOWS[*]} " =~ " ${workflow_name} " ]]; then
                            AVAILABLE_WORKFLOWS+=("$workflow_name")
                        fi
                    fi
                done < <(gh api "repos/$REPO_FULL_NAME/actions/workflows" --jq '.workflows[] | select(.name | test("(?i)release|publish|deploy|build|package") or .path | test("(?i)release|publish|deploy|build|package")) | .name' 2>/dev/null)
                
                # Get lint workflows
                while IFS= read -r workflow_name; do
                    if [ -n "$workflow_name" ]; then
                        workflow_name="${workflow_name//\"/}"
                        LINT_WORKFLOWS+=("$workflow_name")
                        # Only add to AVAILABLE_WORKFLOWS if not already there
                        if ! [[ " ${AVAILABLE_WORKFLOWS[*]} " =~ " ${workflow_name} " ]]; then
                            AVAILABLE_WORKFLOWS+=("$workflow_name")
                        fi
                    fi
                done < <(gh api "repos/$REPO_FULL_NAME/actions/workflows" --jq '.workflows[] | select(.name | test("(?i)lint|format|style|quality") or .path | test("(?i)lint|format|style|quality")) | .name' 2>/dev/null)
                
                # Get doc workflows
                while IFS= read -r workflow_name; do
                    if [ -n "$workflow_name" ]; then
                        workflow_name="${workflow_name//\"/}"
                        DOCS_WORKFLOWS+=("$workflow_name")
                        # Only add to AVAILABLE_WORKFLOWS if not already there
                        if ! [[ " ${AVAILABLE_WORKFLOWS[*]} " =~ " ${workflow_name} " ]]; then
                            AVAILABLE_WORKFLOWS+=("$workflow_name")
                        fi
                    fi
                done < <(gh api "repos/$REPO_FULL_NAME/actions/workflows" --jq '.workflows[] | select(.name | test("(?i)doc|docs|documentation") or .path | test("(?i)doc|docs|documentation")) | .name' 2>/dev/null)
                
                # Get any other workflows not yet categorized
                while IFS= read -r workflow_name; do
                    if [ -n "$workflow_name" ]; then
                        workflow_name="${workflow_name//\"/}"
                        # Check if this workflow is already categorized
                        if ! [[ " ${TEST_WORKFLOWS[*]} " =~ " ${workflow_name} " ]] && 
                           ! [[ " ${RELEASE_WORKFLOWS[*]} " =~ " ${workflow_name} " ]] && 
                           ! [[ " ${LINT_WORKFLOWS[*]} " =~ " ${workflow_name} " ]] && 
                           ! [[ " ${DOCS_WORKFLOWS[*]} " =~ " ${workflow_name} " ]]; then
                            OTHER_WORKFLOWS+=("$workflow_name")
                            # Only add to AVAILABLE_WORKFLOWS if not already there
                            if ! [[ " ${AVAILABLE_WORKFLOWS[*]} " =~ " ${workflow_name} " ]]; then
                                AVAILABLE_WORKFLOWS+=("$workflow_name")
                            fi
                        fi
                    fi
                done < <(gh api "repos/$REPO_FULL_NAME/actions/workflows" --jq '.workflows[] | .name' 2>/dev/null)
            fi
        fi
    fi
    
    # Method 2: Check .github/workflows directory as fallback or additional info
    if [ -d ".github/workflows" ]; then
        if [ ${#AVAILABLE_WORKFLOWS[@]} -eq 0 ]; then
            print_info "Using local files to detect workflows..."
        else
            print_info "Enhancing workflow detection with local files..."
        fi
        
        for file in .github/workflows/*.{yml,yaml}; do
            if [ -f "$file" ] && [ "$file" != ".github/workflows/*.yml" ] && [ "$file" != ".github/workflows/*.yaml" ]; then
                # Extract workflow name from file
                local workflow_name
                workflow_name=$(grep -o 'name:.*' "$file" | head -1 | cut -d':' -f2- | sed 's/^[[:space:]]*//')
                
                if [ -z "$workflow_name" ]; then
                    # Use filename if name not found
                    workflow_name=$(basename "$file" | sed 's/\.[^.]*$//')
                fi
                
                # Skip if already in AVAILABLE_WORKFLOWS
                if [[ " ${AVAILABLE_WORKFLOWS[*]} " =~ " ${workflow_name} " ]]; then
                    continue
                fi
                
                # Add to available workflows
                AVAILABLE_WORKFLOWS+=("$workflow_name")
                
                # Categorize by type based on name and content
                if grep -q -E "test|pytest|unittest|jest|spec|check" "$file" || [[ "$file" =~ [tT]est ]]; then
                    TEST_WORKFLOWS+=("$workflow_name")
                elif grep -q -E "release|deploy|publish|build|package|version" "$file" || [[ "$file" =~ ([rR]elease|[dD]eploy|[pP]ublish|[bB]uild) ]]; then
                    RELEASE_WORKFLOWS+=("$workflow_name")
                elif grep -q -E "lint|format|style|prettier|eslint|black|flake8|ruff|quality" "$file" || [[ "$file" =~ ([lL]int|[fF]ormat|[sS]tyle) ]]; then
                    LINT_WORKFLOWS+=("$workflow_name")
                elif grep -q -E "doc|sphinx|mkdocs|javadoc|doxygen|documentation" "$file" || [[ "$file" =~ [dD]oc ]]; then
                    DOCS_WORKFLOWS+=("$workflow_name")
                else
                    OTHER_WORKFLOWS+=("$workflow_name")
                fi
            fi
        done
    fi
    
    # If still no workflows found, use defaults
    if [ ${#AVAILABLE_WORKFLOWS[@]} -eq 0 ]; then
        print_warning "No workflows detected, using default workflow names"
        # Add default names for common workflow types
        AVAILABLE_WORKFLOWS=("Tests" "Auto Release" "Lint" "Docs")
        TEST_WORKFLOWS=("Tests")
        RELEASE_WORKFLOWS=("Auto Release")
        LINT_WORKFLOWS=("Lint")
        DOCS_WORKFLOWS=("Docs")
    fi
    
    # Report findings
    print_success "Detected ${#AVAILABLE_WORKFLOWS[@]} workflows"
    if [ ${#TEST_WORKFLOWS[@]} -gt 0 ]; then
        print_info "Testing workflows: ${#TEST_WORKFLOWS[@]} (${TEST_WORKFLOWS[*]})"
    else
        print_info "Testing workflows: 0"
    fi
    
    if [ ${#RELEASE_WORKFLOWS[@]} -gt 0 ]; then
        print_info "Release workflows: ${#RELEASE_WORKFLOWS[@]} (${RELEASE_WORKFLOWS[*]})"
    else
        print_info "Release workflows: 0"
    fi
    
    if [ ${#LINT_WORKFLOWS[@]} -gt 0 ]; then
        print_info "Linting workflows: ${#LINT_WORKFLOWS[@]} (${LINT_WORKFLOWS[*]})"
    else
        print_info "Linting workflows: 0"
    fi
    
    if [ ${#DOCS_WORKFLOWS[@]} -gt 0 ]; then
        print_info "Documentation workflows: ${#DOCS_WORKFLOWS[@]} (${DOCS_WORKFLOWS[*]})"
    else
        print_info "Documentation workflows: 0"
    fi
    
    if [ ${#OTHER_WORKFLOWS[@]} -gt 0 ]; then
        print_info "Other workflows: ${#OTHER_WORKFLOWS[@]} (${OTHER_WORKFLOWS[*]})"
    else
        print_info "Other workflows: 0"
    fi
    
    return 0
}

# Function to get workflow statistics from GitHub
get_workflow_stats() {
    if ! command -v gh &>/dev/null || [ -z "$REPO_FULL_NAME" ]; then
        # Can't get stats, set defaults
        recent_success_count=0
        all_runs_count=0
        recent_failure_count=0
        return 1
    fi
    
    # Get counts from GitHub API (with fallbacks to 0 if command fails)
    all_runs_count=$(gh run list --repo "$REPO_FULL_NAME" --limit 100 | grep -c "completed\|failure\|cancelled\|skipped\|in_progress\|queued" 2>/dev/null || echo "0")
    recent_success_count=$(gh run list --repo "$REPO_FULL_NAME" --limit 100 --status completed | grep -c completed 2>/dev/null || echo "0")
    recent_failure_count=$(gh run list --repo "$REPO_FULL_NAME" --limit 100 --status failure | grep -c failure 2>/dev/null || echo "0")
    
    # Get validation errors
    validation_errors=$(gh api "repos/$REPO_OWNER/$REPO_NAME/actions/runs?status=action_required" --jq '.workflow_runs | length' 2>/dev/null || echo "0")
    
    # Calculate total errors
    recent_failure_count=$((recent_failure_count + validation_errors))
    
    return 0
}

# Function to display workflow summary
display_workflow_summary() {
    echo ""
    echo -e "\033[1;33m🔶 WORKFLOW SUMMARY 🔶\033[0m"
    
    # Ensure variables are initialized
    recent_failure_count=${recent_failure_count:-0}
    recent_success_count=${recent_success_count:-0}
    all_runs_count=${all_runs_count:-0}
    
    if [ "$recent_failure_count" -gt 0 ]; then
        echo -e "\033[1;31m❌ GITHUB JOBS SUMMARY: $recent_success_count/$all_runs_count WORKFLOWS COMPLETED SUCCESSFULLY, $recent_failure_count WITH ERRORS\033[0m"
    else
        echo -e "\033[1;32m✅ GITHUB JOBS COMPLETED SUCCESSFULLY\033[0m"
    fi
}

# Function to find the latest workflow run using GitHub CLI
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
classify_errors() {
    local log_file="$1"
    local output_file="$2"
    
    if [ ! -f "$log_file" ]; then
        print_error "Log file not found: $log_file"
        return 1
    fi
    
    # Clear or create output file
    > "$output_file"
    
    print_important "ERROR CLASSIFICATION SUMMARY" >> "$output_file"
    echo "Log file: $log_file" >> "$output_file"
    echo "Classification timestamp: $(date "+%Y-%m-%d %H:%M:%S")" >> "$output_file"
    echo "───────────────────────────────────────────────────────────────" >> "$output_file"
    echo "" >> "$output_file"
    
    # Track statistics
    local critical_count=0
    local severe_count=0
    local warning_count=0
    
    # Check for critical errors and extract relevant context
    print_critical "CRITICAL ERRORS:" >> "$output_file"
    echo "───────────────────────────────────────────────────────────────" >> "$output_file"
    
    # First, check if there are any critical errors
    if grep -q -E "$ERROR_PATTERN_CRITICAL" "$log_file"; then
        # Get critical errors with line numbers
        local critical_lines=$(grep -n -E "$ERROR_PATTERN_CRITICAL" "$log_file" | cut -d':' -f1 | head -20)
        critical_count=$(echo "$critical_lines" | wc -l | tr -d ' ')
        
        # Process each critical error line to extract meaningful context
        echo "$critical_lines" | while read -r line_num; do
            if [ -n "$line_num" ]; then
                # Get 2 lines before and 4 lines after the error for context
                local context_start=$((line_num > 2 ? line_num - 2 : 1))
                local context_end=$((line_num + 4))
                
                # Print the error line with context
                echo -e "\033[1;31m>>> Critical error at line $line_num:\033[0m" >> "$output_file"
                sed -n "${context_start},${context_end}p" "$log_file" | \
                    sed "${line_num}s/^/\033[1;31m→ /" | \
                    sed "${line_num}s/$/\033[0m/" >> "$output_file"
                
                # Extract stack trace if it exists
                if grep -A 10 -E "(Traceback|Stack trace|Call stack|at .*\(.*:[0-9]+\)|File \".*\", line [0-9]+)" "$log_file" | \
                   grep -q -A 5 -B 5 -E "^$line_num:"; then
                    echo -e "\n\033[1;31m>>> Stack trace:\033[0m" >> "$output_file"
                    grep -A 15 -E "(Traceback|Stack trace|Call stack|at .*\(.*:[0-9]+\)|File \".*\", line [0-9]+)" "$log_file" | \
                    grep -A 15 -B 1 -E "^$line_num:" | head -15 >> "$output_file"
                fi
                
                echo "───────────────────────────────────────────────────────────────" >> "$output_file"
            fi
        done
    else
        echo "None found" >> "$output_file"
    fi
    
    echo "" >> "$output_file"
    
    # Check for severe errors (excluding those already identified as critical)
    print_severe "SEVERE ERRORS:" >> "$output_file"
    echo "───────────────────────────────────────────────────────────────" >> "$output_file"
    
    if grep -q -E "$ERROR_PATTERN_SEVERE" "$log_file" && ! grep -q -E "$ERROR_PATTERN_CRITICAL" "$log_file"; then
        # Get severe errors with line numbers, excluding critical patterns
        local severe_lines=$(grep -n -E "$ERROR_PATTERN_SEVERE" "$log_file" | grep -v -E "$ERROR_PATTERN_CRITICAL" | cut -d':' -f1 | head -15)
        severe_count=$(echo "$severe_lines" | wc -l | tr -d ' ')
        
        # Process each severe error line
        echo "$severe_lines" | while read -r line_num; do
            if [ -n "$line_num" ]; then
                # Get 1 line before and 3 lines after the error for context
                local context_start=$((line_num > 1 ? line_num - 1 : 1))
                local context_end=$((line_num + 3))
                
                # Print the error line with context
                echo -e "\033[1;35m>>> Severe error at line $line_num:\033[0m" >> "$output_file"
                sed -n "${context_start},${context_end}p" "$log_file" | \
                    sed "${line_num}s/^/\033[1;35m→ /" | \
                    sed "${line_num}s/$/\033[0m/" >> "$output_file"
                echo "───────────────────────────────────────────────────────────────" >> "$output_file"
            fi
        done
    else
        echo "None found" >> "$output_file"
    fi
    
    echo "" >> "$output_file"
    
    # Check for warnings (excluding those already identified as critical or severe)
    print_warning "WARNINGS:" >> "$output_file"
    echo "───────────────────────────────────────────────────────────────" >> "$output_file"
    
    if grep -q -E "$ERROR_PATTERN_WARNING" "$log_file" && ! grep -q -E "$ERROR_PATTERN_CRITICAL|$ERROR_PATTERN_SEVERE" "$log_file"; then
        # Get warnings with line numbers, excluding critical and severe patterns
        local warning_lines=$(grep -n -E "$ERROR_PATTERN_WARNING" "$log_file" | grep -v -E "$ERROR_PATTERN_CRITICAL|$ERROR_PATTERN_SEVERE" | cut -d':' -f1 | head -10)
        warning_count=$(echo "$warning_lines" | wc -l | tr -d ' ')
        
        # Process each warning line
        echo "$warning_lines" | while read -r line_num; do
            if [ -n "$line_num" ]; then
                # Get just the warning line itself with minimal context
                echo -e "\033[1;33m>>> Warning at line $line_num:\033[0m" >> "$output_file"
                sed -n "${line_num}p" "$log_file" | \
                    sed "s/^/\033[1;33m→ /" | \
                    sed "s/$/\033[0m/" >> "$output_file"
            fi
        done
    else
        echo "None found" >> "$output_file"
    fi
    
    # Add error summary statistics
    echo "" >> "$output_file"
    echo "───────────────────────────────────────────────────────────────" >> "$output_file"
    print_important "ERROR SUMMARY STATISTICS:" >> "$output_file"
    echo "───────────────────────────────────────────────────────────────" >> "$output_file"
    echo "Critical Errors: $critical_count" >> "$output_file"
    echo "Severe Errors: $severe_count" >> "$output_file"
    echo "Warnings: $warning_count" >> "$output_file"
    echo "Total Issues: $((critical_count + severe_count + warning_count))" >> "$output_file"
    
    # Try to identify root cause if possible
    echo "" >> "$output_file"
    print_important "POSSIBLE ROOT CAUSES:" >> "$output_file"
    echo "───────────────────────────────────────────────────────────────" >> "$output_file"
    
    # Check for common root causes
    if grep -q -E "No space left on device|disk space|quota exceeded" "$log_file"; then
        echo "✱ Disk space issue detected - runner may have run out of disk space" >> "$output_file"
    fi
    
    if grep -q -E "memory allocation|out of memory|cannot allocate|allocation failed|OOM|Killed" "$log_file"; then
        echo "✱ Memory issue detected - process may have run out of memory" >> "$output_file"
    fi
    
    if grep -q -E "network.*timeout|connection.*refused|unreachable|DNS|proxy|firewall" "$log_file"; then
        echo "✱ Network connectivity issue detected - check network settings or dependencies" >> "$output_file"
    fi
    
    if grep -q -E "permission denied|access denied|unauthorized|forbidden|EACCES" "$log_file"; then
        echo "✱ Permission issue detected - check access rights or secrets" >> "$output_file"
    fi
    
    if grep -q -E "version mismatch|incompatible|requires version|dependency" "$log_file"; then
        echo "✱ Dependency or version compatibility issue detected" >> "$output_file"
    fi
    
    if grep -q -E "import error|module not found|cannot find module|unknown module" "$log_file"; then
        echo "✱ Missing import or module - check package installation" >> "$output_file"
    fi
    
    if grep -q -E "timeout|timed out|deadline exceeded|cancelled" "$log_file"; then
        echo "✱ Operation timeout detected - workflow may have exceeded time limits" >> "$output_file"
    fi
    
    if grep -q -E "syntax error|parsing error|unexpected token" "$log_file"; then
        echo "✱ Syntax error detected - check recent code changes" >> "$output_file"
    fi
    
    if ! grep -q -E "space left|memory|network|permission|version|import|timeout|syntax" "$log_file"; then
        echo "No specific root cause identified automatically." >> "$output_file"
        echo "Check the detailed error messages above for more information." >> "$output_file"
    fi
    
    # Create errors file with context for the most significant errors
    local error_file="${log_file}.errors"
    > "$error_file"
    grep -n -B 5 -A 10 -E "$ERROR_PATTERN_CRITICAL" "$log_file" > "$error_file" 2>/dev/null || true
    grep -n -B 3 -A 8 -E "$ERROR_PATTERN_SEVERE" "$log_file" | grep -v -E "$ERROR_PATTERN_CRITICAL" >> "$error_file" 2>/dev/null || true
    
    return 0
}

# Function to find local logs after last commit
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
detect_workflow_by_type() {
    local workflow_type="$1"  # 'test', 'release', 'lint', 'docs', or empty for all
    local workflows_found=()

    # First try GitHub API if repository info is available
    if command -v gh &>/dev/null && [ -n "$REPO_FULL_NAME" ]; then
        if gh auth status &>/dev/null; then
            # Use JQ patterns to find workflows matching the requested type
            local jq_pattern=""
            case "$workflow_type" in
                "test"|"tests")
                    jq_pattern='.workflows[] | select(.name | test("(?i)test|ci|check") or .path | test("(?i)test|ci|check")) | .name'
                    ;;
                "build"|"release")
                    jq_pattern='.workflows[] | select(.name | test("(?i)release|publish|deploy|build|package|version") or .path | test("(?i)release|publish|deploy|build|package|version")) | .name'
                    ;;
                "lint")
                    jq_pattern='.workflows[] | select(.name | test("(?i)lint|format|style|quality") or .path | test("(?i)lint|format|style|quality")) | .name'
                    ;;
                "docs")
                    jq_pattern='.workflows[] | select(.name | test("(?i)doc|docs|documentation") or .path | test("(?i)doc|docs|documentation")) | .name'
                    ;;
                *)
                    # Return all workflows if type is not specified
                    jq_pattern='.workflows[] | .name'
                    ;;
            esac
            
            # Execute the query and collect results
            while IFS= read -r workflow_name; do
                if [ -n "$workflow_name" ]; then
                    # Remove quotes if present
                    workflow_name="${workflow_name//\"/}"
                    workflows_found+=("$workflow_name")
                fi
            done < <(gh api "repos/$REPO_FULL_NAME/actions/workflows" --jq "$jq_pattern" 2>/dev/null)
        fi
    fi
    
    # If no workflows found via API, try local detection
    if [ ${#workflows_found[@]} -eq 0 ] && [ -d ".github/workflows" ]; then
        print_info "Trying local workflow detection..."
        
        # Define patterns for each workflow type
        local file_pattern=""
        local content_pattern=""
        
        case "$workflow_type" in
            "test"|"tests")
                file_pattern="*test*.yml"
                content_pattern="tests|test|pytest|unittest|jest|mocha|check"
                ;;
            "build"|"release")
                file_pattern="*{release,publish,deploy,build}*.yml"
                content_pattern="release|publish|deploy|build|package|version"
                ;;
            "lint")
                file_pattern="*{lint,format,style,quality}*.yml"
                content_pattern="lint|format|style|quality"
                ;;
            "docs")
                file_pattern="*doc*.yml"
                content_pattern="doc|docs|documentation"
                ;;
            *)
                file_pattern="*.yml"
                ;;
        esac
        
        # Try to find workflows matching patterns
        for file in .github/workflows/$file_pattern; do
            if [ -f "$file" ] && [ "$file" != ".github/workflows/$file_pattern" ]; then
                # If content pattern is specified, check if file contains the pattern
                if [ -z "$content_pattern" ] || grep -q -E "$content_pattern" "$file" 2>/dev/null; then
                    # Extract workflow name from file
                    local name_from_file
                    name_from_file=$(grep -o 'name:.*' "$file" | head -1 | cut -d':' -f2- | sed 's/^[[:space:]]*//')
                    
                    if [ -z "$name_from_file" ]; then
                        # Use filename if name not found in file
                        name_from_file=$(basename "$file" | sed 's/\.[^.]*$//')
                    fi
                    
                    workflows_found+=("$name_from_file")
                fi
            fi
        done
    fi
    
    # If still no workflows found, use default names
    if [ ${#workflows_found[@]} -eq 0 ]; then
        case "$workflow_type" in
            "test"|"tests")
                workflows_found+=("Tests")
                ;;
            "build"|"release")
                workflows_found+=("Auto Release")
                ;;
            "lint")
                workflows_found+=("Lint")
                ;;
            "docs")
                workflows_found+=("Docs")
                ;;
            *)
                workflows_found+=("Tests" "Auto Release" "Lint" "Docs")
                ;;
        esac
        print_warning "No $workflow_type workflows detected. Using default: ${workflows_found[0]}"
    fi
    
    # Return the first matching workflow (or all of them if requested)
    if [ "$2" = "all" ]; then
        printf "%s\n" "${workflows_found[@]}"
    else
        echo "${workflows_found[0]}"
    fi
}

# Function to process test, build, and other workflow logs
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
show_help() {
    print_header "CLAUDE HELPER SCRIPT: GitHub Actions Workflow Logs Tool v$SCRIPT_VERSION"
    echo "Usage: $0 [global_options] <command> [command_options]"
    echo ""
    print_important "Global Options:"
    echo "  --truncate                Truncate output for readability (by default, full output is shown)"
    echo ""
    print_important "Commands:"
    echo "  list                      List recent workflow runs from GitHub"
    echo "  logs [RUN_ID]             Get logs for a specific workflow run"
    echo "  tests                     Get logs for the latest test workflow run"
    echo "  build|release             Get logs for the latest build/release workflow run"
    echo "  lint                      Get logs for the latest linting workflow run"
    echo "  docs                      Get logs for the latest documentation workflow run"
    echo "  saved                     List all saved log files"
    echo "  latest                    Get the 3 most recent logs after last commit"
    echo "  workflow|workflows        List detected workflows in the repository"
    echo "  search PATTERN [CASE_SENSITIVE] [MAX_RESULTS]"
    echo "                            Search all log files for a pattern"
    echo "  stats                     Show statistics about saved log files"
    echo "  cleanup [DAYS] [--dry-run] Clean up logs older than DAYS (default: $MAX_LOG_AGE_DAYS)"
    echo "  classify [LOG_FILE]       Classify errors in a specific log file"
    echo "  version|--version|-v      Show script version and configuration"
    echo "  help|--help|-h            Show this help message"
    echo "  (Running without arguments will auto-detect repository info and workflow status)"
    echo ""
    print_important "Features:"
    echo "  ✓ Auto-detection of repository info from git, project files, etc."
    echo "  ✓ Dynamic workflow detection and categorization by type (test, release, etc.)"
    echo "  ✓ Intelligent error classification with context and root cause analysis"
    echo "  ✓ Full output by default, with optional truncation via --truncate flag"
    echo "  ✓ Works across projects - fully portable with zero configuration"
    echo ""
    print_important "Examples:"
    echo "  $0 list                   List all recent workflow runs"
    echo "  $0 logs 123456789         Get logs for workflow run ID 123456789"
    echo "  $0 tests                  Get logs for the latest test workflow run"
    echo "  $0 saved                  List all saved log files"
    echo "  $0                        Detect repository info and available workflows"
    echo "  $0 --truncate latest      Get the 3 most recent logs with truncated output"
    echo "  $0 search \"error\"       Search all logs for 'error' (case insensitive)"
    echo "  $0 search \"Exception\" true  Search logs for 'Exception' (case sensitive)"
    echo "  $0 cleanup 10             Delete logs older than 10 days"
    echo "  $0 cleanup --dry-run      Show what logs would be deleted without deleting"
    echo "  $0 classify logs/workflow_12345.log  Classify errors in a specific log file"
    echo ""
}

# Function to list saved log files
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