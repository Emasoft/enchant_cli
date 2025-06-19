#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test suite for part notation detection in make_epub.py
Following TDD methodology: Write tests first, then implementation
"""

import unittest
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from make_epub import has_part_notation, split_text  # noqa: E402


class TestPartNotationDetection(unittest.TestCase):
    """Test part notation detection functionality"""

    def test_has_part_notation_basic(self):
        """Test basic part notation patterns"""
        # Fraction formats
        self.assertTrue(has_part_notation("Chapter 5: The War 1/3"))
        self.assertTrue(has_part_notation("Chapter 5: The War [2/3]"))
        self.assertTrue(has_part_notation("Chapter 5: The War (3 of 5)"))
        self.assertTrue(has_part_notation("Chapter 5: The War (1 out of 3)"))

        # Part word formats
        self.assertTrue(has_part_notation("Chapter 5: The War - Part 1"))
        self.assertTrue(has_part_notation("Chapter 5: The War - part one"))
        self.assertTrue(has_part_notation("Chapter 5: The War pt. 2"))
        self.assertTrue(has_part_notation("Chapter 5: The War Pt 3"))

        # Dash number formats
        self.assertTrue(has_part_notation("Chapter 5: The War - 1"))
        self.assertTrue(has_part_notation("Chapter 5: The War - 2"))

        # Roman numerals (now more restrictive)
        self.assertTrue(has_part_notation("Chapter 5: The War Part I"))
        self.assertTrue(has_part_notation("Chapter 5: The War - II"))
        self.assertTrue(has_part_notation("Chapter 5: The War pt. III"))

    def test_has_part_notation_negative(self):
        """Test titles without part notation"""
        self.assertFalse(has_part_notation("Chapter 5: The War"))
        self.assertFalse(has_part_notation("Chapter 5: Introduction"))
        self.assertFalse(has_part_notation("Chapter 5: The Battle Begins"))
        self.assertFalse(has_part_notation("Chapter 5: Victory"))

    def test_has_part_notation_edge_cases(self):
        """Test edge cases"""
        # Empty string
        self.assertFalse(has_part_notation(""))

        # None should not crash (defensive programming)
        # Note: Current implementation might crash - we should fix this

        # Numbers that aren't parts
        self.assertFalse(has_part_notation("Chapter 5: Year 2023"))
        self.assertFalse(has_part_notation("Chapter 5: 100 Days Later"))

        # Roman numerals in other contexts (should not match)
        self.assertFalse(has_part_notation("Chapter 5: World War II History"))
        self.assertFalse(has_part_notation("Chapter 5: Louis XIV"))
        self.assertFalse(
            has_part_notation("Chapter 5: The War I")
        )  # Plain "I" at end no longer matches

    def test_has_part_notation_case_insensitive(self):
        """Test case insensitivity"""
        self.assertTrue(has_part_notation("Chapter 5: The War - PART 1"))
        self.assertTrue(has_part_notation("Chapter 5: The War - Part One"))
        self.assertTrue(has_part_notation("Chapter 5: The War (1 OF 3)"))
        self.assertTrue(has_part_notation("Chapter 5: The War (1 OUT OF 3)"))


class TestChapterSubNumbering(unittest.TestCase):
    """Test chapter sub-numbering logic"""

    def test_same_chapter_with_parts(self):
        """Test chapters with same number and part notation get sub-numbers"""
        text = """Chapter 5: The War - Part 1
Content for part 1

Chapter 5: The War - Part 2
Content for part 2

Chapter 5: The War - Part 3
Content for part 3"""

        chapters, seq = split_text(text, detect_headings=True, force_no_db=True)

        # Should have 3 chapters
        self.assertEqual(len(chapters), 3)

        # All should be chapter 5 with sub-numbers
        self.assertIn("5.1", chapters[0][0])
        self.assertIn("5.2", chapters[1][0])
        self.assertIn("5.3", chapters[2][0])

    def test_sequential_chapters_with_parts(self):
        """Test sequential chapter numbers with part notation stay unchanged"""
        text = """Chapter 5: The War Part 1
Content for chapter 5

Chapter 6: The War Part 2
Content for chapter 6

Chapter 7: The War Part 3
Content for chapter 7"""

        chapters, seq = split_text(text, detect_headings=True, force_no_db=True)

        # Should have 3 chapters
        self.assertEqual(len(chapters), 3)

        # Should NOT have sub-numbers
        self.assertEqual(chapters[0][0], "Chapter 5: The War Part 1")
        self.assertEqual(chapters[1][0], "Chapter 6: The War Part 2")
        self.assertEqual(chapters[2][0], "Chapter 7: The War Part 3")

    def test_letter_suffix_chapters(self):
        """Test chapters with letter suffixes (14a, 14b, 14c)"""
        text = """Chapter 14a: The First Battle
Content for chapter 14a

Chapter 14b: The First Battle Continues
Content for chapter 14b

Chapter 14c: The First Battle Ends
Content for chapter 14c"""

        chapters, seq = split_text(text, detect_headings=True, force_no_db=True)

        # Should have 3 chapters with sub-numbers
        self.assertEqual(len(chapters), 3)
        self.assertIn(".1", chapters[0][0])
        self.assertIn(".2", chapters[1][0])
        self.assertIn(".3", chapters[2][0])

    def test_mixed_chapters(self):
        """Test mix of regular chapters and multi-part chapters"""
        text = """Chapter 1: Introduction
Content

Chapter 2: Beginning
Content

Chapter 3: The Attack! 1/3
Content

Chapter 3: The Attack! 2/3
Content

Chapter 3: The Attack! 3/3
Content

Chapter 4: Recovery
Content"""

        chapters, seq = split_text(text, detect_headings=True, force_no_db=True)

        # Should have 6 chapters
        self.assertEqual(len(chapters), 6)

        # Regular chapters unchanged
        self.assertEqual(chapters[0][0], "Chapter 1: Introduction")
        self.assertEqual(chapters[1][0], "Chapter 2: Beginning")

        # Multi-part chapters have sub-numbers
        self.assertIn("3.1", chapters[2][0])
        self.assertIn("3.2", chapters[3][0])
        self.assertIn("3.3", chapters[4][0])

        # Back to regular
        self.assertEqual(chapters[5][0], "Chapter 4: Recovery")

    def test_no_false_positives(self):
        """Test that normal chapter titles aren't misidentified"""
        text = """Chapter 1: The Year 2020
Content

Chapter 2: 50 Ways to Success
Content

Chapter 3: World War II
Content

Chapter 4: Day 1 of Training
Content"""

        chapters, seq = split_text(text, detect_headings=True, force_no_db=True)

        # No chapters should have sub-numbers
        for i, (title, _) in enumerate(chapters):
            self.assertNotIn(".", title, f"Chapter {i+1} incorrectly has sub-number")


if __name__ == "__main__":
    unittest.main()
