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
# - Fixed star imports to explicit imports for better code clarity
# - Fixed bare except to catch specific exceptions
# - Fixed equality comparison to True (use truthy check instead)
# - Added proper error handling for empty text in import_text_optimized
# - Removed inefficient io.StringIO usage, using direct splitlines() instead
#

"""
Optimized database module for EPUB chapter parsing.
Uses simplified schema and two-stage search for better performance.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING
from re import Pattern
from collections.abc import Callable

if TYPE_CHECKING:
    pass

from peewee import Model, IntegerField, TextField, BooleanField, AutoField, fn, chunked
from playhouse.sqlite_ext import SqliteExtDatabase


# Database instance - in-memory for maximum speed
db = SqliteExtDatabase(
    ":memory:",
    pragmas={
        "journal_mode": "memory",
        "cache_size": -64000,  # 64MB cache
        "synchronous": 0,  # No sync for in-memory DB
        "temp_store": "memory",
    },
)


class TextLine(Model):  # type: ignore[misc]
    """Simplified single table for all text lines"""

    line_id = AutoField()
    line_number = IntegerField(index=True)
    text_content = TextField()
    is_chapter = BooleanField(default=False)
    chapter_number = IntegerField(null=True)

    class Meta:
        database = db
        indexes = (
            (("line_number",), False),
            (("is_chapter",), False),
        )


class Chapter(Model):  # type: ignore[misc]
    """Table for chapter information"""

    chapter_id = AutoField()
    chapter_number = IntegerField()
    title = TextField()
    start_line = IntegerField()
    end_line = IntegerField()

    class Meta:
        database = db
        indexes = (
            (("chapter_number",), False),
            (("start_line",), False),
        )


def setup_database() -> None:
    """Initialize database and create tables"""
    if db.is_closed():
        db.connect()

    # Register custom functions
    db.register_function(
        lambda pattern, string: bool(re.search(pattern, string, re.IGNORECASE)),
        "regex_search",
        2,
    )

    db.create_tables([TextLine, Chapter], safe=True)


def close_database() -> None:
    """Close database connection"""
    if not db.is_closed():
        db.close()


def import_text_optimized(text: str) -> None:
    """
    Import text using optimized file loading method.
    Uses direct line splitting and chunk size of 1000 for best performance.
    """
    if not text or not text.strip():
        return  # Handle empty text gracefully

    # Direct line splitting is actually faster than StringIO for in-memory text
    lines = text.splitlines()

    if not lines:
        return

    # Prepare data for bulk insert
    data = [{"line_number": i + 1, "text_content": line} for i, line in enumerate(lines)]

    # Insert using optimal chunk size (1000 from benchmark)
    try:
        with db.atomic():
            for batch in chunked(data, 1000):
                TextLine.insert_many(batch).execute()
    except Exception as e:
        raise RuntimeError(f"Failed to import text to database: {e}") from e


def find_chapters_two_stage(
    heading_regex: Pattern[str],
    parse_num_func: Callable[[str | None], int | None],
    is_valid_func: Callable[[str], bool],
) -> list[TextLine]:
    """
    Two-stage chapter finding for optimal performance.
    Stage 1: Basic search for 'chapter' (reduces 632k lines to ~1.5k)
    Stage 2: Apply regex and validation rules to the subset
    """
    # STAGE 1: Fast basic search using LIKE query (fastest from benchmark)
    # This reduces 632k lines to ~1.5k lines
    stage1_query = TextLine.select().where(
        TextLine.text_content.contains("chapter")
        | TextLine.text_content.contains("Chapter")
        | TextLine.text_content.contains("CHAPTER")
        | TextLine.text_content.contains("Ch.")
        | TextLine.text_content.contains("CH.")
        | TextLine.text_content.contains("ch.")
        | TextLine.text_content.contains("Chap")
        | TextLine.text_content.contains("chap")
    )

    stage1_lines = list(stage1_query)
    print(f"[Stage 1] Found {len(stage1_lines)} potential chapter lines")

    # STAGE 2: Apply complex regex and validation to the subset
    validated_chapters = []
    last_chapter_line = -10
    last_chapter_text = None

    for line in stage1_lines:
        content = line.text_content.strip()

        # Skip if too close to last chapter (4-line window)
        if line.line_number - last_chapter_line <= 4:
            if content == last_chapter_text:
                continue  # Skip duplicate

        # Apply regex
        match = heading_regex.match(content)
        if not match:
            continue

        # Apply validation function
        if not is_valid_func(line.text_content):
            continue

        # Extract chapter number
        num_str = None
        for group in [
            "num_d",
            "num_r",
            "num_w",
            "part_d",
            "part_r",
            "part_w",
            "sec_d",
            "hash_d",
        ]:
            try:
                if match.group(group):
                    num_str = match.group(group)
                    break
            except (IndexError, AttributeError):
                pass

        chapter_num = parse_num_func(num_str) if num_str else None
        if chapter_num is None:
            continue

        # Mark as chapter
        line.is_chapter = True
        line.chapter_number = chapter_num
        validated_chapters.append(line)

        # Update tracking
        last_chapter_line = line.line_number
        last_chapter_text = content

    # Batch update all chapter flags
    with db.atomic():
        for batch in chunked(validated_chapters, 100):
            TextLine.bulk_update(batch, fields=[TextLine.is_chapter, TextLine.chapter_number])

    print(f"[Stage 2] Validated {len(validated_chapters)} chapter headings")
    return validated_chapters


def build_chapters_table() -> tuple[list[tuple[str, str]], list[int]]:
    """
    Build chapter content and create Chapter table entries.
    Returns chapters and sequence for compatibility.
    """
    # Get all chapter lines in order
    chapter_lines = list(TextLine.select().where(TextLine.is_chapter).order_by(TextLine.line_number))

    if not chapter_lines:
        # No chapters found, return entire content as one chapter
        all_text = "\n".join(line.text_content for line in TextLine.select().order_by(TextLine.line_number))
        return [("Content", all_text)], []

    chapters = []
    sequence = []
    chapter_records = []

    # Build chapters
    for i, chapter_line in enumerate(chapter_lines):
        # Determine chapter range
        start_line = chapter_line.line_number
        if i + 1 < len(chapter_lines):
            end_line = chapter_lines[i + 1].line_number - 1
        else:
            # Last chapter goes to end of file
            end_line = TextLine.select(fn.MAX(TextLine.line_number)).scalar()

        # Get chapter title
        title = chapter_line.text_content.strip()

        # Get chapter content using efficient aggregation
        content_lines = TextLine.select(TextLine.text_content).where((TextLine.line_number >= start_line) & (TextLine.line_number <= end_line)).order_by(TextLine.line_number)

        content = "\n".join(line.text_content for line in content_lines)

        chapters.append((title, content))
        sequence.append(chapter_line.chapter_number)

        # Prepare Chapter record
        chapter_records.append(
            {
                "chapter_number": chapter_line.chapter_number,
                "title": title,
                "start_line": start_line,
                "end_line": end_line,
            }
        )

    # Insert chapter records
    with db.atomic():
        Chapter.insert_many(chapter_records).execute()

    return chapters, sequence


def process_text_optimized(
    text: str,
    heading_regex: Pattern[str],
    parse_num_func: Callable[[str | None], int | None],
    is_valid_func: Callable[[str], bool],
) -> tuple[list[tuple[str, str]], list[int]]:
    """
    Main entry point for optimized text processing.
    """
    try:
        setup_database()

        # Import text with optimized method
        import_text_optimized(text)

        # Find chapters with two-stage approach
        find_chapters_two_stage(heading_regex, parse_num_func, is_valid_func)

        # Build chapter content and table
        chapters, sequence = build_chapters_table()

        return chapters, sequence

    finally:
        close_database()


# For testing: direct comparison function
def benchmark_comparison(text: str, heading_regex: Pattern[str]) -> None:
    """Compare old vs new approach performance"""
    import time

    # Test new optimized approach
    start = time.time()
    chapters, seq = process_text_optimized(
        text,
        heading_regex,
        lambda s: int(s) if s and s.isdigit() else None,
        lambda line: True,  # Simple validation for benchmark
    )
    optimized_time = time.time() - start

    print(f"\nOptimized approach: {optimized_time:.2f}s")
    print(f"Found {len(chapters)} chapters")
    print(f"Chapter sequence (first 10): {seq[:10]}")
