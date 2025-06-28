#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test suite for file_handler module.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, mock_open, MagicMock
import logging
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from enchant_book_manager.file_handler import (
    load_text_file,
    save_text_file,
    decode_input_file_content,
    detect_file_encoding,
)


class TestLoadTextFile:
    """Test the load_text_file function."""

    @patch("enchant_book_manager.file_handler.Path.is_file", return_value=True)
    @patch("builtins.open", new_callable=mock_open, read_data="Test file content\nLine 2")
    def test_load_valid_file(self, mock_file, mock_is_file):
        """Test loading a valid text file."""
        logger = Mock()

        result = load_text_file("test.txt", logger)

        assert result == "Test file content\nLine 2"
        mock_file.assert_called_once_with(Path.cwd() / "test.txt", encoding="utf8")
        logger.debug.assert_called_once_with("Test file content\nLine 2")

    @patch("enchant_book_manager.file_handler.Path.is_file", return_value=True)
    @patch("builtins.open", new_callable=mock_open, read_data="中文内容")
    def test_load_unicode_file(self, mock_file, mock_is_file):
        """Test loading a file with Unicode content."""
        result = load_text_file("chinese.txt")

        assert result == "中文内容"
        mock_file.assert_called_once()

    @patch("enchant_book_manager.file_handler.Path.is_file", return_value=False)
    def test_load_non_existent_file(self, mock_is_file):
        """Test loading a non-existent file."""
        logger = Mock()

        result = load_text_file("missing.txt", logger)

        assert result is None
        logger.debug.assert_called_once()
        assert "is not a valid file!" in logger.debug.call_args[0][0]

    @patch("enchant_book_manager.file_handler.Path.is_file", return_value=True)
    @patch("builtins.open", side_effect=OSError("Permission denied"))
    def test_load_file_os_error(self, mock_file, mock_is_file):
        """Test loading a file with OS error."""
        logger = Mock()

        result = load_text_file("forbidden.txt", logger)

        assert result is None
        logger.error.assert_called_once()
        assert "Error reading file" in logger.error.call_args[0][0]
        assert "Permission denied" in logger.error.call_args[0][0]

    @patch("enchant_book_manager.file_handler.Path.is_file", return_value=True)
    @patch("builtins.open", side_effect=PermissionError("Access denied"))
    def test_load_file_permission_error(self, mock_file, mock_is_file):
        """Test loading a file with permission error."""
        logger = Mock()

        result = load_text_file("protected.txt", logger)

        assert result is None
        logger.error.assert_called_once()
        assert "Access denied" in logger.error.call_args[0][0]

    @patch("enchant_book_manager.file_handler.Path.is_file", return_value=True)
    @patch("builtins.open", new_callable=mock_open, read_data="Content")
    def test_load_file_with_path_object(self, mock_file, mock_is_file):
        """Test loading a file with Path object."""
        test_path = Path("test.txt")

        result = load_text_file(test_path)

        assert result == "Content"
        mock_file.assert_called_once_with(Path.cwd() / test_path, encoding="utf8")

    @patch("enchant_book_manager.file_handler.Path.is_file", return_value=True)
    @patch("builtins.open", new_callable=mock_open, read_data="Content")
    def test_load_file_without_logger(self, mock_file, mock_is_file):
        """Test loading a file without logger."""
        result = load_text_file("test.txt")

        assert result == "Content"
        # Should not raise any errors


class TestSaveTextFile:
    """Test the save_text_file function."""

    @patch("builtins.open", new_callable=mock_open)
    @patch("enchant_book_manager.file_handler.clean")
    def test_save_text_file(self, mock_clean, mock_file):
        """Test saving text to a file."""
        mock_clean.return_value = "Cleaned text"
        logger = Mock()

        save_text_file("Original text", "output.txt", logger)

        mock_clean.assert_called_once_with("Original text")
        mock_file.assert_called_once_with(Path.cwd() / "output.txt", "wt", encoding="utf-8")
        mock_file().write.assert_called_once_with("Cleaned text")
        logger.debug.assert_called_once()
        assert "Saved text file in:" in logger.debug.call_args[0][0]

    @patch("builtins.open", new_callable=mock_open)
    @patch("enchant_book_manager.file_handler.clean", side_effect=lambda x: x)
    def test_save_unicode_text(self, mock_clean, mock_file):
        """Test saving Unicode text."""
        text = "中文内容 with English"

        save_text_file(text, "unicode.txt")

        mock_file().write.assert_called_once_with(text)

    @patch("builtins.open", side_effect=OSError("Disk full"))
    def test_save_file_os_error(self, mock_file):
        """Test saving file with OS error."""
        logger = Mock()

        with pytest.raises(OSError, match="Disk full"):
            save_text_file("Text", "error.txt", logger)

        logger.error.assert_called_once()
        assert "Error saving file" in logger.error.call_args[0][0]

    @patch("builtins.open", side_effect=PermissionError("Write protected"))
    def test_save_file_permission_error(self, mock_file):
        """Test saving file with permission error."""
        logger = Mock()

        with pytest.raises(PermissionError, match="Write protected"):
            save_text_file("Text", "protected.txt", logger)

        logger.error.assert_called_once()

    @patch("builtins.open", new_callable=mock_open)
    @patch("enchant_book_manager.file_handler.clean", side_effect=lambda x: x)
    def test_save_file_with_path_object(self, mock_clean, mock_file):
        """Test saving file with Path object."""
        test_path = Path("output.txt")

        save_text_file("Text", test_path)

        mock_file.assert_called_once_with(Path.cwd() / test_path, "wt", encoding="utf-8")

    @patch("builtins.open", new_callable=mock_open)
    @patch("enchant_book_manager.file_handler.clean", side_effect=lambda x: x)
    def test_save_file_without_logger(self, mock_clean, mock_file):
        """Test saving file without logger."""
        save_text_file("Text", "output.txt")

        # Should not raise any errors
        mock_file().write.assert_called_once_with("Text")

    @patch("builtins.open", new_callable=mock_open)
    @patch("enchant_book_manager.file_handler.clean")
    def test_save_empty_text(self, mock_clean, mock_file):
        """Test saving empty text."""
        mock_clean.return_value = ""

        save_text_file("", "empty.txt")

        mock_file().write.assert_called_once_with("")


class TestDecodeInputFileContent:
    """Test the decode_input_file_content function."""

    @patch("enchant_book_manager.file_handler.ensure_synced")
    @patch("enchant_book_manager.file_handler.decode_full_file")
    def test_decode_file_content(self, mock_decode, mock_sync):
        """Test decoding file content."""
        input_path = Path("test.txt")
        synced_path = Path("synced/test.txt")
        mock_sync.return_value = synced_path
        mock_decode.return_value = "Decoded content"
        logger = Mock()

        result = decode_input_file_content(input_path, logger)

        assert result == "Decoded content"
        mock_sync.assert_called_once_with(input_path)
        mock_decode.assert_called_once_with(synced_path, logger=logger)

    @patch("enchant_book_manager.file_handler.ensure_synced", side_effect=lambda x: x)
    @patch("enchant_book_manager.file_handler.decode_full_file")
    def test_decode_file_no_sync_needed(self, mock_decode, mock_sync):
        """Test decoding when no sync is needed."""
        input_path = Path("local.txt")
        mock_decode.return_value = "Local content"

        result = decode_input_file_content(input_path)

        assert result == "Local content"
        mock_sync.assert_called_once_with(input_path)
        mock_decode.assert_called_once_with(input_path, logger=None)

    @patch("enchant_book_manager.file_handler.ensure_synced")
    @patch("enchant_book_manager.file_handler.decode_full_file", side_effect=Exception("Decode error"))
    def test_decode_file_error(self, mock_decode, mock_sync):
        """Test decoding file with error."""
        input_path = Path("error.txt")
        mock_sync.return_value = input_path

        with pytest.raises(Exception, match="Decode error"):
            decode_input_file_content(input_path)

    @patch("enchant_book_manager.file_handler.ensure_synced")
    @patch("enchant_book_manager.file_handler.decode_full_file")
    def test_decode_unicode_content(self, mock_decode, mock_sync):
        """Test decoding Unicode content."""
        input_path = Path("chinese.txt")
        mock_sync.return_value = input_path
        mock_decode.return_value = "中文内容"

        result = decode_input_file_content(input_path)

        assert result == "中文内容"


class TestDetectFileEncoding:
    """Test the detect_file_encoding function."""

    @patch("enchant_book_manager.file_handler.ensure_synced")
    @patch("enchant_book_manager.file_handler.common_detect_encoding")
    def test_detect_encoding(self, mock_detect, mock_sync):
        """Test detecting file encoding."""
        file_path = Path("test.txt")
        synced_path = Path("synced/test.txt")
        mock_sync.return_value = synced_path
        mock_detect.return_value = ("utf-8", 0.99)
        logger = Mock()

        result = detect_file_encoding(file_path, logger)

        assert result == "utf-8"
        mock_sync.assert_called_once_with(file_path)
        mock_detect.assert_called_once_with(synced_path, method="universal", logger=logger)

    @patch("enchant_book_manager.file_handler.ensure_synced", side_effect=lambda x: x)
    @patch("enchant_book_manager.file_handler.common_detect_encoding")
    def test_detect_encoding_gb18030(self, mock_detect, mock_sync):
        """Test detecting GB18030 encoding."""
        file_path = Path("chinese.txt")
        mock_detect.return_value = ("gb18030", 0.95)

        result = detect_file_encoding(file_path)

        assert result == "gb18030"

    @patch("enchant_book_manager.file_handler.ensure_synced")
    @patch("enchant_book_manager.file_handler.common_detect_encoding")
    def test_detect_encoding_with_confidence(self, mock_detect, mock_sync):
        """Test that confidence value is ignored."""
        file_path = Path("test.txt")
        mock_sync.return_value = file_path
        mock_detect.return_value = ("iso-8859-1", 0.5)  # Low confidence

        result = detect_file_encoding(file_path)

        assert result == "iso-8859-1"  # Still returns the encoding

    @patch("enchant_book_manager.file_handler.ensure_synced", side_effect=Exception("Sync error"))
    def test_detect_encoding_sync_error(self, mock_sync):
        """Test detecting encoding when sync fails."""
        file_path = Path("error.txt")

        with pytest.raises(Exception, match="Sync error"):
            detect_file_encoding(file_path)

    @patch("enchant_book_manager.file_handler.ensure_synced")
    @patch("enchant_book_manager.file_handler.common_detect_encoding", side_effect=Exception("Detection failed"))
    def test_detect_encoding_detection_error(self, mock_detect, mock_sync):
        """Test detecting encoding when detection fails."""
        file_path = Path("error.txt")
        mock_sync.return_value = file_path

        with pytest.raises(Exception, match="Detection failed"):
            detect_file_encoding(file_path)


class TestIntegration:
    """Integration tests for file handler functions."""

    def test_save_and_load_round_trip(self, tmp_path):
        """Test saving and loading a file."""
        test_file = tmp_path / "test.txt"
        original_text = "Test content\nWith multiple lines\n中文内容"

        # Mock clean to return the text as-is
        with patch("enchant_book_manager.file_handler.clean", side_effect=lambda x: x):
            # Save the file
            save_text_file(original_text, test_file)

        # Load it back
        with patch("enchant_book_manager.file_handler.Path.is_file", return_value=True):
            with patch("builtins.open", mock_open(read_data=original_text)):
                loaded_text = load_text_file(test_file)

        assert loaded_text == original_text

    @patch("enchant_book_manager.file_handler.ensure_synced", side_effect=lambda x: x)
    @patch("enchant_book_manager.file_handler.decode_full_file")
    @patch("enchant_book_manager.file_handler.common_detect_encoding")
    def test_detect_and_decode(self, mock_detect, mock_decode, mock_sync):
        """Test detecting encoding and then decoding."""
        file_path = Path("test.txt")
        mock_detect.return_value = ("gb18030", 0.99)
        mock_decode.return_value = "中文内容"

        # First detect encoding
        encoding = detect_file_encoding(file_path)
        assert encoding == "gb18030"

        # Then decode content
        content = decode_input_file_content(file_path)
        assert content == "中文内容"

        # Verify both functions were called with the same file
        assert mock_sync.call_count == 2
        mock_sync.assert_called_with(file_path)
