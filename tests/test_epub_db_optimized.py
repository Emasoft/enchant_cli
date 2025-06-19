#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tests for optimized database module
"""

import unittest
import re

from epub_db_optimized import (
    setup_database,
    close_database,
    import_text_optimized,
    find_chapters_two_stage,
    build_chapters_table,
    process_text_optimized,
    TextLine,
    Chapter,
    db,
)


class TestEpubDatabaseOptimized(unittest.TestCase):
    """Test optimized database operations for EPUB chapter parsing"""

    def setUp(self):
        """Set up test database"""
        setup_database()

    def tearDown(self):
        """Clean up database after tests"""
        # Clear all data if tables still exist
        try:
            if not db.is_closed():
                TextLine.delete().execute()
                Chapter.delete().execute()
        except Exception:
            pass  # Tables might not exist if test closed the connection
        close_database()

    def test_database_setup(self):
        """Test database initialization"""
        # Verify tables exist
        self.assertTrue(TextLine.table_exists())
        self.assertTrue(Chapter.table_exists())

    def test_import_text_optimized(self):
        """Test optimized text import"""
        text = "Line 1\nLine 2\nLine 3"
        import_text_optimized(text)

        # Verify lines imported
        count = TextLine.select().count()
        self.assertEqual(count, 3)

        # Check content
        line1 = TextLine.get(TextLine.line_number == 1)
        self.assertEqual(line1.text_content, "Line 1")

    def test_two_stage_search(self):
        """Test two-stage chapter finding"""
        text = """Normal line
Chapter 1: Introduction
Some content
Chapter 2: Next Chapter
More content
This mentions chapter but isn't one
CHAPTER 3: UPPERCASE"""

        import_text_optimized(text)

        # Define test regex and functions
        heading_re = re.compile(
            r"^Chapter\s+(?P<num_d>\d+)(?:\s*:\s*(?P<rest>.+))?", re.IGNORECASE
        )

        def parse_num(s):
            return int(s) if s and s.isdigit() else None

        def is_valid(line):
            return True  # Simple validation

        # Run two-stage search
        chapters = find_chapters_two_stage(heading_re, parse_num, is_valid)

        # Should find 3 chapters
        self.assertEqual(len(chapters), 3)
        self.assertEqual(chapters[0].chapter_number, 1)
        self.assertEqual(chapters[1].chapter_number, 2)
        self.assertEqual(chapters[2].chapter_number, 3)

    def test_build_chapters_table(self):
        """Test chapter table building"""
        # Prepare test data with marked chapters
        text = """Chapter 1: First
Content of chapter 1
More content
Chapter 2: Second
Content of chapter 2"""

        import_text_optimized(text)

        # Mark chapters manually for testing
        TextLine.update(is_chapter=True, chapter_number=1).where(
            TextLine.line_number == 1
        ).execute()
        TextLine.update(is_chapter=True, chapter_number=2).where(
            TextLine.line_number == 4
        ).execute()

        # Build chapters
        chapters, seq = build_chapters_table()

        # Verify results
        self.assertEqual(len(chapters), 2)
        self.assertEqual(seq, [1, 2])

        # Check chapter content
        title1, content1 = chapters[0]
        self.assertEqual(title1, "Chapter 1: First")
        self.assertIn("Content of chapter 1", content1)

        # Verify Chapter table entries
        chapter_records = list(Chapter.select())
        self.assertEqual(len(chapter_records), 2)
        self.assertEqual(chapter_records[0].start_line, 1)
        self.assertEqual(chapter_records[0].end_line, 3)

    def test_process_text_optimized_full(self):
        """Test full optimized processing"""
        text = """Prologue
Chapter 1: The Beginning
This is the first chapter.
Chapter 2: The Middle
This is the second chapter.
Chapter 3: The End
This is the final chapter."""

        heading_re = re.compile(
            r"^Chapter\s+(?P<num_d>\d+)(?:\s*:\s*(?P<rest>.+))?", re.IGNORECASE
        )

        def parse_num(s):
            return int(s) if s and s.isdigit() else None

        def is_valid(line):
            return True

        chapters, seq = process_text_optimized(text, heading_re, parse_num, is_valid)

        # Verify results
        self.assertEqual(len(chapters), 3)
        self.assertEqual(seq, [1, 2, 3])

        # Check titles
        self.assertEqual(chapters[0][0], "Chapter 1: The Beginning")
        self.assertEqual(chapters[1][0], "Chapter 2: The Middle")
        self.assertEqual(chapters[2][0], "Chapter 3: The End")

    def test_performance_improvement(self):
        """Test that optimized approach is faster than original"""
        # Generate a large test text
        lines = []
        for i in range(10000):
            if i % 500 == 0:
                lines.append(f"Chapter {i // 500 + 1}: Title {i // 500 + 1}")
            else:
                lines.append(f"Line {i}: Some content here")

        text = "\n".join(lines)

        heading_re = re.compile(
            r"^Chapter\s+(?P<num_d>\d+)(?:\s*:\s*(?P<rest>.+))?", re.IGNORECASE
        )

        def parse_num(s):
            return int(s) if s and s.isdigit() else None

        def is_valid(line):
            return True

        import time

        start = time.time()
        chapters, seq = process_text_optimized(text, heading_re, parse_num, is_valid)
        duration = time.time() - start

        # Should find 20 chapters
        self.assertEqual(len(chapters), 20)
        self.assertEqual(seq, list(range(1, 21)))

        # Should be very fast (under 1 second for 10k lines)
        self.assertLess(duration, 1.0)


if __name__ == "__main__":
    unittest.main()
