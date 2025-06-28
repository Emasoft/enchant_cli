#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test suite for epub_utils module.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call
import logging
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from enchant_book_manager.epub_utils import (
    create_epub_with_config,
    get_epub_config_from_book_info,
)


class TestCreateEpubWithConfig:
    """Test the create_epub_with_config function."""

    @patch("enchant_book_manager.epub_utils.epub_available", True)
    @patch("enchant_book_manager.epub_utils.create_epub_from_txt_file")
    def test_successful_creation(self, mock_create_epub):
        """Test successful EPUB creation with full configuration."""
        # Setup
        mock_create_epub.return_value = (True, [])
        txt_path = Path("test.txt")
        output_path = Path("test.epub")
        config = {
            "title": "Test Book",
            "author": "Test Author",
            "language": "en",
            "cover_path": "/path/to/cover.jpg",
            "generate_toc": True,
            "validate": True,
            "strict_mode": False,
            "custom_css": "body { font-family: serif; }",
            "metadata": {"publisher": "Test Publisher"},
        }
        logger = Mock(spec=logging.Logger)

        # Execute
        success, issues = create_epub_with_config(txt_path, output_path, config, logger)

        # Verify
        assert success is True
        assert issues == []
        mock_create_epub.assert_called_once_with(
            txt_file_path=txt_path,
            output_path=output_path,
            title="Test Book",
            author="Test Author",
            cover_path=Path("/path/to/cover.jpg"),
            generate_toc=True,
            validate=True,
            strict_mode=False,
            language="en",
            custom_css="body { font-family: serif; }",
            metadata={"publisher": "Test Publisher"},
        )
        logger.info.assert_any_call("Creating EPUB for: Test Book by Test Author")
        logger.info.assert_any_call(f"EPUB created successfully: {output_path}")

    @patch("enchant_book_manager.epub_utils.epub_available", False)
    def test_epub_not_available(self):
        """Test when EPUB module is not available."""
        config = {"title": "Test", "author": "Author"}
        logger = Mock(spec=logging.Logger)

        success, issues = create_epub_with_config(Path("test.txt"), Path("test.epub"), config, logger)

        assert success is False
        assert issues == ["EPUB creation requested but 'make_epub' module is not available."]
        logger.error.assert_called_once()

    def test_missing_required_fields(self):
        """Test with missing title or author."""
        logger = Mock(spec=logging.Logger)

        # Missing title
        config = {"author": "Test Author"}
        success, issues = create_epub_with_config(Path("test.txt"), Path("test.epub"), config, logger)
        assert success is False
        assert issues == ["Title and author are required for EPUB creation"]

        # Missing author
        config = {"title": "Test Book"}
        success, issues = create_epub_with_config(Path("test.txt"), Path("test.epub"), config, logger)
        assert success is False
        assert issues == ["Title and author are required for EPUB creation"]

        # Both missing
        config = {}
        success, issues = create_epub_with_config(Path("test.txt"), Path("test.epub"), config, logger)
        assert success is False
        assert issues == ["Title and author are required for EPUB creation"]

    @patch("enchant_book_manager.epub_utils.epub_available", True)
    @patch("enchant_book_manager.epub_utils.create_epub_from_txt_file")
    def test_with_validation_warnings(self, mock_create_epub):
        """Test EPUB creation with validation warnings."""
        # Setup with warnings
        warnings = [
            "Chapter 1 is missing",
            "Chapter 5 is repeated",
            "Chapter 10 is out of order",
        ]
        mock_create_epub.return_value = (True, warnings)
        config = {"title": "Test Book", "author": "Test Author"}
        logger = Mock(spec=logging.Logger)

        # Execute
        success, issues = create_epub_with_config(Path("test.txt"), Path("test.epub"), config, logger)

        # Verify
        assert success is True
        assert issues == warnings
        logger.warning.assert_any_call("EPUB created with 3 validation warnings")
        logger.warning.assert_any_call("  - Chapter 1 is missing")

    @patch("enchant_book_manager.epub_utils.epub_available", True)
    @patch("enchant_book_manager.epub_utils.create_epub_from_txt_file")
    def test_with_many_warnings(self, mock_create_epub):
        """Test EPUB creation with many validation warnings (truncated display)."""
        # Setup with many warnings
        warnings = [f"Warning {i}" for i in range(10)]
        mock_create_epub.return_value = (True, warnings)
        config = {"title": "Test Book", "author": "Test Author"}
        logger = Mock(spec=logging.Logger)

        # Execute
        success, issues = create_epub_with_config(Path("test.txt"), Path("test.epub"), config, logger)

        # Verify only first 5 warnings are logged
        assert success is True
        logger.warning.assert_any_call("  ... and 5 more warnings")

    @patch("enchant_book_manager.epub_utils.epub_available", True)
    @patch("enchant_book_manager.epub_utils.create_epub_from_txt_file")
    def test_creation_failure(self, mock_create_epub):
        """Test EPUB creation failure."""
        # Setup with errors
        errors = ["Invalid chapter structure", "Missing content"]
        mock_create_epub.return_value = (False, errors)
        config = {"title": "Test Book", "author": "Test Author"}
        logger = Mock(spec=logging.Logger)

        # Execute
        success, issues = create_epub_with_config(Path("test.txt"), Path("test.epub"), config, logger)

        # Verify
        assert success is False
        assert issues == errors
        logger.error.assert_any_call("EPUB creation failed with 2 errors")
        logger.error.assert_any_call("  - Invalid chapter structure")

    @patch("enchant_book_manager.epub_utils.epub_available", True)
    @patch("enchant_book_manager.epub_utils.create_epub_from_txt_file")
    def test_exception_handling(self, mock_create_epub):
        """Test exception handling during EPUB creation."""
        # Setup with exception
        mock_create_epub.side_effect = Exception("Test error")
        config = {"title": "Test Book", "author": "Test Author"}
        logger = Mock(spec=logging.Logger)

        # Execute
        success, issues = create_epub_with_config(Path("test.txt"), Path("test.epub"), config, logger)

        # Verify
        assert success is False
        assert issues == ["Unexpected error during EPUB creation: Test error"]
        logger.exception.assert_called_once_with("Error creating EPUB")

    @patch("enchant_book_manager.epub_utils.epub_available", True)
    @patch("enchant_book_manager.epub_utils.create_epub_from_txt_file")
    def test_without_logger(self, mock_create_epub):
        """Test EPUB creation without logger."""
        mock_create_epub.return_value = (True, [])
        config = {"title": "Test Book", "author": "Test Author"}

        # Execute without logger
        success, issues = create_epub_with_config(Path("test.txt"), Path("test.epub"), config, None)

        # Should still work
        assert success is True
        assert issues == []

    @patch("enchant_book_manager.epub_utils.epub_available", True)
    @patch("enchant_book_manager.epub_utils.create_epub_from_txt_file")
    def test_default_values(self, mock_create_epub):
        """Test with minimal config using default values."""
        mock_create_epub.return_value = (True, [])
        config = {"title": "Test Book", "author": "Test Author"}

        success, issues = create_epub_with_config(Path("test.txt"), Path("test.epub"), config)

        # Verify defaults are used
        mock_create_epub.assert_called_once()
        call_args = mock_create_epub.call_args[1]
        assert call_args["generate_toc"] is True
        assert call_args["validate"] is True
        assert call_args["strict_mode"] is False
        assert call_args["language"] == "en"
        assert call_args["custom_css"] is None
        assert call_args["metadata"] is None


class TestGetEpubConfigFromBookInfo:
    """Test the get_epub_config_from_book_info function."""

    def test_basic_book_info(self):
        """Test with basic book information."""
        book_info = {
            "title_english": "Test Novel",
            "author_english": "Test Author",
        }

        config = get_epub_config_from_book_info(book_info)

        assert config == {
            "title": "Test Novel",
            "author": "Test Author",
            "generate_toc": True,
            "validate": True,
            "strict_mode": False,
        }

    def test_with_chinese_info(self):
        """Test with Chinese title and author."""
        book_info = {
            "title_english": "Cultivation Master",
            "author_english": "Unknown Author",
            "title_chinese": "修炼高手",
            "author_chinese": "未知作者",
        }

        config = get_epub_config_from_book_info(book_info)

        assert config["title"] == "Cultivation Master"
        assert config["author"] == "Unknown Author"
        assert config["metadata"]["original_title"] == "修炼高手"
        assert config["metadata"]["original_author"] == "未知作者"

    def test_with_epub_settings(self):
        """Test with EPUB settings from configuration."""
        book_info = {
            "title_english": "Test Novel",
            "author_english": "Test Author",
        }
        epub_settings = {
            "generate_toc": False,
            "validate_chapters": False,
            "strict_mode": True,
            "language": "zh",
            "custom_css": "body { color: red; }",
            "chapter_patterns": ["Chapter", "Part"],
        }

        config = get_epub_config_from_book_info(book_info, epub_settings)

        assert config["generate_toc"] is False
        assert config["validate"] is False
        assert config["strict_mode"] is True
        assert config["language"] == "zh"
        assert config["custom_css"] == "body { color: red; }"
        assert config["chapter_patterns"] == ["Chapter", "Part"]

    def test_with_metadata_settings(self):
        """Test with metadata settings."""
        book_info = {
            "title_english": "Test Novel",
            "author_english": "Test Author",
            "title_chinese": "测试小说",
            "author_chinese": "测试作者",
        }
        epub_settings = {
            "metadata": {
                "publisher": "Test Publisher",
                "series": "Test Series",
                "series_index": "1",
                "description_template": "Translation of '{original_title}' by {original_author}",
                "tags": ["cultivation", "fantasy"],
            }
        }

        config = get_epub_config_from_book_info(book_info, epub_settings)

        metadata = config["metadata"]
        assert metadata["publisher"] == "Test Publisher"
        assert metadata["series"] == "Test Series"
        assert metadata["series_index"] == "1"
        assert metadata["description"] == "Translation of '测试小说' by 测试作者"
        assert metadata["tags"] == ["cultivation", "fantasy"]

    def test_missing_book_info_fields(self):
        """Test with missing book info fields."""
        book_info = {}  # Empty

        config = get_epub_config_from_book_info(book_info)

        assert config["title"] == "Unknown Title"
        assert config["author"] == "Unknown Author"
        assert "metadata" not in config  # No metadata since no Chinese info

    def test_partial_metadata(self):
        """Test with partial metadata settings."""
        book_info = {
            "title_english": "Test Novel",
            "author_english": "Test Author",
        }
        epub_settings = {
            "metadata": {
                "publisher": "Test Publisher",
                # No other metadata fields
            }
        }

        config = get_epub_config_from_book_info(book_info, epub_settings)

        assert config["metadata"]["publisher"] == "Test Publisher"
        assert "series" not in config["metadata"]
        assert "description" not in config["metadata"]

    def test_description_template_formatting(self):
        """Test description template with various formats."""
        book_info = {
            "title_english": "English Title",
            "author_english": "English Author",
            "title_chinese": "中文标题",
            "author_chinese": "中文作者",
        }
        epub_settings = {
            "metadata": {
                "description_template": "{title} ({original_title}) - A translation by EnChANT",
            }
        }

        config = get_epub_config_from_book_info(book_info, epub_settings)

        assert config["metadata"]["description"] == "English Title (中文标题) - A translation by EnChANT"

    def test_empty_epub_settings(self):
        """Test with empty EPUB settings."""
        book_info = {
            "title_english": "Test Novel",
            "author_english": "Test Author",
            "title_chinese": "测试小说",
        }

        config = get_epub_config_from_book_info(book_info, {})

        # Should still have Chinese metadata
        assert config["metadata"]["original_title"] == "测试小说"
        assert "original_author" not in config["metadata"]  # Not provided

    def test_none_epub_settings(self):
        """Test with None EPUB settings."""
        book_info = {
            "title_english": "Test Novel",
            "author_english": "Test Author",
        }

        config = get_epub_config_from_book_info(book_info, None)

        assert config == {
            "title": "Test Novel",
            "author": "Test Author",
            "generate_toc": True,
            "validate": True,
            "strict_mode": False,
        }
