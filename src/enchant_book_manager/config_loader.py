#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
# - Created new module to handle configuration loading and merging
# - Extracted loading logic from config_manager.py
# - Handles file I/O, YAML parsing, and config merging
#

"""
config_loader.py - Configuration loading and merging utilities for ENCHANT
"""

import yaml
import logging
from pathlib import Path
from typing import Any

from .common_yaml_utils import load_safe_yaml, merge_yaml_configs
from .config_schema import DEFAULT_CONFIG_TEMPLATE
from .config_error_reporter import ConfigErrorReporter
from .config_utils import find_line_number


class ConfigLoader:
    """Handles loading and merging of configuration files."""

    def __init__(self, config_path: Path, logger: logging.Logger | None = None):
        """
        Initialize configuration loader.

        Args:
            config_path: Path to configuration file
            logger: Logger instance
        """
        self.config_path = config_path
        self.logger = logger or logging.getLogger(__name__)
        self._config_lines: list[str] = []  # Store file lines for error reporting
        self.error_reporter = ConfigErrorReporter()

    def load_config(self) -> dict[str, Any]:
        """
        Load configuration from file or create default.

        Returns:
            Configuration dictionary

        Raises:
            SystemExit: If configuration has errors
        """
        if not self.config_path.exists():
            self.logger.info(f"Configuration file not found. Creating default at: {self.config_path}")
            self._create_default_config()

        try:
            # First, try to load and parse the YAML
            with open(self.config_path, "r", encoding="utf-8") as f:
                file_content = f.read()

            # Use common YAML loading utility
            config = load_safe_yaml(self.config_path)

            if config is None:
                self.logger.warning("Configuration file is empty. Using defaults.")
                return self.get_default_config()

            # Store file lines for error reporting
            self._config_lines = file_content.split("\n")

            return config

        except yaml.YAMLError as e:
            self.error_reporter.report_yaml_error(e, self.config_path)
            import sys

            sys.exit(1)
        except Exception as e:
            self.logger.error(f"Error loading configuration: {e}")
            raise

    def _create_default_config(self) -> None:
        """Create default configuration file."""
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                f.write(DEFAULT_CONFIG_TEMPLATE)
            self.logger.info("Default configuration file created successfully.")
        except Exception as e:
            self.logger.error(f"Failed to create configuration file: {e}")
            raise

    def get_default_config(self) -> dict[str, Any]:
        """
        Get default configuration as dictionary.

        Returns:
            Default configuration dictionary
        """
        result = yaml.safe_load(DEFAULT_CONFIG_TEMPLATE)
        return result if isinstance(result, dict) else {}

    def merge_with_defaults(self, config: dict[str, Any]) -> dict[str, Any]:
        """
        Merge user config with defaults to ensure all keys exist.

        Args:
            config: User configuration

        Returns:
            Merged configuration
        """
        defaults = self.get_default_config()
        return merge_yaml_configs(defaults, config)

    def get_config_lines(self) -> list[str]:
        """
        Get configuration file lines for error reporting.

        Returns:
            List of configuration file lines
        """
        return self._config_lines

    def find_line_number(self, key_path: str) -> int | None:
        """
        Find the line number of a configuration key in the YAML file.

        Args:
            key_path: Dot-separated path to key

        Returns:
            Line number or None if not found
        """
        return find_line_number(key_path, self._config_lines)
