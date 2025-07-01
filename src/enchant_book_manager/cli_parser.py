#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
# - Initial creation from enchant_cli.py refactoring
# - Extracted command-line parsing logic
# - Contains argument parser setup and validation
# - Refactored create_parser into smaller functions
# - Added _add_basic_args, _add_phase_args, _add_api_args, _add_rename_args, _add_epub_args
# - Reduced create_parser from 359 lines to ~40 lines
# - Moved help text to cli_help_text.py to reduce file size
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

from .cli_help_text import get_epilog_text


def _add_basic_args(parser: argparse.ArgumentParser, config: dict[str, Any]) -> None:
    """Add basic arguments to the parser.

    Args:
        parser: ArgumentParser instance to add arguments to
        config: Configuration dictionary for default values
    """
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


def _add_phase_args(parser: argparse.ArgumentParser) -> None:
    """Add phase control arguments to the parser.

    Args:
        parser: ArgumentParser instance to add arguments to
    """
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


def _add_api_args(parser: argparse.ArgumentParser) -> None:
    """Add API-related arguments to the parser.

    Args:
        parser: ArgumentParser instance to add arguments to
    """
    # API key for renaming (if not skipped)
    parser.add_argument(
        "--openai-api-key",
        type=str,
        help="OpenRouter API key for novel renaming (can also use OPENROUTER_API_KEY env var)",
    )

    # Configuration override arguments
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


def _add_rename_args(parser: argparse.ArgumentParser) -> None:
    """Add renaming phase arguments to the parser.

    Args:
        parser: ArgumentParser instance to add arguments to
    """
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


def _add_epub_args(parser: argparse.ArgumentParser) -> None:
    """Add EPUB generation arguments to the parser.

    Args:
        parser: ArgumentParser instance to add arguments to
    """
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
        epilog=get_epilog_text(),
    )

    # Add arguments in logical groups
    _add_basic_args(parser, config)
    _add_phase_args(parser)
    _add_api_args(parser)
    _add_rename_args(parser)
    _add_epub_args(parser)

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
