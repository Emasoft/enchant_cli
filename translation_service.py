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
import sys
import logging
import requests
import json
import re
import threading
from typing import Optional, Dict, Any
from functools import wraps
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, before_sleep_log
import codecs
from chardet.universaldetector import UniversalDetector
import unicodedata
import string
import functools
import html
import time
from cost_tracker import global_cost_tracker
from common_text_utils import (
    clean, replace_repeated_chars, limit_repeated_chars,
    remove_html_markup, extract_code_blocks, extract_inline_code,
    remove_html_comments, remove_script_and_style, replace_block_tags,
    remove_remaining_tags, unescape_non_code_with_placeholders
)


# Constant parameters: 
DEFAULT_CHUNK_SIZE = 12000  # max chars for each chunk of chinese text to send to the server
CONNECTION_TIMEOUT = 60    # max seconds to wait for connecting with the server (1 minute)
RESPONSE_TIMEOUT = 360     # max seconds to wait for the server response (6 minutes total)
DEFAULT_MAX_TOKENS = 4000  # Default max tokens for API responses

# Define a custom exception for translation failures
class TranslationException(Exception):
    pass

# Define a Tenacity retry wrapper that works on class methods
def retry_with_tenacity(method):
    @wraps(method)
    def wrapper(self, *args, **kwargs):
        # Improved retry settings with time limit
        max_retries = 10  # Maximum 10 retries
        total_time_limit = 18 * 60  # 18 minutes total time limit
        retry_wait_base = 1.0
        retry_wait_min = 3.0
        retry_wait_max = 30.0  # Max 30 seconds between retries
        
        start_time = time.time()
        attempts = 0
        last_exception = None
        
        while attempts < max_retries:
            attempts += 1
            elapsed_time = time.time() - start_time
            
            # Check if we've exceeded total time limit
            if elapsed_time >= total_time_limit:
                error_msg = (f"Translation failed: Exceeded total time limit of {total_time_limit/60:.1f} minutes "
                           f"after {attempts} attempts. Last error: {last_exception}")
                self.logger.error(error_msg)
                # Exit the program on failure - never continue
                print(f"\n❌ FATAL ERROR: {error_msg}")
                sys.exit(1)
            
            try:
                # Log attempt
                if attempts > 1:
                    self.logger.warning(f"Retry attempt {attempts}/{max_retries} after {elapsed_time:.1f}s")
                
                # Call the actual method
                result = method(self, *args, **kwargs)
                
                # Success! Return the result
                if attempts > 1:
                    self.logger.info(f"Successfully completed after {attempts} attempts in {elapsed_time:.1f}s")
                return result
                
            except (requests.exceptions.RequestException, 
                    requests.exceptions.HTTPError,
                    TranslationException) as e:
                last_exception = e
                
                # Check if we should retry
                if attempts >= max_retries:
                    error_msg = f"Translation failed after {max_retries} retries: {e}"
                    self.logger.error(error_msg)
                    print(f"\n❌ FATAL ERROR: {error_msg}")
                    sys.exit(1)
                
                # Check time limit again before waiting
                elapsed_time = time.time() - start_time
                if elapsed_time >= total_time_limit:
                    error_msg = (f"Translation failed: Exceeded total time limit of {total_time_limit/60:.1f} minutes "
                               f"after {attempts} attempts. Last error: {e}")
                    self.logger.error(error_msg)
                    print(f"\n❌ FATAL ERROR: {error_msg}")
                    sys.exit(1)
                
                # Calculate wait time with exponential backoff
                wait_time = min(retry_wait_base * (2 ** (attempts - 1)), retry_wait_max)
                wait_time = max(wait_time, retry_wait_min)
                
                # Don't wait if it would exceed time limit
                if elapsed_time + wait_time >= total_time_limit:
                    wait_time = max(0, total_time_limit - elapsed_time - 1)
                
                if wait_time > 0:
                    self.logger.warning(f"Waiting {wait_time:.1f}s before retry. Error: {e}")
                    time.sleep(wait_time)
                    
        # Should never reach here, but just in case
        error_msg = f"Translation failed: Unexpected exit from retry loop"
        self.logger.error(error_msg)
        print(f"\n❌ FATAL ERROR: {error_msg}")
        sys.exit(1)
        
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


# These functions are already imported from common_text_utils at the top of the file



# Precompute allowed ASCII characters (letters, digits, punctuation)
ALLOWED_ASCII = set(string.ascii_letters + string.digits + string.punctuation)

@functools.lru_cache(maxsize=None)
def is_latin_char(char: str) -> bool:
    """
    Returns True if the non-ASCII character belongs to the Latin script
    based on its Unicode name.
    """
    # Check if it's a digit first
    if char.isdigit():
        return True
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
    # Special case: empty string or only whitespace
    if not text or text.isspace():
        return True  # Consider empty/whitespace as Latin
    
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

    # If no non-whitespace characters, consider as Latin
    if total_count == 0:
        return True
    
    # If no Latin characters were found, consider the text as not Latin.
    if latin_count == 0:
        return False

    non_latin_count = total_count - latin_count
    ratio = non_latin_count / latin_count
    return ratio < threshold
    


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
    def __init__(self, logger: Optional[logging.Logger] = None, use_remote: bool = False,
                 api_key: Optional[str] = None, endpoint: Optional[str] = None,
                 model: Optional[str] = None, temperature: float = 0.05,
                 max_tokens: Optional[int] = None, timeout: Optional[int] = None,
                 config: Optional[Dict[str, Any]] = None,
                 max_retries: Optional[int] = None, retry_wait_base: Optional[float] = None,
                 retry_wait_min: Optional[float] = None, retry_wait_max: Optional[float] = None,
                 connection_timeout: Optional[int] = None, double_pass: Optional[bool] = None,
                 system_prompt: Optional[str] = None, user_prompt_1st_pass: Optional[str] = None,
                 user_prompt_2nd_pass: Optional[str] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.api_key = api_key or os.environ.get('OPENROUTER_API_KEY')
        self.is_remote = use_remote
        self.temperature = temperature
        self.max_tokens = max_tokens or DEFAULT_MAX_TOKENS
        # pricing_manager parameter deprecated - cost tracking handled by global_cost_tracker
        self.config = config or {}
        
        # Retry settings
        self.max_retries = max_retries or 7
        self.retry_wait_base = retry_wait_base or 1.0
        self.retry_wait_min = retry_wait_min or 3.0
        self.retry_wait_max = retry_wait_max or 60.0
        
        # Connection settings
        self.connection_timeout = connection_timeout or CONNECTION_TIMEOUT
        
        # Double pass setting
        self.double_pass = double_pass
        
        # Cost tracking is handled by global_cost_tracker from cost_tracker module
        # Keep local counters for backward compatibility and session-specific stats
        self._cost_lock = threading.Lock()
        self.request_count = 0
        
        if self.is_remote:
            if not self.api_key:
                error_msg = "OPENROUTER_API_KEY not set in environment variables"
                self.log(error_msg, "error")
                raise ValueError(error_msg)
            self.api_url = endpoint or API_URL_OPENROUTER
            self.MODEL_NAME = model or MODEL_NAME_DEEPSEEK
            self.SYSTEM_PROMPT = system_prompt if system_prompt is not None else SYSTEM_PROMPT_DEEPSEEK
            self.USER_PROMPT_1STPASS = user_prompt_1st_pass if user_prompt_1st_pass is not None else USER_PROMPT_1STPASS_DEEPSEEK
            self.USER_PROMPT_2NDPASS = user_prompt_2nd_pass if user_prompt_2nd_pass is not None else USER_PROMPT_2NDPASS_DEEPSEEK
            self.timeout = timeout or RESPONSE_TIMEOUT
            # Set default double_pass if not specified
            if self.double_pass is None:
                self.double_pass = True
        else:
            self.api_url = endpoint or API_URL_LMSTUDIO
            self.MODEL_NAME = model or MODEL_NAME_QWEN
            self.SYSTEM_PROMPT = system_prompt if system_prompt is not None else SYSTEM_PROMPT_QWEN
            self.USER_PROMPT_1STPASS = user_prompt_1st_pass if user_prompt_1st_pass is not None else USER_PROMPT_1STPASS_QWEN
            self.USER_PROMPT_2NDPASS = user_prompt_2nd_pass if user_prompt_2nd_pass is not None else USER_PROMPT_2NDPASS_QWEN
            self.timeout = timeout or RESPONSE_TIMEOUT
            # Set default double_pass if not specified
            if self.double_pass is None:
                self.double_pass = False
        
    def log(self, message: str, level: str = "info") -> None:
        try:
            log_method = getattr(self.logger, level)
            log_method(message)
        except AttributeError:
            # Fallback to info if invalid level provided
            self.logger.info(f"[{level.upper()}] {message}")

    def remove_thinking_block(self, content:str) -> str:
        # Remove Think Tag from Text with Regular Expressions
        content = re.sub(r"<think>.*?</think>\n?", "", content, flags=re.DOTALL)
        content = re.sub(r"<thinking>.*?</thinking>\n?", "", content, flags=re.DOTALL)
        return content

    def remove_custom_tags(self, text: str, keyword: str, ignore_case: bool = True) -> str:
        # Escape keyword in case it contains regex special characters
        escaped_keyword = re.escape(keyword)
        # Build a regex pattern for all variants with different delimiters
        # Include both opening and closing tags
        pattern_str = (
            rf"(</?{escaped_keyword}>|\[/?{escaped_keyword}\]|\{{/?{escaped_keyword}\}}|\(/?{escaped_keyword}\)|##{escaped_keyword}##)"
        )
        # Set regex flags based on the optional parameter
        flags = re.IGNORECASE if ignore_case else 0
        pattern = re.compile(pattern_str, flags)
        # Substitute all occurrences with an empty string
        return pattern.sub("", text)
        
    def remove_excess_empty_lines(self, txt: str) -> str:
        """Match 5 or more newline characters and replace with 4."""
        return re.sub(r'\n{5,}', '\n\n\n\n', txt)
    
        
    def normalize_spaces(self, text: str) -> str:
        """Normalize spaces in text while preserving paragraph structure."""
        lines = text.split('\n')
        normalized_lines = []
        
        for line in lines:
            stripped_line = line.strip()
            if stripped_line:
                # Replace multiple spaces with a single space
                normalized_line = ' '.join(stripped_line.split())
                normalized_lines.append(normalized_line)
            else:
                # Preserve empty lines
                normalized_lines.append('')
        
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
        

    
    def translate_chunk(self, chunk: str, double_translation: Optional[bool] = None, is_last_chunk: bool = False) -> str:
        # Use instance's double_pass setting if not explicitly overridden
        if double_translation is None:
            double_translation = self.double_pass
            
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
        
        ## RETURN THE FINAL TRANSLATED STRING
        return final_translation


    
    @retry_with_tenacity
    def translate_messages(self, messages: str, is_last_chunk: bool = False) -> str:
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
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "stream": False,
#            "top_p": 0,
#            "frequency_penalty": 0,
#            "presence_penalty": 0,
#            "repetition_penalty": 1.1,
#            "top_k": 0,
        }
        
        # Add usage tracking for OpenRouter remote API
        if self.is_remote:
            data["usage"] = {"include": True}
    
        try:
            ##response = requests.get("http://10.255.255.1", timeout=(5, 10))    # Uncomment to test Tenacity auto retry
            response = requests.post(self.api_url, headers=headers, json=data, timeout=(self.connection_timeout, self.timeout))
            self.log(f"Request sent to {self.api_url}")
            response.raise_for_status()
            self.log(f"Server returned RESPONSE: \n{response.json()}")
            
            # Track costs
            result: Dict[str, Any] = response.json()
            if 'usage' in result:
                usage = result['usage']
                
                if self.is_remote:
                    # Use unified cost tracker for OpenRouter
                    cost = global_cost_tracker.track_usage(usage)
                    with self._cost_lock:
                        self.request_count += 1
                    
                    self.log("\n=== Token Usage ===")
                    self.log(f"Prompt tokens: {usage.get('prompt_tokens', 0)}")
                    self.log(f"Completion tokens: {usage.get('completion_tokens', 0)}")
                    self.log(f"Total tokens: {usage.get('total_tokens', 0)}")
                    if cost > 0:
                        self.log(f"Cost for this request: ${cost:.6f}")
                    summary = global_cost_tracker.get_summary()
                    self.log(f"Cumulative cost: ${summary['total_cost']:.6f}")
                    self.log(f"Total requests so far: {summary['request_count']}")
                else:
                    # For local API, just log token usage
                    self.log("\n=== Token Usage (Local API) ===")
                    self.log(f"Prompt tokens: {usage.get('prompt_tokens', 0)}")
                    self.log(f"Completion tokens: {usage.get('completion_tokens', 0)}")
                    self.log(f"Total tokens: {usage.get('total_tokens', 0)}")
                    self.log("Local API - no costs incurred")
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


    def translate_file(self, input_file: str, output_file: str, is_last_chunk=False) -> Optional[str]:
        self.log(f"Translating file: {input_file}")
        try:
            with open(input_file, 'r', encoding='utf-8') as file:
                chinese_text = file.read()
            
            if not chinese_text.strip():
                self.log("Input file is empty or contains only whitespace", "warning")
                return ""
            
            english_text = self.translate_chunk(chinese_text, is_last_chunk=is_last_chunk)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(english_text)
            
            return english_text
        except Exception as e:
            self.log(f"Translation failed: {str(e)}", "error")
            return None


    def translate(self, input_string: str, is_last_chunk: bool = False) -> str:
        #self.log(f"Translating text: {input_string}")
        if not input_string.strip():
            self.log("Input string is empty or contains only whitespace", "warning")
            return ""
        
        try:
            chinese_text = input_string
            english_text = self.translate_chunk(chinese_text, double_translation=None, is_last_chunk=is_last_chunk)
        except Exception as ex:
            self.log(f"Unexpected error during file translation: {ex}", "error")
            return None
        return english_text
    
    def get_cost_summary(self) -> Dict[str, Any]:
        """Get cumulative cost summary for remote API usage."""
        # Get summary from global cost tracker
        summary = global_cost_tracker.get_summary()
        
        # Add model and API type information
        summary['model'] = self.MODEL_NAME
        
        if self.is_remote:
            summary['api_type'] = 'remote'
        else:
            summary['api_type'] = 'local'
            summary['message'] = 'Local API - no costs incurred'
            # Override cost fields for local API
            summary['total_cost'] = 0.0
            summary['average_cost_per_request'] = 0.0
            
        return summary
    
    def format_cost_summary(self) -> str:
        """Format cost summary for display."""
        summary = self.get_cost_summary()
        
        if self.is_remote:
            lines = [
                "\n=== Translation Cost Summary ===",
                f"Model: {summary['model']}",
                f"API Type: {summary['api_type']}",
                f"Total Cost: ${summary['total_cost']:.6f}",
                f"Total Requests: {summary['request_count']}",
                f"Total Tokens: {summary['total_tokens']:,}",
                f"  - Prompt Tokens: {summary['total_prompt_tokens']:,}",
                f"  - Completion Tokens: {summary['total_completion_tokens']:,}",
            ]
            if summary['request_count'] > 0:
                lines.append(f"Average Cost per Request: ${summary['average_cost_per_request']:.6f}")
                lines.append(f"Average Tokens per Request: {summary['total_tokens'] // summary['request_count']:,}")
            return "\n".join(lines)
        else:
            return f"\n=== Translation Cost Summary ===\nModel: {summary['model']}\nAPI Type: {summary['api_type']}\nLocal API - no costs incurred"
    
    def reset_cost_tracking(self) -> None:
        """Reset cost tracking counters."""
        # Reset global tracker
        global_cost_tracker.reset()
        
        # Reset local counter
        with self._cost_lock:
            self.request_count = 0


# Example usage:
if __name__ == "__main__":
    translator = ChineseAITranslator(use_remote=False)
    english_text = translator.translate_file(
        input_file="dummy_chinese.txt", 
        output_file="output.txt"
    )
    if english_text:
        print("Translation completed successfully.")



