#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Tests for file validation utilities."""

import tempfile
from pathlib import Path
import pytest

from enchant_book_manager.common_file_utils import check_file_exists, validate_file_size


class TestCheckFileExists:
    """Test the check_file_exists function."""

    def test_file_exists_and_is_file(self):
        """Test checking an existing file."""
        with tempfile.NamedTemporaryFile() as tf:
            path = Path(tf.name)
            assert check_file_exists(path, file_type="file", raise_on_missing=False)

    def test_dir_exists_and_is_dir(self):
        """Test checking an existing directory."""
        with tempfile.TemporaryDirectory() as td:
            path = Path(td)
            assert check_file_exists(path, file_type="dir", raise_on_missing=False)

    def test_file_not_exists_no_raise(self):
        """Test checking non-existent file without raising."""
        path = Path("/nonexistent/file.txt")
        assert not check_file_exists(path, file_type="file", raise_on_missing=False)

    def test_file_not_exists_with_raise(self):
        """Test checking non-existent file with raising."""
        path = Path("/nonexistent/file.txt")
        with pytest.raises(FileNotFoundError, match="Path not found"):
            check_file_exists(path, file_type="file", raise_on_missing=True)

    def test_wrong_type_file_expected_dir(self):
        """Test file when directory expected."""
        with tempfile.NamedTemporaryFile() as tf:
            path = Path(tf.name)
            assert not check_file_exists(path, file_type="dir", raise_on_missing=False)

    def test_wrong_type_dir_expected_file(self):
        """Test directory when file expected."""
        with tempfile.TemporaryDirectory() as td:
            path = Path(td)
            assert not check_file_exists(path, file_type="file", raise_on_missing=False)

    def test_custom_error_message(self):
        """Test custom error message."""
        path = Path("/nonexistent/file.txt")
        custom_msg = "Custom error: file missing"
        with pytest.raises(FileNotFoundError, match=custom_msg):
            check_file_exists(path, error_message=custom_msg)

    def test_any_type(self):
        """Test 'any' file type accepts both files and directories."""
        with tempfile.NamedTemporaryFile() as tf:
            assert check_file_exists(tf.name, file_type="any")

        with tempfile.TemporaryDirectory() as td:
            assert check_file_exists(td, file_type="any")


class TestValidateFileSize:
    """Test the validate_file_size function."""

    def test_valid_file_size(self):
        """Test file within size bounds."""
        with tempfile.NamedTemporaryFile() as tf:
            tf.write(b"x" * 100)
            tf.flush()

            assert validate_file_size(tf.name, min_size=50, max_size=200)

    def test_file_too_small(self):
        """Test file below minimum size."""
        with tempfile.NamedTemporaryFile() as tf:
            tf.write(b"x" * 10)
            tf.flush()

            assert not validate_file_size(tf.name, min_size=50)

    def test_file_too_large(self):
        """Test file above maximum size."""
        with tempfile.NamedTemporaryFile() as tf:
            tf.write(b"x" * 1000)
            tf.flush()

            assert not validate_file_size(tf.name, max_size=500)

    def test_no_size_limits(self):
        """Test with no size limits specified."""
        with tempfile.NamedTemporaryFile() as tf:
            tf.write(b"x" * 100)
            tf.flush()

            assert validate_file_size(tf.name)

    def test_file_not_found(self):
        """Test non-existent file."""
        with pytest.raises(FileNotFoundError):
            validate_file_size("/nonexistent/file.txt")

    def test_path_is_directory(self):
        """Test path that is a directory."""
        with tempfile.TemporaryDirectory() as td:
            with pytest.raises(ValueError, match="Path is not a file"):
                validate_file_size(td)

    def test_exact_size_boundaries(self):
        """Test files at exact size boundaries."""
        with tempfile.NamedTemporaryFile() as tf:
            # Exactly at minimum
            tf.write(b"x" * 100)
            tf.flush()
            assert validate_file_size(tf.name, min_size=100)

            # Exactly at maximum
            assert validate_file_size(tf.name, max_size=100)
