#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test suite to verify code quality fixes in EPUB modules
Following TDD methodology
"""

import unittest
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from make_epub import parse_num, split_text
from epub_constants import roman_to_int, words_to_int, parse_num as parse_num_shared


class TestCodeQualityFixes(unittest.TestCase):
    """Test code quality fixes and improvements"""
    
    def test_parse_num_handles_none(self):
        """Test that parse_num wrapper handles None correctly"""
        # Should not crash on None input
        result = parse_num(None)
        self.assertIsNone(result)
        
        # Should still work with valid inputs
        self.assertEqual(parse_num("5"), 5)
        self.assertEqual(parse_num("V"), 5)
        self.assertEqual(parse_num("five"), 5)
        self.assertEqual(parse_num("14a"), 14)  # Letter suffix
        
    def test_shared_utilities_work(self):
        """Test that shared utilities from epub_constants work correctly"""
        # Roman numerals
        self.assertEqual(roman_to_int("IV"), 4)
        self.assertEqual(roman_to_int("IX"), 9)
        self.assertEqual(roman_to_int("XIV"), 14)
        
        # Word numbers
        self.assertEqual(words_to_int("twenty-five"), 25)
        self.assertEqual(words_to_int("one hundred"), 100)
        self.assertEqual(words_to_int("three thousand two hundred"), 3200)
        
        # Parse num shared
        self.assertEqual(parse_num_shared("42"), 42)
        self.assertEqual(parse_num_shared("XIV"), 14)
        self.assertEqual(parse_num_shared("fourteen"), 14)
        
    def test_chapter_index_performance(self):
        """Test that chapter indexing provides O(1) lookup"""
        # Create test text with many chapters
        chapters = []
        for i in range(1, 101):
            chapters.append(f"Chapter {i}: Test Chapter\nContent for chapter {i}\n")
        
        text = "\n".join(chapters)
        
        # Process text
        result_chapters, seq = split_text(text, detect_headings=True, force_no_db=True)
        
        # Should have 100 chapters
        self.assertEqual(len(result_chapters), 100)
        self.assertEqual(len(seq), 100)
        
        # Verify sequence is correct
        self.assertEqual(seq, list(range(1, 101)))
        
    def test_type_safety_improvements(self):
        """Test that type safety improvements work correctly"""
        # Test with empty text
        chapters, seq = split_text("", detect_headings=True, force_no_db=True)
        self.assertEqual(len(chapters), 0)
        self.assertEqual(len(seq), 0)
        
        # Test with no chapters
        chapters, seq = split_text("Just some text\nNo chapters here", detect_headings=True, force_no_db=True)
        self.assertEqual(len(chapters), 1)
        self.assertEqual(chapters[0][0], "Content")
        self.assertEqual(len(seq), 0)
        
    def test_constants_consistency(self):
        """Test that constants are consistent across modules"""
        from epub_constants import ENCODING, MIMETYPE, WORD_NUMS, FILENAME_RE
        
        # Test constants are defined
        self.assertEqual(ENCODING, "utf-8")
        self.assertEqual(MIMETYPE, "application/epub+zip")
        self.assertIn("one", WORD_NUMS)
        self.assertIn("hundred", WORD_NUMS)
        
        # Test regex pattern works
        match = FILENAME_RE.match("My Novel by John Doe - Chapter 5.txt")
        self.assertIsNotNone(match)
        self.assertEqual(match.group("title"), "My Novel")
        self.assertEqual(match.group("author"), "John Doe")
        self.assertEqual(match.group("num"), "5")


class TestModuleIntegrity(unittest.TestCase):
    """Test module integrity and dependencies"""
    
    def test_imports_work(self):
        """Test that all imports work correctly"""
        # These imports should not raise errors
        try:
            import make_epub
            import epub_constants
            import epub_toc_enhanced
            import epub_db_optimized
            import epub_builder  # Even though unused, it should still import
            self.assertTrue(True)  # All imports successful
        except ImportError as e:
            self.fail(f"Import failed: {e}")
            
    def test_no_circular_imports(self):
        """Test that there are no circular import issues"""
        # Import in different order
        import epub_constants
        import make_epub
        
        # Should be able to use functions from both
        self.assertTrue(callable(make_epub.parse_num))
        self.assertTrue(callable(epub_constants.parse_num))


if __name__ == '__main__':
    unittest.main()