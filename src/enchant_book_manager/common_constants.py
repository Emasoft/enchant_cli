#!/usr/bin/env python3
# -*- coding: utf-8 -*-

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
Common constants used across multiple modules in the ENCHANT project.

This module centralizes shared constants to avoid duplication and ensure
consistency across the codebase.
"""

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

# Characters that are allowed unlimited repetition by default
# in the limit_repeated_chars function
PRESERVE_UNLIMITED = {
    "\n",  # Newline
    "\t",  # Tab
    " ",  # Space
    "\u3000",  # Full-width space
}

# Maximum characters per chunk for text processing
DEFAULT_MAX_CHARS = 12000

# Default retry settings
DEFAULT_MAX_RETRIES = 10
DEFAULT_MAX_RETRIES_TEST = 2  # Reduced retries for tests
DEFAULT_RETRY_WAIT_MIN = 1.0
DEFAULT_RETRY_WAIT_MAX = 60.0
DEFAULT_RETRY_WAIT_MAX_TEST = 5.0  # Reduced max wait for tests

# API URLs (can be overridden by configuration)
DEFAULT_OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_LMSTUDIO_API_URL = "http://localhost:1234/v1/chat/completions"

# File encoding defaults
DEFAULT_ENCODING = "utf-8"
DEFAULT_ENCODING_FALLBACKS = ["utf-8", "gbk", "gb18030", "big5", "shift_jis"]

# Confidence thresholds
MIN_ENCODING_CONFIDENCE = 0.7
MIN_TRANSLATION_LENGTH_RATIO = 0.3  # Minimum ratio of translated to original text

# File size limits
MIN_FILE_SIZE_KB = 35  # Minimum file size to process
MAX_FILE_SIZE_MB = 100  # Maximum file size to process

# Chapter detection patterns (common across modules)
CHAPTER_PATTERNS = {
    "english_numeric": r"chapter\s+\d+",
    "english_roman": r"chapter\s+[IVXLCDM]+",
    "chinese_numeric": r"第[一二三四五六七八九十百千万]+章",
    "chinese_arabic": r"第\d+章",
}
