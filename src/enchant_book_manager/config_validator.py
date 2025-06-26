#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
# - Created new module to handle configuration validation
# - Extracted validation logic from config_manager.py
# - Contains methods for validating config structure and values
# - Refactored to use separate preset validator for preset-specific validation
#

"""
config_validator.py - Configuration validation utilities for ENCHANT
"""

import logging
from typing import Any

from .config_error_reporter import ConfigErrorReporter
from .config_preset_validator import ConfigPresetValidator
from .config_utils import find_line_number


class ConfigValidator:
    """Validates configuration structure and values."""

    def __init__(self, logger: logging.Logger | None = None):
        """
        Initialize configuration validator.

        Args:
            logger: Logger instance
        """
        self.logger = logger or logging.getLogger(__name__)
        self.error_reporter = ConfigErrorReporter()
        self.preset_validator = ConfigPresetValidator()

    def validate_config_first_error(self, config: dict[str, Any], defaults: dict[str, Any], config_lines: list[str]) -> dict[str, Any] | None:
        """
        Validate configuration and return only the FIRST error found.

        Args:
            config: Configuration to validate
            defaults: Default configuration for reference
            config_lines: Configuration file lines for error reporting

        Returns:
            First error found or None if valid
        """
        # Check for unknown keys at top level
        valid_top_keys = set(defaults.keys())

        for key in config.keys():
            if key not in valid_top_keys:
                line_num = find_line_number(key, config_lines)
                return {
                    "type": "unknown_key",
                    "key": key,
                    "line": line_num,
                    "message": f"Unknown or malformed key '{key}' found. Ignoring.",
                    "context": "top-level",
                }

        # Check presets for errors FIRST (before checking other sections)
        if "presets" in config:
            preset_error = self.preset_validator.validate_presets_first_error(config, defaults, config_lines)
            if preset_error:
                return preset_error

        # Check required top-level sections
        required_sections = {
            "translation": "Translation settings (API endpoints, models, etc.)",
            "text_processing": "Text processing settings (split methods, character limits)",
            "novel_renaming": "Novel metadata extraction settings",
            "epub": "EPUB generation settings",
            "batch": "Batch processing settings",
            "icloud": "iCloud synchronization settings",
            "pricing": "API cost tracking settings",
            "logging": "Logging configuration",
        }

        for section, description in required_sections.items():
            if section not in config:
                # Find where to add it
                last_line = len(config_lines)
                for i, line in enumerate(config_lines):
                    if line.strip() and not line.strip().startswith("#"):
                        last_line = i + 1

                return {
                    "type": "missing_section",
                    "section": section,
                    "description": description,
                    "line": last_line,
                    "message": f"Expected section '{section}' not found. Please add the {section} section after line {last_line}",
                }

        # Validate specific values in sections
        if "translation" in config:
            if "service" in config["translation"]:
                if config["translation"]["service"] not in ["local", "remote"]:
                    line_num = find_line_number("translation.service", config_lines)
                    return {
                        "type": "invalid_value",
                        "path": "translation.service",
                        "value": config["translation"]["service"],
                        "valid_values": ["local", "remote"],
                        "line": line_num,
                        "message": f"Invalid value '{config['translation']['service']}' for translation.service. Must be 'local' or 'remote'",
                    }

        return None

    def report_single_error(self, error: dict[str, Any], config_lines: list[str]) -> None:
        """
        Report a single validation error.

        Args:
            error: Error information
            config_lines: Configuration file lines
        """
        self.error_reporter.report_single_error(error, config_lines)
