#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
common_utils.py - Shared utility functions for EnChANT modules
"""

import re
import unicodedata
from pathlib import Path
from typing import Dict, Any


def sanitize_filename(filename: str, max_length: int = 255) -> str:
    """
    Sanitize filename by removing/replacing invalid characters.
    This is the unified version used across all modules.
    """
    # Remove invalid characters for filenames
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, "_")

    # Replace multiple spaces with single space
    filename = re.sub(r"\s+", " ", filename)

    # Remove leading/trailing spaces and dots
    filename = filename.strip(". ")

    # Handle Unicode characters - normalize and remove non-ASCII if problematic
    filename = unicodedata.normalize("NFKD", filename)

    # Ensure filename doesn't exceed max length
    if len(filename) > max_length:
        # Keep extension if present
        parts = filename.rsplit(".", 1)
        if len(parts) == 2 and len(parts[1]) <= 4:  # Likely an extension
            name, ext = parts
            max_name_length = max_length - len(ext) - 1
            filename = name[:max_name_length] + "." + ext
        else:
            filename = filename[:max_length]

    # Ensure filename is not empty
    if not filename:
        filename = "unnamed"

    return filename


def extract_book_info_from_path(file_path: Path) -> Dict[str, Any]:
    """
    Extract book information from file path or directory name.
    Handles both the standard naming format and fallbacks.
    """
    info = {
        "title_english": "",
        "author_english": "",
        "author_romanized": "",
        "title_original": "",
        "author_original": "",
    }

    # Try to extract from filename first
    filename = file_path.stem if file_path.is_file() else file_path.name

    # Standard format: "English Title by English Author (Romanized Author) - Original Title by Original Author"
    pattern = r"^(.+?) by (.+?) \((.+?)\) - (.+?) by (.+?)$"
    match = re.match(pattern, filename)

    if match:
        info["title_english"] = match.group(1).strip()
        info["author_english"] = match.group(2).strip()
        info["author_romanized"] = match.group(3).strip()
        info["title_original"] = match.group(4).strip()
        info["author_original"] = match.group(5).strip()
    else:
        # Fallback: try simpler patterns
        # Pattern: "Title by Author"
        simple_pattern = r"^(.+?) by (.+?)$"
        match = re.match(simple_pattern, filename)

        if match:
            info["title_english"] = match.group(1).strip()
            info["author_english"] = match.group(2).strip()
        else:
            # Last resort: use filename as title
            info["title_english"] = filename
            info["author_english"] = "Unknown"

    return info
