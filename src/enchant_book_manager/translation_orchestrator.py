#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# HERE IS THE CHANGELOG FOR THIS VERSION OF THE FILE:
# - Created translation orchestrator module
# - Extracted from cli_translator.py
# - Handles book translation workflow
# - Refactored save_translated_book into smaller functions
# - Added _prepare_book_directory, _get_existing_chunks, _translate_chunk, _save_final_book
# - Reduced save_translated_book from 173 lines to ~60 lines
#

"""
translation_orchestrator.py - Book translation orchestration
===========================================================

Orchestrates the translation of books, managing chunks and saving results.
"""

from __future__ import annotations

import errno
import logging
import re
import sys
import time
from pathlib import Path
from typing import Any, Optional

from .translation_service import ChineseAITranslator
from .common_text_utils import remove_excess_empty_lines
from .common_utils import sanitize_filename as common_sanitize_filename
from .icloud_sync import prepare_for_write
from .models import Book, VARIATION_DB
from .cost_logger import save_translation_cost_log

# Default values for chunk retry configuration
DEFAULT_MAX_CHUNK_RETRIES = 3
MAX_RETRY_WAIT_SECONDS = 60


def format_chunk_error_message(
    chunk_number: int,
    max_retries: int,
    last_error: str,
    book_title: str,
    book_author: str,
    output_path: str,
) -> str:
    """Format an error message for chunk translation failure.

    Args:
        chunk_number: The chunk number that failed
        max_retries: Maximum retry attempts that were made
        last_error: The last error message
        book_title: Title of the book
        book_author: Author of the book
        output_path: Path where chunk was supposed to be saved

    Returns:
        Formatted error message
    """
    return f"""
==========================================
CRITICAL ERROR: Translation Failed
==========================================
chunk {chunk_number:06d} could not be translated after {max_retries} attempts.

Book: {book_title} by {book_author}
Last Error: {last_error}
Output Path: {output_path}

Possible causes:
- Translation API is unreachable
- Network connectivity issues
- Invalid API credentials
- Content exceeds token limits

To resume translation, run the command again with --resume flag.
==========================================
"""


def _prepare_book_directory(book: Book, logger: logging.Logger) -> Path:
    """Prepare the directory for saving book translations.

    Args:
        book: Book instance with metadata
        logger: Logger for output

    Returns:
        Path to the book directory
    """
    try:
        folder_name = common_sanitize_filename(f"{book.translated_title} by {book.translated_author}", max_length=100)
        book_dir = Path(folder_name)
        book_dir.mkdir(exist_ok=True)
        return book_dir
    except OSError as e:
        if e.errno != errno.EEXIST:
            logger.error(f"Error creating directory: {e}")
        return Path.cwd()


def _get_existing_chunks(book_dir: Path, book: Book, logger: logging.Logger) -> set[int]:
    """Get the set of existing translated chunk numbers for resuming.

    Args:
        book_dir: Directory containing translated chunks
        book: Book instance with metadata
        logger: Logger for output

    Returns:
        Set of chunk numbers that already exist
    """
    existing_chunk_nums: set[int] = set()

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

    return existing_chunk_nums


def _translate_chunk(
    chunk_number: int,
    original_text: str,
    translator: ChineseAITranslator,
    is_last_chunk: bool,
    max_retries: int,
    logger: logging.Logger,
) -> Optional[str]:
    """Translate a single chunk with retry logic.

    Args:
        chunk_number: Number of the chunk being translated
        original_text: Original text to translate
        translator: Configured translator instance
        is_last_chunk: Whether this is the last chunk
        max_retries: Maximum retry attempts
        logger: Logger for output

    Returns:
        Translated text or None if all attempts failed
    """
    last_error = None

    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"TRANSLATING CHUNK {chunk_number:06d} (Attempt {attempt}/{max_retries})")

            # Check if translator is initialized
            if translator is None:
                raise RuntimeError("Translator not initialized. This function should be called after translator setup.")

            translated_result = translator.translate(original_text, is_last_chunk)
            if translated_result is None:
                raise ValueError("Translation returned None")

            # Validate translated text
            if not translated_result or len(translated_result.strip()) == 0:
                raise ValueError("Translation returned empty or whitespace-only text")

            logger.info(f"Successfully translated chunk {chunk_number:06d} on attempt {attempt}")
            return translated_result

        except Exception as e:
            last_error = e
            logger.error(f"ERROR: Translation failed for chunk {chunk_number:06d} on attempt {attempt}/{max_retries}: {str(e)}")

            if attempt < max_retries:
                # Calculate wait time with exponential backoff
                wait_time = min(2**attempt, MAX_RETRY_WAIT_SECONDS)
                logger.info(f"Waiting {wait_time} seconds before retry...")
                time.sleep(wait_time)

    # All attempts failed
    return None


def _save_chunk_file(
    chunk_number: int,
    translated_text: str,
    book_dir: Path,
    book: Book,
    logger: logging.Logger,
) -> Path:
    """Save a translated chunk to file.

    Args:
        chunk_number: Number of the chunk
        translated_text: Translated text content
        book_dir: Directory to save chunk in
        book: Book instance with metadata
        logger: Logger for output

    Returns:
        Path to the saved chunk file

    Raises:
        OSError: If file cannot be saved
    """
    sanitized_title = common_sanitize_filename(book.translated_title, max_length=50)
    sanitized_author = common_sanitize_filename(book.translated_author, max_length=50)
    output_filename = book_dir / f"{sanitized_title} by {sanitized_author} - Chunk_{chunk_number:06d}.txt"

    try:
        output_filename.write_text(translated_text)
        return output_filename
    except (OSError, PermissionError) as e:
        logger.error(f"Error saving chunk {chunk_number:06d} to {output_filename}: {e}")
        raise


def _save_final_book(
    translated_contents: list[str],
    book: Book,
    book_dir: Path,
    logger: logging.Logger,
) -> Path:
    """Combine and save all translated chunks into final book file.

    Args:
        translated_contents: List of translated text chunks
        book: Book instance with metadata
        book_dir: Directory to save book in
        logger: Logger for output

    Returns:
        Path to the saved book file

    Raises:
        OSError: If file cannot be saved
    """
    # Combine all translated chunks into one full text
    full_translated_text = "\n".join(translated_contents)
    full_translated_text = remove_excess_empty_lines(full_translated_text)

    # Save to a file named with the book metadata
    sanitized_title = common_sanitize_filename(book.translated_title, max_length=50)
    sanitized_author = common_sanitize_filename(book.translated_author, max_length=50)
    output_filename = book_dir / f"translated_{sanitized_title} by {sanitized_author}.txt"

    # Prepare path for writing (ensures parent directory is synced)
    output_filename = prepare_for_write(output_filename)

    try:
        with open(output_filename, "w", encoding="utf-8") as f:
            f.write(full_translated_text)
        logger.info(f"Translated book saved to {output_filename}")
        return output_filename
    except (OSError, PermissionError) as e:
        logger.error(f"Error saving translated book to {output_filename}: {e}")
        raise


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
    book_dir = _prepare_book_directory(book, logger)

    # Prepare autoresume data
    existing_chunk_nums: set[int] = set()
    if resume:
        existing_chunk_nums = _get_existing_chunks(book_dir, book, logger)

    translated_contents = []
    # Sort chunks by chunk_number
    sorted_chunks = sorted(book.chunks, key=lambda ch: ch.chunk_number)

    for chunk in sorted_chunks:
        # Retrieve the Variation corresponding to the original text
        variation = VARIATION_DB.get(chunk.original_variation_id)
        if not variation:
            continue

        # Check if chunk already exists (resume mode)
        if resume and chunk.chunk_number in existing_chunk_nums:
            # Load existing translation
            sanitized_title = common_sanitize_filename(book.translated_title, max_length=50)
            sanitized_author = common_sanitize_filename(book.translated_author, max_length=50)
            p_existing = book_dir / f"{sanitized_title} by {sanitized_author} - Chunk_{chunk.chunk_number:06d}.txt"
            try:
                translated_text = p_existing.read_text(encoding="utf-8")
                logger.info(f"Skipping translation for chunk {chunk.chunk_number}; using existing translation.")
                translated_contents.append(f"\n{translated_text}\n")
                continue
            except FileNotFoundError:
                logger.warning(f"Expected file {p_existing.name} not found; re-translating.")

        # Translate the chunk
        original_text = variation.text_content
        is_last_chunk = chunk.chunk_number == len(sorted_chunks)

        translated_text = _translate_chunk(
            chunk_number=chunk.chunk_number,
            original_text=original_text,
            translator=translator,
            is_last_chunk=is_last_chunk,
            max_retries=max_chunk_retries,
            logger=logger,
        )

        if translated_text is None:
            # All translation attempts failed
            sanitized_title = common_sanitize_filename(book.translated_title, max_length=50)
            sanitized_author = common_sanitize_filename(book.translated_author, max_length=50)
            output_path = book_dir / f"{sanitized_title} by {sanitized_author} - Chunk_{chunk.chunk_number:06d}.txt"

            error_message = format_chunk_error_message(
                chunk_number=chunk.chunk_number,
                max_retries=max_chunk_retries,
                last_error="All retry attempts exhausted",
                book_title=book.translated_title,
                book_author=book.translated_author,
                output_path=str(output_path),
            )
            logger.error(error_message)
            print(error_message)
            sys.exit(1)

        # Save chunk to file
        _save_chunk_file(
            chunk_number=chunk.chunk_number,
            translated_text=translated_text,
            book_dir=book_dir,
            book=book,
            logger=logger,
        )

        # Log and append to contents
        logger.info(f"\nChunk {chunk.chunk_number:06d}:\n{translated_text}\n\n")
        translated_contents.append(f"\n{translated_text}\n")

    # Save the complete translated book
    _save_final_book(translated_contents, book, book_dir, logger)

    # Save cost log for remote translations
    save_translation_cost_log(book, translator, book_dir, len(sorted_chunks), logger)
