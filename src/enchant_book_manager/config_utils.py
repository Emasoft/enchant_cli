#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
# - Created new module for common configuration utilities
# - Extracted find_line_number method used by multiple modules
# - Provides shared utilities to reduce code duplication
#

"""
config_utils.py - Common utilities for ENCHANT configuration modules
"""


def find_line_number(key_path: str, config_lines: list[str]) -> int | None:
    """
    Find the line number of a configuration key in the YAML file.

    Args:
        key_path: Dot-separated path to key
        config_lines: Configuration file lines

    Returns:
        Line number or None if not found
    """
    if not config_lines:
        return None

    # Convert dot notation to YAML path
    keys = key_path.split(".")

    # Search for the key in the file
    for i, line in enumerate(config_lines, 1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        # Calculate indent level
        current_indent = len(line) - len(line.lstrip())

        # Check if this line matches our search path
        for j, key in enumerate(keys):
            expected_indent = j * 2  # YAML typically uses 2-space indent
            if current_indent == expected_indent and stripped.startswith(f"{key}:"):
                if j == len(keys) - 1:
                    return i
                break

    return None
