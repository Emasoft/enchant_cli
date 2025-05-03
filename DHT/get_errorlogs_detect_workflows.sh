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
