#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
# - Refactored from 20KB into 3 smaller modules (text_constants, text_processing, html_processing)
# - This file now serves as a backward compatibility wrapper
# - All original functionality is preserved through imports
#

# Copyright 2025 Emasoft
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

"""
common_text_utils.py - Shared text processing utilities for EnChANT modules
===========================================================================

This module serves as a backward compatibility wrapper after refactoring.
All original functionality is available through imports from the new modules:
- text_constants: Character sets and punctuation constants
- text_processing: Text cleaning and normalization functions
- html_processing: HTML cleaning and processing functions
"""

# Import all constants for backward compatibility
from .text_constants import (
    PRESERVE_UNLIMITED,
    CHINESE_PUNCTUATION,
    ENGLISH_PUNCTUATION,
    SENTENCE_ENDING,
    CLOSING_QUOTES,
    NON_BREAKING,
    ALL_PUNCTUATION,
)

# Import all text processing functions for backward compatibility
from .text_processing import (
    clean,
    replace_repeated_chars,
    limit_repeated_chars,
    remove_excess_empty_lines,
    normalize_spaces,
    clean_adverts,
)

# Import all HTML processing functions for backward compatibility
from .html_processing import (
    extract_code_blocks,
    extract_inline_code,
    remove_html_comments,
    remove_script_and_style,
    replace_block_tags,
    remove_remaining_tags,
    unescape_non_code_with_placeholders,
    remove_html_markup,
)

# Re-export everything for backward compatibility
__all__ = [
    # Constants
    "PRESERVE_UNLIMITED",
    "CHINESE_PUNCTUATION",
    "ENGLISH_PUNCTUATION",
    "SENTENCE_ENDING",
    "CLOSING_QUOTES",
    "NON_BREAKING",
    "ALL_PUNCTUATION",
    # Text processing functions
    "clean",
    "replace_repeated_chars",
    "limit_repeated_chars",
    "remove_excess_empty_lines",
    "normalize_spaces",
    "clean_adverts",
    # HTML processing functions
    "extract_code_blocks",
    "extract_inline_code",
    "remove_html_comments",
    "remove_script_and_style",
    "replace_block_tags",
    "remove_remaining_tags",
    "unescape_non_code_with_placeholders",
    "remove_html_markup",
]
