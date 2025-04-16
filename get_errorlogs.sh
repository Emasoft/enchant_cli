#!/bin/bash
# get_errorlogs.sh - CLAUDE HELPER SCRIPT to fetch error logs from GitHub Actions workflows
# Version 1.1.0 - Enhanced to be fully portable and auto-detect repository details
set -eo pipefail

# Script version
SCRIPT_VERSION="1.1.0"

# Default configuration settings
CONFIG_FILE=".claude_helper_config"
MAX_LOGS_PER_WORKFLOW=5    # Maximum number of log files to keep per workflow ID
MAX_LOG_AGE_DAYS=30        # Maximum age in days for log files before cleanup
MAX_TOTAL_LOGS=50          # Maximum total log files to keep
DEFAULT_OUTPUT_LINES=50    # Default number of lines to display when truncating
DO_TRUNCATE=false          # Default truncation behavior - now false by default

# Parse command-line options
for arg in "$@"; do
    if [ "$arg" = "--truncate" ]; then
        DO_TRUNCATE=true
    fi
done

# Get script directory - resolves symlinks
SCRIPT_DIR=$(cd -- "$(dirname -- "$(readlink -f "${BASH_SOURCE[0]}" 2>/dev/null || echo "${BASH_SOURCE[0]}")")" &>/dev/null && pwd)

# Function to dynamically determine repository information
detect_repository_info() {
    # Create global variables to store repository info
    local detected_owner=""
    local detected_name=""
    local detected_full=""
    
    # Try to get repository information from git
    if command -v git &>/dev/null && git rev-parse --is-inside-work-tree &>/dev/null; then
        # Get remote URL
        local remote_url=$(git config --get remote.origin.url 2>/dev/null)
        
        if [ -n "$remote_url" ]; then
            # Extract owner and name from remote URL
            # Handle different URL formats: https, git, ssh
            if [[ "$remote_url" =~ github\.com[:/]([^/]+)/([^/.]+)(\.git)? ]]; then
                detected_owner="${BASH_REMATCH[1]}"
                detected_name="${BASH_REMATCH[2]}"
                detected_full="$detected_owner/$detected_name"
                print_success "Repository information detected from git: $detected_full"
            elif [[ "$remote_url" =~ ([^:/@]+)[:/]([^/.]+)(\.git)? ]]; then
                # Try to handle other git hosting services
                detected_owner="${BASH_REMATCH[1]}"
                detected_name="${BASH_REMATCH[2]}"
                detected_full="$detected_owner/$detected_name"
                print_success "Repository information detected from git: $detected_full"
            fi
        fi
    fi
    
    # If git detection failed, try package configuration files
    if [ -z "$detected_owner" ] || [ -z "$detected_name" ]; then
        # Try pyproject.toml
        if [ -f "pyproject.toml" ]; then
            # Try different patterns for extracting repo info from pyproject.toml
            local url=$(grep -E "homepage|repository|url" pyproject.toml | grep -o "https://[^\"']*" | head -1)
            if [[ "$url" =~ https?://github\.com/([^/]+)/([^/.]+) ]]; then
                detected_owner="${BASH_REMATCH[1]}"
                detected_name="${BASH_REMATCH[2]}"
                detected_full="$detected_owner/$detected_name"
                print_success "Repository information detected from pyproject.toml: $detected_full"
            elif [ -z "$detected_name" ]; then
                # Try to get just the project name from pyproject.toml
                detected_name=$(grep -E "^name\s*=" pyproject.toml | head -1 | sed -E 's/.*name\s*=\s*"([^"]+)".*/\1/' | sed 's/-/_/g')
                if [ -n "$detected_name" ]; then
                    print_success "Project name detected from pyproject.toml: $detected_name"
                    # If we found the name but not the owner, try to extract email domain as owner
                    if [ -z "$detected_owner" ]; then
                        detected_owner=$(grep -E "email\s*=" pyproject.toml | grep -o "[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}" | head -1 | cut -d'@' -f2 | cut -d'.' -f1)
                        if [ -n "$detected_owner" ]; then
                            detected_full="$detected_owner/$detected_name"
                            print_success "Repository owner guessed from email domain: $detected_owner"
                        fi
                    fi
                fi
            fi
        fi
        
        # Try package.json
        if [ -z "$detected_owner" ] || [ -z "$detected_name" ]; then
            if [ -f "package.json" ]; then
                local url=$(grep -E "\"homepage\"|\"repository\"" package.json | grep -o "https://[^\"]*" | head -1)
                if [[ "$url" =~ https?://github\.com/([^/]+)/([^/.]+) ]]; then
                    detected_owner="${BASH_REMATCH[1]}"
                    detected_name="${BASH_REMATCH[2]}"
                    detected_full="$detected_owner/$detected_name"
                    print_success "Repository information detected from package.json: $detected_full"
                elif [ -z "$detected_name" ]; then
                    # Try to get just the project name from package.json
                    detected_name=$(grep -E "\"name\":" package.json | head -1 | sed -E 's/.*"name":\s*"([^"]+)".*/\1/' | sed 's/-/_/g')
                    if [ -n "$detected_name" ]; then
                        print_success "Project name detected from package.json: $detected_name"
                    fi
                fi
            fi
        fi
        
        # Try cargo.toml for Rust projects
        if [ -z "$detected_owner" ] || [ -z "$detected_name" ]; then
            if [ -f "Cargo.toml" ]; then
                local url=$(grep -E "repository\s*=" Cargo.toml | grep -o "https://[^\"']*" | head -1)
                if [[ "$url" =~ https?://github\.com/([^/]+)/([^/.]+) ]]; then
                    detected_owner="${BASH_REMATCH[1]}"
                    detected_name="${BASH_REMATCH[2]}"
                    detected_full="$detected_owner/$detected_name"
                    print_success "Repository information detected from Cargo.toml: $detected_full"
                elif [ -z "$detected_name" ]; then
                    # Try to get just the project name from Cargo.toml
                    detected_name=$(grep -E "^name\s*=" Cargo.toml | head -1 | sed -E 's/.*name\s*=\s*"([^"]+)".*/\1/' | sed 's/-/_/g')
                    if [ -n "$detected_name" ]; then
                        print_success "Project name detected from Cargo.toml: $detected_name"
                    fi
                fi
            fi
        fi
        
        # Try setup.py as a last resort for Python projects
        if [ -z "$detected_owner" ] || [ -z "$detected_name" ]; then
            if [ -f "setup.py" ]; then
                # Try to find URL pattern in setup.py
                local url=$(grep -E "url\s*=" setup.py | grep -o "https://[^\"']*" | head -1)
                if [[ "$url" =~ https?://github\.com/([^/]+)/([^/.]+) ]]; then
                    detected_owner="${BASH_REMATCH[1]}"
                    detected_name="${BASH_REMATCH[2]}"
                    detected_full="$detected_owner/$detected_name"
                    print_success "Repository information detected from setup.py: $detected_full"
                elif [ -z "$detected_name" ]; then
                    # Try to get just the project name from setup.py
                    detected_name=$(grep -E "name\s*=" setup.py | head -1 | sed -E "s/.*name\s*=\s*['\"]([^'\"]+)['\"].*/\1/" | sed 's/-/_/g')
                    if [ -n "$detected_name" ]; then
                        print_success "Project name detected from setup.py: $detected_name"
                    fi
                fi
            fi
        fi
        
        # Try project directory name if all else fails
        if [ -z "$detected_name" ]; then
            detected_name=$(basename "$(pwd)" | sed 's/-/_/g')
            print_warning "Using current directory name as project name: $detected_name"
        fi
        
        # Try hostname or username for owner if still missing
        if [ -z "$detected_owner" ]; then
            if command -v hostname &>/dev/null; then
                detected_owner=$(hostname | cut -d'.' -f1)
            else
                detected_owner=$(whoami)
            fi
            print_warning "Could not detect repository owner. Using fallback: $detected_owner"
        fi
        
        # Form the full name if we have both parts
        if [ -n "$detected_owner" ] && [ -n "$detected_name" ]; then
            detected_full="$detected_owner/$detected_name"
        fi
    fi
    
    # Export the detected values
    REPO_OWNER="$detected_owner"
    REPO_NAME="$detected_name"
    REPO_FULL_NAME="$detected_full"
    
    print_info "Using repository: $REPO_FULL_NAME"
}

# Function to detect available workflows in the repository
detect_workflows() {
    local workflows=()
    local workflow_files=()
    local workflow_types=()
    
    print_header "Detecting GitHub Workflows"
    
    # Check local .github/workflows directory
    if [ -d ".github/workflows" ]; then
        # Get workflow files
        for workflow_file in .github/workflows/*.{yml,yaml}; do
            if [ -f "$workflow_file" ]; then
                workflow_files+=("$workflow_file")
                
                # Extract workflow name from the file
                local workflow_name=$(grep -E "name:" "$workflow_file" | head -1 | sed 's/name:[[:space:]]*//g' | tr -d '"'"'" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
                if [ -n "$workflow_name" ]; then
                    workflows+=("$workflow_name")
                    print_info "Detected local workflow: $workflow_name ($workflow_file)"
                    
                    # Try to determine workflow type
                    if grep -i -E "\btests\b|\btest\b|\btesting\b|\bci\b" "$workflow_file" >/dev/null; then
                        workflow_types+=("test")
                        print_info "  - Type: Testing workflow"
                    elif grep -i -E "\brelease\b|\bdeploy\b|\bpublish\b|\bbuild\b|\bcd\b" "$workflow_file" >/dev/null; then
                        workflow_types+=("release")
                        print_info "  - Type: Release/Deployment workflow"
                    elif grep -i -E "\blint\b|\bstyle\b|\bformat\b|\bquality\b" "$workflow_file" >/dev/null; then
                        workflow_types+=("lint")
                        print_info "  - Type: Linting/Code quality workflow"
                    elif grep -i -E "\bdocs\b|\bdocumentation\b" "$workflow_file" >/dev/null; then
                        workflow_types+=("docs")
                        print_info "  - Type: Documentation workflow"
                    else
                        workflow_types+=("other")
                        print_info "  - Type: General purpose workflow"
                    fi
                else
                    # Use filename if name not found
                    workflow_name=$(basename "$workflow_file" | sed 's/\.[^.]*$//')
                    workflows+=("$workflow_name")
                    print_info "Detected local workflow from filename: $workflow_name ($workflow_file)"
                    
                    # Try to determine workflow type from filename
                    if [[ "$workflow_name" =~ [tT]est|CI ]]; then
                        workflow_types+=("test")
                        print_info "  - Type: Testing workflow (determined from filename)"
                    elif [[ "$workflow_name" =~ [rR]elease|[dD]eploy|[pP]ublish|[bB]uild|CD ]]; then
                        workflow_types+=("release")
                        print_info "  - Type: Release/Deployment workflow (determined from filename)"
                    elif [[ "$workflow_name" =~ [lL]int|[sS]tyle|[fF]ormat|[qQ]uality ]]; then
                        workflow_types+=("lint")
                        print_info "  - Type: Linting/Code quality workflow (determined from filename)"
                    elif [[ "$workflow_name" =~ [dD]ocs|[dD]ocumentation ]]; then
                        workflow_types+=("docs")
                        print_info "  - Type: Documentation workflow (determined from filename)"
                    else
                        workflow_types+=("other")
                        print_info "  - Type: General purpose workflow (determined from filename)"
                    fi
                fi
            fi
        done
    fi
    
    # If no local workflow files found, try to look for workflow references in project files
    if [ ${#workflow_files[@]} -eq 0 ]; then
        print_warning "No workflow files found in .github/workflows/ directory"
        print_info "Trying to find workflow references in project configuration files..."
        
        # Look for GitHub Actions references in package.json, README.md, etc.
        local has_github_actions=false
        
        # Check README.md for workflow badge references
        if [ -f "README.md" ]; then
            if grep -i -E "github.com/[^/]+/[^/]+/(workflows|actions)" "README.md" >/dev/null; then
                print_info "Found GitHub Actions references in README.md"
                has_github_actions=true
                
                # Try to extract workflow names from badges
                local badge_names=$(grep -i -E "github.com/[^/]+/[^/]+/workflows/([^/]+)" "README.md" | grep -o "workflows/[^/)]*/badge.svg" | sed 's/workflows\///g' | sed 's/\/badge.svg//g' | tr -d '"' | sort -u)
                if [ -n "$badge_names" ]; then
                    print_info "Extracted workflow names from badges:"
                    while IFS= read -r badge_name; do
                        print_info "  - $badge_name"
                        # Convert URL encoding to spaces
                        badge_name=$(echo "$badge_name" | sed 's/%20/ /g')
                        workflows+=("$badge_name")
                        # Guess workflow type from badge name
                        if [[ "$badge_name" =~ [tT]est|CI ]]; then
                            workflow_types+=("test")
                        elif [[ "$badge_name" =~ [rR]elease|[dD]eploy|[pP]ublish|[bB]uild|CD ]]; then
                            workflow_types+=("release")
                        elif [[ "$badge_name" =~ [lL]int|[sS]tyle|[fF]ormat|[qQ]uality ]]; then
                            workflow_types+=("lint")
                        elif [[ "$badge_name" =~ [dD]ocs|[dD]ocumentation ]]; then
                            workflow_types+=("docs")
                        else
                            workflow_types+=("other")
                        fi
                    done <<< "$badge_names"
                fi
            fi
        fi
    fi
    
    # If no local workflows found, try to get them from GitHub
    if [ ${#workflows[@]} -eq 0 ] && command -v gh &>/dev/null; then
        if gh auth status &>/dev/null; then
            print_info "Checking GitHub for workflows..."
            # Try to list workflows from GitHub
            if gh workflow list --repo "$REPO_FULL_NAME" &>/dev/null; then
                print_success "Successfully connected to GitHub API for $REPO_FULL_NAME"
                mapfile -t remote_workflows < <(gh workflow list --repo "$REPO_FULL_NAME" --json name,path -q '.[] | "\(.name)|\(.path)"' 2>/dev/null)
                for workflow_data in "${remote_workflows[@]}"; do
                    local workflow_name=$(echo "$workflow_data" | cut -d'|' -f1)
                    local workflow_path=$(echo "$workflow_data" | cut -d'|' -f2)
                    workflows+=("$workflow_name")
                    print_info "Detected remote workflow: $workflow_name ($workflow_path)"
                    
                    # Try to determine workflow type from name
                    if [[ "$workflow_name" =~ [tT]est|CI ]]; then
                        workflow_types+=("test")
                        print_info "  - Type: Testing workflow"
                    elif [[ "$workflow_name" =~ [rR]elease|[dD]eploy|[pP]ublish|[bB]uild|CD ]]; then
                        workflow_types+=("release")
                        print_info "  - Type: Release/Deployment workflow"
                    elif [[ "$workflow_name" =~ [lL]int|[sS]tyle|[fF]ormat|[qQ]uality ]]; then
                        workflow_types+=("lint")
                        print_info "  - Type: Linting/Code quality workflow"
                    elif [[ "$workflow_name" =~ [dD]ocs|[dD]ocumentation ]]; then
                        workflow_types+=("docs")
                        print_info "  - Type: Documentation workflow"
                    else
                        workflow_types+=("other")
                        print_info "  - Type: General purpose workflow"
                    fi
                done
            else
                print_warning "Could not get workflows from GitHub API for $REPO_FULL_NAME"
            fi
        else
            print_warning "Not authenticated with GitHub. Some remote repository features may be limited."
        fi
    fi
    
    # If still no workflows found, try to make intelligent guesses based on common patterns
    if [ ${#workflows[@]} -eq 0 ]; then
        print_warning "No workflows detected through GitHub API or local files"
        print_info "Making intelligent guesses based on project structure..."
        
        # Check if this is a Python project
        if [ -f "setup.py" ] || [ -f "pyproject.toml" ] || [ -d "src" ] && ls src/*.py &>/dev/null; then
            print_info "Detected Python project structure"
            workflows+=("Python Tests")
            workflow_types+=("test")
            
            # Check for PyPI-related files
            if grep -q -E "pypi|twine|pip" "setup.py" 2>/dev/null || grep -q -E "pypi|twine|pip" "pyproject.toml" 2>/dev/null; then
                print_info "Detected PyPI publishing potential"
                workflows+=("Publish Python Package")
                workflow_types+=("release")
            fi
        # Check if this is a JavaScript/Node.js project
        elif [ -f "package.json" ] || [ -f "package-lock.json" ] || [ -f "yarn.lock" ]; then
            print_info "Detected JavaScript/Node.js project structure"
            workflows+=("Node.js CI")
            workflow_types+=("test")
            
            # Check for npm publishing potential
            if grep -q -E "\"private\":\s*false" "package.json" 2>/dev/null || grep -q -E "\"publish" "package.json" 2>/dev/null; then
                print_info "Detected npm publishing potential"
                workflows+=("Node.js Package")
                workflow_types+=("release")
            fi
        # Check if this is a Rust project
        elif [ -f "Cargo.toml" ] || [ -f "Cargo.lock" ]; then
            print_info "Detected Rust project structure"
            workflows+=("Rust CI")
            workflow_types+=("test")
            
            # Check for crates.io publishing potential
            if grep -q -E "publish\s*=" "Cargo.toml" 2>/dev/null; then
                print_info "Detected crates.io publishing potential"
                workflows+=("Rust Publish")
                workflow_types+=("release")
            fi
        # Check if this is a Docker project
        elif [ -f "Dockerfile" ] || [ -f "docker-compose.yml" ]; then
            print_info "Detected Docker project structure"
            workflows+=("Docker Build")
            workflow_types+=("test")
            workflows+=("Docker Publish")
            workflow_types+=("release")
        # General fallback
        else
            workflows=("CI" "CD")
            workflow_types=("test" "release")
            print_warning "Using generic workflow names: ${workflows[*]}"
        fi
    fi
    
    # Set global variable for workflows
    AVAILABLE_WORKFLOWS=("${workflows[@]}")
    
    # Set global variables for workflow types
    TEST_WORKFLOWS=()
    RELEASE_WORKFLOWS=()
    LINT_WORKFLOWS=()
    DOCS_WORKFLOWS=()
    OTHER_WORKFLOWS=()
    
    # Categorize workflows by type
    for i in "${!workflows[@]}"; do
        workflow_name="${workflows[$i]}"
        if [ $i -lt ${#workflow_types[@]} ]; then
            workflow_type="${workflow_types[$i]}"
            
            case "$workflow_type" in
                "test")
                    TEST_WORKFLOWS+=("$workflow_name")
                    ;;
                "release")
                    RELEASE_WORKFLOWS+=("$workflow_name")
                    ;;
                "lint")
                    LINT_WORKFLOWS+=("$workflow_name")
                    ;;
                "docs")
                    DOCS_WORKFLOWS+=("$workflow_name")
                    ;;
                *)
                    OTHER_WORKFLOWS+=("$workflow_name")
                    ;;
            esac
        else
            # If type is missing, try to determine from name
            if [[ "$workflow_name" =~ [tT]est|CI ]]; then
                TEST_WORKFLOWS+=("$workflow_name")
            elif [[ "$workflow_name" =~ [rR]elease|[dD]eploy|[pP]ublish|[bB]uild|CD ]]; then
                RELEASE_WORKFLOWS+=("$workflow_name")
            elif [[ "$workflow_name" =~ [lL]int|[sS]tyle|[fF]ormat|[qQ]uality ]]; then
                LINT_WORKFLOWS+=("$workflow_name")
            elif [[ "$workflow_name" =~ [dD]ocs|[dD]ocumentation ]]; then
                DOCS_WORKFLOWS+=("$workflow_name")
            else
                OTHER_WORKFLOWS+=("$workflow_name")
            fi
        fi
    done
    
    # Print summary of detected workflows by type
    if [ ${#TEST_WORKFLOWS[@]} -gt 0 ]; then
        print_info "Detected testing workflows: ${TEST_WORKFLOWS[*]}"
    fi
    
    if [ ${#RELEASE_WORKFLOWS[@]} -gt 0 ]; then
        print_info "Detected release workflows: ${RELEASE_WORKFLOWS[*]}"
    fi
    
    if [ ${#LINT_WORKFLOWS[@]} -gt 0 ]; then
        print_info "Detected linting workflows: ${LINT_WORKFLOWS[*]}"
    fi
    
    if [ ${#DOCS_WORKFLOWS[@]} -gt 0 ]; then
        print_info "Detected documentation workflows: ${DOCS_WORKFLOWS[*]}"
    fi
    
    if [ ${#OTHER_WORKFLOWS[@]} -gt 0 ]; then
        print_info "Detected other workflows: ${OTHER_WORKFLOWS[*]}"
    fi
    
    print_success "Total workflows detected: ${#AVAILABLE_WORKFLOWS[@]}"
}

# Print colored output
print_header() { echo -e "\033[1;33m🔶 $1\033[0m"; }
print_success() { echo -e "\033[1;32m✅ $1\033[0m"; }
print_error() { echo -e "\033[1;31m❌ $1\033[0m"; }
print_warning() { echo -e "\033[1;33m⚠️ $1\033[0m"; }
print_info() { echo -e "\033[1;34mℹ️ $1\033[0m"; }
print_critical() { echo -e "\033[1;37;41m🚨 $1\033[0m"; }  # White text on red background
print_severe() { echo -e "\033[1;37;45m🔥 $1\033[0m"; }    # White text on purple background
print_important() { echo -e "\033[1;97;44m📣 $1\033[0m"; } # White text on blue background

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
    local no_display="${2:-false}"  # Option to suppress display, just download
    
    if [ -z "$run_id" ]; then
        # First try to get the ID of a recent failed workflow run for any of our detected workflows
        for workflow in "${AVAILABLE_WORKFLOWS[@]}"; do
            workflow_query=$(echo "$workflow" | tr -d " " | tr '[:upper:]' '[:lower:]')
            print_info "Looking for failed runs of workflow: $workflow"
            
            run_id=$(gh run list --repo "$REPO_FULL_NAME" --workflow "$workflow_query" --status failure --limit 1 --json databaseId -q '.[0].databaseId' 2>/dev/null || echo "")
            if [ -n "$run_id" ]; then
                print_info "Found failed run of '$workflow' workflow: $run_id"
                break
            fi
        done
        
        # If we didn't find any failed workflow, try any status
        if [ -z "$run_id" ]; then
            for workflow in "${AVAILABLE_WORKFLOWS[@]}"; do
                workflow_query=$(echo "$workflow" | tr -d " " | tr '[:upper:]' '[:lower:]')
                print_info "Looking for any runs of workflow: $workflow"
                
                run_id=$(gh run list --repo "$REPO_FULL_NAME" --workflow "$workflow_query" --limit 1 --json databaseId -q '.[0].databaseId' 2>/dev/null || echo "")
                if [ -n "$run_id" ]; then
                    print_info "Found run of '$workflow' workflow: $run_id"
                    break
                fi
            done
        fi
        
        # Last resort - get any workflow run if we still can't find anything
        if [ -z "$run_id" ]; then
            print_warning "Couldn't find specific workflow runs. Trying any workflow..."
            run_id=$(gh run list --repo "$REPO_FULL_NAME" --limit 1 --json databaseId -q '.[0].databaseId' 2>/dev/null || echo "")
            
            if [ -z "$run_id" ]; then
                print_error "No workflow runs found at all."
                return 1
            fi
            
            print_info "Using most recent workflow run: $run_id"
        fi
    else
        print_info "Fetching logs for workflow run: $run_id"
    fi
    
    # Create a logs directory if it doesn't exist
    mkdir -p logs
    
    # Get workflow information with fallback options
    print_info "Fetching workflow information..."
    workflow_info=""
    
    # Try different methods to get workflow info
    for attempt in {1..3}; do
        workflow_info=$(gh run view "$run_id" --repo "$REPO_FULL_NAME" --json name,url,status,conclusion,createdAt,displayTitle 2>/dev/null)
        if [ -n "$workflow_info" ]; then
            break
        fi
        
        # If json output fails, try plain text and parse
        if [ -z "$workflow_info" ] && [ $attempt -eq 2 ]; then
            print_warning "JSON API failed, trying plain text output..."
            workflow_info_text=$(gh run view "$run_id" --repo "$REPO_FULL_NAME" 2>/dev/null)
            if [ -n "$workflow_info_text" ]; then
                # Parse the text output into a simple JSON format
                workflow_name=$(echo "$workflow_info_text" | grep -E "^name:" | sed 's/name:[[:space:]]*//g')
                workflow_status=$(echo "$workflow_info_text" | grep -E "^status:" | sed 's/status:[[:space:]]*//g')
                workflow_url=$(echo "$workflow_info_text" | grep -E "^url:" | sed 's/url:[[:space:]]*//g')
                workflow_info="{\"name\":\"$workflow_name\",\"status\":\"$workflow_status\",\"url\":\"$workflow_url\"}"
                break
            fi
        fi
        
        # Fallback to manually constructing info from the run ID if all else fails
        if [ -z "$workflow_info" ] && [ $attempt -eq 3 ]; then
            print_warning "Could not get workflow information via GitHub CLI. Constructing minimal information..."
            workflow_url="https://github.com/$REPO_FULL_NAME/actions/runs/$run_id"
            workflow_info="{\"name\":\"Unknown Workflow\",\"status\":\"unknown\",\"conclusion\":\"unknown\",\"url\":\"$workflow_url\",\"createdAt\":\"unknown\"}"
            break
        fi
        
        sleep 1
    done
    
    if [ -z "$workflow_info" ]; then
        print_error "Could not get workflow information for run ID: $run_id"
        print_warning "This might be a permissions issue or the workflow has been deleted."
        return 1
    fi
    
    # Get and display workflow details with fallbacks for missing fields
    workflow_name=$(echo "$workflow_info" | jq -r '.name // "Unknown"' 2>/dev/null || echo "Unknown")
    workflow_name=$(echo "$workflow_name" | tr ' ' '_' | tr '/' '_')
    workflow_status=$(echo "$workflow_info" | jq -r '.status // "Unknown"' 2>/dev/null || echo "Unknown")
    workflow_conclusion=$(echo "$workflow_info" | jq -r '.conclusion // "Unknown"' 2>/dev/null || echo "Unknown")
    workflow_url=$(echo "$workflow_info" | jq -r '.url // "Unknown"' 2>/dev/null || echo "https://github.com/$REPO_FULL_NAME/actions/runs/$run_id")
    created_at=$(echo "$workflow_info" | jq -r '.createdAt // "Unknown"' 2>/dev/null || echo "Unknown")
    
    if [ "$no_display" != "true" ]; then
        print_info "Workflow: $workflow_name"
        print_info "Status: $workflow_status (Conclusion: $workflow_conclusion)"
        print_info "Created: $created_at"
        print_info "URL: $workflow_url"
    fi
    
    # Setup log file path
    timestamp=$(date +"%Y%m%d-%H%M%S")
    log_file="logs/workflow_${run_id}_${timestamp}.log"
    error_summary_file="${log_file}.summary"
    error_file="${log_file}.errors"
    classified_file="${log_file}.classified"
    
    if [ "$no_display" != "true" ]; then
        print_info "Downloading logs to $log_file..."
    fi
    
    # Try to download the logs, handling failure gracefully and trying alternative methods
    download_success=false
    
    # Method 1: Use GitHub CLI tool
    if gh run view "$run_id" --repo "$REPO_FULL_NAME" --log > "$log_file" 2>/dev/null; then
        download_success=true
    else
        # Method 2: Try to use GitHub API via curl (for cases when gh CLI can't fetch but the logs exist)
        if command -v curl &>/dev/null && [ -n "$GITHUB_TOKEN" ]; then
            print_warning "GitHub CLI download failed, trying direct API access..."
            curl -s -H "Authorization: token $GITHUB_TOKEN" \
                "https://api.github.com/repos/$REPO_FULL_NAME/actions/runs/$run_id/logs" \
                -o "${log_file}.zip" 2>/dev/null
            
            if [ -f "${log_file}.zip" ] && command -v unzip &>/dev/null; then
                unzip -q -o "${log_file}.zip" -d "logs/temp_${run_id}" 2>/dev/null
                if [ -d "logs/temp_${run_id}" ]; then
                    # Concatenate all log files into one
                    find "logs/temp_${run_id}" -type f -name "*.txt" -exec cat {} \; > "$log_file"
                    rm -rf "logs/temp_${run_id}"
                    rm -f "${log_file}.zip"
                    download_success=true
                fi
            fi
        fi
    fi
    
    # If all download methods failed, create a placeholder log
    if [ "$download_success" != "true" ]; then
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
    print_info "Analyzing logs for errors..."
    
    # Create error files
    > "$error_file"  # Clear or create the file
    > "$error_summary_file"  # Clear or create summary file
    > "$classified_file"  # Clear or create classified errors file
    
    # Get file size
    log_file_size=$(wc -c < "$log_file")
    
    # Only process if the log file is not empty
    if [ "$log_file_size" -gt 0 ]; then
        # First, run the classification to create the classified error file
        classify_errors "$log_file" "$classified_file"
        
        # Save full error extraction with context to the main error file
        print_info "Extracting detailed errors with context..."
        
        # Extract critical errors with more context
        grep -n -A 10 -B 5 -E "${ERROR_PATTERNS["critical"]}" "$log_file" >> "$error_file" 2>/dev/null || true
        
        # Extract severe errors with context 
        grep -n -A 8 -B 3 -E "${ERROR_PATTERNS["severe"]}" "$log_file" | grep -v -E "${ERROR_PATTERNS["critical"]}" >> "$error_file" 2>/dev/null || true
        
        # Extract warnings with less context
        grep -n -A 3 -B 1 -E "${ERROR_PATTERNS["warning"]}" "$log_file" | grep -v -E "${ERROR_PATTERNS["critical"]}|${ERROR_PATTERNS["severe"]}" >> "$error_file" 2>/dev/null || true
        
        # Capture additional context around errors (like function names, class names, file paths)
        grep -n -B 2 -A 0 -E "at [a-zA-Z0-9_.]+\.[a-zA-Z0-9_]+\(" "$log_file" >> "$error_file" 2>/dev/null || true
        grep -n -B 0 -A 0 -E "File \"[^\"]+\", line [0-9]+" "$log_file" >> "$error_file" 2>/dev/null || true
        grep -n -B 0 -A 0 -E "\s+in [a-zA-Z0-9_.]+\.[a-zA-Z0-9_]+" "$log_file" >> "$error_file" 2>/dev/null || true
        
        # Check if any errors were found
        if [ ! -s "$error_file" ]; then
            print_info "No specific errors found. Doing a broader search..."
            # Fallback to more generic error patterns
            grep -n -A 3 -B 1 -E "fail|warn|except|wrong|incorrect|invalid|could not|cannot|unexpected" "$log_file" >> "$error_file" 2>/dev/null || true
        fi
        
        # Create a summary file with the most important bits
        print_info "Creating error summary..."
        
        # Basic run info
        cat > "$error_summary_file" << EOF
# Workflow Summary
- **Run ID:** $run_id
- **Workflow:** $workflow_name
- **Status:** $workflow_status (Conclusion: $workflow_conclusion)
- **Created:** $created_at
- **URL:** $workflow_url

EOF
        
        # If we have classified errors, add them to the summary
        if [ -s "$classified_file" ]; then
            cat "$classified_file" >> "$error_summary_file"
        fi
        
        # If we still don't have any errors, add sample of the log
        if [ ! -s "$error_file" ] && [ ! -s "$classified_file" ]; then
            echo -e "\n## Log Sample (No Errors Found)\n" >> "$error_summary_file"
            head -n 20 "$log_file" >> "$error_summary_file"
            echo -e "\n[...]\n" >> "$error_summary_file"
            tail -n 20 "$log_file" >> "$error_summary_file"
        fi
        
        # Show statistics
        total_lines=$(wc -l < "$log_file")
        error_count=$(grep -c -v "^--$" "$error_file" 2>/dev/null || echo "0")
        
        # If not displaying, we're done
        if [ "$no_display" = "true" ]; then
            if [ -s "$error_file" ] || [ -s "$classified_file" ]; then
                print_success "Logs analyzed: $log_file with $error_count potential errors"
            else
                print_success "Logs analyzed: $log_file (no errors found)"
            fi
            return 0
        fi
        
        print_success "Logs downloaded successfully: $log_file ($total_lines lines)"
        
        # Display the error summary to stdout (not truncated)
        if [ -s "$classified_file" ]; then
            print_important "CLASSIFIED ERROR SUMMARY:"
            cat "$classified_file"
            echo ""
        fi
        
        # Show detailed errors based on truncation setting
        if [ -s "$error_file" ]; then
            print_info "Found potential errors in the log."
            
            if [ "$DO_TRUNCATE" = "true" ]; then
                # Truncated display - show first and last few errors
                print_info "Most significant errors: (truncated, run without --truncate to see all)"
                echo "───────────────────────────────────────────────────────────────"
                # Show the first N lines of the error file
                head -n "$DEFAULT_OUTPUT_LINES" "$error_file"
                echo "..."
                echo "───────────────────────────────────────────────────────────────"
                
                # Show the last errors as well - often the most important
                print_info "Last errors in the log: (truncated, run without --truncate to see all)"
                echo "───────────────────────────────────────────────────────────────"
                tail -n "$DEFAULT_OUTPUT_LINES" "$error_file"
                echo "───────────────────────────────────────────────────────────────"
                
                print_info "Full error log written to: $error_file"
            else
                # Full display - show all errors
                print_info "Full error details:"
                echo "───────────────────────────────────────────────────────────────"
                cat "$error_file"
                echo "───────────────────────────────────────────────────────────────"
            fi
            
            print_info "For complete logs, see: $log_file"
        else
            print_info "No clear errors detected. Please check the full log file: $log_file"
            
            # Show a sample of the log file
            if [ "$DO_TRUNCATE" = "true" ]; then
                echo "───────────────────────────────────────────────────────────────"
                head -n 20 "$log_file"
                echo "..."
                echo "───────────────────────────────────────────────────────────────"
            else
                echo "───────────────────────────────────────────────────────────────"
                cat "$log_file"
                echo "───────────────────────────────────────────────────────────────"
            fi
        fi
    else
        print_warning "Log file is empty or contains no usable content."
        print_info "Please check directly on GitHub:"
        print_info "$workflow_url"
        
        # Create a basic error note
        echo "Log file was empty. Please check workflow directly on GitHub: $workflow_url" > "$error_file"
        echo "Log file was empty. Please check workflow directly on GitHub: $workflow_url" > "$error_summary_file"
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

# Constants for log settings
MAX_LOGS_PER_WORKFLOW=5  # Maximum number of log files to keep per workflow ID
MAX_LOG_AGE_DAYS=30      # Maximum age in days for log files before cleanup
MAX_TOTAL_LOGS=50        # Maximum total log files to keep

# Enhanced error pattern categories
declare -A ERROR_PATTERNS=(
    ["critical"]="Process completed with exit code [1-9]|fatal error|fatal:|FATAL ERROR|Assertion failed|Segmentation fault|core dumped|killed|ERROR:|Connection refused|panic|PANIC|assert|ASSERT|terminated|abort|SIGSEGV|SIGABRT|SIGILL|SIGFPE"
    ["severe"]="exit code [1-9]|failure:|failed with|FAILED|Exception|exception:|Error:|error:|undefined reference|Cannot find|not found|No such file|Permission denied|AccessDenied|Could not access|Cannot access|ImportError|ModuleNotFoundError|TypeError|ValueError|KeyError|AttributeError|AssertionError|UnboundLocalError|IndexError|SyntaxError|NameError|RuntimeError|unexpected|failed to|EACCES|EPERM|ENOENT|compilation failed|command failed|exited with code"
    ["warning"]="WARNING:|warning:|deprecated|Deprecated|DEPRECATED|fixme|FIXME|TODO|todo:|ignored|skipped|suspicious|insecure|unsafe|consider|recommended|inconsistent|possibly|PendingDeprecationWarning|FutureWarning|UserWarning|ResourceWarning"
)

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

# Function to perform log rotation/cleanup to prevent disk space issues
cleanup_old_logs() {
    local max_age="$1"  # In days, defaults to MAX_LOG_AGE_DAYS if not specified
    local dry_run="$2"  # Set to "true" for dry run
    
    if [ -z "$max_age" ]; then
        max_age=$MAX_LOG_AGE_DAYS
    fi
    
    print_header "Log Maintenance"
    print_info "Cleaning up logs older than $max_age days"
    
    local old_logs=()
    local total_size=0
    local current_date=$(date +%s)
    
    # Find log files older than max_age days
    for log_file in logs/workflow_*.log logs/workflow_*.log.errors; do
        if [ -f "$log_file" ]; then
            # Extract timestamp from filename (format: workflow_ID_YYYYMMDD-HHMMSS.log)
            local log_timestamp
            log_timestamp=$(echo "$log_file" | grep -o "[0-9]\{8\}-[0-9]\{6\}")
            
            if [ -n "$log_timestamp" ]; then
                # Convert timestamp to seconds since epoch
                local log_date
                log_date=$(date -d "${log_timestamp:0:8} ${log_timestamp:9:2}:${log_timestamp:11:2}:${log_timestamp:13:2}" +%s 2>/dev/null || \
                          date -j -f "%Y%m%d-%H%M%S" "$log_timestamp" +%s 2>/dev/null)
                
                if [ -n "$log_date" ]; then
                    # Calculate age in days
                    local age_seconds=$((current_date - log_date))
                    local age_days=$((age_seconds / 86400))
                    
                    if [ "$age_days" -gt "$max_age" ]; then
                        old_logs+=("$log_file")
                        total_size=$((total_size + $(stat -c %s "$log_file" 2>/dev/null || stat -f %z "$log_file" 2>/dev/null)))
                    fi
                fi
            fi
        fi
    done
    
    # Report findings
    local file_count=${#old_logs[@]}
    local size_mb=$(echo "scale=2; $total_size / 1048576" | bc)
    
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
    
    # Get all log files (not errors)
    for log_file in logs/workflow_*.log; do
        if [ -f "$log_file" ] && ! [[ "$log_file" == *".errors" ]]; then
            all_logs+=("$log_file")
        fi
    done
    
    # Calculate how many files to delete
    local total_log_count=${#all_logs[@]}
    local delete_count=$((total_log_count - MAX_TOTAL_LOGS))
    
    if [ "$delete_count" -gt 0 ]; then
        # Sort by timestamp, oldest first
        mapfile -t sorted_logs < <(printf '%s\n' "${all_logs[@]}" | sort)
        
        print_info "Maintaining maximum of $MAX_TOTAL_LOGS log files (currently have $total_log_count)"
        
        # Delete oldest files
        if [ "$dry_run" = "true" ]; then
            print_warning "Dry run mode, not deleting any files"
            for ((i=0; i<delete_count; i++)); do
                echo "Would delete: ${sorted_logs[$i]}"
                echo "Would delete: ${sorted_logs[$i]}.errors (if exists)"
            done
        else
            for ((i=0; i<delete_count; i++)); do
                rm -f "${sorted_logs[$i]}"
                rm -f "${sorted_logs[$i]}.errors"
                echo "Deleted: ${sorted_logs[$i]}"
            done
            print_success "Removed $delete_count oldest log files"
        fi
    fi
    
    return 0
}

# Function to classify errors by severity with enhanced context extraction
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
    if grep -q -E "${ERROR_PATTERNS["critical"]}" "$log_file"; then
        # Get critical errors with line numbers
        local critical_lines=$(grep -n -E "${ERROR_PATTERNS["critical"]}" "$log_file" | cut -d':' -f1 | head -20)
        critical_count=$(echo "$critical_lines" | wc -l)
        
        # Process each critical error line to extract meaningful context
        while IFS= read -r line_num; do
            if [ -n "$line_num" ]; then
                # Get 2 lines before and 4 lines after the error for context
                local context_start=$((line_num > 2 ? line_num - 2 : 1))
                local context_end=$((line_num + 4))
                local context_lines=$((context_end - context_start + 1))
                
                # Extract the error line itself
                local error_line=$(sed "${line_num}q;d" "$log_file")
                
                # Extract stack trace if it exists (common patterns in various languages)
                local has_stack_trace=false
                if grep -A 10 -E "(Traceback|Stack trace|Call stack|at .*\(.*:[0-9]+\)|File \".*\", line [0-9]+)" "$log_file" | grep -q -A 5 -B 5 -E "^$line_num:"; then
                    has_stack_trace=true
                fi
                
                # Print the error line with context
                echo -e "\033[1;31m>>> Critical error at line $line_num:\033[0m" >> "$output_file"
                echo "$(sed -n "${context_start},${context_end}p" "$log_file" | sed "${line_num}s/^/\033[1;31m→ /" | sed "${line_num}s/$/\033[0m/")" >> "$output_file"
                
                # If there's a stack trace, try to extract it intelligently
                if [ "$has_stack_trace" = true ]; then
                    echo -e "\n\033[1;31m>>> Stack trace:\033[0m" >> "$output_file"
                    # Look for stack trace patterns after the error line and extract a reasonable portion
                    grep -A 15 -E "(Traceback|Stack trace|Call stack|at .*\(.*:[0-9]+\)|File \".*\", line [0-9]+)" "$log_file" | \
                    grep -A 15 -B 1 -E "^$line_num:" | head -15 >> "$output_file"
                fi
                
                echo "───────────────────────────────────────────────────────────────" >> "$output_file"
            fi
        done <<< "$critical_lines"
    else
        echo "None found" >> "$output_file"
    fi
    
    echo "" >> "$output_file"
    
    # Check for severe errors (excluding those already identified as critical)
    print_severe "SEVERE ERRORS:" >> "$output_file"
    echo "───────────────────────────────────────────────────────────────" >> "$output_file"
    
    if grep -q -E "${ERROR_PATTERNS["severe"]}" "$log_file" && ! grep -q -E "${ERROR_PATTERNS["critical"]}" "$log_file"; then
        # Get severe errors with line numbers, excluding critical patterns
        local severe_lines=$(grep -n -E "${ERROR_PATTERNS["severe"]}" "$log_file" | grep -v -E "${ERROR_PATTERNS["critical"]}" | cut -d':' -f1 | head -15)
        severe_count=$(echo "$severe_lines" | wc -l)
        
        # Process each severe error line
        while IFS= read -r line_num; do
            if [ -n "$line_num" ]; then
                # Get 1 line before and 3 lines after the error for context
                local context_start=$((line_num > 1 ? line_num - 1 : 1))
                local context_end=$((line_num + 3))
                
                # Extract the error line itself
                local error_line=$(sed "${line_num}q;d" "$log_file")
                
                # Print the error line with context
                echo -e "\033[1;35m>>> Severe error at line $line_num:\033[0m" >> "$output_file"
                echo "$(sed -n "${context_start},${context_end}p" "$log_file" | sed "${line_num}s/^/\033[1;35m→ /" | sed "${line_num}s/$/\033[0m/")" >> "$output_file"
                echo "───────────────────────────────────────────────────────────────" >> "$output_file"
            fi
        done <<< "$severe_lines"
    else
        echo "None found" >> "$output_file"
    fi
    
    echo "" >> "$output_file"
    
    # Check for warnings (excluding those already identified as critical or severe)
    print_warning "WARNINGS:" >> "$output_file"
    echo "───────────────────────────────────────────────────────────────" >> "$output_file"
    
    if grep -q -E "${ERROR_PATTERNS["warning"]}" "$log_file" && ! grep -q -E "${ERROR_PATTERNS["critical"]}|${ERROR_PATTERNS["severe"]}" "$log_file"; then
        # Get warnings with line numbers, excluding critical and severe patterns
        local warning_lines=$(grep -n -E "${ERROR_PATTERNS["warning"]}" "$log_file" | grep -v -E "${ERROR_PATTERNS["critical"]}|${ERROR_PATTERNS["severe"]}" | cut -d':' -f1 | head -10)
        warning_count=$(echo "$warning_lines" | wc -l)
        
        # Process each warning line
        while IFS= read -r line_num; do
            if [ -n "$line_num" ]; then
                # Get just the warning line itself with minimal context
                echo -e "\033[1;33m>>> Warning at line $line_num:\033[0m" >> "$output_file"
                echo "$(sed "${line_num}s/^/\033[1;33m→ /" "$log_file" | sed "${line_num}s/$/\033[0m/" | sed -n "${line_num}p")" >> "$output_file"
            fi
        done <<< "$warning_lines"
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
    
    return 0
}

# Function to check for saved logs after a given date
find_local_logs_after_last_commit() {
    local workflow_name="$1"  # Optional workflow name filter
    local target_count="${2:-1}"  # Number of logs to return (default 1)
    
    # Get the date of the last commit
    local last_commit_date
    last_commit_date=$(git log -1 --format="%cd" --date=format:"%Y%m%d-%H%M%S" 2>/dev/null)
    
    if [ -z "$last_commit_date" ]; then
        print_warning "Could not determine last commit date, using all logs"
        # List all log files
        find logs -name "workflow_*.log" -not -name "*.errors" | sort -n
        return
    fi
    
    print_info "Finding logs created after last commit ($last_commit_date)"
    
    # Find all log files matching the workflow name if specified
    local all_logs=()
    
    if [ -n "$workflow_name" ]; then
        # Find logs that might contain the specified workflow name
        for log_file in logs/workflow_*.log; do
            if [ -f "$log_file" ] && ! [[ "$log_file" == *".errors" ]]; then
                # Check if the log file contains the workflow name (case insensitive)
                if grep -q -i "$workflow_name" "$log_file" 2>/dev/null; then
                    all_logs+=("$log_file")
                fi
            fi
        done
    else
        # No workflow name specified, get all logs
        for log_file in logs/workflow_*.log; do
            if [ -f "$log_file" ] && ! [[ "$log_file" == *".errors" ]]; then
                all_logs+=("$log_file")
            fi
        done
    fi
    
    # Sort logs by timestamp in filename
    mapfile -t sorted_logs < <(printf '%s\n' "${all_logs[@]}" | sort -n)
    
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
    
    # Setup grep options
    local grep_opts="-n"
    if [ "$case_sensitive" = "false" ]; then
        grep_opts="$grep_opts -i"
    fi
    
    # Get all log files
    local all_logs=()
    for log_file in logs/workflow_*.log; do
        if [ -f "$log_file" ] && ! [[ "$log_file" == *".errors" ]]; then
            all_logs+=("$log_file")
        fi
    done
    
    # Sort by timestamp, newest first
    mapfile -t sorted_logs < <(printf '%s\n' "${all_logs[@]}" | sort -r)
    
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
        if [ -f "$log_file" ] && ! [[ "$log_file" == *".errors" ]]; then
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
            local file_size=$(stat -c %s "$log_file" 2>/dev/null || stat -f %z "$log_file" 2>/dev/null)
            total_size=$((total_size + file_size))
        fi
    done
    
    # Calculate size in MB
    local size_mb=$(echo "scale=2; $total_size / 1048576" | bc)
    
    # Determine if there are logs after last commit
    local logs_after_commit=0
    readarray -t recent_logs < <(find_local_logs_after_last_commit "" 50)
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
            if [ -f "$log_file" ] && ! [[ "$log_file" == *".errors" ]]; then
                recent_logs+=("$log_file")
            fi
        done
        
        # Sort by timestamp, newest first
        mapfile -t sorted_logs < <(printf '%s\n' "${recent_logs[@]}" | sort -r)
        
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
            
            echo "$status $workflow_type ($timestamp) - Run ID: $run_id - $log_file"
        done
        echo "───────────────────────────────────────────────────────────────"
    fi
    
    return 0
}

# Initialize script environment
initialize_script() {
    print_header "CLAUDE HELPER SCRIPT: GitHub Actions Workflow Logs Tool v$SCRIPT_VERSION"
    
    # Make logs directory if it doesn't exist
    mkdir -p logs
    
    # Detect repository information
    detect_repository_info
    
    # Detect available workflows
    detect_workflows
    
    # Check for required commands
    if ! command -v gh &>/dev/null; then
        print_warning "GitHub CLI (gh) is not installed. Some features will be limited."
        print_info "Install GitHub CLI from: https://cli.github.com"
    elif ! gh auth status &>/dev/null; then
        print_warning "Not authenticated with GitHub CLI. Some features will be limited."
        print_info "Run 'gh auth login' to authenticate."
    fi
    
    # Check for jq command
    if ! command -v jq &>/dev/null; then
        print_warning "jq is not installed. Some features may be limited."
        print_info "Install jq from: https://stedolan.github.io/jq/"
    fi
    
    print_info "Repository: $REPO_FULL_NAME"
    print_info "Detected workflows: ${AVAILABLE_WORKFLOWS[*]}"
}

# Main execution
# First check for help flags which don't need initialization
if [[ "$1" == "help" || "$1" == "--help" || "$1" == "-h" ]]; then
    show_help="true"
else
    # Initialize the script environment
    initialize_script
    show_help="false"
fi

# Process command
case "$1" in
    version|--version|-v)
        print_header "CLAUDE HELPER SCRIPT: GitHub Actions Workflow Logs Tool v$SCRIPT_VERSION"
        echo "Repository: $REPO_FULL_NAME"
        echo "Detected workflows: ${AVAILABLE_WORKFLOWS[*]}"
        echo "Configured settings:"
        echo "  - Max logs per workflow: $MAX_LOGS_PER_WORKFLOW"
        echo "  - Max log age (days): $MAX_LOG_AGE_DAYS"
        echo "  - Max total logs: $MAX_TOTAL_LOGS"
        echo "  - Default output lines: $DEFAULT_OUTPUT_LINES"
        echo "  - Truncation: $([ "$DO_TRUNCATE" = "true" ] && echo "Enabled" || echo "Disabled")"
        ;;
    list)
        get_workflow_runs
        ;;
    logs)
        get_workflow_logs "$2"
        ;;
    saved)
        # List saved logs
        print_header "Listing saved workflow logs"
        found_logs=0
        for log_file in logs/workflow_*.log; do
            if [ -f "$log_file" ] && ! [[ "$log_file" == *".errors" ]]; then
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
        ;;
    search)
        # Search across all log files
        if [ -z "$2" ]; then
            print_error "Search pattern is required"
            print_info "Usage: $0 search PATTERN [CASE_SENSITIVE] [MAX_RESULTS]"
            exit 1
        fi
        search_logs "$2" "${3:-false}" "${4:-50}"
        ;;
    stats)
        # Generate statistics
        generate_stats
        ;;
    cleanup)
        # Perform log cleanup
        max_age="${2:-$MAX_LOG_AGE_DAYS}"
        if [[ "$3" == "--dry-run" || "$2" == "--dry-run" ]]; then
            cleanup_old_logs "$max_age" "true"
        else
            cleanup_old_logs "$max_age" "false"
        fi
        ;;
    workflow|workflows)
        # Show detected workflows
        print_header "Detected GitHub Workflows"
        echo ""
        print_info "The following workflows were detected for $REPO_FULL_NAME:"
        echo ""
        
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
        echo ""
        ;;
        
    detect)
        # Just detect repository and workflow information without fetching logs
        print_header "CLAUDE HELPER SCRIPT: Repository and Workflow Detection"
        echo ""
        
        print_header "Repository Information"
        # Detect repository information
        detect_repository_info
        echo ""
        
        print_header "Available Workflows"
        # Detect workflows
        detect_workflows
        echo ""
        
        # Show configuration
        print_header "Configuration Summary"
        echo "Script version: $SCRIPT_VERSION"
        echo "Working directory: $(pwd)"
        echo "Repository: $REPO_FULL_NAME"
        echo "Owner: $REPO_OWNER"
        echo "Name: $REPO_NAME"
        echo "Total workflows detected: ${#AVAILABLE_WORKFLOWS[@]}"
        echo "Test workflows: ${#TEST_WORKFLOWS[@]}"
        echo "Release workflows: ${#RELEASE_WORKFLOWS[@]}"
        echo "Lint workflows: ${#LINT_WORKFLOWS[@]}"
        echo "Documentation workflows: ${#DOCS_WORKFLOWS[@]}"
        echo "Other workflows: ${#OTHER_WORKFLOWS[@]}"
        echo ""
        
        print_success "Successfully detected repository and workflow information"
        echo ""
        ;;
        
    classify)
        # Classify errors in a specific log file
        if [ -n "$2" ] && [ -f "$2" ]; then
            log_file="$2"
            classified_file="${log_file}.classified"
            
            print_header "Classifying Errors in Log File: $log_file"
            echo ""
            
            print_info "Analyzing log file and extracting errors by severity..."
            classify_errors "$log_file" "$classified_file"
            
            print_success "Classification completed. Results saved to: $classified_file"
            echo ""
            
            print_important "CLASSIFIED ERROR SUMMARY:"
            cat "$classified_file"
            
        else
            print_error "Please provide a valid log file to classify."
            print_info "Usage: $0 classify <log_file>"
            print_info "Example: $0 classify logs/workflow_12345678.log"
            exit 1
        fi
        ;;
    lint)
        # Get logs for lint workflows
        if [ ${#LINT_WORKFLOWS[@]} -gt 0 ]; then
            lint_workflow="${LINT_WORKFLOWS[0]}"
            print_info "Found lint workflow: $lint_workflow"
            
            # First check for saved lint logs
            print_info "Looking for saved logs for workflow: $lint_workflow"
            readarray -t saved_lint_logs < <(find_local_logs_after_last_commit "$lint_workflow" 1)
            
            if [ ${#saved_lint_logs[@]} -gt 0 ]; then
                log_file="${saved_lint_logs[0]}"
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
                    
                    if [ "$DO_TRUNCATE" = "true" ]; then
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
                    grep -n -B 5 -A 10 -E "${ERROR_PATTERNS["critical"]}" "$log_file" > "$error_file" 2>/dev/null || true
                    grep -n -B 3 -A 8 -E "${ERROR_PATTERNS["severe"]}" "$log_file" | grep -v -E "${ERROR_PATTERNS["critical"]}" >> "$error_file" 2>/dev/null || true
                    
                    if [ -s "$error_file" ]; then
                        if [ "$DO_TRUNCATE" = "true" ]; then
                            # Truncated display
                            head -n $DEFAULT_OUTPUT_LINES "$error_file"
                            echo "..."
                        else
                            # Full display
                            cat "$error_file"
                        fi
                    else
                        print_info "No clear errors detected in $log_file"
                    fi
                fi
            else
                # If no saved logs, try to fetch from GitHub
                print_info "No saved logs found for '$lint_workflow'. Fetching from GitHub..."
                lint_run_id=$(get_latest_workflow_run "$lint_workflow")
                if [ -n "$lint_run_id" ]; then
                    get_workflow_logs "$lint_run_id"
                else
                    print_warning "No workflow runs found for '$lint_workflow'."
                    print_info "Use 'list' to see available workflow runs."
                fi
            fi
        else
            print_warning "No lint workflows detected in this repository."
            print_info "Use 'workflows' to see available workflow types."
        fi
        ;;
    docs)
        # Get logs for documentation workflows
        if [ ${#DOCS_WORKFLOWS[@]} -gt 0 ]; then
            docs_workflow="${DOCS_WORKFLOWS[0]}"
            print_info "Found documentation workflow: $docs_workflow"
            
            # First check for saved docs logs
            print_info "Looking for saved logs for workflow: $docs_workflow"
            readarray -t saved_docs_logs < <(find_local_logs_after_last_commit "$docs_workflow" 1)
            
            if [ ${#saved_docs_logs[@]} -gt 0 ]; then
                log_file="${saved_docs_logs[0]}"
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
                    
                    if [ "$DO_TRUNCATE" = "true" ]; then
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
                    grep -n -B 5 -A 10 -E "${ERROR_PATTERNS["critical"]}" "$log_file" > "$error_file" 2>/dev/null || true
                    grep -n -B 3 -A 8 -E "${ERROR_PATTERNS["severe"]}" "$log_file" | grep -v -E "${ERROR_PATTERNS["critical"]}" >> "$error_file" 2>/dev/null || true
                    
                    if [ -s "$error_file" ]; then
                        if [ "$DO_TRUNCATE" = "true" ]; then
                            # Truncated display
                            head -n $DEFAULT_OUTPUT_LINES "$error_file"
                            echo "..."
                        else
                            # Full display
                            cat "$error_file"
                        fi
                    else
                        print_info "No clear errors detected in $log_file"
                    fi
                fi
            else
                # If no saved logs, try to fetch from GitHub
                print_info "No saved logs found for '$docs_workflow'. Fetching from GitHub..."
                docs_run_id=$(get_latest_workflow_run "$docs_workflow")
                if [ -n "$docs_run_id" ]; then
                    get_workflow_logs "$docs_run_id"
                else
                    print_warning "No workflow runs found for '$docs_workflow'."
                    print_info "Use 'list' to see available workflow runs."
                fi
            fi
        else
            print_warning "No documentation workflows detected in this repository."
            print_info "Use 'workflows' to see available workflow types."
        fi
        ;;
    test|tests)
        # Get logs for detected test workflow
        if [ ${#TEST_WORKFLOWS[@]} -gt 0 ]; then
            test_workflow="${TEST_WORKFLOWS[0]}"
            print_info "Found test workflow: $test_workflow"
        else
            # Fallback to old detection method
            test_workflow=""
            for workflow in "${AVAILABLE_WORKFLOWS[@]}"; do
                if [[ "$workflow" == *"[tT]est"* || "$workflow" == *"Tests"* ]]; then
                    test_workflow="$workflow"
                    break
                fi
            done
        fi
        
        if [ -z "$test_workflow" ]; then
            # No test workflow found, use first workflow
            if [ ${#AVAILABLE_WORKFLOWS[@]} -gt 0 ]; then
                test_workflow="${AVAILABLE_WORKFLOWS[0]}"
                print_warning "No specific test workflow found. Using: $test_workflow"
            else
                # Fallback to default
                test_workflow="Tests"
                print_warning "No workflows detected. Using default: $test_workflow"
            fi
        else
            print_info "Found test workflow: $test_workflow"
        fi
        
        # First check for saved test logs
        print_info "Looking for saved logs for workflow: $test_workflow"
        readarray -t saved_test_logs < <(find_local_logs_after_last_commit "$test_workflow" 1)
        
        if [ ${#saved_test_logs[@]} -gt 0 ]; then
            log_file="${saved_test_logs[0]}"
            run_id=$(basename "$log_file" | cut -d '_' -f 2)
            print_success "Using saved log file: $log_file (Run ID: $run_id)"
            
            # Process the saved log
            error_file="${log_file}.errors"
            classified_file="${log_file}.classified"
            error_summary_file="${log_file}.summary"
            
            # If we don't have the error files, create them
            if [ ! -f "$error_file" ] || [ ! -f "$classified_file" ]; then
                print_info "Analyzing log file..."
                # First, run the classification
                classify_errors "$log_file" "$classified_file"
                
                # Extract errors with context
                grep -n -A 10 -B 5 -E "${ERROR_PATTERNS["critical"]}" "$log_file" > "$error_file" 2>/dev/null || true
                grep -n -A 8 -B 3 -E "${ERROR_PATTERNS["severe"]}" "$log_file" | grep -v -E "${ERROR_PATTERNS["critical"]}" >> "$error_file" 2>/dev/null || true
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
                
                if [ "$DO_TRUNCATE" = "true" ]; then
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
                print_info "No clear errors detected in $log_file"
                
                # Show a sample of the log
                if [ "$DO_TRUNCATE" = "true" ]; then
                    echo "───────────────────────────────────────────────────────────────"
                    head -n 20 "$log_file"
                    echo "..."
                    echo "───────────────────────────────────────────────────────────────"
                fi
            fi
        else
            # If no saved logs, try to fetch from GitHub
            print_info "No saved logs found for '$test_workflow'. Fetching from GitHub..."
            test_run_id=$(get_latest_workflow_run "$test_workflow")
            if [ -n "$test_run_id" ]; then
                get_workflow_logs "$test_run_id"
            else
                print_warning "No workflow runs found for '$test_workflow'. Trying any workflow..."
                any_run_id=$(get_latest_workflow_run "")
                if [ -n "$any_run_id" ]; then
                    get_workflow_logs "$any_run_id"
                fi
            fi
        fi
        ;;
    build|release)
        # Get logs for detected build/release workflow
        if [ ${#RELEASE_WORKFLOWS[@]} -gt 0 ]; then
            build_workflow="${RELEASE_WORKFLOWS[0]}"
            print_info "Found release/build workflow: $build_workflow"
        else
            # Fallback to old detection method
            build_workflow=""
            for workflow in "${AVAILABLE_WORKFLOWS[@]}"; do
                if [[ "$workflow" == *"[rR]elease"* || "$workflow" == *"[bB]uild"* || "$workflow" == *"[pP]ublish"* ]]; then
                    build_workflow="$workflow"
                    break
                fi
            done
        fi
        
        if [ -z "$build_workflow" ]; then
            # No build workflow found, use second workflow or first if only one
            if [ ${#AVAILABLE_WORKFLOWS[@]} -gt 1 ]; then
                build_workflow="${AVAILABLE_WORKFLOWS[1]}"
                print_warning "No specific build/release workflow found. Using: $build_workflow"
            elif [ ${#AVAILABLE_WORKFLOWS[@]} -eq 1 ]; then
                build_workflow="${AVAILABLE_WORKFLOWS[0]}"
                print_warning "No specific build/release workflow found. Using: $build_workflow"
            else
                # Fallback to default
                build_workflow="Auto Release"
                print_warning "No workflows detected. Using default: $build_workflow"
            fi
        else
            print_info "Found build/release workflow: $build_workflow"
        fi
        
        # First check for saved build logs
        print_info "Looking for saved logs for workflow: $build_workflow"
        readarray -t saved_build_logs < <(find_local_logs_after_last_commit "$build_workflow" 1)
        
        if [ ${#saved_build_logs[@]} -gt 0 ]; then
            log_file="${saved_build_logs[0]}"
            run_id=$(basename "$log_file" | cut -d '_' -f 2)
            print_success "Using saved log file: $log_file (Run ID: $run_id)"
            
            # Process the saved log
            error_file="${log_file}.errors"
            classified_file="${log_file}.classified"
            error_summary_file="${log_file}.summary"
            
            # If we don't have the error files, create them
            if [ ! -f "$error_file" ] || [ ! -f "$classified_file" ]; then
                print_info "Analyzing log file..."
                # First, run the classification
                classify_errors "$log_file" "$classified_file"
                
                # Extract errors with context
                grep -n -A 10 -B 5 -E "${ERROR_PATTERNS["critical"]}" "$log_file" > "$error_file" 2>/dev/null || true
                grep -n -A 8 -B 3 -E "${ERROR_PATTERNS["severe"]}" "$log_file" | grep -v -E "${ERROR_PATTERNS["critical"]}" >> "$error_file" 2>/dev/null || true
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
                
                if [ "$DO_TRUNCATE" = "true" ]; then
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
                print_info "No clear errors detected in $log_file"
                
                # Show a sample of the log
                if [ "$DO_TRUNCATE" = "true" ]; then
                    echo "───────────────────────────────────────────────────────────────"
                    head -n 20 "$log_file"
                    echo "..."
                    echo "───────────────────────────────────────────────────────────────"
                fi
            fi
        else
            # If no saved logs, try to fetch from GitHub
            print_info "No saved logs found for '$build_workflow'. Fetching from GitHub..."
            build_run_id=$(get_latest_workflow_run "$build_workflow")
            if [ -n "$build_run_id" ]; then
                get_workflow_logs "$build_run_id"
            else
                print_warning "No workflow runs found for '$build_workflow'. Trying any workflow..."
                any_run_id=$(get_latest_workflow_run "")
                if [ -n "$any_run_id" ]; then
                    get_workflow_logs "$any_run_id"
                fi
            fi
        fi
        ;;
    latest)
        # Get the 3 most recent logs after the last commit
        print_header "Finding the 3 most recent workflow logs"
        readarray -t recent_logs < <(find_local_logs_after_last_commit "" 3)
        
        if [ ${#recent_logs[@]} -gt 0 ]; then
            # Sort logs by the detected workflow type for better organization
            declare -A workflow_logs
            
            # Group logs by workflow type
            for log_file in "${recent_logs[@]}"; do
                # Determine workflow type
                workflow_type="Unknown"
                for workflow in "${AVAILABLE_WORKFLOWS[@]}"; do
                    if grep -q -i "$workflow" "$log_file" 2>/dev/null; then
                        workflow_type="$workflow"
                        break
                    fi
                done
                
                # Add to the appropriate group
                if [ -n "${workflow_logs[$workflow_type]}" ]; then
                    workflow_logs[$workflow_type]="${workflow_logs[$workflow_type]} $log_file"
                else
                    workflow_logs[$workflow_type]="$log_file"
                fi
            done
            
            # Process each workflow type
            for workflow_type in "${!workflow_logs[@]}"; do
                print_header "Logs for workflow: $workflow_type"
                
                # Process each log file for this workflow
                for log_file in ${workflow_logs[$workflow_type]}; do
                    run_id=$(basename "$log_file" | cut -d '_' -f 2)
                    timestamp=$(basename "$log_file" | cut -d '_' -f 3 | cut -d '.' -f 1)
                    print_success "Log file: $log_file (Run ID: $run_id, Timestamp: $timestamp)"
                    
                    # Process the saved log
                    error_file="${log_file}.errors"
                    classified_file="${log_file}.classified"
                    
                    # If we don't have the error files, create them
                    if [ ! -f "$classified_file" ]; then
                        print_info "Analyzing log file..."
                        # Run the classification
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
            done
        else
            print_error "No saved log files found after the last commit."
            print_info "Trying to fetch logs from GitHub instead..."
            
            # Fall back to fetching from GitHub
            get_workflow_runs
            
            # Try to get logs for each detected workflow
            for workflow in "${AVAILABLE_WORKFLOWS[@]}"; do
                print_header "Fetching logs for workflow: $workflow"
                workflow_run_id=$(get_latest_workflow_run "$workflow")
                if [ -n "$workflow_run_id" ]; then
                    get_workflow_logs "$workflow_run_id"
                else
                    print_warning "No logs found for workflow: $workflow"
                fi
            done
            
            # If no specific workflow logs found, try any workflow
            if [ "${#AVAILABLE_WORKFLOWS[@]}" -eq 0 ]; then
                print_header "Fetching logs from any available workflow run"
                any_run_id=$(get_latest_workflow_run "")
                if [ -n "$any_run_id" ]; then
                    get_workflow_logs "$any_run_id"
                else
                    print_error "Could not find any workflow runs with available logs."
                    print_info "Try running '$0 list' to see available workflow runs."
                fi
            fi
        fi
        ;;
        
    help|--help|-h)
        # Show help
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
        echo "  detect                    Detect repository info and workflows without fetching logs"
        echo "  version|--version|-v      Show script version and configuration"
        echo "  help|--help|-h            Show this help message"
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
        echo "  $0 detect                 Detect repository info and available workflows"
        echo "  $0 --truncate latest      Get the 3 most recent logs with truncated output"
        echo "  $0 search \"error\"       Search all logs for 'error' (case insensitive)"
        echo "  $0 search \"Exception\" true  Search logs for 'Exception' (case sensitive)"
        echo "  $0 cleanup 10             Delete logs older than 10 days"
        echo "  $0 cleanup --dry-run      Show what logs would be deleted without deleting"
        echo "  $0 classify logs/workflow_12345.log  Classify errors in a specific log file"
        echo ""
        ;;
    *)
        # Handle action based on what we have available
        if [ -d "logs" ] && [ "$(find logs -name "workflow_*.log" | wc -l)" -gt 0 ]; then
            # We have saved logs, show the latest ones
            print_info "No command specified. Showing the latest logs..."
            "$0" latest
        else
            # No saved logs available, run list first
            print_info "No saved logs found. Showing available workflow runs..."
            get_workflow_runs
            
            # Also show available commands
            print_header "Available Commands"
            echo "Try one of these commands:"
            echo "  $0 logs <RUN_ID>      - Get logs for a specific workflow run"
            echo "  $0 tests              - Get logs for the latest test workflow run"
            echo "  $0 help               - Show all available commands"
        fi
        ;;
esac

exit 0