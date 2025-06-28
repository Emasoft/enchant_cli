#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test suite for common_file_utils module.
"""

import pytest
import tempfile
import shutil
import json
import yaml
import logging
from pathlib import Path
from unittest.mock import patch, Mock, MagicMock, mock_open
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from enchant_book_manager.common_file_utils import (
    detect_file_encoding,
    _detect_with_universal,
    _detect_with_chardet,
    decode_file_content,
    decode_full_file,
    decode_file_preview,
    safe_write_file,
)


class TestDetectFileEncoding:
    """Test the detect_file_encoding function."""

    def test_universal_method(self, tmp_path):
        """Test detection using universal detector method."""
        # Create a test file with UTF-8 content
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello 世界", encoding="utf-8")

        encoding, confidence = detect_file_encoding(test_file, method="universal")

        assert encoding == "utf-8"
        assert 0 <= confidence <= 1.0

    def test_chardet_method(self, tmp_path):
        """Test detection using chardet method."""
        # Create a test file with UTF-8 content
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello World! This is a test file with enough content.", encoding="utf-8")

        encoding, confidence = detect_file_encoding(test_file, method="chardet")

        assert encoding in ["utf-8", "ascii"]  # ASCII is subset of UTF-8
        assert 0 <= confidence <= 1.0

    def test_auto_method_high_confidence(self, tmp_path):
        """Test auto method with high confidence chardet result."""
        # Create a test file with distinctive UTF-8 content
        test_file = tmp_path / "test.txt"
        test_file.write_text("你好世界！这是一个测试文件。" * 100, encoding="utf-8")

        encoding, confidence = detect_file_encoding(test_file, method="auto", confidence_threshold=0.5)

        assert encoding == "utf-8"
        assert confidence > 0.5

    @patch("enchant_book_manager.common_file_utils._detect_with_chardet")
    @patch("enchant_book_manager.common_file_utils._detect_with_universal")
    def test_auto_method_low_confidence_fallback(self, mock_universal, mock_chardet, tmp_path):
        """Test auto method falling back to universal when chardet confidence is low."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test")

        # Mock chardet with low confidence
        mock_chardet.return_value = ("ascii", 0.3)
        # Mock universal with higher confidence
        mock_universal.return_value = ("utf-8", 0.9)

        encoding, confidence = detect_file_encoding(test_file, method="auto", confidence_threshold=0.7)

        assert encoding == "utf-8"
        assert confidence == 0.9
        mock_chardet.assert_called_once()
        mock_universal.assert_called_once()

    def test_invalid_method(self, tmp_path):
        """Test with invalid detection method."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test")

        with pytest.raises(ValueError, match="Unknown detection method"):
            detect_file_encoding(test_file, method="invalid")

    def test_with_custom_logger(self, tmp_path):
        """Test with custom logger."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test")

        mock_logger = Mock()
        encoding, confidence = detect_file_encoding(test_file, method="chardet", logger=mock_logger)

        # Should log debug messages
        mock_logger.debug.assert_called()


class TestDetectWithUniversal:
    """Test the _detect_with_universal function."""

    def test_successful_detection(self, tmp_path):
        """Test successful encoding detection."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello 世界", encoding="utf-8")

        logger = Mock()
        encoding, confidence = _detect_with_universal(test_file, logger)

        assert encoding == "utf-8"
        assert 0 <= confidence <= 1.0
        logger.debug.assert_called()

    def test_empty_file(self, tmp_path):
        """Test with empty file."""
        test_file = tmp_path / "empty.txt"
        test_file.write_text("")

        logger = Mock()
        encoding, confidence = _detect_with_universal(test_file, logger)

        assert encoding == "utf-8"  # Default fallback
        assert confidence >= 0

    def test_file_read_error(self, tmp_path):
        """Test error handling when file cannot be read."""
        test_file = tmp_path / "nonexistent.txt"

        logger = Mock()
        encoding, confidence = _detect_with_universal(test_file, logger)

        assert encoding == "utf-8"  # Default fallback
        assert confidence == 0.0
        logger.error.assert_called()


class TestDetectWithChardet:
    """Test the _detect_with_chardet function."""

    def test_successful_detection(self, tmp_path):
        """Test successful encoding detection."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello World! " * 100, encoding="utf-8")

        logger = Mock()
        encoding, confidence = _detect_with_chardet(test_file, None, logger)

        assert encoding in ["utf-8", "ascii"]
        assert 0 <= confidence <= 1.0
        logger.debug.assert_called()

    def test_custom_sample_size(self, tmp_path):
        """Test with custom sample size."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("x" * 100000, encoding="utf-8")  # 100KB file

        logger = Mock()
        encoding, confidence = _detect_with_chardet(test_file, 1024, logger)  # Read only 1KB

        assert encoding in ["utf-8", "ascii"]
        assert 0 <= confidence <= 1.0

    def test_file_read_error(self, tmp_path):
        """Test error handling when file cannot be read."""
        test_file = tmp_path / "nonexistent.txt"

        logger = Mock()
        encoding, confidence = _detect_with_chardet(test_file, None, logger)

        assert encoding == "utf-8"  # Default fallback
        assert confidence == 0.0
        logger.error.assert_called()


class TestDecodeFileContent:
    """Test the decode_file_content function."""

    def test_full_mode(self, tmp_path):
        """Test reading entire file."""
        test_file = tmp_path / "test.txt"
        content = "Hello 世界\n" * 100
        test_file.write_text(content, encoding="utf-8")

        result = decode_file_content(test_file, mode="full")

        assert result == content

    def test_preview_mode(self, tmp_path):
        """Test reading file preview."""
        test_file = tmp_path / "test.txt"
        content = "x" * 50000  # 50KB of content
        test_file.write_text(content, encoding="utf-8")

        result = decode_file_content(test_file, mode="preview", preview_kb=10)

        assert len(result) == 10240  # 10KB

    def test_minimum_file_size_check(self, tmp_path):
        """Test minimum file size checking."""
        test_file = tmp_path / "small.txt"
        test_file.write_text("small")

        # Should raise error when file is too small
        with pytest.raises(ValueError, match="File too small"):
            decode_file_content(test_file, min_file_size_kb=1, raise_on_error=True)

        # Should return None when raise_on_error=False
        result = decode_file_content(test_file, min_file_size_kb=1, raise_on_error=False)
        assert result is None

    def test_truncate_chars(self, tmp_path):
        """Test character truncation."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("x" * 1000, encoding="utf-8")

        result = decode_file_content(test_file, truncate_chars=100)

        assert len(result) == 100
        assert result == "x" * 100

    def test_fallback_encodings(self, tmp_path):
        """Test fallback encoding handling."""
        test_file = tmp_path / "test.txt"
        # Write with GBK encoding
        test_file.write_bytes("你好世界".encode("gbk"))

        # Should successfully decode using fallback
        result = decode_file_content(
            test_file,
            encoding_detector="chardet",
            confidence_threshold=0.99,  # Force fallback
            fallback_encodings=["gbk", "gb18030"],
        )

        assert result == "你好世界"

    def test_error_replacement(self, tmp_path):
        """Test decoding with error replacement."""
        test_file = tmp_path / "test.txt"
        # Write invalid UTF-8 bytes (not a valid sequence in any encoding)
        test_file.write_bytes(b"\x80\x81\x82 Hello \x83\x84\x85")

        result = decode_file_content(
            test_file,
            fallback_encodings=["utf-8"],  # Will fail and use replacement
            encoding_detector="chardet",  # Use chardet to avoid auto-detection
            confidence_threshold=0.99,  # Force fallback
        )

        assert "Hello" in result
        assert "�" in result or "\ufffd" in result  # Replacement character

    def test_nonexistent_file(self, tmp_path):
        """Test with nonexistent file."""
        test_file = tmp_path / "nonexistent.txt"

        # Should raise when raise_on_error=True
        with pytest.raises(Exception):
            decode_file_content(test_file, raise_on_error=True)

        # Should return None when raise_on_error=False
        result = decode_file_content(test_file, raise_on_error=False)
        assert result is None


class TestConvenienceFunctions:
    """Test the convenience wrapper functions."""

    def test_decode_full_file(self, tmp_path):
        """Test decode_full_file wrapper."""
        test_file = tmp_path / "test.txt"
        content = "Hello 世界"
        test_file.write_text(content, encoding="utf-8")

        result = decode_full_file(test_file)

        assert result == content

    def test_decode_full_file_empty(self, tmp_path):
        """Test decode_full_file with nonexistent file."""
        test_file = tmp_path / "nonexistent.txt"

        # Should raise exception
        with pytest.raises(Exception):
            decode_full_file(test_file)

    def test_decode_file_preview_success(self, tmp_path):
        """Test decode_file_preview wrapper."""
        test_file = tmp_path / "test.txt"
        content = "x" * 200000  # 200KB file
        test_file.write_text(content, encoding="utf-8")

        result = decode_file_preview(test_file, kb_to_read=10, max_chars=1000)

        assert result is not None
        assert len(result) == 1000

    def test_decode_file_preview_small_file(self, tmp_path):
        """Test decode_file_preview with file smaller than minimum."""
        test_file = tmp_path / "small.txt"
        test_file.write_text("small content")

        result = decode_file_preview(test_file, min_file_size_kb=1)

        assert result is None  # Too small

    def test_decode_file_preview_error(self, tmp_path):
        """Test decode_file_preview error handling."""
        test_file = tmp_path / "nonexistent.txt"

        result = decode_file_preview(test_file)

        assert result is None  # Returns None on error


class TestSafeWriteFile:
    """Test the safe_write_file function."""

    def test_write_text_file(self, tmp_path):
        """Test writing text content."""
        test_file = tmp_path / "output.txt"

        result = safe_write_file(test_file, "Hello World")

        assert result is True
        assert test_file.read_text() == "Hello World"

    def test_write_json_file(self, tmp_path):
        """Test writing JSON content."""
        test_file = tmp_path / "output.json"
        data = {"key": "value", "number": 42}

        result = safe_write_file(test_file, data, mode="json")

        assert result is True
        with open(test_file) as f:
            loaded = json.load(f)
        assert loaded == data

    def test_write_yaml_file(self, tmp_path):
        """Test writing YAML content."""
        test_file = tmp_path / "output.yaml"
        data = {"key": "value", "list": [1, 2, 3]}

        result = safe_write_file(test_file, data, mode="yaml")

        assert result is True
        with open(test_file) as f:
            loaded = yaml.safe_load(f)
        assert loaded == data

    def test_create_parent_directories(self, tmp_path):
        """Test creating parent directories."""
        test_file = tmp_path / "subdir" / "nested" / "file.txt"

        result = safe_write_file(test_file, "content")

        assert result is True
        assert test_file.exists()
        assert test_file.read_text() == "content"

    def test_backup_existing_file(self, tmp_path):
        """Test backing up existing file."""
        test_file = tmp_path / "file.txt"
        test_file.write_text("original")

        result = safe_write_file(test_file, "new content", backup=True)

        assert result is True
        assert test_file.read_text() == "new content"
        backup_file = test_file.with_suffix(".txt.bak")
        assert backup_file.exists()
        assert backup_file.read_text() == "original"

    def test_permission_error(self, tmp_path):
        """Test handling permission errors."""
        test_file = tmp_path / "readonly.txt"

        with patch("builtins.open", side_effect=PermissionError("No permission")):
            result = safe_write_file(test_file, "content")

        assert result is False

    def test_os_error(self, tmp_path):
        """Test handling OS errors."""
        test_file = tmp_path / "file.txt"

        with patch("builtins.open", side_effect=OSError("Disk full")):
            result = safe_write_file(test_file, "content")

        assert result is False

    def test_unexpected_error(self, tmp_path):
        """Test handling unexpected errors."""
        test_file = tmp_path / "file.txt"

        with patch("builtins.open", side_effect=RuntimeError("Unexpected")):
            result = safe_write_file(test_file, "content")

        assert result is False

    def test_with_custom_logger(self, tmp_path):
        """Test with custom logger."""
        test_file = tmp_path / "file.txt"
        mock_logger = Mock()

        result = safe_write_file(test_file, "content", logger=mock_logger)

        assert result is True
        mock_logger.debug.assert_called()

    def test_unicode_content(self, tmp_path):
        """Test writing Unicode content."""
        test_file = tmp_path / "unicode.txt"
        content = "Hello 世界 🌍"

        result = safe_write_file(test_file, content)

        assert result is True
        assert test_file.read_text(encoding="utf-8") == content

    def test_path_as_string(self, tmp_path):
        """Test with file path as string."""
        test_file = str(tmp_path / "file.txt")

        result = safe_write_file(test_file, "content")

        assert result is True
        assert Path(test_file).read_text() == "content"
