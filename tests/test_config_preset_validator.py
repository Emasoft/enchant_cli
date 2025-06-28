#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test suite for config_preset_validator module.
"""

from pathlib import Path
from unittest.mock import Mock, patch
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from enchant_book_manager.config_preset_validator import ConfigPresetValidator


class TestConfigPresetValidator:
    """Test ConfigPresetValidator class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.validator = ConfigPresetValidator()
        self.config_lines = [
            "presets:",
            "  LOCAL:",
            "    endpoint: http://localhost:5000",
            "    model: local-model",
            "  REMOTE:",
            "    endpoint: https://api.openai.com",
            "    model: gpt-4",
        ]
        self.defaults = {
            "presets": {
                "LOCAL": {
                    "endpoint": "http://localhost:5000",
                    "model": "local-model",
                    "connection_timeout": 30,
                    "response_timeout": 300,
                    "max_retries": 3,
                    "retry_wait_base": 1.0,
                    "retry_wait_max": 60.0,
                    "double_pass": False,
                    "max_chars_per_chunk": 10000,
                    "temperature": 0.7,
                    "max_tokens": 4000,
                    "system_prompt": "You are a translator",
                    "user_prompt_1st_pass": "Translate this",
                    "user_prompt_2nd_pass": "Refine this",
                },
                "REMOTE": {
                    "endpoint": "https://api.openai.com",
                    "model": "gpt-4",
                    "connection_timeout": 30,
                    "response_timeout": 600,
                    "max_retries": 5,
                    "retry_wait_base": 2.0,
                    "retry_wait_max": 120.0,
                    "double_pass": True,
                    "max_chars_per_chunk": 8000,
                    "temperature": 0.5,
                    "max_tokens": 3000,
                    "system_prompt": "You are a professional translator",
                    "user_prompt_1st_pass": "Translate this text",
                    "user_prompt_2nd_pass": "Refine this translation",
                },
            }
        }

    def test_validate_presets_no_presets(self):
        """Test validation when no presets are defined."""
        config = {}
        result = self.validator.validate_presets_first_error(config, self.defaults, self.config_lines)
        assert result is None

    def test_validate_presets_empty_presets(self):
        """Test validation with empty presets section."""
        config = {"presets": {}}
        result = self.validator.validate_presets_first_error(config, self.defaults, self.config_lines)
        assert result is None

    def test_validate_presets_invalid_preset_name_number(self):
        """Test validation with preset name starting with number."""
        config = {"presets": {"1INVALID": {"endpoint": "http://test"}}}
        result = self.validator.validate_presets_first_error(config, self.defaults, self.config_lines)
        assert result is not None
        assert result["type"] == "invalid_preset_name"
        assert result["preset"] == "1INVALID"
        assert "must not begin with a number" in result["message"]

    def test_validate_presets_invalid_preset_name_hyphen(self):
        """Test validation with preset name containing hyphen."""
        config = {"presets": {"MY-PRESET": {"endpoint": "http://test"}}}
        result = self.validator.validate_presets_first_error(config, self.defaults, self.config_lines)
        assert result is not None
        assert result["type"] == "invalid_preset_name"
        assert result["preset"] == "MY-PRESET"
        assert "cannot contain hyphens" in result["message"]

    def test_validate_presets_invalid_preset_name_space(self):
        """Test validation with preset name containing space."""
        config = {"presets": {"MY PRESET": {"endpoint": "http://test"}}}
        result = self.validator.validate_presets_first_error(config, self.defaults, self.config_lines)
        assert result is not None
        assert result["type"] == "invalid_preset_name"
        assert result["preset"] == "MY PRESET"
        assert "cannot contain spaces" in result["message"]

    def test_validate_presets_invalid_preset_name_special_char(self):
        """Test validation with preset name containing special characters."""
        config = {"presets": {"PRESET@123": {"endpoint": "http://test"}}}
        result = self.validator.validate_presets_first_error(config, self.defaults, self.config_lines)
        assert result is not None
        assert result["type"] == "invalid_preset_name"
        assert "must start with a letter or underscore" in result["message"]

    def test_validate_presets_valid_preset_names(self):
        """Test validation with valid preset names."""
        config = {
            "presets": {
                "LOCAL": self.defaults["presets"]["LOCAL"],
                "REMOTE": self.defaults["presets"]["REMOTE"],
                "_CUSTOM": {"endpoint": "http://test", "model": "test"},
                "Custom_123": {"endpoint": "http://test", "model": "test"},
            }
        }
        result = self.validator.validate_presets_first_error(config, self.defaults, self.config_lines)
        assert result is None

    def test_validate_presets_missing_local(self):
        """Test validation when LOCAL preset is missing."""
        config = {"presets": {"REMOTE": self.defaults["presets"]["REMOTE"]}}
        result = self.validator.validate_presets_first_error(config, self.defaults, self.config_lines)
        assert result is not None
        assert result["type"] == "missing_required_preset"
        assert result["preset"] == "LOCAL"
        assert result["can_restore"] is True

    def test_validate_presets_missing_remote(self):
        """Test validation when REMOTE preset is missing."""
        config = {"presets": {"LOCAL": self.defaults["presets"]["LOCAL"]}}
        result = self.validator.validate_presets_first_error(config, self.defaults, self.config_lines)
        assert result is not None
        assert result["type"] == "missing_required_preset"
        assert result["preset"] == "REMOTE"

    def test_validate_presets_invalid_preset_type(self):
        """Test validation when preset is not a dictionary."""
        config = {
            "presets": {
                "LOCAL": "not a dict",
                "REMOTE": self.defaults["presets"]["REMOTE"],
            }
        }
        result = self.validator.validate_presets_first_error(config, self.defaults, self.config_lines)
        assert result is not None
        assert result["type"] == "invalid_preset_type"
        assert result["preset"] == "LOCAL"
        assert "must be a dictionary/mapping" in result["message"]

    def test_validate_presets_unknown_key(self):
        """Test validation with unknown key in preset."""
        config = {
            "presets": {
                "LOCAL": {
                    **self.defaults["presets"]["LOCAL"],
                    "unknown_key": "value",
                },
                "REMOTE": self.defaults["presets"]["REMOTE"],
            }
        }
        result = self.validator.validate_presets_first_error(config, self.defaults, self.config_lines)
        assert result is not None
        assert result["type"] == "unknown_key"
        assert result["key"] == "unknown_key"
        assert result["preset"] == "LOCAL"

    def test_validate_presets_missing_required_key(self):
        """Test validation with missing required key."""
        config = {
            "presets": {
                "LOCAL": {
                    "endpoint": "http://localhost:5000",
                    # Missing model and other required keys
                },
                "REMOTE": self.defaults["presets"]["REMOTE"],
            }
        }
        result = self.validator.validate_presets_first_error(config, self.defaults, self.config_lines)
        assert result is not None
        assert result["type"] == "missing_key"
        assert result["key"] == "model"
        assert result["preset"] == "LOCAL"

    def test_validate_presets_custom_preset_minimal_keys(self):
        """Test validation of custom preset with minimal required keys."""
        config = {
            "presets": {
                "LOCAL": self.defaults["presets"]["LOCAL"],
                "REMOTE": self.defaults["presets"]["REMOTE"],
                "CUSTOM": {
                    "endpoint": "http://custom.api",
                    "model": "custom-model",
                },
            }
        }
        result = self.validator.validate_presets_first_error(config, self.defaults, self.config_lines)
        assert result is None

    def test_validate_preset_values_invalid_integer(self):
        """Test validation with invalid integer value."""
        config = {
            "presets": {
                "LOCAL": {
                    **self.defaults["presets"]["LOCAL"],
                    "max_retries": "not an integer",
                },
                "REMOTE": self.defaults["presets"]["REMOTE"],
            }
        }
        result = self.validator.validate_presets_first_error(config, self.defaults, self.config_lines)
        assert result is not None
        assert result["type"] == "invalid_type"
        assert result["key"] == "max_retries"
        assert "must be an integer" in result["message"]

    def test_validate_preset_values_negative_integer(self):
        """Test validation with negative integer value."""
        config = {
            "presets": {
                "LOCAL": {
                    **self.defaults["presets"]["LOCAL"],
                    "connection_timeout": -1,
                },
                "REMOTE": self.defaults["presets"]["REMOTE"],
            }
        }
        result = self.validator.validate_presets_first_error(config, self.defaults, self.config_lines)
        assert result is not None
        assert result["type"] == "invalid_value"
        assert result["key"] == "connection_timeout"
        assert "must be a positive integer" in result["message"]

    def test_validate_preset_values_invalid_float(self):
        """Test validation with invalid float value."""
        config = {
            "presets": {
                "LOCAL": {
                    **self.defaults["presets"]["LOCAL"],
                    "temperature": "not a float",
                },
                "REMOTE": self.defaults["presets"]["REMOTE"],
            }
        }
        result = self.validator.validate_presets_first_error(config, self.defaults, self.config_lines)
        assert result is not None
        assert result["type"] == "invalid_type"
        assert result["key"] == "temperature"
        assert "must be a number" in result["message"]

    def test_validate_preset_values_negative_float(self):
        """Test validation with negative float value."""
        config = {
            "presets": {
                "LOCAL": {
                    **self.defaults["presets"]["LOCAL"],
                    "retry_wait_base": -1.5,
                },
                "REMOTE": self.defaults["presets"]["REMOTE"],
            }
        }
        result = self.validator.validate_presets_first_error(config, self.defaults, self.config_lines)
        assert result is not None
        assert result["type"] == "invalid_value"
        assert result["key"] == "retry_wait_base"
        assert "must be non-negative" in result["message"]

    def test_validate_preset_values_temperature_too_high(self):
        """Test validation with temperature value too high."""
        config = {
            "presets": {
                "LOCAL": {
                    **self.defaults["presets"]["LOCAL"],
                    "temperature": 2.5,
                },
                "REMOTE": self.defaults["presets"]["REMOTE"],
            }
        }
        result = self.validator.validate_presets_first_error(config, self.defaults, self.config_lines)
        assert result is not None
        assert result["type"] == "invalid_value"
        assert result["key"] == "temperature"
        assert "must be between 0.0 and 2.0" in result["message"]

    def test_validate_preset_values_invalid_boolean(self):
        """Test validation with invalid boolean value."""
        config = {
            "presets": {
                "LOCAL": {
                    **self.defaults["presets"]["LOCAL"],
                    "double_pass": "yes",
                },
                "REMOTE": self.defaults["presets"]["REMOTE"],
            }
        }
        result = self.validator.validate_presets_first_error(config, self.defaults, self.config_lines)
        assert result is not None
        assert result["type"] == "invalid_type"
        assert result["key"] == "double_pass"
        assert "can only be true or false" in result["message"]

    def test_validate_preset_values_invalid_endpoint_type(self):
        """Test validation with non-string endpoint."""
        config = {
            "presets": {
                "LOCAL": {
                    **self.defaults["presets"]["LOCAL"],
                    "endpoint": 123,
                },
                "REMOTE": self.defaults["presets"]["REMOTE"],
            }
        }
        result = self.validator.validate_presets_first_error(config, self.defaults, self.config_lines)
        assert result is not None
        assert result["type"] == "invalid_type"
        assert result["key"] == "endpoint"
        assert "must be a string URL" in result["message"]

    def test_validate_preset_values_invalid_endpoint_format(self):
        """Test validation with invalid endpoint URL format."""
        config = {
            "presets": {
                "LOCAL": {
                    **self.defaults["presets"]["LOCAL"],
                    "endpoint": "not-a-url",
                },
                "REMOTE": self.defaults["presets"]["REMOTE"],
            }
        }
        result = self.validator.validate_presets_first_error(config, self.defaults, self.config_lines)
        assert result is not None
        assert result["type"] == "invalid_value"
        assert result["key"] == "endpoint"
        assert "not a valid openai compatible endpoint format" in result["message"]

    def test_validate_preset_values_empty_model(self):
        """Test validation with empty model string."""
        config = {
            "presets": {
                "LOCAL": {
                    **self.defaults["presets"]["LOCAL"],
                    "model": "",
                },
                "REMOTE": self.defaults["presets"]["REMOTE"],
            }
        }
        result = self.validator.validate_presets_first_error(config, self.defaults, self.config_lines)
        assert result is not None
        assert result["type"] == "invalid_value"
        assert result["key"] == "model"
        assert "must be a non-empty string" in result["message"]

    def test_validate_preset_values_whitespace_model(self):
        """Test validation with whitespace-only model string."""
        config = {
            "presets": {
                "LOCAL": {
                    **self.defaults["presets"]["LOCAL"],
                    "model": "   ",
                },
                "REMOTE": self.defaults["presets"]["REMOTE"],
            }
        }
        result = self.validator.validate_presets_first_error(config, self.defaults, self.config_lines)
        assert result is not None
        assert result["type"] == "invalid_value"
        assert result["key"] == "model"
        assert "must be a non-empty string" in result["message"]

    def test_validate_preset_values_all_valid(self):
        """Test validation with all valid values."""
        config = {
            "presets": {
                "LOCAL": {
                    "endpoint": "http://localhost:5000",
                    "model": "local-model",
                    "connection_timeout": 30,
                    "response_timeout": 300,
                    "max_retries": 3,
                    "retry_wait_base": 1.0,
                    "retry_wait_max": 60.0,
                    "double_pass": False,
                    "max_chars_per_chunk": 10000,
                    "temperature": 0.7,
                    "max_tokens": 4000,
                    "system_prompt": "You are a translator",
                    "user_prompt_1st_pass": "Translate this",
                    "user_prompt_2nd_pass": "Refine this",
                },
                "REMOTE": {
                    "endpoint": "https://api.openai.com",
                    "model": "gpt-4",
                    "connection_timeout": 30,
                    "response_timeout": 600,
                    "max_retries": 5,
                    "retry_wait_base": 2.0,
                    "retry_wait_max": 120.0,
                    "double_pass": True,
                    "max_chars_per_chunk": 8000,
                    "temperature": 0.0,
                    "max_tokens": 3000,
                    "system_prompt": "You are a professional translator",
                    "user_prompt_1st_pass": "Translate this text",
                    "user_prompt_2nd_pass": "Refine this translation",
                },
            }
        }
        result = self.validator.validate_presets_first_error(config, self.defaults, self.config_lines)
        assert result is None

    @patch("enchant_book_manager.config_preset_validator.find_line_number")
    def test_validate_presets_with_line_numbers(self, mock_find_line):
        """Test that line numbers are properly included in errors."""
        mock_find_line.return_value = 42

        config = {"presets": {"BAD-NAME": {"endpoint": "http://test"}}}
        result = self.validator.validate_presets_first_error(config, self.defaults, self.config_lines)

        assert result is not None
        assert result["line"] == 42
        mock_find_line.assert_called_once_with("presets.BAD-NAME", self.config_lines)

    def test_validate_presets_first_error_only(self):
        """Test that only the first error is returned when multiple exist."""
        config = {
            "presets": {
                "1INVALID": {"endpoint": "not-a-url"},  # Two errors here
                "2INVALID": {"model": ""},  # More errors here
            }
        }
        result = self.validator.validate_presets_first_error(config, self.defaults, self.config_lines)

        # Should only get the first error (invalid preset name)
        assert result is not None
        assert result["type"] == "invalid_preset_name"
        assert result["preset"] == "1INVALID"

    def test_validate_preset_missing_key_line_number_calculation(self):
        """Test line number calculation for missing key errors."""
        # Extended config lines with more detail
        config_lines = [
            "presets:",
            "  LOCAL:",
            "    endpoint: http://localhost:5000",
            "    # Missing model key should be added here",
            "  REMOTE:",
            "    endpoint: https://api.openai.com",
            "    model: gpt-4",
        ]

        config = {
            "presets": {
                "LOCAL": {
                    "endpoint": "http://localhost:5000",
                    # Missing model key
                },
                "REMOTE": self.defaults["presets"]["REMOTE"],
            }
        }

        with patch("enchant_book_manager.config_preset_validator.find_line_number") as mock_find_line:
            # Mock line number lookups
            def find_line_side_effect(path, lines):
                if path == "presets.LOCAL":
                    return 2
                elif path == "presets.LOCAL.endpoint":
                    return 3
                return None

            mock_find_line.side_effect = find_line_side_effect

            result = self.validator.validate_presets_first_error(config, self.defaults, config_lines)

            assert result is not None
            assert result["type"] == "missing_key"
            assert result["key"] == "model"
            assert result["line"] == 3  # Should suggest adding after the last existing key

    def test_validate_preset_zero_values(self):
        """Test validation with zero values for numeric fields."""
        config = {
            "presets": {
                "LOCAL": {
                    **self.defaults["presets"]["LOCAL"],
                    "max_tokens": 0,  # Zero should be invalid
                },
                "REMOTE": self.defaults["presets"]["REMOTE"],
            }
        }
        result = self.validator.validate_presets_first_error(config, self.defaults, self.config_lines)
        assert result is not None
        assert result["type"] == "invalid_value"
        assert result["key"] == "max_tokens"
        assert "must be a positive integer" in result["message"]

    def test_validate_preset_temperature_edge_cases(self):
        """Test temperature validation edge cases."""
        # Test temperature = 0.0 (valid)
        config = {
            "presets": {
                "LOCAL": {
                    **self.defaults["presets"]["LOCAL"],
                    "temperature": 0.0,
                },
                "REMOTE": self.defaults["presets"]["REMOTE"],
            }
        }
        result = self.validator.validate_presets_first_error(config, self.defaults, self.config_lines)
        assert result is None

        # Test temperature = 2.0 (valid edge)
        config["presets"]["LOCAL"]["temperature"] = 2.0
        result = self.validator.validate_presets_first_error(config, self.defaults, self.config_lines)
        assert result is None

        # Test temperature = 2.0001 (invalid)
        config["presets"]["LOCAL"]["temperature"] = 2.0001
        result = self.validator.validate_presets_first_error(config, self.defaults, self.config_lines)
        assert result is not None
        assert result["key"] == "temperature"
