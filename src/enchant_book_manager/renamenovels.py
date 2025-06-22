#!/usr/bin/env python3

import os
import requests
import yaml
import json
import logging
import re
import sys
from pathlib import Path
import multiprocessing
from json import JSONDecodeError
from typing import Any, cast
from requests.exceptions import HTTPError, ConnectionError, Timeout
from concurrent.futures import ThreadPoolExecutor
import concurrent.futures
from .common_file_utils import decode_full_file
from .common_utils import sanitize_filename as common_sanitize_filename, retry_with_backoff
from .common_yaml_utils import load_safe_yaml
from .common_constants import DEFAULT_OPENROUTER_API_URL
from .cost_tracker import global_cost_tracker
from .icloud_sync import ICloudSync, ICloudSyncError


# Version constant
VERSION = "1.3.1"
# Constants
MIN_FILE_SIZE_KB = 100
CONTENT_NUMBER_OF_CHARACTERS_HARD_LIMIT = 1500
DEFAULT_KB_TO_READ = 35

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


# Load configuration from YAML file
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


# Note: Cost tracking is now handled by the unified cost_tracker module using OpenRouter API's
# direct cost information. The old model pricing fetch from BerriAI/litellm is no longer needed.

# Model name mapping for OpenRouter
OPENROUTER_MODEL_MAPPING = {
    "gpt-4o": "openai/gpt-4o",
    "gpt-4o-mini": "openai/gpt-4o-mini",
    "gpt-4-turbo": "openai/gpt-4-turbo",
    "gpt-4": "openai/gpt-4",
    "gpt-3.5-turbo": "openai/gpt-3.5-turbo",
    "gpt-3.5-turbo-16k": "openai/gpt-3.5-turbo-16k",
}


# Retry mechanism for making requests to OpenRouter API
@retry_with_backoff(
    max_attempts=5,
    base_wait=4.0,
    max_wait=10.0,
    min_wait=4.0,
    exception_types=(HTTPError, ConnectionError, Timeout),
)
def make_openai_request(api_key: str, model: str, temperature: float, messages: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Make request to OpenRouter API with retry logic.

    Maps model names to OpenRouter format and handles errors.

    Args:
        api_key: OpenRouter API key
        model: Model name (will be mapped to OpenRouter format)
        temperature: Temperature setting for the model
        messages: List of message dictionaries for the chat

    Returns:
        API response dictionary

    Raises:
        HTTPError: If API request fails
        KeyboardInterrupt: If interrupted by user
    """
    # Map model names to OpenRouter format if needed
    openrouter_model = OPENROUTER_MODEL_MAPPING.get(model, model)
    if openrouter_model != model:
        logger.info(f"Mapped model '{model}' to OpenRouter model '{openrouter_model}'")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
        "HTTP-Referer": "https://github.com/enchant-book-manager",  # Required by OpenRouter
        "X-Title": "EnChANT Book Manager - Renaming Phase",
    }
    data = {
        "model": openrouter_model,
        "temperature": temperature,
        "messages": messages,
        "usage": {"include": True},  # Request usage/cost information
    }
    try:
        response = requests.post(
            DEFAULT_OPENROUTER_API_URL,
            headers=headers,
            json=data,
            timeout=10,
        )
        response.raise_for_status()
        logger.info("OpenRouter API request successful.")
        return cast(dict[str, Any], response.json())
    except HTTPError as e:
        if e.response.status_code == 400 and "model" in e.response.text.lower():
            logger.error(f"Model '{model}' (mapped to '{openrouter_model}') not available on OpenRouter.")
            logger.error("Available OpenAI models on OpenRouter: " + ", ".join(OPENROUTER_MODEL_MAPPING.values()))
            logger.error("For other models, use the full model name as listed on OpenRouter.")
        raise
    except KeyboardInterrupt:
        logger.error("Request interrupted by user (Ctrl+C). Exiting gracefully.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error making OpenRouter request: {e}")
        raise


# Function to find all eligible text files in a given folder
def find_text_files(folder_path: Path, recursive: bool) -> list[Path]:
    """
    Find all eligible text files in a given folder.

    Filters out hidden files and files smaller than MIN_FILE_SIZE_KB.

    Args:
        folder_path: Directory to search in
        recursive: Whether to search subdirectories

    Returns:
        List of Path objects for eligible text files
    """
    txt_files = []

    if recursive:
        files = folder_path.rglob("*.txt")
    else:
        files = folder_path.glob("*.txt")

    for file_path in files:
        if file_path.is_file() and not file_path.name.startswith(".") and file_path.stat().st_size >= MIN_FILE_SIZE_KB * 1024:
            txt_files.append(file_path)

    return txt_files


# Function to decode file content to UTF-8
def decode_file_content(file_path: Path, kb_to_read: int, icloud_sync: ICloudSync) -> str | None:
    """Decode file content using common_file_utils with size limit."""
    try:
        synced_path = icloud_sync.ensure_synced(file_path)
    except ICloudSyncError as e:
        logger.error(f"iCloud synchronization failed for '{file_path}': {e}")
        return None

    try:
        # Use the common file utils with size limit
        content = decode_full_file(synced_path, logger=logger)

        if content and kb_to_read:
            # Limit to requested size (approximate character limit)
            char_limit = kb_to_read * 1024  # Rough character estimate
            if len(content) > char_limit:
                content = content[:char_limit]

        return content

    except Exception as e:
        logger.error(f"Failed to decode file '{synced_path}': {e}")
        return None


# Helper function to sanitize filenames


# Function to rename the original file with novel information
def rename_file(file_path: Path, data: dict[str, Any]) -> None:
    """
    Rename file based on extracted novel metadata.

    Creates filename in format: "Title by Author (Romanized) - Original Title by Original Author.txt"
    Handles naming collisions by appending a counter.

    Args:
        file_path: Path to the file to rename
        data: Dictionary containing novel metadata
    """
    title_eng = common_sanitize_filename(data.get("novel_title_english", "Unknown Title"))
    author_eng = common_sanitize_filename(data.get("author_name_english", "Unknown Author"))
    author_roman = common_sanitize_filename(data.get("author_name_romanized", "Unknown"))
    title_orig = common_sanitize_filename(data.get("novel_title_original", "Unknown"))
    author_orig = common_sanitize_filename(data.get("author_name_original", "Unknown"))

    new_name = f"{title_eng} by {author_eng} ({author_roman}) - {title_orig} by {author_orig}.txt"
    new_path = file_path.with_name(new_name)

    # Ensure uniqueness if there are naming collisions
    counter = 1
    while new_path.exists():
        new_name = f"{title_eng} by {author_eng} ({author_roman}) - {title_orig} by {author_orig} ({counter}).txt"
        new_path = file_path.with_name(new_name)
        counter += 1

    logger.info(f"Renaming '{file_path}' to '{new_path}'")
    try:
        file_path.rename(new_path)
    except OSError as e:
        logger.error(f"Failed to rename '{file_path}' to '{new_path}': {e}")


# Helper function to extract JSON from response content
def extract_json(response_content: str) -> dict[str, Any] | None:
    """Attempt to extract JSON from a string."""
    try:
        return cast(dict[str, Any], json.loads(response_content))
    except JSONDecodeError:
        # Attempt to extract JSON using regex
        json_str_match = re.search(r"\{.*\}", response_content, re.DOTALL)
        if json_str_match:
            try:
                return cast(dict[str, Any], json.loads(json_str_match.group()))
            except JSONDecodeError:
                logger.error("Failed to parse JSON from the extracted string.")
                return None
        else:
            logger.error("No JSON object found in the response content.")
            return None


# Global cost tracker is imported from cost_tracker module


def process_novel_file(
    file_path: Path,
    api_key: str,
    model: str = "gpt-4o-mini",
    temperature: float = 0.0,
    dry_run: bool = False,
) -> tuple[bool, Path, dict[str, Any]]:
    """
    Process a single novel file to extract metadata and rename it.

    Args:
        file_path: Path to the novel file
        api_key: OpenAI API key
        model: OpenAI model to use (default: gpt-4o-mini)
        temperature: Model temperature (default: 0.0)
        dry_run: If True, don't actually rename the file (default: False)

    Returns:
        tuple: (success: bool, new_path: Path, metadata: dict)
    """
    try:
        # Cost tracking is now handled by the unified cost_tracker module

        # Initialize iCloud sync
        icloud_sync = ICloudSync(enabled=ICLOUD)

        # Use default kb_to_read
        kb_to_read = DEFAULT_KB_TO_READ

        # Decode file content
        content = decode_file_content(file_path, kb_to_read, icloud_sync)
        if content is None:
            logger.error(f"Failed to decode file content for {file_path}")
            return False, file_path, {}

        # Create prompt
        prompt = (
            "Given the following content from a novel, perform the following tasks:\n"
            "- Detect the language(s) of the text.\n"
            "- Find the title of the novel and the author's name.\n"
            "- Return the title of the novel and author in the original language, followed by their English translations and the romanization of the author's name.\n"
            "Content:\n" + content[:CONTENT_NUMBER_OF_CHARACTERS_HARD_LIMIT] + "\nReturn the response in JSON format as follows:\n"
            "{\n"
            '    "detected_language": "<detected_language>",\n'
            '    "novel_title_original": "<novel_title_original>",\n'
            '    "author_name_original": "<author_name_original>",\n'
            '    "novel_title_english": "<novel_title_english>",\n'
            '    "author_name_english": "<author_name_english>",\n'
            '    "author_name_romanized": "<author_name_romanized>"\n'
            "}\n"
        )

        messages = [{"role": "user", "content": prompt}]
        response = make_openai_request(api_key, model, temperature, messages)

        # Extract response content
        choices = response.get("choices")
        if not choices or not isinstance(choices, list):
            logger.error(f"No choices found in OpenAI response: {response}")
            return False, file_path, {}

        message = choices[0].get("message")
        if not message or "content" not in message:
            logger.error(f"Message content missing in OpenAI response: {response}")
            return False, file_path, {}

        response_content = message["content"]
        response_data = extract_json(response_content)

        if response_data is None:
            logger.error(f"Failed to extract JSON data from OpenAI response for file {file_path}.")
            return False, file_path, {}

        # Validate required keys
        required_keys = [
            "detected_language",
            "novel_title_original",
            "author_name_original",
            "novel_title_english",
            "author_name_english",
            "author_name_romanized",
        ]
        if not all(key in response_data for key in required_keys):
            logger.error(f"Missing keys in response data for file {file_path}: {response_data}")
            return False, file_path, {}

        # Track cost using unified cost tracker
        usage = response.get("usage", {})
        global_cost_tracker.track_usage(usage, str(file_path))

        # Determine new file path
        title_eng = common_sanitize_filename(response_data.get("novel_title_english", "Unknown Title"))
        author_eng = common_sanitize_filename(response_data.get("author_name_english", "Unknown Author"))
        author_roman = common_sanitize_filename(response_data.get("author_name_romanized", "Unknown"))
        title_orig = common_sanitize_filename(response_data.get("novel_title_original", "Unknown"))
        author_orig = common_sanitize_filename(response_data.get("author_name_original", "Unknown"))

        new_name = f"{title_eng} by {author_eng} ({author_roman}) - {title_orig} by {author_orig}.txt"
        new_path = file_path.with_name(new_name)

        # Ensure uniqueness if there are naming collisions
        counter = 1
        while new_path.exists():
            new_name = f"{title_eng} by {author_eng} ({author_roman}) - {title_orig} by {author_orig} ({counter}).txt"
            new_path = file_path.with_name(new_name)
            counter += 1

        # Rename file if not dry run
        if not dry_run:
            logger.info(f"Renaming '{file_path}' to '{new_path}'")
            try:
                file_path.rename(new_path)
            except OSError as e:
                logger.error(f"Failed to rename '{file_path}' to '{new_path}': {e}")
                return False, file_path, response_data
        else:
            logger.info(f"Dry run: Would rename '{file_path}' to '{new_path}'")

        return True, new_path, response_data

    except Exception as e:
        logger.error(f"Error processing novel file {file_path}: {e}")
        return False, file_path, {}


# Helper function to process a single file (used by batch processing)
def process_single_file(
    file_path: Path,
    kb_to_read: int,
    api_key: str,
    model: str,
    temperature: float,
    icloud_sync: ICloudSync,
) -> None:
    """
    Process a single file for batch processing.

    Decodes content, extracts metadata via API, and renames the file.

    Args:
        file_path: Path to the file to process
        kb_to_read: KB to read from file start
        api_key: OpenRouter API key
        model: Model name to use
        temperature: Temperature setting
        icloud_sync: iCloud sync handler
    """
    content = decode_file_content(file_path, kb_to_read, icloud_sync)
    if content is None:
        logger.error(f"Skipping file {file_path} due to decoding errors or iCloud sync failure.")
        return

    prompt = (
        "Given the following content from a novel, perform the following tasks:\n"
        "- Detect the language(s) of the text.\n"
        "- Find the title of the novel and the author's name.\n"
        "- Return the title of the novel and author in the original language, followed by their English translations and the romanization of the author's name.\n"
        "Content:\n" + content[:CONTENT_NUMBER_OF_CHARACTERS_HARD_LIMIT] + "\nReturn the response in JSON format as follows:\n"
        "{\n"
        '    "detected_language": "<detected_language>",\n'
        '    "novel_title_original": "<novel_title_original>",\n'
        '    "author_name_original": "<author_name_original>",\n'
        '    "novel_title_english": "<novel_title_english>",\n'
        '    "author_name_english": "<author_name_english>",\n'
        '    "author_name_romanized": "<author_name_romanized>"\n'
        "}\n"
    )

    messages = [{"role": "user", "content": prompt}]
    response = make_openai_request(api_key, model, temperature, messages)

    try:
        choices = response.get("choices")
        if not choices or not isinstance(choices, list):
            logger.error(f"No choices found in OpenAI response: {response}")
            return

        message = choices[0].get("message")
        if not message or "content" not in message:
            logger.error(f"Message content missing in OpenAI response: {response}")
            return

        response_content = message["content"]
        response_data = extract_json(response_content)

        if response_data is None:
            logger.error(f"Failed to extract JSON data from OpenAI response for file {file_path}.")
            return

        # Validate required keys
        required_keys = [
            "detected_language",
            "novel_title_original",
            "author_name_original",
            "novel_title_english",
            "author_name_english",
            "author_name_romanized",
        ]
        if not all(key in response_data for key in required_keys):
            logger.error(f"Missing keys in response data for file {file_path}: {response_data}")
            return

        # Track cost using unified cost tracker
        usage = response.get("usage", {})
        global_cost_tracker.track_usage(usage, str(file_path))

        rename_file(file_path, response_data)
    except JSONDecodeError as e:
        logger.error(f"JSON decoding error for file {file_path}: {e}")
    except KeyError as e:
        logger.error(f"Missing key in OpenAI response for file {file_path}: {e}")
    except Exception as e:
        logger.error(f"Unexpected error processing file {file_path}: {e}")


# Function to process all files
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

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(
                process_single_file,
                file_path,
                kb_to_read,
                api_key,
                model,
                temperature,
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
