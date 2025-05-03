#!/usr/bin/env bash

# Return error if executed directly - MUST BE PLACED AT THE BEGINNING
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    echo "Error: This script cannot be executed directly. All DHT scripts can only be called by the DHT Launcher in the project root. Please run dhtl.sh (or dhtl.bat) followed by the action you want to execute. For more informations use dhtl.sh --help"
    exit 1
fi

set -eo pipefail
source "${SCRIPT_DIR}/publish_common.sh"

# Function to trigger and verify workflows
trigger_and_verify_workflows() {
    local REPO_FULL_NAME="$1"
    local CURRENT_BRANCH="$2"
    local TEST_WORKFLOWS="$3"
    local RELEASE_WORKFLOWS="$4"
    local OTHER_WORKFLOWS="$5"
    local WAIT_FOR_LOGS="${6:-0}"
    local REPO_EXISTS="${7:-1}"
    
    local WORKFLOW_TRIGGER_SUCCESS=0
    local WORKFLOW_VERIFICATION_SUCCESS=0
    local VERIFICATION_RETRY_COUNT=0
    
    # Skip if repository doesn't exist yet
    if [ "$REPO_EXISTS" -eq 1 ]; then
        # Finally trigger any other workflows if needed
        if [ -n "$OTHER_WORKFLOWS" ]; then
            print_info "Triggering other uncategorized workflows..."
            
            # Try each other workflow
            for workflow in $OTHER_WORKFLOWS; do
                # Skip if we already triggered this workflow
                if [[ "$TEST_WORKFLOWS $RELEASE_WORKFLOWS" == *"$workflow"* ]]; then
                    print_info "Skipping $workflow (already triggered)"
                    continue
                fi
                
                print_info "Triggering uncategorized workflow: $workflow"
                if gh workflow run "$workflow" --repo "$REPO_FULL_NAME" --ref "$CURRENT_BRANCH" -f "reason=Triggered via publish_to_github.sh script"; then
                    print_success "Successfully triggered workflow: $workflow"
                    WORKFLOW_TRIGGER_SUCCESS=1
                else
                    print_warning "Failed to trigger workflow: $workflow. Will try alternative methods."
                    
                    # Try basic API call
                    if gh api --method POST "repos/$REPO_FULL_NAME/actions/workflows/$workflow/dispatches" -f "ref=$CURRENT_BRANCH" --silent; then
                        print_success "Successfully triggered $workflow via API."
                        WORKFLOW_TRIGGER_SUCCESS=1
                    fi
                fi
            done
        fi
        
        # *** STEP 2: Verify and validate workflow triggering ***
        # This step checks that workflows were actually triggered
        print_info "Waiting for GitHub to register triggered workflows..."
        MAX_VERIFICATION_RETRIES=3
        
        while [ $WORKFLOW_VERIFICATION_SUCCESS -eq 0 ] && [ $VERIFICATION_RETRY_COUNT -lt $MAX_VERIFICATION_RETRIES ]; do
            # Wait and then check for recently triggered workflows
            print_info "Verification attempt $(($VERIFICATION_RETRY_COUNT + 1))/$MAX_VERIFICATION_RETRIES - waiting 10 seconds..."
            sleep 10
            
            # Get list of recent workflow runs with multiple fallback approaches
            RECENT_RUNS=""
            
            # Try using gh run list (preferred)
            RECENT_RUNS=$(gh run list --repo "$REPO_FULL_NAME" --limit 5 --json name,status,conclusion,createdAt | grep -E "in_progress|queued|waiting|pending" || echo "")
            
            # If that fails, try direct API call
            if [ -z "$RECENT_RUNS" ]; then
                RECENT_RUNS=$(gh api "repos/$REPO_FULL_NAME/actions/runs?per_page=5" --jq '.workflow_runs[] | select(.status == "in_progress" or .status == "queued" or .status == "waiting")' 2>/dev/null || echo "")
            fi
            
            # Check if we found any running workflows
            if [ -n "$RECENT_RUNS" ]; then
                print_success "Workflows are now running on GitHub!"
                print_info "Check workflow status at: https://github.com/$REPO_FULL_NAME/actions"
                WORKFLOW_VERIFICATION_SUCCESS=1
            else
                print_warning "No running workflows detected yet. GitHub may need more time..."
                VERIFICATION_RETRY_COUNT=$((VERIFICATION_RETRY_COUNT+1))
                
                if [ $VERIFICATION_RETRY_COUNT -ge $MAX_VERIFICATION_RETRIES ]; then
                    print_warning "Could not verify workflow execution after $MAX_VERIFICATION_RETRIES attempts."
                    print_info "This could mean:"
                    print_info "1. Workflows are taking longer than expected to start"
                    print_info "2. Workflows were not properly triggered"
                    print_info "3. GitHub API is having temporary issues"
                    print_info ""
                    print_info "Please check manually at: https://github.com/$REPO_FULL_NAME/actions"
                fi
            fi
        done
        
        # *** STEP 8: Show manual workflow trigger instructions ***
        # If triggering failed, show instructions for manual triggering
        if [ $WORKFLOW_TRIGGER_SUCCESS -eq 0 ]; then
            print_header "CRITICAL: Manual Workflow Triggering Required"
            print_warning "Automated workflow triggering failed. You MUST trigger workflows manually:"
            print_info ""
            print_info "1. Go to: https://github.com/$REPO_FULL_NAME/actions"
            print_info "2. For each workflow:"
            print_info "   a. Click on the workflow name"
            print_info "   b. Click 'Run workflow' button"
            print_info "   c. Select branch: $CURRENT_BRANCH"
            print_info "   d. Click 'Run workflow'"
            print_info ""
            
            print_info "Available workflows:"
            [ -n "$TEST_WORKFLOWS" ] && print_info "   ▶ TEST WORKFLOWS: $TEST_WORKFLOWS"
            [ -n "$RELEASE_WORKFLOWS" ] && print_info "   ▶ RELEASE WORKFLOWS: $RELEASE_WORKFLOWS"
            [ -n "$OTHER_WORKFLOWS" ] && print_info "   ▶ OTHER WORKFLOWS: $OTHER_WORKFLOWS"
            
            print_info ""
            print_info "3. Select branch: $CURRENT_BRANCH"
            print_info "4. Click 'Run workflow'"
            print_info ""
            print_info "Direct links (copy and paste into browser):"
            
            # Generate direct links for all workflows
            ALL_WORKFLOW_LIST="$TEST_WORKFLOWS $RELEASE_WORKFLOWS $OTHER_WORKFLOWS"
            for workflow in $ALL_WORKFLOW_LIST; do
                print_info "• https://github.com/$REPO_FULL_NAME/actions/workflows/$workflow"
            done
            
            print_info ""
            print_info "${BOLD}IMPORTANT NOTE:${NC} After updating workflow files, GitHub needs 3-5 minutes"
            print_info "to recognize the workflow_dispatch event trigger. If you just pushed workflow"
            print_info "file changes, wait a few minutes before trying to trigger the workflows manually."
            print_info ""
        fi
    else
        print_warning "Repository not found on GitHub. Workflows will be triggered once the repository is created."
        print_info "CRITICAL: Once the repository is created, make sure workflows are triggered."
        print_info "Run this script again after creating the repository, or trigger workflows manually."
    fi

    # *** STEP 9: GitHub Release Information ***
    # Get the latest tag for instructions
    LATEST_TAG=$(git describe --tags --abbrev=0 2>/dev/null || echo "v0.1.0")
    print_info "Latest version tag: $LATEST_TAG"

    # *** STEP 10: Wait for workflow logs if requested ***
    if [ "$WAIT_FOR_LOGS" -eq 1 ] && [ "$REPO_EXISTS" -eq 1 ]; then
        print_header "Waiting for Workflow Logs"
        print_info "Will wait up to 60 seconds for workflows to start and generate logs..."
        
        # Wait for workflows to start (up to 60 seconds)
        WAIT_TIME=0
        MAX_WAIT_TIME=60
        WORKFLOWS_RUNNING=0
        
        while [ $WAIT_TIME -lt $MAX_WAIT_TIME ] && [ $WORKFLOWS_RUNNING -eq 0 ]; do
            # Wait 5 seconds between checks
            sleep 5
            WAIT_TIME=$((WAIT_TIME+5))
            
            # Progress indication
            print_info "Waiting for logs... ($WAIT_TIME / $MAX_WAIT_TIME seconds)"
            
            # Check if there are any running workflows
            WORKFLOWS_RUNNING=$(gh run list --repo "$REPO_FULL_NAME" --limit 10 --json status | grep -c "in_progress" || echo "0")
            
            if [ "$WORKFLOWS_RUNNING" -gt 0 ]; then
                print_success "Found $WORKFLOWS_RUNNING workflow(s) running!"
                break
            fi
        done
        
        if [ $WORKFLOWS_RUNNING -eq 0 ]; then
            print_warning "No workflows were detected running after $MAX_WAIT_TIME seconds."
            print_info "Check workflow status later at: https://github.com/$REPO_FULL_NAME/actions"
        else
            print_info "You can check workflow logs at:"
            print_info "https://github.com/$REPO_FULL_NAME/actions"
        fi
    fi
    
    return $WORKFLOW_TRIGGER_SUCCESS
}
