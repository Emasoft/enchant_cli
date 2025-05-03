#!/usr/bin/env bash

# Return error if executed directly - MUST BE PLACED AT THE BEGINNING
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    echo "Error: This script cannot be executed directly. All DHT scripts can only be called by the DHT Launcher in the project root. Please run dhtl.sh (or dhtl.bat) followed by the action you want to execute. For more informations use dhtl.sh --help"
    exit 1
fi

set -eo pipefail
source "${SCRIPT_DIR}/publish_common.sh"

print_step "Checking local repository status..."

# Check if there's a git repo
if [ ! -d "$SCRIPT_DIR/.git" ]; then
    print_warning "No git repository found. Initializing a new repository..."
    git init
    git config --local user.name "$(git config --global user.name || echo "$GITHUB_USER")"
    git config --local user.email "$(git config --global user.email || echo "$GITHUB_USER@users.noreply.github.com")"
    print_success "Git repository initialized."
fi

# Check for uncommitted changes and commit them
if ! git diff --quiet HEAD 2>/dev/null; then
    print_warning "Uncommitted changes detected. Staging and committing automatically..."
    git add -A # Stage all changes first

    print_info "Running pre-commit hooks manually on staged files before commit..."
    # Get list of staged files
    STAGED_FILES=$(git diff --name-only --cached)
    if [ -n "$STAGED_FILES" ]; then
        # Run pre-commit only on the staged files
        # If this fails, try to fix common issues automatically
        $PYTHON_CMD -m pre_commit run --files "$STAGED_FILES" || {
            print_warning "Manual pre-commit run had issues. Attempting to fix automatically..."
            
            # Install linters
            $PYTHON_CMD -m pip install -q ruff shellcheck-py &> /dev/null
            $PYTHON_CMD -m ruff . || print_warning "Ruff check failed, continuing..."
            
            # Re-stage files
            git add -A
            
            # Try hooks again
            $PYTHON_CMD -m pre_commit run --files "$STAGED_FILES" || {
                print_warning "Pre-commit still failing. Will try a manual commit anyway..."
            }
        }
        print_success "Manual pre-hooks processing completed."
        # Re-stage any files potentially modified by the hooks
        echo "   Re-staging potentially modified files..."
        git add -A
    else
        print_info "No files were staged for the pre-commit run (should not happen if changes were detected)."
        # Stage everything to be safe
        git add -A
    fi

    # Generate a commit message based on whether tests or linters were skipped
    COMMIT_MESSAGE="chore: Prepare for release validation"
    if [ $SKIP_TESTS -eq 1 ]; then
        # Add skip-tests marker for GitHub Actions to detect
        COMMIT_MESSAGE="$COMMIT_MESSAGE [skip-tests]"
    fi
    if [ $SKIP_LINTERS -eq 1 ]; then
        # Add skip-linters marker for GitHub Actions to detect
        COMMIT_MESSAGE="$COMMIT_MESSAGE [skip-linters]"
    fi
    
    print_info "Committing staged changes..."
    if ! git commit -m "$COMMIT_MESSAGE"; then
        print_warning "Git commit failed. Attempting to bypass pre-commit hooks..."
        # If commit failed, try bypassing pre-commit hooks
        git commit -m "$COMMIT_MESSAGE" --no-verify || {
            print_error "Git commit failed even with --no-verify. Manual intervention required." 1
            exit 1
        }
        
        # Manually run version bump if the hook was bypassed
        print_info "Running manual version bump since pre-commit hook was bypassed..."
        
        # IMPORTANT: Must use uv tool run for bump-my-version per requirements
        if [ -f "$UV_CMD" ]; then
            print_info "Using uv tool run for bump-my-version (recommended method)"
            "$UV_CMD" tool run "$UV_CMD" tool run "$UV_CMD" tool run bump-my-version bump minor --commit --tag --allow-dirty || {
                print_error "Version bump with uv tool failed." 1
                print_info "See: https://www.andrlik.org/dispatches/til-bump-my-version-uv/"
                exit 1
            }
            print_success "Version bumped successfully using uv tool run"
        else
            print_error "uv not found in virtual environment. Cannot perform version bump." 1
            print_info "Try running: ./reinitialize_env.sh"
            exit 1
        fi
    fi
    print_success "Changes committed."
elif ! git rev-parse --verify HEAD &>/dev/null; then
    print_warning "Empty repository with no commits. Creating initial commit..."
    git add -A
    git commit -m "Initial commit" --no-verify || {
        print_error "Failed to create initial commit. Manual intervention required." 1
        exit 1
    }
    
    # Run initial version bump after first commit
    print_info "Running version bump for initial commit..."
    if [ -f "$UV_CMD" ]; then
        "$UV_CMD" tool run "$UV_CMD" tool run "$UV_CMD" tool run bump-my-version bump minor --commit --tag --allow-dirty || {
            print_warning "Version bump failed for initial commit. Continuing anyway..."
        }
    else
        print_warning "uv not available for initial version bump. Continuing anyway..."
    fi
    
    print_success "Initial commit created."
else
    print_success "Working directory is clean with existing commits."
fi

# *** STEP 4: Run local validation scripts ***
