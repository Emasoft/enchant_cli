#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Improved tests for chunk-level retry mechanism with reduced duplication
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
from pathlib import Path
import tempfile
import shutil

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from cli_translator import save_translated_book, DEFAULT_MAX_CHUNK_RETRIES, MAX_RETRY_WAIT_SECONDS
from cli_translator import Book, Chapter, VARIATION_DB


class BaseChunkRetryTest(unittest.TestCase):
    """Base class for chunk retry tests with common setup"""
    
    def setUp(self):
        """Set up common test fixtures"""
        self.test_dir = tempfile.mkdtemp()
        self.book_id = "test-book-123"
        
        # Create mock book
        self.mock_book = self._create_mock_book()
        
        # Create mock variations
        self.mock_variations = self._create_mock_variations()
        
        # Setup common patches
        self.patches = []
        self._setup_patches()
        
    def tearDown(self):
        """Clean up test fixtures and patches"""
        shutil.rmtree(self.test_dir, ignore_errors=True)
        for p in self.patches:
            p.stop()
    
    def _create_mock_book(self):
        """Create a mock book with chapters"""
        mock_book = Mock(spec=Book)
        mock_book.book_id = self.book_id
        mock_book.translated_title = "Test Novel"
        mock_book.translated_author = "Test Author"
        
        # Create mock chapters
        mock_chapters = []
        for i in range(3):
            chapter = Mock(spec=Chapter)
            chapter.chapter_number = i + 1
            chapter.original_variation_id = f"var-{i+1}"
            mock_chapters.append(chapter)
        
        mock_book.chapters = mock_chapters
        return mock_book
    
    def _create_mock_variations(self):
        """Create mock variations for chapters"""
        return {
            "var-1": Mock(text_content="Chapter 1 content"),
            "var-2": Mock(text_content="Chapter 2 content"),
            "var-3": Mock(text_content="Chapter 3 content")
        }
    
    def _setup_patches(self):
        """Setup common patches for all tests"""
        # Book.get_by_id
        book_patch = patch('cli_translator.Book.get_by_id')
        self.mock_get_book = book_patch.start()
        self.mock_get_book.return_value = self.mock_book
        self.patches.append(book_patch)
        
        # VARIATION_DB
        var_patch = patch('cli_translator.VARIATION_DB')
        self.mock_var_db = var_patch.start()
        self.mock_var_db.get.side_effect = lambda var_id: self.mock_variations.get(var_id)
        self.patches.append(var_patch)
        
        # translator
        trans_patch = patch('cli_translator.translator')
        self.mock_translator = trans_patch.start()
        self.mock_translator.is_remote = False
        self.mock_translator.request_count = 0
        self.patches.append(trans_patch)
        
        # tolog
        log_patch = patch('cli_translator.tolog')
        self.mock_tolog = log_patch.start()
        self.patches.append(log_patch)
        
        # Path.cwd
        cwd_patch = patch('cli_translator.Path.cwd', return_value=Path(self.test_dir))
        cwd_patch.start()
        self.patches.append(cwd_patch)


class TestChunkRetryMechanismImproved(BaseChunkRetryTest):
    """Improved test cases for chunk-level retry mechanism"""
    
    def test_successful_translation_first_attempt(self):
        """Test successful translation on first attempt"""
        self.mock_translator.translate.return_value = "Translated content"
        
        with patch('sys.exit') as mock_exit:
            save_translated_book(self.book_id)
            
            # Should not exit
            mock_exit.assert_not_called()
            
            # Should translate all chunks
            self.assertEqual(self.mock_translator.translate.call_count, 3)
            
            # Check log messages
            success_logs = [call for call in self.mock_tolog.info.call_args_list 
                           if "Successfully translated chunk" in str(call)]
            self.assertEqual(len(success_logs), 3)
    
    @patch('cli_translator.time.sleep')
    def test_translation_retry_on_failure(self, mock_sleep):
        """Test translation retries on failure and succeeds"""
        # First chunk fails twice then succeeds
        self.mock_translator.translate.side_effect = [
            Exception("Network error"),
            Exception("Timeout"),
            "Translated content 1",
            "Translated content 2",
            "Translated content 3"
        ]
        
        with patch('sys.exit') as mock_exit:
            save_translated_book(self.book_id)
            
            # Should not exit
            mock_exit.assert_not_called()
            
            # Should have retried
            self.assertEqual(self.mock_translator.translate.call_count, 5)
            
            # Check sleep was called for retries
            self.assertEqual(mock_sleep.call_count, 2)
            mock_sleep.assert_any_call(2)  # First retry
            mock_sleep.assert_any_call(4)  # Second retry
    
    @patch('cli_translator.time.sleep')
    @patch('cli_translator._module_config', {'translation': {'max_chunk_retries': 3}})
    def test_translation_fails_after_max_retries(self, mock_sleep):
        """Test program exits when all retry attempts fail"""
        # All attempts fail
        self.mock_translator.translate.side_effect = Exception("Persistent error")
        
        with patch('sys.exit') as mock_exit:
            mock_exit.side_effect = SystemExit(1)
            
            with self.assertRaises(SystemExit) as cm:
                save_translated_book(self.book_id)
            
            # Check exit code
            self.assertEqual(cm.exception.code, 1)
            
            # Should exit with error code
            mock_exit.assert_called_once_with(1)
            
            # Should have attempted max_chunk_retries times
            self.assertEqual(self.mock_translator.translate.call_count, 3)
            
            # Check error message was logged using format_chunk_error_message
            error_logs = [call for call in self.mock_tolog.error.call_args_list 
                         if "FATAL ERROR" in str(call)]
            self.assertEqual(len(error_logs), 1)
            
            # Check sleep was called correctly
            self.assertEqual(mock_sleep.call_count, 2)  # No sleep after last attempt
    
    def test_empty_translation_triggers_retry(self):
        """Test that empty or whitespace-only translations trigger retry"""
        # Return empty/whitespace translations then valid ones
        self.mock_translator.translate.side_effect = [
            "",  # Empty
            "   ",  # Whitespace only
            "Valid translation 1",
            "Valid translation 2",
            "Valid translation 3"
        ]
        
        with patch('sys.exit') as mock_exit:
            save_translated_book(self.book_id)
            
            # Should not exit
            mock_exit.assert_not_called()
            
            # Should have retried
            self.assertEqual(self.mock_translator.translate.call_count, 5)
    
    def test_constants_used_correctly(self):
        """Test that constants are used instead of magic numbers"""
        # Check that DEFAULT_MAX_CHUNK_RETRIES is used when no config
        with patch('cli_translator._module_config', None):
            # All attempts fail to trigger the retry logic
            self.mock_translator.translate.side_effect = Exception("Test error")
            
            with patch('sys.exit') as mock_exit:
                mock_exit.side_effect = SystemExit(1)
                
                with self.assertRaises(SystemExit):
                    save_translated_book(self.book_id)
                
                # Should have attempted DEFAULT_MAX_CHUNK_RETRIES times
                self.assertEqual(self.mock_translator.translate.call_count, DEFAULT_MAX_CHUNK_RETRIES)
    
    @patch('cli_translator.time.sleep')
    def test_max_wait_time_respected(self, mock_sleep):
        """Test that exponential backoff respects MAX_RETRY_WAIT_SECONDS"""
        # Need many retries to test max wait time
        with patch('cli_translator._module_config', {'translation': {'max_chunk_retries': 10}}):
            # Fail 9 times then succeed
            errors = [Exception("Test error")] * 9
            self.mock_translator.translate.side_effect = errors + ["Translated"] * 3
            
            with patch('sys.exit') as mock_exit:
                save_translated_book(self.book_id)
                
                # Check that no sleep call exceeds MAX_RETRY_WAIT_SECONDS
                for call in mock_sleep.call_args_list:
                    wait_time = call[0][0]
                    self.assertLessEqual(wait_time, MAX_RETRY_WAIT_SECONDS)


if __name__ == '__main__':
    unittest.main()