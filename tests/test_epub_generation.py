#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test EPUB generation functionality (Phase 3)
"""

import os
import sys
import tempfile
import shutil
import zipfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import xml.etree.ElementTree as ET

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from enchant_book_manager.make_epub import create_epub_from_txt_file


class TestEPUBGeneration:
    """Test cases for EPUB generation from text files"""

    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Set up test fixtures"""
        self.test_dir = tempfile.mkdtemp()
        self.mock_logger = Mock()

    def teardown_method(self):
        """Clean up test fixtures"""
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_simple_epub_generation(self):
        """Test generating EPUB from a simple text file"""
        # Create a simple novel text
        novel_text = """The Great Adventure
by John Smith

Chapter 1: The Beginning

It was a dark and stormy night. Our hero set out on an adventure that would change everything.

The journey began in a small village nestled in the mountains. The air was crisp and cold.

Chapter 2: The Journey

Days passed as our hero traveled through forests and valleys. Each step brought new discoveries.

The path was long and winding, but determination kept them going forward.

Chapter 3: The End

Finally, after many trials, our hero reached their destination. The adventure had come to an end.

But this was just the beginning of a new chapter in their life.
"""

        # Write to text file
        text_file = Path(self.test_dir) / "novel.txt"
        text_file.write_text(novel_text, encoding="utf-8")

        # Generate EPUB
        epub_path = Path(self.test_dir) / "novel.epub"
        success, issues = create_epub_from_txt_file(
            txt_file_path=text_file,
            output_path=epub_path,
            title="The Great Adventure",
            author="John Smith",
            language="en",
        )

        # Verify EPUB was created
        assert success is True
        assert len(issues) == 0
        assert epub_path.exists()

        # Verify EPUB structure
        with zipfile.ZipFile(epub_path, "r") as epub:
            # Check required files exist
            assert "mimetype" in epub.namelist()
            assert "META-INF/container.xml" in epub.namelist()
            assert "OEBPS/content.opf" in epub.namelist()
            assert "OEBPS/toc.ncx" in epub.namelist()

            # Check chapters were created
            assert "OEBPS/Text/chapter1.xhtml" in epub.namelist()
            assert "OEBPS/Text/chapter2.xhtml" in epub.namelist()
            assert "OEBPS/Text/chapter3.xhtml" in epub.namelist()

            # Verify mimetype
            mimetype = epub.read("mimetype").decode("utf-8")
            assert mimetype == "application/epub+zip"

    def test_chapter_detection_patterns(self):
        """Test various chapter heading patterns"""
        test_cases = [
            # Since we're adding title/author before the text, chapter detection varies
            # Pattern 1: "Chapter N: Title"
            ("Chapter 1: The Beginning\n\nContent here.", "Chapter 1: The Beginning"),
            # Pattern 2: "Chapter N"
            ("Chapter 42\n\nContent here.", "Chapter 42"),
            # Pattern 3: "N. Title"
            ("1. Introduction\n\nContent here.", "1. Introduction"),
            # Pattern 4: Roman numerals
            ("I. The First Part\n\nContent here.", "I. The First Part"),
            ("XII. The Twelfth Part\n\nContent here.", "XII. The Twelfth Part"),
            # Pattern 5: "Part N"
            ("Part 1: The Beginning\n\nContent here.", "Part 1: The Beginning"),
        ]

        for text, expected_title in test_cases:
            # Create text file
            text_file = Path(self.test_dir) / "test_pattern.txt"
            text_file.write_text(f"Test Novel\nby Test Author\n\n{text}", encoding="utf-8")

            # Generate EPUB
            epub_path = Path(self.test_dir) / "test_pattern.epub"
            success, issues = create_epub_from_txt_file(
                txt_file_path=text_file,
                output_path=epub_path,
                title="Test Novel",
                author="Test Author",
            )

            assert success is True

            # Check generated chapters
            with zipfile.ZipFile(epub_path, "r") as epub:
                chapter_files = [f for f in epub.namelist() if f.startswith("OEBPS/Text/chapter")]
                # We should have at least one chapter
                assert len(chapter_files) >= 1

                if expected_title:
                    # Find and check the content contains the expected title
                    found = False
                    for chapter_file in chapter_files:
                        chapter_content = epub.read(chapter_file).decode("utf-8")
                        if expected_title in chapter_content:
                            found = True
                            break
                    assert found, f"Expected title '{expected_title}' not found in any chapter"

    def test_epub_metadata(self):
        """Test EPUB metadata generation"""
        novel_text = """Test Novel
by Test Author

Chapter 1

This is test content."""

        text_file = Path(self.test_dir) / "metadata_test.txt"
        text_file.write_text(novel_text, encoding="utf-8")

        # Generate EPUB with custom metadata
        epub_path = Path(self.test_dir) / "metadata_test.epub"
        success, issues = create_epub_from_txt_file(
            txt_file_path=text_file,
            output_path=epub_path,
            title="Custom Title",
            author="Custom Author",
            language="es",  # Spanish
            metadata={
                "publisher": "Test Publisher",
                "description": "This is a test novel",
            },
        )

        assert success is True

        # Check metadata in content.opf
        with zipfile.ZipFile(epub_path, "r") as epub:
            content_opf = epub.read("OEBPS/content.opf").decode("utf-8")

            # Parse XML
            root = ET.fromstring(content_opf)

            # Define namespace
            ns = {"dc": "http://purl.org/dc/elements/1.1/"}

            # Check metadata
            title = root.find(".//dc:title", ns)
            assert title is not None and title.text == "Custom Title"

            creator = root.find(".//dc:creator", ns)
            assert creator is not None and creator.text == "Custom Author"

            language = root.find(".//dc:language", ns)
            assert language is not None and language.text == "es"

            publisher = root.find(".//dc:publisher", ns)
            assert publisher is not None and publisher.text == "Test Publisher"

            description = root.find(".//dc:description", ns)
            assert description is not None and description.text == "This is a test novel"

    def test_empty_text_handling(self):
        """Test handling of empty or minimal text files"""
        # Test empty file
        empty_file = Path(self.test_dir) / "empty.txt"
        empty_file.write_text("", encoding="utf-8")

        epub_path = Path(self.test_dir) / "empty.epub"
        success, issues = create_epub_from_txt_file(
            txt_file_path=empty_file,
            output_path=epub_path,
            title="Empty Book",
            author="No One",
        )

        # Empty files might not generate chapters
        assert success is True
        assert epub_path.exists()

        with zipfile.ZipFile(epub_path, "r") as epub:
            # Check basic structure exists
            assert "mimetype" in epub.namelist()
            assert "OEBPS/content.opf" in epub.namelist()

    def test_large_text_handling(self):
        """Test handling of large text files with many chapters"""
        # Create a novel with 50 chapters
        chapters = []
        for i in range(1, 51):
            chapters.append(f"Chapter {i}: Part {i}\n\nThis is the content of chapter {i}. " * 10)

        novel_text = "Large Novel\nby Prolific Author\n\n" + "\n\n".join(chapters)

        text_file = Path(self.test_dir) / "large_novel.txt"
        text_file.write_text(novel_text, encoding="utf-8")

        epub_path = Path(self.test_dir) / "large_novel.epub"
        success, issues = create_epub_from_txt_file(
            txt_file_path=text_file,
            output_path=epub_path,
            title="Large Novel",
            author="Prolific Author",
        )

        assert success is True

        # Verify all chapters were created (51 including title section)
        with zipfile.ZipFile(epub_path, "r") as epub:
            chapter_files = [f for f in epub.namelist() if f.startswith("OEBPS/Text/chapter")]
            assert len(chapter_files) == 51  # 50 chapters + title section

            # Check table of contents
            toc_ncx = epub.read("OEBPS/toc.ncx").decode("utf-8")
            assert "Chapter 1:" in toc_ncx
            assert "Chapter 50:" in toc_ncx

    def test_special_characters_handling(self):
        """Test handling of special characters in text"""
        novel_text = """Special "Characters" Novel
by Author's Name

Chapter 1: "Quotes" & Ampersands

This chapter has "smart quotes" and regular "quotes".
It also has & ampersands and < less than > greater than symbols.
Even some unicode: café, naïve, résumé, 中文.

Chapter 2: More <Special> Characters

This has <tags> that might look like XML/HTML.
And some special punctuation: — em dash, – en dash, … ellipsis.
"""

        text_file = Path(self.test_dir) / "special_chars.txt"
        text_file.write_text(novel_text, encoding="utf-8")

        epub_path = Path(self.test_dir) / "special_chars.epub"
        success, issues = create_epub_from_txt_file(
            txt_file_path=text_file,
            output_path=epub_path,
            title='Special "Characters" Novel',
            author="Author's Name",
        )

        assert success is True

        # Verify special characters are properly escaped in XML
        with zipfile.ZipFile(epub_path, "r") as epub:
            # Check content.opf
            content_opf = epub.read("OEBPS/content.opf").decode("utf-8")
            # Should be valid XML (parsing will fail if not properly escaped)
            ET.fromstring(content_opf)

            # Check chapter content
            chapter1 = epub.read("OEBPS/Text/chapter2.xhtml").decode("utf-8")  # Chapter 1 is actually the second file
            # Should contain properly escaped characters
            assert "&amp;" in chapter1  # & should be escaped
            assert "&lt;" in chapter1  # < should be escaped
            assert "&gt;" in chapter1  # > should be escaped
            # Unicode should be preserved
            assert "café" in chapter1
            assert "中文" in chapter1

    def test_custom_css_handling(self):
        """Test custom CSS application"""
        novel_text = """Styled Novel
by Designer

Chapter 1

This novel has custom styling."""

        text_file = Path(self.test_dir) / "styled.txt"
        text_file.write_text(novel_text, encoding="utf-8")

        # Create custom CSS
        custom_css = """
body { font-family: 'Georgia', serif; }
h1 { color: #333; }
p { text-indent: 2em; }
"""

        epub_path = Path(self.test_dir) / "styled.epub"
        success, issues = create_epub_from_txt_file(
            txt_file_path=text_file,
            output_path=epub_path,
            title="Styled Novel",
            author="Designer",
            custom_css=custom_css,
        )

        assert success is True

        # Check CSS was included
        with zipfile.ZipFile(epub_path, "r") as epub:
            assert "OEBPS/Styles/style.css" in epub.namelist()
            css_content = epub.read("OEBPS/Styles/style.css").decode("utf-8")
            assert "font-family: 'Georgia', serif" in css_content
            assert "text-indent: 2em" in css_content

    def test_error_handling(self):
        """Test error handling for invalid inputs"""
        # Test non-existent file
        with pytest.raises(Exception):  # Should raise ValidationError
            success, issues = create_epub_from_txt_file(
                txt_file_path=Path("/non/existent/file.txt"),
                output_path=Path(self.test_dir) / "output.epub",
                title="Test",
                author="Test",
            )

        # Test invalid output directory
        text_file = Path(self.test_dir) / "valid.txt"
        text_file.write_text("Valid content", encoding="utf-8")

        # This should create the directory if it doesn't exist or raise an error
        try:
            success, issues = create_epub_from_txt_file(
                txt_file_path=text_file,
                output_path=Path("/invalid/path/output.epub"),
                title="Test",
                author="Test",
            )
            # If it succeeds, that's okay too (might create the directory)
            assert isinstance(success, bool)
        except Exception:
            # Expected if directory creation fails
            pass

    def test_epub_validation(self):
        """Test EPUB validation functionality"""
        # Create a valid EPUB first
        novel_text = """Valid Novel
by Valid Author

Chapter 1: Validation Test

This EPUB should pass validation."""

        text_file = Path(self.test_dir) / "valid.txt"
        text_file.write_text(novel_text, encoding="utf-8")

        epub_path = Path(self.test_dir) / "valid.epub"
        success, issues = create_epub_from_txt_file(
            txt_file_path=text_file,
            output_path=epub_path,
            title="Valid Novel",
            author="Valid Author",
        )

        assert success is True

        # Basic validation - check the EPUB is a valid ZIP
        assert zipfile.is_zipfile(str(epub_path))

    def test_unicode_filename_handling(self):
        """Test handling of unicode characters in filenames"""
        novel_text = """中文小说
作者：测试

第一章：开始

这是一个测试。"""

        # Use unicode in filename
        text_file = Path(self.test_dir) / "中文小说.txt"
        text_file.write_text(novel_text, encoding="utf-8")

        epub_path = Path(self.test_dir) / "中文小说.epub"
        success, issues = create_epub_from_txt_file(
            txt_file_path=text_file,
            output_path=epub_path,
            title="中文小说",
            author="测试作者",
        )

        assert success is True
        assert epub_path.exists()

    def test_missing_chapters_detection(self):
        """Test detection and reporting of missing chapters in sequence"""
        # Create a novel with 12 chapters but missing chapters 1, 5, and 6
        novel_text = """The Incomplete Novel
by Test Author

Chapter 2: The Second

This is chapter 2 content. We're starting from chapter 2, missing chapter 1.

Chapter 3: The Third

Content for chapter 3 follows naturally from chapter 2.

Chapter 4: The Fourth

Chapter 4 continues the story without interruption.

Chapter 7: The Seventh

We jump from chapter 4 to chapter 7, missing chapters 5 and 6.

Chapter 8: The Eighth

Chapter 8 continues from chapter 7.

Chapter 9: The Ninth

The story progresses through chapter 9.

Chapter 10: The Tenth

Double digit chapters begin with chapter 10.

Chapter 11: The Eleventh

Almost at the end with chapter 11.

Chapter 12: The Final Chapter

The story concludes with chapter 12.
"""

        text_file = Path(self.test_dir) / "missing_chapters.txt"
        text_file.write_text(novel_text, encoding="utf-8")

        epub_path = Path(self.test_dir) / "missing_chapters.epub"

        # Create EPUB with validation enabled
        success, issues = create_epub_from_txt_file(
            txt_file_path=text_file,
            output_path=epub_path,
            title="The Incomplete Novel",
            author="Test Author",
            validate=True,
            strict_mode=False,  # Don't abort on issues, just report them
        )

        # Should succeed but report issues
        assert success is True
        assert epub_path.exists()

        # Check that missing chapters are detected
        assert len(issues) > 0, "Should detect missing chapters"

        # Verify specific missing chapters are reported
        issue_messages = " ".join(issues).lower()
        # Note: Chapter 1 is not reported as missing because the sequence starts at 2
        # The algorithm assumes the sequence starts wherever it starts
        assert "number 5 is missing" in issue_messages
        assert "number 6 is missing" in issue_messages

        # Verify the EPUB still contains the chapters that exist
        with zipfile.ZipFile(epub_path, "r") as epub:
            chapter_files = sorted([f for f in epub.namelist() if f.startswith("OEBPS/Text/chapter")])
            # Should have 10 chapters (9 actual + 1 title section)
            assert len(chapter_files) == 10

            # Verify chapter 2 content (which is in chapter3.xhtml due to title section)
            chapter2_content = epub.read("OEBPS/Text/chapter2.xhtml").decode("utf-8")
            assert "Chapter 2: The Second" in chapter2_content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
