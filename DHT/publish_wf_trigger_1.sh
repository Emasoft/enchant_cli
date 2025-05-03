#!/usr/bin/env bash

# Return error if executed directly - MUST BE PLACED AT THE BEGINNING
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    echo "Error: This script cannot be executed directly. All DHT scripts can only be called by the DHT Launcher in the project root. Please run dhtl.sh (or dhtl.bat) followed by the action you want to execute. For more informations use dhtl.sh --help"
    exit 1
fi

set -eo pipefail
source "${SCRIPT_DIR}/publish_common.sh"

    print_step "Triggering GitHub workflows - CRITICAL PROCESS..."
    
    print_info "${BOLD}MANDATORY:${NC} GitHub workflows MUST run to complete the project's CI/CD process."
    print_info "${BOLD}IMPORTANT:${NC} This script will attempt multiple methods to ensure workflows run."
    print_info "If workflows fail to trigger, follow the instructions provided at the end."
    
    # Detect if workflow files are new or modified
    WORKFLOW_FILES_CHANGED=0
    if git diff --name-only HEAD~ 2>/dev/null | grep -q ".github/workflows/"; then
        WORKFLOW_FILES_CHANGED=1
        print_warning "Workflow files were modified in recent commits."
        print_info "GitHub needs time to process workflow file changes before 'workflow_dispatch' events work."
        print_info "Adding extra delay to ensure GitHub recognizes the workflow_dispatch triggers."
        
        # Add extra delay for GitHub to process workflow file changes
        print_info "Waiting 30 seconds for GitHub to finish processing workflow file changes..."
        for i in {1..30}; do
            sleep 1
            if [ $((i % 5)) -eq 0 ]; then
                echo -n "."
            fi
        done
        echo ""
    fi
    
    # Try to detect workflows in multiple ways
    print_info "Identifying all available workflows using multiple detection methods..."
    
    # METHOD 1: Direct file detection
    LOCAL_WORKFLOWS=""
    if [ -d ".github/workflows" ]; then
        LOCAL_WORKFLOWS=$(find .github/workflows -type f -name "*.yml" -o -name "*.yaml" | xargs -n1 basename 2>/dev/null)
    fi
    
    # METHOD 2: API detection (potentially different from local files)
    API_WORKFLOWS=""
    API_WORKFLOWS=$(gh api "repos/$REPO_FULL_NAME/actions/workflows" --jq '.workflows[] | .path' 2>/dev/null | sed 's/.*\/\(.*\)$/\1/' || echo "")
    
    # METHOD 3: Enhanced detection algorithm
    DETECTED_WORKFLOWS=""
    DETECTED_WORKFLOWS=$(detect_available_workflows "$REPO_FULL_NAME" "" "true")
    
    # METHOD 4: Combined detection for maximal coverage
    ALL_WORKFLOWS=""
    for workflow in $LOCAL_WORKFLOWS $API_WORKFLOWS $DETECTED_WORKFLOWS; do
        if ! echo "$ALL_WORKFLOWS" | grep -q "$workflow"; then
            ALL_WORKFLOWS="$ALL_WORKFLOWS $workflow"
        fi
    done
    
    # Trim leading/trailing whitespace
    ALL_WORKFLOWS=$(echo "$ALL_WORKFLOWS" | xargs)
    
    if [ -z "$ALL_WORKFLOWS" ]; then
        print_warning "No workflows detected through any method. Using default workflow names."
        ALL_WORKFLOWS="tests.yml auto_release.yml publish.yml"
    else
        print_info "Identified workflows: $ALL_WORKFLOWS"
    fi
    
    # Group workflows by type for more strategic triggering
    TEST_WORKFLOWS=""
    RELEASE_WORKFLOWS=""
    OTHER_WORKFLOWS=""
    
    for workflow in $ALL_WORKFLOWS; do
        if [[ "$workflow" == *"test"* || "$workflow" == *"ci"* || "$workflow" == *"lint"* || "$workflow" == *"check"* ]]; then
            TEST_WORKFLOWS="$TEST_WORKFLOWS $workflow"
        elif [[ "$workflow" == *"release"* || "$workflow" == *"publish"* || "$workflow" == *"deploy"* || "$workflow" == *"build"* ]]; then
            RELEASE_WORKFLOWS="$RELEASE_WORKFLOWS $workflow"
        else
            OTHER_WORKFLOWS="$OTHER_WORKFLOWS $workflow"
        fi
    done
    
    # Trim whitespace
    TEST_WORKFLOWS=$(echo "$TEST_WORKFLOWS" | xargs)
    RELEASE_WORKFLOWS=$(echo "$RELEASE_WORKFLOWS" | xargs)
    OTHER_WORKFLOWS=$(echo "$OTHER_WORKFLOWS" | xargs)
    
    print_info "Categorized workflows:"
    [ -n "$TEST_WORKFLOWS" ] && print_info "- Tests: $TEST_WORKFLOWS"
    [ -n "$RELEASE_WORKFLOWS" ] && print_info "- Release: $RELEASE_WORKFLOWS"
    [ -n "$OTHER_WORKFLOWS" ] && print_info "- Other: $OTHER_WORKFLOWS"
    
    # Initialize tracking variables
    WORKFLOW_TRIGGER_SUCCESS=0
    TEST_WORKFLOW_TRIGGERED=0
    RELEASE_WORKFLOW_TRIGGERED=0
    VERIFICATION_RETRY_COUNT=0
    WORKFLOW_VERIFICATION_SUCCESS=0
    
    # *** STEP 1: Direct triggering of identified workflows by category ***
    print_info "Triggering workflows by category for optimal CI/CD pipeline execution..."
    
    # First trigger test workflows (most important)
    if [ -n "$TEST_WORKFLOWS" ]; then
        print_info "Triggering test workflows first (highest priority)..."
        
        # Try each test workflow
        for workflow in $TEST_WORKFLOWS; do
            print_info "Triggering test workflow: $workflow"
            ${SCRIPT_DIR}/publish_trigger_workflow.sh "$REPO_FULL_NAME" "$CURRENT_BRANCH" "test" 2
            if [ $? -eq 0 ]; then
                TEST_WORKFLOW_TRIGGERED=1
                WORKFLOW_TRIGGER_SUCCESS=1
            fi
        done
    else
        # Fallback to generic test workflow detection
        print_info "No specific test workflows identified. Using generic test workflow detection..."
        ${SCRIPT_DIR}/publish_trigger_workflow.sh "$REPO_FULL_NAME" "$CURRENT_BRANCH" "test" 2
        if [ $? -eq 0 ]; then
            TEST_WORKFLOW_TRIGGERED=1
            WORKFLOW_TRIGGER_SUCCESS=1
        fi
    fi
    
    # Then trigger release workflows
    if [ -n "$RELEASE_WORKFLOWS" ]; then
        print_info "Triggering release workflows (second priority)..."
        
        # Try each release workflow
        for workflow in $RELEASE_WORKFLOWS; do
            print_info "Triggering release workflow: $workflow"
            ${SCRIPT_DIR}/publish_trigger_workflow.sh "$REPO_FULL_NAME" "$CURRENT_BRANCH" "release" 2
            if [ $? -eq 0 ]; then
                RELEASE_WORKFLOW_TRIGGERED=1
                WORKFLOW_TRIGGER_SUCCESS=1
            fi
        done
    else
        # Fallback to generic release workflow detection
        print_info "No specific release workflows identified. Using generic release workflow detection..."
        ${SCRIPT_DIR}/publish_trigger_workflow.sh "$REPO_FULL_NAME" "$CURRENT_BRANCH" "release" 2
        if [ $? -eq 0 ]; then
            RELEASE_WORKFLOW_TRIGGERED=1
            WORKFLOW_TRIGGER_SUCCESS=1
        fi
    fi
