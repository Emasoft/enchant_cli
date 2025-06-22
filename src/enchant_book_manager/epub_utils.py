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
Common EPUB generation utilities for EnChANT.
Provides a unified interface for EPUB creation with configuration support.
"""

from pathlib import Path
from typing import Optional, Any
import logging

# Import the make_epub module functions
try:
    from .make_epub import create_epub_from_txt_file

    epub_available = True
except ImportError:
    epub_available = False


def create_epub_with_config(
    txt_file_path: Path,
    output_path: Path,
    config: dict[str, Any],
    logger: logging.Logger | None = None,
) -> tuple[bool, list[str]]:
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
    title = config.get("title")
    author = config.get("author")

    if not title or not author:
        error_msg = "Title and author are required for EPUB creation"
        if logger:
            logger.error(error_msg)
        return False, [error_msg]

    # Extract optional configuration with defaults
    cover_path = config.get("cover_path")
    if cover_path:
        cover_path = Path(cover_path)

    generate_toc = config.get("generate_toc", True)
    validate = config.get("validate", True)
    strict_mode = config.get("strict_mode", False)
    language = config.get("language", "en")
    custom_css = config.get("custom_css", None)
    metadata = config.get("metadata", None)

    # Log configuration
    if logger:
        logger.info(f"Creating EPUB for: {title} by {author}")
        logger.debug(f"EPUB configuration: generate_toc={generate_toc}, validate={validate}, strict_mode={strict_mode}, language={language}")

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
            strict_mode=strict_mode,
            language=language,
            custom_css=custom_css,
            metadata=metadata,
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


def get_epub_config_from_book_info(book_info: dict[str, Any], epub_settings: dict[str, Any] | None = None) -> dict[str, Any]:
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
        "title": book_info.get("title_english", "Unknown Title"),
        "author": book_info.get("author_english", "Unknown Author"),
        "generate_toc": True,
        "validate": True,
        "strict_mode": False,
    }

    # Apply EPUB settings from configuration
    if epub_settings:
        # Basic settings
        config["generate_toc"] = epub_settings.get("generate_toc", True)
        config["validate"] = epub_settings.get("validate_chapters", True)
        config["strict_mode"] = epub_settings.get("strict_mode", False)
        config["language"] = epub_settings.get("language", "en")

        # Custom CSS if provided
        if epub_settings.get("custom_css"):
            config["custom_css"] = epub_settings["custom_css"]

        # Chapter patterns if provided
        if epub_settings.get("chapter_patterns"):
            config["chapter_patterns"] = epub_settings["chapter_patterns"]

    # Build metadata
    metadata = {}

    # Original title and author
    if book_info.get("title_chinese"):
        metadata["original_title"] = book_info["title_chinese"]
    if book_info.get("author_chinese"):
        metadata["original_author"] = book_info["author_chinese"]

    # Apply metadata settings from config
    if epub_settings and epub_settings.get("metadata"):
        meta_config = epub_settings["metadata"]

        # Publisher, series, etc.
        if meta_config.get("publisher"):
            metadata["publisher"] = meta_config["publisher"]
        if meta_config.get("series"):
            metadata["series"] = meta_config["series"]
        if meta_config.get("series_index"):
            metadata["series_index"] = meta_config["series_index"]

        # Generate description from template
        if meta_config.get("description_template"):
            template = meta_config["description_template"]
            description = template.format(
                title=config["title"],
                author=config["author"],
                original_title=book_info.get("title_chinese", ""),
                original_author=book_info.get("author_chinese", ""),
            )
            metadata["description"] = description

        # Tags
        if meta_config.get("tags"):
            metadata["tags"] = meta_config["tags"]

    if metadata:
        config["metadata"] = metadata

    return config
