#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test suite for enhanced English chapter pattern detection.
"""

import pytest
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from make_epub import HEADING_RE, parse_num, split_text


class TestEnglishChapterPatterns:
    """Test various English chapter heading patterns"""
    
    @pytest.mark.parametrize("text,expected", [
        ("Chapter 1", 1),
        ("Chapter 42", 42),
        ("CHAPTER 99", 99),
        ("chapter 1000", 1000),
        ("Chapter VII", 7),
        ("Chapter XIV", 14),
        ("Chapter Seven", 7),
        ("Chapter Twenty-Three", 23),
        ("Chapter One Hundred", 100),
    ])
    def test_standard_chapter_patterns(self, text, expected):
        """Test standard 'Chapter N' patterns"""
        match = HEADING_RE.match(text)
        assert match is not None, f"Failed to match: {text}"
        num_str = (match.group("num_d") or match.group("num_r") or match.group("num_w"))
        num = parse_num(num_str)
        assert num == expected
    
    @pytest.mark.parametrize("text,expected", [
        ("Ch. 1", 1),
        ("Ch 5", 5),
        ("Chap. 10", 10),
        ("Chap 15", 15),
        ("ch.42", 42),
    ])
    def test_abbreviated_patterns(self, text, expected):
        """Test abbreviated chapter patterns"""
        match = HEADING_RE.match(text)
        assert match is not None, f"Failed to match: {text}"
        num_str = match.group("num_d")
        num = parse_num(num_str)
        assert num == expected
    
    @pytest.mark.parametrize("text,expected", [
        ("Part 1", 1),
        ("Part IV", 4),
        ("Part Five", 5),
        ("Section 3", 3),
        ("Section XII", 12),
        ("Book 2", 2),
        ("Book Three", 3),
    ])
    def test_part_section_book_patterns(self, text, expected):
        """Test Part, Section, Book patterns"""
        match = HEADING_RE.match(text)
        assert match is not None, f"Failed to match: {text}"
        num_str = (match.group("part_d") or match.group("part_r") or match.group("part_w"))
        num = parse_num(num_str)
        assert num == expected
    
    @pytest.mark.parametrize("text,expected", [
        ("§ 42", 42),
        ("§1", 1),
        ("§ 99", 99),
        ("1.", 1),
        ("42)", 42),
        ("7:", 7),
        ("99-", 99),
    ])
    def test_special_patterns(self, text, expected):
        """Test special patterns like § and numbered lists"""
        match = HEADING_RE.match(text)
        assert match is not None, f"Failed to match: {text}"
        num_str = (match.group("sec_d") or match.group("hash_d"))
        num = parse_num(num_str)
        assert num == expected
    
    @pytest.mark.parametrize("text,expected_num,expected_rest", [
        ("Chapter 1: The Beginning", 1, ": The Beginning"),
        ("Chapter 42 - The Answer", 42, " - The Answer"),
        ("Part IV: A New Hope", 4, ": A New Hope"),
        ("Section 3 — Introduction", 3, " — Introduction"),
    ])
    def test_chapter_with_titles(self, text, expected_num, expected_rest):
        """Test chapters with subtitles"""
        match = HEADING_RE.match(text)
        assert match is not None, f"Failed to match: {text}"
        rest = match.group("rest")
        assert rest == expected_rest
    
    def test_complete_document(self):
        """Test complete document with various patterns"""
        content = """
Some front matter text before chapters.

Chapter 1
This is the first chapter.

Ch. 2: The Second Chapter
More content here.

Part I
A major section.

Section 3
Another section.

§ 4
Legal style section.

5. Listed Chapter
With numbered format.

Chapter VI - Roman Numerals
Classic style.

Chapter Seven: Word Numbers
Written out numbers.
"""
        
        chapters, seq = split_text(content, detect_headings=True)
        
        # Check sequence
        expected_seq = [1, 2, 1, 3, 4, 5, 6, 7]
        assert seq == expected_seq
        
        # Check chapter count (including front matter)
        assert len(chapters) == 9  # Front matter + 8 chapters
        
        # Verify first is front matter
        assert chapters[0][0] == "Front Matter"


class TestChapterSequenceValidation:
    """Test chapter sequence validation"""
    
    @pytest.mark.parametrize("seq", [
        [1, 2, 3, 4, 5],
        [1],
        [10, 11, 12],
    ])
    def test_valid_sequences(self, seq):
        """Test that valid sequences produce no issues"""
        from make_epub import detect_issues
        
        issues = detect_issues(seq)
        assert len(issues) == 0
    
    def test_missing_chapters(self):
        """Test detection of missing chapters"""
        from make_epub import detect_issues
        
        seq = [1, 3, 5]
        issues = detect_issues(seq)
        
        # Should report chapters 2 and 4 missing
        assert "number 2 is missing" in str(issues)
        assert "number 4 is missing" in str(issues)
    
    def test_out_of_order_chapters(self):
        """Test detection of out-of-order chapters"""
        from make_epub import detect_issues
        
        seq = [1, 2, 5, 3, 4]
        issues = detect_issues(seq)
        
        # Should report chapter 3 out of place
        assert any("out of place" in issue for issue in issues)
    
    def test_repeated_chapters(self):
        """Test detection of repeated chapters"""
        from make_epub import detect_issues
        
        seq = [1, 2, 2, 3]
        issues = detect_issues(seq)
        
        # Should report chapter 2 repeated
        assert any("repeated" in issue for issue in issues)
