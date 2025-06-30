#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test suite for make_epub module.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, mock_open
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from enchant_book_manager.make_epub import (
    create_epub_from_chapters,
    create_epub_from_txt_file,
    create_epub_from_directory,
)
from enchant_book_manager.epub_validation import ValidationError


class TestCreateEpubFromChapters:
    """Test the create_epub_from_chapters function."""

    @patch("enchant_book_manager.make_epub.write_new_epub")
    @patch("enchant_book_manager.make_epub.paragraphize")
    def test_create_epub_from_chapters_success(self, mock_paragraphize, mock_write_epub):
        """Test successful EPUB creation from chapters."""
        # Setup test data
        chapters = [
            ("Chapter 1", "Content of chapter 1"),
            ("Chapter 2", "Content of chapter 2"),
        ]
        output_path = MagicMock(spec=Path)
        output_path.parent.mkdir = Mock()

        title = "Test Book"
        author = "Test Author"

        # Mock paragraphize to return HTML
        mock_paragraphize.side_effect = lambda text: f"<p>{text}</p>"

        # Execute
        create_epub_from_chapters(chapters, output_path, title, author)

        # Verify parent directory creation attempted
        # Note: We can't easily mock Path.mkdir() so we'll verify through write_new_epub call

        # Verify paragraphize was called for each chapter
        assert mock_paragraphize.call_count == 2
        mock_paragraphize.assert_any_call("Content of chapter 1")
        mock_paragraphize.assert_any_call("Content of chapter 2")

        # Verify write_new_epub was called with processed chapters
        expected_chapters = [
            ("Chapter 1", "<p>Content of chapter 1</p>"),
            ("Chapter 2", "<p>Content of chapter 2</p>"),
        ]
        mock_write_epub.assert_called_once_with(expected_chapters, output_path, title, author, None)

    @patch("enchant_book_manager.make_epub.write_new_epub")
    @patch("enchant_book_manager.make_epub.paragraphize")
    def test_create_epub_from_chapters_with_cover(self, mock_paragraphize, mock_write_epub):
        """Test EPUB creation with cover image."""
        # Setup test data
        chapters = [("Chapter 1", "Content")]
        output_path = MagicMock(spec=Path)
        output_path.parent.mkdir = Mock()
        cover_path = MagicMock(spec=Path)
        cover_path.exists.return_value = True
        cover_path.suffix = ".jpg"

        # Mock paragraphize
        mock_paragraphize.return_value = "<p>Content</p>"

        # Execute
        create_epub_from_chapters(chapters, output_path, "Title", "Author", cover_path)

        # Verify write_new_epub was called with cover
        mock_write_epub.assert_called_once()
        assert mock_write_epub.call_args[0][4] == cover_path

    def test_create_epub_from_chapters_invalid_cover_format(self):
        """Test validation error for invalid cover format."""
        chapters = [("Chapter 1", "Content")]
        output_path = MagicMock(spec=Path)
        output_path.parent.mkdir = Mock()
        cover_path = MagicMock(spec=Path)
        cover_path.exists.return_value = True
        cover_path.suffix = ".gif"  # Invalid format

        # Should raise ValidationError
        with pytest.raises(ValidationError, match="Cover must be .jpg/.jpeg/.png"):
            create_epub_from_chapters(chapters, output_path, "Title", "Author", cover_path)

    @patch("enchant_book_manager.make_epub.write_new_epub")
    @patch("enchant_book_manager.make_epub.paragraphize")
    def test_create_epub_from_chapters_empty_list(self, mock_paragraphize, mock_write_epub):
        """Test EPUB creation with empty chapter list."""
        output_path = MagicMock(spec=Path)
        output_path.parent.mkdir = Mock()

        # Execute with empty chapters
        create_epub_from_chapters([], output_path, "Title", "Author")

        # Verify write_new_epub was called with empty list
        mock_write_epub.assert_called_once_with([], output_path, "Title", "Author", None)

        # Paragraphize should not be called
        mock_paragraphize.assert_not_called()


class TestCreateEpubFromTxtFile:
    """Test the create_epub_from_txt_file function."""

    @patch("enchant_book_manager.make_epub.write_new_epub")
    @patch("enchant_book_manager.make_epub.split_text")
    @patch("enchant_book_manager.make_epub.paragraphize")
    def test_create_epub_from_txt_file_success(self, mock_paragraphize, mock_split_text, mock_write_epub):
        """Test successful EPUB creation from text file."""
        # Setup
        txt_path = MagicMock(spec=Path)
        txt_path.exists.return_value = True
        txt_path.read_text.return_value = "Chapter 1\nContent 1\n\nChapter 2\nContent 2"

        output_path = MagicMock(spec=Path)
        output_path.parent.mkdir = Mock()

        # Mock split_text to return chapters
        mock_split_text.return_value = (
            [("Chapter 1", "Content 1"), ("Chapter 2", "Content 2")],
            [1, 2],  # Chapter sequence
        )

        # Mock paragraphize
        mock_paragraphize.side_effect = lambda text: f"<p>{text}</p>"

        # Execute
        success, issues = create_epub_from_txt_file(txt_path, output_path, "Test Book", "Test Author")

        # Verify
        assert success is True
        assert issues == []

        # Verify file was read
        txt_path.read_text.assert_called_once_with(encoding="utf-8")

        # Verify split_text was called
        mock_split_text.assert_called_once_with("Chapter 1\nContent 1\n\nChapter 2\nContent 2", detect_headings=True)

        # Verify write_new_epub was called
        mock_write_epub.assert_called_once()

    def test_create_epub_from_txt_file_not_found(self):
        """Test error when input file doesn't exist."""
        txt_path = MagicMock(spec=Path)
        txt_path.exists.return_value = False

        with pytest.raises(ValidationError, match="Input file not found"):
            create_epub_from_txt_file(txt_path, MagicMock(spec=Path), "Title", "Author")

    @patch("enchant_book_manager.make_epub.write_new_epub")
    @patch("enchant_book_manager.make_epub.split_text")
    @patch("enchant_book_manager.make_epub.paragraphize")
    @patch("enchant_book_manager.make_epub.detect_issues")
    @patch("enchant_book_manager.make_epub.log_issue")
    def test_create_epub_from_txt_file_with_validation_issues(
        self,
        mock_log_issue,
        mock_detect_issues,
        mock_paragraphize,
        mock_split_text,
        mock_write_epub,
    ):
        """Test handling of validation issues in strict mode."""
        # Setup
        txt_path = MagicMock(spec=Path)
        txt_path.exists.return_value = True
        txt_path.read_text.return_value = "Chapter 1\nContent"

        # Mock split_text
        mock_split_text.return_value = (
            [("Chapter 1", "Content")],
            [1, 3],
        )  # Missing chapter 2

        # Mock detect_issues to return issues
        mock_detect_issues.return_value = ["Chapter 2 is missing"]

        # Execute in strict mode
        success, issues = create_epub_from_txt_file(
            txt_path,
            MagicMock(spec=Path),
            "Title",
            "Author",
            validate=True,
            strict_mode=True,
        )

        # Verify
        assert success is False
        assert issues == ["Chapter 2 is missing"]

        # Verify issue was logged
        mock_log_issue.assert_called_once()

        # Write should not be called in strict mode with issues
        mock_write_epub.assert_not_called()

    @patch("enchant_book_manager.make_epub.write_new_epub")
    @patch("enchant_book_manager.make_epub.split_text")
    @patch("enchant_book_manager.make_epub.paragraphize")
    def test_create_epub_from_txt_file_read_error(self, mock_paragraphize, mock_split_text, mock_write_epub):
        """Test error handling when reading file fails."""
        # Setup
        txt_path = MagicMock(spec=Path)
        txt_path.exists.return_value = True
        txt_path.read_text.side_effect = UnicodeDecodeError("utf-8", b"", 0, 1, "invalid")

        # Execute
        with pytest.raises(ValidationError, match="Error reading input file"):
            create_epub_from_txt_file(txt_path, MagicMock(spec=Path), "Title", "Author")

    @patch("enchant_book_manager.make_epub.write_new_epub")
    @patch("enchant_book_manager.make_epub.split_text")
    @patch("enchant_book_manager.make_epub.paragraphize")
    def test_create_epub_from_txt_file_with_all_options(self, mock_paragraphize, mock_split_text, mock_write_epub):
        """Test EPUB creation with all optional parameters."""
        # Setup
        txt_path = MagicMock(spec=Path)
        txt_path.exists.return_value = True
        txt_path.read_text.return_value = "Content"

        output_path = MagicMock(spec=Path)
        output_path.parent.mkdir = Mock()
        cover_path = MagicMock(spec=Path)
        cover_path.exists.return_value = True
        cover_path.suffix = ".png"

        # Mock split_text
        mock_split_text.return_value = ([("Chapter 1", "Content")], [1])
        mock_paragraphize.return_value = "<p>Content</p>"

        # Execute with all options
        metadata = {
            "publisher": "Test Publisher",
            "description": "Test Description",
            "series": "Test Series",
            "series_index": "1",
        }

        success, issues = create_epub_from_txt_file(
            txt_path,
            output_path,
            "Title",
            "Author",
            cover_path=cover_path,
            generate_toc=False,
            validate=False,
            language="zh",
            custom_css="body { font-size: 16px; }",
            metadata=metadata,
        )

        # Verify
        assert success is True

        # Verify write_new_epub was called with all parameters
        mock_write_epub.assert_called_once()
        call_args = mock_write_epub.call_args
        assert call_args[1]["language"] == "zh"
        assert call_args[1]["custom_css"] == "body { font-size: 16px; }"
        assert call_args[1]["metadata"] == metadata

    @patch("enchant_book_manager.make_epub.write_new_epub")
    @patch("enchant_book_manager.make_epub.split_text")
    @patch("enchant_book_manager.make_epub.paragraphize")
    def test_create_epub_from_txt_file_write_error(self, mock_paragraphize, mock_split_text, mock_write_epub):
        """Test error handling when EPUB creation fails."""
        # Setup
        txt_path = MagicMock(spec=Path)
        txt_path.exists.return_value = True
        txt_path.read_text.return_value = "Content"

        # Mock split_text
        mock_split_text.return_value = ([("Chapter 1", "Content")], [1])
        mock_paragraphize.return_value = "<p>Content</p>"

        # Mock write_new_epub to raise exception
        mock_write_epub.side_effect = OSError("Disk full")

        # Execute
        success, issues = create_epub_from_txt_file(txt_path, MagicMock(spec=Path), "Title", "Author")

        # Verify
        assert success is False
        assert len(issues) == 1
        assert "Error creating EPUB: Disk full" in issues[0]


class TestCreateEpubFromDirectory:
    """Test the create_epub_from_directory function."""

    @patch("enchant_book_manager.make_epub.write_new_epub")
    @patch("enchant_book_manager.make_epub.collect_chunks")
    @patch("enchant_book_manager.make_epub.split_text")
    @patch("enchant_book_manager.make_epub.paragraphize")
    @patch("enchant_book_manager.make_epub.detect_issues")
    @patch("enchant_book_manager.make_epub.FILENAME_RE")
    def test_create_epub_from_directory_success(
        self,
        mock_filename_re,
        mock_detect_issues,
        mock_paragraphize,
        mock_split_text,
        mock_collect_chunks,
        mock_write_epub,
    ):
        """Test successful EPUB creation from directory."""
        # Setup
        input_dir = MagicMock(spec=Path)
        input_dir.exists.return_value = True
        input_dir.is_dir.return_value = True

        # Mock chunk files
        chunk1 = MagicMock(spec=Path)
        chunk1.name = "Book Title by Author Name - Chunk_000001.txt"
        chunk1.read_text.return_value = "Chapter 1\nContent 1"

        chunk2 = MagicMock(spec=Path)
        chunk2.name = "Book Title by Author Name - Chunk_000002.txt"
        chunk2.read_text.return_value = "Chapter 2\nContent 2"

        # Mock collect_chunks
        mock_collect_chunks.return_value = {1: chunk1, 2: chunk2}

        # Mock split_text
        mock_split_text.return_value = (
            [("Chapter 1", "Content 1"), ("Chapter 2", "Content 2")],
            [1, 2],
        )

        # Mock paragraphize
        mock_paragraphize.side_effect = lambda text: f"<p>{text}</p>"

        # Mock detect_issues - no issues
        mock_detect_issues.return_value = []

        # Mock FILENAME_RE to extract title and author
        mock_match = Mock()
        mock_match.group.side_effect = lambda key: "Book Title" if key == "title" else "Author Name"
        mock_filename_re.match.return_value = mock_match

        # Execute
        issues = create_epub_from_directory(input_dir, MagicMock(spec=Path))

        # Verify
        assert issues == []

        # Verify chunks were collected
        mock_collect_chunks.assert_called_once_with(input_dir)

        # Verify write_new_epub was called
        mock_write_epub.assert_called_once()
        # Should auto-detect title and author from filename
        call_args = mock_write_epub.call_args[0]
        assert call_args[2] == "Book Title"
        assert call_args[3] == "Author Name"

    @patch("enchant_book_manager.make_epub.collect_chunks")
    def test_create_epub_from_directory_not_found(self, mock_collect_chunks):
        """Test error when directory doesn't exist."""
        input_dir = MagicMock(spec=Path)
        input_dir.exists.return_value = False

        with pytest.raises(ValidationError, match="not found or not a directory"):
            create_epub_from_directory(input_dir, MagicMock(spec=Path))

    @patch("enchant_book_manager.make_epub.collect_chunks")
    def test_create_epub_from_directory_no_chunks(self, mock_collect_chunks):
        """Test error when no chunks found."""
        input_dir = MagicMock(spec=Path)
        input_dir.exists.return_value = True
        input_dir.is_dir.return_value = True

        # No chunks found
        mock_collect_chunks.return_value = {}

        with pytest.raises(ValidationError, match="No valid .txt chunks found"):
            create_epub_from_directory(input_dir, MagicMock(spec=Path))

    @patch("enchant_book_manager.make_epub.collect_chunks")
    @patch("enchant_book_manager.make_epub.split_text")
    @patch("enchant_book_manager.make_epub.paragraphize")
    @patch("enchant_book_manager.make_epub.detect_issues")
    def test_create_epub_from_directory_validate_only(
        self,
        mock_detect_issues,
        mock_paragraphize,
        mock_split_text,
        mock_collect_chunks,
    ):
        """Test validate-only mode."""
        # Setup
        input_dir = MagicMock(spec=Path)
        input_dir.exists.return_value = True
        input_dir.is_dir.return_value = True

        # Mock chunk
        chunk = MagicMock(spec=Path)
        chunk.read_text.return_value = "Chapter 1\nContent"
        mock_collect_chunks.return_value = {1: chunk}

        # Mock split_text
        mock_split_text.return_value = ([("Chapter 1", "Content")], [1, 3])

        # Mock detect_issues
        mock_detect_issues.return_value = ["Chapter 2 is missing"]

        # Execute in validate-only mode
        issues = create_epub_from_directory(input_dir, MagicMock(spec=Path), validate_only=True)

        # Verify
        assert issues == ["Chapter 2 is missing"]

        # Write should not be called in validate-only mode
        with patch("enchant_book_manager.make_epub.write_new_epub") as mock_write:
            mock_write.assert_not_called()

    @patch("enchant_book_manager.make_epub.collect_chunks")
    @patch("enchant_book_manager.make_epub.split_text")
    @patch("enchant_book_manager.make_epub.paragraphize")
    @patch("enchant_book_manager.make_epub.detect_issues")
    def test_create_epub_from_directory_strict_mode_with_issues(
        self,
        mock_detect_issues,
        mock_paragraphize,
        mock_split_text,
        mock_collect_chunks,
    ):
        """Test strict mode with validation issues."""
        # Setup
        input_dir = MagicMock(spec=Path)
        input_dir.exists.return_value = True
        input_dir.is_dir.return_value = True

        # Mock chunk
        chunk = MagicMock(spec=Path)
        chunk.read_text.return_value = "Content"
        mock_collect_chunks.return_value = {1: chunk}

        # Mock split_text
        mock_split_text.return_value = ([("Chapter 1", "Content")], [1, 3])

        # Mock detect_issues
        mock_detect_issues.return_value = ["Chapter 2 is missing"]

        # Execute in strict mode
        with pytest.raises(ValidationError, match="Found 1 validation issues"):
            create_epub_from_directory(input_dir, MagicMock(spec=Path), strict=True)

    @patch("enchant_book_manager.make_epub.write_new_epub")
    @patch("enchant_book_manager.make_epub.collect_chunks")
    @patch("enchant_book_manager.make_epub.split_text")
    @patch("enchant_book_manager.make_epub.paragraphize")
    @patch("enchant_book_manager.make_epub.detect_issues")
    def test_create_epub_from_directory_manual_title_author(
        self,
        mock_detect_issues,
        mock_paragraphize,
        mock_split_text,
        mock_collect_chunks,
        mock_write_epub,
    ):
        """Test providing manual title and author."""
        # Setup
        input_dir = MagicMock(spec=Path)
        input_dir.exists.return_value = True
        input_dir.is_dir.return_value = True

        # Mock chunk with unparseable filename
        chunk = MagicMock(spec=Path)
        chunk.name = "chunk001.txt"  # Won't match FILENAME_RE
        chunk.read_text.return_value = "Content"
        mock_collect_chunks.return_value = {1: chunk}

        # Mock split_text
        mock_split_text.return_value = ([("Chapter 1", "Content")], [])
        mock_paragraphize.return_value = "<p>Content</p>"
        mock_detect_issues.return_value = []

        # Execute with manual title/author
        issues = create_epub_from_directory(
            input_dir,
            MagicMock(spec=Path),
            title="Manual Title",
            author="Manual Author",
        )

        # Verify manual title/author were used
        mock_write_epub.assert_called_once()
        call_args = mock_write_epub.call_args[0]
        assert call_args[2] == "Manual Title"
        assert call_args[3] == "Manual Author"
