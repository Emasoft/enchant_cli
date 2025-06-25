#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
# - Initial creation from renamenovels.py refactoring
# - Extracted file processing and renaming logic
# - Contains functions for processing novel files and renaming
#

"""
rename_file_processor.py - File processing utilities for novel renaming
======================================================================

Handles file processing, metadata extraction, and renaming operations
for the novel renaming phase of the ENCHANT system.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from json import JSONDecodeError
from typing import Any, cast

from .common_file_utils import decode_full_file
from .common_utils import sanitize_filename as common_sanitize_filename
from .icloud_sync import ICloudSync, ICloudSyncError
from .rename_api_client import RenameAPIClient

logger = logging.getLogger(__name__)

# Constants
MIN_FILE_SIZE_KB = 100
CONTENT_NUMBER_OF_CHARACTERS_HARD_LIMIT = 1500
DEFAULT_KB_TO_READ = 35


def find_text_files(folder_path: Path, recursive: bool) -> list[Path]:
    """
    Find all eligible text files in a given folder.

    Filters out hidden files and files smaller than MIN_FILE_SIZE_KB.

    Args:
        folder_path: Directory to search in
        recursive: Whether to search subdirectories

    Returns:
        List of Path objects for eligible text files
    """
    txt_files = []

    if recursive:
        files = folder_path.rglob("*.txt")
    else:
        files = folder_path.glob("*.txt")

    for file_path in files:
        if file_path.is_file() and not file_path.name.startswith(".") and file_path.stat().st_size >= MIN_FILE_SIZE_KB * 1024:
            txt_files.append(file_path)

    return txt_files


def decode_file_content(file_path: Path, kb_to_read: int, icloud_sync: ICloudSync) -> str | None:
    """
    Decode file content using common_file_utils with size limit.

    Args:
        file_path: Path to the file to decode
        kb_to_read: KB to read from file start
        icloud_sync: iCloud sync handler

    Returns:
        Decoded content or None if failed
    """
    try:
        synced_path = icloud_sync.ensure_synced(file_path)
    except ICloudSyncError as e:
        logger.error(f"iCloud synchronization failed for '{file_path}': {e}")
        return None

    try:
        # Use the common file utils with size limit
        content = decode_full_file(synced_path, logger=logger)

        if content and kb_to_read:
            # Limit to requested size (approximate character limit)
            char_limit = kb_to_read * 1024  # Rough character estimate
            if len(content) > char_limit:
                content = content[:char_limit]

        return content

    except Exception as e:
        logger.error(f"Failed to decode file '{synced_path}': {e}")
        return None


def extract_json(response_content: str) -> dict[str, Any] | None:
    """
    Attempt to extract JSON from a string.

    Args:
        response_content: String potentially containing JSON

    Returns:
        Extracted dictionary or None if extraction failed
    """
    try:
        return cast(dict[str, Any], json.loads(response_content))
    except JSONDecodeError:
        # Attempt to extract JSON using regex
        json_str_match = re.search(r"\{.*\}", response_content, re.DOTALL)
        if json_str_match:
            try:
                return cast(dict[str, Any], json.loads(json_str_match.group()))
            except JSONDecodeError:
                logger.error("Failed to parse JSON from the extracted string.")
                return None
        else:
            logger.error("No JSON object found in the response content.")
            return None


def create_new_filename(metadata: dict[str, Any]) -> str:
    """
    Create a new filename based on extracted metadata.

    Args:
        metadata: Dictionary containing novel metadata

    Returns:
        New filename string
    """
    title_eng = common_sanitize_filename(metadata.get("novel_title_english", "Unknown Title"))
    author_eng = common_sanitize_filename(metadata.get("author_name_english", "Unknown Author"))
    author_roman = common_sanitize_filename(metadata.get("author_name_romanized", "Unknown"))
    title_orig = common_sanitize_filename(metadata.get("novel_title_original", "Unknown"))
    author_orig = common_sanitize_filename(metadata.get("author_name_original", "Unknown"))

    return f"{title_eng} by {author_eng} ({author_roman}) - {title_orig} by {author_orig}.txt"


def rename_file_with_metadata(file_path: Path, metadata: dict[str, Any]) -> Path:
    """
    Rename file based on extracted novel metadata.

    Creates filename in format: "Title by Author (Romanized) - Original Title by Original Author.txt"
    Handles naming collisions by appending a counter.

    Args:
        file_path: Path to the file to rename
        metadata: Dictionary containing novel metadata

    Returns:
        New path after renaming
    """
    new_name = create_new_filename(metadata)
    new_path = file_path.with_name(new_name)

    # Ensure uniqueness if there are naming collisions
    counter = 1
    while new_path.exists():
        base_name = new_name.rsplit(".", 1)[0]
        new_name = f"{base_name} ({counter}).txt"
        new_path = file_path.with_name(new_name)
        counter += 1

    logger.info(f"Renaming '{file_path}' to '{new_path}'")
    try:
        file_path.rename(new_path)
        return new_path
    except OSError as e:
        logger.error(f"Failed to rename '{file_path}' to '{new_path}': {e}")
        return file_path


def validate_metadata(metadata: dict[str, Any]) -> bool:
    """
    Validate that metadata contains all required keys.

    Args:
        metadata: Dictionary to validate

    Returns:
        True if valid, False otherwise
    """
    required_keys = [
        "detected_language",
        "novel_title_original",
        "author_name_original",
        "novel_title_english",
        "author_name_english",
        "author_name_romanized",
    ]
    return all(key in metadata for key in required_keys)


def process_novel_file(
    file_path: Path,
    api_client: RenameAPIClient,
    dry_run: bool = False,
) -> tuple[bool, Path, dict[str, Any]]:
    """
    Process a single novel file to extract metadata and rename it.

    Args:
        file_path: Path to the novel file
        api_client: API client for metadata extraction
        dry_run: If True, don't actually rename the file (default: False)

    Returns:
        tuple: (success: bool, new_path: Path, metadata: dict)
    """
    try:
        # Initialize iCloud sync
        icloud_sync = ICloudSync(enabled=False)  # Set based on config
        kb_to_read = DEFAULT_KB_TO_READ

        # Decode file content
        content = decode_file_content(file_path, kb_to_read, icloud_sync)
        if content is None:
            logger.error(f"Failed to decode file content for {file_path}")
            return False, file_path, {}

        # Extract metadata using API
        response_content = api_client.extract_metadata(content, CONTENT_NUMBER_OF_CHARACTERS_HARD_LIMIT)
        if response_content is None:
            return False, file_path, {}

        # Parse response
        metadata = extract_json(response_content)
        if metadata is None:
            logger.error(f"Failed to extract JSON data from API response for file {file_path}.")
            return False, file_path, {}

        # Validate metadata
        if not validate_metadata(metadata):
            logger.error(f"Missing keys in response data for file {file_path}: {metadata}")
            return False, file_path, {}

        # Determine new file path
        if not dry_run:
            new_path = rename_file_with_metadata(file_path, metadata)
        else:
            new_name = create_new_filename(metadata)
            new_path = file_path.with_name(new_name)
            logger.info(f"Dry run: Would rename '{file_path}' to '{new_path}'")

        return True, new_path, metadata

    except Exception as e:
        logger.error(f"Error processing novel file {file_path}: {e}")
        return False, file_path, {}
