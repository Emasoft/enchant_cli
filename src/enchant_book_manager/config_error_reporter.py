#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
# - Created new module to handle error reporting
# - Extracted error reporting logic from config_validator.py
# - Contains methods for reporting different types of validation errors
#

"""
config_error_reporter.py - Configuration error reporting utilities for ENCHANT
"""

import yaml
from typing import Any
from pathlib import Path


class ConfigErrorReporter:
    """Reports configuration validation errors."""

    def report_single_error(self, error: dict[str, Any], config_lines: list[str]) -> None:
        """
        Report a single validation error.

        Args:
            error: Error information
            config_lines: Configuration file lines
        """
        line = error.get("line")
        if line is None:
            line = "unknown"

        if error["type"] == "unknown_key":
            print(f"\nline {line}: unknown or malformed key found. Ignoring.")
            if line != "unknown" and config_lines:
                line_idx = int(line) - 1
                if 0 <= line_idx < len(config_lines):
                    print(f"  {config_lines[line_idx].strip()}")

        elif error["type"] == "missing_key" or error["type"] == "missing_section":
            print(f"\nline {line}: {error['message']}")

        elif error["type"] == "invalid_preset_name":
            print(f"\nline {line}: {error['message']}")

        elif error["type"] in ["invalid_value", "invalid_type"]:
            print(f"\nline {line}: {error['message']}")

        elif error["type"] == "missing_required_preset":
            # This is handled separately with user prompt
            pass

        else:
            # Generic error reporting
            print(f"\nline {line}: {error['message']}")

    def report_yaml_error(self, error: yaml.YAMLError, config_path: Path) -> None:
        """
        Report YAML parsing errors with line information.

        Args:
            error: YAML parsing error
            config_path: Path to configuration file
        """
        print("\n" + "=" * 80)
        print("YAML PARSING ERROR")
        print("=" * 80)
        print(f"Failed to parse {config_path}")
        print()

        if hasattr(error, "problem_mark"):
            mark = error.problem_mark
            print(f"Error at line {mark.line + 1}, column {mark.column + 1}:")

            # Show the problematic line
            with open(config_path, "r") as f:
                lines = f.readlines()
                if mark.line < len(lines):
                    print(f"  {mark.line + 1}: {lines[mark.line].rstrip()}")
                    print(f"  {' ' * (len(str(mark.line + 1)) + 2)}{' ' * mark.column}^")

        print()
        print(f"Problem: {error.problem if hasattr(error, 'problem') else str(error)}")

        if hasattr(error, "note"):
            print(f"Note: {error.note}")

        print()
        print("Common YAML issues:")
        print("  - Indentation must be consistent (use spaces, not tabs)")
        print("  - String values with special characters should be quoted")
        print("  - Lists must start with '- ' (dash and space)")
        print("  - Colons in values must be quoted (e.g., 'http://example.com')")
        print()
        print("Fix the syntax error or delete the config file to regenerate defaults.")
        print("=" * 80)
