#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright (c) 2024-2025 Emasoft
# Licensed under the Apache License, Version 2.0 (the "License");
# You may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#     http://www.apache.org/licenses/LICENSE-2.0

from __future__ import annotations

import os
import logging
import requests
import json
import re
from typing import Optional, Dict, Any
from functools import wraps
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, wait_none, before_sleep_log
import codecs
from chardet.universaldetector import UniversalDetector
import unicodedata
import string
import functools
import html
import time


# Constant parameters: 
DEFAULT_CHUNK_SIZE = 12000  # max chars for each chunk of chinese text to send to the server
CONNECTION_TIMEOUT = 30    # max seconds to wait for connecting with the server (reduced from 100)
RESPONSE_TIMEOUT = 300     # max seconds to wait for the server response (reduced from 3000)

# Define a custom exception for translation failures
class TranslationException(Exception):
    pass

# Define a Tenacity retry wrapper that works on class methods
def retry_with_tenacity(method):
    @wraps(method)
    def wrapper(self, *args, **kwargs):
        @retry(
            stop=stop_after_attempt(7),  # Reduced from 77 to 7 attempts
            wait=wait_exponential(multiplier=1, min=3, max=60),  # Cap max wait at 60s
            retry=retry_if_exception_type((
                requests.exceptions.RequestException,
                requests.exceptions.HTTPError,
                TranslationException
            )),
            before_sleep=before_sleep_log(self.logger, logging.WARNING)
        )
        @wraps(method)
        def inner(*args, **kwargs):
            return method(self, *args, **kwargs)

        return inner(*args, **kwargs)
    return wrapper
    

## LLM API SETTINGS CONSTANTS
## ( CAREFULLY CALIBRATED! DO NOT CHANGE! )


#######################
# REMOTE API SETTINGS #
#######################
API_URL_OPENROUTER = 'https://openrouter.ai/api/v1/chat/completions'
MODEL_NAME_DEEPSEEK = 'deepseek/deepseek-r1:nitro'
SYSTEM_PROMPT_DEEPSEEK = ""
USER_PROMPT_1STPASS_DEEPSEEK = """;; [Task]
        You are a professional and helpful translator. You are proficient in languages and literature. You always write in a excellent and refined english prose, following a polished english writing style. Your task is to translate the Chinese text you receive and to output the English translation of it. Answer with only the fully translated english text and nothing else. Do not add comments, annotations or messages for the user. The quality of the translation is very important. Be sure to translate every word, without missing anything. Your aim is to translate the chinese text into english conveying the bright prose or poetry of the original text in the translated version and even surpassing it. Always use curly quotes like `“”` when translating direct speech. Never abridge the translation. You must always return the whole unabridged translation. You must always obey to the TRANSLATION RULES below:

[TRANSLATION RULES]
- Translate directly the Chinese content into perfect English, maintaining or improving the original formatting. 
- Do not omit any information present in the original text.
- Do not leave any chinese character untranslated. 
- Use romanization when a name has no english equivalent. 
- Express the meaning of names between parentheses. For example: `唐舞桐` must be translated as: `Tang Wutong (Dancing Willow)`.
- When translating wuxia and xianxia novels from chinese to english, use the correct daoist terminology. For example the expression `元婴` must be translated as `Nascent Soul`. 
- If some chinese text is unclear or it is missing some parts, you must infer the meaning from the context and write a meaningful and fluent translation anyway. 
- All chinese characters (both traditional or simplified) must be translated in english, including names and chapter titles. 
- If some words or names have no direct translation, you must use the most common english spelling of or use a english paraphrase. 
- You shall also improve the fluency and clarity of the translated text. For example: `修罗场` can be translated as `dramatic and chaotic situation`. `榜下捉婿` can be translated as `Chosing a Son-in-law From a List`. 
- Try not to leave the gender of words and prepositions in ambiguous or neutral form if they refer to people. Do not make inconsistent translations that lead to characters in the text sometimes depicted as male and some other times as female. always use the context to infer the correct gender of a person when translating to english and use that gender every time words and prepositions refer to that person.
- When it is found in a direct speech phrase, always translate `弟弟` as `younger brother`, never as `your younger brother` or `your brother` or `my younger brother` or `my brother`. The same rule must be applied to all parent (mother, father, older brother, older cousine, uncle, etc.). Translate as `his brother` or `his younger brother` only when explicitly accompanied by the possessive pronoun.
- Do not add comments or annotations or anything else not in the original text. Not even translation notes or end of translation markers. 
- Convert all normal quotes pairs (i.e. "" or '') to curly quotes pairs (i.e. “”, ‘’). Always use double curly quotes (`“…”`) to open and close direct speech parts in english, and not the normal double quotes (`"…"`). If one of the opening or closing quotes marks ( like `“` and `”`, or `"` and `"`, or `”` and `„`, or `«` and `»`) is missing, you should add it using the `“` or the `”` character, inferring the right position from the context. For example you must translate `“通行證？”` as `“A pass?”`. 
- The English translation must be fluent and grammatically correct. It must not look like a literal, mechanical translation, but like a high quality brilliant composition that conveys the original meaning using a rich literary level English prose and vocabulary.
- Be sure to keep the translated names and the unique terms used to characterize people and places the same for the whole translation, so that the reader is not confused by sudden changes of names or epithets. 
- Be coherent and use the same writing style for the whole novel. 
- Never summarize or omit any part of the text. Never abridge the translation.
- Every line of text must be accurately translated in english, without exceptions. Even if the last line of text appears truncated or makes no sense, you must translate it.
- No chinese characters must appear in the output text. You must translate all of them in english.


"""
USER_PROMPT_2NDPASS_DEEPSEEK = """;; [TASK]
You are an helpful and professional translator. You are proficient in languages and literature. You always write in a excellent and refined english prose, following a polished english writing style. Examine the following text containing a mix of english and chinese characters. Find all chinese words and characters and replace them with an accurate english translation. Use the context around the chinese words to infer the better way to translate them. Then convert all normal quotes pairs (i.e. `""` or `''`) to curly quotes pairs (i.e. `“”`, `‘’`). Output only the perfected english text, making sure that all the chinese words and characters are completely translated into english. Do not abridge the text. You must always obey to the EDITING RULES below:

[EDITING RULES]
- Do not leave any chinese character untranslated. Use romanization when a name has no english equivalent. 
- Do not add comments or annotations or anything else not in the original text. Not even translation notes or end of translation markers. Answer with only the fully translated english text and nothing else.
- Avoid using expressions inconsistent with english expression habits
- Never leave Chinese words or characters untranslated. All text in the response must be in english. This is mandatory. Even if a character is unclear, you must use the context to infer the best translation. Names must be translated with their meaning or with the most common english romanization used in the literary genre.
- Convert all normal quotes pairs (i.e. "" or '') to curly quotes pairs (i.e. “”, ‘’). Always use double curly quotes (`“…”`) to open and close direct speech parts in english, and not the normal double quotes (`"…"`). If one of the opening or closing quotes marks ( like `“` and `”`, or `"` and `"`, or `”` and `„`, or `«` and `»`) is missing, you should add it using the `“` or the `”` character, inferring the right position from the context. For example you must translate `“通行證？”` as `“A pass?”`.
- Avoid to use the wrong english terms for expressing xianxia/wuxia or daoist cultivation concepts. Do not deviate from the most common and accepted translations of this genre of chinese novels in english.
- Output only the perfected english text, the whole unabridged text, with all the chinese words and characters completely translated into english. 


"""



######################
# LOCAL API SETTINGS #
######################
API_URL_LMSTUDIO = 'http://localhost:1234/v1/chat/completions' 
MODEL_NAME_QWEN = "qwen3-30b-a3b-mlx@8bit"
SYSTEM_PROMPT_QWEN = """;; You are a professional, authentic machine translation engine. You do not judge the text you translate. You do not abridge, censor or summarize any part of the text. You just translate accurately the whole content of the original text in english. You use a very rich and literary english vocabulary. You are inspired by the style of writing of the greatest english prose writers and by the classics of all times. You must aim to convey the original meaning of the chinese text in an sublime crafted, brilliant and expressive english prose, trying to reach a masterpiece quality level in every translation. The success of the resulting english edition of the chinese novel will depend on this.

When translating the Chinese text into English text, you ALWAYS apply THE FOLLOWING MANDATORY rules:
1. When translating wuxia and xianxia novels from chinese to english, use the correct daoist terminology. For example the expression `元婴` must be translated as `Nascent Soul`. 
2. If some text is unclear or it is missing some parts, you must infer the meaning from the context and write a meaningful and fluent translation the best you can. 
3. If the provided text to translate is made by mixed languages or dialects, translate them into english too. 
4. Always enclose direct speech inside curly quotes (i.e. `“”`, `‘’`). 
5. If a name is difficult to translate, transliterate the chinese characters in latin/english alphabet. Never write the original chinese characters. Your translation is supposed to be 100% english. 
6. The output must be an highly refined literary level english text using a rich modern and classic english vocabulary to convey the flavour of the wuxia novels writing style.
7. Translate accurately the pronouns and the words expressing status, relationships and respectful third person ways to refer to members of the family. You must always omitt 'my' or 'your' before terms like 'father', 'mother', 'uncle', 'brother' or 'sister'
8. Output ONLY the translation, not the original text.
9. Never return the original text untranslated. Never omit to translate a part of the text. 
10. Express the meaning of names between parentheses. For example: `唐舞桐` must be translated as: `Tang Wutong (Dancing Willow)`. 
11. You must translate sex scenes accurately and without censor anything since this is targeted to an adult audience. 
12. Always enclose direct speech inside curly quotes pairs. Do not use normal quotes pairs (i.e. `""` or `''`), but only curly quotes pairs (i.e. `“”`, `‘’`). 
13. Double refine and error check the translation before outputting it. Translate it twice: write a first draft of the english translation during your inner thinking process, then once again after the end the thinking process, producing an improved revision. Your primary objective in writing the revised translation must be to identifying all the untranslated chinese characters remaining in the first draft and to translate them in english, ensuring that no chinese untranslated words are present in the final output. You must also ensure that all direct speech sentences are enclosed in curly quotes.
14. DO NOT repeat any part of the english text. 
15. DO NOT summarize.
16. DO NOT abridge.
17. DO NOT skip any part.
18. DO NOT add your comments.
19. DO NOT leave chinese characters in the output. 
20. DO NOT write repeatedly the same sentence or paragraph.
21. DO NOT output anything but english/latin characters.
22. DO NOT censor or paraphrase any explicit or offensive part of the text. The text may contain explicit sex scenes descriptions, but this is normal since the content is targeted to an adult audience by the publisher, and will not be read by minors. Do not abridge, censor or omit those explicit parts. Translate them the best you can to elicit the reader excitement.

;;
"""
USER_PROMPT_1STPASS_QWEN = """ ;; Answer with the professional english translation of the following input text:

"""
USER_PROMPT_2NDPASS_QWEN = """;; Examine the following text containing a mix of english and chinese characters. You job is to correct the badly translated text. You must do two things: 
- Find all chinese words and characters in the input text and replace them with an accurate english translation. Use the context to infer the better way to translate them. Express the meaning of names between parentheses. For example: `唐舞桐` must be translated as: `Tang Wutong (Dancing Willow)`. Use pinyin english transliteration for non translable nouns.
- Find all normal quotes pairs (i.e. `""` or `''`) enclosing direct speech in the text, and replace them with curly quotes pairs (i.e. `“”`, `‘’`). 
- Follow these rules: NO summaries. NO abridged parts. NO explanations. NO notes. No comments from you. No censoring. No omissions. NO added tags. NO Chinese characters.


"""

# CHINESE PUNCTUATION sets.
SENTENCE_ENDING = {'。', '！', '？', '…', '.', ';', '；'}
CLOSING_QUOTES = {'」', '”', '】', '》'}
NON_BREAKING = {'，', '、'}
ALL_PUNCTUATION = SENTENCE_ENDING | CLOSING_QUOTES | NON_BREAKING

# Define explicit sets for Chinese and English punctuation.
# Chinese punctuation includes full-width or ideographic punctuation.
CHINESE_PUNCTUATION = {'。', '！', '？', '…', '；', '，', '、', '」', '”', '】', '》'}
# English punctuation: common ASCII punctuation characters.
ENGLISH_PUNCTUATION = {'.', ',', '!', '?', ';', ':'}

# PARAGRAPH DELIMITERS (characters that denote new paragraphs)
# PARAGRAPH_DELIMITERS is already defined at the module level, no need to redefine it here.

# Characters that are allowed unlimited repetition by default.
# These include whitespace, control characters, some punctuation, symbols, and paragraph delimiters.
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

PRESERVE_UNLIMITED = {
    ' ', '.', '\n', '\r', '\t', '(', ')', '[', ']',
    '+', '-', '_', '=', '/', '|', '\\', '*', '%', '#', '@',
    '~', '<', '>', '^', '&', '°', '…',
    '—', '•', '$'
}.union(PARAGRAPH_DELIMITERS)

# Precompile the regular expression pattern for matching repeated characters.
_repeated_chars = re.compile(r'(.)\1+')


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

    Detailed Rules:
      1. For characters in PRESERVE_UNLIMITED, the repetition is preserved exactly (even if repeated more than 3 times),
         unless overridden by a force option.
      2. For characters in ALL_PUNCTUATION (that are not overridden by a force option), any repeated sequence is collapsed to a single occurrence.
      3. For all other characters (e.g. letters), if a sequence is longer than 3, it is replaced by exactly 3 consecutive occurrences;
         sequences of 3 or fewer remain unchanged.
      4. For numeric characters (as determined by isnumeric()), repetitions are always preserved (i.e. unlimited).
      5. Alternating sequences of different characters (e.g. "ABABAB") are not modified.

    Optional Parameters:
      force_chinese (bool): If True, forces all Chinese punctuation characters (defined in CHINESE_PUNCTUATION)
                                 to be repeated only once.
      force_english (bool): If True, forces all English punctuation characters (defined in ENGLISH_PUNCTUATION)
                                 to be repeated only once, even if they are normally exempt.

    Parameters:
        text (str): The input text to normalize.

    Returns:
        str: The normalized text with excessive character repetitions collapsed as specified.
    """
    def limiter(match):
        # Extract the entire sequence of repeated characters.
        seq = match.group(0)
        char = seq[0]

        # For all numeric characters (covers Arabic, Chinese, Roman, Japanese, etc.), allow unlimited repetitions.
        if char.isnumeric():
            return seq

        # Forced rules override any other considerations:
        if force_chinese and char in CHINESE_PUNCTUATION:
            return char  # Collapse to one occurrence.
        if force_english and char in ENGLISH_PUNCTUATION:
            return char  # Collapse to one occurrence.

        # For characters allowed unlimited repetition by default, preserve the original sequence.
        if char in PRESERVE_UNLIMITED:
            return seq

        # For characters in ALL_PUNCTUATION (non-exempt), collapse any sequence to one occurrence.
        elif char in ALL_PUNCTUATION:
            return char

        # For all other characters, collapse to 3 occurrences if the sequence is too long.
        # If the sequence length is 3 or fewer, leave it unchanged.
        else:
            return seq if len(seq) <= 3 else char * 3

    # Replace all repeated sequences in the text using the limiter function.
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
    # This regex matches text between single backticks.
    modified_text = re.sub(r'`([^`]+)`', repl, text)
    return modified_text, inline_codes

def remove_html_comments(html_str: str) -> str:
    """
    Remove HTML comments.
    """
    return re.sub(r'<!--.*?-->', '', html_str, flags=re.DOTALL)

def remove_script_and_style(html_str: str) -> str:
    """
    Remove <script> and <style> tags along with their entire content.
    """
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
    """
    Replace block-level HTML tags with whitespace markers so that
    the intended formatting (newlines, tabs) is preserved.
    """
    # First, remove comments, scripts, and style blocks.
    html_str = remove_html_comments(html_str)
    html_str = remove_script_and_style(html_str)
    
    # Remove <pre> tags (their content is already extracted).
    html_str = re.sub(r'<\s*/?\s*pre[^>]*>', '', html_str, flags=re.IGNORECASE)
    
    replacements = [
        # Paragraphs: simulate a paragraph break.
        (r'<\s*/\s*p\s*>', '\n'),
        (r'<\s*p[^>]*>', '\n'),
        # Line breaks: convert to newline.
        (r'<\s*br\s*/?\s*>', '\n'),
        # Divisions: add newline after closing div.
        (r'<\s*/\s*div\s*>', '\n'),
        # List items: prefix with a bullet and add newline.
        (r'<\s*li[^>]*>', '  - '),
        (r'<\s*/\s*li\s*>', '\n'),
        # Table rows: newline after each row.
        (r'<\s*/\s*tr\s*>', '\n'),
        # Table cells: add a tab after each cell.
        (r'<\s*/\s*td\s*>', '\t'),
        (r'<\s*/\s*th\s*>', '\t'),
        # Blockquotes: add newlines.
        (r'<\s*blockquote[^>]*>', '\n'),
        (r'<\s*/\s*blockquote\s*>', '\n'),
        # Headers (h1-h6): newlines before and after.
        (r'<\s*h[1-6][^>]*>', '\n'),
        (r'<\s*/\s*h[1-6]\s*>', '\n'),
    ]
    for pattern, repl in replacements:
        html_str = re.sub(pattern, repl, html_str, flags=re.IGNORECASE)
    return html_str

def remove_remaining_tags(html_str: str) -> str:
    """
    Remove any remaining HTML tags (including orphaned or widowed ones)
    while leaving inner text intact.
    
    This function only matches valid HTML tags that start with an optional slash
    followed by an alphabetical character. It will not match stray "<" or ">"
    used in code snippets or math expressions.
    """
    pattern = r'<\s*(\/)?\s*([a-zA-Z][a-zA-Z0-9]*)(?:\s+[^<>]*?)?\s*(\/?)\s*>'
    return re.sub(pattern, '', html_str)

def unescape_non_code_with_placeholders(text: str) -> str:
    """
    Unescape HTML entities in text that is not inside a code block.
    Code block placeholders (both block and inline) are preserved.
    """
    pattern = r'(@@CODEBLOCK\d+@@|@@INLINECODE\d+@@)'
    parts = re.split(pattern, text)
    for i, part in enumerate(parts):
        if re.fullmatch(pattern, part):
            continue  # Leave code placeholders intact.
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
    # Step 1: Extract block-level code.
    html_modified, block_codes = extract_code_blocks(html_str)
    # Step 2: Extract inline code spans.
    html_modified, inline_codes = extract_inline_code(html_modified)
    # Steps 3-5: Remove unwanted content and tags.
    html_modified = remove_html_comments(html_modified)
    html_modified = remove_script_and_style(html_modified)
    html_modified = replace_block_tags(html_modified)
    html_modified = remove_remaining_tags(html_modified)
    # Step 6: Unescape HTML entities outside code placeholders.
    html_modified = unescape_non_code_with_placeholders(html_modified)
    # Step 7: Restore inline code placeholders.
    for i, code in enumerate(inline_codes):
        placeholder = f"@@INLINECODE{i}@@"
        html_modified = html_modified.replace(placeholder, f"`{code}`")
    # Step 8: Restore block-level code placeholders.
    for i, code in enumerate(block_codes):
        placeholder = f"@@CODEBLOCK{i}@@"
        html_modified = html_modified.replace(placeholder, code)
    return html_modified



# Precompute allowed ASCII characters (letters, digits, punctuation)
ALLOWED_ASCII = set(string.ascii_letters + string.digits + string.punctuation)

@functools.lru_cache(maxsize=None)
def is_latin_char(char: str) -> bool:
    """
    Returns True if the non-ASCII character belongs to the Latin script
    based on its Unicode name.
    """
    try:
        return "LATIN" in unicodedata.name(char)
    except ValueError:
        # If the character has no Unicode name, assume it's not Latin.
        return False

def is_latin_charset(text: str, threshold: float = 0.1) -> bool:
    """
    Examines a text string and determines if it is primarily using a Latin-based charset.
    
    For each non-whitespace character, it counts those that are considered Latin.
    For ASCII characters (most common in Latin texts), a fast set membership check is used.
    For non-ASCII characters, the Unicode name is cached to avoid repeated lookups.
    
    The function computes the ratio of non-Latin characters to Latin characters.
    If this ratio exceeds the threshold (default 1%), it returns False (indicating the text is
    not primarily Latin), otherwise True.
    
    :param text: The input text string.
    :param threshold: The maximum allowed ratio of non-Latin characters to Latin characters.
                      Default is 0.01 (i.e., 1%).
    :return: True if the text is primarily Latin, False otherwise.
    """
    total_count = 0
    latin_count = 0

    for char in text:
        if char.isspace():
            continue  # Skip whitespace
        total_count += 1
        cp = ord(char)
        # Fast path for ASCII characters.
        if cp < 128:
            if char in ALLOWED_ASCII:
                latin_count += 1
            continue
        # Use the cached function for non-ASCII characters.
        if is_latin_char(char):
            latin_count += 1

    # If no Latin characters were found, consider the text as not Latin.
    if latin_count == 0:
        return False

    non_latin_count = total_count - latin_count
    ratio = non_latin_count / latin_count
    return ratio < threshold


def compute_costs(completion_response):

    # Get the completion response data
    completion_data: Dict[str, Any] = completion_response.json()
    
    # Extract the generation ID from the response
    generation_id = completion_data["id"]
    
    OPENROUTER_API_KEY = os.environ.get('OPENROUTER_API_KEY')
    
    # Headers for the request
    headers = {"Authorization": f"Bearer {OPENROUTER_API_KEY}"}

    # Wait a moment for the generation stats to be available
    print("\nWaiting for generation stats to be available...")
    time.sleep(2)  # Wait for 2 seconds

    # Make a request to get the generation stats        
    querystring = {"id": f"{generation_id}"}
    generation_response = requests.get("https://openrouter.ai/api/v1/generation", headers=headers, params=querystring)
    print(f"GENERATION RESPONSE: {str(generation_response.json())}")

    generation_stats: Dict[str, Any] = generation_response.json()
    
    # Make a request to get the credits stats
    credits_response = requests.get("https://openrouter.ai/api/v1/credits", headers=headers)
    print(f"CREDITS RESPONSE: {str(credits_response.json())}")

    credits_data: Dict[str, Any] = credits_response.json()
     
    # Print all the information
    print("\n\n=== Token Usage ===")
    print(f"Prompt tokens: {completion_data['usage']['prompt_tokens']}")
    print(f"Completion tokens: {completion_data['usage']['completion_tokens']}")
    print(f"Total tokens: {completion_data['usage']['total_tokens']}")
    
    print("\n=== Generation Stats ===")
    print(f"Cost in USD: ${str(generation_stats['data']['total_cost'])}")
    
    print("\n=== Credits Information ===")
    print(f"Total credits: ${credits_data['data']['total_credits']}")
    print(f"Total usage: ${credits_data['data']['total_usage']}")
    print(f"Remaining credits: ${credits_data['data']['total_credits'] - credits_data['data']['total_usage']}")
    print("\n\n")
    


"""
# disable_tenacity.py
import tenacity

# Backup original method (if you ever want to restore it)
original_retry_call = tenacity.Retrying.__call__

def no_retry_call(self, fn, *args, **kwargs):
    return fn(*args, **kwargs)

# Globally disable retries by overriding Retrying.__call__
tenacity.Retrying.__call__ = no_retry_call
"""




class ChineseAITranslator:
    def __init__(self, logger: Optional[logging.Logger] = None, use_remote: bool = False):
        self.logger = logger or logging.getLogger(__name__)
        self.api_key = os.environ.get('OPENROUTER_API_KEY')
        if not self.api_key:
            self.log("OPENROUTER_API_KEY not set in environment variables", "error")
        self.is_remote = use_remote
        if self.is_remote:
            self.api_url = API_URL_OPENROUTER
            self.MODEL_NAME = MODEL_NAME_DEEPSEEK
            self.SYSTEM_PROMPT = SYSTEM_PROMPT_DEEPSEEK
            self.USER_PROMPT_1STPASS = USER_PROMPT_1STPASS_DEEPSEEK
            self.USER_PROMPT_2NDPASS = USER_PROMPT_2NDPASS_DEEPSEEK
        else:
            self.api_url = API_URL_LMSTUDIO
            self.MODEL_NAME = MODEL_NAME_QWEN
            self.SYSTEM_PROMPT = SYSTEM_PROMPT_QWEN
            self.USER_PROMPT_1STPASS = USER_PROMPT_1STPASS_QWEN
            self.USER_PROMPT_2NDPASS = USER_PROMPT_2NDPASS_QWEN
        
    def log(self, message: str, level: str = "info") -> None:
        log_method = getattr(self.logger, level)
        log_method(message)

    def remove_thinking_block(self, content:str) -> str:
        # Remove Think Tag from Text with Regular Expressions
        content = re.sub(r"<think>.*?</think>\n?", "", content, flags=re.DOTALL)
        content = re.sub(r"<thinking>.*?</thinking>\n?", "", content, flags=re.DOTALL)
        return content

    def remove_custom_tags(self, text, keyword, ignore_case=True):
        # Escape keyword in case it contains regex special characters
        escaped_keyword = re.escape(keyword)
        # Build a regex pattern for all variants with different delimiters
        pattern_str = (
            rf"(<{escaped_keyword}>|\[{escaped_keyword}\]|\{{{escaped_keyword}\}}|\({escaped_keyword}\)|##{escaped_keyword}##)"
        )
        # Set regex flags based on the optional parameter
        flags = re.IGNORECASE if ignore_case else 0
        pattern = re.compile(pattern_str, flags)
        # Substitute all occurrences with an empty string
        return pattern.sub("", text)
        
    def remove_excess_empty_lines(self, txt: str) -> str:
        # Match 5 or more newline characters
        return re.sub(r'\n{5,}', '\n\n\n', txt)
    
        
    def normalize_spaces(self, text: str) -> str:
        # Split the text into lines
        lines = text.split('\n')
        normalized_lines = []
        
        for line in lines:
            # Strip leading/trailing whitespace from the line
            stripped_line = line.strip()
            
            if stripped_line:  # If the line is not empty (contains actual content)
                # Replace multiple spaces with a single space
                normalized_line = ' '.join(stripped_line.split())
                normalized_lines.append(normalized_line)
            else:
                # For empty lines, add only a newline (no spaces)
                normalized_lines.append('')
        
        # Join lines back with newlines
        return '\n'.join(normalized_lines)
    
        
    def remove_translation_markers(self, txt: str) -> str:
        """
        Removes all variations of 'End of translation' markers from the input text.
        
        Args:
            txt (str): The input string containing the translation text.
    
        Returns:
            str: The text with all 'End of translation' markers removed.
        """
        # Refined regex pattern to match variations of "End of translation" with better constraints
        pattern = r"[\[\(\-\*\s]*[-]*End of translation[\.\-\)\]\s]*[\.\-]*[\)\]\*\s]*"
        
        # Use re.sub to remove all variations of "End of translation"
        cleaned_txt = re.sub(pattern, '', txt, flags=re.IGNORECASE)
        
        # Strip leading/trailing whitespace to clean up extra spaces after removal
        cleaned_txt = clean(cleaned_txt)

        # Refined regex pattern to match variations of "Start of translation" with better constraints
        pattern = r"[\[\(\-\*\s]*[-]*Start of translation[\.\-\)\]\s]*[\.\-]*[\)\]\*\s]*"
        
        # Use re.sub to remove all variations of "Start of translation"
        cleaned_txt = re.sub(pattern, '', cleaned_txt, flags=re.IGNORECASE)
        
        # Strip leading/trailing whitespace to clean up extra spaces after removal
        cleaned_txt = clean(cleaned_txt)
        
        # Refined regex pattern to match variations of "English Translation" with better constraints
        pattern = r"[\[\(\-\*\s]*[-]*English Translation[\.\-\)\]\s]*[\.\-]*[\)\]\*\s]*"
        
        # Use re.sub to remove all variations of "English Translation"
        cleaned_txt = re.sub(pattern, '', cleaned_txt, flags=re.IGNORECASE)
        
        # Strip leading/trailing whitespace to clean up extra spaces after removal
        cleaned_txt = clean(cleaned_txt)
        
        # Remove other tags
        cleaned_txt = self.remove_custom_tags(cleaned_txt, "DECLARATION")
        cleaned_txt = self.remove_custom_tags(cleaned_txt, "TRANSLATION")
        cleaned_txt = self.remove_custom_tags(cleaned_txt, "TRANSLATED TEXT")
        cleaned_txt = self.remove_custom_tags(cleaned_txt, "ENGLISH TEXT")
        cleaned_txt = self.remove_custom_tags(cleaned_txt, "REVISED TEXT")
        cleaned_txt = self.remove_custom_tags(cleaned_txt, "CORRECTED TEXT")
        cleaned_txt = self.remove_custom_tags(cleaned_txt, "TRANSLATED IN ENGLISH")
        cleaned_txt = self.remove_custom_tags(cleaned_txt, "TEXT TRANSLATED IN ENGLISH")
        cleaned_txt = self.remove_custom_tags(cleaned_txt, "FIXED TEXT")
        cleaned_txt = self.remove_custom_tags(cleaned_txt, "ENGLISH TRANSLATED TEXT")
        cleaned_txt = self.remove_custom_tags(cleaned_txt, "ENGLISH TRANSLATION")
        cleaned_txt = self.remove_custom_tags(cleaned_txt, "ENGLISH VERSION")
        cleaned_txt = self.remove_custom_tags(cleaned_txt, "TRANSLATED VERSION")
        
        # Remove html markup
        #cleaned_txt = remove_html_markup(cleaned_txt)
        
        # Remove excess spaces
        cleaned_txt = self.normalize_spaces(cleaned_txt)
        
        # Remove empty lines in excess
        cleaned_txt = self.remove_excess_empty_lines(cleaned_txt)
        
        # Strip leading/trailing whitespace to clean up extra spaces after removal
        cleaned_txt = clean(cleaned_txt)
        
        
        return cleaned_txt

    
    def translate_chunk(self, chunk: str, double_translation=False, is_last_chunk=False) -> str:
        self.log("Translating chunk")
        self.log("Double Translation : " + str(double_translation))
        
        # Remove empty lines in excess
        chunk = self.remove_excess_empty_lines(chunk)
        
        prompt1 = f"""{self.USER_PROMPT_1STPASS}

{chunk}

 """


        ## DO THE FIRST TRANSLATION USING THE API
        first_translation = self.translate_messages(prompt1, is_last_chunk)
        first_translation = self.remove_translation_markers(first_translation)
        

        
        prompt2 = f"""{self.USER_PROMPT_2NDPASS}
[*INPUT TEXT TO CORRECT*]

{first_translation}

"""
        if double_translation:
            ## DO THE REFINED SECOND TRANSLATION USING THE API
            self.log("DOING SECOND REFINING TRANSLATION. Sending request to API")
            final_translation = self.translate_messages(prompt2, is_last_chunk)
            final_translation = self.remove_translation_markers(final_translation)
        else:
            final_translation = first_translation

            
        ## Clean the text and separate chapters
        #final_translation = self.separate_chapters(final_translation)
        
        ## RETURN THE FINAL TRANSLATED STRING
        return final_translation


    
    @retry_with_tenacity
    def translate_messages(self, messages: str, is_last_chunk=False) -> str:
        self.log("Sending translation request to API")
        self.log(F"AI MODEL USED: {self.MODEL_NAME}")
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        data: Dict[str, Any] = {
            "model": self.MODEL_NAME,
            "messages": [
                {
                    "role": "system",
                    "content": f"{self.SYSTEM_PROMPT}",
                },
                {
                    "role": "user",
                    "content": messages,
                }
            ],
            "temperature": 0.05,
            "max_tokens": None,
            "stream": False,
#            "top_p": 0,
#            "frequency_penalty": 0,
#            "presence_penalty": 0,
#            "repetition_penalty": 1.1,
#            "top_k": 0,
    
        }
    
        try:
            ##response = requests.get("http://10.255.255.1", timeout=(5, 10))    # Uncomment to test Tenacity auto retry
            response = requests.post(self.api_url, headers=headers, json=data, timeout=(CONNECTION_TIMEOUT, RESPONSE_TIMEOUT))
            self.log(f"Request sent to {self.api_url}")
            response.raise_for_status()
            self.log(f"Server returned RESPONSE: \n{response.json()}")
            if self.is_remote:
                self.compute_costs(response)
            #compute_costs(response)
            result: Dict[str, Any] = response.json()
            if 'choices' in result and len(result['choices']) > 0:
                content = str(result['choices'][0]['message']['content'])
                content = self.remove_thinking_block(content)
                # Raise exception if the content is not primarily Latin-based.
                if not is_latin_charset(content):
                    self.log("Translated text does not appear to be in a Latin-based charset. Retrying...")
                    raise TranslationException("Translated text does not appear to be in a Latin-based charset.")
                if len(content) < 300 and is_last_chunk is False:
                    self.log("Translated text is too short. An error must have occurred. Retrying...")
                    raise TranslationException("Translated text is too short. An error must have occurred. Retrying...")
                return content
            else:
                self.log("Unexpected response structure from API", "error")
                raise ValueError("Unexpected response structure from Open Router API.")
        except requests.exceptions.HTTPError as http_err:
            self.log(f"HTTP error occurred: {http_err}", "error")
            raise TranslationException(f"HTTP error: {http_err}") from http_err
        except requests.exceptions.RequestException as req_err:
            self.log(f"Request exception: {req_err}", "error")
            raise TranslationException(f"Request failed: {req_err}") from req_err
        except json.JSONDecodeError as json_err:
            self.log(f"JSON decode error: {json_err}", "error")
            raise TranslationException(f"JSON error: {json_err}") from json_err
        except Exception as e:
            self.log(f"Unexpected error: {e}", "error")
            raise TranslationException(f"Unexpected error: {e}") from e



    def separate_chapters(self, text: str) -> str:
        # Define patterns for chapter headings
        patterns = [
            # Chapter X: Title or Chapter X - "Title" - Part 1
            r'\b(Chapter\s+\d+\s*[-:—.]*\s*[\"«"]?[A-Za-z0-9\s.,:;!?…]*[\"»"]?\s*[-:—.]*\s*Part\s*\d*)',
            # Chapter in Roman numerals like CHAPTER V: The Finale - Part 1
            r'\b(Chapter\s+[IVXLC]+\s*[-:—.]*\s*[\"«"]?[A-Za-z0-9\s.,:;!?…]*[\"»"]?\s*[-:—.]*\s*Part\s*\d*)',
            # Chapter One - Title - Part 1
            r'\b(Chapter\s+\w+\s*[-:—.]*\s*[\"«"]?[A-Za-z0-9\s.,:;!?…]*[\"»"]?\s*[-:—.]*\s*Part\s*\d*)',
            # Chapter 3: My Farewell, Chapter 3 - My Farewell, etc.
            r'\b(Chapter\s+\d+\s*[-:—]*\s*.*)',
            # Chapter IX - My Farewell
            r'\b(Chapter\s+[IVXLC]+\s*[-:—]*\s*.*)',
            # Chapter One - My Farewell
            r'\b(Chapter\s+\w+\s*[-:—]*\s*.*)',
            # Chapter on its own line
            r'\b(Chapter)\s*$',
            # Prologue and Epilogue
            r'\b(Prologue|Epilogue)\s*$',
        ]
        chapter_pattern = re.compile('|'.join(patterns), re.IGNORECASE)
        return chapter_pattern.sub(r'\n\n\n\1\n\n', text)

    def translate_file(self, input_file: str, output_file: str, is_last_chunk=False) -> Optional[str]:
        self.log(f"Translating file: {input_file}")
        try:
            with open(input_file, 'r', encoding='utf-8') as file:
                chinese_text = file.read()
            
            english_text = self.translate_chunk(chinese_text, is_last_chunk=is_last_chunk)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(english_text)
            
            return english_text
        except Exception as e:
            self.log(f"Translation failed: {str(e)}", "error")
            return None


    def translate(self, input_string: str, is_last_chunk=False) -> str:
        #self.log(f"Translating text: {input_string}")
        try:
            chinese_text = input_string
            english_text = self.translate_chunk(chinese_text, double_translation=False, is_last_chunk=is_last_chunk)
        except Exception as ex:
            self.log(f"Unexpected error during file translation: {ex}", "error")
            return None
        return english_text


# Example usage:
if __name__ == "__main__":
    translator = ChineseAITranslator()
    english_text = translator.translate_file(
        input_file="dummy_chinese.txt", 
        output_file="output.txt"
    )
    if english_text:
        try:
            with open("output.txt", 'w', encoding='utf-8') as file:
                file.write(english_text)
        except IOError as e:
            print(f"File error: {e}")



