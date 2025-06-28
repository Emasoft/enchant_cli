#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test suite for chapter_parser module.
"""

import pytest
import re
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from enchant_book_manager.chapter_parser import (
    split_text_db,
    split_text,
    DB_OPTIMIZED,
)


class TestSplitText:
    """Test the split_text function."""

    def test_no_detection(self):
        """Test with chapter detection disabled."""
        text = "Chapter 1\nSome content\nChapter 2\nMore content"
        chapters, seq = split_text(text, detect_headings=False)

        assert len(chapters) == 1
        assert chapters[0][0] == "Content"
        assert chapters[0][1] == text
        assert seq == []

    def test_simple_chapters(self):
        """Test basic chapter detection."""
        text = """Chapter 1
First chapter content
Some more text

Chapter 2
Second chapter content"""

        chapters, seq = split_text(text, detect_headings=True)

        assert len(chapters) == 2
        assert chapters[0][0] == "Chapter 1"
        assert "First chapter content" in chapters[0][1]
        assert chapters[1][0] == "Chapter 2"
        assert "Second chapter content" in chapters[1][1]
        assert seq == [1, 2]

    def test_front_matter(self):
        """Test detection with front matter."""
        text = """Title Page
Author Name

Dedication

Chapter 1
First chapter"""

        chapters, seq = split_text(text, detect_headings=True)

        assert len(chapters) == 2
        assert chapters[0][0] == "Front Matter"
        assert "Title Page" in chapters[0][1]
        assert "Dedication" in chapters[0][1]
        assert chapters[1][0] == "Chapter 1"
        assert seq == [1]

    def test_roman_numerals(self):
        """Test chapters with Roman numerals."""
        text = """Chapter I
First chapter

Chapter II
Second chapter

Chapter III
Third chapter"""

        chapters, seq = split_text(text, detect_headings=True)

        assert len(chapters) == 3
        assert chapters[0][0] == "Chapter I"
        assert chapters[1][0] == "Chapter II"
        assert chapters[2][0] == "Chapter III"
        assert seq == [1, 2, 3]

    def test_word_numbers(self):
        """Test chapters with word numbers."""
        text = """Chapter One
First chapter

Chapter Two
Second chapter

Chapter Three
Third chapter"""

        chapters, seq = split_text(text, detect_headings=True)

        assert len(chapters) == 3
        assert chapters[0][0] == "Chapter One"
        assert chapters[1][0] == "Chapter Two"
        assert chapters[2][0] == "Chapter Three"
        assert seq == [1, 2, 3]

    def test_part_sections(self):
        """Test part and section detection."""
        text = """Part 1
Part introduction

Section 1
Section content"""

        chapters, seq = split_text(text, detect_headings=True)

        assert len(chapters) == 2
        # Since both have number 1, they get sub-numbering
        assert "Part 1" in chapters[0][0]
        assert "Part 1" in chapters[0][0] or "1.1" in chapters[0][0]
        assert "Section 1" in chapters[1][0]
        assert "Part 2" in chapters[1][0] or "1.2" in chapters[1][0]
        assert seq == [1, 1]

    def test_chapter_with_title(self):
        """Test chapters with titles after number."""
        text = """Chapter 1: The Beginning
First chapter content

Chapter 2: The Journey
Second chapter content"""

        chapters, seq = split_text(text, detect_headings=True)

        assert len(chapters) == 2
        assert chapters[0][0] == "Chapter 1: The Beginning"
        assert chapters[1][0] == "Chapter 2: The Journey"
        assert seq == [1, 2]

    def test_duplicate_detection_close(self):
        """Test duplicate chapter detection within 4 lines."""
        text = """Chapter 1
First line
Chapter 1
This is a duplicate
Chapter 2
Real second chapter"""

        chapters, seq = split_text(text, detect_headings=True)

        # The second "Chapter 1" should be ignored as duplicate
        assert len(chapters) == 2
        assert chapters[0][0] == "Chapter 1"
        assert "This is a duplicate" in chapters[0][1]
        assert chapters[1][0] == "Chapter 2"
        assert seq == [1, 2]

    def test_duplicate_detection_far(self):
        """Test chapters with same number far apart are not duplicates."""
        text = """Chapter 1
First chapter
Line 2
Line 3
Line 4
Line 5
Chapter 1
This is a new Chapter 1"""

        chapters, seq = split_text(text, detect_headings=True)

        # Should treat as separate chapters since >4 lines apart
        # But they get sub-numbering since they have the same number
        assert len(chapters) == 2
        assert "Chapter 1" in chapters[0][0]
        assert "Part 1" in chapters[0][0] or "1.1" in chapters[0][0]
        assert "Chapter 1" in chapters[1][0]
        assert "Part 2" in chapters[1][0] or "1.2" in chapters[1][0]
        assert seq == [1, 1]

    def test_multipart_chapters(self):
        """Test multi-part chapter detection and sub-numbering."""
        text = """Chapter 1
Part one content
Chapter 1 (Part 2)
Part two content
Chapter 1 - Part Three
Part three content"""

        chapters, seq = split_text(text, detect_headings=True)

        # The algorithm detects these as chapters
        assert len(chapters) >= 2

        # Check chapter titles
        chapter_titles = [ch[0] for ch in chapters]

        # Should have detected multiple chapters with Chapter 1
        # The exact format depends on the pattern matching
        assert any("Chapter 1" in title for title in chapter_titles)

        # Check that sub-numbering or part notation exists
        all_titles = " ".join(chapter_titles)
        assert "Part" in all_titles or ".1" in all_titles or ".2" in all_titles

        # The sequence should have multiple 1s
        assert len(seq) >= 2

    def test_invalid_chapter_line(self):
        """Test skipping invalid chapter lines (dialogue, etc.)."""
        text = """"I read Chapter 1 yesterday," she said.
Real content here
Chapter 1
Actual first chapter"""

        chapters, seq = split_text(text, detect_headings=True)

        # The dialogue line is not detected as a chapter, so it becomes front matter
        assert len(chapters) == 2
        assert chapters[0][0] == "Front Matter"
        assert '"I read Chapter 1 yesterday,"' in chapters[0][1]
        assert chapters[1][0] == "Chapter 1"
        assert "Actual first chapter" in chapters[1][1]
        assert seq == [1]

    def test_hash_chapters(self):
        """Test hash-style chapter markers."""
        text = """#001
First chapter

#002
Second chapter"""

        chapters, seq = split_text(text, detect_headings=True)

        assert len(chapters) == 2
        assert chapters[0][0] == "#001"
        assert chapters[1][0] == "#002"
        assert seq == [1, 2]

    def test_blank_only_sections(self):
        """Test handling of blank-only sections between chapters."""
        text = """Chapter 1
Content


Chapter 1


Chapter 2
New content"""

        chapters, seq = split_text(text, detect_headings=True)

        # Blank-only duplicate should be skipped
        assert len(chapters) == 2
        assert chapters[0][0] == "Chapter 1"
        assert chapters[1][0] == "Chapter 2"
        assert seq == [1, 2]

    def test_no_chapters_found(self):
        """Test when no chapters are detected."""
        text = """This is just regular text
without any chapter markers
or headings"""

        chapters, seq = split_text(text, detect_headings=True)

        assert len(chapters) == 1
        assert chapters[0][0] == "Content"
        assert chapters[0][1] == text.strip()
        assert seq == []

    def test_force_no_db(self):
        """Test forcing non-database processing."""
        text = "Chapter 1\nContent" * 10000  # Large text

        chapters, seq = split_text(text, detect_headings=True, force_no_db=True)

        # Should process without trying database optimization
        assert len(chapters) > 0
        assert chapters[0][0] == "Chapter 1"


class TestSplitTextDB:
    """Test the split_text_db function."""

    @patch("enchant_book_manager.chapter_parser.DB_OPTIMIZED", True)
    @patch("enchant_book_manager.chapter_parser.process_text_optimized")
    def test_db_optimization_success(self, mock_process):
        """Test successful database optimization."""
        text = "Chapter 1\nContent"
        mock_process.return_value = ([("Chapter 1", "Content")], [1])

        chapters, seq = split_text_db(text, detect_headings=True)

        assert chapters == [("Chapter 1", "Content")]
        assert seq == [1]
        mock_process.assert_called_once()

    @patch("enchant_book_manager.chapter_parser.DB_OPTIMIZED", True)
    @patch("enchant_book_manager.chapter_parser.process_text_optimized")
    def test_db_optimization_failure_fallback(self, mock_process):
        """Test fallback when database optimization fails."""
        text = "Chapter 1\nContent"
        mock_process.side_effect = Exception("DB error")
        mock_log = Mock()

        chapters, seq = split_text_db(text, detect_headings=True, log_issue_func=mock_log)

        # Should fallback to regular processing
        assert len(chapters) == 1
        assert chapters[0][0] == "Chapter 1"
        mock_log.assert_called_once()
        assert "Database processing failed" in mock_log.call_args[0][0]

    @patch("enchant_book_manager.chapter_parser.DB_OPTIMIZED", False)
    def test_db_not_available(self):
        """Test when database optimization is not available."""
        text = "Chapter 1\nContent"

        chapters, seq = split_text_db(text, detect_headings=True)

        # Should use regular processing
        assert len(chapters) == 1
        assert chapters[0][0] == "Chapter 1"

    def test_db_no_detection(self):
        """Test database function with detection disabled."""
        text = "Chapter 1\nContent"

        chapters, seq = split_text_db(text, detect_headings=False)

        assert chapters == [("Content", text)]
        assert seq == []


class TestLargeFileProcessing:
    """Test processing of large files with automatic DB optimization."""

    @patch("enchant_book_manager.chapter_parser.DB_OPTIMIZED", True)
    @patch("enchant_book_manager.chapter_parser.process_text_optimized")
    def test_large_file_uses_db(self, mock_process):
        """Test that large files automatically use database optimization."""
        # Create text with >100K lines (DB_OPTIMIZATION_THRESHOLD)
        large_text = "\n".join([f"Line {i}" for i in range(100001)])
        large_text = f"Chapter 1\n{large_text}"

        mock_process.return_value = ([("Chapter 1", "...")], [1])

        chapters, seq = split_text(large_text, detect_headings=True)

        # Should have tried database optimization
        mock_process.assert_called_once()

    @patch("enchant_book_manager.chapter_parser.DB_OPTIMIZED", True)
    @patch("enchant_book_manager.chapter_parser.process_text_optimized")
    def test_large_file_db_fails_fallback(self, mock_process):
        """Test fallback for large files when DB fails."""
        # Create text with >100K lines
        large_text = "Chapter 1\nContent\n" + "\n".join([f"Line {i}" for i in range(100001)])

        mock_process.side_effect = Exception("DB error")

        chapters, seq = split_text(large_text, detect_headings=True)

        # Should fallback to regular processing
        assert len(chapters) > 0
        assert chapters[0][0] == "Chapter 1"


class TestComplexChapterPatterns:
    """Test complex chapter patterns and edge cases."""

    def test_sequential_part_chapters(self):
        """Test sequential chapters with part notation."""
        text = """Chapter 1 (Part 1 of 3)
First part

Chapter 2 (Part 2 of 3)
Second part

Chapter 3 (Part 3 of 3)
Third part"""

        chapters, seq = split_text(text, detect_headings=True)

        # Should recognize as sequential, not sub-parts
        assert len(chapters) == 3
        # Should keep original titles without additional sub-numbering
        assert chapters[0][0] == "Chapter 1 (Part 1 of 3)"
        assert chapters[1][0] == "Chapter 2 (Part 2 of 3)"
        assert chapters[2][0] == "Chapter 3 (Part 3 of 3)"
        assert seq == [1, 2, 3]

    def test_mixed_numbering_styles(self):
        """Test mixing different numbering styles."""
        text = """Chapter 1
Arabic numeral

Chapter II
Roman numeral

Chapter Three
Word number

#004
Hash number"""

        chapters, seq = split_text(text, detect_headings=True)

        assert len(chapters) == 4
        assert seq == [1, 2, 3, 4]

    def test_chapter_with_special_characters(self):
        """Test chapters with special characters in titles."""
        text = """Chapter 1: The "Beginning"
Content one

Chapter 2 - The Journey's End
Content two"""

        chapters, seq = split_text(text, detect_headings=True)

        assert len(chapters) == 2
        assert chapters[0][0] == 'Chapter 1: The "Beginning"'
        assert chapters[1][0] == "Chapter 2 - The Journey's End"
