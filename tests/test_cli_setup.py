#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test suite for cli_setup module.
"""

import pytest
import argparse
import logging
import signal
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

import enchant_book_manager.cli_setup
from enchant_book_manager.cli_setup import (
    setup_configuration,
    setup_logging,
    setup_global_services,
    setup_signal_handler,
    check_colorama,
)


class TestSetupConfiguration:
    """Test the setup_configuration function."""

    @patch("enchant_book_manager.cli_setup.ConfigManager")
    @patch("enchant_book_manager.cli_setup.argparse.ArgumentParser")
    def test_setup_configuration_default(self, mock_parser_class, mock_config_manager_class):
        """Test setup with default configuration."""
        # Mock argument parser
        mock_parser = Mock()
        mock_parser_class.return_value = mock_parser
        mock_preset_args = Mock()
        mock_preset_args.config = "enchant_config.yml"
        mock_preset_args.preset = None
        mock_parser.parse_known_args.return_value = (mock_preset_args, [])

        # Mock ConfigManager
        mock_config_manager = Mock()
        mock_config = {"test": "config"}
        mock_config_manager.config = mock_config
        mock_config_manager_class.return_value = mock_config_manager

        config_manager, config = setup_configuration()

        # Verify ConfigManager was created with correct path
        mock_config_manager_class.assert_called_once_with(config_path=Path("enchant_config.yml"))

        # Verify no preset was applied
        mock_config_manager.apply_preset.assert_not_called()

        assert config_manager == mock_config_manager
        assert config == mock_config

    @patch("enchant_book_manager.cli_setup.ConfigManager")
    @patch("enchant_book_manager.cli_setup.argparse.ArgumentParser")
    def test_setup_configuration_with_preset(self, mock_parser_class, mock_config_manager_class):
        """Test setup with preset configuration."""
        # Mock argument parser
        mock_parser = Mock()
        mock_parser_class.return_value = mock_parser
        mock_preset_args = Mock()
        mock_preset_args.config = "custom_config.yml"
        mock_preset_args.preset = "REMOTE"
        mock_parser.parse_known_args.return_value = (mock_preset_args, [])

        # Mock ConfigManager
        mock_config_manager = Mock()
        mock_config = {"test": "config"}
        mock_config_manager.config = mock_config
        mock_config_manager.apply_preset.return_value = True
        mock_config_manager_class.return_value = mock_config_manager

        config_manager, config = setup_configuration()

        # Verify preset was applied
        mock_config_manager.apply_preset.assert_called_once_with("REMOTE")

        assert config_manager == mock_config_manager
        assert config == mock_config

    @patch("enchant_book_manager.cli_setup.sys.exit")
    @patch("enchant_book_manager.cli_setup.print")
    @patch("enchant_book_manager.cli_setup.ConfigManager")
    @patch("enchant_book_manager.cli_setup.argparse.ArgumentParser")
    def test_setup_configuration_preset_failure(self, mock_parser_class, mock_config_manager_class, mock_print, mock_exit):
        """Test setup when preset application fails."""
        # Mock argument parser
        mock_parser = Mock()
        mock_parser_class.return_value = mock_parser
        mock_preset_args = Mock()
        mock_preset_args.config = "config.yml"
        mock_preset_args.preset = "INVALID"
        mock_parser.parse_known_args.return_value = (mock_preset_args, [])

        # Mock ConfigManager
        mock_config_manager = Mock()
        mock_config_manager.apply_preset.return_value = False
        mock_config_manager_class.return_value = mock_config_manager

        setup_configuration()

        # Verify error was printed and exit called
        mock_print.assert_called_with("Failed to apply preset: INVALID")
        mock_exit.assert_called_with(1)

    @patch("enchant_book_manager.cli_setup.sys.exit")
    @patch("enchant_book_manager.cli_setup.print")
    @patch("enchant_book_manager.cli_setup.ConfigManager")
    @patch("enchant_book_manager.cli_setup.argparse.ArgumentParser")
    def test_setup_configuration_value_error(self, mock_parser_class, mock_config_manager_class, mock_print, mock_exit):
        """Test setup when ConfigManager raises ValueError."""
        # Mock argument parser
        mock_parser = Mock()
        mock_parser_class.return_value = mock_parser
        mock_preset_args = Mock()
        mock_preset_args.config = "bad_config.yml"
        mock_preset_args.preset = None
        mock_parser.parse_known_args.return_value = (mock_preset_args, [])

        # Mock ConfigManager to raise ValueError
        mock_config_manager_class.side_effect = ValueError("Invalid configuration")

        setup_configuration()

        # Verify error was printed and exit called
        assert mock_print.call_count == 2
        mock_print.assert_any_call("Configuration error: Invalid configuration")
        mock_print.assert_any_call("Please fix the configuration file or delete it to regenerate defaults.")
        mock_exit.assert_called_with(1)


class TestSetupLogging:
    """Test the setup_logging function."""

    @patch("enchant_book_manager.cli_setup.logging.basicConfig")
    @patch("enchant_book_manager.cli_setup.logging.getLogger")
    def test_setup_logging_basic(self, mock_get_logger, mock_basic_config):
        """Test basic logging setup without file logging."""
        config = {"logging": {"level": "INFO", "format": "%(asctime)s - %(levelname)s - %(message)s", "file_enabled": False, "file_path": "test.log"}}

        mock_logger = Mock(spec=logging.Logger)
        mock_get_logger.return_value = mock_logger

        logger = setup_logging(config)

        # Verify basic config was called
        mock_basic_config.assert_called_once_with(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

        # Verify logger was returned
        assert logger == mock_logger

        # Verify no file handler was added
        mock_logger.addHandler.assert_not_called()

    @patch("enchant_book_manager.cli_setup.logging.FileHandler")
    @patch("enchant_book_manager.cli_setup.logging.basicConfig")
    @patch("enchant_book_manager.cli_setup.logging.getLogger")
    def test_setup_logging_with_file(self, mock_get_logger, mock_basic_config, mock_file_handler_class):
        """Test logging setup with file logging enabled."""
        config = {"logging": {"level": "DEBUG", "format": "%(message)s", "file_enabled": True, "file_path": "app.log"}}

        mock_logger = Mock(spec=logging.Logger)
        mock_get_logger.return_value = mock_logger

        mock_file_handler = Mock()
        mock_file_handler_class.return_value = mock_file_handler

        logger = setup_logging(config)

        # Verify file handler was created and configured
        mock_file_handler_class.assert_called_once_with("app.log")
        mock_file_handler.setLevel.assert_called_once_with(logging.DEBUG)
        mock_file_handler.setFormatter.assert_called_once()

        # Verify handler was added to logger
        mock_logger.addHandler.assert_called_once_with(mock_file_handler)

    @patch("enchant_book_manager.cli_setup.logging.FileHandler")
    @patch("enchant_book_manager.cli_setup.logging.basicConfig")
    @patch("enchant_book_manager.cli_setup.logging.getLogger")
    def test_setup_logging_file_error(self, mock_get_logger, mock_basic_config, mock_file_handler_class):
        """Test logging setup when file handler fails."""
        config = {"logging": {"level": "INFO", "format": "%(message)s", "file_enabled": True, "file_path": "/invalid/path/test.log"}}

        mock_logger = Mock(spec=logging.Logger)
        mock_get_logger.return_value = mock_logger

        # Make FileHandler raise exception
        mock_file_handler_class.side_effect = PermissionError("Permission denied")

        logger = setup_logging(config)

        # Should log error but continue
        mock_logger.error.assert_called_once()
        assert "Failed to set up file logging" in mock_logger.error.call_args[0][0]

        # Logger should still be returned
        assert logger == mock_logger

    def test_setup_logging_invalid_level(self):
        """Test logging setup with invalid log level."""
        config = {"logging": {"level": "INVALID_LEVEL", "format": "%(message)s", "file_enabled": False, "file_path": "test.log"}}

        with patch("enchant_book_manager.cli_setup.logging.basicConfig") as mock_basic_config:
            with patch("enchant_book_manager.cli_setup.logging.getLogger") as mock_get_logger:
                mock_logger = Mock()
                mock_get_logger.return_value = mock_logger

                logger = setup_logging(config)

                # Should fall back to INFO level
                mock_basic_config.assert_called_once()
                assert mock_basic_config.call_args[1]["level"] == logging.INFO


class TestSetupGlobalServices:
    """Test the setup_global_services function."""

    @patch("enchant_book_manager.cli_setup.ICloudSync")
    def test_setup_global_services_enabled(self, mock_icloud_sync_class):
        """Test global services setup with iCloud enabled."""
        config = {"icloud": {"enabled": True}}

        mock_icloud = Mock()
        mock_icloud_sync_class.return_value = mock_icloud

        # Clear global variable
        enchant_book_manager.cli_setup.icloud_sync = None

        setup_global_services(config)

        # Verify ICloudSync was created with correct parameter
        mock_icloud_sync_class.assert_called_once_with(enabled=True)

        # Verify global variable was set
        assert enchant_book_manager.cli_setup.icloud_sync == mock_icloud

    @patch("enchant_book_manager.cli_setup.ICloudSync")
    def test_setup_global_services_disabled(self, mock_icloud_sync_class):
        """Test global services setup with iCloud disabled."""
        config = {"icloud": {"enabled": False}}

        mock_icloud = Mock()
        mock_icloud_sync_class.return_value = mock_icloud

        setup_global_services(config)

        # Verify ICloudSync was created with correct parameter
        mock_icloud_sync_class.assert_called_once_with(enabled=False)


class TestSetupSignalHandler:
    """Test the setup_signal_handler function."""

    @patch("enchant_book_manager.cli_setup.signal.signal")
    def test_setup_signal_handler(self, mock_signal):
        """Test signal handler setup."""
        logger = Mock(spec=logging.Logger)

        setup_signal_handler(logger)

        # Verify signal handler was registered
        mock_signal.assert_called_once()
        assert mock_signal.call_args[0][0] == signal.SIGINT
        assert callable(mock_signal.call_args[0][1])

    @patch("enchant_book_manager.cli_setup.sys.exit")
    @patch("enchant_book_manager.cli_setup.signal.signal")
    def test_signal_handler_execution(self, mock_signal, mock_exit):
        """Test that signal handler works correctly when called."""
        logger = Mock(spec=logging.Logger)

        setup_signal_handler(logger)

        # Get the handler function
        handler_func = mock_signal.call_args[0][1]

        # Call the handler
        handler_func(signal.SIGINT, None)

        # Verify it logged and exited
        logger.info.assert_called_once_with("Interrupt received. Exiting gracefully.")
        mock_exit.assert_called_once_with(0)


class TestCheckColorama:
    """Test the check_colorama function."""

    @patch("builtins.__import__")
    def test_check_colorama_available(self, mock_import):
        """Test when colorama is available."""
        logger = Mock(spec=logging.Logger)

        # Mock successful import
        mock_import.return_value = Mock()

        check_colorama(logger)

        # Should not log warning
        logger.warning.assert_not_called()

    @patch("builtins.__import__")
    def test_check_colorama_not_available(self, mock_import):
        """Test when colorama is not available."""
        logger = Mock(spec=logging.Logger)

        # Mock import failure
        mock_import.side_effect = ImportError("No module named 'colorama'")

        check_colorama(logger)

        # Should log warning
        logger.warning.assert_called_once_with("colorama package not installed. Colored text may not work properly.")


class TestIntegration:
    """Test integration scenarios."""

    @patch("enchant_book_manager.cli_setup.ICloudSync")
    @patch("enchant_book_manager.cli_setup.logging")
    @patch("enchant_book_manager.cli_setup.ConfigManager")
    @patch("enchant_book_manager.cli_setup.argparse.ArgumentParser")
    def test_full_setup_flow(self, mock_parser_class, mock_config_manager_class, mock_logging, mock_icloud_sync_class):
        """Test complete setup flow."""
        # Mock argument parser
        mock_parser = Mock()
        mock_parser_class.return_value = mock_parser
        mock_preset_args = Mock()
        mock_preset_args.config = "config.yml"
        mock_preset_args.preset = None
        mock_parser.parse_known_args.return_value = (mock_preset_args, [])

        # Mock ConfigManager
        mock_config_manager = Mock()
        mock_config = {"logging": {"level": "INFO", "format": "%(message)s", "file_enabled": False, "file_path": "app.log"}, "icloud": {"enabled": True}}
        mock_config_manager.config = mock_config
        mock_config_manager_class.return_value = mock_config_manager

        # Mock logger
        mock_logger = Mock(spec=logging.Logger)
        mock_logging.getLogger.return_value = mock_logger

        # Run full setup
        config_manager, config = setup_configuration()
        logger = setup_logging(config)
        setup_global_services(config)
        setup_signal_handler(logger)
        check_colorama(logger)

        # Verify all components were set up
        assert config_manager == mock_config_manager
        assert logger == mock_logger
        assert enchant_book_manager.cli_setup.icloud_sync is not None
