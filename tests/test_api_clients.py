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

        client = TranslationAPIClient("http://test.com", "test-model")
        result = client.make_request(messages=[{"role": "user", "content": "test"}], temperature=0.5, max_tokens=100, top_p=0.9, frequency_penalty=0.1, presence_penalty=0.2, repetition_penalty=1.0)

        assert result == {"choices": [{"message": {"content": "translated"}}]}
        mock_post.assert_called_once()

    @patch("enchant_book_manager.api_clients.requests.post")
    def test_make_request_http_error(self, mock_post):
        """Test API request with HTTP error."""
        mock_post.side_effect = HTTPError("404 Not Found")

        client = TranslationAPIClient("http://test.com", "test-model")
        with pytest.raises(HTTPError):
            client.make_request([{"role": "user", "content": "test"}])

    @patch("enchant_book_manager.api_clients.requests.post")
    def test_make_request_connection_error(self, mock_post):
        """Test API request with connection error."""
        mock_post.side_effect = ConnectionError("Connection failed")

        client = TranslationAPIClient("http://test.com", "test-model")
        with pytest.raises(ConnectionError):
            client.make_request([{"role": "user", "content": "test"}])

    @patch("enchant_book_manager.api_clients.requests.post")
    def test_make_request_timeout(self, mock_post):
        """Test API request with timeout."""
        mock_post.side_effect = Timeout("Request timed out")

        client = TranslationAPIClient("http://test.com", "test-model")
        with pytest.raises(Timeout):
            client.make_request([{"role": "user", "content": "test"}])

    def test_parse_response_valid(self):
        """Test parsing valid response."""
        client = TranslationAPIClient("http://test.com", "test-model")
        response = {"choices": [{"message": {"content": "translated text"}}], "usage": {"total_tokens": 100, "prompt_tokens": 50, "completion_tokens": 50}}

        content, usage = client.parse_response(response)
        assert content == "translated text"
        assert usage == {"total_tokens": 100, "prompt_tokens": 50, "completion_tokens": 50}

    def test_parse_response_no_choices(self):
        """Test parsing response without choices."""
        client = TranslationAPIClient("http://test.com", "test-model")
        response = {"error": "Invalid request"}

        content, usage = client.parse_response(response)
        assert content is None
        assert usage is None

    def test_parse_response_empty_content(self):
        """Test parsing response with empty content."""
        client = TranslationAPIClient("http://test.com", "test-model")
        response = {"choices": [{"message": {"content": ""}}]}

        content, usage = client.parse_response(response)
        assert content == ""
        assert usage is None


class TestLocalAPIClient:
    """Test the LocalAPIClient class."""

    def test_init(self):
        """Test initialization of LocalAPIClient."""
        client = LocalAPIClient(model_name="test-model", timeout=(10, 20), logger=print)
        assert client.api_url == API_URL_LMSTUDIO
        assert client.model_name == "test-model"
        assert client.timeout == (10, 20)

    def test_init_custom_endpoint(self):
        """Test initialization with custom endpoint."""
        client = LocalAPIClient(model_name="test-model", endpoint="http://custom.local:8080/v1/chat/completions")
        assert client.api_url == "http://custom.local:8080/v1/chat/completions"

    def test_prepare_request_data(self):
        """Test request data preparation for local API."""
        client = LocalAPIClient("test-model")
        messages = [{"role": "user", "content": "test"}]

        data = client.prepare_request_data(messages=messages, temperature=0.5, max_tokens=100, top_p=0.9, frequency_penalty=0.1, presence_penalty=0.2, repetition_penalty=1.5)

        assert data["model"] == "test-model"
        assert data["messages"] == messages
        assert data["temperature"] == 0.5
        assert data["max_tokens"] == 100
        assert data["top_p"] == 0.9
        assert data["frequency_penalty"] == 0.1
        assert data["presence_penalty"] == 0.2
        assert data["repetition_penalty"] == 1.5


class TestRemoteAPIClient:
    """Test the RemoteAPIClient class."""

    def test_init_no_api_key(self):
        """Test initialization without API key."""
        with pytest.raises(ValueError, match="API key required for remote service"):
            RemoteAPIClient(model_name="test-model")

    def test_init_with_api_key(self):
        """Test initialization with API key."""
        client = RemoteAPIClient(model_name="test-model", api_key="test-key", timeout=(10, 20))
        assert client.api_url == API_URL_OPENROUTER
        assert client.api_key == "test-key"
        assert client.headers["Authorization"] == "Bearer test-key"

    def test_init_custom_endpoint(self):
        """Test initialization with custom endpoint."""
        client = RemoteAPIClient(model_name="test-model", api_key="test-key", endpoint="http://custom.api/v1/chat")
        assert client.api_url == "http://custom.api/v1/chat"

    def test_prepare_request_data(self):
        """Test request data preparation for remote API."""
        client = RemoteAPIClient("test-model", api_key="test-key")
        messages = [{"role": "user", "content": "test"}]

        data = client.prepare_request_data(messages=messages, temperature=0.5, max_tokens=100, top_p=0.9, frequency_penalty=0.1, presence_penalty=0.2, repetition_penalty=1.5)

        assert data["model"] == "test-model"
        assert data["messages"] == messages
        assert data["temperature"] == 0.5
        assert data["max_tokens"] == 100
        assert data["top_p"] == 0.9
        assert data["frequency_penalty"] == 0.1
        assert data["presence_penalty"] == 0.2
        # repetition_penalty not supported for remote API
        assert "repetition_penalty" not in data

    @patch("enchant_book_manager.api_clients.requests.post")
    def test_make_request_with_headers(self, mock_post):
        """Test that remote API includes auth headers."""
        mock_response = Mock()
        mock_response.json.return_value = {"choices": [{"message": {"content": "test"}}]}
        mock_post.return_value = mock_response

        client = RemoteAPIClient("test-model", api_key="test-key")
        client.make_request([{"role": "user", "content": "test"}])

        # Check that headers were passed
        call_args = mock_post.call_args
        assert call_args[1]["headers"]["Authorization"] == "Bearer test-key"

    def test_parse_response_with_cost_tracking(self):
        """Test that remote API tracks costs."""
        with patch("enchant_book_manager.api_clients.global_cost_tracker.track_request") as mock_track:
            client = RemoteAPIClient("test-model", api_key="test-key")
            response = {"choices": [{"message": {"content": "translated"}}], "usage": {"total_tokens": 100, "prompt_tokens": 50, "completion_tokens": 50}}

            content, usage = client.parse_response(response)

            assert content == "translated"
            mock_track.assert_called_once_with(model="test-model", usage={"total_tokens": 100, "prompt_tokens": 50, "completion_tokens": 50}, cost=None)


class TestCreateAPIClient:
    """Test the create_api_client factory function."""

    def test_create_local_client(self):
        """Test creating a local API client."""
        client = create_api_client(use_remote=False, model="local-model", api_key=None, endpoint=None, timeout=30, logger=print)
        assert isinstance(client, LocalAPIClient)
        assert client.model_name == "local-model"

    def test_create_remote_client(self):
        """Test creating a remote API client."""
        client = create_api_client(use_remote=True, model="remote-model", api_key="test-key", endpoint=None, timeout=60, logger=None)
        assert isinstance(client, RemoteAPIClient)
        assert client.model_name == "remote-model"
        assert client.api_key == "test-key"

    def test_create_remote_without_key(self):
        """Test creating remote client without API key."""
        with pytest.raises(ValueError, match="API key required for remote service"):
            create_api_client(use_remote=True, model="remote-model", api_key=None)

    def test_create_with_custom_endpoint(self):
        """Test creating client with custom endpoint."""
        client = create_api_client(use_remote=False, model="test-model", endpoint="http://custom:8080/v1/chat")
        assert client.api_url == "http://custom:8080/v1/chat"
