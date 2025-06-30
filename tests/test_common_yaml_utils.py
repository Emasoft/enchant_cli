#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test suite for common_yaml_utils module.
"""

import pytest
import yaml
from pathlib import Path
from unittest.mock import Mock, patch, mock_open
import logging
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from enchant_book_manager.common_yaml_utils import (
    load_safe_yaml,
    save_safe_yaml,
    merge_yaml_configs,
    validate_yaml_schema,
)


class TestLoadSafeYaml:
    """Test the load_safe_yaml function."""

    def test_load_valid_yaml(self, tmp_path):
        """Test loading a valid YAML file."""
        yaml_file = tmp_path / "test.yaml"
        yaml_content = {"key1": "value1", "key2": {"nested": "value2"}}
        yaml_file.write_text(yaml.dump(yaml_content))

        result = load_safe_yaml(yaml_file)

        assert result == yaml_content
        assert isinstance(result, dict)

    def test_load_empty_yaml(self, tmp_path):
        """Test loading an empty YAML file."""
        yaml_file = tmp_path / "empty.yaml"
        yaml_file.write_text("")

        result = load_safe_yaml(yaml_file)

        assert result == {}

    def test_load_yaml_with_none(self, tmp_path):
        """Test loading YAML file that contains None/null."""
        yaml_file = tmp_path / "none.yaml"
        yaml_file.write_text("null")

        result = load_safe_yaml(yaml_file)

        assert result == {}

    def test_file_not_found(self):
        """Test loading non-existent file."""
        with pytest.raises(ValueError, match="YAML file not found"):
            load_safe_yaml("/non/existent/file.yaml")

    def test_invalid_yaml_syntax(self, tmp_path):
        """Test loading file with invalid YAML syntax."""
        yaml_file = tmp_path / "invalid.yaml"
        yaml_file.write_text("key: value\n- invalid mix of dict and list")

        with pytest.raises(ValueError, match="Error parsing YAML file"):
            load_safe_yaml(yaml_file)

    def test_non_dict_root(self, tmp_path):
        """Test loading YAML with non-dictionary root."""
        yaml_file = tmp_path / "list.yaml"
        yaml_file.write_text("- item1\n- item2")

        with pytest.raises(ValueError, match="YAML file must contain a dictionary at the root level"):
            load_safe_yaml(yaml_file)

    def test_with_path_string(self, tmp_path):
        """Test loading with string path instead of Path object."""
        yaml_file = tmp_path / "test.yaml"
        yaml_content = {"test": "value"}
        yaml_file.write_text(yaml.dump(yaml_content))

        result = load_safe_yaml(str(yaml_file))

        assert result == yaml_content

    def test_unicode_content(self, tmp_path):
        """Test loading YAML with Unicode content."""
        yaml_file = tmp_path / "unicode.yaml"
        yaml_content = {"title": "修炼至尊", "author": "张三"}
        yaml_file.write_text(yaml.dump(yaml_content, allow_unicode=True))

        result = load_safe_yaml(yaml_file)

        assert result == yaml_content

    def test_permission_error(self, tmp_path):
        """Test handling permission errors."""
        yaml_file = tmp_path / "test.yaml"
        yaml_file.write_text("key: value")
        yaml_file.chmod(0o000)  # Remove all permissions

        try:
            with pytest.raises(ValueError, match="Error loading YAML file"):
                load_safe_yaml(yaml_file)
        finally:
            yaml_file.chmod(0o644)  # Restore permissions for cleanup

    def test_complex_yaml_structure(self, tmp_path):
        """Test loading complex YAML structures."""
        yaml_file = tmp_path / "complex.yaml"
        yaml_content = {
            "top_level": {
                "nested": {
                    "deep": {
                        "value": "test",
                        "list": [1, 2, 3],
                        "bool": True,
                        "float": 3.14,
                    }
                }
            }
        }
        yaml_file.write_text(yaml.dump(yaml_content))

        result = load_safe_yaml(yaml_file)

        assert result == yaml_content


class TestSaveSafeYaml:
    """Test the save_safe_yaml function."""

    def test_save_simple_dict(self, tmp_path):
        """Test saving a simple dictionary."""
        yaml_file = tmp_path / "output.yaml"
        data = {"key1": "value1", "key2": 123}

        save_safe_yaml(data, yaml_file)

        assert yaml_file.exists()
        loaded = yaml.safe_load(yaml_file.read_text())
        assert loaded == data

    def test_save_with_create_dirs(self, tmp_path):
        """Test saving with directory creation."""
        yaml_file = tmp_path / "sub" / "dir" / "output.yaml"
        data = {"test": "value"}

        save_safe_yaml(data, yaml_file, create_dirs=True)

        assert yaml_file.exists()
        assert yaml_file.parent.exists()

    def test_save_without_create_dirs(self, tmp_path):
        """Test saving without directory creation fails."""
        yaml_file = tmp_path / "nonexistent" / "output.yaml"
        data = {"test": "value"}

        with pytest.raises(ValueError, match="Error saving YAML file"):
            save_safe_yaml(data, yaml_file, create_dirs=False)

    def test_save_unicode_data(self, tmp_path):
        """Test saving Unicode data."""
        yaml_file = tmp_path / "unicode.yaml"
        data = {"title": "修炼至尊", "author": "张三"}

        save_safe_yaml(data, yaml_file)

        # Verify Unicode is preserved
        content = yaml_file.read_text(encoding="utf-8")
        assert "修炼至尊" in content
        assert "张三" in content

    def test_save_complex_structure(self, tmp_path):
        """Test saving complex nested structures."""
        yaml_file = tmp_path / "complex.yaml"
        data = {
            "config": {
                "nested": {
                    "list": [1, 2, {"inner": "value"}],
                    "bool": True,
                    "none": None,
                }
            }
        }

        save_safe_yaml(data, yaml_file)

        loaded = yaml.safe_load(yaml_file.read_text())
        assert loaded == data

    def test_save_with_string_path(self, tmp_path):
        """Test saving with string path instead of Path object."""
        yaml_file = tmp_path / "string_path.yaml"
        data = {"test": "value"}

        save_safe_yaml(data, str(yaml_file))

        assert yaml_file.exists()

    def test_save_permission_error(self, tmp_path):
        """Test handling permission errors during save."""
        yaml_dir = tmp_path / "readonly"
        yaml_dir.mkdir()
        yaml_dir.chmod(0o444)  # Read-only directory
        yaml_file = yaml_dir / "test.yaml"

        try:
            with pytest.raises(ValueError, match="Error saving YAML file"):
                save_safe_yaml({"test": "value"}, yaml_file)
        finally:
            yaml_dir.chmod(0o755)  # Restore permissions

    def test_save_non_serializable_data(self, tmp_path):
        """Test saving data that cannot be serialized to YAML."""
        yaml_file = tmp_path / "bad_data.yaml"

        # Create a non-serializable object
        class NonSerializable:
            pass

        data = {"object": NonSerializable()}

        with pytest.raises(ValueError, match="Error serializing data to YAML"):
            save_safe_yaml(data, yaml_file)

    def test_overwrite_existing_file(self, tmp_path):
        """Test overwriting an existing file."""
        yaml_file = tmp_path / "existing.yaml"
        yaml_file.write_text("old: data")

        new_data = {"new": "data"}
        save_safe_yaml(new_data, yaml_file)

        loaded = yaml.safe_load(yaml_file.read_text())
        assert loaded == new_data
        assert "old" not in loaded


class TestMergeYamlConfigs:
    """Test the merge_yaml_configs function."""

    def test_merge_simple_dicts(self):
        """Test merging simple dictionaries."""
        base = {"key1": "value1", "key2": "value2"}
        override = {"key2": "new_value2", "key3": "value3"}

        result = merge_yaml_configs(base, override)

        assert result == {"key1": "value1", "key2": "new_value2", "key3": "value3"}

    def test_merge_nested_dicts(self):
        """Test merging nested dictionaries."""
        base = {"level1": {"level2": {"key1": "value1", "key2": "value2"}}}
        override = {"level1": {"level2": {"key2": "new_value2", "key3": "value3"}}}

        result = merge_yaml_configs(base, override)

        assert result == {"level1": {"level2": {"key1": "value1", "key2": "new_value2", "key3": "value3"}}}

    def test_override_replaces_non_dict(self):
        """Test that non-dict values are replaced, not merged."""
        base = {"key1": {"nested": "value"}, "key2": [1, 2, 3]}
        override = {"key1": "simple_value", "key2": [4, 5]}

        result = merge_yaml_configs(base, override)

        assert result == {
            "key1": "simple_value",  # Replaced entirely
            "key2": [4, 5],  # Lists are replaced, not merged
        }

    def test_empty_configs(self):
        """Test merging with empty configs."""
        base = {"key": "value"}

        # Empty override
        result = merge_yaml_configs(base, {})
        assert result == base

        # Empty base
        result = merge_yaml_configs({}, base)
        assert result == base

        # Both empty
        result = merge_yaml_configs({}, {})
        assert result == {}

    def test_deep_nesting(self):
        """Test merging deeply nested structures."""
        base = {"a": {"b": {"c": {"d": "value1", "e": "value2"}}}}
        override = {"a": {"b": {"c": {"d": "new_value1", "f": "value3"}, "g": "value4"}}}

        result = merge_yaml_configs(base, override)

        assert result["a"]["b"]["c"]["d"] == "new_value1"
        assert result["a"]["b"]["c"]["e"] == "value2"
        assert result["a"]["b"]["c"]["f"] == "value3"
        assert result["a"]["b"]["g"] == "value4"

    def test_base_not_modified(self):
        """Test that base config is not modified."""
        base = {"key": {"nested": "value"}}
        base_copy = {"key": {"nested": "value"}}
        override = {"key": {"nested": "new_value", "extra": "data"}}

        result = merge_yaml_configs(base, override)

        # Base should remain unchanged
        assert base == base_copy
        # Result should have merged values
        assert result["key"]["nested"] == "new_value"
        assert result["key"]["extra"] == "data"


class TestValidateYamlSchema:
    """Test the validate_yaml_schema function."""

    def test_valid_schema(self):
        """Test validation with matching schema."""
        data = {"name": "test", "age": 25, "active": True}
        schema = {"name": str, "age": int, "active": bool}

        result = validate_yaml_schema(data, schema)

        assert result is None  # No error

    def test_missing_required_key(self):
        """Test validation with missing required key."""
        data = {"name": "test"}
        schema = {"name": str, "age": int}

        result = validate_yaml_schema(data, schema)

        assert result == "Missing required key: age"

    def test_wrong_type(self):
        """Test validation with wrong type."""
        data = {
            "name": "test",
            "age": "25",  # String instead of int
        }
        schema = {"name": str, "age": int}

        result = validate_yaml_schema(data, schema)

        assert result == "Invalid type for age: expected int, got str"

    def test_nested_dict_type(self):
        """Test validation with nested dictionary."""
        data = {"config": {"host": "localhost", "port": 8080}}
        schema = {"config": dict}

        result = validate_yaml_schema(data, schema)

        assert result is None  # Valid

    def test_list_type(self):
        """Test validation with list type."""
        data = {"items": [1, 2, 3]}
        schema = {"items": list}

        result = validate_yaml_schema(data, schema)

        assert result is None  # Valid

    def test_extra_keys_allowed(self):
        """Test that extra keys in data are allowed."""
        data = {"name": "test", "age": 25, "extra": "allowed"}
        schema = {"name": str, "age": int}

        result = validate_yaml_schema(data, schema)

        assert result is None  # Extra keys are okay

    def test_empty_schema(self):
        """Test validation with empty schema."""
        data = {"any": "data"}
        schema = {}

        result = validate_yaml_schema(data, schema)

        assert result is None  # No requirements
