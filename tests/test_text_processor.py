#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test suite for text_processor module.
"""

import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from enchant_book_manager.text_processor import (
    remove_excess_empty_lines,
    get_val,
    strip_urls,
    is_markdown,
    quick_replace,
)


class TestRemoveExcessEmptyLines:
    """Test the remove_excess_empty_lines function."""

    def test_no_empty_lines(self):
        """Test text with no empty lines."""
        text = "Line 1\nLine 2\nLine 3"
        result = remove_excess_empty_lines(text)
        assert result == text

    def test_single_empty_line(self):
        """Test text with single empty lines."""
        text = "Line 1\n\nLine 2\n\nLine 3"
        result = remove_excess_empty_lines(text)
        assert result == text

    def test_two_empty_lines(self):
        """Test text with two consecutive empty lines."""
        text = "Line 1\n\n\nLine 2"
        result = remove_excess_empty_lines(text)
        assert result == text

    def test_three_empty_lines(self):
        """Test text with exactly three empty lines (should not change)."""
        text = "Line 1\n\n\n\nLine 2"  # 4 newlines = 3 empty lines
        result = remove_excess_empty_lines(text)
        assert result == "Line 1\n\n\nLine 2"  # Should reduce to 3 newlines

    def test_many_empty_lines(self):
        """Test text with many consecutive empty lines."""
        text = "Line 1\n\n\n\n\n\n\nLine 2"  # 7 newlines
        result = remove_excess_empty_lines(text)
        assert result == "Line 1\n\n\nLine 2"  # Should reduce to 3 newlines

    def test_multiple_groups_of_empty_lines(self):
        """Test text with multiple groups of excessive empty lines."""
        text = "Line 1\n\n\n\n\nLine 2\n\n\n\n\n\n\nLine 3"
        result = remove_excess_empty_lines(text)
        assert result == "Line 1\n\n\nLine 2\n\n\nLine 3"

    def test_empty_string(self):
        """Test empty string."""
        assert remove_excess_empty_lines("") == ""

    def test_only_newlines(self):
        """Test string with only newlines."""
        text = "\n\n\n\n\n"
        result = remove_excess_empty_lines(text)
        assert result == "\n\n\n"


class TestGetVal:
    """Test the get_val function."""

    def test_valid_index(self):
        """Test getting value at valid index."""
        my_list = [1, 2, 3, 4, 5]
        assert get_val(my_list, 0) == 1
        assert get_val(my_list, 2) == 3
        assert get_val(my_list, 4) == 5

    def test_negative_index(self):
        """Test getting value at negative index."""
        my_list = [1, 2, 3, 4, 5]
        assert get_val(my_list, -1) == 5
        assert get_val(my_list, -3) == 3

    def test_out_of_bounds_positive(self):
        """Test index out of bounds (positive)."""
        my_list = [1, 2, 3]
        assert get_val(my_list, 3) is None
        assert get_val(my_list, 10) is None

    def test_out_of_bounds_negative(self):
        """Test index out of bounds (negative)."""
        my_list = [1, 2, 3]
        assert get_val(my_list, -4) is None
        assert get_val(my_list, -10) is None

    def test_custom_default(self):
        """Test custom default value."""
        my_list = [1, 2, 3]
        assert get_val(my_list, 5, default="missing") == "missing"
        assert get_val(my_list, -5, default=0) == 0

    def test_empty_list(self):
        """Test empty list."""
        assert get_val([], 0) is None
        assert get_val([], 0, default="empty") == "empty"

    def test_different_types(self):
        """Test with different data types."""
        my_list = ["a", {"key": "value"}, [1, 2], None]
        assert get_val(my_list, 0) == "a"
        assert get_val(my_list, 1) == {"key": "value"}
        assert get_val(my_list, 2) == [1, 2]
        assert get_val(my_list, 3) is None


class TestStripUrls:
    """Test the strip_urls function."""

    def test_strip_http_url(self):
        """Test stripping HTTP URLs."""
        text = "Visit http://example.com for more info"
        result = strip_urls(text)
        assert result == "Visit  for more info"

    def test_strip_https_url(self):
        """Test stripping HTTPS URLs."""
        text = "Secure site: https://secure.example.com/page"
        result = strip_urls(text)
        assert result == "Secure site: "

    def test_strip_email(self):
        """Test stripping email addresses."""
        text = "Contact us at info@example.com for details"
        result = strip_urls(text)
        assert result == "Contact us at  for details"

    def test_strip_multiple(self):
        """Test stripping multiple URLs and emails."""
        text = "Visit https://site1.com or http://site2.com. Email: admin@test.com"
        result = strip_urls(text)
        # The period after site2.com is part of the URL match and gets removed
        assert result == "Visit  or  Email: "

    def test_complex_url(self):
        """Test stripping complex URLs with paths and parameters."""
        text = "API docs: https://api.example.com/v1/docs?param=value#section"
        result = strip_urls(text)
        assert result == "API docs: "

    def test_no_urls_or_emails(self):
        """Test text without URLs or emails."""
        text = "This is plain text without any links"
        result = strip_urls(text)
        assert result == text

    def test_empty_string(self):
        """Test empty string."""
        assert strip_urls("") == ""

    def test_complex_email(self):
        """Test complex email addresses."""
        text = "Emails: user.name+tag@sub.domain.com and test_123@example.co.uk"
        result = strip_urls(text)
        assert result == "Emails:  and "


class TestIsMarkdown:
    """Test the is_markdown function."""

    def test_bold_asterisk(self):
        """Test bold text with asterisks."""
        assert is_markdown("This is *bold* text") is True
        assert is_markdown("Multiple *bold* words *here*") is True

    def test_italic_underscore(self):
        """Test italic text with underscores."""
        assert is_markdown("This is _italic_ text") is True

    def test_link_markdown(self):
        """Test markdown links."""
        # URLs are stripped first, so the markdown pattern needs to work without URLs
        assert is_markdown("[Link text](url)") is True
        # With URL, it gets stripped so markdown may not be detected
        assert is_markdown("Click [here]()") is True  # After URL stripping

    def test_inline_code(self):
        """Test inline code."""
        assert is_markdown("Use `code` for this") is True
        assert is_markdown("The `function()` returns") is True

    def test_code_block(self):
        """Test code blocks."""
        assert is_markdown("```python code here```") is True
        assert is_markdown("```\ncode\n```") is True

    def test_plain_text(self):
        """Test plain text without markdown."""
        assert is_markdown("This is plain text") is False
        assert is_markdown("No special formatting here") is False

    def test_multiline_markdown(self):
        """Test markdown with newlines."""
        text = "First line\n*bold text*\nLast line"
        assert is_markdown(text) is True

    def test_url_not_markdown(self):
        """Test that URLs are stripped before markdown check."""
        # URLs should be stripped, so these shouldn't be detected as markdown
        assert is_markdown("Visit http://example.com/path_with_underscores") is False
        assert is_markdown("Email: test_user@example.com") is False

    def test_empty_string(self):
        """Test empty string."""
        assert is_markdown("") is False

    def test_edge_cases(self):
        """Test edge cases."""
        assert is_markdown("*") is False  # Just asterisk
        assert is_markdown("_") is False  # Just underscore
        # Empty link pattern []() actually matches the markdown regex
        assert is_markdown("[]()") is True  # Empty link is valid markdown syntax


class TestQuickReplace:
    """Test the quick_replace function."""

    def test_simple_replace(self):
        """Test simple text replacement."""
        text = "Hello world"
        result = quick_replace(text, "world", "universe")
        assert result == "Hello universe"

    def test_multiple_occurrences(self):
        """Test replacing multiple occurrences."""
        text = "The cat and the cat sat on the mat"
        result = quick_replace(text, "cat", "dog")
        assert result == "The dog and the dog sat on the mat"

    def test_case_insensitive_default(self):
        """Test case insensitive replacement (default)."""
        text = "Hello WORLD and world"
        result = quick_replace(text, "world", "universe")
        assert result == "Hello universe and universe"

    def test_case_sensitive(self):
        """Test case sensitive replacement."""
        text = "Hello WORLD and world"
        result = quick_replace(text, "world", "universe", case_insensitive=False)
        assert result == "Hello WORLD and universe"

    def test_special_characters(self):
        """Test replacement with special regex characters."""
        text = "Price is $10.99 (special offer)"
        result = quick_replace(text, "$10.99", "$5.99")
        assert result == "Price is $5.99 (special offer)"

    def test_special_characters_in_pattern(self):
        """Test pattern with special regex characters."""
        text = "Match [this] and (that)"
        result = quick_replace(text, "[this]", "[replaced]")
        assert result == "Match [replaced] and (that)"

    def test_empty_string(self):
        """Test empty string replacement."""
        assert quick_replace("", "test", "replace") == ""
        # Replacing empty string matches at every position, so it inserts replacement everywhere
        # This is expected regex behavior when pattern is empty
        result = quick_replace("test", "", "X")
        assert "X" in result  # Will have X inserted between each character

    def test_no_match(self):
        """Test when pattern doesn't match."""
        text = "Hello world"
        result = quick_replace(text, "universe", "cosmos")
        assert result == text

    def test_replacement_with_backreference(self):
        """Test that replacement doesn't interpret backreferences."""
        text = "Hello world"
        result = quick_replace(text, "world", "$1")
        assert result == "Hello $1"  # Should be literal $1, not a backreference

    def test_chinese_text(self):
        """Test with Chinese characters."""
        text = "这是中文文本"
        result = quick_replace(text, "中文", "英文")
        assert result == "这是英文文本"

    def test_mixed_content(self):
        """Test with mixed content."""
        text = "Replace THIS and this but not th1s"
        result = quick_replace(text, "this", "that")
        assert result == "Replace that and that but not th1s"
