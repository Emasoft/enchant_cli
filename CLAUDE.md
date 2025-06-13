# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## General Development Guidelines and Rules
- *CRITICAL*: when reading the lines of the source files, do not read just few lines like you usually do. Instead always read all the lines of the file (until you reach the limit of available context memory). No matter what is the situation, searching or editing a file, ALWAYS OBEY TO THIS RULE!!!.
- *CRITICAL*: do not ever do unplanned things or take decisions without asking the user first. All non trivial changes to the code must be planned first, approved by the user, and added to the tasks_checklist.md first. Unless something was specifically instructed by the user, you must not do it. Do not make changes to the codebase without duscussing those with the user first and get those approved. Be conservative and act on a strict need-to-be-changed basis.
- *CRITICAL*: COMMIT AFTER EACH CHANGE TO THE CODE, NO MATTER HOW SMALL!!!
- *CRITICAL*: after receiving instructions from the user, before you proceed, confirm if you understand and tell the user your plan. If instead you do not understand something, or if there are choices to make, ask the user to clarify, then tell the user your plan. Do not proceed with the plan if the user does not approve it.
- *CRITICAL*: **Auto-Lint after changes**: Always run the linters (like ruff, shellcheck, mypy, yamllint, eslint, etc.) after any changes to the code files! ALWAYS DO IT BEFORE COMMITTING!!
- be extremely meticulous and accurate. always check twice any line of code for errors when you edit it.
- never output code that is abridged or with parts replaced by placeholder comments like `# ... rest of the code ...`, `# ... rest of the function as before ...`, `# ... rest of the code remains the same ...`, or similar. You are not chatting. The code you output is going to be saved and linted, so omitting parts of it will cause errors and broken files.
- Be conservative. only change the code that it is strictly necessary to change to implement a feature or fix an issue. Do not change anything else. You must report the user if there is a way to improve certain parts of the code, but do not attempt to do it unless the user explicitly asks you to. 
- when fixing the code, if you find that there are multiple possible solutions, do not start immediately but first present the user all the options and ask him to choose the one to try. For trivial bugs you don't need to do this, of course.
- never remove unused code or variables unless they are wrong, since the program is a WIP and those unused parts are likely going to be developed and used in the future. The only exception is if the user explicitly tells you to do it.
- don't worry about functions imported from external modules, since those dependencies cannot be always included in the chat for your context limit. Do not remove them or implement them just because you can''t find the module or source file they are imported from. You just assume that the imported modules and imported functions work as expected. If you need to change them, ask the user to include them in the chat.
- spend a long time thinking deeply to understand completely the code flow and inner working of the program before writing any code or making any change. 
- if the user asks you to implement a feature or to make a change, always check the source code to ensure that the feature was not already implemented before or it is implemented in another form. Never start a task without checking if that task was already implemented or done somewhere in the codebase.
- if you must write a function, always check if there are already similar functions that can be extended or parametrized to do what new function need to do. Avoid writing duplicated or similar code by reusing the same flexible helper functions where is possible.
- keep the source files as small as possible. If you need to create new functions or classes, prefer creating them in new modules in new files and import them instead of putting them in the same source file that will use them. Small reusable modules are always preferable to big functions and spaghetti code.
- Always check for leaks of secrets in the git repo with `gitleaks git --verbose` and `gitleaks dir --verbose`.
- commit should be atomic, specific, and focus on WHAT changed in subject line with WHY explained in body when needed.
- use semantic commit messages following the format in the Git Commit Message Format memory
- Write only shippable, production ready code. If you wouldn’t ship it, don’t write it. 
- Don't drastically change existing patterns without explicit instruction
- before you execute a terminal command, trigger the command line syntax help or use `cheat <command>` to learn the correct syntax and avoid failed commands.
- if you attempt to run a command and the command is not found, first check the path, and then install it using `brew install`.
- never take shortcuts to skirt around errors. fix them.
- If the solution to a problem is not obvious, take a step back and look at the bigger picture.
- If you are unsure, stop and ask the user for help or additional information.
- if something you are trying to implement or fix does not work, do not fallback to a simpler solution and do not use workarounds to avoid implement it. Do not give up or compromise with a lesser solution. You must always attempt to implement the original planned solution, and if after many attempts it still fails, ask the user for instructions.
- always use type annotations
- always keep the size of source code files below 10Kb. If writing new code in a source file will make the file size bigger than 10Kb, create a new source file , write the code there, and import it as a module. Refactor big files in multiple smaller modules.
- always preserve comments and add them when writing new code.
- always write the docstrings of all functions and improve the existing ones. Use Google-style docstrings with Args/Returns sections, but do not use markdown. 
- never use markdown in comments. 
- when using the Bash tool, always set the timeout parameter to 1800000 (30 minutes).
- always tabulate the tests result in a nice table.
- do not use mockup tests or mocked behaviours unless it is absolutely impossible to do otherwise. If you need to use a service, local or remote, do not mock it, just ask the user to activate it for the duration of the tests. Results of mocked tests are completely useless. Only real tests can discover issues with the codebase.
- always use a **Test-Driven Development (TDD)** methodology (write tests first, the implementation later) when implementing new features or change the existing ones. But first check that the existing tests are written correctly.
- always plan in advance your actions, and break down your plan into very small tasks. Save a file named `DEVELOPMENT_PLAN.md` and write all tasks inside it. Update it with the status of each tasks after any changes.
- do not create prototypes or sketched/abridged versions of the features you need to develop. That is only a waste of time. Instead break down the new features in its elemental components and functions, subdivide it in small autonomous modules with a specific function, and develop one module at time. When each module will be completed (passing the test for the module), then you will be able to implement the original feature easily just combining the modules. The modules can be helper functions, data structures, external librries, anything that is focused and reusable. Prefer functions at classes, but you can create small classes as specialized handlers for certain data and tasks, then also classes can be used as pieces for building the final feature.
- When commit, never mention Claude as the author of the commits or as a Co-author.
- when refactoring, enter thinking mode first, examine the program flow, be attentive to what you're changing, and how it subsequently affects the rest of the codebase as a matter of its blast radius, the codebase landscape, and possible regressions. Also bear in mind the existing type structures and interfaces that compose the makeup of the specific code you're changing.
- always use `Emasoft` as the user name, author and committer name for the git repo.
- always use `713559+Emasoft@users.noreply.github.com` as the user email and git committer email for the git repo.
- always add the following shebang at the beginning of each python file: 

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
```
- always add a short changelog before the imports in of the source code to document all the changes you made to it.

```python
# HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
# <your changelog here…>
# 
```


## Enchant Project Overview

ENCHANT_BOOK_MANAGER is a Python-based system for translating Chinese novels to English using AI translation services. The project supports both local (LM Studio) and remote (OpenRouter) translation APIs, with features for book management, chapter splitting, and EPUB generation.

## Core Architecture

### Main Components

- **cli_translator.py**: Main command-line interface and orchestration layer
- **translation_service.py**: AI translation service with dual API support (local/remote)
- **make_epub.py**: EPUB generation from text chapters with validation (converted to module API)
- **config_manager.py**: Comprehensive YAML configuration management
- **icloud_sync.py**: Automatic iCloud Drive synchronization for macOS/iOS
- **model_pricing.py**: API cost tracking and reporting
- **novel_renamer.py**: Advanced novel metadata extraction using OpenAI
- **common_utils.py**: Shared utility functions across modules
- **ENCHANT-MANAGER/**: Contains additional book management tools and database utilities

### Key Features

- **Dual Translation APIs**: Local (LM Studio with Qwen models) and remote (OpenRouter with DeepSeek)
- **Chapter Management**: Intelligent text splitting while preserving paragraph integrity
- **Batch Processing**: Process multiple novels with progress tracking and resume capability
- **EPUB Generation**: Convert translated novels to EPUB format with TOC
- **Character Limit Handling**: Configurable character limits per translation chunk (default: 11,999 - strictly less than 12,000)
- **Configuration System**: Comprehensive YAML-based configuration with CLI override support
- **iCloud Integration**: Automatic file synchronization for Apple ecosystem users
- **Cost Tracking**: Real-time API usage monitoring and cost calculation
- **Threading Support**: Parallel processing for batch operations

## Development Commands

### Translation Commands

```bash
# Single novel translation (new/replace)
python cli_translator.py novel.txt

# Single novel translation with resume
python cli_translator.py novel.txt --resume

# Batch translation (new)
python cli_translator.py novels_dir --batch

# Batch translation with resume
python cli_translator.py novels_dir --batch --resume

# Use remote API (OpenRouter) instead of local
python cli_translator.py novel.txt --remote

# Generate EPUB along with text
python cli_translator.py novel.txt --epub
```

### EPUB Generation

```bash
# Create EPUB from chapter files
python make_epub.py input_dir -o output.epub --toc --cover cover.jpg

# Validate chapter numbering only
python make_epub.py input_dir -o output.epub --validate-only

# Soft mode (don't abort on issues)
python make_epub.py input_dir -o output.epub --no-strict
```

### Environment Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Set API key for remote translation
export OPENROUTER_API_KEY="your_api_key_here"
```

## Project Structure

### Translation Pipeline

1. **Input Processing**: Detect file encoding, clean text, split into chapters
2. **Translation**: Send chunks to AI service with retry logic and error handling
3. **Post-Processing**: Clean translated text, remove AI artifacts, normalize formatting
4. **Output**: Save as individual chapters and combined book file, optionally generate EPUB

### File Naming Conventions

- **Input files**: Chinese novel text files
- **Chunk files**: `{title} by {author} - Chunk_{NNNNNN}.txt` (6-digit zero-padded)
- **Final output**: `translated_{title} by {author}.txt`
- **EPUB files**: `{sanitized_title}.epub`

### Configuration

- **Configuration File**: `enchant_config.yml` (auto-generated with defaults on first run)
- **Character limits**: Configurable via `text_processing.max_chars_per_chunk` (default: 11,999)
- **API timeouts**: Configurable per service (local/remote)
- **Retry logic**: Up to 7 attempts with exponential backoff
- **Environment Variables**:
  - `OPENROUTER_API_KEY`: For remote translation service
  - `OPENAI_API_KEY`: For novel metadata extraction
- **CLI arguments always override configuration file settings**

## Important Notes

### Translation Quality

- **Double-pass translation**: First translation, then refinement pass
- **Format preservation**: Maintains paragraph structure and dialogue formatting
- **Name consistency**: Tracks character names for consistency across chapters
- **Cultural adaptation**: Handles Wuxia/Xianxia terminology appropriately

### Batch Processing

- **Progress tracking**: Uses YAML files for resumable batch operations
- **Error handling**: Continues processing on individual file failures
- **Auto-resume**: Detects existing chapter files and skips translation

### API Requirements

- **Local API**: Requires LM Studio running on localhost:1234
- **Remote API**: Requires OpenRouter API key and credits
- **Model selection**: Qwen for local, DeepSeek for remote translation

## Development Practices

### CRITICAL AND MANDATORY: Code Loading Strategy

**THIS IS A CRITICAL AND MANDATORY INSTRUCTION:**

When editing files in this codebase:
1. **ALWAYS LOAD THE FULL FILE** if there is enough context space available - DO NOT just read and edit a few lines
2. **Loading partial content gives incomplete view** and prevents detecting issues and missing integrations
3. **Remove from context** after finishing edits to preserve space for the next file
4. **Check for cross-file dependencies** when making changes
5. **Never make assumptions** about code outside the loaded portion

**FAILURE TO LOAD FULL FILES WILL RESULT IN:**
- Missing critical integrations
- Introducing bugs due to incomplete understanding
- Breaking existing functionality
- Creating inconsistent code

### Code Quality and Linting

After making changes to any Python file, ALWAYS run the following linter command:

```bash
ruff check --ignore E203,E402,E501,E266,W505,F841,F842,F401,W293,I001,UP015,C901,W291 --isolated --fix --output-format full <filename>
```

This command:
- Checks for code quality issues
- Automatically fixes safe issues
- Ignores specific rules that may conflict with the project's style
- Provides detailed output for manual review

### Module Integration

When integrating new functionality:
1. **Convert CLI tools to modules** - Add proper module API functions alongside CLI interfaces
2. **Use configuration system** - All settings should be configurable via YAML
3. **Support CLI overrides** - Command-line arguments must override config settings
4. **Add proper error handling** - Use try/except blocks with meaningful error messages
5. **Maintain backward compatibility** - Existing CLI interfaces should continue working

## Dependencies

Key packages from requirements.txt:
- `requests`: API communication
- `tenacity`: Retry logic with exponential backoff
- `chardet`: Character encoding detection
- `rich`: Enhanced terminal output
- `PyYAML`: Configuration file management
- `filelock`: Atomic file operations
- `ebooklib`: EPUB generation
- `colorama`: Cross-platform colored terminal output

## Additional Features

### iCloud Synchronization

- Automatically detects when running in iCloud Drive on macOS/iOS
- Uses `brctl` commands to ensure files are downloaded before reading
- Evicts files after processing to save local storage
- Configurable via `icloud.enabled` setting

### Model Pricing

**For OpenRouter (Remote) API:**

OpenRouter provides built-in cost tracking in the API response. To enable it:

1. Add `"usage": {"include": true}` to the request payload
2. The response will include a `usage` object with:
   - `prompt_tokens`: Number of input tokens
   - `completion_tokens`: Number of output tokens
   - `total_tokens`: Total tokens used
   - `cost`: Cost in credits/USD

Example request without streaming:
```python
payload = {
    "model": "anthropic/claude-3-opus",
    "messages": [{"role": "user", "content": "What is the capital of France?"}],
    "usage": {"include": True}  # Enable cost tracking
}

response = requests.post(url, headers=headers, data=json.dumps(payload))
response_json = response.json()

# Access usage data
if 'usage' in response_json:
    usage = response_json['usage']
    print(f"Total Tokens: {usage.get('total_tokens')}")
    print(f"Prompt Tokens: {usage.get('prompt_tokens')}")
    print(f"Completion Tokens: {usage.get('completion_tokens')}")
    print(f"Cost: ${usage.get('cost')} credits")
```

Example with streaming (using OpenAI client):
```python
from openai import OpenAI

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key="<OPENROUTER_API_KEY>",
)

response = client.chat.completions.create(
    model="anthropic/claude-3-opus",
    messages=messages,
    usage={"include": True},
    stream=True
)

for chunk in response:
    if hasattr(chunk, 'usage'):
        usage = chunk.usage
        print(f"Cost: ${usage.cost} credits")
```

**For Local API:**
- No cost tracking needed (local models are free)
- Pricing manager tracks usage statistics only

### Batch Processing

- Multi-threaded processing with configurable worker count
- Atomic progress tracking with YAML files
- Automatic retry with exponential backoff
- Detailed error reporting and recovery
- Support for recursive directory processing


## Project environment management tools

# Frontend only
uv run pnpm run dev


### Testing

# All tests (if no dhtl present)
uv run bash runtests.sh

# Python tests only
uv run pytest .
uv run pytest ./tests/test_file.py         # Specific file
uv run pytest ./tests/test_file.py::test_function  # Specific test
uv run pytest -k "test_name"               # By test name pattern
uv run pytest -m "not slow"                # Skip slow tests

# Frontend E2E tests
uv run pnpm run e2e
uv run npx playwright test                        # Alternative
uv run npx playwright test --ui                   # With UI mode


### Code Quality

# Run all linters (pre-commit, ruff, black, mypy, shellcheck, yamllint)
dhtl lint

# Lint with automatic fixes
dhtl lint --fix

# Format all code (uses ruff format, black, isort)
dhtl format

# Check formatting without changes
dhtl format --check

### Code Quality

# Python formatting and linting commands syntax to use internally in dhtl:
uv run ruff format       # format with ruff
uv run ruff check --ignore E203,E402,E501,E266,W505,F841,F842,F401,W293,I001,UP015,C901,W291 --isolated --fix --output-format full
COLUMNS=400 uv run mypy --strict --show-error-context --pretty --install-types --no-color-output --non-interactive --show-error-codes --show-error-code-links --no-error-summary --follow-imports=normal cli_translator.py >mypy_lint_log.txt

# TypeScript/JavaScript formatting and linting commands syntax to use internally in dhtl:
uv run pnpm run lint            # ESLint
uv run pnpm run format          # Prettier
uv run pnpm run check           # Check formatting without fixing

# Bash scripts linting commands syntax to use internally in dhtl:
uv run shellcheck --severity=error --extended-analysis=true  # Shellcheck (always use severity=error!)

# YAML scripts linting
uv run yamllint


### Building and Packaging

# Frontend build
uv run pnpm run build

# Build Python package (includes Electron app)
uv run bash ./install.sh              # Full installation from source
uv init                   # Init package with uv, creating pyproject.toml file, git and others
uv init --python 3.10     # Init package with a specific python version
uv init --app             # Init package with app configuration
uv init --lib             # Init package with library module configuration
uv python install 3.10    # Download and install a specific version of Python runtime
uv python pin 3.10        # Change python version for current venv
uv add <..module..>       # Add module to pyproject.toml dependencies
uv add -r requirements.txt # Add requirements from requirements.txt to pyproject.toml
uv pip install -r requirements.txt # Install dependencies from requirements.txt
uv pip compile <..arguments..> # compile requirement file
uv build                  # Build with uv
uv run python -m build    # Build wheel only

# What uv init generates:
```
.
├── .venv
│   ├── bin
│   ├── lib
│   └── pyvenv.cfg
├── .python-version
├── README.md
├── main.py
├── pyproject.toml
└── uv.lock

```

# What pyproject.toml contains:

```
[project]
name = "hello-world"
version = "0.1.0"
description = "Add your description here"
readme = "README.md"
dependencies = []

```

# What the file .python-version contains
The .python-version file contains the project's default Python version. This file tells uv which Python version to use when creating the project's virtual environment.

# What the .venv folder contains
The .venv folder contains your project's virtual environment, a Python environment that is isolated from the rest of your system. This is where uv will install your project's dependencies and binaries.

# What the file uv.lock contains:
uv.lock is a cross-platform lockfile that contains exact information about your project's dependencies. Unlike the pyproject.toml which is used to specify the broad requirements of your project, the lockfile contains the exact resolved versions that are installed in the project environment. This file should be checked into version control, allowing for consistent and reproducible installations across machines.
uv.lock is a human-readable TOML file but is managed by uv and should not be edited manually.

# Install package
uv pip install dist/*.whl    # Install built wheel
uv pip install -e .         # Development install

# Install global uv tools
uv tools install ruff
uv tools install mypy
uv tools install yamllint
uv tools install bump_my_version
...etc.

# Execute globally installed uv tools
uv tools run ruff <..arguments..>
uv tools run mypy <..arguments..>
uv tools run yamllint <..arguments..>
uv tools run bump_my_version <..arguments..>
...etc.