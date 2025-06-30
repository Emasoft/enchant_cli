#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test suite for workflow_phases module.
"""

import pytest
import logging
import argparse
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from enchant_book_manager.workflow_phases import (
    process_renaming_phase,
    process_translation_phase,
    process_epub_phase,
)


class TestProcessRenamingPhase:
    """Test the process_renaming_phase function."""

    def setup_method(self):
        """Set up test fixtures."""
        self.file_path = Path("/test/novel.txt")
        self.current_path = Path("/test/novel.txt")
        self.args = argparse.Namespace()
        self.progress = {"phases": {"renaming": {"status": "pending"}}}
        self.progress_file = Path("/test/progress.json")
        self.logger = logging.getLogger("test")

    def test_skip_renaming(self):
        """Test skipping the renaming phase."""
        self.args.skip_renaming = True

        result = process_renaming_phase(
            self.file_path,
            self.current_path,
            self.args,
            self.progress,
            self.progress_file,
            self.logger,
        )

        assert result == self.current_path
        assert self.progress["phases"]["renaming"]["status"] == "skipped"

    def test_skip_renaming_already_completed(self):
        """Test skipping when already completed."""
        self.args.skip_renaming = True
        self.progress["phases"]["renaming"]["status"] = "completed"

        result = process_renaming_phase(
            self.file_path,
            self.current_path,
            self.args,
            self.progress,
            self.progress_file,
            self.logger,
        )

        # Status should remain completed
        assert result == self.current_path
        assert self.progress["phases"]["renaming"]["status"] == "completed"

    @patch("enchant_book_manager.workflow_phases.renaming_available", False)
    @patch("enchant_book_manager.workflow_phases.save_progress")
    def test_renaming_not_available(self, mock_save):
        """Test when renaming module is not available."""
        self.args.skip_renaming = False

        result = process_renaming_phase(
            self.file_path,
            self.current_path,
            self.args,
            self.progress,
            self.progress_file,
            self.logger,
        )

        assert result == self.current_path
        assert self.progress["phases"]["renaming"]["status"] == "failed"
        assert self.progress["phases"]["renaming"]["error"] == "Module not available"

    @patch("enchant_book_manager.workflow_phases.renaming_available", True)
    @patch("enchant_book_manager.workflow_phases.save_progress")
    def test_no_api_key(self, mock_save):
        """Test when no API key is provided."""
        self.args.skip_renaming = False
        self.args.openai_api_key = None

        with patch("os.getenv", return_value=None):
            result = process_renaming_phase(
                self.file_path,
                self.current_path,
                self.args,
                self.progress,
                self.progress_file,
                self.logger,
            )

        assert result == self.current_path
        assert self.progress["phases"]["renaming"]["status"] == "failed"
        assert self.progress["phases"]["renaming"]["error"] == "No API key"

    @patch("enchant_book_manager.workflow_phases.renaming_available", True)
    @patch("enchant_book_manager.workflow_phases.RenameAPIClient")
    @patch("enchant_book_manager.workflow_phases.rename_novel")
    @patch("enchant_book_manager.workflow_phases.save_progress")
    def test_successful_renaming(self, mock_save, mock_rename, mock_api_client):
        """Test successful renaming."""
        self.args.skip_renaming = False
        self.args.openai_api_key = "test-key"
        self.args.rename_model = "gpt-4"
        self.args.rename_temperature = 0.5
        self.args.rename_dry_run = False

        new_path = Path("/test/Novel by Author.txt")
        mock_rename.return_value = (
            True,
            new_path,
            {"title": "Novel", "author": "Author"},
        )

        result = process_renaming_phase(
            self.file_path,
            self.current_path,
            self.args,
            self.progress,
            self.progress_file,
            self.logger,
        )

        assert result == new_path
        assert self.progress["phases"]["renaming"]["status"] == "completed"
        assert self.progress["phases"]["renaming"]["result"] == str(new_path)

        # Verify API client creation
        mock_api_client.assert_called_once_with(api_key="test-key", model="gpt-4", temperature=0.5)

        # Verify rename call
        mock_rename.assert_called_once_with(self.file_path, api_client=mock_api_client.return_value, dry_run=False)

    @patch("enchant_book_manager.workflow_phases.renaming_available", True)
    @patch("enchant_book_manager.workflow_phases.RenameAPIClient")
    @patch("enchant_book_manager.workflow_phases.rename_novel")
    @patch("enchant_book_manager.workflow_phases.save_progress")
    def test_renaming_failure(self, mock_save, mock_rename, mock_api_client):
        """Test renaming failure."""
        self.args.skip_renaming = False
        self.args.openai_api_key = "test-key"

        mock_rename.return_value = (False, None, None)

        result = process_renaming_phase(
            self.file_path,
            self.current_path,
            self.args,
            self.progress,
            self.progress_file,
            self.logger,
        )

        assert result == self.current_path
        assert self.progress["phases"]["renaming"]["status"] == "failed"

    @patch("enchant_book_manager.workflow_phases.renaming_available", True)
    @patch("enchant_book_manager.workflow_phases.RenameAPIClient")
    @patch("enchant_book_manager.workflow_phases.save_progress")
    def test_renaming_exception(self, mock_save, mock_api_client):
        """Test exception during renaming."""
        self.args.skip_renaming = False
        self.args.openai_api_key = "test-key"

        mock_api_client.side_effect = Exception("API error")

        result = process_renaming_phase(
            self.file_path,
            self.current_path,
            self.args,
            self.progress,
            self.progress_file,
            self.logger,
        )

        assert result == self.current_path
        assert self.progress["phases"]["renaming"]["status"] == "failed"
        assert self.progress["phases"]["renaming"]["error"] == "API error"

    @patch("enchant_book_manager.workflow_phases.renaming_available", True)
    @patch("enchant_book_manager.workflow_phases.RenameAPIClient")
    @patch("enchant_book_manager.workflow_phases.rename_novel")
    @patch("enchant_book_manager.workflow_phases.save_progress")
    def test_default_values(self, mock_save, mock_rename, mock_api_client):
        """Test with default values when args don't have rename attributes."""
        self.args.skip_renaming = False
        self.args.openai_api_key = "test-key"
        # Don't set rename_model, rename_temperature, rename_dry_run

        new_path = Path("/test/renamed.txt")
        mock_rename.return_value = (True, new_path, {})

        result = process_renaming_phase(
            self.file_path,
            self.current_path,
            self.args,
            self.progress,
            self.progress_file,
            self.logger,
        )

        # Verify defaults are used
        mock_api_client.assert_called_once_with(
            api_key="test-key",
            model="gpt-4o-mini",  # default
            temperature=0.0,  # default
        )

        mock_rename.assert_called_once_with(
            self.file_path,
            api_client=mock_api_client.return_value,
            dry_run=False,  # default
        )

    @patch("enchant_book_manager.workflow_phases.renaming_available", True)
    @patch("os.getenv")
    @patch("enchant_book_manager.workflow_phases.RenameAPIClient")
    @patch("enchant_book_manager.workflow_phases.rename_novel")
    @patch("enchant_book_manager.workflow_phases.save_progress")
    def test_api_key_from_env(self, mock_save, mock_rename, mock_api_client, mock_getenv):
        """Test getting API key from environment variable."""
        self.args.skip_renaming = False
        # No args.openai_api_key
        mock_getenv.return_value = "env-api-key"

        new_path = Path("/test/renamed.txt")
        mock_rename.return_value = (True, new_path, {})

        result = process_renaming_phase(
            self.file_path,
            self.current_path,
            self.args,
            self.progress,
            self.progress_file,
            self.logger,
        )

        mock_getenv.assert_called_with("OPENROUTER_API_KEY")
        mock_api_client.assert_called_once_with(api_key="env-api-key", model="gpt-4o-mini", temperature=0.0)


class TestProcessTranslationPhase:
    """Test the process_translation_phase function."""

    def setup_method(self):
        """Set up test fixtures."""
        self.current_path = Path("/test/novel.txt")
        self.args = argparse.Namespace(resume=False)
        self.progress = {"phases": {"translation": {"status": "pending"}}}
        self.progress_file = Path("/test/progress.json")
        self.logger = logging.getLogger("test")

    def test_skip_translation(self):
        """Test skipping the translation phase."""
        self.args.skip_translating = True

        process_translation_phase(self.current_path, self.args, self.progress, self.progress_file, self.logger)

        assert self.progress["phases"]["translation"]["status"] == "skipped"

    def test_skip_translation_already_completed(self):
        """Test skipping when already completed."""
        self.args.skip_translating = True
        self.progress["phases"]["translation"]["status"] = "completed"

        process_translation_phase(self.current_path, self.args, self.progress, self.progress_file, self.logger)

        # Status should remain completed
        assert self.progress["phases"]["translation"]["status"] == "completed"

    @patch("enchant_book_manager.workflow_phases.translation_available", False)
    @patch("enchant_book_manager.workflow_phases.save_progress")
    def test_translation_not_available(self, mock_save):
        """Test when translation module is not available."""
        self.args.skip_translating = False

        process_translation_phase(self.current_path, self.args, self.progress, self.progress_file, self.logger)

        assert self.progress["phases"]["translation"]["status"] == "failed"
        assert self.progress["phases"]["translation"]["error"] == "Module not available"

    @patch("enchant_book_manager.workflow_phases.translation_available", True)
    @patch("enchant_book_manager.workflow_phases.translate_novel")
    @patch("enchant_book_manager.workflow_phases.save_progress")
    def test_successful_translation(self, mock_save, mock_translate):
        """Test successful translation."""
        self.args.skip_translating = False
        self.args.encoding = "utf-8"
        self.args.max_chars = 10000
        self.args.remote = True

        mock_translate.return_value = True

        process_translation_phase(self.current_path, self.args, self.progress, self.progress_file, self.logger)

        assert self.progress["phases"]["translation"]["status"] == "completed"
        assert self.progress["phases"]["translation"]["result"] == "success"

        # Verify translation call
        mock_translate.assert_called_once_with(
            str(self.current_path),
            encoding="utf-8",
            max_chars=10000,
            resume=False,
            create_epub=False,
            remote=True,
        )

    @patch("enchant_book_manager.workflow_phases.translation_available", True)
    @patch("enchant_book_manager.workflow_phases.translate_novel")
    @patch("enchant_book_manager.workflow_phases.save_progress")
    def test_translation_failure(self, mock_save, mock_translate):
        """Test translation failure."""
        self.args.skip_translating = False

        mock_translate.return_value = False

        process_translation_phase(self.current_path, self.args, self.progress, self.progress_file, self.logger)

        assert self.progress["phases"]["translation"]["status"] == "failed"
        assert self.progress["phases"]["translation"]["error"] == "Translation failed"

    @patch("enchant_book_manager.workflow_phases.translation_available", True)
    @patch("enchant_book_manager.workflow_phases.translate_novel")
    @patch("enchant_book_manager.workflow_phases.save_progress")
    def test_translation_exception(self, mock_save, mock_translate):
        """Test exception during translation."""
        self.args.skip_translating = False

        mock_translate.side_effect = Exception("Translation error")

        process_translation_phase(self.current_path, self.args, self.progress, self.progress_file, self.logger)

        assert self.progress["phases"]["translation"]["status"] == "failed"
        assert self.progress["phases"]["translation"]["error"] == "Translation error"

    @patch("enchant_book_manager.workflow_phases.translation_available", True)
    @patch("enchant_book_manager.workflow_phases.translate_novel")
    @patch("enchant_book_manager.workflow_phases.save_progress")
    def test_default_values(self, mock_save, mock_translate):
        """Test with default values when args don't have attributes."""
        self.args.skip_translating = False
        # Don't set encoding, max_chars, remote

        mock_translate.return_value = True

        process_translation_phase(self.current_path, self.args, self.progress, self.progress_file, self.logger)

        # Verify defaults are used
        mock_translate.assert_called_once_with(
            str(self.current_path),
            encoding="utf-8",  # default
            max_chars=12000,  # default
            resume=False,
            create_epub=False,
            remote=False,  # default
        )


class TestProcessEpubPhase:
    """Test the process_epub_phase function."""

    def setup_method(self):
        """Set up test fixtures."""
        self.current_path = Path("/test/novel.txt")
        self.args = argparse.Namespace()
        self.progress = {"phases": {"epub": {"status": "pending"}}}
        self.progress_file = Path("/test/progress.json")
        self.logger = logging.getLogger("test")

    def test_skip_epub(self):
        """Test skipping the EPUB phase."""
        self.args.skip_epub = True

        process_epub_phase(self.current_path, self.args, self.progress, self.progress_file, self.logger)

        assert self.progress["phases"]["epub"]["status"] == "skipped"

    def test_skip_epub_already_completed(self):
        """Test skipping when already completed."""
        self.args.skip_epub = True
        self.progress["phases"]["epub"]["status"] = "completed"

        process_epub_phase(self.current_path, self.args, self.progress, self.progress_file, self.logger)

        # Status should remain completed
        assert self.progress["phases"]["epub"]["status"] == "completed"

    @patch("enchant_book_manager.workflow_phases.epub_available", False)
    @patch("enchant_book_manager.workflow_phases.save_progress")
    def test_epub_not_available(self, mock_save):
        """Test when EPUB module is not available."""
        self.args.skip_epub = False

        process_epub_phase(self.current_path, self.args, self.progress, self.progress_file, self.logger)

        assert self.progress["phases"]["epub"]["status"] == "failed"
        assert self.progress["phases"]["epub"]["error"] == "Module not available"

    @patch("enchant_book_manager.workflow_phases.epub_available", True)
    @patch("enchant_book_manager.workflow_phases.save_progress")
    def test_successful_epub_generation(self, mock_save):
        """Test successful EPUB generation."""
        self.args.skip_epub = False

        with patch("enchant_book_manager.workflow_epub.process_epub_generation") as mock_epub_gen:
            mock_epub_gen.return_value = True

            process_epub_phase(
                self.current_path,
                self.args,
                self.progress,
                self.progress_file,
                self.logger,
            )

        assert self.progress["phases"]["epub"]["status"] == "completed"

        # Verify epub generation call
        mock_epub_gen.assert_called_once_with(self.current_path, self.args, self.progress, self.logger)

    @patch("enchant_book_manager.workflow_phases.epub_available", True)
    @patch("enchant_book_manager.workflow_phases.save_progress")
    def test_epub_generation_failure(self, mock_save):
        """Test EPUB generation failure."""
        self.args.skip_epub = False

        with patch("enchant_book_manager.workflow_epub.process_epub_generation") as mock_epub_gen:
            mock_epub_gen.return_value = False

            process_epub_phase(
                self.current_path,
                self.args,
                self.progress,
                self.progress_file,
                self.logger,
            )

        assert self.progress["phases"]["epub"]["status"] == "failed"

    @patch("enchant_book_manager.workflow_phases.epub_available", True)
    @patch("enchant_book_manager.workflow_phases.save_progress")
    def test_epub_generation_exception(self, mock_save):
        """Test exception during EPUB generation."""
        self.args.skip_epub = False

        with patch("enchant_book_manager.workflow_epub.process_epub_generation") as mock_epub_gen:
            mock_epub_gen.side_effect = Exception("EPUB error")

            process_epub_phase(
                self.current_path,
                self.args,
                self.progress,
                self.progress_file,
                self.logger,
            )

        assert self.progress["phases"]["epub"]["status"] == "failed"
        assert self.progress["phases"]["epub"]["error"] == "EPUB error"

    @patch("enchant_book_manager.workflow_phases.epub_available", True)
    @patch("enchant_book_manager.workflow_phases.save_progress")
    def test_import_error_handling(self, mock_save):
        """Test handling of import error for workflow_epub."""
        self.args.skip_epub = False

        # Mock the import to raise ImportError
        with patch(
            "builtins.__import__",
            side_effect=ImportError("Cannot import workflow_epub"),
        ):
            process_epub_phase(
                self.current_path,
                self.args,
                self.progress,
                self.progress_file,
                self.logger,
            )

        assert self.progress["phases"]["epub"]["status"] == "failed"
        assert "Cannot import workflow_epub" in self.progress["phases"]["epub"]["error"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
