#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test suite for config_error_reporter module.
"""

import pytest
import yaml
from pathlib import Path
from unittest.mock import Mock, patch, mock_open
import sys
import io

sys.path.insert(0, str(Path(__file__).parent.parent))

from enchant_book_manager.config_error_reporter import ConfigErrorReporter


class TestConfigErrorReporter:
    """Test the ConfigErrorReporter class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.reporter = ConfigErrorReporter()

    @patch("builtins.print")
    def test_report_unknown_key_with_line(self, mock_print):
        """Test reporting unknown key error with line information."""
        error = {"type": "unknown_key", "line": 10, "message": "Unknown key"}
        config_lines = [
            "line 1",
            "line 2",
            "line 3",
            "line 4",
            "line 5",
            "line 6",
            "line 7",
            "line 8",
            "line 9",
            "  invalid_key: value",  # Line 10
            "line 11",
        ]

        self.reporter.report_single_error(error, config_lines)

        # Verify print was called with expected messages
        calls = mock_print.call_args_list
        assert len(calls) == 2
        assert "line 10: unknown or malformed key found. Ignoring." in calls[0][0][0]
        assert "invalid_key: value" in calls[1][0][0]

    @patch("builtins.print")
    def test_report_unknown_key_no_line(self, mock_print):
        """Test reporting unknown key error without line information."""
        error = {"type": "unknown_key", "line": None, "message": "Unknown key"}
        config_lines = ["line 1", "line 2"]

        self.reporter.report_single_error(error, config_lines)

        mock_print.assert_called_once_with("\nline unknown: unknown or malformed key found. Ignoring.")

    @patch("builtins.print")
    def test_report_unknown_key_invalid_line_index(self, mock_print):
        """Test reporting unknown key error with out-of-bounds line index."""
        error = {
            "type": "unknown_key",
            "line": 100,  # Out of bounds
            "message": "Unknown key",
        }
        config_lines = ["line 1", "line 2"]

        self.reporter.report_single_error(error, config_lines)

        # Should only print the error message, not the line content
        mock_print.assert_called_once_with("\nline 100: unknown or malformed key found. Ignoring.")

    @patch("builtins.print")
    def test_report_missing_key(self, mock_print):
        """Test reporting missing key error."""
        error = {
            "type": "missing_key",
            "line": 5,
            "message": "Missing required key: api_key",
        }
        config_lines = []

        self.reporter.report_single_error(error, config_lines)

        mock_print.assert_called_once_with("\nline 5: Missing required key: api_key")

    @patch("builtins.print")
    def test_report_missing_section(self, mock_print):
        """Test reporting missing section error."""
        error = {
            "type": "missing_section",
            "line": 1,
            "message": "Missing required section: translation",
        }
        config_lines = []

        self.reporter.report_single_error(error, config_lines)

        mock_print.assert_called_once_with("\nline 1: Missing required section: translation")

    @patch("builtins.print")
    def test_report_invalid_preset_name(self, mock_print):
        """Test reporting invalid preset name error."""
        error = {
            "type": "invalid_preset_name",
            "line": 25,
            "message": "Invalid preset name: UNKNOWN",
        }
        config_lines = []

        self.reporter.report_single_error(error, config_lines)

        mock_print.assert_called_once_with("\nline 25: Invalid preset name: UNKNOWN")

    @patch("builtins.print")
    def test_report_invalid_value(self, mock_print):
        """Test reporting invalid value error."""
        error = {
            "type": "invalid_value",
            "line": 15,
            "message": "Invalid value for temperature: must be between 0 and 1",
        }
        config_lines = []

        self.reporter.report_single_error(error, config_lines)

        mock_print.assert_called_once_with("\nline 15: Invalid value for temperature: must be between 0 and 1")

    @patch("builtins.print")
    def test_report_invalid_type(self, mock_print):
        """Test reporting invalid type error."""
        error = {
            "type": "invalid_type",
            "line": 20,
            "message": "Invalid type for max_tokens: expected int, got str",
        }
        config_lines = []

        self.reporter.report_single_error(error, config_lines)

        mock_print.assert_called_once_with("\nline 20: Invalid type for max_tokens: expected int, got str")

    @patch("builtins.print")
    def test_report_missing_required_preset(self, mock_print):
        """Test that missing_required_preset errors are silently skipped."""
        error = {
            "type": "missing_required_preset",
            "line": 1,
            "message": "Missing required preset",
        }
        config_lines = []

        self.reporter.report_single_error(error, config_lines)

        # Should not print anything for this error type
        mock_print.assert_not_called()

    @patch("builtins.print")
    def test_report_generic_error(self, mock_print):
        """Test reporting generic/unknown error type."""
        error = {
            "type": "custom_error",
            "line": 30,
            "message": "Some custom error message",
        }
        config_lines = []

        self.reporter.report_single_error(error, config_lines)

        mock_print.assert_called_once_with("\nline 30: Some custom error message")

    @patch("builtins.print")
    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data="line1\nline2\n  bad_yaml:\nline4",
    )
    def test_report_yaml_error_with_mark(self, mock_file, mock_print):
        """Test reporting YAML error with problem mark."""
        # Create a mock YAML error with problem mark
        error = Mock(spec=yaml.YAMLError)
        error.problem = "mapping values are not allowed here"
        error.note = None

        problem_mark = Mock()
        problem_mark.line = 2  # 0-indexed, so line 3
        problem_mark.column = 10
        error.problem_mark = problem_mark

        config_path = Path("/test/config.yml")

        self.reporter.report_yaml_error(error, config_path)

        # Verify the error report structure
        print_calls = [str(call) for call in mock_print.call_args_list]
        all_output = " ".join(print_calls)

        # Check key elements are printed
        assert "=" * 80 in all_output
        assert "YAML PARSING ERROR" in all_output
        assert "Failed to parse /test/config.yml" in all_output
        assert "Error at line 3, column 11:" in all_output
        assert "3:   bad_yaml:" in all_output
        assert "^" in all_output  # Error pointer
        assert "mapping values are not allowed here" in all_output
        assert "Common YAML issues:" in all_output

    @patch("builtins.print")
    def test_report_yaml_error_without_mark(self, mock_print):
        """Test reporting YAML error without problem mark."""
        error = yaml.YAMLError("Generic YAML error")
        config_path = Path("/test/config.yml")

        self.reporter.report_yaml_error(error, config_path)

        # Verify basic error structure is printed
        print_calls = [str(call) for call in mock_print.call_args_list]
        all_output = " ".join(print_calls)

        assert "YAML PARSING ERROR" in all_output
        assert "Failed to parse /test/config.yml" in all_output
        assert "Generic YAML error" in all_output
        assert "Common YAML issues:" in all_output

    @patch("builtins.print")
    @patch("builtins.open", new_callable=mock_open, read_data="line1\nline2\nline3")
    def test_report_yaml_error_with_note(self, mock_file, mock_print):
        """Test reporting YAML error with note."""
        error = Mock(spec=yaml.YAMLError)
        error.problem = "found undefined alias"
        error.note = "Check for & and * characters"

        problem_mark = Mock()
        problem_mark.line = 1
        problem_mark.column = 5
        error.problem_mark = problem_mark

        config_path = Path("/test/config.yml")

        self.reporter.report_yaml_error(error, config_path)

        # Verify note is included
        print_calls = [str(call) for call in mock_print.call_args_list]
        all_output = " ".join(print_calls)
        assert "Note: Check for & and * characters" in all_output

    @patch("builtins.print")
    @patch("builtins.open", new_callable=mock_open, read_data="short")
    def test_report_yaml_error_line_out_of_bounds(self, mock_file, mock_print):
        """Test reporting YAML error when line number exceeds file length."""
        error = Mock(spec=yaml.YAMLError)
        error.problem = "unexpected end of file"
        error.note = None

        problem_mark = Mock()
        problem_mark.line = 10  # Beyond file length
        problem_mark.column = 0
        error.problem_mark = problem_mark

        config_path = Path("/test/config.yml")

        self.reporter.report_yaml_error(error, config_path)

        # Should handle gracefully without crashing
        print_calls = [str(call) for call in mock_print.call_args_list]
        all_output = " ".join(print_calls)
        assert "Error at line 11, column 1:" in all_output
        # Should not print the line content since it's out of bounds

    def test_empty_config_lines(self):
        """Test handling empty config lines list."""
        error = {"type": "unknown_key", "line": 1, "message": "Unknown key"}
        config_lines = []

        # Should not raise exception
        with patch("builtins.print"):
            self.reporter.report_single_error(error, config_lines)

    @patch("builtins.print")
    def test_whitespace_handling_in_config_lines(self, mock_print):
        """Test that whitespace is properly stripped from config lines."""
        error = {"type": "unknown_key", "line": 1, "message": "Unknown key"}
        config_lines = ["  \t  whitespace_line  \n  "]

        self.reporter.report_single_error(error, config_lines)

        # Check that whitespace was stripped
        calls = mock_print.call_args_list
        assert len(calls) == 2
        # The code adds two spaces prefix, then the stripped line
        assert calls[1][0][0] == "  whitespace_line"
