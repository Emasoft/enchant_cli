#!/usr/bin/env python3
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
from unittest.mock import Mock, patch
from requests.exceptions import HTTPError, RequestException

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from enchant_book_manager.translation_service import (
    ChineseAITranslator,
    normalize_spaces,
)
from enchant_book_manager.text_validators import (
    is_latin_char,
    is_latin_charset,
    remove_thinking_block,
)
from enchant_book_manager.text_processing import (
    remove_excess_empty_lines,
)


class TestChineseAITranslator:
    """Test suite for ChineseAITranslator class"""

    @pytest.fixture
    def mock_logger(self):
        """Create a mock logger"""
        return Mock(spec=logging.Logger)

    @pytest.fixture
    def translator_local(self, mock_logger):
        """Create a local translator instance"""
        return ChineseAITranslator(logger=mock_logger, use_remote=False)

    @pytest.fixture
    def translator_remote(self, mock_logger):
        """Create a remote translator instance"""
        return ChineseAITranslator(logger=mock_logger, use_remote=True, api_key="test_key")

    def test_init_local(self, translator_local):
        """Test local translator initialization"""
        assert not translator_local.is_remote
        # Note: api_url is now in the API client
        assert translator_local.api_client.api_url == "http://localhost:1234/v1/chat/completions"
        assert translator_local.MODEL_NAME == "qwen3-30b-a3b-mlx@8bit"
        assert translator_local.temperature == 0.1
        assert translator_local.request_count == 0

    def test_init_remote(self, translator_remote):
        """Test remote translator initialization"""
        assert translator_remote.is_remote
        # Note: api_url and api_key are now in the API client
        assert translator_remote.api_client.api_url == "https://openrouter.ai/api/v1/chat/completions"
        assert translator_remote.MODEL_NAME == "deepseek/deepseek-r1:nitro"
        # api_key is no longer stored as an attribute
        assert translator_remote.request_count == 0

    def test_init_remote_no_api_key(self, mock_logger):
        """Test remote translator without API key raises error"""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="API key required for remote service"):
                ChineseAITranslator(logger=mock_logger, use_remote=True, api_key=None)

    def test_log_method(self, translator_local):
        """Test logging method"""
        translator_local.log("Test message")
        translator_local.logger.info.assert_called_once_with("Test message")

        translator_local.log("Error message", "error")
        translator_local.logger.error.assert_called_once_with("Error message")

        translator_local.log("Warning message", "warning")
        translator_local.logger.warning.assert_called_once_with("Warning message")

    def test_remove_thinking_block(self):
        """Test removal of thinking blocks"""
        # Test <think> tag
        text = "Hello <think>internal thoughts</think> world"
        result = remove_thinking_block(text)
        assert result == "Hello world"

        # Test <thinking> tag
        text = "Start <thinking>more thoughts\nwith newline</thinking>\nEnd"
        result = remove_thinking_block(text)
        assert result == "Start End"

        # Test multiple tags
        text = "<think>thought1</think>Text<thinking>thought2</thinking>More"
        result = remove_thinking_block(text)
        assert result == "TextMore"

    def test_remove_custom_tags(self):
        """Test removal of custom tags - functionality moved to validate_translation_output"""
        # This functionality is now part of validate_translation_output in text_validators
        # The tests for tag removal are covered in test_text_validators.py
        pass

    def test_remove_excess_empty_lines(self):
        """Test removal of excess empty lines"""
        # Test 5+ newlines - default max is 2
        text = "Line1\n\n\n\n\nLine2"
        result = remove_excess_empty_lines(text)
        assert result == "Line1\n\nLine2"

        # Test many newlines
        text = "Start\n\n\n\n\n\n\n\n\nEnd"
        result = remove_excess_empty_lines(text)
        assert result == "Start\n\nEnd"

    def test_normalize_spaces(self):
        """Test space normalization"""
        # Test multiple spaces
        text = "Hello    world   test"
        result = normalize_spaces(text)
        assert result == "Hello world test"

        # Test with newlines - trailing spaces are removed
        text = "Line 1   test\n\nLine 2    more"
        result = normalize_spaces(text)
        assert result == "Line 1 test\n\nLine 2 more"

        # Test empty lines preserved
        text = "Start\n\n\nEnd"
        result = normalize_spaces(text)
        assert result == "Start\n\n\nEnd"

    def test_remove_translation_markers(self):
        """Test removal of translation markers - functionality integrated into validate_translation_output"""
        # This functionality is now part of validate_translation_output in text_validators
        # which performs comprehensive cleaning during validation
        pass

    @patch("enchant_book_manager.api_clients.requests.post")
    def test_api_request_success_local(self, mock_post, translator_local):
        """Test successful translation with local API"""
        # Mock successful response for local API (uses "text" field)
        mock_response = Mock()
        mock_response.json.return_value = {
            "choices": [{"text": "Translated text in English"}],
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "total_tokens": 150,
            },
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        messages = translator_local.get_api_messages("Test message")
        result = translator_local.api_request_with_retry(messages)

        assert result == "Translated text in English"
        assert mock_post.called

    @patch("enchant_book_manager.api_clients.requests.post")
    def test_api_request_success_remote(self, mock_post, translator_remote):
        """Test successful translation with remote API and cost tracking"""
        # Mock successful response with cost
        mock_response = Mock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Translated text in English"}}],
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "total_tokens": 150,
                "cost": 0.0025,
            },
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        # Mock global cost tracker
        with patch("enchant_book_manager.translation_service.global_cost_tracker.track_usage") as mock_track_usage:
            mock_track_usage.return_value = 0.0025

            messages = translator_remote.get_api_messages("Test message")
            result = translator_remote.api_request_with_retry(messages)

            assert result == "Translated text in English"
            assert translator_remote.request_count == 1

            # Verify cost tracking was called
            mock_track_usage.assert_called_once()
            usage_arg = mock_track_usage.call_args[0][0]
            assert usage_arg["prompt_tokens"] == 100
            assert usage_arg["completion_tokens"] == 50
            assert usage_arg["total_tokens"] == 150
            assert usage_arg["cost"] == 0.0025

            # No need to verify usage tracking flag in new API

    @patch("enchant_book_manager.api_clients.requests.post")
    def test_api_request_remote_no_cost(self, mock_post, translator_remote):
        """Test remote translation without cost information"""
        # Mock response without cost
        mock_response = Mock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Translated text"}}],
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "total_tokens": 150,
            },
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        # Mock global cost tracker
        with patch("enchant_book_manager.translation_service.global_cost_tracker.track_usage") as mock_track_usage:
            mock_track_usage.return_value = 0.0  # No cost returned

            messages = translator_remote.get_api_messages("Test")
            result = translator_remote.api_request_with_retry(messages)

            assert result == "Translated text"
            assert translator_remote.request_count == 1

            # Verify cost tracking was called with usage data but no cost
            mock_track_usage.assert_called_once()
            usage_arg = mock_track_usage.call_args[0][0]
            assert usage_arg["prompt_tokens"] == 100
            assert usage_arg["completion_tokens"] == 50
            assert usage_arg["total_tokens"] == 150
            assert "cost" not in usage_arg  # No cost field in response

    def test_validate_and_clean_response(self, translator_local):
        """Test response validation and cleaning"""
        # Test the validate_and_clean_response method directly
        # Note: thinking block removal happens separately in remove_thinking_block
        raw_response = "Actual translation"
        is_valid, result = translator_local.validate_and_clean_response(raw_response)
        assert result == "Actual translation"
        assert is_valid  # Should be valid as it's in Latin charset

        # Test with non-Latin characters
        raw_response_chinese = "Translation with 中文 characters"
        is_valid, result = translator_local.validate_and_clean_response(raw_response_chinese)
        assert not is_valid  # Should be invalid due to Chinese characters
        assert result == raw_response_chinese  # Text is returned as-is

    @patch("enchant_book_manager.api_clients.requests.post")
    def test_translate_chunk_non_latin_retry(self, mock_post, translator_local):
        """Test retry when translation is not Latin charset"""
        # First response with Chinese characters
        mock_response1 = Mock()
        mock_response1.json.return_value = {
            "choices": [{"text": "这是中文文本"}]  # Chinese text
        }
        mock_response1.raise_for_status = Mock()

        # Second response with English
        mock_response2 = Mock()
        mock_response2.json.return_value = {"choices": [{"text": "This is English text"}]}
        mock_response2.raise_for_status = Mock()

        mock_post.side_effect = [mock_response1, mock_response2]

        result = translator_local.translate_chunk("Test", is_last_chunk=True)
        assert result == "This is English text"
        assert mock_post.call_count == 2

    @patch("enchant_book_manager.api_clients.requests.post")
    def test_translate_chunk_validates_response(self, mock_post, translator_local):
        """Test that translation validates response properly"""
        # First response with non-Latin characters
        mock_response1 = Mock()
        mock_response1.json.return_value = {"choices": [{"text": "这是中文"}]}  # Chinese text
        mock_response1.raise_for_status = Mock()

        # Second response with Latin text
        mock_response2 = Mock()
        mock_response2.json.return_value = {"choices": [{"text": "This is English text"}]}
        mock_response2.raise_for_status = Mock()

        mock_post.side_effect = [mock_response1, mock_response2]

        # The new implementation validates Latin charset
        result = translator_local.translate_chunk("Test", is_last_chunk=False)
        assert result == "This is English text"
        assert mock_post.call_count == 2

    @patch("enchant_book_manager.api_clients.requests.post")
    def test_translate_chunk_last_chunk(self, mock_post, translator_local):
        """Test that translation works for last chunk"""
        mock_response = Mock()
        mock_response.json.return_value = {"choices": [{"text": "Short translation"}]}
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        result = translator_local.translate_chunk("Test", is_last_chunk=True)
        assert result == "Short translation"
        assert mock_post.call_count == 1

    @patch("enchant_book_manager.common_utils.time.sleep")
    @patch("enchant_book_manager.api_clients.requests.post")
    def test_api_request_http_error(self, mock_post, mock_sleep, translator_local):
        """Test HTTP error handling"""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = HTTPError("404 Not Found")
        mock_post.return_value = mock_response

        # Test that HTTP errors are propagated
        messages = translator_local.get_api_messages("Test")
        result = translator_local.api_request_with_retry(messages, max_retries=1)

        # The retry mechanism should return None on failure
        assert result is None
        assert mock_post.call_count >= 1

    @patch("enchant_book_manager.common_utils.time.sleep")
    @patch("enchant_book_manager.api_clients.requests.post")
    def test_api_request_request_exception(self, mock_post, mock_sleep, translator_local):
        """Test request exception handling"""
        mock_post.side_effect = RequestException("Connection error")

        # Test that request exceptions are handled
        messages = translator_local.get_api_messages("Test")
        result = translator_local.api_request_with_retry(messages, max_retries=1)

        # The retry mechanism should return None on failure
        assert result is None
        assert mock_post.call_count >= 1

    @patch("enchant_book_manager.common_utils.time.sleep")
    @patch("enchant_book_manager.api_clients.requests.post")
    def test_api_request_json_error(self, mock_post, mock_sleep, translator_local):
        """Test JSON decode error"""
        mock_response = Mock()
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        # Test that JSON errors are handled
        messages = translator_local.get_api_messages("Test")
        result = translator_local.api_request_with_retry(messages, max_retries=1)

        # The retry mechanism should return None on failure
        assert result is None
        assert mock_post.call_count >= 1

    @patch("enchant_book_manager.common_utils.time.sleep")
    @patch("enchant_book_manager.api_clients.requests.post")
    def test_api_request_unexpected_response(self, mock_post, mock_sleep, translator_local):
        """Test unexpected response structure"""
        mock_response = Mock()
        mock_response.json.return_value = {"unexpected": "structure"}
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        # Test that unexpected responses are handled
        messages = translator_local.get_api_messages("Test")
        result = translator_local.api_request_with_retry(messages, max_retries=1)

        # The retry mechanism should return None on failure
        assert result is None
        assert mock_post.call_count >= 1

    @patch("enchant_book_manager.api_clients.requests.post")
    def test_translate_chunk_with_cleaning(self, mock_post, translator_local):
        """Test translate_chunk method"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "choices": [{"text": "English text"}],
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "total_tokens": 150,
            },
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        # Test basic translation
        chinese_text = "中文文本"
        result = translator_local.translate_chunk(chinese_text, is_last_chunk=True)

        assert result == "English text"

    @patch("enchant_book_manager.api_clients.requests.post")
    def test_translate_chunk_double_translation(self, mock_post, translator_local):
        """Test double translation feature"""
        # First translation
        mock_response1 = Mock()
        mock_response1.json.return_value = {
            "choices": [{"text": "First pass translation with 中文"}],
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "total_tokens": 150,
            },
        }
        mock_response1.raise_for_status = Mock()

        # Second translation
        mock_response2 = Mock()
        mock_response2.json.return_value = {
            "choices": [{"text": "Second pass translation fully English"}],
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "total_tokens": 150,
            },
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
        input_file.write_text("中文文本", encoding="utf-8")

        output_file = tmp_path / "test_output.txt"

        with patch.object(translator_local, "translate_chunk") as mock_translate:
            mock_translate.return_value = "English text"

            result = translator_local.translate_file(str(input_file), str(output_file))

            assert result == "English text"
            assert output_file.read_text(encoding="utf-8") == "English text"

    def test_translate_file_error(self, translator_local, tmp_path):
        """Test file translation error handling"""
        input_file = tmp_path / "nonexistent.txt"
        output_file = tmp_path / "output.txt"

        result = translator_local.translate_file(str(input_file), str(output_file))

        assert result is None
        translator_local.logger.error.assert_called()

    def test_translate_method(self, translator_local):
        """Test translate method"""
        with patch.object(translator_local, "translate_chunk") as mock_translate:
            mock_translate.return_value = "Translated text"

            result = translator_local.translate("中文", is_last_chunk=True)

            assert result == "Translated text"
            mock_translate.assert_called_once_with("中文", double_translation=None, is_last_chunk=True)

    def test_translate_method_error(self, translator_local):
        """Test translate method error handling"""
        with patch.object(translator_local, "translate_chunk") as mock_translate:
            mock_translate.side_effect = Exception("Translation error")

            result = translator_local.translate("中文")

            assert result is None
            translator_local.logger.error.assert_called()

    def test_get_cost_summary_remote(self, translator_remote):
        """Test cost summary for remote API"""
        # Mock the global cost tracker's summary
        with patch("enchant_book_manager.translation_service.global_cost_tracker.get_summary") as mock_get_summary:
            mock_get_summary.return_value = {
                "total_cost": 0.15,
                "total_tokens": 5000,
                "total_prompt_tokens": 3000,
                "total_completion_tokens": 2000,
                "request_count": 5,
                "average_cost_per_request": 0.03,
            }

            summary = translator_remote.get_cost_summary()

            assert summary["total_cost"] == 0.15
            assert summary["total_tokens"] == 5000
            assert summary["request_count"] == 5
            assert summary["average_cost_per_request"] == 0.03
            assert summary["api_type"] == "remote"
            assert summary["model"] == "deepseek/deepseek-r1:nitro"

    def test_get_cost_summary_local(self, translator_local):
        """Test cost summary for local API"""
        summary = translator_local.get_cost_summary()

        assert summary["total_cost"] == 0.0
        assert summary["message"] == "Local API - no costs incurred"
        assert summary["api_type"] == "local"
        assert summary["model"] == "qwen3-30b-a3b-mlx@8bit"

    def test_format_cost_summary_remote(self, translator_remote):
        """Test formatted cost summary for remote API"""
        # Mock the global cost tracker's summary
        with patch("enchant_book_manager.translation_service.global_cost_tracker.get_summary") as mock_get_summary:
            mock_get_summary.return_value = {
                "total_cost": 0.25,
                "total_tokens": 10000,
                "total_prompt_tokens": 6000,
                "total_completion_tokens": 4000,
                "request_count": 10,
                "average_cost_per_request": 0.025,
            }

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
        # Set initial request count
        translator_remote.request_count = 5

        # Mock the global cost tracker reset
        with patch("enchant_book_manager.translation_service.global_cost_tracker.reset") as mock_reset:
            # Reset
            translator_remote.reset_cost_tracking()

            # Verify reset was called
            mock_reset.assert_called_once()

            # Verify local counter reset
            assert translator_remote.request_count == 0

    def test_thread_safety_cost_tracking(self, translator_remote):
        """Test thread safety of cost tracking"""

        # Function to simulate concurrent request count updates
        def update_costs():
            for _ in range(100):
                with translator_remote._cost_lock:
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

        # Verify results - only request_count is tracked locally
        assert translator_remote.request_count == 1000


class TestUtilityFunctions:
    """Test utility functions"""

    def test_is_latin_char(self):
        """Test Latin character detection"""
        assert is_latin_char("A") is True
        assert is_latin_char("é") is True
        assert is_latin_char("ñ") is True
        assert is_latin_char("中") is False
        assert is_latin_char("あ") is False
        assert is_latin_char("🙂") is False

    def test_is_latin_charset(self):
        """Test Latin charset detection"""
        # Pure Latin text
        assert is_latin_charset("Hello World!") is True
        assert is_latin_charset("Café résumé naïve") is True

        # Mixed with some non-Latin
        assert is_latin_charset("Hello 世界") is False  # 2 Chinese chars out of 7 total = 28%
        assert is_latin_charset("99% English 中") is True  # 1 Chinese char out of ~11 = 9% < 10% threshold
        assert is_latin_charset("90% English 中文") is False  # 2 Chinese chars out of ~12 = 16% > 10%

        # Pure non-Latin
        assert is_latin_charset("你好世界") is False
        assert is_latin_charset("こんにちは") is False

        # Edge cases
        assert is_latin_charset("") is True  # Empty string
        assert is_latin_charset("   ") is True  # Only spaces
        assert is_latin_charset("123") is True  # Numbers

        # Test threshold
        text = "A" * 99 + "中"  # 1% non-Latin
        assert is_latin_charset(text, threshold=0.02) is True
        assert is_latin_charset(text, threshold=0.005) is False


# Note: TestRetryWrapper tests have been removed since retry_with_tenacity
# was replaced with the common retry_with_backoff decorator from common_utils.
# The retry logic is now tested via common_utils module tests.


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=translation_service", "--cov-report=html"])
