#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
# - Created new module from chapter_detector.py refactoring
# - Contains main parsing functions for chapter detection
# - Includes split_text_db, split_text, and detect_issues
#

"""
chapter_parser.py - Main parsing functions for chapter detection
================================================================

Contains the core text splitting and chapter parsing logic, including
database-optimized processing for large files and issue detection.
"""

from __future__ import annotations

import re
from typing import Optional, Callable

from .chapter_patterns import HEADING_RE, DB_OPTIMIZATION_THRESHOLD
from .chapter_validators import has_part_notation, parse_num, is_valid_chapter_line

# Import database module for fast chapter indexing
try:
    from .epub_db_optimized import process_text_optimized

    DB_OPTIMIZED = True
except ImportError:
    # Database optimization not available
    DB_OPTIMIZED = False


def split_text_db(
    text: str,
    detect_headings: bool,
    log_issue_func: Optional[Callable[[str], None]] = None,
) -> tuple[list[tuple[str, str]], list[int]]:
    """
    Database-optimized version for fast chapter parsing.
    Uses SQLite with indexes for efficient processing of large files.
    """
    if not detect_headings:
        return [("Content", text)], []

    try:
        if DB_OPTIMIZED:
            # Use new optimized approach with two-stage search
            return process_text_optimized(text, HEADING_RE, parse_num, is_valid_chapter_line)
        else:
            # Database optimization not available, fallback to regular processing
            return split_text(text, detect_headings, force_no_db=True)

    except Exception as e:
        # Log error and fallback to non-database method
        if log_issue_func:
            log_issue_func(f"Database processing failed: {e}")
        return split_text(text, detect_headings, force_no_db=True)


def split_text(text: str, detect_headings: bool, force_no_db: bool = False) -> tuple[list[tuple[str, str]], list[int]]:
    """
    Enhanced version with:
    1. Position/quote checking for chapter patterns
    2. Smart duplicate detection (4-line window)
    3. Sub-numbering for multi-part chapters

    For large files (>100K lines), automatically uses database optimization.

    Args:
        text: The text to split
        detect_headings: Whether to detect chapter headings
        force_no_db: Force non-database processing (used for fallback)
    """
    # Use database optimization for large files (unless forced not to)
    lines = text.splitlines()
    if not force_no_db and len(lines) > DB_OPTIMIZATION_THRESHOLD:
        try:
            return split_text_db(text, detect_headings)
        except Exception:
            # Fallback to regular processing if database fails
            pass

    # Original implementation for smaller files
    if not detect_headings:
        return [("Content", text)], []

    # First pass: collect raw chapters with position/quote validation
    raw_chapters: list[tuple[str, str, int | None]] = []
    seq = []
    buf = []
    cur_title = None
    cur_num = None  # Track the current chapter's number
    front_done = False
    last_num: int | None = None
    blank_only = True

    # Track recent chapter detections for smart duplicate detection
    last_chapter_line = -10  # Start far back
    last_chapter_num = None
    last_chapter_text = None

    lines = text.splitlines()
    for line_idx, line in enumerate(lines):
        m = HEADING_RE.match(line.strip())
        if m:
            # Additional validation for chapter patterns
            # Only validate lines that start with "Chapter" (not abbreviations or other patterns)
            stripped_line = line.strip().lower()
            if (stripped_line.startswith("chapter ") or stripped_line.startswith("chapter\t")) and not is_valid_chapter_line(line):
                # Skip false positive (dialogue, mid-sentence, etc.)
                buf.append(line)
                blank_only = False
                continue

            # Extract number from whichever group matched
            num_str = m.group("num_d") or m.group("num_r") or m.group("num_w") or m.group("part_d") or m.group("part_r") or m.group("part_w") or m.group("sec_d") or m.group("hash_d")
            num = parse_num(num_str) if num_str else None
            if num is None:
                buf.append(line)
                blank_only = False
                continue

            # Smart duplicate detection
            lines_since_last = line_idx - last_chapter_line
            current_text = line.strip()

            # Skip if same text within 4 lines (true duplicate)
            if lines_since_last <= 4 and current_text == last_chapter_text:
                buf.append(line)
                blank_only = False
                continue

            # For same number within 4 lines, check if it's a different part
            if lines_since_last <= 4 and num == last_chapter_num:
                # Allow if subtitle is different (multi-part chapter)
                pass  # Will be handled by sub-numbering

            # Update tracking
            last_chapter_line = line_idx
            last_chapter_num = num
            last_chapter_text = current_text

            # Original duplicate logic for blank-only sections
            if last_num == num and blank_only:
                buf.clear()
                continue
            last_num = num
            blank_only = True

            if not front_done:
                if buf:
                    raw_chapters.append(("Front Matter", "\n".join(buf).strip(), None))
                    buf.clear()
                front_done = True

            if cur_title:
                raw_chapters.append((cur_title, "\n".join(buf).strip(), cur_num))
                buf.clear()

            # Use the original line text as the chapter title
            cur_title = line.strip()
            cur_num = num  # Save the current chapter's number
            seq.append(num)
        else:
            buf.append(line)
            if line.strip():
                blank_only = False

    if cur_title:
        raw_chapters.append((cur_title, "\n".join(buf).strip(), cur_num))
    elif buf:
        raw_chapters.append(("Content", "\n".join(buf).strip(), None))

    # Second pass: analyze patterns to determine which chapters need sub-numbering
    chapter_groups: dict[int, list[tuple[str, str, int | None]]] = {}
    chapter_index: dict[tuple[int | None, str], int] = {}  # Map (num, title) to index for O(1) lookup

    # Group chapters by their number and build index
    for idx, (title, content, num) in enumerate(raw_chapters):
        if num is not None:
            if num not in chapter_groups:
                chapter_groups[num] = []
            chapter_groups[num].append((title, content, num))
            chapter_index[(num, title)] = idx

    # Analyze each group to determine if sub-numbering is needed
    needs_subnumbering: dict[int, bool] = {}

    for num, group in chapter_groups.items():
        if len(group) > 1:
            # Multiple chapters with same number - need sub-numbering
            needs_subnumbering[num] = True
        else:
            # Single chapter with this number - check if it's part of a sequence
            # Look for part notation that might indicate it's part of a larger sequence
            title = group[0][0]

            # If it has part notation, check adjacent chapters
            if has_part_notation(title):
                # Use index for O(1) lookup instead of linear search
                chapter_idx: int | None = chapter_index.get((num, title))
                if chapter_idx is not None:
                    # Check previous and next chapters
                    prev_has_parts = chapter_idx > 0 and raw_chapters[chapter_idx - 1][2] is not None and has_part_notation(raw_chapters[chapter_idx - 1][0])
                    next_has_parts = chapter_idx < len(raw_chapters) - 1 and raw_chapters[chapter_idx + 1][2] is not None and has_part_notation(raw_chapters[chapter_idx + 1][0])

                    # If adjacent chapters also have part notation with different numbers,
                    # then this is likely sequential numbering, not sub-parts
                    if prev_has_parts or next_has_parts:
                        prev_num = raw_chapters[chapter_idx - 1][2] if chapter_idx > 0 else None
                        next_num = raw_chapters[chapter_idx + 1][2] if chapter_idx < len(raw_chapters) - 1 else None

                        # Sequential if numbers are different
                        if (prev_num != num and prev_num is not None) or (next_num != num and next_num is not None):
                            needs_subnumbering[num] = False
                        else:
                            needs_subnumbering[num] = True
                    else:
                        needs_subnumbering[num] = False
            else:
                needs_subnumbering[num] = False

    # Third pass: generate final chapters with sub-numbering only where needed
    chapters = []
    part_counters: dict[int, int] = {}

    for title, content, num in raw_chapters:
        if num is None:
            # Non-chapter content (Front Matter, etc.)
            chapters.append((title, content))
        elif needs_subnumbering.get(num, False):
            # This chapter needs sub-numbering
            part_counters[num] = part_counters.get(num, 0) + 1
            part_num = part_counters[num]

            # For multi-part chapters, append part number to original title
            # Try to insert the part number after the chapter number
            # Match various chapter patterns to insert part number appropriately
            if re.match(r"^Chapter\s+\w+:", title, re.IGNORECASE):
                # "Chapter One: Title" -> "Chapter One.1: Title"
                new_title = re.sub(r"^(Chapter\s+\w+):", rf"\1.{part_num}:", title, flags=re.IGNORECASE)
            elif re.match(r"^Chapter\s+\w+\s", title, re.IGNORECASE):
                # "Chapter One Title" -> "Chapter One.1 Title"
                new_title = re.sub(
                    r"^(Chapter\s+\w+)(\s)",
                    rf"\1.{part_num}\2",
                    title,
                    flags=re.IGNORECASE,
                )
            else:
                # Fallback: just append part number
                new_title = f"{title} (Part {part_num})"

            chapters.append((new_title, content))
        else:
            # Single chapter or sequential numbering - keep as is
            chapters.append((title, content))

    return chapters, seq
