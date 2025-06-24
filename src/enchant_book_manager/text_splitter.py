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
# - Extracted text splitting functions from cli_translator.py
# - Added Chinese text splitting by punctuation
# - Added paragraph-based splitting
# - Added buffer flushing utility
# - Imported punctuation constants from common_text_utils
#

"""Text splitting utilities for Chinese novel processing."""

from __future__ import annotations

import re
from typing import Optional, Any

from .common_text_utils import (
    ALL_PUNCTUATION,
    CLOSING_QUOTES,
    NON_BREAKING,
    SENTENCE_ENDING,
    clean,
    clean_adverts,
    replace_repeated_chars,
)

# Default maximum characters per chunk
DEFAULT_MAX_CHARS = 11999

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


def flush_buffer(buffer: str, paragraphs: list[str]) -> str:
    """
    If the buffer contains text, normalize spaces and append it as a new paragraph.
    Returns an empty string to reset the buffer.

    Args:
        buffer: Current buffer text
        paragraphs: List to append paragraph to

    Returns:
        Empty string to reset buffer
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
      - paragraph_start_triggers: Characters which, if they follow punctuation, indicate
        a new paragraph is starting.

    Args:
        text: Chinese text to split

    Returns:
        List of paragraphs

    Raises:
        TypeError: If input is not a string
    """
    if not isinstance(text, str):
        raise TypeError("Input text must be a string")

    # Define a comprehensive set of paragraph delimiters.
    paragraph_delimiters = {
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
    paragraph_start_triggers = {"\n", "\u201c", "【", "《", "「"}

    # Preprocess text:
    # 1. Clean and normalize newlines.
    # 2. Remove extra spaces.
    # 3. Replace repeated punctuation and delimiter characters.
    text = clean_adverts(text)
    text = clean(text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(" +", " ", text)
    text = replace_repeated_chars(text, "".join(ALL_PUNCTUATION))
    text = replace_repeated_chars(text, "".join(paragraph_delimiters))

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
            if (next_char in paragraph_start_triggers) or (next_char == " " and next_next_char in paragraph_start_triggers):
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
                if (next_char in paragraph_start_triggers) or (next_char == " " and next_next_char in paragraph_start_triggers):
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

    Args:
        text: Text to split into paragraphs
    Returns:
        List of paragraphs with trailing double newlines

    Raises:
        TypeError: If input is not a string
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


def split_chinese_text_in_parts(text: str, max_chars: int = DEFAULT_MAX_CHARS, logger: Optional[Any] = None) -> list[str]:
    """
    Split Chinese novel text into chunks of maximum character length.

    Keeps paragraphs intact when splitting.

    Args:
        text: The Chinese text to split
        max_chars: Maximum characters per chunk
        logger: Optional logger for debug output

    Returns:
        List of text chunks
    """
    # Always use the new function that splits on actual paragraph breaks
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

    for para in paragraphs:
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

    if logger is not None:
        logger.debug(f"\n -> Import COMPLETE.\n  Total number of paragraphs: {str(paragraph_index)}\n  Total number of chunks: {str(chunks_counter)}\n")

    return chunks
