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
common_utils.py - Shared utility functions for EnChANT modules
"""

import re
import unicodedata
import time
import sys
import os
import functools
from pathlib import Path
from typing import Any, TypeVar
from collections.abc import Callable
import logging

from .common_constants import (
    DEFAULT_MAX_RETRIES,
    DEFAULT_MAX_RETRIES_TEST,
    DEFAULT_RETRY_WAIT_MAX,
    DEFAULT_RETRY_WAIT_MAX_TEST,
)


def is_running_in_test() -> bool:
    """
    Detect if code is running in a test environment.

    Returns:
        True if running in a test environment, False otherwise
    """
    # Check if pytest is running
    if "pytest" in sys.modules:
        return True

    # Check for common test environment variables
    if os.environ.get("PYTEST_CURRENT_TEST"):
        return True

    # Check if running in CI/CD
    if os.environ.get("CI") or os.environ.get("GITHUB_ACTIONS"):
        return True

    return False


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


def extract_book_info_from_path(file_path: Path) -> dict[str, Any]:
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


def retry_with_backoff(
    max_attempts: int = 10,
    base_wait: float = 1.0,
    max_wait: float = 60.0,
    min_wait: float = 1.0,
    exception_types: tuple[type[Exception], ...] = (Exception,),
    time_limit: float | None = None,
    exit_on_failure: bool = False,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator for retrying functions with exponential backoff.

    This is a decorator version of exponential_backoff_retry for standardized retry logic.

    Args:
        max_attempts: Maximum number of attempts
        base_wait: Base wait time in seconds
        max_wait: Maximum wait time in seconds
        min_wait: Minimum wait time in seconds
        exception_types: Tuple of exception types to retry on
        time_limit: Optional total time limit in seconds
        exit_on_failure: If True, exit the program on failure (for critical operations)

    Returns:
        Decorator function
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            # Get logger from the first argument if it's a method with self.logger
            logger = None
            if args and hasattr(args[0], "logger"):
                logger = args[0].logger

            # Use test-specific values if running in test environment
            actual_max_attempts = max_attempts
            actual_max_wait = max_wait

            if is_running_in_test():
                # Use test-specific defaults if using default values
                if max_attempts == DEFAULT_MAX_RETRIES:
                    actual_max_attempts = DEFAULT_MAX_RETRIES_TEST
                if max_wait == DEFAULT_RETRY_WAIT_MAX:
                    actual_max_wait = DEFAULT_RETRY_WAIT_MAX_TEST

            try:
                result = exponential_backoff_retry(
                    func,
                    actual_max_attempts,
                    base_wait,
                    actual_max_wait,
                    min_wait,
                    exception_types,
                    logger,
                    None,  # on_retry
                    time_limit,
                    *args,
                    **kwargs,
                )
                return result
            except Exception as e:
                if exit_on_failure:
                    error_msg = f"Critical failure in {func.__name__} after {actual_max_attempts} attempts: {e}"
                    if logger:
                        logger.error(error_msg)
                    print(f"\\n❌ FATAL ERROR: {error_msg}")
                    sys.exit(1)
                else:
                    raise

        return wrapper

    return decorator


def exponential_backoff_retry(
    func: Callable[..., T],
    max_attempts: int = 10,
    base_wait: float = 1.0,
    max_wait: float = 60.0,
    min_wait: float = 1.0,
    exception_types: tuple[type[Exception], ...] = (Exception,),
    logger: logging.Logger | None = None,
    on_retry: Callable[[int, Exception, float], None] | None = None,
    time_limit: float | None = None,
    *args: Any,
    **kwargs: Any,
) -> T:
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
        Result of func if successful

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
                            logger.error(f"Time limit {time_limit}s exceeded after {attempt} attempts")
                        raise

            if logger:
                logger.warning(f"Attempt {attempt}/{max_attempts} failed: {e}. Retrying in {wait_time:.1f}s...")

            # Call optional retry callback
            if on_retry:
                on_retry(attempt, e, wait_time)

            time.sleep(wait_time)

    # This should not be reached, but just in case
    if last_exception:
        raise last_exception
    raise RuntimeError("Retry function failed without exception")
