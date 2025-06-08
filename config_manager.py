#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
config_manager.py - Comprehensive configuration management for ENCHANT
"""

import os
import yaml
import logging
from pathlib import Path
from typing import Dict, Any, Optional
import multiprocessing

# Default configuration template with extensive comments
DEFAULT_CONFIG_TEMPLATE = """# ENCHANT Configuration File
# ========================
# This file contains default settings for the ENCHANT novel translation system.
# Any command-line arguments will override these settings.

# Translation Settings
# --------------------
translation:
  # AI service to use: 'local' or 'remote'
  # - local: Uses LM Studio running on localhost
  # - remote: Uses OpenRouter API (requires API key)
  service: local
  
  # Local API settings (LM Studio)
  local:
    # API endpoint for local LM Studio
    endpoint: "http://localhost:1234/v1/chat/completions"
    # Model name for local translation
    model: "local-model"
    # Request timeout in seconds
    timeout: 300
  
  # Remote API settings (OpenRouter)
  remote:
    # API endpoint for OpenRouter
    endpoint: "https://openrouter.ai/api/v1/chat/completions"
    # Model to use for translation (e.g., "deepseek/deepseek-chat")
    model: "deepseek/deepseek-chat"
    # API key (can also be set via OPENROUTER_API_KEY environment variable)
    api_key: null
    # Request timeout in seconds
    timeout: 300
  
  # Translation parameters
  # Temperature for AI responses (0.0 = deterministic, 1.0 = creative)
  temperature: 0.3
  # Maximum tokens per response
  max_tokens: 4000
  # Number of retry attempts for failed translations
  max_retries: 7
  # Base wait time between retries (exponential backoff)
  retry_wait_base: 1.0
  # Maximum wait time between retries
  retry_wait_max: 60.0

# Text Processing Settings
# -----------------------
text_processing:
  # Method for splitting text into paragraphs
  # - 'paragraph': Split on double newlines (recommended)
  # - 'punctuation': Split on Chinese punctuation (legacy)
  split_method: paragraph
  
  # How to split large texts
  # - 'PARAGRAPHS': Split by paragraph boundaries
  # - 'SPLIT_POINTS': Use explicit markers in text
  split_mode: PARAGRAPHS
  
  # Maximum characters per translation chunk
  max_chars_per_chunk: 12000
  
  # File encoding (auto-detected if not specified)
  # Common values: utf-8, gb2312, gb18030, big5
  default_encoding: utf-8

# Novel Renaming Settings
# ----------------------
novel_renaming:
  # Enable automatic novel renaming based on AI-extracted metadata
  enabled: false
  
  # OpenAI API settings for metadata extraction
  openai:
    # API key for OpenAI (can also be set via OPENAI_API_KEY environment variable)
    api_key: null
    # Model to use for metadata extraction
    model: "gpt-4o-mini"
    # Temperature for metadata extraction (0.0 = consistent)
    temperature: 0.0
  
  # Amount of text to read for metadata extraction (in KB)
  kb_to_read: 35
  
  # Minimum file size to consider for renaming (in KB)
  min_file_size_kb: 100

# EPUB Generation Settings
# -----------------------
epub:
  # Enable EPUB generation after translation
  enabled: false
  
  # Detect and build table of contents from chapter headings
  build_toc: true
  
  # Language code for EPUB metadata
  language: "zh"
  
  # Include cover image if available
  include_cover: true
  
  # Validate chapter sequence and report issues
  validate_chapters: true
  
  # Strict mode - abort on validation issues
  strict_mode: false

# Batch Processing Settings
# ------------------------
batch:
  # Maximum number of worker threads for parallel processing
  # Set to null to use CPU count
  max_workers: null
  
  # Process subdirectories recursively
  recursive: true
  
  # Pattern for finding text files (glob pattern)
  file_pattern: "*.txt"
  
  # Continue processing even if individual files fail
  continue_on_error: true
  
  # Save progress for resume capability
  save_progress: true
  
  # Progress file names
  progress_file: "translation_batch_progress.yml"
  archive_file: "translations_chronology.yml"

# iCloud Sync Settings
# -------------------
icloud:
  # Enable iCloud sync (auto-detected by default)
  # Set to true/false to force enable/disable
  enabled: null
  
  # Wait timeout for file sync (seconds)
  sync_timeout: 300
  
  # Check interval for sync status (seconds)
  sync_check_interval: 2

# Model Pricing Settings
# ---------------------
pricing:
  # Enable cost calculation and tracking
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
  # Log level: DEBUG, INFO, WARNING, ERROR, CRITICAL
  level: INFO
  
  # Log to file
  file_enabled: true
  file_path: "enchant_book_manager.log"
  
  # Log format
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Advanced Settings
# ----------------
advanced:
  # Clean advertisements from text
  clean_adverts: true
  
  # Character limit for content preview
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
    """Manages configuration for ENCHANT system."""
    
    def __init__(self, config_path: Optional[Path] = None, logger: Optional[logging.Logger] = None):
        """
        Initialize configuration manager.
        
        Args:
            config_path: Path to configuration file (default: enchant_config.yml)
            logger: Logger instance
        """
        self.logger = logger or logging.getLogger(__name__)
        self.config_path = config_path or Path("enchant_config.yml")
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file or create default."""
        if not self.config_path.exists():
            self.logger.info(f"Configuration file not found. Creating default at: {self.config_path}")
            self._create_default_config()
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                
            if config is None:
                self.logger.warning("Configuration file is empty. Using defaults.")
                return self._get_default_config()
            
            # Validate configuration
            if not self._validate_config(config):
                raise ValueError("Configuration validation failed")
            
            # Merge with defaults to ensure all keys exist
            return self._merge_with_defaults(config)
            
        except yaml.YAMLError as e:
            self.logger.error(f"Error parsing configuration file: {e}")
            self.logger.error("Please fix the YAML syntax or delete the file to regenerate defaults.")
            raise ValueError(f"Invalid YAML configuration: {e}")
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
    
    def _validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate configuration structure and values."""
        try:
            # Check required top-level sections
            required_sections = ['translation', 'text_processing', 'novel_renaming', 
                               'epub', 'batch', 'icloud', 'pricing', 'logging']
            
            for section in required_sections:
                if section not in config:
                    self.logger.error(f"Missing required configuration section: {section}")
                    return False
            
            # Validate specific values
            if config['translation']['service'] not in ['local', 'remote']:
                self.logger.error("Invalid translation service. Must be 'local' or 'remote'")
                return False
            
            if config['text_processing']['split_method'] not in ['paragraph', 'punctuation']:
                self.logger.error("Invalid split_method. Must be 'paragraph' or 'punctuation'")
                return False
            
            if config['text_processing']['split_mode'] not in ['PARAGRAPHS', 'SPLIT_POINTS']:
                self.logger.error("Invalid split_mode. Must be 'PARAGRAPHS' or 'SPLIT_POINTS'")
                return False
            
            # Validate numeric values
            if config['text_processing']['max_chars_per_chunk'] <= 0:
                self.logger.error("max_chars_per_chunk must be positive")
                return False
            
            return True
            
        except KeyError as e:
            self.logger.error(f"Missing required configuration key: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Configuration validation error: {e}")
            return False
    
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
    
    def update_with_args(self, args) -> Dict[str, Any]:
        """
        Update configuration with command-line arguments.
        Command-line args take precedence over config file.
        
        Args:
            args: Parsed command-line arguments
            
        Returns:
            Updated configuration dictionary
        """
        config = self.config.copy()
        
        # Map command-line arguments to config keys
        arg_mapping = {
            'encoding': 'text_processing.default_encoding',
            'max_chars': 'text_processing.max_chars_per_chunk',
            'split_method': 'text_processing.split_method',
            'split_mode': 'text_processing.split_mode',
            'remote': 'translation.service',  # True -> 'remote', False -> 'local'
            'epub': 'epub.enabled',
            'batch': 'batch.enabled',
            'max_workers': 'batch.max_workers',
        }
        
        for arg_name, config_path in arg_mapping.items():
            if hasattr(args, arg_name):
                value = getattr(args, arg_name)
                if value is not None:
                    # Special handling for 'remote' flag
                    if arg_name == 'remote':
                        value = 'remote' if value else 'local'
                    
                    # Set value in config
                    keys = config_path.split('.')
                    target = config
                    for key in keys[:-1]:
                        if key not in target:
                            target[key] = {}
                        target = target[key]
                    target[keys[-1]] = value
        
        return config
    
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
            'openai': 'OPENAI_API_KEY'
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