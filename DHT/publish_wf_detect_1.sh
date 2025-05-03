#!/usr/bin/env bash

# Return error if executed directly - MUST BE PLACED AT THE BEGINNING
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    echo "Error: This script cannot be executed directly. All DHT scripts can only be called by the DHT Launcher in the project root. Please run dhtl.sh (or dhtl.bat) followed by the action you want to execute. For more informations use dhtl.sh --help"
    exit 1
fi

set -eo pipefail
source "${SCRIPT_DIR}/publish_common.sh"

# Function to detect and trigger workflows
trigger_workflow() {
    local repo_fullname="$1"
    local branch="$2"
    local workflow_type="$3"
    local max_retries="${4:-3}"
    
    print_step "Detecting and triggering $workflow_type workflow..."
    
    # Get appropriate workflow based on type
    local workflow_file
    workflow_file=$(detect_available_workflows "$repo_fullname" "$workflow_type")

    if [ -z "$workflow_file" ]; then
        print_error "No $workflow_type workflow detected. Cannot trigger workflow."
        print_info "Please check if you have appropriate $workflow_type workflows in .github/workflows/"
        return 1
    fi

    print_info "Detected $workflow_type workflow: $workflow_file"
    
    # Verify if the workflow has workflow_dispatch trigger before attempting to trigger it
    if [ -f ".github/workflows/$workflow_file" ]; then
        if ! grep -q "workflow_dispatch:" ".github/workflows/$workflow_file"; then
            print_warning "The selected workflow file does not contain 'workflow_dispatch:' trigger."
            print_warning "Adding workflow_dispatch support to $workflow_file..."
            
            # Create a temporary file with added workflow_dispatch trigger
            local temp_file
            temp_file=$(mktemp)
            
            # Determine the correct pattern to add workflow_dispatch to the 'on:' section
            if grep -A5 "^on:" ".github/workflows/$workflow_file" | grep -q "{"; then
                # The file uses object syntax for triggers
                sed -e '/^on:.*{/a \  workflow_dispatch: {}\n  # Added by publish_to_github.sh script' ".github/workflows/$workflow_file" > "$temp_file"
            else
                # The file uses list syntax for triggers
                sed -e '/^on:/a \  workflow_dispatch:  # Added by publish_to_github.sh script\n    inputs:\n      reason:\n        description: '"'"'Reason for manual trigger'"'"'\n        required: false\n        default: '"'"'Triggered by publish_to_github.sh'"'"'' ".github/workflows/$workflow_file" > "$temp_file"
            fi
            
            # Check if the modification worked
            if grep -q "workflow_dispatch:" "$temp_file"; then
                # Backup the original file and replace it with the modified version
                cp ".github/workflows/$workflow_file" ".github/workflows/$workflow_file.bak"
                mv "$temp_file" ".github/workflows/$workflow_file"
                
                print_success "Added workflow_dispatch trigger to $workflow_file."
                print_info "You may need to commit and push this change before triggering the workflow."
                
                # Attempt to verify and commit the change
                if git diff --quiet ".github/workflows/$workflow_file"; then
                    print_warning "Failed to modify workflow file. Changes not detected."
                else
                    print_info "Workflow file modified. Committing the change..."
                    git add ".github/workflows/$workflow_file"
                    git commit -m "Add workflow_dispatch trigger to $workflow_file [skip-tests]" || {
                        print_warning "Failed to commit workflow file changes."
                    }
                    
                    # Push the change
                    print_info "Pushing workflow change to repository..."
                    git push origin "$(git rev-parse --abbrev-ref HEAD)" || {
                        print_warning "Failed to push workflow changes. Manual intervention may be required."
                    }
                    
                    # Wait for GitHub to process the workflow file change
                    print_info "Waiting 60 seconds for GitHub to process workflow file changes..."
                    sleep 60
                fi
            else
                print_warning "Failed to add workflow_dispatch trigger to $workflow_file."
                # Clean up the temporary file
                rm -f "$temp_file"
            fi
        else
            print_success "Workflow file has workflow_dispatch trigger. Proceeding with triggering."
        fi
    else
        print_warning "Workflow file not found locally at .github/workflows/$workflow_file."
        print_info "Attempting to trigger using GitHub API without local verification."
    fi
    
    local retry_count=0
    local success="false"
    
    # STEP 1: Direct workflow run with gh CLI
    print_info "Attempting to trigger workflow via gh CLI (preferred method)..."
    while [ $retry_count -lt $max_retries ] && [ "$success" != "true" ]; do
        print_info "Triggering $workflow_type workflow (attempt ${retry_count}/${max_retries})..."
        
        # Add optional inputs for better tracking
        if gh workflow run "$workflow_file" --repo "$repo_fullname" --ref "$branch" -f "reason=Triggered via publish_to_github.sh script"; then
            print_success "$workflow_type workflow triggered successfully via direct gh CLI run."
            success="true"
        elif gh workflow run "$workflow_file" --repo "$repo_fullname" --ref "$branch"; then
            # Try without input parameters, in case the workflow doesn't accept inputs
            print_success "$workflow_type workflow triggered successfully via direct gh CLI run (without inputs)."
            success="true"
        else
            retry_count=$((retry_count+1))
            if [ $retry_count -lt $max_retries ]; then
                print_warning "Failed to trigger $workflow_type workflow. Retrying in 3 seconds... (Attempt $retry_count of $max_retries)"
                sleep 3
            elif [ $retry_count -eq $max_retries ]; then
                # Move to STEP 2
                print_warning "Direct workflow triggering via gh CLI failed after $max_retries attempts."
                print_info "Moving to alternative trigger methods..."
                break
            fi
        fi
    done
    
    # STEP 2: GitHub API dispatches approach
    if [ "$success" != "true" ]; then
        print_info "Attempting to trigger workflow via GitHub API..."
        
        # Try different input formats to handle potential API changes or variations
        local input_formats=(
            # Format 1: Using inputs object with dot notation (newer format)
            "\"inputs\":{\"reason\":\"Triggered via publish_to_github.sh script\"}"
            
            # Format 2: Using inputs array with brackets notation (older format)
            "\"inputs[reason]\":\"Triggered via publish_to_github.sh script\""
            
            # Format 3: No inputs (simplest)
            ""
        )
        
        for format in "${input_formats[@]}"; do
            # Construct the API command based on the input format
            local api_cmd
            if [ -n "$format" ]; then
                api_cmd="gh api --method POST \"repos/$repo_fullname/actions/workflows/$workflow_file/dispatches\" -f \"ref=$branch\" -f $format --silent"
            else
                api_cmd="gh api --method POST \"repos/$repo_fullname/actions/workflows/$workflow_file/dispatches\" -f \"ref=$branch\" --silent"
            fi
            
            print_info "Trying API format: $api_cmd"
            
            # Execute the API command
            if eval "$api_cmd"; then
                print_success "$workflow_type workflow triggered successfully via GitHub API."
                success="true"
                break
            else
                print_warning "API format failed, trying next format..."
            fi
        done
    fi
    
    # STEP 3: Workflow ID approach
    if [ "$success" != "true" ]; then
        print_warning "GitHub API dispatches approach failed. Trying workflow ID method..."
        
        # Get all workflows and extract ID for the specific workflow
        local workflow_id
        workflow_id=$(gh api "repos/$repo_fullname/actions/workflows" --jq ".workflows[] | select(.path | endswith(\"/$workflow_file\")) | .id" 2>/dev/null)
        
        if [ -n "$workflow_id" ]; then
            print_info "Found workflow ID: $workflow_id, attempting to trigger using ID..."
            
            # Try different data formats for the API call
            local data_formats=(
                # Format 1: With inputs object
                "{\"ref\":\"$branch\",\"inputs\":{\"reason\":\"Triggered via publish_to_github.sh script\"}}"
                
                # Format 2: Without inputs
                "{\"ref\":\"$branch\"}"
            )
            
            for data in "${data_formats[@]}"; do
                if gh api --method POST "repos/$repo_fullname/actions/workflows/$workflow_id/dispatches" --input - <<< "$data" 2>/dev/null; then
                    print_success "$workflow_type workflow triggered successfully via workflow ID."
                    success="true"
                    break
                fi
            done
        else
            print_warning "Could not find workflow ID for $workflow_file."
        fi
    fi
    
    # STEP 4: Curl direct REST API approach
    if [ "$success" != "true" ]; then
        print_warning "GitHub CLI approaches failed. Trying direct curl to REST API..."
        
        # Get GitHub token
        GH_TOKEN=$(gh auth token)
        
        # Additional curl implementation would go here
        # ...
        
        # For now, just indicate attempt
        print_warning "Direct curl implementation not fully implemented."
    fi
    
    return $success
}
