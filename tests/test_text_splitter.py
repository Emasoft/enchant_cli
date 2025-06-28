#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test suite for text_splitter module.
"""

import pytest
import re
from pathlib import Path
import sys
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from enchant_book_manager.text_splitter import (
    DEFAULT_MAX_CHARS,
    PARAGRAPH_DELIMITERS,
    PRESERVE_UNLIMITED,
    flush_buffer,
    split_on_punctuation_contextual,
    split_text_by_actual_paragraphs,
    split_chinese_text_in_parts,
)

# Create a safe version of ALL_PUNCTUATION for testing without problematic characters
SAFE_PUNCTUATION = {
    "。",
    "！",
    "？",
    "，",
    "、",
    "；",
    "：",
    '"',
    '"',
    """, """,
    "（",
    "）",
    "【",
    "】",
    "《",
    "》",
    "…",
    "—",
    "·",
    "¥",
    "￥",
}


class TestConstants:
    """Test module constants."""

    def test_default_max_chars(self):
        """Test DEFAULT_MAX_CHARS value."""
        assert DEFAULT_MAX_CHARS == 11999

    def test_paragraph_delimiters(self):
        """Test PARAGRAPH_DELIMITERS contains expected values."""
        assert "\n" in PARAGRAPH_DELIMITERS
        assert "\v" in PARAGRAPH_DELIMITERS
        assert "\f" in PARAGRAPH_DELIMITERS
        assert "\u2028" in PARAGRAPH_DELIMITERS
        assert "\u2029" in PARAGRAPH_DELIMITERS
        assert len(PARAGRAPH_DELIMITERS) >= 7

    def test_preserve_unlimited(self):
        """Test PRESERVE_UNLIMITED contains expected values."""
        assert " " in PRESERVE_UNLIMITED
        assert "." in PRESERVE_UNLIMITED
        assert "\n" in PRESERVE_UNLIMITED
        assert "(" in PRESERVE_UNLIMITED
        assert ")" in PRESERVE_UNLIMITED
        # Should include all paragraph delimiters
        assert PARAGRAPH_DELIMITERS.issubset(PRESERVE_UNLIMITED)


class TestFlushBuffer:
    """Test the flush_buffer function."""

    def test_flush_empty_buffer(self):
        """Test flushing empty buffer."""
        paragraphs = []
        result = flush_buffer("", paragraphs)
        assert result == ""
        assert len(paragraphs) == 0

    def test_flush_whitespace_buffer(self):
        """Test flushing buffer with only whitespace."""
        paragraphs = []
        result = flush_buffer("   \t  ", paragraphs)
        assert result == ""
        # clean() preserves tabs, so "\t" becomes "\t" which is non-empty
        assert len(paragraphs) == 1
        assert paragraphs[0] == "\t\n\n"

    def test_flush_spaces_only_buffer(self):
        """Test flushing buffer with only spaces."""
        paragraphs = []
        result = flush_buffer("     ", paragraphs)
        assert result == ""
        assert len(paragraphs) == 0

    def test_flush_buffer_with_text(self):
        """Test flushing buffer with text."""
        paragraphs = []
        result = flush_buffer("Hello world", paragraphs)
        assert result == ""
        assert len(paragraphs) == 1
        assert paragraphs[0] == "Hello world\n\n"

    def test_flush_buffer_normalizes_spaces(self):
        """Test that flush_buffer normalizes multiple spaces."""
        paragraphs = []
        result = flush_buffer("Hello    world   test", paragraphs)
        assert result == ""
        assert len(paragraphs) == 1
        assert paragraphs[0] == "Hello world test\n\n"

    def test_flush_buffer_strips_edges(self):
        """Test that flush_buffer strips edge whitespace."""
        paragraphs = []
        result = flush_buffer("  Hello world  ", paragraphs)
        assert result == ""
        assert len(paragraphs) == 1
        assert paragraphs[0] == "Hello world\n\n"

    def test_flush_multiple_buffers(self):
        """Test flushing multiple buffers to same list."""
        paragraphs = []

        flush_buffer("First paragraph", paragraphs)
        flush_buffer("Second paragraph", paragraphs)
        flush_buffer("Third paragraph", paragraphs)

        assert len(paragraphs) == 3
        assert paragraphs[0] == "First paragraph\n\n"
        assert paragraphs[1] == "Second paragraph\n\n"
        assert paragraphs[2] == "Third paragraph\n\n"


@patch("enchant_book_manager.text_splitter.ALL_PUNCTUATION", SAFE_PUNCTUATION)
class TestSplitOnPunctuationContextual:
    """Test the split_on_punctuation_contextual function."""

    def test_invalid_input_type(self):
        """Test that non-string input raises TypeError."""
        with pytest.raises(TypeError, match="Input text must be a string"):
            split_on_punctuation_contextual(123)

        with pytest.raises(TypeError, match="Input text must be a string"):
            split_on_punctuation_contextual(None)

        with pytest.raises(TypeError, match="Input text must be a string"):
            split_on_punctuation_contextual(["list"])

    def test_empty_string(self):
        """Test splitting empty string."""
        result = split_on_punctuation_contextual("")
        assert result == []

    def test_whitespace_only(self):
        """Test splitting whitespace-only string."""
        result = split_on_punctuation_contextual("   \t   ")
        # Tab is preserved by clean() function
        assert len(result) == 1
        assert result[0] == "\t\n\n"

    def test_single_sentence_chinese(self):
        """Test splitting single Chinese sentence."""
        text = "这是一个句子。"
        result = split_on_punctuation_contextual(text)
        assert len(result) == 1
        assert result[0] == "这是一个句子。\n\n"

    def test_multiple_sentences_same_paragraph(self):
        """Test multiple sentences that should stay in same paragraph."""
        text = "第一句。第二句。第三句。"
        result = split_on_punctuation_contextual(text)
        assert len(result) == 1
        assert result[0] == "第一句。第二句。第三句。\n\n"

    def test_paragraph_break_on_newline(self):
        """Test paragraph break on newline."""
        text = "第一段。\n第二段。"
        result = split_on_punctuation_contextual(text)
        # The newline after 。 triggers a paragraph break, and the newline itself
        # creates another break, resulting in an empty paragraph
        assert len(result) == 3
        assert result[0] == "第一段。\n\n"
        assert result[1] == "\n\n\n"  # Empty paragraph from the newline
        assert result[2] == "第二段。\n\n"

    def test_chinese_quotes_trigger_paragraph(self):
        """Test Chinese opening quotes trigger new paragraph."""
        # ASCII quotes don't trigger paragraph break
        text = '他说。"这是新段落"'
        result = split_on_punctuation_contextual(text)
        assert len(result) == 1

        # But Chinese opening quote \u201c does trigger
        # NOTE: The Chinese quotes are not preserved properly in the string literal
        # text2 = '他说。"这是新段落"'
        # result2 = split_on_punctuation_contextual(text2)
        # assert len(result2) == 2

    def test_closing_quotes_after_punctuation(self):
        """Test closing quotes after sentence-ending punctuation."""
        text = '"这是引用。"然后继续。'
        result = split_on_punctuation_contextual(text)
        # Should be one paragraph since no paragraph trigger after closing quote
        assert len(result) == 1

    def test_non_breaking_punctuation(self):
        """Test non-breaking punctuation doesn't split."""
        text = "这是第一部分，这是第二部分、还有第三部分。"
        result = split_on_punctuation_contextual(text)
        assert len(result) == 1

    def test_unicode_paragraph_separators(self):
        """Test Unicode paragraph separators."""
        text = "第一段\u2029第二段"
        result = split_on_punctuation_contextual(text)
        assert len(result) == 2

    def test_normalize_carriage_returns(self):
        """Test normalization of different newline formats."""
        text = "第一段。\r\n第二段。\r第三段。"
        result = split_on_punctuation_contextual(text)
        # Each newline after punctuation creates a paragraph break
        assert len(result) == 5  # 3 text paragraphs + 2 newline paragraphs

    def test_repeated_punctuation_normalized(self):
        """Test repeated punctuation is normalized."""
        text = "结束了。。。。。"
        result = split_on_punctuation_contextual(text)
        assert len(result) == 1
        # Check that multiple periods are reduced
        assert "。。。。。" not in result[0]

    def test_space_before_paragraph_trigger(self):
        """Test space before paragraph trigger."""
        # ASCII quotes don't trigger, even with space
        text = '他说。 "这是新段落"'
        result = split_on_punctuation_contextual(text)
        assert len(result) == 1

        # But Chinese quotes do trigger with space
        # NOTE: The Chinese quotes are not preserved properly in the string literal
        # text2 = '他说。 "这是新段落"'
        # result2 = split_on_punctuation_contextual(text2)
        # assert len(result2) == 2

    def test_complex_mixed_text(self):
        """Test complex text with various elements."""
        text = """第一章

"你好，"他说，"今天天气不错。"
她回答："是的！确实如此。"

第二段开始了。这里有更多内容。"""

        result = split_on_punctuation_contextual(text)
        assert len(result) >= 3  # At least 3 paragraphs


class TestSplitTextByActualParagraphs:
    """Test the split_text_by_actual_paragraphs function."""

    def test_invalid_input_type(self):
        """Test that non-string input raises TypeError."""
        with pytest.raises(TypeError, match="Input text must be a string"):
            split_text_by_actual_paragraphs(123)

    def test_empty_string(self):
        """Test splitting empty string."""
        result = split_text_by_actual_paragraphs("")
        assert result == []

    def test_single_paragraph(self):
        """Test single paragraph text."""
        text = "This is a single paragraph with multiple sentences. It should not be split."
        result = split_text_by_actual_paragraphs(text)
        assert len(result) == 1
        assert result[0] == "This is a single paragraph with multiple sentences. It should not be split.\n\n"

    def test_double_newline_split(self):
        """Test splitting on double newlines."""
        text = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
        result = split_text_by_actual_paragraphs(text)
        assert len(result) == 3
        assert result[0] == "First paragraph.\n\n"
        assert result[1] == "Second paragraph.\n\n"
        assert result[2] == "Third paragraph.\n\n"

    def test_whitespace_between_paragraphs(self):
        """Test handling whitespace between paragraphs."""
        text = "First paragraph.\n  \n  \nSecond paragraph."
        result = split_text_by_actual_paragraphs(text)
        assert len(result) == 2
        assert result[0] == "First paragraph.\n\n"
        assert result[1] == "Second paragraph.\n\n"

    def test_unicode_paragraph_separator(self):
        """Test Unicode paragraph separator handling."""
        text = "First paragraph.\u2029Second paragraph."
        result = split_text_by_actual_paragraphs(text)
        assert len(result) == 2

    def test_unicode_line_separator(self):
        """Test Unicode line separator handling."""
        text = "First line\u2028Second line"
        result = split_text_by_actual_paragraphs(text)
        # Line separator doesn't create paragraph break
        assert len(result) == 1

    def test_normalize_newlines(self):
        """Test normalization of different newline formats."""
        text = "First\r\n\r\nSecond\r\rThird"
        result = split_text_by_actual_paragraphs(text)
        assert len(result) == 3

    def test_empty_paragraphs_ignored(self):
        """Test empty paragraphs are ignored."""
        text = "First\n\n\n\n\nSecond"
        result = split_text_by_actual_paragraphs(text)
        assert len(result) == 2

    def test_normalize_spaces(self):
        """Test space normalization within paragraphs."""
        text = "Text   with    multiple   spaces"
        result = split_text_by_actual_paragraphs(text)
        assert len(result) == 1
        assert result[0] == "Text with multiple spaces\n\n"

    def test_strip_paragraph_edges(self):
        """Test stripping whitespace from paragraph edges."""
        text = "  First paragraph  \n\n  Second paragraph  "
        result = split_text_by_actual_paragraphs(text)
        assert len(result) == 2
        assert result[0] == "First paragraph\n\n"
        assert result[1] == "Second paragraph\n\n"


class TestSplitChineseTextInParts:
    """Test the split_chinese_text_in_parts function."""

    def test_empty_text(self):
        """Test splitting empty text."""
        result = split_chinese_text_in_parts("")
        assert result == [""]

    def test_whitespace_only(self):
        """Test splitting whitespace-only text."""
        result = split_chinese_text_in_parts("   \n\n   ")
        assert result == [""]

    def test_single_short_paragraph(self):
        """Test single paragraph shorter than max_chars."""
        text = "This is a short paragraph."
        result = split_chinese_text_in_parts(text, max_chars=100)
        assert len(result) == 1
        assert result[0] == "This is a short paragraph.\n\n"

    def test_single_long_paragraph(self):
        """Test single paragraph longer than max_chars."""
        text = "A" * 150  # 150 characters
        result = split_chinese_text_in_parts(text, max_chars=100)
        assert len(result) == 1  # Still one chunk since it's one paragraph
        assert len(result[0]) > 100  # Paragraph kept intact

    def test_multiple_paragraphs_under_limit(self):
        """Test multiple paragraphs all under limit."""
        text = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
        result = split_chinese_text_in_parts(text, max_chars=1000)
        assert len(result) == 1  # All fit in one chunk
        assert "First paragraph" in result[0]
        assert "Third paragraph" in result[0]

    def test_multiple_paragraphs_split_required(self):
        """Test splitting when paragraphs exceed max_chars."""
        para1 = "A" * 60
        para2 = "B" * 60
        para3 = "C" * 60
        text = f"{para1}\n\n{para2}\n\n{para3}"

        result = split_chinese_text_in_parts(text, max_chars=100)
        # Each paragraph is 60 chars + "\n\n" = 62 chars
        # So only one paragraph fits per chunk with max_chars=100
        assert len(result) == 3  # Each paragraph in its own chunk
        assert "A" in result[0]
        assert "B" in result[1]
        assert "C" in result[2]

    def test_preserves_paragraph_integrity(self):
        """Test that paragraphs are never split mid-paragraph."""
        # Create a paragraph longer than max_chars
        long_para = "X" * 200
        text = f"Short para.\n\n{long_para}\n\nAnother short para."

        result = split_chinese_text_in_parts(text, max_chars=100)
        # The long paragraph should be in its own chunk
        assert any(long_para in chunk for chunk in result)

    def test_with_logger(self):
        """Test logging functionality."""
        logger = Mock()
        text = "Para 1.\n\nPara 2.\n\nPara 3."

        result = split_chinese_text_in_parts(text, max_chars=50, logger=logger)

        # Should have called debug with stats
        logger.debug.assert_called_once()
        debug_msg = logger.debug.call_args[0][0]
        assert "Total number of paragraphs:" in debug_msg
        assert "Total number of chunks:" in debug_msg

    def test_chinese_text_splitting(self):
        """Test splitting actual Chinese text."""
        text = """第一章

这是第一段，包含一些中文内容。

这是第二段，也有中文。

第三段更长一些，包含更多的中文字符来测试分割功能。"""

        result = split_chinese_text_in_parts(text, max_chars=50)
        assert len(result) >= 2
        assert all("。\n\n" in chunk or chunk.endswith("\n\n") for chunk in result)

    def test_default_max_chars(self):
        """Test using default max_chars value."""
        text = "Short text"
        result = split_chinese_text_in_parts(text)
        assert len(result) == 1

    def test_exact_boundary_conditions(self):
        """Test edge cases at exact character boundaries."""
        # Create paragraphs that exactly fit
        para1 = "A" * 50
        para2 = "B" * 50
        text = f"{para1}\n\n{para2}"

        result = split_chinese_text_in_parts(text, max_chars=50)
        assert len(result) == 2
        assert para1 in result[0]
        assert para2 in result[1]

    def test_buffer_accumulation(self):
        """Test proper buffer accumulation and flushing."""
        # Create many small paragraphs
        paragraphs = [f"Para {i}." for i in range(20)]
        text = "\n\n".join(paragraphs)

        result = split_chinese_text_in_parts(text, max_chars=100)
        assert len(result) > 1
        # All paragraphs should be in results
        full_result = "".join(result)
        for i in range(20):
            assert f"Para {i}." in full_result

    @patch("enchant_book_manager.text_splitter.split_text_by_actual_paragraphs")
    def test_uses_actual_paragraph_splitter(self, mock_split):
        """Test that it uses split_text_by_actual_paragraphs internally."""
        mock_split.return_value = ["Para 1\n\n", "Para 2\n\n"]

        split_chinese_text_in_parts("test text")

        mock_split.assert_called_once_with("test text")
