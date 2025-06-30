#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright (c) 2025 Emasoft
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# CHANGELOG:
# - Extracted batch processing functionality from cli_translator.py
# - Added progress tracking with YAML
# - Added batch cost summary generation
# - Added file locking for concurrent access prevention
#

"""Batch processing utilities for translating multiple novels."""

from __future__ import annotations

import datetime as dt
import logging
from pathlib import Path
from typing import Any, Optional

import filelock
import yaml

from .book_importer import import_book_from_txt
from .translation_orchestrator import save_translated_book
from .common_yaml_utils import load_safe_yaml as load_yaml_safe
from .icloud_sync import prepare_for_write
from .cost_tracker import global_cost_tracker
from .translation_service import ChineseAITranslator


def load_safe_yaml(path: Path, logger: Optional[logging.Logger] = None) -> dict[str, Any] | None:
    """
    Safely load YAML file - wrapper for common utility with exception handling.

    Args:
        path: Path to YAML file
        logger: Optional logger for error output

    Returns:
        Loaded YAML data or None on error
    """
    try:
        return load_yaml_safe(path)
    except ValueError as e:
        if logger is not None:
            logger.error(f"Error loading YAML from {path}: {e}")
        return None
    except Exception as e:
        if logger is not None:
            logger.error(f"Unexpected error loading YAML from {path}: {e}")
        return None


def process_batch(
    input_path: Path,
    translator: ChineseAITranslator,
    encoding: str = "utf-8",
    max_chars: int = 12000,
    resume: bool = False,
    create_epub: bool = False,
    logger: Optional[logging.Logger] = None,
) -> None:
    """
    Process batch of novel files.

    Args:
        input_path: Directory containing novels to translate
        translator: Configured translator instance
        encoding: File encoding
        max_chars: Maximum characters per chunk
        resume: Whether to resume interrupted translation
        create_epub: (Deprecated) Kept for backward compatibility
        logger: Logger instance for output
    """
    # Ensure logger is available
    if logger is None:
        logger = logging.getLogger(__name__)

    if not input_path.exists() or not input_path.is_dir():
        logger.error("Batch processing requires an existing directory path.")
        raise ValueError("Invalid batch directory")

    # Add file locking to prevent concurrent access
    lock_path = Path("translation_batch.lock")
    with filelock.FileLock(str(lock_path)):
        # Load or create batch progress
        progress_file = Path("translation_batch_progress.yml")
        history_file = Path("translations_chronology.yml")

        if progress_file.exists():
            progress = load_safe_yaml(progress_file, logger) or {}
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
            try:
                with progress_file.open("w") as f:
                    yaml.safe_dump(progress, f)
            except (OSError, yaml.YAMLError) as e:
                logger.error(f"Error saving progress file: {e}")
                raise

            try:
                logger.info(f"Processing: {Path(item['path']).name}")
                book_id = import_book_from_txt(item["path"], encoding=encoding, max_chars=max_chars, logger=logger)
                save_translated_book(
                    book_id,
                    translator,
                    resume=resume,
                    create_epub=create_epub,
                    logger=logger,
                )
                item["status"] = "completed"
            except Exception as e:
                logger.error(f"Failed to translate {item['path']}: {str(e)}")
                item["status"] = "failed/skipped"
                item["error"] = str(e)
                item["retry_count"] = item.get("retry_count", 0) + 1
            finally:
                item["end_time"] = dt.datetime.now().isoformat()
                try:
                    with progress_file.open("w") as f:
                        yaml.safe_dump(progress, f)
                except (OSError, yaml.YAMLError) as e:
                    logger.error(f"Error saving progress file in finally block: {e}")
                    # Don't re-raise in finally block to avoid masking original exception

                # Move completed batch to history
                if all(file["status"] in ("completed", "failed/skipped") for file in progress["files"]):
                    try:
                        with history_file.open("a", encoding="utf-8") as f:
                            f.write("---\n")
                            yaml.safe_dump(progress, f, allow_unicode=True)
                    except (OSError, yaml.YAMLError) as e:
                        logger.error(f"Error writing to history file: {e}")
                        # Continue anyway - don't fail the whole batch for history logging

                    try:
                        progress_file.unlink()
                    except (FileNotFoundError, PermissionError) as e:
                        logger.error(f"Error deleting progress file: {e}")
                        # Continue anyway - file will be overwritten next time

    # Save batch cost summary for remote translations
    if translator and translator.is_remote and translator.request_count > 0:
        batch_cost_log_path = input_path / "BATCH_AI_COSTS.log"
        batch_cost_log_path = prepare_for_write(batch_cost_log_path)

        completed_count = sum(1 for file in progress["files"] if file["status"] == "completed")
        failed_count = sum(1 for file in progress["files"] if file["status"] == "failed/skipped")

        try:
            with open(batch_cost_log_path, "w", encoding="utf-8") as f:
                f.write("Batch Translation Cost Summary\n")
                f.write("==============================\n\n")
                f.write(f"Batch Directory: {input_path}\n")
                f.write(f"Translation Date: {dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("API Service: OpenRouter (Remote)\n")
                f.write(f"Model: {translator.MODEL_NAME}\n")
                f.write("\nFiles Processed:\n")
                f.write("----------------\n")
                f.write(f"Total Files: {len(progress['files'])}\n")
                f.write(f"Completed: {completed_count}\n")
                f.write(f"Failed/Skipped: {failed_count}\n")
                f.write(f"\n{translator.format_cost_summary()}\n")

                # List individual files and their status
                f.write("\n\nFile Details:\n")
                f.write("-------------\n")
                for file in progress["files"]:
                    filename = Path(file["path"]).name
                    status = file["status"]
                    f.write(f"- {filename}: {status}\n")
                    if "error" in file:
                        f.write(f"  Error: {file['error']}\n")

                # Save raw data
                summary = global_cost_tracker.get_summary()
                f.write("\n\nRaw Cost Data:\n")
                f.write("-------------\n")
                f.write(f"total_cost: {summary['total_cost']}\n")
                f.write(f"total_tokens: {summary['total_tokens']}\n")
                f.write(f"total_prompt_tokens: {summary.get('total_prompt_tokens', 0)}\n")
                f.write(f"total_completion_tokens: {summary.get('total_completion_tokens', 0)}\n")
                f.write(f"request_count: {translator.request_count}\n")
                if completed_count > 0:
                    f.write(f"average_cost_per_novel: ${summary['total_cost'] / completed_count:.6f}\n")
                    f.write(f"average_tokens_per_novel: {summary['total_tokens'] // completed_count:,}\n")
        except (OSError, PermissionError) as e:
            logger.error(f"Error saving batch cost log to {batch_cost_log_path}: {e}")
            # Don't re-raise, just log the error
        else:
            logger.info(f"Batch cost summary saved to {batch_cost_log_path}")
