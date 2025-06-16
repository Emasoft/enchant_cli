#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test suite for epub_db.py - Database module for fast chapter indexing.
Tests peewee ORM mapping functions and database operations.
"""

import unittest
import re
from pathlib import Path
from typing import List, Tuple, Optional

from epub_db import (
    setup_database, close_database, import_text_to_db,
    find_and_mark_chapters, get_chapters_with_content,
    get_chapter_statistics,
    BookLine, LineVariation, db
)
from peewee import fn


class TestEpubDatabase(unittest.TestCase):
    """Test database operations for EPUB chapter parsing"""
    
    def setUp(self):
        """Set up test database before each test"""
        setup_database()
        
    def tearDown(self):
        """Clean up database after each test"""
        try:
            # Clear all data from tables
            BookLine.delete().execute()
            LineVariation.delete().execute()
        except Exception:
            # If tables don't exist or other error, ignore
            pass
        finally:
            close_database()
    
    def test_database_setup(self):
        """Test database initialization and table creation"""
        # Tables should exist
        self.assertTrue(BookLine.table_exists())
        self.assertTrue(LineVariation.table_exists())
        
        # Should be able to query empty tables
        self.assertEqual(BookLine.select().count(), 0)
        self.assertEqual(LineVariation.select().count(), 0)
    
    def test_import_simple_text(self):
        """Test importing simple text into database"""
        text = """Line 1
Line 2
Line 3"""
        
        import_text_to_db(text, book_id='test_book')
        
        # Verify BookLine entries
        book_lines = list(BookLine.select().order_by(BookLine.book_line_number))
        self.assertEqual(len(book_lines), 3)
        self.assertEqual(book_lines[0].book_line_number, 1)
        self.assertEqual(book_lines[2].book_line_number, 3)
        
        # Verify LineVariation entries
        line_vars = list(LineVariation.select().order_by(LineVariation.book_line_number))
        self.assertEqual(len(line_vars), 3)
        self.assertEqual(line_vars[0].text_content, "Line 1")
        self.assertEqual(line_vars[1].text_content, "Line 2")
        self.assertEqual(line_vars[2].text_content, "Line 3")
    
    def test_import_empty_text(self):
        """Test importing empty text"""
        import_text_to_db("", book_id='empty_book')
        
        self.assertEqual(BookLine.select().count(), 0)
        self.assertEqual(LineVariation.select().count(), 0)
    
    def test_find_chapter_headings(self):
        """Test finding and marking chapter headings"""
        text = """Some front matter
Chapter 1: Introduction
This is the first chapter.
Chapter 2: The Beginning
This is the second chapter.
Not a chapter: Chapter 3 in dialogue
Chapter 3: Real Chapter
End of book"""
        
        import_text_to_db(text)
        
        # Define test regex with proper named groups (matching make_epub.py)
        heading_re = re.compile(
            r"^Chapter\s+(?P<num_d>\d+)(?:\s*:\s*(?P<rest>.+))?", 
            re.IGNORECASE
        )
        
        def parse_num(s: Optional[str]) -> Optional[int]:
            return int(s) if s and s.isdigit() else None
        
        def is_valid(line: str) -> bool:
            # Simple validation - chapter at start of line
            return line.strip().lower().startswith('chapter')
        
        # Find and mark chapters
        find_and_mark_chapters(heading_re, parse_num, is_valid)
        
        # Check marked chapters
        chapters = list(BookLine.select().where(BookLine.is_chapter_heading).order_by(BookLine.book_line_number))
        self.assertEqual(len(chapters), 3)
        
        # Verify chapter numbers and titles
        self.assertEqual(chapters[0].chapter_number, 1)
        self.assertEqual(chapters[0].book_line_title, "Chapter 1 – Introduction")
        self.assertEqual(chapters[1].chapter_number, 2)
        self.assertEqual(chapters[2].chapter_number, 3)
    
    def test_duplicate_chapter_detection(self):
        """Test duplicate chapter detection within 4-line window"""
        text = """Chapter 1: First
Chapter 1: First
Some text
More text
Chapter 1: Different subtitle
Chapter 2: Second"""
        
        import_text_to_db(text)
        
        heading_re = re.compile(
            r"^Chapter\s+(?P<num_d>\d+)(?:\s*:\s*(?P<rest>.+))?", 
            re.IGNORECASE
        )
        parse_num = lambda s: int(s) if s and s.isdigit() else None
        is_valid = lambda line: line.strip().lower().startswith('chapter')
        
        find_and_mark_chapters(heading_re, parse_num, is_valid)
        
        # Should have 3 chapters (duplicate on line 2 ignored)
        chapters = list(BookLine.select().where(BookLine.is_chapter_heading).order_by(BookLine.book_line_number))
        self.assertEqual(len(chapters), 3)
        
        # Line numbers should be 1, 5, 6
        self.assertEqual([ch.book_line_number for ch in chapters], [1, 5, 6])
    
    def test_get_chapters_with_content(self):
        """Test retrieving chapters with their content"""
        text = """Front matter text
Chapter 1: First
Content of chapter 1
More content
Chapter 2: Second
Content of chapter 2"""
        
        import_text_to_db(text)
        
        heading_re = re.compile(
            r"^Chapter\s+(?P<num_d>\d+)(?:\s*:\s*(?P<rest>.+))?", 
            re.IGNORECASE
        )
        parse_num = lambda s: int(s) if s and s.isdigit() else None
        is_valid = lambda line: line.strip().lower().startswith('chapter')
        
        find_and_mark_chapters(heading_re, parse_num, is_valid)
        
        # Get chapters with content
        chapters, seq = get_chapters_with_content()
        
        # Should have front matter + 2 chapters
        self.assertEqual(len(chapters), 3)
        
        # Check front matter
        self.assertEqual(chapters[0][0], "Front Matter")
        self.assertEqual(chapters[0][1], "Front matter text")
        
        # Check chapters
        self.assertEqual(chapters[1][0], "Chapter 1 – First")
        self.assertIn("Content of chapter 1", chapters[1][1])
        self.assertEqual(chapters[2][0], "Chapter 2 – Second")
        self.assertIn("Content of chapter 2", chapters[2][1])
        
        # Check sequence
        self.assertEqual(seq, [1, 2])
    
    def test_multipart_chapter_subnumbering(self):
        """Test sub-numbering for multi-part chapters"""
        text = """Chapter 1: Part One
Content
Chapter 1: Part Two
Content
Chapter 1: Part Three
Content
Chapter 2: Normal Chapter
Content"""
        
        import_text_to_db(text)
        
        heading_re = re.compile(
            r"^Chapter\s+(?P<num_d>\d+)(?:\s*:\s*(?P<rest>.+))?", 
            re.IGNORECASE
        )
        parse_num = lambda s: int(s) if s and s.isdigit() else None
        is_valid = lambda line: line.strip().lower().startswith('chapter')
        
        find_and_mark_chapters(heading_re, parse_num, is_valid)
        
        chapters, seq = get_chapters_with_content()
        
        # Check sub-numbering applied
        self.assertEqual(chapters[0][0], "Chapter 1.1: Part One")
        self.assertEqual(chapters[1][0], "Chapter 1.2: Part Two")
        self.assertEqual(chapters[2][0], "Chapter 1.3: Part Three")
        self.assertEqual(chapters[3][0], "Chapter 2 – Normal Chapter")
        
        # Sequence should have original numbers
        self.assertEqual(seq, [1, 1, 1, 2])
    
    def test_peewee_orm_queries(self):
        """Test various peewee ORM query patterns"""
        text = """Line with chapter mention
CHAPTER 2: UPPERCASE
Normal line
Chapter in "quotes"
Another chapter 3 here"""
        
        import_text_to_db(text)
        
        # Test regex_search UDF functionality
        from peewee import fn
        
        # Test case-insensitive regex search
        chapter_lines = (LineVariation
                        .select()
                        .where(fn.regex_search(r'(?i)chapter', LineVariation.text_content))
                        .order_by(LineVariation.book_line_number))
        
        # Should find 4 lines containing 'chapter' (case-insensitive)
        results = list(chapter_lines)
        self.assertEqual(len(results), 4)
        
        # Test join query
        joined_query = (LineVariation
                       .select(LineVariation, BookLine)
                       .join(BookLine, on=(LineVariation.book_line_id == BookLine.book_line_id))
                       .where(LineVariation.book_line_number > 2))
        
        # Should get lines 3, 4, 5
        self.assertEqual(joined_query.count(), 3)
        
        # Test aggregation
        max_line = BookLine.select(fn.MAX(BookLine.book_line_number)).scalar()
        self.assertEqual(max_line, 5)
    
    def test_large_text_performance(self):
        """Test performance with larger text (not 600K lines, but reasonable for test)"""
        # Generate text with 1000 lines and 10 chapters
        lines = []
        chapter_num = 1
        
        for i in range(1000):
            if i % 100 == 0:
                lines.append(f"Chapter {chapter_num}: Chapter Title {chapter_num}")
                chapter_num += 1
            else:
                lines.append(f"Line {i}: Some content here")
        
        text = '\n'.join(lines)
        
        # Import and process
        import_text_to_db(text)
        
        heading_re = re.compile(
            r"^Chapter\s+(?P<num_d>\d+)(?:\s*:\s*(?P<rest>.+))?", 
            re.IGNORECASE
        )
        parse_num = lambda s: int(s) if s and s.isdigit() else None
        is_valid = lambda line: line.strip().lower().startswith('chapter')
        
        find_and_mark_chapters(heading_re, parse_num, is_valid)
        
        # Verify all chapters found
        chapters = BookLine.select().where(BookLine.is_chapter_heading).count()
        self.assertEqual(chapters, 10)
        
        # Test efficient filtering using regex_search
        from peewee import fn
        
        # This should be fast - only checking ~10 lines instead of 1000
        potential_chapters = (LineVariation
                            .select()
                            .where(fn.regex_search(r'(?i)^chapter\s+\d+', LineVariation.text_content))
                            .count())
        
        self.assertEqual(potential_chapters, 10)
    
    def test_regex_search_advanced_patterns(self):
        """Test regex_search with complex patterns"""
        text = """Prologue
Chapter 1: Introduction
Ch. 2 - The Beginning
CHAPTER THREE: UPPERCASE
Chap 4: Abbreviated
Chapter V: Roman Numerals
Part 1: Different Pattern
§ 42: Section Style
5. Numbered List Style
Not a valid chapter in middle of line"""
        
        import_text_to_db(text)
        
        # Test the actual complex heading regex pattern
        # Note: regex_search uses case-insensitive by default in our implementation
        pattern = r"^[^\w]*\s*(?:(?:chapter|ch\.?|chap\.?)\s*\d+|(?:chapter|ch\.?|chap\.?)\s*[ivxlcdm]+|(?:part|section)\s+\d+|§\s*\d+|\d+\s*(?:\.|:|-)?)"
        
        matches = (LineVariation
                  .select()
                  .where(fn.regex_search(pattern, LineVariation.text_content))
                  .order_by(LineVariation.book_line_number))
        
        # Debug: print what was matched
        results = list(matches)
        print(f"\nMatched {len(results)} lines:")
        for r in results:
            print(f"  Line {r.book_line_number}: '{r.text_content}'")
        
        # Should match lines 2, 3, 5, 6, 7, 8, 9 (not line 4 which has word "THREE")
        # Updated expectation based on actual regex capabilities
        self.assertEqual(len(results), 7)
        
        # Verify specific matches
        matched_texts = [r.text_content for r in results]
        self.assertIn("Chapter 1: Introduction", matched_texts)
        self.assertIn("Ch. 2 - The Beginning", matched_texts)
        self.assertIn("Chap 4: Abbreviated", matched_texts)
        self.assertIn("Chapter V: Roman Numerals", matched_texts)
        self.assertIn("Part 1: Different Pattern", matched_texts)
        self.assertIn("§ 42: Section Style", matched_texts)
        self.assertIn("5. Numbered List Style", matched_texts)
        self.assertNotIn("CHAPTER THREE: UPPERCASE", matched_texts)  # Word numbers not in this pattern
        self.assertNotIn("Not a valid chapter in middle of line", matched_texts)


if __name__ == '__main__':
    unittest.main()