#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test suite for epub_constants module.
"""

import pytest
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from enchant_book_manager.epub_constants import (
    ENCODING,
    MIMETYPE,
    WORD_NUMS,
    FILENAME_RE,
    _SINGLE,
    _TENS,
    _SCALES,
    _ROMAN,
    roman_to_int,
    words_to_int,
    parse_num,
)


class TestEpubConstants:
    """Test EPUB constants definitions."""

    def test_encoding_constant(self):
        """Test ENCODING constant."""
        assert ENCODING == "utf-8"
        assert isinstance(ENCODING, str)

    def test_mimetype_constant(self):
        """Test MIMETYPE constant."""
        assert MIMETYPE == "application/epub+zip"
        assert isinstance(MIMETYPE, str)

    def test_word_nums_constant(self):
        """Test WORD_NUMS constant contains expected word numbers."""
        assert isinstance(WORD_NUMS, str)

        # Check basic numbers
        for num in ["one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten"]:
            assert num in WORD_NUMS

        # Check teens
        for num in ["eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen"]:
            assert num in WORD_NUMS

        # Check tens
        for num in ["twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]:
            assert num in WORD_NUMS

        # Check scales
        assert "hundred" in WORD_NUMS
        assert "thousand" in WORD_NUMS

    def test_filename_regex(self):
        """Test FILENAME_RE pattern matching."""
        assert isinstance(FILENAME_RE, re.Pattern)

        # Test valid filename
        match = FILENAME_RE.match("The Great Novel by John Doe - Chapter 5.txt")
        assert match is not None
        assert match.group("title") == "The Great Novel"
        assert match.group("author") == "John Doe"
        assert match.group("num") == "5"

        # Test case insensitive
        match = FILENAME_RE.match("Book Title by Author Name - CHAPTER 10.txt")
        assert match is not None
        assert match.group("num") == "10"

        # Test non-matching patterns
        assert FILENAME_RE.match("Book.txt") is None
        assert FILENAME_RE.match("Book by Author.txt") is None
        assert FILENAME_RE.match("Book - Chapter 5.txt") is None

    def test_single_numbers_dict(self):
        """Test _SINGLE dictionary contains correct mappings."""
        assert isinstance(_SINGLE, dict)
        assert len(_SINGLE) == 20  # 0-19

        # Check some mappings
        assert _SINGLE["zero"] == 0
        assert _SINGLE["one"] == 1
        assert _SINGLE["five"] == 5
        assert _SINGLE["ten"] == 10
        assert _SINGLE["fifteen"] == 15
        assert _SINGLE["nineteen"] == 19

    def test_tens_dict(self):
        """Test _TENS dictionary contains correct mappings."""
        assert isinstance(_TENS, dict)
        assert len(_TENS) == 8  # 20-90

        # Check mappings
        assert _TENS["twenty"] == 20
        assert _TENS["thirty"] == 30
        assert _TENS["forty"] == 40
        assert _TENS["fifty"] == 50
        assert _TENS["sixty"] == 60
        assert _TENS["seventy"] == 70
        assert _TENS["eighty"] == 80
        assert _TENS["ninety"] == 90

    def test_scales_dict(self):
        """Test _SCALES dictionary contains correct mappings."""
        assert isinstance(_SCALES, dict)
        assert len(_SCALES) == 2

        assert _SCALES["hundred"] == 100
        assert _SCALES["thousand"] == 1000

    def test_roman_dict(self):
        """Test _ROMAN dictionary contains correct mappings."""
        assert isinstance(_ROMAN, dict)
        assert len(_ROMAN) == 7

        # Check Roman numeral mappings
        assert _ROMAN["i"] == 1
        assert _ROMAN["v"] == 5
        assert _ROMAN["x"] == 10
        assert _ROMAN["l"] == 50
        assert _ROMAN["c"] == 100
        assert _ROMAN["d"] == 500
        assert _ROMAN["m"] == 1000


class TestRomanToInt:
    """Test roman_to_int function."""

    def test_basic_roman_numerals(self):
        """Test basic single Roman numerals."""
        assert roman_to_int("I") == 1
        assert roman_to_int("V") == 5
        assert roman_to_int("X") == 10
        assert roman_to_int("L") == 50
        assert roman_to_int("C") == 100
        assert roman_to_int("D") == 500
        assert roman_to_int("M") == 1000

    def test_lowercase_roman_numerals(self):
        """Test lowercase Roman numerals."""
        assert roman_to_int("i") == 1
        assert roman_to_int("v") == 5
        assert roman_to_int("x") == 10
        assert roman_to_int("xl") == 40

    def test_additive_notation(self):
        """Test Roman numerals using additive notation."""
        assert roman_to_int("II") == 2
        assert roman_to_int("III") == 3
        assert roman_to_int("VI") == 6
        assert roman_to_int("VII") == 7
        assert roman_to_int("VIII") == 8
        assert roman_to_int("XI") == 11
        assert roman_to_int("XII") == 12
        assert roman_to_int("XIII") == 13
        assert roman_to_int("XV") == 15
        assert roman_to_int("XX") == 20
        assert roman_to_int("XXX") == 30

    def test_subtractive_notation(self):
        """Test Roman numerals using subtractive notation."""
        assert roman_to_int("IV") == 4
        assert roman_to_int("IX") == 9
        assert roman_to_int("XL") == 40
        assert roman_to_int("XC") == 90
        assert roman_to_int("CD") == 400
        assert roman_to_int("CM") == 900

    def test_complex_roman_numerals(self):
        """Test complex Roman numerals."""
        assert roman_to_int("XIV") == 14
        assert roman_to_int("XIX") == 19
        assert roman_to_int("XLIV") == 44
        assert roman_to_int("XLIX") == 49
        assert roman_to_int("XCIX") == 99
        assert roman_to_int("MCMXCIV") == 1994
        assert roman_to_int("MMXXIV") == 2024

    def test_invalid_roman_numeral(self):
        """Test invalid Roman numeral characters."""
        with pytest.raises(ValueError, match="Invalid Roman numeral character"):
            roman_to_int("A")

        with pytest.raises(ValueError, match="Invalid Roman numeral character"):
            roman_to_int("IXZ")


class TestWordsToInt:
    """Test words_to_int function."""

    def test_single_words(self):
        """Test single word numbers."""
        assert words_to_int("one") == 1
        assert words_to_int("five") == 5
        assert words_to_int("ten") == 10
        assert words_to_int("fifteen") == 15
        assert words_to_int("nineteen") == 19

    def test_tens_words(self):
        """Test tens word numbers."""
        assert words_to_int("twenty") == 20
        assert words_to_int("thirty") == 30
        assert words_to_int("forty") == 40
        assert words_to_int("fifty") == 50
        assert words_to_int("ninety") == 90

    def test_compound_numbers(self):
        """Test compound word numbers."""
        assert words_to_int("twenty one") == 21
        assert words_to_int("twenty-one") == 21
        assert words_to_int("thirty five") == 35
        assert words_to_int("ninety nine") == 99

    def test_hundreds(self):
        """Test hundreds."""
        assert words_to_int("hundred") == 100
        assert words_to_int("one hundred") == 100
        assert words_to_int("two hundred") == 200
        assert words_to_int("five hundred") == 500
        assert words_to_int("nine hundred") == 900

    def test_hundreds_with_tens_and_units(self):
        """Test hundreds with tens and units."""
        assert words_to_int("one hundred one") == 101
        assert words_to_int("one hundred twenty") == 120
        assert words_to_int("one hundred twenty one") == 121
        assert words_to_int("five hundred fifty five") == 555
        assert words_to_int("nine hundred ninety nine") == 999

    def test_thousands(self):
        """Test thousands."""
        assert words_to_int("thousand") == 1000
        assert words_to_int("one thousand") == 1000
        assert words_to_int("two thousand") == 2000
        assert words_to_int("ten thousand") == 10000
        assert words_to_int("twenty thousand") == 20000

    def test_complex_numbers(self):
        """Test complex number combinations."""
        assert words_to_int("one thousand one") == 1001
        assert words_to_int("one thousand one hundred") == 1100
        assert words_to_int("one thousand one hundred one") == 1101
        assert words_to_int("two thousand twenty four") == 2024
        assert words_to_int("nineteen hundred ninety four") == 1994

    def test_case_insensitive(self):
        """Test case insensitive parsing."""
        assert words_to_int("TWENTY") == 20
        assert words_to_int("Twenty One") == 21
        assert words_to_int("HUNDRED") == 100

    def test_hyphenated_vs_spaces(self):
        """Test hyphenated vs space-separated numbers."""
        assert words_to_int("twenty-one") == 21
        assert words_to_int("twenty one") == 21
        assert words_to_int("twenty\tone") == 21  # tab

    def test_invalid_word(self):
        """Test invalid word numbers."""
        with pytest.raises(ValueError, match="Unknown word number"):
            words_to_int("invalid")

        with pytest.raises(ValueError, match="Unknown word number"):
            words_to_int("twenty invalid")


class TestParseNum:
    """Test parse_num function."""

    def test_digit_strings(self):
        """Test parsing digit strings."""
        assert parse_num("1") == 1
        assert parse_num("10") == 10
        assert parse_num("123") == 123
        assert parse_num("999") == 999

    def test_letter_suffixes(self):
        """Test parsing numbers with letter suffixes."""
        assert parse_num("14a") == 14
        assert parse_num("14b") == 14
        assert parse_num("25x") == 25
        assert parse_num("100abc") == 100

    def test_roman_numerals(self):
        """Test parsing Roman numerals."""
        assert parse_num("I") == 1
        assert parse_num("V") == 5
        assert parse_num("X") == 10
        assert parse_num("XIV") == 14
        assert parse_num("XLII") == 42

    def test_case_insensitive_roman(self):
        """Test case insensitive Roman numeral parsing."""
        assert parse_num("i") == 1
        assert parse_num("v") == 5
        assert parse_num("x") == 10
        assert parse_num("xiv") == 14

    def test_word_numbers(self):
        """Test parsing word numbers."""
        assert parse_num("one") == 1
        assert parse_num("twenty") == 20
        assert parse_num("twenty one") == 21
        assert parse_num("hundred") == 100

    def test_invalid_inputs(self):
        """Test invalid inputs return None."""
        assert parse_num("") is None
        assert parse_num("abc") is None
        assert parse_num("not a number") is None
        assert parse_num("XIV2") is None  # Mixed Roman and digits
        assert parse_num("12.5") == 125  # Extracts digits "125" from "12.5"

    def test_edge_cases(self):
        """Test edge cases."""
        # Leading zeros
        assert parse_num("007") == 7
        assert parse_num("0100") == 100

        # Just letter suffix
        assert parse_num("a") is None

        # Starting with digit but no digits
        assert parse_num("1a2b") == 12  # Extracts all digits "1" and "2"

    def test_mixed_content(self):
        """Test mixed content extraction."""
        assert parse_num("42abc") == 42
        assert parse_num("100x") == 100
        assert parse_num("1st") == 1
        assert parse_num("2nd") == 2
        assert parse_num("3rd") == 3
        assert parse_num("21st") == 21
