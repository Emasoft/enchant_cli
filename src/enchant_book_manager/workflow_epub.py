#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
# - Initial creation from workflow_orchestrator.py refactoring
# - Extracted EPUB-specific processing functions
# - Contains functions for finding translated files and creating EPUBs
#

"""
workflow_epub.py - EPUB generation utilities for workflow orchestration
======================================================================

Handles EPUB-specific operations including:
- Finding translated files
- Creating EPUBs from translated text
- Applying configuration overrides
- Validation-only mode
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Any

from .common_utils import extract_book_info_from_path, sanitize_filename
from .config_manager import get_config
from .epub_utils import create_epub_with_config, get_epub_config_from_book_info


def find_translated_file(current_path: Path, args: argparse.Namespace, logger: logging.Logger) -> Path | None:
    """
    Find the translated file for EPUB generation.

    Args:
        current_path: Current file path
        args: Command-line arguments
        logger: Logger instance

    Returns:
        Path to translated file or None
    """
    # Check if --translated option was provided
    if hasattr(args, "translated") and args.translated:
        # Use the provided translated file directly
        translated_file = Path(args.translated)
        logger.info(f"Using provided translated file: {translated_file}")
        return translated_file

    # Original logic: look for translated file in expected directory
    # Extract book info from filename
    book_info = extract_book_info_from_path(current_path)

    # Find the output directory for this book
    book_title = book_info.get("title_english", current_path.stem)
    book_author = book_info.get("author_english", "Unknown")

    # Look for translated chunks directory
    safe_folder_name = sanitize_filename(f"{book_title} by {book_author}")
    book_dir = current_path.parent / safe_folder_name

    if book_dir.exists() and book_dir.is_dir():
        # Look for the complete translated text file
        translated_file_pattern = f"translated_{book_title} by {book_author}.txt"
        translated_file = book_dir / translated_file_pattern
        return translated_file

    return None


def create_epub_from_translated(translated_file: Path, current_path: Path, book_title: str, book_author: str, book_info: dict[str, Any], args: argparse.Namespace, progress: dict[str, Any], logger: logging.Logger) -> bool:
    """
    Create EPUB from translated file.

    Args:
        translated_file: Path to translated text file
        current_path: Current file path
        book_title: Book title
        book_author: Book author
        book_info: Book metadata
        args: Command-line arguments
        progress: Progress tracking dictionary
        logger: Logger instance

    Returns:
        True if EPUB created successfully
    """
    # Create EPUB output path
    epub_name = sanitize_filename(book_title) + ".epub"
    epub_path = current_path.parent / epub_name

    # Get EPUB settings from configuration
    config = get_config()
    epub_settings = config.get("epub", {})

    # Build book info for configuration
    book_info_for_config = {
        "title_english": book_title,
        "author_english": book_author,
        "title_chinese": book_info.get("title_chinese", ""),
        "author_chinese": book_info.get("author_chinese", ""),
    }

    # Create EPUB configuration from book info and settings
    epub_config = get_epub_config_from_book_info(book_info=book_info_for_config, epub_settings=epub_settings)

    # Apply command-line overrides
    apply_epub_overrides(epub_config, args, logger)

    # Handle validate-only mode
    if hasattr(args, "validate_only") and args.validate_only:
        return validate_epub_only(translated_file, epub_path, book_title, book_author, epub_config, progress, logger)

    # Create EPUB using the common utility
    success, issues = create_epub_with_config(
        txt_file_path=translated_file,
        output_path=epub_path,
        config=epub_config,
        logger=logger,
    )

    if success:
        progress["phases"]["epub"]["result"] = str(epub_path)
        logger.info(f"EPUB created successfully: {epub_path}")

        if issues:
            logger.warning(f"EPUB created with {len(issues)} validation warnings")
            for issue in issues[:5]:
                logger.warning(f"  - {issue}")
    else:
        progress["phases"]["epub"]["error"] = f"EPUB creation failed: {'; '.join(issues[:3])}"
        logger.error(f"EPUB creation failed with {len(issues)} errors")

    return success


def apply_epub_overrides(epub_config: dict[str, Any], args: argparse.Namespace, logger: logging.Logger) -> None:
    """
    Apply command-line overrides to EPUB configuration.

    Args:
        epub_config: EPUB configuration dictionary (modified in-place)
        args: Command-line arguments
        logger: Logger instance
    """
    # Override EPUB config with command line options
    if hasattr(args, "epub_language") and args.epub_language:
        epub_config["language"] = args.epub_language
    if hasattr(args, "no_toc") and args.no_toc:
        epub_config["generate_toc"] = False
    if hasattr(args, "no_validate") and args.no_validate:
        epub_config["validate_chapters"] = False
    if hasattr(args, "epub_strict") and args.epub_strict:
        epub_config["strict_mode"] = True

    # Handle cover image
    if hasattr(args, "cover") and args.cover:
        cover_path = Path(args.cover)
        if cover_path.exists():
            epub_config["cover_path"] = cover_path
        else:
            logger.warning(f"Cover image not found: {args.cover}")

    # Handle custom CSS
    if hasattr(args, "custom_css") and args.custom_css:
        css_path = Path(args.custom_css)
        if css_path.exists():
            epub_config["custom_css"] = css_path.read_text(encoding="utf-8")
        else:
            logger.warning(f"Custom CSS file not found: {args.custom_css}")

    # Handle metadata
    if hasattr(args, "epub_metadata") and args.epub_metadata:
        try:
            metadata = json.loads(args.epub_metadata)
            epub_config["metadata"] = metadata
        except json.JSONDecodeError as e:
            logger.warning(f"Invalid JSON in epub-metadata: {e}")


def validate_epub_only(translated_file: Path, epub_path: Path, book_title: str, book_author: str, epub_config: dict[str, Any], progress: dict[str, Any], logger: logging.Logger) -> bool:
    """
    Validate EPUB without creating it.

    Args:
        translated_file: Path to translated text file
        epub_path: Path where EPUB would be created
        book_title: Book title
        book_author: Book author
        epub_config: EPUB configuration
        progress: Progress tracking dictionary
        logger: Logger instance

    Returns:
        True if validation passed
    """
    # Just validate, don't create EPUB
    from .make_epub import create_epub_from_txt_file

    success, issues = create_epub_from_txt_file(
        translated_file,
        output_path=epub_path,
        title=book_title,
        author=book_author,
        cover_path=epub_config.get("cover_path"),
        generate_toc=epub_config.get("generate_toc", True),
        validate=True,
        strict_mode=epub_config.get("strict_mode", False),
        language=epub_config.get("language", "en"),
        custom_css=epub_config.get("custom_css"),
        metadata=epub_config.get("metadata"),
    )

    if issues:
        logger.info(f"Validation found {len(issues)} issues")
        for issue in issues:
            logger.warning(f"  - {issue}")
    else:
        logger.info("Validation passed with no issues")

    progress["phases"]["epub"]["status"] = "skipped"
    progress["phases"]["epub"]["result"] = "validate-only"

    return success


def process_epub_generation(current_path: Path, args: argparse.Namespace, progress: dict[str, Any], logger: logging.Logger) -> bool:
    """
    Process EPUB generation with all necessary steps.

    This is the main entry point called from workflow_phases.py.

    Args:
        current_path: Current file path
        args: Command-line arguments
        progress: Progress tracking dictionary
        logger: Logger instance

    Returns:
        True if EPUB generation succeeded
    """
    # Find translated file
    translated_file = find_translated_file(current_path, args, logger)

    if not translated_file or not translated_file.exists():
        # Translated file not found
        if hasattr(args, "translated") and args.translated:
            progress["phases"]["epub"]["error"] = "Provided translated file not found"
            logger.error(f"Provided translated file not found: {args.translated}")
        else:
            progress["phases"]["epub"]["error"] = "No translation directory or file found"
            logger.warning("No translation output directory found or translated file missing")
        return False

    # Extract book info
    book_info = extract_book_info_from_path(translated_file if hasattr(args, "translated") and args.translated else current_path)
    book_title = book_info.get("title_english", current_path.stem)
    book_author = book_info.get("author_english", "Unknown")

    # Override with command line options
    if hasattr(args, "epub_title") and args.epub_title:
        book_title = args.epub_title
    if hasattr(args, "epub_author") and args.epub_author:
        book_author = args.epub_author

    # Create EPUB
    return create_epub_from_translated(translated_file, current_path, book_title, book_author, book_info, args, progress, logger)
