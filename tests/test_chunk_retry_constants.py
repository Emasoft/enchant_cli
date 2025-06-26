#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for chunk retry constants and configuration
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.enchant_book_manager.translation_orchestrator import (
    format_chunk_error_message,
    DEFAULT_MAX_CHUNK_RETRIES,
    MAX_RETRY_WAIT_SECONDS,
)


class TestChunkRetryConstants:
    """Test cases for chunk retry constants"""

    def test_default_constants_exist(self):
        """Test that default constants are defined"""
        assert DEFAULT_MAX_CHUNK_RETRIES is not None
        assert MAX_RETRY_WAIT_SECONDS is not None

    def test_default_values(self):
        """Test default constant values"""
        assert DEFAULT_MAX_CHUNK_RETRIES == 10
        assert MAX_RETRY_WAIT_SECONDS == 60

    def test_format_chunk_error_message_exists(self):
        """Test that error message formatter exists"""
        # Note: format_chunk_error_message moved to translation_orchestrator module
        assert format_chunk_error_message is not None
        assert callable(format_chunk_error_message)

    def test_format_chunk_error_message(self):
        """Test error message formatting"""
        msg = format_chunk_error_message(
            chunk_number=5,
            max_retries=10,
            last_error="Connection refused",
            book_title="Test Book",
            book_author="Test Author",
            output_path="test/path.txt",
        )

        assert "Failed to translate chunk 000005" in msg
        assert "10 attempts" in msg
        assert "Connection refused" in msg
        assert "Test Book by Test Author" in msg
        assert "test/path.txt" in msg
        assert "Possible causes:" in msg
        assert "--resume flag" in msg
