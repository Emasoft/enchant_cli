#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
# - Refactored into smaller modules (rename_api_client.py, rename_file_processor.py)
# - Removed duplicated code that was moved to new modules
# - Now imports and uses functionality from the new modules
# - Kept configuration loading and batch processing coordination
#

# Copyright 2025 Emasoft
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

import os
import yaml
import logging
import sys
from pathlib import Path
import multiprocessing
from typing import Any
from concurrent.futures import ThreadPoolExecutor
import concurrent.futures

from .common_yaml_utils import load_safe_yaml
from .cost_tracker import global_cost_tracker
from .icloud_sync import ICloudSync

# Import from new modules
from .rename_api_client import RenameAPIClient
from .rename_file_processor import (
    find_text_files,
    decode_file_content,
    extract_json,
    validate_metadata,
    rename_file_with_metadata,
    process_novel_file,
    DEFAULT_KB_TO_READ,
    MIN_FILE_SIZE_KB,
    CONTENT_NUMBER_OF_CHARACTERS_HARD_LIMIT,
)

# Version constant
VERSION = "1.3.1"

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Console handler for debug and above
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
console_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
console_handler.setFormatter(console_formatter)
logger.addHandler(console_handler)

# File handler for info and above
file_handler = logging.FileHandler("requests_responses.log")
file_handler.setLevel(logging.INFO)
file_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
file_handler.setFormatter(file_formatter)
logger.addHandler(file_handler)

ICLOUD = False  # Set this to True if you are using iCloud (requires downloadFolder/downloadFile commands)

SUPPORTED_ENCODINGS = [
    "utf-8",
    "ascii",
    "latin-1",
    "macroman",
    "windows-1252",
    "cp850",
    "iso-8859-3",
    "iso-8859-15",
    "cp437",
    "iso-8859-4",
    "iso-8859-2",
    "cp852",
    "koi8-r",
    "iso-8859-5",
    "cp1251",
    "cp866",
    "iso-8859-7",
    "cp1253",
    "iso-8859-6",
    "cp1256",
    "gb18030",
    "big5",
    "euc-kr",
    "cp874",
    "utf-16",
    "utf-16be",
    "utf-16le",
    "utf-32",
    "utf-32be",
    "utf-32le",
    "iso-8859-8",
    "iso-8859-8-e",
    "iso-8859-8-i",
    "mac_cyrillic",
    "mac_greek",
    "mac_romanian",
    "mac_turkish",
    "mac_iceland",
    "mac_centeuro",
    "mac_croatian",
]


def load_config() -> dict[str, Any]:
    """
    Load configuration from YAML file or create default.

    Creates a default config file if none exists.

    Returns:
        Dictionary containing configuration settings
    """
    default_config = {
        "model": "gpt-4o-mini",
        "temperature": 0.0,
        "kb_to_read": DEFAULT_KB_TO_READ,
        "max_workers": multiprocessing.cpu_count(),
        "api_key": None,
    }
    config_path = "renamenovels.conf.yml"
    if not os.path.exists(config_path):
        try:
            with open(config_path, "w") as config_file:
                yaml.dump(default_config, config_file)
            logger.info(f"Default configuration file created at '{config_path}'. Please update it with your settings.")
        except Exception as e:
            logger.error(f"Failed to create default config file: {e}")
        return default_config
    else:
        try:
            config = load_safe_yaml(config_path)
            if not config:  # load_safe_yaml returns {} for empty files
                logger.warning(f"Config file '{config_path}' is empty. Using default configurations.")
                return default_config
            return config
        except ValueError as e:
            logger.error(f"Error loading config file: {e}")
            return default_config
        except Exception as e:
            logger.error(f"Unexpected error loading config file: {e}")
            return default_config


def process_single_file(
    file_path: Path,
    kb_to_read: int,
    api_client: RenameAPIClient,
    icloud_sync: ICloudSync,
) -> None:
    """
    Process a single file for batch processing.

    Decodes content, extracts metadata via API, and renames the file.

    Args:
        file_path: Path to the file to process
        kb_to_read: KB to read from file start
        api_client: API client for metadata extraction
        icloud_sync: iCloud sync handler
    """
    content = decode_file_content(file_path, kb_to_read, icloud_sync)
    if content is None:
        logger.error(f"Skipping file {file_path} due to decoding errors or iCloud sync failure.")
        return

    # Extract metadata using API
    response_content = api_client.extract_metadata(content, CONTENT_NUMBER_OF_CHARACTERS_HARD_LIMIT)
    if response_content is None:
        return

    try:
        metadata = extract_json(response_content)
        if metadata is None:
            logger.error(f"Failed to extract JSON data from API response for file {file_path}.")
            return

        # Validate metadata
        if not validate_metadata(metadata):
            logger.error(f"Missing keys in response data for file {file_path}: {metadata}")
            return

        # Rename the file
        rename_file_with_metadata(file_path, metadata)

    except Exception as e:
        logger.error(f"Unexpected error processing file {file_path}: {e}")


def process_files(
    folder_or_path: Path,
    recursive: bool,
    kb_to_read: int,
    api_key: str,
    model: str,
    temperature: float,
    max_workers: int,
    icloud_sync: ICloudSync,
) -> None:
    """
    Process all eligible files in parallel.

    Uses ThreadPoolExecutor for concurrent processing.

    Args:
        folder_or_path: Directory to process
        recursive: Whether to search subdirectories
        kb_to_read: KB to read from each file
        api_key: OpenRouter API key
        model: Model name to use
        temperature: Temperature setting
        max_workers: Maximum concurrent threads
        icloud_sync: iCloud sync handler
    """
    txt_files = find_text_files(folder_or_path, recursive=recursive)
    if not txt_files:
        logger.error("No eligible text files found to process. Please check the folder or file pattern and ensure files are not hidden or too small.")
        return

    logger.info(f"Starting processing of {len(txt_files)} file(s) with max_workers={max_workers}.")

    # Create API client
    api_client = RenameAPIClient(api_key, model, temperature)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(
                process_single_file,
                file_path,
                kb_to_read,
                api_client,
                icloud_sync,
            )
            for file_path in txt_files
        ]
        try:
            for future in concurrent.futures.as_completed(futures):
                future.result()
        except KeyboardInterrupt:
            logger.info("Processing interrupted by user. Shutting down executor.")
            executor.shutdown(wait=False)
            sys.exit(1)
        except Exception as e:
            logger.error(f"An error occurred during file processing: {e}")

    # Get final cost summary
    summary = global_cost_tracker.get_summary()
    logger.info(f"Total cost for all transactions: ${summary['total_cost']:.6f}")


# This module is now a library only - use enchant_cli.py for command line interface
