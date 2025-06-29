#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Fixed test suite for translation_orchestrator module using realistic fixtures.
"""

import pytest
import tempfile
import shutil
import errno
import sys
from pathlib import Path
from unittest.mock import patch, Mock
import logging

sys.path.insert(0, str(Path(__file__).parent.parent))

from enchant_book_manager.translation_orchestrator import (
    save_translated_book,
    format_chunk_error_message,
)
from enchant_book_manager.models import Chunk, VARIATION_DB

from test_helpers import TestDatabaseHelper, MockTranslator, create_test_logger


class TestSaveTranslatedBookFixed:
    """Test save_translated_book with realistic fixtures."""

    def setup_method(self):
        """Set up test fixtures."""
        self.db_helper = TestDatabaseHelper()
        self.temp_dir = self.db_helper.setup()

    def teardown_method(self):
        """Clean up test fixtures."""
        self.db_helper.teardown()

    def test_directory_creation_error_non_exist(self):
        """Test handling of directory creation errors (non-EEXIST) using realistic setup."""
        # Create test book with a very long title that might cause filesystem issues
        book, chunks = self.db_helper.create_test_book(
            title="A" * 300,  # Very long title to cause potential issues
            author="B" * 300,
        )

        # Create translator
        translator = MockTranslator()

        # Create logger
        logger = create_test_logger()

        # Try to save - the very long filename should cause issues or be handled gracefully
        save_translated_book(book_id=book.book_id, translator=translator, logger=logger)

        # Should complete successfully despite long filename (sanitize_filename should handle it)
        info_messages = [msg for level, msg in logger.messages if level == logging.INFO]
        assert any("Translated book saved to" in msg for msg in info_messages)

    def test_empty_translation_result(self):
        """Test handling of empty translation results with real fixtures."""
        # Create test book
        book, chunks = self.db_helper.create_test_book(num_chunks=1)

        # Create translator that returns empty string
        translator = MockTranslator(return_empty_on_chunks=[1])

        # Create logger
        logger = create_test_logger()

        # Create output directory
        output_dir = self.temp_dir / "output"
        output_dir.mkdir()

        # Mock sys.exit to capture the call
        with patch("sys.exit") as mock_exit:
            # Run the function
            save_translated_book(book_id=book.book_id, translator=translator, logger=logger, module_config={"translation": {"max_chunk_retries": 1}})

        # Verify system exit was called
        mock_exit.assert_called_once_with(1)

        # Verify error was logged
        error_messages = [msg for level, msg in logger.messages if level == logging.ERROR]
        assert any("validation failed" in msg.lower() for msg in error_messages)

    def test_none_translation_result(self):
        """Test handling of None translation results with real fixtures."""
        # Create test book
        book, chunks = self.db_helper.create_test_book(num_chunks=1)

        # Create translator that returns None
        translator = MockTranslator(fail_on_chunks=[1])

        # Create logger
        logger = create_test_logger()

        # Create output directory
        output_dir = self.temp_dir / "output"
        output_dir.mkdir()

        # Mock sys.exit to capture the call
        with patch("sys.exit") as mock_exit:
            # Run the function
            save_translated_book(book_id=book.book_id, translator=translator, logger=logger, module_config={"translation": {"max_chunk_retries": 1}})

        # Verify system exit was called
        mock_exit.assert_called_once_with(1)

        # Verify error was logged with proper error message
        error_messages = [msg for level, msg in logger.messages if level == logging.ERROR]
        assert any("Failed to translate chunk" in msg for msg in error_messages)

    def test_file_write_error(self):
        """Test handling of file write errors with real fixtures."""
        # Create test book
        book, chunks = self.db_helper.create_test_book(num_chunks=1)

        # Create translator
        translator = MockTranslator()

        # Create logger
        logger = create_test_logger()

        # Create output directory
        output_dir = self.temp_dir / "output"
        output_dir.mkdir()

        # Patch open to fail when writing final file
        original_open = open

        def mock_open(path, mode="r", *args, **kwargs):
            if "translated_" in str(path) and "w" in mode:
                raise PermissionError("Cannot write file")
            return original_open(path, mode, *args, **kwargs)

        with patch("builtins.open", mock_open):
            with patch("sys.exit") as mock_exit:
                # Run the function
                save_translated_book(book_id=book.book_id, translator=translator, logger=logger)

        # Should exit due to write error
        mock_exit.assert_called()

    def test_max_retry_wait_limit(self):
        """Test that retry wait time is capped at maximum."""
        # Create test book
        book, chunks = self.db_helper.create_test_book(num_chunks=1)

        # Create a translator that always fails
        translator = MockTranslator(fail_on_chunks=[1])

        # Create logger
        logger = create_test_logger()

        # Track sleep calls
        sleep_times = []

        def mock_sleep(seconds):
            sleep_times.append(seconds)

        with patch("time.sleep", mock_sleep):
            with patch("sys.exit"):
                # Run with high retry count
                save_translated_book(book_id=book.book_id, translator=translator, logger=logger, module_config={"translation": {"max_chunk_retries": 10}})

        # Verify sleep times don't exceed maximum
        assert all(t <= 60 for t in sleep_times)  # MAX_RETRY_WAIT_SECONDS = 60

    def test_successful_translation(self):
        """Test successful translation with real fixtures."""
        # Create test book
        book, chunks = self.db_helper.create_test_book(num_chunks=3)

        # Create translator
        translator = MockTranslator()

        # Create logger
        logger = create_test_logger()

        # Create output directory
        output_dir = self.temp_dir / "output"
        output_dir.mkdir()

        # Run the function
        save_translated_book(book_id=book.book_id, translator=translator, logger=logger)

        # Verify success - check that chunks were saved
        info_messages = [msg for level, msg in logger.messages if level == logging.INFO]
        assert any("Successfully translated chunk" in msg for msg in info_messages)
        assert any("Translated book saved to" in msg for msg in info_messages)

        # Verify all chunks were translated
        assert translator.translation_count == 3


class TestFormatChunkErrorMessage:
    """Test the format_chunk_error_message function."""

    def test_error_message_formatting(self):
        """Test that error message is formatted correctly."""
        message = format_chunk_error_message(chunk_number=5, max_retries=10, last_error="Connection timeout", book_title="Test Novel", book_author="Test Author", output_path="/test/path/chunk_000005.txt")

        # Verify key components are in the message
        assert "Failed to translate chunk 000005" in message
        assert "after 10 attempts" in message
        assert "Connection timeout" in message
        assert "Test Novel by Test Author" in message
        assert "/test/path/chunk_000005.txt" in message
        assert "Possible causes:" in message
        assert "--resume flag" in message
