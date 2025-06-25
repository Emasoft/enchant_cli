#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
# - Created new module from chapter_detector.py refactoring
# - Contains validation functions for chapter detection
# - Includes has_part_notation, parse_num, and is_valid_chapter_line
#

"""
chapter_validators.py - Validation functions for chapter detection
==================================================================

Contains helper functions to validate chapter headings, check for part
notations, and parse numeric values from chapter titles.
"""

from .chapter_patterns import PART_PATTERNS
from .epub_constants import parse_num as parse_num_shared


def has_part_notation(title: str) -> bool:
    """Check if a title contains part notation patterns.

    Args:
        title: Chapter title to check

    Returns:
        True if title contains part notation, False otherwise
    """
    if not title:  # Handle None or empty string
        return False

    # Early return on first match for better performance
    return any(pattern.search(title) for pattern in PART_PATTERNS)


# Use parse_num wrapper to maintain compatibility with existing code
def parse_num(raw: str | None) -> int | None:
    """Wrapper for shared parse_num function."""
    if raw is None:
        return None
    return parse_num_shared(raw)


def is_valid_chapter_line(line: str) -> bool:
    """
    Check if a line contains a valid chapter heading based on:
    1. Chapter word at start of line (or after special chars)
    2. Chapter word not in quotes
    """
    line_stripped = line.strip()
    lower_line = line_stripped.lower()

    # Check if line starts with quotes containing chapter
    if line_stripped.startswith(('"', "'")) and "chapter" in lower_line:
        quote_char = line_stripped[0]
        try:
            end_quote = line_stripped.index(quote_char, 1)
            if "chapter" in line_stripped[:end_quote].lower():
                return False  # Chapter word is in quotes
        except ValueError:
            pass

    # Check if chapter appears mid-sentence (not after special chars)
    chapter_pos = lower_line.find("chapter")
    if chapter_pos == -1:
        return True  # No chapter word, let regex decide

    if chapter_pos == 0:
        return True  # At start of line

    # Check what comes before chapter
    before_chapter = line_stripped[:chapter_pos].strip()

    # Special characters that can precede chapter
    if before_chapter and all(c in "#*>§[](){}|-–—•~/" or c.isspace() for c in before_chapter):
        return True  # After special chars/whitespace only

    # Check if preceded by quotes
    if before_chapter.endswith(('"', "'")):
        return False  # Chapter word likely in quotes

    return False  # Mid-sentence
