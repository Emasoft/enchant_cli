#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test suite for enchant_cli module.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call
import logging

sys.path.insert(0, str(Path(__file__).parent.parent))

from enchant_book_manager.enchant_cli import main, APP_NAME, APP_VERSION, MIN_PYTHON_VERSION_REQUIRED


class TestEnchantCliMain:
    """Test the main CLI entry point."""

    @patch("enchant_book_manager.enchant_cli.setup_signal_handler")
    @patch("enchant_book_manager.enchant_cli.check_colorama")
    @patch("enchant_book_manager.enchant_cli.setup_global_services")
    @patch("enchant_book_manager.enchant_cli.setup_logging")
    @patch("enchant_book_manager.enchant_cli.setup_configuration")
    @patch("enchant_book_manager.enchant_cli.create_parser")
    @patch("enchant_book_manager.enchant_cli.validate_args")
    @patch("enchant_book_manager.enchant_cli.process_novel_unified")
    @patch("enchant_book_manager.enchant_cli.Path")
    @patch("enchant_book_manager.enchant_cli.safe_print")
    @patch("enchant_book_manager.enchant_cli.sys.exit")
    def test_main_single_file_success(
        self,
        mock_exit,
        mock_print,
        mock_path_class,
        mock_process_novel,
        mock_validate_args,
        mock_create_parser,
        mock_setup_config,
        mock_setup_logging,
        mock_setup_global,
        mock_check_colorama,
        mock_signal_handler
    ):
        """Test successful single file processing."""
        # Mock configuration
        mock_config_manager = Mock()
        mock_config = {"log_level": "INFO"}
        mock_setup_config.return_value = (mock_config_manager, mock_config)
        mock_config_manager.update_with_args.return_value = mock_config
        
        # Mock logging
        mock_logger = Mock(spec=logging.Logger)
        mock_setup_logging.return_value = mock_logger
        
        # Mock argument parser
        mock_parser = Mock()
        mock_args = Mock()
        mock_args.batch = False
        mock_args.filepath = "/path/to/file.txt"
        mock_args.translated = None
        mock_parser.parse_args.return_value = mock_args
        mock_create_parser.return_value = mock_parser
        
        # Mock Path
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path_class.return_value = mock_path
        
        # Mock successful processing
        mock_process_novel.return_value = True
        
        # Run main
        main()
        
        # Verify setup calls
        mock_setup_config.assert_called_once()
        mock_setup_logging.assert_called_once_with(mock_config)
        mock_setup_global.assert_called_once_with(mock_config)
        mock_check_colorama.assert_called_once_with(mock_logger)
        mock_signal_handler.assert_called_once_with(mock_logger)
        
        # Verify argument parsing
        mock_create_parser.assert_called_once_with(mock_config)
        mock_validate_args.assert_called_once_with(mock_args, mock_parser)
        
        # Verify processing
        mock_process_novel.assert_called_once_with(mock_path, mock_args, mock_logger)
        mock_print.assert_called_with("[bold green]Novel processing completed successfully![/bold green]")
        mock_exit.assert_not_called()

    @patch("enchant_book_manager.enchant_cli.setup_signal_handler")
    @patch("enchant_book_manager.enchant_cli.check_colorama")
    @patch("enchant_book_manager.enchant_cli.setup_global_services")
    @patch("enchant_book_manager.enchant_cli.setup_logging")
    @patch("enchant_book_manager.enchant_cli.setup_configuration")
    @patch("enchant_book_manager.enchant_cli.create_parser")
    @patch("enchant_book_manager.enchant_cli.validate_args")
    @patch("enchant_book_manager.enchant_cli.process_novel_unified")
    @patch("enchant_book_manager.enchant_cli.Path")
    @patch("enchant_book_manager.enchant_cli.safe_print")
    def test_main_file_not_found(
        self,
        mock_print,
        mock_path_class,
        mock_process_novel,
        mock_validate_args,
        mock_create_parser,
        mock_setup_config,
        mock_setup_logging,
        mock_setup_global,
        mock_check_colorama,
        mock_signal_handler
    ):
        """Test handling of non-existent file."""
        # Mock configuration
        mock_config_manager = Mock()
        mock_config = {"log_level": "INFO"}
        mock_setup_config.return_value = (mock_config_manager, mock_config)
        mock_config_manager.update_with_args.return_value = mock_config
        
        # Mock logging
        mock_logger = Mock(spec=logging.Logger)
        mock_setup_logging.return_value = mock_logger
        
        # Mock argument parser
        mock_parser = Mock()
        mock_args = Mock()
        mock_args.batch = False
        mock_args.filepath = "/path/to/missing.txt"
        mock_args.translated = None
        mock_parser.parse_args.return_value = mock_args
        mock_create_parser.return_value = mock_parser
        
        # Mock Path - file doesn't exist
        mock_path = MagicMock()
        mock_path.exists.return_value = False
        mock_path.__str__.return_value = "/path/to/missing.txt"
        mock_path_class.return_value = mock_path
        
        # Run main with sys.exit mocked to raise SystemExit
        with patch("enchant_book_manager.enchant_cli.sys.exit") as mock_exit:
            mock_exit.side_effect = SystemExit(1)
            
            with pytest.raises(SystemExit) as exc_info:
                main()
            
            assert exc_info.value.code == 1
        
        # Verify error handling
        mock_logger.error.assert_called_with(f"File not found: {mock_path}")
        mock_print.assert_called_with(f"[bold red]File not found: {mock_path}[/bold red]")
        mock_process_novel.assert_not_called()

    @patch("enchant_book_manager.enchant_cli.setup_signal_handler")
    @patch("enchant_book_manager.enchant_cli.check_colorama")
    @patch("enchant_book_manager.enchant_cli.setup_global_services")
    @patch("enchant_book_manager.enchant_cli.setup_logging")
    @patch("enchant_book_manager.enchant_cli.setup_configuration")
    @patch("enchant_book_manager.enchant_cli.create_parser")
    @patch("enchant_book_manager.enchant_cli.validate_args")
    @patch("enchant_book_manager.enchant_cli.process_batch")
    @patch("enchant_book_manager.enchant_cli.safe_print")
    def test_main_batch_mode(
        self,
        mock_print,
        mock_process_batch,
        mock_validate_args,
        mock_create_parser,
        mock_setup_config,
        mock_setup_logging,
        mock_setup_global,
        mock_check_colorama,
        mock_signal_handler
    ):
        """Test batch mode processing."""
        # Mock configuration
        mock_config_manager = Mock()
        mock_config = {"log_level": "INFO"}
        mock_setup_config.return_value = (mock_config_manager, mock_config)
        mock_config_manager.update_with_args.return_value = mock_config
        
        # Mock logging
        mock_logger = Mock(spec=logging.Logger)
        mock_setup_logging.return_value = mock_logger
        
        # Mock argument parser for batch mode
        mock_parser = Mock()
        mock_args = Mock()
        mock_args.batch = True
        mock_args.filepath = "/path/to/batch/dir"
        mock_args.translated = None
        mock_parser.parse_args.return_value = mock_args
        mock_create_parser.return_value = mock_parser
        
        # Run main
        main()
        
        # Verify batch processing was called
        mock_process_batch.assert_called_once_with(mock_args, mock_logger)

    @patch("enchant_book_manager.enchant_cli.setup_signal_handler")
    @patch("enchant_book_manager.enchant_cli.check_colorama")
    @patch("enchant_book_manager.enchant_cli.setup_global_services")
    @patch("enchant_book_manager.enchant_cli.setup_logging")
    @patch("enchant_book_manager.enchant_cli.setup_configuration")
    @patch("enchant_book_manager.enchant_cli.create_parser")
    @patch("enchant_book_manager.enchant_cli.validate_args")
    @patch("enchant_book_manager.enchant_cli.process_novel_unified")
    @patch("enchant_book_manager.enchant_cli.Path")
    @patch("enchant_book_manager.enchant_cli.safe_print")
    @patch("enchant_book_manager.enchant_cli.sys.exit")
    def test_main_with_translated_option(
        self,
        mock_exit,
        mock_print,
        mock_path_class,
        mock_process_novel,
        mock_validate_args,
        mock_create_parser,
        mock_setup_config,
        mock_setup_logging,
        mock_setup_global,
        mock_check_colorama,
        mock_signal_handler
    ):
        """Test processing with --translated option."""
        # Mock configuration
        mock_config_manager = Mock()
        mock_config = {"log_level": "INFO"}
        mock_setup_config.return_value = (mock_config_manager, mock_config)
        mock_config_manager.update_with_args.return_value = mock_config
        
        # Mock logging
        mock_logger = Mock(spec=logging.Logger)
        mock_setup_logging.return_value = mock_logger
        
        # Mock argument parser with translated option
        mock_parser = Mock()
        mock_args = Mock()
        mock_args.batch = False
        mock_args.filepath = None
        mock_args.translated = "/path/to/translated.txt"
        mock_parser.parse_args.return_value = mock_args
        mock_create_parser.return_value = mock_parser
        
        # Mock Path
        mock_path = MagicMock()
        mock_path_class.return_value = mock_path
        
        # Mock successful processing
        mock_process_novel.return_value = True
        
        # Run main
        main()
        
        # Verify translated option was logged
        mock_logger.info.assert_any_call("--translated option provided, automatically skipping renaming and translation phases")
        
        # Verify Path was created with translated file
        mock_path_class.assert_called_with("/path/to/translated.txt")
        
        # Verify processing
        mock_process_novel.assert_called_once_with(mock_path, mock_args, mock_logger)

    @patch("enchant_book_manager.enchant_cli.setup_signal_handler")
    @patch("enchant_book_manager.enchant_cli.check_colorama")
    @patch("enchant_book_manager.enchant_cli.setup_global_services")
    @patch("enchant_book_manager.enchant_cli.setup_logging")
    @patch("enchant_book_manager.enchant_cli.setup_configuration")
    @patch("enchant_book_manager.enchant_cli.create_parser")
    @patch("enchant_book_manager.enchant_cli.validate_args")
    @patch("enchant_book_manager.enchant_cli.process_novel_unified")
    @patch("enchant_book_manager.enchant_cli.Path")
    @patch("enchant_book_manager.enchant_cli.safe_print")
    @patch("enchant_book_manager.enchant_cli.sys.exit")
    def test_main_processing_failure(
        self,
        mock_exit,
        mock_print,
        mock_path_class,
        mock_process_novel,
        mock_validate_args,
        mock_create_parser,
        mock_setup_config,
        mock_setup_logging,
        mock_setup_global,
        mock_check_colorama,
        mock_signal_handler
    ):
        """Test handling of processing failure."""
        # Mock configuration
        mock_config_manager = Mock()
        mock_config = {"log_level": "INFO"}
        mock_setup_config.return_value = (mock_config_manager, mock_config)
        mock_config_manager.update_with_args.return_value = mock_config
        
        # Mock logging
        mock_logger = Mock(spec=logging.Logger)
        mock_setup_logging.return_value = mock_logger
        
        # Mock argument parser
        mock_parser = Mock()
        mock_args = Mock()
        mock_args.batch = False
        mock_args.filepath = "/path/to/file.txt"
        mock_args.translated = None
        mock_parser.parse_args.return_value = mock_args
        mock_create_parser.return_value = mock_parser
        
        # Mock Path
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path_class.return_value = mock_path
        
        # Mock processing failure
        mock_process_novel.return_value = False
        
        # Run main
        main()
        
        # Verify failure handling
        mock_print.assert_called_with("[bold yellow]Novel processing completed with some issues. Check logs for details.[/bold yellow]")
        mock_exit.assert_called_with(1)

    @patch("enchant_book_manager.enchant_cli.setup_signal_handler")
    @patch("enchant_book_manager.enchant_cli.check_colorama")
    @patch("enchant_book_manager.enchant_cli.setup_global_services")
    @patch("enchant_book_manager.enchant_cli.setup_logging")
    @patch("enchant_book_manager.enchant_cli.setup_configuration")
    @patch("enchant_book_manager.enchant_cli.create_parser")
    @patch("enchant_book_manager.enchant_cli.validate_args")
    @patch("enchant_book_manager.enchant_cli.process_novel_unified")
    @patch("enchant_book_manager.enchant_cli.Path")
    @patch("enchant_book_manager.enchant_cli.safe_print")
    @patch("enchant_book_manager.enchant_cli.sys.exit")
    def test_main_exception_handling(
        self,
        mock_exit,
        mock_print,
        mock_path_class,
        mock_process_novel,
        mock_validate_args,
        mock_create_parser,
        mock_setup_config,
        mock_setup_logging,
        mock_setup_global,
        mock_check_colorama,
        mock_signal_handler
    ):
        """Test handling of exceptions during processing."""
        # Mock configuration
        mock_config_manager = Mock()
        mock_config = {"log_level": "INFO"}
        mock_setup_config.return_value = (mock_config_manager, mock_config)
        mock_config_manager.update_with_args.return_value = mock_config
        
        # Mock logging
        mock_logger = Mock(spec=logging.Logger)
        mock_setup_logging.return_value = mock_logger
        
        # Mock argument parser
        mock_parser = Mock()
        mock_args = Mock()
        mock_args.batch = False
        mock_args.filepath = "/path/to/file.txt"
        mock_args.translated = None
        mock_parser.parse_args.return_value = mock_args
        mock_create_parser.return_value = mock_parser
        
        # Mock Path
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path_class.return_value = mock_path
        
        # Mock exception during processing
        test_exception = RuntimeError("Test error")
        mock_process_novel.side_effect = test_exception
        
        # Run main
        main()
        
        # Verify exception handling
        mock_logger.exception.assert_called_with("Fatal error during novel processing")
        mock_print.assert_called_with(f"[bold red]Fatal error: {test_exception}[/bold red]")
        mock_exit.assert_called_with(1)


class TestConstants:
    """Test module constants."""

    def test_app_name(self):
        """Test APP_NAME constant."""
        assert APP_NAME == "EnChANT - English-Chinese Automatic Novel Translator"

    def test_app_version(self):
        """Test APP_VERSION constant."""
        assert APP_VERSION == "1.0.0"

    def test_min_python_version(self):
        """Test MIN_PYTHON_VERSION_REQUIRED constant."""
        assert MIN_PYTHON_VERSION_REQUIRED == "3.8"