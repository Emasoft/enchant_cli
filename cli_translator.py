#!/usr/bin/env python3
# -*- coding: utf-8 -*-
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

import builtins
import sys
import re

APP_NAME = "cli-translator"
APP_VERSION = "0.1.0"  # Semantic version (major.minor.patch)
MIN_PYTHON_VERSION_REQUIRED = "3.8"

# Fallback to standard print if rich isn't available
try:
    from rich import print
except ImportError:
    # Use standard print if rich isn't available
    print = builtins.print
    # Set flag to indicate rich is not available
    rich_available = False
else:
    rich_available = True

def safe_print(*args, **kwargs) -> None:
    """Print with rich if available, else strip markup tags"""
    if rich_available:
        print(*args, **kwargs)
    else:
        # Strip rich markup tags for plain text output
        text = " ".join(str(arg) for arg in args)
        clean_text = re.sub(r'\[/?[^]]+\]', '', text)
        builtins.print(clean_text)

try:
    import colorama as cr
except ImportError:
    cr = None
    # tolog is not yet defined here, so we will log warning later in main if needed

from rich.text import Text

import os
import logging
import signal
import threading
import time

from functools import partial
from pathlib import Path 
from datetime import datetime
from threading import Event
from time import sleep
import uuid
from uuid import UUID
from concurrent.futures import ThreadPoolExecutor
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from translation_service import ChineseAITranslator

import rich
import rich.repr
import enum

import codecs
from chardet.universaldetector import UniversalDetector

from typing import (
    TYPE_CHECKING,
    ClassVar,
    Optional,
    List,
    Dict,
    Any,
    Union,
    Tuple,
    Set,
)
import html
# EPUB imports removed - EPUB generation is handled by enchant_cli.py orchestrator

import errno
import yaml
import datetime as dt
import unicodedata
import filelock

# Import new modules for enhanced functionality
from icloud_sync import ICloudSync, ensure_synced, prepare_for_write
from config_manager import ConfigManager, get_config
# Note: model_pricing module is deprecated - using global_cost_tracker instead

# Import common text processing utilities
from common_text_utils import (
    clean, replace_repeated_chars, limit_repeated_chars,
    extract_code_blocks, extract_inline_code, remove_html_comments,
    remove_script_and_style, replace_block_tags, remove_remaining_tags,
    unescape_non_code_with_placeholders, remove_html_markup, clean_adverts,
    CHINESE_PUNCTUATION, ENGLISH_PUNCTUATION, ALL_PUNCTUATION
)

# Global variables - will be initialized in main()
translator = None
tolog = None
icloud_sync = None
_module_config = None
# Cost tracking is now handled by global_cost_tracker from cost_tracker module

MAXCHARS = 11999  # Default value, will be updated from config in main()

# Chunk retry constants
DEFAULT_MAX_CHUNK_RETRIES = 10
MAX_RETRY_WAIT_SECONDS = 60 


# CHINESE PUNCTUATION sets.
SENTENCE_ENDING = {'。', '！', '？', '…', '.', ';', '；'}
CLOSING_QUOTES = {'」', '”', '】', '》'}
NON_BREAKING = {'，', '、', '°', }
# Note: ALL_PUNCTUATION, CHINESE_PUNCTUATION, and ENGLISH_PUNCTUATION are imported from common_text_utils


# PARAGRAPH DELIMITERS (characters that denote new paragraphs)
PARAGRAPH_DELIMITERS = {
    "\n", "\v", "\f", "\x1c", "\x1d", "\x1e", "\x85", "\u2028", "\u2029"
}

# Characters that are allowed unlimited repetition by default.
# These include whitespace, control characters, some punctuation, symbols, and paragraph delimiters.
PRESERVE_UNLIMITED = {
    ' ', '.', '\n', '\r', '\t', '(', ')', '[', ']',
    '+', '-', '_', '=', '/', '|', '\\', '*', '%', '#', '@',
    '~', '<', '>', '^', '&', '°', '…',
    '—', '•', '$'
}.union(PARAGRAPH_DELIMITERS)

# Precompile the regular expression pattern for matching repeated characters.
_repeated_chars = re.compile(r'(.)\1+')

def sanitize_filename(filename: str) -> str:
    """
    Sanitize filenames by:
    1. Removing illegal characters
    2. Replacing sequences of repeated unsafe characters
    3. Limiting length to 100 characters
    """
    # Remove problematic characters
    filename = re.sub(r'[\\/*?:"<>|]', "", filename)
    
    # Replace repeated characters that could cause filesystem issues
    unsafe_chars = {'-', '_', '.', ' '}
    for char in unsafe_chars:
        pattern = re.escape(char) + r'{2,}'
        filename = re.sub(pattern, char, filename)
    
    # Trim excess whitespace and limit length
    filename = re.sub(r'\s+', ' ', filename).strip()
    return filename[:100]

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
    

def load_text_file(txt_file_name: Union[str, Path]) -> Optional[str]:
        contents = None
        txt_file_name = Path.joinpath(Path.cwd(), Path(txt_file_name))
        if Path.is_file(txt_file_name):
                try:
                    with open(txt_file_name, encoding='utf8') as f:
                            contents = f.read()
                            if tolog is not None:
                                tolog.debug(contents)
                    return contents
                except (IOError, OSError, PermissionError) as e:
                    if tolog is not None:
                        tolog.error(f"Error reading file {txt_file_name}: {e}")
                    return None
        else:
                if tolog is not None:
                    tolog.debug("Error : "+str(txt_file_name)+" is not a valid file!")
                return None

def save_text_file(text: str, filename: Union[str, Path]) -> None:
        file_path = Path(Path.joinpath(Path.cwd(), Path(filename)))
        try:
            with open(file_path, "wt", encoding="utf-8") as f:
                    f.write(clean(text))
            if tolog is not None:
                tolog.debug("Saved text file in: "+str(file_path))
        except (IOError, OSError, PermissionError) as e:
            if tolog is not None:
                tolog.error(f"Error saving file {file_path}: {e}")
            raise
        

def remove_excess_empty_lines(txt: str) -> str:
    """Reduce consecutive empty lines to a maximum of 3 (4 newlines)."""
    # Match 4 or more newline characters and replace with exactly 3 newlines
    return re.sub(r'\n{4,}', '\n\n\n', txt)

def normalize_spaces(text: str) -> str:
    # Split the text into lines
    lines = text.split('\n')
    normalized_lines = []
    
    for line in lines:
        # Strip leading/trailing whitespace from the line
        stripped_line = line.strip()
        
        if stripped_line:  # If the line is not empty (contains actual content)
            # Replace multiple spaces with a single space
            normalized_line = ' '.join(stripped_line.split())
            normalized_lines.append(normalized_line)
        else:
            # For empty lines, add only a newline (no spaces)
            normalized_lines.append('')
    
    # Join lines back with newlines
    return '\n'.join(normalized_lines)
    
        
# HELPER FUNCTION TO GET VALUE OR NONE FROM A LIST ENTRY
# an equivalent of dict.get(key, default) for lists
def get_val(myList: List[Any], idx: int, default: Any = None) -> Any:
    try:
        return myList[idx]
    except IndexError:
        return default
            
        
_email_re = re.compile(r"[a-zA-Z0-9_\.\+\-]+\@[a-zA-Z0-9_\.\-]+\.[a-zA-Z]+")
_url_re = re.compile(r"https?://(-\.)?([^\s/?\.#]+\.?)+(/[^\s]*)?")

def strip_urls(input_text: str) -> str:
    """Strip URLs and emails from a string"""
    input_text = _url_re.sub("", input_text)
    input_text = _email_re.sub("", input_text)
    return input_text

_markdown_re = re.compile(r".*("
                          r"\*(.*)\*|"
                          r"_(.*)_|"
                          r"\[(.*)\]\((.*)\)|"
                          r"`(.*)`|"
                          r"```(.*)```"
                          r").*")


def is_markdown(input_text: str) -> bool:
    """Check if a string is actually markdown"""
    #input_text = input_text[:1000]  # check only first 1000 chars
    # Don't mark part of URLs or email addresses as Markdown
    input_text = strip_urls(input_text)
    return bool(_markdown_re.match(input_text.replace("\n", "")))

    
    
def decode_input_file_content(input_file: Path) -> str:
    # Ensure file is synced from iCloud if needed
    input_file = ensure_synced(input_file)
    
    encoding = detect_file_encoding(input_file)
    if tolog is not None:
        tolog.debug(f"\nDetected encoding: {encoding}")
    
    try:
        with codecs.open(input_file, 'r', encoding=encoding) as f:
            content = f.read()
    except Exception as e:
        if tolog is not None:
            tolog.debug(f"\nAn error occurred processing file '{str(input_file)}': {e}")
            tolog.debug("Defaulting to GB18030 encoding.")
        encoding = 'GB18030'
        try:
            with codecs.open(input_file, 'r', encoding=encoding) as f:
                content = f.read()
        except Exception as e:
            if tolog is not None:
                tolog.debug(f"\nAn error occurred processing file '{str(input_file)}': {e}")
                tolog.debug("Attempt to decode using the detected encoding, replacing errors with the error character.")
            with open(input_file, 'rb') as file:
                content_bytes = file.read()
                # Attempt to decode using the detected encoding, replacing errors with the error character
                content = content_bytes.decode(encoding, errors='replace')
            
    return content
    
    
# try to detect the encoding of chinese text files 
def detect_file_encoding(file_path: Path) -> str:
    # Ensure file is synced from iCloud if needed
    file_path = ensure_synced(file_path)
    
    detector = UniversalDetector()
    try:
        with file_path.open('rb') as f:
            for line in f:
                detector.feed(line)
                if detector.done:
                    break
            detector.close()
            return detector.result['encoding']
    except (IOError, OSError, PermissionError) as e:
        if tolog is not None:
            tolog.error(f"Error detecting encoding for {file_path}: {e}")
        # Default to UTF-8 if detection fails
        return 'utf-8'
        
        
        
    

# Function to extract title and author info from foreign novels filenames (chinese, japanese, etc.)
def foreign_book_title_splitter(filename: Union[str, Path]) -> Tuple[str, str, str, str, str, str]:
    # FILE NAME STRUCTURE - SPLIT THE STRING TO EXTRACT THE INFORMATIONS ABOUT TITLE AND AUTUOR NAMES
    # EXAMPLE:
    # translated_title by translated_author - original_title by original_author.txt
    # 
    
    # Get the parts into variables and return them
    original_title = ' n.d. '
    translated_title = ' n.d. '
    transliterated_title = ' n.d. '
    original_author = ' n.d. '
    translated_author = ' n.d. '
    transliterated_author = ' n.d. '
    
    # Remove the extension
    base_filename = Path(filename).stem
    # Split the main string sections
    if ' - ' in base_filename:
        translated_part, original_part = base_filename.split(' - ')
    else:
        if ' by ' in base_filename:
            original_title, original_author = base_filename.split(' by ')
        else:
            original_title = base_filename
        translated_part = ''
        original_part = base_filename
    # Extract translated title and author
    if translated_part and ' by ' in translated_part:
        translated_title, translated_author = translated_part.split(' by ')
    else:
        translated_title = translated_part
    # Extract original title and author
    if original_part and ' by ' in original_part:
        original_title, original_author = original_part.split(' by ')
    else:
        original_title = original_part

    return original_title, translated_title, transliterated_title, original_author, translated_author, transliterated_author


def split_chinese_text_using_split_points(book_content: str, max_chars: int = MAXCHARS) -> List[str]:
    # SPLIT POINT METHOD
    # Compute split points based on max_chars and chapter patterns
    chapter_pattern = r'第\d+章'  # pattern to split at Chapter title/number line
    total_book_characters = len(book_content)
    split_points_list = []
    counter_chars = 0
    # Ensure pattern_length is at least 0
    pattern_length = max(0, len(chapter_pattern) - 2)  # accounting for the regex special characters
    i = 0
    while i < total_book_characters:
        counter_chars += 1
        if counter_chars > max_chars:
            split_points_list.append(i)
            counter_chars = 0
        elif book_content[i:i+pattern_length] == chapter_pattern:
            split_points_list.append(i)
            counter_chars = 0
        i += 1

    # Split book content at computed split points
    splitted_chapters = [book_content[i:j] for i, j in zip([0]+split_points_list, split_points_list+[None])]
    
    return splitted_chapters


# NOTE: If a chapter/chunk go over the characters limit of max_char, 
# then the chapter is split anyway without waiting for
# the chapter title pattern.
def import_book_from_txt(file_path: Union[str, Path], encoding: str = 'utf-8', chapter_pattern: str = r'Chapter \d+', max_chars: int = MAXCHARS, split_mode: str = 'PARAGRAPHS', split_method: str = 'paragraph') -> str:
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
    #book_content = remove_html_markup(book_content)
    #book_content = normalize_spaces(book_content)
    book_content = remove_excess_empty_lines(book_content)
    
    # COUNT THE NUMBER OF CHARACTERS
    total_book_characters = len(book_content)

    
    # SPLIT THE BOOK IN CHUNKS
    if split_mode == "SPLIT_POINTS":
        splitted_chapters = split_chinese_text_using_split_points(book_content, max_chars)
    elif split_mode == "PARAGRAPHS":
        splitted_chapters = split_chinese_text_in_parts(book_content, max_chars, split_method)
    else:
        # default use split_mode = 'PARAGRAPHS'
        splitted_chapters = split_chinese_text_in_parts(book_content, max_chars, split_method)
        
    # Create new book entry in database
    new_book_id = str(uuid.uuid4())
    original_title, translated_title, transliterated_title, original_author, translated_author, transliterated_author = foreign_book_title_splitter(file_path)
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
            total_characters = total_book_characters,
            )
    except Exception as e:
        if tolog is not None:
            tolog.debug("An exception happened when creating a new variation original for a chapter:")
            tolog.debug("ERROR: "+ str(e))
    finally:
        manual_commit()            
    
    book = Book.get_by_id(new_book_id)
    
    # for each chapter create a new chapter entry and a new orig variation in database
    for index, chapter_content in enumerate(splitted_chapters, start=1):
        new_chapter_id = str(uuid.uuid4())
        new_variation_id = str(uuid.uuid4())
        try:
            Chapter.create(chapter_id=new_chapter_id, book_id=new_book_id, chapter_number=index, original_variation_id=new_variation_id)
        except Exception as e:
            if tolog is not None:
                tolog.debug(f"An exception happened when creating chapter n.{index} with ID {new_variation_id}. ")
                tolog.debug("ERROR: "+ str(e))
        else:
            try:
                Variation.create(
                    variation_id=new_variation_id,
                    book_id=new_book_id,
                    chapter_id=new_chapter_id,
                    chapter_number=index,
                    language="original",
                    category="original",
                    text_content=chapter_content
                )
            except Exception as e:
                chapter_number = index if 'index' in locals() else 'unknown'
                if tolog is not None:
                    tolog.debug(f"An exception happened when creating a new variation original for chapter n.{chapter_number}:")
                    tolog.debug("ERROR: "+ str(e))
        finally:
            manual_commit() 
            
    return new_book_id


def quick_replace(text_content: str, original: str, substitution: str, case_insensitive=True) -> str:
    # case insensitive substitution or not
    if case_insensitive:
        return re.sub("(?i)" + re.escape(original), lambda m: f"{substitution}", text_content)
    else:
        return re.sub(re.escape(original), lambda m: f"{substitution}", text_content)
    
    
def flush_buffer(buffer: str, paragraphs: list) -> str:
    """
    If the buffer contains text, normalize spaces and append it as a new paragraph.
    Returns an empty string to reset the buffer.
    """
    buffer = clean(buffer)
    if buffer:
        buffer = re.sub(' +', ' ', buffer)
        paragraphs.append(buffer + "\n\n")
    return ""

def split_on_punctuation_contextual(text: str) -> list:
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
    SENTENCE_ENDING = {'。', '！', '？', '…', '.', ';', '；'}
    CLOSING_QUOTES = {'」', '”', '】', '》'}
    NON_BREAKING = {'，', '、'}
    # Use the imported ALL_PUNCTUATION from common_text_utils instead of redefining

    # Define a comprehensive set of paragraph delimiters.
    PARAGRAPH_DELIMITERS = {
        "\n",      # Line Feed
        "\v",      # Vertical Tab
        "\f",      # Form Feed
        "\x1c",    # File Separator
        "\x1d",    # Group Separator
        "\x1e",    # Record Separator
        "\x85",    # Next Line (C1 Control Code)
        "\u2028",  # Line Separator
        "\u2029"   # Paragraph Separator
    }
    
    # Define characters that trigger a new paragraph when following punctuation.
    PARAGRAPH_START_TRIGGERS = {'\n', '“', '【', '《', '「'}

    # Preprocess text:
    # 1. Clean and normalize newlines.
    # 2. Remove extra spaces.
    # 3. Replace repeated punctuation and delimiter characters.
    text = clean_adverts(text)
    text = clean(text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(' +', ' ', text)
    text = replace_repeated_chars(text, ALL_PUNCTUATION)
    text = replace_repeated_chars(text, PARAGRAPH_DELIMITERS)
    
    paragraphs = []
    buffer = ""
    length = len(text)
    i = 0
    while i < length:
        char = text[i]
        next_char = text[i+1] if i+1 < length else None
        next_next_char = text[i+2] if i+2 < length else None
        
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
            if (next_char in PARAGRAPH_START_TRIGGERS) or (next_char == ' ' and next_next_char in PARAGRAPH_START_TRIGGERS):
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
                if (next_char in PARAGRAPH_START_TRIGGERS) or (next_char == ' ' and next_next_char in PARAGRAPH_START_TRIGGERS):
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
        paragraphs.append(re.sub(' +', ' ', clean(buffer)) + "\n\n")
    
    return paragraphs


def split_text_by_actual_paragraphs(text: str) -> list:
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
    text = text.replace("\u2028", "\n")    # Line Separator
    
    # Split on double newlines
    raw_paragraphs = re.split(r'\n\s*\n', text)
    
    paragraphs = []
    for para in raw_paragraphs:
        para = para.strip()
        if para:
            # Clean up extra spaces
            para = re.sub(' +', ' ', para)
            # Add back the double newline for consistency
            paragraphs.append(para + "\n\n")
    
    return paragraphs
    
    
    
## Function to split a chinese novel in parts of max n characters keeping the paragraphs intact
def split_chinese_text_in_parts(text: str, max_chars: int = MAXCHARS, split_method: str = 'paragraph') -> List[str]:
    # Choose splitting method based on parameter
    if split_method == 'punctuation':
        # Use legacy punctuation-based splitting
        paragraphs = split_on_punctuation_contextual(text)
    else:
        # Use the new function that splits on actual paragraph breaks
        paragraphs = split_text_by_actual_paragraphs(text)
    chapters = list()
    chapters_counter = 1
    current_char_count = 0
    paragraphs_buffer = []
    paragraph_index = 0
    total_chars = sum(len(para) for para in paragraphs)
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
                chapter = "".join(paragraphs_buffer)
                chapters.append(chapter)
                chapters_counter += 1
                current_char_count = 0
                paragraphs_buffer = []
        
        paragraphs_buffer.append(para)
        chars_processed += len(para)
        current_char_count += len(para)

    # IF THE PARAGRAPH BUFFER STILL CONTAINS SOME PARAGRAPHS
    # THEN SAVE THE RESIDUAL PARAGRAPHS IN A FINAL FILE.
    if paragraphs_buffer:
        paragraph_index += len(paragraphs_buffer)
        chapter = "".join(paragraphs_buffer)
        chapters.append(chapter)
        chapters_counter += 1
                
    if tolog is not None:
        tolog.debug(f"\n -> Import COMPLETE.\n  Total number of paragraphs: {str(paragraph_index)}\n  Total number of chapters: {str(chapters_counter)}\n")
    
    return chapters

# Main function is at the end of this file

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

    @classmethod
    def create(cls, chapter_id, book_id, chapter_number, original_variation_id):
        chapter = cls(chapter_id, book_id, chapter_number, original_variation_id)
        CHAPTER_DB[chapter_id] = chapter
        # Also add the chapter to the corresponding Book's chapters list
        book = Book.get_by_id(book_id)
        if book:
            book.chapters.append(chapter)
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
        return variation

def manual_commit() -> None:
    # Simulate a database commit. In this simple implementation, changes are already in memory.
    # tolog.debug("Manual commit executed.")
    pass


def format_chunk_error_message(chunk_number: int, max_retries: int, last_error: str, 
                              book_title: str, book_author: str, output_path: str) -> str:
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
    # Get max chunk retry attempts from config or use default
    max_chunk_retries = DEFAULT_MAX_CHUNK_RETRIES
    if _module_config:
        max_chunk_retries = _module_config.get('translation', {}).get('max_chunk_retries', DEFAULT_MAX_CHUNK_RETRIES)
    
    book = Book.get_by_id(book_id)
    if not book:
        raise ValueError("Book not found")
    # Create book folder
    try:
        folder_name = sanitize_filename(f"{book.translated_title} by {book.translated_author}")
        book_dir = Path(folder_name)
        book_dir.mkdir(exist_ok=True)
    except OSError as e:
        if e.errno != errno.EEXIST:
            tolog.error(f"Error creating directory: {e}")
            book_dir = Path.cwd()
    
    # Prepare autoresume data
    existing_chunk_nums: Set[int] = set()
    if resume:
        pattern = f"{book.translated_title} by {book.translated_author} - Chunk_*.txt"
        for p in sorted(book_dir.glob(pattern), key=lambda x: x.name):
            match = re.search(r"Chunk_(\d{6})\.txt$", p.name)
            if match:
                existing_chunk_nums.add(int(match.group(1)))
        if existing_chunk_nums:
            tolog.info(f"Autoresume active: existing translated chunks detected: {sorted(existing_chunk_nums)}")
        else:
            tolog.info("Autoresume active but no existing chapter files found.")

    translated_contents = []
    # Sort chapters by chapter_number
    sorted_chapters = sorted(book.chapters, key=lambda ch: ch.chapter_number)
    for chapter in sorted_chapters:
        # Retrieve the Variation corresponding to the original text
        variation = VARIATION_DB.get(chapter.original_variation_id)
        if variation:
            if resume and chapter.chapter_number in existing_chunk_nums:
                p_existing = book_dir / f"{book.translated_title} by {book.translated_author} - Chunk_{chapter.chapter_number:06d}.txt"
                try:
                    translated_text = p_existing.read_text(encoding="utf-8")
                    tolog.info(f"Skipping translation for chunk {chapter.chapter_number}; using existing translation.")
                except FileNotFoundError:
                    tolog.warning(f"Expected file {p_existing.name} not found; re-translating.")
                else:
                    translated_contents.append(f"\n{translated_text}\n")
                    continue
            original_text = variation.text_content
            
            # Use the max_chunk_retries loaded above
            chunk_translated = False
            last_error = None
            output_filename_chapter = book_dir / f"{book.translated_title} by {book.translated_author} - Chunk_{chapter.chapter_number:06d}.txt"
            
            for chunk_attempt in range(1, max_chunk_retries + 1):
                try:
                    tolog.info(f"TRANSLATING CHUNK {chapter.chapter_number:06d} of {len(sorted_chapters)} (Attempt {chunk_attempt}/{max_chunk_retries})")
                    is_last_chunk = (chapter.chapter_number == len(sorted_chapters))
                    translated_text = translator.translate(original_text, is_last_chunk)
                    
                    # Validate translated text
                    if not translated_text or len(translated_text.strip()) == 0:
                        raise ValueError("Translation returned empty or whitespace-only text")
                    
                    # Save chunk to file
                    p = output_filename_chapter
                    try:
                        p.write_text(translated_text)
                    except (IOError, OSError, PermissionError) as e:
                        if tolog is not None:
                            tolog.error(f"Error saving chunk {chapter.chapter_number:06d} to {p}: {e}")
                        raise
                    
                    # Success! Mark as translated and break out of retry loop
                    chunk_translated = True
                    tolog.info(f"Successfully translated chunk {chapter.chapter_number:06d} on attempt {chunk_attempt}")
                    break
                    
                except Exception as e:
                    last_error = e
                    tolog.error(f"ERROR: Translation failed for chunk {chapter.chapter_number:06d} on attempt {chunk_attempt}/{max_chunk_retries}: {str(e)}")
                    
                    if chunk_attempt < max_chunk_retries:
                        # Calculate wait time with exponential backoff
                        wait_time = min(2 ** chunk_attempt, MAX_RETRY_WAIT_SECONDS)
                        tolog.info(f"Waiting {wait_time} seconds before retry...")
                        time.sleep(wait_time)
            
            # Check if translation succeeded after all attempts
            if not chunk_translated:
                # All attempts failed - exit with error
                error_message = format_chunk_error_message(
                    chunk_number=chapter.chapter_number,
                    max_retries=max_chunk_retries,
                    last_error=str(last_error),
                    book_title=book.translated_title,
                    book_author=book.translated_author,
                    output_path=str(output_filename_chapter)
                )
                tolog.error(error_message)
                print(error_message)
                sys.exit(1)
            else:
                # Translation succeeded - log and append to contents
                tolog.info(f"\nChunk {chapter.chapter_number:06d}:\n{translated_text}\n\n")
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
    except (IOError, OSError, PermissionError) as e:
        if tolog is not None:
            tolog.error(f"Error saving translated book to {output_filename}: {e}")
        raise
    
    # Save cost log for remote translations
    if translator and translator.is_remote and translator.request_count > 0:
        cost_log_filename = output_filename.with_suffix('').name + "_AI_COSTS.log"
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
                f.write(f"Total Chunks Translated: {len(sorted_chapters)}\n")
                if translator.request_count > 0 and len(sorted_chapters) > 0:
                    f.write(f"Average Cost per Chapter: ${translator.total_cost / len(sorted_chapters):.6f}\n")
                    f.write(f"Average Tokens per Chapter: {translator.total_tokens // len(sorted_chapters):,}\n")
        
                # Save raw data for potential future analysis
                f.write("\n\nRaw Data:\n")
                f.write("---------\n")
                f.write(f"total_cost: {translator.total_cost}\n")
                f.write(f"total_tokens: {translator.total_tokens}\n")
                f.write(f"total_prompt_tokens: {translator.total_prompt_tokens}\n")
                f.write(f"total_completion_tokens: {translator.total_completion_tokens}\n")
                f.write(f"request_count: {translator.request_count}\n")
            
        except (IOError, OSError, PermissionError) as e:
            if tolog is not None:
                tolog.error(f"Error saving cost log to {cost_log_path}: {e}")
            raise
        tolog.info(f"Cost log saved to {cost_log_path}")
    # EPUB generation removed - this is handled by enchant_cli.py orchestrator
    # The create_epub parameter is kept for backward compatibility but ignored

###############################################
#               MAIN FUNCTION               #
###############################################

def load_safe_yaml(path: Path) -> Optional[Dict[str, Any]]:
    """Safely load YAML file"""
    try:
        if path.exists():
            with path.open('r') as f:
                return yaml.safe_load(f)
        return None
    except Exception as e:
        if tolog is not None:
            tolog.error(f"Error loading YAML from {path}: {e}")
        return None

def process_batch(args) -> None:
    """Process batch of novel files"""
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
                'created': dt.datetime.now().isoformat(),
                'input_folder': str(input_path.resolve()),
                'files': []
            }

        # Populate file list if not resuming
        if not progress.get('files'):
            files_sorted = sorted(input_path.glob('*.txt'), key=lambda x: x.name)
            for file in files_sorted:
                progress['files'].append({
                    'path': str(file.resolve()),
                    'status': 'planned',
                    'end_time': None,
                    'retry_count': 0
                })

        MAX_RETRIES = 3

        # Process files
        for item in progress['files']:
            if item['status'] == 'completed':
                continue
            if item.get('retry_count', 0) >= MAX_RETRIES:
                tolog.warning(f"Skipping {item['path']} after {MAX_RETRIES} failed attempts.")
                item['status'] = 'failed/skipped'
                continue
                
            item['status'] = 'processing'
            item['start_time'] = dt.datetime.now().isoformat()
            try:
                with progress_file.open('w') as f:
                    yaml.safe_dump(progress, f)
            except (IOError, OSError, yaml.YAMLError) as e:
                if tolog is not None:
                    tolog.error(f"Error saving progress file: {e}")
                raise

            try:
                tolog.info(f"Processing: {Path(item['path']).name}")
                book_id = import_book_from_txt(item['path'], 
                                     encoding=args.encoding,
                                     max_chars=args.max_chars, 
                                     split_mode=args.split_mode,
                                     split_method=args.split_method)
                save_translated_book(book_id, resume=args.resume, create_epub=args.epub)
                item['status'] = 'completed'
            except Exception as e:
                tolog.error(f"Failed to translate {item['path']}: {str(e)}")
                item['status'] = 'failed/skipped'
                item['error'] = str(e)
                item['retry_count'] = item.get('retry_count', 0) + 1
            finally:
                item['end_time'] = dt.datetime.now().isoformat()
                try:
                    with progress_file.open('w') as f:
                        yaml.safe_dump(progress, f)
                except (IOError, OSError, yaml.YAMLError) as e:
                    if tolog is not None:
                        tolog.error(f"Error saving progress file in finally block: {e}")
                    # Don't re-raise in finally block to avoid masking original exception
                
                # Move completed batch to history
                if all(file['status'] in ('completed', 'failed/skipped') 
                      for file in progress['files']):
                    try:
                        with history_file.open('a', encoding="utf-8") as f:
                            f.write("---\n")
                            yaml.safe_dump(progress, f, allow_unicode=True)
                    except (IOError, OSError, yaml.YAMLError) as e:
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
        
        completed_count = sum(1 for file in progress['files'] if file['status'] == 'completed')
        failed_count = sum(1 for file in progress['files'] if file['status'] == 'failed/skipped')
        
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
                for file in progress['files']:
                    filename = Path(file['path']).name
                    status = file['status']
                    f.write(f"- {filename}: {status}\n")
                    if 'error' in file:
                        f.write(f"  Error: {file['error']}\n")
                
                # Save raw data
                f.write("\n\nRaw Cost Data:\n")
                f.write("-------------\n")
                f.write(f"total_cost: {translator.total_cost}\n")
                f.write(f"total_tokens: {translator.total_tokens}\n")
                f.write(f"total_prompt_tokens: {translator.total_prompt_tokens}\n")
                f.write(f"total_completion_tokens: {translator.total_completion_tokens}\n")
                f.write(f"request_count: {translator.request_count}\n")
                if completed_count > 0:
                    f.write(f"average_cost_per_novel: ${translator.total_cost / completed_count:.6f}\n")
                    f.write(f"average_tokens_per_novel: {translator.total_tokens // completed_count:,}\n")
        except (IOError, OSError, PermissionError) as e:
            if tolog is not None:
                tolog.error(f"Error saving batch cost log to {batch_cost_log_path}: {e}")
            # Don't re-raise, just log the error
        else:
            tolog.info(f"Batch cost summary saved to {batch_cost_log_path}")

def translate_novel(file_path: str, encoding: str = 'utf-8', max_chars: int = 12000, 
                   split_mode: str = 'PARAGRAPHS', split_method: str = 'paragraph', 
                   resume: bool = False, create_epub: bool = False, remote: bool = False) -> bool:
    """
    Translate a Chinese novel to English.
    
    Args:
        file_path: Path to the Chinese novel text file
        encoding: File encoding (default: utf-8)
        max_chars: Maximum characters per translation chunk (default: 12000)
        split_mode: Text splitting mode (PARAGRAPHS or SPLIT_POINTS)
        split_method: Paragraph detection method (paragraph or punctuation)
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
        tolog.error(f"Configuration error: {e}")
        return False
    
    # Set up logging based on config
    log_level = getattr(logging, config['logging']['level'], logging.INFO)
    log_format = config['logging']['format']
    
    logging.basicConfig(
        level=log_level,
        format=log_format
    )
    tolog = logging.getLogger(__name__)
    
    # Set up file logging if enabled
    if config['logging']['file_enabled']:
        try:
            file_handler = logging.FileHandler(config['logging']['file_path'])
            file_handler.setLevel(log_level)
            file_handler.setFormatter(logging.Formatter(log_format))
            tolog.addHandler(file_handler)
        except (IOError, OSError, PermissionError) as e:
            tolog.error(f"Failed to set up file logging to {config['logging']['file_path']}: {e}")
            # Continue without file logging
    
    # Initialize global services
    global icloud_sync, MAXCHARS
    icloud_sync = ICloudSync(enabled=config['icloud']['enabled'])
    # Cost tracking is now handled by global_cost_tracker
    
    # Update MAXCHARS from config
    MAXCHARS = config['text_processing']['max_chars_per_chunk']
    
    # Warn if colorama is missing
    if cr is None:
        tolog.warning("colorama package not installed. Colored text may not work properly.")
    
    # Set up signal handling for graceful termination
    def signal_handler(sig, frame):
        tolog.info("Interrupt received. Exiting gracefully.")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    # Use the provided parameters
    use_remote = remote
    
    # Initialize translator with configuration
    global translator
    if use_remote:
        # Get API key from config or environment
        api_key = config_manager.get_api_key('openrouter')
        if not api_key:
            tolog.error("OpenRouter API key required. Set OPENROUTER_API_KEY or configure in enchant_config.yml")
            sys.exit(1)
        
        translator = ChineseAITranslator(
            logger=tolog,
            use_remote=True,
            api_key=api_key,
            endpoint=config['translation']['remote']['endpoint'],
            model=config['translation']['remote']['model'],
            temperature=config['translation']['temperature'],
            max_tokens=config['translation']['max_tokens'],
            timeout=config['translation']['remote']['timeout'],
            pricing_manager=None  # Deprecated - cost tracking handled by global_cost_tracker
        )
    else:
        translator = ChineseAITranslator(
            logger=tolog,
            use_remote=False,
            endpoint=config['translation']['local']['endpoint'],
            model=config['translation']['local']['model'],
            temperature=config['translation']['temperature'],
            max_tokens=config['translation']['max_tokens'],
            timeout=config['translation']['local']['timeout'],
            pricing_manager=None  # Deprecated - cost tracking handled by global_cost_tracker
        )
    
    # Note: batch processing is handled by the orchestrator, not here
    
    tolog.info(f"Starting book import for file: {file_path}")
    
    try:
        # Call the import_book_from_txt function to process the text file
        new_book_id = import_book_from_txt(file_path, encoding=encoding, max_chars=max_chars, split_mode=split_mode, split_method=split_method)
        tolog.info(f"Book imported successfully. Book ID: {new_book_id}")
        safe_print(f"[bold green]Book imported successfully. Book ID: {new_book_id}[/bold green]")
    except Exception as e:
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
        elif config['pricing']['enabled']:
            # Cost tracking is now handled by global_cost_tracker
            summary = global_cost_tracker.get_summary()
            tolog.info(f"Cost Summary: Total cost: ${summary['total_cost']:.6f}, Total requests: {summary['request_count']}")
        
        return True
    except Exception as e:
        tolog.exception("Error saving translated book.")
        return False

def main() -> None:
    """CLI entry point for backwards compatibility"""
    global tolog
    
    # Pre-parse to get config file path
    import argparse
    pre_parser = argparse.ArgumentParser(add_help=False)
    pre_parser.add_argument("--config", type=str, default="enchant_config.yml")
    pre_args, _ = pre_parser.parse_known_args()
    
    # Load configuration
    try:
        config_manager = ConfigManager(config_path=Path(pre_args.config))
        config = config_manager.config
    except ValueError as e:
        print(f"Configuration error: {e}")
        print("Please fix the configuration file or delete it to regenerate defaults.")
        sys.exit(1)
    
    # Set up logging based on config
    log_level = getattr(logging, config['logging']['level'], logging.INFO)
    log_format = config['logging']['format']
    
    logging.basicConfig(
        level=log_level,
        format=log_format
    )
    tolog = logging.getLogger(__name__)
    
    # Set up file logging if enabled
    if config['logging']['file_enabled']:
        try:
            file_handler = logging.FileHandler(config['logging']['file_path'])
            file_handler.setLevel(log_level)
            file_handler.setFormatter(logging.Formatter(log_format))
            tolog.addHandler(file_handler)
        except (IOError, OSError, PermissionError) as e:
            tolog.error(f"Failed to set up file logging to {config['logging']['file_path']}: {e}")
            # Continue without file logging
    
    # Initialize global services
    global icloud_sync, MAXCHARS
    icloud_sync = ICloudSync(enabled=config['icloud']['enabled'])
    # Cost tracking is now handled by global_cost_tracker
    
    # Update MAXCHARS from config
    MAXCHARS = config['text_processing']['max_chars_per_chunk']
    
    # Warn if colorama is missing
    if cr is None:
        tolog.warning("colorama package not installed. Colored text may not work properly.")
    
    # Set up signal handling for graceful termination
    def signal_handler(sig, frame):
        tolog.info("Interrupt received. Exiting gracefully.")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="CLI tool for translating Chinese novels to English using AI translation services",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
====================================================================================
USAGE EXAMPLES:
====================================================================================

  Single novel translation (new/replace):
    $ python cli_translator.py novel.txt
    $ python cli_translator.py "My Novel.txt" --encoding gb2312

  Single novel translation with resume:
    $ python cli_translator.py novel.txt --resume

  Batch translation of directory:
    $ python cli_translator.py novels_dir --batch
    $ python cli_translator.py novels_dir --batch --resume

  Remote translation (using OpenRouter):
    $ python cli_translator.py novel.txt --remote
    $ export OPENROUTER_API_KEY="your_key_here"

  Generate EPUB after translation:
    $ python cli_translator.py novel.txt --epub

====================================================================================
"""
    )
    parser.add_argument("filepath", type=str, 
                        help="Path to Chinese novel text file (single mode) or directory containing novels (batch mode)")
    
    parser.add_argument("--config", type=str, default="enchant_config.yml",
                        help="Path to configuration file (default: enchant_config.yml)")
    
    parser.add_argument("--encoding", type=str, default=config['text_processing']['default_encoding'], 
                        help=f"Character encoding of input files. Common: utf-8, gb2312, gb18030, big5 (default: {config['text_processing']['default_encoding']})")
    
    parser.add_argument("--max_chars", type=int, default=config['text_processing']['max_chars_per_chunk'], 
                        help=f"Maximum characters per translation chunk. Affects API usage and memory (default: {config['text_processing']['max_chars_per_chunk']})")
    
    parser.add_argument("--resume", action="store_true", 
                        help="Resume interrupted translation. Single: continues from last chapter. Batch: uses progress file")
    
    parser.add_argument("--epub", action="store_true", 
                        help="Generate EPUB file after translation completes. Creates formatted e-book with table of contents")
    
    parser.add_argument("--split_mode", type=str, 
                        choices=["PARAGRAPHS", "SPLIT_POINTS"], 
                        default=config['text_processing']['split_mode'], 
                        help=f"Text splitting mode. PARAGRAPHS: auto-split by paragraphs. SPLIT_POINTS: use markers in text (default: {config['text_processing']['split_mode']})")
    
    parser.add_argument("--batch", action="store_true", 
                        help="Batch mode: process all .txt files in the specified directory. Tracks progress automatically")
    
    parser.add_argument("--remote", action='store_true', 
                        help="Use remote OpenRouter API instead of local LM Studio. Requires OPENROUTER_API_KEY environment variable")
    
    parser.add_argument("--split-method", dest='split_method', 
                        choices=['punctuation', 'paragraph'], 
                        default=config['text_processing']['split_method'],
                        help=f"Paragraph detection method. 'paragraph': split on double newlines (recommended). 'punctuation': split on Chinese punctuation patterns (legacy) (default: {config['text_processing']['split_method']})")
    
    args = parser.parse_args()
    
    # Update config with command-line arguments
    config = config_manager.update_with_args(args)
    
    if args.batch:
        process_batch(args)
        return
    
    # Call the translate_novel function
    success = translate_novel(
        file_path=args.filepath,
        encoding=args.encoding,
        max_chars=args.max_chars,
        split_mode=args.split_mode,
        split_method=args.split_method,
        resume=args.resume,
        create_epub=args.epub,
        remote=args.remote
    )
    
    if success:
        safe_print("[bold green]Translation completed successfully![/bold green]")
    else:
        safe_print("[bold red]Translation failed. Check logs for details.[/bold red]")
        sys.exit(1)


# Entry point removed - use enchant_cli.py as the main entry point
