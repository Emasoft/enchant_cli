#!/usr/bin/env bash

# Return error if executed directly - MUST BE PLACED AT THE BEGINNING
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    echo "Error: This script cannot be executed directly. All DHT scripts can only be called by the DHT Launcher in the project root. Please run dhtl.sh (or dhtl.bat) followed by the action you want to execute. For more informations use dhtl.sh --help"
    exit 1
fi

set -eo pipefail
source "${SCRIPT_DIR}/publish_common.sh"

print_header "GitHub Integration Complete"
print_success "All local checks passed and code has been pushed to GitHub."
echo ""
print_step "Next Step to Publish:"
echo "   1. Create a GitHub Release:"
echo "      - Go to your repository's 'Releases' page on GitHub."
echo "      - Click 'Draft a new release'."
echo "      - Choose the latest tag that was just pushed: $LATEST_TAG"
echo "      - Add release notes."
echo "      - Click 'Publish release'."
echo ""
echo "   2. Monitor the GitHub Action:"
echo "      - Publishing the GitHub Release will trigger the 'Publish Python Package' workflow."
echo "      - Check the 'Actions' tab in your GitHub repository to monitor its progress."
echo "      - This workflow will build the package again and publish it to PyPI."
echo ""
echo "   3. Or create the release automatically now with:"
echo ""
echo "      gh release create $LATEST_TAG -t \"Release $LATEST_TAG\" \\"
echo "        -n \"## What's Changed\\n- Improvements and bug fixes\\n\\n**Full Changelog**: https://github.com/$REPO_FULL_NAME/commits/$LATEST_TAG\""
echo ""
echo "   4. To check workflow logs again later:"
echo "      ./get_errorlogs.sh latest  # Show the most recent logs"
echo "      ./get_errorlogs.sh tests   # Show logs from test workflows"
echo ""

# Offer to create the release directly if asked
read -p "Would you like to create the GitHub release now? (y/N) " -n 1 -r CREATE_RELEASE
echo
if [[ $CREATE_RELEASE =~ ^[Yy]$ ]]; then
    print_info "Creating GitHub release for tag $LATEST_TAG..."
    gh release create "$LATEST_TAG" -t "Release $LATEST_TAG" \
        -n "## What's Changed
- Improvements and bug fixes
- Test sample inclusion fixed
- Local validation improved

**Full Changelog**: https://github.com/$REPO_FULL_NAME/commits/$LATEST_TAG" || {
        print_error "Failed to create GitHub release. Please create it manually."
    }
    
    print_success "GitHub release created. The publish workflow should start automatically."
    print_info "You can monitor its progress at: https://github.com/$REPO_FULL_NAME/actions"
    
    # Wait for PyPI publication if the release was created
    if [ -z "$DRY_RUN" ]; then
        print_info "Would you like to wait and verify PyPI publication? (This may take several minutes)"
        read -p "Wait for PyPI publication? (y/N) " -n 1 -r WAIT_PYPI
        echo
        
        if [[ $WAIT_PYPI =~ ^[Yy]$ ]]; then
            # Extract version number from tag (remove 'v' prefix)
            VERSION=${LATEST_TAG#v}
            
            print_info "Waiting for GitHub Actions workflow to complete and PyPI to update (about 2-3 minutes)..."
            echo "This will attempt to install version $VERSION from PyPI in 2 minutes..."
            
            # Wait for PyPI index to update
            sleep 120
            
            # Try to install the package
            print_info "Attempting to install enchant-cli==$VERSION from PyPI..."
            if timeout $TIMEOUT_TESTS "$PYTHON_CMD" -m pip install --no-cache-dir enchant-cli=="$VERSION"; then
                print_success "Package published and installed successfully from PyPI!"
                
                # Verify the installed version
                print_info "Verifying installed version..."
                INSTALLED_VERSION=$("$PYTHON_CMD" -m pip show enchant-cli | grep "Version:" | cut -d' ' -f2)
                if [ "$INSTALLED_VERSION" = "$VERSION" ]; then
                    print_success "Installed version ($INSTALLED_VERSION) matches expected version ($VERSION)."
                    
                    # Try running the CLI to verify basic functionality
                    if command -v enchant_cli &>/dev/null; then
                        print_info "Testing installed package functionality..."
                        enchant_cli --version && print_success "CLI functionality verified!" || print_warning "CLI verification failed: Command completed with errors."
                    else
                        print_warning "CLI command not available. May need to restart shell or the CLI entry point is missing."
                        print_info "Trying to access CLI directly through Python module..."
                        "$PYTHON_CMD" -m enchant_cli --version && print_success "CLI module functionality verified!" || print_error "CLI module verification failed. The package may be incorrectly installed or configured."
                    fi
                else
                    print_error "Installed version ($INSTALLED_VERSION) does not match expected version ($VERSION)."
                    print_error "This indicates a version mismatch issue in the PyPI publishing process."
                    print_info "Check if the version was properly bumped in __init__.py and if the build process is using the correct version."
                fi
            else
                print_warning "Package not yet available on PyPI. This is normal if the GitHub Action is still running."
                print_info "You can check the status at: https://github.com/$REPO_FULL_NAME/actions"
                print_info "And verify on PyPI later at: https://pypi.org/project/enchant-cli/$VERSION/"
                print_info "If the package doesn't appear after 10 minutes, check GitHub Actions for errors in the publish workflow."
            fi
        fi
    fi
fi

# Function to verify PyPI publication
verify_pypi_publication() {
    local version="$1"
    local timeout_val="${2:-$TIMEOUT_TESTS}"
    
    print_header "Verifying PyPI Publication"
    
    # Determine version to check
    if [ -z "$version" ]; then
        # Extract version number from tag (remove 'v' prefix)
        version=${LATEST_TAG#v}
    fi
    
    print_info "Checking PyPI for enchant-cli version $version..."
    
    # Try to install the package
    print_info "Attempting to install enchant-cli==$version from PyPI..."
    if timeout "$timeout_val" "$PYTHON_CMD" -m pip install --no-cache-dir enchant-cli=="$version"; then
        print_success "Package exists on PyPI and was installed successfully!"
        
        # Verify the installed version
        print_info "Verifying installed version..."
        INSTALLED_VERSION=$("$PYTHON_CMD" -m pip show enchant-cli | grep "Version:" | cut -d' ' -f2)
        if [ "$INSTALLED_VERSION" = "$version" ]; then
            print_success "Installed version ($INSTALLED_VERSION) matches expected version ($version)."
            
            # Try running the CLI to verify basic functionality
            if command -v enchant_cli &>/dev/null; then
                print_info "Testing installed package functionality..."
                enchant_cli --version && print_success "CLI functionality verified!" || print_warning "CLI verification failed: Command completed with errors."
            else
                print_warning "CLI command not available. May need to restart shell or the CLI entry point is missing."
                print_info "Trying to access CLI directly through Python module..."
                "$PYTHON_CMD" -m enchant_cli --version && print_success "CLI module functionality verified!" || print_error "CLI module verification failed. The package may be incorrectly installed or configured."
            fi
        else
            print_error "Installed version ($INSTALLED_VERSION) does not match expected version ($version)."
            print_error "This indicates a version mismatch issue in the PyPI publishing process."
            print_info "Check if the version was properly bumped in __init__.py and if the build process is using the correct version."
        fi
        
        return 0
    else
        print_warning "Package version $version not found on PyPI or installation failed."
        print_info "If a GitHub release was created, the package may still be in the publishing pipeline."
        print_info "Check PyPI at: https://pypi.org/project/enchant-cli/"
        print_info "And GitHub Actions at: https://github.com/$REPO_FULL_NAME/actions"
        
        return 1
    fi
}

# Check if direct PyPI verification was requested
if [ $VERIFY_PYPI -eq 1 ]; then
    if [ -n "$SPECIFIC_VERSION" ]; then
        # Verify specific version
        verify_pypi_publication "$SPECIFIC_VERSION"
    else
        # Verify latest version (extract from tag)
        verify_pypi_publication
    fi
else
    # Ask if user wants to verify PyPI
    print_info "Would you like to verify if the package is available on PyPI? (y/N)"
    read -p "Verify PyPI publication? " -n 1 -r CHECK_PYPI
    echo
    if [[ $CHECK_PYPI =~ ^[Yy]$ ]]; then
        # Use version from tag
        version=${LATEST_TAG#v}
        print_info "Waiting 20 seconds for PyPI to update..."
        sleep 20
        verify_pypi_publication "$version"
    fi
    
    print_info "🚀 The auto_release GitHub workflow will automatically create a release for version $version (if not already created)."
    print_info "📦 The package will be published to PyPI by the GitHub Actions workflow."
    print_info "🔒 GitHub secrets (PYPI_API_TOKEN, OPENROUTER_API_KEY, CODECOV_API_TOKEN) are automatically configured from your local environment."
    print_info "✅ The GitHub Actions workflow will verify the package was published correctly with version $version."
    print_info "🧪 Tests will automatically run on GitHub Actions" $([ $SKIP_TESTS -eq 1 ] && echo "(since they were skipped locally)")
    print_info "📊 Code coverage will be uploaded to Codecov automatically."
    print_info "📝 A changelog will be automatically generated for the release."
    print_info "📚 For more details on the workflow, see CLAUDE.md section 6 (GitHub Integration)."
fi

exit 0
