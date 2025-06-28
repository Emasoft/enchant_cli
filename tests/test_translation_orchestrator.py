#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test suite for translation_orchestrator module.
"""

import pytest
import logging
import sys
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, mock_open, call
import errno

sys.path.insert(0, str(Path(__file__).parent.parent))

from enchant_book_manager.translation_orchestrator import (
    format_chunk_error_message,
    save_translated_book,
    DEFAULT_MAX_CHUNK_RETRIES,
    MAX_RETRY_WAIT_SECONDS,
)
from enchant_book_manager.models import Book, Chunk, Variation


class TestFormatChunkErrorMessage:
    """Test the format_chunk_error_message function."""

    def test_format_error_message_complete(self):
        """Test formatting a complete error message with all details."""
        message = format_chunk_error_message(chunk_number=42, max_retries=10, last_error="Connection timeout", book_title="Test Book", book_author="Test Author", output_path="/path/to/chunk_000042.txt")

        # Check key elements are present
        assert "chunk 000042" in message
        assert "after 10 attempts" in message
        assert "Connection timeout" in message
        assert "Test Book by Test Author" in message
        assert "/path/to/chunk_000042.txt" in message
        assert "Possible causes:" in message
        assert "Translation API is unreachable" in message
        assert "--resume flag" in message

    def test_format_error_message_escaping(self):
        """Test that special characters in inputs are handled properly."""
        message = format_chunk_error_message(chunk_number=1, max_retries=3, last_error="Error: 'test' failed\n\twith newlines", book_title='Book\'s "Title"', book_author="O'Author", output_path="C:\\path\\to\\file.txt")

        # Check that special characters are preserved
        assert "'test' failed" in message
        assert "with newlines" in message
        assert 'Book\'s "Title"' in message
        assert "O'Author" in message
        assert "C:\\path\\to\\file.txt" in message


class TestSaveTranslatedBook:
    """Test the save_translated_book function."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create mock book
        self.mock_book = Mock(spec=Book)
        self.mock_book.id = "test_book_id"
        self.mock_book.translated_title = "Test Book"
        self.mock_book.translated_author = "Test Author"

        # Create mock chunks
        self.mock_chunk1 = Mock(spec=Chunk)
        self.mock_chunk1.chunk_number = 1
        self.mock_chunk1.original_variation_id = "var1"

        self.mock_chunk2 = Mock(spec=Chunk)
        self.mock_chunk2.chunk_number = 2
        self.mock_chunk2.original_variation_id = "var2"

        self.mock_book.chunks = [self.mock_chunk1, self.mock_chunk2]

        # Create mock variations
        self.mock_var1 = Mock(spec=Variation)
        self.mock_var1.text_content = "Original text 1"

        self.mock_var2 = Mock(spec=Variation)
        self.mock_var2.text_content = "Original text 2"

        # Create mock translator
        self.mock_translator = Mock()
        self.mock_translator.translate.side_effect = ["Translated text 1", "Translated text 2"]

    @patch("enchant_book_manager.translation_orchestrator.Book")
    @patch("enchant_book_manager.translation_orchestrator.VARIATION_DB")
    @patch("enchant_book_manager.translation_orchestrator.Path")
    @patch("enchant_book_manager.translation_orchestrator.save_translation_cost_log")
    @patch("enchant_book_manager.translation_orchestrator.prepare_for_write")
    @patch("enchant_book_manager.translation_orchestrator.remove_excess_empty_lines")
    def test_successful_translation(self, mock_remove_lines, mock_prepare, mock_save_cost, mock_path, mock_var_db, mock_book_class):
        """Test successful translation of a book."""
        # Setup mocks
        mock_book_class.get_by_id.return_value = self.mock_book
        mock_var_db.get.side_effect = [self.mock_var1, self.mock_var2]

        # Mock path operations
        mock_book_dir = MagicMock()
        mock_book_dir.mkdir.return_value = None
        mock_book_dir.glob.return_value = []
        mock_path.return_value = mock_book_dir
        mock_path.cwd.return_value = Path("/current/dir")

        # Mock file operations
        mock_chunk_file1 = MagicMock()
        mock_chunk_file2 = MagicMock()
        mock_output_file = MagicMock()

        # Create proper side effects for Path division operations
        def mock_division(name):
            if "Chunk_000001.txt" in str(name):
                return mock_chunk_file1
            elif "Chunk_000002.txt" in str(name):
                return mock_chunk_file2
            else:
                return mock_output_file

        mock_book_dir.__truediv__.side_effect = mock_division

        mock_prepare.return_value = mock_output_file
        mock_remove_lines.return_value = "\nTranslated text 1\n\nTranslated text 2\n"

        mock_logger = Mock()

        # Execute
        with patch("builtins.open", mock_open()) as mock_file:
            save_translated_book(book_id="test_book_id", translator=self.mock_translator, resume=False, logger=mock_logger)

        # Verify
        mock_book_class.get_by_id.assert_called_once_with("test_book_id")
        assert mock_var_db.get.call_count == 2
        assert self.mock_translator.translate.call_count == 2

        # Verify chunks were written
        assert mock_chunk_file1.write_text.call_count == 1
        assert mock_chunk_file2.write_text.call_count == 1

        # Verify final file was written
        mock_file.assert_called_once()
        handle = mock_file()
        handle.write.assert_called_once()

        # Verify cost logging
        mock_save_cost.assert_called_once()

    @patch("enchant_book_manager.translation_orchestrator.Book")
    def test_book_not_found(self, mock_book_class):
        """Test handling when book is not found."""
        mock_book_class.get_by_id.return_value = None

        with pytest.raises(ValueError, match="Book not found"):
            save_translated_book(book_id="nonexistent", translator=self.mock_translator)

    @patch("enchant_book_manager.translation_orchestrator.Book")
    @patch("enchant_book_manager.translation_orchestrator.VARIATION_DB")
    @patch("enchant_book_manager.translation_orchestrator.Path")
    @patch("enchant_book_manager.translation_orchestrator.sys.exit")
    @patch("enchant_book_manager.translation_orchestrator.time.sleep")
    @patch("enchant_book_manager.translation_orchestrator.prepare_for_write")
    @patch("enchant_book_manager.translation_orchestrator.save_translation_cost_log")
    def test_translation_retry_and_failure(self, mock_save_cost, mock_prepare, mock_sleep, mock_exit, mock_path, mock_var_db, mock_book_class):
        """Test retry mechanism and ultimate failure."""
        # Setup mocks
        mock_book_class.get_by_id.return_value = self.mock_book
        mock_var_db.get.side_effect = [self.mock_var1, self.mock_var2]

        # Mock path operations
        mock_book_dir = MagicMock()
        mock_book_dir.mkdir.return_value = None
        mock_book_dir.glob.return_value = []
        # Mock the chunk file path
        mock_chunk_path = MagicMock()
        mock_chunk_path.__str__.return_value = "/test/path/chunk_000001.txt"
        mock_book_dir.__truediv__.return_value = mock_chunk_path
        mock_path.return_value = mock_book_dir

        # Mock prepare_for_write to return a valid path
        mock_prepare.return_value = Path("/test/final.txt")

        # Make translator fail consistently
        self.mock_translator.translate.side_effect = Exception("API Error")

        mock_logger = Mock()

        # Configure module config for fewer retries in test
        module_config = {"translation": {"max_chunk_retries": 3}}

        # Execute
        with patch("builtins.open", mock_open()):
            save_translated_book(book_id="test_book_id", translator=self.mock_translator, logger=mock_logger, module_config=module_config)

        # Verify retries happened (2 chunks * 3 attempts each = 6)
        assert self.mock_translator.translate.call_count == 6
        assert mock_sleep.call_count == 4  # 2 sleeps per chunk * 2 chunks

        # Verify system exit was called twice (once per chunk failure)
        assert mock_exit.call_count == 2

    @patch("enchant_book_manager.translation_orchestrator.Book")
    @patch("enchant_book_manager.translation_orchestrator.VARIATION_DB")
    @patch("enchant_book_manager.translation_orchestrator.Path")
    @patch("enchant_book_manager.translation_orchestrator.time.sleep")
    def test_translation_retry_success(self, mock_sleep, mock_path, mock_var_db, mock_book_class):
        """Test successful translation after retry."""
        # Setup mocks
        mock_book_class.get_by_id.return_value = self.mock_book
        self.mock_book.chunks = [self.mock_chunk1]  # Single chunk for simplicity
        mock_var_db.get.return_value = self.mock_var1

        # Mock path operations
        mock_book_dir = MagicMock()
        mock_book_dir.mkdir.return_value = None
        mock_book_dir.glob.return_value = []
        mock_path.return_value = mock_book_dir
        mock_path.cwd.return_value = Path("/current/dir")

        # Make translator fail twice then succeed
        self.mock_translator.translate.side_effect = [Exception("Temporary error"), Exception("Another temporary error"), "Translated text 1"]

        mock_logger = Mock()

        # Execute
        with patch("enchant_book_manager.translation_orchestrator.save_translation_cost_log"):
            with patch("enchant_book_manager.translation_orchestrator.prepare_for_write", return_value=Mock()):
                with patch("builtins.open", mock_open()):
                    save_translated_book(book_id="test_book_id", translator=self.mock_translator, logger=mock_logger)

        # Verify retries happened
        assert self.mock_translator.translate.call_count == 3
        assert mock_sleep.call_count == 2  # Sleep between retries

        # Verify exponential backoff
        calls = mock_sleep.call_args_list
        assert calls[0][0][0] == 2  # First retry: 2^1 = 2
        assert calls[1][0][0] == 4  # Second retry: 2^2 = 4

    @patch("enchant_book_manager.translation_orchestrator.Book")
    @patch("enchant_book_manager.translation_orchestrator.VARIATION_DB")
    @patch("enchant_book_manager.translation_orchestrator.Path")
    def test_resume_functionality(self, mock_path, mock_var_db, mock_book_class):
        """Test resume functionality with existing chunks."""
        # Setup mocks
        mock_book_class.get_by_id.return_value = self.mock_book
        mock_var_db.get.side_effect = [self.mock_var1, self.mock_var2]

        # Mock existing chunk file
        mock_existing_file = Mock()
        mock_existing_file.name = "Test Book by Test Author - Chunk_000001.txt"
        mock_existing_file.read_text.return_value = "Previously translated text 1"

        # Mock path operations
        mock_book_dir = MagicMock()
        mock_book_dir.mkdir.return_value = None
        mock_book_dir.glob.return_value = [mock_existing_file]
        mock_book_dir.__truediv__.side_effect = [
            mock_existing_file,  # Existing chunk 1
            Mock(),  # New chunk 2 file
            Mock(),  # Final output file
        ]
        mock_path.return_value = mock_book_dir
        mock_path.cwd.return_value = Path("/current/dir")

        mock_logger = Mock()

        # Execute with resume=True
        with patch("enchant_book_manager.translation_orchestrator.save_translation_cost_log"):
            with patch("enchant_book_manager.translation_orchestrator.prepare_for_write", return_value=Mock()):
                with patch("builtins.open", mock_open()):
                    save_translated_book(book_id="test_book_id", translator=self.mock_translator, resume=True, logger=mock_logger)

        # Verify only second chunk was translated
        self.mock_translator.translate.assert_called_once_with("Original text 2", True)

        # Verify log messages
        assert any("Autoresume active" in str(log_call) for log_call in mock_logger.info.call_args_list)
        assert any("Skipping translation for chunk 1" in str(log_call) for log_call in mock_logger.info.call_args_list)

    @patch("enchant_book_manager.translation_orchestrator.Book")
    @patch("enchant_book_manager.translation_orchestrator.Path")
    def test_directory_creation_error_non_exist(self, mock_path_class, mock_book_class):
        """Test handling of directory creation errors (non-EEXIST)."""
        # Setup mocks
        mock_book_class.get_by_id.return_value = self.mock_book

        # Mock path to raise OSError with non-EEXIST errno
        mock_book_dir = MagicMock()
        error = OSError("Permission denied")
        error.errno = errno.EACCES
        mock_book_dir.mkdir.side_effect = error
        mock_path_class.return_value = mock_book_dir
        mock_path_class.cwd.return_value = Path("/current/dir")

        mock_logger = Mock()

        # Execute - should continue with current directory
        with patch("enchant_book_manager.translation_orchestrator.VARIATION_DB"):
            with patch("enchant_book_manager.translation_orchestrator.save_translation_cost_log"):
                with patch("enchant_book_manager.translation_orchestrator.prepare_for_write", return_value=Mock()):
                    with patch("builtins.open", mock_open()):
                        save_translated_book(book_id="test_book_id", translator=self.mock_translator, logger=mock_logger)

        # Verify error was logged
        assert any("Error creating directory" in str(log_call) for log_call in mock_logger.error.call_args_list)

    @patch("enchant_book_manager.translation_orchestrator.Book")
    @patch("enchant_book_manager.translation_orchestrator.VARIATION_DB")
    @patch("enchant_book_manager.translation_orchestrator.Path")
    @patch("enchant_book_manager.translation_orchestrator.sys.exit")
    @patch("enchant_book_manager.translation_orchestrator.save_translation_cost_log")
    @patch("enchant_book_manager.translation_orchestrator.prepare_for_write")
    def test_empty_translation_result(self, mock_prepare, mock_save_cost, mock_exit, mock_path, mock_var_db, mock_book_class):
        """Test handling of empty translation results."""
        # Setup mocks
        mock_book_class.get_by_id.return_value = self.mock_book
        self.mock_book.chunks = [self.mock_chunk1]
        mock_var_db.get.return_value = self.mock_var1

        # Mock path operations
        mock_book_dir = MagicMock()
        mock_book_dir.mkdir.return_value = None
        mock_book_dir.glob.return_value = []
        # Mock the chunk file path
        mock_chunk_path = MagicMock()
        mock_chunk_path.__str__.return_value = "/test/path/chunk_000001.txt"
        mock_book_dir.__truediv__.return_value = mock_chunk_path
        mock_path.return_value = mock_book_dir

        # Mock prepare_for_write
        mock_prepare.return_value = Path("/test/final.txt")

        # Make translator return empty string
        self.mock_translator.translate.return_value = "   "  # Whitespace only

        mock_logger = Mock()

        # Execute
        with patch("builtins.open", mock_open()):
            save_translated_book(book_id="test_book_id", translator=self.mock_translator, logger=mock_logger, module_config={"translation": {"max_chunk_retries": 1}})

        # Verify system exit was called due to validation failure
        mock_exit.assert_called_once_with(1)

    @patch("enchant_book_manager.translation_orchestrator.Book")
    @patch("enchant_book_manager.translation_orchestrator.VARIATION_DB")
    @patch("enchant_book_manager.translation_orchestrator.Path")
    @patch("enchant_book_manager.translation_orchestrator.sys.exit")
    @patch("enchant_book_manager.translation_orchestrator.save_translation_cost_log")
    @patch("enchant_book_manager.translation_orchestrator.prepare_for_write")
    def test_none_translation_result(self, mock_prepare, mock_save_cost, mock_exit, mock_path, mock_var_db, mock_book_class):
        """Test handling of None translation results."""
        # Setup mocks
        mock_book_class.get_by_id.return_value = self.mock_book
        self.mock_book.chunks = [self.mock_chunk1]
        mock_var_db.get.return_value = self.mock_var1

        # Mock path operations
        mock_book_dir = MagicMock()
        mock_book_dir.mkdir.return_value = None
        mock_book_dir.glob.return_value = []
        # Mock the chunk file path
        mock_chunk_path = MagicMock()
        mock_chunk_path.__str__.return_value = "/test/path/chunk_000001.txt"
        mock_book_dir.__truediv__.return_value = mock_chunk_path
        mock_path.return_value = mock_book_dir

        # Mock prepare_for_write
        mock_prepare.return_value = Path("/test/final.txt")

        # Make translator return None
        self.mock_translator.translate.return_value = None

        mock_logger = Mock()

        # Execute
        with patch("builtins.open", mock_open()):
            save_translated_book(book_id="test_book_id", translator=self.mock_translator, logger=mock_logger, module_config={"translation": {"max_chunk_retries": 1}})

        # Verify system exit was called
        mock_exit.assert_called_once_with(1)

    @patch("enchant_book_manager.translation_orchestrator.Book")
    @patch("enchant_book_manager.translation_orchestrator.VARIATION_DB")
    @patch("enchant_book_manager.translation_orchestrator.Path")
    @patch("enchant_book_manager.translation_orchestrator.sys.exit")
    @patch("enchant_book_manager.translation_orchestrator.save_translation_cost_log")
    @patch("enchant_book_manager.translation_orchestrator.prepare_for_write")
    def test_file_write_error(self, mock_prepare, mock_save_cost, mock_exit, mock_path, mock_var_db, mock_book_class):
        """Test handling of file write errors."""
        # Setup mocks
        mock_book_class.get_by_id.return_value = self.mock_book
        self.mock_book.chunks = [self.mock_chunk1]
        mock_var_db.get.return_value = self.mock_var1

        # Mock path operations
        mock_book_dir = MagicMock()
        mock_book_dir.mkdir.return_value = None
        mock_book_dir.glob.return_value = []
        mock_chunk_file = Mock()
        mock_chunk_file.write_text.side_effect = PermissionError("Access denied")
        mock_chunk_file.__str__.return_value = "/test/path/chunk_000001.txt"
        mock_book_dir.__truediv__.return_value = mock_chunk_file
        mock_path.return_value = mock_book_dir

        # Mock prepare_for_write
        mock_prepare.return_value = Path("/test/final.txt")

        self.mock_translator.translate.return_value = "Translated text"

        mock_logger = Mock()

        # Execute
        save_translated_book(book_id="test_book_id", translator=self.mock_translator, logger=mock_logger, module_config={"translation": {"max_chunk_retries": 1}})

        # Verify system exit was called
        mock_exit.assert_called_once_with(1)

    @patch("enchant_book_manager.translation_orchestrator.Book")
    @patch("enchant_book_manager.translation_orchestrator.VARIATION_DB")
    @patch("enchant_book_manager.translation_orchestrator.Path")
    def test_is_last_chunk_flag(self, mock_path, mock_var_db, mock_book_class):
        """Test that is_last_chunk flag is correctly passed to translator."""
        # Setup mocks
        mock_book_class.get_by_id.return_value = self.mock_book
        self.mock_book.chunks = [self.mock_chunk1, self.mock_chunk2]
        mock_var_db.get.side_effect = [self.mock_var1, self.mock_var2]

        # Mock path operations
        mock_book_dir = MagicMock()
        mock_book_dir.mkdir.return_value = None
        mock_book_dir.glob.return_value = []
        mock_path.return_value = mock_book_dir
        mock_path.cwd.return_value = Path("/current/dir")

        mock_logger = Mock()

        # Execute
        with patch("enchant_book_manager.translation_orchestrator.save_translation_cost_log"):
            with patch("enchant_book_manager.translation_orchestrator.prepare_for_write", return_value=Mock()):
                with patch("builtins.open", mock_open()):
                    save_translated_book(book_id="test_book_id", translator=self.mock_translator, logger=mock_logger)

        # Verify is_last_chunk flag
        calls = self.mock_translator.translate.call_args_list
        assert calls[0][0][1] is False  # First chunk: is_last_chunk=False
        assert calls[1][0][1] is True  # Second chunk: is_last_chunk=True

    @patch("enchant_book_manager.translation_orchestrator.Book")
    @patch("enchant_book_manager.translation_orchestrator.VARIATION_DB")
    @patch("enchant_book_manager.translation_orchestrator.Path")
    @patch("enchant_book_manager.translation_orchestrator.time.sleep")
    def test_max_retry_wait_limit(self, mock_sleep, mock_path, mock_var_db, mock_book_class):
        """Test that retry wait time is capped at MAX_RETRY_WAIT_SECONDS."""
        # Setup mocks
        mock_book_class.get_by_id.return_value = self.mock_book
        self.mock_book.chunks = [self.mock_chunk1]
        mock_var_db.get.return_value = self.mock_var1

        # Mock path operations
        mock_book_dir = MagicMock()
        mock_book_dir.mkdir.return_value = None
        mock_book_dir.glob.return_value = []
        mock_path.return_value = mock_book_dir

        # Make translator fail many times
        self.mock_translator.translate.side_effect = [Exception("Error")] * 10

        mock_logger = Mock()

        # Execute with high retry count
        with patch("enchant_book_manager.translation_orchestrator.sys.exit"):
            save_translated_book(book_id="test_book_id", translator=self.mock_translator, logger=mock_logger, module_config={"translation": {"max_chunk_retries": 10}})

        # Verify wait times are capped
        for sleep_call in mock_sleep.call_args_list[5:]:  # After 5th retry
            assert sleep_call[0][0] <= MAX_RETRY_WAIT_SECONDS

    def test_default_logger_creation(self):
        """Test that a logger is created if none is provided."""
        with patch("enchant_book_manager.translation_orchestrator.Book") as mock_book_class:
            mock_book_class.get_by_id.return_value = None

            with patch("enchant_book_manager.translation_orchestrator.logging.getLogger") as mock_get_logger:
                mock_logger = Mock()
                mock_get_logger.return_value = mock_logger

                try:
                    save_translated_book(
                        book_id="test",
                        translator=self.mock_translator,
                        logger=None,  # No logger provided
                    )
                except ValueError:
                    pass  # Expected due to book not found

                # Verify logger was created
                mock_get_logger.assert_called_once_with("enchant_book_manager.translation_orchestrator")

    @patch("enchant_book_manager.translation_orchestrator.Book")
    @patch("enchant_book_manager.translation_orchestrator.VARIATION_DB")
    @patch("enchant_book_manager.translation_orchestrator.Path")
    @patch("enchant_book_manager.translation_orchestrator.sys.exit")
    @patch("enchant_book_manager.translation_orchestrator.save_translation_cost_log")
    @patch("enchant_book_manager.translation_orchestrator.prepare_for_write")
    def test_translator_not_initialized_error(self, mock_prepare, mock_save_cost, mock_exit, mock_path, mock_var_db, mock_book_class):
        """Test error when translator is None."""
        # Setup mocks
        mock_book_class.get_by_id.return_value = self.mock_book
        self.mock_book.chunks = [self.mock_chunk1]
        mock_var_db.get.return_value = self.mock_var1

        # Mock path operations
        mock_book_dir = MagicMock()
        mock_book_dir.mkdir.return_value = None
        mock_book_dir.glob.return_value = []
        # Mock the chunk file path
        mock_chunk_path = MagicMock()
        mock_chunk_path.__str__.return_value = "/test/path/chunk_000001.txt"
        mock_book_dir.__truediv__.return_value = mock_chunk_path
        mock_path.return_value = mock_book_dir

        # Mock prepare_for_write
        mock_prepare.return_value = Path("/test/final.txt")

        mock_logger = Mock()

        # Execute with None translator
        with patch("builtins.open", mock_open()):
            save_translated_book(book_id="test_book_id", translator=None, logger=mock_logger, module_config={"translation": {"max_chunk_retries": 1}})

        # Verify system exit was called
        mock_exit.assert_called_once_with(1)

        # Verify error was logged
        assert any("Translator not initialized" in str(log_call) for log_call in mock_logger.error.call_args_list)

    @patch("enchant_book_manager.translation_orchestrator.Book")
    @patch("enchant_book_manager.translation_orchestrator.VARIATION_DB")
    @patch("enchant_book_manager.translation_orchestrator.Path")
    def test_final_file_write_error(self, mock_path, mock_var_db, mock_book_class):
        """Test handling of errors when writing the final combined file."""
        # Setup mocks
        mock_book_class.get_by_id.return_value = self.mock_book
        mock_var_db.get.side_effect = [self.mock_var1, self.mock_var2]

        # Mock path operations
        mock_book_dir = MagicMock()
        mock_book_dir.mkdir.return_value = None
        mock_book_dir.glob.return_value = []
        mock_path.return_value = mock_book_dir
        mock_path.cwd.return_value = Path("/current/dir")

        mock_logger = Mock()

        # Execute
        with patch("enchant_book_manager.translation_orchestrator.save_translation_cost_log"):
            with patch("enchant_book_manager.translation_orchestrator.prepare_for_write", return_value=Mock()):
                with patch("builtins.open", mock_open()) as mock_file:
                    mock_file.side_effect = [
                        mock_open()(),  # First call succeeds (for chunks)
                        PermissionError("Cannot write final file"),  # Final file write fails
                    ]

                    with pytest.raises(PermissionError):
                        save_translated_book(book_id="test_book_id", translator=self.mock_translator, logger=mock_logger)

        # Verify error was logged
        assert any("Error saving translated book" in str(log_call) for log_call in mock_logger.error.call_args_list)
