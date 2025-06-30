#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test suite for cli_batch_handler module.
"""

import pytest
import argparse
import datetime as dt
import logging
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, mock_open, call
import yaml
import filelock

import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from enchant_book_manager.cli_batch_handler import (
    process_batch,
    _save_batch_progress,
    _archive_batch_history,
    _cleanup_progress_file,
)


class TestProcessBatch:
    """Test the main process_batch function."""

    @patch("enchant_book_manager.cli_batch_handler.filelock.FileLock")
    @patch("enchant_book_manager.cli_batch_handler.process_novel_unified")
    @patch("enchant_book_manager.cli_batch_handler.load_safe_yaml")
    def test_process_batch_success(self, mock_load_yaml, mock_process_novel, mock_filelock, tmp_path):
        """Test successful batch processing."""
        # Setup test files
        test_dir = tmp_path / "test_novels"
        test_dir.mkdir()
        file1 = test_dir / "novel1.txt"
        file2 = test_dir / "novel2.txt"
        file1.write_text("Test content 1")
        file2.write_text("Test content 2")

        # Mock arguments
        args = Mock()
        args.filepath = str(test_dir)

        # Mock logger
        logger = Mock(spec=logging.Logger)

        # Mock yaml loading (no existing progress)
        mock_load_yaml.return_value = None

        # Mock successful processing
        mock_process_novel.return_value = True

        # Mock file lock
        mock_lock = MagicMock()
        mock_filelock.return_value = mock_lock

        with patch("enchant_book_manager.cli_batch_handler._save_batch_progress") as mock_save:
            with patch("enchant_book_manager.cli_batch_handler._archive_batch_history") as mock_archive:
                with patch("enchant_book_manager.cli_batch_handler._cleanup_progress_file") as mock_cleanup:
                    process_batch(args, logger)

        # Should process both files
        assert mock_process_novel.call_count == 2

        # Should save progress multiple times
        assert mock_save.call_count >= 2

        # Should archive and cleanup when done
        assert mock_archive.call_count == 1
        assert mock_cleanup.call_count == 1

    @patch("enchant_book_manager.cli_batch_handler.sys.exit")
    def test_process_batch_invalid_directory(self, mock_exit, tmp_path):
        """Test batch processing with invalid directory."""
        args = Mock()
        args.filepath = str(tmp_path / "nonexistent")
        logger = Mock(spec=logging.Logger)

        process_batch(args, logger)

        logger.error.assert_called_with("Batch processing requires an existing directory path.")
        mock_exit.assert_called_with(1)

    @patch("enchant_book_manager.cli_batch_handler.Path")
    @patch("enchant_book_manager.cli_batch_handler.filelock.FileLock")
    @patch("enchant_book_manager.cli_batch_handler.process_novel_unified")
    @patch("enchant_book_manager.cli_batch_handler.load_safe_yaml")
    def test_process_batch_resume(
        self,
        mock_load_yaml,
        mock_process_novel,
        mock_filelock,
        mock_path_class,
        tmp_path,
    ):
        """Test resuming batch processing."""
        # Setup test directory
        test_dir = tmp_path / "test_novels"
        test_dir.mkdir()
        file1 = test_dir / "novel1.txt"
        file2 = test_dir / "novel2.txt"
        file1.write_text("Test content 1")
        file2.write_text("Test content 2")

        # Mock existing progress (file1 already completed)
        existing_progress = {
            "created": "2024-01-01T10:00:00",
            "input_folder": str(test_dir),
            "files": [
                {
                    "path": str(file1.resolve()),
                    "status": "completed",
                    "end_time": "2024-01-01T10:30:00",
                    "retry_count": 0,
                },
                {
                    "path": str(file2.resolve()),
                    "status": "planned",
                    "end_time": None,
                    "retry_count": 0,
                },
            ],
        }

        args = Mock()
        args.filepath = str(test_dir)
        logger = Mock(spec=logging.Logger)

        # Setup Path mocks
        def path_side_effect(path_str):
            if path_str == args.filepath:
                return test_dir
            elif "translation_batch_progress.yml" in str(path_str):
                mock_progress_file = Mock()
                mock_progress_file.exists.return_value = True
                return mock_progress_file
            else:
                return Path(path_str)

        mock_path_class.side_effect = path_side_effect

        mock_load_yaml.return_value = existing_progress
        mock_process_novel.return_value = True

        with patch("enchant_book_manager.cli_batch_handler._save_batch_progress"):
            with patch("enchant_book_manager.cli_batch_handler._archive_batch_history"):
                with patch("enchant_book_manager.cli_batch_handler._cleanup_progress_file"):
                    process_batch(args, logger)

        # Should only process the second file
        assert mock_process_novel.call_count == 1
        mock_process_novel.assert_called_with(Path(str(file2.resolve())), args, logger)

    @patch("enchant_book_manager.cli_batch_handler.filelock.FileLock")
    @patch("enchant_book_manager.cli_batch_handler.process_novel_unified")
    @patch("enchant_book_manager.cli_batch_handler.load_safe_yaml")
    def test_process_batch_with_failures(self, mock_load_yaml, mock_process_novel, mock_filelock, tmp_path):
        """Test batch processing with some failures."""
        # Setup test directory
        test_dir = tmp_path / "test_novels"
        test_dir.mkdir()
        file1 = test_dir / "novel1.txt"
        file2 = test_dir / "novel2.txt"
        file1.write_text("Test content 1")
        file2.write_text("Test content 2")

        args = Mock()
        args.filepath = str(test_dir)
        logger = Mock(spec=logging.Logger)

        mock_load_yaml.return_value = None

        # First file fails, second succeeds
        mock_process_novel.side_effect = [False, True]

        with patch("enchant_book_manager.cli_batch_handler._save_batch_progress") as mock_save:
            with patch("enchant_book_manager.cli_batch_handler._archive_batch_history") as mock_archive:
                with patch("enchant_book_manager.cli_batch_handler._cleanup_progress_file") as mock_cleanup:
                    process_batch(args, logger)

        # Should process both files
        assert mock_process_novel.call_count == 2

        # Should still archive when done
        assert mock_archive.call_count == 1

    @patch("enchant_book_manager.cli_batch_handler.Path")
    @patch("enchant_book_manager.cli_batch_handler.filelock.FileLock")
    @patch("enchant_book_manager.cli_batch_handler.process_novel_unified")
    @patch("enchant_book_manager.cli_batch_handler.load_safe_yaml")
    def test_process_batch_max_retries(
        self,
        mock_load_yaml,
        mock_process_novel,
        mock_filelock,
        mock_path_class,
        tmp_path,
    ):
        """Test batch processing respects max retries."""
        test_dir = tmp_path / "test_novels"
        test_dir.mkdir()
        file1 = test_dir / "novel1.txt"
        file1.write_text("Test content 1")

        # Mock file with max retries reached
        existing_progress = {
            "created": "2024-01-01T10:00:00",
            "input_folder": str(test_dir),
            "files": [
                {
                    "path": str(file1.resolve()),
                    "status": "failed",
                    "end_time": None,
                    "retry_count": 3,  # Max retries reached
                }
            ],
        }

        args = Mock()
        args.filepath = str(test_dir)
        logger = Mock(spec=logging.Logger)

        # Setup Path mocks
        def path_side_effect(path_str):
            if path_str == args.filepath:
                return test_dir
            elif "translation_batch_progress.yml" in str(path_str):
                mock_progress_file = Mock()
                mock_progress_file.exists.return_value = True
                return mock_progress_file
            else:
                return Path(path_str)

        mock_path_class.side_effect = path_side_effect

        mock_load_yaml.return_value = existing_progress

        with patch("enchant_book_manager.cli_batch_handler._save_batch_progress"):
            with patch("enchant_book_manager.cli_batch_handler._archive_batch_history"):
                with patch("enchant_book_manager.cli_batch_handler._cleanup_progress_file"):
                    process_batch(args, logger)

        # Should not process the file
        mock_process_novel.assert_not_called()

        # Should log warning
        logger.warning.assert_called_with(f"Skipping {str(file1.resolve())} after 3 failed attempts.")

    @patch("enchant_book_manager.cli_batch_handler.filelock.FileLock")
    @patch("enchant_book_manager.cli_batch_handler.process_novel_unified")
    @patch("enchant_book_manager.cli_batch_handler.load_safe_yaml")
    def test_process_batch_exception_handling(self, mock_load_yaml, mock_process_novel, mock_filelock, tmp_path):
        """Test batch processing handles exceptions properly."""
        test_dir = tmp_path / "test_novels"
        test_dir.mkdir()
        file1 = test_dir / "novel1.txt"
        file1.write_text("Test content 1")

        args = Mock()
        args.filepath = str(test_dir)
        logger = Mock(spec=logging.Logger)

        mock_load_yaml.return_value = None

        # Raise exception during processing
        mock_process_novel.side_effect = Exception("Processing error")

        with patch("enchant_book_manager.cli_batch_handler._save_batch_progress") as mock_save:
            with patch("enchant_book_manager.cli_batch_handler._archive_batch_history"):
                with patch("enchant_book_manager.cli_batch_handler._cleanup_progress_file"):
                    process_batch(args, logger)

        # Should log error
        logger.error.assert_called()

        # Should still save progress
        assert mock_save.call_count >= 1


class TestSaveBatchProgress:
    """Test _save_batch_progress function."""

    def test_save_batch_progress_success(self, tmp_path):
        """Test successful progress save."""
        progress_file = tmp_path / "progress.yml"
        progress = {"status": "test", "files": [{"path": "test.txt"}]}
        logger = Mock(spec=logging.Logger)

        _save_batch_progress(progress_file, progress, logger)

        # Check file was written
        assert progress_file.exists()
        loaded = yaml.safe_load(progress_file.read_text())
        assert loaded == progress

    def test_save_batch_progress_yaml_error(self, tmp_path):
        """Test handling YAML error during save."""
        progress_file = tmp_path / "progress.yml"
        # Create object that can't be serialized to YAML
        progress = {"obj": object()}
        logger = Mock(spec=logging.Logger)

        with pytest.raises(Exception):
            _save_batch_progress(progress_file, progress, logger)

        logger.error.assert_called()

    def test_save_batch_progress_permission_error(self, tmp_path):
        """Test handling permission error during save."""
        progress_file = tmp_path / "readonly" / "progress.yml"
        progress_file.parent.mkdir()
        progress_file.parent.chmod(0o444)  # Read-only directory

        progress = {"status": "test"}
        logger = Mock(spec=logging.Logger)

        try:
            with pytest.raises(Exception):
                _save_batch_progress(progress_file, progress, logger)
            logger.error.assert_called()
        finally:
            # Restore permissions for cleanup
            progress_file.parent.chmod(0o755)


class TestArchiveBatchHistory:
    """Test _archive_batch_history function."""

    def test_archive_batch_history_success(self, tmp_path):
        """Test successful history archiving."""
        history_file = tmp_path / "history.yml"
        progress = {"status": "completed", "files": []}
        logger = Mock(spec=logging.Logger)

        _archive_batch_history(history_file, progress, logger)

        # Check file was written
        assert history_file.exists()
        content = history_file.read_text()
        assert "---\n" in content
        assert "status: completed" in content

    def test_archive_batch_history_append(self, tmp_path):
        """Test appending to existing history file."""
        history_file = tmp_path / "history.yml"
        history_file.write_text("---\nexisting: data\n")

        progress = {"status": "new"}
        logger = Mock(spec=logging.Logger)

        _archive_batch_history(history_file, progress, logger)

        content = history_file.read_text()
        assert content.count("---") == 2
        assert "existing: data" in content
        assert "status: new" in content

    def test_archive_batch_history_error(self, tmp_path):
        """Test error handling during archive."""
        history_file = tmp_path / "readonly" / "history.yml"
        history_file.parent.mkdir()
        history_file.parent.chmod(0o444)  # Read-only directory

        progress = {"status": "test"}
        logger = Mock(spec=logging.Logger)

        try:
            # Should not raise exception
            _archive_batch_history(history_file, progress, logger)
            logger.error.assert_called()
        finally:
            # Restore permissions
            history_file.parent.chmod(0o755)


class TestCleanupProgressFile:
    """Test _cleanup_progress_file function."""

    def test_cleanup_progress_file_success(self, tmp_path):
        """Test successful progress file cleanup."""
        progress_file = tmp_path / "progress.yml"
        progress_file.write_text("test data")
        logger = Mock(spec=logging.Logger)

        _cleanup_progress_file(progress_file, logger)

        # File should be deleted
        assert not progress_file.exists()

    def test_cleanup_progress_file_not_found(self, tmp_path):
        """Test cleanup when file doesn't exist."""
        progress_file = tmp_path / "nonexistent.yml"
        logger = Mock(spec=logging.Logger)

        # Should not raise exception
        _cleanup_progress_file(progress_file, logger)
        logger.error.assert_called()

    def test_cleanup_progress_file_permission_error(self, tmp_path):
        """Test cleanup with permission error."""
        progress_file = tmp_path / "progress.yml"
        progress_file.write_text("test")
        progress_file.chmod(0o444)  # Read-only
        progress_file.parent.chmod(0o555)  # Read-only directory

        logger = Mock(spec=logging.Logger)

        try:
            # Should not raise exception
            _cleanup_progress_file(progress_file, logger)
            logger.error.assert_called()
        finally:
            # Restore permissions
            progress_file.parent.chmod(0o755)
            progress_file.chmod(0o644)


class TestEdgeCases:
    """Test edge cases and special scenarios."""

    @patch("enchant_book_manager.cli_batch_handler.filelock.FileLock")
    @patch("enchant_book_manager.cli_batch_handler.load_safe_yaml")
    def test_empty_directory(self, mock_load_yaml, mock_filelock, tmp_path):
        """Test processing empty directory."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        args = Mock()
        args.filepath = str(empty_dir)
        logger = Mock(spec=logging.Logger)

        mock_load_yaml.return_value = None

        with patch("enchant_book_manager.cli_batch_handler._save_batch_progress"):
            with patch("enchant_book_manager.cli_batch_handler._archive_batch_history"):
                with patch("enchant_book_manager.cli_batch_handler._cleanup_progress_file"):
                    process_batch(args, logger)

        # Should handle empty directory gracefully
        logger.info.assert_not_called()

    @patch("enchant_book_manager.cli_batch_handler.filelock.FileLock")
    @patch("enchant_book_manager.cli_batch_handler.process_novel_unified")
    @patch("enchant_book_manager.cli_batch_handler.load_safe_yaml")
    @patch("enchant_book_manager.cli_batch_handler.dt.datetime")
    def test_timestamp_handling(self, mock_datetime, mock_load_yaml, mock_process_novel, mock_filelock, tmp_path):
        """Test proper timestamp handling."""
        test_dir = tmp_path / "test_novels"
        test_dir.mkdir()
        file1 = test_dir / "novel1.txt"
        file1.write_text("Test content")

        # Mock datetime
        mock_now = MagicMock()
        mock_now.isoformat.return_value = "2024-01-01T12:00:00"
        mock_datetime.now.return_value = mock_now

        args = Mock()
        args.filepath = str(test_dir)
        logger = Mock(spec=logging.Logger)

        mock_load_yaml.return_value = None
        mock_process_novel.return_value = True

        saved_progress = None

        def capture_progress(file, progress, logger):
            nonlocal saved_progress
            saved_progress = progress

        with patch(
            "enchant_book_manager.cli_batch_handler._save_batch_progress",
            side_effect=capture_progress,
        ):
            with patch("enchant_book_manager.cli_batch_handler._archive_batch_history"):
                with patch("enchant_book_manager.cli_batch_handler._cleanup_progress_file"):
                    process_batch(args, logger)

        # Check timestamps were set
        assert saved_progress["created"] == "2024-01-01T12:00:00"
        assert saved_progress["files"][0]["start_time"] == "2024-01-01T12:00:00"
        assert saved_progress["files"][0]["end_time"] == "2024-01-01T12:00:00"
