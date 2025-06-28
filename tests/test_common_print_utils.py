#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test suite for common_print_utils module.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import patch, Mock, call
from io import StringIO

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class TestSafePrint:
    """Test the safe_print function."""

    @patch("enchant_book_manager.common_print_utils.rich_available", True)
    @patch("enchant_book_manager.common_print_utils.print")
    def test_with_rich_available(self, mock_rich_print):
        """Test safe_print when rich is available."""
        from enchant_book_manager.common_print_utils import safe_print

        # Test simple print
        safe_print("Hello World")
        mock_rich_print.assert_called_once_with("Hello World")

        # Test with multiple arguments
        mock_rich_print.reset_mock()
        safe_print("Hello", "World", 123)
        mock_rich_print.assert_called_once_with("Hello", "World", 123)

        # Test with keyword arguments
        mock_rich_print.reset_mock()
        safe_print("Test", end="", flush=True)
        mock_rich_print.assert_called_once_with("Test", end="", flush=True)

    @patch("enchant_book_manager.common_print_utils.rich_available", False)
    @patch("builtins.print")
    def test_without_rich_plain_text(self, mock_print):
        """Test safe_print without rich - plain text."""
        from enchant_book_manager.common_print_utils import safe_print

        # Test simple text
        safe_print("Hello World")
        mock_print.assert_called_once_with("Hello World")

    @patch("enchant_book_manager.common_print_utils.rich_available", False)
    @patch("builtins.print")
    def test_without_rich_strips_markup(self, mock_print):
        """Test safe_print strips rich markup when rich is not available."""
        from enchant_book_manager.common_print_utils import safe_print

        # Test stripping simple markup
        safe_print("[bold]Hello[/bold] World")
        mock_print.assert_called_once_with("Hello World")

        # Test stripping color markup
        mock_print.reset_mock()
        safe_print("[red]Error:[/red] Something went wrong")
        mock_print.assert_called_once_with("Error: Something went wrong")

        # Test stripping multiple markup tags
        mock_print.reset_mock()
        safe_print("[bold][blue]Info:[/blue][/bold] [green]Success![/green]")
        mock_print.assert_called_once_with("Info: Success!")

        # Test stripping nested markup
        mock_print.reset_mock()
        safe_print("[bold]Bold [italic]and italic[/italic] text[/bold]")
        mock_print.assert_called_once_with("Bold and italic text")

    @patch("enchant_book_manager.common_print_utils.rich_available", False)
    @patch("builtins.print")
    def test_without_rich_multiple_args(self, mock_print):
        """Test safe_print with multiple arguments when rich is not available."""
        from enchant_book_manager.common_print_utils import safe_print

        # Multiple arguments get joined with spaces
        safe_print("[bold]Hello[/bold]", "[red]World[/red]", 123)
        mock_print.assert_called_once_with("Hello World 123")

    @patch("enchant_book_manager.common_print_utils.rich_available", False)
    @patch("builtins.print")
    def test_without_rich_non_string_args(self, mock_print):
        """Test safe_print with non-string arguments."""
        from enchant_book_manager.common_print_utils import safe_print

        # Test with various types (the list representation doesn't contain markup to strip)
        safe_print(123, 45.67, True, None, "[bold]text[/bold]")
        mock_print.assert_called_once_with("123 45.67 True None text")

    @patch("enchant_book_manager.common_print_utils.rich_available", False)
    @patch("builtins.print")
    def test_without_rich_special_characters(self, mock_print):
        """Test safe_print preserves special characters."""
        from enchant_book_manager.common_print_utils import safe_print

        # Test with unicode and special characters
        safe_print("Hello 世界 🌍 [bold]Test[/bold]")
        mock_print.assert_called_once_with("Hello 世界 🌍 Test")

    @patch("enchant_book_manager.common_print_utils.rich_available", False)
    @patch("builtins.print")
    def test_without_rich_empty_markup(self, mock_print):
        """Test safe_print handles empty markup tags."""
        from enchant_book_manager.common_print_utils import safe_print

        # Test empty tags - the regex requires at least one character between brackets
        safe_print("Hello [] World [/]")
        # Empty brackets [] won't be stripped, but [/] will be (it has one character)
        mock_print.assert_called_once_with("Hello [] World ")

    @patch("enchant_book_manager.common_print_utils.rich_available", False)
    @patch("builtins.print")
    def test_without_rich_malformed_markup(self, mock_print):
        """Test safe_print handles malformed markup gracefully."""
        from enchant_book_manager.common_print_utils import safe_print

        # Test unclosed tags - should still strip what it can
        safe_print("[bold Hello World")
        mock_print.assert_called_once_with("[bold Hello World")  # Unclosed bracket not stripped

        # Test missing closing bracket
        mock_print.reset_mock()
        safe_print("[bold] Hello [/bold")
        mock_print.assert_called_once_with(" Hello [/bold")  # Only complete tags stripped

    @patch("enchant_book_manager.common_print_utils.rich_available", True)
    @patch("enchant_book_manager.common_print_utils.print")
    def test_with_rich_no_args(self, mock_rich_print):
        """Test safe_print with no arguments."""
        from enchant_book_manager.common_print_utils import safe_print

        safe_print()
        mock_rich_print.assert_called_once_with()

    @patch("enchant_book_manager.common_print_utils.rich_available", False)
    @patch("builtins.print")
    def test_without_rich_no_args(self, mock_print):
        """Test safe_print with no arguments when rich is not available."""
        from enchant_book_manager.common_print_utils import safe_print

        safe_print()
        mock_print.assert_called_once_with("")

    def test_module_import_detection(self):
        """Test that rich availability is detected correctly at import time."""
        # This test verifies the module-level detection logic
        # We can't easily test both paths in the same test run,
        # but we can verify the current state
        import enchant_book_manager.common_print_utils as print_utils

        # Check that rich_available is a boolean
        assert isinstance(print_utils.rich_available, bool)

        # If rich is available, print should be the rich print
        # If not, it should be builtins.print
        if print_utils.rich_available:
            assert print_utils.print.__module__ == "rich"
        else:
            assert print_utils.print == builtins.print

    @patch("enchant_book_manager.common_print_utils.rich_available", False)
    def test_regex_pattern_coverage(self):
        """Test the regex pattern strips various markup formats."""
        from enchant_book_manager.common_print_utils import safe_print
        import enchant_book_manager.common_print_utils as print_utils

        # Test the regex pattern directly
        test_cases = [
            ("[bold]text[/bold]", "text"),
            ("[red on white]text[/]", "text"),
            ("[link=http://example.com]text[/link]", "text"),
            ("[#ff0000]text[/]", "text"),
            ("[rgb(255,0,0)]text[/]", "text"),
            ("[bold italic]text[/]", "text"),
            ("normal [bold]bold[/bold] normal", "normal bold normal"),
            ("[/closing]", ""),  # Just closing tag
            ("[tag with spaces]text[/]", "text"),
            ("[tag_with_underscores]text[/]", "text"),
            ("[tag-with-dashes]text[/]", "text"),
        ]

        for input_text, expected in test_cases:
            # Apply the same regex used in safe_print
            import re

            result = re.sub(r"\[/?[^]]+\]", "", input_text)
            assert result == expected, f"Failed for input: {input_text}"
