#!/usr/bin/env bash

# Return error if executed directly - MUST BE PLACED AT THE BEGINNING
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    echo "Error: This script cannot be executed directly. All DHT scripts can only be called by the DHT Launcher in the project root. Please run dhtl.sh (or dhtl.bat) followed by the action you want to execute. For more informations use dhtl.sh --help"
    exit 1
fi

set -eo pipefail
source "${SCRIPT_DIR}/publish_common.sh"

# publish_to_github.sh - Comprehensive GitHub integration script with enhanced workflow management
#
# ***************************************************************************************
# CRITICAL USAGE NOTE: ALWAYS use with --skip-tests flag to ensure GitHub workflows run!
# COMMAND TEMPLATE:  ./publish_to_github.sh --skip-tests
# ***************************************************************************************
#
# This enhanced script handles the complete workflow from local validation to GitHub:
# 1. Environment setup and validation with thorough uv checks
# 2. YAML validation with comprehensive workflow checking (skippable with --skip-linters)
# 3. Testing and code quality checks (skippable with --skip-tests)
# 4. GitHub repository creation (if needed)
# 5. Secret configuration (if needed)
# 6. Committing changes (if needed)
# 7. Pushing to GitHub
# 8. DYNAMIC WORKFLOW TRIGGERING - detects and triggers workflows even if no changes were made
# 9. Optional waiting for workflow logs with new --wait-for-logs option
# 10. Release management
#
# It's designed to handle various scenarios:
# - First-time setup
# - Continuing an interrupted push
# - Regular updates to an existing repo
# - Automatic workflow discovery and triggering
# - Multi-method workflow triggering with fallbacks
# - Adding workflow_dispatch triggers if missing
# - Failure recovery with clear diagnostics

# All color variables, print_* functions, and check_command function 
# are sourced from publish_common.sh

# Display help information
show_help() {
    # Use ANSI colors for better readability
    cat << EOF
${BOLD}USAGE:${NC} 
    ${GREEN}./publish_to_github.sh --skip-tests${NC} [options]

${BOLD}${RED}!!! CRITICAL USAGE NOTE !!!${NC}
    ${BOLD}You MUST use the --skip-tests flag${NC} to ensure GitHub workflows run properly.
    Tests will still run on GitHub, but using this flag ensures proper workflow triggering.
    
${BOLD}DESCRIPTION:${NC}
    Enhanced GitHub publishing tool for the enchant-cli project with dynamic workflow 
    detection and multi-method triggering capabilities. This script handles all aspects 
    of GitHub integration including YAML validation, workflow detection, repository
    creation, and automatic workflow triggering.

    This is the ${BOLD}ONLY${NC} supported method for pushing code to GitHub. Direct git
    pushes should NOT be used, as this script ensures proper workflow triggering
    and environment validation.

${BOLD}OPTIONS:${NC}
    -h, --help         Show this help message and exit
    ${BOLD}--skip-tests${NC}       ${GREEN}REQUIRED FLAG${NC} - Skip running tests locally (they will run on GitHub)
    --skip-linters     Skip running linters/YAML validation (use with caution)
    --force            Force push to repository (use with extreme caution)
    --dry-run          Execute all steps except final GitHub push
    --verify-pypi      Check if the package is available on PyPI after publishing
    --check-version VER  Check if a specific version is available on PyPI (implies --verify-pypi)
    --wait-for-logs    Wait for workflow logs after pushing to GitHub (60s max)

${BOLD}REQUIRED WORKFLOW:${NC}
    1. Make your code changes
    2. Run: ${GREEN}./publish_to_github.sh --skip-tests${NC}
    3. The script will automatically:
       - Validate environment with enhanced uv checks
       - Validate YAML files with enhanced workflow detection
       - Push changes to GitHub
       - Automatically trigger all workflows without manual intervention
       - Verify that workflows are running
       - Optionally wait for and display workflow logs (with --wait-for-logs)
    4. Workflows will run on GitHub (even though they were skipped locally)

${BOLD}REQUIREMENTS:${NC}
    - GitHub CLI (gh) must be installed
        Install from: https://cli.github.com/manual/installation
    - GitHub CLI must be authenticated 
        Run 'gh auth login' if not already authenticated
    - uv package manager
        Install from: https://github.com/astral-sh/uv#installation

${BOLD}DETAILED SCENARIOS:${NC}
    1. First-time repository setup:
       ${GREEN}./publish_to_github.sh --skip-tests${NC}
       (Will create repo, configure secrets, push code, and trigger workflows)

    2. Regular update to existing repository:
       ${GREEN}./publish_to_github.sh --skip-tests${NC}
       (Will commit changes, validate YAML, push to GitHub, and trigger workflows)

    3. Creating a release:
       ${GREEN}./publish_to_github.sh --skip-tests${NC}
       (Then follow instructions to create a GitHub Release)

    4. Monitoring workflow execution:
       ${GREEN}./publish_to_github.sh --skip-tests --wait-for-logs${NC}
       (Will wait for workflow logs and display any errors)

${BOLD}ENVIRONMENT VARIABLES:${NC}
    The script automatically checks and configures required secrets:
    - OPENROUTER_API_KEY: Required for translation API
    - CODECOV_API_TOKEN: Required for code coverage reporting
    - PYPI_API_TOKEN: Required for PyPI publishing (via OIDC trusted publishing)

${BOLD}EXAMPLES:${NC}
    ${GREEN}./publish_to_github.sh --skip-tests${NC}          # RECOMMENDED usage
    ./publish_to_github.sh --help                # Show this help message
    ${GREEN}./publish_to_github.sh --skip-tests${NC} --skip-linters  # Skip both tests and YAML validation
    ${GREEN}./publish_to_github.sh --skip-tests${NC} --verify-pypi # Check latest package on PyPI after publishing
    ${GREEN}./publish_to_github.sh --skip-tests${NC} --wait-for-logs # Wait for workflow logs after pushing

For more information, see: CLAUDE.md
EOF
    exit 0
}

# Process command-line options
SKIP_TESTS=0
SKIP_LINTERS=0
FORCE_PUSH=0
DRY_RUN=0
VERIFY_PYPI=0
WAIT_FOR_LOGS=0
SPECIFIC_VERSION=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        -h|--help)
            show_help
            ;;
        --skip-tests)
            SKIP_TESTS=1
            shift
            ;;
        --skip-linters)
            SKIP_LINTERS=1
            shift
            ;;
        --force)
            FORCE_PUSH=1
            shift
            ;;
        --dry-run)
            DRY_RUN=1
            shift
            ;;
        --verify-pypi)
            VERIFY_PYPI=1
            shift
            ;;
        --wait-for-logs)
            WAIT_FOR_LOGS=1
            shift
            ;;
        --check-version)
            if [[ -z "$2" || "$2" == -* ]]; then
                print_error "--check-version requires a version argument" 1
                show_help
            fi
            SPECIFIC_VERSION="$2"
            VERIFY_PYPI=1
            shift 2
            ;;
        *)
            print_error "Unknown option: $1" 1
            show_help
            ;;
    esac
done

# === Execute steps ===
STEPS=(
  env_prep yaml_validate repo_status local_checks env_verify
  push_part1 push_part2
  wf_detect_1 wf_detect_2
  wf_trigger_1 wf_trigger_verify
  final_notes
)
for step in "${STEPS[@]}"; do
  print_step "Running $step ..."
  "${SCRIPT_DIR}/publish_${step}.sh" "$@" || { print_error "Step $step failed." 1; }
done
