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
Shared constants and utilities for EPUB modules.
Extracted to avoid code duplication.
"""

import re
from typing import Optional

# Constants
ENCODING = "utf-8"
MIMETYPE = "application/epub+zip"

# Word numbers for conversion
WORD_NUMS = "one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred|thousand"

# Regex patterns
FILENAME_RE = re.compile(
    r"^(?P<title>.+?)\s+by\s+(?P<author>.+?)\s+-\s+Chapter\s+(?P<num>\d+)\.txt$",
    re.IGNORECASE,
)

# Conversion tables
_SINGLE = {
    "zero": 0,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
}

_TENS = {
    "twenty": 20,
    "thirty": 30,
    "forty": 40,
    "fifty": 50,
    "sixty": 60,
    "seventy": 70,
    "eighty": 80,
    "ninety": 90,
}

_SCALES = {"hundred": 100, "thousand": 1000}
_ROMAN = {"i": 1, "v": 5, "x": 10, "l": 50, "c": 100, "d": 500, "m": 1000}


def roman_to_int(s: str) -> int:
    """Convert Roman numerals to integer."""
    total = prev = 0
    for ch in reversed(s.lower()):
        if ch not in _ROMAN:
            raise ValueError(f"Invalid Roman numeral character: {ch}")
        val = _ROMAN[ch]
        total = total - val if val < prev else total + val
        prev = val
    return total


def words_to_int(text: str) -> int:
    """Convert word numbers to integer."""
    tokens = re.split(r"[ \t\-]+", text.lower())
    total = curr = 0
    for tok in tokens:
        if tok in _SINGLE:
            curr += _SINGLE[tok]
        elif tok in _TENS:
            curr += _TENS[tok]
        elif tok in _SCALES:
            curr = max(curr, 1) * _SCALES[tok]
            if tok == "thousand":
                total += curr
                curr = 0
        else:
            raise ValueError(f"Unknown word number: {tok}")
    return total + curr


def parse_num(raw: str) -> int | None:
    """Parse various number formats to integer."""
    # Handle letter suffixes like "14a", "14b"
    if raw and raw[0].isdigit():
        # Extract just the numeric part
        num_part = "".join(c for c in raw if c.isdigit())
        if num_part:
            return int(num_part)

    if raw.isdigit():
        return int(raw)
    if re.fullmatch(r"[ivxlcdm]+", raw, re.IGNORECASE):
        return roman_to_int(raw)
    try:
        return words_to_int(raw)
    except ValueError:
        return None
