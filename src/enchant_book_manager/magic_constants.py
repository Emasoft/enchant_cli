#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# HERE IS THE CHANGELOG FOR THIS VERSION OF THE FILE:
# - Initial creation to consolidate magic numbers found in the codebase
# - Added constants for iCloud sync timeouts and intervals
# - Added constants for file processing sizes and limits
# - Added constants for API configuration defaults
# - Added constants for text validation thresholds
# - Added constants for filename length limits
#

"""
magic_constants.py - Additional constants to replace magic numbers
=================================================================

This module contains constants that were previously hardcoded as magic
numbers throughout the codebase. These constants improve code maintainability
and make the purpose of each value clear.
"""

# iCloud Sync Configuration
# ------------------------
# Timeout for syncing entire folders from iCloud (5 minutes)
ICLOUD_FOLDER_SYNC_TIMEOUT = 300

# Interval between checks for folder sync status (seconds)
ICLOUD_FOLDER_SYNC_CHECK_INTERVAL = 2

# Timeout for downloading individual files from iCloud (2 minutes)
ICLOUD_FILE_SYNC_TIMEOUT = 120

# Interval between checks for file download status (seconds)
ICLOUD_FILE_SYNC_CHECK_INTERVAL = 1

# File Processing Configuration
# ----------------------------
# Default sample size for encoding detection (32KB)
DEFAULT_SAMPLE_SIZE_KB = 32

# Number of bytes in a kilobyte
BYTES_PER_KB = 1024

# Default character limit for content preview
DEFAULT_CONTENT_CHAR_LIMIT = 1500

# Database Operations
# ------------------
# Batch size for bulk database insertions
DB_INSERT_BATCH_SIZE = 1000

# API Configuration
# ----------------
# Default temperature for translation requests (deterministic)
DEFAULT_TRANSLATION_TEMPERATURE = 0.1

# Default timeout for rename API requests (seconds)
RENAME_API_TIMEOUT = 10

# Maximum wait time for rename API retries (seconds)
RENAME_API_MAX_RETRY_WAIT = 10.0

# Filename Length Limits
# ---------------------
# Maximum length for short filename components (title, author)
MAX_FILENAME_LENGTH_SHORT = 50

# Maximum length for full filename (complete path)
MAX_FILENAME_LENGTH_FULL = 100

# Default maximum filename length (OS limit)
DEFAULT_MAX_FILENAME_LENGTH = 255

# Text Validation Configuration
# ----------------------------
# Default threshold for Latin charset validation (10% non-Latin allowed)
DEFAULT_LATIN_CHARSET_THRESHOLD = 0.1

# Strict threshold for Latin charset validation (5% non-Latin allowed)
STRICT_LATIN_CHARSET_THRESHOLD = 0.05

# Maximum allowed consecutive character repetitions
DEFAULT_MAX_CHAR_REPETITIONS = 4

# Maximum number of Chinese characters to show in error messages
MAX_CHINESE_CHARS_IN_ERROR = 10

# Text Processing Configuration
# ----------------------------
# Maximum repeated characters to display (e.g., "..." instead of "............")
MAX_REPEATED_CHAR_DISPLAY = 3

# Default maximum consecutive empty lines allowed
DEFAULT_MAX_EMPTY_LINES = 2

# Temperature Validation
# ---------------------
# Maximum allowed temperature value for AI models
MAX_TEMPERATURE_VALUE = 2.0

# Retry Configuration
# ------------------
# Default retry count for I/O operations
DEFAULT_IO_RETRY_COUNT = 5

# Default retry count for database operations
DEFAULT_DB_RETRY_COUNT = 3

# Minimum temperature value (fully deterministic)
MIN_TEMPERATURE_VALUE = 0.0

# Time Calculation Adjustments
# ---------------------------
# Buffer time subtracted from time limits to ensure operations complete
TIME_LIMIT_BUFFER_SECONDS = 1

# UI Progress Display
# ------------------
# Default TOC starting depth
DEFAULT_TOC_START_DEPTH = 1

# CSS Default Values
# -----------------
# Note: These are kept as strings since they're CSS values, not Python numbers
CSS_MAX_WIDTH_PERCENT = "100%"
CSS_LINE_HEIGHT = "1.4"
CSS_BODY_MARGIN = "5%"
CSS_H1_MARGIN = "2em 0 1em"
CSS_PARAGRAPH_INDENT = "1.5em"
CSS_PARAGRAPH_MARGIN = "0 0 1em"
