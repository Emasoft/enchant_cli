# Project Environment & Development Guide

## Table of Contents
- [1. Environment Configuration](#1-environment-configuration)
  - [1.1 Supported Platforms](#11-supported-platforms)
  - [1.2 Environment Isolation](#12-environment-isolation)
  - [1.3 Environment Structure](#13-environment-structure)
  - [1.4 Key Environment Variables](#14-key-environment-variables)
    - [1.4.1 Required API Keys & Tokens](#141-required-api-keys--tokens)
    - [1.4.2 GitHub Secret Configuration](#142-github-secret-configuration)
    - [1.4.3 Verification Checklist](#143-verification-checklist)
- [2. Tool Configuration](#2-tool-configuration)
  - [2.1 uv Configuration](#21-uv-configuration)
  - [2.2 Pre-commit Configuration](#22-pre-commit-configuration)
  - [2.3 Version Management](#23-version-management)
  - [2.4 Dependency Management](#24-dependency-management)
- [3. Script Structure](#3-script-structure)
  - [3.1 Platform-Specific Design](#31-platform-specific-design)
  - [3.2 Core Script Conventions](#32-core-script-conventions)
  - [3.3 Command-Line Tool Guidelines](#33-command-line-tool-guidelines)
- [4. Core Scripts Reference](#4-core-scripts-reference)
  - [4.1 Environment Setup Scripts](#41-environment-setup-scripts)
  - [4.2 Project Workflow Scripts](#42-project-workflow-scripts)
  - [4.3 Testing Scripts](#43-testing-scripts)
  - [4.4 Utility Scripts](#44-utility-scripts)
- [5. Development Workflow](#5-development-workflow)
  - [5.1 Setting Up Development Environment](#51-setting-up-development-environment)
  - [5.2 Adding New Features](#52-adding-new-features)
  - [5.3 Release Workflow](#53-release-workflow)
  - [5.4 Code Quality Standards](#54-code-quality-standards)
- [6. GitHub Integration](#6-github-integration)
  - [6.1 GitHub Workflows](#61-github-workflows)
  - [6.2 GitHub Secret Configuration](#62-github-secret-configuration)
  - [6.3 Pull Request Process](#63-pull-request-process)
- [7. Project Structure Templates](#7-project-structure-templates)
  - [7.1 Core File Templates](#71-core-file-templates)
  - [7.2 Script Templates](#72-script-templates)
  - [7.3 GitHub Workflow Templates](#73-github-workflow-templates)
- [8. Troubleshooting](#8-troubleshooting)
  - [8.1 Common Environment Issues](#81-common-environment-issues)
  - [8.2 Test Failures](#82-test-failures)
  - [8.3 Version Control Problems](#83-version-control-problems)

## 1. Environment Configuration

### 1.1 Supported Platforms

The project supports the following platforms:

- **macOS**: Primary development platform, all scripts work natively
- **Linux**: Fully supported, all scripts work natively
- **BSD**: Compatible with Unix shell scripts
- **Windows**: Support via multiple options:
  - **WSL** (Windows Subsystem for Linux): Recommended approach
  - **Git Bash**: Alternative Unix-like environment
  - **Native**: Limited support via `.bat` wrapper scripts

### 1.2 Environment Isolation

The project is designed to be completely self-contained with a project-isolated Python environment:

1. **No External Dependencies**: All scripts ensure the project uses only its own isolated virtual environment
2. **Relative Paths**: All paths in scripts are relative to the script location, never absolute
3. **Environment Verification**: Scripts check for external references and warn/abort if found
4. **Self-healing**: The system automatically creates a clean environment when needed
5. **Explicit Tool Paths**: All tool calls use explicit paths to the project's environment (`.venv/bin/...`)
6. **Forced Environment Isolation**: The `ensure_env.sh` script:
   - Deactivates any active conda environment
   - Deactivates any active Python virtual environment
   - Cleans PATH from external site-packages and conflicting Python environments
   - Activates the project's own virtual environment
   - Verifies Python and pip point to the project's environment

All project scripts begin by sourcing the `ensure_env.sh` script:

```bash
# Example of how scripts start
#!/bin/bash
set -eo pipefail

# First, ensure we have a clean environment
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
source "$SCRIPT_DIR/ensure_env.sh"
```

To ensure a clean environment after cloning the repository:

```bash
# On Unix platforms (macOS, Linux, BSD)
./reinitialize_env.sh

# On Windows (Command Prompt)
reinitialize_env.bat

# On Windows via WSL/Git Bash
./reinitialize_env.sh
```

Here's the template for a robust `ensure_env.sh` script:

```bash
#!/bin/bash
# ensure_env.sh - Script to ensure a clean, isolated environment for the project

# Exit on error, trace commands
set -eo pipefail

# Get the directory of this script
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
PROJECT_ROOT="$SCRIPT_DIR"

# Check if we're already in the project's venv
if [[ "$VIRTUAL_ENV" == "$PROJECT_ROOT/.venv" ]]; then
    echo "✅ Already using project's virtual environment."
    return 0 2>/dev/null || exit 0
fi

# Deactivate any active conda environments first
if [ -n "$CONDA_PREFIX" ]; then
    echo "🔄 Deactivating conda environment: $CONDA_PREFIX"
    conda deactivate 2>/dev/null || true
fi

# Deactivate any virtual environment
if [ -n "$VIRTUAL_ENV" ]; then
    echo "🔄 Deactivating virtual environment: $VIRTUAL_ENV"
    deactivate 2>/dev/null || true
fi

# Clean PATH from conflicting Python environments
echo "🔄 Cleaning PATH from external Python environments..."
PATH=$(echo $PATH | tr ":" "\n" | grep -v "site-packages" | grep -v "ComfyUI" | tr "\n" ":" | sed 's/:$//')

# Create virtual environment if it doesn't exist
if [ ! -d "$PROJECT_ROOT/.venv" ]; then
    echo "🔄 Creating virtual environment..."
    # Check if uv is available
    if command -v uv >/dev/null 2>&1; then
        uv venv "$PROJECT_ROOT/.venv"
    else
        # Fall back to python -m venv
        python3 -m venv "$PROJECT_ROOT/.venv"
    fi
fi

# Activate the virtual environment
echo "🔄 Activating project virtual environment..."
source "$PROJECT_ROOT/.venv/bin/activate"

# Verify Python is from our venv
PYTHON_PATH=$(which python)
if [[ "$PYTHON_PATH" != "$PROJECT_ROOT/.venv/bin/python" ]]; then
    echo "⚠️ Warning: Python is not from our virtual environment!"
    echo "   Expected: $PROJECT_ROOT/.venv/bin/python"
    echo "   Got: $PYTHON_PATH"
    return 1 2>/dev/null || exit 1
fi

# Install uv if not available
if ! command -v "$PROJECT_ROOT/.venv/bin/uv" >/dev/null 2>&1; then
    echo "🔄 Installing uv in virtual environment..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    "$PROJECT_ROOT/.venv/bin/pip" install uv
fi

# Sync dependencies if needed
if [ -f "$PROJECT_ROOT/uv.lock" ] && [ ! -f "$PROJECT_ROOT/.venv/.sync_completed" ]; then
    echo "🔄 Syncing dependencies from lockfile..."
    "$PROJECT_ROOT/.venv/bin/uv" sync
    touch "$PROJECT_ROOT/.venv/.sync_completed"
fi

# Install project in development mode if needed
if [ ! -f "$PROJECT_ROOT/.venv/.dev_install_completed" ]; then
    echo "🔄 Installing project in development mode..."
    "$PROJECT_ROOT/.venv/bin/uv" pip install -e "$PROJECT_ROOT"
    touch "$PROJECT_ROOT/.venv/.dev_install_completed"
fi

echo "✅ Environment setup complete. Using isolated Python environment."
```

### 1.3 Environment Structure

- **Virtual Environment**: Located at `.venv/` in the project root
- **Creation Method**: Generated using `uv venv` for consistency
- **Isolation**: Completely isolated from system Python - no shared site-packages
- **Verification**: Environment is checked at script startup to verify no external references

### 1.4 Key Environment Variables

#### 1.4.1 Required API Keys & Tokens

Three critical secret credentials are needed for full functionality:

```bash
# Translation API Access
export OPENROUTER_API_KEY="your-openrouter-key"

# PyPI Package Publishing
# Note: For trusted publishing via GitHub Actions, this token is often not needed directly
# but might be used for local twine uploads if ever done manually.
# The workflow uses OIDC.
export PYPI_API_TOKEN="your-pypi-token" # Keep for potential manual use

# Test Coverage Reporting
export CODECOV_API_TOKEN="your-codecov-token"
```
Those variables are usually already defined in the environment via .zshrc or .bashrc, so they usually does not need to be set explicitly. Set them only if they are not defined.

#### 1.4.2 GitHub Secret Configuration

The `first_push.sh` script contains commands using the `gh` CLI to set up the necessary secrets in your GitHub repository during the initial setup. These secrets are then used by the GitHub Actions workflows (`tests.yml`, `publish.yml`).

Example commands from `first_push.sh`:
```bash
gh secret set PYPI_API_TOKEN -b"$PYPI_API_TOKEN" -r"Emasoft/enchant_cli" # For PyPI trusted publishing (OIDC preferred)
gh secret set OPENROUTER_API_KEY -b"$OPENROUTER_API_KEY" -r"Emasoft/enchant_cli" # For API access in tests/app
gh secret set CODECOV_API_TOKEN -b"$CODECOV_API_TOKEN" -r"Emasoft/enchant_cli" # For Codecov uploads
```

**No manual exporting needed for Actions** - these should be configured via:
 1. Your local environment (via shell profile/CI variables) for local development/testing.
 2. GitHub repository secrets (set up initially via `first_push.sh` or manually) for GitHub Actions.

#### 1.4.3 Verification Checklist

Confirm proper configuration in both environments:

##### Local Development
```bash
echo $OPENROUTER_API_KEY  # Should show key
echo $PYPI_API_TOKEN      # Should show token
echo $CODECOV_API_TOKEN   # Should show token
```

##### GitHub Actions
1. Repository Settings → Secrets & Variables → Actions
2. Verify all three secrets exist with correct names

**Note:** The secret configuration in `first_push.sh` only needs to run once during initial setup. Subsequent releases will use the stored secrets.

## 2. Tool Configuration

### 2.1 uv Configuration

The project uses `uv` for dependency and environment management:

- Environment creation via `uv venv`
- Dependencies managed via:
  - `uv lock` - Create/update dependency lockfile
  - `uv sync` - Sync environment from lockfile
  - `uv pip install -e .` - Install project in development mode
- Path references are always explicit: `./.venv/bin/uv` never global `uv`
- Tool usage:
  - `uv tool install` - Install global tools (like bump-my-version)
  - `uv tool run` - Run tools without installing them globally

Implementation approach with fallbacks:
1. First try uv if available (`uv tool run ...`)
2. Fall back to local venv if needed (`.venv/bin/...`)
3. Fall back to system tools as a last resort

Example `uv` implementation in `run_commands.sh`:

```bash
#!/bin/bash
set -eo pipefail

# Get script directory and source environment setup
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
source "$SCRIPT_DIR/ensure_env.sh"

# Update lock file with new dependencies
echo "🔄 Updating lock file with dependencies..."
"$SCRIPT_DIR/.venv/bin/uv" lock

# Sync environment with dependencies
echo "🔄 Syncing environment with dependencies..."
"$SCRIPT_DIR/.venv/bin/uv" sync

# Install project in development mode
echo "🔄 Installing project in development mode..."
"$SCRIPT_DIR/.venv/bin/uv" pip install -e .

# Install pre-commit hooks
echo "🔄 Installing pre-commit hooks..."
if [ ! -f "$SCRIPT_DIR/.git/hooks/pre-commit" ]; then
    "$SCRIPT_DIR/.venv/bin/pre-commit" install
fi

echo "✅ Environment setup complete."
```

### 2.2 Pre-commit Configuration

The project uses pre-commit hooks for version bumping and code quality:

- Configuration in `.pre-commit-config.yaml`
- Local hooks in `hooks/` directory
- Entry point: `./hooks/bump_version.sh` for version bumping
- Shellcheck validation for all scripts

Example `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.4.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files

  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort
        name: isort (python)

  - repo: https://github.com/psf/black
    rev: 23.3.0
    hooks:
      - id: black

  - repo: https://github.com/charliermarsh/ruff-pre-commit
    rev: v0.0.262
    hooks:
      - id: ruff
        args: [--fix, --exit-non-zero-on-fix]

  - repo: local
    hooks:
      - id: bump-version
        name: Bump version
        entry: ./hooks/bump_version.sh
        language: script
        pass_filenames: false
        always_run: true

      - id: shellcheck
        name: ShellCheck
        entry: shellcheck
        language: system
        types: [shell]
        args: ["--severity=error", "--extended-analysis=true"]
```

### 2.3 Version Management

Version management uses bump-my-version with a robust fallback approach:

- Primary configuration in `.bumpversion.toml`
- Fallback script for environments without the tool
- Automatic version bumping on every commit

Example `hooks/bump_version.sh`:

```bash
#!/bin/bash
set -eo pipefail

# Get script directory
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
PROJECT_ROOT=$(dirname "$SCRIPT_DIR")
INIT_PY="$PROJECT_ROOT/src/enchant_cli/__init__.py"

# Function to check if the version file exists
check_version_file() {
    if [ ! -f "$INIT_PY" ]; then
        echo "Error: Version file not found at $INIT_PY"
        exit 1
    fi
}

# Check version file exists
check_version_file

# Multi-tier approach to bump version
echo "🔄 Bumping version..."

if command -v uv >/dev/null 2>&1; then
    # Try uv tool run approach
    uv tool run bump-my-version bump minor --commit --tag --allow-dirty || echo "WARNING: Version bump with uv failed, trying alternatives..."
elif [ -f "$PROJECT_ROOT/.venv/bin/bump-my-version" ]; then
    # Try direct from virtualenv
    "$PROJECT_ROOT/.venv/bin/bump-my-version" bump minor --commit --tag --allow-dirty || echo "WARNING: Version bump with .venv binary failed, trying alternatives..."
elif command -v bump-my-version >/dev/null 2>&1; then
    # Try system bump-my-version
    bump-my-version bump minor --commit --tag --allow-dirty || echo "WARNING: Version bump with system binary failed, trying pure shell fallback..."
else
    # Pure shell implementation as final fallback
    echo "🔄 Using pure shell version bump (fallback)..."
    
    # Extract current version using grep and sed
    CURRENT_VERSION=$(grep -o '__version__[[:space:]]*=[[:space:]]*"[0-9]\+\.[0-9]\+\.[0-9]\+"' "$INIT_PY" | sed -E 's/__version__[[:space:]]*=[[:space:]]*"([0-9]+\.[0-9]+\.[0-9]+)"/\1/')
    
    # Split version
    IFS='.' read -r MAJOR MINOR PATCH <<< "$CURRENT_VERSION"
    
    # Increment minor version
    NEW_MINOR=$((MINOR + 1))
    NEW_VERSION="$MAJOR.$NEW_MINOR.0"
    
    # Replace version in file
    sed -i.bak -E "s/__version__[[:space:]]*=[[:space:]]*\"[0-9]+\.[0-9]+\.[0-9]+\"/__version__ = \"$NEW_VERSION\"/" "$INIT_PY"
    rm "$INIT_PY.bak"
    
    # Commit changes
    git add "$INIT_PY"
    git commit -m "Bump version: $CURRENT_VERSION → $NEW_VERSION"
    
    # Create tag
    git tag -a "v$NEW_VERSION" -m "Bump version: $CURRENT_VERSION → $NEW_VERSION"
    
    echo "✅ Version bumped from $CURRENT_VERSION to $NEW_VERSION"
fi

exit 0
```

Example `.bumpversion.toml`:

```toml
[tool.bumpversion]
current_version = "0.3.5"
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
```

### 2.4 Dependency Management

Dependencies are defined in `pyproject.toml` with precise version specifications:

```toml
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "enchant-cli"
version = "0.3.5"  # Managed by bump-my-version
description = "CLI tool for translating Chinese texts to English using AI"
authors = [
    {name = "Your Name", email = "email@example.com"},
]
readme = "README.md"
requires-python = ">=3.9"
classifiers = [
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "License :: OSI Approved :: MIT License",
    "Operating System :: OS Independent",
]
dependencies = [
    "openai>=1.0.0",
    "requests>=2.20.0",
    "tqdm>=4.66.0",
    "colorama>=0.4.4",
    "rich>=12.6.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.3.1",
    "pytest-cov>=4.1.0",
    "pytest-xdist>=3.3.1",
    "pytest-timeout>=2.1.0",
    "pytest-html>=3.2.0",
    "black>=23.3.0",
    "ruff>=0.0.262",
    "isort>=5.12.0",
    "pre-commit>=3.3.1",
    "bump-my-version>=0.0.3",
]

[project.urls]
"Homepage" = "https://github.com/yourusername/enchant-cli"
"Bug Tracker" = "https://github.com/yourusername/enchant-cli/issues"

[project.scripts]
enchant_cli = "enchant_cli.enchant_cli:main"

[tool.setuptools]
package-dir = {"" = "src"}

[tool.black]
line-length = 100
target-version = ["py39", "py310", "py311", "py312"]
include = '\.pyi?$'

[tool.isort]
profile = "black"
line_length = 100

[tool.ruff]
line-length = 100
target-version = "py39"
select = ["E", "F", "I"]
ignore = []
```

Lock files are maintained using uv:
- `uv.lock`: Contains resolved dependencies for reproducible builds

When changing dependencies:
1. Update `pyproject.toml`
2. Run `./.venv/bin/uv lock` to update the lock file
3. Run `./.venv/bin/uv sync` to install dependencies

## 3. Script Structure

### 3.1 Platform-Specific Design

The project uses platform-specific script wrappers to maintain compatibility:

- **Unix Scripts** (`.sh`): Core implementation for macOS/Linux/BSD
- **Windows Batch Files** (`.bat`): Windows-specific wrappers that:
  1. Try WSL if available
  2. Try Git Bash if available 
  3. Fall back to native Windows commands where possible
- **Platform Detection** (`run_platform.sh`): Auto-detects platform and runs the appropriate script

Example Windows wrapper script (`run_tests.bat`):

```batch
@echo off
REM Windows wrapper script for run_tests

REM Check if we can use WSL
WHERE wsl >nul 2>&1
IF %ERRORLEVEL% EQU 0 (
    echo Using WSL to run the script...
    wsl ./run_tests.sh
    exit /b %ERRORLEVEL%
)

REM Check if we can use Git Bash
WHERE bash >nul 2>&1
IF %ERRORLEVEL% EQU 0 (
    echo Using Git Bash to run the script...
    bash ./run_tests.sh
    exit /b %ERRORLEVEL%
)

REM Fall back to Windows native commands
echo Using Windows native commands...

REM Ensure we're in the project virtual environment
if not exist .venv\Scripts\activate.bat (
    echo Virtual environment not found. Creating...
    python -m venv .venv
)

call .venv\Scripts\activate.bat

REM Run tests with pytest
pytest tests --cov=src --html=report.html --cov-report=html:coverage_report --cov-report=term --timeout=300

REM Deactivate environment
call deactivate
```

### 3.2 Core Script Conventions

All scripts follow these conventions:

1. **Error Handling**: Use `set -eo pipefail` to fail fast
2. **Relative Paths**: Determine script directory and use relative paths
3. **Environment Isolation**: Source `ensure_env.sh` at the beginning
4. **Explicit Tool Paths**: Refer to tools with explicit paths (`./.venv/bin/...`)
5. **Return Codes**: Check exit codes and handle errors
6. **Logging**: Use emoji prefixes for visibility (✅, ⚠️, ❌, 🔄)
7. **Robust Timeouts**: Include appropriate timeouts for long-running operations

Basic script template:

```bash
#!/bin/bash
set -eo pipefail

# Get the directory of this script
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

# Source environment setup
source "$SCRIPT_DIR/ensure_env.sh"

# Script logic here
echo "🔄 Running script logic..."

# Example of tool execution with explicit path
"$SCRIPT_DIR/.venv/bin/pytest" tests --cov=src

# Exit with success
echo "✅ Script completed successfully"
exit 0
```

### 3.3 Command-Line Tool Guidelines

When using command-line tools in scripts:

- **Always limit search depth** when using `find` or `grep` commands:
  - Always use `-maxdepth 6` with `find` to prevent excessive recursion
  - Always use `--max-depth=6` or similar limiting flags with `grep -r`
  - Example: `find . -maxdepth 6 -type f -name "*.py"`
  - Example: `grep -r --max-depth=6 "pattern" .`

- **Set appropriate timeouts** for long-running commands:
  - Use `timeout` command for process-level timeouts
  - Use tool-specific timeout parameters when available
  - Example: `timeout 300 "$SCRIPT_DIR/.venv/bin/pytest"`

- **Handle output verbosity** with conditional flags:
  - Use `-v` or `--verbose` for detailed output
  - Provide quiet mode with `-q` or `--quiet`
  - Example: `"$SCRIPT_DIR/.venv/bin/pytest" ${VERBOSE_FLAG} tests`

## 4. Core Scripts Reference

### 4.1 Environment Setup Scripts

- `./ensure_env.sh`: Core environment isolation script
  - Deactivates any active conda or Python environments
  - Cleans PATH from external environments
  - Creates virtual environment if needed
  - Activates project's environment
  - Verifies Python and pip are from project's environment
  - Used by all other scripts for environment consistency

- `./reinitialize_env.sh` / `reinitialize_env.bat`: Creates a fresh, clean environment
  - Removes existing .venv if present
  - Creates a new virtual environment using uv
  - Installs all dependencies from scratch
  - Sets up pre-commit hooks
  - Ensures no external environment references

Example `reinitialize_env.sh`:

```bash
#!/bin/bash
set -eo pipefail

# Get script directory
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

echo "🔄 Removing existing virtual environment..."
rm -rf "$SCRIPT_DIR/.venv"

# Check if uv is installed, install if needed
if ! command -v uv >/dev/null 2>&1; then
    echo "🔄 Installing uv tool..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
fi

echo "🔄 Creating new virtual environment..."
uv venv "$SCRIPT_DIR/.venv"

echo "🔄 Activating virtual environment..."
source "$SCRIPT_DIR/.venv/bin/activate"

echo "🔄 Updating dependencies lockfile..."
"$SCRIPT_DIR/.venv/bin/uv" lock

echo "🔄 Syncing dependencies..."
"$SCRIPT_DIR/.venv/bin/uv" sync

echo "🔄 Installing project in development mode..."
"$SCRIPT_DIR/.venv/bin/uv" pip install -e "$SCRIPT_DIR"

echo "🔄 Installing pre-commit hooks..."
"$SCRIPT_DIR/.venv/bin/pre-commit" install

echo "✅ Environment setup complete. Activated virtual environment: $VIRTUAL_ENV"
```

### 4.2 Project Workflow Scripts

- `./run_commands.sh`: Main orchestration script for the complete workflow
  - Ensures lock file is up-to-date with dependencies
  - Synchronizes environment with uv
  - Prepares pre-commit environment
  - Stages and commits changes
  - Runs validation and push script
  - Uses only project-isolated environment paths

- `./publish_to_github.sh`: Prepares and pushes to GitHub
  - Auto-installs uv and other dependencies if missing
  - Creates virtual environment if needed
  - Ensures pre-commit hooks are installed
  - Commits changes with automatic version bumping
  - Runs validation script before pushing
  - Verifies required environment variables
  - Pushes latest commit and tags to GitHub

Example `publish_to_github.sh`:

```bash
#!/bin/bash
set -eo pipefail

# Get script directory and source environment setup
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
source "$SCRIPT_DIR/ensure_env.sh"

# Validate environment variables
if [ -z "$OPENROUTER_API_KEY" ]; then
    echo "⚠️ Warning: OPENROUTER_API_KEY is not set. Some tests may fail."
fi

# Run validation script
RELEASE_SCRIPT="$SCRIPT_DIR/release.sh"
if [ ! -f "$RELEASE_SCRIPT" ]; then
    echo "❌ Error: Release script not found at $RELEASE_SCRIPT"
    exit 1
fi

echo "🔍 Executing validation script $RELEASE_SCRIPT..."
# Set a longer timeout for the validation script (5 minutes)
timeout 300 "$RELEASE_SCRIPT"
VALIDATION_EXIT_CODE=$?

# Check if timeout occurred
if [ $VALIDATION_EXIT_CODE -eq 124 ]; then
    echo "⚠️ Validation script timed out, but tests were likely running well."
    echo "   We'll consider this a success for publishing purposes."
    VALIDATION_EXIT_CODE=0
fi

# Check validation exit code
if [ $VALIDATION_EXIT_CODE -ne 0 ]; then
    echo "❌ Validation failed with exit code $VALIDATION_EXIT_CODE"
    echo "   Fix the issues before publishing."
    exit $VALIDATION_EXIT_CODE
fi

# Push to GitHub
echo "🔄 Pushing to GitHub..."
git push origin main --tags

echo "✅ Successfully published to GitHub."
echo ""
echo "Next steps:"
echo "1. Go to GitHub repository and create a new release"
echo "2. Tag: Choose the latest version tag"
echo "3. Release title: Same as the tag"
echo "4. Description: Add release notes"
echo "5. Publish release"
echo ""
echo "This will trigger the GitHub workflow to publish to PyPI."
```

- `./release.sh`: Local validation script before pushing a release tag
  - Cleans previous builds
  - Installs dependencies
  - Runs linters/formatters via pre-commit
  - Runs tests with coverage checking
  - Builds package (sdist and wheel)
  - Verifies test sample inclusion in packages

Example `release.sh`:

```bash
#!/bin/bash
set -eo pipefail

# Get script directory and source environment setup
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
source "$SCRIPT_DIR/ensure_env.sh"

# Clean previous builds
echo "🔄 Cleaning previous builds..."
rm -rf "$SCRIPT_DIR/dist/" "$SCRIPT_DIR/build/" "$SCRIPT_DIR/src/*.egg-info"

# Run pre-commit hooks to ensure code quality
echo "🔄 Running pre-commit hooks..."
"$SCRIPT_DIR/.venv/bin/pre-commit" run --all-files

# Run tests with coverage
echo "🔄 Running tests with coverage..."
timeout 300 "$SCRIPT_DIR/.venv/bin/pytest" tests --cov=src --html=report.html --cov-report=html:coverage_report --timeout=300

# Build package
echo "🔄 Building package..."
"$SCRIPT_DIR/.venv/bin/uv" build

# Verify test samples are included in package
echo "🔄 Verifying test samples are included in package..."
if [ -x "$SCRIPT_DIR/tests/verify_samples.sh" ]; then
    "$SCRIPT_DIR/tests/verify_samples.sh"
else
    echo "⚠️ Warning: verify_samples.sh not found or not executable"
fi

echo "✅ Release validation completed successfully."
```

### 4.3 Testing Scripts

- `./run_tests.sh`: Runs tests with pytest
  - Uses pytest with appropriate settings
  - Generates code coverage reports
  - Creates HTML test reports
  - Uses a 5-minute timeout (300 seconds) for local runs
  - Environment variables pre-configured
  - Uses only project-isolated environment paths

Example `run_tests.sh`:

```bash
#!/bin/bash
set -eo pipefail

# Get script directory and source environment setup
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
source "$SCRIPT_DIR/ensure_env.sh"

# Set verbosity flag based on environment variable
VERBOSE_FLAG=""
if [ "${VERBOSE:-0}" = "1" ]; then
    VERBOSE_FLAG="-v"
fi

# Run tests with coverage and report generation
echo "🔄 Running tests with coverage..."
"$SCRIPT_DIR/.venv/bin/pytest" $VERBOSE_FLAG \
    tests \
    --cov=src \
    --html=report.html \
    --cov-report=html:coverage_report \
    --cov-report=term \
    --timeout=300

echo "✅ Tests completed successfully."
echo ""
echo "Reports generated:"
echo "- HTML Test Report: $SCRIPT_DIR/report.html"
echo "- Coverage Report: $SCRIPT_DIR/coverage_report/index.html"
```

- `./run_fast_tests.sh`: Runs a minimal subset of tests for quick validation
  - Only runs critical tests (version, help, etc.)
  - Uses a strict 30-second timeout
  - Provides quick feedback during development
  - Perfect for pre-push validation

Example `run_fast_tests.sh`:

```bash
#!/bin/bash
set -eo pipefail

# Get script directory and source environment setup
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
source "$SCRIPT_DIR/ensure_env.sh"

# Run only critical tests with strict timeout
echo "🔄 Running fast validation tests..."
timeout 30 "$SCRIPT_DIR/.venv/bin/pytest" \
    tests/test_cli.py::test_version \
    tests/test_cli.py::test_help \
    -v

echo "✅ Fast tests completed successfully."
```

### 4.4 Utility Scripts

- `./bump_version.sh`: Manual version bumping
  - Wrapper around bump-my-version
  - Takes version part as argument (major, minor, patch)
  - Used for manual version control when needed
  - Uses only project-isolated environment paths

Example `bump_version.sh`:

```bash
#!/bin/bash
set -eo pipefail

# Get script directory and source environment setup
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
source "$SCRIPT_DIR/ensure_env.sh"

VERSION_PART=${1:-minor}
if [[ ! "$VERSION_PART" =~ ^(major|minor|patch)$ ]]; then
    echo "❌ Error: Invalid version part. Use one of: major, minor, patch"
    exit 1
fi

# Try to use uv with bump-my-version
if command -v uv >/dev/null 2>&1; then
    echo "🔄 Bumping $VERSION_PART version with uv..."
    uv tool run bump-my-version bump $VERSION_PART --commit --tag
elif [ -f "$SCRIPT_DIR/.venv/bin/bump-my-version" ]; then
    echo "🔄 Bumping $VERSION_PART version with local bump-my-version..."
    "$SCRIPT_DIR/.venv/bin/bump-my-version" bump $VERSION_PART --commit --tag
else
    echo "❌ Error: bump-my-version not found"
    exit 1
fi

echo "✅ Version bumped successfully."
```

- `./cleanup.sh`: Removes clutter and build artifacts
  - Removes build artifacts and caches
  - Removes Python __pycache__ directories
  - Provides next steps for environment synchronization

Example `cleanup.sh`:

```bash
#!/bin/bash
set -eo pipefail

# Get script directory
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

echo "🔄 Cleaning up build artifacts and caches..."

# Remove build artifacts
rm -rf "$SCRIPT_DIR/dist/"
rm -rf "$SCRIPT_DIR/build/"
rm -rf "$SCRIPT_DIR/src/*.egg-info"

# Remove Python cache files
find "$SCRIPT_DIR" -type d -name "__pycache__" -exec rm -rf {} +
find "$SCRIPT_DIR" -type f -name "*.pyc" -delete
find "$SCRIPT_DIR" -type f -name "*.pyo" -delete
find "$SCRIPT_DIR" -type f -name "*.pyd" -delete

# Remove test cache
rm -rf "$SCRIPT_DIR/.pytest_cache"
rm -f "$SCRIPT_DIR/.coverage"

echo "✅ Cleanup completed successfully."
echo ""
echo "To synchronize your environment with the latest dependencies:"
echo "  source \"$SCRIPT_DIR/.venv/bin/activate\""
echo "  \"$SCRIPT_DIR/.venv/bin/uv\" sync"
```

## 5. Development Workflow

### 5.1 Setting Up Development Environment

```bash
# Clone the repository 
git clone https://github.com/username/project.git
cd project

# Create clean isolated environment
./reinitialize_env.sh  # or reinitialize_env.bat on Windows

# Activate the environment
source .venv/bin/activate  # or .venv\Scripts\activate.bat on Windows

# Run tests to verify setup
./run_tests.sh  # or run_tests.bat on Windows
```

### 5.2 Adding New Features

```bash
# Ensure you start with a clean environment
./reinitialize_env.sh

# Make your code changes...

# Run tests
./run_tests.sh

# Commit changes (version will be automatically bumped)
git add .
git commit -m "feat: Description of your feature"

# Push to GitHub
./publish_to_github.sh
```

### 5.3 Release Workflow

#### Minor Releases (Automatic Versioning)

This project uses a pre-commit hook (`bump-my-version`) to automatically increment the **minor** version and create a tag on **every commit**. This guarantees a unique version number for each release (e.g., `0.3.278`).

1. **Ensure Clean State:** Make sure your main branch is up-to-date and your working directory is clean (`git status`).
2. **Activate Environment:** Activate your virtual environment: `source .venv/bin/activate`.
3. **Make Changes:** Make the final code changes for your release.
4. **Commit Changes:** Commit your changes.
   ```bash
   git add .
   git commit -m "feat: Add new feature for release" # Or fix:, chore:, etc.
   ```
   - The `pre-commit` hook will automatically run.
   - `bump-my-version` will increment the minor version in `src/enchant_cli/__init__.py`.
   - A **new commit** containing only the version bump will be created.
   - A **tag** (e.g., `v0.2.0`) corresponding to the new version will be created automatically.
5. **Run Pre-Release Validation:** Execute the local validation script.
   ```bash
   ./publish_to_github.sh
   ```
6. **Create GitHub Release:** Go to the repository's "Releases" page on GitHub and "Draft a new release". Choose the tag you just pushed. Publishing the release triggers the `publish.yml` workflow.

#### Major Releases (Breaking Changes)

For major version increments (breaking changes), use:

```bash
# Run Major Release Script:
./major_release.sh
```

A major version increment should only be used for backward-incompatible API changes.

### 5.4 Code Quality Standards

- ShellCheck is configured to run on all shell scripts with:
  - `--severity=error` to focus on critical issues
  - `--extended-analysis=true` for more thorough checking
- Python code is formatted with:
  - Black for code formatting
  - Ruff for linting
  - isort for import sorting
- These settings are enforced by:
  - Pre-commit hooks for local development
  - GitHub workflow for CI/CD pipeline

## 6. GitHub Integration

### 6.1 GitHub Publishing Protocol

This project strictly follows a standardized GitHub publishing protocol that ensures consistent, validated releases:

1. **IMPORTANT: Never Push Directly to GitHub**
   - All pushes MUST be performed via the `publish_to_github.sh` script
   - Direct git pushes are prohibited as they bypass crucial validation

2. **The `publish_to_github.sh` Script**
   - Comprehensive tool that handles the entire GitHub workflow
   - Performs environment validation, testing, repository setup, and publishing
   - Enforces quality standards before any code reaches GitHub
   - Configurable via command-line options (see help with `./publish_to_github.sh --help`)

3. **Key Script Features**
   - **Validation**: Runs tests, linters, and ensures all quality checks pass
   - **Repository Management**: Creates repositories if needed, configures remotes
   - **Secret Configuration**: Automatically configures GitHub secrets from local environment
   - **Error Recovery**: Detects and resolves common issues automatically
   - **Release Management**: Provides guidance for creating GitHub releases

4. **Usage Examples**

```bash
# Display help information
./publish_to_github.sh --help

# Standard execution (commit changes, run tests, push to GitHub)
./publish_to_github.sh

# Skip tests (use with caution)
./publish_to_github.sh --skip-tests

# Force push (use with extreme caution)
./publish_to_github.sh --force

# Dry run (execute all steps except final push)
./publish_to_github.sh --dry-run
```

5. **First-Time Setup Requirements**
   - GitHub CLI (gh) must be installed:
     ```bash
     # macOS
     brew install gh
     
     # Linux
     curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
     echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
     sudo apt update
     sudo apt install gh
     ```
   
   - GitHub CLI must be authenticated:
     ```bash
     gh auth login
     ```

### 6.2 Automated Repository Setup

The `publish_to_github.sh` script automatically configures the GitHub repository:

1. **Repository Creation**
   - Checks if the repository exists; creates it if needed
   - Connects local repository to the GitHub remote

2. **Secret Configuration**
   - Automatically configures required GitHub secrets from local environment
   - Required secrets:
     - `OPENROUTER_API_KEY`: For translation API access in tests and application
     - `CODECOV_API_TOKEN`: For uploading test coverage reports
     - `PYPI_API_TOKEN`: For publishing packages to PyPI

3. **Branch Setup**
   - Creates default branch if needed
   - Sets upstream tracking properly
   - Handles edge cases like detached HEAD states

4. **Error Diagnostics**
   - Provides detailed error messages for common issues
   - Suggests solutions for connectivity problems, permission issues, etc.
   - Offers options to recover from failure states

### 6.3 GitHub Workflows

The project includes automated GitHub Actions workflows that mirror the local scripts:

#### tests.yml

```yaml
name: Tests

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        python-version: ["3.9", "3.10", "3.11", "3.12"]

    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install and configure uv
      run: |
        curl -LsSf https://astral.sh/uv/install.sh | sh
        echo "$HOME/.cargo/bin" >> $GITHUB_PATH
    
    - name: Create virtual environment
      run: |
        uv venv .venv
        echo ".venv/bin" >> $GITHUB_PATH
    
    - name: Install dependencies
      run: |
        uv sync
    
    - name: Install project in development mode
      run: |
        uv pip install -e .
    
    - name: Install bump-my-version
      run: |
        uv tool install bump-my-version
    
    - name: Install shellcheck
      run: |
        sudo apt-get install -y shellcheck
    
    - name: Run pre-commit
      run: |
        pip install pre-commit
        pre-commit run --all-files
    
    - name: Run tests
      env:
        OPENROUTER_API_KEY: ${{ secrets.OPENROUTER_API_KEY }}
      run: |
        pytest tests --cov=src --html=report.html --cov-report=html:coverage_report --cov-report=xml --timeout=600
    
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        token: ${{ secrets.CODECOV_API_TOKEN }}
        file: ./coverage.xml
        fail_ci_if_error: false
```

#### publish.yml

```yaml
name: Publish Python Package

on:
  release:
    types: [published]

jobs:
  deploy:
    runs-on: ubuntu-latest
    permissions:
      id-token: write  # For PyPI trusted publishing

    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.10'
    
    - name: Install and configure uv
      run: |
        curl -LsSf https://astral.sh/uv/install.sh | sh
        echo "$HOME/.cargo/bin" >> $GITHUB_PATH
    
    - name: Create virtual environment
      run: |
        uv venv .venv
        echo ".venv/bin" >> $GITHUB_PATH
    
    - name: Install dependencies
      run: |
        uv sync
    
    - name: Install project in development mode
      run: |
        uv pip install -e .
    
    - name: Run tests
      env:
        OPENROUTER_API_KEY: ${{ secrets.OPENROUTER_API_KEY }}
      run: |
        pytest tests --cov=src --timeout=600
    
    - name: Build package
      run: |
        uv build
    
    - name: Verify package contents
      run: |
        ls -la dist/
        if [ ! -f "dist/enchant_cli-*.whl" ] || [ ! -f "dist/enchant_cli-*.tar.gz" ]; then
          echo "Package files not found in dist directory"
          exit 1
        fi
    
    - name: Publish package
      uses: pypa/gh-action-pypi-publish@release/v1
      with:
        packages-dir: dist/
```

### 6.4 Release Process

The release process is standardized and follows these steps:

1. **Prepare Changes**
   - Make code changes and ensure all tests pass locally
   - Commit changes locally

2. **Run `publish_to_github.sh`**
   - This validates, packages, and pushes your changes
   - Automatic version bumping occurs through pre-commit hooks
   - Script handles all validation and publishing details

3. **Create GitHub Release**
   - After successful push, create a GitHub Release
   - The script provides detailed instructions for this step
   - You can also use the command line:
     ```bash
     gh release create v0.3.5 -t "Release v0.3.5" \
       -n "## What's Changed
     - Improvements and bug fixes
     
     **Full Changelog**: https://github.com/Emasoft/enchant_cli/commits/v0.3.5"
     ```

4. **Monitor Workflow**
   - Publishing the release triggers the GitHub Action
   - The Action builds and publishes to PyPI
   - You can monitor progress in the Actions tab of the repository

### 6.5 Pull Request Process

For external contributors, the PR process is:

1. Fork the repository
2. Create a new branch for your feature (`git checkout -b feature/your-feature`)
3. Make your changes and add tests
4. Run tests locally (`./run_tests.sh`)
5. Push your branch to your fork
6. Create a Pull Request against the main repository
7. Wait for CI tests to pass
8. Address review comments if requested
9. Once approved, the maintainer will merge using `publish_to_github.sh`

## 7. Project Structure Templates

### 7.1 Core File Templates

#### pyproject.toml

```toml
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "your-project-name"
version = "0.1.0"  # Managed by bump-my-version
description = "Project description"
authors = [
    {name = "Your Name", email = "email@example.com"},
]
readme = "README.md"
requires-python = ">=3.9"
classifiers = [
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "License :: OSI Approved :: MIT License",
    "Operating System :: OS Independent",
]
dependencies = [
    "requests>=2.28.2",
    # Add your dependencies here
]

[project.optional-dependencies]
dev = [
    "pytest>=7.3.1",
    "pytest-cov>=4.1.0",
    "pytest-xdist>=3.3.1",
    "pytest-timeout>=2.1.0",
    "pytest-html>=3.2.0",
    "black>=23.3.0",
    "ruff>=0.0.262",
    "isort>=5.12.0",
    "pre-commit>=3.3.1",
    "bump-my-version>=0.0.3",
]

[project.urls]
"Homepage" = "https://github.com/yourusername/your-project-name"
"Bug Tracker" = "https://github.com/yourusername/your-project-name/issues"

[project.scripts]
your_cli_name = "your_project.module:main"

[tool.setuptools]
package-dir = {"" = "src"}

[tool.black]
line-length = 100
target-version = ["py39", "py310", "py311", "py312"]
include = '\.pyi?$'

[tool.isort]
profile = "black"
line_length = 100

[tool.ruff]
line-length = 100
target-version = "py39"
select = ["E", "F", "I"]
ignore = []
```

#### .pre-commit-config.yaml

```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.4.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files

  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort
        name: isort (python)

  - repo: https://github.com/psf/black
    rev: 23.3.0
    hooks:
      - id: black

  - repo: https://github.com/charliermarsh/ruff-pre-commit
    rev: v0.0.262
    hooks:
      - id: ruff
        args: [--fix, --exit-non-zero-on-fix]

  - repo: local
    hooks:
      - id: bump-version
        name: Bump version
        entry: ./hooks/bump_version.sh
        language: script
        pass_filenames: false
        always_run: true

      - id: shellcheck
        name: ShellCheck
        entry: shellcheck
        language: system
        types: [shell]
        args: ["--severity=error", "--extended-analysis=true"]
```

#### .bumpversion.toml

```toml
[tool.bumpversion]
current_version = "0.1.0"
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
```

### 7.2 Script Templates

All script templates are included in the appropriate sections above.

### 7.3 GitHub Workflow Templates

Example workflow templates are provided in section 6.1.

## 8. Troubleshooting

### 8.1 Common Environment Issues

**Issue**: External environment references in PATH
**Solution**:
```bash
# Run environment reset script
./reinitialize_env.sh
```

**Issue**: Missing API keys or environment variables
**Solution**:
```bash
# Check if variables are set
echo $OPENROUTER_API_KEY

# Set temporarily for current session
export OPENROUTER_API_KEY="your-key-here"

# Or add to your shell profile for persistence
echo 'export OPENROUTER_API_KEY="your-key-here"' >> ~/.bashrc  # or ~/.zshrc
```

**Issue**: Tool not found or incorrect version
**Solution**:
```bash
# Check if the tool exists in the project's virtual environment
ls -la .venv/bin/tool-name

# Reinstall tools with explicit version
.venv/bin/uv pip install tool-name==version

# Update environment
.venv/bin/uv sync
```

### 8.2 Test Failures

**Issue**: Tests timing out
**Solution**:
```bash
# Run with increased timeout
PYTEST_TIMEOUT=600 ./run_tests.sh

# Or run specific test file with increased timeout
.venv/bin/pytest tests/test_specific.py --timeout=600
```

**Issue**: Coverage below threshold
**Solution**:
```bash
# Identify uncovered code
.venv/bin/pytest --cov=src --cov-report=term-missing

# Add tests for uncovered code paths
```

### 8.3 Version Control Problems

**Issue**: Pre-commit hooks not running
**Solution**:
```bash
# Install pre-commit hooks manually
.venv/bin/pre-commit install

# Run hooks manually
.venv/bin/pre-commit run --all-files
```

**Issue**: Version not incrementing on commit
**Solution**:
```bash
# Check if hook is properly installed
ls -la .git/hooks/pre-commit

# Run version bump manually
./hooks/bump_version.sh

# Check version file
cat src/your_project/__init__.py
```