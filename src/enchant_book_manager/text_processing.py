#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
# - Initial creation from common_text_utils.py refactoring
# - Extracted text processing functions
# - Contains functions for cleaning, normalizing, and processing text
#

"""
text_processing.py - Text processing utilities for EnChANT modules
==================================================================

This module contains text cleaning, normalization, and character manipulation
functions used across multiple EnChANT modules.
"""

import re
from .text_constants import (
    PRESERVE_UNLIMITED,
    ALL_PUNCTUATION,
    CHINESE_PUNCTUATION,
    ENGLISH_PUNCTUATION,
)


def clean(text: str) -> str:
    """
    Clean the input text.

    - Ensures it is a string.
    - Strips leading and trailing **space characters only**.
    - Preserves all control characters (e.g., tabs, newlines, carriage returns).

    Args:
        text: Input text to clean

    Returns:
        Cleaned text with leading/trailing spaces removed

    Raises:
        TypeError: If input is not a string
    """
    if not isinstance(text, str):
        raise TypeError("Input must be a string")
    return text.lstrip(" ").rstrip(" ")


def replace_repeated_chars(text: str, chars: str) -> str:
    """
    Replace any sequence of repeated occurrences of each character in `chars`
    with a single occurrence. For example, "！！！！" becomes "！".

    Args:
        text: Input text
        chars: String of characters to de-duplicate

    Returns:
        Text with repeated characters replaced
    """
    for char in chars:
        # Escape the character to handle any regex special meaning.
        pattern = re.escape(char) + r"{2,}"
        text = re.sub(pattern, char, text)
    return text


def limit_repeated_chars(text: str, force_chinese: bool = False, force_english: bool = False) -> str:
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

    Optional Parameters:
      force_chinese (bool): If True, forces all Chinese punctuation characters to be repeated only once.
      force_english (bool): If True, forces all English punctuation characters to be repeated only once.

    Args:
        text: Input text to process
        force_chinese: Force Chinese punctuation to single occurrence
        force_english: Force English punctuation to single occurrence

    Returns:
        Text with normalized repeated characters
    """

    # Determine which punctuation to limit
    limit_to_one = ALL_PUNCTUATION.copy()

    # Adjust based on force options
    if force_chinese:
        limit_to_one |= CHINESE_PUNCTUATION
    if force_english:
        limit_to_one |= ENGLISH_PUNCTUATION

    # Remove exemptions
    limit_to_one -= PRESERVE_UNLIMITED

    # Process the text character by character
    result = []
    i = 0
    while i < len(text):
        char = text[i]

        # Count consecutive occurrences
        count = 1
        while i + count < len(text) and text[i + count] == char:
            count += 1

        # Apply rules
        if char in limit_to_one:
            # Limit to 1 occurrence
            result.append(char)
        elif char.isnumeric() or char in PRESERVE_UNLIMITED:
            # Preserve all occurrences
            result.append(char * count)
        else:
            # Limit to 3 occurrences for other characters
            result.append(char * min(count, 3))

        i += count

    return "".join(result)


def remove_excess_empty_lines(text: str, max_empty_lines: int = 2) -> str:
    """
    Remove excessive empty lines from text.

    Args:
        text: The input text
        max_empty_lines: Maximum number of consecutive empty lines to keep

    Returns:
        Text with excessive empty lines removed
    """
    # Replace multiple newlines with the maximum allowed
    pattern = r"\n{" + str(max_empty_lines + 1) + ",}"
    replacement = "\n" * max_empty_lines
    return re.sub(pattern, replacement, text)


def normalize_spaces(text: str) -> str:
    """
    Normalize various types of spaces and whitespace characters.

    This function:
    1. Converts various Unicode spaces to regular spaces
    2. Removes zero-width spaces
    3. Normalizes whitespace around punctuation
    4. Removes trailing spaces from lines

    Args:
        text: The input text

    Returns:
        Text with normalized spaces
    """
    # Replace various Unicode spaces with regular space
    space_chars = [
        "\u00a0",  # Non-breaking space
        "\u1680",  # Ogham space mark
        "\u2000",
        "\u2001",
        "\u2002",
        "\u2003",
        "\u2004",
        "\u2005",  # En/em spaces
        "\u2006",
        "\u2007",
        "\u2008",
        "\u2009",
        "\u200a",  # Various spaces
        "\u202f",  # Narrow no-break space
        "\u205f",  # Medium mathematical space
        "\u3000",  # Ideographic space
    ]

    for space_char in space_chars:
        text = text.replace(space_char, " ")

    # Remove zero-width spaces
    zero_width = ["\u200b", "\u200c", "\u200d", "\ufeff"]
    for zw in zero_width:
        text = text.replace(zw, "")

    # Normalize multiple spaces to single space (not at line boundaries)
    lines = text.split("\n")
    normalized_lines = []
    for line in lines:
        # Replace multiple spaces with single space
        line = re.sub(r" {2,}", " ", line)
        # Remove trailing spaces
        line = line.rstrip()
        normalized_lines.append(line)

    return "\n".join(normalized_lines)


def clean_adverts(text_content: str) -> str:
    """
    Clean advertisement text from Chinese novel content.

    This function removes various spam/advertisement patterns commonly found
    in Chinese novel text files, particularly from jimixs and 34gc websites.

    Args:
        text_content: Input text possibly containing advertisements

    Returns:
        Text with advertisements removed
    """
    # Regex patterns to remove spam/advertisements
    spam_patterns = [
        r"吉米小说网\s*[（(]www\.(34gc|jimixs)\.(net|com)[）)]\s*txt电子书下载",
        r"吉米小说网\s*[（(]Www\.(34gc|jimixs)\.(net|com)[）)]\s*免费TXT小说下载",
        r"吉米小说网\s*[（(]www\.jimixs\.com[）)]\s*免费电子书下载",
        r"本电子书由果茶小说网\s*[（(]www\.34gc\.(net|com)[）)]\s*网友上传分享，网址\:http\:\/\/www\.34gc\.net",
        r"(本电子书由){0,1}[吉米小说网果茶]{4,6}\s*[（(]www\.(34gc|jimixs)\.(net|com)[）)]\s*[tx电子书下载网友上传分免费小说在线阅读说下载享]{4,10}",
        r"[,;\.]{0,1}\s*网址\:www\.(34gc|jimixs)\.(net|com)",
        r"吉米小说网\s*[（(]www\.(34gc|jimixs)\.(net|com)[）)]",
        r"本电子书由果茶小说网",
        r"(http\:\/\/){0,1}www\.(34g|jimixs)\.(net|com)",
    ]

    # Replace spam patterns with single space
    for pattern in spam_patterns:
        text_content = re.sub(
            pattern,
            " ",
            text_content,
            count=0,
            flags=re.MULTILINE | re.IGNORECASE | re.UNICODE,
        )

    # Normalize parentheses (convert Chinese to English)
    text_content = text_content.replace("（", "(").replace("）", ")")

    return text_content
