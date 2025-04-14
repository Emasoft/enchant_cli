#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright (c) 2024 Emasoft
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0

from __future__ import annotations

import os
import logging
import requests
import json
import re
import time
from typing import Any, Dict, Optional
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, wait_none, retry_if_exception

# Import shared utilities
from .utils import (
    clean,
    limit_repeated_chars,
    remove_html_markup,
    normalize_spaces,
    remove_excess_empty_lines,
    is_latin_charset,
    replace_repeated_chars, # Ensure this is imported if used directly
    SENTENCE_ENDING, # Import constants if needed
    CLOSING_QUOTES,
    NON_BREAKING,
    ALL_PUNCTUATION,
    PARAGRAPH_DELIMITERS,
    PRESERVE_UNLIMITED,
    CHINESE_PUNCTUATION,
    ENGLISH_PUNCTUATION,
)

# Global API configuration - This captures the key at import time.
# It's still useful for checks outside the constructor or for default values.
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")

# Constants moved to utils.py:
# SENTENCE_ENDING, CLOSING_QUOTES, NON_BREAKING, ALL_PUNCTUATION
# CHINESE_PUNCTUATION, ENGLISH_PUNCTUATION
# PARAGRAPH_DELIMITERS, PRESERVE_UNLIMITED
# _repeated_chars regex

# Functions moved to utils.py:
# clean, replace_repeated_chars, limit_repeated_chars
# extract_code_blocks, extract_inline_code, remove_html_comments,
# remove_script_and_style, replace_block_tags, remove_remaining_tags,
# unescape_non_code_with_placeholders, remove_html_markup
# remove_excess_empty_lines, normalize_spaces
# is_latin_charset


# Define a custom exception for translation failures
class TranslationException(Exception):
    pass


DEFAULT_CHUNK_SIZE = 6000

class ChineseAITranslator:
    def __init__(self, logger: Optional[logging.Logger] = None, verbose: bool = False, min_chunk_length: int = 300):
        self.logger = logger or logging.getLogger(__name__)
        self.verbose = verbose
        self.min_chunk_length = min_chunk_length
        self.api_url = 'https://openrouter.ai/api/v1/chat/completions'
        self.MODEL_NAME = "deepseek/deepseek-r1:nitro" # Default model

        # Use faster model and smaller chunk size in test environments
        if os.environ.get("CI") or os.environ.get("TEST_ENV"):
            self.MODEL_NAME = "google/palm-2"  # Faster model for testing
            self.min_chunk_length = 10  # Allow smaller chunks for testing
            self.logger.info(f"Test environment detected. Using model: {self.MODEL_NAME}, min_chunk_length: {self.min_chunk_length}")

        # Check os.environ directly inside __init__ to respect monkeypatching in tests
        if not os.environ.get("OPENROUTER_API_KEY"):
             self.logger.warning("OPENROUTER_API_KEY environment variable not set. Translation will likely fail.")
             # Optionally raise an error here if the key is absolutely required at init time
             # raise ValueError("OPENROUTER_API_KEY is not set.")


    def compute_costs(self, completion_response) -> float:
        """Computes and returns the cost in USD for a generation request."""
        # Ensure API key is available
        api_key = os.environ.get('OPENROUTER_API_KEY')
        if not api_key:
            self.log("Cannot compute cost, OPENROUTER_API_KEY not found.", "warning")
            return 0.0

        try:
            # Get the completion response data
            completion_data: Dict[str, Any] = completion_response.json()

            # Extract the generation ID from the response
            generation_id = completion_data.get("id")
            if not generation_id:
                 self.log("Could not find generation ID in completion response.", "warning")
                 return 0.0


            # Headers for the request
            headers = {"Authorization": f"Bearer {api_key}"}

            # Wait a moment for the generation stats to be available
            if self.verbose:
                self.log("Waiting for generation stats to be available...")
            time.sleep(2)  # Wait for 2 seconds

            # Make a request to get the generation stats
            querystring = {"id": f"{generation_id}"}
            generation_api_url = "https://openrouter.ai/api/v1/generation"
            generation_response = requests.get(generation_api_url, headers=headers, params=querystring)
            generation_response.raise_for_status() # Raise exception for bad status codes
            if self.verbose:
                self.log(f"GENERATION RESPONSE: {str(generation_response.json())}")

            generation_stats: Dict[str, Any] = generation_response.json()

            # Extract cost, handling potential missing keys
            cost_str = generation_stats.get('data', {}).get('total_cost')
            cost = float(cost_str) if cost_str is not None else 0.0

            # Print detailed info only if verbose
            if self.verbose:
                self.log("\n\n=== Token Usage ===")
                usage = completion_data.get('usage', {})
                self.log(f"Prompt tokens: {usage.get('prompt_tokens', 'N/A')}")
                self.log(f"Completion tokens: {usage.get('completion_tokens', 'N/A')}")
                self.log(f"Total tokens: {usage.get('total_tokens', 'N/A')}")

                self.log("\n=== Generation Stats ===")
                self.log(f"Cost in USD: ${cost:.6f}") # Format cost

                # Make a request to get the credits stats only if verbose
                try:
                    credits_api_url = "https://openrouter.ai/api/v1/credits"
                    credits_response = requests.get(credits_api_url, headers=headers)
                    credits_response.raise_for_status()
                    self.log(f"CREDITS RESPONSE: {str(credits_response.json())}")
                    credits_data: Dict[str, Any] = credits_response.json()

                    self.log("\n=== Credits Information ===")
                    total_credits = credits_data.get('data', {}).get('total_credits', 0.0)
                    total_usage = credits_data.get('data', {}).get('total_usage', 0.0)
                    self.log(f"Total credits: ${total_credits:.6f}")
                    self.log(f"Total usage: ${total_usage:.6f}")
                    self.log(f"Remaining credits: ${total_credits - total_usage:.6f}")
                except requests.exceptions.RequestException as e_credits:
                     self.log(f"Could not fetch credits info: {e_credits}", "warning")
                except (KeyError, ValueError, TypeError, json.JSONDecodeError) as e_credits_proc:
                     self.log(f"Error processing credits data: {e_credits_proc}", "warning")

                self.log("\n\n") # End verbose block

            return cost

        except requests.exceptions.RequestException as e:
            self.log(f"API request failed during cost computation: {e}", "error")
            return 0.0
        except (KeyError, ValueError, TypeError, json.JSONDecodeError) as e:
            self.log(f"Error processing cost data: {e}", "error")
            return 0.0

    def log(self, message: str, level: str = "info") -> None:
        """Logs a message using the configured logger."""
        log_method = getattr(self.logger, level, self.logger.info) # Default to info if level is invalid
        log_method(message)

    def remove_thinking_block(self, content:str) -> str:
        """Remove <think>...</think> or <thinking>...</thinking> blocks."""
        content = re.sub(r"<think>.*?</think>\n?", "", content, flags=re.DOTALL)
        content = re.sub(r"<thinking>.*?</thinking>\n?", "", content, flags=re.DOTALL)
        return content

    def remove_custom_tags(self, text, keyword, ignore_case=True):
        """Remove various bracketed/delimited versions of a keyword tag."""
        escaped_keyword = re.escape(keyword)
        # Pattern covers <tag>, [tag], {tag}, (tag), ##tag##
        pattern_str = (
            rf"(?:<{escaped_keyword}>|\[{escaped_keyword}\]|\{{{escaped_keyword}\}}|\({escaped_keyword}\)|##{escaped_keyword}##)"
        )
        flags = re.IGNORECASE if ignore_case else 0
        pattern = re.compile(pattern_str, flags)
        return pattern.sub("", text)

    def remove_translation_markers(self, txt: str) -> str:
        """Removes various 'End/Start of translation', 'English Translation', etc. markers."""
        # Pattern for End/Start of translation variations
        end_start_pattern = r"[\[\(\-\*\s]*[-]*\[?(?:End|Start)\s+of\s+translation\]?[\.\-\)\]\s]*[\.\-]*[\)\]\*\s]*"
        cleaned_txt = re.sub(end_start_pattern, '', txt, flags=re.IGNORECASE)

        # Pattern for English Translation variations
        eng_trans_pattern = r"[\[\(\-\*\s]*[-]*\[?English\s+Translation\]?[\.\-\)\]\s]*[\.\-]*[\)\]\*\s]*"
        cleaned_txt = re.sub(eng_trans_pattern, '', cleaned_txt, flags=re.IGNORECASE)

        # Remove other specific tags using the helper function
        tags_to_remove = [
            "DECLARATION", "TRANSLATION", "TRANSLATED TEXT", "ENGLISH TEXT",
            "REVISED TEXT", "CORRECTED TEXT", "TRANSLATED IN ENGLISH",
            "TEXT TRANSLATED IN ENGLISH", "FIXED TEXT", "ENGLISH TRANSLATED TEXT",
            "ENGLISH VERSION", "TRANSLATED VERSION"
        ]
        for tag in tags_to_remove:
            cleaned_txt = self.remove_custom_tags(cleaned_txt, tag)

        # Remove html markup using util function
        cleaned_txt = remove_html_markup(cleaned_txt)

        # Normalize spaces and empty lines using util functions
        cleaned_txt = normalize_spaces(cleaned_txt)
        cleaned_txt = remove_excess_empty_lines(cleaned_txt)

        # Final clean using util function
        cleaned_txt = clean(cleaned_txt)

        return cleaned_txt


    def translate_chunk(self, chunk: str, double_translation: bool = False, is_last_chunk: bool = False) -> tuple[str, float]:
        """Translates a single chunk, optionally performing a second refinement pass."""
        self.log(f"Preparing to translate chunk (length: {len(chunk)} chars). Double translation: {double_translation}.")
        total_cost = 0.0

        # --- Prompt for First Translation Pass ---
        prompt1 = f"""[Task]
You are a professional and helpful translator specializing in Chinese literature (including web novels like wuxia/xianxia) and technical documents. You are proficient in both languages and possess a deep understanding of cultural nuances. Your goal is to produce translations that are not only accurate but also capture the style, tone, and fluency of a native English text. Always write in excellent and refined English prose, following a polished writing style.

Your task is to translate the provided Chinese text into English. Output ONLY the fully translated English text.

[Constraints & Rules]
1.  **Output Only Translation:** Do NOT add comments, annotations, messages, greetings, or any text other than the direct English translation.
2.  **Completeness:** Translate every word and character. Do not omit sentences, paragraphs, or any information present in the original. Never abridge the translation.
3.  **No Chinese Characters:** The final output must contain ZERO Chinese characters (neither traditional nor simplified).
4.  **Accuracy & Fluency:** The translation must be grammatically correct, fluent, and natural-sounding English. Avoid literal, mechanical translations. Aim for a high-quality literary level.
5.  **Style & Tone:** Maintain the original text's style (e.g., formal, informal, poetic, technical) and tone (e.g., humorous, serious, suspenseful).
6.  **Formatting:** Preserve basic paragraph structure. Maintain the original's use of line breaks where significant.
7.  **Quotes:** Always use proper English curly quotation marks (“ ” for outer quotes, ‘ ’ for inner quotes). Convert any straight quotes (" ' `) or non-standard quotes (like 「」, 『』, «») to curly quotes. Ensure quotes are correctly paired; add missing partners where contextually appropriate (e.g., translate `“通行證？”` as `“A pass?”`).
8.  **Names:**
    *   Use standard Pinyin romanization for names unless a widely accepted English equivalent exists.
    *   Optionally, include the meaning of names in parentheses *only on their first significant appearance* if it adds cultural context relevant to the story (e.g., `Tang Wutong (Dancing Willow)`). Be consistent; don't add meanings repeatedly.
9.  **Genre-Specific Terms (Wuxia/Xianxia):** Use established English terminology for cultivation concepts, sects, skills, etc. (e.g., `元婴` -> `Nascent Soul`, `筑基` -> `Foundation Establishment`, `金丹` -> `Golden Core`). Maintain consistency with these terms.
10. **Pronouns & Gender:** Infer the correct gender of characters from context and use appropriate English pronouns (he/she/him/her) consistently. Avoid ambiguous or neutral terms for people where gender is implied.
11. **Family/Honorific Terms:** Translate terms like `弟弟` (didi) contextually. If used in direct address, translate as `younger brother`. If used descriptively with a possessive in Chinese (e.g., `他的弟弟`), translate as `his younger brother`. Apply similar logic to `哥哥` (gege - older brother), `姐姐` (jiejie - older sister), `妹妹` (meimei - younger sister), `叔叔` (shushu - uncle), etc.
12. **Ambiguity/Missing Text:** If parts of the Chinese text are unclear or seem incomplete, use the surrounding context to infer the most likely meaning and provide a fluent, coherent translation. Do not simply state that the text is unclear. Translate even potentially truncated final lines.
13. **Consistency:** Maintain consistent terminology for names, places, unique items, and concepts throughout the entire translation. Use the same writing style consistently.

[CHINESE TEXT TO TRANSLATE]
```
{chunk}
```

[Output]
(Provide only the English translation below this line)
"""
        ## --- Perform First Translation ---
        try:
            first_translation, cost1 = self.translate_messages(prompt1, is_last_chunk)
            total_cost += cost1
            self.log(f"First translation pass completed. Cost: ${cost1:.6f}")
            # Clean markers immediately after receiving response
            first_translation = self.remove_translation_markers(first_translation)
            if not first_translation:
                 self.log("First translation pass returned empty content after cleaning.", "warning")
                 # Decide if we should retry or return empty
                 # For now, return empty and zero cost if first pass fails badly
                 return "", total_cost

        except Exception as e:
             self.log(f"Error during first translation pass: {e}", "error")
             # Decide how to handle: re-raise, return partial, return error marker?
             # Re-raising allows tenacity to handle retries if configured at a higher level
             raise TranslationException(f"First translation pass failed: {e}") from e


        ## --- Perform Second (Refinement) Translation if requested ---
        if double_translation:
            self.log("Performing second refinement translation pass.")
            # --- Prompt for Second Translation Pass ---
            prompt2 = f"""[Task]
You are an expert English editor and proofreader specializing in refining translations from Chinese. You will be given a piece of English text that was previously translated from Chinese. Your task is to meticulously review and improve this text based on the following rules, ensuring perfect English fluency, accuracy, and consistency, while eliminating any remaining Chinese characters or translation artifacts.

[Input Text Analysis]
The provided text is an English translation of a Chinese original. It may contain:
*   Lingering Chinese characters or Pinyin that were missed.
*   Awkward phrasing or unnatural English constructions ("translationese").
*   Incorrect or inconsistent use of terminology (especially for names or genre-specific concepts).
*   Improper quotation mark usage (straight quotes instead of curly quotes).
*   Minor grammatical errors or typos.

[Editing & Refinement Rules]
1.  **Eliminate All Chinese:** Find and replace EVERY remaining Chinese character or Pinyin syllable with its correct English translation or standard romanization, using context to ensure accuracy. The final output must be 100% English.
2.  **Ensure Fluency:** Rephrase any awkward sentences or unnatural "translationese" to sound like native, polished English prose. Improve flow and clarity.
3.  **Correct Terminology:** Ensure consistency and correctness of names, places, and genre-specific terms (e.g., cultivation levels). Use standard English equivalents.
4.  **Fix Quotes:** Convert all straight quotes (`"`, `'`) to proper English curly quotes (`“ ”`, `‘ ’`). Ensure correct nesting and pairing.
5.  **Grammar & Style:** Correct any grammatical errors, typos, or punctuation mistakes. Maintain a consistent, high-quality literary style.
6.  **Completeness:** Do NOT remove or summarize any part of the text. The refined output must contain the same information as the input.
7.  **Output Only Refined Text:** Do NOT add any comments, notes, or explanations. Output only the final, perfected English text.

[TEXT TO REFINE]
```
{first_translation}
```

[Output]
(Provide only the refined English text below this line)
"""
            try:
                final_translation, cost2 = self.translate_messages(prompt2, is_last_chunk)
                total_cost += cost2
                self.log(f"Second translation pass completed. Cost: ${cost2:.6f}")
                # Clean markers again after second pass
                final_translation = self.remove_translation_markers(final_translation)
                if not final_translation:
                     self.log("Second translation pass returned empty content after cleaning. Using result from first pass.", "warning")
                     final_translation = first_translation # Fallback to first pass result

            except Exception as e:
                 self.log(f"Error during second translation pass: {e}. Using result from first pass.", "error")
                 # If second pass fails, fall back to the result of the first pass
                 final_translation = first_translation
        else:
            # If double translation is not enabled, the result from the first pass is the final one
            final_translation = first_translation

        ## --- Final Cleanup (Optional, potentially redundant if cleaning is good) ---
        # final_translation = self.separate_chapters(final_translation) # Example cleanup

        ## RETURN THE FINAL TRANSLATED STRING AND TOTAL COST
        self.log(f"Chunk translation finished. Final length: {len(final_translation)}. Total cost for chunk: ${total_cost:.6f}")
        return final_translation, total_cost


    # Custom retry condition to avoid retrying on 401/404
    def _should_retry_translation(exception):
        if isinstance(exception, requests.exceptions.HTTPError):
            # Do not retry on 401 (Unauthorized) or 404 (Not Found)
            return exception.response.status_code not in [401, 404]
        # Retry on other RequestExceptions, HTTPError (like 5xx), and our custom TranslationException
        return isinstance(exception, (requests.exceptions.RequestException, TranslationException))

    @retry(
        stop=stop_after_attempt(5),  # Retry up to 5 times
        wait=wait_exponential(multiplier=1, min=2, max=60),  # Exponential backoff: 2s, 4s, 8s, 16s, 30s (max)
        retry=retry_if_exception(_should_retry_translation), # Use custom retry condition
        before_sleep=lambda retry_state: logging.getLogger(__name__).warning(f"Retrying translation request (attempt {retry_state.attempt_number}) after error: {retry_state.outcome.exception()}")
    )
    def translate_messages(self, prompt: str, is_last_chunk=False) -> tuple[str, float]:
        """Sends the prompt to the OpenRouter API and handles retries."""
        # Ensure API key is available for each attempt
        api_key = os.environ.get('OPENROUTER_API_KEY')
        if not api_key:
            self.log("OPENROUTER_API_KEY not found.", "error")
            # Raising allows retry logic to potentially catch it if key appears later,
            # but likely better to fail fast if key is missing.
            raise TranslationException("OpenRouter API key not configured.")

        self.log(f"Sending translation request to API. Model: {self.MODEL_NAME}")
        cost = 0.0  # Initialize cost for this attempt
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost", # Optional: Add referrer
            "X-Title": "Enchant CLI", # Optional: Add title
        }
        data: Dict[str, Any] = {
            "model": self.MODEL_NAME,
            "messages": [
                {
                    "role": "user",
                    "content": prompt, # Use the passed prompt directly
                }
            ],
            "temperature": 0.6, # Adjust as needed
            "max_tokens": None, # Let the model decide based on input/output needs
            "stream": False, # Keep stream false for simpler handling
        }

        try:
            response = requests.post(self.api_url, headers=headers, json=data, timeout=180) # Add timeout (e.g., 3 minutes)
            self.log(f"API request sent to {self.api_url}. Status Code: {response.status_code}")
            response.raise_for_status() # Check for HTTP errors (4xx, 5xx)

            if self.verbose:
                try:
                    # Log the full response only in verbose mode
                    self.log(f"Server returned RESPONSE: \n{json.dumps(response.json(), indent=2)}")
                except json.JSONDecodeError:
                    self.log(f"Server returned non-JSON response: {response.text}")

            # --- Process successful response ---
            result: Dict[str, Any] = response.json()
            cost = self.compute_costs(response) # Calculate cost based on successful response

            if 'choices' in result and len(result['choices']) > 0 and 'message' in result['choices'][0] and 'content' in result['choices'][0]['message']:
                content = str(result['choices'][0]['message']['content'])
                content = self.remove_thinking_block(content) # Remove <think> tags

                # --- Content Validation ---
                if not content:
                     self.log("API returned empty content.", "warning")
                     # Consider if empty content is a valid translation or an error
                     # If it's an error, raise TranslationException to retry
                     raise TranslationException("API returned empty content.")

                # Check if the content is primarily Latin-based.
                if not is_latin_charset(content):
                    self.log("Translated text does not appear to be in a Latin-based charset. Retrying...", "warning")
                    raise TranslationException("Translated text does not appear to be in a Latin-based charset.")

                # Check minimum length (unless it's the very last chunk)
                if len(content) < self.min_chunk_length and not is_last_chunk:
                    self.log(f"Translated text too short ({len(content)} < {self.min_chunk_length}). Retrying...", "warning")
                    raise TranslationException(f"Translated text is too short ({len(content)} chars). Retrying...")

                self.log(f"Successfully received and validated translation content (length: {len(content)}).")
                return content, cost
            else:
                # This case means the API call succeeded (2xx) but the response structure was wrong
                self.log("Unexpected response structure from API (missing choices/content).", "error")
                # Raise TranslationException to trigger retry, as this indicates an API issue
                raise TranslationException("Unexpected response structure from Open Router API.")

        # --- Exception Handling for Retries ---
        except requests.exceptions.Timeout as timeout_err:
             self.log(f"Request timed out: {timeout_err}", "warning")
             raise # Re-raise Timeout to allow tenacity to retry

        except requests.exceptions.HTTPError as http_err:
            # Log specific details for common errors
            if http_err.response.status_code == 401:
                 self.log("HTTP 401 Unauthorized: Check your API key.", "error")
                 # Retry condition in decorator now handles this
                 raise # Re-raise the original HTTPError
            elif http_err.response.status_code == 404:
                 self.log(f"HTTP 404 Not Found: Check API endpoint or model name ('{self.MODEL_NAME}').", "error")
                 raise # Re-raise the original HTTPError (retry condition handles stopping)
            elif http_err.response.status_code == 429:
                 self.log("HTTP 429 Too Many Requests: Rate limit likely exceeded.", "warning")
                 # Tenacity's exponential backoff will handle waiting
            elif http_err.response.status_code >= 500:
                 self.log(f"HTTP Server Error ({http_err.response.status_code}): {http_err}", "warning")
                 # Server errors are good candidates for retrying
            else:
                 self.log(f"HTTP error occurred: {http_err}", "warning")
            raise # Re-raise to allow tenacity to retry (unless stopped by retry condition)

        except requests.exceptions.RequestException as req_err:
            # Catch other request exceptions (like connection errors)
            self.log(f"Request exception: {req_err}", "warning")
            raise # Re-raise to allow tenacity to retry

        except json.JSONDecodeError as json_err:
            # If the response isn't valid JSON (might happen on server errors)
            self.log(f"JSON decode error: {json_err}. Response text: {response.text[:500]}...", "warning")
            # Treat as a server-side issue, potentially retry
            raise TranslationException(f"Failed to decode API response: {json_err}") from json_err

        except TranslationException as trans_err:
            # Catch validation errors raised within this function
            self.log(f"Translation validation failed: {trans_err}", "warning")
            raise # Re-raise to allow tenacity to retry

        except Exception as e:
            # Catch any other unexpected errors
            self.log(f"An unexpected error occurred during API call: {e}", "error")
            # Wrap in TranslationException to potentially allow retry
            raise TranslationException(f"Unexpected error during API call: {e}") from e


    def separate_chapters(self, text: str) -> str:
        """Adds extra newlines before chapter headings."""
        # Define patterns for chapter headings (adjust as needed)
        patterns = [
            # Chapter X: Title or Chapter X - "Title" - Part 1
            r'\b(Chapter\s+\d+\s*[-:—.]*\s*[\"«"]?[A-Za-z0-9\s.,:;!?\'’`‘…]*[\"»"]?\s*[-:—.]*\s*Part\s*\d*)',
            # Chapter in Roman numerals like CHAPTER V: The Finale - Part 1
            r'\b(Chapter\s+[IVXLC]+\s*[-:—.]*\s*[\"«"]?[A-Za-z0-9\s.,:;!?\'’`‘…]*[\"»"]?\s*[-:—.]*\s*Part\s*\d*)',
            # Chapter One - Title - Part 1
            r'\b(Chapter\s+\w+\s*[-:—.]*\s*[\"«"]?[A-Za-z0-9\s.,:;!?\'’`‘…]*[\"»"]?\s*[-:—.]*\s*Part\s*\d*)',
            # Chapter 3: My Farewell, Chapter 3 - My Farewell, etc.
            r'\b(Chapter\s+\d+\s*[-:—]*\s*.*)',
            # Chapter IX - My Farewell
            r'\b(Chapter\s+[IVXLC]+\s*[-:—]*\s*.*)',
            # Chapter One - My Farewell
            r'\b(Chapter\s+\w+\s*[-:—]*\s*.*)',
            # Chapter on its own line (less specific, place later)
            r'^\s*(Chapter\s*(?:\d+|[IVXLC]+|\w+))\s*$',
            # Prologue and Epilogue on their own lines
            r'^\s*(Prologue|Epilogue)\s*$',
        ]
        # Combine patterns, ensure case-insensitivity and multiline matching
        chapter_pattern = re.compile('|'.join(f"({p})" for p in patterns), re.IGNORECASE | re.MULTILINE)

        # Use a function for replacement to handle potential overlapping matches if needed
        # and ensure exactly 3 newlines before the matched heading
        def repl(match):
            # Find which group matched (non-empty group)
            heading = next(g for g in match.groups() if g is not None)
            return f'\n\n\n{heading.strip()}\n\n' # Add newlines before and after stripped heading

        # Apply the replacement
        # Note: This simple sub might insert extra newlines if patterns overlap significantly.
        # A more robust approach might involve iterating through matches.
        separated_text = chapter_pattern.sub(r'\n\n\n\1\n\n', text)

        # Clean up potential excessive newlines created by the substitution
        return remove_excess_empty_lines(separated_text)


    def translate(self, input_string: str, double_translation: bool = False, is_last_chunk: bool = False) -> tuple[str, float]:
        """Main entry point for translating a string (chunk)."""
        self.log(f"Starting translation for input string (length: {len(input_string)} chars).")
        if not input_string:
             self.log("Input string is empty, skipping translation.", "warning")
             return "", 0.0
        try:
            # Call the chunk translation logic
            english_text, cost = self.translate_chunk(
                input_string,
                double_translation=double_translation,
                is_last_chunk=is_last_chunk
            )
            self.log("Translation process completed for the input string.")
            return english_text, cost
        except Exception as ex:
            # Catch errors from translate_chunk (including retries failing)
            self.log(f"Failed to translate input string after retries: {ex}", "error")
            # Return empty string and zero cost to indicate failure at this level
            return "", 0.0

