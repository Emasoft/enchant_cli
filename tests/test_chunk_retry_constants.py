#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for chunk retry constants and configuration
"""

import unittest
from unittest.mock import patch
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import cli_translator


class TestChunkRetryConstants(unittest.TestCase):
    """Test cases for chunk retry constants"""
    
    def test_default_constants_exist(self):
        """Test that default constants are defined"""
        self.assertTrue(hasattr(cli_translator, 'DEFAULT_MAX_CHUNK_RETRIES'))
        self.assertTrue(hasattr(cli_translator, 'MAX_RETRY_WAIT_SECONDS'))
        
    def test_default_values(self):
        """Test default constant values"""
        self.assertEqual(cli_translator.DEFAULT_MAX_CHUNK_RETRIES, 10)
        self.assertEqual(cli_translator.MAX_RETRY_WAIT_SECONDS, 60)
        
    def test_format_chunk_error_message_exists(self):
        """Test that error message formatter exists"""
        self.assertTrue(hasattr(cli_translator, 'format_chunk_error_message'))
        self.assertTrue(callable(cli_translator.format_chunk_error_message))
        
    def test_format_chunk_error_message(self):
        """Test error message formatting"""
        msg = cli_translator.format_chunk_error_message(
            chunk_number=5,
            max_retries=10,
            last_error="Connection refused",
            book_title="Test Book",
            book_author="Test Author",
            output_path="test/path.txt"
        )
        
        self.assertIn("Failed to translate chunk 000005", msg)
        self.assertIn("10 attempts", msg)
        self.assertIn("Connection refused", msg)
        self.assertIn("Test Book by Test Author", msg)
        self.assertIn("test/path.txt", msg)
        self.assertIn("Possible causes:", msg)
        self.assertIn("--resume flag", msg)


if __name__ == '__main__':
    unittest.main()