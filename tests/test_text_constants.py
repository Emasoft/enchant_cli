#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test suite for text_constants module.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from enchant_book_manager.text_constants import (
    PRESERVE_UNLIMITED,
    CHINESE_PUNCTUATION,
    ENGLISH_PUNCTUATION,
    SENTENCE_ENDING,
    CLOSING_QUOTES,
    NON_BREAKING,
    ALL_PUNCTUATION,
)


class TestTextConstants:
    """Test text constants definitions."""

    def test_preserve_unlimited_set(self):
        """Test PRESERVE_UNLIMITED contains expected characters."""
        # Check it's a set
        assert isinstance(PRESERVE_UNLIMITED, set)

        # Check some expected characters are present
        assert " " in PRESERVE_UNLIMITED  # Regular space
        assert "\t" in PRESERVE_UNLIMITED  # Tab
        assert "\n" in PRESERVE_UNLIMITED  # Newline
        assert "\r" in PRESERVE_UNLIMITED  # Carriage return
        assert "　" in PRESERVE_UNLIMITED  # Full-width space

        # Check common punctuation
        assert "!" in PRESERVE_UNLIMITED
        assert "?" in PRESERVE_UNLIMITED
        assert "." in PRESERVE_UNLIMITED
        assert "," in PRESERVE_UNLIMITED

        # Check brackets and quotes
        assert "(" in PRESERVE_UNLIMITED
        assert ")" in PRESERVE_UNLIMITED
        assert '"' in PRESERVE_UNLIMITED
        assert "'" in PRESERVE_UNLIMITED

        # Check special Unicode spaces
        assert "\u00a0" in PRESERVE_UNLIMITED  # Non-breaking space
        assert "\u2002" in PRESERVE_UNLIMITED  # En space
        assert "\u200b" in PRESERVE_UNLIMITED  # Zero-width space

        # Verify it has substantial content
        assert len(PRESERVE_UNLIMITED) > 50  # Should have many characters

    def test_chinese_punctuation_set(self):
        """Test CHINESE_PUNCTUATION contains Chinese punctuation marks."""
        assert isinstance(CHINESE_PUNCTUATION, set)

        # Check common Chinese punctuation
        assert "。" in CHINESE_PUNCTUATION  # Chinese period
        assert "，" in CHINESE_PUNCTUATION  # Chinese comma
        assert "、" in CHINESE_PUNCTUATION  # Enumeration comma
        assert "；" in CHINESE_PUNCTUATION  # Chinese semicolon
        assert "：" in CHINESE_PUNCTUATION  # Chinese colon
        assert "？" in CHINESE_PUNCTUATION  # Chinese question mark
        assert "！" in CHINESE_PUNCTUATION  # Chinese exclamation

        # Check Chinese quotes
        assert '"' in CHINESE_PUNCTUATION  # Regular double quote
        # Note: The source file appears to have curly quotes on line 95 but they don't parse correctly

        # Check Chinese brackets
        assert "（" in CHINESE_PUNCTUATION  # Left parenthesis
        assert "）" in CHINESE_PUNCTUATION  # Right parenthesis
        assert "【" in CHINESE_PUNCTUATION  # Left black bracket
        assert "】" in CHINESE_PUNCTUATION  # Right black bracket
        assert "《" in CHINESE_PUNCTUATION  # Left angle bracket
        assert "》" in CHINESE_PUNCTUATION  # Right angle bracket

        # Check other marks
        assert "—" in CHINESE_PUNCTUATION  # Em dash
        assert "…" in CHINESE_PUNCTUATION  # Ellipsis
        assert "·" in CHINESE_PUNCTUATION  # Middle dot

        # Check currency symbols
        assert "￥" in CHINESE_PUNCTUATION  # Full-width yen
        assert "¥" in CHINESE_PUNCTUATION  # Half-width yen

    def test_english_punctuation_set(self):
        """Test ENGLISH_PUNCTUATION contains English punctuation marks."""
        assert isinstance(ENGLISH_PUNCTUATION, set)

        # Check basic punctuation
        assert "." in ENGLISH_PUNCTUATION
        assert "," in ENGLISH_PUNCTUATION
        assert ";" in ENGLISH_PUNCTUATION
        assert ":" in ENGLISH_PUNCTUATION
        assert "?" in ENGLISH_PUNCTUATION
        assert "!" in ENGLISH_PUNCTUATION

        # Check quotes
        assert '"' in ENGLISH_PUNCTUATION
        assert "'" in ENGLISH_PUNCTUATION

        # Check brackets
        assert "(" in ENGLISH_PUNCTUATION
        assert ")" in ENGLISH_PUNCTUATION
        assert "[" in ENGLISH_PUNCTUATION
        assert "]" in ENGLISH_PUNCTUATION
        assert "{" in ENGLISH_PUNCTUATION
        assert "}" in ENGLISH_PUNCTUATION

        # Check symbols
        assert "@" in ENGLISH_PUNCTUATION
        assert "#" in ENGLISH_PUNCTUATION
        assert "$" in ENGLISH_PUNCTUATION
        assert "%" in ENGLISH_PUNCTUATION
        assert "&" in ENGLISH_PUNCTUATION
        assert "*" in ENGLISH_PUNCTUATION

        # Check mathematical symbols
        assert "+" in ENGLISH_PUNCTUATION
        assert "-" in ENGLISH_PUNCTUATION
        assert "=" in ENGLISH_PUNCTUATION
        assert "<" in ENGLISH_PUNCTUATION
        assert ">" in ENGLISH_PUNCTUATION

        # Check other symbols
        assert "/" in ENGLISH_PUNCTUATION
        assert "\\" in ENGLISH_PUNCTUATION
        assert "|" in ENGLISH_PUNCTUATION
        assert "^" in ENGLISH_PUNCTUATION
        assert "~" in ENGLISH_PUNCTUATION
        assert "`" in ENGLISH_PUNCTUATION

    def test_sentence_ending_set(self):
        """Test SENTENCE_ENDING contains sentence-ending punctuation."""
        assert isinstance(SENTENCE_ENDING, set)

        # Chinese sentence endings
        assert "。" in SENTENCE_ENDING  # Chinese period
        assert "！" in SENTENCE_ENDING  # Chinese exclamation
        assert "？" in SENTENCE_ENDING  # Chinese question mark

        # English sentence endings
        assert "." in SENTENCE_ENDING  # Period
        assert ";" in SENTENCE_ENDING  # Semicolon
        assert "；" in SENTENCE_ENDING  # Chinese semicolon

        # Ellipsis
        assert "…" in SENTENCE_ENDING

        # Should be a focused set
        assert len(SENTENCE_ENDING) < 10

    def test_closing_quotes_set(self):
        """Test CLOSING_QUOTES contains closing quote characters."""
        assert isinstance(CLOSING_QUOTES, set)

        # Chinese closing quotes
        assert "」" in CLOSING_QUOTES  # Right corner bracket
        assert '"' in CLOSING_QUOTES  # Regular double quote
        assert "】" in CLOSING_QUOTES  # Right black bracket
        assert "》" in CLOSING_QUOTES  # Right angle bracket

        # Should be a small focused set
        assert len(CLOSING_QUOTES) == 4

    def test_non_breaking_set(self):
        """Test NON_BREAKING contains non-breaking punctuation."""
        assert isinstance(NON_BREAKING, set)

        # Check expected non-breaking punctuation
        assert "，" in NON_BREAKING  # Chinese comma
        assert "、" in NON_BREAKING  # Enumeration comma
        assert "°" in NON_BREAKING  # Degree symbol

        # Should be a small focused set
        assert len(NON_BREAKING) == 3

    def test_all_punctuation_set(self):
        """Test ALL_PUNCTUATION is union of Chinese and English punctuation."""
        assert isinstance(ALL_PUNCTUATION, set)

        # Should be the union of Chinese and English
        assert ALL_PUNCTUATION == CHINESE_PUNCTUATION | ENGLISH_PUNCTUATION

        # Should contain all Chinese punctuation
        for char in CHINESE_PUNCTUATION:
            assert char in ALL_PUNCTUATION

        # Should contain all English punctuation
        for char in ENGLISH_PUNCTUATION:
            assert char in ALL_PUNCTUATION

        # Size should be consistent
        # Account for potential overlap between sets
        assert len(ALL_PUNCTUATION) <= len(CHINESE_PUNCTUATION) + len(ENGLISH_PUNCTUATION)

    def test_no_empty_strings(self):
        """Test that no constant contains empty strings."""
        all_constants = [
            PRESERVE_UNLIMITED,
            CHINESE_PUNCTUATION,
            ENGLISH_PUNCTUATION,
            SENTENCE_ENDING,
            CLOSING_QUOTES,
            NON_BREAKING,
            ALL_PUNCTUATION,
        ]

        for constant in all_constants:
            assert "" not in constant
            assert None not in constant

    def test_all_strings(self):
        """Test that all constants contain only strings."""
        all_constants = [
            PRESERVE_UNLIMITED,
            CHINESE_PUNCTUATION,
            ENGLISH_PUNCTUATION,
            SENTENCE_ENDING,
            CLOSING_QUOTES,
            NON_BREAKING,
            ALL_PUNCTUATION,
        ]

        for constant in all_constants:
            for item in constant:
                assert isinstance(item, str)

    def test_unique_characters(self):
        """Test that each set contains unique characters."""
        all_constants = {
            "PRESERVE_UNLIMITED": PRESERVE_UNLIMITED,
            "CHINESE_PUNCTUATION": CHINESE_PUNCTUATION,
            "ENGLISH_PUNCTUATION": ENGLISH_PUNCTUATION,
            "SENTENCE_ENDING": SENTENCE_ENDING,
            "CLOSING_QUOTES": CLOSING_QUOTES,
            "NON_BREAKING": NON_BREAKING,
            "ALL_PUNCTUATION": ALL_PUNCTUATION,
        }

        for name, constant in all_constants.items():
            # Convert to list to check for duplicates
            as_list = list(constant)
            assert len(as_list) == len(set(as_list)), f"{name} contains duplicates"

    def test_overlaps_between_sets(self):
        """Test expected overlaps between punctuation sets."""
        # Some punctuation appears in both Chinese and English
        overlap = CHINESE_PUNCTUATION & ENGLISH_PUNCTUATION

        # Common punctuation like quotes and dashes
        assert '"' in overlap  # Regular quote
        assert "—" in overlap  # Em dash
        assert "…" in overlap  # Ellipsis

        # Sentence endings should be subset of language punctuation
        chinese_endings = SENTENCE_ENDING & CHINESE_PUNCTUATION
        assert "。" in chinese_endings
        assert "！" in chinese_endings
        assert "？" in chinese_endings

        english_endings = SENTENCE_ENDING & ENGLISH_PUNCTUATION
        assert "." in english_endings
        assert ";" in english_endings

    def test_character_encoding(self):
        """Test that special Unicode characters are properly encoded."""
        # Check specific Unicode code points
        assert "\u3000" in PRESERVE_UNLIMITED  # Ideographic space (　)
        assert "\u00a0" in PRESERVE_UNLIMITED  # Non-breaking space
        assert "\u200b" in PRESERVE_UNLIMITED  # Zero-width space

        # Chinese punctuation Unicode ranges
        for char in CHINESE_PUNCTUATION:
            # Skip multi-character strings
            if len(char) > 1:
                continue

            # Most Chinese punctuation is in these ranges
            ord_val = ord(char)
            is_cjk = (
                (0x3000 <= ord_val <= 0x303F)  # CJK symbols
                or (0xFF00 <= ord_val <= 0xFFEF)  # Halfwidth/fullwidth
                or (0x2000 <= ord_val <= 0x206F)  # General punctuation
                or (ord_val == ord("¥"))  # Yen sign
            )
            assert is_cjk or char in ["—", "…", "·", '"'], f"Unexpected char: {char} ({ord_val:#x})"
