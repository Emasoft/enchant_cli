#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
# - Created new module to handle command-line arguments configuration
# - Extracted argument handling logic from config_manager.py
# - Manages mapping of CLI args to config values
#

"""
config_args_handler.py - Command-line arguments handling for ENCHANT configuration
"""

import copy
from typing import Any


class ConfigArgsHandler:
    """Handles updating configuration with command-line arguments."""

    def update_config_with_args(self, config: dict[str, Any], args: Any, preset_manager: Any) -> dict[str, Any]:
        """
        Update configuration with command-line arguments.
        Command-line args take precedence over config file and presets.

        Args:
            config: Configuration dictionary
            args: Parsed command-line arguments
            preset_manager: Preset manager instance

        Returns:
            Updated configuration dictionary
        """
        config = copy.deepcopy(config)

        # Handle double-pass arguments
        double_pass = None
        if hasattr(args, "double_pass") and args.double_pass:
            double_pass = True
        elif hasattr(args, "no_double_pass") and args.no_double_pass:
            double_pass = False

        # Map command-line arguments to config keys
        arg_mapping = {
            "encoding": "text_processing.default_encoding",
            "max_chars": "text_processing.max_chars_per_chunk",
            "remote": "translation.service",  # True -> 'remote', False -> 'local'
            "epub": "epub.enabled",
            "batch": "batch.enabled",
            "max_workers": "batch.max_workers",
            "connection_timeout": "translation.connection_timeout",
            "response_timeout": "translation.response_timeout",
            "max_retries": "translation.max_retries",
            "retry_wait_base": "translation.retry_wait_base",
            "retry_wait_max": "translation.retry_wait_max",
            "temperature": "translation.temperature",
            "max_tokens": "translation.max_tokens",
            "model": "translation.model",
            "endpoint": "translation.endpoint",
        }

        # First apply preset values if active
        if preset_manager.active_preset:
            preset = config.get("presets", {}).get(preset_manager.active_preset, {})
            config = preset_manager.update_config_with_preset(config, preset)

        # Then override with command-line arguments
        for arg_name, config_path in arg_mapping.items():
            if hasattr(args, arg_name):
                value = getattr(args, arg_name)
                if value is not None:
                    # Special handling for 'remote' flag
                    if arg_name == "remote":
                        value = "remote" if value else "local"

                    # Set value in config
                    self._set_config_value(config, config_path, value)

        # Handle double_pass separately after other args
        if double_pass is not None:
            self._set_config_value(config, "translation.double_pass", double_pass)

        return config

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
