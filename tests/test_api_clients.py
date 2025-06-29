#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test suite for api_clients module.
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
import requests
from requests.exceptions import HTTPError, ConnectionError, Timeout

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from enchant_book_manager.api_clients import (
    TranslationAPIClient,
    LocalAPIClient,
    RemoteAPIClient,
    create_api_client,
)
from enchant_book_manager.translation_constants import (
    CONNECTION_TIMEOUT,
    RESPONSE_TIMEOUT,
    DEFAULT_MAX_TOKENS,
    API_URL_LMSTUDIO,
    API_URL_OPENROUTER,
)


class TestTranslationAPIClient:
    """Test the base TranslationAPIClient class."""

    def test_init(self):
        """Test initialization of TranslationAPIClient."""
        client = TranslationAPIClient(api_url="http://test.com", model_name="test-model", timeout=(10, 20), logger=print)
        assert client.api_url == "http://test.com"
        assert client.model_name == "test-model"
        assert client.timeout == (10, 20)
        assert client.logger == print

    def test_init_defaults(self):
        """Test initialization with defaults."""
        client = TranslationAPIClient(api_url="http://test.com", model_name="test-model")
        assert client.timeout == (CONNECTION_TIMEOUT, RESPONSE_TIMEOUT)
        # Logger is now a noop function if not provided
        assert callable(client.logger)

    @patch("enchant_book_manager.api_clients.requests.post")
    def test_make_request_success(self, mock_post):
        """Test successful API request."""
        mock_response = Mock()
        mock_response.json.return_value = {"choices": [{"message": {"content": "translated"}}]}
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        # Create a concrete subclass for testing
        class TestClient(TranslationAPIClient):
            def prepare_request(self, messages, **kwargs):
                return {"messages": messages, **kwargs}

            def parse_response(self, response_data):
                choices = response_data.get("choices", [])
                if choices:
                    return choices[0]["message"]["content"], {}
                return None, {}

        client = TestClient("http://test.com", "test-model")
        result = client.make_request(messages=[{"role": "user", "content": "test"}], temperature=0.5, max_tokens=100)

        assert result == "translated"
        mock_post.assert_called_once()

    @patch("enchant_book_manager.api_clients.requests.post")
    def test_make_request_http_error(self, mock_post):
        """Test API request with HTTP error."""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = HTTPError("404 Not Found")
        mock_post.return_value = mock_response

        # Create a concrete subclass for testing
        class TestClient(TranslationAPIClient):
            def prepare_request(self, messages, **kwargs):
                return {"messages": messages, **kwargs}

            def parse_response(self, response_data):
                return None, {}

        client = TestClient("http://test.com", "test-model")
        result = client.make_request([{"role": "user", "content": "test"}])
        assert result is None

    @patch("enchant_book_manager.api_clients.requests.post")
    def test_make_request_connection_error(self, mock_post):
        """Test API request with connection error."""
        mock_post.side_effect = ConnectionError("Connection failed")

        # Create a concrete subclass for testing
        class TestClient(TranslationAPIClient):
            def prepare_request(self, messages, **kwargs):
                return {"messages": messages, **kwargs}

            def parse_response(self, response_data):
                return None, {}

        client = TestClient("http://test.com", "test-model")
        result = client.make_request([{"role": "user", "content": "test"}])
        assert result is None

    @patch("enchant_book_manager.api_clients.requests.post")
    def test_make_request_timeout(self, mock_post):
        """Test API request with timeout."""
        mock_post.side_effect = Timeout("Request timed out")

        # Create a concrete subclass for testing
        class TestClient(TranslationAPIClient):
            def prepare_request(self, messages, **kwargs):
                return {"messages": messages, **kwargs}

            def parse_response(self, response_data):
                return None, {}

        client = TestClient("http://test.com", "test-model")
        result = client.make_request([{"role": "user", "content": "test"}])
        assert result is None

    def test_parse_response_valid(self):
        """Test parsing valid response - tests must be implemented in subclasses."""
        # This test verifies that parse_response is abstract
        client = TranslationAPIClient("http://test.com", "test-model")
        with pytest.raises(NotImplementedError):
            client.parse_response({})

    def test_prepare_request_abstract(self):
        """Test that prepare_request is abstract."""
        client = TranslationAPIClient("http://test.com", "test-model")
        with pytest.raises(NotImplementedError):
            client.prepare_request([])


class TestLocalAPIClient:
    """Test the LocalAPIClient class."""

    def test_init(self):
        """Test initialization of LocalAPIClient."""
        client = LocalAPIClient(model_name="test-model", logger=print)
        assert client.api_url == API_URL_LMSTUDIO
        assert client.model_name == "test-model"
        assert client.logger == print
        # Timeout is set by parent class
        assert client.timeout == (CONNECTION_TIMEOUT, RESPONSE_TIMEOUT)

    def test_init_defaults(self):
        """Test initialization with defaults."""
        client = LocalAPIClient(model_name="test-model")
        assert client.api_url == API_URL_LMSTUDIO
        assert callable(client.logger)

    def test_prepare_request(self):
        """Test request data preparation for local API."""
        client = LocalAPIClient("test-model")
        messages = [{"role": "system", "content": "You are a translator"}, {"role": "user", "content": "test"}]

        data = client.prepare_request(messages, temperature=0.5, max_tokens=100)

        assert data["model"] == "test-model"
        assert "prompt" in data
        assert "You are a translator" in data["prompt"]
        assert "test" in data["prompt"]
        assert data["temperature"] == 0.5
        assert data["max_tokens"] == 100
        assert data["stream"] is False

    def test_parse_response(self):
        """Test response parsing for local API."""
        client = LocalAPIClient("test-model")

        # Test successful response
        response = {"choices": [{"text": "  translated text  "}], "usage": {"total_tokens": 100}}

        text, usage = client.parse_response(response)
        assert text == "translated text"
        assert usage == {"total_tokens": 100}

        # Test response without choices
        with pytest.raises(KeyError):
            client.parse_response({})


class TestRemoteAPIClient:
    """Test the RemoteAPIClient class."""

    def test_init_with_api_key(self):
        """Test initialization with API key."""
        client = RemoteAPIClient(api_key="test-key", model_name="test-model", logger=print)
        assert client.api_url == API_URL_OPENROUTER
        assert client.model_name == "test-model"
        assert client.logger == print
        assert client.headers["Authorization"] == "Bearer test-key"
        assert client.headers["HTTP-Referer"] == "https://github.com/enchant-novels"
        assert client.headers["X-Title"] == "EnChANT Book Manager"
        # Timeout is set by parent class
        assert client.timeout == (CONNECTION_TIMEOUT, RESPONSE_TIMEOUT)

    def test_init_defaults(self):
        """Test initialization with defaults."""
        client = RemoteAPIClient(api_key="test-key", model_name="test-model")
        assert callable(client.logger)

    def test_prepare_request(self):
        """Test request data preparation for remote API."""
        client = RemoteAPIClient(api_key="test-key", model_name="test-model")
        messages = [{"role": "user", "content": "test"}]

        data = client.prepare_request(messages, temperature=0.5, max_tokens=100, top_p=0.9, frequency_penalty=0.1, presence_penalty=0.2, repetition_penalty=1.5)

        assert data["model"] == "test-model"
        assert data["messages"] == messages
        assert data["temperature"] == 0.5
        assert data["max_tokens"] == 100
        assert data["top_p"] == 0.9
        assert data["frequency_penalty"] == 0.1
        assert data["presence_penalty"] == 0.2
        assert data["repetition_penalty"] == 1.5

    @patch("enchant_book_manager.api_clients.requests.post")
    def test_make_request_with_headers(self, mock_post):
        """Test that remote API includes auth headers."""
        mock_response = Mock()
        mock_response.json.return_value = {"choices": [{"message": {"content": "test"}}], "usage": {}}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        client = RemoteAPIClient(api_key="test-key", model_name="test-model")
        result = client.make_request([{"role": "user", "content": "test"}])

        # Check that headers were passed
        call_args = mock_post.call_args
        assert call_args[1]["headers"]["Authorization"] == "Bearer test-key"
        assert result == "test"

    def test_parse_response(self):
        """Test response parsing for remote API."""
        client = RemoteAPIClient(api_key="test-key", model_name="test-model")

        # Test successful response
        response = {"choices": [{"message": {"content": "  translated  "}}], "usage": {"total_tokens": 100, "prompt_tokens": 50, "completion_tokens": 50}}

        text, usage = client.parse_response(response)
        assert text == "translated"
        assert usage == {"total_tokens": 100, "prompt_tokens": 50, "completion_tokens": 50}

        # Test error response
        error_response = {"error": {"code": "rate_limit", "message": "Rate limit exceeded"}}
        with pytest.raises(ValueError, match="API error \\(rate_limit\\): Rate limit exceeded"):
            client.parse_response(error_response)

        # Test response without choices
        with pytest.raises(KeyError):
            client.parse_response({})

    def test_track_usage(self):
        """Test that remote API tracks costs."""
        with patch("enchant_book_manager.api_clients.global_cost_tracker.track_usage") as mock_track:
            client = RemoteAPIClient(api_key="test-key", model_name="test-model")
            usage_info = {"total_tokens": 100, "prompt_tokens": 50, "completion_tokens": 50}

            client._track_usage(usage_info)

            mock_track.assert_called_once_with(usage_info)


class TestCreateAPIClient:
    """Test the create_api_client factory function."""

    def test_create_local_client(self):
        """Test creating a local API client."""
        client = create_api_client(use_remote=False, model_name="local-model", api_key=None, logger=print)
        assert isinstance(client, LocalAPIClient)
        assert client.model_name == "local-model"
        assert client.logger == print

    def test_create_local_client_default_model(self):
        """Test creating a local API client with default model."""
        client = create_api_client(use_remote=False)
        assert isinstance(client, LocalAPIClient)
        # Default model should be set from constants
        assert client.model_name is not None

    def test_create_remote_client(self):
        """Test creating a remote API client."""
        client = create_api_client(use_remote=True, model_name="remote-model", api_key="test-key", logger=None)
        assert isinstance(client, RemoteAPIClient)
        assert client.model_name == "remote-model"

    def test_create_remote_client_default_model(self):
        """Test creating a remote API client with default model."""
        client = create_api_client(use_remote=True, api_key="test-key")
        assert isinstance(client, RemoteAPIClient)
        # Default model should be set from constants
        assert client.model_name is not None

    def test_create_remote_without_key(self):
        """Test creating remote client without API key."""
        with pytest.raises(ValueError, match="API key required for remote service"):
            create_api_client(use_remote=True, model_name="remote-model", api_key=None)
