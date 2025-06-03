#!/usr/bin/env python3
from __future__ import annotations

from rich import print
import colorama as cr
from rich.console import RenderableType
from rich.table import Table
from rich.text import Text

import os
import sys
import re
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

import rich.repr
import enum
import multiexit

import codecs
from chardet.universaldetector import UniversalDetector

from typing import (
    TYPE_CHECKING,
    ClassVar,
)

from bs4 import BeautifulSoup

def remove_html_markup(text):
    # Create a BeautifulSoup object. Use 'html.parser' or 'lxml' if available
    soup = BeautifulSoup(text, 'html.parser')
    
    # Get all text and strip whitespace
    plain_text = soup.get_text(separator=' ', strip=True)
    
    # Replace multiple spaces with a single space and strip again
    plain_text = ' '.join(plain_text.split())
    
    return plain_text


# Initialize the translator
translator = ChineseAITranslator(logger=logging.getLogger(__name__))

global tolog

MAXCHARS = 1000 # TODO: make this value configurable by the user 

# CHINESE PUNCTUATION
# Characters groups for chinese punctuation and paragraph delimiters.
# Ideographic '『' and '』' are omitted because they are usually nested inside '「' and '」'.
# Ideographic '（' and '）' are omitted because they are rarely used as paragraph delimiters.
OPENING_PUNCTUATION = ['「', '“', '【', '《']
CLOSING_PUNCTUATION = ['。', '.', '…', '！', '？', '」', '”', '】', ';','》', '；']
# Control characters for paragraph delimiters
PARAGRAPH_DELIMITERS = [
    "\n",      # Line Feed
    "\r",      # Carriage Return
    "\r\n",    # Carriage Return + Line Feed
    "\v",      # Line Tabulation
    "\f",      # Form Feed
    "\x1c",    # File Separator
    "\x1d",    # Group Separator
    "\x1e",    # Record Separator
    "\x85",    # Next Line (C1 Control Code)
    "\u2028",  # Line Separator
    "\u2029"   # Paragraph Separator
    ]
    
    
    
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
                f.write(text.strip())
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
        
        
def replace_repeated_chars(text, chars):
    """
    Replace repeated occurrences of characters in the chars list with a single occurrence.
    
    Parameters:
    - text (str): The input text.
    - chars (list): List of characters to replace if repeated.
    
    Returns:
    - str: Text with replaced characters.
    """
    for char in chars:
        pattern = re.escape(char) + "+"
        text = str(re.sub(pattern, char, text))
        return text
        
    

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
    # Extract translated title and author
    if ' by ' in translated_part:
        translated_title, translated_author = translated_part.split(' by ')
    else:
        translated_title = translated_part
    # Extract original title and author
    if ' by ' in original_part:
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
    book_content = remove_html_markup(book_content)
    book_content = normalize_spaces(book_content)
    book_content = remove_excess_empty_lines(book_content)
    
    # COUNT THE NUMBER OF CHARACTERS
    total_book_characters = len(book_content)

    
    # SPLIT THE BOOK IN CHUNKS
    if split_mode in "SPLIT_POINTS":
        splitted_chapters = split_chinese_text_using_split_points(book_content, max_chars)
    elif split_mode in "PARAGRAPHS":
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
            original_author=original_title,
            translated_author=translated_title,
            transliterated_author=translated_title,
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


def clean(text_content: str) -> str:
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

    subst = ""

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

        
## Function to split a chinese string into paragraphs
## Return a list of paragraphs
def split_on_punctuation_contextual(text: str) -> list:
    text = clean(text)
    
    paragraphs = []
    buffer = ""
    text = re.sub(' +', ' ', text) # Remove repeated spaces but preserve new lines
    text = replace_repeated_chars(text, OPENING_PUNCTUATION)
    text = replace_repeated_chars(text, CLOSING_PUNCTUATION)
    text = replace_repeated_chars(text, PARAGRAPH_DELIMITERS)
                
    for i, char in enumerate(text):
        next_char = text[i + 1] if i + 1 < len(text) else None
        next_next_char = text[i + 2] if i + 2 < len(text) else None
        
        # TEST AGAINST MULTIPLE LINE BREAKS
        if (char in ['\n'] and next_char in ['\n']) or (char in ['\n'] and next_char == ' ' and next_next_char in ['\n']): 
            buffer += char
            buffer = buffer.strip()
            if buffer:
                paragraphs.append(buffer+"\n\n")
            buffer = ""
            continue
        
        # TEST AGAINST PARAGRAPHS DELIMITERS
        if char in PARAGRAPH_DELIMITERS:
            buffer += char
            buffer = buffer.strip()
            if buffer:
                paragraphs.append(buffer+"\n\n")
            buffer = ""
            continue  

        # TEST AGAINST PUNCTUATION (not always closing punctuations are paragraph delimiters!
        # patterns: "?" and "?》" and "?》。" ).
        if char in CLOSING_PUNCTUATION:
            if (next_char not in ['”','」','》','】','。','.','…'] and (next_char is ' ' and next_next_char in ['”','」','》','】','。','.','…']) is False):
                    if next_char in ['\n','', '“','【', '《','「'] or (next_char is ' ' and next_next_char in ['\n','', '“','【', '《','「']):
                        buffer += char
                        buffer = buffer.strip()
                        if buffer:
                            paragraphs.append(buffer+"\n\n")
                        buffer = ""
                        continue
        
        # ALL TESTS PASSED. ADD THE CHARACTER TO THE PARAGRAPH AND CONTINUE TO THE NEXT.
        buffer += char

    # IF THE CHARACTERS BUFFER STILL CONTAINS SOME CHARACTERS
    # THEN ADD THE RESIDUAL CHARACTERS AS A NEW PARAGRAPH.
    if buffer:
        buffer = buffer.strip()
        if buffer:
            buffer = re.sub(' +', ' ', buffer)
            paragraphs.append(buffer+"\n\n")
        
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
                
    tolog.debug(f"\n -> Processing COMPLETE!\n  Total number of paragraphs: {str(paragraph_index)}\n  Total number of chapters: {str(chapters_counter)}\n")
    
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

def save_translated_book(book_id):
    """
    Simulate translation of the book and save the translated text to a file.
    For each chapter, use the translator to translate the original text.
    """
    book = Book.get_by_id(book_id)
    if not book:
        raise ValueError("Book not found")

    translated_contents = []
    # Sort chapters by chapter_number
    sorted_chapters = sorted(book.chapters, key=lambda ch: ch.chapter_number)
    for chapter in sorted_chapters:
        # Retrieve the Variation corresponding to the original text
        variation = VARIATION_DB.get(chapter.original_variation_id)
        if variation:
            original_text = variation.text_content
            try:
                tolog.info(f"TRANSLATING CHAPTER {str(chapter.chapter_number)} of {str(len(sorted_chapters))}")
                is_last_chunk = (chapter.chapter_number == len(sorted_chapters))
                translated_text = translator.translate(original_text, is_last_chunk)
            except Exception as e:
                tolog.error(f"ERROR: Translation failed for chapter {str(chapter.chapter_number)} : {str(e)}")
                # In case translation fails, simulate translation by appending a marker
                translated_text = original_text + f"\n\n\n[Translation Failed for chunk number {str(chapter.chapter_number)}]\n\n"
            translated_contents.append(f"Chapter {chapter.chapter_number}:\n{translated_text}\n\n")
    # Combine all translated chapters into one full text
    full_translated_text = "\n".join(translated_contents)
    full_translated_text = remove_excess_empty_lines(full_translated_text)
    # Save to a file named with the book_id
    output_filename = f"translated_{book.translated_title} by {book.translated_author}.txt"
    with open(output_filename, "w", encoding="utf-8") as f:
        f.write(full_translated_text)
    tolog.info(f"Translated book saved to {output_filename}")

###############################################
#               MAIN FUNCTION               #
###############################################

def main():
    global tolog
    # Set up logging
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )
    tolog = logging.getLogger(__name__)
    
    # Set up signal handling for graceful termination
    def signal_handler(sig, frame):
        tolog.info("Interrupt received. Exiting gracefully.")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    # Parse command-line arguments
    import argparse
    parser = argparse.ArgumentParser(
        description="Import a book from a text file, split it into chapters, and add to the database."
    )
    parser.add_argument("filepath", type=str, help="Path to the input text file")
    parser.add_argument("--encoding", type=str, default="utf-8", help="File encoding (default: utf-8)")
    parser.add_argument("--max_chars", type=int, default=MAXCHARS, help="Maximum characters per chapter")
    parser.add_argument(
        "--split_mode", 
        type=str, 
        choices=["PARAGRAPHS", "SPLIT_POINTS"], 
        default="PARAGRAPHS", 
        help="Mode to split text (default: PARAGRAPHS)"
    )
    
    args = parser.parse_args()
    
    file_path = args.filepath
    encoding = args.encoding
    max_chars = args.max_chars
    split_mode = args.split_mode
    
    tolog.info(f"Starting book import for file: {file_path}")
    
    try:
        # Call the import_book_from_txt function to process the text file
        new_book_id = import_book_from_txt(file_path, encoding=encoding, max_chars=max_chars, split_mode=split_mode)
        tolog.info(f"Book imported successfully. Book ID: {new_book_id}")
        print(f"[bold green]Book imported successfully. Book ID: {new_book_id}[/bold green]")
    except Exception as e:
        tolog.exception("An error occurred during book import.")
        print(f"[bold red]Error during book import: {e}[/bold red]")
        sys.exit(1)
    
    # Save the translated book after import
    try:
        save_translated_book(new_book_id)
        tolog.info("Translated book saved successfully.")
        print(f"[bold green]Translated book saved successfully.[/bold green]")
    except Exception as e:
        tolog.exception("Error saving translated book.")
        print(f"[bold red]Error saving translated book: {e}[/bold red]")
        sys.exit(1)

if __name__ == "__main__":
    main()
    