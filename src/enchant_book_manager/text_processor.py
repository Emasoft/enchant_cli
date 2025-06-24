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
# - Extracted text processing functions from cli_translator.py
# - Added URL and email stripping functions
# - Added markdown detection
# - Added text replacement utilities
# - Added helper functions for list access
#

"""Text processing utilities for the EnChANT Book Manager."""

from __future__ import annotations

import re
from typing import Any


# Precompiled regex patterns
_email_re = re.compile(r"[a-zA-Z0-9_\.\+\-]+\@[a-zA-Z0-9_\.\-]+\.[a-zA-Z]+")
_url_re = re.compile(r"https?://(-\.)?([^\s/?\.#]+\.?)+(/[^\s]*)?")
_markdown_re = re.compile(r".*(" r"\*(.*)\*|" r"_(.*)_|" r"\[(.*)\]\((.*)\)|" r"`(.*)`|" r"```(.*)```" r").*")


def remove_excess_empty_lines(txt: str) -> str:
    """
    Reduce consecutive empty lines to a maximum of 3 (4 newlines).

    Args:
        txt: Text with potentially excessive empty lines

    Returns:
        Text with normalized empty lines
    """
    # Match 4 or more newline characters and replace with exactly 3 newlines
    return re.sub(r"\n{4,}", "\n\n\n", txt)


def get_val(my_list: list[Any], idx: int, default: Any = None) -> Any:
    """
    Get value from list at index, returning default if index is out of bounds.

    An equivalent of dict.get(key, default) for lists.

    Args:
        my_list: The list to get value from
        idx: The index to access
        default: Default value if index is out of bounds

    Returns:
        Value at index or default if index is invalid
    """
    try:
        return my_list[idx]
    except IndexError:
        return default


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


def is_markdown(input_text: str) -> bool:
    """
    Check if a string contains markdown formatting.

    Args:
        input_text: Text to check for markdown

    Returns:
        True if text contains markdown formatting, False otherwise
    """
    # Don't mark part of URLs or email addresses as Markdown
    input_text = strip_urls(input_text)
    return bool(_markdown_re.match(input_text.replace("\n", "")))


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
