#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test suite for config_loader module.
"""

import pytest
import yaml
import logging
from pathlib import Path
from unittest.mock import Mock, patch, mock_open, MagicMock
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from enchant_book_manager.config_loader import ConfigLoader


class TestConfigLoader:
    """Test the ConfigLoader class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config_path = Path("/test/config.yml")
        self.logger = Mock(spec=logging.Logger)
        self.loader = ConfigLoader(self.config_path, self.logger)

    def test_init(self):
        """Test ConfigLoader initialization."""
        # Test with logger
        loader = ConfigLoader(self.config_path, self.logger)
        assert loader.config_path == self.config_path
        assert loader.logger == self.logger
        assert loader._config_lines == []
        assert loader.error_reporter is not None

        # Test without logger
        with patch("enchant_book_manager.config_loader.logging.getLogger") as mock_get_logger:
            mock_default_logger = Mock()
            mock_get_logger.return_value = mock_default_logger
            loader = ConfigLoader(self.config_path)
            assert loader.logger == mock_default_logger
            mock_get_logger.assert_called_once_with("enchant_book_manager.config_loader")

    @patch("enchant_book_manager.config_loader.Path.exists")
    @patch("enchant_book_manager.config_loader.load_safe_yaml")
    @patch("builtins.open", new_callable=mock_open, read_data="key: value\nother: 123")
    def test_load_config_existing_file(self, mock_file, mock_load_yaml, mock_exists):
        """Test loading configuration from existing file."""
        mock_exists.return_value = True
        mock_load_yaml.return_value = {"key": "value", "other": 123}

        result = self.loader.load_config()

        assert result == {"key": "value", "other": 123}
        assert self.loader._config_lines == ["key: value", "other: 123"]
        mock_load_yaml.assert_called_once_with(self.config_path)

    @patch("enchant_book_manager.config_loader.Path.exists")
    @patch("enchant_book_manager.config_loader.load_safe_yaml")
    @patch("builtins.open", new_callable=mock_open, read_data="default: config")
    def test_load_config_create_default(self, mock_file, mock_load_yaml, mock_exists):
        """Test creating default configuration when file doesn't exist."""
        # First call returns False (file doesn't exist), second returns True (after creation)
        mock_exists.side_effect = [False, True]
        mock_load_yaml.return_value = {"default": "config"}

        with patch.object(self.loader, "_create_default_config") as mock_create:
            result = self.loader.load_config()

            assert result == {"default": "config"}
            mock_create.assert_called_once()
            self.logger.info.assert_any_call(f"Configuration file not found. Creating default at: {self.config_path}")

    @patch("enchant_book_manager.config_loader.Path.exists")
    @patch("enchant_book_manager.config_loader.load_safe_yaml")
    @patch("builtins.open", new_callable=mock_open, read_data="")
    def test_load_config_empty_file(self, mock_file, mock_load_yaml, mock_exists):
        """Test loading empty configuration file."""
        mock_exists.return_value = True
        mock_load_yaml.return_value = None

        with patch.object(self.loader, "get_default_config") as mock_get_default:
            mock_get_default.return_value = {"default": "config"}

            result = self.loader.load_config()

            assert result == {"default": "config"}
            self.logger.warning.assert_called_once_with("Configuration file is empty. Using defaults.")

    @patch("enchant_book_manager.config_loader.Path.exists")
    @patch("enchant_book_manager.config_loader.load_safe_yaml")
    @patch("sys.exit")
    def test_load_config_yaml_error(self, mock_exit, mock_load_yaml, mock_exists):
        """Test handling YAML parsing errors."""
        mock_exists.return_value = True
        yaml_error = yaml.YAMLError("Invalid YAML")
        mock_load_yaml.side_effect = yaml_error

        with patch("builtins.open", new_callable=mock_open, read_data="bad: yaml:"):
            with patch.object(self.loader.error_reporter, "report_yaml_error") as mock_report:
                self.loader.load_config()

                mock_report.assert_called_once_with(yaml_error, self.config_path)
                mock_exit.assert_called_once_with(1)

    @patch("enchant_book_manager.config_loader.Path.exists")
    @patch("builtins.open")
    def test_load_config_generic_error(self, mock_file, mock_exists):
        """Test handling generic errors during loading."""
        mock_exists.return_value = True
        mock_file.side_effect = PermissionError("Permission denied")

        with pytest.raises(PermissionError):
            self.loader.load_config()

        self.logger.error.assert_called_once()
        assert "Error loading configuration: Permission denied" in self.logger.error.call_args[0][0]

    @patch("builtins.open", new_callable=mock_open)
    def test_create_default_config_success(self, mock_file):
        """Test successful creation of default configuration."""
        self.loader._create_default_config()

        # Verify file was opened for writing
        mock_file.assert_called_once_with(self.config_path, "w", encoding="utf-8")

        # Verify default template was written
        handle = mock_file()
        from enchant_book_manager.config_schema import DEFAULT_CONFIG_TEMPLATE

        handle.write.assert_called_once_with(DEFAULT_CONFIG_TEMPLATE)

        self.logger.info.assert_called_once_with("Default configuration file created successfully.")

    @patch("builtins.open")
    def test_create_default_config_error(self, mock_file):
        """Test error handling during default config creation."""
        mock_file.side_effect = OSError("Disk full")

        with pytest.raises(OSError):
            self.loader._create_default_config()

        self.logger.error.assert_called_once()
        assert "Failed to create configuration file: Disk full" in self.logger.error.call_args[0][0]

    @patch("enchant_book_manager.config_loader.yaml.safe_load")
    def test_get_default_config(self, mock_yaml_load):
        """Test getting default configuration as dictionary."""
        mock_yaml_load.return_value = {"default": "config", "nested": {"key": "value"}}

        result = self.loader.get_default_config()

        assert result == {"default": "config", "nested": {"key": "value"}}
        from enchant_book_manager.config_schema import DEFAULT_CONFIG_TEMPLATE

        mock_yaml_load.assert_called_once_with(DEFAULT_CONFIG_TEMPLATE)

    @patch("enchant_book_manager.config_loader.yaml.safe_load")
    def test_get_default_config_non_dict(self, mock_yaml_load):
        """Test getting default config when YAML doesn't return dict."""
        mock_yaml_load.return_value = "not a dict"

        result = self.loader.get_default_config()

        assert result == {}

    @patch("enchant_book_manager.config_loader.merge_yaml_configs")
    def test_merge_with_defaults(self, mock_merge):
        """Test merging user config with defaults."""
        user_config = {"user": "config"}
        mock_merge.return_value = {"merged": "config"}

        with patch.object(self.loader, "get_default_config") as mock_get_default:
            mock_get_default.return_value = {"default": "config"}

            result = self.loader.merge_with_defaults(user_config)

            assert result == {"merged": "config"}
            mock_get_default.assert_called_once()
            mock_merge.assert_called_once_with({"default": "config"}, {"user": "config"})

    def test_get_config_lines(self):
        """Test getting configuration lines."""
        self.loader._config_lines = ["line1", "line2", "line3"]

        result = self.loader.get_config_lines()

        assert result == ["line1", "line2", "line3"]

    @patch("enchant_book_manager.config_loader.find_line_number")
    def test_find_line_number(self, mock_find):
        """Test finding line number of configuration key."""
        self.loader._config_lines = ["key: value", "nested:", "  subkey: value"]
        mock_find.return_value = 3

        result = self.loader.find_line_number("nested.subkey")

        assert result == 3
        mock_find.assert_called_once_with("nested.subkey", self.loader._config_lines)

    def test_get_config_lines_empty(self):
        """Test getting config lines when not loaded yet."""
        assert self.loader.get_config_lines() == []

    @patch("enchant_book_manager.config_loader.Path.exists")
    @patch("enchant_book_manager.config_loader.load_safe_yaml")
    @patch("builtins.open", new_callable=mock_open, read_data="line1\nline2\nline3")
    def test_config_lines_storage(self, mock_file, mock_load_yaml, mock_exists):
        """Test that config lines are properly stored after loading."""
        mock_exists.return_value = True
        mock_load_yaml.return_value = {"test": "config"}

        self.loader.load_config()

        assert self.loader._config_lines == ["line1", "line2", "line3"]

    @patch("enchant_book_manager.config_loader.Path.exists")
    @patch("enchant_book_manager.config_loader.load_safe_yaml")
    def test_load_config_with_complex_yaml(self, mock_load_yaml, mock_exists):
        """Test loading complex YAML configuration."""
        mock_exists.return_value = True
        complex_config = {
            "translation": {
                "local": {"endpoint": "http://localhost"},
                "remote": {"endpoint": "https://api.example.com"},
                "temperature": 0.7,
            },
            "text_processing": {"max_chars_per_chunk": 10000, "encoding": "utf-8"},
        }
        mock_load_yaml.return_value = complex_config

        with patch("builtins.open", new_callable=mock_open, read_data="complex: yaml"):
            result = self.loader.load_config()

            assert result == complex_config
