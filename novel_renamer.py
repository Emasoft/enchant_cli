#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
novel_renamer.py - Module for renaming Chinese novel files based on AI-extracted metadata
"""

import os
import re
import json
import logging
import requests
import chardet
import yaml
from pathlib import Path
from typing import Optional, Dict, Tuple
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from requests.exceptions import HTTPError, ConnectionError, Timeout
from common_utils import sanitize_filename
from common_file_utils import decode_file_preview

# Constants
MIN_FILE_SIZE_KB = 100
CONTENT_NUMBER_OF_CHARACTERS_HARD_LIMIT = 1500
DEFAULT_KB_TO_READ = 35

SUPPORTED_ENCODINGS = [
    'utf-8', 'gbk', 'gb2312', 'gb18030', 'big5', 'big5hkscs',
    'shift_jis', 'euc_jp', 'euc_kr', 'iso-2022-jp', 'iso-2022-kr',
    'utf-16', 'utf-16-le', 'utf-16-be', 'utf-32', 'utf-32-le', 'utf-32-be'
]

# System prompt for AI
SYSTEM_PROMPT = """
You are a helpful assistant analyzing Chinese novels to extract metadata. Given the beginning of a Chinese novel text, extract:
1. The novel title in the original language (Chinese)
2. The novel title in English translation
3. The author name in the original language
4. The author name in romanized form (pinyin or romaji)
5. The author name in English (if available, otherwise use romanized form)

Respond in JSON format with these exact keys:
- novel_title_original
- novel_title_english  
- author_name_original
- author_name_romanized
- author_name_english

If you cannot determine a value, use "Unknown" as the value.
"""

# Configuration
def load_renamer_config(config_path: Optional[Path] = None) -> Dict:
    """
    Load configuration for novel renamer from YAML file.
    
    Args:
        config_path: Path to config file (default: renamenovels.conf.yml)
    
    Returns:
        Configuration dictionary
    """
    default_config = {
        'model': 'gpt-4o-mini',
        'temperature': 0.0,
        'kb_to_read': DEFAULT_KB_TO_READ,
        'max_workers': None,  # Will use CPU count if None
        'api_key': None
    }
    
    if config_path is None:
        config_path = Path('renamenovels.conf.yml')
    
    if not config_path.exists():
        logging.info(f"Config file not found at {config_path}, using defaults")
        return default_config
    
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
            if config is None:
                return default_config
            # Merge with defaults
            for key, value in default_config.items():
                if key not in config:
                    config[key] = value
            return config
    except Exception as e:
        logging.error(f"Error loading config file: {e}")
        return default_config

# sanitize_filename is now imported from common_utils

def decode_file_content(file_path: Path, kb_to_read: int = DEFAULT_KB_TO_READ) -> Optional[str]:
    """
    Wrapper for backward compatibility - uses common_file_utils.decode_file_preview
    """
    return decode_file_preview(
        file_path,
        kb_to_read=kb_to_read,
        min_file_size_kb=MIN_FILE_SIZE_KB,
        max_chars=CONTENT_NUMBER_OF_CHARACTERS_HARD_LIMIT,
        logger=logging.getLogger(__name__)
    )

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(min=1, max=10),
    retry=retry_if_exception_type((HTTPError, ConnectionError, Timeout))
)
def extract_metadata_with_ai(content: str, api_key: str, model: str = "gpt-4o-mini", temperature: float = 0.0) -> Optional[Dict]:
    """Extract novel metadata using OpenAI API."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Analyze this Chinese novel text and extract the metadata:\n\n{content}"}
        ],
        "temperature": temperature,
        "response_format": {"type": "json_object"}
    }
    
    response = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers=headers,
        json=data,
        timeout=30
    )
    
    response.raise_for_status()
    
    result = response.json()
    try:
        metadata = json.loads(result['choices'][0]['message']['content'])
        return metadata
    except (json.JSONDecodeError, KeyError) as e:
        logging.error(f"Failed to parse AI response: {e}")
        return None

def rename_novel_file(file_path: Path, metadata: Dict) -> Optional[Path]:
    """Rename novel file based on extracted metadata."""
    title_eng = sanitize_filename(metadata.get('novel_title_english', 'Unknown Title'))
    author_eng = sanitize_filename(metadata.get('author_name_english', 'Unknown Author'))
    author_roman = sanitize_filename(metadata.get('author_name_romanized', 'Unknown'))
    title_orig = sanitize_filename(metadata.get('novel_title_original', 'Unknown'))
    author_orig = sanitize_filename(metadata.get('author_name_original', 'Unknown'))
    
    new_name = f"{title_eng} by {author_eng} ({author_roman}) - {title_orig} by {author_orig}.txt"
    new_path = file_path.with_name(new_name)
    
    # Ensure uniqueness
    counter = 1
    while new_path.exists():
        new_name = f"{title_eng} by {author_eng} ({author_roman}) - {title_orig} by {author_orig} ({counter}).txt"
        new_path = file_path.with_name(new_name)
        counter += 1
    
    try:
        file_path.rename(new_path)
        logging.info(f"Renamed '{file_path}' to '{new_path}'")
        return new_path
    except OSError as e:
        logging.error(f"Failed to rename '{file_path}' to '{new_path}': {e}")
        return None

def process_novel_file(file_path: Path, api_key: str, model: str = "gpt-4o-mini", 
                      temperature: float = 0.0, kb_to_read: int = DEFAULT_KB_TO_READ,
                      dry_run: bool = False) -> Tuple[bool, Optional[Path], Optional[Dict]]:
    """
    Process a single novel file for renaming.
    Returns: (success, new_path, metadata)
    """
    # Check if file already follows our naming convention
    if re.match(r'^.+ by .+ \(.+\) - .+ by .+\.txt$', file_path.name):
        logging.info(f"File '{file_path}' already follows naming convention. Skipping.")
        return (True, file_path, None)
    
    # Read and decode file content
    content = decode_file_content(file_path, kb_to_read)
    if not content:
        return (False, None, None)
    
    # Extract metadata using AI
    metadata = extract_metadata_with_ai(content, api_key, model, temperature)
    if not metadata:
        return (False, None, None)
    
    # Rename file (or just return metadata if dry_run)
    if dry_run:
        logging.info(f"[DRY RUN] Would rename '{file_path}' based on metadata: {metadata}")
        return (True, None, metadata)
    else:
        new_path = rename_novel_file(file_path, metadata)
        return (new_path is not None, new_path, metadata)

# extract_novel_info_from_filename functionality is now in common_utils.extract_book_info_from_path

def process_batch_novels(directory: Path, api_key: str, model: str = "gpt-4o-mini",
                        temperature: float = 0.0, kb_to_read: int = DEFAULT_KB_TO_READ,
                        recursive: bool = False, dry_run: bool = False,
                        max_workers: Optional[int] = None) -> Dict[str, Dict]:
    """
    Process multiple novel files in a directory for batch renaming.
    
    Args:
        directory: Directory containing novel files
        api_key: OpenAI API key
        model: Model to use for metadata extraction
        temperature: Model temperature
        kb_to_read: KB to read from each file
        recursive: Whether to search subdirectories
        dry_run: If True, only return metadata without renaming
        max_workers: Max threads for parallel processing (default: CPU count)
    
    Returns:
        Dictionary mapping file paths to results:
        {
            "path/to/file.txt": {
                "success": bool,
                "new_path": Optional[Path],
                "metadata": Optional[Dict],
                "error": Optional[str]
            }
        }
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed
    import multiprocessing
    
    if max_workers is None:
        max_workers = multiprocessing.cpu_count()
    
    # Find all text files
    if recursive:
        txt_files = list(directory.rglob('*.txt'))
    else:
        txt_files = list(directory.glob('*.txt'))
    
    # Filter out small files
    eligible_files = []
    for file_path in txt_files:
        if file_path.is_file() and not file_path.name.startswith('.'):
            try:
                if file_path.stat().st_size >= MIN_FILE_SIZE_KB * 1024:
                    eligible_files.append(file_path)
            except OSError:
                logging.warning(f"Could not access file: {file_path}")
    
    if not eligible_files:
        logging.warning("No eligible text files found to process.")
        return {}
    
    logging.info(f"Processing {len(eligible_files)} files with {max_workers} workers")
    
    results = {}
    
    def process_file_wrapper(file_path):
        """Wrapper to catch exceptions and return structured result"""
        try:
            success, new_path, metadata = process_novel_file(
                file_path, api_key, model, temperature, kb_to_read, dry_run
            )
            return file_path, {
                "success": success,
                "new_path": new_path,
                "metadata": metadata,
                "error": None
            }
        except Exception as e:
            logging.error(f"Error processing {file_path}: {e}")
            return file_path, {
                "success": False,
                "new_path": None,
                "metadata": None,
                "error": str(e)
            }
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_file = {
            executor.submit(process_file_wrapper, file_path): file_path
            for file_path in eligible_files
        }
        
        for future in as_completed(future_to_file):
            file_path, result = future.result()
            results[str(file_path)] = result
    
    # Log summary
    successful = sum(1 for r in results.values() if r["success"])
    logging.info(f"Batch processing complete: {successful}/{len(eligible_files)} files renamed successfully")
    
    return results