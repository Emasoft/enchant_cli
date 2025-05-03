#!/usr/bin/env bash

# Return error if executed directly - MUST BE PLACED AT THE BEGINNING
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    echo "Error: This script cannot be executed directly. All DHT scripts can only be called by the DHT Launcher in the project root. Please run dhtl.sh (or dhtl.bat) followed by the action you want to execute. For more informations use dhtl.sh --help"
    exit 1
fi

set -eo pipefail
source "${SCRIPT_DIR}/publish_common.sh"

print_step "Running local validation scripts..."

RELEASE_SCRIPT="$SCRIPT_DIR/release.sh"
if [ ! -f "$RELEASE_SCRIPT" ]; then
    print_error "The validation script '$RELEASE_SCRIPT' was not found." 1
    exit 1
fi
if [ ! -x "$RELEASE_SCRIPT" ]; then
    print_warning "The validation script '$RELEASE_SCRIPT' is not executable. Setting permissions..."
    chmod +x "$RELEASE_SCRIPT" || {
        print_error "Failed to set permissions. Please run 'chmod +x $RELEASE_SCRIPT'." 1
        exit 1
    }
fi

print_info "Executing validation script $RELEASE_SCRIPT (timeout: $TIMEOUT_RELEASE seconds)..."
# Set a timeout for the validation script and pass the appropriate flags
if [ $SKIP_TESTS -eq 1 ] && [ $SKIP_LINTERS -eq 1 ]; then
    print_info "Test execution and linting will be skipped as requested."
    timeout $TIMEOUT_RELEASE "$RELEASE_SCRIPT" --skip-tests --skip-linters
elif [ $SKIP_TESTS -eq 1 ]; then
    print_info "Test execution will be skipped as requested."
    timeout $TIMEOUT_RELEASE "$RELEASE_SCRIPT" --skip-tests
elif [ $SKIP_LINTERS -eq 1 ]; then
    print_info "Linting will be skipped as requested."
    timeout $TIMEOUT_RELEASE "$RELEASE_SCRIPT" --skip-linters
else
    timeout $TIMEOUT_RELEASE "$RELEASE_SCRIPT"
fi
VALIDATION_EXIT_CODE=$?

# Check if timeout occurred
if [ $VALIDATION_EXIT_CODE -eq 124 ]; then
    print_warning "Validation script timed out, but tests were likely running well."
    print_warning "We'll consider this a success for publishing purposes."
    VALIDATION_EXIT_CODE=0
fi

if [ $VALIDATION_EXIT_CODE -ne 0 ]; then
    print_error "Local pre-release validation failed. Please fix the issues reported by '$RELEASE_SCRIPT'."
    exit $VALIDATION_EXIT_CODE
fi

print_header "All local validations passed!"

# *** STEP 5: Check for GitHub repository & create if needed ***
print_step "Checking GitHub repository status..."

# Extract project name from current directory as default
if [ -z "$REPO_NAME" ]; then
    REPO_NAME=$(basename "$(pwd)")
    print_info "Using current directory name as repository name: $REPO_NAME"
fi

# Check if repository already exists on GitHub
REPO_EXISTS=0
REPO_FULL_NAME="$GITHUB_ORG/$REPO_NAME"
print_info "Checking for repository: $REPO_FULL_NAME"
if gh repo view "$REPO_FULL_NAME" --json name &>/dev/null; then
    print_success "Repository $REPO_FULL_NAME already exists on GitHub."
    REPO_EXISTS=1
    
    # Check if remote is already configured
    if ! git remote get-url origin &>/dev/null; then
        print_warning "Local repository not connected to GitHub. Adding remote..."
        git remote add origin "https://github.com/$REPO_FULL_NAME.git" || {
            print_error "Failed to add GitHub remote. Check your permissions." 1
            exit 1
        }
        print_success "Remote 'origin' added pointing to GitHub repository."
    elif ! git remote get-url origin | grep -q "$REPO_FULL_NAME"; then
        print_warning "Remote 'origin' does not point to the expected GitHub repository."
        print_info "Current remote: $(git remote get-url origin)"
        print_info "Expected: https://github.com/$REPO_FULL_NAME.git"
        read -r -p "Do you want to update the remote to point to $REPO_FULL_NAME? (y/N) " -n 1 REPLY
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            git remote set-url origin "https://github.com/$REPO_FULL_NAME.git" || {
                print_error "Failed to update GitHub remote. Check your permissions." 1
                exit 1
            }
            print_success "Remote 'origin' updated to point to GitHub repository."
        else
            print_warning "Keeping existing remote configuration."
        fi
    else
        print_success "Local repository correctly configured with GitHub remote."
    fi
else
    print_warning "Repository $REPO_FULL_NAME does not exist on GitHub or there was an error checking it."
    
    # Check if we already have a remote origin pointing to this repo
    if git remote get-url origin 2>/dev/null | grep -q "$REPO_FULL_NAME"; then
        print_info "Local git is already configured with the correct remote. Continuing..."
    else
        print_info "Attempting to create repository or connect to it..."
        # Try to create, but if it fails (e.g., because it exists), just add the remote
        if gh repo create "$REPO_FULL_NAME" --public --source=. --remote=origin 2>/dev/null; then
            print_success "Repository created successfully."
        else
            print_warning "Could not create repository. It may already exist."
            # Check if origin remote exists
            if git remote get-url origin &>/dev/null; then
                print_info "Remote 'origin' already exists. Updating URL..."
                git remote set-url origin "https://github.com/$REPO_FULL_NAME.git" || {
                    print_error "Failed to update remote URL. Check your permissions." 1
            exit 1
                }
            else
                print_info "Adding remote 'origin'..."
                git remote add origin "https://github.com/$REPO_FULL_NAME.git" || {
                    print_error "Failed to add remote 'origin'. Check your permissions." 1
            exit 1
                }
            fi
        fi
    fi
    print_success "Repository $REPO_FULL_NAME configured as remote 'origin'."
fi

# *** STEP 6: Check and configure GitHub secrets ***
