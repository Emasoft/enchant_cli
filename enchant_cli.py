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

APP_NAME = "EnChANT - English-Chinese Automatic Novel Translator"
APP_VERSION = "1.0.0"  # Semantic version (major.minor.patch)
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

def safe_print(*args, **kwargs):
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

# Only import rich components if rich is available
if rich_available:
    from rich.console import RenderableType
    from rich.table import Table
    from rich.text import Text
else:
    # Define dummy classes for when rich is not available
    RenderableType = None
    Table = None
    Text = None

import os
import logging
import asyncio
import queue
import signal
import threading
import time
import http

from functools import partial
from queue import Queue, Empty
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
from novel_renamer import process_novel_file
from epub_builder import build_epub_from_directory
from common_utils import sanitize_filename, extract_book_info_from_path

import enum

if rich_available:
    import rich
    import rich.repr

try:
    import multiexit
except ImportError:
    multiexit = None

import codecs
from chardet.universaldetector import UniversalDetector

from typing import (
    TYPE_CHECKING,
    ClassVar,
)
import html
try:
    from ebooklib import epub  # for EPUB generation
except ImportError:
    epub = None  # Will notify user if EPUB creation is requested without library

import errno
import yaml
import datetime as dt
import unicodedata
import filelock

# Global variables - will be initialized in main()
translator = None
tolog = None

MAXCHARS = 12000 # TODO: make this value configurable by the user 


# CHINESE PUNCTUATION sets.
SENTENCE_ENDING = {'。', '！', '？', '…', '.', ';', '；'}
CLOSING_QUOTES = {'」', '”', '】', '》'}
NON_BREAKING = {'，', '、', '°', }
ALL_PUNCTUATION = SENTENCE_ENDING | CLOSING_QUOTES | NON_BREAKING

# Define explicit sets for Chinese and English punctuation.
# Chinese punctuation includes full-width or ideographic punctuation.
CHINESE_PUNCTUATION = {'。', '！', '？', '…', '；', '，', '、', '」', '”', '】', '》'}
# English punctuation: common ASCII punctuation characters.
ENGLISH_PUNCTUATION = {'.', ',', '!', ';', ':', '’','‘','“','”',"'",'(',')','{','}','"','«','»','ー','︱','⁋','❝','❞','⁇','⁈','⁉︎','¿','?'}

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

def clean(text: str) -> str:
    """
    Clean the input text:
      - Ensures it is a string.
      - Strips leading and trailing **space characters only**.
      - Preserves all control characters (e.g., tabs, newlines, carriage returns).
    """
    if not isinstance(text, str):
        raise TypeError("Input must be a string")
    return text.lstrip(' ').rstrip(' ')

# sanitize_filename is now imported from common_utils

def replace_repeated_chars(text: str, chars) -> str:
    """
    Replace any sequence of repeated occurrences of each character in `chars`
    with a single occurrence. For example, "！！！！" becomes "！".
    """
    for char in chars:
        # Escape the character to handle any regex special meaning.
        pattern = re.escape(char) + r'{2,}'
        text = re.sub(pattern, char, text)
    return text

def limit_repeated_chars(text, force_chinese=False, force_english=False):
    """
    Normalize repeated character sequences in the input text.

    This function processes the text by applying the following rules:

    ╔════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╗
    ║ List of Characters                           │ Max Repetitions     │ Example Input           │ Example Output          ║
    ╠════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╣
    ║ PRESERVE_UNLIMITED (default)                 │ ∞                   │ "#####", "....."        │ "#####", "....."        ║
    ║ (whitespace, control, symbols, etc.)         │                     │                         │                         ║
    ╠════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╣
    ║ ALL_PUNCTUATION (non-exempt)                 │ 1                   │ "！！！！！！"            │ "！"                     ║
    ╠═════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╣
    ║ Other characters (e.g. letters)              │ 3                   │ "aaaaa"                 │ "aaa"                    ║
    ╠═════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╣
    ║ Numbers (all numeric characters in all lang) │ ∞                   │ "ⅣⅣⅣⅣ", "111111"      │ "ⅣⅣⅣⅣ", "111111"       ║
    ╠═════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╣
    ║ Chinese punctuation (if force_chinese=True)  │ 1                  │ "！！！！"                │ "！"                      ║
    ╠═════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╣
    ║ English punctuation (if force_english=True)  │ 1                  │ "!!!!!"                  │ "!"                      ║
    ╚═════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╝

    Detailed Rules:
      1. For characters in PRESERVE_UNLIMITED, the repetition is preserved exactly (even if repeated more than 3 times),
         unless overridden by a force option.
      2. For characters in ALL_PUNCTUATION (that are not overridden by a force option), any repeated sequence is collapsed to a single occurrence.
      3. For all other characters (e.g. letters), if a sequence is longer than 3, it is replaced by exactly 3 consecutive occurrences;
         sequences of 3 or fewer remain unchanged.
      4. For numeric characters (as determined by isnumeric()), repetitions are always preserved (i.e. unlimited).
      5. Alternating sequences of different characters (e.g. "ABABAB") are not modified.

    Optional Parameters:
      force_chinese (bool): If True, forces all Chinese punctuation characters (defined in CHINESE_PUNCTUATION)
                                 to be repeated only once.
      force_english (bool): If True, forces all English punctuation characters (defined in ENGLISH_PUNCTUATION)
                                 to be repeated only once, even if they are normally exempt.

    Parameters:
        text (str): The input text to normalize.

    Returns:
        str: The normalized text with excessive character repetitions collapsed as specified.
    """
    def limiter(match):
        # Extract the entire sequence of repeated characters.
        seq = match.group(0)
        char = seq[0]

        # For all numeric characters (covers Arabic, Chinese, Roman, Japanese, etc.), allow unlimited repetitions.
        if char.isnumeric():
            return seq

        # Forced rules override any other considerations:
        if force_chinese and char in CHINESE_PUNCTUATION:
            return char  # Collapse to one occurrence.
        if force_english and char in ENGLISH_PUNCTUATION:
            return char  # Collapse to one occurrence.

        # For characters allowed unlimited repetition by default, preserve the original sequence.
        if char in PRESERVE_UNLIMITED:
            return seq

        # For characters in ALL_PUNCTUATION (non-exempt), collapse any sequence to one occurrence.
        elif char in ALL_PUNCTUATION:
            return char

        # For all other characters, collapse to 3 occurrences if the sequence is too long.
        # If the sequence length is 3 or fewer, leave it unchanged.
        else:
            return seq if len(seq) <= 3 else char * 3

    # Replace all repeated sequences in the text using the limiter function.
    return _repeated_chars.sub(limiter, text)




def extract_code_blocks(html_str: str):
    """
    Extract <pre> and <code> blocks from the HTML and replace them with placeholders.
    Returns the modified HTML and a list of block code contents.
    """
    block_codes = []
    def repl(match):
        code_content = match.group(2)
        placeholder = f"@@CODEBLOCK{len(block_codes)}@@"
        block_codes.append(code_content)
        return placeholder
    modified_html = re.sub(
        r'<\s*(pre|code)[^>]*>(.*?)<\s*/\s*\1\s*>',
        repl,
        html_str,
        flags=re.DOTALL | re.IGNORECASE
    )
    return modified_html, block_codes

def extract_inline_code(text: str):
    """
    Extract inline code spans delimited by single backticks and replace them with placeholders.
    Returns the modified text and a list of inline code contents.
    """
    inline_codes = []
    def repl(match):
        code_content = match.group(1)
        placeholder = f"@@INLINECODE{len(inline_codes)}@@"
        inline_codes.append(code_content)
        return placeholder
    # This regex matches text between single backticks.
    modified_text = re.sub(r'`([^`]+)`', repl, text)
    return modified_text, inline_codes

def remove_html_comments(html_str: str) -> str:
    """
    Remove HTML comments.
    """
    return re.sub(r'<!--.*?-->', '', html_str, flags=re.DOTALL)

def remove_script_and_style(html_str: str) -> str:
    """
    Remove <script> and <style> tags along with their entire content.
    """
    html_str = re.sub(
        r'<\s*script[^>]*>.*?<\s*/\s*script\s*>',
        '',
        html_str,
        flags=re.DOTALL | re.IGNORECASE
    )
    html_str = re.sub(
        r'<\s*style[^>]*>.*?<\s*/\s*style\s*>',
        '',
        html_str,
        flags=re.DOTALL | re.IGNORECASE
    )
    return html_str

def replace_block_tags(html_str: str) -> str:
    """
    Replace block-level HTML tags with whitespace markers so that
    the intended formatting (newlines, tabs) is preserved.
    """
    # First, remove comments, scripts, and style blocks.
    html_str = remove_html_comments(html_str)
    html_str = remove_script_and_style(html_str)
    
    # Remove <pre> tags (their content is already extracted).
    html_str = re.sub(r'<\s*/?\s*pre[^>]*>', '', html_str, flags=re.IGNORECASE)
    
    replacements = [
        # Paragraphs: simulate a paragraph break.
        (r'<\s*/\s*p\s*>', '\n'),
        (r'<\s*p[^>]*>', '\n'),
        # Line breaks: convert to newline.
        (r'<\s*br\s*/?\s*>', '\n'),
        # Divisions: add newline after closing div.
        (r'<\s*/\s*div\s*>', '\n'),
        # List items: prefix with a bullet and add newline.
        (r'<\s*li[^>]*>', '  - '),
        (r'<\s*/\s*li\s*>', '\n'),
        # Table rows: newline after each row.
        (r'<\s*/\s*tr\s*>', '\n'),
        # Table cells: add a tab after each cell.
        (r'<\s*/\s*td\s*>', '\t'),
        (r'<\s*/\s*th\s*>', '\t'),
        # Blockquotes: add newlines.
        (r'<\s*blockquote[^>]*>', '\n'),
        (r'<\s*/\s*blockquote\s*>', '\n'),
        # Headers (h1-h6): newlines before and after.
        (r'<\s*h[1-6][^>]*>', '\n'),
        (r'<\s*/\s*h[1-6]\s*>', '\n'),
    ]
    for pattern, repl in replacements:
        html_str = re.sub(pattern, repl, html_str, flags=re.IGNORECASE)
    return html_str

def remove_remaining_tags(html_str: str) -> str:
    """
    Remove any remaining HTML tags (including orphaned or widowed ones)
    while leaving inner text intact.
    
    This function only matches valid HTML tags that start with an optional slash
    followed by an alphabetical character. It will not match stray "<" or ">"
    used in code snippets or math expressions.
    """
    pattern = r'<\s*(\/)?\s*([a-zA-Z][a-zA-Z0-9]*)(?:\s+[^<>]*?)?\s*(\/?)\s*>'
    return re.sub(pattern, '', html_str)

def unescape_non_code_with_placeholders(text: str) -> str:
    """
    Unescape HTML entities in text that is not inside a code block.
    Code block placeholders (both block and inline) are preserved.
    """
    pattern = r'(@@CODEBLOCK\d+@@|@@INLINECODE\d+@@)'
    parts = re.split(pattern, text)
    for i, part in enumerate(parts):
        if re.fullmatch(pattern, part):
            continue  # Leave code placeholders intact.
        else:
            parts[i] = html.unescape(part)
    return ''.join(parts)

def remove_html_markup(html_str: str) -> str:
    """
    Clean the HTML text by performing the following steps:
      1. Extract block-level code (<pre> and <code>) and replace them with placeholders.
      2. Extract inline code spans (delimited by single backticks) and replace them with placeholders.
      3. Remove HTML comments, <script>, and <style> blocks (including their content).
      4. Replace block-level tags (like <p>, <br>, <div>, etc.) with whitespace markers.
      5. Remove any remaining HTML tags (only valid tags are removed, protecting math/code).
      6. Unescape HTML entities outside code placeholders.
      7. Restore the inline code placeholders.
      8. Restore the block-level code placeholders.
      
    This process preserves spacing (including repeated spaces, tabs, newlines),
    leaves literal characters (including < or >) intact in code or math expressions,
    and unescapes HTML entities in regular text.
    """
    # Step 1: Extract block-level code.
    html_modified, block_codes = extract_code_blocks(html_str)
    # Step 2: Extract inline code spans.
    html_modified, inline_codes = extract_inline_code(html_modified)
    # Steps 3-5: Remove unwanted content and tags.
    html_modified = remove_html_comments(html_modified)
    html_modified = remove_script_and_style(html_modified)
    html_modified = replace_block_tags(html_modified)
    html_modified = remove_remaining_tags(html_modified)
    # Step 6: Unescape HTML entities outside code placeholders.
    html_modified = unescape_non_code_with_placeholders(html_modified)
    # Step 7: Restore inline code placeholders.
    for i, code in enumerate(inline_codes):
        placeholder = f"@@INLINECODE{i}@@"
        html_modified = html_modified.replace(placeholder, f"`{code}`")
    # Step 8: Restore block-level code placeholders.
    for i, code in enumerate(block_codes):
        placeholder = f"@@CODEBLOCK{i}@@"
        html_modified = html_modified.replace(placeholder, code)
    return html_modified
    
    
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
                with open(txt_file_name, encoding='utf8') as f:
                        contents = f.read()
                        tolog.debug(contents)
                return contents
        else:
                tolog.debug("Error : "+str(txt_file_name)+" is not a valid file!")
                return None

def save_text_file(text, filename):
        file_path = Path(Path.joinpath(Path.cwd(), Path(filename)))
        with open(file_path, "wt", encoding="utf-8") as f:
                f.write(clean(text))
        tolog.debug("Saved text file in: "+str(file_path))
        

def remove_excess_empty_lines(txt: str) -> str:
    # Match 5 or more newline characters
    return re.sub(r'\n{5,}', '\n\n\n\n', txt)

def normalize_spaces(text):
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
def get_val(myList, idx, default=None):
    try:
        return myList[idx]
    except IndexError:
        return default
            
        
_email_re = re.compile(r"[a-zA-Z0-9_\.\+\-]+\@[a-zA-Z0-9_\.\-]+\.[a-zA-Z]+")
_url_re = re.compile(r"https?://(-\.)?([^\s/?\.#]+\.?)+(/[^\s]*)?")

def strip_urls(input_text):
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


def is_markdown(input_text):
    """Check if a string is actually markdown"""
    #input_text = input_text[:1000]  # check only first 1000 chars
    # Don't mark part of URLs or email addresses as Markdown
    input_text = strip_urls(input_text)
    return bool(_markdown_re.match(input_text.replace("\n", "")))

    
    
def decode_input_file_content(input_file: Path) -> str:
    encoding = detect_file_encoding(input_file)
    tolog.debug(f"\nDetected encoding: {encoding}")
    
    try:
        with codecs.open(input_file, 'r', encoding=encoding) as f:
            content = f.read()
    except Exception as e:
        tolog.debug(f"\nAn error occurred processing file '{str(input_file)}': {e}")
        tolog.debug("Defaulting to GB18030 encoding.")
        encoding = 'GB18030'
        try:
            with codecs.open(input_file, 'r', encoding=encoding) as f:
                content = f.read()
        except Exception as e:
            tolog.debug(f"\nAn error occurred processing file '{str(input_file)}': {e}")
            tolog.debug("Attempt to decode using the detected encoding, replacing errors with the error character.")
            with open(input_file, 'rb') as file:
                content_bytes = file.read()
                # Attempt to decode using the detected encoding, replacing errors with the error character
                content = content_bytes.decode(encoding, errors='replace')
            
    return content
    
    
# try to detect the encoding of chinese text files 
def detect_file_encoding(file_path: Path) -> str:
    detector = UniversalDetector()
    with file_path.open('rb') as f:
        for line in f:
            detector.feed(line)
            if detector.done:
                break
        detector.close()
        return detector.result['encoding']
        
        
        
    

# Function to extract title and author info from foreign novels filenames (chinese, japanese, etc.)
def foreign_book_title_splitter(filename):
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


def split_chinese_text_using_split_points(book_content, max_chars=MAXCHARS):
    # SPLIT POINT METHOD
    # Compute split points based on max_chars and chapter patterns
    chapter_pattern = r'第\d+章'  # pattern to split at Chapter title/number line
    total_book_characters = len(book_content)
    split_points_list = []
    counter_chars = 0
    pattern_length = len(chapter_pattern) - 2  # accounting for the regex special characters
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
def import_book_from_txt(file_path, encoding='utf-8', chapter_pattern=r'Chapter \d+', max_chars=MAXCHARS, split_mode='PARAGRAPHS'):
    tolog.debug(" -> import_book_from_text()")

    filename = Path(file_path).name
    duplicate_book = Book.get_or_none(Book.source_file == filename)
    if duplicate_book is not None:
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
        splitted_chapters = split_chinese_text_in_parts(book_content, max_chars)
    else:
        # default use split_mode = 'PARAGRAPHS'
        splitted_chapters = split_chinese_text_in_parts(book_content, max_chars)
        
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
                tolog.debug(f"An exception happened when creating a new variation original for chapter n.{chapter_number}:")
                tolog.debug("ERROR: "+ str(e))
        finally:
            manual_commit() 
            
    return new_book_id


def clean_adverts(text_content: str) -> str:
    # string to remove from content
    spam1regex = [  r"吉米小说网\s*[（(]www\.(34gc|jimixs)\.(net|com)[）)]\s*txt电子书下载",
                    r"吉米小说网\s*[（(]Www\.(34gc|jimixs)\.(net|com)[）)]\s*免费TXT小说下载",
                    r"吉米小说网\s*[（(]www\.jimixs\.com[）)]\s*免费电子书下载",
                    r"本电子书由果茶小说网\s*[（(]www\.34gc\.(net|com)[）)]\s*网友上传分享，网址\:http\:\/\/www\.34gc\.net",
                    r"(本电子书由){0,1}[吉米小说网果茶]{4,6}\s*[（(]www\.(34gc|jimixs)\.(net|com)[）)]\s*[tx电子书下载网友上传分免费小说在线阅读说下载享]{4,10}",
                    r"[,;\.]{0,1}\s*网址\:www\.(34gc|jimixs)\.(net|com)",
                    r"吉米小说网\s*[（(]www\.(34gc|jimixs)\.(net|com)[）)]",
                    r"本电子书由果茶小说网",
                    r"吉米小说网\s*[（(]www\.(34gc|jimixs)\.(net|com)[）)]",
                    r"(http\:\/\/){0,1}www\.(34g|jimixs)\.(net|com)",
                ]

    subst = " "

    for regex_pattern in spam1regex:
        # You can manually specify the number of replacements by changing the 4th argument
        text_content = re.sub(regex_pattern, subst, text_content, 0, re.MULTILINE | re.IGNORECASE | re.UNICODE)


    open_parh = '('
    open_parh_chinese = '（'
    closed_parh = ')'
    closed_parh_chinese = '）'

    text_content = quick_replace(text_content, open_parh_chinese, open_parh)
    text_content = quick_replace(text_content, closed_parh_chinese, closed_parh)
    return text_content


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
    # For normalization, combine all punctuation characters
    ALL_PUNCTUATION = SENTENCE_ENDING | CLOSING_QUOTES | NON_BREAKING

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

    
    
    
## Function to split a chinese novel in parts of max n characters keeping the paragraphs intact
def split_chinese_text_in_parts(text: str, max_chars=MAXCHARS) -> list:
    paragraphs = split_on_punctuation_contextual(text)
    chapters = list()
    chapters_counter = 1
    current_char_count = 0
    paragraphs_buffer = []
    paragraph_index = 0
    total_chars = sum(len(para) for para in paragraphs)
    chars_processed = 0
    chapter = ""
            
    for i, para in enumerate(paragraphs):
        # CHECK IF THE CURRENT PARAGRAPHS BUFFER HAS REACHED
        # THE CHARACTERS LIMIT AND IN SUCH CASE SAVE AND EMPTY THE PARAGRAPHS BUFFER
        if current_char_count + len(para) > max_chars:
            for p in paragraphs_buffer:
                paragraph_index += 1
                chapter += p
            chapters.append(chapter)
            chapters_counter += 1
            chapter = ""
            current_char_count = 0
            paragraphs_buffer = []
        
        paragraphs_buffer.append(para)
        chars_processed += len(para)
        current_char_count += len(para)

    # IF THE PARAGRAPH BUFFER STILL CONTAINS SOME PARAGRAPHS
    # THEN SAVE THE RESIDUAL PARAGRAPHS IN A FINAL FILE.
    if paragraphs_buffer:
        for p in paragraphs_buffer:
            paragraph_index += 1
            chapter += p
        chapters.append(chapter)
        chapters_counter += 1
                
    tolog.debug(f"\n -> Import COMPLETE.\n  Total number of paragraphs: {str(paragraph_index)}\n  Total number of chapters: {str(chapters_counter)}\n")
    
    return chapters

## TODO : ADD THE MISSING MAIN FUNCTION HERE

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

def manual_commit():
    # Simulate a database commit. In this simple implementation, changes are already in memory.
    # tolog.debug("Manual commit executed.")
    pass

def save_translated_book(book_id, resume: bool = False, create_epub: bool = False):
    """
    Simulate translation of the book and save the translated text to a file.
    For each chapter, use the translator to translate the original text.
    """
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
    existing_chapter_nums: set[int] = set()
    if resume:
        pattern = f"{book.translated_title} by {book.translated_author} - Chapter *.txt"
        for p in sorted(book_dir.glob(pattern), key=lambda x: x.name):
            match = re.search(r"Chapter (\d+)\.txt$", p.name)
            if match:
                existing_chapter_nums.add(int(match.group(1)))
        if existing_chapter_nums:
            tolog.info(f"Autoresume active: existing translated chapters detected: {sorted(existing_chapter_nums)}")
        else:
            tolog.info("Autoresume active but no existing chapter files found.")

    translated_contents = []
    # Sort chapters by chapter_number
    sorted_chapters = sorted(book.chapters, key=lambda ch: ch.chapter_number)
    for chapter in sorted_chapters:
        # Retrieve the Variation corresponding to the original text
        variation = VARIATION_DB.get(chapter.original_variation_id)
        if variation:
            if resume and chapter.chapter_number in existing_chapter_nums:
                p_existing = book_dir / f"{book.translated_title} by {book.translated_author} - Chapter {chapter.chapter_number}.txt"
                try:
                    translated_text = p_existing.read_text(encoding="utf-8")
                    tolog.info(f"Skipping translation for chapter {chapter.chapter_number}; using existing translation.")
                except FileNotFoundError:
                    tolog.warning(f"Expected file {p_existing.name} not found; re-translating.")
                else:
                    translated_contents.append(f"\n{translated_text}\n")
                    continue
            original_text = variation.text_content
            try:
                tolog.info(f"TRANSLATING CHAPTER {str(chapter.chapter_number)} of {str(len(sorted_chapters))}")
                is_last_chunk = (chapter.chapter_number == len(sorted_chapters))
                translated_text = translator.translate(original_text, is_last_chunk)
                output_filename_chapter = book_dir / f"{book.translated_title} by {book.translated_author} - Chapter {chapter.chapter_number}.txt"
                p = output_filename_chapter
                p.write_text(translated_text)
            except Exception as e:
                tolog.error(f"ERROR: Translation failed for chapter {str(chapter.chapter_number)} : {str(e)}")
                # In case translation fails, simulate translation by appending a marker
                translated_text = original_text + f"\n\n\n[Translation Failed for chunk number {str(chapter.chapter_number)}]\n\n"
            tolog.info(f"\nChapter {chapter.chapter_number}:\n{translated_text}\n\n")
            translated_contents.append(f"\n{translated_text}\n")
    # Combine all translated chapters into one full text
    full_translated_text = "\n".join(translated_contents)
    full_translated_text = remove_excess_empty_lines(full_translated_text)
    # Save to a file named with the book_id
    output_filename = book_dir / f"translated_{book.translated_title} by {book.translated_author}.txt"
    with open(output_filename, "w", encoding="utf-8") as f:
        f.write(full_translated_text)
    tolog.info(f"Translated book saved to {output_filename}")
    if create_epub:
        if epub is None:
            tolog.error("EPUB creation requested but 'ebooklib' is not installed.")
            safe_print("[bold red]Missing dependency 'ebooklib'. Please upload its source distribution so I can proceed.[/bold red]")
        else:
            try:
                epub_filename = str(output_filename).replace(".txt", ".epub")
                _chapters_html = []
                book_epub = epub.EpubBook()
                book_epub.set_identifier(str(book.book_id))
                book_epub.set_title(book.translated_title or book.title)
                book_epub.set_language("zh")  # adjust if needed
                if book.translated_author:
                    book_epub.add_author(book.translated_author)
                # Build chapters
                for ch_num, ch_text in enumerate(translated_contents, start=1):
                    chap = epub.EpubHtml(title=f"Chapter {ch_num}", file_name=f"chap_{ch_num}.xhtml", lang="zh")
                    # Preserve line breaks to ensure no text is lost
                    escaped = html.escape(ch_text)
                    chap.content = f"<h1>Chapter {ch_num}</h1><p>" + escaped.replace('\n','<br/>') + "</p>"
                    book_epub.add_item(chap)
                    _chapters_html.append(chap)
                # Define Table of Contents and spine
                book_epub.toc = tuple(_chapters_html)
                book_epub.spine = ["nav"] + _chapters_html
                # Add default navigation files
                book_epub.add_item(epub.EpubNcx())
                book_epub.add_item(epub.EpubNav())
                epub.write_epub(epub_filename, book_epub, {})
                tolog.info(f"EPUB saved to {epub_filename}")
                safe_print(f"[bold green]EPUB saved to {epub_filename}[/bold green]")
            except Exception as e:
                tolog.exception("Error while creating EPUB.")
                safe_print(f"[bold red]Error while creating EPUB: {e}[/bold red]")

###############################################
#               MAIN FUNCTION               #
###############################################

def load_safe_yaml(path: Path):
    """Atomically load YAML with temp file handling"""
    try:
        temp_path = path.with_suffix(".lock")
        with temp_path.open("w") as temp_file:
            temp_file.write(path.read_text())
        return yaml.safe_load(temp_path.read_text())
    finally:
        temp_path.unlink(missing_ok=True)

def process_novel_unified(file_path: Path, args) -> bool:
    """
    Unified processing function for a single novel file with all three phases:
    1. Renaming (unless --skip-renaming)
    2. Translation (unless --skip-translating)
    3. EPUB generation (unless --skip-epub)
    
    Returns True if all enabled phases completed successfully
    """
    original_path = file_path
    current_path = file_path
    
    # Create a progress file for this specific novel to track phases
    progress_file = file_path.parent / f".{file_path.stem}_progress.yml"
    
    # Load existing progress if resuming
    if args.resume and progress_file.exists():
        progress = load_safe_yaml(progress_file) or {}
    else:
        progress = {
            'original_file': str(file_path),
            'phases': {
                'renaming': {'status': 'pending', 'result': None},
                'translation': {'status': 'pending', 'result': None},
                'epub': {'status': 'pending', 'result': None}
            }
        }
    
    # Update current path from progress if available
    if progress['phases']['renaming']['status'] == 'completed' and progress['phases']['renaming']['result']:
        current_path = Path(progress['phases']['renaming']['result'])
        if current_path.exists():
            tolog.info(f"Resuming with renamed file: {current_path.name}")
        else:
            current_path = file_path
    
    # Phase 1: Renaming
    if not args.skip_renaming and progress['phases']['renaming']['status'] != 'completed':
        tolog.info(f"Phase 1: Renaming file {file_path.name}")
        
        # Get API key
        api_key = args.openai_api_key or os.getenv('OPENAI_API_KEY')
        if not api_key:
            tolog.error("OpenAI API key required for renaming. Use --openai-api-key or set OPENAI_API_KEY env var")
            return False
        
        try:
            success, new_path, metadata = process_novel_file(
                file_path, 
                api_key=api_key,
                model="gpt-4o-mini",
                temperature=0.0,
                dry_run=False
            )
            
            if success and new_path:
                current_path = new_path
                progress['phases']['renaming']['status'] = 'completed'
                progress['phases']['renaming']['result'] = str(new_path)
                tolog.info(f"File renamed to: {new_path.name}")
            else:
                tolog.warning(f"Renaming failed for {file_path.name}, continuing with original name")
                progress['phases']['renaming']['status'] = 'failed'
                
            # Save progress
            with progress_file.open('w') as f:
                yaml.safe_dump(progress, f)
                
        except Exception as e:
            tolog.error(f"Error during renaming: {e}")
            progress['phases']['renaming']['status'] = 'failed'
            progress['phases']['renaming']['error'] = str(e)
            with progress_file.open('w') as f:
                yaml.safe_dump(progress, f)
            if not args.resume:
                return False
    
    # Phase 2: Translation
    if not args.skip_translating and progress['phases']['translation']['status'] != 'completed':
        tolog.info(f"Phase 2: Translating {current_path.name}")
        
        try:
            # Import and translate the book
            new_book_id = import_book_from_txt(
                str(current_path), 
                encoding=args.encoding, 
                max_chars=args.max_chars, 
                split_mode=args.split_mode
            )
            
            # Save translated chapters
            save_translated_book(new_book_id, resume=args.resume, create_epub=False)
            
            progress['phases']['translation']['status'] = 'completed'
            progress['phases']['translation']['result'] = new_book_id
            with progress_file.open('w') as f:
                yaml.safe_dump(progress, f)
                
            tolog.info(f"Translation completed for book ID: {new_book_id}")
            
        except Exception as e:
            tolog.error(f"Error during translation: {e}")
            progress['phases']['translation']['status'] = 'failed'
            progress['phases']['translation']['error'] = str(e)
            with progress_file.open('w') as f:
                yaml.safe_dump(progress, f)
            if not args.resume:
                return False
    
    # Phase 3: EPUB Generation
    if not args.skip_epub and progress['phases']['epub']['status'] != 'completed':
        tolog.info(f"Phase 3: Generating EPUB for {current_path.name}")
        
        try:
            # Extract book info from filename
            book_info = extract_book_info_from_path(current_path)
            
            # Find the output directory for this book
            book_title = book_info['title_english'] or current_path.stem
            book_author = book_info['author_english'] or "Unknown"
            
            # Look for translated chapters directory
            book_dir = current_path.parent / book_title
            if not book_dir.exists():
                # Try with sanitized name
                safe_title = re.sub(r'[^\w\s-]', '_', book_title).strip()
                book_dir = current_path.parent / safe_title
            
            if book_dir.exists() and book_dir.is_dir():
                # Create EPUB output path
                epub_name = re.sub(r'[^\w\s-]', '_', book_title).strip() + ".epub"
                epub_path = current_path.parent / epub_name
                
                # Build EPUB
                success, issues = build_epub_from_directory(
                    book_dir,
                    epub_path,
                    title=book_title,
                    author=book_author,
                    detect_toc=True,
                    strict=not args.resume,
                    logger=tolog
                )
                
                if success:
                    progress['phases']['epub']['status'] = 'completed'
                    progress['phases']['epub']['result'] = str(epub_path)
                    with progress_file.open('w') as f:
                        yaml.safe_dump(progress, f)
                    
                    tolog.info(f"EPUB created successfully: {epub_path}")
                    if issues:
                        tolog.warning(f"EPUB created with {len(issues)} issues")
                else:
                    progress['phases']['epub']['status'] = 'failed'
                    progress['phases']['epub']['error'] = f"{len(issues)} issues"
                    with progress_file.open('w') as f:
                        yaml.safe_dump(progress, f)
                        
                    tolog.error(f"EPUB creation failed with {len(issues)} issues")
                    if not args.resume:
                        return False
            else:
                tolog.warning(f"No translated chapters found for EPUB generation at {book_dir}")
                progress['phases']['epub']['status'] = 'skipped'
                progress['phases']['epub']['error'] = 'No chapters found'
                with progress_file.open('w') as f:
                    yaml.safe_dump(progress, f)
                
        except Exception as e:
            tolog.error(f"Error during EPUB generation: {e}")
            progress['phases']['epub']['status'] = 'failed'
            progress['phases']['epub']['error'] = str(e)
            with progress_file.open('w') as f:
                yaml.safe_dump(progress, f)
            if not args.resume:
                return False
    
    # Clean up progress file if all phases completed successfully
    all_completed = all(
        phase['status'] in ('completed', 'skipped') 
        for phase in progress['phases'].values()
    )
    if all_completed and progress_file.exists():
        progress_file.unlink()
        tolog.info("All phases completed, removed progress file")
    
    return True

def process_batch(args):
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
            with progress_file.open('w') as f:
                yaml.safe_dump(progress, f)

            try:
                tolog.info(f"Processing: {Path(item['path']).name}")
                
                # Use unified processor
                success = process_novel_unified(Path(item['path']), args)
                
                if success:
                    item['status'] = 'completed'
                else:
                    raise Exception("One or more phases failed")
                    
            except Exception as e:
                tolog.error(f"Failed to process {item['path']}: {str(e)}")
                item['status'] = 'failed/skipped'
                item['error'] = str(e)
                item['retry_count'] = item.get('retry_count', 0) + 1
            finally:
                item['end_time'] = dt.datetime.now().isoformat()
                with progress_file.open('w') as f:
                    yaml.safe_dump(progress, f)
                
                # Move completed batch to history
                if all(file['status'] in ('completed', 'failed/skipped') 
                      for file in progress['files']):
                    with history_file.open('a', encoding="utf-8") as f:
                        f.write("---\n")
                        yaml.safe_dump(progress, f, allow_unicode=True)
                    progress_file.unlink()

def main():
    global tolog
    # Set up logging
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )
    tolog = logging.getLogger(__name__)
    
    # Warn if colorama is missing
    if cr is None:
        tolog.warning("colorama package not installed. Colored text may not work properly.")
    
    # Set up signal handling for graceful termination
    def signal_handler(sig, frame):
        tolog.info("Interrupt received. Exiting gracefully.")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    # Parse command-line arguments
    import argparse
    parser = argparse.ArgumentParser(
        description="EnChANT - English-Chinese Automatic Novel Translator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
USAGE EXAMPLES:
  Full processing (rename + translate + EPUB):
    $ ./enchant_cli.py novel.txt --openai-api-key YOUR_KEY

  Skip renaming (translate + EPUB only):
    $ ./enchant_cli.py novel.txt --skip-renaming

  Skip translation (rename + EPUB from existing translation):
    $ ./enchant_cli.py novel.txt --skip-translating --openai-api-key YOUR_KEY

  EPUB generation only:
    $ ./enchant_cli.py novel.txt --skip-renaming --skip-translating

  Batch processing with all phases:
    $ ./enchant_cli.py novels_dir --batch --openai-api-key YOUR_KEY

  Resume interrupted batch:
    $ ./enchant_cli.py novels_dir --batch --resume

PROCESSING PHASES:
  1. RENAMING: Extract metadata and rename files (requires OpenAI API key)
  2. TRANSLATION: Translate Chinese text to English
  3. EPUB: Generate EPUB from translated chapters

SKIP FLAGS:
  --skip-renaming     Skip phase 1 (file renaming)
  --skip-translating  Skip phase 2 (translation)
  --skip-epub        Skip phase 3 (EPUB generation)

BEHAVIOR:
  • Each phase can be independently skipped
  • Skipped phases preserve existing data
  • --resume works with all phase combinations
  • Progress saved for batch operations

API KEYS:
  • Renaming requires OpenAI API key (--openai-api-key or OPENAI_API_KEY env)
  • Translation uses local LM Studio by default (--remote for OpenRouter)
"""
    )
    parser.add_argument("filepath", type=str, help="Path to the input text file or directory for batch")
    parser.add_argument("--encoding", type=str, default="utf-8", help="File encoding (default: utf-8)")
    parser.add_argument("--max_chars", type=int, default=MAXCHARS, help="Maximum characters per chapter")
    parser.add_argument("--resume", action="store_true", help="Resume translation from last translated chapter")
    parser.add_argument("--epub", action="store_true", help="Deprecated: Use --skip-epub to control EPUB generation")
    parser.add_argument(
        "--split_mode", 
        type=str, 
        choices=["PARAGRAPHS", "SPLIT_POINTS"], 
        default="PARAGRAPHS", 
        help="Mode to split text (default: PARAGRAPHS)"
    )
    parser.add_argument("--batch", action="store_true", help="Process a batch of novels in a directory")
    parser.add_argument("--remote", action='store_true', help="Use remote translation server")
    
    # Skip flags for different phases
    parser.add_argument("--skip-renaming", action="store_true", help="Skip the file renaming phase")
    parser.add_argument("--skip-translating", action="store_true", help="Skip the translation phase")
    parser.add_argument("--skip-epub", action="store_true", help="Skip the EPUB generation phase")
    
    # API key for renaming (if not skipped)
    parser.add_argument("--openai-api-key", type=str, help="OpenAI API key for novel renaming (can also use OPENAI_API_KEY env var)")
    
    args = parser.parse_args()
    
    # Handle backwards compatibility for --epub flag
    if args.epub:
        tolog.warning("--epub flag is deprecated. EPUB generation is now enabled by default. Use --skip-epub to disable.")
        # If user explicitly set --epub, ensure --skip-epub is not set
        if hasattr(args, 'skip_epub') and args.skip_epub:
            tolog.warning("Both --epub and --skip-epub specified. --skip-epub takes precedence.")
    
    # Initialize translator with remote option
    global translator
    translator = ChineseAITranslator(logger=tolog, use_remote=args.remote)
    
    if args.batch:
        process_batch(args)
        return
    
    # Single file processing
    file_path = Path(args.filepath)
    
    # Check if file exists
    if not file_path.exists():
        tolog.error(f"File not found: {file_path}")
        safe_print(f"[bold red]File not found: {file_path}[/bold red]")
        sys.exit(1)
    
    # Process single file with unified processor
    tolog.info(f"Starting unified processing for file: {file_path}")
    
    try:
        success = process_novel_unified(file_path, args)
        
        if success:
            safe_print("[bold green]Novel processing completed successfully![/bold green]")
        else:
            safe_print("[bold yellow]Novel processing completed with some issues. Check logs for details.[/bold yellow]")
            sys.exit(1)
            
    except Exception as e:
        tolog.exception("Fatal error during novel processing")
        safe_print(f"[bold red]Fatal error: {e}[/bold red]")
        sys.exit(1)

if __name__ == "__main__":
    main()
