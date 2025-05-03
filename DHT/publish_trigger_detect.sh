#!/usr/bin/env bash

# Return error if executed directly - MUST BE PLACED AT THE BEGINNING
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    echo "Error: This script cannot be executed directly. All DHT scripts can only be called by the DHT Launcher in the project root. Please run dhtl.sh (or dhtl.bat) followed by the action you want to execute. For more informations use dhtl.sh --help"
    exit 1
fi

set -eo pipefail
source "${SCRIPT_DIR}/publish_common.sh"

# Function to detect the available workflows 
# This is an improved version that uses a multi-tiered detection approach
detect_available_workflows() {
    local repo_fullname="$1"
    local workflow_type="$2"  # 'test', 'release', or empty for all
    local max_depth=3  # How deep to search for workflow files
    local quiet="${3:-false}"  # Optional parameter to suppress info messages
    
    # Define standard pattern mappings for workflow types
    local test_patterns="tests|test|pytest|unittest|jest|mocha|check|lint|quality|ci"
    local release_patterns="release|publish|deploy|build|package|version|deploy|upload|distribute"
    
    # STEP 1: Check for workflow files in standard location
    # This approach relies on presence and naming of files
    if [ -d ".github/workflows" ]; then
        # Only show this message if not in quiet mode
        if [ "$quiet" != "true" ]; then
            print_info "Checking for local workflow files in .github/workflows/"
        fi
        
        # Use find with depth limit for safety
        local workflow_files
        workflow_files=$(find ".github/workflows" -maxdepth $max_depth -type f -name "*.yml" -o -name "*.yaml" 2>/dev/null | sort)
        
        # Filter workflow files by type if requested
        if [ -n "$workflow_files" ]; then
            if [ "$workflow_type" = "test" ]; then
                # First try with exact known names
                for name in "tests.yml" "test.yml" "ci.yml" "quality.yml" "lint.yml" "check.yml"; do
                    if echo "$workflow_files" | grep -q "$name"; then
                        if [ "$quiet" != "true" ]; then
                            print_info "Found matching test workflow file by known name: $name"
                        fi
                        echo "$name"
                        return 0
                    fi
                done
                
                # Then try with pattern matching on the filename
                local test_workflow
                test_workflow=$(echo "$workflow_files" | grep -E "($test_patterns)" | head -1 | xargs -n1 basename 2>/dev/null)
                if [ -n "$test_workflow" ]; then
                    if [ "$quiet" != "true" ]; then
                        print_info "Found matching test workflow file by pattern: $test_workflow"
                    fi
                    echo "$test_workflow"
                    return 0
                fi
            elif [ "$workflow_type" = "release" ]; then
                # First try with exact known names
                for name in "auto_release.yml" "release.yml" "publish.yml" "deploy.yml" "build.yml" "package.yml"; do
                    if echo "$workflow_files" | grep -q "$name"; then
                        if [ "$quiet" != "true" ]; then
                            print_info "Found matching release workflow file by known name: $name"
                        fi
                        echo "$name"
                        return 0
                    fi
                done
                
                # Then try with pattern matching on the filename
                local release_workflow
                release_workflow=$(echo "$workflow_files" | grep -E "($release_patterns)" | head -1 | xargs -n1 basename 2>/dev/null)
                if [ -n "$release_workflow" ]; then
                    if [ "$quiet" != "true" ]; then
                        print_info "Found matching release workflow file by pattern: $release_workflow"
                    fi
                    echo "$release_workflow"
                    return 0
                fi
            elif [ -z "$workflow_type" ]; then
                # Return all workflow filenames
                echo "$workflow_files" | xargs -n1 basename 2>/dev/null
                return 0
            fi
        fi
    fi
    
    # STEP 2: Content-based detection
    # This approach checks the contents of files for workflow indicators
    if [ -d ".github/workflows" ]; then
        if [ "$quiet" != "true" ]; then
            print_info "No matching workflow files found by name. Checking file contents..."
        fi
        
        local test_workflows=()
        local release_workflows=()
        local all_workflows=()
        
        # Create temporary arrays to store workflows
        while IFS= read -r file; do
            if [ -f "$file" ]; then
                # Get the base filename
                local basename_file
                basename_file=$(basename "$file")
                all_workflows+=("$basename_file")
                
                # Check for workflow_dispatch trigger - essential for our workflow triggering
                local has_workflow_dispatch=0
                if grep -q "workflow_dispatch:" "$file" 2>/dev/null; then
                    has_workflow_dispatch=1
                fi
                
                # Check workflow file content to determine its purpose
                if grep -q -E "($test_patterns)" "$file" 2>/dev/null; then
                    test_workflows+=("$basename_file")
                    # Prioritize workflows with workflow_dispatch trigger
                    if [ $has_workflow_dispatch -eq 1 ] && [ "$workflow_type" = "test" ]; then
                        if [ "$quiet" != "true" ]; then
                            print_info "Found test workflow with workflow_dispatch: $basename_file"
                        fi
                        echo "$basename_file"
                        return 0
                    fi
                fi
                
                if grep -q -E "($release_patterns)" "$file" 2>/dev/null; then
                    release_workflows+=("$basename_file")
                    # Prioritize workflows with workflow_dispatch trigger
                    if [ $has_workflow_dispatch -eq 1 ] && [ "$workflow_type" = "release" ]; then
                        if [ "$quiet" != "true" ]; then
                            print_info "Found release workflow with workflow_dispatch: $basename_file"
                        fi
                        echo "$basename_file"
                        return 0
                    fi
                fi
            fi
        done < <(find ".github/workflows" -maxdepth $max_depth -type f -name "*.yml" -o -name "*.yaml" 2>/dev/null)
        
        # Return results based on workflow type
        if [ "$workflow_type" = "test" ] && [ ${#test_workflows[@]} -gt 0 ]; then
            if [ "$quiet" != "true" ]; then
                print_info "Found matching test workflow by content: ${test_workflows[0]}"
            fi
            echo "${test_workflows[0]}"
            return 0
        elif [ "$workflow_type" = "release" ] && [ ${#release_workflows[@]} -gt 0 ]; then
            if [ "$quiet" != "true" ]; then
                print_info "Found matching release workflow by content: ${release_workflows[0]}"
            fi
            echo "${release_workflows[0]}"
            return 0
        elif [ -z "$workflow_type" ] && [ ${#all_workflows[@]} -gt 0 ]; then
            for wf in "${all_workflows[@]}"; do
                echo "$wf"
            done
            return 0
        fi
    fi
    
    # STEP 3: GitHub API detection
    # This approach uses the GitHub API to retrieve workflow information
    if [ "$quiet" != "true" ]; then
        print_info "No matching workflow files found locally. Trying GitHub API..."
    fi
    
    # Get all workflows from the GitHub API
    local all_workflows
    all_workflows=$(gh api "repos/$repo_fullname/actions/workflows" --jq '.workflows[]' 2>/dev/null)
    
    if [ -n "$all_workflows" ]; then
        # Parse all workflows based on workflow type
        if [ "$workflow_type" = "test" ]; then
            # Look for testing-related workflows by name or path pattern
            local api_test_workflow
            api_test_workflow=$(gh api "repos/$repo_fullname/actions/workflows" --jq ".workflows[] | select(.name | test(\"(?i)($test_patterns)\") or .path | test(\"(?i)($test_patterns)\")) | .path" | sed 's/.*\/\(.*\)$/\1/' | head -1)
            
            if [ -n "$api_test_workflow" ]; then
                if [ "$quiet" != "true" ]; then
                    print_info "Found test workflow via GitHub API: $api_test_workflow"
                fi
                echo "$api_test_workflow"
                return 0
            fi
        elif [ "$workflow_type" = "release" ]; then
            # Look for release-related workflows by name or path pattern
            local api_release_workflow
            api_release_workflow=$(gh api "repos/$repo_fullname/actions/workflows" --jq ".workflows[] | select(.name | test(\"(?i)($release_patterns)\") or .path | test(\"(?i)($release_patterns)\")) | .path" | sed 's/.*\/\(.*\)$/\1/' | head -1)
            
            if [ -n "$api_release_workflow" ]; then
                if [ "$quiet" != "true" ]; then
                    print_info "Found release workflow via GitHub API: $api_release_workflow"
                fi
                echo "$api_release_workflow"
                return 0
            fi
        else
            # Return all workflow paths for general use
            local api_all_workflows
            api_all_workflows=$(gh api "repos/$repo_fullname/actions/workflows" --jq '.workflows[] | .path' | sed 's/.*\/\(.*\)$/\1/')
            
            if [ -n "$api_all_workflows" ]; then
                echo "$api_all_workflows"
                return 0
            fi
        fi
    fi
    
    # STEP 4: Default fallback
    # If all else fails, return standard default workflow names
    if [ "$quiet" != "true" ]; then
        print_warning "No workflows found through any detection method. Using default fallback names."
    fi
    
    if [ "$workflow_type" = "test" ]; then
        echo "tests.yml"  # Default test workflow name
    elif [ "$workflow_type" = "release" ]; then
        echo "auto_release.yml"  # Default release workflow name
    elif [ -z "$workflow_type" ]; then
        echo "tests.yml"
        echo "auto_release.yml"
        echo "publish.yml"
    fi
    
    return 1
}
