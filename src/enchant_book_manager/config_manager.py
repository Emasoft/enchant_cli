#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
# - Refactored into smaller modules (<10KB each)
# - Created config_schema.py for configuration template
# - Created config_loader.py for loading and merging logic
# - Created config_validator.py for validation logic
# - Created preset_manager.py for preset management
# - Main config_manager.py now acts as orchestrator
# - Maintained backward compatibility with same public API
#

# Copyright 2025 Emasoft
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
config_manager.py - Comprehensive configuration management for ENCHANT with presets support
"""

import os
import logging
from pathlib import Path
from typing import Any

from .config_loader import ConfigLoader
from .config_validator import ConfigValidator
from .preset_manager import PresetManager
from .config_args_handler import ConfigArgsHandler


class ConfigManager:
    """Manages configuration for ENCHANT system with presets support."""

    def __init__(
        self,
        config_path: Path | None = None,
        logger: logging.Logger | None = None,
    ):
        """
        Initialize configuration manager.

        Args:
            config_path: Path to configuration file (default: enchant_config.yml)
            logger: Logger instance
        """
        self.logger = logger or logging.getLogger(__name__)
        self.config_path = config_path or Path("enchant_config.yml")

        # Initialize components
        self.loader = ConfigLoader(self.config_path, self.logger)
        self.validator = ConfigValidator(self.logger)
        self.preset_manager = PresetManager(self.logger)
        self.args_handler = ConfigArgsHandler()

        # Load configuration
        self.config = self._load_config()

        # For backward compatibility
        self._config_lines = self.loader.get_config_lines()
        self.active_preset = self.preset_manager.active_preset

    def _load_config(self) -> dict[str, Any]:
        """Load configuration from file or create default."""
        # Load raw config
        config = self.loader.load_config()

        # Get defaults for validation
        defaults = self.loader.get_default_config()

        # Validate configuration - get FIRST error only
        first_error = self.validator.validate_config_first_error(config, defaults, self.loader.get_config_lines())

        if first_error:
            # Check if it's a restorable error (missing LOCAL or REMOTE preset)
            if first_error.get("can_restore"):
                if first_error["type"] == "missing_required_preset":
                    preset_name = first_error["preset"]
                    response = input(f"\nRequired preset '{preset_name}' is missing. " f"Restore default values? (y/n): ")
                    if response.lower() == "y":
                        default_presets = defaults.get("presets", {})
                        if "presets" not in config:
                            config["presets"] = {}
                        config["presets"][preset_name] = default_presets.get(preset_name, {})
                        self.logger.info(f"Restored default '{preset_name}' preset")
                        # Re-validate after restoration
                        first_error = self.validator.validate_config_first_error(config, defaults, self.loader.get_config_lines())

            # If there's still an error, report and exit
            if first_error:
                self.validator.report_single_error(first_error, self.loader.get_config_lines())
                import sys

                sys.exit(1)

        # Merge with defaults to ensure all keys exist
        return self.loader.merge_with_defaults(config)

    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation.

        Args:
            key_path: Dot-separated path (e.g., 'translation.local.endpoint')
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        keys = key_path.split(".")
        value = self.config

        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default

        return value

    def apply_preset(self, preset_name: str) -> bool:
        """
        Apply a preset configuration.

        Args:
            preset_name: Name of the preset to apply

        Returns:
            True if preset was applied successfully
        """
        result = self.preset_manager.apply_preset(preset_name, self.config)
        # Update local reference for backward compatibility
        self.active_preset = self.preset_manager.active_preset
        return result

    def get_preset_value(self, key: str, default: Any = None) -> Any:
        """
        Get value from active preset or default.

        Args:
            key: Key to retrieve from preset
            default: Default value if not found

        Returns:
            Value from preset or default
        """
        return self.preset_manager.get_preset_value(key, self.config, default)

    def get_available_presets(self) -> list[str]:
        """Get list of available presets."""
        return self.preset_manager.get_available_presets(self.config)

    def update_with_args(self, args: Any) -> dict[str, Any]:
        """
        Update configuration with command-line arguments.
        Command-line args take precedence over config file and presets.

        Args:
            args: Parsed command-line arguments

        Returns:
            Updated configuration dictionary
        """
        # Apply preset if specified
        if hasattr(args, "preset") and args.preset:
            self.apply_preset(args.preset)

        # Delegate to args handler
        return self.args_handler.update_config_with_args(self.config, args, self.preset_manager)

    def get_api_key(self, service: str) -> str | None:
        """
        Get API key for a service from config or environment.

        Args:
            service: Service name ('openrouter', 'openai')

        Returns:
            API key or None
        """
        # Check environment variables first
        env_vars = {"openrouter": "OPENROUTER_API_KEY", "openai": "OPENROUTER_API_KEY"}

        env_key = os.getenv(env_vars.get(service, ""))
        if env_key:
            return env_key

        # Then check config
        if service == "openrouter":
            api_key = self.get("translation.remote.api_key")
            return str(api_key) if api_key is not None else None
        elif service == "openai":
            api_key = self.get("novel_renaming.openai.api_key")
            return str(api_key) if api_key is not None else None

        return None


# Global config instance
_global_config = None


def get_config(config_path: Path | None = None) -> ConfigManager:
    """Get or create global configuration instance."""
    global _global_config
    if _global_config is None:
        _global_config = ConfigManager(config_path)
    return _global_config


def load_config(config_path: Path | None = None) -> dict[str, Any]:
    """Load configuration and return as dictionary."""
    return get_config(config_path).config
