#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
# - Initial creation from common_text_utils.py refactoring
# - Extracted HTML processing functions
# - Contains functions for cleaning and processing HTML content
#

"""
html_processing.py - HTML processing utilities for EnChANT modules
==================================================================

This module contains HTML cleaning and processing functions used for
extracting text from HTML content while preserving code blocks and
important formatting.
"""

import re
import html


def extract_code_blocks(html_str: str) -> tuple[str, list[str]]:
    """
    Extract <pre> and <code> blocks from HTML and replace with placeholders.

    Args:
        html_str: HTML string to process

    Returns:
        Tuple of (modified HTML with placeholders, list of extracted code blocks)
    """
    code_blocks = []
    counter = 0

    def replace_code(match: re.Match[str]) -> str:
        nonlocal counter
        code_blocks.append(match.group(0))
        placeholder = f"__CODE_BLOCK_{counter}__"
        counter += 1
        return placeholder

    # Extract <pre> blocks
    html_str = re.sub(
        r"<pre\b[^>]*>.*?</pre>",
        replace_code,
        html_str,
        flags=re.DOTALL | re.IGNORECASE,
    )
    # Extract <code> blocks
    html_str = re.sub(
        r"<code\b[^>]*>.*?</code>",
        replace_code,
        html_str,
        flags=re.DOTALL | re.IGNORECASE,
    )

    return html_str, code_blocks


def extract_inline_code(text: str) -> tuple[str, list[str]]:
    """
    Extract inline code (backtick delimited) and replace with placeholders.

    Args:
        text: Text containing inline code

    Returns:
        Tuple of (modified text with placeholders, list of extracted code snippets)
    """
    code_snippets = []
    counter = 0

    def replace_inline(match: re.Match[str]) -> str:
        nonlocal counter
        code_snippets.append(match.group(0))
        placeholder = f"__INLINE_CODE_{counter}__"
        counter += 1
        return placeholder

    # Extract inline code (single backticks)
    text = re.sub(r"`[^`]+`", replace_inline, text)

    return text, code_snippets


def remove_html_comments(html_str: str) -> str:
    """
    Remove HTML comments from the string.

    Args:
        html_str: HTML string containing comments

    Returns:
        HTML string with comments removed
    """
    return re.sub(r"<!--.*?-->", "", html_str, flags=re.DOTALL)


def remove_script_and_style(html_str: str) -> str:
    """
    Remove <script> and <style> tags and their content.

    Args:
        html_str: HTML string containing script/style tags

    Returns:
        HTML string with script and style tags removed
    """
    html_str = re.sub(r"<script\b[^>]*>.*?</script>", "", html_str, flags=re.DOTALL | re.IGNORECASE)
    html_str = re.sub(r"<style\b[^>]*>.*?</style>", "", html_str, flags=re.DOTALL | re.IGNORECASE)
    return html_str


def replace_block_tags(html_str: str) -> str:
    """
    Replace block-level tags with appropriate whitespace markers.

    Args:
        html_str: HTML string to process

    Returns:
        String with block tags replaced by whitespace
    """
    # First, remove comments, scripts, and style blocks.
    html_str = remove_html_comments(html_str)
    html_str = remove_script_and_style(html_str)

    # Remove <pre> tags (their content is already extracted).
    html_str = re.sub(r"<\s*/?\s*pre[^>]*>", "", html_str, flags=re.IGNORECASE)

    replacements = [
        # Paragraphs: simulate a paragraph break.
        (r"<\s*/\s*p\s*>", "\n"),
        (r"<\s*p[^>]*>", "\n"),
        # Line breaks: convert to newline.
        (r"<\s*br\s*/?\s*>", "\n"),
        # Divisions: add newline after closing div.
        (r"<\s*/\s*div\s*>", "\n"),
        # List items: prefix with a bullet and add newline.
        (r"<\s*li[^>]*>", "  - "),
        (r"<\s*/\s*li\s*>", "\n"),
        # Table rows: newline after each row.
        (r"<\s*/\s*tr\s*>", "\n"),
        # Table cells: add a tab after each cell.
        (r"<\s*/\s*td\s*>", "\t"),
        (r"<\s*/\s*th\s*>", "\t"),
        # Blockquotes: add newlines.
        (r"<\s*blockquote[^>]*>", "\n"),
        (r"<\s*/\s*blockquote\s*>", "\n"),
        # Headers (h1-h6): newlines before and after.
        (r"<\s*h[1-6][^>]*>", "\n"),
        (r"<\s*/\s*h[1-6]\s*>", "\n"),
    ]
    for pattern, repl in replacements:
        html_str = re.sub(pattern, repl, html_str, flags=re.IGNORECASE)
    return html_str


def remove_remaining_tags(html_str: str) -> str:
    """
    Remove any remaining HTML tags (but preserve content).

    Only removes valid HTML tags, not math expressions like <x>.

    Args:
        html_str: HTML string with remaining tags

    Returns:
        String with tags removed
    """
    # Only remove valid HTML tags (not math expressions like <x>)
    return re.sub(r"</?[a-zA-Z][^>]*>", "", html_str)


def unescape_non_code_with_placeholders(text: str) -> str:
    """
    Unescape HTML entities except in code placeholders.

    Args:
        text: Text with HTML entities and code placeholders

    Returns:
        Text with entities unescaped (except in placeholders)
    """
    pattern = r"(__(?:CODE_BLOCK|INLINE_CODE)_\d+__)"
    parts = re.split(pattern, text)
    for i, part in enumerate(parts):
        if re.fullmatch(r"__(?:CODE_BLOCK|INLINE_CODE)_\d+__", part):
            continue  # Leave code placeholders intact
        else:
            parts[i] = html.unescape(part)
    return "".join(parts)


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

    Args:
        html_str: HTML string to clean

    Returns:
        Cleaned text with HTML markup removed
    """
    # Step 1: Extract block-level code
    html_modified, block_codes = extract_code_blocks(html_str)

    # Step 2: Extract inline code spans
    html_modified, inline_codes = extract_inline_code(html_modified)

    # Steps 3-4: Remove unwanted content and replace block tags
    # Note: replace_block_tags already calls remove_html_comments and remove_script_and_style
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
