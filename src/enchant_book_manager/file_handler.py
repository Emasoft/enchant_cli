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
# - Extracted file handling functions from cli_translator.py
# - Added text file loading and saving
# - Added encoding detection wrappers
# - Integrated iCloud sync support
#

"""File handling utilities for the EnChANT Book Manager."""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Any

from .common_text_utils import clean
from .common_file_utils import (
    decode_full_file,
    detect_file_encoding as common_detect_encoding,
)
from .icloud_sync import ensure_synced


def load_text_file(txt_file_name: str | Path, logger: Optional[Any] = None) -> str | None:
    """
    Load text file contents.

    Args:
        txt_file_name: Path to the text file
        logger: Optional logger for debug output

    Returns:
        File contents as string, or None if file cannot be read
    """
    contents = None
    txt_file_name = Path.joinpath(Path.cwd(), Path(txt_file_name))
    if Path.is_file(txt_file_name):
        try:
            with open(txt_file_name, encoding="utf8") as f:
                contents = f.read()
                if logger is not None:
                    logger.debug(contents)
            return contents
        except (OSError, PermissionError) as e:
            if logger is not None:
                logger.error(f"Error reading file {txt_file_name}: {e}")
            return None
    else:
        if logger is not None:
            logger.debug("Error : " + str(txt_file_name) + " is not a valid file!")
        return None


def save_text_file(text: str, filename: str | Path, logger: Optional[Any] = None) -> None:
    """
    Save text to a file.

    Args:
        text: Text content to save
        filename: Path where to save the file
        logger: Optional logger for debug output

    Raises:
        OSError: If file cannot be saved
        PermissionError: If insufficient permissions
    """
    file_path = Path(Path.joinpath(Path.cwd(), Path(filename)))
    try:
        with open(file_path, "wt", encoding="utf-8") as f:
            f.write(clean(text))
        if logger is not None:
            logger.debug("Saved text file in: " + str(file_path))
    except (OSError, PermissionError) as e:
        if logger is not None:
            logger.error(f"Error saving file {file_path}: {e}")
        raise


def decode_input_file_content(input_file: Path, logger: Optional[Any] = None) -> str:
    """
    Decode file content with automatic encoding detection.

    Uses common file utilities for consistent encoding detection across modules.
    Ensures file is synced from iCloud if needed.

    Args:
        input_file: Path to the file to decode
        logger: Optional logger for debug output

    Returns:
        Decoded file content as string
    """
    # Ensure file is synced from iCloud if needed
    input_file = ensure_synced(input_file)

    # Use common file utility for decoding
    return decode_full_file(input_file, logger=logger)


def detect_file_encoding(file_path: Path, logger: Optional[Any] = None) -> str:
    """
    Detect the encoding of a file.

    Uses common file utilities for consistent encoding detection.

    Args:
        file_path: Path to the file to analyze
        logger: Optional logger for debug output

    Returns:
        Detected encoding name (defaults to 'utf-8' on error)
    """
    # Ensure file is synced from iCloud if needed
    file_path = ensure_synced(file_path)

    # Use common detection with universal method for compatibility
    encoding, _ = common_detect_encoding(file_path, method="universal", logger=logger)
    return encoding
