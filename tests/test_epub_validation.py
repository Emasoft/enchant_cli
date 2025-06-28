#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test suite for epub_validation module.
"""

import json
import os
import pytest
from datetime import datetime
from pathlib import Path
import sys
from unittest.mock import Mock, patch, mock_open, MagicMock
import tempfile

sys.path.insert(0, str(Path(__file__).parent.parent))

from enchant_book_manager.epub_validation import (
    ValidationError,
    _log_path,
    log_issue,
    set_json_log,
    ensure_dir_readable,
    ensure_output_ok,
    ensure_cover_ok,
    collect_chunks,
    _ERROR_LOG,
    _JSON_LOG,
)


class TestLogPath:
    """Test the _log_path function."""

    @patch("enchant_book_manager.epub_validation.Path.cwd")
    def test_log_path_generation(self, mock_cwd):
        """Test log path generation with timestamp."""
        mock_cwd.return_value = Path("/test/dir")

        # Actually call the function to get a real path
        result = _log_path()

        # Check it has the right prefix and suffix
        assert str(result).startswith("/test/dir/errors_")
        assert str(result).endswith(".log")

        # Check the timestamp format (YYYYMMDD_HHMMSS)
        filename = result.name
        timestamp_part = filename[7:-4]  # Remove "errors_" and ".log"
        assert len(timestamp_part) == 15  # YYYYMMDD_HHMMSS
        assert timestamp_part[8] == "_"  # Check underscore position


class TestLogIssue:
    """Test the log_issue function."""

    def setup_method(self):
        """Reset global log variables before each test."""
        # Save original values
        import enchant_book_manager.epub_validation as module

        self.original_error_log = module._ERROR_LOG
        self.original_json_log = module._JSON_LOG
        # Reset to None
        module._ERROR_LOG = None
        module._JSON_LOG = None

    def teardown_method(self):
        """Restore original values after each test."""
        import enchant_book_manager.epub_validation as module

        module._ERROR_LOG = self.original_error_log
        module._JSON_LOG = self.original_json_log

    @patch("enchant_book_manager.epub_validation._log_path")
    @patch("enchant_book_manager.epub_validation.Path.open", new_callable=mock_open)
    @patch("enchant_book_manager.epub_validation.datetime")
    def test_log_issue_first_call(self, mock_datetime, mock_file_open, mock_log_path):
        """Test logging issue on first call creates log file."""
        mock_log_path.return_value = Path("/test/errors.log")
        mock_datetime.now.return_value.isoformat.return_value = "2024-01-15T14:30:22"

        log_issue("Test error message")

        # Check log file was created
        mock_log_path.assert_called_once()

        # Check file was opened and written
        mock_file_open.assert_called_once_with("a", encoding="utf-8")
        handle = mock_file_open()
        handle.write.assert_called_once_with("[2024-01-15T14:30:22] Test error message\n")

    @patch("enchant_book_manager.epub_validation.Path.open", new_callable=mock_open)
    @patch("enchant_book_manager.epub_validation.datetime")
    def test_log_issue_existing_log(self, mock_datetime, mock_file_open):
        """Test logging to existing log file."""
        import enchant_book_manager.epub_validation as module

        module._ERROR_LOG = Path("/test/existing.log")
        mock_datetime.now.return_value.isoformat.return_value = "2024-01-15T14:35:00"

        log_issue("Another error")

        mock_file_open.assert_called_once_with("a", encoding="utf-8")
        handle = mock_file_open()
        handle.write.assert_called_once_with("[2024-01-15T14:35:00] Another error\n")

    @patch("enchant_book_manager.epub_validation.Path.open", new_callable=mock_open)
    def test_log_issue_with_json_object(self, mock_file_open):
        """Test logging with JSON object."""
        import enchant_book_manager.epub_validation as module

        module._ERROR_LOG = Path("/test/error.log")
        module._JSON_LOG = Path("/test/json.log")

        test_obj = {"error": "test", "code": 42}
        log_issue("Error with object", test_obj)

        # Should open both files
        assert mock_file_open.call_count == 2

        # Check JSON was written
        calls = mock_file_open().write.call_args_list
        json_written = False
        for call in calls:
            if call[0][0] == '{"error": "test", "code": 42}\n':
                json_written = True
                break
        assert json_written

    @patch("enchant_book_manager.epub_validation.Path.open", new_callable=mock_open)
    def test_log_issue_no_json_log(self, mock_file_open):
        """Test logging with object but no JSON log set."""
        import enchant_book_manager.epub_validation as module

        module._ERROR_LOG = Path("/test/error.log")
        module._JSON_LOG = None

        log_issue("Error", {"data": "test"})

        # Should only open error log, not JSON log
        assert mock_file_open.call_count == 1


class TestSetJsonLog:
    """Test the set_json_log function."""

    def test_set_json_log(self):
        """Test setting JSON log path."""
        import enchant_book_manager.epub_validation as module

        original = module._JSON_LOG

        test_path = Path("/test/json.log")
        set_json_log(test_path)

        assert module._JSON_LOG == test_path

        # Restore
        module._JSON_LOG = original


class TestValidationError:
    """Test the ValidationError exception."""

    def test_validation_error_is_exception(self):
        """Test that ValidationError is an Exception."""
        assert issubclass(ValidationError, Exception)

    def test_validation_error_creation(self):
        """Test creating ValidationError with message."""
        error = ValidationError("Test error")
        assert str(error) == "Test error"


class TestEnsureDirReadable:
    """Test the ensure_dir_readable function."""

    def test_valid_readable_directory(self):
        """Test with valid readable directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir)
            # Should not raise
            ensure_dir_readable(path)

    def test_nonexistent_directory(self):
        """Test with non-existent directory."""
        path = Path("/nonexistent/directory/path")
        with pytest.raises(ValidationError, match="not found or not a directory"):
            ensure_dir_readable(path)

    def test_file_not_directory(self):
        """Test with file instead of directory."""
        with tempfile.NamedTemporaryFile() as tmpfile:
            path = Path(tmpfile.name)
            with pytest.raises(ValidationError, match="not found or not a directory"):
                ensure_dir_readable(path)

    @patch("os.access")
    def test_no_read_permission(self, mock_access):
        """Test directory without read permission."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir)
            mock_access.return_value = False

            with pytest.raises(ValidationError, match="No read permission"):
                ensure_dir_readable(path)

    @patch("pathlib.Path.iterdir")
    def test_oserror_reading_directory(self, mock_iterdir):
        """Test OSError when reading directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir)
            mock_iterdir.side_effect = OSError("Permission denied")

            with pytest.raises(ValidationError, match="Cannot read directory"):
                ensure_dir_readable(path)


class TestEnsureOutputOk:
    """Test the ensure_output_ok function."""

    def test_append_mode_valid_epub(self):
        """Test append mode with valid EPUB file."""
        with tempfile.NamedTemporaryFile(suffix=".epub") as tmpfile:
            path = Path(tmpfile.name)
            # Should not raise
            ensure_output_ok(path, append=True)

    def test_append_mode_non_epub(self):
        """Test append mode with non-EPUB file."""
        path = Path("/test/file.txt")
        with pytest.raises(ValidationError, match="Cannot write EPUB"):
            ensure_output_ok(path, append=True)

    def test_append_mode_nonexistent_epub(self):
        """Test append mode with non-existent EPUB."""
        path = Path("/nonexistent/file.epub")
        with pytest.raises(ValidationError, match="Cannot write EPUB"):
            ensure_output_ok(path, append=True)

    @patch("os.access")
    def test_append_mode_no_write_permission(self, mock_access):
        """Test append mode without write permission."""
        with tempfile.NamedTemporaryFile(suffix=".epub") as tmpfile:
            path = Path(tmpfile.name)
            mock_access.return_value = False

            with pytest.raises(ValidationError, match="Cannot write EPUB"):
                ensure_output_ok(path, append=True)

    def test_create_mode_epub_in_writable_dir(self):
        """Test create mode with EPUB in writable directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test.epub"
            # Should not raise
            ensure_output_ok(path, append=False)

    def test_create_mode_directory_target(self):
        """Test create mode with directory as target."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "subdir"
            # Should create directory
            ensure_output_ok(path, append=False)
            assert path.exists()
            assert path.is_dir()

    @patch("pathlib.Path.mkdir")
    def test_create_mode_mkdir_error(self, mock_mkdir):
        """Test create mode with mkdir error."""
        mock_mkdir.side_effect = OSError("Permission denied")
        path = Path("/test/dir/file.epub")

        with pytest.raises(ValidationError, match="Cannot create directory"):
            ensure_output_ok(path, append=False)

    @patch("os.access")
    def test_create_mode_no_write_permission(self, mock_access):
        """Test create mode without write permission."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test.epub"
            mock_access.return_value = False

            with pytest.raises(ValidationError, match="No write permission"):
                ensure_output_ok(path, append=False)


class TestEnsureCoverOk:
    """Test the ensure_cover_ok function."""

    def test_valid_jpg_cover(self):
        """Test with valid JPG cover."""
        with tempfile.NamedTemporaryFile(suffix=".jpg") as tmpfile:
            path = Path(tmpfile.name)
            # Should not raise
            ensure_cover_ok(path)

    def test_valid_jpeg_cover(self):
        """Test with valid JPEG cover."""
        with tempfile.NamedTemporaryFile(suffix=".jpeg") as tmpfile:
            path = Path(tmpfile.name)
            # Should not raise
            ensure_cover_ok(path)

    def test_valid_png_cover(self):
        """Test with valid PNG cover."""
        with tempfile.NamedTemporaryFile(suffix=".png") as tmpfile:
            path = Path(tmpfile.name)
            # Should not raise
            ensure_cover_ok(path)

    def test_directory_not_file(self):
        """Test with directory instead of file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir)
            with pytest.raises(ValidationError, match="is not a file"):
                ensure_cover_ok(path)

    def test_invalid_extension(self):
        """Test with invalid file extension."""
        with tempfile.NamedTemporaryFile(suffix=".gif") as tmpfile:
            path = Path(tmpfile.name)
            with pytest.raises(ValidationError, match="must be .jpg/.jpeg/.png"):
                ensure_cover_ok(path)

    def test_case_insensitive_extension(self):
        """Test that extension check is case-insensitive."""
        with tempfile.NamedTemporaryFile(suffix=".JPG") as tmpfile:
            path = Path(tmpfile.name)
            # Should not raise
            ensure_cover_ok(path)

    @patch("os.access")
    def test_no_read_permission(self, mock_access):
        """Test cover without read permission."""
        with tempfile.NamedTemporaryFile(suffix=".jpg") as tmpfile:
            path = Path(tmpfile.name)
            mock_access.return_value = False

            with pytest.raises(ValidationError, match="No read permission"):
                ensure_cover_ok(path)


class TestCollectChunks:
    """Test the collect_chunks function."""

    @patch("enchant_book_manager.epub_validation.log_issue")
    def test_valid_chunks(self, mock_log):
        """Test collecting valid chapter chunks."""
        with tempfile.TemporaryDirectory() as tmpdir:
            folder = Path(tmpdir)

            # Create valid chapter files
            (folder / "Book Title by Author - Chapter 1.txt").write_text("Chapter 1 content")
            (folder / "Book Title by Author - Chapter 2.txt").write_text("Chapter 2 content")
            (folder / "Book Title by Author - Chapter 10.txt").write_text("Chapter 10 content")

            result = collect_chunks(folder)

            assert len(result) == 3
            assert 1 in result
            assert 2 in result
            assert 10 in result
            assert result[1].name == "Book Title by Author - Chapter 1.txt"

            # No issues should be logged
            mock_log.assert_not_called()

    def test_no_txt_files(self):
        """Test with directory containing no .txt files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            folder = Path(tmpdir)
            # Create non-txt files
            (folder / "file.pdf").write_text("pdf")

            with pytest.raises(ValidationError, match="No valid .txt chunks found"):
                collect_chunks(folder)

    def test_malformed_filenames(self):
        """Test with malformed filenames."""
        with tempfile.TemporaryDirectory() as tmpdir:
            folder = Path(tmpdir)

            # Create files with wrong format
            (folder / "Chapter1.txt").write_text("content")
            (folder / "Book - Chapter One.txt").write_text("content")
            (folder / "random.txt").write_text("content")

            with pytest.raises(ValidationError) as exc_info:
                collect_chunks(folder)

            assert "No valid .txt chunks found" in str(exc_info.value)
            assert "Issues:" in str(exc_info.value)
            assert "Malformed filename" in str(exc_info.value)

    @patch("enchant_book_manager.epub_validation.log_issue")
    def test_empty_files(self, mock_log):
        """Test with empty chapter files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            folder = Path(tmpdir)

            # Create empty file
            (folder / "Book by Author - Chapter 1.txt").write_text("")
            # Create valid file
            (folder / "Book by Author - Chapter 2.txt").write_text("content")

            result = collect_chunks(folder)

            assert len(result) == 1
            assert 2 in result
            assert 1 not in result

            # Empty file issue should be logged
            mock_log.assert_called_once()
            assert "Empty file" in mock_log.call_args[0][0]

    @patch("enchant_book_manager.epub_validation.log_issue")
    def test_broken_symlink(self, mock_log):
        """Test with broken symlink."""
        with tempfile.TemporaryDirectory() as tmpdir:
            folder = Path(tmpdir)

            # Create a target file that we'll delete
            target = folder / "target.txt"
            target.write_text("content")

            # Create symlink
            link = folder / "Book by Author - Chapter 1.txt"
            link.symlink_to(target)

            # Delete target to make symlink broken
            target.unlink()

            # Create valid file
            (folder / "Book by Author - Chapter 2.txt").write_text("content")

            result = collect_chunks(folder)

            # Should only have the valid file
            assert len(result) == 1
            assert 2 in result

            # Broken symlink should be logged
            mock_log.assert_called_once()
            assert "Broken symlink" in mock_log.call_args[0][0]

    @patch("enchant_book_manager.epub_validation.log_issue")
    def test_os_error_handling(self, mock_log):
        """Test handling of OS errors."""
        with tempfile.TemporaryDirectory() as tmpdir:
            folder = Path(tmpdir)

            # Create a file
            test_file = folder / "Book by Author - Chapter 1.txt"
            test_file.write_text("content")

            # Create another file that will work
            valid_file = folder / "Book by Author - Chapter 2.txt"
            valid_file.write_text("content")

            # Mock stat to raise OSError only for the first file
            original_stat = Path.stat

            def mock_stat(self, **kwargs):
                if self.name == "Book by Author - Chapter 1.txt":
                    raise OSError("Permission denied")
                return original_stat(self, **kwargs)

            with patch.object(Path, "stat", mock_stat):
                result = collect_chunks(folder)

                # Should have the valid file
                assert len(result) == 1
                assert 2 in result

                # OS error should be logged
                mock_log.assert_called_once()
                assert "OS error" in mock_log.call_args[0][0]

    @patch("enchant_book_manager.epub_validation.log_issue")
    def test_mixed_valid_invalid_files(self, mock_log):
        """Test with mix of valid and invalid files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            folder = Path(tmpdir)

            # Valid files
            (folder / "Book by Author - Chapter 1.txt").write_text("Chapter 1")
            (folder / "Book by Author - Chapter 3.txt").write_text("Chapter 3")

            # Invalid files
            (folder / "Book by Author - Chapter 2.txt").write_text("")  # Empty
            (folder / "random.txt").write_text("content")  # Malformed
            (folder / "Book - Chapter Four.txt").write_text("content")  # Non-numeric

            result = collect_chunks(folder)

            assert len(result) == 2
            assert 1 in result
            assert 3 in result

            # Issues should be logged
            assert mock_log.call_count == 3

    def test_issue_truncation_in_error_message(self):
        """Test that error message truncates issues list."""
        with tempfile.TemporaryDirectory() as tmpdir:
            folder = Path(tmpdir)

            # Create many invalid files
            for i in range(10):
                (folder / f"invalid_{i}.txt").write_text("content")

            with pytest.raises(ValidationError) as exc_info:
                collect_chunks(folder)

            error_msg = str(exc_info.value)
            assert "Issues:" in error_msg
            assert "... and 7 more" in error_msg  # Should show first 3 and count of rest
