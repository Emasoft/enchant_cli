#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test suite for workflow_epub module.
"""

import pytest
import json
import logging
import argparse
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from enchant_book_manager.workflow_epub import (
    find_translated_file,
    create_epub_from_translated,
    apply_epub_overrides,
    validate_epub_only,
    process_epub_generation,
)


class TestFindTranslatedFile:
    """Test the find_translated_file function."""

    def setup_method(self):
        """Set up test fixtures."""
        self.current_path = Path("/test/novel.txt")
        self.args = argparse.Namespace()
        self.logger = logging.getLogger("test")

    def test_with_translated_argument(self):
        """Test when --translated argument is provided."""
        self.args.translated = "/path/to/translated.txt"

        result = find_translated_file(self.current_path, self.args, self.logger)

        assert result == Path("/path/to/translated.txt")

    def test_no_translated_argument_no_attribute(self):
        """Test when args has no translated attribute."""
        # Don't set args.translated

        with patch("enchant_book_manager.workflow_epub.extract_book_info_from_path") as mock_extract:
            mock_extract.return_value = {"title_english": "Test Novel", "author_english": "Test Author"}

            result = find_translated_file(self.current_path, self.args, self.logger)

        # Should fall through to checking for directory
        assert result is None

    @patch("enchant_book_manager.workflow_epub.extract_book_info_from_path")
    def test_find_in_expected_directory(self, mock_extract, tmp_path):
        """Test finding translated file in expected directory."""
        # Setup
        self.current_path = tmp_path / "Novel by Author.txt"
        self.current_path.write_text("content")

        mock_extract.return_value = {"title_english": "Novel", "author_english": "Author"}

        # Create expected directory structure
        book_dir = tmp_path / "Novel by Author"
        book_dir.mkdir()
        translated_file = book_dir / "translated_Novel by Author.txt"
        translated_file.write_text("translated content")

        result = find_translated_file(self.current_path, self.args, self.logger)

        assert result == translated_file

    @patch("enchant_book_manager.workflow_epub.extract_book_info_from_path")
    def test_directory_not_found(self, mock_extract, tmp_path):
        """Test when expected directory doesn't exist."""
        self.current_path = tmp_path / "novel.txt"
        self.current_path.write_text("content")

        mock_extract.return_value = {"title_english": "Novel", "author_english": "Author"}

        # Don't create the expected directory
        result = find_translated_file(self.current_path, self.args, self.logger)

        assert result is None

    @patch("enchant_book_manager.workflow_epub.extract_book_info_from_path")
    def test_translated_file_not_in_directory(self, mock_extract, tmp_path):
        """Test when directory exists but translated file doesn't."""
        self.current_path = tmp_path / "novel.txt"
        self.current_path.write_text("content")

        mock_extract.return_value = {"title_english": "Novel", "author_english": "Author"}

        # Create directory but not the translated file
        book_dir = tmp_path / "Novel by Author"
        book_dir.mkdir()

        result = find_translated_file(self.current_path, self.args, self.logger)

        # Returns the path even if file doesn't exist yet
        expected = book_dir / "translated_Novel by Author.txt"
        assert result == expected

    @patch("enchant_book_manager.workflow_epub.extract_book_info_from_path")
    def test_missing_book_info(self, mock_extract, tmp_path):
        """Test with missing book info."""
        self.current_path = tmp_path / "novel.txt"
        self.current_path.write_text("content")

        mock_extract.return_value = {}

        # Should use filename stem as title
        book_dir = tmp_path / "novel by Unknown"

        result = find_translated_file(self.current_path, self.args, self.logger)

        assert result is None


class TestCreateEpubFromTranslated:
    """Test the create_epub_from_translated function."""

    def setup_method(self):
        """Set up test fixtures."""
        self.translated_file = Path("/test/translated.txt")
        self.current_path = Path("/test/novel.txt")
        self.book_title = "Test Novel"
        self.book_author = "Test Author"
        self.book_info = {"title_chinese": "测试小说", "author_chinese": "测试作者"}
        self.args = argparse.Namespace()
        self.progress = {"phases": {"epub": {}}}
        self.logger = logging.getLogger("test")

    @patch("enchant_book_manager.workflow_epub.get_config")
    @patch("enchant_book_manager.workflow_epub.get_epub_config_from_book_info")
    @patch("enchant_book_manager.workflow_epub.create_epub_with_config")
    def test_successful_creation(self, mock_create, mock_get_config, mock_get_global_config):
        """Test successful EPUB creation."""
        # Setup mocks
        mock_get_global_config.return_value = {"epub": {"setting1": "value1"}}
        mock_get_config.return_value = {"language": "en", "generate_toc": True}
        mock_create.return_value = (True, [])

        result = create_epub_from_translated(self.translated_file, self.current_path, self.book_title, self.book_author, self.book_info, self.args, self.progress, self.logger)

        assert result is True
        assert self.progress["phases"]["epub"]["result"] == "/test/Test Novel.epub"

        # Verify create_epub_with_config was called
        mock_create.assert_called_once()
        call_args = mock_create.call_args
        assert call_args.kwargs["txt_file_path"] == self.translated_file
        assert call_args.kwargs["output_path"] == Path("/test/Test Novel.epub")

    @patch("enchant_book_manager.workflow_epub.get_config")
    @patch("enchant_book_manager.workflow_epub.get_epub_config_from_book_info")
    @patch("enchant_book_manager.workflow_epub.create_epub_with_config")
    def test_creation_with_warnings(self, mock_create, mock_get_config, mock_get_global_config):
        """Test EPUB creation with validation warnings."""
        # Setup mocks
        mock_get_global_config.return_value = {"epub": {}}
        mock_get_config.return_value = {}
        mock_create.return_value = (True, ["Warning 1", "Warning 2"])

        result = create_epub_from_translated(self.translated_file, self.current_path, self.book_title, self.book_author, self.book_info, self.args, self.progress, self.logger)

        assert result is True
        assert self.progress["phases"]["epub"]["result"] == "/test/Test Novel.epub"

    @patch("enchant_book_manager.workflow_epub.get_config")
    @patch("enchant_book_manager.workflow_epub.get_epub_config_from_book_info")
    @patch("enchant_book_manager.workflow_epub.create_epub_with_config")
    def test_creation_failure(self, mock_create, mock_get_config, mock_get_global_config):
        """Test EPUB creation failure."""
        # Setup mocks
        mock_get_global_config.return_value = {"epub": {}}
        mock_get_config.return_value = {}
        mock_create.return_value = (False, ["Error 1", "Error 2", "Error 3", "Error 4"])

        result = create_epub_from_translated(self.translated_file, self.current_path, self.book_title, self.book_author, self.book_info, self.args, self.progress, self.logger)

        assert result is False
        assert "EPUB creation failed" in self.progress["phases"]["epub"]["error"]
        assert "Error 1" in self.progress["phases"]["epub"]["error"]

    @patch("enchant_book_manager.workflow_epub.get_config")
    @patch("enchant_book_manager.workflow_epub.get_epub_config_from_book_info")
    @patch("enchant_book_manager.workflow_epub.validate_epub_only")
    def test_validate_only_mode(self, mock_validate, mock_get_config, mock_get_global_config):
        """Test validate-only mode."""
        # Setup
        self.args.validate_only = True
        mock_get_global_config.return_value = {"epub": {}}
        mock_get_config.return_value = {}
        mock_validate.return_value = True

        result = create_epub_from_translated(self.translated_file, self.current_path, self.book_title, self.book_author, self.book_info, self.args, self.progress, self.logger)

        assert result is True
        mock_validate.assert_called_once()

    @patch("enchant_book_manager.workflow_epub.get_config")
    @patch("enchant_book_manager.workflow_epub.get_epub_config_from_book_info")
    @patch("enchant_book_manager.workflow_epub.create_epub_with_config")
    @patch("enchant_book_manager.workflow_epub.apply_epub_overrides")
    def test_overrides_applied(self, mock_apply, mock_create, mock_get_config, mock_get_global_config):
        """Test that command-line overrides are applied."""
        # Setup mocks
        mock_get_global_config.return_value = {"epub": {}}
        mock_get_config.return_value = {}
        mock_create.return_value = (True, [])

        result = create_epub_from_translated(self.translated_file, self.current_path, self.book_title, self.book_author, self.book_info, self.args, self.progress, self.logger)

        assert result is True
        # Verify apply_epub_overrides was called
        mock_apply.assert_called_once()
        assert mock_apply.call_args.args[1] == self.args


class TestApplyEpubOverrides:
    """Test the apply_epub_overrides function."""

    def setup_method(self):
        """Set up test fixtures."""
        self.epub_config = {"language": "en", "generate_toc": True, "validate_chapters": True, "strict_mode": False}
        self.args = argparse.Namespace()
        self.logger = logging.getLogger("test")

    def test_language_override(self):
        """Test language override."""
        self.args.epub_language = "zh"

        apply_epub_overrides(self.epub_config, self.args, self.logger)

        assert self.epub_config["language"] == "zh"

    def test_no_toc_override(self):
        """Test no_toc override."""
        self.args.no_toc = True

        apply_epub_overrides(self.epub_config, self.args, self.logger)

        assert self.epub_config["generate_toc"] is False

    def test_no_validate_override(self):
        """Test no_validate override."""
        self.args.no_validate = True

        apply_epub_overrides(self.epub_config, self.args, self.logger)

        assert self.epub_config["validate_chapters"] is False

    def test_strict_mode_override(self):
        """Test strict mode override."""
        self.args.epub_strict = True

        apply_epub_overrides(self.epub_config, self.args, self.logger)

        assert self.epub_config["strict_mode"] is True

    def test_cover_image_exists(self, tmp_path):
        """Test cover image override when file exists."""
        cover_file = tmp_path / "cover.jpg"
        cover_file.write_bytes(b"fake image data")
        self.args.cover = str(cover_file)

        apply_epub_overrides(self.epub_config, self.args, self.logger)

        assert self.epub_config["cover_path"] == cover_file

    def test_cover_image_not_exists(self):
        """Test cover image override when file doesn't exist."""
        self.args.cover = "/nonexistent/cover.jpg"

        apply_epub_overrides(self.epub_config, self.args, self.logger)

        assert "cover_path" not in self.epub_config

    def test_custom_css_exists(self, tmp_path):
        """Test custom CSS override when file exists."""
        css_file = tmp_path / "custom.css"
        css_content = "body { font-family: serif; }"
        css_file.write_text(css_content, encoding="utf-8")
        self.args.custom_css = str(css_file)

        apply_epub_overrides(self.epub_config, self.args, self.logger)

        assert self.epub_config["custom_css"] == css_content

    def test_custom_css_not_exists(self):
        """Test custom CSS override when file doesn't exist."""
        self.args.custom_css = "/nonexistent/custom.css"

        apply_epub_overrides(self.epub_config, self.args, self.logger)

        assert "custom_css" not in self.epub_config

    def test_valid_metadata_json(self):
        """Test valid metadata JSON override."""
        metadata = {"publisher": "Test Publisher", "language": "en-US"}
        self.args.epub_metadata = json.dumps(metadata)

        apply_epub_overrides(self.epub_config, self.args, self.logger)

        assert self.epub_config["metadata"] == metadata

    def test_invalid_metadata_json(self):
        """Test invalid metadata JSON override."""
        self.args.epub_metadata = "invalid json{"

        apply_epub_overrides(self.epub_config, self.args, self.logger)

        assert "metadata" not in self.epub_config

    def test_no_overrides(self):
        """Test when no overrides are present."""
        # Don't set any args attributes
        original_config = self.epub_config.copy()

        apply_epub_overrides(self.epub_config, self.args, self.logger)

        assert self.epub_config == original_config

    def test_multiple_overrides(self):
        """Test multiple overrides together."""
        self.args.epub_language = "fr"
        self.args.no_toc = True
        self.args.epub_strict = True

        apply_epub_overrides(self.epub_config, self.args, self.logger)

        assert self.epub_config["language"] == "fr"
        assert self.epub_config["generate_toc"] is False
        assert self.epub_config["strict_mode"] is True


class TestValidateEpubOnly:
    """Test the validate_epub_only function."""

    def setup_method(self):
        """Set up test fixtures."""
        self.translated_file = Path("/test/translated.txt")
        self.epub_path = Path("/test/book.epub")
        self.book_title = "Test Book"
        self.book_author = "Test Author"
        self.epub_config = {"language": "en", "generate_toc": True, "strict_mode": False}
        self.progress = {"phases": {"epub": {}}}
        self.logger = logging.getLogger("test")

    @patch("enchant_book_manager.make_epub.create_epub_from_txt_file")
    def test_validation_no_issues(self, mock_create):
        """Test validation with no issues."""
        mock_create.return_value = (True, [])

        result = validate_epub_only(self.translated_file, self.epub_path, self.book_title, self.book_author, self.epub_config, self.progress, self.logger)

        assert result is True
        assert self.progress["phases"]["epub"]["status"] == "skipped"
        assert self.progress["phases"]["epub"]["result"] == "validate-only"

        # Verify create_epub_from_txt_file was called with validate=True
        mock_create.assert_called_once()
        call_kwargs = mock_create.call_args.kwargs
        assert call_kwargs["validate"] is True

    @patch("enchant_book_manager.make_epub.create_epub_from_txt_file")
    def test_validation_with_issues(self, mock_create):
        """Test validation with issues."""
        mock_create.return_value = (False, ["Issue 1", "Issue 2"])

        result = validate_epub_only(self.translated_file, self.epub_path, self.book_title, self.book_author, self.epub_config, self.progress, self.logger)

        assert result is False
        assert self.progress["phases"]["epub"]["status"] == "skipped"
        assert self.progress["phases"]["epub"]["result"] == "validate-only"

    @patch("enchant_book_manager.make_epub.create_epub_from_txt_file")
    def test_validation_with_config_options(self, mock_create):
        """Test validation passes config options correctly."""
        mock_create.return_value = (True, [])

        self.epub_config["cover_path"] = Path("/test/cover.jpg")
        self.epub_config["custom_css"] = "body { color: red; }"
        self.epub_config["metadata"] = {"publisher": "Test"}

        result = validate_epub_only(self.translated_file, self.epub_path, self.book_title, self.book_author, self.epub_config, self.progress, self.logger)

        assert result is True

        # Verify all config options were passed
        call_kwargs = mock_create.call_args.kwargs
        assert call_kwargs["cover_path"] == Path("/test/cover.jpg")
        assert call_kwargs["custom_css"] == "body { color: red; }"
        assert call_kwargs["metadata"] == {"publisher": "Test"}
        assert call_kwargs["language"] == "en"
        assert call_kwargs["generate_toc"] is True
        assert call_kwargs["strict_mode"] is False


class TestProcessEpubGeneration:
    """Test the process_epub_generation function."""

    def setup_method(self):
        """Set up test fixtures."""
        self.current_path = Path("/test/novel.txt")
        self.args = argparse.Namespace()
        self.progress = {"phases": {"epub": {}}}
        self.logger = logging.getLogger("test")

    @patch("enchant_book_manager.workflow_epub.find_translated_file")
    @patch("enchant_book_manager.workflow_epub.extract_book_info_from_path")
    @patch("enchant_book_manager.workflow_epub.create_epub_from_translated")
    def test_successful_generation(self, mock_create, mock_extract, mock_find):
        """Test successful EPUB generation."""
        # Setup mocks
        translated_file = Path("/test/translated.txt")
        mock_find.return_value = translated_file
        translated_file = Mock(spec=Path)
        translated_file.exists.return_value = True
        mock_find.return_value = translated_file

        mock_extract.return_value = {"title_english": "Novel", "author_english": "Author"}
        mock_create.return_value = True

        result = process_epub_generation(self.current_path, self.args, self.progress, self.logger)

        assert result is True
        mock_create.assert_called_once()

    @patch("enchant_book_manager.workflow_epub.find_translated_file")
    def test_translated_file_not_found(self, mock_find):
        """Test when translated file is not found."""
        mock_find.return_value = None

        result = process_epub_generation(self.current_path, self.args, self.progress, self.logger)

        assert result is False
        assert self.progress["phases"]["epub"]["error"] == "No translation directory or file found"

    @patch("enchant_book_manager.workflow_epub.find_translated_file")
    def test_provided_translated_not_exists(self, mock_find):
        """Test when provided translated file doesn't exist."""
        self.args.translated = "/test/missing.txt"
        translated_file = Mock(spec=Path)
        translated_file.exists.return_value = False
        mock_find.return_value = translated_file

        result = process_epub_generation(self.current_path, self.args, self.progress, self.logger)

        assert result is False
        assert self.progress["phases"]["epub"]["error"] == "Provided translated file not found"

    @patch("enchant_book_manager.workflow_epub.find_translated_file")
    @patch("enchant_book_manager.workflow_epub.extract_book_info_from_path")
    @patch("enchant_book_manager.workflow_epub.create_epub_from_translated")
    def test_title_author_overrides(self, mock_create, mock_extract, mock_find):
        """Test title and author overrides from command line."""
        # Setup mocks
        translated_file = Mock(spec=Path)
        translated_file.exists.return_value = True
        mock_find.return_value = translated_file

        mock_extract.return_value = {"title_english": "Original Title", "author_english": "Original Author"}
        mock_create.return_value = True

        # Set overrides
        self.args.epub_title = "Override Title"
        self.args.epub_author = "Override Author"

        result = process_epub_generation(self.current_path, self.args, self.progress, self.logger)

        assert result is True

        # Verify overrides were used
        call_args = mock_create.call_args.args
        assert call_args[2] == "Override Title"  # book_title
        assert call_args[3] == "Override Author"  # book_author

    @patch("enchant_book_manager.workflow_epub.find_translated_file")
    @patch("enchant_book_manager.workflow_epub.extract_book_info_from_path")
    @patch("enchant_book_manager.workflow_epub.create_epub_from_translated")
    def test_extract_from_translated_path(self, mock_create, mock_extract, mock_find):
        """Test book info extraction from translated file when provided."""
        # Setup mocks
        self.args.translated = "/test/translated.txt"
        translated_file = Mock(spec=Path)
        translated_file.exists.return_value = True
        mock_find.return_value = translated_file

        mock_extract.return_value = {"title_english": "Novel", "author_english": "Author"}
        mock_create.return_value = True

        result = process_epub_generation(self.current_path, self.args, self.progress, self.logger)

        assert result is True
        # Should extract from translated file when args.translated is set
        mock_extract.assert_called_with(translated_file)

    @patch("enchant_book_manager.workflow_epub.find_translated_file")
    @patch("enchant_book_manager.workflow_epub.extract_book_info_from_path")
    @patch("enchant_book_manager.workflow_epub.create_epub_from_translated")
    def test_fallback_title_author(self, mock_create, mock_extract, mock_find):
        """Test fallback values when book info is missing."""
        # Setup mocks
        translated_file = Mock(spec=Path)
        translated_file.exists.return_value = True
        mock_find.return_value = translated_file

        mock_extract.return_value = {}  # No book info
        mock_create.return_value = True

        result = process_epub_generation(self.current_path, self.args, self.progress, self.logger)

        assert result is True

        # Should use filename stem and "Unknown" as fallbacks
        call_args = mock_create.call_args.args
        assert call_args[2] == "novel"  # book_title from stem
        assert call_args[3] == "Unknown"  # book_author default

    @patch("enchant_book_manager.workflow_epub.find_translated_file")
    @patch("enchant_book_manager.workflow_epub.extract_book_info_from_path")
    @patch("enchant_book_manager.workflow_epub.create_epub_from_translated")
    def test_creation_failure(self, mock_create, mock_extract, mock_find):
        """Test handling of EPUB creation failure."""
        # Setup mocks
        translated_file = Mock(spec=Path)
        translated_file.exists.return_value = True
        mock_find.return_value = translated_file

        mock_extract.return_value = {"title_english": "Novel", "author_english": "Author"}
        mock_create.return_value = False

        result = process_epub_generation(self.current_path, self.args, self.progress, self.logger)

        assert result is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
