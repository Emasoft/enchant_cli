#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test suite for config_utils module.
"""

import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from enchant_book_manager.config_utils import find_line_number


class TestFindLineNumber:
    """Test the find_line_number function."""

    def test_find_line_number_simple_key(self):
        """Test finding a simple top-level key."""
        config_lines = [
            "# Comment line",
            "key1: value1",
            "key2: value2",
            "key3: value3",
        ]

        assert find_line_number("key1", config_lines) == 2
        assert find_line_number("key2", config_lines) == 3
        assert find_line_number("key3", config_lines) == 4

    def test_find_line_number_nested_key(self):
        """Test finding nested keys."""
        config_lines = [
            "section1:",
            "  key1: value1",
            "  key2: value2",
            "section2:",
            "  key3: value3",
        ]

        assert find_line_number("section1", config_lines) == 1
        assert find_line_number("section1.key1", config_lines) == 2
        assert find_line_number("section1.key2", config_lines) == 3
        assert find_line_number("section2.key3", config_lines) == 5

    def test_find_line_number_deeply_nested(self):
        """Test finding deeply nested keys."""
        config_lines = ["level1:", "  level2:", "    level3:", "      key: value"]

        assert find_line_number("level1", config_lines) == 1
        assert find_line_number("level1.level2", config_lines) == 2
        assert find_line_number("level1.level2.level3", config_lines) == 3
        assert find_line_number("level1.level2.level3.key", config_lines) == 4

    def test_find_line_number_with_comments(self):
        """Test finding keys with comment lines interspersed."""
        config_lines = [
            "# Start of config",
            "key1: value1",
            "# Middle comment",
            "section:",
            "  # Nested comment",
            "  key2: value2",
        ]

        assert find_line_number("key1", config_lines) == 2
        assert find_line_number("section", config_lines) == 4
        assert find_line_number("section.key2", config_lines) == 6

    def test_find_line_number_not_found(self):
        """Test when key is not found."""
        config_lines = ["key1: value1", "section:", "  key2: value2"]

        assert find_line_number("nonexistent", config_lines) is None
        assert find_line_number("section.nonexistent", config_lines) is None
        assert find_line_number("key1.nested", config_lines) is None

    def test_find_line_number_empty_lines(self):
        """Test with empty lines in config."""
        config_lines = ["", "key1: value1", "", "section:", "", "  key2: value2", ""]

        assert find_line_number("key1", config_lines) == 2
        assert find_line_number("section", config_lines) == 4
        assert find_line_number("section.key2", config_lines) == 6

    def test_find_line_number_empty_config(self):
        """Test with empty config lines."""
        assert find_line_number("any.key", []) is None

    def test_find_line_number_none_config(self):
        """Test with None config lines."""
        assert find_line_number("any.key", None) is None

    def test_find_line_number_only_comments(self):
        """Test with config containing only comments."""
        config_lines = ["# Comment 1", "# Comment 2", "# Comment 3"]

        assert find_line_number("any.key", config_lines) is None

    def test_find_line_number_mixed_indentation(self):
        """Test with inconsistent indentation."""
        config_lines = [
            "section1:",
            "  key1: value1",  # 2 spaces
            "   key2: value2",  # 3 spaces (should not match)
            " key3: value3",  # 1 space (should not match)
        ]

        assert find_line_number("section1.key1", config_lines) == 2
        assert find_line_number("section1.key2", config_lines) is None  # Wrong indent
        assert find_line_number("section1.key3", config_lines) is None  # Wrong indent

    def test_find_line_number_with_spaces_in_values(self):
        """Test keys with spaces in values."""
        config_lines = [
            "key: value with spaces",
            "section:",
            "  key: another value with spaces",
        ]

        assert find_line_number("key", config_lines) == 1
        assert find_line_number("section.key", config_lines) == 3

    def test_find_line_number_yaml_list(self):
        """Test with YAML list syntax."""
        config_lines = ["items:", "  - item1", "  - item2", "key: value"]

        assert find_line_number("items", config_lines) == 1
        assert find_line_number("key", config_lines) == 4

    def test_find_line_number_partial_match(self):
        """Test that partial matches don't count."""
        config_lines = ["key: value", "key_extended: value", "prefix_key: value"]

        assert find_line_number("key", config_lines) == 1
        # Should not match key_extended or prefix_key

    def test_find_line_number_colon_in_value(self):
        """Test keys with colons in values."""
        config_lines = ['key: "value: with colon"', "url: http://example.com:8080"]

        assert find_line_number("key", config_lines) == 1
        assert find_line_number("url", config_lines) == 2

    def test_find_line_number_complex_nested_structure(self):
        """Test with complex nested structure."""
        config_lines = [
            "database:",
            "  connection:",
            "    host: localhost",
            "    port: 5432",
            "  credentials:",
            "    username: admin",
            "    password: secret",
        ]

        assert find_line_number("database", config_lines) == 1
        assert find_line_number("database.connection", config_lines) == 2
        assert find_line_number("database.connection.host", config_lines) == 3
        assert find_line_number("database.connection.port", config_lines) == 4
        assert find_line_number("database.credentials", config_lines) == 5
        assert find_line_number("database.credentials.username", config_lines) == 6
        assert find_line_number("database.credentials.password", config_lines) == 7

    def test_find_line_number_edge_cases(self):
        """Test various edge cases."""
        # Empty key
        assert find_line_number("", ["key: value"]) is None

        # Key with trailing dot
        assert find_line_number("key.", ["key: value"]) is None

        # Key with leading dot
        assert find_line_number(".key", ["key: value"]) is None

        # Multiple dots
        assert find_line_number("key..nested", ["key:", "  nested: value"]) is None

    def test_find_line_number_case_sensitive(self):
        """Test that key matching is case sensitive."""
        config_lines = ["Key: value1", "key: value2", "KEY: value3"]

        assert find_line_number("Key", config_lines) == 1
        assert find_line_number("key", config_lines) == 2
        assert find_line_number("KEY", config_lines) == 3

    def test_find_line_number_multiline_values(self):
        """Test with multiline YAML values."""
        config_lines = ["key1: |", "  This is a", "  multiline value", "key2: value"]

        assert find_line_number("key1", config_lines) == 1
        assert find_line_number("key2", config_lines) == 4

    def test_find_line_number_quoted_keys(self):
        """Test with quoted keys."""
        config_lines = [
            '"special.key": value',
            "'another.special': value",
            "normal_key: value",
        ]

        # Note: This function expects unquoted key names
        assert find_line_number("normal_key", config_lines) == 3
        # Quoted keys might not be found as expected
        assert find_line_number("special.key", config_lines) is None
