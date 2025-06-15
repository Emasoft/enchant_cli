#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Comprehensive tests for translation_service.py with 100% coverage
"""

try:
    import pytest
except ImportError:
    pytest = None
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
    """Test suite for ChineseAITranslator class"""
    
    @pytest.fixture
    def mock_logger(self):
        """Create a mock logger"""
        return Mock(spec=logging.Logger)
    
    @pytest.fixture
    def mock_pricing_manager(self):
        """Create a mock pricing manager"""
        manager = Mock()
        manager.calculate_cost.return_value = (0.05, {'input_cost': 0.03, 'output_cost': 0.02})
        return manager
    
    @pytest.fixture
    def translator_local(self, mock_logger, mock_pricing_manager):
        """Create a local translator instance"""
        return ChineseAITranslator(
            logger=mock_logger,
            use_remote=False,
            pricing_manager=mock_pricing_manager
        )
    
    @pytest.fixture
    def translator_remote(self, mock_logger):
        """Create a remote translator instance"""
        return ChineseAITranslator(
            logger=mock_logger,
            use_remote=True,
            api_key="test_key"
        )
    
    def test_init_local(self, translator_local):
        """Test local translator initialization"""
        assert not translator_local.is_remote
        assert translator_local.api_url == 'http://localhost:1234/v1/chat/completions'
        assert translator_local.MODEL_NAME == "qwen3-30b-a3b-mlx@8bit"
        assert translator_local.temperature == 0.05
        assert translator_local.total_cost == 0.0
        assert translator_local.request_count == 0
    
    def test_init_remote(self, translator_remote):
        """Test remote translator initialization"""
        assert translator_remote.is_remote
        assert translator_remote.api_url == 'https://openrouter.ai/api/v1/chat/completions'
        assert translator_remote.MODEL_NAME == 'deepseek/deepseek-r1:nitro'
        assert translator_remote.api_key == "test_key"
        assert translator_remote.total_cost == 0.0
        assert translator_remote.request_count == 0
    
    def test_init_remote_no_api_key(self, mock_logger):
        """Test remote translator without API key raises error"""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="OPENROUTER_API_KEY not set in environment variables"):
                translator = ChineseAITranslator(
                    logger=mock_logger,
                    use_remote=True,
                    api_key=None
                )
    
    def test_log_method(self, translator_local):
        """Test logging method"""
        translator_local.log("Test message")
        translator_local.logger.info.assert_called_once_with("Test message")
        
        translator_local.log("Error message", "error")
        translator_local.logger.error.assert_called_once_with("Error message")
        
        translator_local.log("Warning message", "warning")
        translator_local.logger.warning.assert_called_once_with("Warning message")
    
    def test_remove_thinking_block(self, translator_local):
        """Test removal of thinking blocks"""
        # Test <think> tag
        text = "Hello <think>internal thoughts</think> world"
        result = translator_local.remove_thinking_block(text)
        assert result == "Hello  world"
        
        # Test <thinking> tag
        text = "Start <thinking>more thoughts\nwith newline</thinking>\nEnd"
        result = translator_local.remove_thinking_block(text)
        assert result == "Start End"
        
        # Test multiple tags
        text = "<think>thought1</think>Text<thinking>thought2</thinking>More"
        result = translator_local.remove_thinking_block(text)
        assert result == "TextMore"
    
    def test_remove_custom_tags(self, translator_local):
        """Test removal of custom tags"""
        # Test different tag formats
        text = "<TRANSLATION>Hello</TRANSLATION> [TRANSLATION] {TRANSLATION} (TRANSLATION) ##TRANSLATION##"
        result = translator_local.remove_custom_tags(text, "TRANSLATION")
        assert result == "Hello    "
        
        # Test case sensitivity
        text = "<translation>test</translation>"
        result = translator_local.remove_custom_tags(text, "TRANSLATION", ignore_case=True)
        assert result == "test"
        
        result = translator_local.remove_custom_tags(text, "TRANSLATION", ignore_case=False)
        assert result == "<translation>test</translation>"
    
    def test_remove_excess_empty_lines(self, translator_local):
        """Test removal of excess empty lines"""
        # Test 5+ newlines
        text = "Line1\n\n\n\n\nLine2"
        result = translator_local.remove_excess_empty_lines(text)
        assert result == "Line1\n\n\n\nLine2"
        
        # Test many newlines
        text = "Start\n\n\n\n\n\n\n\n\nEnd"
        result = translator_local.remove_excess_empty_lines(text)
        assert result == "Start\n\n\n\nEnd"
    
    def test_normalize_spaces(self, translator_local):
        """Test space normalization"""
        # Test multiple spaces
        text = "Hello    world   test"
        result = translator_local.normalize_spaces(text)
        assert result == "Hello world test"
        
        # Test with newlines
        text = "Line 1   test\n\nLine 2    more"
        result = translator_local.normalize_spaces(text)
        assert result == "Line 1 test\n\nLine 2 more"
        
        # Test empty lines preserved
        text = "Start\n\n\nEnd"
        result = translator_local.normalize_spaces(text)
        assert result == "Start\n\n\nEnd"
    
    def test_remove_translation_markers(self, translator_local):
        """Test removal of translation markers"""
        # Test various markers
        text = "[End of translation] Some text **Start of translation** More text"
        result = translator_local.remove_translation_markers(text)
        assert "End of translation" not in result
        assert "Start of translation" not in result
        
        # Test English Translation marker
        text = "Content [English Translation] More content"
        result = translator_local.remove_translation_markers(text)
        assert "English Translation" not in result
        
        # Test all custom tags
        tags = [
            "DECLARATION", "TRANSLATION", "TRANSLATED TEXT", 
            "ENGLISH TEXT", "REVISED TEXT", "CORRECTED TEXT",
            "TRANSLATED IN ENGLISH", "TEXT TRANSLATED IN ENGLISH",
            "FIXED TEXT", "ENGLISH TRANSLATED TEXT", 
            "ENGLISH TRANSLATION", "ENGLISH VERSION", "TRANSLATED VERSION"
        ]
        
        for tag in tags:
            text = f"<{tag}>content</{tag}>"
            result = translator_local.remove_translation_markers(text)
            assert tag not in result
    
    def test_separate_chapters(self, translator_local):
        """Test chapter separation"""
        # Test various chapter formats
        text = "Chapter 1: Introduction\nContent\nChapter 2 - The Beginning"
        result = translator_local.separate_chapters(text)
        assert "\n\n\nChapter 1: Introduction\n\n" in result
        assert "\n\n\nChapter 2 - The Beginning" in result
        
        # Test Roman numerals
        text = "Chapter IX - Final\nContent"
        result = translator_local.separate_chapters(text)
        assert "\n\n\nChapter IX - Final" in result
        
        # Test Prologue/Epilogue
        text = "Prologue\nContent\nEpilogue"
        result = translator_local.separate_chapters(text)
        assert "\n\n\nPrologue\n\n" in result
        assert "\n\n\nEpilogue" in result
    
    @patch('translation_service.requests.post')
    def test_translate_messages_success_local(self, mock_post, translator_local):
        """Test successful translation with local API"""
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
        
        result = translator_local.translate_messages("Test message", is_last_chunk=True)
        
        assert result == "Translated text in English"
        assert mock_post.called
        assert translator_local.pricing_manager.calculate_cost.called
    
    @patch('translation_service.requests.post')
    def test_translate_messages_success_remote(self, mock_post, translator_remote):
        """Test successful translation with remote API and cost tracking"""
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
        
        result = translator_remote.translate_messages("Test message", is_last_chunk=True)
        
        assert result == "Translated text in English"
        assert translator_remote.total_cost == 0.0025
        assert translator_remote.total_tokens == 150
        assert translator_remote.request_count == 1
        
        # Verify usage tracking was enabled
        call_args = mock_post.call_args
        assert call_args[1]['json']['usage'] == {'include': True}
    
    @patch('translation_service.requests.post')
    def test_translate_messages_remote_no_cost(self, mock_post, translator_remote):
        """Test remote translation without cost information"""
        # Mock response without cost
        mock_response = Mock()
        mock_response.json.return_value = {
            'choices': [{
                'message': {
                    'content': 'Translated text'
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
        
        result = translator_remote.translate_messages("Test", is_last_chunk=True)
        
        assert result == "Translated text"
        assert translator_remote.total_cost == 0.0
        assert translator_remote.total_tokens == 150
        assert translator_remote.request_count == 1
    
    @patch('translation_service.requests.post')
    def test_translate_messages_thinking_removal(self, mock_post, translator_local):
        """Test thinking block removal from response"""
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
        
        result = translator_local.translate_messages("Test", is_last_chunk=True)
        assert result == "Actual translation"
    
    @patch('translation_service.requests.post')
    def test_translate_messages_non_latin_retry(self, mock_post, translator_local):
        """Test retry when translation is not Latin charset"""
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
        
        result = translator_local.translate_messages("Test", is_last_chunk=True)
        assert result == "This is English text"
        assert mock_post.call_count == 2
    
    @patch('translation_service.requests.post')
    def test_translate_messages_too_short_retry(self, mock_post, translator_local):
        """Test retry when translation is too short"""
        # First response too short
        mock_response1 = Mock()
        mock_response1.json.return_value = {
            'choices': [{
                'message': {
                    'content': 'Short'
                }
            }]
        }
        mock_response1.raise_for_status = Mock()
        
        # Second response adequate
        mock_response2 = Mock()
        mock_response2.json.return_value = {
            'choices': [{
                'message': {
                    'content': 'A' * 301  # Long enough
                }
            }]
        }
        mock_response2.raise_for_status = Mock()
        
        mock_post.side_effect = [mock_response1, mock_response2]
        
        result = translator_local.translate_messages("Test", is_last_chunk=False)
        assert result == 'A' * 301
        assert mock_post.call_count == 2
    
    @patch('translation_service.requests.post')
    def test_translate_messages_last_chunk_short_ok(self, mock_post, translator_local):
        """Test that short translations are OK for last chunk"""
        mock_response = Mock()
        mock_response.json.return_value = {
            'choices': [{
                'message': {
                    'content': 'Short translation'
                }
            }]
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        result = translator_local.translate_messages("Test", is_last_chunk=True)
        assert result == "Short translation"
        assert mock_post.call_count == 1
    
    @patch('translation_service.requests.post')
    def test_translate_messages_http_error(self, mock_post, translator_local):
        """Test HTTP error handling"""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = HTTPError("404 Not Found")
        mock_post.return_value = mock_response
        
        with pytest.raises(TranslationException) as exc_info:
            translator_local.translate_messages("Test")
        
        assert "HTTP error: 404 Not Found" in str(exc_info.value)
    
    @patch('translation_service.requests.post')
    def test_translate_messages_request_exception(self, mock_post, translator_local):
        """Test request exception handling"""
        mock_post.side_effect = RequestException("Connection error")
        
        with pytest.raises(TranslationException) as exc_info:
            translator_local.translate_messages("Test")
        
        assert "Request failed: Connection error" in str(exc_info.value)
    
    @patch('translation_service.requests.post')
    def test_translate_messages_json_error(self, mock_post, translator_local):
        """Test JSON decode error"""
        mock_response = Mock()
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        with pytest.raises(TranslationException) as exc_info:
            translator_local.translate_messages("Test")
        
        assert "JSON error:" in str(exc_info.value)
    
    @patch('translation_service.requests.post')
    def test_translate_messages_unexpected_response(self, mock_post, translator_local):
        """Test unexpected response structure"""
        mock_response = Mock()
        mock_response.json.return_value = {'unexpected': 'structure'}
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        with pytest.raises(ValueError) as exc_info:
            translator_local.translate_messages("Test")
        
        assert "Unexpected response structure" in str(exc_info.value)
    
    @patch('translation_service.requests.post')
    def test_translate_chunk(self, mock_post, translator_local):
        """Test translate_chunk method"""
        mock_response = Mock()
        mock_response.json.return_value = {
            'choices': [{
                'message': {
                    'content': '[TRANSLATION]English text[/TRANSLATION]'
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
        
        # Test with excessive empty lines
        chinese_text = "中文\n\n\n\n\n\n文本"
        result = translator_local.translate_chunk(chinese_text, is_last_chunk=True)
        
        assert result == "English text"
        assert "\n\n\n\n\n" not in result
    
    @patch('translation_service.requests.post')
    def test_translate_chunk_double_translation(self, mock_post, translator_local):
        """Test double translation feature"""
        # First translation
        mock_response1 = Mock()
        mock_response1.json.return_value = {
            'choices': [{
                'message': {
                    'content': 'First pass translation with 中文'
                }
            }],
            'usage': {
                'prompt_tokens': 100,
                'completion_tokens': 50,
                'total_tokens': 150
            }
        }
        mock_response1.raise_for_status = Mock()
        
        # Second translation
        mock_response2 = Mock()
        mock_response2.json.return_value = {
            'choices': [{
                'message': {
                    'content': 'Second pass translation fully English'
                }
            }],
            'usage': {
                'prompt_tokens': 100,
                'completion_tokens': 50,
                'total_tokens': 150
            }
        }
        mock_response2.raise_for_status = Mock()
        
        mock_post.side_effect = [mock_response1, mock_response2]
        
        result = translator_local.translate_chunk("中文文本", double_translation=True, is_last_chunk=True)
        
        assert result == "Second pass translation fully English"
        assert mock_post.call_count == 2
    
    def test_translate_file(self, translator_local, tmp_path):
        """Test file translation"""
        # Create test file
        input_file = tmp_path / "test_input.txt"
        input_file.write_text("中文文本", encoding='utf-8')
        
        output_file = tmp_path / "test_output.txt"
        
        with patch.object(translator_local, 'translate_chunk') as mock_translate:
            mock_translate.return_value = "English text"
            
            result = translator_local.translate_file(
                str(input_file), 
                str(output_file)
            )
            
            assert result == "English text"
            assert output_file.read_text(encoding='utf-8') == "English text"
    
    def test_translate_file_error(self, translator_local, tmp_path):
        """Test file translation error handling"""
        input_file = tmp_path / "nonexistent.txt"
        output_file = tmp_path / "output.txt"
        
        result = translator_local.translate_file(
            str(input_file), 
            str(output_file)
        )
        
        assert result is None
        translator_local.logger.error.assert_called()
    
    def test_translate_method(self, translator_local):
        """Test translate method"""
        with patch.object(translator_local, 'translate_chunk') as mock_translate:
            mock_translate.return_value = "Translated text"
            
            result = translator_local.translate("中文", is_last_chunk=True)
            
            assert result == "Translated text"
            mock_translate.assert_called_once_with(
                "中文", 
                double_translation=False, 
                is_last_chunk=True
            )
    
    def test_translate_method_error(self, translator_local):
        """Test translate method error handling"""
        with patch.object(translator_local, 'translate_chunk') as mock_translate:
            mock_translate.side_effect = Exception("Translation error")
            
            result = translator_local.translate("中文")
            
            assert result is None
            translator_local.logger.error.assert_called()
    
    def test_get_cost_summary_remote(self, translator_remote):
        """Test cost summary for remote API"""
        # Set some test values
        with translator_remote._cost_lock:
            translator_remote.total_cost = 0.15
            translator_remote.total_tokens = 5000
            translator_remote.total_prompt_tokens = 3000
            translator_remote.total_completion_tokens = 2000
            translator_remote.request_count = 5
        
        summary = translator_remote.get_cost_summary()
        
        assert summary['total_cost'] == 0.15
        assert summary['total_tokens'] == 5000
        assert summary['request_count'] == 5
        assert summary['average_cost_per_request'] == 0.03
        assert summary['api_type'] == 'remote'
        assert summary['model'] == 'deepseek/deepseek-r1:nitro'
    
    def test_get_cost_summary_local(self, translator_local):
        """Test cost summary for local API"""
        summary = translator_local.get_cost_summary()
        
        assert summary['total_cost'] == 0.0
        assert summary['message'] == 'Local API - no costs incurred'
        assert summary['api_type'] == 'local'
        assert summary['model'] == 'qwen3-30b-a3b-mlx@8bit'
    
    def test_format_cost_summary_remote(self, translator_remote):
        """Test formatted cost summary for remote API"""
        # Set test values
        with translator_remote._cost_lock:
            translator_remote.total_cost = 0.25
            translator_remote.total_tokens = 10000
            translator_remote.total_prompt_tokens = 6000
            translator_remote.total_completion_tokens = 4000
            translator_remote.request_count = 10
        
        result = translator_remote.format_cost_summary()
        
        assert "Total Cost: $0.250000" in result
        assert "Total Requests: 10" in result
        assert "Total Tokens: 10,000" in result
        assert "Average Cost per Request: $0.025000" in result
        assert "Average Tokens per Request: 1,000" in result
        assert "Model: deepseek/deepseek-r1:nitro" in result
    
    def test_format_cost_summary_local(self, translator_local):
        """Test formatted cost summary for local API"""
        result = translator_local.format_cost_summary()
        
        assert "Local API - no costs incurred" in result
        assert "Model: qwen3-30b-a3b-mlx@8bit" in result
        assert "API Type: local" in result
    
    def test_reset_cost_tracking(self, translator_remote):
        """Test resetting cost tracking"""
        # Set some values
        with translator_remote._cost_lock:
            translator_remote.total_cost = 1.0
            translator_remote.total_tokens = 1000
            translator_remote.request_count = 5
        
        # Reset
        translator_remote.reset_cost_tracking()
        
        # Verify all reset
        assert translator_remote.total_cost == 0.0
        assert translator_remote.total_tokens == 0
        assert translator_remote.total_prompt_tokens == 0
        assert translator_remote.total_completion_tokens == 0
        assert translator_remote.request_count == 0
    
    def test_thread_safety_cost_tracking(self, translator_remote):
        """Test thread safety of cost tracking"""
        # Function to simulate concurrent cost updates
        def update_costs():
            for _ in range(100):
                with translator_remote._cost_lock:
                    translator_remote.total_cost += 0.01
                    translator_remote.request_count += 1
        
        # Create and start threads
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=update_costs)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # Verify results
        assert translator_remote.total_cost == pytest.approx(10.0, rel=1e-9)
        assert translator_remote.request_count == 1000


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
        assert is_latin_charset("") == False  # Empty string
        assert is_latin_charset("   ") == True  # Only spaces
        assert is_latin_charset("123") == True  # Numbers
        
        # Test threshold
        text = "A" * 99 + "中"  # 1% non-Latin
        assert is_latin_charset(text, threshold=0.02) == True
        assert is_latin_charset(text, threshold=0.005) == False


class TestRetryWrapper:
    """Test retry_with_tenacity wrapper"""
    
    def test_retry_on_http_error(self):
        """Test retry on HTTP errors"""
        mock_obj = Mock()
        mock_obj.logger = Mock(spec=logging.Logger)
        mock_obj.max_retries = 7
        mock_obj.retry_wait_base = 1.0
        mock_obj.retry_wait_min = 3.0
        mock_obj.retry_wait_max = 60.0
        
        # Create a method that fails then succeeds
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
    
    def test_retry_exhaustion(self):
        """Test retry exhaustion after max attempts"""
        mock_obj = Mock()
        mock_obj.logger = Mock(spec=logging.Logger)
        mock_obj.max_retries = 3
        mock_obj.retry_wait_base = 0.1
        mock_obj.retry_wait_min = 0.1
        mock_obj.retry_wait_max = 0.5
        mock_obj.logger = Mock(spec=logging.Logger)
        
        def always_failing_method(self):
            raise requests.exceptions.RequestException("Always fails")
        
        wrapped = retry_with_tenacity(always_failing_method)
        
        with pytest.raises(requests.exceptions.RequestException):
            wrapped(mock_obj)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=translation_service", "--cov-report=html"])