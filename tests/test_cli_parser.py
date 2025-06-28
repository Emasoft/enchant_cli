#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test suite for cli_parser module.
"""

import pytest
import argparse
from pathlib import Path
from unittest.mock import Mock, patch
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from enchant_book_manager.cli_parser import create_parser, validate_args


class TestCreateParser:
    """Test the create_parser function."""

    def test_create_parser_basic(self):
        """Test creating parser with basic config."""
        config = {
            "text_processing": {
                "default_encoding": "utf-8",
                "max_chars_per_chunk": 12000,
            }
        }

        parser = create_parser(config)

        # Test basic properties
        assert isinstance(parser, argparse.ArgumentParser)
        assert "EnChANT - English-Chinese Automatic Novel Translator" in parser.description
        assert parser.formatter_class == argparse.RawDescriptionHelpFormatter
        assert "USAGE EXAMPLES" in parser.epilog

    def test_create_parser_arguments(self):
        """Test all arguments are properly configured."""
        config = {
            "text_processing": {
                "default_encoding": "utf-8",
                "max_chars_per_chunk": 12000,
            }
        }

        parser = create_parser(config)

        # Test that all key arguments are present
        action_names = [action.dest for action in parser._actions]

        # Core arguments
        assert "filepath" in action_names
        assert "config" in action_names
        assert "preset" in action_names
        assert "encoding" in action_names
        assert "max_chars" in action_names
        assert "resume" in action_names
        assert "epub" in action_names
        assert "batch" in action_names
        assert "remote" in action_names

        # Skip flags
        assert "skip_renaming" in action_names
        assert "skip_translating" in action_names
        assert "skip_epub" in action_names

        # Other arguments
        assert "translated" in action_names
        assert "openai_api_key" in action_names
        assert "timeout" in action_names
        assert "max_retries" in action_names
        assert "model" in action_names
        assert "endpoint" in action_names
        assert "temperature" in action_names
        assert "max_tokens" in action_names
        assert "double_pass" in action_names

        # Renaming options
        assert "rename_model" in action_names
        assert "rename_temperature" in action_names
        assert "kb_to_read" in action_names
        assert "rename_workers" in action_names
        assert "rename_dry_run" in action_names

        # EPUB options
        assert "epub_title" in action_names
        assert "epub_author" in action_names
        assert "cover" in action_names
        assert "epub_language" in action_names
        assert "no_toc" in action_names
        assert "no_validate" in action_names
        assert "epub_strict" in action_names
        assert "custom_css" in action_names
        assert "epub_metadata" in action_names
        assert "json_log" in action_names
        assert "validate_only" in action_names

    def test_parse_minimal_args(self):
        """Test parsing minimal arguments."""
        config = {
            "text_processing": {
                "default_encoding": "utf-8",
                "max_chars_per_chunk": 12000,
            }
        }

        parser = create_parser(config)
        args = parser.parse_args(["test.txt"])

        assert args.filepath == "test.txt"
        assert args.config == "enchant_config.yml"
        assert args.encoding == "utf-8"
        assert args.max_chars == 12000
        assert not args.resume
        assert not args.batch
        assert not args.remote
        assert not args.skip_renaming
        assert not args.skip_translating
        assert not args.skip_epub

    def test_parse_all_skip_flags(self):
        """Test parsing with all skip flags."""
        config = {
            "text_processing": {
                "default_encoding": "utf-8",
                "max_chars_per_chunk": 12000,
            }
        }

        parser = create_parser(config)
        args = parser.parse_args(["test.txt", "--skip-renaming", "--skip-translating", "--skip-epub"])

        assert args.skip_renaming
        assert args.skip_translating
        assert args.skip_epub

    def test_parse_batch_mode(self):
        """Test parsing batch mode arguments."""
        config = {
            "text_processing": {
                "default_encoding": "utf-8",
                "max_chars_per_chunk": 12000,
            }
        }

        parser = create_parser(config)
        args = parser.parse_args(["novels/", "--batch", "--resume", "--encoding", "gb18030"])

        assert args.filepath == "novels/"
        assert args.batch
        assert args.resume
        assert args.encoding == "gb18030"

    def test_parse_epub_options(self):
        """Test parsing EPUB-specific options."""
        config = {
            "text_processing": {
                "default_encoding": "utf-8",
                "max_chars_per_chunk": 12000,
            }
        }

        parser = create_parser(config)
        args = parser.parse_args(
            ["test.txt", "--epub", "--epub-title", "My Title", "--epub-author", "My Author", "--cover", "cover.jpg", "--epub-language", "zh", "--no-toc", "--no-validate", "--epub-strict", "--custom-css", "style.css", "--epub-metadata", '{"publisher": "Test"}', "--json-log", "log.json", "--validate-only"]
        )

        assert args.epub
        assert args.epub_title == "My Title"
        assert args.epub_author == "My Author"
        assert args.cover == "cover.jpg"
        assert args.epub_language == "zh"
        assert args.no_toc
        assert args.no_validate
        assert args.epub_strict
        assert args.custom_css == "style.css"
        assert args.epub_metadata == '{"publisher": "Test"}'
        assert args.json_log == "log.json"
        assert args.validate_only

    def test_parse_model_overrides(self):
        """Test parsing model override options."""
        config = {
            "text_processing": {
                "default_encoding": "utf-8",
                "max_chars_per_chunk": 12000,
            }
        }

        parser = create_parser(config)
        args = parser.parse_args(["test.txt", "--model", "gpt-4", "--temperature", "0.5", "--max-tokens", "2000", "--double-pass", "--rename-model", "gpt-3.5-turbo", "--rename-temperature", "0.7"])

        assert args.model == "gpt-4"
        assert args.temperature == 0.5
        assert args.max_tokens == 2000
        assert args.double_pass
        assert args.rename_model == "gpt-3.5-turbo"
        assert args.rename_temperature == 0.7

    def test_parse_translated_option(self):
        """Test parsing --translated option."""
        config = {
            "text_processing": {
                "default_encoding": "utf-8",
                "max_chars_per_chunk": 12000,
            }
        }

        parser = create_parser(config)
        args = parser.parse_args(["--translated", "translated.txt"])

        assert args.translated == "translated.txt"
        assert args.filepath is None  # Optional when using --translated

    def test_parse_with_defaults(self):
        """Test default values are applied correctly."""
        config = {
            "text_processing": {
                "default_encoding": "gb2312",
                "max_chars_per_chunk": 8000,
            }
        }

        parser = create_parser(config)
        args = parser.parse_args(["test.txt"])

        # Should use config defaults
        assert args.encoding == "gb2312"
        assert args.max_chars == 8000
        assert args.kb_to_read == 35  # Hard-coded default
        assert args.epub_language == "en"  # Hard-coded default


class TestValidateArgs:
    """Test the validate_args function."""

    @patch("enchant_book_manager.cli_parser.Path")
    def test_validate_args_with_filepath(self, mock_path):
        """Test validation with normal filepath."""
        parser = Mock(spec=argparse.ArgumentParser)
        args = Mock()
        args.translated = None
        args.filepath = "test.txt"

        validate_args(args, parser)

        # Should not call parser.error
        parser.error.assert_not_called()

    @patch("enchant_book_manager.cli_parser.Path")
    def test_validate_args_translated_file_exists(self, mock_path_class):
        """Test validation with existing translated file."""
        # Create mock path instance
        mock_path = Mock()
        mock_path.exists.return_value = True
        mock_path.is_file.return_value = True
        mock_path_class.return_value = mock_path

        parser = Mock(spec=argparse.ArgumentParser)
        args = Mock()
        args.translated = "translated.txt"
        args.filepath = None
        args.skip_renaming = False
        args.skip_translating = False

        validate_args(args, parser)

        # Should set skip flags
        assert args.skip_renaming
        assert args.skip_translating

        # Should not call parser.error
        parser.error.assert_not_called()

    @patch("enchant_book_manager.cli_parser.Path")
    def test_validate_args_translated_file_not_exists(self, mock_path_class):
        """Test validation with non-existent translated file."""
        # Create mock path instance
        mock_path = Mock()
        mock_path.exists.return_value = False
        mock_path_class.return_value = mock_path

        parser = Mock(spec=argparse.ArgumentParser)
        args = Mock()
        args.translated = "nonexistent.txt"

        validate_args(args, parser)

        # Should call parser.error
        parser.error.assert_called_with("Translated file not found: nonexistent.txt")

    @patch("enchant_book_manager.cli_parser.Path")
    def test_validate_args_translated_is_directory(self, mock_path_class):
        """Test validation when translated path is a directory."""
        # Create mock path instance
        mock_path = Mock()
        mock_path.exists.return_value = True
        mock_path.is_file.return_value = False
        mock_path_class.return_value = mock_path

        parser = Mock(spec=argparse.ArgumentParser)
        args = Mock()
        args.translated = "some_dir/"

        validate_args(args, parser)

        # Should call parser.error
        parser.error.assert_called_with("Translated path is not a file: some_dir/")

    def test_validate_args_no_filepath_no_translated(self):
        """Test validation when neither filepath nor translated is provided."""
        parser = Mock(spec=argparse.ArgumentParser)
        args = Mock()
        args.translated = None
        args.filepath = None

        validate_args(args, parser)

        # Should call parser.error
        parser.error.assert_called_with("filepath is required unless using --translated option")

    @patch("enchant_book_manager.cli_parser.Path")
    def test_validate_args_both_filepath_and_translated(self, mock_path_class):
        """Test validation when both filepath and translated are provided."""
        # Create mock path instance
        mock_path = Mock()
        mock_path.exists.return_value = True
        mock_path.is_file.return_value = True
        mock_path_class.return_value = mock_path

        parser = Mock(spec=argparse.ArgumentParser)
        args = Mock()
        args.translated = "translated.txt"
        args.filepath = "original.txt"
        args.skip_renaming = False
        args.skip_translating = False

        validate_args(args, parser)

        # Should still set skip flags
        assert args.skip_renaming
        assert args.skip_translating

        # Should not error (both are allowed)
        parser.error.assert_not_called()


class TestParserIntegration:
    """Test parser integration scenarios."""

    def test_full_workflow_parsing(self):
        """Test parsing a full workflow command."""
        config = {
            "text_processing": {
                "default_encoding": "utf-8",
                "max_chars_per_chunk": 12000,
            }
        }

        parser = create_parser(config)
        args = parser.parse_args(["chinese_novel.txt", "--openai-api-key", "test_key", "--remote", "--epub", "--model", "gpt-4", "--temperature", "0.3", "--max-chars", "5000", "--epub-title", "My Novel", "--epub-author", "Test Author", "--cover", "cover.jpg"])

        assert args.filepath == "chinese_novel.txt"
        assert args.openai_api_key == "test_key"
        assert args.remote
        assert args.epub
        assert args.model == "gpt-4"
        assert args.temperature == 0.3
        assert args.max_chars == 5000
        assert args.epub_title == "My Novel"
        assert args.epub_author == "Test Author"
        assert args.cover == "cover.jpg"

    def test_rename_only_workflow(self):
        """Test parsing rename-only workflow."""
        config = {
            "text_processing": {
                "default_encoding": "utf-8",
                "max_chars_per_chunk": 12000,
            }
        }

        parser = create_parser(config)
        args = parser.parse_args(["chinese_novel.txt", "--skip-translating", "--skip-epub", "--openai-api-key", "test_key", "--rename-dry-run"])

        assert args.skip_translating
        assert args.skip_epub
        assert args.openai_api_key == "test_key"
        assert args.rename_dry_run
        assert not args.skip_renaming

    def test_batch_with_preset(self):
        """Test parsing batch mode with preset."""
        config = {
            "text_processing": {
                "default_encoding": "utf-8",
                "max_chars_per_chunk": 12000,
            }
        }

        parser = create_parser(config)
        args = parser.parse_args(["novels/", "--batch", "--preset", "REMOTE", "--config", "custom_config.yml"])

        assert args.filepath == "novels/"
        assert args.batch
        assert args.preset == "REMOTE"
        assert args.config == "custom_config.yml"
