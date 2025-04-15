#!/usr/bin/env python3
#
# Copyright (c) 2024 Emasoft
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0

from __future__ import annotations

from . import __version__

APP_NAME = "enchant_cli"
MIN_PYTHON_VERSION_REQUIRED = "3.8"

import codecs
import enum
import logging
import os
import re
import signal
import sys
import time
import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from threading import Event
from time import sleep

# from chardet.universaldetector import UniversalDetector # Moved to utils
from typing import (
    TYPE_CHECKING,
    ClassVar,
)

import click  # Import click
import colorama as cr
import multiexit
import rich
import rich.repr
from rich import print
from rich.console import Console, RenderableType
from rich.table import Table
from rich.text import Text

from .translation_service import ChineseAITranslator  # Use relative import

# Import shared utilities
from .utils import (
    ALL_PUNCTUATION,
    CHINESE_PUNCTUATION,
    CLOSING_QUOTES,
    ENGLISH_PUNCTUATION,
    NON_BREAKING,
    PARAGRAPH_DELIMITERS,
    PRESERVE_UNLIMITED,
    SENTENCE_ENDING,  # Import constants if needed
    clean,
    clean_adverts,
    decode_input_file_content,
    detect_file_encoding,
    flush_buffer,
    foreign_book_title_splitter,  # Import moved function
    is_markdown,
    limit_repeated_chars,
    normalize_spaces,
    quick_replace,
    remove_excess_empty_lines,
    remove_html_markup,
    replace_repeated_chars,  # Ensure this is imported if used directly
    split_on_punctuation_contextual,
    strip_urls,
)

# import html # Moved to utils

# Initialize translator later, inside main, once verbose flag is known
translator = None # Placeholder

global tolog


# Constants moved to utils.py:
# SENTENCE_ENDING, CLOSING_QUOTES, NON_BREAKING, ALL_PUNCTUATION
# CHINESE_PUNCTUATION, ENGLISH_PUNCTUATION
# PARAGRAPH_DELIMITERS, PRESERVE_UNLIMITED
# _repeated_chars regex

# Functions moved to utils.py:
# clean, replace_repeated_chars, limit_repeated_chars
# extract_code_blocks, extract_inline_code, remove_html_comments,
# remove_script_and_style, replace_block_tags, remove_remaining_tags,
# unescape_non_code_with_placeholders, remove_html_markup
# remove_excess_empty_lines, normalize_spaces
# strip_urls, is_markdown
# detect_file_encoding, decode_input_file_content
# clean_adverts, quick_replace, flush_buffer, split_on_punctuation_contextual
# foreign_book_title_splitter


### HELPER CLASSES #####

class TranslationState(enum.Enum):
    """A description of the worker's current state."""
    PENDING = 1
    """Translation task is initialized, but not running."""
    RUNNING = 2
    """Translation task is running."""
    CANCELLED = 3
    """Translation task is not running, and was cancelled."""
    ERROR = 4
    """Translation task is not running, and exited with an error."""
    SUCCESS = 5
    """Translation task is not running, and completed successfully."""


def load_text_file(txt_file_name):
        contents = None
        txt_file_name = Path.joinpath(Path.cwd(), Path(txt_file_name))
        if Path.is_file(txt_file_name):
                # Use the robust decode function from utils
                contents = decode_input_file_content(txt_file_name, tolog)
                tolog.debug(contents)
                return contents
        else:
                tolog.debug("Error : "+str(txt_file_name)+" is not a valid file!")
                return None

def save_text_file(text, filename):
        file_path = Path(Path.joinpath(Path.cwd(), Path(filename)))
        with open(file_path, "w", encoding="utf-8") as f:
                f.write(clean(text)) # Use clean from utils
        tolog.debug("Saved text file in: "+str(file_path))


# HELPER FUNCTION TO GET VALUE OR NONE FROM A LIST ENTRY
# an equivalent of dict.get(key, default) for lists
def get_val(myList, idx, default=None):
    try:
        return myList[idx]
    except IndexError:
        return default


# Function to extract title and author info from foreign novels filenames (chinese, japanese, etc.)
# MOVED TO utils.py


def split_chinese_text_using_split_points(book_content, max_chars: int = 6000):
    # SPLIT POINT METHOD
    # Compute split points based on max_chars and chapter patterns
    chapter_pattern = r'第\d+章'  # pattern to split at Chapter title/number line
    total_book_characters = len(book_content)
    split_points_list = []
    counter_chars = 0
    # Correctly calculate pattern length for matching
    # Example: '第\d+章' -> '第', one or more digits, '章'. Minimum length is 3.
    # We need to find the start of the pattern.
    # A simple approach is to search for the pattern start '第'.
    i = 0
    while i < total_book_characters:
        # Check if the current position starts a chapter pattern
        match = re.match(chapter_pattern, book_content[i:])
        if match:
            # If a chapter pattern is found, and we have accumulated some characters,
            # split before the chapter pattern.
            if counter_chars > 0: # Avoid splitting right at the beginning
                 split_points_list.append(i)
                 counter_chars = 0 # Reset counter after split
            # Move index past the matched chapter pattern
            i += match.end()
            counter_chars += match.end() # Count characters in the chapter title itself
            continue # Continue to next character after the pattern

        # Check if max_chars limit is reached
        if counter_chars >= max_chars:
            # Find the nearest sentence ending before the current position to split cleanly
            # Look back up to, say, 100 characters for a sentence end
            split_pos = -1
            search_end = i
            search_start = max(0, i - 100)
            for j in range(search_end - 1, search_start -1, -1):
                 if book_content[j] in SENTENCE_ENDING:
                     split_pos = j + 1 # Split after the punctuation
                     break
            if split_pos != -1 and split_pos > (split_points_list[-1] if split_points_list else 0):
                 split_points_list.append(split_pos)
                 counter_chars = i - split_pos # Reset counter based on actual split point
            else:
                 # If no suitable punctuation found nearby, force split at current position
                 split_points_list.append(i)
                 counter_chars = 0

        counter_chars += 1
        i += 1


    # Split book content at computed split points
    splitted_chapters = []
    start_index = 0
    for point in split_points_list:
        splitted_chapters.append(book_content[start_index:point])
        start_index = point
    # Add the last remaining part
    splitted_chapters.append(book_content[start_index:])

    # Filter out empty strings that might result from splitting logic
    splitted_chapters = [ch for ch in splitted_chapters if ch]

    return splitted_chapters


# NOTE: If a chapter/chunk go over the characters limit of max_char,
# then the chapter is split anyway without waiting for
# the chapter title pattern.
def import_book_from_txt(file_path, chapter_pattern=r'Chapter \d+', max_chars: int = 6000, split_mode='PARAGRAPHS'):
    tolog.debug(" -> import_book_from_text()")

    filename = Path(file_path).name
    # Check if book already exists (using the in-memory DB structure)
    duplicate_book = Book.get_or_none(Book.source_file == filename)
    if duplicate_book is not None:
        tolog.error(f"ERROR - Book with filename '{filename}' was already imported in db!")
        # Return existing ID or handle as needed
        return str(duplicate_book.book_id)

    # LOAD FILE CONTENT using robust util function
    try:
        book_content = decode_input_file_content(Path(file_path), tolog)
    except OSError as e:
        tolog.error(f"Failed to load or decode file {file_path}: {e}")
        return None # Indicate failure

    # CLEAN UP THE TEXT CONTENT using utils
    # book_content = remove_html_markup(book_content) # Uncomment if HTML expected
    book_content = normalize_spaces(book_content)
    book_content = remove_excess_empty_lines(book_content)

    # COUNT THE NUMBER OF CHARACTERS
    total_book_characters = len(book_content)
    if total_book_characters == 0:
        tolog.warning(f"Input file '{filename}' is empty or contains no processable content.")
        # Decide how to handle empty files - skip or create empty book?
        # For now, let's skip.
        return None


    # SPLIT THE BOOK IN CHUNKS
    if split_mode.upper() == "SPLIT_POINTS":
        splitted_chapters = split_chinese_text_using_split_points(book_content, max_chars=max_chars)
    elif split_mode.upper() == "PARAGRAPHS":
        splitted_chapters = split_chinese_text_in_parts(book_content, max_chars=max_chars)
    else:
        # default use split_mode = 'PARAGRAPHS'
        tolog.warning(f"Unknown split_mode '{split_mode}', defaulting to PARAGRAPHS.")
        splitted_chapters = split_chinese_text_in_parts(book_content, max_chars=max_chars)

    if not splitted_chapters:
         tolog.error(f"Text splitting resulted in zero chapters for file '{filename}'. Check content and splitting logic.")
         return None

    # Create new book entry in database
    new_book_id = str(uuid.uuid4())
    # Use correct unpacking order from foreign_book_title_splitter (now imported from utils)
    (translated_title, original_title, transliterated_title,
     translated_author, original_author, transliterated_author) = foreign_book_title_splitter(file_path)

    # Use parsed names, fallback if empty
    book_title = translated_title or original_title or "Untitled Book"
    book_author = translated_author or original_author or "Unknown Author"

    try:
        Book.create(
            book_id=new_book_id,
            title=book_title,
            original_title=original_title,
            translated_title=translated_title,
            transliterated_title=transliterated_title,
            author=book_author,
            original_author=original_author, # Corrected mapping
            translated_author=translated_author, # Corrected mapping
            transliterated_author=transliterated_author, # Corrected mapping
            source_file=filename,
            total_characters = total_book_characters,
            )
    except Exception as e:
        tolog.error(f"An exception happened when creating the book entry for {filename}: {e}")
        return None # Indicate failure
    finally:
        manual_commit()

    book = Book.get_by_id(new_book_id)
    if not book:
         tolog.error(f"Failed to retrieve newly created book with ID {new_book_id}")
         return None

    # for each chapter create a new chapter entry and a new orig variation in database
    chapters_created = 0
    for index, chapter_content in enumerate(splitted_chapters, start=1):
        new_chapter_id = str(uuid.uuid4())
        new_variation_id = str(uuid.uuid4())
        try:
            Chapter.create(chapter_id=new_chapter_id, book_id=new_book_id, chapter_number=index, original_variation_id=new_variation_id)
            Variation.create(
                variation_id=new_variation_id,
                book_id=new_book_id,
                chapter_id=new_chapter_id,
                chapter_number=index,
                language="original",
                category="original",
                text_content=chapter_content
            )
            chapters_created += 1
        except Exception as e:
            tolog.error(f"An exception happened when creating chapter n.{index} or its variation for book {new_book_id}: {e}")
            # Decide if we should continue or abort the whole book import
            # For now, log error and continue
        finally:
            manual_commit()

    if chapters_created == 0:
        tolog.error(f"Failed to create any chapters for book {new_book_id}. Rolling back book creation (conceptual).")
        # In a real DB, you'd delete the book entry here.
        # For the in-memory version, we can remove it:
        if new_book_id in BOOK_DB:
            del BOOK_DB[new_book_id]
        return None

    tolog.info(f"Successfully imported book '{book_title}' ({new_book_id}) with {chapters_created} chapters.")
    return new_book_id


## Function to split a chinese novel in parts of max n characters keeping the paragraphs intact
def process_batch(input_dir: Path, output_dir: Path | None, max_chars: int, split_mode: str, verbose: bool, double_translate: bool):
    # Parameter name kept as double_translate for backward compatibility
    """
    Process all .txt files in a directory for batch translation.
    """
    logger = logging.getLogger(__name__) # Use local logger instance
    txt_files = [f for f in input_dir.iterdir() if f.is_file() and f.suffix.lower() == ".txt"]
    logger.info(f"Found {len(txt_files)} .txt files in '{input_dir}'. Starting batch processing.")
    if not txt_files:
        click.secho(f"No .txt files found in the specified directory: {input_dir}", fg="yellow")
        return

    if not output_dir:
        output_dir = input_dir / "translated"
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Output directory set to: {output_dir}")

    processed = 0
    skipped = 0
    failed = 0
    total_cost = 0.0

    for file in txt_files:
        try:
            # Generate output filename from parsed metadata
            # Use correct unpacking order (function now imported from utils)
            (trans_title, _, _, trans_author, orig_author, _) = foreign_book_title_splitter(file.name)
            # Use original author name if translated author is unknown or empty
            author_name_for_file = orig_author if trans_author in ["Unknown Author", ""] else trans_author
            title_for_file = trans_title or "Untitled"
            out_name = f"{title_for_file} by {author_name_for_file}.txt"
            # Sanitize filename (optional, but good practice)
            out_name = re.sub(r'[<>:"/\\|?*]', '_', out_name) # Replace invalid chars
            output_path = output_dir / out_name

            click.secho(f"\nProcessing file: {file.name}", fg="cyan")
            click.echo(f"Output path: {output_path}")

            # Call main logic for single file translation
            # Need to simulate the main function's core logic here or refactor main
            # For now, let's call the import and save logic directly

            # 1. Import book
            book_id = import_book_from_txt(
                file_path=str(file),
                max_chars=max_chars,
                split_mode=split_mode.upper()
            )

            if not book_id:
                logger.warning(f"Skipping file {file.name}: Import failed or file was empty/invalid.")
                click.secho(f"Skipping file {file.name}: Import failed.", fg="yellow")
                skipped += 1
                continue # Skip to next file

            # 2. Translate and save book
            file_cost_result = save_translated_book(book_id, str(output_path), double_translate)
            if file_cost_result is None:
                logger.error(f"Critical error during translation or saving for {file.name}. Skipping.")
                click.secho(f"Error processing file {file.name}: Translation/Save failed.", fg="red")
                failed += 1
                continue # Skip to next file

            file_cost = file_cost_result
            total_cost += file_cost
            logger.info(f"Successfully processed {file.name}. Cost: ${file_cost:.6f}")
            click.secho(f"Successfully processed {file.name}.", fg="green")
            processed += 1

        except Exception as e:
            failed += 1
            logger.error(f"Error processing file {file.name}: {e}", exc_info=verbose) # Log traceback if verbose
            click.secho(f"Error processing file {file.name}: {e}", fg="red")

    # Final summary
    click.secho("\n--- Batch Processing Summary ---", bold=True)
    click.secho(f"Processed: {processed}", fg="green")
    click.secho(f"Skipped:   {skipped}", fg="yellow")
    click.secho(f"Failed:    {failed}", fg="red")
    click.secho(f"Total Estimated Cost: ${total_cost:.6f}")
    click.secho("------------------------------")


def split_chinese_text_in_parts(text: str, max_chars: int = 6000) -> list:
    # Use the robust splitting function from utils
    paragraphs = split_on_punctuation_contextual(text)
    if not paragraphs:
        tolog.warning("split_on_punctuation_contextual returned no paragraphs.")
        return []

    chapters = []
    current_char_count = 0
    paragraphs_buffer = []
    total_paragraphs = len(paragraphs)
    paragraphs_processed_count = 0

    for i, para in enumerate(paragraphs):
        para_len = len(para)
        # Check if adding the current paragraph exceeds the limit
        if current_char_count + para_len > max_chars and paragraphs_buffer:
            # If buffer is not empty and limit is exceeded, finalize the current chapter
            chapter = "".join(paragraphs_buffer)
            chapters.append(chapter)
            tolog.debug(f"Created chapter {len(chapters)} with {current_char_count} chars, {len(paragraphs_buffer)} paras.")

            # Start new chapter buffer with the current paragraph
            paragraphs_buffer = [para]
            current_char_count = para_len
        else:
            # Add paragraph to buffer and update count
            paragraphs_buffer.append(para)
            current_char_count += para_len

        paragraphs_processed_count += 1

    # Add any remaining paragraphs in the buffer as the last chapter
    if paragraphs_buffer:
        chapter = "".join(paragraphs_buffer)
        chapters.append(chapter)
        tolog.debug(f"Created final chapter {len(chapters)} with {current_char_count} chars, {len(paragraphs_buffer)} paras.")

    tolog.debug(f"\n -> Splitting COMPLETE.\n  Total paragraphs processed: {paragraphs_processed_count}\n  Total chapters created: {len(chapters)}\n")

    return chapters


###############################################
#              ADDED CLASSES                #
###############################################

# In-memory “database” dictionaries
BOOK_DB = {}
CHAPTER_DB = {}
VARIATION_DB = {}

class Field:
    def __init__(self, name):
        self.name = name
    def __get__(self, instance, owner):
        if instance is None:
            return self
        return instance.__dict__.get(self.name)
    def __set__(self, instance, value):
        instance.__dict__[self.name] = value
    def __eq__(self, other):
        # When used in a class-level comparison (e.g., Book.source_file == filename),
        # return a lambda that checks whether the instance's attribute equals 'other'.
        return lambda instance: getattr(instance, self.name, None) == other

class Book:
    # Using Field descriptor for source_file to support query comparisons
    source_file = Field('source_file')

    def __init__(self, book_id, title, original_title, translated_title, transliterated_title,
                 author, original_author, translated_author, transliterated_author, source_file, total_characters):
        self.book_id = book_id
        self.title = title
        self.original_title = original_title
        self.translated_title = translated_title
        self.transliterated_title = transliterated_title
        self.author = author
        self.original_author = original_author
        self.translated_author = translated_author
        self.transliterated_author = transliterated_author
        self.source_file = source_file
        self.total_characters = total_characters
        self.chapters = []  # List to hold Chapter instances

    @classmethod
    def create(cls, **kwargs):
        book = cls(
            book_id=kwargs.get("book_id"),
            title=kwargs.get("title"),
            original_title=kwargs.get("original_title"),
            translated_title=kwargs.get("translated_title"),
            transliterated_title=kwargs.get("transliterated_title"),
            author=kwargs.get("author"),
            original_author=kwargs.get("original_author"),
            translated_author=kwargs.get("translated_author"),
            transliterated_author=kwargs.get("transliterated_author"),
            source_file=kwargs.get("source_file"),
            total_characters=kwargs.get("total_characters")
        )
        BOOK_DB[book.book_id] = book
        return book

    @classmethod
    def get_or_none(cls, condition):
        for book in BOOK_DB.values():
            # The condition is expected to be a lambda function generated by Field.__eq__
            if condition(book):
                return book
        return None

    @classmethod
    def get_by_id(cls, book_id):
        return BOOK_DB.get(book_id)

class Chapter:
    def __init__(self, chapter_id, book_id, chapter_number, original_variation_id):
        self.chapter_id = chapter_id
        self.book_id = book_id
        self.chapter_number = chapter_number
        self.original_variation_id = original_variation_id
        # Add a link back to the book instance for easier navigation
        self.book = Book.get_by_id(book_id)

    @classmethod
    def create(cls, chapter_id, book_id, chapter_number, original_variation_id):
        chapter = cls(chapter_id, book_id, chapter_number, original_variation_id)
        CHAPTER_DB[chapter_id] = chapter
        # Also add the chapter to the corresponding Book's chapters list
        book = Book.get_by_id(book_id)
        if book:
            # Ensure chapters are added in order or sorted later
            book.chapters.append(chapter)
            # Keep the list sorted by chapter number
            book.chapters.sort(key=lambda c: c.chapter_number)
        else:
             # Log a warning if the book doesn't exist when creating a chapter
             logging.getLogger(__name__).warning(f"Attempted to create chapter {chapter_id} for non-existent book {book_id}")
        return chapter

class Variation:
    def __init__(self, variation_id, book_id, chapter_id, chapter_number, language, category, text_content):
        self.variation_id = variation_id
        self.book_id = book_id
        self.chapter_id = chapter_id
        self.chapter_number = chapter_number
        self.language = language
        self.category = category
        self.text_content = text_content
        # Add links for easier navigation
        self.book = Book.get_by_id(book_id)
        self.chapter = CHAPTER_DB.get(chapter_id)


    @classmethod
    def create(cls, **kwargs):
        variation = cls(
            variation_id=kwargs.get("variation_id"),
            book_id=kwargs.get("book_id"),
            chapter_id=kwargs.get("chapter_id"),
            chapter_number=kwargs.get("chapter_number"),
            language=kwargs.get("language"),
            category=kwargs.get("category"),
            text_content=kwargs.get("text_content")
        )
        VARIATION_DB[variation.variation_id] = variation
        # Optionally link variation back to chapter?
        # chapter = CHAPTER_DB.get(variation.chapter_id)
        # if chapter:
        #     if variation.category == 'original':
        #         chapter.original_variation = variation # Assuming you add this attribute
        #     # Add other variation types if needed
        return variation

def manual_commit():
    # Simulate a database commit. In this simple implementation, changes are already in memory.
    # tolog.debug("Manual commit executed.")
    pass

def save_translated_book(book_id, output_filename, double_translate: bool) -> float | None:
    """
    Translate the book chapter by chapter, save the combined translated text,
    and return the total translation cost, or None if a critical error occurs.
    """
    book = Book.get_by_id(book_id)
    if not book:
        tolog.error(f"Book with ID {book_id} not found in DB for saving.")
        raise ValueError("Book not found")

    translated_contents = []
    total_cost = 0.0 # Initialize total cost
    # Chapters should already be sorted in book.chapters if create logic is correct
    # sorted_chapters = sorted(book.chapters, key=lambda ch: ch.chapter_number)
    sorted_chapters = book.chapters # Use the potentially pre-sorted list
    num_chapters = len(sorted_chapters) # Get total number of chapters

    if num_chapters == 0:
        tolog.warning(f"Book {book_id} has no chapters to translate.")
        # Decide what to do: save empty file or raise error?
        # Let's save an empty file for now.
        output_path = Path(output_filename)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("", encoding="utf-8")
        tolog.info(f"Saved empty file for book with no chapters: {output_path}")
        return 0.0


    output_path_dir = Path(output_filename).parent
    output_path_dir.mkdir(parents=True, exist_ok=True) # Ensure dir exists once

    for i, chapter in enumerate(sorted_chapters):
        # Retrieve the Variation corresponding to the original text
        variation = VARIATION_DB.get(chapter.original_variation_id)
        if not variation:
             tolog.error(f"Original variation {chapter.original_variation_id} not found for chapter {chapter.chapter_number} (ID: {chapter.chapter_id}) in book {book_id}.")
             # Append error marker to output
             translated_contents.append(f"\n\n[ERROR: Original text missing for chapter {chapter.chapter_number}]\n\n")
             continue # Skip to next chapter

        original_text = variation.text_content
        try:
            tolog.info(f"TRANSLATING CHAPTER {chapter.chapter_number} of {num_chapters} (Book: {book.title})")
            is_last_chunk = (i == num_chapters - 1) # Correct check for last chunk
            translated_text, chunk_cost = translator.translate(
                original_text,
                double_translation=double_translate,
                is_last_chunk=is_last_chunk
            )
            # Check if translation failed (indicated by empty string and zero cost from translate method)
            if not translated_text and chunk_cost == 0.0 and original_text:
                 tolog.error(f"ERROR: Translation failed critically for chapter {chapter.chapter_number!s}. Aborting save.")
                 return None # Indicate critical failure

            total_cost += chunk_cost # Add cost of this chunk
            tolog.debug(f"Chapter {chapter.chapter_number} cost: ${chunk_cost:.6f}")

            # # Save individual chapter file (REMOVED - only save combined file)
            # # Use sanitized names
            # safe_title = re.sub(r'[<>:"/\\|?*]', '_', book.translated_title or book.title)
            # safe_author = re.sub(r'[<>:"/\\|?*]', '_', book.translated_author or book.author)
            # output_filename_chapter = f"{safe_title} by {safe_author} - Chapter {chapter.chapter_number}.txt"
            # p = output_path_dir / output_filename_chapter
            # try:
            #     p.write_text(translated_text, encoding="utf-8")
            # except Exception as write_err:
            #      tolog.error(f"Failed to write individual chapter file {p}: {write_err}")


        except Exception as e:
            tolog.error(f"ERROR: Translation failed for chapter {chapter.chapter_number!s} : {e!s}", exc_info=tolog.level == logging.DEBUG)
            # In case translation fails, append a marker
            translated_text = original_text + f"\n\n\n[Translation Failed for chapter number {chapter.chapter_number!s}]\n\n"
            # Optionally return None here to indicate critical failure to the caller
            return None # Indicate critical failure
        # tolog.info(f"\nChapter {chapter.chapter_number}:\n{translated_text}\n\n") # Maybe too verbose for INFO
        translated_contents.append(f"\n{translated_text}\n")

    # Combine all translated chapters into one full text
    full_translated_text = "\n".join(translated_contents)
    full_translated_text = remove_excess_empty_lines(full_translated_text) # Use util

    # Save the combined file
    output_path = Path(output_filename)
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(full_translated_text)
        tolog.info(f"Combined translated book saved to {output_path}")
    except Exception as write_err:
         tolog.error(f"Failed to write combined translated book file {output_path}: {write_err}")
         # Decide if we should raise the error or just log it
         return None # Indicate failure to write
         # For now, log and return the cost accumulated so far

    return total_cost # Return the aggregated cost

###############################################
#               MAIN FUNCTION               #
###############################################

def get_detailed_version():
    """Generate a detailed version string for display"""
    return f"Enchant-CLI - Version {__version__}"

@click.command(context_settings=dict(help_option_names=['-h', '--help']), name="enchant_cli")
@click.version_option(__version__, "-V", "--version", message=get_detailed_version(), prog_name=APP_NAME, help="Show version and exit immediately.")
@click.argument(
    "filepath",
    type=click.Path(exists=True, readable=True, path_type=Path),
)
@click.option(
    "--batch",
    is_flag=True,
    default=False,
    help="Process all TXT files in the specified directory (filepath must be a directory)."
)
@click.option(
    "--max-chars",
    type=click.IntRange(min=100), # Add a minimum sensible limit
    default=6000,
    show_default=True,
    help="Maximum characters per chunk for splitting.",
)
@click.option(
    "--split-mode", # Use hyphenated name for CLI option
    type=click.Choice(["PARAGRAPHS", "SPLIT_POINTS"], case_sensitive=False),
    default="PARAGRAPHS",
    show_default=True,
    help="Mode to split text.",
)
@click.option(
    "-o", "--output",
    type=click.Path(dir_okay=True, file_okay=True, writable=True, path_type=Path), # Allow directory for batch output
    default=None,
    help="Path to the output translated file or directory (for batch). Defaults to 'translated_<input_filename>' or './translated/' for batch.",
)
@click.option(
    "-v", "--verbose",
    is_flag=True,
    default=False,
    help="Enable verbose logging (DEBUG level).",
)
@click.option(
    "--double-translation", "--double-translate", # Keep both for compatibility
    "double_translate", # Use a consistent internal name
    is_flag=True,
    default=False,
    help="Perform a second translation pass for refinement (increases cost).",
)
def main(filepath: Path, batch: bool, max_chars: int, split_mode: str, output: Path | None, verbose: bool, double_translate: bool):
    """
    Translates Chinese text files (.txt) to English using the OpenRouter API.

    Can process a single file or a directory of files in batch mode.
    """
    global tolog
    global translator # Declare translator as global to modify it
    
    # Display version at startup
    click.secho(get_detailed_version(), fg="cyan", bold=True)

    # Set up logging based on verbosity
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(levelname)-8s - %(name)s - %(message)s", # Improved format
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    tolog = logging.getLogger(__name__) # Use __name__ for logger name
    if not verbose:
        # Silence overly verbose libraries
        logging.getLogger("requests").setLevel(logging.WARNING)
        logging.getLogger("urllib3").setLevel(logging.WARNING)
        logging.getLogger("chardet").setLevel(logging.WARNING)

    # Initialize the translator with the correct verbosity
    try:
        translator = ChineseAITranslator(logger=tolog, verbose=verbose)
    except Exception as e:
         tolog.error(f"Failed to initialize translator: {e}", exc_info=verbose)
         click.secho(f"Error: Failed to initialize translator: {e}", fg="red", err=True) # Add click output
         sys.exit(1)

    tolog.debug(f"CLI Arguments: filepath={filepath}, batch={batch}, max_chars={max_chars}, split_mode={split_mode}, output={output}, verbose={verbose}, double_translate={double_translate}")

    # --- Argument Validation ---
    if batch and not filepath.is_dir():
        click.secho(f"Error: --batch flag requires 'filepath' to be a directory, but got '{filepath}'", fg="red", err=True)
        sys.exit(1)
    if not batch and not filepath.is_file():
         click.secho(f"Error: Expected 'filepath' to be a file, but got '{filepath}' (use --batch for directories)", fg="red", err=True)
         sys.exit(1)
    if batch and output and output.is_file():
         click.secho(f"Error: In batch mode, --output must be a directory, but got file '{output}'", fg="red", err=True)
         sys.exit(1)
    if not batch and output and output.is_dir():
         click.secho(f"Error: In single file mode, --output must be a file path, but got directory '{output}'", fg="red", err=True)
         sys.exit(1)


    # --- Execution Logic ---
    start_time = time.monotonic() # Record start time
    total_cost = 0.0

    # Set up signal handling
    def signal_handler(sig, frame):
        tolog.warning("Interrupt received. Attempting graceful exit...")
        click.echo("\nInterrupt received. Exiting gracefully.", err=True)
        # Perform any necessary cleanup here if needed
        sys.exit(0)
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


    try:
        # Handle batch processing
        if batch:
            process_batch(
                input_dir=filepath,
                output_dir=output, # Pass output path (might be None)
                max_chars=max_chars,
                split_mode=split_mode,
                verbose=verbose,
                double_translate=double_translate
            )
            # Note: process_batch now handles its own summary and cost reporting
        else:
            # Handle single file processing
            tolog.info(f"Starting translation for single file: {filepath}")

            # 1. Import book
            new_book_id = import_book_from_txt(
                file_path=str(filepath), # Pass as string if function expects string
                max_chars=max_chars,
                split_mode=split_mode.upper() # Ensure uppercase for internal logic
            )

            if not new_book_id:
                # Error already logged by import_book_from_txt
                click.secho(f"Error during book import for {filepath}. Check logs.", fg="red", bold=True)
                sys.exit(1)

            tolog.info(f"Book imported successfully. Book ID: {new_book_id}")
            click.secho(f"Book imported successfully. Book ID: {new_book_id}", fg="green")

            # 2. Determine output filename and save
            if output:
                output_file = output
            else:
                # Default output filename in the current directory
                output_file = Path.cwd() / f"translated_{filepath.stem}.txt"

            tolog.info(f"Output will be saved to: {output_file}")
            click.echo(f"Output will be saved to: {output_file}")

            cost_result = save_translated_book(new_book_id, str(output_file), double_translate) # Pass flag and get cost

            if cost_result is None: # Check if save_translated_book indicated failure
                click.secho(f"Critical error during translation or saving for {filepath}. Check logs.", fg="red", bold=True)
                sys.exit(1)
            total_cost = cost_result

            tolog.info("Translated book saved successfully.")
            click.secho(f"Translated book saved successfully to {output_file}.", fg="green", bold=True)

            # --- Single File Summary ---
            end_time = time.monotonic() # Record end time
            total_duration = end_time - start_time

            summary_table = Table(title="Translation Summary", show_header=False, box=rich.box.ROUNDED, padding=(0, 1))
            summary_table.add_column("Metric", style="dim")
            summary_table.add_column("Value", style="bold")
            summary_table.add_row("Input File", str(filepath.name))
            summary_table.add_row("Output File", str(output_file.name))
            summary_table.add_row("Total Time", f"{total_duration:.2f} seconds")
            summary_table.add_row("Estimated Cost", f"${total_cost:.6f}")
            print(summary_table) # Use rich's print

    except Exception as e:
        tolog.exception("An unexpected error occurred during the main execution.") # Log full traceback
        click.secho(f"An unexpected error occurred: {e}", fg="red", bold=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
