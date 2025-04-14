# Enchant CLI Translator

[![PyPI Version](https://img.shields.io/pypi/v/enchant-cli)](https://pypi.org/project/enchant-cli)
[![Python Versions](https://img.shields.io/pypi/pyversions/enchant-cli)](https://pypi.org/project/enchant-cli)
[![License](https://img.shields.io/pypi/l/enchant-cli)](https://github.com/Emasoft/enchant-cli/blob/main/LICENSE) <!-- Use PyPI license shield -->
[![Tests Status](https://github.com/Emasoft/enchant-cli/actions/workflows/tests.yml/badge.svg)](https://github.com/Emasoft/enchant-cli/actions/workflows/tests.yml) <!-- Link to tests workflow -->
[![Codecov](https://codecov.io/gh/Emasoft/enchant-cli/graph/badge.svg?token=YOUR_ACTUAL_CODECOV_TOKEN_HERE)](https://codecov.io/gh/Emasoft/enchant-cli) <!-- IMPORTANT: Replace YOUR_ACTUAL_CODECOV_TOKEN_HERE with the actual token from your Codecov repository settings -->

A command-line translation tool specifically designed for converting Chinese novels and technical documents into fluent English using AI via the OpenRouter API. It handles text splitting, context-aware translation, and basic formatting preservation.


## Features
- Chinese-to-English translation of text files (.txt)
- Intelligent text splitting (by paragraph context or chapter markers)
- Context-aware translation using large language models (via OpenRouter)
- Optional second translation pass for refinement
- Handles HTML/Markdown content within text (preserves code blocks)
- Batch processing for translating multiple files in a directory
- Basic detection of file encoding
- Configurable chunk size for API requests
- Verbose logging for debugging

## Installation

```bash
# Install from PyPI using pip
pip install enchant-cli

# Or using uv
uv pip install enchant-cli
```

## Development Setup

```bash
# 1. Clone the repository
git clone https://github.com/Emasoft/enchant-cli.git
cd enchant-cli

# 2. Set up environment variables (see Configuration section)
# Example: export OPENROUTER_API_KEY="your-key-here"
#          export CODECOV_API_TOKEN="your-token-here" # For coverage reporting

# 3. Create a virtual environment (recommended)
python -m venv .venv

# 4. Activate the virtual environment (IMPORTANT!)
source .venv/bin/activate  # On Windows use `.venv\Scripts\activate`
# Your terminal prompt should now show (.venv)

# 5. Install dependencies using uv (includes dev dependencies)
# Ensure uv is installed: pip install uv
# Run this command *while the virtual environment is active*
uv pip install -e .[dev]
# This installs the package in editable mode and all dev dependencies into your .venv

# 6. (Optional) Install pre-commit hooks
# Run this command *while the virtual environment is active*
pre-commit install
```

### Running Tests

**Prerequisites:**
1.  Ensure you have followed the "Development Setup" steps above.
2.  **Activate the virtual environment:** `source .venv/bin/activate`
3.  Set the required `OPENROUTER_API_KEY` environment variable: `export OPENROUTER_API_KEY="your-api-key-here"`

**Run tests:**
```bash
# Run the test script (while .venv is active)
./run_tests.sh
```

The `./run_tests.sh` script now assumes dependencies are already installed in the active virtual environment and directly runs `pytest` with the configured options.

**After running tests:**
*   An HTML test report will be generated at `report.html`.
*   An HTML coverage report will be generated in the `coverage_report/` directory.

```bash
# Open HTML coverage report (macOS example)
open coverage_report/index.html

# Open HTML test report (macOS example)
open report.html
```

## Usage

**Basic Translation (Single File):**
```bash
# Ensure your virtual environment is active if running from source
# source .venv/bin/activate

enchant_cli input.txt -o output.txt
```
*   `input.txt`: Your Chinese text file.
*   `output.txt`: The path where the English translation will be saved. If omitted, defaults to `translated_input.txt` in the current directory.

**Batch Translation (Directory):**
```bash
# Ensure your virtual environment is active if running from source
# source .venv/bin/activate

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
*   `-V, --version`: Show version information.
*   `-h, --help`: Show help message.

## Configuration

This tool requires an API key from [OpenRouter.ai](https://openrouter.ai/) to function.

Set the following environment variable:
```bash
# Required for translation
export OPENROUTER_API_KEY="your-openrouter-key-here"

# Optional: Required for uploading test coverage reports during development/CI
export CODECOV_API_TOKEN="your-codecov-token-here"
```
You can set these in your shell profile (e.g., `.zshrc`, `.bashrc`), export them in your current session, or potentially use a `.env` file (though direct export is often clearer for CLI tools).

See [Environment Configuration Reference](docs/environment.md) for more details.

## Limitations

*   **In-Memory State:** The internal representation of the book (chapters, variations) is currently stored in memory and is lost when the program exits. Only the final translated output file is saved persistently.
*   **API Costs:** Translation relies on the OpenRouter API, which charges based on model usage. Be mindful of the costs associated with the chosen model and the amount of text translated. The `--double-translate` option will approximately double the cost.
*   **Error Handling:** While basic error handling and retries for API calls are implemented, complex network issues or persistent API problems might require manual intervention.

## Release Process

Releasing a new version involves these steps:

1.  **Ensure Clean State:** Make sure your main branch is up-to-date and your working directory is clean (`git status`).
2.  **Activate Environment:** Activate your virtual environment: `source .venv/bin/activate`.
3.  **Run Validations:** Execute the local validation script to run tests, linters, and build checks:
    ```bash
    ./release.sh
    ```
    Fix any issues reported by the script.
4.  **Bump Version:** Use `bump-my-version` to increment the version number. This will update `src/enchant_cli/__init__.py`, create a commit, and tag the commit (based on `.bumpversion.toml` configuration).
    ```bash
    # Example for a patch release (run while .venv is active):
    bump-my-version patch

    # Or use the wrapper script:
    # ./bump_version.sh patch
    ```
5.  **Push Changes and Tag:** Push the commit and the newly created tag to GitHub:
    ```bash
    git push origin main --tags
    ```
6.  **Create GitHub Release:** Go to the repository's "Releases" page on GitHub and draft a new release. Choose the tag you just pushed (e.g., `v0.1.1`). Add release notes (consider using `git-chglog` output). Publishing the release will trigger the `publish.yml` workflow.
7.  **Monitor Workflow:** Check the "Actions" tab on GitHub to ensure the `publish.yml` workflow runs successfully and publishes the package to PyPI.
8.  **Verify on PyPI:** Check the [enchant-cli page on PyPI](https://pypi.org/project/enchant-cli) to confirm the new version is available.

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
