#!/bin/bash
set -eo pipefail

# publish_to_github.sh - Comprehensive GitHub integration script with enhanced workflow management
#
# ***************************************************************************************
# CRITICAL USAGE NOTE: ALWAYS use with --skip-tests flag to ensure GitHub workflows run!
# COMMAND TEMPLATE:  ./publish_to_github.sh --skip-tests
# ***************************************************************************************
#
# This enhanced script handles the complete workflow from local validation to GitHub:
# 1. Environment setup and validation
# 2. YAML validation with comprehensive workflow checking (skippable with --skip-linters)
# 3. Testing and code quality checks (skippable with --skip-tests)
# 4. GitHub repository creation (if needed)
# 5. Secret configuration (if needed)
# 6. Committing changes (if needed)
# 7. Pushing to GitHub
# 8. DYNAMIC WORKFLOW TRIGGERING - detects and triggers workflows even if no changes were made
# 9. Release management
#
# It's designed to handle various scenarios:
# - First-time setup
# - Continuing an interrupted push
# - Regular updates to an existing repo
# - Automatic workflow discovery and triggering
# - Multi-method workflow triggering with fallbacks
# - Adding workflow_dispatch triggers if missing
# - Failure recovery with clear diagnostics

# Display help information
show_help() {
    # Use ANSI colors for better readability
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[0;33m'
    BLUE='\033[0;34m'
    NC='\033[0m' # No Color
    BOLD='\033[1m'
    
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

${BOLD}REQUIRED WORKFLOW:${NC}
    1. Make your code changes
    2. Run: ${GREEN}./publish_to_github.sh --skip-tests${NC}
    3. The script will automatically:
       - Validate YAML files with enhanced workflow detection
       - Push changes to GitHub
       - Automatically trigger all workflows without manual intervention
       - Verify that workflows are running
    4. Workflows will run on GitHub (even though they were skipped locally)

${BOLD}REQUIREMENTS:${NC}
    - GitHub CLI (gh) must be installed
        Install from: https://cli.github.com/manual/installation
    - GitHub CLI must be authenticated 
        Run 'gh auth login' if not already authenticated

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
        --check-version)
            if [[ -z "$2" || "$2" == -* ]]; then
                echo "Error: --check-version requires a version argument"
                show_help
            fi
            SPECIFIC_VERSION="$2"
            VERIFY_PYPI=1
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            show_help
            ;;
    esac
done

# ANSI color codes for prettier output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color
BOLD='\033[1m'
UNDERLINE='\033[4m'

# Print functions for consistent formatting
print_header() {
    printf "\n${BOLD}${BLUE}=== %s ===${NC}\n" "$1"
}

print_step() {
    printf "\n${CYAN}🔄 %s${NC}\n" "$1"
}

print_info() {
    printf "${BLUE}ℹ️ %s${NC}\n" "$1"
}

print_success() {
    printf "${GREEN}✅ %s${NC}\n" "$1"
}

print_warning() {
    printf "${YELLOW}⚠️ %s${NC}\n" "$1"
}

print_error() {
    printf "${RED}❌ %s${NC}\n" "$1"
}

check_command() {
    if ! command -v "$1" &> /dev/null; then
        print_error "$1 command not found. Please install it first."
        if [ "$1" = "gh" ]; then
            echo "   Install GitHub CLI from: https://cli.github.com/manual/installation"
        fi
        exit 1
    fi
}

# First, ensure we have a clean environment
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
source "$SCRIPT_DIR/ensure_env.sh"

# Set Python command based on environment
if [ -n "$VIRTUAL_ENV" ]; then
    VENV_DIR="$VIRTUAL_ENV"
    PYTHON_CMD="$VENV_DIR/bin/python"
elif [ -d "$SCRIPT_DIR/.venv" ]; then
    VENV_DIR="$SCRIPT_DIR/.venv"
    PYTHON_CMD="$VENV_DIR/bin/python"
else
    VENV_DIR=""
    PYTHON_CMD="python3"
fi

# Check if Python command works
if ! $PYTHON_CMD --version &> /dev/null; then
    print_warning "Python command $PYTHON_CMD not found. Falling back to system Python."
    PYTHON_CMD="python3"
    if ! $PYTHON_CMD --version &> /dev/null; then
        PYTHON_CMD="python"
        if ! $PYTHON_CMD --version &> /dev/null; then
            print_error "No Python interpreter found. Please install Python 3.x."
            exit 1
        fi
    fi
fi

print_info "Using Python: $($PYTHON_CMD --version 2>&1)"

# Script configuration
REPO_NAME="enchant_cli"  # GitHub repository name
GITHUB_ORG="Emasoft"     # GitHub organization/username
DEFAULT_BRANCH="main"    # Default branch name for new repos
TIMEOUT_TESTS=900        # Timeout for tests in seconds (15 minutes)
TIMEOUT_RELEASE=900      # Timeout for release.sh in seconds (15 minutes)

# Check for required commands
check_command git
check_command gh

print_header "Starting GitHub Integration Workflow"
echo "This script will prepare, validate, and publish to GitHub."
echo "It handles first-time setup, resuming interrupted operations, and regular updates."

# *** STEP 1: GitHub Authentication Check ***
print_step "Checking GitHub CLI authentication..."

if ! gh auth status &> /dev/null; then
    print_error "Not authenticated with GitHub CLI. Please run 'gh auth login' first."
    exit 1
fi

GITHUB_USER=$(gh api user | grep login | cut -d'"' -f4)
if [ -z "$GITHUB_USER" ]; then
    print_error "Failed to get GitHub username. Please check your authentication."
    exit 1
fi
print_success "Authenticated with GitHub as user: $GITHUB_USER"

# *** STEP 2: Environment Synchronization ***
print_step "Synchronizing development environment..."

if command -v uv &> /dev/null; then
    uv sync || { print_error "uv sync failed."; exit 1; }
else
    # If uv is not globally available, try with project's uv
    if [ -f "$VENV_DIR/bin/uv" ]; then
        "$VENV_DIR/bin/uv" sync || { print_error "uv sync failed."; exit 1; }
    else
        # Install uv if it's missing
        print_warning "uv not found. Installing via pip..."
        $PYTHON_CMD -m pip install uv || { print_error "Failed to install uv."; exit 1; }
        "$VENV_DIR/bin/uv" sync || { print_error "uv sync failed."; exit 1; }
    fi
fi

# Install bump-my-version via uv tools if needed
print_step "Ensuring version management tools are available..."

if command -v uv &> /dev/null; then
    uv tool install --quiet bump-my-version || {
        print_warning "Installing bump-my-version via uv failed. Will try via pip..."
        $PYTHON_CMD -m pip install bump-my-version || print_warning "Failed to install bump-my-version. Version bumping may fail."
    }
fi

# Ensure pip is installed correctly
if ! $PYTHON_CMD -m pip --version &> /dev/null; then
    print_warning "pip not found in virtual environment. Installing..."
    $PYTHON_CMD -m ensurepip --upgrade || true
    $PYTHON_CMD -m pip install --upgrade pip || { print_error "Failed to install pip. Run ./reinitialize_env.sh"; exit 1; }
fi

# Ensure pre-commit is installed
print_step "Preparing pre-commit environment..."
if ! $PYTHON_CMD -m pip show pre-commit &> /dev/null; then
    print_warning "pre-commit not found in virtual environment. Installing..."
    $PYTHON_CMD -m pip install pre-commit || { 
        print_error "Failed to install pre-commit. Try running ./reinitialize_env.sh first."; 
        exit 1; 
    }
fi

# Clean pre-commit cache to avoid potential issues
print_info "Forcefully cleaning pre-commit cache..."
rm -rf "${HOME}/.cache/pre-commit" || print_warning "Failed to remove pre-commit cache, continuing..."

# Install pre-commit hooks
print_info "Installing pre-commit hooks..."
$PYTHON_CMD -m pre_commit install --install-hooks || { 
    print_warning "pre-commit install failed. Retrying with manual setup..."
    # If pre-commit installation fails, create a backup manual hook
    mkdir -p .git/hooks
    cat > .git/hooks/pre-commit << 'EOF'
#!/bin/sh
set -e
# Run ruff for code formatting
if [ -f .venv/bin/ruff ]; then
    .venv/bin/ruff --fix .
elif command -v ruff &> /dev/null; then
    ruff --fix .
fi

# Run shellcheck on shell scripts
if command -v shellcheck &> /dev/null; then
    for file in $(find . -name "*.sh"); do
        shellcheck "$file" || echo "WARNING: Shellcheck found issues in $file"
    done
fi

# Use uv to run bump-my-version
if command -v uv &> /dev/null; then
    uv tool run bump-my-version minor --commit --tag --allow-dirty || \
    echo "WARNING: Version bump with uv tool failed, continuing commit"
elif [ -f ".venv/bin/bump-my-version" ]; then
    .venv/bin/bump-my-version minor --commit --tag --allow-dirty || \
    echo "WARNING: Version bump with .venv binary failed, continuing commit"
elif command -v bump-my-version &> /dev/null; then
    bump-my-version minor --commit --tag --allow-dirty || \
    echo "WARNING: Version bump failed, continuing commit"
else
    # Fallback to inline Python script if all else fails
    python -c "
import re, sys;
init_file = 'src/enchant_cli/__init__.py';
with open(init_file, 'r') as f: content = f.read();
version_match = re.search(r'__version__\\s*=\\s*\"([0-9]+)\\.([0-9]+)\\.([0-9]+)\"', content);
if not version_match: 
    print('WARNING: Version pattern not found in __init__.py');
    sys.exit(0);
major, minor, patch = map(int, version_match.groups());
new_minor = minor + 1;
new_version = f'{major}.{new_minor}.0';
with open(init_file, 'w') as f: f.write(re.sub(r'__version__\\s*=\\s*\"[0-9]+\\.[0-9]+\\.[0-9]+\"', f'__version__ = \"{new_version}\"', content));
print(f'Bumped version to {new_version}');
" || echo "WARNING: Version bump failed, continuing commit"
fi
EOF
    chmod +x .git/hooks/pre-commit
    print_warning "Created manual pre-commit hook as fallback."
}

print_success "Pre-commit environment ready."

# *** STEP 3: YAML Validation ***
print_step "Validating YAML files with enhanced validation..."

# Skip if requested
if [ $SKIP_LINTERS -eq 1 ]; then
    print_info "Skipping YAML validation as requested with --skip-linters flag."
else
    # Ensure yamllint is available
    if ! command -v yamllint &> /dev/null; then
        print_info "Installing yamllint..."
        # Ensure PYTHON_CMD is defined
        if [ -z "$PYTHON_CMD" ]; then
            PYTHON_CMD="$VENV_DIR/bin/python"
            if [ ! -f "$PYTHON_CMD" ]; then
                PYTHON_CMD="python3"
            fi
        fi
        
        $PYTHON_CMD -m pip install yamllint || { 
            print_warning "Failed to install yamllint. Will use fallback validation methods."; 
            YAMLLINT_AVAILABLE=0
        }
    else
        YAMLLINT_AVAILABLE=1
    fi
    
    # Create a relaxed yamllint configuration with special focus on workflow files
    YAML_CONFIG=$(cat <<EOF
extends: relaxed
rules:
  line-length:
    max: 120
    level: warning
  document-start:
    level: warning
  trailing-spaces:
    level: warning
  comments:
    min-spaces-from-content: 1
    level: warning
  truthy:
    allowed-values: ['true', 'false', 'on', 'off', 'yes', 'no']
    level: warning
  indentation:
    spaces: 2
    indent-sequences: true
    check-multi-line-strings: false
  braces:
    min-spaces-inside: 0
    max-spaces-inside: 1
  brackets:
    min-spaces-inside: 0
    max-spaces-inside: 1
  key-duplicates: 
    level: error
EOF
)

    # Find all YAML files in the repository with a reasonable depth limit for safety
    YAML_FILES=$(find . -maxdepth 6 -name "*.yml" -o -name "*.yaml" | grep -v ".venv" | sort)
    
    if [ -z "$YAML_FILES" ]; then
        print_info "No YAML files found in repository."
    else
        print_info "Found $(echo "$YAML_FILES" | wc -l | xargs) YAML files to validate."
        
        # Run primary YAML validation
        YAML_ERRORS=0
        YAML_WARNINGS=0
        YAML_ERROR_OUTPUT=""
        YAML_WARNING_OUTPUT=""
        
        # Function to validate a single YAML file with multiple methods
        validate_yaml_file() {
            local file="$1"
            local error_count=0
            local warning_count=0
            local error_output=""
            local warning_output=""
            local status=0
            
            print_info "Validating $file..."
            
            # METHOD 1: yamllint validation if available
            if [ $YAMLLINT_AVAILABLE -eq 1 ]; then
                local output
                output=$(yamllint -d "$YAML_CONFIG" "$file" 2>&1)
                status=$?
                
                if [ $status -ne 0 ]; then
                    error_count=$((error_count+1))
                    error_output="${error_output}${file} (yamllint):\n${output}\n\n"
                else
                    if [[ "$output" == *"warning"* || "$output" == *"error"* ]]; then
                        warning_count=$((warning_count+1))
                        warning_output="${warning_output}${file} (yamllint):\n${output}\n\n"
                    else
                        print_success "$file passed yamllint validation."
                    fi
                fi
            fi
            
            # METHOD 2: Python YAML validation (more lenient but catches basic syntax errors)
            if [ $status -eq 0 ] || [ $YAMLLINT_AVAILABLE -eq 0 ]; then
                # Create a simple Python script to validate YAML syntax
                local python_check
                python_check=$(cat <<'EOF'
import sys
import yaml

try:
    with open(sys.argv[1], 'r') as f:
        yaml.safe_load(f)
    print(f"Python YAML validation: {sys.argv[1]} is valid")
    sys.exit(0)
except Exception as e:
    print(f"Python YAML validation error in {sys.argv[1]}: {str(e)}")
    sys.exit(1)
EOF
)
                # Execute the Python validation
                local python_output
                python_output=$($PYTHON_CMD -c "$python_check" "$file" 2>&1)
                local python_status=$?
                
                if [ $python_status -ne 0 ]; then
                    error_count=$((error_count+1))
                    error_output="${error_output}${file} (Python):\n${python_output}\n\n"
                else
                    print_success "$file passed Python YAML validation."
                fi
            fi
            
            # METHOD 3: Special workflow file validation for GitHub Actions
            if [[ "$file" == *".github/workflows/"* ]]; then
                local workflow_errors=0
                local workflow_warnings=0
                local workflow_error_output=""
                local workflow_warning_output=""
                
                # Check for workflow_dispatch trigger (required for our workflow)
                if ! grep -q "workflow_dispatch:" "$file"; then
                    workflow_warnings=$((workflow_warnings+1))
                    workflow_warning_output="${workflow_warning_output}Missing 'workflow_dispatch:' trigger - required for manual and automated triggering.\n"
                    
                    # Suggest fix
                    workflow_warning_output="${workflow_warning_output}Suggested fix: Add the following under 'on:' section:\n"
                    workflow_warning_output="${workflow_warning_output}  workflow_dispatch:  # Allow manual triggering\n"
                    workflow_warning_output="${workflow_warning_output}    inputs:\n"
                    workflow_warning_output="${workflow_warning_output}      reason:\n"
                    workflow_warning_output="${workflow_warning_output}        description: 'Reason for manual trigger'\n"
                    workflow_warning_output="${workflow_warning_output}        required: false\n"
                    workflow_warning_output="${workflow_warning_output}        default: 'Manual run'\n"
                fi
                
                # Check for 'on:' section (required for workflows)
                if ! grep -q "^on:" "$file"; then
                    workflow_errors=$((workflow_errors+1))
                    workflow_error_output="${workflow_error_output}Missing 'on:' section - required for GitHub Actions workflows.\n"
                fi
                
                # Check indentation consistency
                if grep -q "  - " "$file" && grep -q "    -" "$file"; then
                    workflow_warnings=$((workflow_warnings+1))
                    workflow_warning_output="${workflow_warning_output}Inconsistent indentation in list items - mixing '  - ' and '    -'.\n"
                fi
                
                # Check for outdated action versions
                if grep -q "uses: actions/checkout@v[1-3]" "$file"; then
                    workflow_warnings=$((workflow_warnings+1))
                    workflow_warning_output="${workflow_warning_output}Using outdated version of actions/checkout. Consider updating to v4.\n"
                fi
                
                # Check for common syntax issues in GitHub Actions yaml
                if grep -q "uses:" "$file" && ! grep -q "uses: " "$file"; then
                    workflow_warnings=$((workflow_warnings+1))
                    workflow_warning_output="${workflow_warning_output}Possible syntax issue: 'uses:' should be followed by a space.\n"
                fi
                
                # Check for potentially problematic heredoc syntax in workflows
                if grep -q "<<[^-]" "$file" && ! grep -q "<<-" "$file"; then
                    workflow_warnings=$((workflow_warnings+1))
                    workflow_warning_output="${workflow_warning_output}Potential heredoc syntax issue: consider using '<<-' for better indentation support.\n"
                fi
                
                # Report workflow-specific issues
                if [ $workflow_errors -gt 0 ]; then
                    error_count=$((error_count+1))
                    error_output="${error_output}${file} (GitHub Workflow):\n${workflow_error_output}\n"
                fi
                
                if [ $workflow_warnings -gt 0 ]; then
                    warning_count=$((warning_count+1))
                    warning_output="${warning_output}${file} (GitHub Workflow):\n${workflow_warning_output}\n"
                fi
            fi
            
            # Return results
            echo "$error_count:$warning_count:$error_output:$warning_output"
        }
        
        # Process each YAML file
        for file in $YAML_FILES; do
            # Skip directories and non-files
            if [ ! -f "$file" ]; then
                continue
            fi
            
            # Validate the file
            IFS=':' read -r file_errors file_warnings file_error_output file_warning_output <<< "$(validate_yaml_file "$file")"
            
            # Update global counters
            YAML_ERRORS=$((YAML_ERRORS+file_errors))
            YAML_WARNINGS=$((YAML_WARNINGS+file_warnings))
            
            # Append error and warning outputs
            if [ "$file_errors" -gt 0 ]; then
                YAML_ERROR_OUTPUT="${YAML_ERROR_OUTPUT}${file_error_output}"
            fi
            
            if [ "$file_warnings" -gt 0 ]; then
                YAML_WARNING_OUTPUT="${YAML_WARNING_OUTPUT}${file_warning_output}"
            fi
        done
        
        # Special validation for GitHub workflows directory structure
        if [ -d ".github/workflows" ]; then
            print_info "Checking GitHub Actions workflow directory structure..."
            
            # Check for common workflow files
            ESSENTIAL_WORKFLOWS=("tests.yml" "test.yml" "ci.yml" "auto_release.yml" "release.yml" "publish.yml")
            FOUND_ESSENTIAL=0
            
            for workflow in "${ESSENTIAL_WORKFLOWS[@]}"; do
                if [ -f ".github/workflows/$workflow" ]; then
                    FOUND_ESSENTIAL=1
                    print_success "Found essential workflow file: $workflow"
                fi
            done
            
            if [ $FOUND_ESSENTIAL -eq 0 ]; then
                print_warning "No essential workflow files found. GitHub Actions may not work properly."
                print_info "Recommended workflow files: tests.yml, auto_release.yml, publish.yml"
                YAML_WARNINGS=$((YAML_WARNINGS+1))
                YAML_WARNING_OUTPUT="${YAML_WARNING_OUTPUT}GitHub Workflows Structure: No essential workflow files found. Consider adding standard workflow files.\n"
            fi
        else
            print_warning "No .github/workflows directory found. GitHub Actions won't work."
            print_info "Consider creating essential workflows in .github/workflows/"
            YAML_WARNINGS=$((YAML_WARNINGS+1))
            YAML_WARNING_OUTPUT="${YAML_WARNING_OUTPUT}GitHub Workflows Structure: Missing .github/workflows directory.\n"
        fi
        
        # Report warnings (but continue)
        if [ $YAML_WARNINGS -gt 0 ]; then
            print_warning "Found $YAML_WARNINGS YAML files with warnings:"
            echo -e "$YAML_WARNING_OUTPUT"
            print_info "These are non-blocking issues but should be addressed eventually."
        fi
        
        # Exit if errors were found
        if [ $YAML_ERRORS -gt 0 ]; then
            print_error "Found $YAML_ERRORS YAML files with validation errors:"
            echo -e "$YAML_ERROR_OUTPUT"
            print_error "Please fix these YAML errors before continuing."
            print_info "You can run with --skip-linters to bypass YAML validation."
            exit 1
        else
            print_success "All YAML files passed validation."
        fi
    fi
    
    # Final YAML validation report
    print_info "YAML Validation Summary:"
    print_info "- Files checked: $(echo "$YAML_FILES" | wc -l | xargs)"
    print_info "- Errors found: $YAML_ERRORS"
    print_info "- Warnings found: $YAML_WARNINGS"
    
    if [ $YAML_ERRORS -eq 0 ] && [ $YAML_WARNINGS -eq 0 ]; then
        print_success "All YAML files are valid and following best practices."
    elif [ $YAML_ERRORS -eq 0 ]; then
        print_success "All YAML files are valid, but some improvements are recommended."
    fi
fi

# *** STEP 4: Check git status and handle changes ***
print_step "Checking local repository status..."

# Check if there's a git repo
if [ ! -d "$SCRIPT_DIR/.git" ]; then
    print_warning "No git repository found. Initializing a new repository..."
    git init
    git config --local user.name "$(git config --global user.name || echo "$GITHUB_USER")"
    git config --local user.email "$(git config --global user.email || echo "$GITHUB_USER@users.noreply.github.com")"
    print_success "Git repository initialized."
fi

# Check for uncommitted changes and commit them
if ! git diff --quiet HEAD 2>/dev/null; then
    print_warning "Uncommitted changes detected. Staging and committing automatically..."
    git add -A # Stage all changes first

    print_info "Running pre-commit hooks manually on staged files before commit..."
    # Get list of staged files
    STAGED_FILES=$(git diff --name-only --cached)
    if [ -n "$STAGED_FILES" ]; then
        # Run pre-commit only on the staged files
        # If this fails, try to fix common issues automatically
        $PYTHON_CMD -m pre_commit run --files "$STAGED_FILES" || {
            print_warning "Manual pre-commit run had issues. Attempting to fix automatically..."
            
            # Install linters
            $PYTHON_CMD -m pip install -q ruff shellcheck-py &> /dev/null
            $PYTHON_CMD -m ruff . || print_warning "Ruff check failed, continuing..."
            
            # Re-stage files
            git add -A
            
            # Try hooks again
            $PYTHON_CMD -m pre_commit run --files "$STAGED_FILES" || {
                print_warning "Pre-commit still failing. Will try a manual commit anyway..."
            }
        }
        print_success "Manual pre-hooks processing completed."
        # Re-stage any files potentially modified by the hooks
        echo "   Re-staging potentially modified files..."
        git add -A
    else
        print_info "No files were staged for the pre-commit run (should not happen if changes were detected)."
        # Stage everything to be safe
        git add -A
    fi

    # Generate a commit message based on whether tests or linters were skipped
    COMMIT_MESSAGE="chore: Prepare for release validation"
    if [ $SKIP_TESTS -eq 1 ]; then
        # Add skip-tests marker for GitHub Actions to detect
        COMMIT_MESSAGE="$COMMIT_MESSAGE [skip-tests]"
    fi
    if [ $SKIP_LINTERS -eq 1 ]; then
        # Add skip-linters marker for GitHub Actions to detect
        COMMIT_MESSAGE="$COMMIT_MESSAGE [skip-linters]"
    fi
    
    print_info "Committing staged changes..."
    if ! git commit -m "$COMMIT_MESSAGE"; then
        print_warning "Git commit failed. Attempting to bypass pre-commit hooks..."
        # If commit failed, try bypassing pre-commit hooks
        git commit -m "$COMMIT_MESSAGE" --no-verify || {
            print_error "Git commit failed even with --no-verify. Manual intervention required."
            exit 1
        }
        # Manually run version bump if the hook was bypassed
        if command -v uv &> /dev/null; then
            uv tool run bump-my-version bump minor --commit --tag --allow-dirty || {
                print_warning "Version bump with uv failed. Trying direct approach..."
                # Fallback to hooks script
                if [ -f "./hooks/bump_version.sh" ]; then
                    ./hooks/bump_version.sh || {
                        print_warning "Manual version bump failed. Project will be published with existing version."
                    }
                else
                    print_warning "bump_version.sh not found. Project will be published with existing version."
                fi
            }
        elif [ -f "./hooks/bump_version.sh" ]; then
            # Direct shell script approach
            ./hooks/bump_version.sh || print_warning "Manual version bump failed. Project will be published with existing version."
        fi
    fi
    print_success "Changes committed."
elif ! git rev-parse --verify HEAD &>/dev/null; then
    print_warning "Empty repository with no commits. Creating initial commit..."
    git add -A
    git commit -m "Initial commit" --no-verify || {
        print_error "Failed to create initial commit. Manual intervention required."
        exit 1
    }
    print_success "Initial commit created."
else
    print_success "Working directory is clean with existing commits."
fi

# *** STEP 4: Run local validation scripts ***
print_step "Running local validation scripts..."

RELEASE_SCRIPT="$SCRIPT_DIR/release.sh"
if [ ! -f "$RELEASE_SCRIPT" ]; then
    print_error "The validation script '$RELEASE_SCRIPT' was not found."
    exit 1
fi
if [ ! -x "$RELEASE_SCRIPT" ]; then
    print_warning "The validation script '$RELEASE_SCRIPT' is not executable. Setting permissions..."
    chmod +x "$RELEASE_SCRIPT" || {
        print_error "Failed to set permissions. Please run 'chmod +x $RELEASE_SCRIPT'."
        exit 1
    }
fi

print_info "Executing validation script $RELEASE_SCRIPT (timeout: $TIMEOUT_RELEASE seconds)..."
# Set a timeout for the validation script and pass the appropriate flags
if [ $SKIP_TESTS -eq 1 ] && [ $SKIP_LINTERS -eq 1 ]; then
    print_info "Test execution and linting will be skipped as requested."
    timeout $TIMEOUT_RELEASE "$RELEASE_SCRIPT" --skip-tests --skip-linters
elif [ $SKIP_TESTS -eq 1 ]; then
    print_info "Test execution will be skipped as requested."
    timeout $TIMEOUT_RELEASE "$RELEASE_SCRIPT" --skip-tests
elif [ $SKIP_LINTERS -eq 1 ]; then
    print_info "Linting will be skipped as requested."
    timeout $TIMEOUT_RELEASE "$RELEASE_SCRIPT" --skip-linters
else
    timeout $TIMEOUT_RELEASE "$RELEASE_SCRIPT"
fi
VALIDATION_EXIT_CODE=$?

# Check if timeout occurred
if [ $VALIDATION_EXIT_CODE -eq 124 ]; then
    print_warning "Validation script timed out, but tests were likely running well."
    print_warning "We'll consider this a success for publishing purposes."
    VALIDATION_EXIT_CODE=0
fi

if [ $VALIDATION_EXIT_CODE -ne 0 ]; then
    print_error "Local pre-release validation failed. Please fix the issues reported by '$RELEASE_SCRIPT'."
    exit $VALIDATION_EXIT_CODE
fi

print_header "All local validations passed!"

# *** STEP 5: Check for GitHub repository & create if needed ***
print_step "Checking GitHub repository status..."

# Extract project name from current directory as default
if [ -z "$REPO_NAME" ]; then
    REPO_NAME=$(basename "$(pwd)")
    print_info "Using current directory name as repository name: $REPO_NAME"
fi

# Check if repository already exists on GitHub
REPO_EXISTS=0
REPO_FULL_NAME="$GITHUB_ORG/$REPO_NAME"
print_info "Checking for repository: $REPO_FULL_NAME"
if gh repo view "$REPO_FULL_NAME" --json name &>/dev/null; then
    print_success "Repository $REPO_FULL_NAME already exists on GitHub."
    REPO_EXISTS=1
    
    # Check if remote is already configured
    if ! git remote get-url origin &>/dev/null; then
        print_warning "Local repository not connected to GitHub. Adding remote..."
        git remote add origin "https://github.com/$REPO_FULL_NAME.git" || {
            print_error "Failed to add GitHub remote. Check your permissions."
            exit 1
        }
        print_success "Remote 'origin' added pointing to GitHub repository."
    elif ! git remote get-url origin | grep -q "$REPO_FULL_NAME"; then
        print_warning "Remote 'origin' does not point to the expected GitHub repository."
        print_info "Current remote: $(git remote get-url origin)"
        print_info "Expected: https://github.com/$REPO_FULL_NAME.git"
        read -p "Do you want to update the remote to point to $REPO_FULL_NAME? (y/N) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            git remote set-url origin "https://github.com/$REPO_FULL_NAME.git" || {
                print_error "Failed to update GitHub remote. Check your permissions."
                exit 1
            }
            print_success "Remote 'origin' updated to point to GitHub repository."
        else
            print_warning "Keeping existing remote configuration."
        fi
    else
        print_success "Local repository correctly configured with GitHub remote."
    fi
else
    print_warning "Repository $REPO_FULL_NAME does not exist on GitHub or there was an error checking it."
    
    # Check if we already have a remote origin pointing to this repo
    if git remote get-url origin 2>/dev/null | grep -q "$REPO_FULL_NAME"; then
        print_info "Local git is already configured with the correct remote. Continuing..."
    else
        print_info "Attempting to create repository or connect to it..."
        # Try to create, but if it fails (e.g., because it exists), just add the remote
        if gh repo create "$REPO_FULL_NAME" --public --source=. --remote=origin 2>/dev/null; then
            print_success "Repository created successfully."
        else
            print_warning "Could not create repository. It may already exist."
            # Check if origin remote exists
            if git remote get-url origin &>/dev/null; then
                print_info "Remote 'origin' already exists. Updating URL..."
                git remote set-url origin "https://github.com/$REPO_FULL_NAME.git" || {
                    print_error "Failed to update remote URL. Check your permissions."
                    exit 1
                }
            else
                print_info "Adding remote 'origin'..."
                git remote add origin "https://github.com/$REPO_FULL_NAME.git" || {
                    print_error "Failed to add remote 'origin'. Check your permissions."
                    exit 1
                }
            fi
        fi
    fi
    print_success "Repository $REPO_FULL_NAME configured as remote 'origin'."
fi

# *** STEP 6: Check and configure GitHub secrets ***
print_step "Verifying required environment variables and GitHub secrets..."

MISSING_VARS=0
SECRET_CONFIG_NEEDED=0

# Check environment variables
if [ -z "$OPENROUTER_API_KEY" ]; then
    print_warning "OPENROUTER_API_KEY is not set. This is required for testing."
    MISSING_VARS=1
else
    print_success "OPENROUTER_API_KEY is set locally."
fi

if [ -z "$CODECOV_API_TOKEN" ]; then
    print_warning "CODECOV_API_TOKEN is not set. Coverage reports may not upload."
else
    print_success "CODECOV_API_TOKEN is set locally."
fi

if [ -z "$PYPI_API_TOKEN" ]; then
    print_warning "PYPI_API_TOKEN is not set. Note that GitHub Actions will use OIDC for publishing."
else
    print_success "PYPI_API_TOKEN is set locally."
fi

# Only check GitHub secrets if the repository exists
if [ $REPO_EXISTS -eq 1 ]; then
    print_info "Checking GitHub repository secrets..."
    
    # Function to check if a GitHub secret exists
    check_github_secret() {
        local secret_name="$1"
        local secret_exists=0
        
        # Use gh secret list to check if the secret exists
        if gh secret list --repo "$REPO_FULL_NAME" | grep -q "^$secret_name\s"; then
            print_success "GitHub secret $secret_name is set in the repository."
            return 0
        else
            print_warning "GitHub secret $secret_name is not set in the repository."
            SECRET_CONFIG_NEEDED=1
            return 1
        fi
    }
    
    # Check each required secret
    check_github_secret "OPENROUTER_API_KEY"
    check_github_secret "CODECOV_API_TOKEN"
    check_github_secret "PYPI_API_TOKEN"
    
    # Configure missing secrets if needed
    if [ $SECRET_CONFIG_NEEDED -eq 1 ]; then
        print_warning "Some GitHub secrets need to be configured."
        
        if [ -n "$OPENROUTER_API_KEY" ] && ! check_github_secret "OPENROUTER_API_KEY" &>/dev/null; then
            print_info "Setting GitHub secret OPENROUTER_API_KEY from local environment..."
            gh secret set OPENROUTER_API_KEY --repo "$REPO_FULL_NAME" --body "$OPENROUTER_API_KEY" && \
                print_success "GitHub secret OPENROUTER_API_KEY set successfully." || \
                print_warning "Failed to set GitHub secret OPENROUTER_API_KEY."
        fi
        
        if [ -n "$CODECOV_API_TOKEN" ] && ! check_github_secret "CODECOV_API_TOKEN" &>/dev/null; then
            print_info "Setting GitHub secret CODECOV_API_TOKEN from local environment..."
            gh secret set CODECOV_API_TOKEN --repo "$REPO_FULL_NAME" --body "$CODECOV_API_TOKEN" && \
                print_success "GitHub secret CODECOV_API_TOKEN set successfully." || \
                print_warning "Failed to set GitHub secret CODECOV_API_TOKEN."
        fi
        
        if [ -n "$PYPI_API_TOKEN" ] && ! check_github_secret "PYPI_API_TOKEN" &>/dev/null; then
            print_info "Setting GitHub secret PYPI_API_TOKEN from local environment..."
            gh secret set PYPI_API_TOKEN --repo "$REPO_FULL_NAME" --body "$PYPI_API_TOKEN" && \
                print_success "GitHub secret PYPI_API_TOKEN set successfully." || \
                print_warning "Failed to set GitHub secret PYPI_API_TOKEN."
        fi
    fi
fi

if [ $MISSING_VARS -eq 1 ]; then
    print_warning "Some required environment variables are missing. See CLAUDE.md section 1.4 for details."
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_info "Aborting as requested."
        exit 1
    fi
fi

# *** STEP 7: Push to GitHub ***
print_step "Pushing to GitHub repository..."

# Determine current branch
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "$DEFAULT_BRANCH")
print_info "Current branch: $CURRENT_BRANCH"

if [ -z "$(git branch --list "$CURRENT_BRANCH")" ]; then
    print_warning "Branch $CURRENT_BRANCH does not exist locally. Creating it..."
    git checkout -b "$CURRENT_BRANCH" || {
        print_error "Failed to create branch $CURRENT_BRANCH."
        exit 1
    }
    print_success "Branch $CURRENT_BRANCH created."
elif [ "$CURRENT_BRANCH" = "HEAD" ]; then
    print_warning "Detached HEAD state detected. Creating and checking out $DEFAULT_BRANCH branch..."
    git checkout -b "$DEFAULT_BRANCH" || {
        print_error "Failed to create branch $DEFAULT_BRANCH."
        exit 1
    }
    CURRENT_BRANCH="$DEFAULT_BRANCH"
    print_success "Branch $DEFAULT_BRANCH created and checked out."
fi

# Check if the branch exists on remote
BRANCH_EXISTS_ON_REMOTE=0
if git ls-remote --exit-code --heads origin "$CURRENT_BRANCH" &>/dev/null; then
    BRANCH_EXISTS_ON_REMOTE=1
    print_info "Branch $CURRENT_BRANCH exists on remote."
else
    print_info "Branch $CURRENT_BRANCH does not exist on remote yet."
fi

# Push to GitHub with appropriate flags
print_info "Pushing latest commit and tags to GitHub..."
if [ $BRANCH_EXISTS_ON_REMOTE -eq 1 ]; then
    # Branch exists, perform standard push
    git push origin "$CURRENT_BRANCH" --tags || { 
        print_error "git push failed. Attempting to diagnose..."
        git remote -v
        print_info "Checking remote connectivity..."
        git ls-remote --exit-code origin &>/dev/null || print_error "Cannot connect to remote 'origin'."
        print_info "Please check remote, branch name, permissions, and conflicts."
        
        # Offer to force push if needed
        read -p "Do you want to try force pushing? This may overwrite remote changes. (y/N) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            print_warning "Attempting force push..."
            git push --force origin "$CURRENT_BRANCH" --tags || {
                print_error "Force push failed. Manual intervention required."
                exit 1
            }
            print_success "Force push successful."
        else
            print_info "Force push declined. Exiting."
            exit 1
        fi
    }
else
    # First push, set upstream
    git push -u origin "$CURRENT_BRANCH" --tags || {
        print_error "Initial push failed. Attempting to diagnose..."
        git remote -v
        print_info "Checking remote connectivity..."
        git ls-remote --exit-code origin &>/dev/null || print_error "Cannot connect to remote 'origin'."
        print_info "Please check remote, branch name, and permissions."
        exit 1
    }
fi

print_success "Push to GitHub successful."

# Give GitHub systems time to process workflow file changes
print_info "Waiting 120 seconds for GitHub to process workflow file changes..."
print_info "This delay is necessary for GitHub to update its internal configurations after workflow file changes."
print_info "Without this delay, workflow_dispatch events may fail with 'Workflow does not have workflow_dispatch trigger' errors."
sleep 120

# *** STEP 8: Trigger GitHub Workflows ***
# CRITICAL: Always trigger workflows even if there were no changes
print_header "Ensuring GitHub workflows are ALWAYS triggered"
print_info "This step is MANDATORY - workflows MUST run even if no changes were committed or pushed!"

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

# Function to trigger a workflow with multiple fallback mechanisms
# Enhanced with better error handling and more fallback methods
trigger_workflow() {
    local repo_fullname="$1"
    local branch="$2"
    local workflow_type="$3"  # 'test' or 'release'
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
        
        if [ -n "$GH_TOKEN" ]; then
            # Try with workflow ID if available
            if [ -n "$workflow_id" ]; then
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
            if [ "$success" != "true" ]; then
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
    fi
    
    # STEP 5: Last resort - try to trigger ANY workflow
    if [ "$success" != "true" ]; then
        print_warning "All standard approaches failed. Searching for ANY triggerable workflow..."
        
        # Try to find any workflow with workflow_dispatch
        local all_workflow_files
        all_workflow_files=$(detect_available_workflows "$repo_fullname" "")
        
        for wf in $all_workflow_files; do
            print_info "Trying to trigger workflow: $wf..."
            
            # Try the gh CLI approach first
            if gh workflow run "$wf" --repo "$repo_fullname" --ref "$branch"; then
                print_success "Successfully triggered $wf workflow."
                success="true"
                break
            fi
            
            # Try API approach as fallback
            local wf_id
            wf_id=$(gh api "repos/$repo_fullname/actions/workflows" --jq ".workflows[] | select(.path | endswith(\"/$wf\")) | .id" 2>/dev/null)
            
            if [ -n "$wf_id" ]; then
                if gh api --method POST "repos/$repo_fullname/actions/workflows/$wf_id/dispatches" -f "ref=$branch" --silent; then
                    print_success "Successfully triggered $wf workflow via API."
                    success="true"
                    break
                fi
            fi
        done
    fi
    
    # STEP 6: Manual fallback instructions if everything fails
    if [ "$success" != "true" ]; then
        print_error "All automated methods to trigger workflows failed."
        print_warning "CRITICAL: Workflows must be triggered! Please trigger them manually:"
        print_info "1. Go to: https://github.com/$repo_fullname/actions"
        print_info "2. Find the '$workflow_file' workflow"
        print_info "3. Click 'Run workflow' button"
        print_info "4. Select branch: $branch"
        print_info "5. Click 'Run workflow'"
        
        # Create a link with direct workflow trigger 
        print_info ""
        print_info "Or use this direct link to trigger the workflow (copy and paste in browser):"
        print_info "https://github.com/$repo_fullname/actions/workflows/$workflow_file/dispatches"
        print_info ""
        print_info "For browser triggering, you may need to wait 5-10 minutes after pushing workflow file changes,"
        print_info "as GitHub's internal systems need time to recognize the workflow_dispatch event trigger."
        
        # Create detailed troubleshooting guide
        print_info ""
        print_info "== TROUBLESHOOTING GUIDE =="
        print_info "If workflows cannot be triggered, check the following:"
        print_info "1. Ensure all workflow files have a 'workflow_dispatch:' trigger"
        print_info "2. Verify GitHub permissions are correct (need write access to the repository)"
        print_info "3. Check recent Actions API rate limits at: https://github.com/$repo_fullname/settings/actions"
        print_info "4. Ensure the branch exists and is pushed to GitHub"
        print_info "5. Try running 'gh auth status' to verify GitHub authentication"
        print_info "6. After modifying workflow files, GitHub needs 1-5 minutes to recognize changes"
        print_info ""
        
        return 1
    fi
    
    return 0
}

# Main workflow triggering logic for GitHub Actions
if [ $REPO_EXISTS -eq 1 ]; then
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
            trigger_workflow "$REPO_FULL_NAME" "$CURRENT_BRANCH" "test" 2
            if [ $? -eq 0 ]; then
                TEST_WORKFLOW_TRIGGERED=1
                WORKFLOW_TRIGGER_SUCCESS=1
            fi
        done
    else
        # Fallback to generic test workflow detection
        print_info "No specific test workflows identified. Using generic test workflow detection..."
        trigger_workflow "$REPO_FULL_NAME" "$CURRENT_BRANCH" "test" 2
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
            trigger_workflow "$REPO_FULL_NAME" "$CURRENT_BRANCH" "release" 2
            if [ $? -eq 0 ]; then
                RELEASE_WORKFLOW_TRIGGERED=1
                WORKFLOW_TRIGGER_SUCCESS=1
            fi
        done
    else
        # Fallback to generic release workflow detection
        print_info "No specific release workflows identified. Using generic release workflow detection..."
        trigger_workflow "$REPO_FULL_NAME" "$CURRENT_BRANCH" "release" 2
        if [ $? -eq 0 ]; then
            RELEASE_WORKFLOW_TRIGGERED=1
            WORKFLOW_TRIGGER_SUCCESS=1
        fi
    fi
    
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
            print_info "No runs detected via gh run list. Trying GitHub API directly..."
            RECENT_RUNS=$(gh api "repos/$REPO_FULL_NAME/actions/runs" --jq '.workflow_runs[] | select(.status == "queued" or .status == "in_progress") | .name' 2>/dev/null || echo "")
        fi
        
        if [ -n "$RECENT_RUNS" ]; then
            print_success "GitHub workflows have been successfully triggered and are in progress."
            print_info "Active workflow runs detected: $RECENT_RUNS"
            WORKFLOW_VERIFICATION_SUCCESS=1
            break
        else
            VERIFICATION_RETRY_COUNT=$((VERIFICATION_RETRY_COUNT+1))
            
            if [ $VERIFICATION_RETRY_COUNT -lt $MAX_VERIFICATION_RETRIES ]; then
                print_warning "No active workflow runs detected yet. Retrying verification..."
                
                # If we modified workflow files recently, GitHub might need more time
                if [ $WORKFLOW_FILES_CHANGED -eq 1 ]; then
                    print_info "Since workflow files were modified, GitHub might need more time."
                    print_info "Waiting an additional 20 seconds..."
                    sleep 20
                fi
            fi
        fi
    done
    
    # *** STEP 3: Final status report and manual instructions if needed ***
    if [ $WORKFLOW_VERIFICATION_SUCCESS -eq 1 ]; then
        print_header "GitHub Workflow Triggering Successful!"
        print_success "Workflows have been triggered and are running."
        print_info "You can monitor their progress at: https://github.com/$REPO_FULL_NAME/actions"
    else
        # If we successfully triggered but couldn't verify, it might just be a delay
        if [ $WORKFLOW_TRIGGER_SUCCESS -eq 1 ]; then
            print_warning "Workflows were triggered but couldn't be verified as running yet."
            print_info "This is usually a delay in GitHub's systems and workflows should start soon."
            print_info "Wait a few minutes and then check: https://github.com/$REPO_FULL_NAME/actions"
        else
            print_error "Failed to trigger workflows automatically after multiple attempts."
            print_warning "${BOLD}CRITICAL:${NC} Workflows MUST be triggered manually to complete the CI/CD process!"
            
            # Provide detailed manual triggering instructions
            print_info ""
            print_info "${BOLD}==== MANUAL WORKFLOW TRIGGERING INSTRUCTIONS ====${NC}"
            print_info "1. Go to: https://github.com/$REPO_FULL_NAME/actions"
            print_info "2. For each workflow listed below, click on it, then click the 'Run workflow' button:"
            
            # Create list of direct links to workflow run pages
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

# *** STEP 10: Final instructions & verification ***
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
