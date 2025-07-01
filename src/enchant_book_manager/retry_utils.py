#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# HERE IS THE CHANGELOG FOR THIS VERSION OF THE FILE:
# - Created new retry_utils.py module with preset retry configurations
# - Added network_retry, file_io_retry, and database_retry decorators
# - Added api_retry decorator for API calls with custom timeout
# - All presets use the existing retry_with_backoff decorator
#

"""
retry_utils.py - Preset retry configurations for common scenarios

This module provides convenient preset retry decorators for common
operations like network requests, file I/O, and database operations.
"""

from typing import Callable, TypeVar
import requests
from .common_utils import retry_with_backoff
from .common_constants import (
    DEFAULT_MAX_RETRIES,
    DEFAULT_RETRY_WAIT_MIN,
    DEFAULT_RETRY_WAIT_MAX,
)
from .magic_constants import (
    RENAME_API_MAX_RETRY_WAIT,
    RENAME_API_TIMEOUT,
    DEFAULT_IO_RETRY_COUNT,
    DEFAULT_DB_RETRY_COUNT,
)

T = TypeVar("T")


def network_retry(
    max_attempts: int = DEFAULT_MAX_RETRIES,
    max_wait: float = DEFAULT_RETRY_WAIT_MAX,
    exit_on_failure: bool = False,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Retry decorator preset for network operations.

    Retries on common network errors: ConnectionError, Timeout, HTTPError.

    Args:
        max_attempts: Maximum retry attempts (default: 10)
        max_wait: Maximum wait between retries (default: 60s)
        exit_on_failure: Exit program on failure (default: False)

    Returns:
        Configured retry decorator

    Example:
        @network_retry()
        def fetch_data(url):
            return requests.get(url).json()
    """
    network_exceptions = (
        requests.ConnectionError,
        requests.Timeout,
        requests.HTTPError,
        ConnectionError,
        TimeoutError,
    )

    return retry_with_backoff(
        max_attempts=max_attempts,
        base_wait=DEFAULT_RETRY_WAIT_MIN,
        max_wait=max_wait,
        min_wait=DEFAULT_RETRY_WAIT_MIN,
        exception_types=network_exceptions,
        exit_on_failure=exit_on_failure,
    )


def file_io_retry(
    max_attempts: int = DEFAULT_IO_RETRY_COUNT,
    max_wait: float = 10.0,
    exit_on_failure: bool = False,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Retry decorator preset for file I/O operations.

    Retries on common file errors: OSError, PermissionError, IOError.

    Args:
        max_attempts: Maximum retry attempts (default: 5)
        max_wait: Maximum wait between retries (default: 10s)
        exit_on_failure: Exit program on failure (default: False)

    Returns:
        Configured retry decorator

    Example:
        @file_io_retry()
        def save_file(path, content):
            with open(path, 'w') as f:
                f.write(content)
    """
    file_exceptions = (
        OSError,
        PermissionError,
        IOError,
        FileNotFoundError,
    )

    return retry_with_backoff(
        max_attempts=max_attempts,
        base_wait=0.5,  # Shorter initial wait for file operations
        max_wait=max_wait,
        min_wait=0.5,
        exception_types=file_exceptions,
        exit_on_failure=exit_on_failure,
    )


def database_retry(
    max_attempts: int = DEFAULT_DB_RETRY_COUNT,
    max_wait: float = 20.0,
    exit_on_failure: bool = False,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Retry decorator preset for database operations.

    Retries on database-related errors including KeyError for our in-memory DB.

    Args:
        max_attempts: Maximum retry attempts (default: 3)
        max_wait: Maximum wait between retries (default: 20s)
        exit_on_failure: Exit program on failure (default: False)

    Returns:
        Configured retry decorator

    Example:
        @database_retry()
        def get_book(book_id):
            return Book.get_by_id(book_id)
    """
    db_exceptions = (
        KeyError,  # For our in-memory database
        RuntimeError,  # For thread conflicts
        Exception,  # Generic fallback
    )

    return retry_with_backoff(
        max_attempts=max_attempts,
        base_wait=1.0,
        max_wait=max_wait,
        min_wait=1.0,
        exception_types=db_exceptions,
        exit_on_failure=exit_on_failure,
    )


def api_retry(
    max_attempts: int = DEFAULT_MAX_RETRIES,
    max_wait: float = RENAME_API_MAX_RETRY_WAIT,
    timeout: float = RENAME_API_TIMEOUT,
    exit_on_failure: bool = False,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Retry decorator preset for API calls with timeout.

    Specifically configured for API operations with shorter timeouts.

    Args:
        max_attempts: Maximum retry attempts (default: 10)
        max_wait: Maximum wait between retries (default: 10s)
        timeout: Time limit for the entire retry operation (default: 10s)
        exit_on_failure: Exit program on failure (default: False)

    Returns:
        Configured retry decorator

    Example:
        @api_retry()
        def call_translation_api(text):
            return api.translate(text)
    """
    api_exceptions = (
        requests.ConnectionError,
        requests.Timeout,
        requests.HTTPError,
        ConnectionError,
        TimeoutError,
        ValueError,  # For API response parsing errors
        KeyError,  # For missing API response fields
    )

    return retry_with_backoff(
        max_attempts=max_attempts,
        base_wait=1.0,
        max_wait=max_wait,
        min_wait=1.0,
        exception_types=api_exceptions,
        time_limit=timeout,
        exit_on_failure=exit_on_failure,
    )


# Convenience aliases for common use cases
def critical_network_retry() -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Create a network retry decorator that exits on failure."""
    return network_retry(exit_on_failure=True)


def critical_file_retry() -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Create a file I/O retry decorator that exits on failure."""
    return file_io_retry(exit_on_failure=True)


def quick_retry() -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Create a quick retry decorator with reduced attempts and wait time."""
    return retry_with_backoff(max_attempts=3, max_wait=5.0)
