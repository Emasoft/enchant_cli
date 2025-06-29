#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test suite for workflow_progress module.
"""

import pytest
import yaml
import logging
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, mock_open
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from enchant_book_manager.workflow_progress import (
    load_safe_yaml_wrapper,
    save_progress,
    create_initial_progress,
    is_phase_completed,
    are_all_phases_completed,
    get_progress_file_path,
)


class TestLoadSafeYamlWrapper:
    """Test the load_safe_yaml_wrapper function."""

    def setup_method(self):
        """Set up test fixtures."""
        self.path = Path("/test/progress.yml")
        self.logger = logging.getLogger("test")

    @patch("enchant_book_manager.workflow_progress.load_safe_yaml")
    def test_successful_load(self, mock_load):
        """Test successful YAML loading."""
        expected_data = {"test": "data"}
        mock_load.return_value = expected_data

        result = load_safe_yaml_wrapper(self.path, self.logger)

        assert result == expected_data
        mock_load.assert_called_once_with(self.path)

    @patch("enchant_book_manager.workflow_progress.load_safe_yaml")
    def test_value_error(self, mock_load):
        """Test handling of ValueError from load_safe_yaml."""
        mock_load.side_effect = ValueError("Invalid YAML")

        result = load_safe_yaml_wrapper(self.path, self.logger)

        assert result is None
        mock_load.assert_called_once_with(self.path)

    @patch("enchant_book_manager.workflow_progress.load_safe_yaml")
    def test_unexpected_error(self, mock_load):
        """Test handling of unexpected exceptions."""
        mock_load.side_effect = Exception("Unexpected error")

        result = load_safe_yaml_wrapper(self.path, self.logger)

        assert result is None
        mock_load.assert_called_once_with(self.path)

    @patch("enchant_book_manager.workflow_progress.load_safe_yaml")
    def test_empty_result(self, mock_load):
        """Test handling of empty/None result."""
        mock_load.return_value = None

        result = load_safe_yaml_wrapper(self.path, self.logger)

        assert result is None

    @patch("enchant_book_manager.workflow_progress.load_safe_yaml")
    def test_complex_data(self, mock_load):
        """Test with complex nested data structure."""
        complex_data = {"phases": {"renaming": {"status": "completed", "result": "/path/to/renamed.txt"}, "translation": {"status": "in_progress", "chunks": 5}, "epub": {"status": "pending"}}, "metadata": {"version": "1.0"}}
        mock_load.return_value = complex_data

        result = load_safe_yaml_wrapper(self.path, self.logger)

        assert result == complex_data


class TestSaveProgress:
    """Test the save_progress function."""

    def setup_method(self):
        """Set up test fixtures."""
        self.progress_file = Path("/test/progress.yml")
        self.progress = {"original_file": "/test/novel.txt", "phases": {"renaming": {"status": "completed"}, "translation": {"status": "pending"}, "epub": {"status": "pending"}}}
        self.logger = logging.getLogger("test")

    def test_successful_save(self):
        """Test successful progress save."""
        mock_file = mock_open()

        with patch("pathlib.Path.open", mock_file):
            save_progress(self.progress_file, self.progress, self.logger)

        mock_file.assert_called_once_with("w")
        handle = mock_file()

        # Verify yaml.safe_dump was called with the file handle
        written_content = "".join(call.args[0] for call in handle.write.call_args_list)
        # Should contain our progress data
        assert "original_file" in written_content
        assert "renaming" in written_content
        assert "completed" in written_content

    def test_os_error(self):
        """Test handling of OSError during save."""
        with patch("pathlib.Path.open", side_effect=OSError("Permission denied")):
            # Should not raise exception
            save_progress(self.progress_file, self.progress, self.logger)

    def test_yaml_error(self):
        """Test handling of YAML error during save."""
        mock_file = mock_open()

        with patch("pathlib.Path.open", mock_file):
            with patch("yaml.safe_dump", side_effect=yaml.YAMLError("YAML error")):
                # Should not raise exception
                save_progress(self.progress_file, self.progress, self.logger)

    def test_empty_progress(self):
        """Test saving empty progress dictionary."""
        mock_file = mock_open()

        with patch("pathlib.Path.open", mock_file):
            save_progress(self.progress_file, {}, self.logger)

        mock_file.assert_called_once_with("w")

    def test_complex_progress(self):
        """Test saving complex progress structure."""
        complex_progress = {
            "original_file": "/test/novel.txt",
            "phases": {
                "renaming": {"status": "completed", "result": "/test/Novel by Author.txt", "metadata": {"title": "Novel", "author": "Author"}},
                "translation": {"status": "in_progress", "chunks_completed": 5, "total_chunks": 10},
                "epub": {"status": "failed", "error": "Chapter validation failed", "issues": ["Missing chapter 3", "Duplicate chapter 7"]},
            },
            "timestamp": "2024-01-01T12:00:00",
        }

        mock_file = mock_open()
        with patch("pathlib.Path.open", mock_file):
            save_progress(self.progress_file, complex_progress, self.logger)

        mock_file.assert_called_once_with("w")


class TestCreateInitialProgress:
    """Test the create_initial_progress function."""

    def test_basic_creation(self):
        """Test basic initial progress creation."""
        file_path = Path("/test/novel.txt")

        result = create_initial_progress(file_path)

        assert result["original_file"] == str(file_path)
        assert "phases" in result
        assert result["phases"]["renaming"]["status"] == "pending"
        assert result["phases"]["renaming"]["result"] is None
        assert result["phases"]["translation"]["status"] == "pending"
        assert result["phases"]["translation"]["result"] is None
        assert result["phases"]["epub"]["status"] == "pending"
        assert result["phases"]["epub"]["result"] is None

    def test_windows_path(self):
        """Test with Windows-style path."""
        file_path = Path("C:\\Users\\test\\novel.txt")

        result = create_initial_progress(file_path)

        # Path should be converted to string
        assert isinstance(result["original_file"], str)
        assert "novel.txt" in result["original_file"]

    def test_relative_path(self):
        """Test with relative path."""
        file_path = Path("./novels/test.txt")

        result = create_initial_progress(file_path)

        # Path normalization may remove leading ./
        assert result["original_file"] == str(file_path).replace("./", "")

    def test_path_with_unicode(self):
        """Test with Unicode characters in path."""
        file_path = Path("/test/中文小说.txt")

        result = create_initial_progress(file_path)

        assert result["original_file"] == str(file_path)

    def test_structure_integrity(self):
        """Test that the structure is complete and correct."""
        file_path = Path("/test/novel.txt")

        result = create_initial_progress(file_path)

        # Check all required keys exist
        assert set(result.keys()) == {"original_file", "phases"}
        assert set(result["phases"].keys()) == {"renaming", "translation", "epub"}

        # Check each phase has correct structure
        for phase_name in ["renaming", "translation", "epub"]:
            phase = result["phases"][phase_name]
            assert set(phase.keys()) == {"status", "result"}
            assert phase["status"] == "pending"
            assert phase["result"] is None


class TestIsPhaseCompleted:
    """Test the is_phase_completed function."""

    def test_completed_phase(self):
        """Test with completed phase."""
        progress = {"phases": {"renaming": {"status": "completed", "result": "/renamed.txt"}, "translation": {"status": "pending"}, "epub": {"status": "pending"}}}

        assert is_phase_completed(progress, "renaming") is True

    def test_pending_phase(self):
        """Test with pending phase."""
        progress = {"phases": {"renaming": {"status": "pending"}, "translation": {"status": "pending"}, "epub": {"status": "pending"}}}

        assert is_phase_completed(progress, "renaming") is False

    def test_skipped_phase(self):
        """Test with skipped phase."""
        progress = {"phases": {"renaming": {"status": "skipped"}, "translation": {"status": "pending"}, "epub": {"status": "pending"}}}

        assert is_phase_completed(progress, "renaming") is False

    def test_failed_phase(self):
        """Test with failed phase."""
        progress = {"phases": {"renaming": {"status": "failed", "error": "API error"}, "translation": {"status": "pending"}, "epub": {"status": "pending"}}}

        assert is_phase_completed(progress, "renaming") is False

    def test_missing_phase(self):
        """Test with missing phase."""
        progress = {
            "phases": {
                "renaming": {"status": "completed"}
                # translation and epub missing
            }
        }

        assert is_phase_completed(progress, "translation") is False

    def test_missing_phases_key(self):
        """Test with missing phases key."""
        progress = {"original_file": "/test.txt"}

        assert is_phase_completed(progress, "renaming") is False

    def test_missing_status(self):
        """Test with missing status."""
        progress = {
            "phases": {
                "renaming": {"result": "/renamed.txt"}  # No status
            }
        }

        assert is_phase_completed(progress, "renaming") is False

    def test_empty_status(self):
        """Test with empty status string."""
        progress = {"phases": {"renaming": {"status": ""}}}

        assert is_phase_completed(progress, "renaming") is False

    def test_all_phases(self):
        """Test checking all phase names."""
        progress = {"phases": {"renaming": {"status": "completed"}, "translation": {"status": "completed"}, "epub": {"status": "pending"}}}

        assert is_phase_completed(progress, "renaming") is True
        assert is_phase_completed(progress, "translation") is True
        assert is_phase_completed(progress, "epub") is False


class TestAreAllPhasesCompleted:
    """Test the are_all_phases_completed function."""

    def test_all_completed(self):
        """Test when all phases are completed."""
        progress = {"phases": {"renaming": {"status": "completed"}, "translation": {"status": "completed"}, "epub": {"status": "completed"}}}

        assert are_all_phases_completed(progress) is True

    def test_all_skipped(self):
        """Test when all phases are skipped."""
        progress = {"phases": {"renaming": {"status": "skipped"}, "translation": {"status": "skipped"}, "epub": {"status": "skipped"}}}

        assert are_all_phases_completed(progress) is True

    def test_mixed_completed_skipped(self):
        """Test with mix of completed and skipped."""
        progress = {"phases": {"renaming": {"status": "completed"}, "translation": {"status": "skipped"}, "epub": {"status": "completed"}}}

        assert are_all_phases_completed(progress) is True

    def test_one_pending(self):
        """Test when one phase is pending."""
        progress = {"phases": {"renaming": {"status": "completed"}, "translation": {"status": "completed"}, "epub": {"status": "pending"}}}

        assert are_all_phases_completed(progress) is False

    def test_one_failed(self):
        """Test when one phase failed."""
        progress = {"phases": {"renaming": {"status": "completed"}, "translation": {"status": "failed"}, "epub": {"status": "skipped"}}}

        assert are_all_phases_completed(progress) is False

    def test_empty_phases(self):
        """Test with empty phases dictionary."""
        progress = {"phases": {}}

        assert are_all_phases_completed(progress) is True

    def test_missing_phases_key(self):
        """Test with missing phases key."""
        progress = {"original_file": "/test.txt"}

        assert are_all_phases_completed(progress) is True

    def test_partial_phases(self):
        """Test with only some phases present."""
        progress = {
            "phases": {
                "renaming": {"status": "completed"},
                "translation": {"status": "completed"},
                # epub missing
            }
        }

        assert are_all_phases_completed(progress) is True

    def test_invalid_status(self):
        """Test with invalid status value."""
        progress = {"phases": {"renaming": {"status": "completed"}, "translation": {"status": "in_progress"}, "epub": {"status": "skipped"}}}

        assert are_all_phases_completed(progress) is False


class TestGetProgressFilePath:
    """Test the get_progress_file_path function."""

    def test_basic_path(self):
        """Test with basic file path."""
        file_path = Path("/test/novel.txt")

        result = get_progress_file_path(file_path)

        assert result == Path("/test/.novel_progress.yml")

    def test_path_with_multiple_dots(self):
        """Test with filename containing multiple dots."""
        file_path = Path("/test/my.novel.v2.txt")

        result = get_progress_file_path(file_path)

        # Should use stem (everything before last dot)
        assert result == Path("/test/.my.novel.v2_progress.yml")

    def test_path_without_extension(self):
        """Test with file without extension."""
        file_path = Path("/test/novel")

        result = get_progress_file_path(file_path)

        assert result == Path("/test/.novel_progress.yml")

    def test_windows_path(self):
        """Test with Windows-style path."""
        file_path = Path("C:\\Users\\test\\novel.txt")

        result = get_progress_file_path(file_path)

        # Should create hidden file in same directory
        # On non-Windows systems, the entire path becomes the filename
        if result.name == ".novel_progress.yml":
            # Running on Windows
            assert result.parent == file_path.parent
        else:
            # Running on Unix-like system where backslashes are part of filename
            assert "_progress.yml" in result.name

    def test_relative_path(self):
        """Test with relative path."""
        file_path = Path("novels/chinese/book.txt")

        result = get_progress_file_path(file_path)

        assert result == Path("novels/chinese/.book_progress.yml")

    def test_unicode_filename(self):
        """Test with Unicode filename."""
        file_path = Path("/test/中文小说.txt")

        result = get_progress_file_path(file_path)

        assert result == Path("/test/.中文小说_progress.yml")

    def test_hidden_file_input(self):
        """Test with already hidden file."""
        file_path = Path("/test/.hidden_novel.txt")

        result = get_progress_file_path(file_path)

        # Should still add dot prefix
        assert result == Path("/test/..hidden_novel_progress.yml")

    def test_root_directory(self):
        """Test with file in root directory."""
        file_path = Path("/novel.txt")

        result = get_progress_file_path(file_path)

        assert result == Path("/.novel_progress.yml")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
