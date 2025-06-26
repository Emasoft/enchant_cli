#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
# - Initial creation from enchant_cli.py refactoring
# - Extracted command-line parsing logic
# - Contains argument parser setup and validation
#

"""
cli_parser.py - Command-line argument parsing for EnChANT
========================================================

Handles parsing and validation of command-line arguments for the EnChANT CLI.
Provides the argument parser configuration and help text.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any


def create_parser(config: dict[str, Any]) -> argparse.ArgumentParser:
    """Create the argument parser with all command-line options.

    Args:
        config: Configuration dictionary for default values

    Returns:
        Configured ArgumentParser instance
    """
    parser = argparse.ArgumentParser(
        description="EnChANT - English-Chinese Automatic Novel Translator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
====================================================================================
USAGE EXAMPLES:
====================================================================================

SINGLE FILE PROCESSING:

  Full processing (rename + translate + EPUB):
    $ enchant-cli "我的小说.txt" --openai-api-key YOUR_KEY

  Translation only (skip renaming, generate EPUB):
    $ enchant-cli "My Novel.txt" --skip-renaming

  EPUB from any translated text file:
    $ enchant-cli --translated "path/to/translated.txt"

  Process renamed file (skip renaming phase):
    $ enchant-cli "Novel Title by Author Name.txt" --skip-renaming

  Just rename files (no translation or EPUB):
    $ enchant-cli "小说.txt" --skip-translating --skip-epub --openai-api-key YOUR_KEY

BATCH PROCESSING:

  Process entire directory:
    $ enchant-cli novels/ --batch --openai-api-key YOUR_KEY

  Resume interrupted batch:
    $ enchant-cli novels/ --batch --resume

  Batch with custom encoding:
    $ enchant-cli novels/ --batch --encoding gb18030

ADVANCED OPTIONS:

  Use remote API (OpenRouter) instead of local:
    $ enchant-cli novel.txt --remote
    $ export OPENROUTER_API_KEY=your_key_here

  Custom configuration file:
    $ enchant-cli novel.txt --config my_config.yml

  Use configuration preset:
    $ enchant-cli novel.txt --preset REMOTE

  Override model settings:
    $ enchant-cli novel.txt --model "gpt-4" --temperature 0.3

  Handle Big5 encoded files:
    $ enchant-cli "traditional_novel.txt" --encoding big5

  Custom chunk size for large files:
    $ enchant-cli huge_novel.txt --max-chars 5000

RENAMING OPTIONS:

  Custom model for renaming:
    $ enchant-cli novel.txt --rename-model "gpt-4" --openai-api-key YOUR_KEY

  Preview renaming without changes:
    $ enchant-cli novel.txt --rename-dry-run --openai-api-key YOUR_KEY

  Adjust metadata extraction:
    $ enchant-cli novel.txt --kb-to-read 50 --rename-temperature 0.5

EPUB OPTIONS:

  Custom title and author:
    $ enchant-cli --translated novel.txt --epub-title "My Title" --epub-author "My Author"

  Add cover image:
    $ enchant-cli --translated novel.txt --cover "cover.jpg"

  Custom CSS styling:
    $ enchant-cli --translated novel.txt --custom-css "style.css"

  Add metadata:
    $ enchant-cli --translated novel.txt --epub-metadata '{"publisher": "My Pub", "series": "My Series"}'

  Validate chapters only:
    $ enchant-cli --translated novel.txt --validate-only

  Disable TOC generation:
    $ enchant-cli --translated novel.txt --no-toc

  Strict validation mode:
    $ enchant-cli --translated novel.txt --epub-strict

PHASE COMBINATIONS:

  Rename only:
    $ enchant-cli "中文小说.txt" --skip-translating --skip-epub --openai-api-key YOUR_KEY

  Translate only (no rename, no EPUB):
    $ enchant-cli "Already Named Novel.txt" --skip-renaming --skip-epub

  EPUB only from translation directory:
    $ enchant-cli "Novel by Author.txt" --skip-renaming --skip-translating

  EPUB from external translated file:
    $ enchant-cli --translated "/path/to/translation.txt"

====================================================================================
PROCESSING PHASES:
====================================================================================
  1. RENAMING: Extract metadata and rename files (requires OpenRouter API key)
     Options: --rename-model, --rename-temperature, --kb-to-read, --rename-dry-run

  2. TRANSLATION: Translate Chinese text to English
     Options: --remote, --max-chars, --resume, --model, --temperature

  3. EPUB: Generate EPUB from translated novel
     Options: --epub-title, --epub-author, --cover, --epub-language, --custom-css,
              --epub-metadata, --no-toc, --no-validate, --epub-strict, --validate-only

SKIP FLAGS:
  --skip-renaming     Skip phase 1 (file renaming)
  --skip-translating  Skip phase 2 (translation)
  --skip-epub        Skip phase 3 (EPUB generation)

BEHAVIOR:
  • Each phase can be independently skipped
  • Skipped phases preserve existing data
  • --resume works with all phase combinations
  • Progress saved for batch operations
  • --translated allows EPUB from any text file

API KEYS:
  • Renaming requires OpenRouter API key (--openai-api-key or OPENROUTER_API_KEY env)
  • Translation uses local LM Studio by default (--remote for OpenRouter)
  • Remote translation requires OPENROUTER_API_KEY environment variable
""",
    )

    parser.add_argument(
        "filepath",
        type=str,
        nargs="?",
        help="Path to Chinese novel text file (single mode) or directory containing novels (batch mode). Optional when using --translated with --skip-renaming and --skip-translating",
    )

    parser.add_argument(
        "--config",
        type=str,
        default="enchant_config.yml",
        help="Path to configuration file (default: enchant_config.yml)",
    )

    parser.add_argument(
        "--preset",
        type=str,
        help="Configuration preset name (LOCAL, REMOTE, or custom preset)",
    )

    parser.add_argument(
        "--encoding",
        type=str,
        default=config["text_processing"]["default_encoding"],
        help=f"Character encoding of input files. Common: utf-8, gb2312, gb18030, big5 (default: {config['text_processing']['default_encoding']})",
    )

    parser.add_argument(
        "--max-chars",
        type=int,
        default=config["text_processing"]["max_chars_per_chunk"],
        help=f"Maximum characters per translation chunk. Affects API usage and memory (default: {config['text_processing']['max_chars_per_chunk']})",
    )

    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume interrupted translation. Single: continues from last chunk. Batch: uses progress file",
    )

    parser.add_argument(
        "--epub",
        action="store_true",
        help="Generate EPUB file after translation completes. Creates formatted e-book with table of contents",
    )

    parser.add_argument(
        "--batch",
        action="store_true",
        help="Batch mode: process all .txt files in the specified directory. Tracks progress automatically",
    )

    parser.add_argument(
        "--remote",
        action="store_true",
        help="Use remote OpenRouter API instead of local LM Studio. Requires OPENROUTER_API_KEY environment variable",
    )

    # Skip flags for different phases
    parser.add_argument("--skip-renaming", action="store_true", help="Skip the file renaming phase")
    parser.add_argument("--skip-translating", action="store_true", help="Skip the translation phase")
    parser.add_argument("--skip-epub", action="store_true", help="Skip the EPUB generation phase")

    # Translated file path for direct EPUB generation
    parser.add_argument(
        "--translated",
        type=str,
        help="Path to already translated text file for direct EPUB generation. Automatically implies --skip-renaming and --skip-translating. Makes filepath argument optional",
    )

    # API key for renaming (if not skipped)
    parser.add_argument(
        "--openai-api-key",
        type=str,
        help="OpenRouter API key for novel renaming (can also use OPENROUTER_API_KEY env var)",
    )

    # Add configuration override arguments
    parser.add_argument(
        "--timeout",
        type=int,
        help="API request timeout in seconds (overrides config/preset)",
    )

    parser.add_argument(
        "--max-retries",
        type=int,
        help="Maximum retry attempts for failed requests (overrides config/preset)",
    )

    parser.add_argument("--model", type=str, help="AI model name (overrides config/preset)")

    parser.add_argument("--endpoint", type=str, help="API endpoint URL (overrides config/preset)")

    parser.add_argument(
        "--temperature",
        type=float,
        help="AI model temperature (overrides config/preset)",
    )

    parser.add_argument(
        "--max-tokens",
        type=int,
        help="Maximum tokens per request (overrides config/preset)",
    )

    parser.add_argument(
        "--double-pass",
        action="store_true",
        help="Enable double-pass translation (overrides config/preset)",
    )

    # Renaming phase options
    parser.add_argument(
        "--rename-model",
        type=str,
        help="AI model for renaming phase (overrides config/preset)",
    )

    parser.add_argument(
        "--rename-temperature",
        type=float,
        help="Temperature for renaming phase (overrides config/preset)",
    )

    parser.add_argument(
        "--kb-to-read",
        type=int,
        default=35,
        help="KB to read from file start for metadata extraction (default: 35)",
    )

    parser.add_argument(
        "--rename-workers",
        type=int,
        help="Number of parallel workers for batch renaming (default: CPU count)",
    )

    parser.add_argument(
        "--rename-dry-run",
        action="store_true",
        help="Preview what files would be renamed without actually renaming them",
    )

    # EPUB generation options
    parser.add_argument(
        "--epub-title",
        type=str,
        help="Override book title for EPUB",
    )

    parser.add_argument(
        "--epub-author",
        type=str,
        help="Override author name for EPUB",
    )

    parser.add_argument(
        "--cover",
        type=str,
        help="Path to cover image file (.jpg/.jpeg/.png)",
    )

    parser.add_argument(
        "--epub-language",
        type=str,
        default="en",
        help="Language code for the EPUB (default: en)",
    )

    parser.add_argument(
        "--no-toc",
        action="store_true",
        help="Disable table of contents generation",
    )

    parser.add_argument(
        "--no-validate",
        action="store_true",
        help="Skip chapter validation",
    )

    parser.add_argument(
        "--epub-strict",
        action="store_true",
        help="Enable strict mode (abort on validation issues)",
    )

    parser.add_argument(
        "--custom-css",
        type=str,
        help="Path to custom CSS file for EPUB styling",
    )

    parser.add_argument(
        "--epub-metadata",
        type=str,
        help='Additional metadata in JSON format: {"publisher": "...", "description": "...", "series": "...", "series_index": "..."}',
    )

    parser.add_argument(
        "--json-log",
        type=str,
        help="Enable JSON logging for chapter validation issues (path to log file)",
    )

    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Just scan and validate chapters without creating EPUB",
    )

    return parser


def validate_args(args: argparse.Namespace, parser: argparse.ArgumentParser) -> None:
    """Validate parsed arguments and apply additional logic.

    Args:
        args: Parsed command-line arguments
        parser: ArgumentParser instance for error reporting

    Raises:
        SystemExit: If validation fails
    """
    # If --translated is provided, automatically set skip flags
    if args.translated:
        args.skip_renaming = True
        args.skip_translating = True
        # Note: logging not available here, will be logged in main

        # Validate that the translated file exists
        translated_path = Path(args.translated)
        if not translated_path.exists():
            parser.error(f"Translated file not found: {args.translated}")
        if not translated_path.is_file():
            parser.error(f"Translated path is not a file: {args.translated}")

    # Check if filepath is required
    if not args.filepath:
        # filepath is optional when using --translated
        if not args.translated:
            parser.error("filepath is required unless using --translated option")
