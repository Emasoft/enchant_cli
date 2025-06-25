#!/usr/bin/env python3
"""
Test edge cases for chunk processing and error handling
"""

try:
    import pytest
except ImportError:
    pytest = None
import sys
import os
from unittest.mock import Mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestEdgeCases:
    """Test edge cases and error conditions"""

    def test_chunk_numbering_edge_cases(self):
        """Test chunk numbering with edge values"""
        # Test minimum
        assert f"Chunk_{0:06d}.txt" == "Chunk_000000.txt"

        # Test maximum 6-digit
        assert f"Chunk_{999999:06d}.txt" == "Chunk_999999.txt"

        # Test overflow (should still work but with more digits)
        assert f"Chunk_{1000000:06d}.txt" == "Chunk_1000000.txt"

    def test_empty_line_reduction_edge_cases(self):
        """Test empty line reduction with various inputs"""
        from enchant_book_manager.text_processor import remove_excess_empty_lines

        # Empty string
        assert remove_excess_empty_lines("") == ""

        # Only newlines
        assert remove_excess_empty_lines("\n\n\n\n\n") == "\n\n\n"

        # Mixed content
        assert remove_excess_empty_lines("A\n\n\n\n\nB\n\n\n\n\n\nC") == "A\n\n\nB\n\n\nC"

        # Windows line endings
        text = "A\r\n\r\n\r\n\r\nB"
        # Should not affect \r\n patterns
        result = remove_excess_empty_lines(text)
        assert "\r" in result  # Carriage returns preserved

    def test_character_limit_boundary(self):
        """Test character limit at exact boundary"""
        from enchant_book_manager.text_splitter import split_chinese_text_in_parts

        # Mock logger
        mock_logger = Mock()

        # Note: The function processes paragraphs and adds "\n\n" to each
        # For a single continuous text block, it becomes one paragraph

        # Test 1: Single paragraph that fits within limit (including "\n\n")
        text = "A" * 11997  # 11997 + "\n\n" = 11999
        chunks = split_chinese_text_in_parts(text, max_chars=11999, logger=mock_logger)
        assert len(chunks) == 1
        assert len(chunks[0]) == 11999  # Including the "\n\n"

        # Test 2: Single paragraph that exceeds limit when "\n\n" is added
        text = "A" * 11999  # 11999 + "\n\n" = 12001, exceeds 11999
        chunks = split_chinese_text_in_parts(text, max_chars=11999, logger=mock_logger)
        # This creates 1 chunk because we keep paragraphs together when possible
        # The >= check allows a single paragraph to slightly exceed the limit
        assert len(chunks) == 1
        assert len(chunks[0]) == 12001

        # Test 3: Multiple paragraphs that require splitting
        para1 = "A" * 6000
        para2 = "B" * 6000
        text = f"{para1}\n\n{para2}"  # Two paragraphs
        chunks = split_chinese_text_in_parts(text, max_chars=11999, logger=mock_logger)
        # Should create 2 chunks, one for each paragraph
        assert len(chunks) == 2
        assert all(len(chunk) < 12000 for chunk in chunks)

    def test_none_global_variables(self):
        """Test handling of None global variables"""
        from enchant_book_manager.text_splitter import split_chinese_text_in_parts
        from enchant_book_manager.file_handler import load_text_file

        # Functions should handle None logger gracefully
        # After our fixes, this should NOT raise AttributeError
        result = split_chinese_text_in_parts("test text", max_chars=100, logger=None)
        assert isinstance(result, list)
        assert len(result) == 1
        assert "test text" in result[0]

        # Test other functions too
        result = load_text_file("nonexistent.txt", logger=None)  # Should return None, not crash
        assert result is None

    def test_chunk_parsing_regex(self):
        """Test chunk filename parsing regex"""
        import re

        pattern = r"Chunk_(\d{6})\.txt$"

        # Valid formats
        match = re.search(pattern, "Book Title - Chunk_000001.txt")
        assert match is not None
        assert match.group(1) == "000001"

        match = re.search(pattern, "Chunk_123456.txt")
        assert match is not None
        assert match.group(1) == "123456"

        # Invalid formats
        assert re.search(pattern, "Chapter_1.txt") is None
        assert re.search(pattern, "Chunk_1.txt") is None
        assert re.search(pattern, "Chunk_00001.txt") is None  # Only 5 digits

        # 7 digits - should match first 6 only if using \d{6} not \d{6}$
        match = re.search(pattern, "Chunk_0000001.txt")
        assert match is None  # Pattern requires exactly 6 digits before .txt

    def test_unicode_handling(self):
        """Test handling of various Unicode characters"""
        from enchant_book_manager.text_processor import remove_excess_empty_lines

        # Chinese text with newlines
        text = "第一章\n\n\n\n\n中文内容"
        result = remove_excess_empty_lines(text)
        assert result == "第一章\n\n\n中文内容"

        # Mixed scripts
        text = "English\n\n\n\n\n中文\n\n\n\n\n日本語"
        result = remove_excess_empty_lines(text)
        assert result == "English\n\n\n中文\n\n\n日本語"

    def test_file_path_edge_cases(self):
        """Test handling of special characters in file paths"""
        # Test with spaces in title
        title = "Book With Spaces"
        author = "Author Name"
        chunk_num = 1

        filename = f"{title} by {author} - Chunk_{chunk_num:06d}.txt"
        assert filename == "Book With Spaces by Author Name - Chunk_000001.txt"

        # Test with special characters (should be handled by sanitize_filename)
        # This is just to ensure our format string works
        title = "Book: Subtitle"
        filename = f"{title} by {author} - Chunk_{chunk_num:06d}.txt"
        assert "Chunk_000001.txt" in filename

    def test_empty_book_handling(self):
        """Test handling of empty or very short books"""
        from enchant_book_manager.text_splitter import split_chinese_text_in_parts

        # Mock logger
        mock_logger = Mock()

        # Empty text
        chunks = split_chinese_text_in_parts("", max_chars=11999, logger=mock_logger)
        assert len(chunks) == 1
        assert chunks[0] == ""

        # Very short text (function adds \n\n to paragraphs)
        chunks = split_chinese_text_in_parts("Short", max_chars=11999, logger=mock_logger)
        assert len(chunks) == 1
        assert chunks[0] == "Short\n\n"

    def test_consistency_between_functions(self):
        """Test that different functions use consistent limits"""
        from enchant_book_manager.text_splitter import DEFAULT_MAX_CHARS
        from enchant_book_manager.text_splitter import split_chinese_text_in_parts

        # Check DEFAULT_MAX_CHARS
        assert DEFAULT_MAX_CHARS == 11999

        # Check that functions respect the limit
        mock_logger = Mock()

        # Create text that should split at paragraph boundary
        para1 = "A" * 6000
        para2 = "B" * 6000  # Total would be 12000
        text = f"{para1}\n\n{para2}"

        chunks = split_chinese_text_in_parts(text, max_chars=11999, logger=mock_logger)

        # Should split into 2 chunks
        assert len(chunks) == 2
        # Each chunk will have the paragraph + "\n\n", so slightly over 6000
        assert all(len(chunk) < 12000 for chunk in chunks)


if __name__ == "__main__":
    # Run tests
    if pytest:
        pytest.main([__file__, "-v"])
    else:
        # Manual test runner

        test_class = TestEdgeCases()
        test_methods = [method for method in dir(test_class) if method.startswith("test_") and callable(getattr(test_class, method))]

        passed = 0
        failed = 0

        print("Running Edge Case Tests...")
        print("=" * 80)

        for method_name in test_methods:
            try:
                method = getattr(test_class, method_name)
                method()
                print(f"✓ {method_name}")
                passed += 1
            except Exception as e:
                print(f"✗ {method_name}: {e}")
                failed += 1

        print("=" * 80)
        print(f"Results: {passed} passed, {failed} failed")
        sys.exit(0 if failed == 0 else 1)
