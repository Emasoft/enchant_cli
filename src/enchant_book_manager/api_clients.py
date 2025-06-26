#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
# - Initial creation from translation_service.py refactoring
# - Extracted API client implementations for local and remote services
# - Contains request handling, response parsing, and error management
#

"""
api_clients.py - API client implementations for translation services
===================================================================

Provides API client classes for communicating with local (LM Studio)
and remote (OpenRouter) translation services.
"""

from __future__ import annotations

import json
from typing import Any, Optional, Callable
import requests

from .cost_tracker import global_cost_tracker
from .translation_constants import (
    CONNECTION_TIMEOUT,
    RESPONSE_TIMEOUT,
    DEFAULT_MAX_TOKENS,
    API_URL_LMSTUDIO,
    API_URL_OPENROUTER,
)


class TranslationAPIClient:
    """Base class for translation API clients.

    Provides common functionality for API communication,
    error handling, and response processing.
    """

    def __init__(
        self,
        api_url: str,
        model_name: str,
        timeout: tuple[int, int] = (CONNECTION_TIMEOUT, RESPONSE_TIMEOUT),
        logger: Optional[Callable[[str, str], None]] = None,
    ):
        """Initialize API client.

        Args:
            api_url: Base URL for the API endpoint
            model_name: Name of the model to use
            timeout: Tuple of (connection_timeout, response_timeout)
            logger: Optional logger function
        """
        self.api_url = api_url
        self.model_name = model_name
        self.timeout = timeout

        # Default logger that does nothing
        def noop_logger(msg: str, level: str = "info") -> None:
            pass

        self.logger: Callable[[str, str], None] = logger or noop_logger
        self.headers = {"Content-Type": "application/json"}

    def _log(self, message: str, level: str = "info") -> None:
        """Log a message using the configured logger."""
        self.logger(message, level)

    def prepare_request(self, messages: list[dict[str, Any]], **kwargs: Any) -> dict[str, Any]:
        """Prepare the request payload.

        Args:
            messages: List of message dictionaries
            **kwargs: Additional parameters

        Returns:
            Request payload dictionary
        """
        raise NotImplementedError("Subclass must implement prepare_request")

    def parse_response(self, response_data: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        """Parse the API response.

        Args:
            response_data: Raw response data from API

        Returns:
            Tuple of (translated_text, usage_info)
        """
        raise NotImplementedError("Subclass must implement parse_response")

    def make_request(self, messages: list[dict[str, Any]], **kwargs: Any) -> Optional[str]:
        """Make a translation request to the API.

        Args:
            messages: List of message dictionaries
            **kwargs: Additional parameters

        Returns:
            Translated text or None if failed
        """
        payload = self.prepare_request(messages, **kwargs)

        try:
            self._log(f"Sending request to {self.api_url}")
            response = requests.post(
                self.api_url,
                headers=self.headers,
                data=json.dumps(payload),
                timeout=self.timeout,
            )

            response.raise_for_status()
            response_data = response.json()

            translated_text, usage_info = self.parse_response(response_data)

            # Track usage if available
            if usage_info:
                self._track_usage(usage_info)

            return translated_text

        except requests.exceptions.Timeout:
            self._log("Request timed out", "error")
            return None
        except requests.exceptions.RequestException as e:
            self._log(f"Request failed: {e}", "error")
            return None
        except (KeyError, json.JSONDecodeError) as e:
            self._log(f"Failed to parse response: {e}", "error")
            return None

    def _track_usage(self, usage_info: dict[str, Any]) -> None:
        """Track API usage for cost calculation.

        Args:
            usage_info: Dictionary containing usage information
        """
        # Default implementation does nothing
        pass


class LocalAPIClient(TranslationAPIClient):
    """API client for local LM Studio server."""

    def __init__(self, model_name: str, logger: Optional[Callable[[str, str], None]] = None):
        """Initialize local API client.

        Args:
            model_name: Name of the model to use
            logger: Optional logger function
        """
        super().__init__(api_url=API_URL_LMSTUDIO, model_name=model_name, logger=logger)

    def prepare_request(self, messages: list[dict[str, Any]], **kwargs: Any) -> dict[str, Any]:
        """Prepare request for LM Studio API.

        Args:
            messages: List of message dictionaries
            **kwargs: Additional parameters (temperature, max_tokens)

        Returns:
            Request payload for LM Studio
        """
        # For LM Studio, we need to format as a single prompt
        prompt = ""
        for msg in messages:
            if msg["role"] == "system":
                prompt += msg["content"] + "\n\n"
            elif msg["role"] == "user":
                prompt += msg["content"]

        return {
            "model": self.model_name,
            "prompt": prompt,
            "max_tokens": kwargs.get("max_tokens", DEFAULT_MAX_TOKENS),
            "temperature": kwargs.get("temperature", 0.1),
            "stream": False,
        }

    def parse_response(self, response_data: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        """Parse LM Studio API response.

        Args:
            response_data: Raw response from LM Studio

        Returns:
            Tuple of (translated_text, usage_info)
        """
        choices = response_data.get("choices", [])
        if not choices:
            raise KeyError("No choices in response")

        translated_text = choices[0].get("text", "").strip()

        # LM Studio may not provide usage info
        usage_info = response_data.get("usage", {})

        return translated_text, usage_info


class RemoteAPIClient(TranslationAPIClient):
    """API client for remote OpenRouter service."""

    def __init__(
        self,
        api_key: str,
        model_name: str,
        logger: Optional[Callable[[str, str], None]] = None,
    ):
        """Initialize remote API client.

        Args:
            api_key: API key for authentication
            model_name: Name of the model to use
            logger: Optional logger function
        """
        super().__init__(api_url=API_URL_OPENROUTER, model_name=model_name, logger=logger)
        self.headers["Authorization"] = f"Bearer {api_key}"
        self.headers["HTTP-Referer"] = "https://github.com/enchant-novels"
        self.headers["X-Title"] = "EnChANT Book Manager"

    def prepare_request(self, messages: list[dict[str, Any]], **kwargs: Any) -> dict[str, Any]:
        """Prepare request for OpenRouter API.

        Args:
            messages: List of message dictionaries
            **kwargs: Additional parameters

        Returns:
            Request payload for OpenRouter
        """
        return {
            "model": self.model_name,
            "messages": messages,
            "max_tokens": kwargs.get("max_tokens", DEFAULT_MAX_TOKENS),
            "temperature": kwargs.get("temperature", 0.1),
            "top_p": kwargs.get("top_p", 0.01),
            "frequency_penalty": kwargs.get("frequency_penalty", 0.3),
            "presence_penalty": kwargs.get("presence_penalty", 0.0),
            "repetition_penalty": kwargs.get("repetition_penalty", 1.0),
        }

    def parse_response(self, response_data: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        """Parse OpenRouter API response.

        Args:
            response_data: Raw response from OpenRouter

        Returns:
            Tuple of (translated_text, usage_info)
        """
        # Check for error response
        if "error" in response_data:
            error = response_data["error"]
            error_msg = error.get("message", "Unknown error")
            error_code = error.get("code", "unknown")
            raise ValueError(f"API error ({error_code}): {error_msg}")

        choices = response_data.get("choices", [])
        if not choices:
            raise KeyError("No choices in response")

        message = choices[0].get("message", {})
        translated_text = message.get("content", "").strip()

        # Get usage information for cost tracking
        usage_info = response_data.get("usage", {})

        return translated_text, usage_info

    def _track_usage(self, usage_info: dict[str, Any]) -> None:
        """Track API usage for cost calculation.

        Args:
            usage_info: Dictionary containing token usage
        """
        if usage_info:
            prompt_tokens = usage_info.get("prompt_tokens", 0)
            completion_tokens = usage_info.get("completion_tokens", 0)
            total_tokens = usage_info.get("total_tokens", 0)

            # Track usage in global cost tracker
            global_cost_tracker.track_usage(usage_info)


def create_api_client(
    use_remote: bool,
    api_key: Optional[str] = None,
    model_name: Optional[str] = None,
    logger: Optional[Callable[[str, str], None]] = None,
) -> TranslationAPIClient:
    """Factory function to create appropriate API client.

    Args:
        use_remote: Whether to use remote API
        api_key: API key for remote service
        model_name: Model name to use
        logger: Optional logger function

    Returns:
        Configured API client instance

    Raises:
        ValueError: If remote API requested but no API key provided
    """
    if use_remote:
        if not api_key:
            raise ValueError("API key required for remote service")
        from .translation_constants import MODEL_NAME_DEEPSEEK

        return RemoteAPIClient(api_key=api_key, model_name=model_name or MODEL_NAME_DEEPSEEK, logger=logger)
    else:
        from .translation_constants import MODEL_NAME_QWEN

        return LocalAPIClient(model_name=model_name or MODEL_NAME_QWEN, logger=logger)
