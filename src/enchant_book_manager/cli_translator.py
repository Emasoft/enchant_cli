#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright (c) 2025 Emasoft
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# CHANGELOG:
# - Refactored into smaller modules for better maintainability
# - Extracted models, text processing, file handling, and orchestration
# - Main module now focuses on configuration and entry point
#

from __future__ import annotations

import logging
import signal
import sys
from pathlib import Path
from typing import (
    Any,
    Optional,
)

from .common_print_utils import safe_print
from .config_manager import ConfigManager
from .cost_tracker import global_cost_tracker
from .icloud_sync import ICloudSync
from .translation_service import ChineseAITranslator

# Import from new modules
from .models import Book, Chunk, VARIATION_DB
from .book_importer import import_book_from_txt
from .translation_orchestrator import save_translated_book as _save_translated_book_impl, DEFAULT_MAX_CHUNK_RETRIES, MAX_RETRY_WAIT_SECONDS
from .batch_processor import process_batch
from .text_splitter import DEFAULT_MAX_CHARS

try:
    import colorama as cr
except ImportError:
    cr = None  # type: ignore[assignment]
    # tolog is not yet defined here, so we will log warning later in main if needed

APP_NAME = "cli-translator"
APP_VERSION = "0.1.0"  # Semantic version (major.minor.patch)
MIN_PYTHON_VERSION_REQUIRED = "3.8"
# EPUB imports removed - EPUB generation is handled by enchant_cli.py orchestrator
# Note: model_pricing module is deprecated - using global_cost_tracker instead

# Global variables - will be initialized in main()
translator: ChineseAITranslator | None = None
tolog: logging.Logger | None = None
icloud_sync: ICloudSync | None = None
_module_config: dict[str, Any] | None = None


# Backward compatibility wrapper for save_translated_book
def save_translated_book(book_id: str, resume: bool = False, create_epub: bool = False) -> None:
    """
    Backward compatibility wrapper for save_translated_book.
    Uses the global translator instance.
    """
    global translator, tolog, _module_config
    if translator is None:
        raise RuntimeError("Translator not initialized. Call translate_novel() first.")
    return _save_translated_book_impl(book_id=book_id, translator=translator, resume=resume, create_epub=create_epub, logger=tolog, module_config=_module_config)


# Cost tracking is now handled by global_cost_tracker from cost_tracker module

MAXCHARS = DEFAULT_MAX_CHARS  # Default value, will be updated from config in main()


def translate_novel(
    file_path: str,
    encoding: str = "utf-8",
    max_chars: int = 12000,
    resume: bool = False,
    create_epub: bool = False,
    remote: bool = False,
) -> bool:
    """
    Translate a Chinese novel to English.

    Args:
        file_path: Path to the Chinese novel text file
        encoding: File encoding (default: utf-8)
        max_chars: Maximum characters per translation chunk (default: 12000)
        resume: Resume interrupted translation
        create_epub: (Deprecated) Kept for backward compatibility, ignored.
                     EPUB generation is handled by enchant_cli.py orchestrator
        remote: Use remote API instead of local

    Returns:
        bool: True if translation completed successfully, False otherwise
    """
    global tolog, translator, _module_config

    # Load configuration
    try:
        config_manager = ConfigManager(config_path=Path("enchant_config.yml"))
        config = config_manager.config
        # Store config globally for use by other functions
        _module_config = config
    except ValueError as e:
        # tolog hasn't been initialized yet, use print for error
        print(f"Configuration error: {e}")
        return False

    # Set up logging based on config
    log_level = getattr(logging, config["logging"]["level"], logging.INFO)
    log_format = config["logging"]["format"]

    logging.basicConfig(level=log_level, format=log_format)
    tolog = logging.getLogger(__name__)

    # Set up file logging if enabled
    if config["logging"]["file_enabled"]:
        try:
            file_handler = logging.FileHandler(config["logging"]["file_path"])
            file_handler.setLevel(log_level)
            file_handler.setFormatter(logging.Formatter(log_format))
            tolog.addHandler(file_handler)
        except (OSError, PermissionError) as e:
            tolog.error(f"Failed to set up file logging to {config['logging']['file_path']}: {e}")
            # Continue without file logging

    # Initialize global services
    global icloud_sync, MAXCHARS
    icloud_sync = ICloudSync(enabled=config["icloud"]["enabled"])
    # Cost tracking is now handled by global_cost_tracker

    # Update MAXCHARS from config
    MAXCHARS = config["text_processing"]["max_chars_per_chunk"]

    # Warn if colorama is missing
    if cr is None:
        tolog.warning("colorama package not installed. Colored text may not work properly.")

    # Set up signal handling for graceful termination
    def signal_handler(sig: int, frame: Any) -> None:
        tolog.info("Interrupt received. Exiting gracefully.")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    # Use the provided parameters
    use_remote = remote

    # Initialize translator with configuration
    global translator
    if use_remote:
        # Get API key from config or environment
        api_key = config_manager.get_api_key("openrouter")
        if not api_key:
            tolog.error("OpenRouter API key required. Set OPENROUTER_API_KEY or configure in enchant_config.yml")
            sys.exit(1)

        translator = ChineseAITranslator(
            logger=tolog,
            use_remote=True,
            api_key=api_key,
            endpoint=config["translation"]["remote"]["endpoint"],
            model=config["translation"]["remote"]["model"],
            temperature=config["translation"]["temperature"],
            max_tokens=config["translation"]["max_tokens"],
            timeout=config["translation"]["remote"]["timeout"],
        )
    else:
        translator = ChineseAITranslator(
            logger=tolog,
            use_remote=False,
            endpoint=config["translation"]["local"]["endpoint"],
            model=config["translation"]["local"]["model"],
            temperature=config["translation"]["temperature"],
            max_tokens=config["translation"]["max_tokens"],
            timeout=config["translation"]["local"]["timeout"],
        )

    # Note: batch processing is handled by the orchestrator, not here

    tolog.info(f"Starting book import for file: {file_path}")

    try:
        # Call the import_book_from_txt function to process the text file
        new_book_id = import_book_from_txt(file_path, encoding=encoding, max_chars=max_chars, logger=tolog)
        tolog.info(f"Book imported successfully. Book ID: {new_book_id}")
        safe_print(f"[bold green]Book imported successfully. Book ID: {new_book_id}[/bold green]")
    except Exception:
        tolog.exception("An error occurred during book import.")
        return False

    # Save the translated book after import
    try:
        _save_translated_book_impl(new_book_id, translator, resume=resume, create_epub=create_epub, logger=tolog, module_config=_module_config)
        tolog.info("Translated book saved successfully.")
        safe_print("[bold green]Translated book saved successfully.[/bold green]")

        # Log cost summary (don't print to console when called from orchestrator)
        if use_remote and translator:
            cost_summary = translator.format_cost_summary()
            tolog.info("Cost Summary:\n" + cost_summary)
        elif config["pricing"]["enabled"]:
            # Cost tracking is now handled by global_cost_tracker
            summary = global_cost_tracker.get_summary()
            tolog.info(f"Cost Summary: Total cost: ${summary['total_cost']:.6f}, Total requests: {summary['request_count']}")

        return True
    except Exception:
        tolog.exception("Error saving translated book.")
        return False


# This module is now a library only - use enchant_cli.py for command line interface
