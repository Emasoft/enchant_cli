#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test suite for common_constants module.
"""

import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from enchant_book_manager.common_constants import (
    PARAGRAPH_DELIMITERS,
    PRESERVE_UNLIMITED,
    DEFAULT_MAX_CHARS,
    DEFAULT_MAX_RETRIES,
    DEFAULT_MAX_RETRIES_TEST,
    DEFAULT_RETRY_WAIT_MIN,
    DEFAULT_RETRY_WAIT_MAX,
    DEFAULT_RETRY_WAIT_MAX_TEST,
    DEFAULT_OPENROUTER_API_URL,
    DEFAULT_LMSTUDIO_API_URL,
    DEFAULT_ENCODING,
    DEFAULT_ENCODING_FALLBACKS,
    MIN_ENCODING_CONFIDENCE,
    MIN_TRANSLATION_LENGTH_RATIO,
    MIN_FILE_SIZE_KB,
    MAX_FILE_SIZE_MB,
    CHAPTER_PATTERNS,
)


class TestCommonConstants:
    """Test all constants are properly defined and have expected values."""

    def test_paragraph_delimiters(self):
        """Test paragraph delimiter constants."""
        assert isinstance(PARAGRAPH_DELIMITERS, set)
        assert "\n" in PARAGRAPH_DELIMITERS
        assert "\v" in PARAGRAPH_DELIMITERS
        assert "\f" in PARAGRAPH_DELIMITERS
        assert "\x1c" in PARAGRAPH_DELIMITERS
        assert "\x1d" in PARAGRAPH_DELIMITERS
        assert "\x1e" in PARAGRAPH_DELIMITERS
        assert "\x85" in PARAGRAPH_DELIMITERS
        assert "\u2028" in PARAGRAPH_DELIMITERS
        assert "\u2029" in PARAGRAPH_DELIMITERS
        assert len(PARAGRAPH_DELIMITERS) == 9

    def test_preserve_unlimited(self):
        """Test preserve unlimited characters set."""
        assert isinstance(PRESERVE_UNLIMITED, set)
        assert "\n" in PRESERVE_UNLIMITED
        assert "\t" in PRESERVE_UNLIMITED
        assert " " in PRESERVE_UNLIMITED
        assert "\u3000" in PRESERVE_UNLIMITED  # Full-width space
        assert len(PRESERVE_UNLIMITED) == 4

    def test_default_max_chars(self):
        """Test default max characters constant."""
        assert isinstance(DEFAULT_MAX_CHARS, int)
        assert DEFAULT_MAX_CHARS == 12000
        assert DEFAULT_MAX_CHARS > 0

    def test_retry_constants(self):
        """Test retry-related constants."""
        assert isinstance(DEFAULT_MAX_RETRIES, int)
        assert DEFAULT_MAX_RETRIES == 10
        assert DEFAULT_MAX_RETRIES > 0

        assert isinstance(DEFAULT_MAX_RETRIES_TEST, int)
        assert DEFAULT_MAX_RETRIES_TEST == 2
        assert DEFAULT_MAX_RETRIES_TEST < DEFAULT_MAX_RETRIES

        assert isinstance(DEFAULT_RETRY_WAIT_MIN, float)
        assert DEFAULT_RETRY_WAIT_MIN == 1.0
        assert DEFAULT_RETRY_WAIT_MIN > 0

        assert isinstance(DEFAULT_RETRY_WAIT_MAX, float)
        assert DEFAULT_RETRY_WAIT_MAX == 60.0
        assert DEFAULT_RETRY_WAIT_MAX > DEFAULT_RETRY_WAIT_MIN

        assert isinstance(DEFAULT_RETRY_WAIT_MAX_TEST, float)
        assert DEFAULT_RETRY_WAIT_MAX_TEST == 5.0
        assert DEFAULT_RETRY_WAIT_MAX_TEST < DEFAULT_RETRY_WAIT_MAX

    def test_api_urls(self):
        """Test API URL constants."""
        assert isinstance(DEFAULT_OPENROUTER_API_URL, str)
        assert DEFAULT_OPENROUTER_API_URL == "https://openrouter.ai/api/v1/chat/completions"
        assert DEFAULT_OPENROUTER_API_URL.startswith("https://")
        assert "openrouter.ai" in DEFAULT_OPENROUTER_API_URL

        assert isinstance(DEFAULT_LMSTUDIO_API_URL, str)
        assert DEFAULT_LMSTUDIO_API_URL == "http://localhost:1234/v1/chat/completions"
        assert DEFAULT_LMSTUDIO_API_URL.startswith("http://")
        assert "localhost" in DEFAULT_LMSTUDIO_API_URL

    def test_encoding_constants(self):
        """Test encoding-related constants."""
        assert isinstance(DEFAULT_ENCODING, str)
        assert DEFAULT_ENCODING == "utf-8"

        assert isinstance(DEFAULT_ENCODING_FALLBACKS, list)
        assert len(DEFAULT_ENCODING_FALLBACKS) == 5
        assert "utf-8" in DEFAULT_ENCODING_FALLBACKS
        assert "gbk" in DEFAULT_ENCODING_FALLBACKS
        assert "gb18030" in DEFAULT_ENCODING_FALLBACKS
        assert "big5" in DEFAULT_ENCODING_FALLBACKS
        assert "shift_jis" in DEFAULT_ENCODING_FALLBACKS

    def test_confidence_thresholds(self):
        """Test confidence threshold constants."""
        assert isinstance(MIN_ENCODING_CONFIDENCE, float)
        assert MIN_ENCODING_CONFIDENCE == 0.7
        assert 0 < MIN_ENCODING_CONFIDENCE <= 1

        assert isinstance(MIN_TRANSLATION_LENGTH_RATIO, float)
        assert MIN_TRANSLATION_LENGTH_RATIO == 0.3
        assert 0 < MIN_TRANSLATION_LENGTH_RATIO <= 1

    def test_file_size_limits(self):
        """Test file size limit constants."""
        assert isinstance(MIN_FILE_SIZE_KB, int)
        assert MIN_FILE_SIZE_KB == 35
        assert MIN_FILE_SIZE_KB > 0

        assert isinstance(MAX_FILE_SIZE_MB, int)
        assert MAX_FILE_SIZE_MB == 100
        assert MAX_FILE_SIZE_MB > 0
        assert MAX_FILE_SIZE_MB * 1024 > MIN_FILE_SIZE_KB  # Max should be larger than min

    def test_chapter_patterns(self):
        """Test chapter pattern constants."""
        assert isinstance(CHAPTER_PATTERNS, dict)
        assert len(CHAPTER_PATTERNS) == 4

        assert "english_numeric" in CHAPTER_PATTERNS
        assert CHAPTER_PATTERNS["english_numeric"] == r"chapter\s+\d+"

        assert "english_roman" in CHAPTER_PATTERNS
        assert CHAPTER_PATTERNS["english_roman"] == r"chapter\s+[IVXLCDM]+"

        assert "chinese_numeric" in CHAPTER_PATTERNS
        assert CHAPTER_PATTERNS["chinese_numeric"] == r"第[一二三四五六七八九十百千万]+章"

        assert "chinese_arabic" in CHAPTER_PATTERNS
        assert CHAPTER_PATTERNS["chinese_arabic"] == r"第\d+章"

    def test_constants_immutability(self):
        """Test that constants are not accidentally mutable."""
        # Sets and dicts are mutable, but we shouldn't modify them
        original_delimiters = PARAGRAPH_DELIMITERS.copy()
        original_preserve = PRESERVE_UNLIMITED.copy()
        original_patterns = CHAPTER_PATTERNS.copy()

        # Verify they haven't been modified
        assert PARAGRAPH_DELIMITERS == original_delimiters
        assert PRESERVE_UNLIMITED == original_preserve
        assert CHAPTER_PATTERNS == original_patterns

    def test_constants_relationships(self):
        """Test relationships between related constants."""
        # Test wait time should be less than production wait time
        assert DEFAULT_RETRY_WAIT_MAX_TEST < DEFAULT_RETRY_WAIT_MAX

        # Test retries should be less than production retries
        assert DEFAULT_MAX_RETRIES_TEST < DEFAULT_MAX_RETRIES

        # Min wait should be less than max wait
        assert DEFAULT_RETRY_WAIT_MIN < DEFAULT_RETRY_WAIT_MAX
        assert DEFAULT_RETRY_WAIT_MIN < DEFAULT_RETRY_WAIT_MAX_TEST

        # File size relationship
        assert MIN_FILE_SIZE_KB < MAX_FILE_SIZE_MB * 1024
