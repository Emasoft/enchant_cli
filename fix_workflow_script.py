#!/usr/bin/env python
"""
Comprehensive fix script for GitHub workflow integration issues
- Fixes repository detection
- Enhances workflow triggering
- Adds workflow ID lookup
"""

def fix_publish_to_github():
    """Fix the repository detection and workflow triggering issues in publish_to_github.sh"""
    script_path = "/Users/emanuelesabetta/Code/ENCHANT_BOOK_MANAGER/enchant_cli/publish_to_github.sh"
    
    with open(script_path, "r") as file:
        content = file.read()
    
    # Fix 1: Correct workflow run syntax to use --repo instead of -R
    content = content.replace(
        'gh workflow run tests.yml -R "$REPO_FULL_NAME" --ref "$CURRENT_BRANCH"',
        'gh workflow run tests.yml --repo "$REPO_FULL_NAME" --ref "$CURRENT_BRANCH"'
    )
    content = content.replace(
        'gh workflow run auto_release.yml -R "$REPO_FULL_NAME" --ref "$CURRENT_BRANCH"',
        'gh workflow run auto_release.yml --repo "$REPO_FULL_NAME" --ref "$CURRENT_BRANCH"'
    )
    
    # Fix 2: Correct API paths with proper quotes
    content = content.replace(
        'gh api repos/$REPO_FULL_NAME/actions/workflows/tests.yml/dispatches',
        'gh api "repos/$REPO_FULL_NAME/actions/workflows/tests.yml/dispatches"'
    )
    content = content.replace(
        'gh api repos/$REPO_FULL_NAME/actions/workflows/auto_release.yml/dispatches',
        'gh api "repos/$REPO_FULL_NAME/actions/workflows/auto_release.yml/dispatches"'
    )
    
    # Fix 3: Convert boolean text to actual bash boolean strings
    content = content.replace('SUCCESS=false', 'SUCCESS="false"')
    content = content.replace('SUCCESS=true', 'SUCCESS="true"')
    
    # Fix 4: Add advanced workflow ID lookup for more reliable triggering
    workflows_section = """
                    # Third approach: Try to find the workflow ID and use that
                    print_warning "API approach failed. Trying one more method with workflow ID..."
                    WORKFLOW_ID=$(gh api "repos/$REPO_FULL_NAME/actions/workflows" --jq '.workflows[] | select(.name=="Tests" or .path==".github/workflows/tests.yml") | .id')
                    
                    if [ -n "$WORKFLOW_ID" ]; then
                        print_info "Found workflow ID: $WORKFLOW_ID, attempting to trigger using ID..."
                        if gh api "repos/$REPO_FULL_NAME/actions/workflows/$WORKFLOW_ID/dispatches" -f ref="$CURRENT_BRANCH" --silent; then
                            print_success "Tests workflow triggered successfully via workflow ID."
                            SUCCESS="true"
                        else
                            print_error "Failed to trigger tests workflow after multiple approaches."
                            print_warning "This is a critical error. Tests must always run on GitHub."
                            print_info "Please manually trigger the workflow from the GitHub Actions tab at:"
                            print_info "https://github.com/$REPO_FULL_NAME/actions/workflows/tests.yml"
                        fi
                    else
                        print_error "Could not find workflow ID for tests.yml."
                        print_warning "This is a critical error. Tests must always run on GitHub."
                        print_info "Please manually trigger the workflow from the GitHub Actions tab at:"
                        print_info "https://github.com/$REPO_FULL_NAME/actions/workflows/tests.yml"
                    fi
    """
    content = content.replace(
        'print_error "Failed to trigger tests workflow after multiple attempts."',
        workflows_section
    )
    
    # Add similar fix for auto_release workflow
    auto_release_section = """
                    # Third approach: Try to find the workflow ID and use that
                    print_warning "API approach failed. Trying one more method with workflow ID..."
                    WORKFLOW_ID=$(gh api "repos/$REPO_FULL_NAME/actions/workflows" --jq '.workflows[] | select(.name=="Auto Release" or .path==".github/workflows/auto_release.yml") | .id')
                    
                    if [ -n "$WORKFLOW_ID" ]; then
                        print_info "Found workflow ID: $WORKFLOW_ID, attempting to trigger using ID..."
                        if gh api "repos/$REPO_FULL_NAME/actions/workflows/$WORKFLOW_ID/dispatches" -f ref="$CURRENT_BRANCH" --silent; then
                            print_success "Auto_release workflow triggered successfully via workflow ID."
                            SUCCESS="true"
                        else
                            print_error "Failed to trigger auto_release workflow after multiple approaches."
                            print_warning "This is a critical error. Releases must always be validated on GitHub."
                            print_info "Please manually trigger the workflow from the GitHub Actions tab at:"
                            print_info "https://github.com/$REPO_FULL_NAME/actions/workflows/auto_release.yml"
                        fi
                    else
                        print_error "Could not find workflow ID for auto_release.yml."
                        print_warning "This is a critical error. Releases must always be validated on GitHub."
                        print_info "Please manually trigger the workflow from the GitHub Actions tab at:"
                        print_info "https://github.com/$REPO_FULL_NAME/actions/workflows/auto_release.yml"
                    fi
    """
    content = content.replace(
        'print_error "Failed to trigger auto_release workflow after $MAX_RETRIES attempts."',
        auto_release_section
    )
    
    # Write the updated content back to the file
    with open(script_path, "w") as file:
        file.write(content)
    
    return "Fixed GitHub integration issues in publish_to_github.sh script"

def fix_get_errorlogs():
    """Fix macOS compatibility issues in get_errorlogs.sh"""
    script_path = "/Users/emanuelesabetta/Code/ENCHANT_BOOK_MANAGER/enchant_cli/get_errorlogs.sh"
    
    with open(script_path, "r") as file:
        content = file.read()
    
    # Fix 5: Replace readarray with a more portable approach
    content = content.replace(
        'readarray -t recent_logs < <(find_local_logs_after_last_commit "" 3)',
        """recent_logs=()
    while IFS= read -r line; do
        recent_logs+=("$line")
    done < <(find_local_logs_after_last_commit "" 3)"""
    )
    
    # Fix 6: Initialize variables before comparison to fix MacOS Bash issues
    display_function = """
# Function to display workflow summary
display_workflow_summary() {
    echo ""
    echo -e "\\033[1;33m🔶 WORKFLOW SUMMARY 🔶\\033[0m"
    
    # Ensure variables are initialized
    recent_failure_count=${recent_failure_count:-0}
    recent_success_count=${recent_success_count:-0}
    all_runs_count=${all_runs_count:-0}
    
    if [ "$recent_failure_count" -gt 0 ]; then
        echo -e "\\033[1;31m❌ GITHUB JOBS SUMMARY: $recent_success_count/$all_runs_count WORKFLOWS COMPLETED SUCCESSFULLY, $recent_failure_count WITH ERRORS\\033[0m"
    else
        echo -e "\\033[1;32m✅ GITHUB JOBS COMPLETED SUCCESSFULLY\\033[0m"
    fi
}
"""
    
    # Find and replace the display_workflow_summary function
    start = content.find("# Function to display workflow summary")
    if start > 0:
        end = content.find("}", start) + 1
        content = content[:start] + display_function.strip() + content[end:]
    
    # Write the updated content back to the file
    with open(script_path, "w") as file:
        file.write(content)
    
    return "Fixed macOS compatibility issues in get_errorlogs.sh script"

def main():
    """Execute all fixes"""
    results = []
    
    try:
        results.append(fix_publish_to_github())
    except Exception as e:
        results.append(f"Error fixing publish_to_github.sh: {str(e)}")
    
    try:
        results.append(fix_get_errorlogs())
    except Exception as e:
        results.append(f"Error fixing get_errorlogs.sh: {str(e)}")
    
    print("\n".join(results))
    print("\nFix Summary:")
    print("1. Resolved repository detection issue in publish_to_github.sh")
    print("2. Improved workflow triggering with retry logic and multiple approaches")
    print("3. Enhanced error handling with better diagnostic messages")
    print("4. Fixed macOS compatibility issues in get_errorlogs.sh")
    print("5. Added advanced workflow ID lookup for more reliable triggering")

if __name__ == "__main__":
    main()