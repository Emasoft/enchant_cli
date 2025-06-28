#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test suite for translation_constants module.
"""

import sys
import string
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from enchant_book_manager.translation_constants import (
    # Timeouts and limits
    DEFAULT_CHUNK_SIZE,
    CONNECTION_TIMEOUT,
    RESPONSE_TIMEOUT,
    DEFAULT_MAX_TOKENS,
    # Remote API settings
    API_URL_OPENROUTER,
    MODEL_NAME_DEEPSEEK,
    SYSTEM_PROMPT_DEEPSEEK,
    USER_PROMPT_1STPASS_DEEPSEEK,
    USER_PROMPT_2NDPASS_DEEPSEEK,
    # Local API settings
    API_URL_LMSTUDIO,
    MODEL_NAME_QWEN,
    SYSTEM_PROMPT_QWEN,
    USER_PROMPT_1STPASS_QWEN,
    USER_PROMPT_2NDPASS_QWEN,
    # Character sets
    PARAGRAPH_DELIMITERS,
    PRESERVE_UNLIMITED,
    ALLOWED_ASCII,
)
from enchant_book_manager.common_constants import (
    DEFAULT_LMSTUDIO_API_URL,
    DEFAULT_OPENROUTER_API_URL,
)


class TestTranslationConstants:
    """Test translation constants definitions."""

    def test_timeout_constants(self):
        """Test timeout and size constants."""
        # Check chunk size is reasonable
        assert isinstance(DEFAULT_CHUNK_SIZE, int)
        assert DEFAULT_CHUNK_SIZE > 0
        assert DEFAULT_CHUNK_SIZE == 12000  # 12K chars

        # Check timeouts
        assert isinstance(CONNECTION_TIMEOUT, int)
        assert CONNECTION_TIMEOUT > 0
        assert CONNECTION_TIMEOUT == 60  # 1 minute

        assert isinstance(RESPONSE_TIMEOUT, int)
        assert RESPONSE_TIMEOUT > 0
        assert RESPONSE_TIMEOUT == 480  # 8 minutes

        # Response timeout should be greater than connection timeout
        assert RESPONSE_TIMEOUT > CONNECTION_TIMEOUT

        # Check max tokens
        assert isinstance(DEFAULT_MAX_TOKENS, int)
        assert DEFAULT_MAX_TOKENS > 0
        assert DEFAULT_MAX_TOKENS == 4000

    def test_remote_api_settings(self):
        """Test remote API configuration constants."""
        # Check API URL
        assert API_URL_OPENROUTER == DEFAULT_OPENROUTER_API_URL
        assert isinstance(API_URL_OPENROUTER, str)
        assert API_URL_OPENROUTER.startswith("http")

        # Check model name
        assert isinstance(MODEL_NAME_DEEPSEEK, str)
        assert MODEL_NAME_DEEPSEEK == "deepseek/deepseek-r1:nitro"
        assert "/" in MODEL_NAME_DEEPSEEK  # Should have provider/model format

        # Check system prompt (empty for DeepSeek)
        assert isinstance(SYSTEM_PROMPT_DEEPSEEK, str)
        assert SYSTEM_PROMPT_DEEPSEEK == ""

    def test_deepseek_prompts(self):
        """Test DeepSeek prompt templates."""
        # First pass prompt
        assert isinstance(USER_PROMPT_1STPASS_DEEPSEEK, str)
        assert len(USER_PROMPT_1STPASS_DEEPSEEK) > 100  # Should be substantial
        assert "[Task]" in USER_PROMPT_1STPASS_DEEPSEEK
        assert "[TRANSLATION RULES]" in USER_PROMPT_1STPASS_DEEPSEEK
        assert "chinese" in USER_PROMPT_1STPASS_DEEPSEEK.lower()
        assert "english" in USER_PROMPT_1STPASS_DEEPSEEK.lower()

        # Check for key translation rules
        assert "Nascent Soul" in USER_PROMPT_1STPASS_DEEPSEEK  # Wuxia terminology
        assert "curly quotes" in USER_PROMPT_1STPASS_DEEPSEEK
        assert "\u201c" in USER_PROMPT_1STPASS_DEEPSEEK  # Has curly quote example

        # Second pass prompt
        assert isinstance(USER_PROMPT_2NDPASS_DEEPSEEK, str)
        assert len(USER_PROMPT_2NDPASS_DEEPSEEK) > 100
        assert "[TASK]" in USER_PROMPT_2NDPASS_DEEPSEEK
        assert "[EDITING RULES]" in USER_PROMPT_2NDPASS_DEEPSEEK

    def test_local_api_settings(self):
        """Test local API configuration constants."""
        # Check API URL
        assert API_URL_LMSTUDIO == DEFAULT_LMSTUDIO_API_URL
        assert isinstance(API_URL_LMSTUDIO, str)
        assert API_URL_LMSTUDIO.startswith("http")

        # Check model name
        assert isinstance(MODEL_NAME_QWEN, str)
        assert MODEL_NAME_QWEN == "qwen3-30b-a3b-mlx@8bit"
        assert "@" in MODEL_NAME_QWEN  # Has quantization info

    def test_qwen_prompts(self):
        """Test Qwen prompt templates."""
        # System prompt
        assert isinstance(SYSTEM_PROMPT_QWEN, str)
        assert len(SYSTEM_PROMPT_QWEN) > 100
        assert "professional" in SYSTEM_PROMPT_QWEN
        assert "machine translation" in SYSTEM_PROMPT_QWEN

        # Check for numbered rules
        for i in range(1, 23):  # Rules 1-22
            assert f"{i}." in SYSTEM_PROMPT_QWEN

        # First pass prompt
        assert isinstance(USER_PROMPT_1STPASS_QWEN, str)
        assert "professional english translation" in USER_PROMPT_1STPASS_QWEN

        # Second pass prompt
        assert isinstance(USER_PROMPT_2NDPASS_QWEN, str)
        assert "chinese words and characters" in USER_PROMPT_2NDPASS_QWEN
        assert "curly quotes" in USER_PROMPT_2NDPASS_QWEN

    def test_paragraph_delimiters(self):
        """Test paragraph delimiter character set."""
        assert isinstance(PARAGRAPH_DELIMITERS, set)

        # Check common delimiters
        assert "\n" in PARAGRAPH_DELIMITERS  # Line Feed
        assert "\v" in PARAGRAPH_DELIMITERS  # Vertical Tab
        assert "\f" in PARAGRAPH_DELIMITERS  # Form Feed

        # Check Unicode delimiters
        assert "\u2028" in PARAGRAPH_DELIMITERS  # Line Separator
        assert "\u2029" in PARAGRAPH_DELIMITERS  # Paragraph Separator
        assert "\x85" in PARAGRAPH_DELIMITERS  # Next Line

        # Check special delimiters
        assert "\x1c" in PARAGRAPH_DELIMITERS  # File Separator
        assert "\x1d" in PARAGRAPH_DELIMITERS  # Group Separator
        assert "\x1e" in PARAGRAPH_DELIMITERS  # Record Separator

    def test_preserve_unlimited(self):
        """Test characters allowed unlimited repetition."""
        assert isinstance(PRESERVE_UNLIMITED, set)

        # Check basic characters
        assert " " in PRESERVE_UNLIMITED  # Space
        assert "." in PRESERVE_UNLIMITED  # Period
        assert "\n" in PRESERVE_UNLIMITED  # Newline
        assert "\r" in PRESERVE_UNLIMITED  # Carriage return
        assert "\t" in PRESERVE_UNLIMITED  # Tab

        # Check brackets and parentheses
        assert "(" in PRESERVE_UNLIMITED
        assert ")" in PRESERVE_UNLIMITED
        assert "[" in PRESERVE_UNLIMITED
        assert "]" in PRESERVE_UNLIMITED

        # Check symbols
        assert "+" in PRESERVE_UNLIMITED
        assert "-" in PRESERVE_UNLIMITED
        assert "_" in PRESERVE_UNLIMITED
        assert "=" in PRESERVE_UNLIMITED
        assert "/" in PRESERVE_UNLIMITED
        assert "\\" in PRESERVE_UNLIMITED
        assert "*" in PRESERVE_UNLIMITED
        assert "%" in PRESERVE_UNLIMITED
        assert "#" in PRESERVE_UNLIMITED
        assert "@" in PRESERVE_UNLIMITED
        assert "~" in PRESERVE_UNLIMITED
        assert "<" in PRESERVE_UNLIMITED
        assert ">" in PRESERVE_UNLIMITED
        assert "^" in PRESERVE_UNLIMITED
        assert "&" in PRESERVE_UNLIMITED

        # Check special characters
        assert "°" in PRESERVE_UNLIMITED  # Degree
        assert "…" in PRESERVE_UNLIMITED  # Ellipsis
        assert "—" in PRESERVE_UNLIMITED  # Em dash
        assert "•" in PRESERVE_UNLIMITED  # Bullet
        assert "$" in PRESERVE_UNLIMITED  # Dollar
        assert "|" in PRESERVE_UNLIMITED  # Pipe

        # Should include all paragraph delimiters
        for delimiter in PARAGRAPH_DELIMITERS:
            assert delimiter in PRESERVE_UNLIMITED

    def test_allowed_ascii(self):
        """Test allowed ASCII character set."""
        assert isinstance(ALLOWED_ASCII, set)

        # Should contain all ASCII letters
        for char in string.ascii_letters:
            assert char in ALLOWED_ASCII

        # Should contain all digits
        for char in string.digits:
            assert char in ALLOWED_ASCII

        # Should contain all ASCII punctuation
        for char in string.punctuation:
            assert char in ALLOWED_ASCII

        # Size check
        expected_size = len(string.ascii_letters) + len(string.digits) + len(string.punctuation)
        assert len(ALLOWED_ASCII) == expected_size

    def test_prompt_consistency(self):
        """Test consistency between prompts."""
        # Both DeepSeek prompts should mention curly quotes
        assert "curly quotes" in USER_PROMPT_1STPASS_DEEPSEEK.lower()
        assert "curly quotes" in USER_PROMPT_2NDPASS_DEEPSEEK.lower()

        # Both Qwen prompts should be consistent in style
        assert ";;" in SYSTEM_PROMPT_QWEN  # Uses ;; delimiter
        assert ";;" in USER_PROMPT_1STPASS_QWEN
        assert ";;" in USER_PROMPT_2NDPASS_QWEN

        # All prompts should mention translation
        all_prompts = [
            USER_PROMPT_1STPASS_DEEPSEEK,
            USER_PROMPT_2NDPASS_DEEPSEEK,
            SYSTEM_PROMPT_QWEN,
            USER_PROMPT_1STPASS_QWEN,
            USER_PROMPT_2NDPASS_QWEN,
        ]
        for prompt in all_prompts:
            assert "translat" in prompt.lower()  # translate/translation

    def test_model_names_format(self):
        """Test model name formatting conventions."""
        # Remote model should have provider/model format
        assert "/" in MODEL_NAME_DEEPSEEK
        provider, model = MODEL_NAME_DEEPSEEK.split("/", 1)
        assert provider == "deepseek"
        assert model.startswith("deepseek-")

        # Local model should have quantization info
        assert "@" in MODEL_NAME_QWEN
        base_model, quant = MODEL_NAME_QWEN.split("@", 1)
        assert base_model.startswith("qwen")
        assert "bit" in quant  # e.g., "8bit"

    def test_no_overlaps_in_sets(self):
        """Test that character sets do not have unexpected overlaps."""
        # Paragraph delimiters should be a subset of preserve unlimited
        assert PARAGRAPH_DELIMITERS.issubset(PRESERVE_UNLIMITED)

        # Allowed ASCII should not overlap with most Unicode delimiters
        unicode_delimiters = {d for d in PARAGRAPH_DELIMITERS if ord(d) > 127}
        assert not ALLOWED_ASCII & unicode_delimiters  # No overlap

    def test_url_formats(self):
        """Test API URL formats."""
        # Both URLs should be valid HTTP(S) URLs
        assert API_URL_OPENROUTER.startswith(("http://", "https://"))
        assert API_URL_LMSTUDIO.startswith(("http://", "https://"))

        # URLs should end with expected path
        assert "chat/completions" in API_URL_OPENROUTER
        assert "chat/completions" in API_URL_LMSTUDIO

    def test_prompt_length_reasonable(self):
        """Test that prompts are not too short or too long."""
        # System prompts
        assert 100 < len(SYSTEM_PROMPT_QWEN) < 10000  # Reasonable length

        # User prompts should be substantial but not excessive
        assert 100 < len(USER_PROMPT_1STPASS_DEEPSEEK) < 10000
        assert 100 < len(USER_PROMPT_2NDPASS_DEEPSEEK) < 10000
        assert 50 < len(USER_PROMPT_1STPASS_QWEN) < 1000
        assert 50 < len(USER_PROMPT_2NDPASS_QWEN) < 1000
