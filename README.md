# EnChANT - English-Chinese Automatic Novel Translator

[![CI](https://github.com/Emasoft/enchant-book-manager/actions/workflows/ci.yml/badge.svg)](https://github.com/Emasoft/enchant-book-manager/actions/workflows/ci.yml)
[![Dependency Check](https://github.com/Emasoft/enchant-book-manager/actions/workflows/dependency-check.yml/badge.svg)](https://github.com/Emasoft/enchant-book-manager/actions/workflows/dependency-check.yml)
[![Pre-commit](https://github.com/Emasoft/enchant-book-manager/actions/workflows/pre-commit.yml/badge.svg)](https://github.com/Emasoft/enchant-book-manager/actions/workflows/pre-commit.yml)
[![Gitleaks Security](https://github.com/Emasoft/enchant-book-manager/actions/workflows/gitleaks.yml/badge.svg)](https://github.com/Emasoft/enchant-book-manager/actions/workflows/gitleaks.yml)

A unified tool for processing Chinese novels through three phases:
1. **Renaming** - AI-powered metadata extraction and file renaming
2. **Translation** - Chinese to English translation using AI
3. **EPUB Generation** - Create EPUB files from translated chapters

## Table of Contents
- [Features](#features)
- [Installation](#installation)
  - [Prerequisites](#prerequisites)
  - [Install from PyPI](#install-from-pypi)
  - [Install from Source](#install-from-source)
  - [Development Setup](#development-setup)
- [Quick Start](#quick-start)
- [Command Line Interface](#command-line-interface)
  - [Main Command (`enchant`)](#main-command-enchant)
  - [Individual Commands](#individual-commands)
- [Usage Examples](#usage-examples)
- [Configuration](#configuration)
- [Project Structure](#project-structure)
- [API Requirements](#api-requirements)
- [Development](#development)
- [Testing](#testing)
- [Contributing](#contributing)

## Features

- **Three-Phase Processing**: Rename → Translate → EPUB generation
- **Flexible Workflow**: Skip any phase independently
- **Batch Processing**: Process entire directories of novels
- **Resume Support**: Continue interrupted operations
- **Multiple Encodings**: Support for UTF-8, GB2312, GB18030, Big5
- **Smart Chapter Detection**: Recognizes various chapter formats
- **Progress Tracking**: Automatic progress saving and recovery
- **API Integration**: Works with local LM Studio or remote OpenRouter API
- **Cost Tracking**: Monitors API usage costs (remote mode)

## Installation

### Prerequisites

- Python 3.12 or higher
- For local translation: [LM Studio](https://lmstudio.ai/) running on localhost:1234
- For renaming/remote translation: OpenRouter API key

### Install from PyPI

```bash
pip install enchant-book-manager
```

### Install from Source

#### Using UV (Recommended)

[UV](https://github.com/astral-sh/uv) is a modern Python package manager that's faster and more reliable than pip.

```bash
# Install UV
pip install uv

# Clone the repository
git clone https://github.com/Emasoft/enchant-book-manager.git
cd enchant-book-manager

# Create virtual environment and install
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv sync
```

#### Using pip

```bash
# Clone the repository
git clone https://github.com/Emasoft/enchant-book-manager.git
cd enchant-book-manager

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install in editable mode
pip install -e .
```

### Development Setup

For development with all testing and linting tools:

```bash
# Using UV
uv sync --all-extras

# Using pip
pip install -e ".[dev]"

# Install pre-commit hooks
uv run pre-commit install  # or: pre-commit install
```

## Quick Start

### Full Processing (All Phases)
```bash
enchant novel.txt --openai-api-key YOUR_KEY
```

### Translation Only (Skip Renaming)
```bash
enchant novel.txt --skip-renaming
```

### EPUB Generation Only (From Existing Translation)
```bash
enchant novel.txt --skip-renaming --skip-translating

# Or directly from any translated text file:
enchant --translated path/to/translated.txt
```

### Batch Processing
```bash
enchant novels_folder --batch --openai-api-key YOUR_KEY
```

## Command Line Interface

### Main Command (`enchant`)

The main orchestrator that coordinates all three processing phases.

```
usage: enchant [-h] [--config CONFIG] [--preset PRESET] [--encoding ENCODING]
               [--max-chars MAX_CHARS] [--resume] [--epub] [--batch]
               [--remote] [--skip-renaming] [--skip-translating] [--skip-epub]
               [--translated TRANSLATED] [--openai-api-key OPENAI_API_KEY]
               [--timeout TIMEOUT] [--max-retries MAX_RETRIES] [--model MODEL]
               [--endpoint ENDPOINT] [--temperature TEMPERATURE]
               [--max-tokens MAX_TOKENS] [--double-pass]
               [filepath]

EnChANT - English-Chinese Automatic Novel Translator

positional arguments:
  filepath              Path to Chinese novel text file (single mode) or
                        directory containing novels (batch mode). Optional
                        when using --translated with --skip-renaming and
                        --skip-translating

options:
  -h, --help            show this help message and exit
  --config CONFIG       Path to configuration file (default:
                        enchant_config.yml)
  --preset PRESET       Configuration preset name (LOCAL, REMOTE, or custom
                        preset)
  --encoding ENCODING   Character encoding of input files. Common: utf-8,
                        gb2312, gb18030, big5 (default: utf-8)
  --max-chars MAX_CHARS
                        Maximum characters per translation chunk. Affects API
                        usage and memory (default: 11999)
  --resume              Resume interrupted translation. Single: continues from
                        last chunk. Batch: uses progress file
  --epub                Generate EPUB file after translation completes.
                        Creates formatted e-book with table of contents
  --batch               Batch mode: process all .txt files in the specified
                        directory. Tracks progress automatically
  --remote              Use remote OpenRouter API instead of local LM Studio.
                        Requires OPENROUTER_API_KEY environment variable
  --skip-renaming       Skip the file renaming phase
  --skip-translating    Skip the translation phase
  --skip-epub           Skip the EPUB generation phase
  --translated TRANSLATED
                        Path to already translated text file for direct EPUB
                        generation. Automatically implies --skip-renaming and
                        --skip-translating. Makes filepath argument optional
  --openai-api-key OPENAI_API_KEY
                        OpenRouter API key for novel renaming (can also use
                        OPENROUTER_API_KEY env var)
  --timeout TIMEOUT     API request timeout in seconds (overrides
                        config/preset)
  --max-retries MAX_RETRIES
                        Maximum retry attempts for failed requests (overrides
                        config/preset)
  --model MODEL         AI model name (overrides config/preset)
  --endpoint ENDPOINT   API endpoint URL (overrides config/preset)
  --temperature TEMPERATURE
                        AI model temperature (overrides config/preset)
  --max-tokens MAX_TOKENS
                        Maximum tokens per request (overrides config/preset)
  --double-pass         Enable double-pass translation (overrides
                        config/preset)
```

### Individual Commands

#### Translation Command (`enchant-translate`)

```
usage: enchant-translate [-h] [--config CONFIG] [--encoding ENCODING]
                         [--max_chars MAX_CHARS] [--resume] [--epub] [--batch]
                         [--remote]
                         filepath

CLI tool for translating Chinese novels to English using AI translation services

positional arguments:
  filepath              Path to Chinese novel text file (single mode) or
                        directory containing novels (batch mode)

options:
  -h, --help            show this help message and exit
  --config CONFIG       Path to configuration file (default:
                        enchant_config.yml)
  --encoding ENCODING   Character encoding of input files. Common: utf-8,
                        gb2312, gb18030, big5 (default: utf-8)
  --max_chars MAX_CHARS
                        Maximum characters per translation chunk. Affects API
                        usage and memory (default: 11999)
  --resume              Resume interrupted translation. Single: continues from
                        last chunk. Batch: uses progress file
  --epub                Generate EPUB file after translation completes.
                        Creates formatted e-book with table of contents
  --batch               Batch mode: process all .txt files in the specified
                        directory. Tracks progress automatically
  --remote              Use remote OpenRouter API instead of local LM Studio.
                        Requires OPENROUTER_API_KEY environment variable
```

#### Rename Command (`enchant-rename`)

```
usage: enchant-rename [-h] [-r] [-k KB] [--version] path

Novel Auto Renamer v1.3.1
Automatically rename text files based on extracted novel information.

positional arguments:
  path             Path to the folder containing text files.

options:
  -h, --help       show this help message and exit
  -r, --recursive  Recursively search through subfolders.
  -k KB, --kb KB   Amount of KB to read from the beginning of each file.
  --version        show program's version number and exit
```

#### EPUB Builder Command (`enchant-epub`)

```
usage: enchant-epub [-h] -o OUTPUT [--title TITLE] [--author AUTHOR] [--toc]
                    [--cover COVER] [--add N[+]] [--validate-only]
                    [--no-strict] [--json-log JSON_LOG]
                    input_dir

TXT chunks → EPUB builder / validator

positional arguments:
  input_dir             Directory with .txt chunks

options:
  -h, --help            show this help message and exit
  -o OUTPUT, --output OUTPUT
                        Output directory or .epub
  --title TITLE         Override book title
  --author AUTHOR       Override author
  --toc                 Detect chapter headings and build TOC
  --cover COVER         Cover image (jpg/png)
  --add N[+]            Append chunk N (or N+) to existing EPUB
  --validate-only       Only scan & report issues
  --no-strict           Soft mode (don't abort on issues)
  --json-log JSON_LOG   Write JSON-lines issue log
```

## Usage Examples

### Single File Processing

```bash
# Full processing (rename + translate + EPUB)
enchant "我的小说.txt" --openai-api-key YOUR_KEY

# Translation only (skip renaming, generate EPUB)
enchant "My Novel.txt" --skip-renaming

# EPUB from any translated text file
enchant --translated "path/to/translated.txt"

# Process renamed file (skip renaming phase)
enchant "Novel Title by Author Name.txt" --skip-renaming

# Just rename files (no translation or EPUB)
enchant "小说.txt" --skip-translating --skip-epub --openai-api-key YOUR_KEY
```

### Batch Processing

```bash
# Process entire directory
enchant novels/ --batch --openai-api-key YOUR_KEY

# Resume interrupted batch
enchant novels/ --batch --resume

# Batch with custom encoding
enchant novels/ --batch --encoding gb18030
```

### Advanced Options

```bash
# Use remote API (OpenRouter) instead of local
export OPENROUTER_API_KEY=your_key_here
enchant novel.txt --remote

# Custom configuration file
enchant novel.txt --config my_config.yml

# Use configuration preset
enchant novel.txt --preset REMOTE

# Override model settings
enchant novel.txt --model "gpt-4" --temperature 0.3

# Handle Big5 encoded files
enchant "traditional_novel.txt" --encoding big5

# Custom chunk size for large files
enchant huge_novel.txt --max-chars 5000
```

### Phase Combinations

```bash
# Rename only
enchant "中文小说.txt" --skip-translating --skip-epub --openai-api-key YOUR_KEY

# Translate only (no rename, no EPUB)
enchant "Already Named Novel.txt" --skip-renaming --skip-epub

# EPUB only from translation directory
enchant "Novel by Author.txt" --skip-renaming --skip-translating

# EPUB from external translated file
enchant --translated "/path/to/translation.txt"
```

## Configuration

The tool uses YAML configuration files. Default configuration is `enchant_config.yml` in the current directory.

### Example Configuration

```yaml
# enchant_config.yml
translation:
  local:
    endpoint: "http://localhost:1234/v1/completions"
    model: "local-model"
    temperature: 0.7
    max_tokens: 4000
  remote:
    endpoint: "https://openrouter.ai/api/v1/chat/completions"
    model: "anthropic/claude-3-haiku"
    temperature: 0.7
    max_tokens: 4000

renaming:
  model: "openai/gpt-4o-mini"
  temperature: 0.7
  max_tokens: 500

api:
  timeout: 300
  max_retries: 3
```

## Project Structure

After processing, files are organized as:
```
input_dir/
├── original_novel.txt
├── Renamed Novel by Author (Romanized) - 原标题 by 原作者.txt
├── Renamed Novel/
│   ├── Renamed Novel by Author - Chapter 1.txt
│   ├── Renamed Novel by Author - Chapter 2.txt
│   └── ...
├── translated_Renamed Novel by Author.txt
└── Renamed_Novel.epub
```

## API Requirements

### For Renaming Phase
- **API**: OpenRouter API
- **Key**: Set via `--openai-api-key` or `OPENROUTER_API_KEY` environment variable
- **Models**: Supports any OpenRouter-compatible model (default: gpt-4o-mini)

### For Translation Phase

#### Local Mode (Default)
- **Requirements**: LM Studio running on `localhost:1234`
- **Models**: Any model loaded in LM Studio
- **Cost**: Free (runs on your hardware)

#### Remote Mode (`--remote`)
- **API**: OpenRouter API
- **Key**: Set `OPENROUTER_API_KEY` environment variable
- **Models**: Any OpenRouter model (default: claude-3-haiku)
- **Cost**: Based on model usage

## Development

This project uses modern Python development tools:

### Package Management
- **UV**: Fast, reliable Python package manager
- **pyproject.toml**: PEP 621 compliant project configuration

### Code Quality
- **ruff**: Fast Python linter and formatter
- **mypy**: Static type checking
- **black**: Code formatting
- **pre-commit**: Git hooks for code quality

### Dependency Management
- **deptry**: Dependency checker (runs on commits)
- **pip-audit**: Security vulnerability scanning

### CI/CD
- GitHub Actions for continuous integration
- Automated testing, linting, and security checks
- Gitleaks for secret scanning

## Testing

Run the test suite:

```bash
# Using UV
uv run pytest

# With coverage
uv run pytest --cov=src/enchant_book_manager --cov-report=html

# Run specific test
uv run pytest tests/test_enchant_cli.py::test_batch_mode
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Install development dependencies (`uv sync --all-extras`)
4. Make your changes
5. Run tests and linting (`uv run pytest && uv run ruff check`)
6. Commit your changes (pre-commit hooks will run automatically)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

### Development Commands

```bash
# Format code
uv run ruff format

# Lint code
uv run ruff check --fix

# Type checking
uv run mypy src

# Run pre-commit on all files
uv run pre-commit run --all-files

# Update dependencies
uv lock --update-all
```
