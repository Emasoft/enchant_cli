#!/usr/bin/env python3
#
# Copyright (c) 2024 Emasoft
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0

from __future__ import annotations

import codecs
import functools
import html
import re
import string
import unicodedata
from pathlib import Path

from chardet.universaldetector import UniversalDetector

# CHINESE PUNCTUATION sets.
SENTENCE_ENDING = {'。', '！', '？', '…', '.', ';', '；'}
CLOSING_QUOTES = {'」', '”', '】', '》'}
NON_BREAKING = {'，', '、'}
ALL_PUNCTUATION = SENTENCE_ENDING | CLOSING_QUOTES | NON_BREAKING

# Define explicit sets for Chinese and English punctuation.
CHINESE_PUNCTUATION = {'。', '！', '？', '…', '；', '，', '、', '」', '”', '】', '》'}
ENGLISH_PUNCTUATION = {'.', ',', '!', '?', ';', ':'}

# PARAGRAPH DELIMITERS (characters that denote new paragraphs)
PARAGRAPH_DELIMITERS = {
    "\n",      # Line Feed
    "\v",      # Vertical Tab
    "\f",      # Form Feed
    "\x1c",    # File Separator
    "\x1d",    # Group Separator
    "\x1e",    # Record Separator
    "\x85",    # Next Line (C1 Control Code)
    "\u2028",  # Line Separator
    "\u2029"   # Paragraph Separator
}

# Characters that are allowed unlimited repetition by default.
PRESERVE_UNLIMITED = {
    ' ', '.', '\n', '\r', '\t', '(', ')', '[', ']',
    '+', '-', '_', '=', '/', '|', '\\', '*', '%', '#', '@',
    '~', '<', '>', '^', '&', '°', '…',
    '—', '•', '$'
}.union(PARAGRAPH_DELIMITERS)

# Precompile the regular expression pattern for matching repeated characters.
_repeated_chars = re.compile(r'(.)\1+')

# Precompute allowed ASCII characters (letters, digits, punctuation)
ALLOWED_ASCII = set(string.ascii_letters + string.digits + string.punctuation)

# Precompiled regex for URLs and emails
_email_re = re.compile(r"[a-zA-Z0-9_\.\+\-]+\@[a-zA-Z0-9_\.\-]+\.[a-zA-Z]+")
_url_re = re.compile(r"https?://(-\.)?([^\s/?\.#]+\.?)+(/[^\s]*)?")
# Test comment to trigger pre-commit version bump
_markdown_re = re.compile(r".*("
                          r"\*(.*)\*|"
                          r"_(.*)_|" # Added escaped brackets for link text
                          r"\[(.*)\]\((.*)\)|"
                          r"`(.*)`|"
                          r"```(.*)```"
                          r").*")


def clean(text: str) -> str:
    """
    Clean the input text:
      - Ensures it is a string.
      - Strips leading and trailing **space characters only**.
      - Preserves all control characters (e.g., tabs, newlines, carriage returns).
    """
    if not isinstance(text, str):
        raise TypeError("Input must be a string")
    return text.lstrip(' ').rstrip(' ')

def replace_repeated_chars(text: str, chars) -> str:
    """
    Replace any sequence of repeated occurrences of each character in `chars`
    with a single occurrence. For example, "！！！！" becomes "！".
    """
    for char in chars:
        if char not in PRESERVE_UNLIMITED:
            # Escape the character to handle any regex special meaning.
            pattern = re.escape(char) + r'{2,}'
            text = re.sub(pattern, char, text)
    return text

def limit_repeated_chars(text, force_chinese=False, force_english=False):
    """
    Normalize repeated character sequences in the input text.
    (See docstring in original files for detailed rules table)
    """
    def limiter(match):
        seq = match.group(0)
        char = seq[0]
        if char.isnumeric():
            return seq
        if force_chinese and char in CHINESE_PUNCTUATION:
            return char
        if force_english and char in ENGLISH_PUNCTUATION:
            return char
        if char in PRESERVE_UNLIMITED:
            return seq
        elif char in ALL_PUNCTUATION:
            return char
        else:
            return seq if len(seq) <= 3 else char * 3
    return _repeated_chars.sub(limiter, text)

def extract_code_blocks(html_str: str):
    """
    Extract <pre> and <code> blocks from the HTML and replace them with placeholders.
    Returns the modified HTML and a list of block code contents.
    """
    block_codes = []
    def repl(match):
        code_content = match.group(2)
        placeholder = f"@@CODEBLOCK{len(block_codes)}@@"
        block_codes.append(code_content)
        return placeholder
    modified_html = re.sub(
        r'<\s*(pre|code)[^>]*>(.*?)<\s*/\s*\1\s*>',
        repl,
        html_str,
        flags=re.DOTALL | re.IGNORECASE
    )
    return modified_html, block_codes

def extract_inline_code(text: str):
    """
    Extract inline code spans delimited by single backticks and replace them with placeholders.
    Returns the modified text and a list of inline code contents.
    """
    inline_codes = []
    def repl(match):
        code_content = match.group(1)
        placeholder = f"@@INLINECODE{len(inline_codes)}@@"
        inline_codes.append(code_content)
        return placeholder
    modified_text = re.sub(r'`([^`]+)`', repl, text)
    return modified_text, inline_codes

def remove_html_comments(html_str: str) -> str:
    """Remove HTML comments."""
    return re.sub(r'<!--.*?-->', '', html_str, flags=re.DOTALL)

def remove_script_and_style(html_str: str) -> str:
    """Remove <script> and <style> tags along with their entire content."""
    html_str = re.sub(
        r'<\s*script[^>]*>.*?<\s*/\s*script\s*>',
        '',
        html_str,
        flags=re.DOTALL | re.IGNORECASE
    )
    html_str = re.sub(
        r'<\s*style[^>]*>.*?<\s*/\s*style\s*>',
        '',
        html_str,
        flags=re.DOTALL | re.IGNORECASE
    )
    return html_str

def replace_block_tags(html_str: str) -> str:
    """Replace block-level HTML tags with whitespace markers."""
    html_str = remove_html_comments(html_str)
    html_str = remove_script_and_style(html_str)
    html_str = re.sub(r'<\s*/?\s*pre[^>]*>', '', html_str, flags=re.IGNORECASE)
    replacements = [
        (r'<\s*/\s*p\s*>', '\n'), (r'<\s*p[^>]*>', '\n'),
        (r'<\s*br\s*/?\s*>', '\n'),
        (r'<\s*/\s*div\s*>', '\n'),
        (r'<\s*li[^>]*>', '  - '), (r'<\s*/\s*li\s*>', '\n'),
        (r'<\s*/\s*tr\s*>', '\n'),
        (r'<\s*/\s*td\s*>', '\t'), (r'<\s*/\s*th\s*>', '\t'),
        (r'<\s*blockquote[^>]*>', '\n'), (r'<\s*/\s*blockquote\s*>', '\n'),
        (r'<\s*h[1-6][^>]*>', '\n'), (r'<\s*/\s*h[1-6]\s*>', '\n'),
    ]
    for pattern, repl in replacements:
        html_str = re.sub(pattern, repl, html_str, flags=re.IGNORECASE)
    return html_str

def remove_remaining_tags(html_str: str) -> str:
    """Remove any remaining valid HTML tags."""
    pattern = r'<\s*(\/)?\s*([a-zA-Z][a-zA-Z0-9]*)(?:\s+[^<>]*?)?\s*(\/?)\s*>'
    return re.sub(pattern, '', html_str)

def unescape_non_code_with_placeholders(text: str) -> str:
    """Unescape HTML entities in text that is not inside a code block."""
    pattern = r'(@@CODEBLOCK\d+@@|@@INLINECODE\d+@@)'
    parts = re.split(pattern, text)
    for i, part in enumerate(parts):
        if re.fullmatch(pattern, part):
            continue
        else:
            parts[i] = html.unescape(part)
    return ''.join(parts)

def remove_html_markup(html_str: str) -> str:
    """Clean HTML text, preserving code blocks and inline code."""
    html_modified, block_codes = extract_code_blocks(html_str)
    html_modified, inline_codes = extract_inline_code(html_modified)
    html_modified = remove_html_comments(html_modified)
    html_modified = remove_script_and_style(html_modified)
    html_modified = replace_block_tags(html_modified)
    html_modified = remove_remaining_tags(html_modified)
    html_modified = unescape_non_code_with_placeholders(html_modified)
    for i, code in enumerate(inline_codes):
        placeholder = f"@@INLINECODE{i}@@"
        html_modified = html_modified.replace(placeholder, f"`{code}`")
    for i, code in enumerate(block_codes):
        placeholder = f"@@CODEBLOCK{i}@@"
        html_modified = html_modified.replace(placeholder, code)
    return html_modified

def remove_excess_empty_lines(txt: str) -> str:
    """Replace 5 or more consecutive newline characters with exactly 4."""
    return re.sub(r'\n{5,}', '\n\n\n\n', txt)

def normalize_spaces(text: str) -> str:
    """Normalize spaces within lines and preserve empty lines."""
    lines = text.split('\n')
    normalized_lines = []
    for line in lines:
        stripped_line = clean(line)
        if stripped_line:
            normalized_line = ' '.join(stripped_line.split())
            normalized_lines.append(normalized_line)
        else:
            normalized_lines.append('')
    return '\n'.join(normalized_lines)

def strip_urls(input_text: str) -> str:
    """Strip URLs and emails from a string."""
    input_text = _url_re.sub("", input_text)
    input_text = _email_re.sub("", input_text)
    return input_text

def is_markdown(input_text: str) -> bool:
    """Check if a string contains common Markdown syntax."""
    # Check before stripping URLs, as stripping can break link syntax
    return bool(_markdown_re.match(input_text.replace("\n", "")))

def detect_file_encoding(file_path: Path) -> str | None:
    """Detect file encoding using chardet."""
    detector = UniversalDetector()
    with file_path.open('rb') as f:
        for line in f:
            detector.feed(line)
            if detector.done:
                break
        detector.close()
        result = detector.result
        if result and result['confidence'] > 0.8:
            return result['encoding']
        return None # Or return a default like 'utf-8' or 'GB18030'

@functools.cache
def is_latin_char(char: str) -> bool:
    """Check if a non-ASCII character belongs to the Latin script."""
    try:
        return "LATIN" in unicodedata.name(char)
    except ValueError:
        return False

def is_latin_charset(text: str, threshold: float = 0.3) -> bool:
    """Determine if text is primarily Latin-based."""
    total_count = 0
    latin_count = 0
    for char in text:
        if char.isspace():
            continue
        total_count += 1
        cp = ord(char)
        if cp < 128:
            if char in ALLOWED_ASCII:
                latin_count += 1
            continue
        if is_latin_char(char):
            latin_count += 1
    if latin_count == 0:
        return False
    non_latin_count = total_count - latin_count
    ratio = non_latin_count / latin_count
    return ratio < threshold

def quick_replace(text_content: str, original: str, substitution: str, case_insensitive=True) -> str:
    """Perform case-sensitive or insensitive string replacement."""
    if case_insensitive:
        return re.sub("(?i)" + re.escape(original), lambda m: f"{substitution}", text_content)
    else:
        return re.sub(re.escape(original), lambda m: f"{substitution}", text_content)

def clean_adverts(text_content: str) -> str:
    """Remove common advertisement patterns found in Chinese web novels."""
    spam1regex = [
        r"吉米小说网\s*[（(]www\.(34gc|jimixs)\.(net|com)[）)]\s*txt电子书下载",
        r"吉米小说网\s*[（(]Www\.(34gc|jimixs)\.(net|com)[）)]\s*免费TXT小说下载",
        r"吉米小说网\s*[（(]www\.jimixs\.com[）)]\s*免费电子书下载",
        r"本电子书由果茶小说网\s*[（(]www\.34gc\.(net|com)[）)]\s*网友上传分享，网址\:http\:\/\/www\.34gc\.net",
        r"(本电子书由){0,1}[吉米小说网果茶]{4,6}\s*[（(]www\.(34gc|jimixs)\.(net|com)[）)]\s*[tx电子书下载网友上传分免费小说在线阅读说下载享]{4,10}",
        r"[,;\.]{0,1}\s*网址\:www\.(34gc|jimixs)\.(net|com)",
        r"吉米小说网\s*[（(]www\.(34gc|jimixs)\.(net|com)[）)]",
        r"本电子书由果茶小说网",
        r"吉米小说网\s*[（(]www\.(34gc|jimixs)\.(net|com)[）)]",
        r"(http\:\/\/){0,1}www\.(34g|jimixs)\.(net|com)",
    ]
    subst = " "
    for regex_pattern in spam1regex:
        text_content = re.sub(regex_pattern, subst, text_content, 0, re.MULTILINE | re.IGNORECASE | re.UNICODE)

    open_parh_chinese = '（'
    closed_parh_chinese = '）'
    text_content = quick_replace(text_content, open_parh_chinese, '(')
    text_content = quick_replace(text_content, closed_parh_chinese, ')')
    return text_content

def flush_buffer(buffer: str, paragraphs: list) -> str:
    """Normalize and append buffer content to paragraphs list."""
    buffer = clean(buffer)
    if buffer:
        buffer = re.sub(' +', ' ', buffer)
        paragraphs.append(buffer + "\n\n")
    return ""

def split_on_punctuation_contextual(text: str) -> list:
    """Splits Chinese text into paragraphs based on punctuation and context."""
    if not isinstance(text, str):
        raise TypeError("Input text must be a string")

    # Local definitions for clarity within this function
    SENTENCE_ENDING_LOCAL = {'。', '！', '？', '…', '.', ';', '；'}
    CLOSING_QUOTES_LOCAL = {'」', '”', '】', '》'}
    NON_BREAKING_LOCAL = {'，', '、'}
    ALL_PUNCTUATION_LOCAL = SENTENCE_ENDING_LOCAL | CLOSING_QUOTES_LOCAL | NON_BREAKING_LOCAL
    PARAGRAPH_START_TRIGGERS = {'\n', '“', '【', '《', '「'}

    text = clean_adverts(text)
    text = clean(text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(' +', ' ', text)
    text = replace_repeated_chars(text, ALL_PUNCTUATION_LOCAL)
    text = replace_repeated_chars(text, PARAGRAPH_DELIMITERS)

    paragraphs = []
    buffer = ""
    length = len(text)
    i = 0
    while i < length:
        char = text[i]
        next_char = text[i+1] if i+1 < length else None
        next_next_char = text[i+2] if i+2 < length else None

        buffer += char # Add current char

        if char in PARAGRAPH_DELIMITERS:
            # If we hit a paragraph delimiter, flush the buffer (excluding the delimiter itself if it's just added)
            buffer_to_flush = buffer[:-1] if buffer.endswith(char) else buffer
            buffer = flush_buffer(buffer_to_flush, paragraphs)
            i += 1
            continue

        if char in SENTENCE_ENDING_LOCAL:
            # Check if next char triggers a new paragraph or is non-breaking
            should_split = True
            if next_char is None: # End of text
                should_split = True
            elif next_char in PARAGRAPH_START_TRIGGERS or next_char in PARAGRAPH_DELIMITERS:
                should_split = True
            elif next_char == ' ' and next_next_char in PARAGRAPH_START_TRIGGERS:
                should_split = True
            elif next_char in CLOSING_QUOTES_LOCAL or next_char in NON_BREAKING_LOCAL:
                should_split = False # Keep quote or comma with sentence
            # Add other conditions where split should NOT happen immediately after sentence end?

            if should_split:
                buffer = flush_buffer(buffer, paragraphs)
            i += 1
            continue

        if char in NON_BREAKING_LOCAL:
            # Just add to buffer, no special splitting logic here
            i += 1
            continue

        # Handle closing quotes after potentially splitting based on previous char
        if char in CLOSING_QUOTES_LOCAL:
             # Check if next char triggers a new paragraph
             if (next_char in PARAGRAPH_START_TRIGGERS) or (next_char == ' ' and next_next_char in PARAGRAPH_START_TRIGGERS):
                 buffer = flush_buffer(buffer, paragraphs)
             i += 1
             continue

        # If it's none of the special characters, just increment i
        i += 1

    if clean(buffer):
        paragraphs.append(re.sub(' +', ' ', clean(buffer)) + "\n\n")

    return paragraphs

def decode_input_file_content(input_file: Path, logger) -> str:
    """Read file content, detecting encoding."""
    encoding = detect_file_encoding(input_file)
    logger.debug(f"\nDetected encoding: {encoding}")

    try:
        with codecs.open(input_file, 'r', encoding=encoding) as f:
            content = f.read()
    except Exception as e:
        logger.debug(f"\nError reading file '{input_file!s}' with detected encoding {encoding}: {e}")
        logger.debug("Falling back to GB18030 encoding.")
        encoding = 'GB18030'
        try:
            with codecs.open(input_file, 'r', encoding=encoding) as f:
                content = f.read()
        except Exception as e:
            logger.debug(f"\nError reading file '{input_file!s}' with GB18030: {e}")
            logger.debug("Attempting decode with detected encoding, replacing errors.")
            try:
                with open(input_file, 'rb') as file:
                    content_bytes = file.read()
                content = content_bytes.decode(encoding or 'utf-8', errors='replace') # Use utf-8 if detection failed
            except Exception as final_e:
                 logger.error(f"\nFATAL: Could not decode file '{input_file!s}' even with error replacement: {final_e}")
                 raise OSError(f"Could not decode file {input_file}") from final_e

    return content

# Function to extract title and author info from foreign novels filenames (chinese, japanese, etc.)
def foreign_book_title_splitter(filename):
    """
    Parse filenames with structure:
    "Translated Title by Translated Author (Romanization) - Original Title by Original Author"
    Returns tuple:
    (translated_title, original_title, transliterated_title, trans_author, orig_author, translit_author)
    """
    base_filename = Path(filename).stem

    # Split on ' - ' (with spaces) for main parts
    if ' - ' in base_filename:
        translated_part, original_part = re.split(r'\s+-\s+', base_filename, 1)
    else:
        translated_part, original_part = base_filename, ''

    # Helper to extract title and author
    def parse_part(part: str):
        # Remove romanization in parentheses for author
        # Split on ' by ' not inside parentheses
        match = re.match(r"^(.*?) by (.*?)(?: \([^)]+\))?$", part)
        if match:
            title = match.group(1)
            author = match.group(2)
            return title, author
        else:
            # If ' by ' not found, assume the whole part is the title
            return part, "Unknown Author"

    translated_title, translated_author = parse_part(translated_part)
    if original_part:
        original_title, original_author = parse_part(original_part)
    else:
        # If no original part, assume original is same as translated
        original_title, original_author = translated_title, translated_author

    # Return structure: (trans_title, orig_title, translit_title, trans_author, orig_author, translit_author)
    # We don't have transliterated info from filename, so leave empty
    return (
        translated_title.strip(),
        original_title.strip(),
        "", # transliterated_title
        translated_author.strip(),
        original_author.strip(),
        "" # transliterated_author
    )
