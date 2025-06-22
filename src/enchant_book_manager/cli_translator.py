#!/usr/bin/env python3
#
# Copyright (c) 2025 Emasoft
#
# Licensed under the Apache License, Version 2.0 (the "License");
# You may not use this file except in compliance with the License.
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
#
# Copyright (c) 2024 Emasoft

from __future__ import annotations

import datetime as dt
import enum
import errno
import logging
import re
import signal
import sys
import time
import uuid
from pathlib import Path
from typing import (
    Any,
    Dict,
    Optional,
)

import filelock
import yaml

from .common_print_utils import safe_print
from .common_text_utils import (
    ALL_PUNCTUATION,
    CLOSING_QUOTES,
    NON_BREAKING,
    SENTENCE_ENDING,
    clean,
    clean_adverts,
    replace_repeated_chars,
)
from .common_utils import sanitize_filename as common_sanitize_filename
from .common_yaml_utils import load_safe_yaml as load_yaml_safe
from .common_file_utils import (
    decode_full_file,
    detect_file_encoding as common_detect_encoding,
)
from .config_manager import ConfigManager
from .cost_tracker import global_cost_tracker
from .icloud_sync import ICloudSync, ensure_synced, prepare_for_write
from .translation_service import ChineseAITranslator

try:
    import colorama as cr
except ImportError:
    cr = None  # type: ignore[assignment]
    # tolog is not yet defined here, so we will log warning later in main if needed

APP_NAME = "cli-translator"
APP_VERSION = "0.1.0"  # Semantic version (major.minor.patch)
MIN_PYTHON_VERSION_REQUIRED = "3.8"
# EPUB imports removed - EPUB generation is handled by enchant_cli.py orchestrator
# Note: model_pricing module is deprecated - using global_cost_tracker instead

# Global variables - will be initialized in main()
translator: Optional[ChineseAITranslator] = None
tolog: Optional[logging.Logger] = None
icloud_sync: Optional[ICloudSync] = None
_module_config: Optional[Dict[str, Any]] = None
# Cost tracking is now handled by global_cost_tracker from cost_tracker module

MAXCHARS = 11999  # Default value, will be updated from config in main()

# Chunk retry constants
DEFAULT_MAX_CHUNK_RETRIES = 10
MAX_RETRY_WAIT_SECONDS = 60


# All punctuation constants are imported from common_text_utils:
# SENTENCE_ENDING, CLOSING_QUOTES, NON_BREAKING, ALL_PUNCTUATION


# PARAGRAPH DELIMITERS (characters that denote new paragraphs)
PARAGRAPH_DELIMITERS = {
    "\n",
    "\v",
    "\f",
    "\x1c",
    "\x1d",
    "\x1e",
    "\x85",
    "\u2028",
    "\u2029",
}

# Characters that are allowed unlimited repetition by default.
# These include whitespace, control characters, some punctuation, symbols, and paragraph delimiters.
PRESERVE_UNLIMITED = {
    " ",
    ".",
    "\n",
    "\r",
    "\t",
    "(",
    ")",
    "[",
    "]",
    "+",
    "-",
    "_",
    "=",
    "/",
    "|",
    "\\",
    "*",
    "%",
    "#",
    "@",
    "~",
    "<",
    ">",
    "^",
    "&",
    "°",
    "…",
    "—",
    "•",
    "$",
}.union(PARAGRAPH_DELIMITERS)

# Precompile the regular expression pattern for matching repeated characters.
_repeated_chars = re.compile(r"(.)\1+")


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


def load_text_file(txt_file_name: str | Path) -> str | None:
    """
    Load text file contents.

    Args:
        txt_file_name: Path to the text file

    Returns:
        File contents as string, or None if file cannot be read
    """
    contents = None
    txt_file_name = Path.joinpath(Path.cwd(), Path(txt_file_name))
    if Path.is_file(txt_file_name):
        try:
            with open(txt_file_name, encoding="utf8") as f:
                contents = f.read()
                if tolog is not None:
                    tolog.debug(contents)
            return contents
        except (OSError, PermissionError) as e:
            if tolog is not None:
                tolog.error(f"Error reading file {txt_file_name}: {e}")
            return None
    else:
        if tolog is not None:
            tolog.debug("Error : " + str(txt_file_name) + " is not a valid file!")
        return None


def save_text_file(text: str, filename: str | Path) -> None:
    """
    Save text to a file.

    Args:
        text: Text content to save
        filename: Path where to save the file
    """
    file_path = Path(Path.joinpath(Path.cwd(), Path(filename)))
    try:
        with open(file_path, "wt", encoding="utf-8") as f:
            f.write(clean(text))
        if tolog is not None:
            tolog.debug("Saved text file in: " + str(file_path))
    except (OSError, PermissionError) as e:
        if tolog is not None:
            tolog.error(f"Error saving file {file_path}: {e}")
        raise


def remove_excess_empty_lines(txt: str) -> str:
    """Reduce consecutive empty lines to a maximum of 3 (4 newlines)."""
    # Match 4 or more newline characters and replace with exactly 3 newlines
    return re.sub(r"\n{4,}", "\n\n\n", txt)


# NOTE: normalize_spaces function removed - use from common_text_utils if needed


# HELPER FUNCTION TO GET VALUE OR NONE FROM A LIST ENTRY
# an equivalent of dict.get(key, default) for lists
def get_val(myList: list[Any], idx: int, default: Any = None) -> Any:
    """
    Get value from list at index, returning default if index is out of bounds.

    An equivalent of dict.get(key, default) for lists.

    Args:
        myList: The list to get value from
        idx: The index to access
        default: Default value if index is out of bounds

    Returns:
        Value at index or default if index is invalid
    """
    try:
        return myList[idx]
    except IndexError:
        return default


_email_re = re.compile(r"[a-zA-Z0-9_\.\+\-]+\@[a-zA-Z0-9_\.\-]+\.[a-zA-Z]+")
_url_re = re.compile(r"https?://(-\.)?([^\s/?\.#]+\.?)+(/[^\s]*)?")


def strip_urls(input_text: str) -> str:
    """
    Strip URLs and emails from a string.

    Args:
        input_text: Text containing URLs and/or emails

    Returns:
        Text with URLs and emails removed
    """
    input_text = _url_re.sub("", input_text)
    input_text = _email_re.sub("", input_text)
    return input_text


_markdown_re = re.compile(r".*(" r"\*(.*)\*|" r"_(.*)_|" r"\[(.*)\]\((.*)\)|" r"`(.*)`|" r"```(.*)```" r").*")


def is_markdown(input_text: str) -> bool:
    """
    Check if a string contains markdown formatting.

    Args:
        input_text: Text to check for markdown

    Returns:
        True if text contains markdown formatting, False otherwise
    """
    # input_text = input_text[:1000]  # check only first 1000 chars
    # Don't mark part of URLs or email addresses as Markdown
    input_text = strip_urls(input_text)
    return bool(_markdown_re.match(input_text.replace("\n", "")))


def decode_input_file_content(input_file: Path) -> str:
    """
    Decode file content with automatic encoding detection.

    Uses common file utilities for consistent encoding detection across modules.
    Ensures file is synced from iCloud if needed.

    Args:
        input_file: Path to the file to decode

    Returns:
        Decoded file content as string
    """
    # Ensure file is synced from iCloud if needed
    input_file = ensure_synced(input_file)

    # Use common file utility for decoding
    return decode_full_file(input_file, logger=tolog)


# Wrapper for common encoding detection for backward compatibility
def detect_file_encoding(file_path: Path) -> str:
    """
    Detect the encoding of a file.

    Uses common file utilities for consistent encoding detection.

    Args:
        file_path: Path to the file to analyze

    Returns:
        Detected encoding name (defaults to 'utf-8' on error)
    """
    # Ensure file is synced from iCloud if needed
    file_path = ensure_synced(file_path)

    # Use common detection with universal method for compatibility
    encoding, _ = common_detect_encoding(file_path, method="universal", logger=tolog)
    return encoding


# Function to extract title and author info from foreign novels filenames (chinese, japanese, etc.)
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
    # FILE NAME STRUCTURE - SPLIT THE STRING TO EXTRACT THE INFORMATIONS ABOUT TITLE AND AUTUOR NAMES
    # EXAMPLE:
    # translated_title by translated_author - original_title by original_author.txt
    #

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


# Import the original language novel txt file and split it in chunks of max MAXCHARS characters
def import_book_from_txt(file_path: str | Path, encoding: str = "utf-8", max_chars: int = MAXCHARS) -> str:
    """
    Import a book from text file and split into chunks.

    Args:
        file_path: Path to the book text file
        encoding: File encoding (unused, auto-detected)
        max_chars: Maximum characters per chunk

    Returns:
        The book_id of the imported book
    """
    if tolog is not None:
        tolog.debug(" -> import_book_from_text()")

    filename = Path(file_path).name
    duplicate_book = Book.get_or_none(Book.source_file == filename)
    if duplicate_book is not None:
        if tolog is not None:
            tolog.debug("ERROR - Book with filename '{filename}' was already imported in db!")
        return str(duplicate_book.book_id)

    # LOAD FILE CONTENT
    book_content = decode_input_file_content(Path(file_path))

    # CLEAN UP THE TEXT CONTENT
    # book_content = remove_html_markup(book_content)
    # book_content = normalize_spaces(book_content)
    book_content = remove_excess_empty_lines(book_content)

    # COUNT THE NUMBER OF CHARACTERS
    total_book_characters = len(book_content)

    # SPLIT THE BOOK IN CHUNKS
    splitted_chunks = split_chinese_text_in_parts(book_content, max_chars)

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
        if tolog is not None:
            tolog.debug("An exception happened when creating a new variation original for a chunk:")
            tolog.debug("ERROR: " + str(e))
    finally:
        manual_commit()

    book = Book.get_by_id(new_book_id)

    # for each chunk create a new chunk entry and a new orig variation in database
    for index, chunk_content in enumerate(splitted_chunks, start=1):
        new_chunk_id = str(uuid.uuid4())
        new_variation_id = str(uuid.uuid4())
        try:
            chunk.create(
                chunk_id=new_chunk_id,
                book_id=new_book_id,
                chunk_number=index,
                original_variation_id=new_variation_id,
            )
        except Exception as e:
            if tolog is not None:
                tolog.debug(f"An exception happened when creating chunk n.{index} with ID {new_variation_id}. ")
                tolog.debug("ERROR: " + str(e))
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
                if tolog is not None:
                    tolog.debug(f"An exception happened when creating a new variation original for chunk n.{chunk_number}:")
                    tolog.debug("ERROR: " + str(e))
        finally:
            manual_commit()

    return new_book_id


def quick_replace(text_content: str, original: str, substitution: str, case_insensitive: bool = True) -> str:
    """
    Replace all occurrences of a string with another string.

    Args:
        text_content: The text to modify
        original: String to find
        substitution: String to replace with
        case_insensitive: Whether to ignore case when matching

    Returns:
        Modified text with replacements made
    """
    # case insensitive substitution or not
    if case_insensitive:
        return re.sub("(?i)" + re.escape(original), lambda m: f"{substitution}", text_content)
    else:
        return re.sub(re.escape(original), lambda m: f"{substitution}", text_content)


def flush_buffer(buffer: str, paragraphs: list[str]) -> str:
    """
    If the buffer contains text, normalize spaces and append it as a new paragraph.
    Returns an empty string to reset the buffer.
    """
    buffer = clean(buffer)
    if buffer:
        buffer = re.sub(" +", " ", buffer)
        paragraphs.append(buffer + "\n\n")
    return ""


def split_on_punctuation_contextual(text: str) -> list[str]:
    """
    Splits Chinese text into paragraphs based on punctuation and newline delimiters.

    The function uses:
      - SENTENCE_ENDING: Punctuation that typically ends a sentence.
      - CLOSING_QUOTES: Trailing quotes that may follow sentence-ending punctuation.
      - NON_BREAKING: Punctuation such as the Chinese comma and enumeration comma that
        do not trigger a paragraph break.
      - PARAGRAPH_DELIMITERS: A comprehensive set of newline and Unicode paragraph separators.
      - PARAGRAPH_START_TRIGGERS: Characters which, if they follow punctuation, indicate
        a new paragraph is starting.

    Returns a list of paragraphs.
    """
    if not isinstance(text, str):
        raise TypeError("Input text must be a string")

    # CHINESE PUNCTUATION
    # Characters groups for chinese punctuation and paragraph delimiters.
    # Ideographic '『' and '』' are omitted because they are usually nested inside '「' and '」'.
    # Ideographic '（' and '）' are omitted because they are rarely used as paragraph delimiters.
    # Use the imported punctuation constants from common_text_utils

    # Define a comprehensive set of paragraph delimiters.
    PARAGRAPH_DELIMITERS = {
        "\n",  # Line Feed
        "\v",  # Vertical Tab
        "\f",  # Form Feed
        "\x1c",  # File Separator
        "\x1d",  # Group Separator
        "\x1e",  # Record Separator
        "\x85",  # Next Line (C1 Control Code)
        "\u2028",  # Line Separator
        "\u2029",  # Paragraph Separator
    }

    # Define characters that trigger a new paragraph when following punctuation.
    PARAGRAPH_START_TRIGGERS = {"\n", "“", "【", "《", "「"}

    # Preprocess text:
    # 1. Clean and normalize newlines.
    # 2. Remove extra spaces.
    # 3. Replace repeated punctuation and delimiter characters.
    text = clean_adverts(text)
    text = clean(text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(" +", " ", text)
    text = replace_repeated_chars(text, "".join(ALL_PUNCTUATION))
    text = replace_repeated_chars(text, "".join(PARAGRAPH_DELIMITERS))

    paragraphs: list[str] = []
    buffer = ""
    length = len(text)
    i = 0
    while i < length:
        char = text[i]
        next_char = text[i + 1] if i + 1 < length else None
        next_next_char = text[i + 2] if i + 2 < length else None

        # If the character is a paragraph delimiter, flush the buffer.
        if char in PARAGRAPH_DELIMITERS:
            buffer += char
            buffer = flush_buffer(buffer, paragraphs)
            i += 1
            continue

        # If the character is a sentence-ending punctuation, add it.
        if char in SENTENCE_ENDING:
            buffer += char
            # Lookahead: If the next character indicates the start of a new paragraph
            if (next_char in PARAGRAPH_START_TRIGGERS) or (next_char == " " and next_next_char in PARAGRAPH_START_TRIGGERS):
                buffer = flush_buffer(buffer, paragraphs)
                i += 1
                continue
            i += 1
            continue

        # If the character is a closing quote,
        # flush only if it directly follows sentence-ending punctuation.
        if char in CLOSING_QUOTES:
            if buffer and buffer[-1] in SENTENCE_ENDING:
                buffer += char
                if (next_char in PARAGRAPH_START_TRIGGERS) or (next_char == " " and next_next_char in PARAGRAPH_START_TRIGGERS):
                    buffer = flush_buffer(buffer, paragraphs)
                    i += 1
                    continue
                else:
                    i += 1
                    continue
            else:
                buffer += char
                i += 1
                continue

        # For non-breaking punctuation, simply add the character.
        if char in NON_BREAKING:
            buffer += char
            i += 1
            continue

        # Otherwise, append the current character.
        buffer += char
        i += 1

    # Flush any residual text in the buffer as the last paragraph.
    if clean(buffer):
        paragraphs.append(re.sub(" +", " ", clean(buffer)) + "\n\n")

    return paragraphs


def split_text_by_actual_paragraphs(text: str) -> list[str]:
    """
    Splits text into paragraphs based on actual paragraph breaks (double newlines).
    This preserves the natural paragraph structure of the text.
    """
    if not isinstance(text, str):
        raise TypeError("Input text must be a string")

    # Preprocess text
    text = clean_adverts(text)
    text = clean(text)

    # Normalize newlines
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Split on double newlines (actual paragraph breaks)
    # Also handle other Unicode paragraph separators
    text = text.replace("\u2029", "\n\n")  # Paragraph Separator
    text = text.replace("\u2028", "\n")  # Line Separator

    # Split on double newlines
    raw_paragraphs = re.split(r"\n\s*\n", text)

    paragraphs = []
    for para in raw_paragraphs:
        para = para.strip()
        if para:
            # Clean up extra spaces
            para = re.sub(" +", " ", para)
            # Add back the double newline for consistency
            paragraphs.append(para + "\n\n")

    return paragraphs


## Function to split a chinese novel in parts of max n characters keeping the paragraphs intact
def split_chinese_text_in_parts(text: str, max_chars: int = MAXCHARS) -> list[str]:
    """
    Split Chinese novel text into chunks of maximum character length.

    Keeps paragraphs intact when splitting.

    Args:
        text: The Chinese text to split
        max_chars: Maximum characters per chunk

    Returns:
        List of text chunks
    """
    # Choose splitting method based on parameter
    # Always use paragraph splitting method
    if False:  # Legacy punctuation method disabled
        # Use legacy punctuation-based splitting
        paragraphs = split_on_punctuation_contextual(text)
    else:
        # Use the new function that splits on actual paragraph breaks
        paragraphs = split_text_by_actual_paragraphs(text)
    chunks = list()
    chunks_counter = 1
    current_char_count = 0
    paragraphs_buffer: list[str] = []
    paragraph_index = 0
    chars_processed = 0

    # Handle empty text
    if not paragraphs or all(not p.strip() for p in paragraphs):
        return [""]

    for i, para in enumerate(paragraphs):
        # CHECK IF THE CURRENT PARAGRAPHS BUFFER HAS REACHED
        # THE CHARACTERS LIMIT AND IN SUCH CASE SAVE AND EMPTY THE PARAGRAPHS BUFFER
        if current_char_count + len(para) > max_chars:
            # Only save if buffer has content
            if paragraphs_buffer:
                paragraph_index += len(paragraphs_buffer)
                chunk = "".join(paragraphs_buffer)
                chunks.append(chunk)
                chunks_counter += 1
                current_char_count = 0
                paragraphs_buffer = []

        paragraphs_buffer.append(para)
        chars_processed += len(para)
        current_char_count += len(para)

    # IF THE PARAGRAPH BUFFER STILL CONTAINS SOME PARAGRAPHS
    # THEN SAVE THE RESIDUAL PARAGRAPHS IN A FINAL FILE.
    if paragraphs_buffer:
        paragraph_index += len(paragraphs_buffer)
        chunk = "".join(paragraphs_buffer)
        chunks.append(chunk)
        chunks_counter += 1

    if tolog is not None:
        tolog.debug(f"\n -> Import COMPLETE.\n  Total number of paragraphs: {str(paragraph_index)}\n  Total number of chunks: {str(chunks_counter)}\n")

    return chunks


# Main function is at the end of this file

###############################################
#              ADDED CLASSES                #
###############################################

# In-memory “database” dictionaries
BOOK_DB = {}
chunk_DB = {}
VARIATION_DB = {}


class Field:
    """
    Simple descriptor class for field access in in-memory database.

    Allows attribute-style access and comparison operations.
    """

    def __init__(self, name: str) -> None:
        self.name = name

    def __get__(self, instance: Any, owner: type) -> Any:
        if instance is None:
            return self
        return instance.__dict__.get(self.name)

    def __set__(self, instance: Any, value: Any) -> None:
        instance.__dict__[self.name] = value

    def __eq__(self, other: Any) -> Any:
        # When used in a class-level comparison (e.g., Book.source_file == filename),
        # return a lambda that checks whether the instance's attribute equals 'other'.
        return lambda instance: getattr(instance, self.name, None) == other


class Book:
    """
    Represents a book in the translation system.

    Stores metadata about the book including titles, authors, and source file info.
    """

    # Using Field descriptor for source_file to support query comparisons
    source_file = Field("source_file")

    def __init__(
        self,
        book_id: str,
        title: str,
        original_title: str,
        translated_title: str,
        transliterated_title: str,
        author: str,
        original_author: str,
        translated_author: str,
        transliterated_author: str,
        source_file: str,
        total_characters: int,
    ) -> None:
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
        self.chunks: list[chunk] = []  # List to hold chunk instances

    @classmethod
    def create(cls, **kwargs: Any) -> Book:
        """
        Create a new Book instance and add it to the database.

        Args:
            **kwargs: Book attributes (book_id, title, authors, etc.)

        Returns:
            The created Book instance
        """
        book = cls(
            book_id=kwargs.get("book_id", ""),
            title=kwargs.get("title", ""),
            original_title=kwargs.get("original_title", ""),
            translated_title=kwargs.get("translated_title", ""),
            transliterated_title=kwargs.get("transliterated_title", ""),
            author=kwargs.get("author", ""),
            original_author=kwargs.get("original_author", ""),
            translated_author=kwargs.get("translated_author", ""),
            transliterated_author=kwargs.get("transliterated_author", ""),
            source_file=kwargs.get("source_file", ""),
            total_characters=kwargs.get("total_characters", 0),
        )
        BOOK_DB[book.book_id] = book
        return book

    @classmethod
    def get_or_none(cls, condition: Any) -> Optional[Book]:
        """
        Find a book matching the given condition.

        Args:
            condition: A callable that returns True for matching books

        Returns:
            The first matching Book instance or None
        """
        for book in BOOK_DB.values():
            if condition(book):
                return book
        return None

    @classmethod
    def get_by_id(cls, book_id: str) -> Book:
        """
        Get a book by its ID.

        Args:
            book_id: The book's unique identifier

        Returns:
            The Book instance

        Raises:
            KeyError: If book not found
        """
        book = BOOK_DB.get(book_id)
        if book is None:
            raise KeyError(f"Book with id {book_id} not found")
        return book


class chunk:
    """
    Represents a text chunk of a book for translation.

    Books are split into chunks for manageable translation.
    """

    def __init__(self, chunk_id: str, book_id: str, chunk_number: int, original_variation_id: str) -> None:
        self.chunk_id = chunk_id
        self.book_id = book_id
        self.chunk_number = chunk_number
        self.original_variation_id = original_variation_id

    @classmethod
    def create(cls, chunk_id: str, book_id: str, chunk_number: int, original_variation_id: str) -> chunk:
        """
        Create a new chunk and add it to the database.

        Args:
            chunk_id: Unique identifier for the chunk
            book_id: ID of the book this chunk belongs to
            chunk_number: Sequential number of this chunk
            original_variation_id: ID of the original text variation

        Returns:
            The created chunk instance
        """
        chunk = cls(chunk_id, book_id, chunk_number, original_variation_id)
        chunk_DB[chunk_id] = chunk
        # Also add the chunk to the corresponding Book's chunks list
        book = Book.get_by_id(book_id)
        if book:
            book.chunks.append(chunk)
        return chunk


class Variation:
    """
    Represents a text variation (original or translated) of a chunk.

    Stores the actual text content and metadata about language and category.
    """

    def __init__(
        self,
        variation_id: str,
        book_id: str,
        chunk_id: str,
        chunk_number: int,
        language: str,
        category: str,
        text_content: str,
    ) -> None:
        self.variation_id = variation_id
        self.book_id = book_id
        self.chunk_id = chunk_id
        self.chunk_number = chunk_number
        self.language = language
        self.category = category
        self.text_content = text_content

    @classmethod
    def create(cls, **kwargs: Any) -> Variation:
        """
        Create a new Variation instance and add it to the database.

        Args:
            **kwargs: Variation attributes (variation_id, text_content, etc.)

        Returns:
            The created Variation instance
        """
        variation = cls(
            variation_id=kwargs.get("variation_id", ""),
            book_id=kwargs.get("book_id", ""),
            chunk_id=kwargs.get("chunk_id", ""),
            chunk_number=kwargs.get("chunk_number", 0),
            language=kwargs.get("language", ""),
            category=kwargs.get("category", ""),
            text_content=kwargs.get("text_content", ""),
        )
        VARIATION_DB[variation.variation_id] = variation
        return variation


def manual_commit() -> None:
    """
    Simulate a database commit (no-op for in-memory storage).
    """
    # Simulate a database commit. In this simple implementation, changes are already in memory.
    # tolog.debug("Manual commit executed.")
    pass


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


def save_translated_book(book_id: str, resume: bool = False, create_epub: bool = False) -> None:
    """
    Simulate translation of the book and save the translated text to a file.
    For each chunk, use the translator to translate the original text.

    Note: The create_epub parameter is kept for backward compatibility but is ignored.
    EPUB generation is handled by enchant_cli.py orchestrator.
    """
    # Ensure logger is available
    global tolog
    if tolog is None:
        tolog = logging.getLogger(__name__)

    # Get max chunk retry attempts from config or use default
    max_chunk_retries = DEFAULT_MAX_CHUNK_RETRIES
    if _module_config:
        max_chunk_retries = _module_config.get("translation", {}).get("max_chunk_retries", DEFAULT_MAX_CHUNK_RETRIES)

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
            tolog.error(f"Error creating directory: {e}")
            book_dir = Path.cwd()

    # Prepare autoresume data
    existing_chunk_nums: set[int] = set()
    if resume:
        pattern = f"{book.translated_title} by {book.translated_author} - Chunk_*.txt"
        for p in sorted(book_dir.glob(pattern), key=lambda x: x.name):
            match = re.search(r"Chunk_(\d{6})\.txt$", p.name)
            if match:
                existing_chunk_nums.add(int(match.group(1)))
        if existing_chunk_nums:
            tolog.info(f"Autoresume active: existing translated chunks detected: {sorted(existing_chunk_nums)}")
        else:
            tolog.info("Autoresume active but no existing chunk files found.")

    translated_contents = []
    # Sort chunks by chunk_number
    sorted_chunks = sorted(book.chunks, key=lambda ch: ch.chunk_number)
    for chunk in sorted_chunks:
        # Retrieve the Variation corresponding to the original text
        variation = VARIATION_DB.get(chunk.original_variation_id)
        if variation:
            if resume and chunk.chunk_number in existing_chunk_nums:
                p_existing = book_dir / f"{book.translated_title} by {book.translated_author} - Chunk_{chunk.chunk_number:06d}.txt"
                try:
                    translated_text = p_existing.read_text(encoding="utf-8")
                    tolog.info(f"Skipping translation for chunk {chunk.chunk_number}; using existing translation.")
                except FileNotFoundError:
                    tolog.warning(f"Expected file {p_existing.name} not found; re-translating.")
                else:
                    translated_contents.append(f"\n{translated_text}\n")
                    continue
            original_text = variation.text_content

            # Use the max_chunk_retries loaded above
            chunk_translated = False
            last_error = None
            output_filename_chunk = book_dir / f"{book.translated_title} by {book.translated_author} - Chunk_{chunk.chunk_number:06d}.txt"

            for chunk_attempt in range(1, max_chunk_retries + 1):
                try:
                    tolog.info(f"TRANSLATING CHUNK {chunk.chunk_number:06d} of {len(sorted_chunks)} (Attempt {chunk_attempt}/{max_chunk_retries})")
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
                        if tolog is not None:
                            tolog.error(f"Error saving chunk {chunk.chunk_number:06d} to {p}: {e}")
                        raise

                    # Success! Mark as translated and break out of retry loop
                    chunk_translated = True
                    tolog.info(f"Successfully translated chunk {chunk.chunk_number:06d} on attempt {chunk_attempt}")
                    break

                except Exception as e:
                    last_error = e
                    tolog.error(f"ERROR: Translation failed for chunk {chunk.chunk_number:06d} on attempt {chunk_attempt}/{max_chunk_retries}: {str(e)}")

                    if chunk_attempt < max_chunk_retries:
                        # Calculate wait time with exponential backoff
                        wait_time = min(2**chunk_attempt, MAX_RETRY_WAIT_SECONDS)
                        tolog.info(f"Waiting {wait_time} seconds before retry...")
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
                tolog.error(error_message)
                print(error_message)
                sys.exit(1)
            else:
                # Translation succeeded - log and append to contents
                tolog.info(f"\nChunk {chunk.chunk_number:06d}:\n{translated_text}\n\n")
                translated_contents.append(f"\n{translated_text}\n")
    # Combine all translated chunks into one full text
    full_translated_text = "\n".join(translated_contents)
    full_translated_text = remove_excess_empty_lines(full_translated_text)
    # Save to a file named with the book_id
    output_filename = book_dir / f"translated_{book.translated_title} by {book.translated_author}.txt"
    # Prepare path for writing (ensures parent directory is synced)
    output_filename = prepare_for_write(output_filename)
    try:
        with open(output_filename, "w", encoding="utf-8") as f:
            f.write(full_translated_text)
        if tolog is not None:
            tolog.info(f"Translated book saved to {output_filename}")
    except (OSError, PermissionError) as e:
        if tolog is not None:
            tolog.error(f"Error saving translated book to {output_filename}: {e}")
        raise

    # Save cost log for remote translations
    if translator and translator.is_remote and translator.request_count > 0:
        cost_log_filename = output_filename.with_suffix("").name + "_AI_COSTS.log"
        cost_log_path = book_dir / cost_log_filename
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
                f.write(f"Total Chunks Translated: {len(sorted_chunks)}\n")
                summary = global_cost_tracker.get_summary()
                if summary["request_count"] > 0 and len(sorted_chunks) > 0:
                    f.write(f"Average Cost per chunk: ${summary['total_cost'] / len(sorted_chunks):.6f}\n")
                    f.write(f"Average Tokens per chunk: {summary['total_tokens'] // len(sorted_chunks):,}\n")

                # Save raw data for potential future analysis
                f.write("\n\nRaw Data:\n")
                f.write("---------\n")
                f.write(f"total_cost: {summary['total_cost']}\n")
                f.write(f"total_tokens: {summary['total_tokens']}\n")
                f.write(f"total_prompt_tokens: {summary.get('total_prompt_tokens', 0)}\n")
                f.write(f"total_completion_tokens: {summary.get('total_completion_tokens', 0)}\n")
                f.write(f"request_count: {translator.request_count}\n")

        except (OSError, PermissionError) as e:
            if tolog is not None:
                tolog.error(f"Error saving cost log to {cost_log_path}: {e}")
            raise
        tolog.info(f"Cost log saved to {cost_log_path}")
    # EPUB generation removed - this is handled by enchant_cli.py orchestrator
    # The create_epub parameter is kept for backward compatibility but ignored


###############################################
#               MAIN FUNCTION               #
###############################################


def load_safe_yaml(path: Path) -> dict[str, Any] | None:
    """Safely load YAML file - wrapper for common utility with exception handling"""
    try:
        return load_yaml_safe(path)
    except ValueError as e:
        if tolog is not None:
            tolog.error(f"Error loading YAML from {path}: {e}")
        return None
    except Exception as e:
        if tolog is not None:
            tolog.error(f"Unexpected error loading YAML from {path}: {e}")
        return None


def process_batch(args: Any) -> None:
    """Process batch of novel files"""
    # Ensure logger is available
    global tolog
    if tolog is None:
        tolog = logging.getLogger(__name__)

    input_path = Path(args.filepath)
    if not input_path.exists() or not input_path.is_dir():
        tolog.error("Batch processing requires an existing directory path.")
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

        MAX_RETRIES = 3

        # Process files
        for item in progress["files"]:
            if item["status"] == "completed":
                continue
            if item.get("retry_count", 0) >= MAX_RETRIES:
                tolog.warning(f"Skipping {item['path']} after {MAX_RETRIES} failed attempts.")
                item["status"] = "failed/skipped"
                continue

            item["status"] = "processing"
            item["start_time"] = dt.datetime.now().isoformat()
            try:
                with progress_file.open("w") as f:
                    yaml.safe_dump(progress, f)
            except (OSError, yaml.YAMLError) as e:
                if tolog is not None:
                    tolog.error(f"Error saving progress file: {e}")
                raise

            try:
                tolog.info(f"Processing: {Path(item['path']).name}")
                book_id = import_book_from_txt(item["path"], encoding=args.encoding, max_chars=args.max_chars)
                save_translated_book(book_id, resume=args.resume, create_epub=args.epub)
                item["status"] = "completed"
            except Exception as e:
                tolog.error(f"Failed to translate {item['path']}: {str(e)}")
                item["status"] = "failed/skipped"
                item["error"] = str(e)
                item["retry_count"] = item.get("retry_count", 0) + 1
            finally:
                item["end_time"] = dt.datetime.now().isoformat()
                try:
                    with progress_file.open("w") as f:
                        yaml.safe_dump(progress, f)
                except (OSError, yaml.YAMLError) as e:
                    if tolog is not None:
                        tolog.error(f"Error saving progress file in finally block: {e}")
                    # Don't re-raise in finally block to avoid masking original exception

                # Move completed batch to history
                if all(file["status"] in ("completed", "failed/skipped") for file in progress["files"]):
                    try:
                        with history_file.open("a", encoding="utf-8") as f:
                            f.write("---\n")
                            yaml.safe_dump(progress, f, allow_unicode=True)
                    except (OSError, yaml.YAMLError) as e:
                        if tolog is not None:
                            tolog.error(f"Error writing to history file: {e}")
                        # Continue anyway - don't fail the whole batch for history logging

                    try:
                        progress_file.unlink()
                    except (FileNotFoundError, PermissionError) as e:
                        if tolog is not None:
                            tolog.error(f"Error deleting progress file: {e}")
                        # Continue anyway - file will be overwritten next time

    # Save batch cost summary for remote translations
    global translator
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
            if tolog is not None:
                tolog.error(f"Error saving batch cost log to {batch_cost_log_path}: {e}")
            # Don't re-raise, just log the error
        else:
            tolog.info(f"Batch cost summary saved to {batch_cost_log_path}")


def translate_novel(
    file_path: str,
    encoding: str = "utf-8",
    max_chars: int = 12000,
    resume: bool = False,
    create_epub: bool = False,
    remote: bool = False,
) -> bool:
    """
    Translate a Chinese novel to English.

    Args:
        file_path: Path to the Chinese novel text file
        encoding: File encoding (default: utf-8)
        max_chars: Maximum characters per translation chunk (default: 12000)
        resume: Resume interrupted translation
        create_epub: (Deprecated) Kept for backward compatibility, ignored.
                     EPUB generation is handled by enchant_cli.py orchestrator
        remote: Use remote API instead of local

    Returns:
        bool: True if translation completed successfully, False otherwise
    """
    global tolog, translator, _module_config

    # Load configuration
    try:
        config_manager = ConfigManager(config_path=Path("enchant_config.yml"))
        config = config_manager.config
        # Store config globally for use by other functions
        _module_config = config
    except ValueError as e:
        # tolog hasn't been initialized yet, use print for error
        print(f"Configuration error: {e}")
        return False

    # Set up logging based on config
    log_level = getattr(logging, config["logging"]["level"], logging.INFO)
    log_format = config["logging"]["format"]

    logging.basicConfig(level=log_level, format=log_format)
    tolog = logging.getLogger(__name__)

    # Set up file logging if enabled
    if config["logging"]["file_enabled"]:
        try:
            file_handler = logging.FileHandler(config["logging"]["file_path"])
            file_handler.setLevel(log_level)
            file_handler.setFormatter(logging.Formatter(log_format))
            tolog.addHandler(file_handler)
        except (OSError, PermissionError) as e:
            tolog.error(f"Failed to set up file logging to {config['logging']['file_path']}: {e}")
            # Continue without file logging

    # Initialize global services
    global icloud_sync, MAXCHARS
    icloud_sync = ICloudSync(enabled=config["icloud"]["enabled"])
    # Cost tracking is now handled by global_cost_tracker

    # Update MAXCHARS from config
    MAXCHARS = config["text_processing"]["max_chars_per_chunk"]

    # Warn if colorama is missing
    if cr is None:
        tolog.warning("colorama package not installed. Colored text may not work properly.")

    # Set up signal handling for graceful termination
    def signal_handler(sig: int, frame: Any) -> None:
        tolog.info("Interrupt received. Exiting gracefully.")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    # Use the provided parameters
    use_remote = remote

    # Initialize translator with configuration
    global translator
    if use_remote:
        # Get API key from config or environment
        api_key = config_manager.get_api_key("openrouter")
        if not api_key:
            tolog.error("OpenRouter API key required. Set OPENROUTER_API_KEY or configure in enchant_config.yml")
            sys.exit(1)

        translator = ChineseAITranslator(
            logger=tolog,
            use_remote=True,
            api_key=api_key,
            endpoint=config["translation"]["remote"]["endpoint"],
            model=config["translation"]["remote"]["model"],
            temperature=config["translation"]["temperature"],
            max_tokens=config["translation"]["max_tokens"],
            timeout=config["translation"]["remote"]["timeout"],
        )
    else:
        translator = ChineseAITranslator(
            logger=tolog,
            use_remote=False,
            endpoint=config["translation"]["local"]["endpoint"],
            model=config["translation"]["local"]["model"],
            temperature=config["translation"]["temperature"],
            max_tokens=config["translation"]["max_tokens"],
            timeout=config["translation"]["local"]["timeout"],
        )

    # Note: batch processing is handled by the orchestrator, not here

    tolog.info(f"Starting book import for file: {file_path}")

    try:
        # Call the import_book_from_txt function to process the text file
        new_book_id = import_book_from_txt(file_path, encoding=encoding, max_chars=max_chars)
        tolog.info(f"Book imported successfully. Book ID: {new_book_id}")
        safe_print(f"[bold green]Book imported successfully. Book ID: {new_book_id}[/bold green]")
    except Exception:
        tolog.exception("An error occurred during book import.")
        return False

    # Save the translated book after import
    try:
        save_translated_book(new_book_id, resume=resume, create_epub=create_epub)
        tolog.info("Translated book saved successfully.")
        safe_print("[bold green]Translated book saved successfully.[/bold green]")

        # Log cost summary (don't print to console when called from orchestrator)
        if use_remote and translator:
            cost_summary = translator.format_cost_summary()
            tolog.info("Cost Summary:\n" + cost_summary)
        elif config["pricing"]["enabled"]:
            # Cost tracking is now handled by global_cost_tracker
            summary = global_cost_tracker.get_summary()
            tolog.info(f"Cost Summary: Total cost: ${summary['total_cost']:.6f}, Total requests: {summary['request_count']}")

        return True
    except Exception:
        tolog.exception("Error saving translated book.")
        return False


# This module is now a library only - use enchant_cli.py for command line interface
