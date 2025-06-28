#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test suite for config_schema module.
"""

import pytest
import yaml
from pathlib import Path
import sys
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from enchant_book_manager.config_schema import (
    indent_prompt,
    DEFAULT_CONFIG_TEMPLATE,
)


class TestIndentPrompt:
    """Test the indent_prompt function."""

    def test_indent_single_line(self):
        """Test indenting a single line."""
        prompt = "This is a single line"
        result = indent_prompt(prompt, 4)
        assert result == "    This is a single line"

    def test_indent_multi_line(self):
        """Test indenting multiple lines."""
        prompt = "Line 1\nLine 2\nLine 3"
        result = indent_prompt(prompt, 2)
        expected = "  Line 1\n  Line 2\n  Line 3"
        assert result == expected

    def test_indent_with_empty_lines(self):
        """Test indenting with empty lines."""
        prompt = "Line 1\n\nLine 3\n"
        result = indent_prompt(prompt, 3)
        expected = "   Line 1\n\n   Line 3\n"
        assert result == expected

    def test_indent_default_level(self):
        """Test default indent level of 6."""
        prompt = "Test line"
        result = indent_prompt(prompt)
        assert result == "      Test line"

    def test_indent_zero_level(self):
        """Test zero indent level."""
        prompt = "No indent"
        result = indent_prompt(prompt, 0)
        assert result == "No indent"

    def test_indent_with_trailing_newline(self):
        """Test indenting text with trailing newline."""
        prompt = "Line 1\nLine 2\n"
        result = indent_prompt(prompt, 2)
        expected = "  Line 1\n  Line 2\n"
        assert result == expected

    def test_indent_empty_string(self):
        """Test indenting empty string."""
        result = indent_prompt("", 4)
        assert result == ""

    def test_indent_only_newlines(self):
        """Test indenting string with only newlines."""
        prompt = "\n\n\n"
        result = indent_prompt(prompt, 2)
        expected = "\n\n\n"
        assert result == expected


class TestDefaultConfigTemplate:
    """Test the DEFAULT_CONFIG_TEMPLATE."""

    def test_config_template_is_string(self):
        """Test that DEFAULT_CONFIG_TEMPLATE is a string."""
        assert isinstance(DEFAULT_CONFIG_TEMPLATE, str)
        assert len(DEFAULT_CONFIG_TEMPLATE) > 0

    def test_config_template_is_valid_yaml(self):
        """Test that DEFAULT_CONFIG_TEMPLATE is valid YAML."""
        # Should not raise exception
        config = yaml.safe_load(DEFAULT_CONFIG_TEMPLATE)
        assert isinstance(config, dict)

    def test_config_has_required_sections(self):
        """Test that config has all required sections."""
        config = yaml.safe_load(DEFAULT_CONFIG_TEMPLATE)

        # Check top-level sections
        required_sections = [
            "presets",
            "translation",
            "text_processing",
            "novel_renaming",
            "epub",
            "batch",
            "icloud",
            "pricing",
            "logging",
            "advanced",
        ]
        for section in required_sections:
            assert section in config, f"Missing section: {section}"

    def test_presets_section(self):
        """Test the presets section structure."""
        config = yaml.safe_load(DEFAULT_CONFIG_TEMPLATE)

        # Check required presets exist
        assert "LOCAL" in config["presets"]
        assert "REMOTE" in config["presets"]

        # Check LOCAL preset has all required fields
        local_preset = config["presets"]["LOCAL"]
        required_fields = [
            "endpoint",
            "model",
            "connection_timeout",
            "response_timeout",
            "max_retries",
            "retry_wait_base",
            "retry_wait_max",
            "double_pass",
            "max_chars_per_chunk",
            "temperature",
            "max_tokens",
            "system_prompt",
            "user_prompt_1st_pass",
            "user_prompt_2nd_pass",
        ]
        for field in required_fields:
            assert field in local_preset, f"Missing field in LOCAL preset: {field}"

        # Check REMOTE preset has all required fields
        remote_preset = config["presets"]["REMOTE"]
        for field in required_fields:
            assert field in remote_preset, f"Missing field in REMOTE preset: {field}"

    def test_preset_values(self):
        """Test preset default values."""
        config = yaml.safe_load(DEFAULT_CONFIG_TEMPLATE)

        # Test LOCAL preset defaults
        local = config["presets"]["LOCAL"]
        assert local["endpoint"] == "http://localhost:1234/v1/chat/completions"
        assert local["model"] == "qwen3-30b-a3b-mlx@8bit"
        assert local["connection_timeout"] == 30
        assert local["response_timeout"] == 300
        assert local["max_retries"] == 7
        assert local["retry_wait_base"] == 1.0
        assert local["retry_wait_max"] == 60.0
        assert local["double_pass"] is False
        assert local["max_chars_per_chunk"] == 11999
        assert local["temperature"] == 0.05
        assert local["max_tokens"] == 4000

        # Test REMOTE preset defaults
        remote = config["presets"]["REMOTE"]
        assert remote["endpoint"] == "https://openrouter.ai/api/v1/chat/completions"
        assert remote["model"] == "deepseek/deepseek-r1:nitro"
        assert remote["double_pass"] is True
        assert remote["system_prompt"] == ""

    def test_preset_prompts_exist(self):
        """Test that preset prompts exist and are non-empty."""
        config = yaml.safe_load(DEFAULT_CONFIG_TEMPLATE)

        # LOCAL preset should have all prompts
        local = config["presets"]["LOCAL"]
        assert len(local["system_prompt"]) > 100  # Should be substantial
        assert len(local["user_prompt_1st_pass"]) > 50
        assert len(local["user_prompt_2nd_pass"]) > 50

        # REMOTE preset should have user prompts
        remote = config["presets"]["REMOTE"]
        assert remote["system_prompt"] == ""  # Remote uses empty system prompt
        assert len(remote["user_prompt_1st_pass"]) > 100
        assert len(remote["user_prompt_2nd_pass"]) > 100

    def test_translation_section(self):
        """Test the translation section structure."""
        config = yaml.safe_load(DEFAULT_CONFIG_TEMPLATE)
        trans = config["translation"]

        assert trans["service"] == "local"
        assert trans["active_preset"] == "LOCAL"
        assert "local" in trans
        assert "remote" in trans
        assert trans["temperature"] == 0.3
        assert trans["max_tokens"] == 4000
        assert trans["max_retries"] == 7

    def test_text_processing_section(self):
        """Test the text_processing section."""
        config = yaml.safe_load(DEFAULT_CONFIG_TEMPLATE)
        tp = config["text_processing"]

        assert tp["max_chars_per_chunk"] == 11999
        assert tp["default_encoding"] == "utf-8"

    def test_novel_renaming_section(self):
        """Test the novel_renaming section."""
        config = yaml.safe_load(DEFAULT_CONFIG_TEMPLATE)
        nr = config["novel_renaming"]

        assert nr["enabled"] is False
        assert "openai" in nr
        assert nr["openai"]["model"] == "gpt-4o-mini"
        assert nr["kb_to_read"] == 35
        assert nr["min_file_size_kb"] == 100

    def test_epub_section(self):
        """Test the epub section."""
        config = yaml.safe_load(DEFAULT_CONFIG_TEMPLATE)
        epub = config["epub"]

        assert epub["enabled"] is False
        assert epub["build_toc"] is True
        assert epub["language"] == "zh"
        assert epub["include_cover"] is True
        assert epub["validate_chapters"] is True
        assert epub["strict_mode"] is False

    def test_batch_section(self):
        """Test the batch section."""
        config = yaml.safe_load(DEFAULT_CONFIG_TEMPLATE)
        batch = config["batch"]

        assert batch["max_workers"] is None
        assert batch["recursive"] is True
        assert batch["file_pattern"] == "*.txt"
        assert batch["continue_on_error"] is True
        assert batch["save_progress"] is True
        assert batch["progress_file"] == "translation_batch_progress.yml"
        assert batch["archive_file"] == "translations_chronology.yml"

    def test_icloud_section(self):
        """Test the icloud section."""
        config = yaml.safe_load(DEFAULT_CONFIG_TEMPLATE)
        icloud = config["icloud"]

        assert icloud["enabled"] is None
        assert icloud["sync_timeout"] == 300
        assert icloud["sync_check_interval"] == 2

    def test_pricing_section(self):
        """Test the pricing section."""
        config = yaml.safe_load(DEFAULT_CONFIG_TEMPLATE)
        pricing = config["pricing"]

        assert pricing["enabled"] is True
        assert "pricing_url" in pricing
        assert "fallback_urls" in pricing
        assert isinstance(pricing["fallback_urls"], list)
        assert len(pricing["fallback_urls"]) > 0

    def test_logging_section(self):
        """Test the logging section."""
        config = yaml.safe_load(DEFAULT_CONFIG_TEMPLATE)
        logging = config["logging"]

        assert logging["level"] == "INFO"
        assert logging["file_enabled"] is True
        assert logging["file_path"] == "enchant_book_manager.log"
        assert "format" in logging

    def test_advanced_section(self):
        """Test the advanced section."""
        config = yaml.safe_load(DEFAULT_CONFIG_TEMPLATE)
        advanced = config["advanced"]

        assert advanced["clean_adverts"] is True
        assert advanced["content_preview_limit"] == 1500
        assert "supported_encodings" in advanced
        assert isinstance(advanced["supported_encodings"], list)
        assert "utf-8" in advanced["supported_encodings"]
        assert "gb18030" in advanced["supported_encodings"]

    def test_config_has_helpful_comments(self):
        """Test that config template includes helpful comments."""
        # Check for comment markers
        assert "# ENCHANT Configuration File" in DEFAULT_CONFIG_TEMPLATE
        assert "# Translation Presets" in DEFAULT_CONFIG_TEMPLATE
        assert "# IMPORTANT:" in DEFAULT_CONFIG_TEMPLATE
        assert "# Local translation preset" in DEFAULT_CONFIG_TEMPLATE
        assert "# Remote translation preset" in DEFAULT_CONFIG_TEMPLATE
        assert "# Add your custom presets here" in DEFAULT_CONFIG_TEMPLATE

    def test_config_includes_example_preset(self):
        """Test that config includes example custom preset."""
        assert "# CUSTOM_FAST:" in DEFAULT_CONFIG_TEMPLATE
        assert "#   endpoint:" in DEFAULT_CONFIG_TEMPLATE
        assert "#   model:" in DEFAULT_CONFIG_TEMPLATE

    def test_prompts_are_embedded(self):
        """Test that prompts are properly embedded in template."""
        config = yaml.safe_load(DEFAULT_CONFIG_TEMPLATE)

        # Check that prompts were embedded
        local = config["presets"]["LOCAL"]
        # Check for key phrases from actual prompts
        assert "professional, authentic machine translation engine" in local["system_prompt"]
        assert "professional english translation" in local["user_prompt_1st_pass"]
        assert "Examine the following text" in local["user_prompt_2nd_pass"]

        remote = config["presets"]["REMOTE"]
        assert "professional and helpful translator" in remote["user_prompt_1st_pass"]
        assert "helpful and professional translator" in remote["user_prompt_2nd_pass"]

    def test_api_key_fields_are_null(self):
        """Test that API key fields default to null."""
        config = yaml.safe_load(DEFAULT_CONFIG_TEMPLATE)

        assert config["translation"]["remote"]["api_key"] is None
        assert config["novel_renaming"]["openai"]["api_key"] is None

    def test_numeric_values_have_correct_types(self):
        """Test that numeric values have correct types."""
        config = yaml.safe_load(DEFAULT_CONFIG_TEMPLATE)

        # Check integers
        assert isinstance(config["presets"]["LOCAL"]["connection_timeout"], int)
        assert isinstance(config["presets"]["LOCAL"]["response_timeout"], int)
        assert isinstance(config["presets"]["LOCAL"]["max_retries"], int)
        assert isinstance(config["presets"]["LOCAL"]["max_chars_per_chunk"], int)
        assert isinstance(config["presets"]["LOCAL"]["max_tokens"], int)

        # Check floats
        assert isinstance(config["presets"]["LOCAL"]["retry_wait_base"], float)
        assert isinstance(config["presets"]["LOCAL"]["retry_wait_max"], float)
        assert isinstance(config["presets"]["LOCAL"]["temperature"], float)

        # Check booleans
        assert isinstance(config["presets"]["LOCAL"]["double_pass"], bool)
        assert isinstance(config["epub"]["enabled"], bool)
        assert isinstance(config["batch"]["recursive"], bool)
