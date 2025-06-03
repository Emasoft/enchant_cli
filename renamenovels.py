#!/usr/bin/env python3

import os
import requests
import chardet
import yaml
import json
import tenacity
import logging
import subprocess
import shlex
import re
import argparse
import sys
import string
import getpass
from pathlib import Path
import multiprocessing
from json import JSONDecodeError
from typing import Optional
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from requests.exceptions import HTTPError, ConnectionError, Timeout
from concurrent.futures import ThreadPoolExecutor
import concurrent.futures
import threading
import waiting  # Ensure this library is installed: pip install waiting

# ==========================
# ICloudSync Class Definition
# ==========================

class ICloudSyncError(Exception):
    """Custom exception for iCloud synchronization errors."""
    pass

class ICloudSync:
    def __init__(self, icloud_enabled: bool = True):
        self.ICLOUD = icloud_enabled
        if self.ICLOUD:
            self.validate_commands()

    def validate_commands(self):
        """Ensure that required iCloud sync commands are available."""
        import shutil
        required_commands = ['downloadFolder', 'downloadFile']
        missing = [cmd for cmd in required_commands if shutil.which(cmd) is None]
        if missing:
            logger.error(f"Missing required commands: {', '.join(missing)}. Please install them and ensure they are in the system's PATH.")
            raise ICloudSyncError(f"Missing commands: {', '.join(missing)}")

    def check_and_wait_for_sync(self, path: Path) -> Path:
        """Check and wait for iCloud synchronization of the given path."""
        if not self.ICLOUD:
            return path

        if path.is_dir():
            self.force_sync_folder(path)
            return path
        elif path.is_file():
            synced_file = self.force_sync_file(path)
            return synced_file
        else:
            logger.warning(f"Path '{path}' is neither a file nor a directory. Skipping iCloud sync.")
            return path

    def force_sync_folder(self, folder_path: Path, recursive: bool = False, depth: int = 0) -> None:
        """Force iCloud synchronization for a folder."""
        if not self.ICLOUD:
            return

        if folder_path.is_dir():
            logger.info(f"FORCING iCloud Sync for Folder: {folder_path}")
            command = shlex.split(f'downloadFolder "{folder_path}"')
            try:
                subprocess.run(command, stdout=subprocess.PIPE, check=True)
            except subprocess.CalledProcessError as e:
                logger.error(f"Error executing command '{' '.join(command)}': {e}")
                raise ICloudSyncError(f"Failed to sync folder: {folder_path}")

            if not recursive and depth >= 1:
                return
            depth += 1
            for file in folder_path.iterdir():
                if file.is_dir():
                    self.force_sync_folder(file, recursive, depth)
                elif file.is_file():
                    self.force_sync_file(file)

            # Waiting for the folder to be free of dummy files
            try:
                waiting.wait(
                    lambda: self.check_folder_is_free_of_dummy_files(folder_path),
                    sleep_seconds=5,
                    timeout_seconds=300,  # Max timeout
                    waiting_for="iCloud folder to be free of dummy files"
                )
            except waiting.TimeoutExpired:
                logger.error(f"Timeout while waiting for folder '{folder_path}' to be free of dummy files.")
                raise ICloudSyncError(f"Timeout syncing folder: {folder_path}")
        else:
            raise ICloudSyncError(f"Path '{folder_path}' is not a directory.")

    def check_folder_is_free_of_dummy_files(self, folder_path: Path) -> bool:
        """Check if the folder is free of iCloud dummy files."""
        if not self.ICLOUD:
            return True

        if folder_path.is_dir():
            icloud_dummyfiles_exist = any(file.suffix == '.icloud' for file in folder_path.iterdir())
            if not icloud_dummyfiles_exist:
                return True
            else:
                logger.info("CHECK FOLDER FOR ICLOUD DUMMY FILES - DUMMY EXISTS - WAITING...")
                return False
        else:
            return True

    def force_sync_file(self, file_path: Path) -> Path:
        """Force iCloud synchronization for a single file."""
        if not self.ICLOUD:
            return file_path

        filename = file_path.name
        if filename.endswith('.icloud'):
            logger.info(f"FORCING iCloud Sync for File: {file_path}")
            command = shlex.split(f'downloadFile "{file_path}"')
            try:
                subprocess.run(command, stdout=subprocess.PIPE, check=True)
            except subprocess.CalledProcessError as e:
                logger.error(f"Error executing command '{' '.join(command)}': {e}")
                raise ICloudSyncError(f"Failed to sync file: {file_path}")

            # Waiting for the file to be fully downloaded
            try:
                waiting.wait(
                    lambda: self.check_if_not_icloud_dummyfile(file_path),
                    sleep_seconds=5,
                    timeout_seconds=300,  # Max timeout
                    waiting_for="iCloud file to be fully downloaded"
                )
            except waiting.TimeoutExpired:
                logger.error(f"Timeout while waiting for file '{file_path}' to be fully downloaded.")
                raise ICloudSyncError(f"Timeout syncing file: {file_path}")

            file_true_name = re.sub(r'\.icloud$', '', filename)
            return file_path.parent / file_true_name
        else:
            file_dummy_name = f"{filename.strip()}.icloud"
            dummy_file_path = file_path.parent / file_dummy_name
            if dummy_file_path.is_file():
                return self.force_sync_file(dummy_file_path)
            else:
                return file_path

    def check_if_not_icloud_dummyfile(self, file_path: Path) -> bool:
        """Check if the file is not an iCloud dummy file."""
        if not self.ICLOUD:
            return True

        if file_path.name.endswith('.icloud'):
            file_true_name = re.sub(r'\.icloud$', '', file_path.name)
            true_file_path = file_path.parent / file_true_name
            if true_file_path.is_file():
                return True
            else:
                return False
        return True

# ==========================
# End of ICloudSync Class
# ==========================

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
console_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console_handler.setFormatter(console_formatter)
logger.addHandler(console_handler)

# File handler for info and above
file_handler = logging.FileHandler('requests_responses.log')
file_handler.setLevel(logging.INFO)
file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(file_formatter)
logger.addHandler(file_handler)

ICLOUD = True  # Set this to True if you are using iCloud

SUPPORTED_ENCODINGS = [
    'utf-8', 'ascii', 'latin-1', 'macroman', 'windows-1252', 'cp850', 'iso-8859-3', 'iso-8859-15', 'cp437',
    'iso-8859-4', 'iso-8859-2', 'cp852', 'koi8-r', 'iso-8859-5', 'cp1251', 'cp866',
    'iso-8859-7', 'cp1253', 'iso-8859-6', 'cp1256', 'gb18030', 'big5', 'euc-kr', 'cp874',
    'utf-16', 'utf-16be', 'utf-16le', 'utf-32', 'utf-32be', 'utf-32le',
    'iso-8859-8', 'iso-8859-8-e', 'iso-8859-8-i', 'mac_cyrillic', 'mac_greek', 'mac_romanian',
    'mac_turkish', 'mac_iceland', 'mac_centeuro', 'mac_croatian'
]

# Load configuration from YAML file
def load_config() -> dict:
    default_config = {
        'model': 'gpt-4o-mini',
        'temperature': 0.0,
        'kb_to_read': DEFAULT_KB_TO_READ,
        'max_workers': multiprocessing.cpu_count(),
        'api_key': None
    }
    config_path = 'renamenovels.conf.yml'
    if not os.path.exists(config_path):
        try:
            with open(config_path, 'w') as config_file:
                yaml.dump(default_config, config_file)
            logger.info(f"Default configuration file created at '{config_path}'. Please update it with your settings.")
        except Exception as e:
            logger.error(f"Failed to create default config file: {e}")
        return default_config
    else:
        try:
            with open(config_path, 'r') as config_file:
                config = yaml.safe_load(config_file)
                if config is None:
                    logger.warning(f"Config file '{config_path}' is empty. Using default configurations.")
                    return default_config
                return config
        except yaml.YAMLError as e:
            logger.error(f"Error loading config file: {e}")
            return default_config
        except Exception as e:
            logger.error(f"Unexpected error loading config file: {e}")
            return default_config

# Load model pricing info with retry
@retry(stop=stop_after_attempt(10), wait=wait_exponential(multiplier=1, min=4, max=30))
def load_model_pricing() -> Optional[dict]:
    pricing_urls = [
        'https://raw.githubusercontent.com/BerriAI/litellm/main/model_prices_and_context_window.json',
        'https://cdn.jsdelivr.net/gh/BerriAI/litellm@main/model_prices_and_context_window.json',
        'https://raw.fastgit.org/BerriAI/litellm/main/model_prices_and_context_window.json'
    ]
    for pricing_url in pricing_urls:
        try:
            response = requests.get(pricing_url, timeout=10)
            response.raise_for_status()
            logger.info(f"Successfully fetched model pricing information from {pricing_url}")
            return response.json()
        except requests.RequestException as e:
            logger.warning(f"Error fetching model pricing information from {pricing_url}: {e}")
    raise RuntimeError("Failed to fetch model pricing information from all available mirrors.")

# Retry mechanism for making requests to OpenAI API
@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception_type((HTTPError, ConnectionError, Timeout))
)
def make_openai_request(api_key: str, model: str, temperature: float, messages: list) -> dict:
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    data = {
        "model": model,
        "temperature": temperature,
        "messages": messages
    }
    try:
        response = requests.post('https://api.openai.com/v1/chat/completions', headers=headers, json=data, timeout=10)
        response.raise_for_status()
        logger.info("OpenAI API request successful.")
        return response.json()
    except KeyboardInterrupt:
        logger.error("Request interrupted by user (Ctrl+C). Exiting gracefully.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error making OpenAI request: {e}")
        raise

# Function to find all eligible text files in a given folder
def find_text_files(folder_path: Path, recursive: bool) -> list:
    txt_files = []

    if recursive:
        files = folder_path.rglob('*.txt')
    else:
        files = folder_path.glob('*.txt')

    for file_path in files:
        if file_path.is_file() and not file_path.name.startswith('.') and file_path.stat().st_size >= MIN_FILE_SIZE_KB * 1024:
            txt_files.append(file_path)

    return txt_files

# Function to decode file content to UTF-8
def decode_file_content(file_path: Path, kb_to_read: int, icloud_sync: ICloudSync) -> Optional[str]:
    try:
        synced_path = icloud_sync.check_and_wait_for_sync(file_path)
    except ICloudSyncError as e:
        logger.error(f"iCloud synchronization failed for '{file_path}': {e}")
        return None

    try:
        with open(synced_path, 'rb') as f:
            raw_data = f.read(kb_to_read * 1024)
    except PermissionError as e:
        logger.error(f"Permission denied for file '{synced_path}': {e}")
        return None
    except FileNotFoundError as e:
        logger.error(f"File not found '{synced_path}': {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error reading file '{synced_path}': {e}")
        return None

    detected_encoding = chardet.detect(raw_data)['encoding']
    if detected_encoding is None or detected_encoding.lower() not in SUPPORTED_ENCODINGS:
        logger.warning(f"Encoding not detected or unsupported for file '{synced_path}'. Attempting fallback to 'gb18030'.")
        detected_encoding = 'gb18030'  # Fallback to GB18030 if encoding is not detected or is unreliable
    try:
        return raw_data.decode(detected_encoding, errors='replace')
    except (LookupError, UnicodeDecodeError) as e:
        logger.error(f"Error decoding file '{synced_path}': {e}")
        try:
            return raw_data.decode('utf-8', errors='replace')
        except Exception as e:
            logger.error(f"Failed to decode file '{synced_path}' with fallback 'utf-8': {e}")
            return None

# Helper function to sanitize filenames
def sanitize_filename(name: str) -> str:
    """Sanitize the filename by replacing invalid characters with underscores."""
    # Remove any characters not allowed in filenames
    sanitized = re.sub(r'[<>:"/\\|?*\n\r\t]', '_', name)
    # Replace multiple underscores with a single one
    sanitized = re.sub(r'_+', '_', sanitized)
    # Strip leading and trailing underscores or spaces
    sanitized = sanitized.strip(' _')
    return sanitized or "Unnamed"

# Function to rename the original file with novel information
def rename_file(file_path: Path, data: dict):
    title_eng = sanitize_filename(data.get('novel_title_english', 'Unknown Title'))
    author_eng = sanitize_filename(data.get('author_name_english', 'Unknown Author'))
    author_roman = sanitize_filename(data.get('author_name_romanized', 'Unknown'))
    title_orig = sanitize_filename(data.get('novel_title_original', 'Unknown'))
    author_orig = sanitize_filename(data.get('author_name_original', 'Unknown'))

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
def extract_json(response_content: str) -> Optional[dict]:
    """Attempt to extract JSON from a string."""
    try:
        return json.loads(response_content)
    except JSONDecodeError:
        # Attempt to extract JSON using regex
        json_str_match = re.search(r'\{.*\}', response_content, re.DOTALL)
        if json_str_match:
            try:
                return json.loads(json_str_match.group())
            except JSONDecodeError:
                logger.error("Failed to parse JSON from the extracted string.")
                return None
        else:
            logger.error("No JSON object found in the response content.")
            return None

# Global variables for cumulative cost
cumulative_cost = 0.0
cumulative_cost_lock = threading.Lock()

# Helper function to process a single file
def process_single_file(file_path: Path, kb_to_read: int, api_key: str, model: str, temperature: float, pricing_info: dict, icloud_sync: ICloudSync):
    global cumulative_cost
    content = decode_file_content(file_path, kb_to_read, icloud_sync)
    if content is None:
        logger.error(f"Skipping file {file_path} due to decoding errors or iCloud sync failure.")
        return

    prompt = (
        "Given the following content from a novel, perform the following tasks:\n"
        "- Detect the language(s) of the text.\n"
        "- Find the title of the novel and the author's name.\n"
        "- Return the title of the novel and author in the original language, followed by their English translations and the romanization of the author's name.\n"
        "Content:\n" + content[:CONTENT_NUMBER_OF_CHARACTERS_HARD_LIMIT] +
        "\nReturn the response in JSON format as follows:\n"
        "{\n"
        "    \"detected_language\": \"<detected_language>\",\n"
        "    \"novel_title_original\": \"<novel_title_original>\",\n"
        "    \"author_name_original\": \"<author_name_original>\",\n"
        "    \"novel_title_english\": \"<novel_title_english>\",\n"
        "    \"author_name_english\": \"<author_name_english>\",\n"
        "    \"author_name_romanized\": \"<author_name_romanized>\"\n"
        "}\n"
    )

    messages = [{"role": "user", "content": prompt}]
    response = make_openai_request(api_key, model, temperature, messages)

    try:
        choices = response.get('choices')
        if not choices or not isinstance(choices, list):
            logger.error(f"No choices found in OpenAI response: {response}")
            return

        message = choices[0].get('message')
        if not message or 'content' not in message:
            logger.error(f"Message content missing in OpenAI response: {response}")
            return

        response_content = message['content']
        response_data = extract_json(response_content)

        if response_data is None:
            logger.error(f"Failed to extract JSON data from OpenAI response for file {file_path}.")
            return

        # Validate required keys
        required_keys = [
            'detected_language',
            'novel_title_original',
            'author_name_original',
            'novel_title_english',
            'author_name_english',
            'author_name_romanized'
        ]
        if not all(key in response_data for key in required_keys):
            logger.error(f"Missing keys in response data for file {file_path}: {response_data}")
            return

        # Calculate cost
        usage = response.get('usage', {})
        prompt_tokens = usage.get('prompt_tokens', 0)
        completion_tokens = usage.get('completion_tokens', 0)
        total_tokens = usage.get('total_tokens', 0)

        model_pricing = pricing_info.get(model)
        if not model_pricing:
            logger.warning(f"No pricing information found for model '{model}'. Unable to calculate cost.")
            cost = 0.0
        else:
            input_cost_per_token = model_pricing.get('input_cost_per_token', 0.0)
            output_cost_per_token = model_pricing.get('output_cost_per_token', 0.0)
            # Calculate cost
            cost = (prompt_tokens * input_cost_per_token) + (completion_tokens * output_cost_per_token)

        logger.info(f"File '{file_path}' used {total_tokens} tokens. Cost: ${cost:.6f}")

        # Accumulate the cost
        with cumulative_cost_lock:
            cumulative_cost += cost

        rename_file(file_path, response_data)
    except JSONDecodeError as e:
        logger.error(f"JSON decoding error for file {file_path}: {e}")
    except KeyError as e:
        logger.error(f"Missing key in OpenAI response for file {file_path}: {e}")
    except Exception as e:
        logger.error(f"Unexpected error processing file {file_path}: {e}")

# Function to process all files
def process_files(folder_or_path: Path, recursive: bool, kb_to_read: int, api_key: str, model: str, temperature: float, pricing_info: dict, max_workers: int, icloud_sync: ICloudSync):
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
                pricing_info,  # Pass pricing_info to the processing function
                icloud_sync
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

    logger.info(f"Total cost for all transactions: ${cumulative_cost:.6f}")

# Argument parsing
def parse_args():
    parser = argparse.ArgumentParser(
        description=f"Novel Auto Renamer v{VERSION}\nAutomatically rename text files based on extracted novel information.",
        epilog="Example usage:\n  python renamenovels.py /path/to/folder -r -k 50",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('path', type=str, help="Path to the folder containing text files.")
    parser.add_argument('-r', '--recursive', action='store_true', help="Recursively search through subfolders.")
    parser.add_argument('-k', '--kb', type=int, help="Amount of KB to read from the beginning of each file.", default=DEFAULT_KB_TO_READ)
    parser.add_argument('--version', action='version', version=f"Novel Auto Renamer v{VERSION}")
    return parser.parse_args()

# Entry point of the script
def main():
    try:
        args = parse_args()
        kb_to_read = args.kb

        # Load configuration
        config = load_config()
        model = config.get('model', 'gpt-4o-mini')
        temperature = config.get('temperature', 0.0)
        max_workers = config.get('max_workers', multiprocessing.cpu_count())
        kb_to_read = config.get('kb_to_read', kb_to_read)

        # Load API key from config or environment
        api_key = config.get('api_key') or os.getenv('OPENAI_API_KEY')
        if not api_key:
            api_key = getpass.getpass("Please enter your OpenAI API key: ").strip()

        if not api_key:
            logger.error("OpenAI API key is required. Please provide it via config file, environment variable, or input prompt.")
            sys.exit(1)

        # Load model pricing information
        pricing_info = load_model_pricing()

        # Initialize ICloudSync
        icloud_sync = ICloudSync(icloud_enabled=False)

        # Process files
        process_files(
            Path(args.path), 
            recursive=args.recursive, 
            kb_to_read=kb_to_read, 
            api_key=api_key, 
            model=model, 
            temperature=temperature, 
            pricing_info=pricing_info,
            max_workers=max_workers,
            icloud_sync=icloud_sync
        )
    except KeyboardInterrupt:
        logger.info("Script interrupted by user. Exiting gracefully.")
        sys.exit(0)
    except ICloudSyncError as e:
        logger.error(f"iCloud synchronization failed: {e}")
        sys.exit(1)
    except RuntimeError as e:
        logger.error(f"Runtime error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

    