#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Comprehensive edge case tests for ENCHANT
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cli_translator
from unittest.mock import Mock

# Mock the logger
cli_translator.tolog = Mock()

def test_empty_text_handling():
    """Test handling of empty text"""
    print("Testing empty text handling...")
    
    # Test completely empty text
    result = cli_translator.split_chinese_text_in_parts("", max_chars=100)
    assert result == [""], f"Empty text should return [''], got {result}"
    
    # Test whitespace only
    result = cli_translator.split_chinese_text_in_parts("   \n  \n   ", max_chars=100)
    assert result == [""], f"Whitespace should return [''], got {result}"
    
    print("✓ Empty text handling tests passed")


def test_character_limit_strict():
    """Test that character limit is strictly less than 12000"""
    print("\nTesting character limit < 12000...")
    
    # Test with default MAXCHARS (should be 11999)
    assert cli_translator.MAXCHARS == 11999, f"MAXCHARS should be 11999, got {cli_translator.MAXCHARS}"
    
    # Test with multiple paragraphs that respect the limit
    para1 = "A" * 5000
    para2 = "B" * 5000
    para3 = "C" * 5000
    text = f"{para1}\n\n{para2}\n\n{para3}"
    
    chunks = cli_translator.split_chinese_text_in_parts(text, max_chars=11999)
    
    # Should create 2 chunks: first two paragraphs in chunk 1, third in chunk 2
    assert len(chunks) == 2, f"Expected 2 chunks, got {len(chunks)}"
    
    # Verify no chunk exceeds the practical limit (allowing single paragraphs to slightly exceed)
    for i, chunk in enumerate(chunks):
        # For multiple paragraph chunks, they should respect the limit
        if "\n\n" in chunk.strip():  # Multiple paragraphs
            assert len(chunk) < 12000, f"Multi-paragraph chunk {i} exceeds limit: {len(chunk)} chars"
    
    print("✓ Character limit tests passed")


def test_empty_line_reduction():
    """Test that empty lines are reduced to max 3 consecutive"""
    print("\nTesting empty line reduction...")
    
    # Test with many consecutive newlines
    text = "Line 1\n\n\n\n\n\n\nLine 2\n\n\n\n\n\n\n\n\nLine 3"
    result = cli_translator.remove_excess_empty_lines(text)
    
    # Check that no more than 3 consecutive newlines exist
    assert "\n\n\n\n" not in result, "Found 4+ consecutive newlines"
    assert "\n\n\n" in result, "Should preserve up to 3 newlines"
    
    # Test edge case with newlines at start/end
    text = "\n\n\n\n\n\nStart\n\n\n\n\nEnd\n\n\n\n\n"
    result = cli_translator.remove_excess_empty_lines(text)
    assert result.startswith("\n\n\n"), "Should preserve 3 newlines at start"
    assert result.endswith("\n\n\n"), "Should preserve 3 newlines at end"
    
    print("✓ Empty line reduction tests passed")


def test_chunk_naming_format():
    """Test chunk naming format with 6-digit padding"""
    print("\nTesting chunk naming format...")
    
    # Test regex pattern for chunk files
    import re
    pattern = r"Chunk_(\d{6})\.txt$"
    
    # Valid chunk names
    valid_names = [
        "Book Title by Author - Chunk_000001.txt",
        "Another Book by Someone - Chunk_999999.txt",
        "Test - Chunk_000100.txt"
    ]
    
    for name in valid_names:
        match = re.search(pattern, name)
        assert match is not None, f"Valid name '{name}' didn't match pattern"
        chunk_num = int(match.group(1))
        assert 1 <= chunk_num <= 999999, f"Chunk number out of range: {chunk_num}"
    
    # Invalid chunk names
    invalid_names = [
        "Book - Chapter 1.txt",  # Old format
        "Book - Chunk_1.txt",    # Not padded
        "Book - Chunk_0000001.txt",  # 7 digits
        "Book - chunk_000001.txt",   # lowercase
    ]
    
    for name in invalid_names:
        match = re.search(pattern, name)
        assert match is None, f"Invalid name '{name}' matched pattern"
    
    print("✓ Chunk naming format tests passed")


def test_paragraph_preservation():
    """Test that paragraphs are preserved correctly"""
    print("\nTesting paragraph preservation...")
    
    # Test with proper paragraphs
    text = """第一段内容。这是第一段的继续。

第二段内容。这是第二段的继续。

第三段内容。这是第三段的继续。"""
    
    chunks = cli_translator.split_chinese_text_in_parts(text, max_chars=200)
    assert len(chunks) == 1, "Small text should stay in one chunk"
    
    # Verify paragraphs are preserved
    assert "第一段" in chunks[0] and "第二段" in chunks[0] and "第三段" in chunks[0]
    
    print("✓ Paragraph preservation tests passed")


def test_special_characters():
    """Test handling of special characters"""
    print("\nTesting special character handling...")
    
    # Test with various special characters
    text = 'Test with émojis 😀 and symbols ™️ © ® and quotes "test" \'test\''
    chunks = cli_translator.split_chinese_text_in_parts(text, max_chars=200)
    
    assert len(chunks) == 1
    assert "😀" in chunks[0], "Emoji should be preserved"
    assert "™️" in chunks[0], "Symbols should be preserved"
    
    print("✓ Special character tests passed")


def test_mixed_content():
    """Test with mixed Chinese/English content"""
    print("\nTesting mixed content...")
    
    text = """Chapter 1: 开始

这是中文内容 with some English mixed in.

Another paragraph 另一段中文。

Final section 最后一部分。"""
    
    chunks = cli_translator.split_chinese_text_in_parts(text, max_chars=200)
    assert "Chapter 1" in chunks[0]
    assert "中文内容" in chunks[0]
    assert "English" in chunks[0]
    
    print("✓ Mixed content tests passed")


def test_boundary_conditions():
    """Test various boundary conditions"""
    print("\nTesting boundary conditions...")
    
    # Test single character
    result = cli_translator.split_chinese_text_in_parts("A", max_chars=10)
    assert len(result) == 1
    assert result[0].strip() == "A"
    
    # Test exactly at limit (accounting for paragraph ending)
    text = "A" * 11997  # 11997 + "\n\n" = 11999
    result = cli_translator.split_chinese_text_in_parts(text, max_chars=11999)
    assert len(result) == 1
    
    # Test just over limit
    text = "A" * 11998  # Would be 12000 with "\n\n"
    result = cli_translator.split_chinese_text_in_parts(text, max_chars=11999)
    assert len(result) == 1  # Single paragraph kept together
    
    print("✓ Boundary condition tests passed")


def test_none_safety():
    """Test that all functions handle None logger safely"""
    print("\nTesting None safety...")
    
    # Save original logger
    orig_logger = cli_translator.tolog
    
    try:
        # Set logger to None
        cli_translator.tolog = None
        
        # Test various functions that use logging
        # These functions should handle None logger gracefully
        result = cli_translator.load_text_file("nonexistent.txt")
        assert result is None  # Should return None for non-existent file
        
        # Test text processing functions
        cli_translator.split_chinese_text_in_parts("test", max_chars=100)
        cli_translator.remove_excess_empty_lines("test\n\n\n\n\ntest")
        cli_translator.limit_repeated_chars("test....")
        
        # Test with actual temporary file for save_text_file
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as tmp:
            tmp_path = tmp.name
        
        try:
            cli_translator.save_text_file("test content", tmp_path)
            # Verify file was created
            assert os.path.exists(tmp_path)
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
        
        print("✓ None safety tests passed")
        
    except AttributeError as e:
        print(f"✗ Function failed with None logger: {e}")
        raise
    
    finally:
        # Restore logger
        cli_translator.tolog = orig_logger


def run_all_tests():
    """Run all edge case tests"""
    print("=" * 60)
    print("Running comprehensive edge case tests...")
    print("=" * 60)
    
    tests = [
        test_empty_text_handling,
        test_character_limit_strict,
        test_empty_line_reduction,
        test_chunk_naming_format,
        test_paragraph_preservation,
        test_special_characters,
        test_mixed_content,
        test_boundary_conditions,
        test_none_safety,
    ]
    
    failed = 0
    for test in tests:
        try:
            test()
        except Exception as e:
            print(f"\n✗ {test.__name__} FAILED: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "=" * 60)
    if failed == 0:
        print(f"✓ All {len(tests)} tests passed!")
    else:
        print(f"✗ {failed}/{len(tests)} tests failed")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)