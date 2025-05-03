#!/usr/bin/env bash

# Return error if executed directly - MUST BE PLACED AT THE BEGINNING
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    echo "Error: This script cannot be executed directly. All DHT scripts can only be called by the DHT Launcher in the project root. Please run dhtl.sh (or dhtl.bat) followed by the action you want to execute. For more informations use dhtl.sh --help"
    exit 1
fi

set -eo pipefail
source "${SCRIPT_DIR}/publish_common.sh"

print_step "Verifying required environment variables and GitHub secrets..."

MISSING_VARS=0
SECRET_CONFIG_NEEDED=0

# Check environment variables
if [ -z "$OPENROUTER_API_KEY" ]; then
    print_warning "OPENROUTER_API_KEY is not set. This is required for testing."
    MISSING_VARS=1
else
    print_success "OPENROUTER_API_KEY is set locally."
fi

if [ -z "$CODECOV_API_TOKEN" ]; then
    print_warning "CODECOV_API_TOKEN is not set. Coverage reports may not upload."
else
    print_success "CODECOV_API_TOKEN is set locally."
fi

if [ -z "$PYPI_API_TOKEN" ]; then
    print_warning "PYPI_API_TOKEN is not set. Note that GitHub Actions will use OIDC for publishing."
else
    print_success "PYPI_API_TOKEN is set locally."
fi

# Only check GitHub secrets if the repository exists
if [ $REPO_EXISTS -eq 1 ]; then
    print_info "Checking GitHub repository secrets..."
    
    # Function to check if a GitHub secret exists
    check_github_secret() {
        local secret_name="$1"
        local secret_exists=0
        
        # Use gh secret list to check if the secret exists
        if gh secret list --repo "$REPO_FULL_NAME" | grep -q "^$secret_name\s"; then
            print_success "GitHub secret $secret_name is set in the repository."
            return 0
        else
            print_warning "GitHub secret $secret_name is not set in the repository."
            SECRET_CONFIG_NEEDED=1
            return 1
        fi
    }
    
    # Check each required secret
    check_github_secret "OPENROUTER_API_KEY"
    check_github_secret "CODECOV_API_TOKEN"
    check_github_secret "PYPI_API_TOKEN"
    
    # Configure missing secrets if needed
    if [ $SECRET_CONFIG_NEEDED -eq 1 ]; then
        print_warning "Some GitHub secrets need to be configured."
        
        if [ -n "$OPENROUTER_API_KEY" ] && ! check_github_secret "OPENROUTER_API_KEY" &>/dev/null; then
            print_info "Setting GitHub secret OPENROUTER_API_KEY from local environment..."
            gh secret set OPENROUTER_API_KEY --repo "$REPO_FULL_NAME" --body "$OPENROUTER_API_KEY" && \
                print_success "GitHub secret OPENROUTER_API_KEY set successfully." || \
                print_warning "Failed to set GitHub secret OPENROUTER_API_KEY."
        fi
        
        if [ -n "$CODECOV_API_TOKEN" ] && ! check_github_secret "CODECOV_API_TOKEN" &>/dev/null; then
            print_info "Setting GitHub secret CODECOV_API_TOKEN from local environment..."
            gh secret set CODECOV_API_TOKEN --repo "$REPO_FULL_NAME" --body "$CODECOV_API_TOKEN" && \
                print_success "GitHub secret CODECOV_API_TOKEN set successfully." || \
                print_warning "Failed to set GitHub secret CODECOV_API_TOKEN."
        fi
        
        if [ -n "$PYPI_API_TOKEN" ] && ! check_github_secret "PYPI_API_TOKEN" &>/dev/null; then
            print_info "Setting GitHub secret PYPI_API_TOKEN from local environment..."
            gh secret set PYPI_API_TOKEN --repo "$REPO_FULL_NAME" --body "$PYPI_API_TOKEN" && \
                print_success "GitHub secret PYPI_API_TOKEN set successfully." || \
                print_warning "Failed to set GitHub secret PYPI_API_TOKEN."
        fi
    fi
fi

if [ $MISSING_VARS -eq 1 ]; then
    print_warning "Some required environment variables are missing. See CLAUDE.md section 1.4 for details."
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_info "Aborting as requested."
        exit 1
    fi
fi

# *** STEP 7: Push to GitHub ***
