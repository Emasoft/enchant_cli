#!/usr/bin/env python3
# -*- coding: utf-8 -*-

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

# HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
# - Fixed missing import of epub_db module (removed fallback to non-existent module)
# - Removed unused variables: has_parts (line 494) and has_letter_suffix (lines 497-500)
# - Extracted shared constants and utilities to epub_constants.py to avoid duplication
# - Added DB_OPTIMIZATION_THRESHOLD constant instead of magic number
# - Simplified database fallback logic
# - MAJOR REFACTORING: Split into smaller modules (chapter_detector, epub_builders, epub_generator, epub_validation)
# - This file now serves as the main API module, importing from the smaller modules
#

"""
make_epub.py – build or extend an EPUB from numbered plain-text “chunk” files
============================================================================

* Converts a directory of *.txt* “chunks” into an EPUB-2 book (or appends new
  chunks to an existing one).
* Detects headings such as **“Chapter 7”**, **“Chapter VII”**, or
  **“Chapter Seven”** (1-9999 in words) and canonicalises them.
* Builds the exact list of chapter numbers *in the order they appear*, collapses
  consecutive duplicate heading lines, and passes it to `detect_issues(seq)`
  which reports anomalies in the required wording:

    • `chapter N is missing`
    • `chapter N is out of place after chapter M`
    • `chapter N is switched in place with chapter M`
    • `chapter N is repeated K times after chapter M`

* Run-modes
  • **strict**  (default) abort on issues
  • **soft**    `--no-strict` log issues, still build
  • **validate-only** just scan & exit
  • Optional JSON-lines issue log (`--json-log`).

Pure Python ≥ 3.8.  Output EPUB passes *epubcheck*.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Any

# Import from refactored modules
from .chapter_detector import (
    HEADING_RE,
    PART_PATTERNS,
    has_part_notation,
    is_valid_chapter_line,
    parse_num,
    split_text,
    split_text_db,
    detect_issues,
)
from .epub_builders import (
    build_chap_xhtml,
    build_container_xml,
    build_content_opf,
    build_cover_xhtml,
    build_style_css,
    build_toc_ncx,
    paragraphize,
)
from .epub_generator import (
    write_new_epub,
    extend_epub,
)
from .epub_validation import (
    ValidationError,
    ensure_dir_readable,
    ensure_output_ok,
    ensure_cover_ok,
    collect_chunks,
    log_issue,
    set_json_log,
)
from .epub_constants import (
    ENCODING,
    MIMETYPE,
    FILENAME_RE,
)


# NOTE: All these functions are now imported from the refactored modules above.
# They are kept here for backward compatibility, but the actual implementations
# are in the respective modules.


# ───────────────────────── Module API ─────────────────────────


def create_epub_from_chapters(
    chapters: list[tuple[str, str]],
    output_path: Path,
    title: str,
    author: str,
    cover_path: Path | None = None,
    detect_headings: bool = True,
) -> None:
    """
    Create an EPUB from a list of chapters.

    Args:
        chapters: List of (chapter_title, chapter_content) tuples
        output_path: Path where the EPUB should be saved
        title: Book title
        author: Book author
        cover_path: Optional path to cover image
        detect_headings: Whether to detect and process chapter headings

    Raises:
        ValidationError: If there are issues with inputs
        OSError: If there are file system errors
    """
    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Validate cover if provided
    if cover_path and cover_path.exists():
        if cover_path.suffix.lower() not in {".jpg", ".jpeg", ".png"}:
            raise ValidationError("Cover must be .jpg/.jpeg/.png")

    # Process chapters - convert text to HTML
    processed_chapters = []
    for chap_title, chap_content in chapters:
        # Convert plain text to HTML paragraphs
        html_content = paragraphize(chap_content)
        processed_chapters.append((chap_title, html_content))

    # Create the EPUB
    write_new_epub(processed_chapters, output_path, title, author, cover_path)


def create_epub_from_txt_file(
    txt_file_path: Path,
    output_path: Path,
    title: str,
    author: str,
    cover_path: Path | None = None,
    generate_toc: bool = True,
    validate: bool = True,
    strict_mode: bool = False,
    language: str = "en",
    custom_css: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> tuple[bool, list[str]]:
    """
    Create an EPUB from a complete translated text file.
    This is the main entry point for enchant_cli.py integration.

    Args:
        txt_file_path: Path to the complete translated text file
        output_path: Path where the EPUB should be saved
        title: Book title
        author: Book author
        cover_path: Optional path to cover image
        generate_toc: Whether to detect chapter headings and build TOC
        validate: Whether to validate chapter sequence
        strict_mode: Whether to abort on validation issues
        language: Language code for the book (default: 'en')
        custom_css: Optional custom CSS content to use instead of default
        metadata: Optional dictionary with additional metadata:
            - publisher: Publisher name
            - description: Book description
            - series: Series name
            - series_index: Position in series

    Returns:
        Tuple of (success: bool, issues: List[str])

    Raises:
        ValidationError: If there are issues with inputs
        OSError: If there are file system errors
    """
    # Read the complete text file
    if not txt_file_path.exists():
        raise ValidationError(f"Input file not found: {txt_file_path}")

    try:
        full_text = txt_file_path.read_text(encoding="utf-8")
    except Exception as e:
        raise ValidationError(f"Error reading input file: {e}") from e

    # Split text into chapters and detect headings
    chap_blocks, chapter_sequence = split_text(full_text, detect_headings=generate_toc)
    chapters = [(title, paragraphize(content)) for title, content in chap_blocks]

    # Validate chapter sequence if requested
    issues = []
    if validate and generate_toc:
        issues = detect_issues(chapter_sequence)
        for issue in issues:
            log_issue(issue, {"file": str(txt_file_path), "issue": issue})

        if issues and strict_mode:
            return False, issues

    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Validate cover if provided
    if cover_path and cover_path.exists():
        if cover_path.suffix.lower() not in {".jpg", ".jpeg", ".png"}:
            raise ValidationError("Cover must be .jpg/.jpeg/.png")

    # Create the EPUB
    try:
        write_new_epub(
            chapters,
            output_path,
            title,
            author,
            cover_path,
            language=language,
            custom_css=custom_css,
            metadata=metadata,
        )
        return True, issues
    except Exception as e:
        issues.append(f"Error creating EPUB: {e}")
        return False, issues


def create_epub_from_directory(
    input_dir: Path,
    output_path: Path,
    title: str | None = None,
    author: str | None = None,
    cover_path: Path | None = None,
    detect_headings: bool = True,
    validate_only: bool = False,
    strict: bool = True,
) -> list[str]:
    """
    Create an EPUB from a directory of chapter files.

    Args:
        input_dir: Directory containing chapter .txt files
        output_path: Path where the EPUB should be saved
        title: Book title (auto-detected if None)
        author: Book author (auto-detected if None)
        cover_path: Optional path to cover image
        detect_headings: Whether to detect and process chapter headings
        validate_only: Only validate, don't create EPUB
        strict: Abort on validation issues

    Returns:
        List of validation issue messages (empty if no issues)

    Raises:
        ValidationError: If there are issues with inputs and strict=True
        OSError: If there are file system errors
    """
    # Ensure directory is readable
    if not input_dir.exists() or not input_dir.is_dir():
        raise ValidationError(f"Directory '{input_dir}' not found or not a directory.")

    # Collect chunks
    chunks = collect_chunks(input_dir)
    if not chunks:
        raise ValidationError("No valid .txt chunks found.")

    # Read and combine all chunks
    full_text = "\n".join(chunks[i].read_text(ENCODING) for i in sorted(chunks))

    # Split into chapters and detect issues
    chap_blocks, seq = split_text(full_text, detect_headings)
    chapters = [(t, paragraphize(b)) for t, b in chap_blocks]

    # Check for issues
    issues = detect_issues(seq) if seq else []

    if validate_only:
        return issues

    if issues and strict:
        raise ValidationError(f"Found {len(issues)} validation issues in chapter sequence")

    # Auto-detect title and author if not provided
    if not title or not author:
        first = chunks[min(chunks)]
        if m := FILENAME_RE.match(first.name):
            title = title or m.group("title")
            author = author or m.group("author")
        else:
            title = title or "Untitled"
            author = author or "Unknown"

    # Create the EPUB
    write_new_epub(chapters, output_path, title, author, cover_path)

    return issues


# ───────────────────────── CLI entry point ───────────────────────── #


# This module is now a library only - use enchant_cli.py for command line interface
