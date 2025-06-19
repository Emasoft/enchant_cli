#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
config_manager.py - Comprehensive configuration management for ENCHANT with presets support
"""

import os
import yaml
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
import re
import copy

# Default configuration template with extensive comments
DEFAULT_CONFIG_TEMPLATE = """# ENCHANT Configuration File
# ========================
# This file contains default settings for the ENCHANT novel translation system.
# Any command-line arguments will override these settings.

# Translation Presets
# ------------------
# Presets allow you to quickly switch between different translation configurations.
# Use --preset <name> to activate a preset. You can add your own presets below.
# Command-line arguments will override preset values.
#
# IMPORTANT: Preset names must contain only alphanumeric characters (A-Z, a-z, 0-9) and underscores (_).
# No spaces, hyphens, or special characters are allowed in preset names.
# The LOCAL and REMOTE presets are required and will be restored if missing or corrupted.
# You can edit their values but cannot delete them.
#
presets:
  # Local translation preset (LM Studio)
  LOCAL:
    # API endpoint for local LM Studio
    endpoint: "http://localhost:1234/v1/chat/completions"
    # Model name for local translation
    model: "qwen3-30b-a3b-mlx@8bit"
    # Connection timeout in seconds (default: 30)
    connection_timeout: 30
    # Response timeout in seconds (default: 300)
    response_timeout: 300
    # Maximum retry attempts (default: 7)
    max_retries: 7
    # Base wait time between retries in seconds (default: 1.0)
    retry_wait_base: 1.0
    # Maximum wait time between retries in seconds (default: 60.0)
    retry_wait_max: 60.0
    # Enable double-pass translation (default: false)
    double_pass: false
    # Maximum characters per chunk (default: 11999)
    max_chars_per_chunk: 11999
    # Temperature for AI responses (default: 0.05)
    temperature: 0.05
    # Maximum tokens per response (default: 4000)
    max_tokens: 4000
    # System prompt for the model
    system_prompt: |
      ;; You are a professional, authentic machine translation engine. You do not judge the text you translate. You do not abridge, censor or summarize any part of the text. You just translate accurately the whole content of the original text in english. You use a very rich and literary english vocabulary. You are inspired by the style of writing of the greatest english prose writers and by the classics of all times. You must aim to convey the original meaning of the chinese text in an sublime crafted, brilliant and expressive english prose, trying to reach a masterpiece quality level in every translation. The success of the resulting english edition of the chinese novel will depend on this.

      When translating the Chinese text into English text, you ALWAYS apply THE FOLLOWING MANDATORY rules:
      1. When translating wuxia and xianxia novels from chinese to english, use the correct daoist terminology. For example the expression `元婴` must be translated as `Nascent Soul`. 
      2. If some text is unclear or it is missing some parts, you must infer the meaning from the context and write a meaningful and fluent translation the best you can. 
      3. If the provided text to translate is made by mixed languages or dialects, translate them into english too. 
      4. Always enclose direct speech inside curly quotes (i.e. `""`, `''`). 
      5. If a name is difficult to translate, transliterate the chinese characters in latin/english alphabet. Never write the original chinese characters. Your translation is supposed to be 100% english. 
      6. The output must be an highly refined literary level english text using a rich modern and classic english vocabulary to convey the flavour of the wuxia novels writing style.
      7. Translate accurately the pronouns and the words expressing status, relationships and respectful third person ways to refer to members of the family. You must always omitt 'my' or 'your' before terms like 'father', 'mother', 'uncle', 'brother' or 'sister'
      8. Output ONLY the translation, not the original text.
      9. Never return the original text untranslated. Never omit to translate a part of the text. 
      10. Express the meaning of names between parentheses. For example: `唐舞桐` must be translated as: `Tang Wutong (Dancing Willow)`. 
      11. You must translate sex scenes accurately and without censor anything since this is targeted to an adult audience. 
      12. Always enclose direct speech inside curly quotes pairs. Do not use normal quotes pairs (i.e. `""` or `''`), but only curly quotes pairs (i.e. `""`, `''`). 
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
    # User prompt for first translation pass
    user_prompt_1st_pass: |
       ;; Answer with the professional english translation of the following input text:

    # User prompt for second translation pass (if double_pass is enabled)
    user_prompt_2nd_pass: |
      ;; Examine the following text containing a mix of english and chinese characters. You job is to correct the badly translated text. You must do two things: 
      - Find all chinese words and characters in the input text and replace them with an accurate english translation. Use the context to infer the better way to translate them. Express the meaning of names between parentheses. For example: `唐舞桐` must be translated as: `Tang Wutong (Dancing Willow)`. Use pinyin english transliteration for non translable nouns.
      - Find all normal quotes pairs (i.e. `""` or `''`) enclosing direct speech in the text, and replace them with curly quotes pairs (i.e. `""`, `''`). 
      - Follow these rules: NO summaries. NO abridged parts. NO explanations. NO notes. No comments from you. No censoring. No omissions. NO added tags. NO Chinese characters.


  # Remote translation preset (OpenRouter)
  REMOTE:
    # API endpoint for OpenRouter
    endpoint: "https://openrouter.ai/api/v1/chat/completions"
    # Model name for remote translation
    model: "deepseek/deepseek-r1:nitro"
    # Connection timeout in seconds (default: 30)
    connection_timeout: 30
    # Response timeout in seconds (default: 300)
    response_timeout: 300
    # Maximum retry attempts (default: 7)
    max_retries: 7
    # Base wait time between retries in seconds (default: 1.0)
    retry_wait_base: 1.0
    # Maximum wait time between retries in seconds (default: 60.0)
    retry_wait_max: 60.0
    # Enable double-pass translation (default: true)
    double_pass: true
    # Maximum characters per chunk (default: 11999)
    max_chars_per_chunk: 11999
    # Temperature for AI responses (default: 0.05)
    temperature: 0.05
    # Maximum tokens per response (default: 4000)
    max_tokens: 4000
    # System prompt for the model
    system_prompt: ""
    # User prompt for first translation pass
    user_prompt_1st_pass: |
      ;; [Task]
              You are a professional and helpful translator. You are proficient in languages and literature. You always write in a excellent and refined english prose, following a polished english writing style. Your task is to translate the Chinese text you receive and to output the English translation of it. Answer with only the fully translated english text and nothing else. Do not add comments, annotations or messages for the user. The quality of the translation is very important. Be sure to translate every word, without missing anything. Your aim is to translate the chinese text into english conveying the bright prose or poetry of the original text in the translated version and even surpassing it. Always use curly quotes like `""` when translating direct speech. Never abridge the translation. You must always return the whole unabridged translation. You must always obey to the TRANSLATION RULES below:

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
      - Convert all normal quotes pairs (i.e. "" or '') to curly quotes pairs (i.e. "", ''). Always use double curly quotes (`"…"`) to open and close direct speech parts in english, and not the normal double quotes (`"…"`). If one of the opening or closing quotes marks ( like `"` and `"`, or `"` and `"`, or `"` and `„`, or `«` and `»`) is missing, you should add it using the `"` or the `"` character, inferring the right position from the context. For example you must translate `"通行證？"` as `"A pass?"`. 
      - The English translation must be fluent and grammatically correct. It must not look like a literal, mechanical translation, but like a high quality brilliant composition that conveys the original meaning using a rich literary level English prose and vocabulary.
      - Be sure to keep the translated names and the unique terms used to characterize people and places the same for the whole translation, so that the reader is not confused by sudden changes of names or epithets. 
      - Be coherent and use the same writing style for the whole novel. 
      - Never summarize or omit any part of the text. Never abridge the translation.
      - Every line of text must be accurately translated in english, without exceptions. Even if the last line of text appears truncated or makes no sense, you must translate it.
      - No chinese characters must appear in the output text. You must translate all of them in english.


    # User prompt for second translation pass
    user_prompt_2nd_pass: |
      ;; [TASK]
      You are an helpful and professional translator. You are proficient in languages and literature. You always write in a excellent and refined english prose, following a polished english writing style. Examine the following text containing a mix of english and chinese characters. Find all chinese words and characters and replace them with an accurate english translation. Use the context around the chinese words to infer the better way to translate them. Then convert all normal quotes pairs (i.e. `""` or `''`) to curly quotes pairs (i.e. `""`, `''`). Output only the perfected english text, making sure that all the chinese words and characters are completely translated into english. Do not abridge the text. You must always obey to the EDITING RULES below:

      [EDITING RULES]
      - Do not leave any chinese character untranslated. Use romanization when a name has no english equivalent. 
      - Do not add comments or annotations or anything else not in the original text. Not even translation notes or end of translation markers. Answer with only the fully translated english text and nothing else.
      - Avoid using expressions inconsistent with english expression habits
      - Never leave Chinese words or characters untranslated. All text in the response must be in english. This is mandatory. Even if a character is unclear, you must use the context to infer the best translation. Names must be translated with their meaning or with the most common english romanization used in the literary genre.
      - Convert all normal quotes pairs (i.e. "" or '') to curly quotes pairs (i.e. "", ''). Always use double curly quotes (`"…"`) to open and close direct speech parts in english, and not the normal double quotes (`"…"`). If one of the opening or closing quotes marks ( like `"` and `"`, or `"` and `"`, or `"` and `„`, or `«` and `»`) is missing, you should add it using the `"` or the `"` character, inferring the right position from the context. For example you must translate `"通行證？"` as `"A pass?"`.
      - Avoid to use the wrong english terms for expressing xianxia/wuxia or daoist cultivation concepts. Do not deviate from the most common and accepted translations of this genre of chinese novels in english.
      - Output only the perfected english text, the whole unabridged text, with all the chinese words and characters completely translated into english. 


  # Add your custom presets here
  # Example:
  # CUSTOM_FAST:
  #   endpoint: "http://localhost:1234/v1/chat/completions"
  #   model: "custom-model"
  #   connection_timeout: 15
  #   response_timeout: 120
  #   max_retries: 3
  #   retry_wait_base: 0.5
  #   retry_wait_max: 30.0
  #   double_pass: false
  #   max_chars_per_chunk: 8000
  #   temperature: 0.1
  #   max_tokens: 2000
  #   system_prompt: "Your custom system prompt"
  #   user_prompt_1st_pass: "Your custom first pass prompt"
  #   user_prompt_2nd_pass: "Your custom second pass prompt"

# Translation Settings
# --------------------
translation:
  # AI service to use: 'local' or 'remote'
  # - local: Uses LM Studio running on localhost
  # - remote: Uses OpenRouter API (requires API key)
  service: local
  
  # Active preset (can be overridden with --preset)
  active_preset: LOCAL
  
  # Local API settings (LM Studio)
  local:
    # API endpoint for local LM Studio (default: http://localhost:1234/v1/chat/completions)
    endpoint: "http://localhost:1234/v1/chat/completions"
    # Model name for local translation (default: local-model)
    model: "local-model"
    # Connection timeout in seconds (default: 30)
    connection_timeout: 30
    # Response timeout in seconds (default: 300)
    timeout: 300
  
  # Remote API settings (OpenRouter)
  remote:
    # API endpoint for OpenRouter (default: https://openrouter.ai/api/v1/chat/completions)
    endpoint: "https://openrouter.ai/api/v1/chat/completions"
    # Model to use for translation (default: deepseek/deepseek-chat)
    model: "deepseek/deepseek-chat"
    # API key (can also be set via OPENROUTER_API_KEY environment variable)
    api_key: null
    # Connection timeout in seconds (default: 30)
    connection_timeout: 30
    # Response timeout in seconds (default: 300)
    timeout: 300
  
  # Translation parameters
  # Temperature for AI responses (0.0 = deterministic, 1.0 = creative) (default: 0.3)
  temperature: 0.3
  # Maximum tokens per response (default: 4000)
  max_tokens: 4000
  # Number of retry attempts for failed translations (default: 7)
  max_retries: 7
  # Base wait time between retries (exponential backoff) (default: 1.0)
  retry_wait_base: 1.0
  # Maximum wait time between retries (default: 60.0)
  retry_wait_max: 60.0

# Text Processing Settings
# -----------------------
text_processing:
  # Text is automatically split into paragraphs at double newlines
  
  # Maximum characters per translation chunk (default: 11999)
  max_chars_per_chunk: 11999
  
  # File encoding (auto-detected if not specified)
  # Common values: utf-8, gb2312, gb18030, big5
  # (default: utf-8)
  default_encoding: utf-8

# Novel Renaming Settings
# ----------------------
novel_renaming:
  # Enable automatic novel renaming based on AI-extracted metadata (default: false)
  enabled: false
  
  # OpenAI API settings for metadata extraction
  openai:
    # API key for OpenRouter (can also be set via OPENROUTER_API_KEY environment variable)
    api_key: null
    # Model to use for metadata extraction (default: gpt-4o-mini)
    model: "gpt-4o-mini"
    # Temperature for metadata extraction (0.0 = consistent) (default: 0.0)
    temperature: 0.0
  
  # Amount of text to read for metadata extraction (in KB) (default: 35)
  kb_to_read: 35
  
  # Minimum file size to consider for renaming (in KB) (default: 100)
  min_file_size_kb: 100

# EPUB Generation Settings
# -----------------------
epub:
  # Enable EPUB generation after translation (default: false)
  enabled: false
  
  # Detect and build table of contents from chapter headings (default: true)
  build_toc: true
  
  # Language code for EPUB metadata (default: zh)
  language: "zh"
  
  # Include cover image if available (default: true)
  include_cover: true
  
  # Validate chapter sequence and report issues (default: true)
  validate_chapters: true
  
  # Strict mode - abort on validation issues (default: false)
  strict_mode: false

# Batch Processing Settings
# ------------------------
batch:
  # Maximum number of worker threads for parallel processing
  # Set to null to use CPU count (default: null)
  max_workers: null
  
  # Process subdirectories recursively (default: true)
  recursive: true
  
  # Pattern for finding text files (glob pattern) (default: *.txt)
  file_pattern: "*.txt"
  
  # Continue processing even if individual files fail (default: true)
  continue_on_error: true
  
  # Save progress for resume capability (default: true)
  save_progress: true
  
  # Progress file names
  progress_file: "translation_batch_progress.yml"
  archive_file: "translations_chronology.yml"

# iCloud Sync Settings
# -------------------
icloud:
  # Enable iCloud sync (auto-detected by default)
  # Set to true/false to force enable/disable (default: null)
  enabled: null
  
  # Wait timeout for file sync (seconds) (default: 300)
  sync_timeout: 300
  
  # Check interval for sync status (seconds) (default: 2)
  sync_check_interval: 2

# Model Pricing Settings
# ---------------------
pricing:
  # Enable cost calculation and tracking (default: true)
  enabled: true
  
  # URL to fetch model pricing (LiteLLM pricing database)
  pricing_url: "https://raw.githubusercontent.com/BerriAI/litellm/main/model_prices_and_context_window.json"
  
  # Fallback URLs if primary fails
  fallback_urls:
    - "https://cdn.jsdelivr.net/gh/BerriAI/litellm@main/model_prices_and_context_window.json"
    - "https://raw.fastgit.org/BerriAI/litellm/main/model_prices_and_context_window.json"

# Logging Settings
# ---------------
logging:
  # Log level: DEBUG, INFO, WARNING, ERROR, CRITICAL (default: INFO)
  level: INFO
  
  # Log to file (default: true)
  file_enabled: true
  file_path: "enchant_book_manager.log"
  
  # Log format
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Advanced Settings
# ----------------
advanced:
  # Clean advertisements from text (default: true)
  clean_adverts: true
  
  # Character limit for content preview (default: 1500)
  content_preview_limit: 1500
  
  # Supported file encodings for detection
  supported_encodings:
    - utf-8
    - gb18030
    - gb2312
    - big5
    - big5hkscs
    - shift_jis
    - euc_jp
    - euc_kr
    - iso-2022-jp
    - iso-2022-kr
    - utf-16
    - utf-16-le
    - utf-16-be
"""

class ConfigManager:
    """Manages configuration for ENCHANT system with presets support."""
    
    def __init__(self, config_path: Optional[Path] = None, logger: Optional[logging.Logger] = None):
        """
        Initialize configuration manager.
        
        Args:
            config_path: Path to configuration file (default: enchant_config.yml)
            logger: Logger instance
        """
        self.logger = logger or logging.getLogger(__name__)
        self.config_path = config_path or Path("enchant_config.yml")
        self._config_lines = []  # Store file lines for error reporting
        self.config = self._load_config()
        self.active_preset = None
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file or create default."""
        if not self.config_path.exists():
            self.logger.info(f"Configuration file not found. Creating default at: {self.config_path}")
            self._create_default_config()
        
        try:
            # First, try to load and parse the YAML
            with open(self.config_path, 'r', encoding='utf-8') as f:
                file_content = f.read()
                config = yaml.safe_load(file_content)
                
            if config is None:
                self.logger.warning("Configuration file is empty. Using defaults.")
                return self._get_default_config()
            
            # Store file lines for error reporting
            self._config_lines = file_content.split('\n')
            
            # Validate configuration - get FIRST error only
            first_error = self._validate_config_first_error(config)
            if first_error:
                # Check if it's a restorable error (missing LOCAL or REMOTE preset)
                if first_error.get('can_restore'):
                    if first_error['type'] == 'missing_required_preset':
                        preset_name = first_error['preset']
                        response = input(f"\nRequired preset '{preset_name}' is missing. Restore default values? (y/n): ")
                        if response.lower() == 'y':
                            defaults = self._get_default_config()
                            default_presets = defaults.get('presets', {})
                            if 'presets' not in config:
                                config['presets'] = {}
                            config['presets'][preset_name] = default_presets.get(preset_name, {})
                            self.logger.info(f"Restored default '{preset_name}' preset")
                            # Re-validate after restoration
                            first_error = self._validate_config_first_error(config)
                
                # If there's still an error, report and exit
                if first_error:
                    self._report_single_error(first_error)
                    import sys
                    sys.exit(1)
            
            # Merge with defaults to ensure all keys exist
            return self._merge_with_defaults(config)
            
        except yaml.YAMLError as e:
            self._report_yaml_error(e)
            import sys
            sys.exit(1)
        except Exception as e:
            self.logger.error(f"Error loading configuration: {e}")
            raise
    
    def _create_default_config(self):
        """Create default configuration file."""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                f.write(DEFAULT_CONFIG_TEMPLATE)
            self.logger.info("Default configuration file created successfully.")
        except Exception as e:
            self.logger.error(f"Failed to create configuration file: {e}")
            raise
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration as dictionary."""
        return yaml.safe_load(DEFAULT_CONFIG_TEMPLATE)
    
    def _validate_config_first_error(self, config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Validate configuration and return only the FIRST error found."""
        # Check for unknown keys at top level
        defaults = self._get_default_config()
        valid_top_keys = set(defaults.keys())
        
        for key in config.keys():
            if key not in valid_top_keys:
                line_num = self._find_line_number(key)
                return {
                    'type': 'unknown_key',
                    'key': key,
                    'line': line_num,
                    'message': f"Unknown or malformed key '{key}' found. Ignoring.",
                    'context': 'top-level'
                }
        
        # Check presets for errors FIRST (before checking other sections)
        if 'presets' in config:
            preset_error = self._validate_presets_first_error(config)
            if preset_error:
                return preset_error
        
        # Check required top-level sections
        required_sections = {
            'translation': 'Translation settings (API endpoints, models, etc.)',
            'text_processing': 'Text processing settings (split methods, character limits)',
            'novel_renaming': 'Novel metadata extraction settings',
            'epub': 'EPUB generation settings',
            'batch': 'Batch processing settings',
            'icloud': 'iCloud synchronization settings',
            'pricing': 'API cost tracking settings',
            'logging': 'Logging configuration'
        }
        
        for section, description in required_sections.items():
            if section not in config:
                # Find where to add it
                last_line = len(self._config_lines)
                for i, line in enumerate(self._config_lines):
                    if line.strip() and not line.strip().startswith('#'):
                        last_line = i + 1
                
                return {
                    'type': 'missing_section',
                    'section': section,
                    'description': description,
                    'line': last_line,
                    'message': f"Expected section '{section}' not found. Please add the {section} section after line {last_line}"
                }
        
        # Validate specific values in sections
        if 'translation' in config:
            if 'service' in config['translation']:
                if config['translation']['service'] not in ['local', 'remote']:
                    line_num = self._find_line_number('translation.service')
                    return {
                        'type': 'invalid_value',
                        'path': 'translation.service',
                        'value': config['translation']['service'],
                        'valid_values': ['local', 'remote'],
                        'line': line_num,
                        'message': f"Invalid value '{config['translation']['service']}' for translation.service. Must be 'local' or 'remote'"
                    }
        
        # Text is automatically split into paragraphs at double newlines
        
        return None
    
    def _validate_presets_first_error(self, config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Validate presets and return only the FIRST error found."""
        
        presets = config.get('presets', {})
        if not presets:
            return None
        
        # First check for unknown keys in presets section
        defaults = self._get_default_config()
        default_presets = defaults.get('presets', {})
        
        # Get all valid preset keys from default presets
        valid_preset_keys = set()
        for preset in default_presets.values():
            if isinstance(preset, dict):
                valid_preset_keys.update(preset.keys())
        
        # Validate preset names first
        valid_name_pattern = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')
        for preset_name in presets.keys():
            if not valid_name_pattern.match(preset_name):
                line_num = self._find_line_number(f'presets.{preset_name}')
                error_msg = "Preset names must start with a letter or underscore, followed by letters, numbers, or underscores"
                if preset_name[0].isdigit():
                    error_msg = "invalid preset name. Names must not begin with a number!"
                elif '-' in preset_name:
                    error_msg = "invalid preset name. Names cannot contain hyphens (-). Use underscores (_) instead"
                elif ' ' in preset_name:
                    error_msg = "invalid preset name. Names cannot contain spaces. Use underscores (_) instead"
                
                return {
                    'type': 'invalid_preset_name',
                    'preset': preset_name,
                    'message': error_msg,
                    'line': line_num
                }
        
        # Check for required presets (LOCAL and REMOTE)
        for required_preset in ['LOCAL', 'REMOTE']:
            if required_preset not in presets:
                return {
                    'type': 'missing_required_preset',
                    'preset': required_preset,
                    'message': f"Required preset '{required_preset}' is missing",
                    'can_restore': True
                }
        
        # Now validate each preset's contents
        for preset_name, preset_data in presets.items():
            if not isinstance(preset_data, dict):
                line_num = self._find_line_number(f'presets.{preset_name}')
                return {
                    'type': 'invalid_preset_type',
                    'preset': preset_name,
                    'message': f"Preset '{preset_name}' must be a dictionary/mapping",
                    'line': line_num
                }
            
            # Check for unknown keys in this preset
            for key in preset_data.keys():
                if key not in valid_preset_keys:
                    line_num = self._find_line_number(f'presets.{preset_name}.{key}')
                    return {
                        'type': 'unknown_key',
                        'key': key,
                        'preset': preset_name,
                        'line': line_num,
                        'message': "unknown or malformed key found. Ignoring.",
                        'context': f'preset {preset_name}'
                    }
            
            # Check for missing required keys
            required_keys = ['endpoint', 'model', 'connection_timeout', 'response_timeout', 
                           'max_retries', 'retry_wait_base', 'retry_wait_max', 'double_pass',
                           'max_chars_per_chunk', 'temperature', 'max_tokens', 'system_prompt',
                           'user_prompt_1st_pass', 'user_prompt_2nd_pass']
            
            # For custom presets, only check basic required keys
            if preset_name not in ['LOCAL', 'REMOTE']:
                required_keys = ['endpoint', 'model']
            
            for key in required_keys:
                if key not in preset_data:
                    # Find the line where this key should be added
                    preset_line = self._find_line_number(f'presets.{preset_name}')
                    # Look for the last key in this preset
                    last_key_line = preset_line
                    for existing_key in preset_data.keys():
                        key_line = self._find_line_number(f'presets.{preset_name}.{existing_key}')
                        if key_line and key_line > last_key_line:
                            last_key_line = key_line
                    
                    return {
                        'type': 'missing_key',
                        'preset': preset_name,
                        'key': key,
                        'line': last_key_line,
                        'message': f"expected key '{key}' not found. Please add the {key} key after line {last_key_line}"
                    }
            
            # Validate values for each key
            value_error = self._validate_preset_values_first_error(preset_name, preset_data)
            if value_error:
                return value_error
        
        return None
    
    def _validate_preset_values_first_error(self, preset_name: str, preset_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Validate preset values and return only the FIRST error found."""
        # Check each value in order
        for key, value in preset_data.items():
            line_num = self._find_line_number(f'presets.{preset_name}.{key}')
            
            # Validate based on key type
            if key in ['connection_timeout', 'response_timeout', 'max_retries', 'max_chars_per_chunk', 'max_tokens']:
                try:
                    int_val = int(value)
                    if int_val <= 0:
                        return {
                            'type': 'invalid_value',
                            'preset': preset_name,
                            'key': key,
                            'value': value,
                            'line': line_num,
                            'message': f"invalid value for {key}. {key} value must be a positive integer"
                        }
                except (ValueError, TypeError):
                    return {
                        'type': 'invalid_type',
                        'preset': preset_name,
                        'key': key,
                        'value': value,
                        'line': line_num,
                        'message': f"invalid value for {key}. {key} must be an integer"
                    }
            
            elif key in ['retry_wait_base', 'retry_wait_max', 'temperature']:
                try:
                    float_val = float(value)
                    if float_val < 0:
                        return {
                            'type': 'invalid_value',
                            'preset': preset_name,
                            'key': key,
                            'value': value,
                            'line': line_num,
                            'message': f"invalid value for {key}. {key} must be non-negative"
                        }
                    if key == 'temperature' and float_val > 2.0:
                        return {
                            'type': 'invalid_value',
                            'preset': preset_name,
                            'key': key,
                            'value': value,
                            'line': line_num,
                            'message': "invalid value for temperature. Temperature must be between 0.0 and 2.0"
                        }
                except (ValueError, TypeError):
                    return {
                        'type': 'invalid_type',
                        'preset': preset_name,
                        'key': key,
                        'value': value,
                        'line': line_num,
                        'message': f"invalid value for {key}. {key} must be a number"
                    }
            
            elif key == 'double_pass':
                if not isinstance(value, bool):
                    return {
                        'type': 'invalid_type',
                        'preset': preset_name,
                        'key': key,
                        'value': value,
                        'line': line_num,
                        'message': "invalid value for double_pass. double_pass value can only be true or false"
                    }
            
            elif key == 'endpoint':
                if not isinstance(value, str):
                    return {
                        'type': 'invalid_type',
                        'preset': preset_name,
                        'key': key,
                        'value': value,
                        'line': line_num,
                        'message': "invalid value for endpoint. Endpoint must be a string URL"
                    }
                elif not (value.startswith('http://') or value.startswith('https://')):
                    return {
                        'type': 'invalid_value',
                        'preset': preset_name,
                        'key': key,
                        'value': value,
                        'line': line_num,
                        'message': "api endpoint url not a valid openai compatible endpoint format!"
                    }
            
            elif key == 'model':
                if not isinstance(value, str) or not value.strip():
                    return {
                        'type': 'invalid_value',
                        'preset': preset_name,
                        'key': key,
                        'value': value,
                        'line': line_num,
                        'message': "invalid value for model. Model must be a non-empty string"
                    }
        
        return None
    
    def _report_single_error(self, error: Dict[str, Any]) -> None:
        """Report a single validation error."""
        line = error.get('line')
        if line is None:
            line = 'unknown'
        
        if error['type'] == 'unknown_key':
            print(f"\nline {line}: unknown or malformed key found. Ignoring.")
            if line != 'unknown' and hasattr(self, '_config_lines'):
                line_idx = int(line) - 1
                if 0 <= line_idx < len(self._config_lines):
                    print(f"  {self._config_lines[line_idx].strip()}")
        
        elif error['type'] == 'missing_key' or error['type'] == 'missing_section':
            print(f"\nline {line}: {error['message']}")
        
        elif error['type'] == 'invalid_preset_name':
            print(f"\nline {line}: {error['message']}")
        
        elif error['type'] in ['invalid_value', 'invalid_type']:
            print(f"\nline {line}: {error['message']}")
        
        elif error['type'] == 'missing_required_preset':
            # This is handled separately with user prompt
            pass
        
        else:
            # Generic error reporting
            print(f"\nline {line}: {error['message']}")
    
    def _find_line_number(self, key_path: str) -> Optional[int]:
        """Find the line number of a configuration key in the YAML file."""
        if not hasattr(self, '_config_lines'):
            return None
            
        # Convert dot notation to YAML path
        keys = key_path.split('.')
        
        # Search for the key in the file
        indent_level = 0
        current_section = None
        
        for i, line in enumerate(self._config_lines, 1):
            stripped = line.strip()
            if not stripped or stripped.startswith('#'):
                continue
                
            # Calculate indent level
            current_indent = len(line) - len(line.lstrip())
            
            # Check if this line matches our search path
            for j, key in enumerate(keys):
                expected_indent = j * 2  # YAML typically uses 2-space indent
                if current_indent == expected_indent and stripped.startswith(f"{key}:"):
                    if j == len(keys) - 1:
                        return i
                    current_section = key
                    break
        
        return None
    
    
    def _report_yaml_error(self, error: yaml.YAMLError) -> None:
        """Report YAML parsing errors with line information."""
        print("\n" + "="*80)
        print("YAML PARSING ERROR")
        print("="*80)
        print(f"Failed to parse {self.config_path}")
        print()
        
        if hasattr(error, 'problem_mark'):
            mark = error.problem_mark
            print(f"Error at line {mark.line + 1}, column {mark.column + 1}:")
            
            # Show the problematic line
            with open(self.config_path, 'r') as f:
                lines = f.readlines()
                if mark.line < len(lines):
                    print(f"  {mark.line + 1}: {lines[mark.line].rstrip()}")
                    print(f"  {' ' * (len(str(mark.line + 1)) + 2)}{' ' * mark.column}^")
        
        print()
        print(f"Problem: {error.problem if hasattr(error, 'problem') else str(error)}")
        
        if hasattr(error, 'note'):
            print(f"Note: {error.note}")
        
        print()
        print("Common YAML issues:")
        print("  - Indentation must be consistent (use spaces, not tabs)")
        print("  - String values with special characters should be quoted")
        print("  - Lists must start with '- ' (dash and space)")
        print("  - Colons in values must be quoted (e.g., 'http://example.com')")
        print()
        print("Fix the syntax error or delete the config file to regenerate defaults.")
        print("="*80)
    
    def _merge_with_defaults(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Merge user config with defaults to ensure all keys exist."""
        defaults = self._get_default_config()
        return self._deep_merge(defaults, config)
    
    def _deep_merge(self, base: Dict, update: Dict) -> Dict:
        """Deep merge two dictionaries."""
        result = base.copy()
        
        for key, value in update.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation.
        
        Args:
            key_path: Dot-separated path (e.g., 'translation.local.endpoint')
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        keys = key_path.split('.')
        value = self.config
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        
        return value
    
    def apply_preset(self, preset_name: str) -> bool:
        """
        Apply a preset configuration.
        
        Args:
            preset_name: Name of the preset to apply
            
        Returns:
            True if preset was applied successfully
        """
        
        # Validate preset name format
        valid_name_pattern = re.compile(r'^[A-Za-z0-9_]+$')
        if not valid_name_pattern.match(preset_name):
            self.logger.error(f"Invalid preset name '{preset_name}'. Preset names must contain only alphanumeric characters and underscores.")
            return False
        
        presets = self.config.get('presets', {})
        if preset_name not in presets:
            available = list(presets.keys())
            self.logger.error(f"Preset '{preset_name}' not found. Available presets: {', '.join(available)}")
            # Exit with error for non-existent preset
            import sys
            sys.exit(1)
        
        preset = presets[preset_name]
        self.active_preset = preset_name
        
        # Apply preset values to config
        # Note: We don't modify the original config, but track the active preset
        # The get_preset_value method will handle retrieving values
        
        self.logger.info(f"Applied preset: {preset_name}")
        return True
    
    def get_preset_value(self, key: str, default: Any = None) -> Any:
        """
        Get value from active preset or default.
        
        Args:
            key: Key to retrieve from preset
            default: Default value if not found
            
        Returns:
            Value from preset or default
        """
        if self.active_preset and 'presets' in self.config:
            preset = self.config['presets'].get(self.active_preset, {})
            if key in preset:
                return preset[key]
        return default
    
    def get_available_presets(self) -> List[str]:
        """Get list of available presets."""
        return list(self.config.get('presets', {}).keys())
    
    def update_with_args(self, args) -> Dict[str, Any]:
        """
        Update configuration with command-line arguments.
        Command-line args take precedence over config file and presets.
        
        Args:
            args: Parsed command-line arguments
            
        Returns:
            Updated configuration dictionary
        """
        config = copy.deepcopy(self.config)
        
        # Apply preset if specified
        if hasattr(args, 'preset') and args.preset:
            self.apply_preset(args.preset)
        
        # Handle double-pass arguments
        double_pass = None
        if hasattr(args, 'double_pass') and args.double_pass:
            double_pass = True
        elif hasattr(args, 'no_double_pass') and args.no_double_pass:
            double_pass = False
            
        # Map command-line arguments to config keys
        arg_mapping = {
            'encoding': 'text_processing.default_encoding',
            'max_chars': 'text_processing.max_chars_per_chunk',
            'remote': 'translation.service',  # True -> 'remote', False -> 'local'
            'epub': 'epub.enabled',
            'batch': 'batch.enabled',
            'max_workers': 'batch.max_workers',
            'connection_timeout': 'translation.connection_timeout',
            'response_timeout': 'translation.response_timeout',
            'max_retries': 'translation.max_retries',
            'retry_wait_base': 'translation.retry_wait_base',
            'retry_wait_max': 'translation.retry_wait_max',
            'temperature': 'translation.temperature',
            'max_tokens': 'translation.max_tokens',
            'model': 'translation.model',
            'endpoint': 'translation.endpoint',
        }
        
        # First apply preset values if active
        if self.active_preset:
            preset = self.config.get('presets', {}).get(self.active_preset, {})
            for key, value in preset.items():
                if key in ['connection_timeout', 'response_timeout', 'max_retries', 
                          'retry_wait_base', 'retry_wait_max', 'temperature', 
                          'max_tokens', 'double_pass', 'model', 'endpoint',
                          'max_chars_per_chunk']:
                    # Map preset keys to config paths
                    if key == 'max_chars_per_chunk':
                        self._set_config_value(config, 'text_processing.max_chars_per_chunk', value)
                    elif key in ['model', 'endpoint', 'connection_timeout', 'response_timeout']:
                        service = 'remote' if self.active_preset == 'REMOTE' else 'local'
                        if key == 'response_timeout':
                            self._set_config_value(config, f'translation.{service}.timeout', value)
                        elif key == 'connection_timeout':
                            self._set_config_value(config, f'translation.{service}.connection_timeout', value)
                        else:
                            self._set_config_value(config, f'translation.{service}.{key}', value)
                    else:
                        self._set_config_value(config, f'translation.{key}', value)
        
        # Then override with command-line arguments
        for arg_name, config_path in arg_mapping.items():
            if hasattr(args, arg_name):
                value = getattr(args, arg_name)
                if value is not None:
                    # Special handling for 'remote' flag
                    if arg_name == 'remote':
                        value = 'remote' if value else 'local'
                    
                    # Set value in config
                    self._set_config_value(config, config_path, value)
        
        # Handle double_pass separately after other args
        if double_pass is not None:
            self._set_config_value(config, 'translation.double_pass', double_pass)
        
        return config
    
    def _set_config_value(self, config: Dict, path: str, value: Any):
        """Set a value in the config dictionary using dot notation."""
        keys = path.split('.')
        target = config
        for key in keys[:-1]:
            if key not in target:
                target[key] = {}
            target = target[key]
        target[keys[-1]] = value
    
    def get_api_key(self, service: str) -> Optional[str]:
        """
        Get API key for a service from config or environment.
        
        Args:
            service: Service name ('openrouter', 'openai')
            
        Returns:
            API key or None
        """
        # Check environment variables first
        env_vars = {
            'openrouter': 'OPENROUTER_API_KEY',
            'openai': 'OPENROUTER_API_KEY'
        }
        
        env_key = os.getenv(env_vars.get(service, ''))
        if env_key:
            return env_key
        
        # Then check config
        if service == 'openrouter':
            return self.get('translation.remote.api_key')
        elif service == 'openai':
            return self.get('novel_renaming.openai.api_key')
        
        return None


# Global config instance
_global_config = None

def get_config(config_path: Optional[Path] = None) -> ConfigManager:
    """Get or create global configuration instance."""
    global _global_config
    if _global_config is None:
        _global_config = ConfigManager(config_path)
    return _global_config

def load_config(config_path: Optional[Path] = None) -> Dict[str, Any]:
    """Load configuration and return as dictionary."""
    return get_config(config_path).config