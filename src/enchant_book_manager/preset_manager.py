#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
# - Created new module to handle preset management functionality
# - Extracted preset-related methods from config_manager.py
# - Manages preset application and value retrieval
#

"""
preset_manager.py - Preset management utilities for ENCHANT
"""

import re
import copy
import logging
from typing import Any


class PresetManager:
    """Manages configuration presets."""

    def __init__(self, logger: logging.Logger | None = None):
        """
        Initialize preset manager.

        Args:
            logger: Logger instance
        """
        self.logger = logger or logging.getLogger(__name__)
        self.active_preset: str | None = None

    def apply_preset(self, preset_name: str, config: dict[str, Any]) -> bool:
        """
        Apply a preset configuration.

        Args:
            preset_name: Name of the preset to apply
            config: Configuration dictionary

        Returns:
            True if preset was applied successfully

        Raises:
            SystemExit: If preset not found
        """
        # Validate preset name format
        valid_name_pattern = re.compile(r"^[A-Za-z0-9_]+$")
        if not valid_name_pattern.match(preset_name):
            self.logger.error(f"Invalid preset name '{preset_name}'. " "Preset names must contain only alphanumeric characters and underscores.")
            return False

        presets = config.get("presets", {})
        if preset_name not in presets:
            available = list(presets.keys())
            self.logger.error(f"Preset '{preset_name}' not found. Available presets: {', '.join(available)}")
            # Exit with error for non-existent preset
            import sys

            sys.exit(1)

        self.active_preset = preset_name

        # Apply preset values to config
        # Note: We don't modify the original config, but track the active preset
        # The get_preset_value method will handle retrieving values

        self.logger.info(f"Applied preset: {preset_name}")
        return True

    def get_preset_value(self, key: str, config: dict[str, Any], default: Any = None) -> Any:
        """
        Get value from active preset or default.

        Args:
            key: Key to retrieve from preset
            config: Configuration dictionary
            default: Default value if not found

        Returns:
            Value from preset or default
        """
        if self.active_preset and "presets" in config:
            preset = config["presets"].get(self.active_preset, {})
            if key in preset:
                return preset[key]
        return default

    def get_available_presets(self, config: dict[str, Any]) -> list[str]:
        """
        Get list of available presets.

        Args:
            config: Configuration dictionary

        Returns:
            List of preset names
        """
        return list(config.get("presets", {}).keys())

    def update_config_with_preset(self, config: dict[str, Any], preset_values: dict[str, Any]) -> dict[str, Any]:
        """
        Update configuration with preset values.

        Args:
            config: Configuration dictionary to update
            preset_values: Preset values to apply

        Returns:
            Updated configuration
        """
        updated_config = copy.deepcopy(config)

        for key, value in preset_values.items():
            if key in [
                "connection_timeout",
                "response_timeout",
                "max_retries",
                "retry_wait_base",
                "retry_wait_max",
                "temperature",
                "max_tokens",
                "double_pass",
                "model",
                "endpoint",
                "max_chars_per_chunk",
            ]:
                # Map preset keys to config paths
                if key == "max_chars_per_chunk":
                    self._set_config_value(updated_config, "text_processing.max_chars_per_chunk", value)
                elif key in ["model", "endpoint", "connection_timeout", "response_timeout"]:
                    service = "remote" if self.active_preset == "REMOTE" else "local"
                    if key == "response_timeout":
                        self._set_config_value(updated_config, f"translation.{service}.timeout", value)
                    elif key == "connection_timeout":
                        self._set_config_value(
                            updated_config,
                            f"translation.{service}.connection_timeout",
                            value,
                        )
                    else:
                        self._set_config_value(updated_config, f"translation.{service}.{key}", value)
                else:
                    self._set_config_value(updated_config, f"translation.{key}", value)

        return updated_config

    def _set_config_value(self, config: dict[str, Any], path: str, value: Any) -> None:
        """
        Set a value in the config dictionary using dot notation.

        Args:
            config: Configuration dictionary
            path: Dot-separated path to key
            value: Value to set
        """
        keys = path.split(".")
        target = config
        for key in keys[:-1]:
            if key not in target:
                target[key] = {}
            target = target[key]
        target[keys[-1]] = value

    def get_active_preset(self) -> str | None:
        """
        Get the currently active preset name.

        Returns:
            Active preset name or None
        """
        return self.active_preset
