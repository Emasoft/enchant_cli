#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test suite for chapter_validators module.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from enchant_book_manager.chapter_validators import (
    has_part_notation,
    parse_num,
    is_valid_chapter_line,
)


class TestHasPartNotation:
    """Test the has_part_notation function."""

    def test_fraction_patterns(self):
        """Test detection of fraction patterns."""
        assert has_part_notation("Chapter 1 1/3")
        assert has_part_notation("Chapter 1 [1/3]")
        assert has_part_notation("Chapter 1 (1 of 3)")
        assert has_part_notation("Chapter 1 (1 out of 3)")
        assert has_part_notation("Part 2/5")
        assert has_part_notation("[3/4]")

    def test_part_word_patterns(self):
        """Test detection of part word patterns."""
        assert has_part_notation("Chapter 1 Part 1")
        assert has_part_notation("Chapter 1 part one")
        assert has_part_notation("Chapter 1 PART TWO")
        assert has_part_notation("Chapter 1 Pt. 1")
        assert has_part_notation("Chapter 1 pt 2")
        assert has_part_notation("Title Pt One")

    def test_dash_patterns(self):
        """Test detection of dash patterns."""
        assert has_part_notation("Chapter 1 - 1")
        assert has_part_notation("Chapter 1 - 2")
        assert has_part_notation("Title - 3")

    def test_roman_numeral_patterns(self):
        """Test detection of Roman numeral patterns."""
        assert has_part_notation("Part I")
        assert has_part_notation("Part IV")
        assert has_part_notation("pt. V")
        assert has_part_notation("PT X")
        assert has_part_notation("Chapter 1 - I")
        assert has_part_notation("Title - II")

    def test_no_part_notation(self):
        """Test titles without part notation."""
        assert not has_part_notation("Chapter 1")
        assert not has_part_notation("Chapter One")
        assert not has_part_notation("The Beginning")
        assert not has_part_notation("Introduction")
        assert not has_part_notation("Prologue")
        assert not has_part_notation("Louis XIV")  # Roman numeral but not a part

    def test_edge_cases(self):
        """Test edge cases for has_part_notation."""
        # Empty and None
        assert not has_part_notation("")
        assert not has_part_notation(None)

        # Whitespace
        assert not has_part_notation("   ")

        # Case variations
        assert has_part_notation("CHAPTER 1 PART 1")
        assert has_part_notation("chapter 1 part 1")
        assert has_part_notation("ChApTeR 1 PaRt 1")

        # Multiple patterns in one title
        assert has_part_notation("Chapter 1 Part 1 (1/3)")
        assert has_part_notation("Chapter 1 - 1 [1/3]")

    def test_performance_early_return(self):
        """Test that function returns early on first match."""
        # Create a mock to verify early return behavior
        with patch("enchant_book_manager.chapter_validators.PART_PATTERNS") as mock_patterns:
            # Create mock patterns where first one matches
            pattern1 = Mock()
            pattern1.search.return_value = True  # First pattern matches
            pattern2 = Mock()
            pattern2.search.return_value = True  # Should not be called

            mock_patterns.__iter__.return_value = [pattern1, pattern2]

            result = has_part_notation("Test title")

            assert result is True
            pattern1.search.assert_called_once_with("Test title")
            pattern2.search.assert_not_called()  # Should not reach second pattern


class TestParseNum:
    """Test the parse_num function."""

    def test_parse_arabic_numbers(self):
        """Test parsing Arabic numerals."""
        assert parse_num("1") == 1
        assert parse_num("42") == 42
        assert parse_num("100") == 100
        assert parse_num("999") == 999

    def test_parse_roman_numerals(self):
        """Test parsing Roman numerals."""
        assert parse_num("I") == 1
        assert parse_num("IV") == 4
        assert parse_num("V") == 5
        assert parse_num("IX") == 9
        assert parse_num("X") == 10
        assert parse_num("XIV") == 14
        assert parse_num("XX") == 20
        assert parse_num("L") == 50
        assert parse_num("C") == 100

    def test_parse_word_numbers(self):
        """Test parsing word numbers."""
        assert parse_num("one") == 1
        assert parse_num("five") == 5
        assert parse_num("ten") == 10
        assert parse_num("twenty") == 20
        assert parse_num("twenty-one") == 21
        assert parse_num("fifty") == 50
        assert parse_num("ninety-nine") == 99

    def test_case_insensitive(self):
        """Test case insensitive parsing."""
        assert parse_num("ONE") == 1
        assert parse_num("One") == 1
        assert parse_num("TwEnTy") == 20
        assert parse_num("iv") == 4
        assert parse_num("IV") == 4

    def test_none_and_empty(self):
        """Test handling of None and empty strings."""
        assert parse_num(None) is None
        assert parse_num("") is None

    def test_invalid_inputs(self):
        """Test invalid inputs return None."""
        assert parse_num("invalid") is None
        assert parse_num("abc") is None
        assert parse_num("abc123") is None  # Numbers must be at start

    def test_partial_parsing(self):
        """Test parse_num extracts numbers from start of string."""
        assert parse_num("123abc") == 123  # Extracts leading digits
        assert parse_num("1.5") == 15  # Treats decimal as two digits
        assert parse_num("one hundred") == 100  # Parses compound word numbers

    def test_whitespace_handling(self):
        """Test handling of whitespace."""
        # parse_num doesn't strip whitespace - returns None
        assert parse_num("  1  ") is None
        assert parse_num(" twenty ") is None
        assert parse_num("\tIV\t") is None

        # Only works without whitespace
        assert parse_num("1") == 1
        assert parse_num("twenty") == 20
        assert parse_num("IV") == 4


class TestIsValidChapterLine:
    """Test the is_valid_chapter_line function."""

    def test_chapter_at_start(self):
        """Test chapter word at start of line."""
        assert is_valid_chapter_line("Chapter 1")
        assert is_valid_chapter_line("Chapter One")
        assert is_valid_chapter_line("CHAPTER 42")
        assert is_valid_chapter_line("chapter 5: The Beginning")

    def test_chapter_after_special_chars(self):
        """Test chapter word after special characters."""
        assert is_valid_chapter_line("### Chapter 1")
        assert is_valid_chapter_line("*** Chapter 5")
        assert is_valid_chapter_line("> Chapter 10")
        assert is_valid_chapter_line("§ Chapter 15")
        assert is_valid_chapter_line("[Chapter 20]")
        assert is_valid_chapter_line("(Chapter 25)")
        assert is_valid_chapter_line("{Chapter 30}")
        assert is_valid_chapter_line("| Chapter 35")
        assert is_valid_chapter_line("- Chapter 40")
        assert is_valid_chapter_line("– Chapter 45")
        assert is_valid_chapter_line("— Chapter 50")
        assert is_valid_chapter_line("• Chapter 55")
        assert is_valid_chapter_line("~ Chapter 60")
        assert is_valid_chapter_line("/ Chapter 65")

    def test_chapter_in_quotes(self):
        """Test chapter word inside quotes is invalid."""
        assert not is_valid_chapter_line('"Chapter 1" he said')
        assert not is_valid_chapter_line("'Chapter 1' was the title")
        assert not is_valid_chapter_line('"In Chapter 1, we learn..."')
        assert not is_valid_chapter_line("'The Chapter' begins")

    def test_chapter_mid_sentence(self):
        """Test chapter word mid-sentence is invalid."""
        assert not is_valid_chapter_line("In this chapter we learn")
        assert not is_valid_chapter_line("The chapter begins with")
        assert not is_valid_chapter_line("Read chapter 5 carefully")
        assert not is_valid_chapter_line("This is chapter one")

    def test_no_chapter_word(self):
        """Test lines without chapter word."""
        # When no chapter word, let regex decide
        assert is_valid_chapter_line("Part 1")
        assert is_valid_chapter_line("Section 5")
        assert is_valid_chapter_line("1. Introduction")
        assert is_valid_chapter_line("Prologue")

    def test_edge_cases(self):
        """Test edge cases."""
        # Empty and whitespace
        assert is_valid_chapter_line("")
        assert is_valid_chapter_line("   ")

        # Mixed case
        assert is_valid_chapter_line("ChApTeR 1")
        assert is_valid_chapter_line("CHAPTER ONE")

        # Special quote handling
        assert not is_valid_chapter_line('"Chapter')  # Unclosed quote
        assert is_valid_chapter_line('Chapter"')  # Quote after chapter

        # Chapter at very end
        assert not is_valid_chapter_line("This is a chapter")
        assert not is_valid_chapter_line("Read the chapter")

    def test_complex_scenarios(self):
        """Test complex real-world scenarios."""
        # Dialogue examples
        assert not is_valid_chapter_line('"Look at Chapter 5," she said.')
        assert not is_valid_chapter_line("'Chapter 1 is important,' he replied.")
        assert not is_valid_chapter_line('"Chapter One: The Beginning" was written on the door.')

        # Valid chapter headings with formatting
        assert is_valid_chapter_line("***Chapter 1: The Journey Begins***")
        assert is_valid_chapter_line("---Chapter 42---")
        assert is_valid_chapter_line("### Chapter 7: Lucky Number")

        # Mixed content
        assert is_valid_chapter_line("Chapter 1 - 'The Beginning'")  # Chapter not in quotes
        assert not is_valid_chapter_line("He said 'Chapter 1' loudly")  # Chapter in quotes

    def test_whitespace_variations(self):
        """Test various whitespace scenarios."""
        assert is_valid_chapter_line("   Chapter 1")  # Leading spaces
        assert is_valid_chapter_line("Chapter 1   ")  # Trailing spaces
        assert is_valid_chapter_line("   Chapter   1   ")  # Multiple spaces
        assert is_valid_chapter_line("\tChapter 1")  # Tab
        assert is_valid_chapter_line("  ***  Chapter 1")  # Spaces around special chars
