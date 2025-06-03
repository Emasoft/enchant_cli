#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
common_text_utils.py - Shared text processing utilities for EnChANT modules

This module contains text cleaning, HTML processing, and character manipulation
functions used across multiple EnChANT modules.
"""

import re
import html
import string
import unicodedata
from typing import List, Tuple, Set, Optional

# Constants from original modules
PRESERVE_UNLIMITED = {
    '　', '\u3000', '\u2002', '\u2003', '\u2004', '\u2005', '\u2006', '\u2007', '\u2008', 
    '\u2009', '\u200a', '\u200b', '\u2028', '\u2029', '\u202f', '\u205f', '\ufeff',
    '\u00a0', '\u1680', '\u180e', '\t', '\n', '\r', '\v', '\f', '\x1c', '\x1d', '\x1e', 
    '\x1f', '\x85', '\xa0', ' ', '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', 
    ',', '-', '.', '/', ':', ';', '<', '=', '>', '?', '@', '[', '\\', ']', '^', '_', 
    '`', '{', '|', '}', '~'
}

# Punctuation sets for different languages
CHINESE_PUNCTUATION = {
    '。', '，', '、', '；', '：', '？', '！', '"', '"', ''', ''', '（', '）', 
    '【', '】', '《', '》', '—', '…', '·', '￥', '¥'
}

ENGLISH_PUNCTUATION = {
    '.', ',', ';', ':', '?', '!', '"', "'", '(', ')', '[', ']', 
    '{', '}', '-', '—', '…', '/', '\\', '@', '#', '$', '%', '^', 
    '&', '*', '+', '=', '|', '~', '`', '<', '>'
}

ALL_PUNCTUATION = CHINESE_PUNCTUATION | ENGLISH_PUNCTUATION


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
        # Escape the character to handle any regex special meaning.
        pattern = re.escape(char) + r'{2,}'
        text = re.sub(pattern, char, text)
    return text


def limit_repeated_chars(text, force_chinese=False, force_english=False):
    """
    Normalize repeated character sequences in the input text.

    This function processes the text by applying the following rules:

    ╔════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╗
    ║ List of Characters                           │ Max Repetitions     │ Example Input           │ Example Output          ║
    ╠════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╣
    ║ PRESERVE_UNLIMITED (default)                 │ ∞                   │ "#####", "....."        │ "#####", "....."        ║
    ║ (whitespace, control, symbols, etc.)         │                     │                         │                         ║
    ╠════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╣
    ║ ALL_PUNCTUATION (non-exempt)                 │ 1                   │ "！！！！！！"            │ "！"                     ║
    ╠═════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╣
    ║ Other characters (e.g. letters)              │ 3                   │ "aaaaa"                 │ "aaa"                    ║
    ╠═════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╣
    ║ Numbers (all numeric characters in all lang) │ ∞                   │ "ⅣⅣⅣⅣ", "111111"      │ "ⅣⅣⅣⅣ", "111111"       ║
    ╠═════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╣
    ║ Chinese punctuation (if force_chinese=True)  │ 1                  │ "！！！！"                │ "！"                      ║
    ╠═════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╣
    ║ English punctuation (if force_english=True)  │ 1                  │ "!!!!!"                  │ "!"                      ║
    ╚═════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╝

    Optional Parameters:
      force_chinese (bool): If True, forces all Chinese punctuation characters to be repeated only once.
      force_english (bool): If True, forces all English punctuation characters to be repeated only once.
    """
    
    # Determine which punctuation to limit
    limit_to_one = ALL_PUNCTUATION.copy()
    
    # Adjust based on force options
    if force_chinese:
        limit_to_one |= CHINESE_PUNCTUATION
    if force_english:
        limit_to_one |= ENGLISH_PUNCTUATION
    
    # Remove exemptions
    limit_to_one -= PRESERVE_UNLIMITED
    
    # Process the text character by character
    result = []
    i = 0
    while i < len(text):
        char = text[i]
        
        # Count consecutive occurrences
        count = 1
        while i + count < len(text) and text[i + count] == char:
            count += 1
        
        # Apply rules
        if char in limit_to_one:
            # Limit to 1 occurrence
            result.append(char)
        elif char.isnumeric() or char in PRESERVE_UNLIMITED:
            # Preserve all occurrences
            result.append(char * count)
        else:
            # Limit to 3 occurrences for other characters
            result.append(char * min(count, 3))
        
        i += count
    
    return ''.join(result)


# HTML Processing Functions

def extract_code_blocks(html_str: str) -> Tuple[str, List[str]]:
    """
    Extract <pre> and <code> blocks from HTML and replace with placeholders.
    Returns modified HTML and list of extracted code blocks.
    """
    code_blocks = []
    counter = 0
    
    def replace_code(match):
        nonlocal counter
        code_blocks.append(match.group(0))
        placeholder = f"__CODE_BLOCK_{counter}__"
        counter += 1
        return placeholder
    
    # Extract <pre> blocks
    html_str = re.sub(r'<pre\b[^>]*>.*?</pre>', replace_code, html_str, flags=re.DOTALL | re.IGNORECASE)
    # Extract <code> blocks
    html_str = re.sub(r'<code\b[^>]*>.*?</code>', replace_code, html_str, flags=re.DOTALL | re.IGNORECASE)
    
    return html_str, code_blocks


def extract_inline_code(text: str) -> Tuple[str, List[str]]:
    """
    Extract inline code (backtick delimited) and replace with placeholders.
    Returns modified text and list of extracted code snippets.
    """
    code_snippets = []
    counter = 0
    
    def replace_inline(match):
        nonlocal counter
        code_snippets.append(match.group(0))
        placeholder = f"__INLINE_CODE_{counter}__"
        counter += 1
        return placeholder
    
    # Extract inline code (single backticks)
    text = re.sub(r'`[^`]+`', replace_inline, text)
    
    return text, code_snippets


def remove_html_comments(html_str: str) -> str:
    """Remove HTML comments from the string."""
    return re.sub(r'<!--.*?-->', '', html_str, flags=re.DOTALL)


def remove_script_and_style(html_str: str) -> str:
    """Remove <script> and <style> tags and their content."""
    html_str = re.sub(r'<script\b[^>]*>.*?</script>', '', html_str, flags=re.DOTALL | re.IGNORECASE)
    html_str = re.sub(r'<style\b[^>]*>.*?</style>', '', html_str, flags=re.DOTALL | re.IGNORECASE)
    return html_str


def replace_block_tags(html_str: str) -> str:
    """Replace block-level tags with appropriate whitespace markers."""
    # Tags that should be replaced with double newline
    block_tags = ['p', 'div', 'section', 'article', 'header', 'footer', 'main', 'aside',
                  'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'li', 'blockquote',
                  'pre', 'table', 'tr', 'td', 'th', 'form', 'fieldset', 'legend']
    
    for tag in block_tags:
        html_str = re.sub(f'</{tag}>', '\n\n', html_str, flags=re.IGNORECASE)
        html_str = re.sub(f'<{tag}\\b[^>]*>', '', html_str, flags=re.IGNORECASE)
    
    # <br> tags should be single newline
    html_str = re.sub(r'<br\s*/?>', '\n', html_str, flags=re.IGNORECASE)
    
    return html_str


def remove_remaining_tags(html_str: str) -> str:
    """Remove any remaining HTML tags (but preserve content)."""
    # Only remove valid HTML tags (not math expressions like <x>)
    return re.sub(r'</?[a-zA-Z][^>]*>', '', html_str)


def unescape_non_code_with_placeholders(text: str) -> str:
    """Unescape HTML entities except in code placeholders."""
    pattern = r'__(?:CODE_BLOCK|INLINE_CODE)_\d+__'
    parts = re.split(pattern, text)
    for i, part in enumerate(parts):
        if re.fullmatch(pattern, part):
            continue  # Leave code placeholders intact
        else:
            parts[i] = html.unescape(part)
    return ''.join(parts)


def remove_html_markup(html_str: str) -> str:
    """
    Clean the HTML text by performing the following steps:
      1. Extract block-level code (<pre> and <code>) and replace them with placeholders.
      2. Extract inline code spans (delimited by single backticks) and replace them with placeholders.
      3. Remove HTML comments, <script>, and <style> blocks (including their content).
      4. Replace block-level tags (like <p>, <br>, <div>, etc.) with whitespace markers.
      5. Remove any remaining HTML tags (only valid tags are removed, protecting math/code).
      6. Unescape HTML entities outside code placeholders.
      7. Restore the inline code placeholders.
      8. Restore the block-level code placeholders.
      
    This process preserves spacing (including repeated spaces, tabs, newlines),
    leaves literal characters (including < or >) intact in code or math expressions,
    and unescapes HTML entities in regular text.
    """
    # Step 1: Extract block-level code
    html_modified, block_codes = extract_code_blocks(html_str)
    
    # Step 2: Extract inline code spans
    html_modified, inline_codes = extract_inline_code(html_modified)
    
    # Step 3: Remove unwanted content
    html_modified = remove_html_comments(html_modified)
    html_modified = remove_script_and_style(html_modified)
    
    # Step 4: Replace block tags with whitespace
    html_modified = replace_block_tags(html_modified)
    
    # Step 5: Remove remaining tags
    html_modified = remove_remaining_tags(html_modified)
    
    # Step 6: Unescape HTML entities (except in placeholders)
    html_modified = unescape_non_code_with_placeholders(html_modified)
    
    # Step 7: Restore inline code
    for i, code in enumerate(inline_codes):
        html_modified = html_modified.replace(f"__INLINE_CODE_{i}__", code)
    
    # Step 8: Restore block code
    for i, code in enumerate(block_codes):
        html_modified = html_modified.replace(f"__CODE_BLOCK_{i}__", code)
    
    return html_modified