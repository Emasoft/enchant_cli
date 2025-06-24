#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
# - Initial creation from enchant_cli.py refactoring
# - Extracted batch processing logic for orchestration
# - Handles progress tracking and file locking for batch operations
# - Works with workflow_orchestrator for unified processing
#

"""
cli_batch_handler.py - Batch novel processing for CLI orchestration
==================================================================

Handles batch processing of multiple novel files with progress tracking,
resume capability, and file locking to prevent concurrent access.
This module works with the workflow orchestrator for unified processing.
"""

from __future__ import annotations

import argparse
import datetime as dt
import logging
import sys
from pathlib import Path
from typing import Any

import filelock
import yaml

from .common_yaml_utils import load_safe_yaml
from .workflow_orchestrator import process_novel_unified


def process_batch(args: argparse.Namespace, logger: logging.Logger) -> None:
    """Process batch of novel files using unified orchestration.

    Args:
        args: Command-line arguments
        logger: Logger instance
    """
    input_path = Path(args.filepath)
    if not input_path.exists() or not input_path.is_dir():
        logger.error("Batch processing requires an existing directory path.")
        sys.exit(1)

    # Add file locking to prevent concurrent access
    lock_path = Path("translation_batch.lock")
    with filelock.FileLock(str(lock_path)):
        # Load or create batch progress
        progress_file = Path("translation_batch_progress.yml")
        history_file = Path("translations_chronology.yml")

        if progress_file.exists():
            progress = load_safe_yaml(progress_file) or {}
        else:
            progress = {
                "created": dt.datetime.now().isoformat(),
                "input_folder": str(input_path.resolve()),
                "files": [],
            }

        # Populate file list if not resuming
        if not progress.get("files"):
            files_sorted = sorted(input_path.glob("*.txt"), key=lambda x: x.name)
            for file in files_sorted:
                progress["files"].append(
                    {
                        "path": str(file.resolve()),
                        "status": "planned",
                        "end_time": None,
                        "retry_count": 0,
                    }
                )

        max_retries = 3

        # Process files
        for item in progress["files"]:
            if item["status"] == "completed":
                continue
            if item.get("retry_count", 0) >= max_retries:
                logger.warning(f"Skipping {item['path']} after {max_retries} failed attempts.")
                item["status"] = "failed/skipped"
                continue

            item["status"] = "processing"
            item["start_time"] = dt.datetime.now().isoformat()
            _save_batch_progress(progress_file, progress, logger)

            try:
                logger.info(f"Processing: {Path(item['path']).name}")

                # Use unified processor
                success = process_novel_unified(Path(item["path"]), args, logger)

                if success:
                    item["status"] = "completed"
                else:
                    raise Exception("One or more phases failed")

            except Exception as e:
                logger.error(f"Failed to process {item['path']}: {str(e)}")
                item["status"] = "failed/skipped"
                item["error"] = str(e)
                item["retry_count"] = item.get("retry_count", 0) + 1
            finally:
                item["end_time"] = dt.datetime.now().isoformat()
                _save_batch_progress(progress_file, progress, logger)

                # Move completed batch to history
                if all(file["status"] in ("completed", "failed/skipped") for file in progress["files"]):
                    _archive_batch_history(history_file, progress, logger)
                    _cleanup_progress_file(progress_file, logger)


def _save_batch_progress(progress_file: Path, progress: dict[str, Any], logger: logging.Logger) -> None:
    """Save batch progress to file.

    Args:
        progress_file: Path to progress file
        progress: Progress data
        logger: Logger instance

    Raises:
        Exception: If save fails (critical for batch processing)
    """
    try:
        with progress_file.open("w") as f:
            yaml.safe_dump(progress, f)
    except (OSError, yaml.YAMLError) as e:
        logger.error(f"Error saving batch progress: {e}")
        # Re-raise as this is critical for batch processing
        raise


def _archive_batch_history(history_file: Path, progress: dict[str, Any], logger: logging.Logger) -> None:
    """Archive completed batch to history file.

    Args:
        history_file: Path to history file
        progress: Completed batch progress
        logger: Logger instance
    """
    try:
        with history_file.open("a", encoding="utf-8") as f:
            f.write("---\n")
            yaml.safe_dump(progress, f, allow_unicode=True)
    except (OSError, yaml.YAMLError) as e:
        logger.error(f"Error writing to history file: {e}")
        # Continue anyway - history is not critical


def _cleanup_progress_file(progress_file: Path, logger: logging.Logger) -> None:
    """Remove progress file after batch completion.

    Args:
        progress_file: Path to progress file
        logger: Logger instance
    """
    try:
        progress_file.unlink()
    except (FileNotFoundError, PermissionError) as e:
        logger.error(f"Error deleting progress file: {e}")
        # Continue anyway - file will be overwritten next time
