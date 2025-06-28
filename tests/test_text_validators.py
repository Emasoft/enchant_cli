#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test suite for text_validators module.
"""

import pytest
import re
from pathlib import Path
import sys
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from enchant_book_manager.text_validators import (
    is_latin_char,
    is_latin_charset,
    clean_repeated_chars,
    remove_thinking_block,
    validate_translation_output,
    _repeated_chars,
)


class TestIsLatinChar:
    """Test the is_latin_char function."""

    def test_ascii_letters(self):
        """Test ASCII letters are recognized as Latin."""
        assert is_latin_char("a") is True
        assert is_latin_char("Z") is True
        assert is_latin_char("m") is True

    def test_ascii_digits(self):
        """Test ASCII digits are recognized as Latin."""
        assert is_latin_char("0") is True
        assert is_latin_char("5") is True
        assert is_latin_char("9") is True

    def test_ascii_punctuation(self):
        """Test ASCII punctuation is recognized as Latin."""
        assert is_latin_char(".") is True
        assert is_latin_char(",") is True
        assert is_latin_char("!") is True
        assert is_latin_char("?") is True
        assert is_latin_char("@") is True
        assert is_latin_char("#") is True

    def test_latin_unicode_chars(self):
        """Test Latin Unicode characters are recognized."""
        assert is_latin_char("á") is True  # Latin small letter a with acute
        assert is_latin_char("é") is True  # Latin small letter e with acute
        assert is_latin_char("ñ") is True  # Latin small letter n with tilde
        assert is_latin_char("ü") is True  # Latin small letter u with diaeresis
        assert is_latin_char("Ö") is True  # Latin capital letter O with diaeresis

    def test_chinese_chars(self):
        """Test Chinese characters are not recognized as Latin."""
        assert is_latin_char("中") is False
        assert is_latin_char("文") is False
        assert is_latin_char("你") is False
        assert is_latin_char("好") is False

    def test_japanese_chars(self):
        """Test Japanese characters are not recognized as Latin."""
        assert is_latin_char("あ") is False  # Hiragana
        assert is_latin_char("カ") is False  # Katakana
        assert is_latin_char("日") is False  # Kanji

    def test_arabic_chars(self):
        """Test Arabic characters are not recognized as Latin."""
        assert is_latin_char("ا") is False
        assert is_latin_char("ب") is False

    def test_cyrillic_chars(self):
        """Test Cyrillic characters are not recognized as Latin."""
        assert is_latin_char("а") is False  # Cyrillic 'a' (looks like Latin 'a')
        assert is_latin_char("б") is False
        assert is_latin_char("в") is False

    def test_special_unicode_chars(self):
        """Test special Unicode characters."""
        assert is_latin_char(" ") is False  # Space (not in ALLOWED_ASCII)
        assert is_latin_char("\n") is False  # Newline (not in ALLOWED_ASCII)
        assert is_latin_char("€") is False  # Euro sign (not Latin)
        assert is_latin_char("™") is False  # Trademark (not Latin)

    @patch("enchant_book_manager.text_validators.unicodedata.name")
    def test_unicode_name_error(self, mock_name):
        """Test handling of unicodedata.name errors."""
        # Simulate ValueError from unicodedata.name
        mock_name.side_effect = ValueError("no such name")

        # Should return False when name lookup fails
        assert is_latin_char("℥") is False  # Some obscure character


class TestIsLatinCharset:
    """Test the is_latin_charset function."""

    def test_empty_text(self):
        """Test empty text is considered Latin."""
        assert is_latin_charset("") is True

    def test_pure_latin_text(self):
        """Test pure Latin text."""
        assert is_latin_charset("Hello, World!") is True
        assert is_latin_charset("The quick brown fox jumps over the lazy dog.") is True
        assert is_latin_charset("Testing 123 with punctuation!!!") is True

    def test_latin_with_accents(self):
        """Test Latin text with accented characters."""
        assert is_latin_charset("Café, naïve, résumé") is True
        assert is_latin_charset("Señor José María") is True
        assert is_latin_charset("Zürich, München, Köln") is True

    def test_pure_chinese_text(self):
        """Test pure Chinese text."""
        assert is_latin_charset("这是中文文本") is False
        assert is_latin_charset("你好世界") is False

    def test_mixed_text_below_threshold(self):
        """Test mixed text below default threshold (10%)."""
        # 1 Chinese char out of 20 = 5% < 10%
        text = "Hello World! This is 中 mostly English text."
        assert is_latin_charset(text) is True

    def test_mixed_text_above_threshold(self):
        """Test mixed text above default threshold."""
        # More than 10% Chinese
        text = "Hello 世界! This 是 mixed 文本."
        assert is_latin_charset(text) is False

    def test_custom_threshold(self):
        """Test with custom threshold values."""
        text = "Hello 中 World"  # ~11% non-Latin

        # With 5% threshold, should fail
        assert is_latin_charset(text, threshold=0.05) is False

        # With 20% threshold, should pass
        assert is_latin_charset(text, threshold=0.2) is True

    def test_whitespace_and_punctuation_ignored(self):
        """Test that whitespace and punctuation are ignored in counting."""
        # Lots of spaces and punctuation shouldn't affect the count
        text = "    Hello...    World!!!    ???    "
        assert is_latin_charset(text) is True

        # Chinese with lots of punctuation
        text = "。。。中文。。。"
        assert is_latin_charset(text) is False

    def test_only_whitespace_and_punctuation(self):
        """Test text with only whitespace and punctuation."""
        assert is_latin_charset("   ") is True
        assert is_latin_charset("...!!!???") is True
        assert is_latin_charset("\t\n\r") is True

    def test_threshold_edge_cases(self):
        """Test threshold edge cases."""
        # Exactly at threshold
        text = "abcdefghi中"  # 1 out of 10 = 10%
        assert is_latin_charset(text, threshold=0.1) is True
        assert is_latin_charset(text, threshold=0.09) is False


class TestCleanRepeatedChars:
    """Test the clean_repeated_chars function."""

    def test_no_repeated_chars(self):
        """Test text with no repeated characters."""
        assert clean_repeated_chars("Hello World") == "Hello World"
        assert clean_repeated_chars("Testing 123") == "Testing 123"

    def test_repeated_letters(self):
        """Test repeated letters are limited."""
        assert clean_repeated_chars("Hellooooo") == "Helloooo"  # Limited to 4
        assert clean_repeated_chars("Yessssssss") == "Yessss"  # All 8 s's are replaced with 4
        assert clean_repeated_chars("aaaaaa") == "aaaa"

    def test_repeated_below_limit(self):
        """Test repeated characters below the limit."""
        assert clean_repeated_chars("Hello") == "Hello"  # 2 l's
        assert clean_repeated_chars("Hiii") == "Hiii"  # 3 i's
        assert clean_repeated_chars("Yess") == "Yess"  # 2 s's

    def test_preserve_unlimited_chars(self):
        """Test that PRESERVE_UNLIMITED characters are not limited."""
        # Spaces should be preserved
        assert clean_repeated_chars("Hello     World") == "Hello     World"

        # Dots should be preserved
        assert clean_repeated_chars("Wait........") == "Wait........"

        # Newlines should be preserved
        assert clean_repeated_chars("Line1\n\n\n\n\nLine2") == "Line1\n\n\n\n\nLine2"

    def test_custom_max_allowed(self):
        """Test custom max_allowed parameter."""
        assert clean_repeated_chars("Hellooooo", max_allowed=2) == "Helloo"
        assert clean_repeated_chars("Yessssss", max_allowed=3) == "Yesss"
        assert clean_repeated_chars("aaaaaa", max_allowed=1) == "a"

    def test_mixed_repeated_chars(self):
        """Test text with multiple repeated character sequences."""
        text = "Hellooooo!!!!!     Worldddd..."
        expected = "Helloooo!!!!     Worldddd..."  # Letters limited, spaces/dots preserved
        assert clean_repeated_chars(text) == expected

    def test_unicode_repeated_chars(self):
        """Test repeated Unicode characters."""
        assert clean_repeated_chars("中中中中中中") == "中中中中"
        assert clean_repeated_chars("ñññññ") == "ññññ"

    def test_empty_string(self):
        """Test empty string."""
        assert clean_repeated_chars("") == ""

    def test_repeated_chars_regex(self):
        """Test the precompiled regex pattern."""
        # Verify the regex pattern works correctly
        match = _repeated_chars.search("aaa")
        assert match is not None
        assert match.group(0) == "aaa"
        assert match.group(1) == "a"


class TestRemoveThinkingBlock:
    """Test the remove_thinking_block function."""

    def test_no_thinking_blocks(self):
        """Test text with no thinking blocks."""
        text = "This is normal text without any thinking blocks."
        assert remove_thinking_block(text) == text

    def test_single_think_block(self):
        """Test removing single <think> block."""
        text = "Before <think>internal thoughts</think> After"
        assert remove_thinking_block(text) == "Before After"

    def test_single_thinking_block(self):
        """Test removing single <thinking> block."""
        text = "Start <thinking>pondering this</thinking> End"
        assert remove_thinking_block(text) == "Start End"

    def test_multiple_think_blocks(self):
        """Test removing multiple <think> blocks."""
        text = "A <think>first</think> B <think>second</think> C"
        assert remove_thinking_block(text) == "A B C"

    def test_multiple_thinking_blocks(self):
        """Test removing multiple <thinking> blocks."""
        text = "X <thinking>one</thinking> Y <thinking>two</thinking> Z"
        assert remove_thinking_block(text) == "X Y Z"

    def test_mixed_blocks(self):
        """Test removing both types of blocks."""
        text = "Start <think>short</think> middle <thinking>longer thought</thinking> end"
        assert remove_thinking_block(text) == "Start middle end"

    def test_multiline_blocks(self):
        """Test removing multiline blocks."""
        text = """First line
<think>
Multiple
lines
of thinking
</think>
Last line"""
        # The function replaces all whitespace with single spaces
        assert remove_thinking_block(text) == "First line Last line"

    def test_nested_content(self):
        """Test blocks with nested content."""
        text = "Before <thinking>Some <nested> content</thinking> After"
        assert remove_thinking_block(text) == "Before After"

    def test_empty_blocks(self):
        """Test empty thinking blocks."""
        text = "Text <think></think> more <thinking></thinking> text"
        assert remove_thinking_block(text) == "Text more text"

    def test_extra_whitespace_cleanup(self):
        """Test that extra whitespace is cleaned up."""
        text = "A  <think>removed</think>  B"
        assert remove_thinking_block(text) == "A B"

        text = "Start\n\n<thinking>block</thinking>\n\nEnd"
        # All whitespace including newlines is replaced with single space
        assert remove_thinking_block(text) == "Start End"

    def test_no_strip_edges(self):
        """Test that edges are stripped."""
        text = "  <think>start block</think> middle   "
        assert remove_thinking_block(text) == "middle"

    def test_unclosed_blocks(self):
        """Test that unclosed blocks are not removed."""
        text = "Text <think>unclosed block"
        assert remove_thinking_block(text) == text

        text = "Text <thinking>also unclosed"
        assert remove_thinking_block(text) == text

    def test_case_sensitivity(self):
        """Test that tags are case-sensitive."""
        text = "Keep <THINK>this</THINK> and <Thinking>this</Thinking> too"
        assert remove_thinking_block(text) == text


class TestValidateTranslationOutput:
    """Test the validate_translation_output function."""

    def test_valid_english_text(self):
        """Test valid English text passes validation."""
        text = "This is a valid English translation."
        is_valid, cleaned = validate_translation_output(text)
        assert is_valid is True
        assert cleaned == text

    def test_english_with_accents(self):
        """Test English with accented characters passes."""
        text = "The café serves naïve customers."
        is_valid, cleaned = validate_translation_output(text)
        assert is_valid is True
        assert cleaned == text

    def test_chinese_characters_fail(self):
        """Test text with Chinese characters fails validation."""
        text = "This has some 中文 characters"
        is_valid, cleaned = validate_translation_output(text)
        assert is_valid is False
        assert cleaned == text  # Original text returned

    def test_excessive_repetition_cleaned(self):
        """Test that excessive repetition is cleaned."""
        text = "Hellooooooo World!!!!!!!!"
        is_valid, cleaned = validate_translation_output(text)
        assert is_valid is True
        assert cleaned == "Helloooo World!!!!"

    def test_threshold_check(self):
        """Test the 5% threshold for non-Latin characters."""
        # Just under 5% Chinese (1 char in 21 total)
        text = "This is mostly English text 中"
        is_valid, cleaned = validate_translation_output(text)
        assert is_valid is True

        # Over 5% Chinese
        text = "This 是 mixed 文本"
        is_valid, cleaned = validate_translation_output(text)
        assert is_valid is False

    def test_logger_warnings(self):
        """Test that logger is called for warnings."""
        logger = Mock()

        # Test with Chinese characters
        text = "This has 中文 characters"
        is_valid, cleaned = validate_translation_output(text, logger)

        assert is_valid is False
        # Check logger was called
        assert logger.call_count >= 1
        warning_call = logger.call_args_list[0]
        assert warning_call[0][0] == "Translation contains too many non-Latin characters"
        assert warning_call[0][1] == "warning"

    def test_chinese_character_reporting(self):
        """Test that specific Chinese characters are reported."""
        logger = Mock()

        text = "Text with 你好世界 and 中文"
        is_valid, cleaned = validate_translation_output(text, logger)

        assert is_valid is False
        # Should have two logger calls
        assert logger.call_count == 2

        # Second call should report Chinese characters
        chinese_report = logger.call_args_list[1]
        assert "Found Chinese characters:" in chinese_report[0][0]
        assert chinese_report[0][1] == "warning"

    def test_many_chinese_chars_limited_report(self):
        """Test that only first 10 unique Chinese chars are reported."""
        logger = Mock()

        # Text with many different Chinese characters
        text = "包含很多不同的中文字符测试验证功能是否正常工作"
        is_valid, cleaned = validate_translation_output(text, logger)

        assert is_valid is False
        # Check the Chinese character report
        chinese_report = logger.call_args_list[1][0][0]
        # Count reported characters (between "Found Chinese characters: " and the end)
        reported_chars = chinese_report.split(": ")[1].split(", ")
        assert len(reported_chars) <= 10

    def test_empty_text(self):
        """Test empty text validation."""
        is_valid, cleaned = validate_translation_output("")
        assert is_valid is True
        assert cleaned == ""

    def test_whitespace_only(self):
        """Test whitespace-only text."""
        is_valid, cleaned = validate_translation_output("   \n\t   ")
        assert is_valid is True
        assert cleaned == "   \n\t   "

    def test_no_logger(self):
        """Test validation works without logger."""
        text = "Text with 中文"
        is_valid, cleaned = validate_translation_output(text, logger=None)
        assert is_valid is False
        assert cleaned == text

    def test_preserve_unlimited_in_output(self):
        """Test that PRESERVE_UNLIMITED chars are preserved in output."""
        text = "Text with     spaces and........ dots"
        is_valid, cleaned = validate_translation_output(text)
        assert is_valid is True
        assert "     " in cleaned  # Spaces preserved
        assert "........" in cleaned  # Dots preserved
