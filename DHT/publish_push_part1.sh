#!/usr/bin/env bash

# Return error if executed directly - MUST BE PLACED AT THE BEGINNING
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    echo "Error: This script cannot be executed directly. All DHT scripts can only be called by the DHT Launcher in the project root. Please run dhtl.sh (or dhtl.bat) followed by the action you want to execute. For more informations use dhtl.sh --help"
    exit 1
fi

set -eo pipefail
source "${SCRIPT_DIR}/publish_common.sh"

print_step "Pushing to GitHub repository..."

# Determine current branch
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "$DEFAULT_BRANCH")
print_info "Current branch: $CURRENT_BRANCH"

if [ -z "$(git branch --list "$CURRENT_BRANCH")" ]; then
    print_warning "Branch $CURRENT_BRANCH does not exist locally. Creating it..."
    git checkout -b "$CURRENT_BRANCH" || {
        print_error "Failed to create branch $CURRENT_BRANCH." 1
            exit 1
    }
    print_success "Branch $CURRENT_BRANCH created."
elif [ "$CURRENT_BRANCH" = "HEAD" ]; then
    print_warning "Detached HEAD state detected. Creating and checking out $DEFAULT_BRANCH branch..."
    git checkout -b "$DEFAULT_BRANCH" || {
        print_error "Failed to create branch $DEFAULT_BRANCH." 1
            exit 1
    }
    CURRENT_BRANCH="$DEFAULT_BRANCH"
    print_success "Branch $DEFAULT_BRANCH created and checked out."
fi

# Check if the branch exists on remote
BRANCH_EXISTS_ON_REMOTE=0
if git ls-remote --exit-code --heads origin "$CURRENT_BRANCH" &>/dev/null; then
    BRANCH_EXISTS_ON_REMOTE=1
    print_info "Branch $CURRENT_BRANCH exists on remote."
else
    print_info "Branch $CURRENT_BRANCH does not exist on remote yet."
fi

# Push to GitHub with appropriate flags
print_info "Pushing latest commit and tags to GitHub..."
if [ $BRANCH_EXISTS_ON_REMOTE -eq 1 ]; then
    # Branch exists, perform standard push
    git push origin "$CURRENT_BRANCH" --tags || { 
        print_error "git push failed. Attempting to diagnose..."
        git remote -v
        print_info "Checking remote connectivity..."
        git ls-remote --exit-code origin &>/dev/null || print_error "Cannot connect to remote 'origin'."
        print_info "Please check remote, branch name, permissions, and conflicts."
        
        # Offer to force push if needed
        read -p "Do you want to try force pushing? This may overwrite remote changes. (y/N) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            print_warning "Attempting force push..."
            git push --force origin "$CURRENT_BRANCH" --tags || {
                print_error "Force push failed. Manual intervention required." 1
            exit 1
            }
            print_success "Force push successful."
        else
            print_info "Force push declined. Exiting."
            exit 1
        fi
    }
else
    # First push, set upstream
    git push -u origin "$CURRENT_BRANCH" --tags || {
        print_error "Initial push failed. Attempting to diagnose..."
        git remote -v
        print_info "Checking remote connectivity..."
        git ls-remote --exit-code origin &>/dev/null || print_error "Cannot connect to remote 'origin'."
        print_info "Please check remote, branch name, and permissions."
        exit 1
    }
fi

print_success "Push to GitHub successful."

# Give GitHub systems time to process workflow file changes
print_info "Waiting 120 seconds for GitHub to process workflow file changes..."
print_info "This delay is necessary for GitHub to update its internal configurations after workflow file changes."
print_info "Without this delay, workflow_dispatch events may fail with 'Workflow does not have workflow_dispatch trigger' errors."
sleep 120

# *** STEP 8: Trigger GitHub Workflows ***
# CRITICAL: Always trigger workflows even if there were no changes
print_header "Ensuring GitHub workflows are ALWAYS triggered"
print_info "This step is MANDATORY - workflows MUST run even if no changes were committed or pushed!"

# Check if get_errorlogs.sh exists and is executable (needed for --wait-for-logs option)
if [ $WAIT_FOR_LOGS -eq 1 ]; then
    if [ ! -f "$SCRIPT_DIR/get_errorlogs.sh" ]; then
        print_warning "get_errorlogs.sh not found. Cannot wait for workflow logs."
        WAIT_FOR_LOGS=0
    elif [ ! -x "$SCRIPT_DIR/get_errorlogs.sh" ]; then
        print_warning "get_errorlogs.sh not executable. Setting permissions..."
        chmod +x "$SCRIPT_DIR/get_errorlogs.sh" || {
            print_warning "Failed to set permissions on get_errorlogs.sh. Cannot wait for workflow logs."
            WAIT_FOR_LOGS=0
        }
    else
        print_info "get_errorlogs.sh found and executable. Will wait for workflow logs after pushing."
    fi
fi
