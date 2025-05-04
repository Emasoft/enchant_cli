# CLAUDE.md

## 1. Project Understanding
1.1. Analyze the project's purpose and goals thoroughly before writing code
1.2. Ask clarifying questions if the project requirements are unclear
1.3. Confirm understanding of the frameworks and API used by the project before implementation
1.4. Verify the environment and virtual environment configuration before writing any code
1.5. Prioritize user experience in UI/UX implementations

## 2. Development Environment Setup
2.1. Use Node.js version 18.x or higher or Python 3.10+ as required by the project
2.2. Install all development dependencies using the appropriate package manager (`npm install`, `pip install -r requirements.txt`, etc.)
2.3. Set up environment variables according to `.env.example`
2.4. For Python projects using uv:
   2.4.1. Always create a virtual environment in `.venv` folder for Linux/Mac/BSD systems
   2.4.2. Always create a virtual environment in `.venv_windows` folder for Windows systems
   2.4.3. If the project must be compatible with both platforms, configure both `.venv` and `.venv_windows`
   2.4.4. Always install all tools and binaries into these virtual environments folders to ensure project portability
   2.4.5. Always use uv for every operation in the project environment and to setup the package configuration
2.5. For Conda-based projects:
   2.5.1. Use conda commands to create a virtual environment with the exact same name as the project folder
   2.5.2. Example: `conda create -n project_name python=3.10`
   2.5.3. Ensure proper Python runtime is specified during environment creation
   2.5.4. Activate with `conda activate project_name`
   2.5.5. Never mix pip/uv and conda for installing packages
   2.5.6. Always run `conda info` and `conda doctor` first to understand the environment
2.6. If using VS Code, install the recommended extensions in `.vscode/extensions.json`
2.7. If using GitHub, install the gh CLI within the virtual environment
2.8. Configure linting and formatting tools within the project's virtual environment as uv tools
2.9. Ensure all tools are installed with relative paths, and that relative paths are used in the dev scripts to keep the project folder or repo relocatable on any dir or computer or docker container

## 3. File Structure
3.1. Follow this standard directory structure precisely:
```
project_root/
├── .venv/                # Virtual environment for Linux/Mac/BSD
├── .venv_windows/        # Virtual environment for Windows
├── src/                  # Source code
│   ├── components/       # Reusable UI components
│   ├── services/         # Business logic and API services
│   ├── utils/            # Helper functions and utilities
│   └── main.py           # Application entry point
├── tests/                # All tests MUST be placed here
│   ├── unit/             # Unit tests
│   ├── integration/      # Integration tests
│   └── e2e/              # End-to-end tests
├── docs/                 # Documentation
├── scripts/              # temp scripts
├── DHT/                  # Development Helpers Toolkit (permanent scripts reusable in other projects)
├── config/               # Configuration files
├── data/                 # Data files (sample data, fixtures)
├── assets/               # Static assets
├── tasks_checklist.md    # Task tracking
├── requirements.txt      # Python dependencies
├── setup.py              # Package setup
├── .gitignore            # Git ignore file
└── README.md             # Project overview
```
3.2. Always use relative paths from the project root in all code and configuration files
3.3. Example of correct path usage: `./src/utils/helpers.py` instead of absolute paths
3.4. Never hardcode absolute paths that would break portability
3.5. Place all tests exclusively in the `./tests` folder, organized by test type
3.6. Document any new directories thoroughly
3.7. Use barrel files (`index.js` or `__init__.py`) for clean exports
3.8. Keep component-specific resources with their respective components

## 4. Coding Standards
4.1. Write clean, readable code with clear variable names
4.2. Follow the project's naming conventions consistently
4.3. Use camelCase for JavaScript variables and functions, PascalCase for components and classes
4.4. Use snake_case for Python variables and functions, PascalCase for classes
4.5. Comment complex logic thoroughly with JSDoc or docstring style comments
4.6. Keep functions pure and small, ideally under 30 lines
4.7. Use type hints for all functions and variables (TypeScript or Python type annotations)
4.8. Handle errors explicitly with try/catch blocks
4.9. Always use relative paths for imports and file operations
4.10. Avoid any hardcoded values, use constants and environment variables
4.11. Follow the DRY (Don't Repeat Yourself) principle
4.12. Ensure accessibility standards are met for all UI components
4.13. CRITICAL: NEVER modify the translation model from "deepseek/deepseek-r1:nitro" as the prompts have been meticulously calibrated for this specific model for optimal results
4.14. CRITICAL: For ANY change to the implementation of core functionality (especially in translation methods), you MUST ask for explicit approval before making the change. This includes changes to the translation pipeline, prompt engineering, or API integrations
4.15. CRITICAL: Never replace carefully calibrated prompts or API integrations without explicit permission. These have been meticulously optimized over long periods of time

## 5. Task Management
5.1. All tasks planned and completed must be tracked in `tasks_checklist.md` in the project root, which must include a legend explaining the meaning of all emoji status indicators
5.2. Each task must have a unique progressive number that is never reused
5.3. Use the following emoji system to mark task status by placing the emoji INSIDE the checkbox:
   5.3.1. - [🕐] = TODO - Task planned but not yet started
   5.3.2. - [📋] = Planning TDD - Designing tests before implementation
   5.3.3. - [✏️] = Tests writing in progress - Writing test cases
   5.3.4. - [💻] = Coding in progress - Active development
   5.3.5. - [🧪] = Running tests - Testing implementation
   5.3.6. - [🪲] = BUG FIXING - Debugging in progress
   5.3.7. - [⏸️] = Paused - Temporarily on hold
   5.3.8. - [🚫] = Blocked by one or more github issues
   5.3.9. - [🗑️] = Cancelled - Task will not be completed
   5.3.10. - [❎] = Replaced - Superseded by another task
   5.3.11. - [✅] = Completed - Task finished successfully
   5.3.12. - [❌] = Tests for this task failed
   5.3.13. - [🚷] = Cannot proceed due to dependency. Waiting for completion of other tasks
5.4. Include creation timestamp and last updated timestamp for each task
5.5. Example task format:
```markdown
- [💻] #42 - Implement user authentication
  - Created: 2023-04-22 15:30
  - Updated: 2023-04-23 10:45
  - Branch: feature/user-auth
  - Tests Attempts: PASS=9999 FAIL=9999
  - Blocked by github issues : #123 #189
  - Replaced by task : none
  - Waiting for the completion of task: none
  - Additional Notes: Add JWT-based authentication system
```
5.6. Always update the task status when progress is made
5.7. Request explicit permission from the user before adding new tasks
5.8. Include references to GitHub issues with direct links when applicable
5.9. Include the Git branch name where the task is being implemented
5.10. Maintain chronological order with newest tasks at the bottom
5.11. Include a legend at the top of the file explaining all emoji statuses:
```markdown
# Tasks Checklist

## Status Legend
- [🕐] = TODO - Task planned but not yet started
- [📋] = Planning TDD - Designing tests before implementation
- [✏️] = Tests writing in progress - Writing test cases
- [💻] = Coding in progress - Active development
- [🧪] = Running tests - Testing implementation
- [🪲] = BUG FIXING - Debugging in progress
- [⏸️] = Paused - Temporarily on hold
- [🚫] = Blocked by one or more github issues
- [🗑️] = Cancelled - Task will not be completed
- [❎] = Replaced - Superseded by another task
- [✅] = Completed - Task finished successfully
- [❌] = Tests for this task failed
- [🚷] = Cannot proceed due to dependency. Waiting for completion of other tasks

```

## 6. Workflow Instructions
6.1. Start each development session by pulling the latest changes
6.2. Create a new branch for each feature or fix using the pattern: `type/description` (e.g., `feature/user-authentication`)
6.3. Before any git operation that could modify the working directory (checkout, rebase, pull, stash, etc.):
   6.3.1. Create a backup of the entire project folder including untracked files
   6.3.2. Save the backup as a zip file in the project's backups directory with timestamp: `backups/project_name_YYYY-MM-DD_HHMMSS.zip`
   6.3.3. Example command: `mkdir -p backups && zip -r backups/project_name_$(date +%Y-%m-%d_%H%M%S).zip .`
   6.3.4. CRITICAL: Never lose important untracked files due to git operations like branch switching. Always backup and refer to backups/README.md for restoration instructions.
6.4. Commit changes with clear, descriptive messages following the Conventional Commits standard
6.5. Write tests before implementing features (TDD approach)
6.6. Run linting and tests before pushing changes
6.7. Request code reviews from a headless independent instance of Claude Code
6.8. Address code review comments promptly
6.9. Document all API changes in the API documentation file: "./docs/api.md"
6.10. Update the changelog and "./tasks_checklist.md" for all significant changes

## 7. Testing Instructions
7.1. Write all tests in the `./tests` directory organized by test type:
   7.1.1. Unit tests in `./tests/unit/`
   7.1.2. Integration tests in `./tests/integration/`
   7.1.3. End-to-end tests in `./tests/e2e/`
7.2. Create unit tests for all business logic
7.3. Implement integration tests for API endpoints
7.4. Create end-to-end tests for critical user flows
7.5. Use appropriate testing frameworks based on the project (Jest, PyTest, etc.)
7.6. Maintain at least 98% test coverage
7.7. Mock external dependencies in tests
7.8. Test edge cases and error scenarios
7.9. Run tests locally before pushing code
7.10. Use TDD (Test-Driven Development) for every new feature added
7.11. Do not mock the functions if they are required by the tests but are yet not written. Write all missing functions, not the mockup but the complete true working functions, following the TDD methodology.

## 8. Documentation Requirements
8.1. Document all functions with JSDoc comments or appropriate docstrings
8.2. Update README.md with any new features or changes
8.3. Keep API documentation current and complete
8.4. Document all environment variables and their purposes
8.5. Include setup instructions for new dependencies
8.6. Document any database schema changes
8.7. Create or update user guides for new features
8.8. Add detailed comments for complex logic or algorithms
8.9. Document known issues and their workarounds
8.10. Keep the changelog up to date. If possible use a git hook or a DHT command and a github workfow to automate the writing of the changelog.

## 9. Version Control
9.1. Use Git for version control
9.2. Follow the Gitflow workflow
9.3. Name branches according to the pattern: `type/description` (e.g., `feature/user-authentication`)
9.4. Write descriptive commit messages following the Conventional Commits standard:
   ```
   feat(auth): implement JWT authentication
   fix(api): resolve issue with pagination
   docs(readme): update installation instructions
   ```
9.5. IMPORTANT: Before any destructive Git operation (checkout, pull, rebase, stash, etc.):
   ```bash
   # Create timestamped backup of entire project including untracked files
   cd ..
   zip -r project_name_$(date +%Y-%m-%d_%H%M%S).zip project_name
   cd project_name
   # Now proceed with Git operation
   ```
9.6. Squash commits before merging to main
9.7. Tag all releases with semantic version numbers
9.8. Keep the main branch stable and deployable at all times
9.9. Use Pull Requests for code review
9.10. Address all code review comments before merging
9.11. Keep branches up to date with the main branch

## 10. Deployment
10.1. Use CI/CD pipelines for automated testing and deployment
10.2. Test builds in a staging environment before production
10.3. Follow the deployment checklist before each release
10.4. Monitor application performance after deployment
10.5. Document the rollback procedure for emergency situations
10.6. Use feature flags for gradual feature rollout
10.7. Run database migrations as part of the deployment process
10.8. Update documentation with each new release
10.9. Notify stakeholders before major deployments
10.10. Conduct post-deployment verification


# Project Environment & Development Guide

## 11. Codecov Integration

This project uses Codecov for test coverage reporting and monitoring. The following guidelines must be strictly followed:

### 11.1 Coverage Configuration

- Coverage reports are generated using pytest-cov with branch coverage
- XML reports are used for CI/CD pipelines
- Local coverage reporting is done via the dhtl coverage command
- Repository token must be kept secure and never committed to the codebase

### 11.2 Local Coverage Workflow

Always follow this workflow for local coverage reporting:

1. **Generate coverage report:** 
   ```bash
   # Use the dedicated dhtl command
   ./dhtl.sh coverage

   # This internally runs:
   # pytest --cov=src/enchant_cli --cov-report=xml --cov-branch
   ```

2. **View coverage report:**
   ```bash
   # The command automatically shows a summary in the terminal
   # HTML reports are also generated in coverage_report/
   ```

3. **Update coverage badge:**
   ```bash
   # Codecov badges are automatically updated on CI
   # Local badges are not supported
   ```

### 11.3 CI/CD Coverage Workflow

The GitHub Actions workflow automatically:
1. Runs tests with coverage on each push to main
2. Uploads coverage data to Codecov using codecov-cli
3. Updates repository badge
4. Generates PR comments with coverage delta

### 11.4 Codecov CLI Setup

The project uses codecov-cli installed within the project's virtual environment for enhanced security:

- **Installation:** codecov-cli is installed automatically in the virtual environment
- **Authentication:** Repository token is kept secure in GitHub Secrets
- **Commands:** All interactions are done via the dhtl.sh wrapper
- **Local token:** For local uploads, the CODECOV_TOKEN environment variable is used

### 11.5 Coverage Thresholds

- Minimum code coverage: 80% for all files
- Target code coverage: 95%+ for all files
- Critical modules (translation_service.py): 98%+ coverage

### 11.6 Repository Configuration

- Repository: Emasoft/enchant_cli
- Repository token: Configured in GitHub Actions secrets
- Branch coverage: Enabled
- PR comments: Enabled
- Coverage status checks: Required for merging

### 11.7 Key Commands

```bash
# Run tests with coverage
./dhtl.sh coverage

# Run tests with coverage and upload to Codecov
./dhtl.sh coverage --upload

# Run tests with coverage on a specific file
./dhtl.sh coverage --file=src/enchant_cli/utils.py

# Generate HTML report only (no tests)
./dhtl.sh coverage --report-only
```

# ⚠️ CRITICAL: ALWAYS USE dhtl.sh (or dhtl.bat) FOR ALL OPERATIONS

NEVER run scripts directly. ALWAYS use the DHT Launcher to execute any operation:
```bash
# Unix/Linux/macOS - The ONLY correct way to run scripts and commands
./dhtl.sh [command] [options]

# Windows - The ONLY correct way to run scripts and commands
dhtl.bat [command] [options]
```

The DHT Launcher (dhtl.sh/dhtl.bat) creates a guardian session that:
- Manages resources and memory usage
- Launches scripts in monitored process pools
- Sets appropriate resource limits
- Prevents memory leaks
- Ensures clean process termination
- Provides consistent environment setup

All commands that were previously executed by running scripts directly must now be launched via dhtl. This is MANDATORY to ensure proper resource management and monitoring.

Available commands:
- `test`: Run tests
- `lint`: Run linters
- `build`: Build Python package
- `publish`: Publish to GitHub
- `script`: Run helper scripts
- `guardian`: Manage process guardian
- `restore`: Restore dependencies
- And many more (see `./dhtl.sh help`)

This rule MUST be followed without exception, even when not explicitly stated in a request.
Direct script execution bypasses crucial resource management that the dhtl launcher handles.

# ⚠️ CRITICAL: ALWAYS BACKUP BEFORE DESTRUCTIVE OPERATIONS

**MANDATORY SAFETY RULE:** Before performing any operation that could modify or delete untracked files (rebasing, branch switching, git restore, etc.), you MUST create a complete backup of the entire project directory.

Always create a zip backup with timestamp in your home directory:

```bash
# On Unix/Linux/macOS
zip -r ~/project_backup_$(date +"%Y%m%d_%H%M%S").zip /path/to/project

# On Windows
powershell -command "Compress-Archive -Path . -DestinationPath $HOME/project_backup_$(Get-Date -Format 'yyyyMMdd_HHmmss').zip"
```

This backup must include ALL untracked and hidden files/folders. Store it in your user home directory with a timestamp suffix.

**NEVER SKIP THIS STEP!** Important untracked files that are not under version control would be permanently lost otherwise. The project contains critical untracked files that must be preserved.

While the `dhtl rebase` command automatically creates this backup, you must manually create backups before performing any other potentially destructive git operations.

See the README.md in the DHT folder for more details about this critical safety rule.

# CRITICAL: KEEP ALL SOURCE FILES UNDER 12KB

All script and source code files must be kept below 12KB in size. This is MANDATORY to avoid context memory issues when examining them with AI tools. Files under 12KB can be loaded entirely in memory and examined without truncation. Files larger than 11-12KB will be difficult for LLMs (like Claude) to keep in their context memory without truncation, making code assistance more challenging.

When adding new functionality:
- Split large files into smaller, focused modules
- Use helper functions in separate files
- Avoid excessive comments that increase file size
- Consider extracting reusable components

# CRITICAL: EXTERNALIZE DUPLICATE FUNCTIONS TO REDUCE CODE DUPLICATION

When you find duplicate functions across multiple files:
1. Identify if the functions truly perform the same task and have the same dependencies
2. Create a dedicated helper script for these shared functions
3. Source the helper script in the original files that need the functions
4. Remove the duplicate implementations from the original files

Important considerations:
- Only externalize when function dependencies are minimal (avoid creating large helper files)
- If externalizing functions would require copying too many dependencies, it might be better to keep the duplication
- Ensure helper scripts stay under the 12KB limit
- Use semantic naming for helper scripts (e.g., `print_helpers.sh` for printing functions)
- Place helper scripts in a dedicated directory if they become numerous

# Development Helper Toolkit Launcher (DHTL)

This project includes a portable Development Helper Toolkit Launcher (DHTL) designed to simplify development tasks and enforce resource limits. The toolkit provides:

1. **Process Guardian**: Monitors and manages resource usage (memory, CPU) for Node.js and Python processes
2. **Error Log Analysis**: Sophisticated detection and classification of errors in workflow logs 
3. **GitHub Integration**: Enhanced workflow management, repository operations, and automation
4. **Shell Script Fixing**: Automated fixing of common issues in shell scripts
5. **Environment Management**: Smart project detection and virtual environment setup

## Using the Development Helper Toolkit Launcher

All development tools should be accessed through the centralized launcher:

```bash
# Unix/Linux/macOS
./dhtl.sh [command] [options]

# Windows
dhtl.bat [command] [options]
```

### General Commands:

- `setup`: Set up the toolkit for the current project
  ```bash
  ./dhtl.sh setup
  ```

- `env`: Show environment information and detect API keys
  ```bash
  ./dhtl.sh env
  ```

- `restore`: Restore cached dependencies
  ```bash
  ./dhtl.sh restore
  ```

- `clean`: Clean cache and temporary files
  ```bash
  ./dhtl.sh clean
  ```

### Development Tools:

- `node`: Run Node.js commands with resource limits
  ```bash
  ./dhtl.sh node script.js
  ```

- `script`: Run development helper scripts
  ```bash
  ./dhtl.sh script get_errorlogs
  ./dhtl.sh script fix_workflow_script
  ```

- `guardian`: Control the process guardian
  ```bash
  ./dhtl.sh guardian status
  ./dhtl.sh guardian stop
  ```

### Options:

- `--no-guardian`: Run without process guardian (for lightweight tasks)
  ```bash
  ./dhtl.sh --no-guardian script get_errorlogs
  ```

- `--quiet`: Reduce output verbosity
  ```bash
  ./dhtl.sh --quiet node build.js
  ```

This toolkit can be reused across different projects. Key features:

- **Project Awareness**: Automatically detects the project root by looking for common markers (.git, package.json, etc.)
- **Environment Management**: Auto-creates and manages virtual environments per platform
- **Portable Configuration**: Creates a `.dhtconfig` file to remember project-specific settings
- **Cross-Platform**: Works consistently on macOS, Linux, and Windows
- **Self-Contained**: Manages its own dependencies with automatic setup
- **Resource Management**: Monitors and controls memory usage to prevent overloading the system

# CRITICAL: ALWAYS USE publish_to_github.sh --skip-tests FOR GITHUB OPERATIONS

NEVER use direct git commands like `git push` to push changes to GitHub. ALWAYS use the provided script:
```bash
# Unix/Linux/macOS - The ONLY correct way to push to GitHub
./publish_to_github.sh --skip-tests

# Windows - The ONLY correct way to push to GitHub
publish_to_github.bat --skip-tests
```

## Available Flags:

- `--skip-tests`: Skip running tests locally (tests will ALWAYS run on GitHub regardless)
- `--skip-linters`: Skip running linters/code quality checks locally (linting will ALWAYS run on GitHub regardless)
- `--force`: Force push to repository (use with extreme caution)
- `--dry-run`: Execute all steps except final GitHub push
- `--verify-pypi`: Check if the package is available on PyPI after publishing
- `--check-version VER`: Check if a specific version is available on PyPI

IMPORTANT NOTES:
- Even when using --skip-tests or --skip-linters, the GitHub workflows will ALWAYS run tests and linting remotely
- This ensures code quality even when skipping local validation
- For local linting, use explicit commands like `pre-commit run --all-files` to fix issues before pushing
- The [skip-tests] and [skip-linters] tags in commit messages are ONLY markers that these were skipped locally

Examples:
```bash
# Skip both tests and linters
./publish_to_github.sh --skip-tests --skip-linters

# Skip only linters but run tests
./publish_to_github.sh --skip-linters

# Skip only tests but run linters
./publish_to_github.sh --skip-tests
```

The following rules MUST be followed without exception, even when not explicitly stated in a request.
- Never give direct git commands. Always use the DHT scripts launcher. Direct git commands bypass crucial validation steps and repository management steps that the dht script handles.
- If there is no command and script to do a certain operation via dhtl.sh (or dhtl.bat on windows), just add the command to the dhtl launcher and write the correspondent new script inside the DHT folder.
- Always use the dhtl.sh (or dhtl.bat on windows) to launch the scripts inside the DHT folder. 
- All scripts must be placed in the DHT folder, except for the dhtl launchers.
- Always ensure to use the correct uv environment with proper activation.
- Always assume API keys are already properly defined in the environment - never try to redefine them.
- If tests fail due to missing API keys, inform the user to set up the keys in their environment and exit.
- CRITICAL: For ANY change to the implementation of core functionality (especially in translation methods), you MUST ask for explicit approval before making the change. This includes changes to the translation pipeline, prompt engineering, or API integrations.
- CRITICAL: Never replace carefully calibrated prompts or API integrations without explicit permission. These have been meticulously optimized over long periods of time.
- CRITICAL: Always check if a functionality is already implemented before implementing it. This includes checking both the codebase and the virtual environment setup.


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

# On Windows using Command Prompt
reinitialize_env.bat

# On Windows using PowerShell
.\reinitialize_env.bat

# On Windows via WSL or Git Bash
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
# Use a portable approach that doesn't depend on specific paths
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
# To set a secret for a specific remote repository always use this syntax:
$ gh secret set MYSECRET --repo origin/repo --body "$ENV_VALUE"

# Example
$ gh secret set OPENROUTER_API_KEY --repo "Emasoft/enchant_cli" --body "$OPENROUTER_API_KEY"
```

IMPORTANT: Always use the `--body` flag instead of `-b` for setting secret values to ensure compatibility with all `gh` CLI versions.

NOTE: The `--repo` flag usage differs between `gh secret` commands and other `gh` commands. For `gh secret` commands, the format is `--repo "org/repo"`, while other `gh` commands may use different formats.

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

Version management uses `bump-my-version` with a proper uv integration following best practices:

- **Installation via uv tool**: Always install using `uv tool install bump-my-version`
- **Execution via uv tool run**: Always execute using `uv tool run bump-my-version`
- **Never use pip install**: Avoid using pip to install bump-my-version
- **Primary configuration**: Use `.bumpversion.toml` for configuration
- **Allow dirty by default**: Set `allow_dirty = true` for pre-commit compatibility
- **Pre-commit hook integration**: Configure to run on every commit
- **Fallback mechanisms**: Include robust fallbacks for edge cases

#### Best Practices for bump-my-version with uv

When using bump-my-version with uv, follow these guidelines to avoid issues:

1. **Installation**: Always install using uv tool:
   ```bash
   uv tool install bump-my-version
   ```

2. **Execution**: Always run through uv tool run:
   ```bash
   uv tool run bump-my-version bump minor --commit --tag
   ```

3. **Pre-commit configuration**: In `.pre-commit-config.yaml`, use:
   ```yaml
   - repo: local
     hooks:
       - id: bump-version
         name: Bump version
         entry: uv tool run bump-my-version bump minor --commit --tag --allow-dirty
         language: system
         pass_filenames: false
         always_run: true
   ```

4. **Configuration in pyproject.toml**: Include uv sync command in hooks:
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
   pre_commit_hook = "uv sync"  # This ensures dependencies stay in sync
   ```

5. **Avoid using bump-my-version binary directly**: This leads to synchronization issues with uv

#### Example `hooks/bump_version.sh` - Correctly Using uv with bump-my-version:

```bash
#!/bin/bash
set -eo pipefail

# Get script directory
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
PROJECT_ROOT=$(dirname "$SCRIPT_DIR")
INIT_PY="$PROJECT_ROOT/src/enchant_cli/__init__.py"
UV_CMD="$PROJECT_ROOT/.venv/bin/uv"

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

# Recommended approach: Always use uv tool run (never use direct binary calls)
if [ -f "$UV_CMD" ]; then
    # Preferred method: Using uv tool run with proper arguments
    echo "Using uv tool run for bump-my-version (recommended method)"
    "$UV_CMD" tool run bump-my-version bump minor --commit --tag --allow-dirty || {
        echo "WARNING: Version bump with uv tool failed, trying alternatives..."
    }
else
    # Fallback approaches (less preferred, only for extreme edge cases)
    if command -v uv >/dev/null 2>&1; then
        # Try global uv installation as fallback
        echo "WARNING: Using global uv installation (non-isolated environment)"
        uv tool run bump-my-version bump minor --commit --tag --allow-dirty || {
            echo "WARNING: Version bump failed with global uv - ensure uv is properly installed"
        }
    elif [ -f "$PROJECT_ROOT/.venv/bin/bump-my-version" ]; then
        # Direct virtualenv access (not recommended - may cause sync issues with uv)
        echo "WARNING: Using direct virtualenv binary (not recommended)"
        "$PROJECT_ROOT/.venv/bin/bump-my-version" bump minor --commit --tag --allow-dirty || {
            echo "WARNING: Version bump with direct binary failed"
        }
    else
        # Pure shell implementation as final fallback (for extreme edge cases)
        echo "🔄 Using pure shell version bump (emergency fallback)..."
        
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
fi

# Sync dependencies after version bump (important for uv workflow)
if [ -f "$UV_CMD" ]; then
    "$UV_CMD" sync || echo "WARNING: uv sync failed after version bump"
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

Dependencies are defined in `pyproject.toml`:

```toml
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "enchant-cli"
version = "0.3.5"  # Managed by bump-my-version
description = "CLI tool for translating Chinese texts to English using AI"
authors = [
    {name = "Emasoft", email = "email@example.com"},
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
"Homepage" = "https://github.com/yEmasoft/enchant-cli"
"Bug Tracker" = "https://github.com/Emasoft/enchant-cli/issues"

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


### 3.2 Core Script Conventions

All scripts follow these conventions:

1. **Error Handling**: Use `set -eo pipefail` to fail fast
2. **Relative Paths**: Determine script directory and use relative paths
3. **Environment Isolation**: Source `ensure_env.sh` at the beginning
4. **Explicit Tool Paths**: Refer to tools with explicit paths (`./.venv/bin/...`)
5. **Return Codes**: Check exit codes and handle errors
6. **Logging**: Use emoji prefixes for visibility 
7. **Robust Timeouts**: Include appropriate timeouts for long-running operations
8. **Cross-Platform Path Handling**: 
   - Use `${HOME}` instead of `~` for home directory references
   - Use correct directory separators per platform (`/` for Unix, `\` for Windows)
   - For Windows `.bat` files, use `%SCRIPT_DIR%` for paths
   - For Unix `.sh` files, use `$SCRIPT_DIR` for paths

