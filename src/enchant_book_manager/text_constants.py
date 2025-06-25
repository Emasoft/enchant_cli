#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
# - Initial creation from common_text_utils.py refactoring
# - Extracted all text processing constants
# - Contains character sets for punctuation and special characters
#

"""
text_constants.py - Text processing constants for EnChANT modules
=================================================================

This module contains constant definitions for text processing,
including character sets for various punctuation types and
special characters that need special handling.
"""

# Constants from original modules
PRESERVE_UNLIMITED = {
    "　",
    "\u2002",
    "\u2003",
    "\u2004",
    "\u2005",
    "\u2006",
    "\u2007",
    "\u2008",
    "\u2009",
    "\u200a",
    "\u200b",
    "\u2028",
    "\u2029",
    "\u202f",
    "\u205f",
    "\ufeff",
    "\u00a0",
    "\u1680",
    "\u180e",
    "\t",
    "\n",
    "\r",
    "\v",
    "\f",
    "\x1c",
    "\x1d",
    "\x1e",
    "\x1f",
    "\x85",
    " ",
    "!",
    '"',
    "#",
    "$",
    "%",
    "&",
    "'",
    "(",
    ")",
    "*",
    "+",
    ",",
    "-",
    ".",
    "/",
    ":",
    ";",
    "<",
    "=",
    ">",
    "?",
    "@",
    "[",
    "\\",
    "]",
    "^",
    "_",
    "`",
    "{",
    "|",
    "}",
    "~",
}

# Punctuation sets for different languages
CHINESE_PUNCTUATION = {
    "。",
    "，",
    "、",
    "；",
    "：",
    "？",
    "！",
    '"',
    """, """,
    "（",
    "）",
    "【",
    "】",
    "《",
    "》",
    "—",
    "…",
    "·",
    "￥",
    "¥",
}

ENGLISH_PUNCTUATION = {
    ".",
    ",",
    ";",
    ":",
    "?",
    "!",
    '"',
    "'",
    "(",
    ")",
    "[",
    "]",
    "{",
    "}",
    "-",
    "—",
    "…",
    "/",
    "\\",
    "@",
    "#",
    "$",
    "%",
    "^",
    "&",
    "*",
    "+",
    "=",
    "|",
    "~",
    "`",
    "<",
    ">",
}

# Sentence ending punctuation
SENTENCE_ENDING = {"。", "！", "？", "…", ".", ";", "；"}

# Closing quotes
CLOSING_QUOTES = {"」", '"', "】", "》"}

# Non-breaking punctuation
NON_BREAKING = {"，", "、", "°"}

ALL_PUNCTUATION = CHINESE_PUNCTUATION | ENGLISH_PUNCTUATION
