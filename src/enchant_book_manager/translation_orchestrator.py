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
# - Extracted translation orchestration from cli_translator.py
# - Added chunk translation with retry logic
# - Moved cost logging to separate cost_logger module
# - Added error formatting utilities
#

"""Translation orchestration for the EnChANT Book Manager."""

from __future__ import annotations

import errno
import logging
import re
import sys
import time
from pathlib import Path
from typing import Any, Optional

from .models import Book, VARIATION_DB
from .common_utils import sanitize_filename as common_sanitize_filename
from .text_processor import remove_excess_empty_lines
from .icloud_sync import prepare_for_write
from .translation_service import ChineseAITranslator
from .cost_logger import save_translation_cost_log

# Chunk retry constants
DEFAULT_MAX_CHUNK_RETRIES = 10
MAX_RETRY_WAIT_SECONDS = 60


def format_chunk_error_message(
    chunk_number: int,
    max_retries: int,
    last_error: str,
    book_title: str,
    book_author: str,
    output_path: str,
) -> str:
    """
    Format a comprehensive error message for chunk translation failures.

    Args:
        chunk_number: The chunk number that failed
        max_retries: Number of retry attempts made
        last_error: The last error message
        book_title: Title of the book being translated
        book_author: Author of the book
        output_path: Path where the chunk would have been saved

    Returns:
        Formatted error message with troubleshooting information
    """
    return (
        f"\n\nFATAL ERROR: Failed to translate chunk {chunk_number:06d} after {max_retries} attempts.\n"
        f"Last error: {last_error}\n"
        f"Book: {book_title} by {book_author}\n"
        f"Chunk file would have been: {output_path}\n\n"
        f"Possible causes:\n"
        f"- Translation API is unreachable or returning errors\n"
        f"- Network connectivity issues\n"
        f"- Insufficient disk space to save translated chunks\n"
        f"- File permissions preventing file write\n"
        f"- API quota exceeded or authentication issues\n\n"
        f"Please check the logs above for more details and resolve the issue before retrying.\n"
        f"To resume translation from this point, use the --resume flag.\n"
    )


def save_translated_book(
    book_id: str,
    translator: ChineseAITranslator,
    resume: bool = False,
    create_epub: bool = False,
    logger: Optional[logging.Logger] = None,
    module_config: Optional[dict[str, Any]] = None,
) -> None:
    """
    Simulate translation of the book and save the translated text to a file.
    For each chunk, use the translator to translate the original text.

    Note: The create_epub parameter is kept for backward compatibility but is ignored.
    EPUB generation is handled by enchant_cli.py orchestrator.

    Args:
        book_id: ID of the book to translate
        translator: Configured translator instance
        resume: Whether to resume interrupted translation
        create_epub: (Deprecated) Kept for backward compatibility
        logger: Logger instance for output
        module_config: Module configuration dictionary
    """
    # Ensure logger is available
    if logger is None:
        logger = logging.getLogger(__name__)

    # Get max chunk retry attempts from config or use default
    max_chunk_retries = DEFAULT_MAX_CHUNK_RETRIES
    if module_config:
        max_chunk_retries = module_config.get("translation", {}).get("max_chunk_retries", DEFAULT_MAX_CHUNK_RETRIES)

    book = Book.get_by_id(book_id)
    if not book:
        raise ValueError("Book not found")

    # Create book folder
    try:
        folder_name = common_sanitize_filename(f"{book.translated_title} by {book.translated_author}", max_length=100)
        book_dir = Path(folder_name)
        book_dir.mkdir(exist_ok=True)
    except OSError as e:
        if e.errno != errno.EEXIST:
            logger.error(f"Error creating directory: {e}")
            book_dir = Path.cwd()

    # Prepare autoresume data
    existing_chunk_nums: set[int] = set()
    if resume:
        # Use sanitized names for pattern matching
        sanitized_title = common_sanitize_filename(book.translated_title, max_length=50)
        sanitized_author = common_sanitize_filename(book.translated_author, max_length=50)
        pattern = f"{sanitized_title} by {sanitized_author} - Chunk_*.txt"
        for p in sorted(book_dir.glob(pattern), key=lambda x: x.name):
            match = re.search(r"Chunk_(\d{6})\.txt$", p.name)
            if match:
                existing_chunk_nums.add(int(match.group(1)))
        if existing_chunk_nums:
            logger.info(f"Autoresume active: existing translated chunks detected: {sorted(existing_chunk_nums)}")
        else:
            logger.info("Autoresume active but no existing chunk files found.")

    translated_contents = []
    # Sort chunks by chunk_number
    sorted_chunks = sorted(book.chunks, key=lambda ch: ch.chunk_number)
    for chunk in sorted_chunks:
        # Retrieve the Variation corresponding to the original text
        variation = VARIATION_DB.get(chunk.original_variation_id)
        if variation:
            if resume and chunk.chunk_number in existing_chunk_nums:
                # Use same sanitized names as used in chunk filename creation
                sanitized_title = common_sanitize_filename(book.translated_title, max_length=50)
                sanitized_author = common_sanitize_filename(book.translated_author, max_length=50)
                p_existing = book_dir / f"{sanitized_title} by {sanitized_author} - Chunk_{chunk.chunk_number:06d}.txt"
                try:
                    translated_text = p_existing.read_text(encoding="utf-8")
                    logger.info(f"Skipping translation for chunk {chunk.chunk_number}; using existing translation.")
                except FileNotFoundError:
                    logger.warning(f"Expected file {p_existing.name} not found; re-translating.")
                else:
                    translated_contents.append(f"\n{translated_text}\n")
                    continue
            original_text = variation.text_content

            # Use the max_chunk_retries loaded above
            chunk_translated = False
            last_error = None
            # Sanitize the filename parts to avoid OS filename length errors
            sanitized_title = common_sanitize_filename(book.translated_title, max_length=50)
            sanitized_author = common_sanitize_filename(book.translated_author, max_length=50)
            output_filename_chunk = book_dir / f"{sanitized_title} by {sanitized_author} - Chunk_{chunk.chunk_number:06d}.txt"

            for chunk_attempt in range(1, max_chunk_retries + 1):
                try:
                    logger.info(f"TRANSLATING CHUNK {chunk.chunk_number:06d} of {len(sorted_chunks)} (Attempt {chunk_attempt}/{max_chunk_retries})")
                    is_last_chunk = chunk.chunk_number == len(sorted_chunks)

                    # Check if translator is initialized
                    if translator is None:
                        raise RuntimeError("Translator not initialized. This function should be called after translator setup.")

                    translated_result = translator.translate(original_text, is_last_chunk)
                    if translated_result is None:
                        raise ValueError("Translation returned None")
                    translated_text = translated_result

                    # Validate translated text
                    if not translated_text or len(translated_text.strip()) == 0:
                        raise ValueError("Translation returned empty or whitespace-only text")

                    # Save chunk to file
                    p = output_filename_chunk
                    try:
                        p.write_text(translated_text)
                    except (OSError, PermissionError) as e:
                        logger.error(f"Error saving chunk {chunk.chunk_number:06d} to {p}: {e}")
                        raise

                    # Success! Mark as translated and break out of retry loop
                    chunk_translated = True
                    logger.info(f"Successfully translated chunk {chunk.chunk_number:06d} on attempt {chunk_attempt}")
                    break

                except Exception as e:
                    last_error = e
                    logger.error(f"ERROR: Translation failed for chunk {chunk.chunk_number:06d} on attempt {chunk_attempt}/{max_chunk_retries}: {str(e)}")

                    if chunk_attempt < max_chunk_retries:
                        # Calculate wait time with exponential backoff
                        wait_time = min(2**chunk_attempt, MAX_RETRY_WAIT_SECONDS)
                        logger.info(f"Waiting {wait_time} seconds before retry...")
                        time.sleep(wait_time)

            # Check if translation succeeded after all attempts
            if not chunk_translated:
                # All attempts failed - exit with error
                error_message = format_chunk_error_message(
                    chunk_number=chunk.chunk_number,
                    max_retries=max_chunk_retries,
                    last_error=str(last_error),
                    book_title=book.translated_title,
                    book_author=book.translated_author,
                    output_path=str(output_filename_chunk),
                )
                logger.error(error_message)
                print(error_message)
                sys.exit(1)
            else:
                # Translation succeeded - log and append to contents
                logger.info(f"\nChunk {chunk.chunk_number:06d}:\n{translated_text}\n\n")
                translated_contents.append(f"\n{translated_text}\n")

    # Combine all translated chunks into one full text
    full_translated_text = "\n".join(translated_contents)
    full_translated_text = remove_excess_empty_lines(full_translated_text)

    # Save to a file named with the book_id
    # Sanitize the filename to avoid OS filename length errors
    sanitized_title = common_sanitize_filename(book.translated_title, max_length=50)
    sanitized_author = common_sanitize_filename(book.translated_author, max_length=50)
    output_filename = book_dir / f"translated_{sanitized_title} by {sanitized_author}.txt"
    # Prepare path for writing (ensures parent directory is synced)
    output_filename = prepare_for_write(output_filename)
    try:
        with open(output_filename, "w", encoding="utf-8") as f:
            f.write(full_translated_text)
        logger.info(f"Translated book saved to {output_filename}")
    except (OSError, PermissionError) as e:
        logger.error(f"Error saving translated book to {output_filename}: {e}")
        raise

    # Save cost log for remote translations
    save_translation_cost_log(book, translator, book_dir, len(sorted_chunks), logger)
