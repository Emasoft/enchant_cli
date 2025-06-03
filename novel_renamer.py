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
from pathlib import Path
from typing import Optional, Dict, Tuple
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from requests.exceptions import HTTPError, ConnectionError, Timeout

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

def sanitize_filename(filename: str) -> str:
    """Sanitize filename by removing/replacing invalid characters."""
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    filename = filename.strip('. ')
    return filename[:255]  # Max filename length

def decode_file_content(file_path: Path, kb_to_read: int = DEFAULT_KB_TO_READ) -> Optional[str]:
    """Decode file content with automatic encoding detection."""
    try:
        # Check file size
        file_size_kb = file_path.stat().st_size / 1024
        if file_size_kb < MIN_FILE_SIZE_KB:
            logging.warning(f"File '{file_path}' is smaller than {MIN_FILE_SIZE_KB} KB. Skipping.")
            return None

        # Read file for encoding detection
        with open(file_path, 'rb') as f:
            raw_data = f.read(kb_to_read * 1024)
        
        # Detect encoding
        detected = chardet.detect(raw_data)
        encoding = detected['encoding']
        confidence = detected['confidence']
        
        if not encoding or confidence < 0.7:
            # Try common Chinese encodings
            for enc in ['gb18030', 'gbk', 'utf-8']:
                try:
                    return raw_data.decode(enc)
                except UnicodeDecodeError:
                    continue
            logging.error(f"Failed to decode '{file_path}' with any common encoding")
            return None
        
        # Decode with detected encoding
        try:
            content = raw_data.decode(encoding)
        except UnicodeDecodeError:
            # Fallback to GB18030
            try:
                content = raw_data.decode('gb18030')
            except UnicodeDecodeError:
                logging.error(f"Failed to decode '{file_path}' even with GB18030")
                return None
        
        # Truncate if too long
        if len(content) > CONTENT_NUMBER_OF_CHARACTERS_HARD_LIMIT:
            content = content[:CONTENT_NUMBER_OF_CHARACTERS_HARD_LIMIT]
        
        return content
        
    except Exception as e:
        logging.error(f"Error reading file '{file_path}': {e}")
        return None

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

def extract_novel_info_from_filename(filename: str) -> Dict[str, str]:
    """
    Extract novel information from standardized filename format.
    Format: "English Title by English Author (Romanized Author) - Original Title by Original Author.txt"
    """
    info = {
        'title_english': '',
        'author_english': '',
        'author_romanized': '',
        'title_original': '',
        'author_original': ''
    }
    
    # Remove extension
    base_filename = Path(filename).stem
    
    # Match the pattern
    pattern = r'^(.+?) by (.+?) \((.+?)\) - (.+?) by (.+?)$'
    match = re.match(pattern, base_filename)
    
    if match:
        info['title_english'] = match.group(1)
        info['author_english'] = match.group(2)
        info['author_romanized'] = match.group(3)
        info['title_original'] = match.group(4)
        info['author_original'] = match.group(5)
    
    return info