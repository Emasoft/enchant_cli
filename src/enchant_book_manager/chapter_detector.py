#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
# - Refactored into multiple smaller modules
# - This file now serves as a backward compatibility wrapper
# - Constants moved to chapter_patterns.py
# - Validation functions moved to chapter_validators.py
# - Parsing functions moved to chapter_parser.py
#

"""
chapter_detector.py - Chapter detection and parsing for EPUB generation
======================================================================

Handles detection of chapter headings in various formats (numeric, roman, word)
and splits text into chapters with proper sequencing and validation.

This module now serves as a backward compatibility wrapper, importing from:
- chapter_patterns.py: Regex patterns and constants
- chapter_validators.py: Validation helper functions
- chapter_parser.py: Main parsing and detection logic
"""

# Import everything for backward compatibility
from .chapter_patterns import (
    HEADING_RE,
    PART_PATTERNS,
    DB_OPTIMIZATION_THRESHOLD,
)

from .chapter_validators import (
    has_part_notation,
    parse_num,
    is_valid_chapter_line,
)

from .chapter_parser import (
    split_text_db,
    split_text,
)

from .chapter_issues import (
    detect_issues,
)

# Re-export all symbols for backward compatibility
__all__ = [
    # From chapter_patterns
    "HEADING_RE",
    "PART_PATTERNS",
    "DB_OPTIMIZATION_THRESHOLD",
    # From chapter_validators
    "has_part_notation",
    "parse_num",
    "is_valid_chapter_line",
    # From chapter_parser
    "split_text_db",
    "split_text",
    "detect_issues",
]
