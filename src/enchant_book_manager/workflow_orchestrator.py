#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
# - Refactored from 24KB into 3 smaller modules (workflow_progress, workflow_phases, workflow_epub)
# - This file now serves as the main orchestrator importing from the new modules
# - All original functionality is preserved
#

"""
workflow_orchestrator.py - Novel processing workflow orchestration
=================================================================

Manages the unified 3-phase processing workflow for novels:
1. Renaming (metadata extraction)
2. Translation (Chinese to English)
3. EPUB generation

This module now serves as the main orchestrator that delegates to:
- workflow_progress.py: Progress tracking utilities
- workflow_phases.py: Individual phase processors
- workflow_epub.py: EPUB-specific operations
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from .workflow_progress import (
    load_safe_yaml_wrapper,
    create_initial_progress,
    get_progress_file_path,
)
from .workflow_phases import (
    process_renaming_phase,
    process_translation_phase,
    process_epub_phase,
)


def process_novel_unified(file_path: Path, args: argparse.Namespace, logger: logging.Logger) -> bool:
    """
    Unified processing function for a single novel file with all three phases.

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
    progress_file = get_progress_file_path(file_path)

    # Load existing progress if resuming
    if args.resume and progress_file.exists():
        progress = load_safe_yaml_wrapper(progress_file, logger) or create_initial_progress(file_path)
    else:
        progress = create_initial_progress(file_path)

    # Update current path from progress if available
    if progress["phases"]["renaming"]["status"] == "completed" and progress["phases"]["renaming"]["result"]:
        current_path = Path(progress["phases"]["renaming"]["result"])
        if current_path.exists():
            logger.info(f"Resuming with renamed file: {current_path.name}")
        else:
            current_path = file_path

    # Phase 1: Renaming
    current_path = process_renaming_phase(file_path, current_path, args, progress, progress_file, logger)

    # Phase 2: Translation
    process_translation_phase(current_path, args, progress, progress_file, logger)

    # Phase 3: EPUB Generation
    process_epub_phase(current_path, args, progress, progress_file, logger)

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
