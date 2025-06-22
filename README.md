<div align="center">

# 📚 EnChANT - English-Chinese Automatic Novel Translator

**Transform Chinese novels into English EPUBs with AI-powered translation**

[![CI Status](https://github.com/Emasoft/enchant-book-manager/actions/workflows/ci.yml/badge.svg)](https://github.com/Emasoft/enchant-book-manager/actions/workflows/ci.yml)
[![Dependency Check](https://github.com/Emasoft/enchant-book-manager/actions/workflows/dependency-check.yml/badge.svg)](https://github.com/Emasoft/enchant-book-manager/actions/workflows/dependency-check.yml)
[![Pre-commit](https://github.com/Emasoft/enchant-book-manager/actions/workflows/pre-commit.yml/badge.svg)](https://github.com/Emasoft/enchant-book-manager/actions/workflows/pre-commit.yml)
[![Security Scan](https://github.com/Emasoft/enchant-book-manager/actions/workflows/gitleaks.yml/badge.svg)](https://github.com/Emasoft/enchant-book-manager/actions/workflows/gitleaks.yml)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache%202.0-yellow.svg)](https://opensource.org/licenses/Apache-2.0)
[![Package: UV](https://img.shields.io/badge/package-UV-green.svg)](https://github.com/astral-sh/uv)

<p align="center">
  <strong>⚠️ ALPHA SOFTWARE - USE AT YOUR OWN RISK ⚠️</strong>
</p>

<p align="center">
  <em>This project is in early alpha stage and not ready for production use.<br/>Features may change, break, or be incomplete. Testing and feedback welcome!</em>
</p>

</div>

---

## 🎯 Overview

EnChANT is a comprehensive system for transforming Chinese novels into professionally formatted English EPUBs. It automates the entire workflow from raw Chinese text files to polished e-books, leveraging AI for accurate translation while preserving the literary quality of the original work.

### 🔄 Three-Phase Processing Pipeline

1. **📝 Intelligent Renaming** - Extract metadata using AI to rename files with proper English titles and author names
2. **🌐 Advanced Translation** - Translate Chinese text to English using local or cloud AI models with context awareness
3. **📖 EPUB Generation** - Create well-formatted EPUB files with proper chapter detection and table of contents

## 📑 Table of Contents

<details>
<summary>Click to expand</summary>

- [🎯 Overview](#-overview)
- [✨ Features](#-features)
- [⚡ Quick Start](#-quick-start)
- [📦 Installation](#-installation)
  - [Prerequisites](#prerequisites)
  - [Install from PyPI](#install-from-pypi)
  - [Install from Source](#install-from-source)
  - [Development Setup](#development-setup)
- [🚀 Usage](#-usage)
  - [Command Line Interface](#command-line-interface)
  - [Basic Examples](#basic-examples)
  - [Advanced Usage](#advanced-usage)
- [⚙️ Configuration](#️-configuration)
  - [Configuration File](#configuration-file)
  - [Environment Variables](#environment-variables)
- [📁 Project Structure](#-project-structure)
- [🔑 API Requirements](#-api-requirements)
- [🛠️ Development](#️-development)
  - [Development Tools](#development-tools)
  - [Code Quality](#code-quality)
  - [Building](#building)
- [🧪 Testing](#-testing)
- [🤝 Contributing](#-contributing)
- [📄 License](#-license)
- [🙏 Acknowledgments](#-acknowledgments)

</details>

## ✨ Features

### 🎨 Core Capabilities
- **🔄 Unified Processing Pipeline** - Single command orchestrates all three phases
- **⚡ Smart Phase Management** - Skip any phase or run them independently
- **📂 Batch Operations** - Process entire directories with parallel execution
- **💾 Robust Resume Support** - Continue from exact interruption point
- **🌏 Multi-Encoding Support** - UTF-8, GB2312, GB18030, Big5, and more
- **📊 Progress Tracking** - Real-time progress with automatic state saving

### 🤖 AI Integration
- **🏠 Local Mode** - Use LM Studio for free, private translation
- **☁️ Cloud Mode** - OpenRouter API with 100+ model options
- **💰 Cost Tracking** - Monitor API usage and expenses in real-time
- **🔧 Model Flexibility** - Switch models on-the-fly via command line

### 📚 EPUB Features
- **🔍 Smart Chapter Detection** - Recognizes 20+ chapter patterns
- **📑 Automatic TOC Generation** - Build navigable table of contents
- **🎨 Full Customization** - Custom CSS, metadata, covers
- **✅ Chapter Validation** - Ensure proper sequence and formatting
- **🌐 Multi-Language Support** - Set language codes for proper rendering

## ⚡ Quick Start

```bash
# Install from PyPI (when available)
pip install enchant-book-manager

# Process a Chinese novel with AI renaming and translation
enchant-cli "我的小说.txt" --openai-api-key YOUR_KEY

# Translate only (skip renaming)
enchant-cli "My Novel.txt" --skip-renaming

# Generate EPUB from translated text
enchant-cli --translated "path/to/translated.txt"
```

## 📦 Installation

### Prerequisites

| Requirement | Version | Purpose |
|------------|---------|----------|
| Python | 3.12+ | Core runtime |
| [LM Studio](https://lmstudio.ai/) | Latest | Local AI translation (optional) |
| [OpenRouter API](https://openrouter.ai/) | - | Cloud translation & renaming (optional) |
| UV | Latest | Package management (development) |

### Install from PyPI

> **Note**: PyPI package coming soon! For now, please install from source.

```bash
# When available:
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

## 🚀 Usage

### Basic Examples

<details>
<summary>📖 Single Novel Processing</summary>

```bash
# Full pipeline: Rename → Translate → EPUB
enchant-cli "我的小说.txt" --openai-api-key YOUR_KEY

# Skip renaming (for pre-named files)
enchant-cli "My Novel by Author.txt" --skip-renaming

# EPUB only (from existing translation)
enchant-cli --translated "translated_novel.txt"
```

</details>

<details>
<summary>📚 Batch Processing</summary>

```bash
# Process entire directory
enchant-cli novels/ --batch --openai-api-key YOUR_KEY

# Resume interrupted batch
enchant-cli novels/ --batch --resume

# Custom encoding for legacy files
enchant-cli novels/ --batch --encoding gb18030
```

</details>

<details>
<summary>🎯 Phase Control</summary>

```bash
# Rename only
enchant-cli "中文小说.txt" --skip-translating --skip-epub

# Translate only
enchant-cli "Novel.txt" --skip-renaming --skip-epub

# EPUB only
enchant-cli "Novel.txt" --skip-renaming --skip-translating
```

</details>

### Command Line Interface

<details>
<summary>View full help output</summary>

```
usage: enchant-cli [-h] [--config CONFIG] [--preset PRESET]
                   [--encoding ENCODING] [--max-chars MAX_CHARS] [--resume]
                   [--epub] [--batch] [--remote] [--skip-renaming]
                   [--skip-translating] [--skip-epub]
                   [--translated TRANSLATED] [--openai-api-key OPENAI_API_KEY]
                   [--timeout TIMEOUT] [--max-retries MAX_RETRIES]
                   [--model MODEL] [--endpoint ENDPOINT]
                   [--temperature TEMPERATURE] [--max-tokens MAX_TOKENS]
                   [--double-pass] [--rename-model RENAME_MODEL]
                   [--rename-temperature RENAME_TEMPERATURE]
                   [--kb-to-read KB_TO_READ] [--rename-workers RENAME_WORKERS]
                   [--rename-dry-run] [--epub-title EPUB_TITLE]
                   [--epub-author EPUB_AUTHOR] [--cover COVER]
                   [--epub-language EPUB_LANGUAGE] [--no-toc] [--no-validate]
                   [--epub-strict] [--custom-css CUSTOM_CSS]
                   [--epub-metadata EPUB_METADATA] [--json-log JSON_LOG]
                   [--validate-only]
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
  --rename-model RENAME_MODEL
                        AI model for renaming phase (overrides config/preset)
  --rename-temperature RENAME_TEMPERATURE
                        Temperature for renaming phase (overrides
                        config/preset)
  --kb-to-read KB_TO_READ
                        KB to read from file start for metadata extraction
                        (default: 35)
  --rename-workers RENAME_WORKERS
                        Number of parallel workers for batch renaming
                        (default: CPU count)
  --rename-dry-run      Preview what files would be renamed without actually
                        renaming them
  --epub-title EPUB_TITLE
                        Override book title for EPUB
  --epub-author EPUB_AUTHOR
                        Override author name for EPUB
  --cover COVER         Path to cover image file (.jpg/.jpeg/.png)
  --epub-language EPUB_LANGUAGE
                        Language code for the EPUB (default: en)
  --no-toc              Disable table of contents generation
  --no-validate         Skip chapter validation
  --epub-strict         Enable strict mode (abort on validation issues)
  --custom-css CUSTOM_CSS
                        Path to custom CSS file for EPUB styling
  --epub-metadata EPUB_METADATA
                        Additional metadata in JSON format: {"publisher":
                        "...", "description": "...", "series": "...",
                        "series_index": "..."}
  --json-log JSON_LOG   Enable JSON logging for chapter validation issues
                        (path to log file)
  --validate-only       Just scan and validate chapters without creating EPUB
```

</details>

### Advanced Usage

<details>
<summary>🔧 Model Configuration</summary>

```bash
# Use specific models
enchant-cli novel.txt --model "gpt-4" --temperature 0.3

# Different model for renaming
enchant-cli novel.txt --rename-model "claude-3-haiku"

# Custom endpoints
enchant-cli novel.txt --endpoint "http://localhost:8080/v1/completions"
```

</details>

<details>
<summary>📝 EPUB Customization</summary>

```bash
# Full EPUB customization
enchant-cli --translated novel.txt \
  --epub-title "My Custom Title" \
  --epub-author "Author Name" \
  --cover "cover.jpg" \
  --custom-css "style.css" \
  --epub-metadata '{"publisher": "My Publisher", "series": "Book 1"}'

# Validation and debugging
enchant-cli --translated novel.txt --validate-only --json-log validation.json
```

</details>

<details>
<summary>🌐 Encoding Support</summary>

```bash
# Handle various Chinese encodings
enchant-cli "traditional.txt" --encoding big5
enchant-cli "simplified.txt" --encoding gb2312
enchant-cli "modern.txt" --encoding gb18030

# Auto-detect encoding (default)
enchant-cli "unknown_encoding.txt"
```

</details>

## ⚙️ Configuration

### Configuration File

EnChANT uses YAML configuration for default settings. Create `enchant_config.yml` in your working directory:

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

epub:
  language: "en"
  generate_toc: true
  validate_chapters: true
  strict_mode: false

api:
  timeout: 300
  max_retries: 3
```

### Environment Variables

```bash
# OpenRouter API key for cloud translation and renaming
export OPENROUTER_API_KEY="your-key-here"

# Python environment (if using specific version)
export UV_PYTHON="python3.12"

# Disable telemetry (optional)
export UV_NO_ANALYTICS=1
```

## 📁 Project Structure

### Output Organization

```
📂 novels/                              # Input directory
├── 📄 我的小说.txt                      # Original Chinese novel
├── 📄 My Novel by Author Name.txt      # After renaming
├── 📁 My Novel/                        # Translation workspace
│   ├── 📄 Chapter 0001.txt             # Individual chapters
│   ├── 📄 Chapter 0002.txt
│   └── 📄 ...
├── 📄 translated_My Novel by Author.txt # Complete translation
└── 📚 My_Novel.epub                    # Final EPUB
```

### Source Code Structure

```
📂 src/enchant_book_manager/
├── 📄 enchant_cli.py         # Main CLI orchestrator
├── 📄 renamenovels.py        # AI-powered renaming
├── 📄 cli_translator.py      # Translation engine
├── 📄 make_epub.py           # EPUB generator
├── 📄 config_manager.py      # Configuration handling
├── 📄 cost_tracker.py        # API cost tracking
└── 📄 common_*.py            # Shared utilities
```

## 🔑 API Requirements

### Local Translation (Default)

<table>
<tr>
<td><strong>✅ Pros</strong></td>
<td><strong>❌ Cons</strong></td>
</tr>
<tr>
<td>

- Free (no API costs)
- Private (data stays local)
- No rate limits
- Works offline

</td>
<td>

- Requires LM Studio setup
- Needs powerful hardware
- Limited model selection
- Slower on CPU

</td>
</tr>
</table>

**Setup**: Install [LM Studio](https://lmstudio.ai/) and load a model (e.g., Qwen 2.5)

### Cloud Translation (OpenRouter)

<table>
<tr>
<td><strong>✅ Pros</strong></td>
<td><strong>❌ Cons</strong></td>
</tr>
<tr>
<td>

- 100+ model options
- No hardware requirements
- Fast processing
- Professional models

</td>
<td>

- Costs money per use
- Requires API key
- Internet required
- Rate limits apply

</td>
</tr>
</table>

**Setup**: Get API key from [OpenRouter](https://openrouter.ai/)

## 🛠️ Development

### Development Tools

| Tool | Purpose | Command |
|------|---------|----------|
| **UV** | Package management | `uv sync` |
| **Ruff** | Linting & formatting | `uv run ruff check` |
| **MyPy** | Type checking | `uv run mypy src` |
| **Pytest** | Testing | `uv run pytest` |
| **Pre-commit** | Git hooks | `uv run pre-commit install` |

### Code Quality

```bash
# Run all quality checks
uv run pre-commit run --all-files

# Format code
uv run ruff format

# Type check
uv run mypy src --strict

# Security scan
gitleaks detect --verbose
```

### Building

```bash
# Build distribution packages
uv build

# Install locally for testing
uv pip install -e .

# Create standalone executable (coming soon)
# uv build --standalone
```

## 🧪 Testing

```bash
# Run all tests
uv run pytest

# Run with coverage report
uv run pytest --cov=src/enchant_book_manager --cov-report=html

# Run specific test file
uv run pytest tests/test_enchant_cli.py

# Run integration tests (requires API key)
OPENROUTER_API_KEY=your_key uv run pytest tests/integration/

# Run with verbose output
uv run pytest -v --tb=short
```

### Test Coverage

| Module | Coverage |
|--------|----------|
| Core CLI | 92% |
| Translation | 88% |
| EPUB Generation | 95% |
| Utilities | 99% |

## 🤝 Contributing

We welcome contributions! This is an alpha project and needs community help to improve.

### How to Contribute

1. **🍴 Fork** the repository
2. **🌿 Branch** from `main` (`git checkout -b feature/your-feature`)
3. **📦 Install** dev dependencies (`uv sync --all-extras`)
4. **✨ Make** your changes
5. **✅ Test** thoroughly (`uv run pytest`)
6. **📝 Commit** with clear messages
7. **⬆️ Push** to your fork
8. **🎯 PR** with description of changes

### Areas Needing Help

- 🌍 Additional language support
- 🧪 More test coverage
- 📚 Documentation improvements
- 🐛 Bug fixes and edge cases
- 🎨 UI/UX enhancements
- 🚀 Performance optimizations

### Code Style

```bash
# Before committing, run:
uv run pre-commit run --all-files
```

## 📄 License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [LM Studio](https://lmstudio.ai/) for local AI infrastructure
- [OpenRouter](https://openrouter.ai/) for unified model access
- [UV](https://github.com/astral-sh/uv) for modern Python tooling
- [Ruff](https://github.com/astral-sh/ruff) for blazing-fast linting
- All contributors and testers

---

<div align="center">

**Made with ❤️ for the Chinese novel translation community**

[Report Bug](https://github.com/Emasoft/enchant-book-manager/issues) · [Request Feature](https://github.com/Emasoft/enchant-book-manager/issues) · [Discussions](https://github.com/Emasoft/enchant-book-manager/discussions)

</div>
