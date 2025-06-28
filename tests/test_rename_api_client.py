#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test suite for rename_api_client module.
"""

import pytest
import json
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import requests
from requests.exceptions import HTTPError, ConnectionError, Timeout

sys.path.insert(0, str(Path(__file__).parent.parent))

from enchant_book_manager.rename_api_client import (
    RenameAPIClient,
    OPENROUTER_MODEL_MAPPING,
)


class TestRenameAPIClient:
    """Test the RenameAPIClient class."""

    @classmethod
    def setup_class(cls):
        """Patch retry decorator for all tests."""
        cls.retry_patcher = patch("enchant_book_manager.common_utils.exponential_backoff_retry")
        mock_retry = cls.retry_patcher.start()

        # Make retry just call the function once with the correct args
        def mock_retry_func(
            func,
            max_attempts,
            base_wait,
            max_wait,
            min_wait,
            exception_types,
            logger,
            on_retry,
            time_limit,
            *args,
            **kwargs,
        ):
            # Just call the function with the original args and kwargs
            return func(*args, **kwargs)

        mock_retry.side_effect = mock_retry_func

    @classmethod
    def teardown_class(cls):
        """Stop retry patcher."""
        cls.retry_patcher.stop()

    def test_init_default_values(self):
        """Test initialization with default values."""
        client = RenameAPIClient(api_key="test_key")

        assert client.api_key == "test_key"
        assert client.model == "gpt-4o-mini"
        assert client.temperature == 0.0
        assert client.api_url == "https://openrouter.ai/api/v1/chat/completions"

    def test_init_custom_values(self):
        """Test initialization with custom values."""
        client = RenameAPIClient(api_key="custom_key", model="gpt-4", temperature=0.7)

        assert client.api_key == "custom_key"
        assert client.model == "gpt-4"
        assert client.temperature == 0.7

    def test_get_openrouter_model_mapped(self):
        """Test model name mapping for known models."""
        client = RenameAPIClient(api_key="test")

        # Test all mapped models
        for original, mapped in OPENROUTER_MODEL_MAPPING.items():
            client.model = original
            with patch("enchant_book_manager.rename_api_client.logger") as mock_logger:
                result = client.get_openrouter_model()
                assert result == mapped
                mock_logger.info.assert_called_once_with(f"Mapped model '{original}' to OpenRouter model '{mapped}'")

    def test_get_openrouter_model_unmapped(self):
        """Test model name for unmapped models."""
        client = RenameAPIClient(api_key="test")
        client.model = "claude-3-sonnet"

        with patch("enchant_book_manager.rename_api_client.logger") as mock_logger:
            result = client.get_openrouter_model()
            assert result == "claude-3-sonnet"
            mock_logger.info.assert_not_called()

    @patch("enchant_book_manager.rename_api_client.requests.post")
    def test_make_request_success(self, mock_post):
        """Test successful API request."""
        client = RenameAPIClient(api_key="test_key", model="gpt-4o-mini")

        # Mock response
        mock_response = Mock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "test response"}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5},
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        messages = [{"role": "user", "content": "test"}]
        result = client.make_request(messages)

        # Verify request
        mock_post.assert_called_once_with(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer test_key",
                "HTTP-Referer": "https://github.com/enchant-book-manager",
                "X-Title": "EnChANT Book Manager - Renaming Phase",
            },
            json={
                "model": "openai/gpt-4o-mini",
                "temperature": 0.0,
                "messages": messages,
                "usage": {"include": True},
            },
            timeout=10,
        )

        assert result == mock_response.json.return_value

    @patch("enchant_book_manager.rename_api_client.requests.post")
    def test_make_request_http_error(self, mock_post):
        """Test API request with HTTP error."""
        client = RenameAPIClient(api_key="test_key")

        # Mock HTTP error
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Invalid model specified"
        mock_response.raise_for_status.side_effect = HTTPError(response=mock_response)
        mock_post.return_value = mock_response

        with patch("enchant_book_manager.rename_api_client.logger") as mock_logger:
            with pytest.raises(HTTPError):
                client.make_request([{"role": "user", "content": "test"}])

            # Check error logging
            assert mock_logger.error.call_count >= 3

    @patch("enchant_book_manager.rename_api_client.requests.post")
    def test_make_request_connection_error(self, mock_post):
        """Test API request with connection error."""
        client = RenameAPIClient(api_key="test_key")
        mock_post.side_effect = ConnectionError("Network error")

        with pytest.raises(ConnectionError):
            client.make_request([{"role": "user", "content": "test"}])

    @patch("enchant_book_manager.rename_api_client.requests.post")
    def test_make_request_timeout(self, mock_post):
        """Test API request with timeout."""
        client = RenameAPIClient(api_key="test_key")
        mock_post.side_effect = Timeout("Request timed out")

        with pytest.raises(Timeout):
            client.make_request([{"role": "user", "content": "test"}])

    @patch("enchant_book_manager.rename_api_client.requests.post")
    @patch("enchant_book_manager.rename_api_client.sys.exit")
    def test_make_request_keyboard_interrupt(self, mock_exit, mock_post):
        """Test API request with keyboard interrupt."""
        client = RenameAPIClient(api_key="test_key")
        mock_post.side_effect = KeyboardInterrupt()

        with patch("enchant_book_manager.rename_api_client.logger") as mock_logger:
            # The method catches KeyboardInterrupt and calls sys.exit, so it doesn't raise
            client.make_request([{"role": "user", "content": "test"}])

            mock_logger.error.assert_called_with("Request interrupted by user (Ctrl+C). Exiting gracefully.")
            mock_exit.assert_called_once_with(1)

    @patch("enchant_book_manager.rename_api_client.requests.post")
    def test_make_request_generic_exception(self, mock_post):
        """Test API request with generic exception."""
        client = RenameAPIClient(api_key="test_key")
        mock_post.side_effect = Exception("Unexpected error")

        with patch("enchant_book_manager.rename_api_client.logger") as mock_logger:
            with pytest.raises(Exception):
                client.make_request([{"role": "user", "content": "test"}])

            mock_logger.error.assert_called_with("Error making OpenRouter request: Unexpected error")

    @patch.object(RenameAPIClient, "make_request")
    @patch("enchant_book_manager.rename_api_client.global_cost_tracker")
    def test_extract_metadata_success(self, mock_cost_tracker, mock_make_request):
        """Test successful metadata extraction."""
        client = RenameAPIClient(api_key="test_key")

        # Mock response
        mock_response = {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "detected_language": "Chinese",
                                "novel_title_original": "测试小说",
                                "author_name_original": "测试作者",
                                "novel_title_english": "Test Novel",
                                "author_name_english": "Test Author",
                                "author_name_romanized": "Ceshi Zuozhe",
                            }
                        )
                    }
                }
            ],
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "total_tokens": 150,
            },
        }
        mock_make_request.return_value = mock_response

        content = "这是一本测试小说的内容..."
        result = client.extract_metadata(content, char_limit=100)

        # Verify prompt construction
        call_args = mock_make_request.call_args[0][0]
        assert len(call_args) == 1
        assert call_args[0]["role"] == "user"
        assert "Given the following content from a novel" in call_args[0]["content"]
        assert content[:100] in call_args[0]["content"]
        assert "JSON format" in call_args[0]["content"]

        # Verify response
        assert result == mock_response["choices"][0]["message"]["content"]

        # Verify cost tracking
        mock_cost_tracker.track_usage.assert_called_once_with(mock_response["usage"])

    @patch.object(RenameAPIClient, "make_request")
    def test_extract_metadata_no_choices(self, mock_make_request):
        """Test metadata extraction with no choices in response."""
        client = RenameAPIClient(api_key="test_key")

        # Mock response without choices
        mock_make_request.return_value = {"usage": {}}

        with patch("enchant_book_manager.rename_api_client.logger") as mock_logger:
            result = client.extract_metadata("test content")
            assert result is None
            mock_logger.error.assert_called_once()
            assert "No choices found" in mock_logger.error.call_args[0][0]

    @patch.object(RenameAPIClient, "make_request")
    def test_extract_metadata_invalid_choices(self, mock_make_request):
        """Test metadata extraction with invalid choices format."""
        client = RenameAPIClient(api_key="test_key")

        # Mock response with invalid choices
        mock_make_request.return_value = {"choices": "not a list"}

        with patch("enchant_book_manager.rename_api_client.logger") as mock_logger:
            result = client.extract_metadata("test content")
            assert result is None
            mock_logger.error.assert_called_once()
            assert "No choices found" in mock_logger.error.call_args[0][0]

    @patch.object(RenameAPIClient, "make_request")
    def test_extract_metadata_no_message(self, mock_make_request):
        """Test metadata extraction with no message in choice."""
        client = RenameAPIClient(api_key="test_key")

        # Mock response without message
        mock_make_request.return_value = {"choices": [{"role": "assistant"}]}

        with patch("enchant_book_manager.rename_api_client.logger") as mock_logger:
            result = client.extract_metadata("test content")
            assert result is None
            mock_logger.error.assert_called_once()
            assert "Message content missing" in mock_logger.error.call_args[0][0]

    @patch.object(RenameAPIClient, "make_request")
    def test_extract_metadata_no_content(self, mock_make_request):
        """Test metadata extraction with no content in message."""
        client = RenameAPIClient(api_key="test_key")

        # Mock response without content
        mock_make_request.return_value = {"choices": [{"message": {"role": "assistant"}}]}

        with patch("enchant_book_manager.rename_api_client.logger") as mock_logger:
            result = client.extract_metadata("test content")
            assert result is None
            mock_logger.error.assert_called_once()
            assert "Message content missing" in mock_logger.error.call_args[0][0]

    @patch.object(RenameAPIClient, "make_request")
    def test_extract_metadata_non_string_content(self, mock_make_request):
        """Test metadata extraction with non-string content."""
        client = RenameAPIClient(api_key="test_key")

        # Mock response with non-string content
        mock_make_request.return_value = {"choices": [{"message": {"content": {"json": "data"}}}]}

        with patch("enchant_book_manager.rename_api_client.logger") as mock_logger:
            result = client.extract_metadata("test content")
            assert result is None
            mock_logger.error.assert_called_once()
            assert "Expected string response content" in mock_logger.error.call_args[0][0]

    @patch.object(RenameAPIClient, "make_request")
    def test_extract_metadata_char_limit(self, mock_make_request):
        """Test that char_limit is respected."""
        client = RenameAPIClient(api_key="test_key")

        # Mock response
        mock_make_request.return_value = {
            "choices": [{"message": {"content": "response"}}],
            "usage": {},
        }

        # Long content
        content = "x" * 2000
        client.extract_metadata(content, char_limit=100)

        # Check that only first 100 chars were sent
        call_args = mock_make_request.call_args[0][0]
        prompt_content = call_args[0]["content"]
        assert "x" * 100 in prompt_content
        assert "x" * 101 not in prompt_content

    @patch.object(RenameAPIClient, "make_request")
    @patch("enchant_book_manager.rename_api_client.global_cost_tracker")
    def test_extract_metadata_no_usage_info(self, mock_cost_tracker, mock_make_request):
        """Test metadata extraction when no usage info is provided."""
        client = RenameAPIClient(api_key="test_key")

        # Mock response without usage
        mock_make_request.return_value = {"choices": [{"message": {"content": "response"}}]}

        result = client.extract_metadata("test")
        assert result == "response"

        # Should still call track_usage with empty dict
        mock_cost_tracker.track_usage.assert_called_once_with({})

    def test_model_mapping_completeness(self):
        """Test that all common OpenAI models are mapped."""
        expected_models = [
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-4-turbo",
            "gpt-4",
            "gpt-3.5-turbo",
            "gpt-3.5-turbo-16k",
        ]

        for model in expected_models:
            assert model in OPENROUTER_MODEL_MAPPING
            assert OPENROUTER_MODEL_MAPPING[model].startswith("openai/")

    @patch.object(RenameAPIClient, "make_request")
    def test_extract_metadata_prompt_format(self, mock_make_request):
        """Test the exact format of the extraction prompt."""
        client = RenameAPIClient(api_key="test_key")

        # Mock response
        mock_make_request.return_value = {
            "choices": [{"message": {"content": "response"}}],
            "usage": {},
        }

        content = "Test novel content"
        client.extract_metadata(content)

        # Get the prompt
        call_args = mock_make_request.call_args[0][0]
        prompt = call_args[0]["content"]

        # Check all required elements are in prompt
        assert "Detect the language(s) of the text" in prompt
        assert "Find the title of the novel and the author's name" in prompt
        assert "Return the title of the novel and author in the original language" in prompt
        assert "JSON format" in prompt
        assert '"detected_language"' in prompt
        assert '"novel_title_original"' in prompt
        assert '"author_name_original"' in prompt
        assert '"novel_title_english"' in prompt
        assert '"author_name_english"' in prompt
        assert '"author_name_romanized"' in prompt
