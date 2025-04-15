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

### Platform-Specific Script Structure

The project uses platform-specific script wrappers to maintain compatibility:

- **Unix Scripts** (`.sh`): Core implementation for macOS/Linux/BSD
- **Windows Batch Files** (`.bat`): Windows-specific wrappers that:
  1. Try WSL if available
  2. Try Git Bash if available
  3. Fall back to native Windows commands where possible
- **Platform Detection** (`run_platform.sh`): Auto-detects platform and runs the appropriate script

## Virtual Environment
- Project uses a Python virtual environment located at `.venv/`
- Created using uv: `.venv/pyvenv.cfg` contains version info
- Environment is isolated from system Python - no shared site-packages 
- Project prompt is set to "enchant_cli"
- Scripts automatically create and manage this environment if needed

## uv Tool Configuration
- This project uses uv for dependency management
- `uv` command should be installed globally and available in PATH
- Scripts are designed to detect, create, and use the project's environment
- All Python commands explicitly use the project's virtual environment Python (`.venv/bin/python`)
- All script files use relative paths to ensure consistency across platforms
- No external environments are used - the project is completely self-contained

## Pre-commit Configuration
- Configured to use bump-my-version as a local hook (no external repository needed)
- Automatically bumps minor version on every commit (creating unique numbered releases like 0.3.278)
- Creates tags automatically for each version increment
- Version is displayed in CLI header and when using --version flag
- The ruff linter configuration has been updated to ignore several code style issues
- Uses shellcheck to verify shell scripts

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
  2. Run `uv lock` to update the lock file
  3. Run `uv sync` to install dependencies according to the lock file

## Building and Publishing
- Package version is managed in `src/enchant_cli/__init__.py`
- Automatic version bumping with bump-my-version via pre-commit is temporarily disabled
  - Need to manually run `bump-my-version minor` before commit
  - Or manually update version in `src/enchant_cli/__init__.py`
- Build process:
  1. `uv build` creates both wheel and sdist packages
  2. GitHub Actions automates PyPI publishing on release

## Script Execution Rules
- ALWAYS use the provided scripts without parameters - never use custom shell commands
- All settings are properly configured within the scripts themselves
- Scripts have proper defaults and handle all edge cases automatically
- DO NOT pass environment variables or parameters - they're already set appropriately
- All paths in scripts are RELATIVE, ensuring they work in any environment
- No private data is included in the scripts

## Code Quality Standards
- ShellCheck is configured to run on all shell scripts with:
  - `--severity=error` to focus on critical issues
  - `--extended-analysis=true` for more thorough checking
- These settings are enforced by:
  - Pre-commit hooks for local development
  - GitHub workflow for CI/CD pipeline
- All scripts comply with these standards to ensure robustness and portability

## Script Documentation

### Core Workflow Scripts
- `./run_commands.sh`: Main orchestration script that runs the complete workflow
  - Ensures lock file is up-to-date with dependencies
  - Synchronizes environment with uv
  - Prepares pre-commit environment
  - Stages and commits changes
  - Runs validation and push script (publish_to_github.sh)
  - Proper sequencing of operations with error handling

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
  - Does NOT commit, tag, push, or set secrets

- `./run_tests.sh`: Runs tests with pytest
  - Uses pytest with appropriate settings
  - Generates code coverage reports
  - Creates HTML test reports
  - Fixed 10-minute timeout (600 seconds)
  - Environment variables pre-configured

### Setup Scripts
- `./first_push.sh`: Sets up initial GitHub repository
  - Initializes git repository
  - Creates initial commit
  - Sets up remote origin
  - Provides instructions for setting up GitHub secrets

- `./setup_package.sh`: Sets up initial package structure
  - Creates directory structure
  - Creates essential package files
  - Creates test sample data
  - Initializes configuration files

- `./install_apache_license.sh`: Installs Apache 2.0 LICENSE
  - Downloads official Apache 2.0 license
  - Verifies download and license content
  - Provides guidance for license configuration

### Utility Scripts
- `./bump_version.sh`: Manual version bumping
  - Wrapper around bump-my-version
  - Takes version part as argument (major, minor, patch)
  - Used for manual version control when needed

- `./major_release.sh`: Major version release script
  - Increments MAJOR version number (x.0.0)
  - Use only for breaking changes
  - Runs validation tests
  - Does not commit changes automatically
  - Provides detailed next steps
  - Has corresponding Windows wrapper `major_release.bat`

- `./cleanup.sh`: Removes clutter and build artifacts
  - Removes build artifacts and caches
  - Removes Python __pycache__ directories
  - Provides next steps for environment synchronization

- `./resetgit.sh`: Resets git history (use with caution)
  - Deletes .git directory and history
  - Initializes new repository
  - Creates initial commit

- `./tests/verify_samples.sh`: Verifies test samples exist
  - Checks sample file existence
  - Verifies sample content integrity
  
- `./run_platform.sh`: Cross-platform script runner
  - Automatically detects the operating system
  - Executes platform-specific script versions
  - Falls back to generic scripts when specific ones aren't available
  - Adds capability for Linux, macOS, BSD, and Windows support
  - Makes cross-platform development easier

All scripts have correct defaults, proper error handling, and appropriate timeouts. They should be used without additional parameters.

## Script Sequence

### Unix Platforms (macOS/Linux/BSD)
1. `uv lock` - Update the lock file
2. `uv sync` - Apply dependency changes to the environment
3. Run pre-commit checks
4. Commit changes (triggering automatic version bump)
5. Run validation with `./release.sh` 
6. Push to GitHub with `./publish_to_github.sh`

### Windows Platforms
1. For WSL/Git Bash: Follow the Unix platform sequence
2. For native Windows:
   - Use `.bat` wrapper scripts (e.g., `run_tests.bat`)
   - Or use the cross-platform runner: `run_platform.sh command_name`

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
4. Commit changes (triggering automatic version bump)
5. Run validation with `./release.sh`
6. Push to GitHub with `./publish_to_github.sh`

## Notes
- Always work within the activated virtual environment
- Use `uv pip install -e .` for editable installs during development
- The `test_sample.txt` file must be included in both sdist and wheel packages