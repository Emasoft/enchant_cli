#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
# - Created new module to handle preset validation
# - Extracted preset validation logic from config_validator.py
# - Contains methods for validating preset structure and values
#

"""
config_preset_validator.py - Preset validation utilities for ENCHANT
"""

import re
from typing import Any

from .config_utils import find_line_number


class ConfigPresetValidator:
    """Validates configuration presets."""

    def validate_presets_first_error(self, config: dict[str, Any], defaults: dict[str, Any], config_lines: list[str]) -> dict[str, Any] | None:
        """
        Validate presets and return only the FIRST error found.

        Args:
            config: Configuration to validate
            defaults: Default configuration for reference
            config_lines: Configuration file lines for error reporting

        Returns:
            First error found or None if valid
        """
        presets = config.get("presets", {})
        if not presets:
            return None

        # First check for unknown keys in presets section
        default_presets = defaults.get("presets", {})

        # Get all valid preset keys from default presets
        valid_preset_keys: set[str] = set()
        for preset in default_presets.values():
            if isinstance(preset, dict):
                valid_preset_keys.update(preset.keys())

        # Validate preset names first
        valid_name_pattern = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
        for preset_name in presets.keys():
            if not valid_name_pattern.match(preset_name):
                line_num = find_line_number(f"presets.{preset_name}", config_lines)
                error_msg = "Preset names must start with a letter or underscore, followed by letters, numbers, or underscores"
                if preset_name[0].isdigit():
                    error_msg = "invalid preset name. Names must not begin with a number!"
                elif "-" in preset_name:
                    error_msg = "invalid preset name. Names cannot contain hyphens (-). Use underscores (_) instead"
                elif " " in preset_name:
                    error_msg = "invalid preset name. Names cannot contain spaces. Use underscores (_) instead"

                return {
                    "type": "invalid_preset_name",
                    "preset": preset_name,
                    "message": error_msg,
                    "line": line_num,
                }

        # Check for required presets (LOCAL and REMOTE)
        for required_preset in ["LOCAL", "REMOTE"]:
            if required_preset not in presets:
                return {
                    "type": "missing_required_preset",
                    "preset": required_preset,
                    "message": f"Required preset '{required_preset}' is missing",
                    "can_restore": True,
                }

        # Now validate each preset's contents
        for preset_name, preset_data in presets.items():
            if not isinstance(preset_data, dict):
                line_num = find_line_number(f"presets.{preset_name}", config_lines)
                return {
                    "type": "invalid_preset_type",
                    "preset": preset_name,
                    "message": f"Preset '{preset_name}' must be a dictionary/mapping",
                    "line": line_num,
                }

            # Check for unknown keys in this preset
            for key in preset_data.keys():
                if key not in valid_preset_keys:
                    line_num = find_line_number(f"presets.{preset_name}.{key}", config_lines)
                    return {
                        "type": "unknown_key",
                        "key": key,
                        "preset": preset_name,
                        "line": line_num,
                        "message": "unknown or malformed key found. Ignoring.",
                        "context": f"preset {preset_name}",
                    }

            # Check for missing required keys
            required_keys = [
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

            # For custom presets, only check basic required keys
            if preset_name not in ["LOCAL", "REMOTE"]:
                required_keys = ["endpoint", "model"]

            for key in required_keys:
                if key not in preset_data:
                    # Find the line where this key should be added
                    preset_line = find_line_number(f"presets.{preset_name}", config_lines)
                    # Look for the last key in this preset
                    last_key_line = preset_line if preset_line is not None else 0
                    for existing_key in preset_data.keys():
                        key_line = find_line_number(f"presets.{preset_name}.{existing_key}", config_lines)
                        if key_line is not None and key_line > last_key_line:
                            last_key_line = key_line

                    return {
                        "type": "missing_key",
                        "preset": preset_name,
                        "key": key,
                        "line": last_key_line,
                        "message": f"expected key '{key}' not found. Please add the {key} key after line {last_key_line}",
                    }

            # Validate values for each key
            value_error = self._validate_preset_values_first_error(preset_name, preset_data, config_lines)
            if value_error:
                return value_error

        return None

    def _validate_preset_values_first_error(self, preset_name: str, preset_data: dict[str, Any], config_lines: list[str]) -> dict[str, Any] | None:
        """
        Validate preset values and return only the FIRST error found.

        Args:
            preset_name: Name of preset being validated
            preset_data: Preset data to validate
            config_lines: Configuration file lines for error reporting

        Returns:
            First error found or None if valid
        """
        # Check each value in order
        for key, value in preset_data.items():
            line_num = find_line_number(f"presets.{preset_name}.{key}", config_lines)

            # Validate based on key type
            if key in [
                "connection_timeout",
                "response_timeout",
                "max_retries",
                "max_chars_per_chunk",
                "max_tokens",
            ]:
                try:
                    int_val = int(value)
                    if int_val <= 0:
                        return {
                            "type": "invalid_value",
                            "preset": preset_name,
                            "key": key,
                            "value": value,
                            "line": line_num,
                            "message": f"invalid value for {key}. {key} value must be a positive integer",
                        }
                except (ValueError, TypeError):
                    return {
                        "type": "invalid_type",
                        "preset": preset_name,
                        "key": key,
                        "value": value,
                        "line": line_num,
                        "message": f"invalid value for {key}. {key} must be an integer",
                    }

            elif key in ["retry_wait_base", "retry_wait_max", "temperature"]:
                try:
                    float_val = float(value)
                    if float_val < 0:
                        return {
                            "type": "invalid_value",
                            "preset": preset_name,
                            "key": key,
                            "value": value,
                            "line": line_num,
                            "message": f"invalid value for {key}. {key} must be non-negative",
                        }
                    if key == "temperature" and float_val > 2.0:
                        return {
                            "type": "invalid_value",
                            "preset": preset_name,
                            "key": key,
                            "value": value,
                            "line": line_num,
                            "message": "invalid value for temperature. Temperature must be between 0.0 and 2.0",
                        }
                except (ValueError, TypeError):
                    return {
                        "type": "invalid_type",
                        "preset": preset_name,
                        "key": key,
                        "value": value,
                        "line": line_num,
                        "message": f"invalid value for {key}. {key} must be a number",
                    }

            elif key == "double_pass":
                if not isinstance(value, bool):
                    return {
                        "type": "invalid_type",
                        "preset": preset_name,
                        "key": key,
                        "value": value,
                        "line": line_num,
                        "message": "invalid value for double_pass. double_pass value can only be true or false",
                    }

            elif key == "endpoint":
                if not isinstance(value, str):
                    return {
                        "type": "invalid_type",
                        "preset": preset_name,
                        "key": key,
                        "value": value,
                        "line": line_num,
                        "message": "invalid value for endpoint. Endpoint must be a string URL",
                    }
                elif not (value.startswith("http://") or value.startswith("https://")):
                    return {
                        "type": "invalid_value",
                        "preset": preset_name,
                        "key": key,
                        "value": value,
                        "line": line_num,
                        "message": "api endpoint url not a valid openai compatible endpoint format!",
                    }

            elif key == "model":
                if not isinstance(value, str) or not value.strip():
                    return {
                        "type": "invalid_value",
                        "preset": preset_name,
                        "key": key,
                        "value": value,
                        "line": line_num,
                        "message": "invalid value for model. Model must be a non-empty string",
                    }

        return None
