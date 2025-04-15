# Environment Configuration for enchant_cli

## Supported Platforms

The project supports the following platforms:

- **macOS**: Primary development platform, all scripts work natively
- **Linux**: Fully supported, all scripts work natively
- **BSD**: Compatible with Unix shell scripts
- **Windows**: Support via multiple options:
  - **WSL** (Windows Subsystem for Linux): Recommended approach
  - **Git Bash**: Alternative Unix-like environment
  - **Native**: Limited support via `.bat` wrapper scripts

## Project Environment Isolation

The project is designed to be completely self-contained with a project-isolated Python environment:

1. **No External Dependencies**: All scripts ensure the project uses only its own isolated virtual environment
2. **Relative Paths**: All paths in scripts are relative to the script location, never absolute
3. **Environment Verification**: Scripts check for external references and warn/abort if found
4. **Self-healing**: The system automatically creates a clean environment when needed
5. **Explicit Tool Paths**: All tool calls use explicit paths to the project's environment (`.venv/bin/...`)

To ensure a clean environment after cloning the repository:

```bash
# On Unix platforms (macOS, Linux, BSD)
./reinitialize_env.sh

# On Windows (Command Prompt)
reinitialize_env.bat

# On Windows via WSL/Git Bash
./reinitialize_env.sh
```

## Environment Structure

- **Virtual Environment**: Located at `.venv/` in the project root
- **Creation Method**: Generated using `uv venv` for consistency
- **Isolation**: Completely isolated from system Python - no shared site-packages
- **Verification**: Environment is checked at script startup to verify no external references

## Platform-Specific Script Structure

The project uses platform-specific script wrappers to maintain compatibility:

- **Unix Scripts** (`.sh`): Core implementation for macOS/Linux/BSD
- **Windows Batch Files** (`.bat`): Windows-specific wrappers that:
  1. Try WSL if available
  2. Try Git Bash if available 
  3. Fall back to native Windows commands where possible
- **Platform Detection** (`run_platform.sh`): Auto-detects platform and runs the appropriate script

## uv Tool Configuration

- Project uses `uv` for dependency and environment management
- All scripts include environment creation logic via `uv venv`
- Dependencies managed via:
  - `uv lock` - Create/update dependency lockfile
  - `uv sync` - Sync environment from lockfile
  - `uv pip install -e .` - Install project in development mode
- Path references are always explicit: `./.venv/bin/uv` never global `uv`

## Pre-commit Configuration

- Configured to use bump-my-version as a local hook with explicit path to the project's environment
- Entry point: `./.venv/bin/bump-my-version` (never system `bump-my-version`) 
- Automatically bumps minor version on every commit (creating unique numbered releases like 0.3.278)
- Creates tags automatically for each version increment
- Version is displayed in CLI header and when using --version flag
- Shellcheck validates all scripts with `--severity=error --extended-analysis=true` settings

## Key Environment Variables

- Required API keys are already configured in the user's environment - DO NOT EXPORT OR OVERRIDE THEM:
  - OPENROUTER_API_KEY: For translation API functionality (ALREADY SET - DO NOT EXPORT)
  - PYPI_API_TOKEN: For PyPI package publishing (ALREADY SET - DO NOT EXPORT)
  - CODECOV_API_TOKEN: For test coverage reporting (ALREADY SET - DO NOT EXPORT)
  
As stated in docs/environment.md: "Those variables are usually already defined in the environment via .zshrc or .bashrc, so they usually does not need to be set explicitly. Set them only if they are not defined."

## Dependency Management

- Dependencies are defined in `pyproject.toml` 
- Lock files are maintained using uv:
  - `uv.lock`: Contains resolved dependencies for reproducible builds
- When changing dependencies:
  1. Update `pyproject.toml`
  2. Run `./.venv/bin/uv lock` to update the lock file using project's uv
  3. Run `./.venv/bin/uv sync` to install dependencies according to the lock file

## Building and Publishing

- Package version is managed in `src/enchant_cli/__init__.py`
- Automatic version bumping with bump-my-version via pre-commit
- Build process:
  1. `./.venv/bin/uv build` creates both wheel and sdist packages
  2. GitHub Actions automates PyPI publishing on release

## Script Execution Rules

- ALWAYS use the provided scripts without parameters - never use custom shell commands
- Always ensure you're running from a clean environment (run `./reinitialize_env.sh` if in doubt)
- All settings are properly configured within the scripts themselves
- Scripts have proper defaults and handle all edge cases automatically
- DO NOT pass environment variables or parameters - they're already set appropriately
- All paths in scripts are RELATIVE, ensuring they work in any environment
- No private data is included in the scripts
- No external environment paths are included in scripts

## Development Workflow

### Setting up a Fresh Development Environment

```bash
# Clone the repository 
git clone https://github.com/Emasoft/enchant-cli.git
cd enchant-cli

# Create clean isolated environment
./reinitialize_env.sh  # or reinitialize_env.bat on Windows

# Activate the environment
source .venv/bin/activate  # or .venv\Scripts\activate.bat on Windows

# Run tests to verify setup
./run_tests.sh  # or run_tests.bat on Windows
```

### Adding New Features

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

## Code Quality Standards

- ShellCheck is configured to run on all shell scripts with:
  - `--severity=error` to focus on critical issues
  - `--extended-analysis=true` for more thorough checking
- These settings are enforced by:
  - Pre-commit hooks for local development
  - GitHub workflow for CI/CD pipeline
- All scripts comply with these standards to ensure robustness and portability

## Command-Line Tool Usage Guidelines

- **Always limit search depth** when using `find` or `grep` commands:
  - Always use `-maxdepth 6` with `find` to prevent excessive recursion
  - Always use `--max-depth=6` or similar limiting flags with `grep -r`
  - This prevents performance issues with deeply nested directories
  - Example: `find . -maxdepth 6 -type f -name "*.py"`
  - Example: `grep -r --max-depth=6 "pattern" .`

## Script Documentation

### Core Scripts

- `./reinitialize_env.sh` / `reinitialize_env.bat`: Creates a fresh, clean environment
  - Removes existing .venv if present
  - Creates a new virtual environment using uv
  - Installs all dependencies from scratch
  - Sets up pre-commit hooks
  - Ensures no external environment references

- `./run_platform.sh`: Cross-platform script runner
  - Automatically detects the operating system
  - Uses platform-specific script versions
  - Verifies environment cleanliness
  - Ensures correct paths and environment isolation
  - Handles Windows, Linux, macOS, and BSD compatibility

- `./run_commands.sh`: Main orchestration script that runs the complete workflow
  - Ensures lock file is up-to-date with dependencies
  - Synchronizes environment with uv
  - Prepares pre-commit environment
  - Stages and commits changes
  - Runs validation and push script (publish_to_github.sh)
  - Uses only project-isolated environment paths

- `./publish_to_github.sh`: Prepares and pushes to GitHub
  - Auto-installs uv and other dependencies if missing
  - Creates virtual environment if needed
  - Ensures pre-commit hooks are installed
  - Commits changes with automatic version bumping
  - Runs validation script (release.sh)
  - Verifies required environment variables
  - Pushes latest commit and tags to GitHub
  - Provides detailed next steps for publishing

- `./release.sh`: Local validation script before pushing a release tag
  - Cleans previous builds
  - Installs dependencies
  - Runs linters/formatters via pre-commit
  - Runs tests with coverage checking (10-minute timeout)
  - Builds package (sdist and wheel)
  - Verifies test sample inclusion in packages
  - Uses only project-isolated environment paths

- `./run_tests.sh`: Runs tests with pytest
  - Uses pytest with appropriate settings
  - Generates code coverage reports
  - Creates HTML test reports
  - Fixed 10-minute timeout (600 seconds)
  - Environment variables pre-configured
  - Uses only project-isolated environment paths

### Utility Scripts

- `./major_release.sh`: Major version release script
  - Increments MAJOR version number (x.0.0)
  - Use only for breaking changes
  - Runs validation tests
  - Does not commit changes automatically
  - Provides detailed next steps
  - Has corresponding Windows wrapper `major_release.bat`

- `./bump_version.sh`: Manual version bumping
  - Wrapper around bump-my-version
  - Takes version part as argument (major, minor, patch)
  - Used for manual version control when needed
  - Uses only project-isolated environment paths

- `./cleanup.sh`: Removes clutter and build artifacts
  - Removes build artifacts and caches
  - Removes Python __pycache__ directories
  - Provides next steps for environment synchronization

- `./tests/verify_samples.sh`: Verifies test samples exist
  - Checks sample file existence
  - Verifies sample content integrity
  - Uses only relative paths

## GitHub Workflows

The project includes GitHub workflows that mirror the local scripts:

### tests.yml
- Parallels `run_tests.sh` in the GitHub environment
- Runs on every push and pull request
- Tests across multiple Python versions (3.9, 3.10, 3.11, 3.12, 3.13)
- Includes shellcheck validation with `--severity=error --extended-analysis=true`
- Uploads test coverage to Codecov

### publish.yml
- Parallels `release.sh` and publishing workflow
- Triggered when a GitHub Release is published
- Uses trusted publishing with OIDC for PyPI
- Builds and verifies package
- Publishes to PyPI
- Performs post-publish verification

When changes are pushed to GitHub, these workflows automatically run the same validations as the local scripts, ensuring consistent behavior across environments.