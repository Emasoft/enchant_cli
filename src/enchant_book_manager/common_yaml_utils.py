#!/usr/bin/env python3
# -*- coding: utf-8 -*-

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
Common YAML utility functions for safe loading and saving.

This module provides utilities for safely handling YAML files with proper
error handling and validation.
"""

import yaml
from pathlib import Path
from typing import Any
import logging

logger = logging.getLogger(__name__)


def load_safe_yaml(yaml_path: str | Path) -> dict[str, Any]:
    """
    Safely load YAML file with error handling.

    Args:
        yaml_path: Path to the YAML file

    Returns:
        Dictionary containing the loaded YAML data

    Raises:
        ValueError: If the file cannot be loaded or parsed
    """
    yaml_path = Path(yaml_path)

    if not yaml_path.exists():
        raise ValueError(f"YAML file not found: {yaml_path}")

    try:
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if data is None:
            return {}

        if not isinstance(data, dict):
            raise ValueError(f"YAML file must contain a dictionary at the root level, got {type(data)}")

        return data

    except yaml.YAMLError as e:
        raise ValueError(f"Error parsing YAML file {yaml_path}: {e}") from e
    except Exception as e:
        raise ValueError(f"Error loading YAML file {yaml_path}: {e}") from e


def save_safe_yaml(data: dict[str, Any], yaml_path: str | Path, create_dirs: bool = True) -> None:
    """
    Safely save data to YAML file with error handling.

    Args:
        data: Dictionary to save as YAML
        yaml_path: Path where to save the YAML file
        create_dirs: Whether to create parent directories if they don't exist

    Raises:
        ValueError: If the data cannot be serialized or saved
    """
    yaml_path = Path(yaml_path)

    if create_dirs:
        yaml_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(yaml_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, default_flow_style=False, allow_unicode=True)

    except yaml.YAMLError as e:
        raise ValueError(f"Error serializing data to YAML: {e}") from e
    except Exception as e:
        raise ValueError(f"Error saving YAML file {yaml_path}: {e}") from e


def merge_yaml_configs(base_config: dict[str, Any], override_config: dict[str, Any]) -> dict[str, Any]:
    """
    Deep merge two YAML configurations, with override taking precedence.

    Args:
        base_config: Base configuration dictionary
        override_config: Override configuration dictionary

    Returns:
        Merged configuration dictionary
    """
    result = base_config.copy()

    for key, value in override_config.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            # Recursively merge nested dictionaries
            result[key] = merge_yaml_configs(result[key], value)
        else:
            # Override value
            result[key] = value

    return result


def validate_yaml_schema(data: dict[str, Any], schema: dict[str, Any]) -> str | None:
    """
    Validate YAML data against a simple schema.

    Args:
        data: YAML data to validate
        schema: Schema definition (simplified, not JSON Schema)

    Returns:
        None if valid, error message if invalid
    """
    # This is a simplified validation - could be enhanced with jsonschema
    for key, expected_type in schema.items():
        if key not in data:
            return f"Missing required key: {key}"

        if not isinstance(data[key], expected_type):
            return f"Invalid type for {key}: expected {expected_type.__name__}, got {type(data[key]).__name__}"

    return None
