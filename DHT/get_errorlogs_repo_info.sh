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
