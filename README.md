# Enchant CLI Translator

[![PyPI Version](https://img.shields.io/pypi/v/enchant-cli)](https://pypi.org/project/enchant-cli)
[![Python Versions](https://img.shields.io/pypi/pyversions/enchant-cli)](https://pypi.org/project/enchant-cli)
[![License](https://img.shields.io/pypi/l/enchant-cli)](https://github.com/Emasoft/enchant-cli/blob/main/LICENSE)
[![Tests Status](https://github.com/Emasoft/enchant-cli/actions/workflows/tests.yml/badge.svg)](https://github.com/Emasoft/enchant-cli/actions/workflows/tests.yml) <!-- Link to tests workflow -->
[![Codecov](https://codecov.io/gh/Emasoft/enchant-cli/graph/badge.svg?token=YOUR_ACTUAL_CODECOV_TOKEN_HERE)](https://codecov.io/gh/Emasoft/enchant-cli) <!-- IMPORTANT: Replace YOUR_ACTUAL_CODECOV_TOKEN_HERE with the token from your Codecov repository settings page (under 'Badge') -->

A command-line translation tool specifically designed for converting Chinese novels and technical documents into fluent English using AI via the OpenRouter API. It handles text splitting, context-aware translation, and basic formatting preservation.

## What it Does

1.  **Reads:** Takes a Chinese text file (.txt) or a directory of files as input.
2.  **Cleans & Splits:** Cleans the text (removes ads, normalizes spaces) and splits it into manageable chunks based on paragraphs or character limits.
3.  **Translates:** Sends each chunk to an AI model (via OpenRouter) for translation into English, handling retries and basic validation.
4.  **Refines (Optional):** Performs a second AI pass to refine the English translation for better fluency and accuracy.
5.  **Combines & Saves:** Joins the translated chunks back together and saves the result to an output file.

## Features
- Chinese-to-English translation of text files (.txt)
- Intelligent text splitting (by paragraph context or chapter markers)
- Context-aware translation using large language models (via OpenRouter)
- Optional second translation pass for refinement
- Basic handling of HTML/Markdown content within text (attempts to preserve code blocks)
- Batch processing for translating multiple files in a directory
- Basic detection of file encoding
- Configurable chunk size for API requests
- Verbose logging for debugging
- Automatic minor version bumping and tagging on every commit (via pre-commit hook).

## Installation

```bash
# Install from PyPI using pip
pip install enchant-cli
```
```bash
# Or using uv
uv pip install enchant-cli
```

## Development Setup

This project uses `uv` for dependency management, provides isolated environments, and ensures consistent operation across all platforms.

### Quick Start (Self-Contained Environment)

```bash
# 1. Clone the repository
git clone https://github.com/Emasoft/enchant-cli.git
cd enchant-cli

# 2. Create a completely isolated environment
./reinitialize_env.sh         # On macOS/Linux/BSD
# or
reinitialize_env.bat          # On Windows Command Prompt
# or via WSL/Git Bash on Windows
./reinitialize_env.sh

# 3. Activate the environment 
source .venv/bin/activate     # On macOS/Linux/BSD
# or
.venv\Scripts\activate.bat    # On Windows Command Prompt
.venv\Scripts\Activate.ps1    # On Windows PowerShell
source .venv/Scripts/activate # On Git Bash for Windows

# 4. Run tests to verify setup
./run_tests.sh                # On macOS/Linux/BSD
# or 
run_tests.bat                 # On Windows
```

### Environment Variables

Required for running tests/translation:
```bash
export OPENROUTER_API_KEY="your-key-here"
```

Optional for development/CI:
```bash
export CODECOV_API_TOKEN="your-token-here" # For coverage reporting
export PYPI_API_TOKEN="your-pypi-token"    # For PyPI uploads
```

### Key Features of Development Environment

- **Isolated Development**: Project creates and manages its own environment
- **Cross-Platform**: Works on macOS, Linux, BSD, and Windows
- **Self-Contained**: All scripts use relative paths only
- **Automatic Versioning**: Minor version incremented on every commit
- **Environment Verification**: Checks for external references at runtime
- **Automatic Dependency Management**: Managed through uv lock/sync

### Environment Troubleshooting

If you encounter errors related to external environments or see messages like:
```
⚠️ Warning: Environment contains external references
```

Simply reinitialize your environment:
```bash
./reinitialize_env.sh         # On macOS/Linux/BSD
# or
reinitialize_env.bat          # On Windows
```

This completely removes the existing environment and creates a fresh one with no external dependencies.

### Running Tests

**Prerequisites:**
1.  Ensure you have followed the "Development Setup" steps above.
2.  **Activate the virtual environment:** `source .venv/bin/activate` (or equivalent)
3.  Set the required `OPENROUTER_API_KEY` environment variable: `export OPENROUTER_API_KEY="your-api-key-here"` (needed for some tests, though many are mocked).

**Run tests using the script:**
```bash
# Run the test script (while .venv is active)
./run_tests.sh
```

The `./run_tests.sh` script now assumes dependencies are already installed in the active virtual environment and directly runs `pytest` with the configured options.

**Test Reports:**
*   An HTML test report will be generated at `report.html`.
*   An HTML coverage report will be generated in the `coverage_report/` directory.

```bash
# Open HTML coverage report (macOS example)
open coverage_report/index.html

# Open HTML test report (macOS example)
open report.html
```

## Usage

**Translate a Single File:**
```bash
# Ensure your virtual environment is active if running from source
# source .venv/bin/activate (or equivalent)

enchant_cli input.txt -o output.txt
```
*   `input.txt`: Your Chinese text file.
*   `output.txt`: The path where the English translation will be saved. If omitted, defaults to `translated_input.txt` in the current directory.

**Batch Translation (Directory):**
```bash
# Ensure your virtual environment is active if running from source
# source .venv/bin/activate (or equivalent)
 
enchant_cli --batch /path/to/chinese_files/ -o /path/to/output_dir/
```
*   `--batch`: Flag to enable batch mode.
*   `/path/to/chinese_files/`: Directory containing the .txt files to translate.
*   `/path/to/output_dir/`: Directory where translated files will be saved. If omitted, defaults to a `translated/` subdirectory inside the input directory.

**Common Options:**
*   `--max-chars <number>`: Maximum characters per chunk sent to the API (default: 6000).
*   `--split-mode [PARAGRAPHS|SPLIT_POINTS]`: How to split the text (default: PARAGRAPHS).
*   `--double-translate`: Perform a second refinement pass (increases cost and time).
*   `-v, --verbose`: Enable detailed DEBUG logging.
*   `-V, --version`: Show version information and exit immediately (e.g., `Enchant-CLI - Version 0.3.278`).
*   `-h, --help`: Show help message.

## Configuration

This tool requires an API key from [OpenRouter.ai](https://openrouter.ai/) to function.

Set the following environment variable:
```bash
# Required for translation functionality
export OPENROUTER_API_KEY="your-openrouter-key-here"

# Optional: Required for uploading test coverage reports (development/CI)
export CODECOV_API_TOKEN="your-codecov-token-here"
```
You can set these in your shell profile (e.g., `.zshrc`, `.bashrc`), export them in your current session, or potentially use a `.env` file (though direct export is often clearer for CLI tools).

See [Developer Guide](docs/dev-guides/CLAUDE.md) for detailed environment configuration and more information.

## Supported Platforms

The Enchant CLI Translator supports multiple platforms:

- **macOS** (Primary development platform)
- **Linux** (Fully supported)
- **BSD** (Compatible)
- **Windows** (Supported via WSL or Git Bash; limited native support)

### Platform-Specific Notes

- **macOS/Linux/BSD**: Run all scripts directly (e.g., `./run_tests.sh`)
- **Windows**:
  - **Recommended**: Use Windows Subsystem for Linux (WSL) or Git Bash
  - **Alternative**: Use `.bat` wrapper scripts (e.g., `run_tests.bat`) which automatically use WSL/Git Bash if available
  - **Manual**: Follow Windows-specific instructions in the Development Setup section

For cross-platform compatibility, use the platform-detection wrapper scripts (e.g., `run_platform.sh`) which automatically detect your OS and run the appropriate version.

## Limitations

*   **In-Memory State:** The internal representation of the book (chapters, variations) is currently stored only in memory and is lost when the program exits. Only the final translated output file is saved persistently.
*   **API Costs:** Translation relies on the OpenRouter API, which charges based on model usage. Be mindful of the costs associated with the chosen model and the amount of text translated. The `--double-translate` option will approximately double the cost.
*   **Error Handling:** While basic error handling and retries for API calls are implemented, complex network issues or persistent API problems might require manual intervention.

## Release Workflow

### Publishing to GitHub: Critical Protocol

**IMPORTANT**: All code pushes to GitHub MUST use the `publish_to_github.sh` script. Direct git pushes are prohibited as they bypass essential validation.

The `publish_to_github.sh` script:
- Runs comprehensive validation (tests, linting, build verification)
- Creates repository if needed and configures GitHub remote
- Sets up required GitHub secrets automatically
- Handles code pushing with proper error recovery
- Provides release creation guidance

```bash
# Display help with all options
./publish_to_github.sh --help

# Standard execution (recommended approach)
./publish_to_github.sh
```

### Automated Versioning

This project uses a pre-commit hook (`bump-my-version`) to automatically increment the **minor** version and create a tag on **every commit**. This guarantees a unique version number for each release (e.g., `0.3.278`), which is displayed when running the application.

### Release Process

1. **Prepare Your Environment**
   - Make sure your main branch is up-to-date: `git pull`
   - Ensure clean working directory: `git status`
   - Activate virtual environment: `source .venv/bin/activate`

2. **Make Your Changes**
   - Implement code changes
   - Add tests as needed
   - Run tests locally: `./run_tests.sh` or `./run_fast_tests.sh`

3. **Commit Changes**
   - Stage your changes: `git add .`
   - Commit (triggers version bump): `git commit -m "feat: Add new feature"`
   - The pre-commit hook will automatically:
     - Run code quality checks
     - Bump the version number
     - Create a git tag
     - Create a new commit with the version update

4. **Publish to GitHub**
   - Run the publishing script: `./publish_to_github.sh`
   - The script will:
     - Validate your code and run tests
     - Ensure the GitHub repository exists
     - Configure GitHub secrets if needed
     - Push your changes and tags to GitHub
     - Provide instructions for creating a release

5. **Create GitHub Release**
   - Follow the instructions provided by the publish script
   - OR use the GitHub CLI: 
     ```bash
     gh release create v0.3.5 -t "Release v0.3.5" \
       -n "## What's Changed
     - New features and bug fixes"
     ```
   - Publishing the release triggers the PyPI publishing workflow

6. **Verify Publication**
   - Check the [enchant-cli page on PyPI](https://pypi.org/project/enchant-cli) 
   - Verify the new version is available for installation

### Major Releases (Breaking Changes)

For major version increments (breaking changes), use:

```bash
# Run Major Release Script
./major_release.sh
```

Then follow steps 4-6 above. Major version increments should only be used for backward-incompatible API changes.

### First-Time Setup Requirements

If you're setting up a new development environment:

1. **Install GitHub CLI**
   ```bash
   # macOS
   brew install gh
   
   # Linux
   sudo apt install gh  # or equivalent for your distro
   ```

2. **Authenticate GitHub CLI**
   ```bash
   gh auth login
   ```

3. **Set Required Environment Variables**
   ```bash
   export OPENROUTER_API_KEY="your-key-here"
   export CODECOV_API_TOKEN="your-token-here"  # Optional, for coverage reporting
   export PYPI_API_TOKEN="your-token-here"     # Optional, for manual PyPI uploads
   ```

For more detailed information, see the [GitHub Integration](docs/dev-guides/CLAUDE.md#6-github-integration) section of the developer guide.

## Development and CI/CD

### Script Validation
* All shell scripts are validated with ShellCheck using `--severity=error --extended-analysis=true`
* Scripts use relative paths for environment portability
* No private data is included in scripts - configuration is via environment variables

### GitHub Workflows
* **tests.yml**: Runs on every push/PR, tests with multiple Python versions (3.9-3.13)
* **publish.yml**: Triggered by GitHub Releases, builds and publishes to PyPI
* Both workflows mirror the behavior of local scripts for consistency

For detailed CI/CD information, see the workflow files in `.github/workflows/`.

## Contributing

Contributions are welcome!

1.  Fork the repository.
2.  Follow the **Development Setup** instructions (including activating the `.venv`).
3.  Create a feature branch (`git checkout -b feature/your-feature-name`).
4.  Make your changes and add tests.
5.  Ensure tests pass (`./run_tests.sh` while `.venv` is active).
6.  Commit your changes (`git commit -m 'Add some feature'`).
7.  Push to the branch (`git push origin feature/your-feature-name`).
8.  Open a Pull Request.
