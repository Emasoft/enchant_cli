#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
# - Initial creation from workflow_orchestrator.py refactoring
# - Extracted phase processing functions
# - Contains the three phase processing functions (rename, translate, epub)
#

"""
workflow_phases.py - Individual phase processors for workflow orchestration
==========================================================================

Contains the processing logic for each of the three phases:
1. Renaming (metadata extraction)
2. Translation (Chinese to English)
3. EPUB generation
"""

from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path
from typing import Any

from .workflow_progress import save_progress

# Import modules for the three phases
try:
    from .rename_api_client import RenameAPIClient
    from .rename_file_processor import process_novel_file as rename_novel

    renaming_available = True
except ImportError:
    renaming_available = False

try:
    from .cli_translator import translate_novel

    translation_available = True
except ImportError:
    translation_available = False

try:
    from .epub_utils import create_epub_with_config  # noqa: F401

    epub_available = True
except ImportError:
    epub_available = False


def process_renaming_phase(
    file_path: Path,
    current_path: Path,
    args: argparse.Namespace,
    progress: dict[str, Any],
    progress_file: Path,
    logger: logging.Logger,
) -> Path:
    """
    Process the renaming phase of workflow.

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

                    # Create API client
                    api_client = RenameAPIClient(
                        api_key=api_key,
                        model=rename_model,
                        temperature=rename_temperature,
                    )

                    # Process the file
                    success, new_path, metadata = rename_novel(
                        file_path,
                        api_client=api_client,
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
        save_progress(progress_file, progress, logger)

    return current_path


def process_translation_phase(
    current_path: Path,
    args: argparse.Namespace,
    progress: dict[str, Any],
    progress_file: Path,
    logger: logging.Logger,
) -> None:
    """
    Process the translation phase of workflow.

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
        save_progress(progress_file, progress, logger)


def process_epub_phase(
    current_path: Path,
    args: argparse.Namespace,
    progress: dict[str, Any],
    progress_file: Path,
    logger: logging.Logger,
) -> None:
    """
    Process the EPUB generation phase of workflow.

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
                # Import epub handler to avoid circular import
                from .workflow_epub import process_epub_generation

                # Delegate to epub handler
                success = process_epub_generation(current_path, args, progress, logger)

                if success:
                    progress["phases"]["epub"]["status"] = "completed"
                else:
                    progress["phases"]["epub"]["status"] = "failed"

            except Exception as e:
                logger.error(f"Error during EPUB generation: {e}")
                progress["phases"]["epub"]["status"] = "failed"
                progress["phases"]["epub"]["error"] = str(e)

        # Save progress
        save_progress(progress_file, progress, logger)
