#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
# - Initial creation from enchant_cli.py refactoring
# - Extracted unified novel processing logic
# - Contains the main orchestration flow for 3-phase processing
# - Handles progress tracking and phase coordination
#

"""
workflow_orchestrator.py - Novel processing workflow orchestration
=================================================================

Manages the unified 3-phase processing workflow for novels:
1. Renaming (metadata extraction)
2. Translation (Chinese to English)
3. EPUB generation

Handles progress tracking, phase coordination, and error recovery.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
from pathlib import Path
from typing import Any, Optional

import yaml

from .common_utils import extract_book_info_from_path, sanitize_filename
from .common_yaml_utils import load_safe_yaml
from .config_manager import get_config

# Import modules for the three phases
try:
    from .renamenovels import process_novel_file as rename_novel

    renaming_available = True
except ImportError:
    renaming_available = False

try:
    from .cli_translator import translate_novel

    translation_available = True
except ImportError:
    translation_available = False

try:
    from .epub_utils import create_epub_with_config, get_epub_config_from_book_info

    epub_available = True
except ImportError:
    epub_available = False


def load_safe_yaml_wrapper(path: Path, logger: logging.Logger) -> dict[str, Any] | None:
    """Safely load YAML file - wrapper for common utility with exception handling.

    Args:
        path: Path to YAML file
        logger: Logger instance

    Returns:
        Loaded YAML data or None on error
    """
    try:
        return load_safe_yaml(path)
    except ValueError as e:
        logger.error(f"Error loading YAML from {path}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error loading YAML from {path}: {e}")
        return None


def process_novel_unified(file_path: Path, args: argparse.Namespace, logger: logging.Logger) -> bool:
    """
    Unified processing function for a single novel file with all three phases:
    1. Renaming (unless --skip-renaming)
    2. Translation (unless --skip-translating)
    3. EPUB generation (unless --skip-epub)

    Args:
        file_path: Path to the novel file
        args: Command-line arguments
        logger: Logger instance

    Returns:
        True if all enabled phases completed successfully
    """
    current_path = file_path

    # Create a progress file for this specific novel to track phases
    progress_file = file_path.parent / f".{file_path.stem}_progress.yml"

    # Load existing progress if resuming
    if args.resume and progress_file.exists():
        progress = load_safe_yaml_wrapper(progress_file, logger) or {}
    else:
        progress = {
            "original_file": str(file_path),
            "phases": {
                "renaming": {"status": "pending", "result": None},
                "translation": {"status": "pending", "result": None},
                "epub": {"status": "pending", "result": None},
            },
        }

    # Update current path from progress if available
    if progress["phases"]["renaming"]["status"] == "completed" and progress["phases"]["renaming"]["result"]:
        current_path = Path(progress["phases"]["renaming"]["result"])
        if current_path.exists():
            logger.info(f"Resuming with renamed file: {current_path.name}")
        else:
            current_path = file_path

    # Phase 1: Renaming
    current_path = _process_renaming_phase(file_path, current_path, args, progress, progress_file, logger)

    # Phase 2: Translation
    _process_translation_phase(current_path, args, progress, progress_file, logger)

    # Phase 3: EPUB Generation
    _process_epub_phase(current_path, args, progress, progress_file, logger)

    # Clean up progress file if all phases completed successfully
    all_completed = all(phase["status"] in ("completed", "skipped") for phase in progress["phases"].values())
    if all_completed and progress_file.exists():
        try:
            progress_file.unlink()
            logger.info("All phases completed, removed progress file")
        except (FileNotFoundError, PermissionError) as e:
            logger.warning(f"Could not remove progress file: {e}")
            # Not critical - file will be overwritten next time

    return all_completed


def _process_renaming_phase(file_path: Path, current_path: Path, args: argparse.Namespace, progress: dict[str, Any], progress_file: Path, logger: logging.Logger) -> Path:
    """Process the renaming phase of workflow.

    Args:
        file_path: Original file path
        current_path: Current file path (may be renamed)
        args: Command-line arguments
        progress: Progress tracking dictionary
        progress_file: Path to progress file
        logger: Logger instance

    Returns:
        Updated current path after renaming
    """
    if getattr(args, "skip_renaming", False):
        # Mark as skipped if not already completed
        if progress["phases"]["renaming"]["status"] != "completed":
            progress["phases"]["renaming"]["status"] = "skipped"
            logger.info("Phase 1: Skipping renaming phase")
    elif not getattr(args, "skip_renaming", False) and progress["phases"]["renaming"]["status"] != "completed":
        logger.info(f"Phase 1: Renaming file {file_path.name}")

        if not renaming_available:
            logger.error("Renaming phase requested but renamenovels module not available")
            progress["phases"]["renaming"]["status"] = "failed"
            progress["phases"]["renaming"]["error"] = "Module not available"
        else:
            # Get API key for renaming
            api_key = getattr(args, "openai_api_key", None) or os.getenv("OPENROUTER_API_KEY")
            if not api_key:
                logger.error("OpenRouter API key required for renaming. Use --openai-api-key or set OPENROUTER_API_KEY env var")
                progress["phases"]["renaming"]["status"] = "failed"
                progress["phases"]["renaming"]["error"] = "No API key"
            else:
                try:
                    # Use command line options if provided, otherwise defaults
                    rename_model = getattr(args, "rename_model", None) or "gpt-4o-mini"
                    rename_temperature = float(getattr(args, "rename_temperature", 0.0)) if hasattr(args, "rename_temperature") and args.rename_temperature is not None else 0.0
                    rename_dry_run = getattr(args, "rename_dry_run", False)

                    success, new_path, metadata = rename_novel(
                        file_path,
                        api_key=api_key,
                        model=rename_model,
                        temperature=rename_temperature,
                        dry_run=rename_dry_run,
                    )

                    if success and new_path:
                        current_path = new_path
                        progress["phases"]["renaming"]["status"] = "completed"
                        progress["phases"]["renaming"]["result"] = str(new_path)
                        logger.info(f"File renamed to: {new_path.name}")
                    else:
                        logger.warning(f"Renaming failed for {file_path.name}, continuing with original name")
                        progress["phases"]["renaming"]["status"] = "failed"

                except Exception as e:
                    logger.error(f"Error during renaming: {e}")
                    progress["phases"]["renaming"]["status"] = "failed"
                    progress["phases"]["renaming"]["error"] = str(e)

        # Save progress
        _save_progress(progress_file, progress, logger)

    return current_path


def _process_translation_phase(current_path: Path, args: argparse.Namespace, progress: dict[str, Any], progress_file: Path, logger: logging.Logger) -> None:
    """Process the translation phase of workflow.

    Args:
        current_path: Current file path
        args: Command-line arguments
        progress: Progress tracking dictionary
        progress_file: Path to progress file
        logger: Logger instance
    """
    if getattr(args, "skip_translating", False):
        # Mark as skipped if not already completed
        if progress["phases"]["translation"]["status"] != "completed":
            progress["phases"]["translation"]["status"] = "skipped"
            logger.info("Phase 2: Skipping translation phase")
    elif not getattr(args, "skip_translating", False) and progress["phases"]["translation"]["status"] != "completed":
        logger.info(f"Phase 2: Translating {current_path.name}")

        if not translation_available:
            logger.error("Translation phase requested but cli_translator module not available")
            progress["phases"]["translation"]["status"] = "failed"
            progress["phases"]["translation"]["error"] = "Module not available"
        else:
            try:
                # Call translation module
                success = translate_novel(
                    str(current_path),
                    encoding=getattr(args, "encoding", "utf-8"),
                    max_chars=getattr(args, "max_chars", 12000),
                    resume=args.resume,
                    create_epub=False,  # EPUB handled in phase 3
                    remote=getattr(args, "remote", False),
                )

                if success:
                    progress["phases"]["translation"]["status"] = "completed"
                    progress["phases"]["translation"]["result"] = "success"
                    logger.info(f"Translation completed for {current_path.name}")
                else:
                    progress["phases"]["translation"]["status"] = "failed"
                    progress["phases"]["translation"]["error"] = "Translation failed"

            except Exception as e:
                logger.error(f"Error during translation: {e}")
                progress["phases"]["translation"]["status"] = "failed"
                progress["phases"]["translation"]["error"] = str(e)

        # Save progress
        _save_progress(progress_file, progress, logger)


def _process_epub_phase(current_path: Path, args: argparse.Namespace, progress: dict[str, Any], progress_file: Path, logger: logging.Logger) -> None:
    """Process the EPUB generation phase of workflow.

    Args:
        current_path: Current file path
        args: Command-line arguments
        progress: Progress tracking dictionary
        progress_file: Path to progress file
        logger: Logger instance
    """
    if getattr(args, "skip_epub", False):
        # Mark as skipped if not already completed
        if progress["phases"]["epub"]["status"] != "completed":
            progress["phases"]["epub"]["status"] = "skipped"
            logger.info("Phase 3: Skipping EPUB generation phase")
    elif not getattr(args, "skip_epub", False) and progress["phases"]["epub"]["status"] != "completed":
        logger.info(f"Phase 3: Generating EPUB for {current_path.name}")

        if not epub_available:
            logger.error("EPUB phase requested but make_epub module not available")
            progress["phases"]["epub"]["status"] = "failed"
            progress["phases"]["epub"]["error"] = "Module not available"
        else:
            try:
                # Find translated file
                translated_file = _find_translated_file(current_path, args, logger)

                if translated_file and translated_file.exists():
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
                    success = _create_epub_from_translated(translated_file, current_path, book_title, book_author, book_info, args, progress, logger)

                    if success:
                        progress["phases"]["epub"]["status"] = "completed"
                    else:
                        progress["phases"]["epub"]["status"] = "failed"
                else:
                    # Translated file not found
                    progress["phases"]["epub"]["status"] = "failed"
                    if hasattr(args, "translated") and args.translated:
                        progress["phases"]["epub"]["error"] = "Provided translated file not found"
                        logger.error(f"Provided translated file not found: {args.translated}")
                    else:
                        progress["phases"]["epub"]["error"] = "No translation directory or file found"
                        logger.warning("No translation output directory found or translated file missing")

            except Exception as e:
                logger.error(f"Error during EPUB generation: {e}")
                progress["phases"]["epub"]["status"] = "failed"
                progress["phases"]["epub"]["error"] = str(e)

        # Save progress
        _save_progress(progress_file, progress, logger)


def _find_translated_file(current_path: Path, args: argparse.Namespace, logger: logging.Logger) -> Optional[Path]:
    """Find the translated file for EPUB generation.

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


def _create_epub_from_translated(translated_file: Path, current_path: Path, book_title: str, book_author: str, book_info: dict[str, Any], args: argparse.Namespace, progress: dict[str, Any], logger: logging.Logger) -> bool:
    """Create EPUB from translated file.

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
    _apply_epub_overrides(epub_config, args, logger)

    # Handle validate-only mode
    if hasattr(args, "validate_only") and args.validate_only:
        return _validate_epub_only(translated_file, epub_path, book_title, book_author, epub_config, progress, logger)

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


def _apply_epub_overrides(epub_config: dict[str, Any], args: argparse.Namespace, logger: logging.Logger) -> None:
    """Apply command-line overrides to EPUB configuration.

    Args:
        epub_config: EPUB configuration dictionary
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


def _validate_epub_only(translated_file: Path, epub_path: Path, book_title: str, book_author: str, epub_config: dict[str, Any], progress: dict[str, Any], logger: logging.Logger) -> bool:
    """Validate EPUB without creating it.

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


def _save_progress(progress_file: Path, progress: dict[str, Any], logger: logging.Logger) -> None:
    """Save progress to YAML file.

    Args:
        progress_file: Path to progress file
        progress: Progress data to save
        logger: Logger instance
    """
    try:
        with progress_file.open("w") as f:
            yaml.safe_dump(progress, f)
    except (OSError, yaml.YAMLError) as e:
        logger.error(f"Error saving progress file: {e}")
        # Continue anyway - progress tracking is not critical
