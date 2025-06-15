#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for chunk-level retry mechanism in cli_translator.py
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
from pathlib import Path
import tempfile
import shutil
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from cli_translator import save_translated_book
from cli_translator import Book, Chapter, VARIATION_DB


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
            chapter = Mock(spec=Chapter)
            chapter.chapter_number = i + 1
            chapter.original_variation_id = f"var-{i+1}"
            self.mock_chapters.append(chapter)
        
        self.mock_book.chapters = self.mock_chapters
        
        # Create mock variations
        self.mock_variations = {
            "var-1": Mock(text_content="Chapter 1 content"),
            "var-2": Mock(text_content="Chapter 2 content"),
            "var-3": Mock(text_content="Chapter 3 content")
        }
        
    def teardown_method(self):
        """Clean up test fixtures"""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    @patch('cli_translator.Book.get_by_id')
    @patch('cli_translator.VARIATION_DB')
    @patch('cli_translator.translator')
    @patch('cli_translator.tolog')
    def test_successful_translation_first_attempt(self, mock_tolog, mock_translator, mock_var_db, mock_get_book):
        """Test successful translation on first attempt"""
        # Setup mocks
        mock_get_book.return_value = self.mock_book
        mock_var_db.get.side_effect = lambda var_id: self.mock_variations.get(var_id)
        mock_translator.translate.return_value = "Translated content"
        mock_translator.is_remote = False
        mock_translator.request_count = 0
        
        # Change to test directory
        with patch('cli_translator.Path.cwd', return_value=Path(self.test_dir)):
            with patch('sys.exit') as mock_exit:
                save_translated_book(self.book_id)
                
                # Should not exit
                mock_exit.assert_not_called()
                
                # Should translate all chunks
                assert mock_translator.translate.call_count == 3
                
                # Check log messages
                success_logs = [call for call in mock_tolog.info.call_args_list 
                               if "Successfully translated chunk" in str(call)]
                assert len(success_logs) == 3
    
    @patch('cli_translator.Book.get_by_id')
    @patch('cli_translator.VARIATION_DB')
    @patch('cli_translator.translator')
    @patch('cli_translator.tolog')
    @patch('cli_translator.time.sleep')
    def test_translation_retry_on_failure(self, mock_sleep, mock_tolog, mock_translator, mock_var_db, mock_get_book):
        """Test translation retries on failure and succeeds"""
        # Setup mocks
        mock_get_book.return_value = self.mock_book
        mock_var_db.get.side_effect = lambda var_id: self.mock_variations.get(var_id)
        
        # First chunk fails twice then succeeds
        mock_translator.translate.side_effect = [
            Exception("Network error"),
            Exception("Timeout"),
            "Translated content 1",
            "Translated content 2",
            "Translated content 3"
        ]
        mock_translator.is_remote = False
        mock_translator.request_count = 0
        
        # Change to test directory
        with patch('cli_translator.Path.cwd', return_value=Path(self.test_dir)):
            with patch('sys.exit') as mock_exit:
                save_translated_book(self.book_id)
                
                # Should not exit
                mock_exit.assert_not_called()
                
                # Should have retried
                assert mock_translator.translate.call_count == 5
                
                # Check sleep was called for retries
                assert mock_sleep.call_count == 2
                mock_sleep.assert_any_call(2)  # First retry
                mock_sleep.assert_any_call(4)  # Second retry
    
    @patch('cli_translator.Book.get_by_id')
    @patch('cli_translator.VARIATION_DB')
    @patch('cli_translator.translator')
    @patch('cli_translator.tolog')
    @patch('cli_translator.time.sleep')
    @patch('cli_translator._module_config', {'translation': {'max_chunk_retries': 3}})
    def test_translation_fails_after_max_retries(self, mock_sleep, mock_tolog, mock_translator, mock_var_db, mock_get_book):
        """Test program exits when all retry attempts fail"""
        
        # Setup mocks
        mock_get_book.return_value = self.mock_book
        mock_var_db.get.side_effect = lambda var_id: self.mock_variations.get(var_id)
        
        # All attempts fail
        mock_translator.translate.side_effect = Exception("Persistent error")
        mock_translator.is_remote = False
        mock_translator.request_count = 0
        
        # Change to test directory
        with patch('cli_translator.Path.cwd', return_value=Path(self.test_dir)):
            with patch('sys.exit') as mock_exit:
                # Since sys.exit will be called, we need to catch it to verify
                mock_exit.side_effect = SystemExit(1)
                
                with pytest.raises(SystemExit) as cm:
                    save_translated_book(self.book_id)
                
                # Check exit code
                assert cm.value.code == 1
                
                # Should exit with error code
                mock_exit.assert_called_once_with(1)
                
                # Should have attempted max_chunk_retries times
                assert mock_translator.translate.call_count == 3
                
                # Check error message was logged
                error_logs = [call for call in mock_tolog.error.call_args_list 
                             if "FATAL ERROR" in str(call)]
                assert len(error_logs) == 1
                
                # Check sleep was called correctly
                assert mock_sleep.call_count == 2  # No sleep after last attempt
    
    @patch('cli_translator.Book.get_by_id')
    @patch('cli_translator.VARIATION_DB')
    @patch('cli_translator.translator')
    @patch('cli_translator.tolog')
    def test_empty_translation_triggers_retry(self, mock_tolog, mock_translator, mock_var_db, mock_get_book):
        """Test that empty or whitespace-only translations trigger retry"""
        # Setup mocks
        mock_get_book.return_value = self.mock_book
        mock_var_db.get.side_effect = lambda var_id: self.mock_variations.get(var_id)
        
        # Return empty/whitespace translations then valid ones
        mock_translator.translate.side_effect = [
            "",  # Empty
            "   ",  # Whitespace only
            "Valid translation 1",
            "Valid translation 2",
            "Valid translation 3"
        ]
        mock_translator.is_remote = False
        mock_translator.request_count = 0
        
        # Change to test directory
        with patch('cli_translator.Path.cwd', return_value=Path(self.test_dir)):
            with patch('sys.exit') as mock_exit:
                save_translated_book(self.book_id)
                
                # Should not exit
                mock_exit.assert_not_called()
                
                # Should have retried
                assert mock_translator.translate.call_count == 5
    
    @patch('cli_translator.Book.get_by_id')
    @patch('cli_translator.VARIATION_DB')
    @patch('cli_translator.translator')
    @patch('cli_translator.tolog')
    def test_file_write_error_triggers_retry(self, mock_tolog, mock_translator, mock_var_db, mock_get_book):
        """Test that file write errors trigger retry"""
        # Setup mocks
        mock_get_book.return_value = self.mock_book
        mock_var_db.get.side_effect = lambda var_id: self.mock_variations.get(var_id)
        mock_translator.translate.return_value = "Translated content"
        mock_translator.is_remote = False
        mock_translator.request_count = 0
        
        # Make first write attempt fail
        write_attempts = [0]
        def mock_write_text(content):
            write_attempts[0] += 1
            if write_attempts[0] == 1:
                raise PermissionError("Access denied")
            # Succeed on subsequent attempts
        
        # Change to test directory
        with patch('cli_translator.Path.cwd', return_value=Path(self.test_dir)):
            with patch('cli_translator.Path.write_text', side_effect=mock_write_text):
                with patch('sys.exit') as mock_exit:
                    save_translated_book(self.book_id)
                    
                    # Should not exit (recovers from write error)
                    mock_exit.assert_not_called()
    
    @patch('cli_translator.Book.get_by_id')
    def test_book_not_found_raises_error(self, mock_get_book):
        """Test that missing book raises ValueError"""
        mock_get_book.return_value = None
        
        with pytest.raises(ValueError) as context:
            save_translated_book("non-existent-book")
        
        assert str(context.value) == "Book not found"
