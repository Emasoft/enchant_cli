#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test suite for workflow_orchestrator module.
"""

import pytest
import logging
import argparse
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call
import yaml

import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from enchant_book_manager.workflow_orchestrator import process_novel_unified


class TestProcessNovelUnified:
    """Test the process_novel_unified function."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create mock args
        self.args = Mock(spec=argparse.Namespace)
        self.args.resume = False
        self.args.skip_renaming = False
        self.args.skip_translating = False
        self.args.skip_epub = False
        self.args.translated = None

        # Create mock logger
        self.logger = Mock(spec=logging.Logger)

        # Create test file path
        self.file_path = Path("/test/novel.txt")

    @patch("enchant_book_manager.workflow_orchestrator.get_progress_file_path")
    @patch("enchant_book_manager.workflow_orchestrator.create_initial_progress")
    @patch("enchant_book_manager.workflow_orchestrator.process_renaming_phase")
    @patch("enchant_book_manager.workflow_orchestrator.process_translation_phase")
    @patch("enchant_book_manager.workflow_orchestrator.process_epub_phase")
    def test_process_novel_all_phases_success(
        self,
        mock_epub,
        mock_translation,
        mock_renaming,
        mock_create_progress,
        mock_get_progress_path,
    ):
        """Test successful processing through all phases."""
        # Mock progress file path
        mock_progress_file = MagicMock()
        mock_progress_file.exists.return_value = False
        mock_get_progress_path.return_value = mock_progress_file

        # Mock initial progress
        initial_progress = {
            "phases": {
                "renaming": {"status": "pending", "result": None},
                "translation": {"status": "pending", "result": None},
                "epub": {"status": "pending", "result": None},
            }
        }
        mock_create_progress.return_value = initial_progress

        # Mock phase results - simulate successful completion
        renamed_path = Path("/test/renamed_novel.txt")
        mock_renaming.return_value = renamed_path

        # Run the function
        result = process_novel_unified(self.file_path, self.args, self.logger)

        # Verify all phases were called
        mock_renaming.assert_called_once_with(
            self.file_path,
            self.file_path,
            self.args,
            initial_progress,
            mock_progress_file,
            self.logger,
        )
        mock_translation.assert_called_once_with(renamed_path, self.args, initial_progress, mock_progress_file, self.logger)
        mock_epub.assert_called_once_with(renamed_path, self.args, initial_progress, mock_progress_file, self.logger)

        # Since we didn't simulate the phases updating progress, result should be False
        assert result is False  # All phases still pending in our mock

    @patch("enchant_book_manager.workflow_orchestrator.get_progress_file_path")
    @patch("enchant_book_manager.workflow_orchestrator.load_safe_yaml_wrapper")
    @patch("enchant_book_manager.workflow_orchestrator.create_initial_progress")
    @patch("enchant_book_manager.workflow_orchestrator.process_renaming_phase")
    @patch("enchant_book_manager.workflow_orchestrator.process_translation_phase")
    @patch("enchant_book_manager.workflow_orchestrator.process_epub_phase")
    def test_process_novel_resume_mode(
        self,
        mock_epub,
        mock_translation,
        mock_renaming,
        mock_create_progress,
        mock_load_yaml,
        mock_get_progress_path,
    ):
        """Test resuming from existing progress."""
        # Enable resume mode
        self.args.resume = True

        # Mock progress file exists
        mock_progress_file = MagicMock()
        mock_progress_file.exists.return_value = True
        mock_get_progress_path.return_value = mock_progress_file

        # Mock existing progress - renaming already completed
        renamed_path = "/test/renamed_novel.txt"
        existing_progress = {
            "phases": {
                "renaming": {"status": "completed", "result": renamed_path},
                "translation": {"status": "pending", "result": None},
                "epub": {"status": "pending", "result": None},
            }
        }
        mock_load_yaml.return_value = existing_progress

        # Mock renamed file exists
        with patch("enchant_book_manager.workflow_orchestrator.Path") as mock_path_class:
            mock_renamed_path = MagicMock()
            mock_renamed_path.exists.return_value = True
            mock_renamed_path.name = "renamed_novel.txt"
            mock_path_class.return_value = mock_renamed_path

            # Mock phase results
            mock_renaming.return_value = mock_renamed_path

            # Run the function
            result = process_novel_unified(self.file_path, self.args, self.logger)

            # Verify progress was loaded
            mock_load_yaml.assert_called_once_with(mock_progress_file, self.logger)

            # Verify logger info about resuming
            self.logger.info.assert_any_call("Resuming with renamed file: renamed_novel.txt")

    @patch("enchant_book_manager.workflow_orchestrator.get_progress_file_path")
    @patch("enchant_book_manager.workflow_orchestrator.create_initial_progress")
    @patch("enchant_book_manager.workflow_orchestrator.process_renaming_phase")
    @patch("enchant_book_manager.workflow_orchestrator.process_translation_phase")
    @patch("enchant_book_manager.workflow_orchestrator.process_epub_phase")
    def test_process_novel_skip_renaming(
        self,
        mock_epub,
        mock_translation,
        mock_renaming,
        mock_create_progress,
        mock_get_progress_path,
    ):
        """Test skipping the renaming phase."""
        # Skip renaming
        self.args.skip_renaming = True

        # Mock progress file path
        mock_progress_file = MagicMock()
        mock_progress_file.exists.return_value = False
        mock_get_progress_path.return_value = mock_progress_file

        # Mock initial progress
        initial_progress = {
            "phases": {
                "renaming": {"status": "pending", "result": None},
                "translation": {"status": "pending", "result": None},
                "epub": {"status": "pending", "result": None},
            }
        }
        mock_create_progress.return_value = initial_progress

        # Mock renaming returns original path (no renaming)
        mock_renaming.return_value = self.file_path

        # Run the function
        result = process_novel_unified(self.file_path, self.args, self.logger)

        # Verify renaming was called but should have skipped internally
        mock_renaming.assert_called_once()

        # Translation and epub should use original path
        mock_translation.assert_called_once_with(self.file_path, self.args, initial_progress, mock_progress_file, self.logger)

    @patch("enchant_book_manager.workflow_orchestrator.get_progress_file_path")
    @patch("enchant_book_manager.workflow_orchestrator.create_initial_progress")
    @patch("enchant_book_manager.workflow_orchestrator.process_renaming_phase")
    @patch("enchant_book_manager.workflow_orchestrator.process_translation_phase")
    @patch("enchant_book_manager.workflow_orchestrator.process_epub_phase")
    def test_process_novel_all_phases_completed_cleanup(
        self,
        mock_epub,
        mock_translation,
        mock_renaming,
        mock_create_progress,
        mock_get_progress_path,
    ):
        """Test progress file cleanup when all phases complete."""
        # Mock progress file path
        mock_progress_file = MagicMock()
        mock_progress_file.exists.return_value = True
        mock_get_progress_path.return_value = mock_progress_file

        # Mock initial progress that will be updated to completed
        progress = {
            "phases": {
                "renaming": {"status": "completed", "result": "/test/renamed.txt"},
                "translation": {
                    "status": "completed",
                    "result": "/test/translated.txt",
                },
                "epub": {"status": "completed", "result": "/test/book.epub"},
            }
        }
        mock_create_progress.return_value = progress

        # Mock phase results
        mock_renaming.return_value = Path("/test/renamed.txt")

        # Run the function
        result = process_novel_unified(self.file_path, self.args, self.logger)

        # Verify cleanup was attempted
        mock_progress_file.unlink.assert_called_once()
        self.logger.info.assert_any_call("All phases completed, removed progress file")

        # Result should be True since all phases are completed
        assert result is True

    @patch("enchant_book_manager.workflow_orchestrator.get_progress_file_path")
    @patch("enchant_book_manager.workflow_orchestrator.create_initial_progress")
    @patch("enchant_book_manager.workflow_orchestrator.process_renaming_phase")
    @patch("enchant_book_manager.workflow_orchestrator.process_translation_phase")
    @patch("enchant_book_manager.workflow_orchestrator.process_epub_phase")
    def test_process_novel_cleanup_permission_error(
        self,
        mock_epub,
        mock_translation,
        mock_renaming,
        mock_create_progress,
        mock_get_progress_path,
    ):
        """Test handling permission error during progress file cleanup."""
        # Mock progress file path
        mock_progress_file = MagicMock()
        mock_progress_file.exists.return_value = True
        mock_progress_file.unlink.side_effect = PermissionError("Access denied")
        mock_get_progress_path.return_value = mock_progress_file

        # Mock progress with all phases completed
        progress = {
            "phases": {
                "renaming": {"status": "completed", "result": "/test/renamed.txt"},
                "translation": {
                    "status": "completed",
                    "result": "/test/translated.txt",
                },
                "epub": {"status": "completed", "result": "/test/book.epub"},
            }
        }
        mock_create_progress.return_value = progress

        # Mock phase results
        mock_renaming.return_value = Path("/test/renamed.txt")

        # Run the function
        result = process_novel_unified(self.file_path, self.args, self.logger)

        # Verify warning was logged
        self.logger.warning.assert_called_with("Could not remove progress file: Access denied")

        # Result should still be True
        assert result is True

    @patch("enchant_book_manager.workflow_orchestrator.get_progress_file_path")
    @patch("enchant_book_manager.workflow_orchestrator.create_initial_progress")
    @patch("enchant_book_manager.workflow_orchestrator.process_renaming_phase")
    @patch("enchant_book_manager.workflow_orchestrator.process_translation_phase")
    @patch("enchant_book_manager.workflow_orchestrator.process_epub_phase")
    def test_process_novel_mixed_status(
        self,
        mock_epub,
        mock_translation,
        mock_renaming,
        mock_create_progress,
        mock_get_progress_path,
    ):
        """Test with mixed phase statuses (some completed, some skipped)."""
        # Mock progress file path
        mock_progress_file = MagicMock()
        mock_progress_file.exists.return_value = False
        mock_get_progress_path.return_value = mock_progress_file

        # Mock progress with mixed statuses
        progress = {
            "phases": {
                "renaming": {"status": "skipped", "result": None},
                "translation": {
                    "status": "completed",
                    "result": "/test/translated.txt",
                },
                "epub": {"status": "skipped", "result": None},
            }
        }
        mock_create_progress.return_value = progress

        # Mock phase results
        mock_renaming.return_value = self.file_path

        # Run the function
        result = process_novel_unified(self.file_path, self.args, self.logger)

        # Result should be True since all are either completed or skipped
        assert result is True

    @patch("enchant_book_manager.workflow_orchestrator.get_progress_file_path")
    @patch("enchant_book_manager.workflow_orchestrator.load_safe_yaml_wrapper")
    @patch("enchant_book_manager.workflow_orchestrator.create_initial_progress")
    @patch("enchant_book_manager.workflow_orchestrator.process_renaming_phase")
    @patch("enchant_book_manager.workflow_orchestrator.process_translation_phase")
    @patch("enchant_book_manager.workflow_orchestrator.process_epub_phase")
    def test_process_novel_resume_renamed_file_missing(
        self,
        mock_epub,
        mock_translation,
        mock_renaming,
        mock_create_progress,
        mock_load_yaml,
        mock_get_progress_path,
    ):
        """Test resuming when renamed file no longer exists."""
        # Enable resume mode
        self.args.resume = True

        # Mock progress file exists
        mock_progress_file = MagicMock()
        mock_progress_file.exists.return_value = True
        mock_get_progress_path.return_value = mock_progress_file

        # Mock existing progress - renaming completed but file missing
        renamed_path = "/test/renamed_novel.txt"
        existing_progress = {
            "phases": {
                "renaming": {"status": "completed", "result": renamed_path},
                "translation": {"status": "pending", "result": None},
                "epub": {"status": "pending", "result": None},
            }
        }
        mock_load_yaml.return_value = existing_progress

        # Mock renamed file does not exist
        with patch("enchant_book_manager.workflow_orchestrator.Path") as mock_path_class:
            mock_renamed_path = MagicMock()
            mock_renamed_path.exists.return_value = False
            mock_path_class.return_value = mock_renamed_path

            # Mock phase results - should fall back to original path
            mock_renaming.return_value = self.file_path

            # Run the function
            result = process_novel_unified(self.file_path, self.args, self.logger)

            # Verify it fell back to original path
            mock_translation.assert_called_once_with(
                self.file_path,
                self.args,
                existing_progress,
                mock_progress_file,
                self.logger,
            )

    @patch("enchant_book_manager.workflow_orchestrator.get_progress_file_path")
    @patch("enchant_book_manager.workflow_orchestrator.load_safe_yaml_wrapper")
    @patch("enchant_book_manager.workflow_orchestrator.create_initial_progress")
    @patch("enchant_book_manager.workflow_orchestrator.process_renaming_phase")
    @patch("enchant_book_manager.workflow_orchestrator.process_translation_phase")
    @patch("enchant_book_manager.workflow_orchestrator.process_epub_phase")
    def test_process_novel_resume_with_null_progress(
        self,
        mock_epub,
        mock_translation,
        mock_renaming,
        mock_create_progress,
        mock_load_yaml,
        mock_get_progress_path,
    ):
        """Test resuming when yaml load returns None."""
        # Enable resume mode
        self.args.resume = True

        # Mock progress file exists
        mock_progress_file = MagicMock()
        mock_progress_file.exists.return_value = True
        mock_get_progress_path.return_value = mock_progress_file

        # Mock yaml load returns None
        mock_load_yaml.return_value = None

        # Mock initial progress
        initial_progress = {
            "phases": {
                "renaming": {"status": "pending", "result": None},
                "translation": {"status": "pending", "result": None},
                "epub": {"status": "pending", "result": None},
            }
        }
        mock_create_progress.return_value = initial_progress

        # Mock phase results
        mock_renaming.return_value = self.file_path

        # Run the function
        result = process_novel_unified(self.file_path, self.args, self.logger)

        # Verify it created new progress
        mock_create_progress.assert_called_once_with(self.file_path)

        # Verify phases were called with initial progress
        mock_renaming.assert_called_once_with(
            self.file_path,
            self.file_path,
            self.args,
            initial_progress,
            mock_progress_file,
            self.logger,
        )

    @patch("enchant_book_manager.workflow_orchestrator.get_progress_file_path")
    @patch("enchant_book_manager.workflow_orchestrator.create_initial_progress")
    @patch("enchant_book_manager.workflow_orchestrator.process_renaming_phase")
    @patch("enchant_book_manager.workflow_orchestrator.process_translation_phase")
    @patch("enchant_book_manager.workflow_orchestrator.process_epub_phase")
    def test_process_novel_with_translated_option(
        self,
        mock_epub,
        mock_translation,
        mock_renaming,
        mock_create_progress,
        mock_get_progress_path,
    ):
        """Test processing with --translated option."""
        # Set translated option
        self.args.translated = "/test/already_translated.txt"

        # Mock progress file path
        mock_progress_file = MagicMock()
        mock_progress_file.exists.return_value = False
        mock_get_progress_path.return_value = mock_progress_file

        # Mock initial progress
        initial_progress = {
            "phases": {
                "renaming": {"status": "pending", "result": None},
                "translation": {"status": "pending", "result": None},
                "epub": {"status": "pending", "result": None},
            }
        }
        mock_create_progress.return_value = initial_progress

        # Mock phase results
        mock_renaming.return_value = self.file_path

        # Run the function
        result = process_novel_unified(self.file_path, self.args, self.logger)

        # All phases should still be called - the phases themselves handle skipping
        mock_renaming.assert_called_once()
        mock_translation.assert_called_once()
        mock_epub.assert_called_once()
