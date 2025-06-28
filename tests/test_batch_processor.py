#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test suite for batch_processor module.
"""

import pytest
import datetime as dt
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, mock_open
import logging
import yaml
import filelock

import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from enchant_book_manager.batch_processor import (
    load_safe_yaml,
    process_batch,
)


class TestLoadSafeYaml:
    """Test the load_safe_yaml function."""

    def test_load_valid_yaml(self, tmp_path):
        """Test loading valid YAML file."""
        yaml_file = tmp_path / "test.yaml"
        test_data = {"key": "value", "number": 42}
        yaml_file.write_text(yaml.dump(test_data))

        result = load_safe_yaml(yaml_file)
        assert result == test_data

    def test_load_empty_yaml(self, tmp_path):
        """Test loading empty YAML file."""
        yaml_file = tmp_path / "empty.yaml"
        yaml_file.write_text("")

        result = load_safe_yaml(yaml_file)
        assert result == {}

    def test_load_nonexistent_file(self, tmp_path):
        """Test loading non-existent file."""
        yaml_file = tmp_path / "nonexistent.yaml"

        result = load_safe_yaml(yaml_file)
        assert result is None

    def test_load_invalid_yaml(self, tmp_path):
        """Test loading invalid YAML file."""
        yaml_file = tmp_path / "invalid.yaml"
        yaml_file.write_text("{ invalid: yaml: content }")

        result = load_safe_yaml(yaml_file)
        assert result is None

    def test_load_with_logger(self, tmp_path):
        """Test loading with logger."""
        yaml_file = tmp_path / "test.yaml"
        yaml_file.write_text("key: value")
        logger = Mock(spec=logging.Logger)

        result = load_safe_yaml(yaml_file, logger)
        assert result == {"key": "value"}
        assert logger.error.call_count == 0


class TestProcessBatch:
    """Test the main process_batch function."""

    @patch("enchant_book_manager.batch_processor.filelock.FileLock")
    @patch("enchant_book_manager.batch_processor.save_translated_book")
    @patch("enchant_book_manager.batch_processor.import_book_from_txt")
    def test_process_batch_success(self, mock_import, mock_save, mock_filelock, tmp_path):
        """Test successful batch processing."""
        # Ensure progress file doesn't exist
        progress_file = Path("translation_batch_progress.yml")
        if progress_file.exists():
            progress_file.unlink()

        # Create test directory with files
        input_dir = tmp_path / "novels"
        input_dir.mkdir()
        file1 = input_dir / "book1.txt"
        file2 = input_dir / "book2.txt"
        file1.write_text("Chinese text 1")
        file2.write_text("Chinese text 2")

        mock_import.side_effect = ["book_id_1", "book_id_2"]
        mock_translator = Mock()
        mock_translator.is_remote = True
        mock_translator.request_count = 10
        mock_translator.MODEL_NAME = "gpt-4"
        mock_translator.format_cost_summary.return_value = "Cost: $0.10"

        logger = Mock(spec=logging.Logger)

        # Mock global_cost_tracker
        with patch("enchant_book_manager.batch_processor.global_cost_tracker") as mock_cost_tracker:
            mock_cost_tracker.get_summary.return_value = {"total_cost": 0.10, "total_tokens": 1000, "total_prompt_tokens": 500, "total_completion_tokens": 500}

            # Mock prepare_for_write to return the same path
            with patch("enchant_book_manager.batch_processor.prepare_for_write", side_effect=lambda x: x):
                process_batch(input_path=input_dir, translator=mock_translator, encoding="utf-8", max_chars=1000, resume=False, create_epub=False, logger=logger)

        assert mock_import.call_count == 2
        assert mock_save.call_count == 2

        # Check that cost summary was written
        cost_log = input_dir / "BATCH_AI_COSTS.log"
        assert cost_log.exists()

    @patch("enchant_book_manager.batch_processor.filelock.FileLock")
    @patch("enchant_book_manager.batch_processor.save_translated_book")
    @patch("enchant_book_manager.batch_processor.import_book_from_txt")
    def test_process_batch_with_failure(self, mock_import, mock_save, mock_filelock, tmp_path):
        """Test batch processing with some failures."""
        # Ensure progress file doesn't exist
        progress_file = Path("translation_batch_progress.yml")
        if progress_file.exists():
            progress_file.unlink()

        input_dir = tmp_path / "novels"
        input_dir.mkdir()
        file1 = input_dir / "book1.txt"
        file2 = input_dir / "book2.txt"
        file1.write_text("Chinese text 1")
        file2.write_text("Chinese text 2")

        mock_import.side_effect = ["book_id_1", Exception("Import failed")]
        mock_translator = Mock()
        mock_translator.is_remote = False  # Don't trigger cost summary
        logger = Mock(spec=logging.Logger)

        process_batch(input_path=input_dir, translator=mock_translator, encoding="utf-8", max_chars=1000, resume=False, create_epub=False, logger=logger)

        assert mock_import.call_count == 2
        assert mock_save.call_count == 1  # Only called for successful import

    @patch("enchant_book_manager.batch_processor.filelock.FileLock")
    @patch("enchant_book_manager.batch_processor.save_translated_book")
    @patch("enchant_book_manager.batch_processor.import_book_from_txt")
    def test_process_batch_resume(self, mock_import, mock_save, mock_filelock, tmp_path):
        """Test batch processing with resume."""
        input_dir = tmp_path / "novels"
        input_dir.mkdir()
        file1 = input_dir / "book1.txt"
        file2 = input_dir / "book2.txt"
        file1.write_text("Chinese text 1")
        file2.write_text("Chinese text 2")

        # Create a real progress file
        progress_file = Path("translation_batch_progress.yml")
        progress_data = {"created": "2024-01-01T00:00:00", "input_folder": str(input_dir), "files": [{"path": str(file1), "status": "completed", "end_time": "2024-01-01T01:00:00", "retry_count": 0}, {"path": str(file2), "status": "planned", "end_time": None, "retry_count": 0}]}
        with open(progress_file, "w") as f:
            yaml.safe_dump(progress_data, f)

        try:
            mock_import.return_value = "book_id_2"
            mock_translator = Mock()
            mock_translator.is_remote = False
            logger = Mock(spec=logging.Logger)

            process_batch(input_path=input_dir, translator=mock_translator, encoding="utf-8", max_chars=1000, resume=True, create_epub=False, logger=logger)

            # Should only process book2
            assert mock_import.call_count == 1
            assert str(file2) in str(mock_import.call_args)
        finally:
            # Clean up progress file
            if progress_file.exists():
                progress_file.unlink()

    def test_process_batch_invalid_directory(self, tmp_path):
        """Test batch processing with invalid directory."""
        non_existent_dir = tmp_path / "non_existent"
        mock_translator = Mock()
        logger = Mock(spec=logging.Logger)

        with pytest.raises(ValueError, match="Invalid batch directory"):
            process_batch(input_path=non_existent_dir, translator=mock_translator, logger=logger)

    def test_process_batch_empty_directory(self, tmp_path):
        """Test batch processing with empty directory."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        mock_translator = Mock()
        mock_translator.is_remote = False
        logger = Mock(spec=logging.Logger)

        with patch("enchant_book_manager.batch_processor.filelock.FileLock"):
            process_batch(input_path=empty_dir, translator=mock_translator, logger=logger)

        # Progress file should be created and removed
        progress_file = Path("translation_batch_progress.yml")
        assert not progress_file.exists()

    @patch("enchant_book_manager.batch_processor.filelock.FileLock")
    @patch("enchant_book_manager.batch_processor.save_translated_book")
    @patch("enchant_book_manager.batch_processor.import_book_from_txt")
    def test_process_batch_max_retries_exceeded(self, mock_import, mock_save, mock_filelock, tmp_path):
        """Test batch processing when max retries exceeded."""
        input_dir = tmp_path / "novels"
        input_dir.mkdir()

        # Create a real progress file with retry count at max
        progress_file = Path("translation_batch_progress.yml")
        progress_data = {"created": "2024-01-01T00:00:00", "input_folder": str(input_dir), "files": [{"path": str(input_dir / "book1.txt"), "status": "failed", "retry_count": 3, "end_time": None}]}
        with open(progress_file, "w") as f:
            yaml.safe_dump(progress_data, f)

        try:
            mock_translator = Mock()
            mock_translator.is_remote = False
            logger = Mock(spec=logging.Logger)

            process_batch(input_path=input_dir, translator=mock_translator, logger=logger)

            # Should not attempt to process the file
            assert mock_import.call_count == 0
            assert mock_save.call_count == 0
            logger.warning.assert_called_once()
        finally:
            # Clean up progress file
            if progress_file.exists():
                progress_file.unlink()

    @patch("enchant_book_manager.batch_processor.filelock.FileLock")
    @patch("enchant_book_manager.batch_processor.yaml.safe_dump")
    @patch("enchant_book_manager.batch_processor.save_translated_book")
    @patch("enchant_book_manager.batch_processor.import_book_from_txt")
    def test_process_batch_progress_save_error(self, mock_import, mock_save, mock_yaml_dump, mock_filelock, tmp_path):
        """Test batch processing when progress save fails."""
        input_dir = tmp_path / "novels"
        input_dir.mkdir()
        file1 = input_dir / "book1.txt"
        file1.write_text("Chinese text 1")

        mock_import.return_value = "book_id_1"
        mock_translator = Mock()
        mock_translator.is_remote = False
        logger = Mock(spec=logging.Logger)

        # Make yaml.safe_dump fail first time, then succeed
        mock_yaml_dump.side_effect = [yaml.YAMLError("Save failed"), None, None]

        with pytest.raises(yaml.YAMLError):
            process_batch(input_path=input_dir, translator=mock_translator, logger=logger)

    @patch("enchant_book_manager.batch_processor.filelock.FileLock")
    @patch("enchant_book_manager.batch_processor.save_translated_book")
    @patch("enchant_book_manager.batch_processor.import_book_from_txt")
    def test_process_batch_no_logger(self, mock_import, mock_save, mock_filelock, tmp_path):
        """Test batch processing without logger."""
        input_dir = tmp_path / "novels"
        input_dir.mkdir()
        file1 = input_dir / "book1.txt"
        file1.write_text("Chinese text 1")

        mock_import.return_value = "book_id_1"
        mock_translator = Mock()
        mock_translator.is_remote = False

        # Ensure progress file doesn't exist
        progress_file = Path("translation_batch_progress.yml")
        if progress_file.exists():
            progress_file.unlink()

        # Call without logger
        process_batch(input_path=input_dir, translator=mock_translator)

        assert mock_import.call_count == 1
        assert mock_save.call_count == 1

    @patch("enchant_book_manager.batch_processor.filelock.FileLock")
    @patch("enchant_book_manager.batch_processor.save_translated_book")
    @patch("enchant_book_manager.batch_processor.import_book_from_txt")
    def test_process_batch_cost_summary_error(self, mock_import, mock_save, mock_filelock, tmp_path):
        """Test batch processing when cost summary save fails."""
        input_dir = tmp_path / "novels"
        input_dir.mkdir()
        file1 = input_dir / "book1.txt"
        file1.write_text("Chinese text 1")

        mock_import.return_value = "book_id_1"
        mock_translator = Mock()
        mock_translator.is_remote = True
        mock_translator.request_count = 10
        mock_translator.MODEL_NAME = "gpt-4"
        mock_translator.format_cost_summary.return_value = "Cost: $0.10"

        logger = Mock(spec=logging.Logger)

        # Mock global_cost_tracker
        with patch("enchant_book_manager.batch_processor.global_cost_tracker") as mock_cost_tracker:
            mock_cost_tracker.get_summary.return_value = {"total_cost": 0.10, "total_tokens": 1000}

            # Mock prepare_for_write to return the same path
            with patch("enchant_book_manager.batch_processor.prepare_for_write", side_effect=lambda x: x):
                # Use a custom open that works normally until we try to write the cost log
                original_open = open
                open_call_count = 0

                def mock_open_func(path, *args, **kwargs):
                    nonlocal open_call_count
                    open_call_count += 1
                    # Let progress file writes succeed (first few calls)
                    if "BATCH_AI_COSTS.log" in str(path):
                        raise OSError("Cannot write cost log")
                    return original_open(path, *args, **kwargs)

                with patch("builtins.open", side_effect=mock_open_func):
                    process_batch(input_path=input_dir, translator=mock_translator, logger=logger)

        # Should log error but not raise exception
        assert any("Error saving batch cost log" in str(call) for call in logger.error.call_args_list)
        assert mock_import.call_count == 1
        assert mock_save.call_count == 1
