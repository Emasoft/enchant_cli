# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

ENCHANT_BOOK_MANAGER is a Python-based system for translating Chinese novels to English using AI translation services. The project supports both local (LM Studio) and remote (OpenRouter) translation APIs, with features for book management, chapter splitting, and EPUB generation.

## Core Architecture

### Main Components

- **cli_translator.py**: Main command-line interface and orchestration layer
- **translation_service.py**: AI translation service with dual API support (local/remote)
- **make_epub.py**: EPUB generation from text chapters with validation
- **ENCHANT-MANAGER/**: Contains additional book management tools and database utilities

### Key Features

- **Dual Translation APIs**: Local (LM Studio with Qwen models) and remote (OpenRouter with DeepSeek)
- **Chapter Management**: Intelligent text splitting while preserving paragraph integrity
- **Batch Processing**: Process multiple novels with progress tracking and resume capability
- **EPUB Generation**: Convert translated novels to EPUB format with TOC
- **Character Limit Handling**: Configurable character limits per translation chunk (default: 12,000)

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
- **Chapter files**: `{title} by {author} - Chapter {N}.txt`
- **Final output**: `translated_{title} by {author}.txt`
- **EPUB files**: `{sanitized_title}.epub`

### Configuration

- **Character limits**: Controlled by `MAXCHARS` constant (default: 12,000)
- **API timeouts**: Connection (30s), Response (300s)
- **Retry logic**: Up to 7 attempts with exponential backoff

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

## Dependencies

Key packages from pyproject.toml:
- `requests`: API communication
- `tenacity`: Retry logic with exponential backoff
- `chardet`: Character encoding detection
- `rich`: Enhanced terminal output
- `textual`: TUI components (in ENCHANT-MANAGER)
- `peewee`: Database ORM (for book management)
- `ebooklib`: EPUB generation (optional dependency)