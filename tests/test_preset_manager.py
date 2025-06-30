#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test suite for preset_manager module.
"""

import pytest
import logging
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from enchant_book_manager.preset_manager import PresetManager


class TestPresetManager:
    """Test the PresetManager class."""

    def test_initialization(self):
        """Test PresetManager initialization."""
        # With logger
        logger = Mock(spec=logging.Logger)
        manager = PresetManager(logger)
        assert manager.logger == logger
        assert manager.active_preset is None

        # Without logger
        manager = PresetManager()
        assert isinstance(manager.logger, logging.Logger)
        assert manager.active_preset is None

    def test_apply_preset_success(self):
        """Test successfully applying a preset."""
        logger = Mock()
        manager = PresetManager(logger)
        config = {
            "presets": {
                "LOCAL": {"endpoint": "http://localhost:1234"},
                "REMOTE": {"endpoint": "https://api.example.com"},
            }
        }

        result = manager.apply_preset("LOCAL", config)

        assert result is True
        assert manager.active_preset == "LOCAL"
        logger.info.assert_called_once_with("Applied preset: LOCAL")

    def test_apply_preset_invalid_name(self):
        """Test applying preset with invalid name."""
        logger = Mock()
        manager = PresetManager(logger)
        config = {"presets": {}}

        # Invalid name with special characters
        result = manager.apply_preset("invalid-name!", config)

        assert result is False
        assert manager.active_preset is None
        logger.error.assert_called_once()
        assert "Invalid preset name" in logger.error.call_args[0][0]

    @patch("sys.exit")
    def test_apply_preset_not_found(self, mock_exit):
        """Test applying non-existent preset."""
        logger = Mock()
        manager = PresetManager(logger)
        config = {"presets": {"LOCAL": {}, "REMOTE": {}}}

        manager.apply_preset("NONEXISTENT", config)

        logger.error.assert_called_once()
        error_msg = logger.error.call_args[0][0]
        assert "Preset 'NONEXISTENT' not found" in error_msg
        assert "Available presets: LOCAL, REMOTE" in error_msg
        mock_exit.assert_called_once_with(1)

    def test_apply_preset_valid_names(self):
        """Test various valid preset names."""
        manager = PresetManager()
        config = {
            "presets": {
                "LOCAL": {},
                "REMOTE_API": {},
                "Custom123": {},
                "test_preset": {},
                "_private": {},
            }
        }

        # All these should be valid
        for preset_name in [
            "LOCAL",
            "REMOTE_API",
            "Custom123",
            "test_preset",
            "_private",
        ]:
            result = manager.apply_preset(preset_name, config)
            assert result is True
            assert manager.active_preset == preset_name

    def test_get_preset_value_with_active_preset(self):
        """Test getting value from active preset."""
        manager = PresetManager()
        manager.active_preset = "LOCAL"
        config = {
            "presets": {
                "LOCAL": {
                    "endpoint": "http://localhost:1234",
                    "model": "local-model",
                    "temperature": 0.7,
                }
            }
        }

        # Get existing value
        assert manager.get_preset_value("endpoint", config) == "http://localhost:1234"
        assert manager.get_preset_value("model", config) == "local-model"
        assert manager.get_preset_value("temperature", config) == 0.7

        # Get non-existent value with default
        assert manager.get_preset_value("missing", config, "default") == "default"

    def test_get_preset_value_no_active_preset(self):
        """Test getting value when no preset is active."""
        manager = PresetManager()
        config = {"presets": {"LOCAL": {"endpoint": "http://localhost"}}}

        # Should return default
        assert manager.get_preset_value("endpoint", config, "default") == "default"

    def test_get_preset_value_no_presets_in_config(self):
        """Test getting value when config has no presets."""
        manager = PresetManager()
        manager.active_preset = "LOCAL"
        config = {}  # No presets section

        assert manager.get_preset_value("key", config, "default") == "default"

    def test_get_available_presets(self):
        """Test getting list of available presets."""
        manager = PresetManager()
        config = {
            "presets": {
                "LOCAL": {},
                "REMOTE": {},
                "CUSTOM": {},
            }
        }

        presets = manager.get_available_presets(config)

        assert len(presets) == 3
        assert "LOCAL" in presets
        assert "REMOTE" in presets
        assert "CUSTOM" in presets

    def test_get_available_presets_empty(self):
        """Test getting presets when none exist."""
        manager = PresetManager()

        # No presets section
        assert manager.get_available_presets({}) == []

        # Empty presets section
        assert manager.get_available_presets({"presets": {}}) == []

    def test_update_config_with_preset_basic(self):
        """Test updating config with basic preset values."""
        manager = PresetManager()
        manager.active_preset = "LOCAL"

        config = {
            "translation": {
                "local": {},
                "remote": {},
            }
        }

        preset_values = {
            "model": "test-model",
            "endpoint": "http://localhost:8080",
            "temperature": 0.5,
            "max_tokens": 1000,
        }

        updated = manager.update_config_with_preset(config, preset_values)

        # Check values were set
        assert updated["translation"]["local"]["model"] == "test-model"
        assert updated["translation"]["local"]["endpoint"] == "http://localhost:8080"
        assert updated["translation"]["temperature"] == 0.5
        assert updated["translation"]["max_tokens"] == 1000

        # Original config should not be modified
        assert "model" not in config["translation"]["local"]

    def test_update_config_with_preset_remote(self):
        """Test updating config for REMOTE preset."""
        manager = PresetManager()
        manager.active_preset = "REMOTE"

        config = {"translation": {}}
        preset_values = {
            "model": "gpt-4",
            "endpoint": "https://api.openai.com",
            "response_timeout": 30,
            "connection_timeout": 10,
        }

        updated = manager.update_config_with_preset(config, preset_values)

        assert updated["translation"]["remote"]["model"] == "gpt-4"
        assert updated["translation"]["remote"]["endpoint"] == "https://api.openai.com"
        assert updated["translation"]["remote"]["timeout"] == 30
        assert updated["translation"]["remote"]["connection_timeout"] == 10

    def test_update_config_with_preset_text_processing(self):
        """Test updating text processing config."""
        manager = PresetManager()
        config = {}
        preset_values = {"max_chars_per_chunk": 5000}

        updated = manager.update_config_with_preset(config, preset_values)

        assert updated["text_processing"]["max_chars_per_chunk"] == 5000

    def test_update_config_with_preset_retry_settings(self):
        """Test updating retry-related settings."""
        manager = PresetManager()
        config = {}
        preset_values = {
            "max_retries": 5,
            "retry_wait_base": 2.0,
            "retry_wait_max": 60.0,
            "double_pass": True,
        }

        updated = manager.update_config_with_preset(config, preset_values)

        assert updated["translation"]["max_retries"] == 5
        assert updated["translation"]["retry_wait_base"] == 2.0
        assert updated["translation"]["retry_wait_max"] == 60.0
        assert updated["translation"]["double_pass"] is True

    def test_set_config_value_simple(self):
        """Test setting simple config value."""
        manager = PresetManager()
        config = {}

        manager._set_config_value(config, "key", "value")
        assert config["key"] == "value"

    def test_set_config_value_nested(self):
        """Test setting nested config value."""
        manager = PresetManager()
        config = {}

        manager._set_config_value(config, "level1.level2.key", "value")
        assert config["level1"]["level2"]["key"] == "value"

    def test_set_config_value_existing_path(self):
        """Test setting value in existing path."""
        manager = PresetManager()
        config = {
            "level1": {
                "level2": {
                    "existing": "old",
                }
            }
        }

        manager._set_config_value(config, "level1.level2.new", "value")

        assert config["level1"]["level2"]["existing"] == "old"
        assert config["level1"]["level2"]["new"] == "value"

    def test_get_active_preset(self):
        """Test getting active preset."""
        manager = PresetManager()

        # Initially None
        assert manager.get_active_preset() is None

        # After setting
        manager.active_preset = "LOCAL"
        assert manager.get_active_preset() == "LOCAL"

    def test_update_config_comprehensive(self):
        """Test comprehensive config update with all preset values."""
        manager = PresetManager()
        manager.active_preset = "LOCAL"

        config = {}
        preset_values = {
            # Model settings
            "model": "local-llm",
            "endpoint": "http://localhost:1234",
            "temperature": 0.7,
            "max_tokens": 2000,
            # Timeouts
            "connection_timeout": 5,
            "response_timeout": 60,
            # Retry settings
            "max_retries": 3,
            "retry_wait_base": 1.0,
            "retry_wait_max": 30.0,
            # Processing
            "double_pass": False,
            "max_chars_per_chunk": 4000,
            # Should be ignored (not in allowed keys)
            "unknown_key": "ignored",
        }

        updated = manager.update_config_with_preset(config, preset_values)

        # Verify all values are set correctly
        assert updated["translation"]["local"]["model"] == "local-llm"
        assert updated["translation"]["local"]["endpoint"] == "http://localhost:1234"
        assert updated["translation"]["local"]["timeout"] == 60
        assert updated["translation"]["local"]["connection_timeout"] == 5
        assert updated["translation"]["temperature"] == 0.7
        assert updated["translation"]["max_tokens"] == 2000
        assert updated["translation"]["max_retries"] == 3
        assert updated["translation"]["retry_wait_base"] == 1.0
        assert updated["translation"]["retry_wait_max"] == 30.0
        assert updated["translation"]["double_pass"] is False
        assert updated["text_processing"]["max_chars_per_chunk"] == 4000

        # Unknown key should not be added
        assert "unknown_key" not in updated
        assert "unknown_key" not in updated["translation"]

    def test_multiple_preset_applications(self):
        """Test applying multiple presets in sequence."""
        manager = PresetManager()
        config = {
            "presets": {
                "LOCAL": {"model": "local"},
                "REMOTE": {"model": "remote"},
                "CUSTOM": {"model": "custom"},
            }
        }

        # Apply different presets
        assert manager.apply_preset("LOCAL", config) is True
        assert manager.active_preset == "LOCAL"
        assert manager.get_preset_value("model", config) == "local"

        assert manager.apply_preset("REMOTE", config) is True
        assert manager.active_preset == "REMOTE"
        assert manager.get_preset_value("model", config) == "remote"

        assert manager.apply_preset("CUSTOM", config) is True
        assert manager.active_preset == "CUSTOM"
        assert manager.get_preset_value("model", config) == "custom"
