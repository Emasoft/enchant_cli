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

This project uses `uv` for dependency management and `pre-commit` for code quality checks and automatic version bumping.

```bash
# 1. Clone the repository
git clone https://github.com/Emasoft/enchant-cli.git
cd enchant-cli

# 2. Set up environment variables (see Configuration section)
#    Required for running tests/translation:
#    export OPENROUTER_API_KEY="your-key-here"
#    Optional for development/CI:
#    export CODECOV_API_TOKEN="your-token-here" # For coverage reporting
#    export PYPI_API_TOKEN="your-pypi-token"    # For potential manual PyPI uploads

# 3. Create a virtual environment (recommended)
python -m venv .venv

# 4. Activate the virtual environment (IMPORTANT!)
# For macOS/Linux/BSD:
source .venv/bin/activate
# For Windows Command Prompt:
# .venv\Scripts\activate.bat
# For Windows PowerShell:
# .venv\Scripts\Activate.ps1
# For Git Bash on Windows:
# source .venv/Scripts/activate
# Your terminal prompt should now show (.venv)

# 5. Install dependencies using uv (includes dev dependencies)
#    Ensure uv is installed: pip install uv
#    Run this command *while the virtual environment is active*
uv pip install -e .[dev]
#    This installs the package in editable mode and all dev dependencies
#    from the uv.lock file into your .venv

# 6. (Optional) Install pre-commit hooks
#    Run this command *while the virtual environment is active*
#    This enables automatic formatting, linting, and version bumping on commit.
pre-commit install
```

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

See [Environment Configuration Reference](docs/environment.md) for more details.

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

### Minor Releases (Automatic Versioning)

This project uses a pre-commit hook (`bump-my-version`) to automatically increment the **minor** version and create a tag on **every commit**. This guarantees a unique version number for each release (e.g., `0.3.278`), which is displayed when running the application. The release process leverages this:

1.  **Ensure Clean State:** Make sure your main branch is up-to-date and your working directory is clean (`git status`).
2.  **Activate Environment:** Activate your virtual environment: `source .venv/bin/activate`.
3.  **Make Changes:** Make the final code changes for your release.
4.  **Commit Changes:** Commit your changes.
    ```bash
    git add .
    git commit -m "feat: Add new feature for release" # Or fix:, chore:, etc.
    ```
    *   The `pre-commit` hook will automatically run.
    *   `bump-my-version` will increment the minor version in `src/enchant_cli/__init__.py`.
    *   A **new commit** containing only the version bump will be created.
    *   A **tag** (e.g., `v0.2.0`) corresponding to the new version will be created automatically.
5.  **Run Pre-Release Validation:** Execute the local validation script. This runs linters, tests, and build checks defined in `release.sh`.
    ```bash
    # For macOS/Linux/BSD:
    ./publish_to_github.sh
    # For Windows with WSL/Git Bash:
    ./run_platform.sh publish_to_github
    # For Windows native:
    publish_to_github.bat
    ```
    Fix any issues reported by the script and commit the fixes (which will trigger another version bump - this is expected with this workflow). Re-run until it passes.
6.  **Push Changes and Tag:** Push the latest commit and the automatically generated tag to GitHub:
    ```bash
    git push origin main --tags
    ```
7.  **Create GitHub Release:** Go to the repository's "Releases" page on GitHub and "Draft a new release". Choose the tag you just pushed (e.g., `v0.2.0`). Add release notes. Publishing the release triggers the `publish.yml` workflow.
8.  **Monitor Workflow:** Check the "Actions" tab on GitHub to ensure the `Publish Python Package` workflow runs successfully and publishes the package to PyPI.
9.  **Verify on PyPI:** Check the [enchant-cli page on PyPI](https://pypi.org/project/enchant-cli) to confirm the new version is available.

### Major Releases (Breaking Changes)

For major version increments (breaking changes), use the dedicated script:

1. **Ensure Clean State:** Make sure your main branch is up-to-date and your working directory is clean (`git status`).
2. **Activate Environment:** Activate your virtual environment.
3. **Run Major Release Script:**
   ```bash
   # For macOS/Linux/BSD:
   ./major_release.sh
   # For Windows with WSL/Git Bash:
   ./run_platform.sh major_release
   # For Windows native:
   major_release.bat
   ```
4. **Update CHANGELOG.md:** Document all breaking changes in detail.
5. **Commit and Push:** Follow steps 6-9 from the minor release process.

A major version increment should only be used for backward-incompatible API changes.

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
