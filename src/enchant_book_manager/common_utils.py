#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
common_utils.py - Shared utility functions for EnChANT modules
"""

import re
import unicodedata
import time
from pathlib import Path
from typing import Dict, Any, Optional, Callable, TypeVar
import logging


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


T = TypeVar("T")


def exponential_backoff_retry(
    func: Callable[..., T],
    max_attempts: int = 10,
    base_wait: float = 1.0,
    max_wait: float = 60.0,
    min_wait: float = 1.0,
    exception_types: tuple[type[Exception], ...] = (Exception,),
    logger: Optional[logging.Logger] = None,
    on_retry: Optional[Callable[[int, Exception, float], None]] = None,
    time_limit: Optional[float] = None,
    *args,
    **kwargs,
) -> Optional[T]:
    """
    Generic retry function with exponential backoff.

    Args:
        func: Function to retry
        max_attempts: Maximum number of attempts
        base_wait: Base wait time in seconds
        max_wait: Maximum wait time in seconds
        min_wait: Minimum wait time in seconds
        exception_types: Tuple of exception types to catch and retry
        logger: Optional logger for debug messages
        on_retry: Optional callback function called on each retry with (attempt, exception, wait_time)
        time_limit: Optional total time limit in seconds
        *args: Arguments to pass to func
        **kwargs: Keyword arguments to pass to func

    Returns:
        Result of func if successful, None if all attempts failed

    Raises:
        Exception: Re-raises the last exception if all attempts fail
    """
    start_time = time.time()
    last_exception = None

    for attempt in range(1, max_attempts + 1):
        try:
            return func(*args, **kwargs)
        except exception_types as e:
            last_exception = e

            if attempt >= max_attempts:
                if logger:
                    logger.error(f"All {max_attempts} attempts failed. Last error: {e}")
                raise

            # Calculate wait time with exponential backoff
            wait_time = min(base_wait * (2 ** (attempt - 1)), max_wait)
            wait_time = max(wait_time, min_wait)

            # Check time limit if specified
            if time_limit:
                elapsed = time.time() - start_time
                if elapsed + wait_time >= time_limit:
                    wait_time = max(0, time_limit - elapsed - 1)
                    if wait_time <= 0:
                        if logger:
                            logger.error(
                                f"Time limit {time_limit}s exceeded after {attempt} attempts"
                            )
                        raise

            if logger:
                logger.warning(
                    f"Attempt {attempt}/{max_attempts} failed: {e}. Retrying in {wait_time:.1f}s..."
                )

            # Call optional retry callback
            if on_retry:
                on_retry(attempt, e, wait_time)

            time.sleep(wait_time)

    # This should not be reached, but just in case
    if last_exception:
        raise last_exception
    return None
