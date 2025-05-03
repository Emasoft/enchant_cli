#!/usr/bin/env bash

# Return error if executed directly - MUST BE PLACED AT THE BEGINNING
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    echo "Error: This script cannot be executed directly. All DHT scripts can only be called by the DHT Launcher in the project root. Please run dhtl.sh (or dhtl.bat) followed by the action you want to execute. For more informations use dhtl.sh --help"
    exit 1
fi

set -eo pipefail
source "${SCRIPT_DIR}/publish_common.sh"

# Function to trigger workflows with curl REST API approach
trigger_workflow_with_curl() {
    local repo_fullname="$1"
    local branch="$2"
    local workflow_type="$3"
    local workflow_file="$4"
    local workflow_id="$5"
    
    local success="false"
    
    print_info "Attempting curl-based REST API workflow triggering..."
    
    # Get GitHub token
    local GH_TOKEN
    GH_TOKEN=$(gh auth token)
    
    if [ -n "$GH_TOKEN" ]; then
        # Try with workflow ID if available
        if [ -n "$workflow_id" ]; then
            print_info "Using workflow ID: $workflow_id"
            
            # Try different data formats
            local data_formats=(
                # Format 1: With inputs
                "{\"ref\":\"$branch\",\"inputs\":{\"reason\":\"Triggered via publish_to_github.sh script\"}}"
                
                # Format 2: Without inputs
                "{\"ref\":\"$branch\"}"
            )
            
            for data in "${data_formats[@]}"; do
                if curl -s -X POST -H "Authorization: token $GH_TOKEN" \
                   -H "Accept: application/vnd.github.v3+json" \
                   "https://api.github.com/repos/$repo_fullname/actions/workflows/$workflow_id/dispatches" \
                   -d "$data"; then
                    print_success "$workflow_type workflow triggered successfully via curl with workflow ID."
                    success="true"
                    break
                fi
            done
        fi
        
        # If still not successful, try with the workflow file path
        if [ "$success" != "true" ] && [ -n "$workflow_file" ]; then
            print_info "Using workflow file path: $workflow_file"
            
            if curl -s -X POST -H "Authorization: token $GH_TOKEN" \
               -H "Accept: application/vnd.github.v3+json" \
               "https://api.github.com/repos/$repo_fullname/actions/workflows/$workflow_file/dispatches" \
               -d "{\"ref\":\"$branch\",\"inputs\":{\"reason\":\"Triggered via publish_to_github.sh script\"}}"; then
                print_success "$workflow_type workflow triggered successfully via curl with workflow path."
                success="true"
            fi
        fi
    else
        print_error "Could not get GitHub token for curl approach."
    fi
    
    # Return success status (0 for success, 1 for failure)
    if [ "$success" = "true" ]; then
        return 0
    else
        return 1
    fi
}
