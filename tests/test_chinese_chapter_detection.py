#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test suite for Chinese chapter pattern detection in EPUB generation.
"""

import unittest
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from make_epub import HEADING_RE, parse_num


class TestChineseChapterDetection(unittest.TestCase):
    """Test Chinese chapter pattern detection"""
    
    def test_existing_english_patterns_work(self):
        """Verify existing English patterns still work"""
        test_cases = [
            ("Chapter 1", 1),
            ("Chapter 42", 42),
            ("Chapter VII", 7),
            ("Chapter Seven", 7),
            ("CHAPTER 99", 99),
            ("chapter twenty-three", 23),
        ]
        
        for text, expected in test_cases:
            with self.subTest(text=text):
                match = HEADING_RE.match(text)
                self.assertIsNotNone(match, f"Failed to match: {text}")
                if match.group("num_d"):
                    num = int(match.group("num_d"))
                elif match.group("num_r"):
                    num = parse_num(match.group("num_r"))
                elif match.group("num_w"):
                    num = parse_num(match.group("num_w"))
                self.assertEqual(num, expected)
    
    def test_chinese_numeric_patterns(self):
        """Test Chinese numeric chapter patterns"""
        # These tests will fail until we implement Chinese pattern support
        test_cases = [
            ("第1章", 1),
            ("第42章", 42),
            ("第100章", 100),
            ("第１章", 1),  # Full-width numbers
            ("第一章", 1),
            ("第二章", 2),
            ("第十章", 10),
            ("第十一章", 11),
            ("第二十章", 20),
            ("第九十九章", 99),
            ("第一百章", 100),
            ("第一千章", 1000),
        ]
        
        # This test is expected to fail with current implementation
        # Uncomment when implementing Chinese support
        # for text, expected in test_cases:
        #     with self.subTest(text=text):
        #         match = CHINESE_HEADING_RE.match(text)
        #         self.assertIsNotNone(match, f"Failed to match: {text}")
        #         num = parse_chinese_num(match.group("num"))
        #         self.assertEqual(num, expected)
    
    def test_mixed_content_chapter_detection(self):
        """Test detecting chapters in mixed English/Chinese content"""
        content = """
Chapter 1
This is the first chapter in English.

第二章
这是第二章的中文内容。

Chapter Three
Back to English for chapter three.

第4章
第四章又是中文。
"""
        # This will test the split_text function when updated
        # Expected: 4 chapters detected
        pass
    
    def test_chinese_number_parsing(self):
        """Test parsing Chinese numbers to integers"""
        test_cases = [
            ("一", 1),
            ("二", 2),
            ("三", 3),
            ("四", 4),
            ("五", 5),
            ("六", 6),
            ("七", 7),
            ("八", 8),
            ("九", 9),
            ("十", 10),
            ("十一", 11),
            ("十二", 12),
            ("二十", 20),
            ("二十三", 23),
            ("九十九", 99),
            ("一百", 100),
            ("一百零一", 101),
            ("二百五十", 250),
            ("九百九十九", 999),
            ("一千", 1000),
            ("一千零一", 1001),
            ("两千", 2000),
            ("九千九百九十九", 9999),
        ]
        
        # This test is for the future parse_chinese_num function
        # for text, expected in test_cases:
        #     with self.subTest(text=text):
        #         result = parse_chinese_num(text)
        #         self.assertEqual(result, expected)


if __name__ == '__main__':
    unittest.main()