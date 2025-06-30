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
# - Extracted cost logging functionality from translation_orchestrator.py
# - Handles saving translation cost summaries to log files
#

"""Cost logging utilities for the EnChANT Book Manager."""

from __future__ import annotations

import datetime as dt
import logging
from pathlib import Path
from typing import Optional

from .models import Book
from .icloud_sync import prepare_for_write
from .cost_tracker import global_cost_tracker
from .translation_service import ChineseAITranslator
from .common_utils import sanitize_filename as common_sanitize_filename


def save_translation_cost_log(
    book: Book,
    translator: ChineseAITranslator,
    output_dir: Path,
    total_chunks: int,
    logger: Optional[logging.Logger] = None,
) -> None:
    """
    Save cost log for remote translations.

    Args:
        book: Book object with metadata
        translator: Translator instance with cost tracking
        output_dir: Directory to save the cost log
        total_chunks: Total number of chunks translated
        logger: Optional logger for output
    """
    if logger is None:
        logger = logging.getLogger(__name__)

    if not (translator and translator.is_remote and translator.request_count > 0):
        return

    # Sanitize the filename to avoid OS filename length errors
    sanitized_title = common_sanitize_filename(book.translated_title, max_length=50)
    sanitized_author = common_sanitize_filename(book.translated_author, max_length=50)
    cost_log_filename = f"translated_{sanitized_title} by {sanitized_author}_AI_COSTS.log"
    cost_log_path = output_dir / cost_log_filename
    cost_log_path = prepare_for_write(cost_log_path)

    try:
        with open(cost_log_path, "w", encoding="utf-8") as f:
            f.write("AI Translation Cost Log\n")
            f.write("======================\n\n")
            f.write(f"Novel: {book.translated_title} by {book.translated_author}\n")
            f.write(f"Translation Date: {dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("API Service: OpenRouter (Remote)\n")
            f.write(f"Model: {translator.MODEL_NAME}\n")
            f.write(f"\n{translator.format_cost_summary()}\n")

            # Add per-request breakdown if needed
            f.write("\n\nDetailed Breakdown:\n")
            f.write("-------------------\n")
            f.write(f"Total Chunks Translated: {total_chunks}\n")
            summary = global_cost_tracker.get_summary()
            if summary["request_count"] > 0 and total_chunks > 0:
                f.write(f"Average Cost per chunk: ${summary['total_cost'] / total_chunks:.6f}\n")
                f.write(f"Average Tokens per chunk: {summary['total_tokens'] // total_chunks:,}\n")

            # Save raw data for potential future analysis
            f.write("\n\nRaw Data:\n")
            f.write("---------\n")
            f.write(f"total_cost: {summary['total_cost']}\n")
            f.write(f"total_tokens: {summary['total_tokens']}\n")
            f.write(f"total_prompt_tokens: {summary.get('total_prompt_tokens', 0)}\n")
            f.write(f"total_completion_tokens: {summary.get('total_completion_tokens', 0)}\n")
            f.write(f"request_count: {translator.request_count}\n")

    except (OSError, PermissionError) as e:
        logger.error(f"Error saving cost log to {cost_log_path}: {e}")
        raise
    logger.info(f"Cost log saved to {cost_log_path}")
