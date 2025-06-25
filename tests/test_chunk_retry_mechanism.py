#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for chunk-level retry mechanism in cli_translator.py
"""

import pytest
from unittest.mock import Mock, patch
import sys
from pathlib import Path
import tempfile
import shutil
import logging

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from enchant_book_manager.translation_orchestrator import save_translated_book
from enchant_book_manager.models import Book, Chunk


class TestChunkRetryMechanism:
    """Test cases for chunk-level retry mechanism"""

    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Set up test fixtures"""
        self.test_dir = tempfile.mkdtemp()
        self.book_id = "test-book-123"

        # Create mock book
        self.mock_book = Mock(spec=Book)
        self.mock_book.book_id = self.book_id
        self.mock_book.translated_title = "Test Novel"
        self.mock_book.translated_author = "Test Author"

        # Create mock chapters
        self.mock_chapters = []
        for i in range(3):
            chapter = Mock(spec=Chunk)
            chapter.chunk_number = i + 1
            chapter.original_variation_id = f"var-{i + 1}"
            self.mock_chapters.append(chapter)

        self.mock_book.chunks = self.mock_chapters

        # Create mock variations
        self.mock_variations = {
            "var-1": Mock(text_content="Chapter 1 content"),
            "var-2": Mock(text_content="Chapter 2 content"),
            "var-3": Mock(text_content="Chapter 3 content"),
        }

    def teardown_method(self):
        """Clean up test fixtures"""
        shutil.rmtree(self.test_dir, ignore_errors=True)

    @patch("enchant_book_manager.models.Book.get_by_id")
    @patch("enchant_book_manager.translation_orchestrator.VARIATION_DB")
    def test_successful_translation_first_attempt(self, mock_var_db, mock_get_book):
        """Test successful translation on first attempt"""
        # Setup mocks
        mock_get_book.return_value = self.mock_book
        mock_var_db.get.side_effect = lambda var_id: self.mock_variations.get(var_id)

        # Create mock translator and logger
        from enchant_book_manager.translation_service import ChineseAITranslator

        mock_translator = Mock(spec=ChineseAITranslator)
        mock_translator.translate.return_value = "Translated content"
        mock_translator.is_remote = False
        mock_translator.request_count = 0

        mock_logger = Mock(spec=logging.Logger)

        # Change to test directory
        with patch(
            "enchant_book_manager.translation_orchestrator.Path.cwd",
            return_value=Path(self.test_dir),
        ):
            with patch("sys.exit") as mock_exit:
                save_translated_book(
                    self.book_id,
                    translator=mock_translator,
                    resume=False,
                    create_epub=False,
                    logger=mock_logger,
                    module_config={},
                )

                # Should not exit
                mock_exit.assert_not_called()

                # Should translate all chunks
                assert mock_translator.translate.call_count == 3

                # Check log messages
                success_logs = [call for call in mock_logger.info.call_args_list if "Successfully translated chunk" in str(call)]
                assert len(success_logs) == 3

    @patch("enchant_book_manager.models.Book.get_by_id")
    @patch("enchant_book_manager.translation_orchestrator.VARIATION_DB")
    @patch("enchant_book_manager.translation_orchestrator.time.sleep")
    def test_translation_retry_on_failure(self, mock_sleep, mock_var_db, mock_get_book):
        """Test translation retries on failure and succeeds"""
        # Setup mocks
        mock_get_book.return_value = self.mock_book
        mock_var_db.get.side_effect = lambda var_id: self.mock_variations.get(var_id)

        # Create mock translator and logger
        from enchant_book_manager.translation_service import ChineseAITranslator

        mock_translator = Mock(spec=ChineseAITranslator)
        # First chunk fails twice then succeeds
        mock_translator.translate.side_effect = [
            Exception("Network error"),
            Exception("Timeout"),
            "Translated content 1",
            "Translated content 2",
            "Translated content 3",
        ]
        # Configure attributes properly to avoid MagicMock comparison issues
        mock_translator.is_remote = False
        mock_translator.request_count = 0

        mock_logger = Mock(spec=logging.Logger)

        # Change to test directory
        with patch(
            "enchant_book_manager.translation_orchestrator.Path.cwd",
            return_value=Path(self.test_dir),
        ):
            with patch("sys.exit") as mock_exit:
                save_translated_book(
                    self.book_id,
                    translator=mock_translator,
                    resume=False,
                    create_epub=False,
                    logger=mock_logger,
                    module_config={},
                )

                # Should not exit
                mock_exit.assert_not_called()

                # Should have retried
                assert mock_translator.translate.call_count == 5

                # Check sleep was called for retries
                assert mock_sleep.call_count == 2
                mock_sleep.assert_any_call(2)  # First retry
                mock_sleep.assert_any_call(4)  # Second retry

    @patch("enchant_book_manager.models.Book.get_by_id")
    @patch("enchant_book_manager.translation_orchestrator.VARIATION_DB")
    @patch("enchant_book_manager.translation_orchestrator.time.sleep")
    def test_translation_fails_after_max_retries(self, mock_sleep, mock_var_db, mock_get_book):
        """Test program exits when all retry attempts fail"""

        # Setup mocks
        mock_get_book.return_value = self.mock_book
        mock_var_db.get.side_effect = lambda var_id: self.mock_variations.get(var_id)

        # Create mock translator and logger
        from enchant_book_manager.translation_service import ChineseAITranslator

        mock_translator = Mock(spec=ChineseAITranslator)
        # All attempts fail
        mock_translator.translate.side_effect = Exception("Persistent error")
        # Configure attributes properly to avoid MagicMock comparison issues
        mock_translator.is_remote = False
        mock_translator.request_count = 0

        mock_logger = Mock(spec=logging.Logger)

        # Change to test directory
        with patch(
            "enchant_book_manager.translation_orchestrator.Path.cwd",
            return_value=Path(self.test_dir),
        ):
            with patch("sys.exit") as mock_exit:
                # Since sys.exit will be called, we need to catch it to verify
                mock_exit.side_effect = SystemExit(1)

                with pytest.raises(SystemExit) as cm:
                    save_translated_book(
                        self.book_id,
                        translator=mock_translator,
                        resume=False,
                        create_epub=False,
                        logger=mock_logger,
                        module_config={"translation": {"max_chunk_retries": 3}},
                    )

                # Check exit code
                assert cm.value.code == 1

                # Should exit with error code
                mock_exit.assert_called_once_with(1)

                # Should have attempted max_chunk_retries times
                assert mock_translator.translate.call_count == 3

                # Check error message was logged
                error_logs = [call for call in mock_logger.error.call_args_list if "FATAL ERROR" in str(call)]
                assert len(error_logs) == 1

                # Check sleep was called correctly
                assert mock_sleep.call_count == 2  # No sleep after last attempt

    @patch("enchant_book_manager.models.Book.get_by_id")
    @patch("enchant_book_manager.translation_orchestrator.VARIATION_DB")
    @patch("enchant_book_manager.translation_orchestrator.time.sleep")
    def test_empty_translation_triggers_retry(self, mock_sleep, mock_var_db, mock_get_book):
        """Test that empty or whitespace-only translations trigger retry"""
        # Setup mocks
        mock_get_book.return_value = self.mock_book
        mock_var_db.get.side_effect = lambda var_id: self.mock_variations.get(var_id)

        # Create mock translator and logger
        from enchant_book_manager.translation_service import ChineseAITranslator

        mock_translator = Mock(spec=ChineseAITranslator)
        # Return empty/whitespace translations then valid ones
        mock_translator.translate.side_effect = [
            "",  # Empty
            "   ",  # Whitespace only
            "Valid translation 1",
            "Valid translation 2",
            "Valid translation 3",
        ]
        # Configure attributes properly to avoid MagicMock comparison issues
        mock_translator.is_remote = False
        mock_translator.request_count = 0

        mock_logger = Mock(spec=logging.Logger)

        # Change to test directory
        with patch(
            "enchant_book_manager.translation_orchestrator.Path.cwd",
            return_value=Path(self.test_dir),
        ):
            with patch("sys.exit") as mock_exit:
                save_translated_book(
                    self.book_id,
                    translator=mock_translator,
                    resume=False,
                    create_epub=False,
                    logger=mock_logger,
                    module_config={},
                )

                # Should not exit
                mock_exit.assert_not_called()

                # Should have retried
                assert mock_translator.translate.call_count == 5

    @patch("enchant_book_manager.models.Book.get_by_id")
    @patch("enchant_book_manager.translation_orchestrator.VARIATION_DB")
    @patch("enchant_book_manager.translation_orchestrator.time.sleep")
    def test_file_write_error_triggers_retry(self, mock_sleep, mock_var_db, mock_get_book):
        """Test that file write errors trigger retry"""
        # Setup mocks
        mock_get_book.return_value = self.mock_book
        mock_var_db.get.side_effect = lambda var_id: self.mock_variations.get(var_id)
        # Create mock translator and logger
        from enchant_book_manager.translation_service import ChineseAITranslator

        mock_translator = Mock(spec=ChineseAITranslator)
        mock_translator.translate.return_value = "Translated content"
        # Configure attributes properly to avoid MagicMock comparison issues
        mock_translator.is_remote = False
        mock_translator.request_count = 0

        mock_logger = Mock(spec=logging.Logger)

        # Make first write attempt fail
        write_attempts = [0]

        def mock_write_text(content):
            write_attempts[0] += 1
            if write_attempts[0] == 1:
                raise PermissionError("Access denied")
            # Succeed on subsequent attempts

        # Change to test directory
        with patch(
            "enchant_book_manager.translation_orchestrator.Path.cwd",
            return_value=Path(self.test_dir),
        ):
            with patch(
                "enchant_book_manager.translation_orchestrator.Path.write_text",
                side_effect=mock_write_text,
            ):
                with patch("sys.exit") as mock_exit:
                    save_translated_book(
                        self.book_id,
                        translator=mock_translator,
                        resume=False,
                        create_epub=False,
                        logger=mock_logger,
                        module_config={},
                    )

                    # Should not exit (recovers from write error)
                    mock_exit.assert_not_called()

    @patch("enchant_book_manager.models.Book.get_by_id")
    def test_book_not_found_raises_error(self, mock_get_book):
        """Test that missing book raises ValueError"""
        mock_get_book.return_value = None

        # Create mock translator and logger
        from enchant_book_manager.translation_service import ChineseAITranslator

        mock_translator = Mock(spec=ChineseAITranslator)
        mock_logger = Mock(spec=logging.Logger)

        with pytest.raises(ValueError) as context:
            save_translated_book(
                "non-existent-book",
                translator=mock_translator,
                resume=False,
                create_epub=False,
                logger=mock_logger,
                module_config={},
            )

        assert str(context.value) == "Book not found"
