#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test suite for cli_translator module.
"""

import pytest
import logging
import signal
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

import enchant_book_manager.cli_translator
from enchant_book_manager.cli_translator import (
    translate_novel,
    save_translated_book,
    APP_NAME,
    APP_VERSION,
    MIN_PYTHON_VERSION_REQUIRED,
)


class TestGlobalVariables:
    """Test module-level constants and variables."""

    def test_app_constants(self):
        """Test application constants."""
        assert APP_NAME == "cli-translator"
        assert APP_VERSION == "0.1.0"
        assert MIN_PYTHON_VERSION_REQUIRED == "3.8"

    def test_global_variables_initial_state(self):
        """Test that global variables are initially None."""
        # Reset globals
        enchant_book_manager.cli_translator.translator = None
        enchant_book_manager.cli_translator.tolog = None
        enchant_book_manager.cli_translator.icloud_sync = None
        enchant_book_manager.cli_translator._module_config = None

        assert enchant_book_manager.cli_translator.translator is None
        assert enchant_book_manager.cli_translator.tolog is None
        assert enchant_book_manager.cli_translator.icloud_sync is None
        assert enchant_book_manager.cli_translator._module_config is None


class TestSaveTranslatedBook:
    """Test the save_translated_book wrapper function."""

    def test_save_translated_book_no_translator(self):
        """Test save_translated_book when translator is not initialized."""
        # Reset translator
        enchant_book_manager.cli_translator.translator = None

        with pytest.raises(RuntimeError, match="Translator not initialized"):
            save_translated_book("book_id")

    @patch("enchant_book_manager.cli_translator._save_translated_book_impl")
    def test_save_translated_book_with_translator(self, mock_save_impl):
        """Test save_translated_book with translator initialized."""
        # Setup globals
        mock_translator = Mock()
        mock_logger = Mock(spec=logging.Logger)
        mock_config = {"test": "config"}

        enchant_book_manager.cli_translator.translator = mock_translator
        enchant_book_manager.cli_translator.tolog = mock_logger
        enchant_book_manager.cli_translator._module_config = mock_config

        # Call function
        save_translated_book("book123", resume=True, create_epub=True)

        # Verify implementation was called correctly
        mock_save_impl.assert_called_once_with(
            book_id="book123",
            translator=mock_translator,
            resume=True,
            create_epub=True,
            logger=mock_logger,
            module_config=mock_config,
        )


class TestTranslateNovel:
    """Test the main translate_novel function."""

    def setup_method(self):
        """Reset global variables before each test."""
        enchant_book_manager.cli_translator.translator = None
        enchant_book_manager.cli_translator.tolog = None
        enchant_book_manager.cli_translator.icloud_sync = None
        enchant_book_manager.cli_translator._module_config = None

    @patch("enchant_book_manager.cli_translator.signal.signal")
    @patch("enchant_book_manager.cli_translator.ICloudSync")
    @patch("enchant_book_manager.cli_translator.ChineseAITranslator")
    @patch("enchant_book_manager.cli_translator._save_translated_book_impl")
    @patch("enchant_book_manager.cli_translator.import_book_from_txt")
    @patch("enchant_book_manager.cli_translator.ConfigManager")
    @patch("enchant_book_manager.cli_translator.logging.basicConfig")
    @patch("enchant_book_manager.cli_translator.logging.getLogger")
    def test_translate_novel_success_local(
        self,
        mock_get_logger,
        mock_basic_config,
        mock_config_manager_class,
        mock_import_book,
        mock_save_book,
        mock_translator_class,
        mock_icloud_class,
        mock_signal,
    ):
        """Test successful local translation."""
        # Mock configuration
        mock_config = {
            "logging": {
                "level": "INFO",
                "format": "%(message)s",
                "file_enabled": False,
                "file_path": "app.log",
            },
            "icloud": {"enabled": False},
            "text_processing": {"max_chars_per_chunk": 10000},
            "translation": {
                "local": {
                    "endpoint": "http://localhost:5000",
                    "model": "local-model",
                    "timeout": 300,
                },
                "temperature": 0.7,
                "max_tokens": 4000,
            },
            "pricing": {"enabled": False},
        }

        mock_config_manager = Mock()
        mock_config_manager.config = mock_config
        mock_config_manager_class.return_value = mock_config_manager

        # Mock logger
        mock_logger = Mock(spec=logging.Logger)
        mock_get_logger.return_value = mock_logger

        # Mock translator
        mock_translator = Mock()
        mock_translator_class.return_value = mock_translator

        # Mock icloud
        mock_icloud = Mock()
        mock_icloud_class.return_value = mock_icloud

        # Mock book import
        mock_import_book.return_value = "book123"

        # Call function
        result = translate_novel(
            "test.txt",
            encoding="utf-8",
            max_chars=12000,
            resume=False,
            create_epub=False,
            remote=False,
        )

        # Verify success
        assert result is True

        # Verify configuration was loaded
        mock_config_manager_class.assert_called_once_with(config_path=Path("enchant_config.yml"))

        # Verify logging was configured
        mock_basic_config.assert_called_once_with(level=logging.INFO, format="%(message)s")

        # Verify translator was initialized with local config
        mock_translator_class.assert_called_once_with(
            logger=mock_logger,
            use_remote=False,
            endpoint="http://localhost:5000",
            model="local-model",
            temperature=0.7,
            max_tokens=4000,
            timeout=300,
        )

        # Verify book was imported and saved
        mock_import_book.assert_called_once_with("test.txt", encoding="utf-8", max_chars=12000, logger=mock_logger)
        mock_save_book.assert_called_once()

    @patch("enchant_book_manager.cli_translator.sys.exit")
    @patch("enchant_book_manager.cli_translator.signal.signal")
    @patch("enchant_book_manager.cli_translator.ICloudSync")
    @patch("enchant_book_manager.cli_translator.ChineseAITranslator")
    @patch("enchant_book_manager.cli_translator.import_book_from_txt")
    @patch("enchant_book_manager.cli_translator.ConfigManager")
    @patch("enchant_book_manager.cli_translator.logging.basicConfig")
    @patch("enchant_book_manager.cli_translator.logging.getLogger")
    def test_translate_novel_remote_no_api_key(
        self,
        mock_get_logger,
        mock_basic_config,
        mock_config_manager_class,
        mock_import_book,
        mock_translator_class,
        mock_icloud_class,
        mock_signal,
        mock_exit,
    ):
        """Test remote translation without API key."""
        # Mock configuration
        mock_config = {
            "logging": {
                "level": "INFO",
                "format": "%(message)s",
                "file_enabled": False,
                "file_path": "app.log",
            },
            "icloud": {"enabled": False},
            "text_processing": {"max_chars_per_chunk": 10000},
            "translation": {
                "remote": {
                    "endpoint": "https://api.openrouter.ai",
                    "model": "gpt-4",
                    "timeout": 600,
                },
                "temperature": 0.7,
                "max_tokens": 4000,
            },
            "pricing": {"enabled": True},
        }

        mock_config_manager = Mock()
        mock_config_manager.config = mock_config
        mock_config_manager.get_api_key.return_value = None  # No API key
        mock_config_manager_class.return_value = mock_config_manager

        # Mock logger
        mock_logger = Mock(spec=logging.Logger)
        mock_get_logger.return_value = mock_logger

        # Call function
        translate_novel("test.txt", remote=True)

        # Verify error was logged and exit called
        mock_logger.error.assert_called_with("OpenRouter API key required. Set OPENROUTER_API_KEY or configure in enchant_config.yml")
        mock_exit.assert_called_with(1)

    @patch("enchant_book_manager.cli_translator.global_cost_tracker")
    @patch("enchant_book_manager.cli_translator.signal.signal")
    @patch("enchant_book_manager.cli_translator.ICloudSync")
    @patch("enchant_book_manager.cli_translator.ChineseAITranslator")
    @patch("enchant_book_manager.cli_translator._save_translated_book_impl")
    @patch("enchant_book_manager.cli_translator.import_book_from_txt")
    @patch("enchant_book_manager.cli_translator.ConfigManager")
    @patch("enchant_book_manager.cli_translator.logging.basicConfig")
    @patch("enchant_book_manager.cli_translator.logging.getLogger")
    def test_translate_novel_remote_with_cost_tracking(
        self,
        mock_get_logger,
        mock_basic_config,
        mock_config_manager_class,
        mock_import_book,
        mock_save_book,
        mock_translator_class,
        mock_icloud_class,
        mock_signal,
        mock_cost_tracker,
    ):
        """Test remote translation with cost tracking."""
        # Mock configuration
        mock_config = {
            "logging": {
                "level": "DEBUG",
                "format": "%(message)s",
                "file_enabled": True,
                "file_path": "app.log",
            },
            "icloud": {"enabled": True},
            "text_processing": {"max_chars_per_chunk": 8000},
            "translation": {
                "remote": {
                    "endpoint": "https://api.openrouter.ai",
                    "model": "gpt-4",
                    "timeout": 600,
                },
                "temperature": 0.5,
                "max_tokens": 3000,
            },
            "pricing": {"enabled": True},
        }

        mock_config_manager = Mock()
        mock_config_manager.config = mock_config
        mock_config_manager.get_api_key.return_value = "test-api-key"
        mock_config_manager_class.return_value = mock_config_manager

        # Mock logger
        mock_logger = Mock(spec=logging.Logger)
        mock_get_logger.return_value = mock_logger

        # Mock file handler
        with patch("enchant_book_manager.cli_translator.logging.FileHandler") as mock_file_handler_class:
            mock_file_handler = Mock()
            mock_file_handler_class.return_value = mock_file_handler

            # Mock translator
            mock_translator = Mock()
            mock_translator.format_cost_summary.return_value = "Total cost: $1.50"
            mock_translator_class.return_value = mock_translator

            # Mock book import
            mock_import_book.return_value = "book456"

            # Call function
            result = translate_novel(
                "chinese_novel.txt",
                encoding="gb2312",
                max_chars=5000,
                resume=True,
                remote=True,
            )

            # Verify success
            assert result is True

            # Verify file handler was set up
            mock_file_handler_class.assert_called_once_with("app.log")
            mock_file_handler.setLevel.assert_called_once_with(logging.DEBUG)
            mock_logger.addHandler.assert_called_once_with(mock_file_handler)

            # Verify translator was initialized with remote config
            mock_translator_class.assert_called_once_with(
                logger=mock_logger,
                use_remote=True,
                api_key="test-api-key",
                endpoint="https://api.openrouter.ai",
                model="gpt-4",
                temperature=0.5,
                max_tokens=3000,
                timeout=600,
            )

            # Verify cost summary was logged
            mock_logger.info.assert_any_call("Cost Summary:\nTotal cost: $1.50")

    @patch("enchant_book_manager.cli_translator.print")
    @patch("enchant_book_manager.cli_translator.ConfigManager")
    def test_translate_novel_config_error(self, mock_config_manager_class, mock_print):
        """Test handling of configuration errors."""
        # Make ConfigManager raise ValueError
        mock_config_manager_class.side_effect = ValueError("Invalid config")

        # Call function
        result = translate_novel("test.txt")

        # Verify failure
        assert result is False
        mock_print.assert_called_with("Configuration error: Invalid config")

    @patch("enchant_book_manager.cli_translator.signal.signal")
    @patch("enchant_book_manager.cli_translator.ICloudSync")
    @patch("enchant_book_manager.cli_translator.ChineseAITranslator")
    @patch("enchant_book_manager.cli_translator.import_book_from_txt")
    @patch("enchant_book_manager.cli_translator.ConfigManager")
    @patch("enchant_book_manager.cli_translator.logging.basicConfig")
    @patch("enchant_book_manager.cli_translator.logging.getLogger")
    def test_translate_novel_import_error(
        self,
        mock_get_logger,
        mock_basic_config,
        mock_config_manager_class,
        mock_import_book,
        mock_translator_class,
        mock_icloud_class,
        mock_signal,
    ):
        """Test handling of import errors."""
        # Mock configuration
        mock_config = {
            "logging": {
                "level": "INFO",
                "format": "%(message)s",
                "file_enabled": False,
            },
            "icloud": {"enabled": False},
            "text_processing": {"max_chars_per_chunk": 10000},
            "translation": {
                "local": {
                    "endpoint": "http://localhost",
                    "model": "local",
                    "timeout": 300,
                },
                "temperature": 0.7,
                "max_tokens": 4000,
            },
            "pricing": {"enabled": False},
        }

        mock_config_manager = Mock()
        mock_config_manager.config = mock_config
        mock_config_manager_class.return_value = mock_config_manager

        # Mock logger
        mock_logger = Mock(spec=logging.Logger)
        mock_get_logger.return_value = mock_logger

        # Make import raise exception
        mock_import_book.side_effect = Exception("Import failed")

        # Call function
        result = translate_novel("test.txt")

        # Verify failure
        assert result is False
        mock_logger.exception.assert_called_with("An error occurred during book import.")

    @patch("enchant_book_manager.cli_translator.signal.signal")
    @patch("enchant_book_manager.cli_translator.ICloudSync")
    @patch("enchant_book_manager.cli_translator.ChineseAITranslator")
    @patch("enchant_book_manager.cli_translator._save_translated_book_impl")
    @patch("enchant_book_manager.cli_translator.import_book_from_txt")
    @patch("enchant_book_manager.cli_translator.ConfigManager")
    @patch("enchant_book_manager.cli_translator.logging.basicConfig")
    @patch("enchant_book_manager.cli_translator.logging.getLogger")
    def test_translate_novel_save_error(
        self,
        mock_get_logger,
        mock_basic_config,
        mock_config_manager_class,
        mock_import_book,
        mock_save_book,
        mock_translator_class,
        mock_icloud_class,
        mock_signal,
    ):
        """Test handling of save errors."""
        # Mock configuration
        mock_config = {
            "logging": {
                "level": "INFO",
                "format": "%(message)s",
                "file_enabled": False,
            },
            "icloud": {"enabled": False},
            "text_processing": {"max_chars_per_chunk": 10000},
            "translation": {
                "local": {
                    "endpoint": "http://localhost",
                    "model": "local",
                    "timeout": 300,
                },
                "temperature": 0.7,
                "max_tokens": 4000,
            },
            "pricing": {"enabled": False},
        }

        mock_config_manager = Mock()
        mock_config_manager.config = mock_config
        mock_config_manager_class.return_value = mock_config_manager

        # Mock logger
        mock_logger = Mock(spec=logging.Logger)
        mock_get_logger.return_value = mock_logger

        # Mock successful import
        mock_import_book.return_value = "book789"

        # Make save raise exception
        mock_save_book.side_effect = Exception("Save failed")

        # Call function
        result = translate_novel("test.txt")

        # Verify failure
        assert result is False
        mock_logger.exception.assert_called_with("Error saving translated book.")

    @patch("enchant_book_manager.cli_translator.signal.signal")
    @patch("enchant_book_manager.cli_translator.ICloudSync")
    @patch("enchant_book_manager.cli_translator.ChineseAITranslator")
    @patch("enchant_book_manager.cli_translator.ConfigManager")
    @patch("enchant_book_manager.cli_translator.logging.basicConfig")
    @patch("enchant_book_manager.cli_translator.logging.getLogger")
    @patch("enchant_book_manager.cli_translator.logging.FileHandler")
    def test_translate_novel_file_logging_error(
        self,
        mock_file_handler_class,
        mock_get_logger,
        mock_basic_config,
        mock_config_manager_class,
        mock_translator_class,
        mock_icloud_class,
        mock_signal,
    ):
        """Test handling of file logging errors."""
        # Mock configuration with file logging enabled
        mock_config = {
            "logging": {
                "level": "INFO",
                "format": "%(message)s",
                "file_enabled": True,
                "file_path": "/invalid/path/app.log",
            },
            "icloud": {"enabled": False},
            "text_processing": {"max_chars_per_chunk": 10000},
            "translation": {
                "local": {
                    "endpoint": "http://localhost",
                    "model": "local",
                    "timeout": 300,
                },
                "temperature": 0.7,
                "max_tokens": 4000,
            },
            "pricing": {"enabled": False},
        }

        mock_config_manager = Mock()
        mock_config_manager.config = mock_config
        mock_config_manager_class.return_value = mock_config_manager

        # Mock logger
        mock_logger = Mock(spec=logging.Logger)
        mock_get_logger.return_value = mock_logger

        # Make FileHandler raise exception
        mock_file_handler_class.side_effect = PermissionError("Permission denied")

        # Import the function to test the flow continues
        with patch("enchant_book_manager.cli_translator.import_book_from_txt") as mock_import:
            mock_import.return_value = "book123"
            with patch("enchant_book_manager.cli_translator._save_translated_book_impl"):
                result = translate_novel("test.txt")

        # Should continue despite logging error
        assert result is True
        mock_logger.error.assert_called_once()
        assert "Failed to set up file logging" in mock_logger.error.call_args[0][0]

    @patch("enchant_book_manager.cli_translator.sys.exit")
    @patch("enchant_book_manager.cli_translator.signal.signal")
    @patch("enchant_book_manager.cli_translator.ICloudSync")
    @patch("enchant_book_manager.cli_translator.ChineseAITranslator")
    @patch("enchant_book_manager.cli_translator.ConfigManager")
    @patch("enchant_book_manager.cli_translator.logging.basicConfig")
    @patch("enchant_book_manager.cli_translator.logging.getLogger")
    def test_signal_handler(
        self,
        mock_get_logger,
        mock_basic_config,
        mock_config_manager_class,
        mock_translator_class,
        mock_icloud_class,
        mock_signal,
        mock_exit,
    ):
        """Test signal handler setup and execution."""
        # Mock configuration
        mock_config = {
            "logging": {
                "level": "INFO",
                "format": "%(message)s",
                "file_enabled": False,
            },
            "icloud": {"enabled": False},
            "text_processing": {"max_chars_per_chunk": 10000},
            "translation": {
                "local": {
                    "endpoint": "http://localhost",
                    "model": "local",
                    "timeout": 300,
                },
                "temperature": 0.7,
                "max_tokens": 4000,
            },
            "pricing": {"enabled": False},
        }

        mock_config_manager = Mock()
        mock_config_manager.config = mock_config
        mock_config_manager_class.return_value = mock_config_manager

        # Mock logger
        mock_logger = Mock(spec=logging.Logger)
        mock_get_logger.return_value = mock_logger

        # Start the function
        with patch("enchant_book_manager.cli_translator.import_book_from_txt"):
            translate_novel("test.txt")

        # Verify signal handler was registered
        mock_signal.assert_called_once()
        assert mock_signal.call_args[0][0] == signal.SIGINT

        # Get and test the signal handler
        handler = mock_signal.call_args[0][1]
        handler(signal.SIGINT, None)

        # Verify it logged and exited
        mock_logger.info.assert_any_call("Interrupt received. Exiting gracefully.")
        mock_exit.assert_called_with(0)


class TestColoramaWarning:
    """Test colorama import warning."""

    @patch("enchant_book_manager.cli_translator.cr", None)
    @patch("enchant_book_manager.cli_translator.signal.signal")
    @patch("enchant_book_manager.cli_translator.ICloudSync")
    @patch("enchant_book_manager.cli_translator.ChineseAITranslator")
    @patch("enchant_book_manager.cli_translator.ConfigManager")
    @patch("enchant_book_manager.cli_translator.logging.basicConfig")
    @patch("enchant_book_manager.cli_translator.logging.getLogger")
    def test_colorama_warning(
        self,
        mock_get_logger,
        mock_basic_config,
        mock_config_manager_class,
        mock_translator_class,
        mock_icloud_class,
        mock_signal,
    ):
        """Test warning when colorama is not available."""
        # Mock configuration
        mock_config = {
            "logging": {
                "level": "INFO",
                "format": "%(message)s",
                "file_enabled": False,
            },
            "icloud": {"enabled": False},
            "text_processing": {"max_chars_per_chunk": 10000},
            "translation": {
                "local": {
                    "endpoint": "http://localhost",
                    "model": "local",
                    "timeout": 300,
                },
                "temperature": 0.7,
                "max_tokens": 4000,
            },
            "pricing": {"enabled": False},
        }

        mock_config_manager = Mock()
        mock_config_manager.config = mock_config
        mock_config_manager_class.return_value = mock_config_manager

        # Mock logger
        mock_logger = Mock(spec=logging.Logger)
        mock_get_logger.return_value = mock_logger

        # Start translation to trigger colorama check
        with patch("enchant_book_manager.cli_translator.import_book_from_txt"):
            translate_novel("test.txt")

        # Verify warning was logged
        mock_logger.warning.assert_called_with("colorama package not installed. Colored text may not work properly.")


class TestCostTracking:
    """Test cost tracking integration."""

    @patch("enchant_book_manager.cli_translator.global_cost_tracker")
    @patch("enchant_book_manager.cli_translator.signal.signal")
    @patch("enchant_book_manager.cli_translator.ICloudSync")
    @patch("enchant_book_manager.cli_translator.ChineseAITranslator")
    @patch("enchant_book_manager.cli_translator._save_translated_book_impl")
    @patch("enchant_book_manager.cli_translator.import_book_from_txt")
    @patch("enchant_book_manager.cli_translator.ConfigManager")
    @patch("enchant_book_manager.cli_translator.logging.basicConfig")
    @patch("enchant_book_manager.cli_translator.logging.getLogger")
    def test_local_translation_with_pricing_enabled(
        self,
        mock_get_logger,
        mock_basic_config,
        mock_config_manager_class,
        mock_import_book,
        mock_save_book,
        mock_translator_class,
        mock_icloud_class,
        mock_signal,
        mock_cost_tracker,
    ):
        """Test local translation with pricing enabled."""
        # Mock configuration
        mock_config = {
            "logging": {
                "level": "INFO",
                "format": "%(message)s",
                "file_enabled": False,
            },
            "icloud": {"enabled": False},
            "text_processing": {"max_chars_per_chunk": 10000},
            "translation": {
                "local": {
                    "endpoint": "http://localhost",
                    "model": "local",
                    "timeout": 300,
                },
                "temperature": 0.7,
                "max_tokens": 4000,
            },
            "pricing": {"enabled": True},
        }

        mock_config_manager = Mock()
        mock_config_manager.config = mock_config
        mock_config_manager_class.return_value = mock_config_manager

        # Mock logger
        mock_logger = Mock(spec=logging.Logger)
        mock_get_logger.return_value = mock_logger

        # Mock cost tracker summary
        mock_cost_tracker.get_summary.return_value = {
            "total_cost": 0.5,
            "request_count": 10,
        }

        # Mock book import
        mock_import_book.return_value = "book123"

        # Call function
        result = translate_novel("test.txt", remote=False)

        # Verify success
        assert result is True

        # Verify cost summary was logged
        mock_logger.info.assert_any_call("Cost Summary: Total cost: $0.500000, Total requests: 10")
