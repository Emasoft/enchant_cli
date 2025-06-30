#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test suite for renamenovels module.
"""

import pytest
import logging
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, mock_open
import yaml
import sys
import concurrent.futures

sys.path.insert(0, str(Path(__file__).parent.parent))

from enchant_book_manager.renamenovels import (
    load_config,
    process_single_file,
    process_files,
    DEFAULT_KB_TO_READ,
    CONTENT_NUMBER_OF_CHARACTERS_HARD_LIMIT,
)


class TestLoadConfig:
    """Test the load_config function."""

    @patch("os.path.exists")
    @patch("builtins.open", new_callable=mock_open)
    @patch("enchant_book_manager.renamenovels.yaml.dump")
    def test_load_config_creates_default(self, mock_yaml_dump, mock_file, mock_exists):
        """Test creating default config when file doesn't exist."""
        # Config file doesn't exist
        mock_exists.return_value = False

        # Execute
        config = load_config()

        # Verify default config returned
        assert config["model"] == "gpt-4o-mini"
        assert config["temperature"] == 0.0
        assert config["kb_to_read"] == DEFAULT_KB_TO_READ
        assert config["api_key"] is None
        assert "max_workers" in config

        # Verify file was created
        mock_file.assert_called_once_with("renamenovels.conf.yml", "w")
        mock_yaml_dump.assert_called_once()

    @patch("os.path.exists")
    @patch("enchant_book_manager.renamenovels.load_safe_yaml")
    def test_load_config_reads_existing(self, mock_load_yaml, mock_exists):
        """Test loading existing config file."""
        # Config file exists
        mock_exists.return_value = True

        # Mock config content
        test_config = {
            "model": "gpt-4",
            "temperature": 0.5,
            "kb_to_read": 10,
            "max_workers": 4,
            "api_key": "test-key",
        }
        mock_load_yaml.return_value = test_config

        # Execute
        config = load_config()

        # Verify loaded config
        assert config == test_config
        mock_load_yaml.assert_called_once_with("renamenovels.conf.yml")

    @patch("os.path.exists")
    @patch("enchant_book_manager.renamenovels.load_safe_yaml")
    def test_load_config_empty_file(self, mock_load_yaml, mock_exists):
        """Test handling empty config file."""
        # Config file exists but is empty
        mock_exists.return_value = True
        mock_load_yaml.return_value = {}

        # Execute
        config = load_config()

        # Verify default config returned
        assert config["model"] == "gpt-4o-mini"
        assert config["temperature"] == 0.0

    @patch("os.path.exists")
    @patch("enchant_book_manager.renamenovels.load_safe_yaml")
    def test_load_config_yaml_error(self, mock_load_yaml, mock_exists):
        """Test handling YAML parsing error."""
        # Config file exists but has error
        mock_exists.return_value = True
        mock_load_yaml.side_effect = ValueError("Invalid YAML")

        # Execute
        config = load_config()

        # Verify default config returned
        assert config["model"] == "gpt-4o-mini"
        assert config["temperature"] == 0.0

    @patch("os.path.exists")
    @patch("builtins.open")
    @patch("enchant_book_manager.renamenovels.yaml.dump")
    def test_load_config_write_error(self, mock_yaml_dump, mock_file, mock_exists):
        """Test handling file write error when creating default."""
        # Config file doesn't exist
        mock_exists.return_value = False

        # Mock file write error
        mock_file.side_effect = IOError("Permission denied")

        # Execute
        config = load_config()

        # Verify default config still returned
        assert config["model"] == "gpt-4o-mini"


class TestProcessSingleFile:
    """Test the process_single_file function."""

    def setup_method(self):
        """Set up test fixtures."""
        self.file_path = Path("/test/novel.txt")
        self.kb_to_read = 5
        self.api_client = Mock()
        self.icloud_sync = Mock()

    @patch("enchant_book_manager.renamenovels.decode_file_content")
    @patch("enchant_book_manager.renamenovels.extract_json")
    @patch("enchant_book_manager.renamenovels.validate_metadata")
    @patch("enchant_book_manager.renamenovels.rename_file_with_metadata")
    def test_process_single_file_success(self, mock_rename, mock_validate, mock_extract, mock_decode):
        """Test successful file processing."""
        # Mock successful decode
        mock_decode.return_value = "Sample Chinese text content"

        # Mock successful API response
        self.api_client.extract_metadata.return_value = '{"title": "Test Title", "author": "Test Author"}'

        # Mock successful JSON extraction
        mock_extract.return_value = {"title": "Test Title", "author": "Test Author"}

        # Mock validation success
        mock_validate.return_value = True

        # Execute
        process_single_file(self.file_path, self.kb_to_read, self.api_client, self.icloud_sync)

        # Verify workflow
        mock_decode.assert_called_once_with(self.file_path, self.kb_to_read, self.icloud_sync)
        self.api_client.extract_metadata.assert_called_once_with("Sample Chinese text content", CONTENT_NUMBER_OF_CHARACTERS_HARD_LIMIT)
        mock_extract.assert_called_once_with('{"title": "Test Title", "author": "Test Author"}')
        mock_validate.assert_called_once_with({"title": "Test Title", "author": "Test Author"})
        mock_rename.assert_called_once_with(self.file_path, {"title": "Test Title", "author": "Test Author"})

    @patch("enchant_book_manager.renamenovels.decode_file_content")
    def test_process_single_file_decode_failure(self, mock_decode):
        """Test handling of decode failure."""
        # Mock decode failure
        mock_decode.return_value = None

        # Execute
        process_single_file(self.file_path, self.kb_to_read, self.api_client, self.icloud_sync)

        # Verify API not called
        self.api_client.extract_metadata.assert_not_called()

    @patch("enchant_book_manager.renamenovels.decode_file_content")
    def test_process_single_file_api_failure(self, mock_decode):
        """Test handling of API failure."""
        # Mock successful decode
        mock_decode.return_value = "Sample content"

        # Mock API failure
        self.api_client.extract_metadata.return_value = None

        # Execute
        process_single_file(self.file_path, self.kb_to_read, self.api_client, self.icloud_sync)

        # Verify process stops after API failure
        mock_decode.assert_called_once()
        self.api_client.extract_metadata.assert_called_once()

    @patch("enchant_book_manager.renamenovels.decode_file_content")
    @patch("enchant_book_manager.renamenovels.extract_json")
    def test_process_single_file_json_extraction_failure(self, mock_extract, mock_decode):
        """Test handling of JSON extraction failure."""
        # Mock successful decode and API
        mock_decode.return_value = "Sample content"
        self.api_client.extract_metadata.return_value = "Invalid JSON response"

        # Mock JSON extraction failure
        mock_extract.return_value = None

        # Execute
        process_single_file(self.file_path, self.kb_to_read, self.api_client, self.icloud_sync)

        # Verify process stops after extraction failure
        mock_extract.assert_called_once()

    @patch("enchant_book_manager.renamenovels.decode_file_content")
    @patch("enchant_book_manager.renamenovels.extract_json")
    @patch("enchant_book_manager.renamenovels.validate_metadata")
    def test_process_single_file_validation_failure(self, mock_validate, mock_extract, mock_decode):
        """Test handling of metadata validation failure."""
        # Mock successful decode, API, and extraction
        mock_decode.return_value = "Sample content"
        self.api_client.extract_metadata.return_value = '{"title": "Test"}'
        mock_extract.return_value = {"title": "Test"}  # Missing author

        # Mock validation failure
        mock_validate.return_value = False

        # Execute
        process_single_file(self.file_path, self.kb_to_read, self.api_client, self.icloud_sync)

        # Verify rename not called
        mock_validate.assert_called_once()

    @patch("enchant_book_manager.renamenovels.decode_file_content")
    @patch("enchant_book_manager.renamenovels.extract_json")
    @patch("enchant_book_manager.renamenovels.validate_metadata")
    @patch("enchant_book_manager.renamenovels.rename_file_with_metadata")
    def test_process_single_file_unexpected_error(self, mock_rename, mock_validate, mock_extract, mock_decode):
        """Test handling of unexpected errors."""
        # Mock successful initial steps
        mock_decode.return_value = "Sample content"
        self.api_client.extract_metadata.return_value = '{"title": "Test", "author": "Author"}'
        mock_extract.return_value = {"title": "Test", "author": "Author"}
        mock_validate.return_value = True

        # Mock rename raises exception
        mock_rename.side_effect = Exception("Unexpected error")

        # Execute - should not raise
        process_single_file(self.file_path, self.kb_to_read, self.api_client, self.icloud_sync)

        # Verify exception was caught
        mock_rename.assert_called_once()


class TestProcessFiles:
    """Test the process_files function."""

    def setup_method(self):
        """Set up test fixtures."""
        self.folder_path = Path("/test/novels")
        self.api_key = "test-api-key"
        self.model = "gpt-4o-mini"
        self.temperature = 0.0
        self.max_workers = 2
        self.icloud_sync = Mock()

    @patch("enchant_book_manager.renamenovels.find_text_files")
    @patch("enchant_book_manager.renamenovels.RenameAPIClient")
    @patch("enchant_book_manager.renamenovels.ThreadPoolExecutor")
    @patch("enchant_book_manager.renamenovels.process_single_file")
    def test_process_files_success(
        self,
        mock_process_single,
        mock_executor_class,
        mock_api_client_class,
        mock_find_files,
    ):
        """Test successful batch processing."""
        # Mock found files
        test_files = [Path("/test/file1.txt"), Path("/test/file2.txt")]
        mock_find_files.return_value = test_files

        # Mock API client
        mock_api_client = Mock()
        mock_api_client_class.return_value = mock_api_client

        # Mock executor
        mock_executor = MagicMock()
        mock_executor_class.return_value.__enter__.return_value = mock_executor

        # Mock futures
        mock_future1 = Mock()
        mock_future1.result.return_value = None
        mock_future2 = Mock()
        mock_future2.result.return_value = None
        mock_executor.submit.side_effect = [mock_future1, mock_future2]

        # Mock as_completed
        with patch("enchant_book_manager.renamenovels.concurrent.futures.as_completed") as mock_as_completed:
            mock_as_completed.return_value = [mock_future1, mock_future2]

            # Execute
            process_files(
                self.folder_path,
                recursive=True,
                kb_to_read=5,
                api_key=self.api_key,
                model=self.model,
                temperature=self.temperature,
                max_workers=self.max_workers,
                icloud_sync=self.icloud_sync,
            )

        # Verify
        mock_find_files.assert_called_once_with(self.folder_path, recursive=True)
        mock_api_client_class.assert_called_once_with(self.api_key, self.model, self.temperature)
        assert mock_executor.submit.call_count == 2

    @patch("enchant_book_manager.renamenovels.find_text_files")
    def test_process_files_no_files_found(self, mock_find_files):
        """Test handling when no files are found."""
        # No files found
        mock_find_files.return_value = []

        # Execute
        process_files(
            self.folder_path,
            recursive=False,
            kb_to_read=5,
            api_key=self.api_key,
            model=self.model,
            temperature=self.temperature,
            max_workers=self.max_workers,
            icloud_sync=self.icloud_sync,
        )

        # Verify early return
        mock_find_files.assert_called_once()

    @patch("enchant_book_manager.renamenovels.find_text_files")
    @patch("enchant_book_manager.renamenovels.RenameAPIClient")
    @patch("enchant_book_manager.renamenovels.ThreadPoolExecutor")
    def test_process_files_keyboard_interrupt(self, mock_executor_class, mock_api_client_class, mock_find_files):
        """Test handling of keyboard interrupt."""
        # Mock found files
        mock_find_files.return_value = [Path("/test/file1.txt")]

        # Mock API client
        mock_api_client_class.return_value = Mock()

        # Mock executor
        mock_executor = MagicMock()
        mock_executor_class.return_value.__enter__.return_value = mock_executor

        # Mock future that raises KeyboardInterrupt
        mock_future = Mock()
        mock_future.result.side_effect = KeyboardInterrupt()
        mock_executor.submit.return_value = mock_future

        # Mock as_completed
        with patch("enchant_book_manager.renamenovels.concurrent.futures.as_completed") as mock_as_completed:
            mock_as_completed.return_value = [mock_future]

            # Execute
            with pytest.raises(SystemExit) as exc_info:
                process_files(
                    self.folder_path,
                    recursive=True,
                    kb_to_read=5,
                    api_key=self.api_key,
                    model=self.model,
                    temperature=self.temperature,
                    max_workers=self.max_workers,
                    icloud_sync=self.icloud_sync,
                )

            assert exc_info.value.code == 1

        # Verify executor shutdown was called
        mock_executor.shutdown.assert_called_once_with(wait=False)

    @patch("enchant_book_manager.renamenovels.find_text_files")
    @patch("enchant_book_manager.renamenovels.RenameAPIClient")
    @patch("enchant_book_manager.renamenovels.ThreadPoolExecutor")
    @patch("enchant_book_manager.renamenovels.global_cost_tracker")
    def test_process_files_with_error(
        self,
        mock_cost_tracker,
        mock_executor_class,
        mock_api_client_class,
        mock_find_files,
    ):
        """Test handling of processing errors."""
        # Mock found files
        mock_find_files.return_value = [Path("/test/file1.txt")]

        # Mock API client
        mock_api_client_class.return_value = Mock()

        # Mock executor
        mock_executor = MagicMock()
        mock_executor_class.return_value.__enter__.return_value = mock_executor

        # Mock future that raises exception
        mock_future = Mock()
        mock_future.result.side_effect = Exception("Processing error")
        mock_executor.submit.return_value = mock_future

        # Mock cost tracker
        mock_cost_tracker.get_summary.return_value = {"total_cost": 0.123456}

        # Mock as_completed
        with patch("enchant_book_manager.renamenovels.concurrent.futures.as_completed") as mock_as_completed:
            mock_as_completed.return_value = [mock_future]

            # Execute - should handle error gracefully
            process_files(
                self.folder_path,
                recursive=True,
                kb_to_read=5,
                api_key=self.api_key,
                model=self.model,
                temperature=self.temperature,
                max_workers=self.max_workers,
                icloud_sync=self.icloud_sync,
            )

        # Verify cost summary still logged
        mock_cost_tracker.get_summary.assert_called_once()

    @patch("enchant_book_manager.renamenovels.find_text_files")
    @patch("enchant_book_manager.renamenovels.RenameAPIClient")
    @patch("enchant_book_manager.renamenovels.ThreadPoolExecutor")
    @patch("enchant_book_manager.renamenovels.global_cost_tracker")
    def test_process_files_cost_tracking(
        self,
        mock_cost_tracker,
        mock_executor_class,
        mock_api_client_class,
        mock_find_files,
    ):
        """Test cost tracking summary."""
        # Mock found files
        mock_find_files.return_value = [Path("/test/file1.txt")]

        # Mock API client
        mock_api_client_class.return_value = Mock()

        # Mock executor
        mock_executor = MagicMock()
        mock_executor_class.return_value.__enter__.return_value = mock_executor

        # Mock successful future
        mock_future = Mock()
        mock_future.result.return_value = None
        mock_executor.submit.return_value = mock_future

        # Mock cost tracker with non-zero cost
        mock_cost_tracker.get_summary.return_value = {"total_cost": 0.025000}

        # Mock as_completed
        with patch("enchant_book_manager.renamenovels.concurrent.futures.as_completed") as mock_as_completed:
            mock_as_completed.return_value = [mock_future]

            # Execute
            process_files(
                self.folder_path,
                recursive=False,
                kb_to_read=5,
                api_key=self.api_key,
                model=self.model,
                temperature=self.temperature,
                max_workers=1,
                icloud_sync=self.icloud_sync,
            )

        # Verify cost summary retrieved
        mock_cost_tracker.get_summary.assert_called_once()
