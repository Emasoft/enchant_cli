#!/usr/bin/env python3

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

"""
common_text_utils.py - Shared text processing utilities for EnChANT modules

This module contains text cleaning, HTML processing, and character manipulation
functions used across multiple EnChANT modules.
"""

import re
import html
# No typing imports needed - using built-in types

# Constants from original modules
PRESERVE_UNLIMITED = {
    "　",
    "\u2002",
    "\u2003",
    "\u2004",
    "\u2005",
    "\u2006",
    "\u2007",
    "\u2008",
    "\u2009",
    "\u200a",
    "\u200b",
    "\u2028",
    "\u2029",
    "\u202f",
    "\u205f",
    "\ufeff",
    "\u00a0",
    "\u1680",
    "\u180e",
    "\t",
    "\n",
    "\r",
    "\v",
    "\f",
    "\x1c",
    "\x1d",
    "\x1e",
    "\x1f",
    "\x85",
    " ",
    "!",
    '"',
    "#",
    "$",
    "%",
    "&",
    "'",
    "(",
    ")",
    "*",
    "+",
    ",",
    "-",
    ".",
    "/",
    ":",
    ";",
    "<",
    "=",
    ">",
    "?",
    "@",
    "[",
    "\\",
    "]",
    "^",
    "_",
    "`",
    "{",
    "|",
    "}",
    "~",
}

# Punctuation sets for different languages
CHINESE_PUNCTUATION = {
    "。",
    "，",
    "、",
    "；",
    "：",
    "？",
    "！",
    '"',
    """, """,
    "（",
    "）",
    "【",
    "】",
    "《",
    "》",
    "—",
    "…",
    "·",
    "￥",
    "¥",
}

ENGLISH_PUNCTUATION = {
    ".",
    ",",
    ";",
    ":",
    "?",
    "!",
    '"',
    "'",
    "(",
    ")",
    "[",
    "]",
    "{",
    "}",
    "-",
    "—",
    "…",
    "/",
    "\\",
    "@",
    "#",
    "$",
    "%",
    "^",
    "&",
    "*",
    "+",
    "=",
    "|",
    "~",
    "`",
    "<",
    ">",
}

# Sentence ending punctuation
SENTENCE_ENDING = {"。", "！", "？", "…", ".", ";", "；"}

# Closing quotes
CLOSING_QUOTES = {"」", '"', "】", "》"}

# Non-breaking punctuation
NON_BREAKING = {"，", "、", "°"}

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
    return text.lstrip(" ").rstrip(" ")


def replace_repeated_chars(text: str, chars: str) -> str:
    """
    Replace any sequence of repeated occurrences of each character in `chars`
    with a single occurrence. For example, "！！！！" becomes "！".
    """
    for char in chars:
        # Escape the character to handle any regex special meaning.
        pattern = re.escape(char) + r"{2,}"
        text = re.sub(pattern, char, text)
    return text


def limit_repeated_chars(text: str, force_chinese: bool = False, force_english: bool = False) -> str:
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

    return "".join(result)


# HTML Processing Functions


def extract_code_blocks(html_str: str) -> tuple[str, list[str]]:
    """
    Extract <pre> and <code> blocks from HTML and replace with placeholders.
    Returns modified HTML and list of extracted code blocks.
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
    Returns modified text and list of extracted code snippets.
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
    """Remove HTML comments from the string."""
    return re.sub(r"<!--.*?-->", "", html_str, flags=re.DOTALL)


def remove_script_and_style(html_str: str) -> str:
    """Remove <script> and <style> tags and their content."""
    html_str = re.sub(r"<script\b[^>]*>.*?</script>", "", html_str, flags=re.DOTALL | re.IGNORECASE)
    html_str = re.sub(r"<style\b[^>]*>.*?</style>", "", html_str, flags=re.DOTALL | re.IGNORECASE)
    return html_str


def replace_block_tags(html_str: str) -> str:
    """Replace block-level tags with appropriate whitespace markers."""
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
    """Remove any remaining HTML tags (but preserve content)."""
    # Only remove valid HTML tags (not math expressions like <x>)
    return re.sub(r"</?[a-zA-Z][^>]*>", "", html_str)


def unescape_non_code_with_placeholders(text: str) -> str:
    """Unescape HTML entities except in code placeholders."""
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


def remove_excess_empty_lines(text: str, max_empty_lines: int = 2) -> str:
    """
    Remove excessive empty lines from text.

    Args:
        text: The input text
        max_empty_lines: Maximum number of consecutive empty lines to keep

    Returns:
        Text with excessive empty lines removed
    """
    # Replace multiple newlines with the maximum allowed
    pattern = r"\n{" + str(max_empty_lines + 1) + ",}"
    replacement = "\n" * max_empty_lines
    return re.sub(pattern, replacement, text)


def normalize_spaces(text: str) -> str:
    """
    Normalize various types of spaces and whitespace characters.

    This function:
    1. Converts various Unicode spaces to regular spaces
    2. Removes zero-width spaces
    3. Normalizes whitespace around punctuation
    4. Removes trailing spaces from lines

    Args:
        text: The input text

    Returns:
        Text with normalized spaces
    """
    # Replace various Unicode spaces with regular space
    space_chars = [
        "\u00a0",  # Non-breaking space
        "\u1680",  # Ogham space mark
        "\u2000",
        "\u2001",
        "\u2002",
        "\u2003",
        "\u2004",
        "\u2005",  # En/em spaces
        "\u2006",
        "\u2007",
        "\u2008",
        "\u2009",
        "\u200a",  # Various spaces
        "\u202f",  # Narrow no-break space
        "\u205f",  # Medium mathematical space
        "\u3000",  # Ideographic space
    ]

    for space_char in space_chars:
        text = text.replace(space_char, " ")

    # Remove zero-width spaces
    zero_width = ["\u200b", "\u200c", "\u200d", "\ufeff"]
    for zw in zero_width:
        text = text.replace(zw, "")

    # Normalize multiple spaces to single space (not at line boundaries)
    lines = text.split("\n")
    normalized_lines = []
    for line in lines:
        # Replace multiple spaces with single space
        line = re.sub(r" {2,}", " ", line)
        # Remove trailing spaces
        line = line.rstrip()
        normalized_lines.append(line)

    return "\n".join(normalized_lines)


def clean_adverts(text_content: str) -> str:
    """
    Clean advertisement text from Chinese novel content.

    This function removes various spam/advertisement patterns commonly found
    in Chinese novel text files, particularly from jimixs and 34gc websites.
    """
    # Regex patterns to remove spam/advertisements
    spam_patterns = [
        r"吉米小说网\s*[（(]www\.(34gc|jimixs)\.(net|com)[）)]\s*txt电子书下载",
        r"吉米小说网\s*[（(]Www\.(34gc|jimixs)\.(net|com)[）)]\s*免费TXT小说下载",
        r"吉米小说网\s*[（(]www\.jimixs\.com[）)]\s*免费电子书下载",
        r"本电子书由果茶小说网\s*[（(]www\.34gc\.(net|com)[）)]\s*网友上传分享，网址\:http\:\/\/www\.34gc\.net",
        r"(本电子书由){0,1}[吉米小说网果茶]{4,6}\s*[（(]www\.(34gc|jimixs)\.(net|com)[）)]\s*[tx电子书下载网友上传分免费小说在线阅读说下载享]{4,10}",
        r"[,;\.]{0,1}\s*网址\:www\.(34gc|jimixs)\.(net|com)",
        r"吉米小说网\s*[（(]www\.(34gc|jimixs)\.(net|com)[）)]",
        r"本电子书由果茶小说网",
        r"(http\:\/\/){0,1}www\.(34g|jimixs)\.(net|com)",
    ]

    # Replace spam patterns with single space
    for pattern in spam_patterns:
        text_content = re.sub(
            pattern,
            " ",
            text_content,
            count=0,
            flags=re.MULTILINE | re.IGNORECASE | re.UNICODE,
        )

    # Normalize parentheses (convert Chinese to English)
    text_content = text_content.replace("（", "(").replace("）", ")")

    return text_content
