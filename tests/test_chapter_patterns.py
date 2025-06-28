#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test suite for chapter_patterns module.
"""

import pytest
import re
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from enchant_book_manager.chapter_patterns import (
    HEADING_RE,
    PART_PATTERNS,
    DB_OPTIMIZATION_THRESHOLD,
)


class TestHeadingRegex:
    """Test the HEADING_RE regex pattern."""

    def test_chapter_with_digits(self):
        """Test chapter headings with digit numbering."""
        # Basic patterns
        assert HEADING_RE.match("Chapter 1")
        assert HEADING_RE.match("Chapter 42")
        assert HEADING_RE.match("Ch. 5")
        assert HEADING_RE.match("Ch 7")
        assert HEADING_RE.match("Chap. 9")
        assert HEADING_RE.match("Chap 11")

        # With letter suffix
        assert HEADING_RE.match("Chapter 1a")
        assert HEADING_RE.match("Chapter 3b")

        # Check captured groups
        match = HEADING_RE.match("Chapter 42")
        assert match.group("num_d") == "42"
        assert match.group("num_r") is None
        assert match.group("num_w") is None

    def test_chapter_with_roman_numerals(self):
        """Test chapter headings with Roman numeral numbering."""
        assert HEADING_RE.match("Chapter IV")
        assert HEADING_RE.match("Chapter XIV")
        assert HEADING_RE.match("Ch. XVI")
        assert HEADING_RE.match("chapter xiv")  # Case insensitive

        # Check captured groups
        match = HEADING_RE.match("Chapter XIV")
        assert match.group("num_d") is None
        assert match.group("num_r") == "XIV"
        assert match.group("num_w") is None

    def test_chapter_with_word_numbers(self):
        """Test chapter headings with word numbering."""
        assert HEADING_RE.match("Chapter One")
        assert HEADING_RE.match("Chapter Twenty")
        assert HEADING_RE.match("Chapter Twenty-Five")
        assert HEADING_RE.match("Chapter Thirty Three")  # Space instead of hyphen

        # Check captured groups
        match = HEADING_RE.match("Chapter Twenty-Five")
        assert match.group("num_d") is None
        assert match.group("num_r") is None
        assert match.group("num_w") == "Twenty-Five"

    def test_part_section_book_patterns(self):
        """Test Part, Section, and Book headings."""
        # Part patterns
        assert HEADING_RE.match("Part 1")
        assert HEADING_RE.match("Part IV")
        assert HEADING_RE.match("Part One")

        # Section patterns
        assert HEADING_RE.match("Section 5")
        assert HEADING_RE.match("Section XII")
        assert HEADING_RE.match("Section Three")

        # Book patterns
        assert HEADING_RE.match("Book 2")
        assert HEADING_RE.match("Book VII")
        assert HEADING_RE.match("Book Four")

        # Check captured groups for Part
        match = HEADING_RE.match("Part 5")
        assert match.group("part_d") == "5"
        assert match.group("part_r") is None
        assert match.group("part_w") is None

    def test_section_symbol_pattern(self):
        """Test section symbol (§) pattern."""
        # The § symbol is treated as a non-word character,
        # so "§ 42" actually matches the hash_d pattern, not sec_d
        assert HEADING_RE.match("§ 42")
        assert HEADING_RE.match("§42")  # Without space

        # Check captured groups
        match = HEADING_RE.match("§ 42")
        # This matches as hash_d because § is a leading non-word char
        assert match.group("hash_d") == "42"
        assert match.group("sec_d") is None

        # To match sec_d, we would need a pattern like "Section § 42"
        # but that's not how the regex is structured

    def test_hash_number_pattern(self):
        """Test hash number patterns (just number at start)."""
        assert HEADING_RE.match("1. Introduction")
        assert HEADING_RE.match("42) The Answer")
        assert HEADING_RE.match("7: Lucky Number")
        assert HEADING_RE.match("13- Unlucky")
        assert HEADING_RE.match("99 Bottles")  # Just number

        # Check captured groups
        match = HEADING_RE.match("42) The Answer")
        assert match.group("hash_d") == "42"
        assert match.group("rest") == ") The Answer"  # The ) is part of rest

    def test_leading_characters(self):
        """Test handling of leading non-word characters."""
        assert HEADING_RE.match("   Chapter 1")  # Leading spaces
        assert HEADING_RE.match("***Chapter 5")  # Leading asterisks
        assert HEADING_RE.match("---Chapter 10")  # Leading dashes
        assert HEADING_RE.match("   ***   Chapter 15")  # Mixed

    def test_case_insensitivity(self):
        """Test case insensitive matching."""
        assert HEADING_RE.match("CHAPTER 1")
        assert HEADING_RE.match("chapter 1")
        assert HEADING_RE.match("ChApTeR 1")
        assert HEADING_RE.match("PART ONE")
        assert HEADING_RE.match("part one")

    def test_rest_capture(self):
        """Test capturing the rest of the line after chapter number."""
        match = HEADING_RE.match("Chapter 1: The Beginning")
        assert match.group("rest") == ": The Beginning"

        match = HEADING_RE.match("Chapter 42 - The Answer to Everything")
        assert match.group("rest") == " - The Answer to Everything"

    def test_non_matching_patterns(self):
        """Test patterns that should not match."""
        assert not HEADING_RE.match("Not a chapter")
        assert not HEADING_RE.match("The Chapter")  # No number
        assert not HEADING_RE.match("Chapter")  # No number
        assert not HEADING_RE.match("Middle 123 text")  # Number not at start
        assert not HEADING_RE.match("Prologue")
        assert not HEADING_RE.match("Epilogue")

    def test_edge_cases(self):
        """Test edge cases and special scenarios."""
        # Empty or whitespace
        assert not HEADING_RE.match("")
        assert not HEADING_RE.match("   ")

        # Special formatting
        assert HEADING_RE.match("CHAPTER 1A")  # Capital letter suffix
        assert HEADING_RE.match("Chapter1")  # No space
        assert HEADING_RE.match("Ch1")  # No period or space

        # Mixed Roman numerals
        assert HEADING_RE.match("Chapter MCMXCIX")  # 1999 in Roman


class TestPartPatterns:
    """Test the PART_PATTERNS regex list."""

    def test_fraction_patterns(self):
        """Test fraction notation patterns."""
        # Pattern 1: Simple fraction
        pattern = PART_PATTERNS[0]
        assert pattern.search("Chapter 1 1/3")
        assert pattern.search("Part 2/5")
        match = pattern.search("Section 3/4")
        assert match.groups() == ("3", "4")

        # Pattern 2: Bracketed fraction
        pattern = PART_PATTERNS[1]
        assert pattern.search("Chapter 1 [1/3]")
        assert pattern.search("Title [2/5]")
        match = pattern.search("[3/4]")
        assert match.groups() == ("3", "4")

        # Pattern 3: "of" notation
        pattern = PART_PATTERNS[2]
        assert pattern.search("Chapter 1 (1 of 3)")
        assert pattern.search("Part (2 of 5)")
        match = pattern.search("(3 of 4)")
        assert match.groups() == ("3", "4")

        # Pattern 4: "out of" notation
        pattern = PART_PATTERNS[3]
        assert pattern.search("Chapter 1 (1 out of 3)")
        assert pattern.search("(2 out of 5)")

    def test_part_word_patterns(self):
        """Test part word patterns."""
        # Pattern 5: "part" + number/word
        pattern = PART_PATTERNS[4]
        assert pattern.search("Chapter 1 Part 1")
        assert pattern.search("Chapter 1 part one")
        assert pattern.search("Title Part Two")
        assert pattern.search("PART THREE")  # Case insensitive

        # Pattern 6: "pt" + number/word
        pattern = PART_PATTERNS[5]
        assert pattern.search("Chapter 1 Pt. 1")
        assert pattern.search("Chapter 1 pt 2")
        assert pattern.search("Title Pt One")

    def test_dash_number_patterns(self):
        """Test dash number patterns."""
        # Pattern 7: dash + number at end
        pattern = PART_PATTERNS[6]
        assert pattern.search("Chapter 1 - 1")
        assert pattern.search("Title - 2")
        match = pattern.search("Something - 3")
        assert match.group(1) == "3"

        # Should match at end only
        assert not pattern.search("- 1 more text")

    def test_roman_numeral_patterns(self):
        """Test Roman numeral patterns."""
        # Pattern 8: Part + Roman
        pattern = PART_PATTERNS[7]
        assert pattern.search("Part I")
        assert pattern.search("Part IV")
        assert pattern.search("pt. V")
        assert pattern.search("PT X")  # Case insensitive

        # Should not match names
        assert not pattern.search("Louis XIV")
        assert not pattern.search("King Henry VIII")

        # Pattern 9: dash + Roman at end
        pattern = PART_PATTERNS[8]
        assert pattern.search("Chapter 1 - I")
        assert pattern.search("Title - II")
        assert pattern.search(" - V")  # Pattern requires whitespace before dash

    def test_multiple_patterns_in_text(self):
        """Test detection of multiple part patterns."""
        text = "Chapter 1 Part 1 (1/3)"

        # Should match both patterns
        matches_found = []
        for pattern in PART_PATTERNS:
            if pattern.search(text):
                matches_found.append(pattern)

        assert len(matches_found) >= 2  # At least two patterns match

    def test_edge_cases(self):
        """Test edge cases for part patterns."""
        # Numbers with spaces
        assert PART_PATTERNS[0].search("1 / 3")
        assert PART_PATTERNS[1].search("[1 / 3]")
        assert PART_PATTERNS[2].search("(1 of 3)")

        # Case variations
        assert PART_PATTERNS[2].search("(1 OF 3)")
        assert PART_PATTERNS[4].search("PART ONE")
        assert PART_PATTERNS[4].search("part ONE")

        # No false positives
        assert not any(p.search("Chapter without parts") for p in PART_PATTERNS)


class TestConstants:
    """Test module constants."""

    def test_db_optimization_threshold(self):
        """Test DB_OPTIMIZATION_THRESHOLD constant."""
        assert isinstance(DB_OPTIMIZATION_THRESHOLD, int)
        assert DB_OPTIMIZATION_THRESHOLD > 0
        assert DB_OPTIMIZATION_THRESHOLD == 100000  # Expected value

    def test_regex_compilation(self):
        """Test that regex patterns are properly compiled."""
        # HEADING_RE should be a compiled regex
        assert hasattr(HEADING_RE, "match")
        assert hasattr(HEADING_RE, "search")
        assert isinstance(HEADING_RE, re.Pattern)

        # All PART_PATTERNS should be compiled regexes
        assert isinstance(PART_PATTERNS, list)
        assert len(PART_PATTERNS) > 0
        for pattern in PART_PATTERNS:
            assert isinstance(pattern, re.Pattern)
            assert hasattr(pattern, "match")
            assert hasattr(pattern, "search")

    def test_word_nums_in_heading_re(self):
        """Test that WORD_NUMS are properly included in HEADING_RE."""
        # Test some standard word numbers
        word_numbers = ["One", "Two", "Three", "Four", "Five", "Ten", "Twenty", "Thirty", "Forty", "Fifty", "Twenty-One", "Thirty-Two", "Ninety-Nine"]

        for num in word_numbers:
            assert HEADING_RE.match(f"Chapter {num}")
            assert HEADING_RE.match(f"Part {num}")
