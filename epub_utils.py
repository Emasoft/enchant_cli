#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Common EPUB generation utilities for EnChANT.
Provides a unified interface for EPUB creation with configuration support.
"""

from pathlib import Path
from typing import Optional, Tuple, List, Dict, Any
import logging

# Import the make_epub module functions
try:
    from make_epub import create_epub_from_txt_file
    epub_available = True
except ImportError:
    epub_available = False


def create_epub_with_config(
    txt_file_path: Path,
    output_path: Path,
    config: Dict[str, Any],
    logger: Optional[logging.Logger] = None
) -> Tuple[bool, List[str]]:
    """
    Create an EPUB file from a translated text file using configuration.
    
    This is the main entry point for EPUB generation in the EnChANT system.
    It provides a consistent interface and handles all configuration options.
    
    Args:
        txt_file_path: Path to the complete translated text file
        output_path: Path where the EPUB should be saved
        config: Configuration dictionary containing:
            - title: Book title (required)
            - author: Book author (required)
            - language: Language code (default: 'en')
            - cover_path: Optional path to cover image
            - generate_toc: Whether to detect chapters (default: True)
            - validate: Whether to validate chapter sequence (default: True)
            - strict_mode: Whether to abort on validation issues (default: False)
            - custom_css: Optional custom CSS content
            - metadata: Optional additional metadata dict
        logger: Optional logger instance
        
    Returns:
        Tuple of (success: bool, issues: List[str])
    """
    if not epub_available:
        error_msg = "EPUB creation requested but 'make_epub' module is not available."
        if logger:
            logger.error(error_msg)
        return False, [error_msg]
    
    # Extract required configuration
    title = config.get('title')
    author = config.get('author')
    
    if not title or not author:
        error_msg = "Title and author are required for EPUB creation"
        if logger:
            logger.error(error_msg)
        return False, [error_msg]
    
    # Extract optional configuration with defaults
    cover_path = config.get('cover_path')
    if cover_path:
        cover_path = Path(cover_path)
    
    generate_toc = config.get('generate_toc', True)
    validate = config.get('validate', True)
    strict_mode = config.get('strict_mode', False)
    
    # Log configuration
    if logger:
        logger.info(f"Creating EPUB for: {title} by {author}")
        logger.debug(f"EPUB configuration: generate_toc={generate_toc}, validate={validate}, strict_mode={strict_mode}")
    
    try:
        # Call the make_epub function
        success, issues = create_epub_from_txt_file(
            txt_file_path=txt_file_path,
            output_path=output_path,
            title=title,
            author=author,
            cover_path=cover_path,
            generate_toc=generate_toc,
            validate=validate,
            strict_mode=strict_mode
        )
        
        # Log results
        if logger:
            if success:
                logger.info(f"EPUB created successfully: {output_path}")
                if issues:
                    logger.warning(f"EPUB created with {len(issues)} validation warnings")
                    for issue in issues[:5]:
                        logger.warning(f"  - {issue}")
                    if len(issues) > 5:
                        logger.warning(f"  ... and {len(issues) - 5} more warnings")
            else:
                logger.error(f"EPUB creation failed with {len(issues)} errors")
                for issue in issues[:5]:
                    logger.error(f"  - {issue}")
                if len(issues) > 5:
                    logger.error(f"  ... and {len(issues) - 5} more errors")
        
        return success, issues
        
    except Exception as e:
        error_msg = f"Unexpected error during EPUB creation: {str(e)}"
        if logger:
            logger.exception("Error creating EPUB")
        return False, [error_msg]


def get_epub_config_from_book_info(
    book_info: Dict[str, Any],
    epub_settings: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Build EPUB configuration from book information and settings.
    
    Args:
        book_info: Dictionary containing book metadata:
            - title_english: English title
            - author_english: English author name
            - title_chinese: Original Chinese title (optional)
            - author_chinese: Original Chinese author (optional)
        epub_settings: Optional EPUB-specific settings from config
        
    Returns:
        Configuration dictionary for create_epub_with_config
    """
    config = {
        'title': book_info.get('title_english', 'Unknown Title'),
        'author': book_info.get('author_english', 'Unknown Author'),
        'generate_toc': True,
        'validate': True,
        'strict_mode': False
    }
    
    # Add any EPUB-specific settings
    if epub_settings:
        config.update(epub_settings)
    
    # Add metadata if available
    metadata = {}
    if book_info.get('title_chinese'):
        metadata['original_title'] = book_info['title_chinese']
    if book_info.get('author_chinese'):
        metadata['original_author'] = book_info['author_chinese']
    
    if metadata:
        config['metadata'] = metadata
    
    return config