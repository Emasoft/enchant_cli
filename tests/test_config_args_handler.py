#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test suite for config_args_handler module.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from enchant_book_manager.config_args_handler import ConfigArgsHandler


class TestConfigArgsHandler:
    """Test the ConfigArgsHandler class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.handler = ConfigArgsHandler()
        self.base_config = {
            "text_processing": {
                "default_encoding": "utf-8",
                "max_chars_per_chunk": 12000,
            },
            "translation": {
                "service": "local",
                "temperature": 0.7,
                "max_tokens": 4000,
                "model": "gpt-3.5-turbo",
                "endpoint": "http://localhost:5000",
                "connection_timeout": 30,
                "response_timeout": 300,
                "max_retries": 3,
                "retry_wait_base": 2,
                "retry_wait_max": 60,
                "double_pass": False,
            },
            "epub": {"enabled": False},
            "batch": {"enabled": False, "max_workers": 4},
        }

    def test_update_config_no_args(self):
        """Test updating config with no command-line arguments."""
        args = Mock()
        # Set all attributes to None
        for attr in [
            "encoding",
            "max_chars",
            "remote",
            "epub",
            "batch",
            "max_workers",
            "connection_timeout",
            "response_timeout",
            "max_retries",
            "retry_wait_base",
            "retry_wait_max",
            "temperature",
            "max_tokens",
            "model",
            "endpoint",
            "double_pass",
            "no_double_pass",
        ]:
            setattr(args, attr, None)

        preset_manager = Mock()
        preset_manager.active_preset = None

        result = self.handler.update_config_with_args(self.base_config, args, preset_manager)

        # Should be unchanged
        assert result == self.base_config
        # Should be a copy, not the same object
        assert result is not self.base_config

    def test_update_config_with_basic_args(self):
        """Test updating config with basic command-line arguments."""
        args = Mock()
        args.encoding = "gb2312"
        args.max_chars = 8000
        args.temperature = 0.5
        args.max_tokens = 2000
        args.model = "gpt-4"
        args.endpoint = "https://api.openai.com"

        # Set other attributes to None
        for attr in [
            "remote",
            "epub",
            "batch",
            "max_workers",
            "connection_timeout",
            "response_timeout",
            "max_retries",
            "retry_wait_base",
            "retry_wait_max",
            "double_pass",
            "no_double_pass",
        ]:
            setattr(args, attr, None)

        preset_manager = Mock()
        preset_manager.active_preset = None

        result = self.handler.update_config_with_args(self.base_config, args, preset_manager)

        # Verify updates
        assert result["text_processing"]["default_encoding"] == "gb2312"
        assert result["text_processing"]["max_chars_per_chunk"] == 8000
        assert result["translation"]["temperature"] == 0.5
        assert result["translation"]["max_tokens"] == 2000
        assert result["translation"]["model"] == "gpt-4"
        assert result["translation"]["endpoint"] == "https://api.openai.com"

    def test_update_config_remote_flag(self):
        """Test updating config with remote flag."""
        # Test remote=True
        args = Mock()
        args.remote = True
        for attr in [
            "encoding",
            "max_chars",
            "epub",
            "batch",
            "max_workers",
            "connection_timeout",
            "response_timeout",
            "max_retries",
            "retry_wait_base",
            "retry_wait_max",
            "temperature",
            "max_tokens",
            "model",
            "endpoint",
            "double_pass",
            "no_double_pass",
        ]:
            setattr(args, attr, None)

        preset_manager = Mock()
        preset_manager.active_preset = None

        result = self.handler.update_config_with_args(self.base_config, args, preset_manager)
        assert result["translation"]["service"] == "remote"

        # Test remote=False
        args.remote = False
        result = self.handler.update_config_with_args(self.base_config, args, preset_manager)
        assert result["translation"]["service"] == "local"

    def test_update_config_boolean_flags(self):
        """Test updating config with boolean flags."""
        args = Mock()
        args.epub = True
        args.batch = True

        # Set other attributes to None
        for attr in [
            "encoding",
            "max_chars",
            "remote",
            "max_workers",
            "connection_timeout",
            "response_timeout",
            "max_retries",
            "retry_wait_base",
            "retry_wait_max",
            "temperature",
            "max_tokens",
            "model",
            "endpoint",
            "double_pass",
            "no_double_pass",
        ]:
            setattr(args, attr, None)

        preset_manager = Mock()
        preset_manager.active_preset = None

        result = self.handler.update_config_with_args(self.base_config, args, preset_manager)

        assert result["epub"]["enabled"] is True
        assert result["batch"]["enabled"] is True

    def test_update_config_double_pass_handling(self):
        """Test handling of double_pass and no_double_pass arguments."""
        preset_manager = Mock()
        preset_manager.active_preset = None

        # Test double_pass=True
        args = Mock()
        args.double_pass = True
        args.no_double_pass = False
        for attr in [
            "encoding",
            "max_chars",
            "remote",
            "epub",
            "batch",
            "max_workers",
            "connection_timeout",
            "response_timeout",
            "max_retries",
            "retry_wait_base",
            "retry_wait_max",
            "temperature",
            "max_tokens",
            "model",
            "endpoint",
        ]:
            setattr(args, attr, None)

        result = self.handler.update_config_with_args(self.base_config, args, preset_manager)
        assert result["translation"]["double_pass"] is True

        # Test no_double_pass=True
        args.double_pass = False
        args.no_double_pass = True
        result = self.handler.update_config_with_args(self.base_config, args, preset_manager)
        assert result["translation"]["double_pass"] is False

        # Test neither flag set
        args.double_pass = False
        args.no_double_pass = False
        result = self.handler.update_config_with_args(self.base_config, args, preset_manager)
        # Should remain unchanged from base config
        assert result["translation"]["double_pass"] is False

    def test_update_config_with_preset(self):
        """Test updating config with active preset."""
        args = Mock()
        # All args None
        for attr in [
            "encoding",
            "max_chars",
            "remote",
            "epub",
            "batch",
            "max_workers",
            "connection_timeout",
            "response_timeout",
            "max_retries",
            "retry_wait_base",
            "retry_wait_max",
            "temperature",
            "max_tokens",
            "model",
            "endpoint",
            "double_pass",
            "no_double_pass",
        ]:
            setattr(args, attr, None)

        preset_manager = Mock()
        preset_manager.active_preset = "REMOTE"

        # Add preset to config
        self.base_config["presets"] = {"REMOTE": {"translation": {"service": "remote", "model": "gpt-4"}}}

        # Mock update_config_with_preset to simulate preset application
        preset_manager.update_config_with_preset = Mock(
            return_value={
                **self.base_config,
                "translation": {
                    **self.base_config["translation"],
                    "service": "remote",
                    "model": "gpt-4",
                },
            }
        )

        result = self.handler.update_config_with_args(self.base_config, args, preset_manager)

        # Verify preset was applied
        preset_manager.update_config_with_preset.assert_called_once()
        assert result["translation"]["service"] == "remote"
        assert result["translation"]["model"] == "gpt-4"

    def test_update_config_args_override_preset(self):
        """Test that command-line args override preset values."""
        args = Mock()
        args.model = "gpt-3.5-turbo"  # This should override preset
        args.temperature = 0.8

        # Set other attributes to None
        for attr in [
            "encoding",
            "max_chars",
            "remote",
            "epub",
            "batch",
            "max_workers",
            "connection_timeout",
            "response_timeout",
            "max_retries",
            "retry_wait_base",
            "retry_wait_max",
            "max_tokens",
            "endpoint",
            "double_pass",
            "no_double_pass",
        ]:
            setattr(args, attr, None)

        preset_manager = Mock()
        preset_manager.active_preset = "REMOTE"

        # Add preset to config
        self.base_config["presets"] = {
            "REMOTE": {
                "translation": {
                    "service": "remote",
                    "model": "gpt-4",
                    "temperature": 0.3,
                }
            }
        }

        # Mock preset application
        preset_manager.update_config_with_preset = Mock(
            return_value={
                **self.base_config,
                "translation": {
                    **self.base_config["translation"],
                    "service": "remote",
                    "model": "gpt-4",
                    "temperature": 0.3,
                },
            }
        )

        result = self.handler.update_config_with_args(self.base_config, args, preset_manager)

        # Args should override preset
        assert result["translation"]["model"] == "gpt-3.5-turbo"
        assert result["translation"]["temperature"] == 0.8
        assert result["translation"]["service"] == "remote"  # From preset

    def test_update_config_timeout_args(self):
        """Test updating config with timeout arguments."""
        args = Mock()
        args.connection_timeout = 60
        args.response_timeout = 600
        args.max_retries = 5
        args.retry_wait_base = 3
        args.retry_wait_max = 120

        # Set other attributes to None
        for attr in [
            "encoding",
            "max_chars",
            "remote",
            "epub",
            "batch",
            "max_workers",
            "temperature",
            "max_tokens",
            "model",
            "endpoint",
            "double_pass",
            "no_double_pass",
        ]:
            setattr(args, attr, None)

        preset_manager = Mock()
        preset_manager.active_preset = None

        result = self.handler.update_config_with_args(self.base_config, args, preset_manager)

        assert result["translation"]["connection_timeout"] == 60
        assert result["translation"]["response_timeout"] == 600
        assert result["translation"]["max_retries"] == 5
        assert result["translation"]["retry_wait_base"] == 3
        assert result["translation"]["retry_wait_max"] == 120

    def test_set_config_value_nested(self):
        """Test _set_config_value with nested paths."""
        config = {}

        # Test creating nested structure
        self.handler._set_config_value(config, "a.b.c", "value")
        assert config == {"a": {"b": {"c": "value"}}}

        # Test updating existing value
        self.handler._set_config_value(config, "a.b.d", "another")
        assert config == {"a": {"b": {"c": "value", "d": "another"}}}

        # Test single level
        self.handler._set_config_value(config, "x", 123)
        assert config["x"] == 123

    def test_update_config_missing_attributes(self):
        """Test handling of args object missing expected attributes."""
        args = Mock()
        # Only set a few attributes
        args.encoding = "utf-16"
        args.max_chars = 5000

        # Explicitly delete other attributes to simulate them not existing
        delattr(args, "remote")
        delattr(args, "epub")

        preset_manager = Mock()
        preset_manager.active_preset = None

        result = self.handler.update_config_with_args(self.base_config, args, preset_manager)

        # Should only update the attributes that exist
        assert result["text_processing"]["default_encoding"] == "utf-16"
        assert result["text_processing"]["max_chars_per_chunk"] == 5000
        # Other values should remain unchanged
        assert result["translation"]["service"] == "local"
        assert result["epub"]["enabled"] is False

    def test_update_config_all_args(self):
        """Test updating config with all possible arguments."""
        args = Mock()
        args.encoding = "gb18030"
        args.max_chars = 15000
        args.remote = True
        args.epub = True
        args.batch = True
        args.max_workers = 8
        args.connection_timeout = 45
        args.response_timeout = 450
        args.max_retries = 10
        args.retry_wait_base = 5
        args.retry_wait_max = 180
        args.temperature = 0.9
        args.max_tokens = 6000
        args.model = "claude-3"
        args.endpoint = "https://api.anthropic.com"
        args.double_pass = True
        args.no_double_pass = False

        preset_manager = Mock()
        preset_manager.active_preset = None

        result = self.handler.update_config_with_args(self.base_config, args, preset_manager)

        # Verify all updates
        assert result["text_processing"]["default_encoding"] == "gb18030"
        assert result["text_processing"]["max_chars_per_chunk"] == 15000
        assert result["translation"]["service"] == "remote"
        assert result["epub"]["enabled"] is True
        assert result["batch"]["enabled"] is True
        assert result["batch"]["max_workers"] == 8
        assert result["translation"]["connection_timeout"] == 45
        assert result["translation"]["response_timeout"] == 450
        assert result["translation"]["max_retries"] == 10
        assert result["translation"]["retry_wait_base"] == 5
        assert result["translation"]["retry_wait_max"] == 180
        assert result["translation"]["temperature"] == 0.9
        assert result["translation"]["max_tokens"] == 6000
        assert result["translation"]["model"] == "claude-3"
        assert result["translation"]["endpoint"] == "https://api.anthropic.com"
        assert result["translation"]["double_pass"] is True
