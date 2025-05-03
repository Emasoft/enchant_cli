#!/bin/bash

# Return error if executed directly - MUST BE PLACED AT THE BEGINNING
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    echo "Error: This script cannot be executed directly. All DHT scripts can only be called by the DHT Launcher in the project root. Please run dhtl.sh (or dhtl.bat) followed by the action you want to execute. For more informations use dhtl.sh --help"
    exit 1
fi

# install_uv.sh - Comprehensive uv installer and configuration script
# This script installs uv and related tools in an isolated environment

set -eo pipefail

# Get the directory of this script

# ANSI color codes for pretty output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color
BOLD='\033[1m'

print_header() {
    echo -e "${BOLD}${BLUE}=== $1 ===${NC}"
    echo ""
}

print_step() {
    echo -e "${CYAN}🔄 $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️ $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
    
    # If there's a second parameter, exit with that code
    if [ -n "$2" ]; then
        exit "$2"
    fi
}

# Function to check if command exists
command_exists() {
    command -v "$1" &> /dev/null
}

# Function to install uv
install_uv() {
    print_step "Installing uv..."
    
    # Check if we already have uv in the project's venv
    if [ -d "$SCRIPT_DIR/.venv" ] && [ -f "$SCRIPT_DIR/.venv/bin/uv" ]; then
        print_success "uv is already installed in project's venv"
        PYTHON_CMD="$SCRIPT_DIR/.venv/bin/python"
        UV_CMD="$SCRIPT_DIR/.venv/bin/uv"
        return 0
    fi
    
    # Create virtual environment if it doesn't exist
    if [ ! -d "$SCRIPT_DIR/.venv" ]; then
        print_step "Creating virtual environment..."
        
        # Check for system Python
        if command_exists python3; then
            PYTHON_CMD="python3"
        elif command_exists python; then
            PYTHON_CMD="python"
        else
            print_error "No Python installation found. Please install Python 3.9 or newer." 1
        fi
        
        # Create venv with system Python initially
        "$PYTHON_CMD" -m venv "$SCRIPT_DIR/.venv"
        print_success "Created virtual environment at $SCRIPT_DIR/.venv"
    fi
    
    # Activate the virtual environment
    source "$SCRIPT_DIR/.venv/bin/activate"
    PYTHON_CMD="$SCRIPT_DIR/.venv/bin/python"
    
    # Install uv inside the virtual environment
    if command_exists curl; then
        print_step "Installing uv using the official installer..."
        curl -LsSf https://astral.sh/uv/install.sh | sh
        "$PYTHON_CMD" -m pip install uv
    else
        print_step "Installing uv using pip..."
        "$PYTHON_CMD" -m pip install uv
    fi
    
    # Set the UV_CMD variable
    UV_CMD="$SCRIPT_DIR/.venv/bin/uv"
    
    if [ -f "$UV_CMD" ]; then
        print_success "Successfully installed uv: $("$UV_CMD" --version)"
    else
        print_error "Failed to install uv" 1
    fi
}

# Function to install pre-commit-uv
install_pre_commit_uv() {
    print_step "Installing pre-commit-uv..."
    
    # Install pre-commit-uv using uv
    "$UV_CMD" pip install pre-commit-uv
    
    print_success "Installed pre-commit-uv"
}

# Function to install tox-uv
install_tox_uv() {
    print_step "Installing tox-uv..."
    
    # Install tox-uv using uv
    "$UV_CMD" pip install tox tox-uv
    
    print_success "Installed tox-uv"
}

# Function to install bump-my-version
install_bump_my_version() {
    print_step "Installing bump-my-version..."
    
    # Install bump-my-version using uv tool
    "$UV_CMD" tool install bump-my-version
    
    print_success "Installed bump-my-version"
}

# Function to setup the virtual environment with all dev dependencies
setup_dev_environment() {
    print_step "Setting up development environment..."
    
    # Sync all dependencies from lock file if it exists
    if [ -f "$SCRIPT_DIR/uv.lock" ]; then
        print_info "Syncing dependencies from lock file..."
        "$UV_CMD" sync
    fi
    
    # Install package in development mode
    print_info "Installing package in development mode..."
    "$UV_CMD" pip install -e "$SCRIPT_DIR"
    
    print_success "Development environment setup complete"
}

# Function to create tox.ini with uv support
create_tox_config() {
    print_step "Creating tox.ini with uv support..."
    
    if [ ! -f "$SCRIPT_DIR/tox.ini" ]; then
        cat > "$SCRIPT_DIR/tox.ini" << EOF
[tox]
envlist = py39, py310, py311, py312, py313
isolated_build = True
requires =
    tox-uv>=0.8.1
    tox>=4.11.4

[testenv]
deps =
    pytest>=7.3.1
    pytest-cov>=4.1.0
    pytest-timeout>=2.1.0
commands =
    pytest {posargs:tests} --cov=enchant_cli --cov-report=term --cov-report=xml --timeout=900

[testenv:lint]
deps =
    ruff>=0.3.0
    black>=23.3.0
commands =
    ruff check .
    ruff format --check .

[testenv:typecheck]
deps =
    mypy>=1.0.0
commands =
    mypy src/enchant_cli

[testenv:docs]
deps =
    mkdocs>=1.4.0
    mkdocs-material>=8.5.0
commands =
    mkdocs build
EOF
        print_success "Created tox.ini with uv configuration"
    else
        print_info "tox.ini already exists, checking for uv configuration..."
        
        # Check if tox.ini has tox-uv configuration
        if grep -q "tox-uv" "$SCRIPT_DIR/tox.ini"; then
            print_success "tox.ini already configured with tox-uv"
        else
            print_warning "tox.ini exists but doesn't appear to have tox-uv configuration"
            print_info "Please add the following to the [tox] section of tox.ini:"
            echo "requires ="
            echo "    tox-uv>=0.8.1"
            echo "    tox>=4.11.4"
        fi
    fi
}

# Function to update or create .pre-commit-config.yaml
update_pre_commit_config() {
    print_step "Updating pre-commit configuration for uv integration..."
    
    if [ -f "$SCRIPT_DIR/.pre-commit-config.yaml" ]; then
        # Check if pre-commit-uv is already configured
        if grep -q "pre-commit-uv" "$SCRIPT_DIR/.pre-commit-config.yaml"; then
            print_success "pre-commit-uv already configured in .pre-commit-config.yaml"
        else
            print_info "Adding pre-commit-uv to existing configuration..."
            
            # Backup existing config
            cp "$SCRIPT_DIR/.pre-commit-config.yaml" "$SCRIPT_DIR/.pre-commit-config.yaml.bak"
            
            # Insert pre-commit-uv configuration at the beginning of repos section
            # This is a bit tricky with sed, so we'll use a temporary file approach
            
            # Create a temporary file with pre-commit-uv configuration
            cat > "$SCRIPT_DIR/.pre-commit-uv-config.tmp" << EOF
repos:
  - repo: https://github.com/tox-dev/pre-commit-uv
    rev: 0.0.5  # Use the latest version
    hooks:
      - id: pip-sync-uv
        name: Sync development environment with uv
        args: ["--check"]
        files: '(^pyproject\.toml|uv\.lock|\\..*\.toml)$'
      - id: pip-compile-uv
        name: Lock dependencies with uv
        args: ["--check", "--upgrade"]
        files: 'pyproject\.toml$'

EOF
            
            # Append the original content (excluding the first line with 'repos:')
            if grep -q "^repos:" "$SCRIPT_DIR/.pre-commit-config.yaml"; then
                tail -n +2 "$SCRIPT_DIR/.pre-commit-config.yaml" >> "$SCRIPT_DIR/.pre-commit-uv-config.tmp"
                mv "$SCRIPT_DIR/.pre-commit-uv-config.tmp" "$SCRIPT_DIR/.pre-commit-config.yaml"
                print_success "Added pre-commit-uv configuration to .pre-commit-config.yaml"
            else
                # If the file doesn't start with 'repos:', just prepend the config
                cat "$SCRIPT_DIR/.pre-commit-uv-config.tmp" "$SCRIPT_DIR/.pre-commit-config.yaml" > "$SCRIPT_DIR/.pre-commit-uv-config.final"
                mv "$SCRIPT_DIR/.pre-commit-uv-config.final" "$SCRIPT_DIR/.pre-commit-config.yaml"
                rm -f "$SCRIPT_DIR/.pre-commit-uv-config.tmp"
                print_success "Added pre-commit-uv configuration to .pre-commit-config.yaml"
            fi
        fi
    else
        # Create a new .pre-commit-config.yaml file
        print_info "Creating new .pre-commit-config.yaml with uv integration..."
        
        cat > "$SCRIPT_DIR/.pre-commit-config.yaml" << EOF
repos:
  - repo: https://github.com/tox-dev/pre-commit-uv
    rev: 0.0.5  # Use the latest version
    hooks:
      - id: pip-sync-uv
        name: Sync development environment with uv
        args: ["--check"]
        files: '(^pyproject\.toml|uv\.lock|\\..*\.toml)$'
      - id: pip-compile-uv
        name: Lock dependencies with uv
        args: ["--check", "--upgrade"]
        files: 'pyproject\.toml$'

  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.4.7
    hooks:
      - id: ruff
        args: ["--fix"]

  - repo: https://github.com/psf/black-pre-commit-mirror
    rev: 24.3.0
    hooks:
      - id: black

  - repo: https://github.com/shellcheck-py/shellcheck-py
    rev: v0.10.0.1
    hooks:
      - id: shellcheck
        args: ["--severity=error", "--extended-analysis=true"]

  - repo: local
    hooks:
      - id: bump-version
        name: Increment version using bump-my-version
        description: 'Bump version: increment minor version with automatic commit and tag'
        entry: ./.venv/bin/uv tool run bump-my-version bump minor --commit --tag --allow-dirty
        language: system
        pass_filenames: false
        stages: [pre-commit]
        always_run: true
EOF
        print_success "Created new .pre-commit-config.yaml with uv integration"
    fi
}

# Function to update GitHub workflow files
update_github_workflows() {
    print_step "Updating GitHub workflow files for uv integration..."
    
    # Check if .github/workflows directory exists
    if [ -d "$SCRIPT_DIR/.github/workflows" ]; then
        print_info "Found GitHub workflow directory"
        
        # Loop through workflow files and update them
        for workflow_file in "$SCRIPT_DIR/.github/workflows"/*.yml; do
            workflow_name=$(basename "$workflow_file")
            print_info "Processing workflow file: $workflow_name"
            
            # Check if the workflow already uses uv
            if grep -q "uv" "$workflow_file"; then
                print_info "Workflow $workflow_name already uses uv"
            else
                # Backup the workflow file
                cp "$workflow_file" "${workflow_file}.bak"
                
                # Replace pip install with uv sync or uv pip install -e .
                if grep -q "pip install" "$workflow_file"; then
                    print_info "Updating pip commands to use uv in $workflow_name"
                    
                    # Use sed to replace pip install with uv
                    sed -i.tmp 's/pip install -e \./uv pip install -e ./g' "$workflow_file"
                    sed -i.tmp 's/pip install/uv pip install/g' "$workflow_file"
                    
                    # Replace requirements.txt install if it exists
                    sed -i.tmp 's/pip install -r requirements.txt/uv sync/g' "$workflow_file"
                    
                    # Remove temporary files
                    rm -f "${workflow_file}.tmp"
                    
                    print_success "Updated pip commands in $workflow_name"
                fi
                
                # Add uv installation section if not present
                if ! grep -q "Install uv" "$workflow_file"; then
                    print_info "Adding uv installation section to $workflow_name"
                    
                    # This is a complex operation, we'll use a placeholder approach
                    # Insert after Python setup
                    if grep -q "setup-python" "$workflow_file"; then
                        # Create a temporary file with uv installation steps
                        cat > "$SCRIPT_DIR/.uv-install-steps.tmp" << EOF
      - name: Install uv
        run: |
          curl -LsSf https://astral.sh/uv/install.sh | sh
          pip install uv
EOF
                        
                        # Insert after setup-python step
                        awk '/setup-python/{print;print "";getline;print;print "      - name: Install uv";print "        run: |";print "          curl -LsSf https://astral.sh/uv/install.sh | sh";print "          pip install uv";next}1' "$workflow_file" > "${workflow_file}.new"
                        mv "${workflow_file}.new" "$workflow_file"
                        
                        print_success "Added uv installation to $workflow_name"
                    fi
                fi
                
                # Add tox-uv for tox-based workflows
                if grep -q "tox" "$workflow_file" && ! grep -q "tox-uv" "$workflow_file"; then
                    print_info "Adding tox-uv to tox-based workflow $workflow_name"
                    
                    # Replace tox installation with tox + tox-uv
                    sed -i.tmp 's/pip install tox/uv pip install tox tox-uv/g' "$workflow_file"
                    rm -f "${workflow_file}.tmp"
                    
                    print_success "Added tox-uv to $workflow_name"
                fi
            fi
        done
    else
        print_warning "No GitHub workflow directory found at $SCRIPT_DIR/.github/workflows"
    fi
}

# Function to update or create .bumpversion.toml
update_bump_my_version_config() {
    print_step "Updating bump-my-version configuration for uv integration..."
    
    # Look for .bumpversion.toml or bump-my-version configuration in pyproject.toml
    if [ -f "$SCRIPT_DIR/.bumpversion.toml" ]; then
        print_info "Found .bumpversion.toml"
        
        # Check if uv sync is in pre_commit_hooks
        if grep -q "uv sync" "$SCRIPT_DIR/.bumpversion.toml"; then
            print_success ".bumpversion.toml already configured with uv sync"
        else
            # Update pre_commit_hooks to include uv sync
            print_info "Updating pre_commit_hooks in .bumpversion.toml"
            
            # Create a backup
            cp "$SCRIPT_DIR/.bumpversion.toml" "$SCRIPT_DIR/.bumpversion.toml.bak"
            
            # Check if pre_commit_hooks exists
            if grep -q "pre_commit_hooks" "$SCRIPT_DIR/.bumpversion.toml"; then
                # Replace existing pre_commit_hooks line
                sed -i.tmp 's/pre_commit_hooks.*/pre_commit_hooks = ["uv sync", "git add uv.lock"]/g' "$SCRIPT_DIR/.bumpversion.toml"
                rm -f "$SCRIPT_DIR/.bumpversion.toml.tmp"
            else
                # Add pre_commit_hooks line at the end of the [tool.bumpversion] section
                awk '/\[tool.bumpversion\]/{p=1} p && /^$/{print "pre_commit_hooks = [\"uv sync\", \"git add uv.lock\"]"; p=0} {print}' "$SCRIPT_DIR/.bumpversion.toml" > "$SCRIPT_DIR/.bumpversion.toml.new"
                mv "$SCRIPT_DIR/.bumpversion.toml.new" "$SCRIPT_DIR/.bumpversion.toml"
            fi
            
            print_success "Updated pre_commit_hooks in .bumpversion.toml"
        fi
    elif [ -f "$SCRIPT_DIR/pyproject.toml" ] && grep -q "\[tool.bumpversion\]" "$SCRIPT_DIR/pyproject.toml"; then
        print_info "Found bump-my-version configuration in pyproject.toml"
        
        # Check if uv sync is in pre_commit_hooks
        if grep -q "uv sync" "$SCRIPT_DIR/pyproject.toml"; then
            print_success "pyproject.toml already configured with uv sync for bump-my-version"
        else
            # Update pre_commit_hooks to include uv sync
            print_info "Updating pre_commit_hooks in pyproject.toml"
            
            # Create a backup
            cp "$SCRIPT_DIR/pyproject.toml" "$SCRIPT_DIR/pyproject.toml.bak"
            
            # Check if pre_commit_hooks exists
            if grep -q "pre_commit_hooks" "$SCRIPT_DIR/pyproject.toml"; then
                # Replace existing pre_commit_hooks line
                sed -i.tmp 's/pre_commit_hooks.*/pre_commit_hooks = ["uv sync", "git add uv.lock"]/g' "$SCRIPT_DIR/pyproject.toml"
                rm -f "$SCRIPT_DIR/pyproject.toml.tmp"
            else
                # Add pre_commit_hooks line at the end of the [tool.bumpversion] section
                awk '/\[tool.bumpversion\]/{p=1} p && /^\[/{print "pre_commit_hooks = [\"uv sync\", \"git add uv.lock\"]"; p=0; print; next} {print}' "$SCRIPT_DIR/pyproject.toml" > "$SCRIPT_DIR/pyproject.toml.new"
                mv "$SCRIPT_DIR/pyproject.toml.new" "$SCRIPT_DIR/pyproject.toml"
            fi
            
            print_success "Updated pre_commit_hooks in pyproject.toml"
        fi
    else
        # Create a new .bumpversion.toml file
        print_info "Creating new .bumpversion.toml with uv integration..."
        
        # Try to detect current version
        current_version="0.1.0"
        if [ -f "$SCRIPT_DIR/src/enchant_cli/__init__.py" ]; then
            version_line=$(grep '__version__' "$SCRIPT_DIR/src/enchant_cli/__init__.py")
            if [ -n "$version_line" ]; then
                current_version=$(echo "$version_line" | sed -E 's/.*"([0-9]+\.[0-9]+\.[0-9]+)".*/\1/')
            fi
        fi
        
        cat > "$SCRIPT_DIR/.bumpversion.toml" << EOF
[tool.bumpversion]
current_version = "$current_version"
parse = "(?P<major>\\d+)\\.(?P<minor>\\d+)\\.(?P<patch>\\d+)"
serialize = ["{major}.{minor}.{patch}"]
search = "__version__ = \"{current_version}\""
replace = "__version__ = \"{new_version}\""
regex = false
ignore_missing_version = false
tag = true
sign_tags = false
tag_name = "v{new_version}"
tag_message = "Bump version: {current_version} → {new_version}"
allow_dirty = true
commit = true
message = "Bump version: {current_version} → {new_version}"
commit_args = ""
pre_commit_hooks = ["uv sync", "git add uv.lock"]
EOF
        print_success "Created new .bumpversion.toml with uv integration"
    fi
}

# Function to update hooks/bump_version.sh
update_bump_version_script() {
    print_step "Updating bump_version.sh to use uv..."
    
    # Check if hooks directory and script exist
    if [ -d "$SCRIPT_DIR/hooks" ] && [ -f "$SCRIPT_DIR/hooks/bump_version.sh" ]; then
        print_info "Found hooks/bump_version.sh"
        
        # Create a backup
        cp "$SCRIPT_DIR/hooks/bump_version.sh" "$SCRIPT_DIR/hooks/bump_version.sh.bak"
        
        # Update the script to use uv
        if grep -q "uv tool run" "$SCRIPT_DIR/hooks/bump_version.sh"; then
            print_success "hooks/bump_version.sh already uses uv tool run"
        else
            print_info "Updating hooks/bump_version.sh to use uv tool run"
            
            # Create a new script with uv integration
            cat > "$SCRIPT_DIR/hooks/bump_version.sh" << EOF
#!/bin/bash
# bump_version.sh - Script for bumping project version using bump-my-version with uv
set -eo pipefail

# Get script directory
PROJECT_ROOT=\$(dirname "\$SCRIPT_DIR")

# Default version part if not specified
VERSION_PART=\${1:-minor}

# Validate version part
if [[ ! "\$VERSION_PART" =~ ^(major|minor|patch)$ ]]; then
    echo "❌ Error: Invalid version part. Use one of: major, minor, patch"
    exit 1
fi

# Try using uv tool run (recommended approach)
if command -v uv >/dev/null 2>&1; then
    echo "🔄 Bumping \$VERSION_PART version with uv tool run..."
    uv tool run bump-my-version bump "\$VERSION_PART" --commit --tag --allow-dirty
    exit \$?
elif [ -f "\$PROJECT_ROOT/.venv/bin/uv" ]; then
    echo "🔄 Bumping \$VERSION_PART version with .venv/bin/uv tool run..."
    "\$PROJECT_ROOT/.venv/bin/uv" tool run bump-my-version bump "\$VERSION_PART" --commit --tag --allow-dirty
    exit \$?
elif [ -f "\$PROJECT_ROOT/.venv/bin/bump-my-version" ]; then
    echo "🔄 Bumping \$VERSION_PART version with .venv/bin/bump-my-version..."
    "\$PROJECT_ROOT/.venv/bin/bump-my-version" bump "\$VERSION_PART" --commit --tag --allow-dirty
    exit \$?
else
    echo "❌ Neither uv nor bump-my-version found in path or virtual environment"
    echo "💡 Run install_uv.sh to set up the environment properly"
    exit 1
fi
EOF
            
            # Make the script executable
            chmod +x "$SCRIPT_DIR/hooks/bump_version.sh"
            
            print_success "Updated hooks/bump_version.sh to use uv tool run"
        fi
    else
        print_warning "hooks/bump_version.sh not found"
        
        # Create the directory and script if they don't exist
        if [ ! -d "$SCRIPT_DIR/hooks" ]; then
            mkdir -p "$SCRIPT_DIR/hooks"
        fi
        
        # Create the script
        cat > "$SCRIPT_DIR/hooks/bump_version.sh" << EOF
#!/bin/bash
# bump_version.sh - Script for bumping project version using bump-my-version with uv
set -eo pipefail

# Get script directory
PROJECT_ROOT=\$(dirname "\$SCRIPT_DIR")

# Default version part if not specified
VERSION_PART=\${1:-minor}

# Validate version part
if [[ ! "\$VERSION_PART" =~ ^(major|minor|patch)$ ]]; then
    echo "❌ Error: Invalid version part. Use one of: major, minor, patch"
    exit 1
fi

# Try using uv tool run (recommended approach)
if command -v uv >/dev/null 2>&1; then
    echo "🔄 Bumping \$VERSION_PART version with uv tool run..."
    uv tool run bump-my-version bump "\$VERSION_PART" --commit --tag --allow-dirty
    exit \$?
elif [ -f "\$PROJECT_ROOT/.venv/bin/uv" ]; then
    echo "🔄 Bumping \$VERSION_PART version with .venv/bin/uv tool run..."
    "\$PROJECT_ROOT/.venv/bin/uv" tool run bump-my-version bump "\$VERSION_PART" --commit --tag --allow-dirty
    exit \$?
elif [ -f "\$PROJECT_ROOT/.venv/bin/bump-my-version" ]; then
    echo "🔄 Bumping \$VERSION_PART version with .venv/bin/bump-my-version..."
    "\$PROJECT_ROOT/.venv/bin/bump-my-version" bump "\$VERSION_PART" --commit --tag --allow-dirty
    exit \$?
else
    echo "❌ Neither uv nor bump-my-version found in path or virtual environment"
    echo "💡 Run install_uv.sh to set up the environment properly"
    exit 1
fi
EOF
        
        # Make the script executable
        chmod +x "$SCRIPT_DIR/hooks/bump_version.sh"
        
        print_success "Created new hooks/bump_version.sh with uv integration"
    fi
}

# Main function
main() {
    print_header "UV Toolchain Installer and Configuration"
    
    # Install uv
    install_uv
    
    # Install tools using uv
    install_pre_commit_uv
    install_tox_uv
    install_bump_my_version
    
    # Setup development environment
    setup_dev_environment
    
    # Update configuration files for uv integration
    create_tox_config
    update_pre_commit_config
    update_github_workflows
    update_bump_my_version_config
    update_bump_version_script
    
    print_header "Installation and Configuration Complete"
    print_success "uv and related tools have been installed and configured successfully."
    print_info "Next steps:"
    print_info "1. Run 'source .venv/bin/activate' to activate the virtual environment"
    print_info "2. Run 'pre-commit install' to install the pre-commit hooks"
    print_info "3. Run 'tox -e py' to run tests in your Python version"
    print_info "4. Use 'uv sync' to keep your environment in sync with dependencies"
    
    # Return to the project directory
    cd "$SCRIPT_DIR" || return
}

# Run the main function
main
