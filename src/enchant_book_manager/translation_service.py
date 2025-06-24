#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright (c) 2024-2025 Emasoft
# Licensed under the Apache License, Version 2.0 (the "License");
# You may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
# - Refactored from original 40KB file into smaller modules
# - Extracted constants to translation_constants.py
# - Extracted validation to text_validators.py
# - Extracted API clients to api_clients.py
# - Main class now focuses on orchestration and translation flow
#

from __future__ import annotations

import os
import logging
import re
import threading
from typing import Any, Optional, Callable
import functools
import time

from .cost_tracker import global_cost_tracker
from .common_text_utils import clean, normalize_spaces as common_normalize_spaces
from .common_utils import retry_with_backoff
from .common_constants import DEFAULT_MAX_RETRIES, DEFAULT_RETRY_WAIT_MAX

# Import from refactored modules
from .translation_constants import (
    DEFAULT_CHUNK_SIZE,
    DEFAULT_MAX_TOKENS,
    MODEL_NAME_DEEPSEEK,
    MODEL_NAME_QWEN,
    SYSTEM_PROMPT_DEEPSEEK,
    SYSTEM_PROMPT_QWEN,
    USER_PROMPT_1STPASS_DEEPSEEK,
    USER_PROMPT_2NDPASS_DEEPSEEK,
    USER_PROMPT_1STPASS_QWEN,
    USER_PROMPT_2NDPASS_QWEN,
)
from .text_validators import (
    is_latin_charset,
    validate_translation_output,
    clean_repeated_chars,
)
from .api_clients import create_api_client, TranslationAPIClient


# Define a custom exception for translation failures
class TranslationError(Exception):
    pass


def no_retry_call(fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    """
    Direct function call without retry logic.
    Used when retry is not appropriate.
    """
    return fn(*args, **kwargs)


class ChineseAITranslator:
    """
    Main translator class for Chinese to English translation.

    Coordinates the translation process using configured API clients
    and handles chunking, validation, and cost tracking.
    """

    def __init__(
        self,
        logger: Optional[logging.Logger] = None,
        use_remote: bool = False,
        api_key: Optional[str] = None,
        endpoint: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        timeout: int = 480,
        top_p: float = 0.01,
        frequency_penalty: float = 0.3,
        presence_penalty: float = 0.0,
        repetition_penalty: float = 1.0,
    ):
        """
        Initialize the translator with configuration.

        Args:
            logger: Logger instance for output
            use_remote: Whether to use remote API (OpenRouter) or local (LM Studio)
            api_key: API key for remote service
            endpoint: Custom API endpoint (overrides default)
            model: Model name to use (overrides default)
            temperature: Sampling temperature (0.0 to 1.0)
            max_tokens: Maximum tokens in response
            timeout: Request timeout in seconds
            top_p: Nucleus sampling parameter
            frequency_penalty: Penalty for token frequency
            presence_penalty: Penalty for token presence
            repetition_penalty: Penalty for repetition
        """
        self.logger = logger
        self.is_remote = use_remote
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        self.top_p = top_p
        self.frequency_penalty = frequency_penalty
        self.presence_penalty = presence_penalty
        self.repetition_penalty = repetition_penalty

        # Cost tracking
        self._cost_lock = threading.Lock()
        self.request_count = 0

        # Set up model configuration based on API type
        if use_remote:
            self.MODEL_NAME = model or MODEL_NAME_DEEPSEEK
            self.SYSTEM_PROMPT = SYSTEM_PROMPT_DEEPSEEK
            self.USER_PROMPT_1STPASS = USER_PROMPT_1STPASS_DEEPSEEK
            self.USER_PROMPT_2NDPASS = USER_PROMPT_2NDPASS_DEEPSEEK
        else:
            self.MODEL_NAME = model or MODEL_NAME_QWEN
            self.SYSTEM_PROMPT = SYSTEM_PROMPT_QWEN
            self.USER_PROMPT_1STPASS = USER_PROMPT_1STPASS_QWEN
            self.USER_PROMPT_2NDPASS = USER_PROMPT_2NDPASS_QWEN

        # Create API client
        self.api_client = create_api_client(use_remote=use_remote, api_key=api_key, model_name=self.MODEL_NAME, logger=self.log)

        # Override endpoint if provided
        if endpoint:
            self.api_client.api_url = endpoint

    def log(self, message: str, level: str = "info") -> None:
        """Log a message with appropriate level."""
        if self.logger:
            log_method = getattr(self.logger, level, self.logger.info)
            log_method(message)

    def get_api_messages(self, chinese_text: str, double_translation: Optional[bool] = None) -> list[dict[str, str]]:
        """
        Create the API message structure for translation.

        Args:
            chinese_text: Text to translate
            double_translation: Whether this is a second pass

        Returns:
            List of message dictionaries for API
        """
        if double_translation:
            # Second pass - cleaning up any remaining Chinese
            user_prompt = self.USER_PROMPT_2NDPASS + chinese_text
        else:
            # First pass - main translation
            user_prompt = self.USER_PROMPT_1STPASS + chinese_text

        messages = []

        # Add system prompt if available
        if self.SYSTEM_PROMPT:
            messages.append({"role": "system", "content": self.SYSTEM_PROMPT})

        # Add user prompt
        messages.append({"role": "user", "content": user_prompt})

        return messages

    def api_request_with_retry(
        self,
        messages: list[dict[str, str]],
        double_translation: Optional[bool] = None,
        max_retries: int = DEFAULT_MAX_RETRIES,
    ) -> Optional[str]:
        """
        Make API request with retry logic.

        Args:
            messages: Messages to send to API
            double_translation: Whether this is a second pass
            max_retries: Maximum retry attempts

        Returns:
            Translated text or None if all retries failed
        """
        # Track request count
        with self._cost_lock:
            self.request_count += 1

        # Prepare kwargs for API request
        api_kwargs = {
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }

        if self.is_remote:
            # Add remote-specific parameters
            api_kwargs.update(
                {
                    "top_p": self.top_p,
                    "frequency_penalty": self.frequency_penalty,
                    "presence_penalty": self.presence_penalty,
                    "repetition_penalty": self.repetition_penalty,
                }
            )

        # Use exponential backoff retry for API calls
        from .common_utils import exponential_backoff_retry

        return exponential_backoff_retry(
            self.api_client.make_request,
            max_retries,
            1.0,  # base_wait
            DEFAULT_RETRY_WAIT_MAX,  # max_wait
            1.0,  # min_wait
            (Exception,),  # exception_types
            self.logger,  # logger - pass the actual logger object
            None,  # on_retry
            None,  # time_limit
            messages,
            **api_kwargs,
        )

    def validate_and_clean_response(self, response_text: str, attempt: int = 1) -> tuple[bool, str]:
        """
        Validate and clean the translation response.

        Args:
            response_text: Raw response from API
            attempt: Current attempt number

        Returns:
            Tuple of (is_valid, cleaned_text)
        """
        if not response_text:
            self.log("Empty response received", "warning")
            return False, ""

        # Use validation from text_validators module
        is_valid, cleaned_text = validate_translation_output(response_text, self.log)

        if not is_valid and attempt == 1:
            self.log("Response contains non-Latin characters, will attempt cleanup", "warning")

        return is_valid, cleaned_text

    def translate_chunk(
        self,
        chinese_text: str,
        double_translation: Optional[bool] = None,
        is_last_chunk: bool = False,
    ) -> Optional[str]:
        """
        Translate a chunk of Chinese text to English.

        Args:
            chinese_text: Chinese text chunk to translate
            double_translation: Force double translation mode
            is_last_chunk: Whether this is the last chunk

        Returns:
            Translated English text or None if failed
        """
        if not chinese_text or not chinese_text.strip():
            self.log("Empty chunk provided", "warning")
            return ""

        # Clean input text
        chinese_text = clean(chinese_text)
        chinese_text = normalize_spaces(chinese_text)

        # Prepare messages
        messages = self.get_api_messages(chinese_text, double_translation=False)

        # First translation attempt
        self.log(f"Translating chunk of {len(chinese_text)} characters...")
        response_text = self.api_request_with_retry(messages)

        if not response_text:
            self.log("Translation failed - no response", "error")
            return None

        # Validate response
        is_valid, cleaned_text = self.validate_and_clean_response(response_text, attempt=1)

        # If not valid or double translation requested, do second pass
        if not is_valid or (double_translation is True):
            self.log("Performing second translation pass...")
            messages = self.get_api_messages(cleaned_text, double_translation=True)
            second_response = self.api_request_with_retry(messages)

            if second_response:
                is_valid, cleaned_text = self.validate_and_clean_response(second_response, attempt=2)

        # Final validation
        if not is_latin_charset(cleaned_text, threshold=0.05):
            self.log("Translation still contains non-Latin characters after cleanup", "warning")

        return cleaned_text

    def translate_file(self, input_file: str, output_file: Optional[str] = None) -> Optional[str]:
        """
        Translate a file from Chinese to English.

        Args:
            input_file: Path to input file
            output_file: Path to output file (optional)

        Returns:
            Translated text or None if failed
        """
        self.log(f"Translating file: {input_file}")

        # This is a simplified version - the actual implementation
        # would need proper file handling and chunking logic
        try:
            with open(input_file, "r", encoding="utf-8") as f:
                chinese_text = f.read()

            english_text = self.translate(chinese_text)

            if english_text and output_file:
                with open(output_file, "w", encoding="utf-8") as f:
                    f.write(english_text)

            return english_text

        except Exception as e:
            self.log(f"Error translating file: {e}", "error")
            return None

    def translate(self, input_string: str, is_last_chunk: bool = False) -> Optional[str]:
        """
        Translate a string from Chinese to English.

        Main entry point for translation requests.

        Args:
            input_string: Chinese text to translate
            is_last_chunk: Whether this is the last chunk

        Returns:
            Translated English text or None if failed
        """
        if not input_string.strip():
            self.log("Input string is empty or contains only whitespace", "warning")
            return ""

        try:
            english_text = self.translate_chunk(input_string, double_translation=None, is_last_chunk=is_last_chunk)
        except Exception as ex:
            self.log(f"Unexpected error during translation: {ex}", "error")
            return None

        return english_text

    def get_cost_summary(self) -> dict[str, Any]:
        """
        Get cumulative cost summary for remote API usage.

        Returns:
            Dictionary with cost tracking information
        """
        # Get summary from global cost tracker
        summary = global_cost_tracker.get_summary()

        # Add model and API type information
        summary["model"] = self.MODEL_NAME

        if self.is_remote:
            summary["api_type"] = "remote"
        else:
            summary["api_type"] = "local"
            summary["message"] = "Local API - no costs incurred"
            # Override cost fields for local API
            summary["total_cost"] = 0.0
            summary["average_cost_per_request"] = 0.0

        return summary

    def format_cost_summary(self) -> str:
        """
        Format cost summary as human-readable string.

        Returns:
            Formatted string with cost breakdown
        """
        summary = self.get_cost_summary()

        if self.is_remote:
            lines = [
                "\n=== Translation Cost Summary ===",
                f"Model: {summary['model']}",
                f"API Type: {summary['api_type']}",
                f"Total Cost: ${summary['total_cost']:.6f}",
                f"Total Requests: {summary['request_count']}",
                f"Total Tokens: {summary['total_tokens']:,}",
                f"  - Prompt Tokens: {summary['total_prompt_tokens']:,}",
                f"  - Completion Tokens: {summary['total_completion_tokens']:,}",
            ]
            if summary["request_count"] > 0:
                lines.append(f"Average Cost per Request: ${summary['average_cost_per_request']:.6f}")
                lines.append(f"Average Tokens per Request: {summary['total_tokens'] // summary['request_count']:,}")
            return "\n".join(lines)
        else:
            return f"\n=== Translation Cost Summary ===\n" f"Model: {summary['model']}\n" f"API Type: {summary['api_type']}\n" f"Local API - no costs incurred"

    def reset_cost_tracking(self) -> None:
        """Reset cost tracking counters."""
        # Reset global tracker
        global_cost_tracker.reset()

        # Reset local counter
        with self._cost_lock:
            self.request_count = 0


# Import normalize_spaces function
def normalize_spaces(text: str, preserve_paragraphs: bool = True) -> str:
    """Wrapper for common_normalize_spaces with translator-specific defaults."""
    # Note: common_normalize_spaces doesn't have preserve_paragraphs parameter
    # Just call it directly
    return common_normalize_spaces(text)


# Example usage:
if __name__ == "__main__":
    translator = ChineseAITranslator(use_remote=False)
    english_text = translator.translate_file(input_file="dummy_chinese.txt", output_file="output.txt")
    if english_text:
        # This is example code, print is acceptable here
        print("Translation completed successfully.")
