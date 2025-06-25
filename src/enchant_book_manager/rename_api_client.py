#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
# - Initial creation from renamenovels.py refactoring
# - Extracted OpenRouter API client functionality
# - Contains model mapping and API request logic
#

"""
rename_api_client.py - OpenRouter API client for novel metadata extraction
========================================================================

Handles API communication with OpenRouter for extracting novel metadata
from text content using various AI models.
"""

from __future__ import annotations

import requests
import logging
import sys
from typing import Any, cast
from requests.exceptions import HTTPError, ConnectionError, Timeout

from .common_utils import retry_with_backoff
from .common_constants import DEFAULT_OPENROUTER_API_URL
from .cost_tracker import global_cost_tracker

logger = logging.getLogger(__name__)

# Model name mapping for OpenRouter
OPENROUTER_MODEL_MAPPING = {
    "gpt-4o": "openai/gpt-4o",
    "gpt-4o-mini": "openai/gpt-4o-mini",
    "gpt-4-turbo": "openai/gpt-4-turbo",
    "gpt-4": "openai/gpt-4",
    "gpt-3.5-turbo": "openai/gpt-3.5-turbo",
    "gpt-3.5-turbo-16k": "openai/gpt-3.5-turbo-16k",
}


class RenameAPIClient:
    """Client for interacting with OpenRouter API for novel metadata extraction."""

    def __init__(self, api_key: str, model: str = "gpt-4o-mini", temperature: float = 0.0):
        """
        Initialize the API client.

        Args:
            api_key: OpenRouter API key
            model: Model name to use (default: gpt-4o-mini)
            temperature: Temperature setting for the model (default: 0.0)
        """
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.api_url = DEFAULT_OPENROUTER_API_URL

    def get_openrouter_model(self) -> str:
        """
        Get the OpenRouter-formatted model name.

        Returns:
            OpenRouter-compatible model name
        """
        openrouter_model = OPENROUTER_MODEL_MAPPING.get(self.model, self.model)
        if openrouter_model != self.model:
            logger.info(f"Mapped model '{self.model}' to OpenRouter model '{openrouter_model}'")
        return openrouter_model

    @retry_with_backoff(
        max_attempts=5,
        base_wait=4.0,
        max_wait=10.0,
        min_wait=4.0,
        exception_types=(HTTPError, ConnectionError, Timeout),
    )
    def make_request(self, messages: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Make request to OpenRouter API with retry logic.

        Args:
            messages: List of message dictionaries for the chat

        Returns:
            API response dictionary

        Raises:
            HTTPError: If API request fails
            KeyboardInterrupt: If interrupted by user
        """
        openrouter_model = self.get_openrouter_model()

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://github.com/enchant-book-manager",  # Required by OpenRouter
            "X-Title": "EnChANT Book Manager - Renaming Phase",
        }
        data = {
            "model": openrouter_model,
            "temperature": self.temperature,
            "messages": messages,
            "usage": {"include": True},  # Request usage/cost information
        }
        try:
            response = requests.post(
                self.api_url,
                headers=headers,
                json=data,
                timeout=10,
            )
            response.raise_for_status()
            logger.info("OpenRouter API request successful.")
            return cast(dict[str, Any], response.json())
        except HTTPError as e:
            if e.response.status_code == 400 and "model" in e.response.text.lower():
                logger.error(f"Model '{self.model}' (mapped to '{openrouter_model}') not available on OpenRouter.")
                logger.error("Available OpenAI models on OpenRouter: " + ", ".join(OPENROUTER_MODEL_MAPPING.values()))
                logger.error("For other models, use the full model name as listed on OpenRouter.")
            raise
        except KeyboardInterrupt:
            logger.error("Request interrupted by user (Ctrl+C). Exiting gracefully.")
            sys.exit(1)
        except Exception as e:
            logger.error(f"Error making OpenRouter request: {e}")
            raise

    def extract_metadata(self, content: str, char_limit: int = 1500) -> str | None:
        """
        Extract novel metadata from content using AI.

        Args:
            content: Text content to analyze
            char_limit: Maximum characters to send to API

        Returns:
            Response content string or None if extraction failed
        """
        # Create prompt
        prompt = (
            "Given the following content from a novel, perform the following tasks:\n"
            "- Detect the language(s) of the text.\n"
            "- Find the title of the novel and the author's name.\n"
            "- Return the title of the novel and author in the original language, followed by their English translations and the romanization of the author's name.\n"
            "Content:\n" + content[:char_limit] + "\nReturn the response in JSON format as follows:\n"
            "{\n"
            '    "detected_language": "<detected_language>",\n'
            '    "novel_title_original": "<novel_title_original>",\n'
            '    "author_name_original": "<author_name_original>",\n'
            '    "novel_title_english": "<novel_title_english>",\n'
            '    "author_name_english": "<author_name_english>",\n'
            '    "author_name_romanized": "<author_name_romanized>"\n'
            "}\n"
        )

        messages = [{"role": "user", "content": prompt}]
        response = self.make_request(messages)

        # Extract response content
        choices = response.get("choices")
        if not choices or not isinstance(choices, list):
            logger.error(f"No choices found in OpenAI response: {response}")
            return None

        message = choices[0].get("message")
        if not message or "content" not in message:
            logger.error(f"Message content missing in OpenAI response: {response}")
            return None

        response_content = message["content"]
        if not isinstance(response_content, str):
            logger.error(f"Expected string response content, got {type(response_content)}")
            return None

        # Track cost using unified cost tracker
        usage = response.get("usage", {})
        global_cost_tracker.track_usage(usage)

        return response_content
