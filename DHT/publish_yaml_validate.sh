#!/usr/bin/env bash

# Return error if executed directly - MUST BE PLACED AT THE BEGINNING
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    echo "Error: This script cannot be executed directly. All DHT scripts can only be called by the DHT Launcher in the project root. Please run dhtl.sh (or dhtl.bat) followed by the action you want to execute. For more informations use dhtl.sh --help"
    exit 1
fi

set -eo pipefail
source "${SCRIPT_DIR}/publish_common.sh"

print_step "Verifying bump-my-version installation..."
if ! "$UV_VENV" tool list 2>/dev/null | grep -q "bump-my-version"; then
    print_warning "bump-my-version not found in uv tools. Installing..."
    "$UV_VENV" tool install bump-my-version || {
        print_error "Failed to install bump-my-version using uv tool." 1
        print_info "See: https://www.andrlik.org/dispatches/til-bump-my-version-uv/"
        exit 1
    }
fi

# Verify bump-my-version works
if ! "$UV_VENV" tool run bump-my-version --version &>/dev/null; then
    print_error "bump-my-version installation is broken or incomplete." 1
    print_info "Try: uv tool uninstall bump-my-version && uv tool install bump-my-version"
    exit 1
fi
print_success "bump-my-version is properly installed: $("$UV_VENV" tool run bump-my-version --version 2>&1 | head -n 1)"

# Validate pre-commit installation
print_info "Verifying pre-commit installation..."
if ! "$PYTHON_CMD" -m pip show pre-commit &>/dev/null; then
    print_warning "pre-commit not found. Installing..."
    "$PYTHON_CMD" -m pip install pre-commit || {
        print_error "Failed to install pre-commit." 1
        exit 1
    }
fi
print_success "pre-commit is properly installed: $("$VENV_DIR/bin/pre-commit" --version 2>&1 | head -n 1)"

# Check if pre-commit hooks are installed
if [ ! -f "$SCRIPT_DIR/.git/hooks/pre-commit" ]; then
    print_warning "pre-commit hooks not installed. Installing..."
    "$VENV_DIR/bin/pre-commit" install || {
        print_error "Failed to install pre-commit hooks." 1
        exit 1
    }
fi
print_success "pre-commit hooks are installed"

# Basic summary of environment validation
print_success "Environment validation complete. All required tools are properly configured."

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
    print_error "Not authenticated with GitHub CLI. Please run 'gh auth login' first." 1
            exit 1
fi

GITHUB_USER=$(gh api user | grep login | cut -d'"' -f4)
if [ -z "$GITHUB_USER" ]; then
    print_error "Failed to get GitHub username. Please check your authentication." 1
            exit 1
fi
print_success "Authenticated with GitHub as user: $GITHUB_USER"

# *** STEP 2: Environment Synchronization ***
print_step "Performing environment synchronization with uv..."

# We must use our project-specific uv from the virtual environment
UV_CMD="$VENV_DIR/bin/uv"
if [ ! -f "$UV_CMD" ]; then
    print_error "uv not found in virtual environment. This is required." 1
    print_info "Try running: ./reinitialize_env.sh"
    exit 1
fi

# Sync dependencies
print_info "Synchronizing dependencies with uv..."
"$UV_CMD" sync || {
    print_error "uv sync failed. Environment may be in an inconsistent state." 1
    print_info "Try running: ./reinitialize_env.sh"
    exit 1
}
print_success "Dependency synchronization successful"

# Verify pip installation
if ! $PYTHON_CMD -m pip --version &> /dev/null; then
    print_error "pip not found in virtual environment. This is required." 1
    print_info "Try running: ./reinitialize_env.sh"
    exit 1
fi

# Ensure bump-my-version is installed via uv tool (required method)
print_step "Verifying bump-my-version installation via uv..."

if ! "$UV_CMD" tool list 2>/dev/null | grep -q "bump-my-version"; then
    print_info "bump-my-version not found in uv tools. Installing..."
    "$UV_CMD" tool install bump-my-version || {
        print_error "Failed to install bump-my-version using uv tool." 1
        print_info "See: https://www.andrlik.org/dispatches/til-bump-my-version-uv/"
        print_info "Try running: uv tool install bump-my-version"
        exit 1
    }
fi

# Verify bump-my-version works
if ! "$UV_CMD" tool run bump-my-version --version &>/dev/null; then
    print_error "bump-my-version installation is broken or incomplete." 1
    print_info "Try: uv tool uninstall bump-my-version && uv tool install bump-my-version"
    exit 1
fi
BUMP_VERSION=$("$UV_CMD" tool run bump-my-version --version 2>&1 | head -n 1)
print_success "bump-my-version is properly installed: $BUMP_VERSION"

# Ensure pre-commit is installed and working
print_step "Preparing pre-commit environment..."
if ! $PYTHON_CMD -m pip show pre-commit &> /dev/null; then
    print_info "pre-commit not found in virtual environment. Installing..."
    "$UV_CMD" pip install pre-commit || { 
        print_error "Failed to install pre-commit. Try running ./reinitialize_env.sh first." 1
        exit 1; 
    }
fi

# Clean pre-commit cache to avoid potential issues
print_info "Cleaning pre-commit cache..."
rm -rf "${HOME}/.cache/pre-commit" || print_warning "Failed to remove pre-commit cache, continuing..."

# Install pre-commit hooks
print_info "Installing pre-commit hooks..."
$PYTHON_CMD -m pre_commit install --install-hooks || { 
    print_warning "pre-commit install failed. Creating manual backup hook..."
    # If pre-commit installation fails, create a backup manual hook
    mkdir -p .git/hooks
    cat > .git/hooks/pre-commit << 'EOF'
#!/bin/sh
set -e

# Get the directory of this script
PROJECT_ROOT=$(dirname "$SCRIPT_DIR")

# Run code formatting with ruff if available
if [ -f "$PROJECT_ROOT/.venv/bin/ruff" ]; then
    "$PROJECT_ROOT/.venv/bin/ruff" --fix "$PROJECT_ROOT"
elif command -v ruff &> /dev/null; then
    ruff --fix "$PROJECT_ROOT"
fi

# Run shellcheck on shell scripts if available
if command -v shellcheck &> /dev/null; then
    find "$PROJECT_ROOT" -name "*.sh" -maxdepth 3 -print0 | xargs -0 -n1 shellcheck || echo "WARNING: Shellcheck found issues"
fi

# IMPORTANT: Use uv to run bump-my-version (required method)
if [ -f "$PROJECT_ROOT/.venv/bin/uv" ]; then
    "$PROJECT_ROOT/.venv/bin/uv" tool run bump-my-version minor --commit --tag --allow-dirty || \
    echo "WARNING: Version bump with uv tool failed, continuing commit"
elif command -v uv &> /dev/null; then
    "$UV_CMD" tool run bump-my-version minor --commit --tag --allow-dirty || \
    echo "WARNING: Version bump with uv tool failed, continuing commit"
else
    echo "WARNING: uv not found, version bump might fail!"
    # Try any available bump-my-version method
    if [ -f "$PROJECT_ROOT/.venv/bin/bump-my-version" ]; then
        "$PROJECT_ROOT/.venv/bin/bump-my-version" minor --commit --tag --allow-dirty || echo "WARNING: Version bump failed"
    elif command -v bump-my-version &> /dev/null; then
        bump-my-version minor --commit --tag --allow-dirty || echo "WARNING: Version bump failed"
    fi
fi
EOF
    chmod +x .git/hooks/pre-commit
    print_warning "Created manual pre-commit hook as fallback."
}

print_success "Environment synchronization complete. All dependencies are up-to-date."

# *** STEP 3: YAML Validation ***
print_step "Validating YAML files with enhanced validation..."

# Skip if requested
if [ $SKIP_LINTERS -eq 1 ]; then
    print_info "Skipping YAML validation as requested with --skip-linters flag."
else
    # Ensure yamllint is available
    if ! command -v yamllint &> /dev/null; then
        print_info "Installing yamllint for enhanced YAML validation..."
        
        # Use uv for installation (preferred method)
        if [ -f "$UV_CMD" ]; then
            "$UV_CMD" pip install yamllint || { 
                print_warning "Failed to install yamllint via uv. Trying pip directly..."
                "$PYTHON_CMD" -m pip install yamllint || { 
                    print_warning "Failed to install yamllint. Will use fallback validation methods."
                    YAMLLINT_AVAILABLE=0
                }
            }
        else
            # Fall back to pip if uv isn't available (shouldn't happen with our checks)
            "$PYTHON_CMD" -m pip install yamllint || { 
                print_warning "Failed to install yamllint. Will use fallback validation methods."
                YAMLLINT_AVAILABLE=0
            }
        fi
        
        # Verify installation was successful
        if command -v yamllint &> /dev/null || [ -f "$VENV_DIR/bin/yamllint" ]; then
            YAMLLINT_AVAILABLE=1
            print_success "yamllint installed successfully"
        else
            YAMLLINT_AVAILABLE=0
            print_warning "yamllint installation could not be verified"
        fi
    else
        YAMLLINT_AVAILABLE=1
        print_success "yamllint is already installed"
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
