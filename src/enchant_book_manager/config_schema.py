#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
# - Created new module to hold configuration schema and default template
# - Extracted DEFAULT_CONFIG_TEMPLATE from config_manager.py
# - This module defines the configuration structure and defaults
#

"""
config_schema.py - Configuration schema and default template for ENCHANT
"""

from .config_prompts import (
    LOCAL_SYSTEM_PROMPT,
    LOCAL_USER_PROMPT_1ST,
    LOCAL_USER_PROMPT_2ND,
    REMOTE_USER_PROMPT_1ST,
    REMOTE_USER_PROMPT_2ND,
)


def indent_prompt(prompt: str, indent_level: int = 6) -> str:
    """
    Indent a multi-line prompt for proper YAML formatting.

    Args:
        prompt: The prompt string to indent
        indent_level: Number of spaces to indent (default: 6)

    Returns:
        Indented prompt string
    """
    indent = " " * indent_level
    lines = prompt.split("\n")
    return "\n".join(indent + line if line else "" for line in lines)


# Pre-format the prompts with proper indentation
_LOCAL_SYSTEM_PROMPT_INDENTED = indent_prompt(LOCAL_SYSTEM_PROMPT)
_LOCAL_USER_PROMPT_1ST_INDENTED = indent_prompt(LOCAL_USER_PROMPT_1ST)
_LOCAL_USER_PROMPT_2ND_INDENTED = indent_prompt(LOCAL_USER_PROMPT_2ND)
_REMOTE_USER_PROMPT_1ST_INDENTED = indent_prompt(REMOTE_USER_PROMPT_1ST)
_REMOTE_USER_PROMPT_2ND_INDENTED = indent_prompt(REMOTE_USER_PROMPT_2ND)

# Default configuration template with extensive comments
DEFAULT_CONFIG_TEMPLATE = f"""# ENCHANT Configuration File
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
{_LOCAL_SYSTEM_PROMPT_INDENTED}
    # User prompt for first translation pass
    user_prompt_1st_pass: |
{_LOCAL_USER_PROMPT_1ST_INDENTED}

    # User prompt for second translation pass (if double_pass is enabled)
    user_prompt_2nd_pass: |
{_LOCAL_USER_PROMPT_2ND_INDENTED}


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
{_REMOTE_USER_PROMPT_1ST_INDENTED}


    # User prompt for second translation pass
    user_prompt_2nd_pass: |
{_REMOTE_USER_PROMPT_2ND_INDENTED}


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
