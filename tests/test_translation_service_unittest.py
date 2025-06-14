#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Comprehensive tests for translation_service.py with 100% coverage
"""

import unittest
import json
import logging
import threading
import time
from unittest.mock import Mock, patch, MagicMock, call
import requests
from requests.exceptions import HTTPError, RequestException, Timeout

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from translation_service import (
    ChineseAITranslator, TranslationException, is_latin_char, 
    is_latin_charset, retry_with_tenacity
)


class TestChineseAITranslator(unittest.TestCase):
    """Test suite for ChineseAITranslator class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_logger = Mock(spec=logging.Logger)
        self.mock_pricing_manager = Mock()
        self.mock_pricing_manager.calculate_cost.return_value = (0.05, {'input_cost': 0.03, 'output_cost': 0.02})
        
        # Create translators
        self.translator_local = ChineseAITranslator(
            logger=self.mock_logger,
            use_remote=False,
            pricing_manager=self.mock_pricing_manager
        )
        
        self.translator_remote = ChineseAITranslator(
            logger=self.mock_logger,
            use_remote=True,
            api_key="test-key",
            pricing_manager=self.mock_pricing_manager
        )
    
    def test_initialization_local(self):
        """Test local translator initialization"""
        translator = ChineseAITranslator(use_remote=False)
        self.assertFalse(translator.is_remote)
        self.assertEqual(translator.endpoint, "http://localhost:1234/v1/chat/completions")
        self.assertIsNone(translator.api_key)
        self.assertEqual(translator.total_cost, 0.0)
        self.assertEqual(translator.request_count, 0)
    
    def test_initialization_remote(self):
        """Test remote translator initialization"""
        translator = ChineseAITranslator(use_remote=True, api_key="test-key")
        self.assertTrue(translator.is_remote)
        self.assertEqual(translator.endpoint, "https://openrouter.ai/api/v1/chat/completions")
        self.assertEqual(translator.api_key, "test-key")
    
    def test_translate_empty_text(self):
        """Test translation with empty text"""
        result = self.translator_local.translate("")
        self.assertEqual(result, "")
        result = self.translator_local.translate("   ")
        self.assertEqual(result, "")
    
    @patch('requests.post')
    def test_translate_success(self, mock_post):
        """Test successful translation"""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'choices': [{
                'message': {
                    'content': 'Hello, world!'
                }
            }],
            'usage': {
                'prompt_tokens': 10,
                'completion_tokens': 5,
                'total_tokens': 15
            }
        }
        mock_post.return_value = mock_response
        
        # Translate
        result = self.translator_remote.translate("你好，世界！")
        
        # Verify
        self.assertEqual(result, 'Hello, world!')
        self.assertEqual(self.translator_remote.request_count, 1)
        self.assertEqual(self.translator_remote.total_cost, 0.05)
    
    @patch('requests.post')
    def test_translate_retry_on_failure(self, mock_post):
        """Test translation retry mechanism"""
        # First call fails, second succeeds
        error_response = Mock()
        error_response.status_code = 500
        error_response.raise_for_status.side_effect = HTTPError("Server error")
        
        success_response = Mock()
        success_response.status_code = 200
        success_response.json.return_value = {
            'choices': [{'message': {'content': 'Success'}}],
            'usage': {'prompt_tokens': 10, 'completion_tokens': 5}
        }
        
        mock_post.side_effect = [error_response, success_response]
        
        # Should succeed after retry
        with patch('translation_service.time.sleep'):  # Speed up test
            result = self.translator_remote.translate("Test")
        
        self.assertEqual(result, 'Success')
        self.assertEqual(mock_post.call_count, 2)
    
    def test_is_latin_char(self):
        """Test Latin character detection"""
        self.assertTrue(is_latin_char('A'))
        self.assertTrue(is_latin_char('z'))
        self.assertTrue(is_latin_char('5'))
        self.assertFalse(is_latin_char('中'))
        self.assertFalse(is_latin_char('あ'))
    
    def test_is_latin_charset(self):
        """Test Latin charset detection"""
        self.assertTrue(is_latin_charset("Hello World 123"))
        self.assertTrue(is_latin_charset("Test!@#$%"))
        self.assertFalse(is_latin_charset("你好"))
        self.assertFalse(is_latin_charset("Hello 你好"))
        self.assertTrue(is_latin_charset("你", threshold=0))  # Edge case
    
    @patch('requests.post')
    def test_cost_tracking(self, mock_post):
        """Test cost tracking functionality"""
        # Mock multiple responses
        responses = []
        for i in range(3):
            resp = Mock()
            resp.status_code = 200
            resp.json.return_value = {
                'choices': [{'message': {'content': f'Translation {i}'}}],
                'usage': {'prompt_tokens': 10, 'completion_tokens': 5}
            }
            responses.append(resp)
        
        mock_post.side_effect = responses
        
        # Make multiple translations
        for i in range(3):
            self.translator_remote.translate(f"Text {i}")
        
        # Verify cost accumulation
        self.assertEqual(self.translator_remote.request_count, 3)
        self.assertEqual(self.translator_remote.total_cost, 0.15)  # 3 * 0.05


class TestUtilityFunctions(unittest.TestCase):
    """Test utility functions"""
    
    def test_retry_with_tenacity_decorator(self):
        """Test the retry_with_tenacity decorator"""
        call_count = 0
        
        @retry_with_tenacity
        def failing_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Temporary failure")
            return "Success"
        
        # Should succeed after retries
        with patch('translation_service.time.sleep'):  # Speed up test
            result = failing_function()
        
        self.assertEqual(result, "Success")
        self.assertEqual(call_count, 3)


if __name__ == '__main__':
    unittest.main()