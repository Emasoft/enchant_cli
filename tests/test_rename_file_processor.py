#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test suite for rename_file_processor module.
"""

import pytest
import json
import logging
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from enchant_book_manager.rename_file_processor import (
    find_text_files,
    decode_file_content,
    extract_json,
    create_new_filename,
    rename_file_with_metadata,
    validate_metadata,
    process_novel_file,
    MIN_FILE_SIZE_KB,
    CONTENT_NUMBER_OF_CHARACTERS_HARD_LIMIT,
    DEFAULT_KB_TO_READ,
)
from enchant_book_manager.icloud_sync import ICloudSyncError


class TestFindTextFiles:
    """Test the find_text_files function."""

    def test_non_recursive_search(self, tmp_path):
        """Test finding text files without recursion."""
        # Create test files
        (tmp_path / "file1.txt").write_text("x" * (MIN_FILE_SIZE_KB * 1024))
        (tmp_path / "file2.txt").write_text("x" * (MIN_FILE_SIZE_KB * 1024))
        (tmp_path / "small.txt").write_text("too small")
        (tmp_path / ".hidden.txt").write_text("x" * (MIN_FILE_SIZE_KB * 1024))
        (tmp_path / "not_text.pdf").write_text("x" * (MIN_FILE_SIZE_KB * 1024))

        # Create subdirectory with files
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "sub_file.txt").write_text("x" * (MIN_FILE_SIZE_KB * 1024))

        result = find_text_files(tmp_path, recursive=False)

        assert len(result) == 2
        assert tmp_path / "file1.txt" in result
        assert tmp_path / "file2.txt" in result
        assert tmp_path / "small.txt" not in result  # Too small
        assert tmp_path / ".hidden.txt" not in result  # Hidden
        assert subdir / "sub_file.txt" not in result  # Not recursive

    def test_recursive_search(self, tmp_path):
        """Test finding text files with recursion."""
        # Create test files
        (tmp_path / "file1.txt").write_text("x" * (MIN_FILE_SIZE_KB * 1024))

        # Create nested subdirectories
        subdir1 = tmp_path / "subdir1"
        subdir1.mkdir()
        (subdir1 / "sub_file1.txt").write_text("x" * (MIN_FILE_SIZE_KB * 1024))

        subdir2 = subdir1 / "subdir2"
        subdir2.mkdir()
        (subdir2 / "sub_file2.txt").write_text("x" * (MIN_FILE_SIZE_KB * 1024))

        result = find_text_files(tmp_path, recursive=True)

        assert len(result) == 3
        assert tmp_path / "file1.txt" in result
        assert subdir1 / "sub_file1.txt" in result
        assert subdir2 / "sub_file2.txt" in result

    def test_empty_directory(self, tmp_path):
        """Test with empty directory."""
        result = find_text_files(tmp_path, recursive=False)
        assert result == []

    def test_no_eligible_files(self, tmp_path):
        """Test directory with no eligible files."""
        # Only small files
        (tmp_path / "small1.txt").write_text("small")
        (tmp_path / "small2.txt").write_text("tiny")

        # Hidden files
        (tmp_path / ".hidden1.txt").write_text("x" * (MIN_FILE_SIZE_KB * 1024))

        # Non-text files
        (tmp_path / "file.pdf").write_text("x" * (MIN_FILE_SIZE_KB * 1024))

        result = find_text_files(tmp_path, recursive=False)
        assert result == []

    def test_size_boundary(self, tmp_path):
        """Test files at the size boundary."""
        # Exactly at boundary
        (tmp_path / "exact.txt").write_text("x" * (MIN_FILE_SIZE_KB * 1024))

        # Just below boundary
        (tmp_path / "below.txt").write_text("x" * (MIN_FILE_SIZE_KB * 1024 - 1))

        # Just above boundary
        (tmp_path / "above.txt").write_text("x" * (MIN_FILE_SIZE_KB * 1024 + 1))

        result = find_text_files(tmp_path, recursive=False)

        assert len(result) == 2
        assert tmp_path / "exact.txt" in result
        assert tmp_path / "above.txt" in result
        assert tmp_path / "below.txt" not in result


class TestDecodeFileContent:
    """Test the decode_file_content function."""

    def setup_method(self):
        """Set up test fixtures."""
        self.logger = logging.getLogger("test")

    @patch("enchant_book_manager.rename_file_processor.decode_full_file")
    def test_successful_decode(self, mock_decode):
        """Test successful file decoding."""
        file_path = Path("/test/file.txt")
        mock_icloud = Mock()
        mock_icloud.ensure_synced.return_value = file_path
        mock_decode.return_value = "Test content " * 100

        result = decode_file_content(file_path, 10, mock_icloud)

        assert result is not None
        assert len(result) <= 10 * 1024  # Should be limited
        mock_icloud.ensure_synced.assert_called_once_with(file_path)
        mock_decode.assert_called_once()

    @patch("enchant_book_manager.rename_file_processor.decode_full_file")
    def test_icloud_sync_error(self, mock_decode):
        """Test handling of iCloud sync error."""
        file_path = Path("/test/file.txt")
        mock_icloud = Mock()
        mock_icloud.ensure_synced.side_effect = ICloudSyncError("Sync failed")

        result = decode_file_content(file_path, 10, mock_icloud)

        assert result is None
        mock_decode.assert_not_called()

    @patch("enchant_book_manager.rename_file_processor.decode_full_file")
    def test_decode_failure(self, mock_decode):
        """Test handling of decode failure."""
        file_path = Path("/test/file.txt")
        mock_icloud = Mock()
        mock_icloud.ensure_synced.return_value = file_path
        mock_decode.side_effect = Exception("Decode error")

        result = decode_file_content(file_path, 10, mock_icloud)

        assert result is None

    @patch("enchant_book_manager.rename_file_processor.decode_full_file")
    def test_no_size_limit(self, mock_decode):
        """Test decoding without size limit."""
        file_path = Path("/test/file.txt")
        mock_icloud = Mock()
        mock_icloud.ensure_synced.return_value = file_path
        mock_decode.return_value = "Test content " * 1000

        result = decode_file_content(file_path, 0, mock_icloud)

        # Should return full content
        assert result == "Test content " * 1000

    @patch("enchant_book_manager.rename_file_processor.decode_full_file")
    def test_empty_content(self, mock_decode):
        """Test handling of empty content."""
        file_path = Path("/test/file.txt")
        mock_icloud = Mock()
        mock_icloud.ensure_synced.return_value = file_path
        mock_decode.return_value = ""

        result = decode_file_content(file_path, 10, mock_icloud)

        assert result == ""


class TestExtractJson:
    """Test the extract_json function."""

    def test_valid_json(self):
        """Test extraction of valid JSON."""
        response = '{"title": "Test", "author": "Author"}'
        result = extract_json(response)

        assert result == {"title": "Test", "author": "Author"}

    def test_json_with_text(self):
        """Test extraction of JSON embedded in text."""
        response = 'Here is the data: {"title": "Test", "author": "Author"} and more text'
        result = extract_json(response)

        assert result == {"title": "Test", "author": "Author"}

    def test_multiline_json(self):
        """Test extraction of multiline JSON."""
        response = """Some text before
        {
            "title": "Test",
            "author": "Author"
        }
        Some text after"""
        result = extract_json(response)

        assert result == {"title": "Test", "author": "Author"}

    def test_invalid_json(self):
        """Test handling of invalid JSON."""
        response = '{"title": "Test", "author": }'  # Invalid
        result = extract_json(response)

        assert result is None

    def test_no_json(self):
        """Test handling when no JSON is present."""
        response = "Just some plain text without JSON"
        result = extract_json(response)

        assert result is None

    def test_nested_json(self):
        """Test extraction of nested JSON."""
        response = '{"data": {"title": "Test", "meta": {"author": "Author"}}}'
        result = extract_json(response)

        assert result == {"data": {"title": "Test", "meta": {"author": "Author"}}}

    def test_json_with_special_chars(self):
        """Test JSON with special characters."""
        response = '{"title": "Test\\"Book", "author": "Author\\nName"}'
        result = extract_json(response)

        assert result == {"title": 'Test"Book', "author": "Author\nName"}


class TestCreateNewFilename:
    """Test the create_new_filename function."""

    def test_complete_metadata(self):
        """Test with complete metadata."""
        metadata = {
            "novel_title_english": "Great Novel",
            "author_name_english": "John Doe",
            "author_name_romanized": "Doe John",
            "novel_title_original": "偉大小說",
            "author_name_original": "約翰·多伊",
        }

        result = create_new_filename(metadata)
        expected = "Great Novel by John Doe (Doe John) - 偉大小說 by 約翰·多伊.txt"
        assert result == expected

    def test_missing_fields(self):
        """Test with missing metadata fields."""
        metadata = {
            "novel_title_english": "Test Novel"
            # Missing other fields
        }

        result = create_new_filename(metadata)
        expected = "Test Novel by Unknown Author (Unknown) - Unknown by Unknown.txt"
        assert result == expected

    def test_special_characters(self):
        """Test filename sanitization of special characters."""
        metadata = {
            "novel_title_english": "Novel: Part 1/2",
            "author_name_english": "Author <Name>",
            "author_name_romanized": "Name|Author",
            "novel_title_original": "小説：第一部",
            "author_name_original": "作者名",
        }

        result = create_new_filename(metadata)
        # Special characters should be sanitized in English parts
        assert "/" not in result
        assert "<" not in result
        assert ">" not in result
        assert "|" not in result
        # Note: Chinese colon "：" is different from English ":" and may not be sanitized
        assert result.count(":") <= 1  # At most one colon from the Chinese part

    def test_empty_values(self):
        """Test with empty string values."""
        metadata = {
            "novel_title_english": "",
            "author_name_english": "",
            "author_name_romanized": "",
            "novel_title_original": "",
            "author_name_original": "",
        }

        result = create_new_filename(metadata)
        # Empty strings are sanitized to "unnamed"
        assert "unnamed" in result


class TestRenameFileWithMetadata:
    """Test the rename_file_with_metadata function."""

    def test_successful_rename(self, tmp_path):
        """Test successful file renaming."""
        # Create test file
        old_file = tmp_path / "old_name.txt"
        old_file.write_text("content")

        metadata = {
            "novel_title_english": "New Novel",
            "author_name_english": "Author",
            "author_name_romanized": "Author",
            "novel_title_original": "新小説",
            "author_name_original": "作者",
        }

        new_path = rename_file_with_metadata(old_file, metadata)

        assert new_path.exists()
        assert not old_file.exists()
        assert "New Novel by Author" in new_path.name

    def test_naming_collision(self, tmp_path):
        """Test handling of naming collisions."""
        # Create existing file with target name
        metadata = {
            "novel_title_english": "Novel",
            "author_name_english": "Author",
            "author_name_romanized": "Author",
            "novel_title_original": "小説",
            "author_name_original": "作者",
        }

        expected_name = create_new_filename(metadata)
        existing_file = tmp_path / expected_name
        existing_file.write_text("existing")

        # Create file to rename
        old_file = tmp_path / "old_name.txt"
        old_file.write_text("content")

        new_path = rename_file_with_metadata(old_file, metadata)

        assert new_path.exists()
        assert not old_file.exists()
        assert "(1)" in new_path.name
        assert existing_file.exists()  # Original should still exist

    def test_multiple_collisions(self, tmp_path):
        """Test handling of multiple naming collisions."""
        metadata = {
            "novel_title_english": "Novel",
            "author_name_english": "Author",
            "author_name_romanized": "Author",
            "novel_title_original": "小説",
            "author_name_original": "作者",
        }

        # Create existing files to force collision
        expected_name = create_new_filename(metadata)
        (tmp_path / expected_name).write_text("existing1")

        # Create file to rename
        old_file = tmp_path / "old_name.txt"
        old_file.write_text("content")

        new_path = rename_file_with_metadata(old_file, metadata)

        assert new_path.exists()
        assert not old_file.exists()
        # Should have (1) appended due to collision
        assert new_path.name.endswith("(1).txt")

    def test_rename_failure(self, tmp_path):
        """Test handling of rename failure."""
        old_file = tmp_path / "old_name.txt"
        old_file.write_text("content")

        metadata = {
            "novel_title_english": "Novel",
            "author_name_english": "Author",
            "author_name_romanized": "Author",
            "novel_title_original": "小説",
            "author_name_original": "作者",
        }

        # Mock rename to fail
        with patch.object(Path, "rename", side_effect=OSError("Permission denied")):
            new_path = rename_file_with_metadata(old_file, metadata)

        assert new_path == old_file  # Should return original path
        assert old_file.exists()  # File should still exist


class TestValidateMetadata:
    """Test the validate_metadata function."""

    def test_valid_metadata(self):
        """Test with valid metadata containing all required keys."""
        metadata = {
            "detected_language": "zh",
            "novel_title_original": "原始标题",
            "author_name_original": "原始作者",
            "novel_title_english": "English Title",
            "author_name_english": "English Author",
            "author_name_romanized": "Romanized Author",
        }

        assert validate_metadata(metadata) is True

    def test_missing_key(self):
        """Test with missing required key."""
        metadata = {
            "detected_language": "zh",
            "novel_title_original": "原始标题",
            # Missing other required keys
        }

        assert validate_metadata(metadata) is False

    def test_empty_metadata(self):
        """Test with empty metadata."""
        assert validate_metadata({}) is False

    def test_extra_keys(self):
        """Test that extra keys don't affect validation."""
        metadata = {
            "detected_language": "zh",
            "novel_title_original": "原始标题",
            "author_name_original": "原始作者",
            "novel_title_english": "English Title",
            "author_name_english": "English Author",
            "author_name_romanized": "Romanized Author",
            "extra_key": "Extra Value",
            "another_extra": 123,
        }

        assert validate_metadata(metadata) is True

    def test_none_values(self):
        """Test that None values are considered present."""
        metadata = {
            "detected_language": None,
            "novel_title_original": None,
            "author_name_original": None,
            "novel_title_english": None,
            "author_name_english": None,
            "author_name_romanized": None,
        }

        assert validate_metadata(metadata) is True


class TestProcessNovelFile:
    """Test the process_novel_file function."""

    def setup_method(self):
        """Set up test fixtures."""
        self.file_path = Path("/test/novel.txt")
        self.api_client = Mock()

    @patch("enchant_book_manager.rename_file_processor.ICloudSync")
    @patch("enchant_book_manager.rename_file_processor.decode_file_content")
    def test_successful_processing(self, mock_decode, mock_icloud_class):
        """Test successful novel file processing."""
        # Setup mocks
        mock_icloud = Mock()
        mock_icloud_class.return_value = mock_icloud

        mock_decode.return_value = "Novel content"

        self.api_client.extract_metadata.return_value = json.dumps(
            {
                "detected_language": "zh",
                "novel_title_original": "原始标题",
                "author_name_original": "原始作者",
                "novel_title_english": "English Title",
                "author_name_english": "English Author",
                "author_name_romanized": "Romanized Author",
            }
        )

        with patch("enchant_book_manager.rename_file_processor.rename_file_with_metadata") as mock_rename:
            new_path = Path("/test/English Title by English Author.txt")
            mock_rename.return_value = new_path

            success, result_path, metadata = process_novel_file(self.file_path, self.api_client, dry_run=False)

        assert success is True
        assert result_path == new_path
        assert metadata["novel_title_english"] == "English Title"

        # Verify calls
        mock_decode.assert_called_once_with(self.file_path, DEFAULT_KB_TO_READ, mock_icloud)
        self.api_client.extract_metadata.assert_called_once_with("Novel content", CONTENT_NUMBER_OF_CHARACTERS_HARD_LIMIT)
        mock_rename.assert_called_once()

    @patch("enchant_book_manager.rename_file_processor.ICloudSync")
    @patch("enchant_book_manager.rename_file_processor.decode_file_content")
    def test_dry_run_mode(self, mock_decode, mock_icloud_class):
        """Test dry run mode doesn't rename file."""
        # Setup mocks
        mock_icloud = Mock()
        mock_icloud_class.return_value = mock_icloud

        mock_decode.return_value = "Novel content"

        self.api_client.extract_metadata.return_value = json.dumps(
            {
                "detected_language": "zh",
                "novel_title_original": "原始标题",
                "author_name_original": "原始作者",
                "novel_title_english": "English Title",
                "author_name_english": "English Author",
                "author_name_romanized": "Romanized Author",
            }
        )

        with patch("enchant_book_manager.rename_file_processor.rename_file_with_metadata") as mock_rename:
            success, result_path, metadata = process_novel_file(self.file_path, self.api_client, dry_run=True)

        assert success is True
        assert "English Title by English Author" in result_path.name
        assert metadata["novel_title_english"] == "English Title"

        # Should not call rename in dry run
        mock_rename.assert_not_called()

    @patch("enchant_book_manager.rename_file_processor.ICloudSync")
    @patch("enchant_book_manager.rename_file_processor.decode_file_content")
    def test_decode_failure(self, mock_decode, mock_icloud_class):
        """Test handling of decode failure."""
        mock_icloud = Mock()
        mock_icloud_class.return_value = mock_icloud

        mock_decode.return_value = None

        success, result_path, metadata = process_novel_file(self.file_path, self.api_client, dry_run=False)

        assert success is False
        assert result_path == self.file_path
        assert metadata == {}

        self.api_client.extract_metadata.assert_not_called()

    @patch("enchant_book_manager.rename_file_processor.ICloudSync")
    @patch("enchant_book_manager.rename_file_processor.decode_file_content")
    def test_api_failure(self, mock_decode, mock_icloud_class):
        """Test handling of API failure."""
        mock_icloud = Mock()
        mock_icloud_class.return_value = mock_icloud

        mock_decode.return_value = "Novel content"
        self.api_client.extract_metadata.return_value = None

        success, result_path, metadata = process_novel_file(self.file_path, self.api_client, dry_run=False)

        assert success is False
        assert result_path == self.file_path
        assert metadata == {}

    @patch("enchant_book_manager.rename_file_processor.ICloudSync")
    @patch("enchant_book_manager.rename_file_processor.decode_file_content")
    def test_invalid_json_response(self, mock_decode, mock_icloud_class):
        """Test handling of invalid JSON in API response."""
        mock_icloud = Mock()
        mock_icloud_class.return_value = mock_icloud

        mock_decode.return_value = "Novel content"
        self.api_client.extract_metadata.return_value = "Invalid JSON response"

        success, result_path, metadata = process_novel_file(self.file_path, self.api_client, dry_run=False)

        assert success is False
        assert result_path == self.file_path
        assert metadata == {}

    @patch("enchant_book_manager.rename_file_processor.ICloudSync")
    @patch("enchant_book_manager.rename_file_processor.decode_file_content")
    def test_invalid_metadata(self, mock_decode, mock_icloud_class):
        """Test handling of invalid metadata."""
        mock_icloud = Mock()
        mock_icloud_class.return_value = mock_icloud

        mock_decode.return_value = "Novel content"
        self.api_client.extract_metadata.return_value = json.dumps(
            {
                "detected_language": "zh",
                # Missing required fields
            }
        )

        success, result_path, metadata = process_novel_file(self.file_path, self.api_client, dry_run=False)

        assert success is False
        assert result_path == self.file_path
        assert metadata == {}

    @patch("enchant_book_manager.rename_file_processor.ICloudSync")
    @patch("enchant_book_manager.rename_file_processor.decode_file_content")
    def test_exception_handling(self, mock_decode, mock_icloud_class):
        """Test handling of unexpected exceptions."""
        mock_icloud = Mock()
        mock_icloud_class.return_value = mock_icloud

        mock_decode.side_effect = Exception("Unexpected error")

        success, result_path, metadata = process_novel_file(self.file_path, self.api_client, dry_run=False)

        assert success is False
        assert result_path == self.file_path
        assert metadata == {}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
