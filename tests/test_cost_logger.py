#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test suite for cost_logger module.
"""

import pytest
import datetime as dt
import logging
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, mock_open
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from enchant_book_manager.cost_logger import save_translation_cost_log
from enchant_book_manager.models import Book


class TestSaveTranslationCostLog:
    """Test the save_translation_cost_log function."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create a mock book
        self.book = Mock(spec=Book)
        self.book.translated_title = "Test Novel"
        self.book.translated_author = "Test Author"

        # Create a mock translator
        self.translator = Mock()
        self.translator.is_remote = True
        self.translator.request_count = 5
        self.translator.MODEL_NAME = "test-model"
        self.translator.format_cost_summary.return_value = "Cost Summary: $1.50 total"

        # Other fixtures
        self.output_dir = Path("/tmp/test_output")
        self.total_chunks = 10
        self.logger = Mock(spec=logging.Logger)

    @patch("enchant_book_manager.cost_logger.global_cost_tracker")
    @patch("enchant_book_manager.cost_logger.prepare_for_write")
    @patch("builtins.open", new_callable=mock_open)
    @patch("enchant_book_manager.cost_logger.dt.datetime")
    def test_save_cost_log_success(self, mock_datetime, mock_file, mock_prepare, mock_tracker):
        """Test successful cost log saving."""
        # Setup mocks
        mock_now = Mock()
        mock_now.strftime.return_value = "2024-01-01 12:00:00"
        mock_datetime.now.return_value = mock_now

        mock_prepare.return_value = self.output_dir / "translated_Test Novel by Test Author_AI_COSTS.log"

        mock_tracker.get_summary.return_value = {
            "total_cost": 1.50,
            "total_tokens": 5000,
            "total_prompt_tokens": 3000,
            "total_completion_tokens": 2000,
            "request_count": 5,
        }

        # Call function
        save_translation_cost_log(self.book, self.translator, self.output_dir, self.total_chunks, self.logger)

        # Verify prepare_for_write was called
        expected_path = self.output_dir / "translated_Test Novel by Test Author_AI_COSTS.log"
        mock_prepare.assert_called_once_with(expected_path)

        # Verify file was opened for writing
        mock_file.assert_called_once_with(mock_prepare.return_value, "w", encoding="utf-8")

        # Verify content was written
        handle = mock_file()
        write_calls = handle.write.call_args_list
        content = "".join(call[0][0] for call in write_calls)

        assert "AI Translation Cost Log" in content
        assert "Novel: Test Novel by Test Author" in content
        assert "Translation Date: 2024-01-01 12:00:00" in content
        assert "API Service: OpenRouter (Remote)" in content
        assert "Model: test-model" in content
        assert "Cost Summary: $1.50 total" in content
        assert "Total Chunks Translated: 10" in content
        assert "Average Cost per chunk: $0.150000" in content
        assert "Average Tokens per chunk: 500" in content
        assert "total_cost: 1.5" in content
        assert "total_tokens: 5000" in content
        assert "request_count: 5" in content

        # Verify logger was called
        self.logger.info.assert_called_once()
        assert "Cost log saved to" in self.logger.info.call_args[0][0]

    def test_skip_non_remote_translator(self):
        """Test that cost log is skipped for non-remote translators."""
        self.translator.is_remote = False

        with patch("enchant_book_manager.cost_logger.prepare_for_write") as mock_prepare:
            save_translation_cost_log(
                self.book,
                self.translator,
                self.output_dir,
                self.total_chunks,
                self.logger,
            )

        # Should not prepare or write any file
        mock_prepare.assert_not_called()
        self.logger.info.assert_not_called()

    def test_skip_zero_requests(self):
        """Test that cost log is skipped when no requests were made."""
        self.translator.request_count = 0

        with patch("enchant_book_manager.cost_logger.prepare_for_write") as mock_prepare:
            save_translation_cost_log(
                self.book,
                self.translator,
                self.output_dir,
                self.total_chunks,
                self.logger,
            )

        # Should not prepare or write any file
        mock_prepare.assert_not_called()
        self.logger.info.assert_not_called()

    def test_skip_none_translator(self):
        """Test that cost log is skipped when translator is None."""
        with patch("enchant_book_manager.cost_logger.prepare_for_write") as mock_prepare:
            save_translation_cost_log(
                self.book,
                None,  # No translator
                self.output_dir,
                self.total_chunks,
                self.logger,
            )

        # Should not prepare or write any file
        mock_prepare.assert_not_called()
        self.logger.info.assert_not_called()

    @patch("enchant_book_manager.cost_logger.global_cost_tracker")
    @patch("enchant_book_manager.cost_logger.prepare_for_write")
    @patch("builtins.open", new_callable=mock_open)
    def test_save_cost_log_file_error(self, mock_file, mock_prepare, mock_tracker):
        """Test handling of file write errors."""
        # Setup mocks
        mock_prepare.return_value = self.output_dir / "test.log"
        mock_file.side_effect = PermissionError("Permission denied")

        # Call function and expect exception
        with pytest.raises(PermissionError):
            save_translation_cost_log(
                self.book,
                self.translator,
                self.output_dir,
                self.total_chunks,
                self.logger,
            )

        # Verify error was logged
        self.logger.error.assert_called_once()
        assert "Error saving cost log" in self.logger.error.call_args[0][0]

    @patch("enchant_book_manager.cost_logger.global_cost_tracker")
    @patch("enchant_book_manager.cost_logger.prepare_for_write")
    @patch("builtins.open", new_callable=mock_open)
    @patch("enchant_book_manager.cost_logger.dt.datetime")
    def test_save_cost_log_zero_chunks(self, mock_datetime, mock_file, mock_prepare, mock_tracker):
        """Test cost log with zero chunks (edge case)."""
        # Setup mocks
        mock_now = Mock()
        mock_now.strftime.return_value = "2024-01-01 12:00:00"
        mock_datetime.now.return_value = mock_now

        mock_prepare.return_value = self.output_dir / "test.log"

        mock_tracker.get_summary.return_value = {
            "total_cost": 0,
            "total_tokens": 0,
            "request_count": 1,  # Still had a request
        }

        # Call with zero chunks
        save_translation_cost_log(
            self.book,
            self.translator,
            self.output_dir,
            0,  # Zero chunks
            self.logger,
        )

        # Should not attempt division by zero
        handle = mock_file()
        write_calls = handle.write.call_args_list
        content = "".join(call[0][0] for call in write_calls)

        # Should skip average calculations
        assert "Average Cost per chunk:" not in content
        assert "Average Tokens per chunk:" not in content

    @patch("enchant_book_manager.cost_logger.global_cost_tracker")
    @patch("enchant_book_manager.cost_logger.prepare_for_write")
    @patch("builtins.open", new_callable=mock_open)
    @patch("enchant_book_manager.cost_logger.logging.getLogger")
    def test_save_cost_log_default_logger(self, mock_get_logger, mock_file, mock_prepare, mock_tracker):
        """Test that default logger is used when none provided."""
        # Setup mocks
        default_logger = Mock(spec=logging.Logger)
        mock_get_logger.return_value = default_logger

        mock_prepare.return_value = self.output_dir / "test.log"
        mock_tracker.get_summary.return_value = {
            "total_cost": 1.0,
            "total_tokens": 1000,
            "request_count": 1,
        }

        # Call without logger
        save_translation_cost_log(
            self.book,
            self.translator,
            self.output_dir,
            self.total_chunks,
            None,  # No logger provided
        )

        # Verify default logger was obtained
        mock_get_logger.assert_called_once_with("enchant_book_manager.cost_logger")

        # Verify default logger was used
        default_logger.info.assert_called_once()

    @patch("enchant_book_manager.cost_logger.global_cost_tracker")
    @patch("enchant_book_manager.cost_logger.prepare_for_write")
    @patch("builtins.open", new_callable=mock_open)
    def test_special_characters_in_filename(self, mock_file, mock_prepare, mock_tracker):
        """Test handling of special characters in book title/author."""
        # Book with special characters
        self.book.translated_title = "Test: Novel/With\\Special"
        self.book.translated_author = "Author<>Name"

        mock_prepare.return_value = self.output_dir / "sanitized_filename.log"
        mock_tracker.get_summary.return_value = {
            "total_cost": 1.0,
            "total_tokens": 1000,
            "request_count": 1,
        }

        # Call function
        save_translation_cost_log(self.book, self.translator, self.output_dir, self.total_chunks, self.logger)

        # Verify prepare_for_write was called with sanitized filename
        # Special characters are replaced with underscores by sanitize_filename
        expected_path = self.output_dir / "translated_Test_ Novel_With_Special by Author__Name_AI_COSTS.log"
        mock_prepare.assert_called_once_with(expected_path)

    @patch("enchant_book_manager.cost_logger.global_cost_tracker")
    @patch("enchant_book_manager.cost_logger.prepare_for_write")
    @patch("builtins.open", new_callable=mock_open)
    @patch("enchant_book_manager.cost_logger.dt.datetime")
    def test_missing_optional_fields_in_summary(self, mock_datetime, mock_file, mock_prepare, mock_tracker):
        """Test handling when cost tracker summary is missing optional fields."""
        # Setup mocks
        mock_now = Mock()
        mock_now.strftime.return_value = "2024-01-01 12:00:00"
        mock_datetime.now.return_value = mock_now

        mock_prepare.return_value = self.output_dir / "test.log"

        # Summary missing optional prompt/completion token fields
        mock_tracker.get_summary.return_value = {
            "total_cost": 1.50,
            "total_tokens": 5000,
            "request_count": 5,
            # Missing: total_prompt_tokens, total_completion_tokens
        }

        # Call function
        save_translation_cost_log(self.book, self.translator, self.output_dir, self.total_chunks, self.logger)

        # Verify it handles missing fields gracefully
        handle = mock_file()
        write_calls = handle.write.call_args_list
        content = "".join(call[0][0] for call in write_calls)

        # Should use get() with default 0
        assert "total_prompt_tokens: 0" in content
        assert "total_completion_tokens: 0" in content
