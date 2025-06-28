#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test suite for config_validator module.
"""

import pytest
import logging
from pathlib import Path
import sys
from unittest.mock import Mock, patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))

from enchant_book_manager.config_validator import ConfigValidator


class TestConfigValidator:
    """Test the ConfigValidator class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.validator = ConfigValidator()
        self.defaults = {
            "presets": {
                "LOCAL": {
                    "endpoint": "http://localhost:1234",
                    "model": "local-model",
                    "connection_timeout": 30,
                    "response_timeout": 300,
                    "max_retries": 7,
                    "retry_wait_base": 1.0,
                    "retry_wait_max": 60.0,
                    "double_pass": False,
                    "max_chars_per_chunk": 11999,
                    "temperature": 0.05,
                    "max_tokens": 4000,
                    "system_prompt": "prompt",
                    "user_prompt_1st_pass": "prompt",
                    "user_prompt_2nd_pass": "prompt",
                },
                "REMOTE": {
                    "endpoint": "https://api.example.com",
                    "model": "remote-model",
                    "connection_timeout": 30,
                    "response_timeout": 300,
                    "max_retries": 7,
                    "retry_wait_base": 1.0,
                    "retry_wait_max": 60.0,
                    "double_pass": True,
                    "max_chars_per_chunk": 11999,
                    "temperature": 0.05,
                    "max_tokens": 4000,
                    "system_prompt": "",
                    "user_prompt_1st_pass": "prompt",
                    "user_prompt_2nd_pass": "prompt",
                },
            },
            "translation": {"service": "local"},
            "text_processing": {"max_chars": 1000},
            "novel_renaming": {"enabled": False},
            "epub": {"enabled": False},
            "batch": {"max_workers": 4},
            "icloud": {"enabled": False},
            "pricing": {"enabled": True},
            "logging": {"level": "INFO"},
        }
        self.config_lines = [
            "presets:",
            "  LOCAL:",
            "    endpoint: http://localhost:1234",
            "translation:",
            "  service: local",
        ]

    def test_init_with_logger(self):
        """Test initialization with custom logger."""
        logger = Mock(spec=logging.Logger)
        validator = ConfigValidator(logger=logger)
        assert validator.logger == logger
        assert validator.error_reporter is not None
        assert validator.preset_validator is not None

    def test_init_without_logger(self):
        """Test initialization without logger (uses default)."""
        validator = ConfigValidator()
        assert isinstance(validator.logger, logging.Logger)
        assert validator.error_reporter is not None
        assert validator.preset_validator is not None

    def test_validate_config_valid(self):
        """Test validation of valid configuration."""
        config = {
            "presets": self.defaults["presets"],
            "translation": {"service": "local"},
            "text_processing": {"max_chars": 1000},
            "novel_renaming": {"enabled": False},
            "epub": {"enabled": False},
            "batch": {"max_workers": 4},
            "icloud": {"enabled": False},
            "pricing": {"enabled": True},
            "logging": {"level": "INFO"},
        }

        result = self.validator.validate_config_first_error(config, self.defaults, self.config_lines)
        assert result is None

    def test_validate_config_unknown_top_key(self):
        """Test validation with unknown top-level key."""
        config = {
            "unknown_key": "value",
            "translation": {"service": "local"},
            "text_processing": {"max_chars": 1000},
            "novel_renaming": {"enabled": False},
            "epub": {"enabled": False},
            "batch": {"max_workers": 4},
            "icloud": {"enabled": False},
            "pricing": {"enabled": True},
            "logging": {"level": "INFO"},
        }

        result = self.validator.validate_config_first_error(config, self.defaults, self.config_lines)
        assert result is not None
        assert result["type"] == "unknown_key"
        assert result["key"] == "unknown_key"
        assert "Unknown or malformed key" in result["message"]

    @patch("enchant_book_manager.config_validator.find_line_number")
    def test_validate_config_unknown_key_with_line(self, mock_find_line):
        """Test unknown key error includes line number."""
        mock_find_line.return_value = 5

        config = {"unknown_key": "value"}
        result = self.validator.validate_config_first_error(config, self.defaults, self.config_lines)

        assert result["line"] == 5
        mock_find_line.assert_called_once_with("unknown_key", self.config_lines)

    def test_validate_config_missing_section(self):
        """Test validation with missing required section."""
        config = {
            "presets": self.defaults["presets"],
            # Missing translation section
            "text_processing": {"max_chars": 1000},
            "novel_renaming": {"enabled": False},
            "epub": {"enabled": False},
            "batch": {"max_workers": 4},
            "icloud": {"enabled": False},
            "pricing": {"enabled": True},
            "logging": {"level": "INFO"},
        }

        result = self.validator.validate_config_first_error(config, self.defaults, self.config_lines)
        assert result is not None
        assert result["type"] == "missing_section"
        assert result["section"] == "translation"
        assert "Translation settings" in result["description"]

    def test_validate_config_multiple_missing_sections(self):
        """Test that only first missing section is reported."""
        config = {
            "presets": self.defaults["presets"],
            # Missing multiple sections
            "text_processing": {"max_chars": 1000},
            "novel_renaming": {"enabled": False},
            # Missing epub, batch, icloud, pricing, logging
        }

        result = self.validator.validate_config_first_error(config, self.defaults, self.config_lines)
        assert result is not None
        assert result["type"] == "missing_section"
        # Should report first missing section (translation)
        assert result["section"] == "translation"

    def test_validate_config_invalid_service_value(self):
        """Test validation with invalid translation service value."""
        config = {
            "presets": self.defaults["presets"],
            "translation": {"service": "invalid"},  # Should be 'local' or 'remote'
            "text_processing": {"max_chars": 1000},
            "novel_renaming": {"enabled": False},
            "epub": {"enabled": False},
            "batch": {"max_workers": 4},
            "icloud": {"enabled": False},
            "pricing": {"enabled": True},
            "logging": {"level": "INFO"},
        }

        result = self.validator.validate_config_first_error(config, self.defaults, self.config_lines)
        assert result is not None
        assert result["type"] == "invalid_value"
        assert result["path"] == "translation.service"
        assert result["value"] == "invalid"
        assert result["valid_values"] == ["local", "remote"]

    @patch("enchant_book_manager.config_validator.ConfigPresetValidator")
    def test_validate_config_preset_error(self, mock_preset_validator_class):
        """Test that preset errors are checked first."""
        # Mock preset validator to return an error
        mock_preset_validator = Mock()
        mock_preset_error = {"type": "preset_error", "message": "Invalid preset"}
        mock_preset_validator.validate_presets_first_error.return_value = mock_preset_error
        mock_preset_validator_class.return_value = mock_preset_validator

        validator = ConfigValidator()

        config = {
            "presets": {"INVALID": {}},  # Invalid preset
            # Even with missing sections, preset error should be returned first
            # Missing all other sections
        }

        result = validator.validate_config_first_error(config, self.defaults, self.config_lines)
        assert result == mock_preset_error

    def test_validate_config_no_presets_section(self):
        """Test validation when presets section is missing."""
        config = {
            # No presets section
            "translation": {"service": "local"},
            "text_processing": {"max_chars": 1000},
            "novel_renaming": {"enabled": False},
            "epub": {"enabled": False},
            "batch": {"max_workers": 4},
            "icloud": {"enabled": False},
            "pricing": {"enabled": True},
            "logging": {"level": "INFO"},
        }

        result = self.validator.validate_config_first_error(config, self.defaults, self.config_lines)
        # Should pass - presets section is not in required_sections
        assert result is None

    def test_validate_config_empty_translation_section(self):
        """Test validation with empty translation section."""
        config = {
            "presets": self.defaults["presets"],
            "translation": {},  # Empty but present
            "text_processing": {"max_chars": 1000},
            "novel_renaming": {"enabled": False},
            "epub": {"enabled": False},
            "batch": {"max_workers": 4},
            "icloud": {"enabled": False},
            "pricing": {"enabled": True},
            "logging": {"level": "INFO"},
        }

        result = self.validator.validate_config_first_error(config, self.defaults, self.config_lines)
        # Should pass - service key is optional
        assert result is None

    def test_report_single_error(self):
        """Test error reporting delegation."""
        error = {"type": "test_error", "message": "Test error message", "line": 10}

        with patch.object(self.validator.error_reporter, "report_single_error") as mock_report:
            self.validator.report_single_error(error, self.config_lines)
            mock_report.assert_called_once_with(error, self.config_lines)

    def test_validate_config_complex_scenario(self):
        """Test complex validation scenario with multiple potential errors."""
        config = {
            "unknown_key": "value",  # Unknown key (first error)
            "presets": {
                "INVALID_NAME!": {}  # Invalid preset name (would be second error)
            },
            "translation": {"service": "invalid"},  # Invalid value (would be third error)
            # Missing multiple sections (would be fourth+ errors)
        }

        result = self.validator.validate_config_first_error(config, self.defaults, self.config_lines)
        # Should return the FIRST error found
        assert result is not None
        assert result["type"] == "unknown_key"
        assert result["key"] == "unknown_key"

    def test_missing_section_line_calculation(self):
        """Test line number calculation for missing sections."""
        config_lines = [
            "# Comment",
            "presets:",
            "  LOCAL:",
            "    endpoint: test",
            "# Another comment",
        ]

        config = {
            "presets": self.defaults["presets"],
            # Missing translation and other sections
        }

        result = self.validator.validate_config_first_error(config, self.defaults, config_lines)
        assert result is not None
        assert result["type"] == "missing_section"
        # Should suggest adding after last non-comment line
        assert result["line"] == 4  # After "    endpoint: test"

    def test_missing_section_empty_config_lines(self):
        """Test missing section with empty config lines."""
        config = {
            "presets": self.defaults["presets"],
            # Missing translation
        }

        result = self.validator.validate_config_first_error(config, self.defaults, [])
        assert result is not None
        assert result["type"] == "missing_section"
        assert result["line"] == 0  # Empty file

    def test_validate_config_order_of_checks(self):
        """Test that validation checks are performed in correct order."""
        # Create a config with multiple types of errors
        config = {
            "unknown": "value",  # Unknown key
            "presets": {
                "BAD!": {}  # Bad preset
            },
            "translation": {"service": "wrong"},  # Invalid value
            # Missing sections
        }

        # Mock the preset validator to track if it's called
        with patch.object(self.validator.preset_validator, "validate_presets_first_error") as mock_preset:
            mock_preset.return_value = None  # No preset errors

            result = self.validator.validate_config_first_error(config, self.defaults, self.config_lines)

            # Unknown key should be found first, before preset validation
            assert result["type"] == "unknown_key"
            # Preset validator should not have been called
            mock_preset.assert_not_called()
