#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Comprehensive tests for translation_service.py with exact production configuration values
"""

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


class TestChineseAITranslator:
    """Test suite for ChineseAITranslator class with production configuration"""
    
    def create_mock_logger(self):
        """Create a mock logger"""
        return Mock(spec=logging.Logger)
    
    def create_mock_pricing_manager(self):
        """Create a mock pricing manager"""
        manager = Mock()
        manager.calculate_cost.return_value = (0.05, {'input_cost': 0.03, 'output_cost': 0.02})
        return manager
    
    def create_translator_local(self):
        """Create a local translator instance with exact production values"""
        return ChineseAITranslator(
            logger=self.create_mock_logger(),
            use_remote=False,
            pricing_manager=self.create_mock_pricing_manager(),
            temperature=0.05  # Exact production value
        )
    
    def create_translator_remote(self):
        """Create a remote translator instance with exact production values"""
        return ChineseAITranslator(
            logger=self.create_mock_logger(),
            use_remote=True,
            api_key="test_key",
            temperature=0.05  # Exact production value
        )
    
    def test_init_local(self):
        """Test local translator initialization with production values"""
        translator = self.create_translator_local()
        
        assert not translator.is_remote
        assert translator.api_url == 'http://localhost:1234/v1/chat/completions'  # Production value
        assert translator.MODEL_NAME == "qwen3-30b-a3b-mlx@8bit"  # Production model
        assert translator.temperature == 0.05  # Production temperature
        assert translator.total_cost == 0.0
        assert translator.request_count == 0
    
    def test_init_remote(self):
        """Test remote translator initialization with production values"""
        translator = self.create_translator_remote()
        
        assert translator.is_remote
        assert translator.api_url == 'https://openrouter.ai/api/v1/chat/completions'  # Production URL
        assert translator.MODEL_NAME == 'deepseek/deepseek-r1:nitro'  # Production model
        assert translator.api_key == "test_key"
        assert translator.temperature == 0.05  # Production temperature
        assert translator.total_cost == 0.0
        assert translator.request_count == 0
    
    def test_init_remote_no_api_key(self):
        """Test remote translator without API key logs error"""
        mock_logger = self.create_mock_logger()
        
        with patch.dict(os.environ, {}, clear=True):
            translator = ChineseAITranslator(
                logger=mock_logger,
                use_remote=True,
                api_key=None
            )
            mock_logger.error.assert_called_once_with(
                "OPENROUTER_API_KEY not set in environment variables"
            )
    
    def test_log_method(self):
        """Test logging method"""
        translator = self.create_translator_local()
        
        translator.log("Test message")
        translator.logger.info.assert_called_once_with("Test message")
        
        translator.log("Error message", "error")
        translator.logger.error.assert_called_once_with("Error message")
        
        translator.log("Warning message", "warning")
        translator.logger.warning.assert_called_once_with("Warning message")
    
    def test_remove_thinking_block(self):
        """Test removal of thinking blocks"""
        translator = self.create_translator_local()
        
        # Test <think> tag
        text = "Hello <think>internal thoughts</think> world"
        result = translator.remove_thinking_block(text)
        assert result == "Hello  world"
        
        # Test <thinking> tag
        text = "Start <thinking>more thoughts\nwith newline</thinking>\nEnd"
        result = translator.remove_thinking_block(text)
        assert result == "Start End"
        
        # Test multiple tags
        text = "<think>thought1</think>Text<thinking>thought2</thinking>More"
        result = translator.remove_thinking_block(text)
        assert result == "TextMore"
    
    def test_production_prompts_local(self):
        """Test that local API uses exact production prompts"""
        translator = self.create_translator_local()
        
        # Test system prompt (local uses extensive system prompt)
        assert translator.system_prompt_local.startswith(";; You are a professional, authentic machine translation engine")
        assert "元婴` must be translated as `Nascent Soul`" in translator.system_prompt_local
        assert "Tang Wutong (Dancing Willow)" in translator.system_prompt_local
        assert "NO Chinese characters" in translator.system_prompt_local
        
        # Test user prompts
        user_prompt = translator.get_user_prompt_local("test text", True)
        assert user_prompt.startswith(";; Answer with the professional english translation")
        
        user_prompt_second = translator.get_user_prompt_local("test text", False)
        assert user_prompt_second.startswith(";; Examine the following text containing a mix of english and chinese")
    
    def test_production_prompts_remote(self):
        """Test that remote API uses exact production prompts"""
        translator = self.create_translator_remote()
        
        # Remote uses empty system prompt
        assert translator.system_prompt_remote == ""
        
        # Test first pass prompt
        user_prompt = translator.get_user_prompt_remote("test text", True)
        assert user_prompt.startswith(";; [Task]")
        assert "Tang Wutong (Dancing Willow)" in user_prompt
        assert "元婴` must be translated as `Nascent Soul`" in user_prompt
        assert "deepseek/deepseek-r1:nitro" not in user_prompt  # Model name not in prompt
        
        # Test second pass prompt  
        user_prompt_second = translator.get_user_prompt_remote("test text", False)
        assert user_prompt_second.startswith(";; [TASK]")
        assert "EDITING RULES" in user_prompt_second
    
    @patch('requests.post')
    def test_translate_messages_success_local(self, mock_post):
        """Test successful translation with local API and production values"""
        translator = self.create_translator_local()
        
        # Mock successful response
        mock_response = Mock()
        mock_response.json.return_value = {
            'choices': [{
                'message': {
                    'content': 'Translated text in English'
                }
            }],
            'usage': {
                'prompt_tokens': 100,
                'completion_tokens': 50,
                'total_tokens': 150
            }
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        result = translator.translate_messages("Test message")
        
        assert result == "Translated text in English"
        assert mock_post.called
        assert translator.pricing_manager.calculate_cost.called
        
        # Verify production endpoint and model used
        call_args = mock_post.call_args
        assert call_args[0][0] == 'http://localhost:1234/v1/chat/completions'
        assert call_args[1]['json']['model'] == 'qwen3-30b-a3b-mlx@8bit'
        assert call_args[1]['json']['temperature'] == 0.05
    
    @patch('requests.post')
    def test_translate_messages_success_remote(self, mock_post):
        """Test successful translation with remote API and cost tracking"""
        translator = self.create_translator_remote()
        
        # Mock successful response with cost
        mock_response = Mock()
        mock_response.json.return_value = {
            'choices': [{
                'message': {
                    'content': 'Translated text in English'
                }
            }],
            'usage': {
                'prompt_tokens': 100,
                'completion_tokens': 50,
                'total_tokens': 150,
                'cost': 0.0025
            }
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        result = translator.translate_messages("Test message")
        
        assert result == "Translated text in English"
        assert translator.total_cost == 0.0025
        assert translator.total_tokens == 150
        assert translator.request_count == 1
        
        # Verify usage tracking was enabled and production values used
        call_args = mock_post.call_args
        assert call_args[1]['json']['usage'] == {'include': True}
        assert call_args[0][0] == 'https://openrouter.ai/api/v1/chat/completions'
        assert call_args[1]['json']['model'] == 'deepseek/deepseek-r1:nitro'
        assert call_args[1]['json']['temperature'] == 0.05
    
    @patch('requests.post')
    def test_translate_messages_thinking_removal(self, mock_post):
        """Test thinking block removal from response"""
        translator = self.create_translator_local()
        
        mock_response = Mock()
        mock_response.json.return_value = {
            'choices': [{
                'message': {
                    'content': '<think>Internal thought</think>Actual translation'
                }
            }]
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        result = translator.translate_messages("Test")
        assert result == "Actual translation"
    
    @patch('requests.post')
    def test_translate_messages_non_latin_retry(self, mock_post):
        """Test retry when translation is not Latin charset"""
        translator = self.create_translator_local()
        
        # First response with Chinese characters
        mock_response1 = Mock()
        mock_response1.json.return_value = {
            'choices': [{
                'message': {
                    'content': '这是中文文本'  # Chinese text
                }
            }]
        }
        mock_response1.raise_for_status = Mock()
        
        # Second response with English
        mock_response2 = Mock()
        mock_response2.json.return_value = {
            'choices': [{
                'message': {
                    'content': 'This is English text'
                }
            }]
        }
        mock_response2.raise_for_status = Mock()
        
        mock_post.side_effect = [mock_response1, mock_response2]
        
        result = translator.translate_messages("Test")
        assert result == "This is English text"
        assert mock_post.call_count == 2
    
    def test_configuration_constants(self):
        """Test that production configuration constants are correct"""
        translator_local = self.create_translator_local()
        translator_remote = self.create_translator_remote()
        
        # Test connection timeouts (production values)
        assert translator_local.connection_timeout == 30  # seconds
        assert translator_remote.connection_timeout == 30
        
        # Test response timeouts (production values)  
        assert translator_local.timeout == 300  # seconds
        assert translator_remote.timeout == 300
        
        # Test model names (exact production values)
        assert translator_local.MODEL_NAME == "qwen3-30b-a3b-mlx@8bit"
        assert translator_remote.MODEL_NAME == "deepseek/deepseek-r1:nitro"
        
        # Test API endpoints (exact production values)
        assert translator_local.api_url == "http://localhost:1234/v1/chat/completions"
        assert translator_remote.api_url == "https://openrouter.ai/api/v1/chat/completions"
    
    def test_cost_summary_formatting_with_production_model(self):
        """Test cost summary formatting with production model names"""
        translator = self.create_translator_remote()
        
        # Set test values
        with translator._cost_lock:
            translator.total_cost = 0.12345
            translator.total_tokens = 50000
            translator.total_prompt_tokens = 30000
            translator.total_completion_tokens = 20000
            translator.request_count = 25
            translator.MODEL_NAME = "deepseek/deepseek-r1:nitro"  # Production model
        
        # Get formatted summary
        summary = translator.format_cost_summary()
        
        # Verify formatting with production model
        assert "Total Cost: $0.123450" in summary
        assert "Model: deepseek/deepseek-r1:nitro" in summary
        assert "API Type: remote" in summary
    
    def test_reset_cost_tracking(self):
        """Test resetting cost tracking"""
        translator = self.create_translator_remote()
        
        # Set some values
        with translator._cost_lock:
            translator.total_cost = 1.0
            translator.total_tokens = 1000
            translator.request_count = 5
        
        # Reset
        translator.reset_cost_tracking()
        
        # Verify all reset
        assert translator.total_cost == 0.0
        assert translator.total_tokens == 0
        assert translator.total_prompt_tokens == 0
        assert translator.total_completion_tokens == 0
        assert translator.request_count == 0


class TestUtilityFunctions:
    """Test utility functions"""
    
    def test_is_latin_char(self):
        """Test Latin character detection"""
        assert is_latin_char('A') == True
        assert is_latin_char('é') == True
        assert is_latin_char('ñ') == True
        assert is_latin_char('中') == False
        assert is_latin_char('あ') == False
        assert is_latin_char('🙂') == False
    
    def test_is_latin_charset(self):
        """Test Latin charset detection"""
        # Pure Latin text
        assert is_latin_charset("Hello World!") == True
        assert is_latin_charset("Café résumé naïve") == True
        
        # Mixed with some non-Latin
        assert is_latin_charset("Hello 世界") == False
        assert is_latin_charset("99% English 中") == False
        
        # Pure non-Latin
        assert is_latin_charset("你好世界") == False
        assert is_latin_charset("こんにちは") == False
        
        # Edge cases
        assert is_latin_charset("") == True  # Empty string
        assert is_latin_charset("   ") == True  # Only spaces
        assert is_latin_charset("123") == True  # Numbers
        
        # Test threshold
        text = "A" * 99 + "中"  # 1% non-Latin
        assert is_latin_charset(text, threshold=0.02) == True
        assert is_latin_charset(text, threshold=0.005) == False


class TestRetryWrapper:
    """Test retry_with_tenacity wrapper with production retry settings"""
    
    def test_retry_on_http_error(self):
        """Test retry on HTTP errors with production retry count (7 attempts)"""
        mock_obj = Mock()
        mock_obj.logger = Mock(spec=logging.Logger)
        mock_obj.max_retries = 7
        mock_obj.retry_wait_base = 1.0
        mock_obj.retry_wait_min = 3.0
        mock_obj.retry_wait_max = 60.0
        
        # Create a method that fails then succeeds (within 7 attempts)
        call_count = 0
        def failing_method(self):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise requests.exceptions.HTTPError("Server error")
            return "Success"
        
        # Apply decorator
        wrapped = retry_with_tenacity(failing_method)
        
        # Test
        result = wrapped(mock_obj)
        assert result == "Success"
        assert call_count == 3
    
    def test_retry_on_translation_exception(self):
        """Test retry on TranslationException"""
        mock_obj = Mock()
        mock_obj.logger = Mock(spec=logging.Logger)
        mock_obj.max_retries = 7
        mock_obj.retry_wait_base = 1.0
        mock_obj.retry_wait_min = 3.0
        mock_obj.retry_wait_max = 60.0
        
        call_count = 0
        def failing_method(self):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise TranslationException("Translation failed")
            return "Success"
        
        wrapped = retry_with_tenacity(failing_method)
        result = wrapped(mock_obj)
        assert result == "Success"
        assert call_count == 2


if __name__ == "__main__":
    # Run tests manually
    test_translator = TestChineseAITranslator()
    test_utils = TestUtilityFunctions()
    test_retry = TestRetryWrapper()
    
    test_methods = [
        # Translator tests
        (test_translator, 'test_init_local'),
        (test_translator, 'test_init_remote'),
        (test_translator, 'test_init_remote_no_api_key'),
        (test_translator, 'test_log_method'),
        (test_translator, 'test_remove_thinking_block'),
        (test_translator, 'test_production_prompts_local'),
        (test_translator, 'test_production_prompts_remote'),
        (test_translator, 'test_translate_messages_success_local'),
        (test_translator, 'test_translate_messages_success_remote'),
        (test_translator, 'test_translate_messages_thinking_removal'),
        (test_translator, 'test_translate_messages_non_latin_retry'),
        (test_translator, 'test_configuration_constants'),
        (test_translator, 'test_cost_summary_formatting_with_production_model'),
        (test_translator, 'test_reset_cost_tracking'),
        
        # Utility tests
        (test_utils, 'test_is_latin_char'),
        (test_utils, 'test_is_latin_charset'),
        
        # Retry tests
        (test_retry, 'test_retry_on_http_error'),
        (test_retry, 'test_retry_on_translation_exception'),
    ]
    
    passed = 0
    failed = 0
    
    for test_instance, method_name in test_methods:
        try:
            method = getattr(test_instance, method_name)
            method()
            print(f"✓ {method_name}")
            passed += 1
        except Exception as e:
            print(f"✗ {method_name}: {e}")
            failed += 1
    
    print(f"\nResults: {passed} passed, {failed} failed")
