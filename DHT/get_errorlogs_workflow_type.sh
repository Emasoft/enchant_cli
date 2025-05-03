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
