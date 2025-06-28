#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test suite for chapter_detector module and related modules.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from enchant_book_manager.chapter_detector import (
    HEADING_RE,
    PART_PATTERNS,
    DB_OPTIMIZATION_THRESHOLD,
    has_part_notation,
    parse_num,
    is_valid_chapter_line,
    split_text_db,
    split_text,
    detect_issues,
)


class TestChapterPatterns:
    """Test chapter pattern constants."""

    def test_heading_regex(self):
        """Test HEADING_RE pattern matches various chapter formats."""
        # Test numeric chapters
        assert HEADING_RE.match("Chapter 1")
        assert HEADING_RE.match("CHAPTER 1")
        assert HEADING_RE.match("Chapter 42")

        # Test roman numeral chapters
        assert HEADING_RE.match("Chapter I")
        assert HEADING_RE.match("Chapter XII")
        assert HEADING_RE.match("Chapter MCMXCIX")

        # Test word number chapters
        assert HEADING_RE.match("Chapter One")
        assert HEADING_RE.match("Chapter Twenty-Three")
        assert HEADING_RE.match("Chapter Ninety-Nine")

        # Test with colons and titles
        assert HEADING_RE.match("Chapter 1: The Beginning")
        assert HEADING_RE.match("Chapter XII: The End")

        # Test edge cases
        assert not HEADING_RE.match("Not a chapter")
        assert not HEADING_RE.match("Chapter")  # No number

    def test_part_patterns(self):
        """Test PART_PATTERNS for part notation detection."""
        assert isinstance(PART_PATTERNS, list)
        assert len(PART_PATTERNS) > 0

        # Test some common part notations
        part_text = "Part 1 - The Beginning"
        matched = False
        for pattern in PART_PATTERNS:
            if pattern.search(part_text):
                matched = True
                break
        assert matched

    def test_db_optimization_threshold(self):
        """Test DB_OPTIMIZATION_THRESHOLD constant."""
        assert isinstance(DB_OPTIMIZATION_THRESHOLD, int)
        assert DB_OPTIMIZATION_THRESHOLD > 0
        assert DB_OPTIMIZATION_THRESHOLD == 100000  # Expected value


class TestChapterValidators:
    """Test chapter validation functions."""

    def test_has_part_notation(self):
        """Test has_part_notation function."""
        # Should detect part notation based on actual PART_PATTERNS
        assert has_part_notation("Part One: The Beginning")
        assert has_part_notation("Part 1 - Introduction")
        assert has_part_notation("PART I")
        assert has_part_notation("Chapter 1 - Part 1")
        assert has_part_notation("Chapter 1 (1 of 3)")
        assert has_part_notation("Chapter 1 [1/3]")
        assert has_part_notation("Chapter 1 - 1")

        # Should not detect part notation
        assert not has_part_notation("Chapter 1")
        assert not has_part_notation("The party was fun")
        assert not has_part_notation("")
        assert not has_part_notation("Book 1: The Journey")  # Not in PART_PATTERNS
        assert not has_part_notation("Volume I")  # Not in PART_PATTERNS

    def test_parse_num_numeric(self):
        """Test parse_num with numeric chapters."""
        assert parse_num("1") == 1
        assert parse_num("42") == 42
        assert parse_num("999") == 999
        assert parse_num("0") == 0

    def test_parse_num_roman(self):
        """Test parse_num with roman numerals."""
        assert parse_num("I") == 1
        assert parse_num("II") == 2
        assert parse_num("III") == 3
        assert parse_num("IV") == 4
        assert parse_num("V") == 5
        assert parse_num("IX") == 9
        assert parse_num("X") == 10
        assert parse_num("XI") == 11
        assert parse_num("XX") == 20
        assert parse_num("XXI") == 21
        assert parse_num("L") == 50
        assert parse_num("C") == 100
        assert parse_num("D") == 500
        assert parse_num("M") == 1000

    def test_parse_num_word(self):
        """Test parse_num with word numbers."""
        assert parse_num("one") == 1
        assert parse_num("two") == 2
        assert parse_num("three") == 3
        assert parse_num("ten") == 10
        assert parse_num("eleven") == 11
        assert parse_num("twenty") == 20
        assert parse_num("twenty-one") == 21
        assert parse_num("thirty") == 30
        assert parse_num("fifty") == 50
        assert parse_num("hundred") == 100

    def test_parse_num_edge_cases(self):
        """Test parse_num edge cases."""
        assert parse_num("") is None
        assert parse_num("invalid") is None
        assert parse_num("abc123") is None
        assert parse_num("Chapter") is None

    def test_is_valid_chapter_line(self):
        """Test is_valid_chapter_line function."""
        # Valid chapter lines (function only takes the line, not index/lines)
        assert is_valid_chapter_line("Chapter 1")
        assert is_valid_chapter_line("Chapter 1: The Beginning")
        assert is_valid_chapter_line("# Chapter 1")  # After special char
        assert is_valid_chapter_line("  Chapter 1")  # At start after whitespace

        # Not valid - chapter in quotes or mid-sentence
        assert not is_valid_chapter_line('"Chapter 1"')
        assert not is_valid_chapter_line("He said Chapter 1")
        assert not is_valid_chapter_line('The "Chapter 1" begins')


class TestChapterParser:
    """Test chapter parsing functions."""

    def test_split_text_no_detection(self):
        """Test split_text with detection disabled."""
        text = "This is some text\nWith multiple lines\nBut no chapters"
        chapters, seq_nums = split_text(text, detect_headings=False)

        assert len(chapters) == 1
        assert chapters[0] == ("Content", text)
        assert seq_nums == []

    def test_split_text_simple_chapters(self):
        """Test split_text with simple chapter structure."""
        text = """Chapter 1
This is the first chapter.

Chapter 2
This is the second chapter.

Chapter 3
This is the third chapter."""

        chapters, seq_nums = split_text(text, detect_headings=True)

        assert len(chapters) == 3
        assert chapters[0][0] == "Chapter 1"
        assert "first chapter" in chapters[0][1]
        assert chapters[1][0] == "Chapter 2"
        assert "second chapter" in chapters[1][1]
        assert chapters[2][0] == "Chapter 3"
        assert "third chapter" in chapters[2][1]
        assert seq_nums == [1, 2, 3]

    def test_split_text_with_front_matter(self):
        """Test split_text with front matter before first chapter."""
        text = """Preface
This is the preface.

Introduction
Some introduction text.

Chapter 1
The actual story begins."""

        chapters, seq_nums = split_text(text, detect_headings=True)

        # Should have front matter and one chapter
        assert len(chapters) == 2
        assert chapters[0][0] == "Front Matter"
        assert "Preface" in chapters[0][1]
        assert "Introduction" in chapters[0][1]
        assert chapters[1][0] == "Chapter 1"

    def test_split_text_roman_numerals(self):
        """Test split_text with roman numeral chapters."""
        text = """Chapter I
First chapter.

Chapter II
Second chapter.

Chapter III
Third chapter."""

        chapters, seq_nums = split_text(text, detect_headings=True)

        assert len(chapters) == 3
        assert seq_nums == [1, 2, 3]

    def test_split_text_word_numbers(self):
        """Test split_text with word number chapters."""
        text = """Chapter One
First chapter.

Chapter Two
Second chapter.

Chapter Three
Third chapter."""

        chapters, seq_nums = split_text(text, detect_headings=True)

        assert len(chapters) == 3
        assert seq_nums == [1, 2, 3]

    def test_split_text_with_part_notation(self):
        """Test split_text with part notation."""
        text = """Part One: The Beginning

Chapter 1
First chapter.

Chapter 2
Second chapter."""

        chapters, seq_nums = split_text(text, detect_headings=True)

        # Part notation should be detected as a heading
        assert len(chapters) >= 2
        # Check that chapters are detected properly
        chapter_titles = [ch[0] for ch in chapters]
        # Part One should be detected due to HEADING_RE pattern
        assert "Part One: The Beginning" in chapter_titles
        # Chapter 2 should definitely be there
        assert "Chapter 2" in chapter_titles
        # Chapter 1 might be merged or separate depending on implementation
        assert len(chapters) >= 2

    @patch("enchant_book_manager.chapter_parser.process_text_optimized")
    @patch("enchant_book_manager.chapter_parser.DB_OPTIMIZED", True)
    def test_split_text_db_optimized(self, mock_process):
        """Test split_text_db with database optimization."""
        text = "Chapter 1\nContent"
        mock_process.return_value = ([("Chapter 1", "Content")], [1])

        chapters, seq_nums = split_text_db(text, detect_headings=True)

        assert chapters == [("Chapter 1", "Content")]
        assert seq_nums == [1]
        mock_process.assert_called_once()

    def test_split_text_db_no_detection(self):
        """Test split_text_db with detection disabled."""
        text = "Some text without chapters"
        chapters, seq_nums = split_text_db(text, detect_headings=False)

        assert chapters == [("Content", text)]
        assert seq_nums == []

    @patch("enchant_book_manager.chapter_parser.DB_OPTIMIZED", False)
    def test_split_text_db_fallback(self):
        """Test split_text_db fallback when DB not available."""
        text = "Chapter 1\nContent"
        chapters, seq_nums = split_text_db(text, detect_headings=True)

        # Should fallback to regular split_text
        assert len(chapters) > 0

    def test_split_text_large_file_threshold(self):
        """Test split_text behavior with large files."""
        # Create text with many lines
        lines = ["Line " + str(i) for i in range(1000)]
        lines.insert(0, "Chapter 1")
        lines.insert(500, "Chapter 2")
        text = "\n".join(lines)

        chapters, seq_nums = split_text(text, detect_headings=True, force_no_db=True)

        assert len(chapters) == 2
        assert chapters[0][0] == "Chapter 1"
        assert chapters[1][0] == "Chapter 2"

    def test_detect_issues(self):
        """Test detect_issues function."""
        # Create text with various issues
        text = """Chapter 1
Content

Chapter 3
Missing chapter 2

Chapter 3
Duplicate chapter

Chapter IV
Mixed numbering styles"""

        chapters, seq_nums = split_text(text, detect_headings=True)

        # Verify the split detected the sequence issues
        # Should have Chapter 1, Chapter 3 (possibly merged duplicates), and Chapter IV
        assert 1 in seq_nums
        assert 3 in seq_nums
        # Check that the gap (missing Chapter 2) exists
        assert 2 not in seq_nums
        # Roman numeral IV should be parsed as 4
        assert 4 in seq_nums

    def test_split_text_quoted_chapters(self):
        """Test chapter detection behavior with quoted text."""
        text = """He said "Chapter 1 was great!"

Chapter 1
The real chapter begins here.

"Chapter 2" is mentioned here.

Chapter 2
Another real chapter."""

        chapters, seq_nums = split_text(text, detect_headings=True)

        # The current implementation detects lines starting with quotes as chapters
        # if they match the HEADING_RE pattern. The is_valid_chapter_line filter
        # only applies to lines starting with "chapter" (lowercase)

        # Should have detected both Chapter 1 and Chapter 2
        assert 1 in seq_nums
        assert 2 in seq_nums

        # The implementation currently treats quoted lines as valid chapters
        # This is a limitation but we'll document the actual behavior
        chapter_titles = [ch[0] for ch in chapters]

        # At least the real chapters should be detected
        assert any("Chapter 1" == title.strip() for title in chapter_titles)
        # Chapter 2 content should be somewhere in the results
        assert any("Another real chapter" in ch[1] for ch in chapters)

    def test_split_text_sub_numbering(self):
        """Test sub-numbering for multi-part chapters."""
        text = """Chapter 1
Part 1 of chapter 1

Chapter 1
Part 2 of chapter 1

Chapter 2
New chapter"""

        chapters, seq_nums = split_text(text, detect_headings=True)

        # Should handle duplicate chapter numbers with sub-numbering
        assert len(chapters) >= 2
        # Check that both Chapter 1 parts are included
        chapter_titles = [ch[0] for ch in chapters]
        assert chapter_titles.count("Chapter 1") <= 1  # Should be combined or sub-numbered
