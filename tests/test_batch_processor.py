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

    @patch("enchant_book_manager.batch_processor.save_translated_book")
    @patch("enchant_book_manager.batch_processor.import_book_from_txt")
    def test_process_batch_success(self, mock_import, mock_save, tmp_path):
        """Test successful batch processing."""
        # Create test files
        file1 = tmp_path / "book1.txt"
        file2 = tmp_path / "book2.txt"
        file1.write_text("Chinese text 1")
        file2.write_text("Chinese text 2")

        mock_import.side_effect = ["book_id_1", "book_id_2"]
        mock_translator = Mock()
        mock_config = {"text_processing": {"max_chars_per_chunk": 1000}}
        logger = Mock(spec=logging.Logger)

        result = process_batch(file_paths=[file1, file2], translator=mock_translator, encoding="utf-8", max_chars=1000, resume=False, create_epub=False, logger=logger, module_config=mock_config)

        assert result is True
        assert mock_import.call_count == 2
        assert mock_save.call_count == 2

    @patch("enchant_book_manager.batch_processor.save_translated_book")
    @patch("enchant_book_manager.batch_processor.import_book_from_txt")
    def test_process_batch_with_failure(self, mock_import, mock_save, tmp_path):
        """Test batch processing with some failures."""
        file1 = tmp_path / "book1.txt"
        file2 = tmp_path / "book2.txt"
        file1.write_text("Chinese text 1")
        file2.write_text("Chinese text 2")

        mock_import.side_effect = ["book_id_1", Exception("Import failed")]
        mock_translator = Mock()
        mock_config = {"text_processing": {"max_chars_per_chunk": 1000}}
        logger = Mock(spec=logging.Logger)

        result = process_batch(file_paths=[file1, file2], translator=mock_translator, encoding="utf-8", max_chars=1000, resume=False, create_epub=False, logger=logger, module_config=mock_config)

        # Should return True even with partial failures
        assert result is True
        assert mock_import.call_count == 2
        assert mock_save.call_count == 1  # Only called for successful import

    @patch("enchant_book_manager.batch_processor.load_batch_progress")
    def test_process_batch_resume(self, mock_load_progress, tmp_path):
        """Test batch processing with resume."""
        file1 = tmp_path / "book1.txt"
        file2 = tmp_path / "book2.txt"
        file1.write_text("Chinese text 1")
        file2.write_text("Chinese text 2")

        # Mock progress showing book1 is already completed
        mock_load_progress.return_value = {"books": {str(file1): {"status": "completed"}, str(file2): {"status": "pending"}}}

        mock_translator = Mock()
        mock_config = {"text_processing": {"max_chars_per_chunk": 1000}}
        logger = Mock(spec=logging.Logger)

        with patch("enchant_book_manager.batch_processor.import_book_from_txt") as mock_import:
            mock_import.return_value = "book_id_2"

            result = process_batch(file_paths=[file1, file2], translator=mock_translator, encoding="utf-8", max_chars=1000, resume=True, create_epub=False, logger=logger, module_config=mock_config)

            # Should only process book2
            assert mock_import.call_count == 1
            assert str(file2) in str(mock_import.call_args)
