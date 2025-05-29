import os
import logging
import requests
import json
import re
from typing import Optional, Dict, Any
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, wait_none
import codecs
from chardet.universaldetector import UniversalDetector
#!/usr/bin/env python3
import unicodedata
import string
import functools

from bs4 import BeautifulSoup


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

def is_latin_charset(text: str, threshold: float = 0.03) -> bool:
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


DEFAULT_CHUNK_SIZE = 1000

class ChineseAITranslator:
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.api_key = "fake-key" #os.environ.get('OPENROUTER_API_KEY')
        if not self.api_key:
            self.log("OPENROUTER_API_KEY not set in environment variables", "error")
        self.api_url = 'http://localhost:1234/v1/chat/completions'  ##"https://openrouter.ai/api/v1/chat/completions"
        self.MODEL_NAME = "yism-34b-0rn-mlx"   #"qwen/qwen-2-7b-instruct:free"
        
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
        return re.sub(r'\n{5,}', '\n\n\n\n', txt)
        
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
    
        
    def remove_html_markup(self, text) -> str:
        # Create a BeautifulSoup object. Use 'html.parser' or 'lxml' if available
        soup = BeautifulSoup(text, 'html.parser')
        
        # Get all text and strip whitespace
        plain_text = soup.get_text(separator=' ', strip=True)
        
        # Replace multiple spaces with a single space and strip again
        plain_text = ' '.join(plain_text.split())
        
        return plain_text

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
        cleaned_txt = cleaned_txt.strip()

        # Refined regex pattern to match variations of "Start of translation" with better constraints
        pattern = r"[\[\(\-\*\s]*[-]*Start of translation[\.\-\)\]\s]*[\.\-]*[\)\]\*\s]*"
        
        # Use re.sub to remove all variations of "Start of translation"
        cleaned_txt = re.sub(pattern, '', cleaned_txt, flags=re.IGNORECASE)
        
        # Strip leading/trailing whitespace to clean up extra spaces after removal
        cleaned_txt = cleaned_txt.strip()
        
        # Refined regex pattern to match variations of "English Translation" with better constraints
        pattern = r"[\[\(\-\*\s]*[-]*English Translation[\.\-\)\]\s]*[\.\-]*[\)\]\*\s]*"
        
        # Use re.sub to remove all variations of "English Translation"
        cleaned_txt = re.sub(pattern, '', cleaned_txt, flags=re.IGNORECASE)
        
        # Strip leading/trailing whitespace to clean up extra spaces after removal
        cleaned_txt = cleaned_txt.strip()
        
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
        cleaned_txt = self.remove_html_markup(cleaned_txt)
        
        # Remove excess spaces
        cleaned_txt = self.normalize_spaces(cleaned_txt)
        
        # Remove empty lines in excess
        cleaned_txt = self.remove_excess_empty_lines(cleaned_txt)
        
        # Strip leading/trailing whitespace to clean up extra spaces after removal
        cleaned_txt = cleaned_txt.strip()
        
        return cleaned_txt

    
    def translate_chunk(self, chunk: str, double_translation=False, is_last_chunk=False) -> str:
        self.log("Translating chunk")
        
        prompt1 = f"""[Task]
        You are a professional translator proficient in Chinese. Your task is to translate the Chinese text you receive and to output the English translation of it. Answer with only the fully translated english text and nothing else. Do not add comments, annotations or messages for the user. The quality of the translation is very important. Be sure to translate every word, without missing anything. Your aim is to translate the chinese text into english conveying the bright prose or poetry of the original text in the translated version and even surpassing it. You must always obey to the TRANSLATION RULES below:


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
- Always use true double quotes (`“…”`) to open and close direct speech parts in english, and not `"`. If one of the opening or closing quotes marks ( like `“` and `”`, or `"` and `"`, or `”` and `„`, or `«` and `»`) is missing, you should add it using the `“` or the `”` character, inferring the right position from the context. For example you must translate `“通行證？”` as `“A pass?”`. 
- The English translation must be fluent and grammatically correct. It must not look like a literal, mechanical translation, but like a high quality brilliant composition that conveys the original meaning using a rich literary level English prose and vocabulary.
- Be sure to keep the translated names and the unique terms used to characterize people and places the same for the whole translation, so that the reader is not confused by sudden changes of names or epithets. 
- Be coherent and use the same writing style for the whole novel. 
- Never summarize or omit any part of the text.  
- Every line of text must be accurately translated in english, without exceptions. Even if the last line of text appears truncated or makes no sense, you must translate it.
- No chinese characters must appear in the output text. You must translate all of them in english.
</TRANSLATION RULES>

[Chinese Text To Translate]
```
{chunk}
```

"""
        ## DO THE FIRST TRANSLATION USING THE API
        first_translation = self.translate_messages(prompt1, is_last_chunk)
        first_translation = self.remove_translation_markers(first_translation)
        

        
        prompt2 = f"""
<Task>
Examine the following text containing a mix of english and chinese characters. Find all chinese words and characters and replace them with an accurate english translation. Use the context around the chinese words to infer the better way to translate them. Output only the perfected english text, with all the chinese words and characters completely translated into english. 
</Task>

<Constraints> 
- Do not leave any chinese character untranslated. Use romanization when a name has no english equivalent. 
- Do not add comments or annotations or anything else not in the original text. Not even translation notes or end of translation markers. Answer with only the fully translated english text and nothing else.
- Avoid using expressions inconsistent with english expression habits
- Never leave Chinese words or characters untranslated. All text in the response must be in english. This is mandatory. Even if a character is unclear, you must use the context to infer the best translation. Names must be translated with their meaning or with the most common english romanization used in the literary genre.
- Always use true double quotes (`“…”`) to open and close direct speech parts in english, and not `"`. If one of the opening or closing quotes marks ( like `“` and `”`, or `"` and `"`, or `”` and `„`, or `«` and `»`) is missing, you should add it using the `“` or the `”` character, inferring the right position from the context. For example you must translate `“通行證？”` as `“A pass?”`.
- Avoid to use the wrong english terms for expressing xianxia/wuxia or daoist cultivation concepts. Do not deviate from the most common and accepted translations of this genre of chinese novels in english.
- Output only the perfected english text, with all the chinese words and characters completely translated into english. 
</Constraints>

<Text>
{first_translation}
</Text>
"""
        if double_translation:
            ## DO THE REFINED SECOND TRANSLATION USING THE API
            final_translation = self.translate_messages(prompt2, is_last_chunk)
            final_translation = self.remove_translation_markers(final_translation)
        else:
            final_translation = first_translation

            
        ## Clean the text and separate chapters
        final_translation = self.separate_chapters(final_translation)
        
        ## RETURN THE FINAL TRANSLATED STRING
        return final_translation






    # Define a custom exception for translation failures
    class TranslationException(Exception):
        pass
    
    
    @retry(
        stop=stop_after_attempt(77),
        wait=wait_exponential(multiplier=1, min=1, max=300),
        retry=retry_if_exception_type((requests.exceptions.RequestException, requests.exceptions.HTTPError, TranslationException))
    )
    def translate_messages(self, messages: str, is_last_chunk=False) -> str:
        self.log("Sending translation request to API")
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        data: Dict[str, Any] = {
            "model": self.MODEL_NAME,
            "messages": [
                {
                    "role": "user",
                    "content": messages,
                }
            ],
            "temperature": 0.1,
            "max_tokens": -1,
            "stream": False,
#            "top_p": 0,
#            "frequency_penalty": 0,
#            "presence_penalty": 0,
#            "repetition_penalty": 1.1,
#            "top_k": 0,
    
        }
    
        try:
            response = requests.post(self.api_url, headers=headers, json=data)
            self.log(f"Request sent to {self.api_url}")
            response.raise_for_status()
            self.log(f"Server returned RESPONSE: \n{response.json()}")
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
            raise
        except requests.exceptions.RequestException as req_err:
            self.log(f"Request exception: {req_err}", "error")
            raise
        except json.JSONDecodeError as json_err:
            self.log(f"JSON decode error: {json_err}", "error")
            raise



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

    def translate_file(self, input_file: str, output_file: str, is_last_chunk=False) -> None:
        self.log(f"Translating file: {input_file}")
        try:
            with open(input_file, 'r', encoding='utf-8') as file:
                chinese_text = file.read()
            
            english_text = self.translate_chunk(chinese_text, is_last_chunk)
        except Exception as e:
            self.log(f"Unexpected error during file translation: {str(e)}", "error")
            return None
        return english_text


    def translate(self, input_string: str, is_last_chunk=False) -> str:
        #self.log(f"Translating text: {input_string}")
        try:
            chinese_text = input_string
            english_text = self.translate_chunk(chinese_text, is_last_chunk)
        except Exception as e:
            self.log(f"Unexpected error during file translation: {str(e)}", "error")
            return None
        return english_text


# Example usage:
if __name__ == "__main__":
    translator = ChineseAITranslator()
    english_text = translator.translate_file("dummy_chinese.txt")
    try:
        with open(output_file, 'w', encoding='utf-8') as file:
            file.write(english_text)
        self.log(f"Translation saved to: {output_file}")
    except IOError as e:
        self.log(f"File operation failed: {str(e)}", "error")


