#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
# - Created new module from chapter_detector.py refactoring
# - Contains regex patterns and constants for chapter detection
# - Includes HEADING_RE, PART_PATTERNS, and DB_OPTIMIZATION_THRESHOLD
#

"""
chapter_patterns.py - Regex patterns and constants for chapter detection
========================================================================

Contains compiled regular expressions and pattern lists used to identify
chapter headings and part notations in various formats.
"""

import re
from .epub_constants import WORD_NUMS

# ────────────────────────── regexes & tables ────────────────────────── #

# Enhanced regex for various English chapter heading patterns
HEADING_RE = re.compile(
    rf"^[^\w]*\s*"  # Allow leading non-word chars and whitespace
    rf"(?:"  # Start of main group
    rf"(?:chapter|ch\.?|chap\.?)\s*"  # "Chapter", "Ch.", "Ch", "Chap.", "Chap" (space optional)
    rf"(?:(?P<num_d>\d+[a-z]?)|(?P<num_r>[ivxlcdm]+)|"  # Added [a-z]? for letter suffixes
    rf"(?P<num_w>(?:{WORD_NUMS})(?:[-\s](?:{WORD_NUMS}))*))"
    rf"|"  # OR
    rf"(?:part|section|book)\s+"  # "Part", "Section", "Book"
    rf"(?:(?P<part_d>\d+)|(?P<part_r>[ivxlcdm]+)|"
    rf"(?P<part_w>(?:{WORD_NUMS})(?:[-\s](?:{WORD_NUMS}))*))"
    rf"|"  # OR
    rf"§\s*(?P<sec_d>\d+)"  # "§ 42" style
    rf"|"  # OR
    rf"(?P<hash_d>\d+)\s*(?:\.|\)|:|-)?"  # "1.", "1)", "1:", "1-" at start of line
    rf")"
    rf"\b(?P<rest>.*)$",
    re.IGNORECASE,
)

# Regex patterns for detecting part notation in chapter titles
PART_PATTERNS = [
    # Fraction patterns: 1/3, 2/3, [1/3], (1 of 3)
    re.compile(r"\b(\d+)\s*/\s*(\d+)\b"),
    re.compile(r"\[(\d+)\s*/\s*(\d+)\]"),
    re.compile(r"\((\d+)\s*of\s*(\d+)\)", re.IGNORECASE),
    re.compile(r"\((\d+)\s*out\s*of\s*(\d+)\)", re.IGNORECASE),
    # Part word patterns: part 1, part one, pt. 1
    re.compile(
        r"\bpart\s+(\d+|one|two|three|four|five|six|seven|eight|nine|ten)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bpt\.?\s+(\d+|one|two|three|four|five|six|seven|eight|nine|ten)\b",
        re.IGNORECASE,
    ),
    # Dash number patterns: - 1, - 2
    re.compile(r"\s+-\s+(\d+)\s*$"),
    # Roman numeral patterns at end with word boundary: Part I, Part II, etc
    # More restrictive to avoid matching names like "Louis XIV"
    re.compile(r"(?:part|pt\.?)\s+([IVX]+)\s*$", re.IGNORECASE),
    re.compile(r"\s+-\s+([IVX]+)\s*$"),  # "- I", "- II", etc
]

# Database optimization threshold
DB_OPTIMIZATION_THRESHOLD = 100000  # Number of lines before using database
