#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test suite for config_manager module.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, mock_open
import logging
import sys
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent))

from enchant_book_manager.config_manager import ConfigManager


class TestConfigManager:
    """Test the ConfigManager class."""

    @patch("enchant_book_manager.config_manager.ConfigLoader")
    @patch("enchant_book_manager.config_manager.ConfigValidator")
    @patch("enchant_book_manager.config_manager.PresetManager")
    @patch("enchant_book_manager.config_manager.ConfigArgsHandler")
    def test_initialization(self, mock_args_handler, mock_preset_mgr, mock_validator, mock_loader):
        """Test ConfigManager initialization."""
        # Setup mocks
        mock_loader_instance = MagicMock()
        mock_loader_instance.load_config.return_value = {"test": "config"}
        mock_loader_instance.get_default_config.return_value = {"test": "default"}
        mock_loader_instance.get_config_lines.return_value = []
        mock_loader_instance.merge_with_defaults.return_value = {"test": "merged"}
        mock_loader.return_value = mock_loader_instance

        mock_validator_instance = MagicMock()
        mock_validator_instance.validate_config_first_error.return_value = None
        mock_validator.return_value = mock_validator_instance

        mock_preset_mgr_instance = MagicMock()
        mock_preset_mgr_instance.active_preset = "LOCAL"
        mock_preset_mgr.return_value = mock_preset_mgr_instance

        # Create ConfigManager
        config_path = Path("test_config.yml")
        logger = Mock(spec=logging.Logger)
        manager = ConfigManager(config_path, logger)

        # Verify initialization
        assert manager.config_path == config_path
        assert manager.logger == logger
        assert manager.config == {"test": "merged"}
        assert manager.active_preset == "LOCAL"

        # Verify component initialization
        mock_loader.assert_called_once_with(config_path, logger)
        mock_validator.assert_called_once_with(logger)
        mock_preset_mgr.assert_called_once_with(logger)

    @patch("enchant_book_manager.config_manager.ConfigLoader")
    @patch("enchant_book_manager.config_manager.ConfigValidator")
    @patch("enchant_book_manager.config_manager.PresetManager")
    def test_default_config_path(self, mock_preset_mgr, mock_validator, mock_loader):
        """Test ConfigManager with default config path."""
        # Setup minimal mocks
        mock_loader_instance = MagicMock()
        mock_loader_instance.load_config.return_value = {}
        mock_loader_instance.get_default_config.return_value = {}
        mock_loader_instance.get_config_lines.return_value = []
        mock_loader_instance.merge_with_defaults.return_value = {}
        mock_loader.return_value = mock_loader_instance

        mock_validator.return_value.validate_config_first_error.return_value = None

        manager = ConfigManager()

        assert manager.config_path == Path("enchant_config.yml")
        assert isinstance(manager.logger, logging.Logger)

    def test_get_config_value(self):
        """Test getting configuration values with dot notation."""
        manager = ConfigManager.__new__(ConfigManager)
        manager.config = {"translation": {"local": {"endpoint": "http://localhost:1234", "model": "test-model"}, "remote": {"api_key": "test-key"}}, "simple_value": "test"}

        # Test nested access
        assert manager.get("translation.local.endpoint") == "http://localhost:1234"
        assert manager.get("translation.local.model") == "test-model"
        assert manager.get("translation.remote.api_key") == "test-key"

        # Test simple value
        assert manager.get("simple_value") == "test"

        # Test non-existent keys
        assert manager.get("non.existent.key") is None
        assert manager.get("non.existent.key", "default") == "default"

        # Test partial paths
        local_config = manager.get("translation.local")
        assert isinstance(local_config, dict)
        assert local_config["endpoint"] == "http://localhost:1234"

    @patch("enchant_book_manager.config_manager.ConfigLoader")
    @patch("enchant_book_manager.config_manager.ConfigValidator")
    @patch("enchant_book_manager.config_manager.PresetManager")
    @patch("builtins.input", return_value="y")
    @patch("sys.exit")
    def test_restore_missing_preset(self, mock_exit, mock_input, mock_preset_mgr, mock_validator, mock_loader):
        """Test restoring missing required preset."""
        # Setup mocks
        mock_loader_instance = MagicMock()
        mock_loader_instance.load_config.return_value = {"presets": {}}
        mock_loader_instance.get_default_config.return_value = {"presets": {"LOCAL": {"api_type": "local"}, "REMOTE": {"api_type": "remote"}}}
        mock_loader_instance.get_config_lines.return_value = []
        mock_loader_instance.merge_with_defaults.return_value = {"test": "config"}
        mock_loader.return_value = mock_loader_instance

        # First validation fails, second succeeds after restoration
        mock_validator_instance = MagicMock()
        mock_validator_instance.validate_config_first_error.side_effect = [
            {"type": "missing_required_preset", "preset": "LOCAL", "can_restore": True},
            None,  # Success after restoration
        ]
        mock_validator.return_value = mock_validator_instance

        manager = ConfigManager()

        # Verify restoration happened
        mock_input.assert_called_once()
        assert mock_validator_instance.validate_config_first_error.call_count == 2
        mock_exit.assert_not_called()

    @patch("enchant_book_manager.config_manager.ConfigLoader")
    @patch("enchant_book_manager.config_manager.ConfigValidator")
    @patch("enchant_book_manager.config_manager.PresetManager")
    @patch("sys.exit")
    def test_validation_error_exit(self, mock_exit, mock_preset_mgr, mock_validator, mock_loader):
        """Test that validation errors cause exit."""
        # Setup mocks
        mock_loader_instance = MagicMock()
        mock_loader_instance.load_config.return_value = {"invalid": "config"}
        mock_loader_instance.get_default_config.return_value = {}
        mock_loader_instance.get_config_lines.return_value = []
        mock_loader.return_value = mock_loader_instance

        mock_validator_instance = MagicMock()
        mock_validator_instance.validate_config_first_error.return_value = {"type": "invalid_value", "key": "test.key", "message": "Invalid value"}
        mock_validator.return_value = mock_validator_instance

        # Create manager - should exit due to validation error
        ConfigManager()

        mock_validator_instance.report_single_error.assert_called_once()
        mock_exit.assert_called_once_with(1)

    def test_apply_preset(self):
        """Test applying a preset configuration."""
        manager = ConfigManager.__new__(ConfigManager)
        manager.config = {"presets": {"TEST": {"key": "value"}}}
        manager.logger = Mock()

        mock_preset_mgr = MagicMock()
        mock_preset_mgr.apply_preset.return_value = True
        mock_preset_mgr.active_preset = "TEST"
        manager.preset_manager = mock_preset_mgr

        result = manager.apply_preset("TEST")

        assert result is True
        assert manager.active_preset == "TEST"
        mock_preset_mgr.apply_preset.assert_called_once_with("TEST", manager.config)

    def test_get_preset_value(self):
        """Test getting value from active preset."""
        manager = ConfigManager.__new__(ConfigManager)
        manager.config = {"presets": {"LOCAL": {"model": "local-model", "temperature": 0.7}}}

        mock_preset_mgr = MagicMock()
        mock_preset_mgr.get_preset_value.return_value = "local-model"
        manager.preset_manager = mock_preset_mgr

        value = manager.get_preset_value("model", default="default-model")

        assert value == "local-model"
        mock_preset_mgr.get_preset_value.assert_called_once_with("model", manager.config, "default-model")

    def test_update_with_args(self):
        """Test updating configuration from command line arguments."""
        manager = ConfigManager.__new__(ConfigManager)
        manager.config = {"test": "original"}
        manager.logger = Mock()

        mock_args_handler = MagicMock()
        mock_args_handler.update_config_with_args.return_value = {"test": "updated"}
        manager.args_handler = mock_args_handler

        mock_preset_mgr = MagicMock()
        manager.preset_manager = mock_preset_mgr

        args = MagicMock()
        args.preset = None
        result = manager.update_with_args(args)

        assert result == {"test": "updated"}
        mock_args_handler.update_config_with_args.assert_called_once_with(manager.config, args, mock_preset_mgr)

    def test_get_api_key(self):
        """Test getting API key from config or environment."""
        # Clear any existing environment variables
        with patch.dict("os.environ", {}, clear=True):
            manager = ConfigManager.__new__(ConfigManager)
            manager.config = {"translation": {"remote": {"api_key": "remote-key"}}, "novel_renaming": {"openai": {"api_key": "openai-key"}}}

            # Test getting from config
            assert manager.get_api_key("openrouter") == "remote-key"
            assert manager.get_api_key("openai") == "openai-key"
            assert manager.get_api_key("unknown") is None

        # Test getting from environment
        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "env-key"}, clear=True):
            assert manager.get_api_key("openrouter") == "env-key"  # Env takes precedence

    def test_get_available_presets(self):
        """Test getting list of available presets."""
        manager = ConfigManager.__new__(ConfigManager)
        manager.config = {"presets": {"LOCAL": {}, "REMOTE": {}, "CUSTOM": {}}}

        mock_preset_mgr = MagicMock()
        mock_preset_mgr.get_available_presets.return_value = ["LOCAL", "REMOTE", "CUSTOM"]
        manager.preset_manager = mock_preset_mgr

        presets = manager.get_available_presets()

        assert set(presets) == {"LOCAL", "REMOTE", "CUSTOM"}
        mock_preset_mgr.get_available_presets.assert_called_once_with(manager.config)
