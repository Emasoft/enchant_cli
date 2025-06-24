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
# - Extracted book import functionality from cli_translator.py
# - Added foreign book title parsing
# - Added book import with chunk creation
# - Integrated with models module
#

"""Book import utilities for the EnChANT Book Manager."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Optional, Any

from .models import Book, Chunk, Variation, manual_commit
from .file_handler import decode_input_file_content
from .text_processor import remove_excess_empty_lines
from .text_splitter import split_chinese_text_in_parts, DEFAULT_MAX_CHARS


def foreign_book_title_splitter(
    filename: str | Path,
) -> tuple[str, str, str, str, str, str]:
    """
    Extract title and author info from foreign novel filenames.

    Expected format: translated_title by translated_author - original_title by original_author.txt

    Args:
        filename: The filename to parse

    Returns:
        Tuple of (original_title, translated_title, transliterated_title,
                 original_author, translated_author, transliterated_author)
    """
    # Get the parts into variables and return them
    original_title = " n.d. "
    translated_title = " n.d. "
    transliterated_title = " n.d. "
    original_author = " n.d. "
    translated_author = " n.d. "
    transliterated_author = " n.d. "

    # Remove the extension
    base_filename = Path(filename).stem
    # Split the main string sections
    if " - " in base_filename:
        translated_part, original_part = base_filename.split(" - ")
    else:
        if " by " in base_filename:
            original_title, original_author = base_filename.split(" by ")
        else:
            original_title = base_filename
        translated_part = ""
        original_part = base_filename
    # Extract translated title and author
    if translated_part and " by " in translated_part:
        translated_title, translated_author = translated_part.split(" by ")
    else:
        translated_title = translated_part
    # Extract original title and author
    if original_part and " by " in original_part:
        original_title, original_author = original_part.split(" by ")
    else:
        original_title = original_part

    return (
        original_title,
        translated_title,
        transliterated_title,
        original_author,
        translated_author,
        transliterated_author,
    )


def import_book_from_txt(file_path: str | Path, encoding: str = "utf-8", max_chars: int = DEFAULT_MAX_CHARS, logger: Optional[Any] = None) -> str:
    """
    Import a book from text file and split into chunks.

    Args:
        file_path: Path to the book text file
        encoding: File encoding (unused, auto-detected)
        max_chars: Maximum characters per chunk
        logger: Optional logger for debug output

    Returns:
        The book_id of the imported book
    """
    if logger is not None:
        logger.debug(" -> import_book_from_text()")

    filename = Path(file_path).name
    duplicate_book = Book.get_or_none(Book.source_file == filename)
    if duplicate_book is not None:
        if logger is not None:
            logger.debug(f"ERROR - Book with filename '{filename}' was already imported in db!")
        return str(duplicate_book.book_id)

    # LOAD FILE CONTENT
    book_content = decode_input_file_content(Path(file_path), logger=logger)

    # CLEAN UP THE TEXT CONTENT
    book_content = remove_excess_empty_lines(book_content)

    # COUNT THE NUMBER OF CHARACTERS
    total_book_characters = len(book_content)

    # SPLIT THE BOOK IN CHUNKS
    splitted_chunks = split_chinese_text_in_parts(book_content, max_chars, logger=logger)

    # Create new book entry in database
    new_book_id = str(uuid.uuid4())
    (
        original_title,
        translated_title,
        transliterated_title,
        original_author,
        translated_author,
        transliterated_author,
    ) = foreign_book_title_splitter(file_path)
    book_title = translated_title
    book_author = translated_author

    try:
        Book.create(
            book_id=new_book_id,
            title=book_title,
            original_title=original_title,
            translated_title=translated_title,
            transliterated_title=transliterated_title,
            author=book_author,
            original_author=original_author,
            translated_author=translated_author,
            transliterated_author=transliterated_author,
            source_file=filename,
            total_characters=total_book_characters,
        )
    except Exception as e:
        if logger is not None:
            logger.debug("An exception happened when creating a new variation original for a chunk:")
            logger.debug("ERROR: " + str(e))
    finally:
        manual_commit()

    book = Book.get_by_id(new_book_id)

    # for each chunk create a new chunk entry and a new orig variation in database
    for index, chunk_content in enumerate(splitted_chunks, start=1):
        new_chunk_id = str(uuid.uuid4())
        new_variation_id = str(uuid.uuid4())
        try:
            Chunk.create(
                chunk_id=new_chunk_id,
                book_id=new_book_id,
                chunk_number=index,
                original_variation_id=new_variation_id,
            )
        except Exception as e:
            if logger is not None:
                logger.debug(f"An exception happened when creating chunk n.{index} with ID {new_variation_id}. ")
                logger.debug("ERROR: " + str(e))
        else:
            try:
                Variation.create(
                    variation_id=new_variation_id,
                    book_id=new_book_id,
                    chunk_id=new_chunk_id,
                    chunk_number=index,
                    language="original",
                    category="original",
                    text_content=chunk_content,
                )
            except Exception as e:
                chunk_number = index if "index" in locals() else "unknown"
                if logger is not None:
                    logger.debug(f"An exception happened when creating a new variation original for chunk n.{chunk_number}:")
                    logger.debug("ERROR: " + str(e))
        finally:
            manual_commit()

    return new_book_id
