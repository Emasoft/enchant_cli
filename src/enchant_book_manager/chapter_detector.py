#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
# - Initial creation from make_epub.py refactoring
# - Extracted chapter detection and parsing logic
# - Includes pattern matching, parsing, and validation functions
# - Contains split_text and related functions for chapter processing
#

"""
chapter_detector.py - Chapter detection and parsing for EPUB generation
======================================================================

Handles detection of chapter headings in various formats (numeric, roman, word)
and splits text into chapters with proper sequencing and validation.
"""

from __future__ import annotations

import re
from typing import Optional, Any, Callable

from .epub_constants import (
    ENCODING,
    WORD_NUMS,
    parse_num as parse_num_shared,
)

# Import database module for fast chapter indexing
try:
    from .epub_db_optimized import process_text_optimized

    DB_OPTIMIZED = True
except ImportError:
    # Database optimization not available
    DB_OPTIMIZED = False

# ────────────────────────── regexes & tables ────────────────────────── #

# Enhanced regex for various English chapter heading patterns
HEADING_RE = re.compile(
    rf"^[^\w]*\s*"  # Allow leading non-word chars and whitespace
    rf"(?:"  # Start of main group
    rf"(?:chapter|ch\.?|chap\.?)\s*"  # "Chapter", "Ch.", "Ch", "Chap.", "Chap" (space optional)
    rf"(?:(?P<num_d>\d+[a-z]?)|(?P<num_r>[ivxlcdm]+)|"  # Added [a-z]? for letter suffixes
    rf"(?P<num_w>(?:{WORD_NUMS})(?:[-\s](?:{WORD_NUMS}))*))"
    rf"|"  # OR
    rf"(?:part|section|book)\s+"  # "Part", "Section", "Book"
    rf"(?:(?P<part_d>\d+)|(?P<part_r>[ivxlcdm]+)|"
    rf"(?P<part_w>(?:{WORD_NUMS})(?:[-\s](?:{WORD_NUMS}))*))"
    rf"|"  # OR
    rf"§\s*(?P<sec_d>\d+)"  # "§ 42" style
    rf"|"  # OR
    rf"(?P<hash_d>\d+)\s*(?:\.|\)|:|-)?"  # "1.", "1)", "1:", "1-" at start of line
    rf")"
    rf"\b(?P<rest>.*)$",
    re.IGNORECASE,
)

# Regex patterns for detecting part notation in chapter titles
PART_PATTERNS = [
    # Fraction patterns: 1/3, 2/3, [1/3], (1 of 3)
    re.compile(r"\b(\d+)\s*/\s*(\d+)\b"),
    re.compile(r"\[(\d+)\s*/\s*(\d+)\]"),
    re.compile(r"\((\d+)\s*of\s*(\d+)\)", re.IGNORECASE),
    re.compile(r"\((\d+)\s*out\s*of\s*(\d+)\)", re.IGNORECASE),
    # Part word patterns: part 1, part one, pt. 1
    re.compile(
        r"\bpart\s+(\d+|one|two|three|four|five|six|seven|eight|nine|ten)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bpt\.?\s+(\d+|one|two|three|four|five|six|seven|eight|nine|ten)\b",
        re.IGNORECASE,
    ),
    # Dash number patterns: - 1, - 2
    re.compile(r"\s+-\s+(\d+)\s*$"),
    # Roman numeral patterns at end with word boundary: Part I, Part II, etc
    # More restrictive to avoid matching names like "Louis XIV"
    re.compile(r"(?:part|pt\.?)\s+([IVX]+)\s*$", re.IGNORECASE),
    re.compile(r"\s+-\s+([IVX]+)\s*$"),  # "- I", "- II", etc
]

# Database optimization threshold
DB_OPTIMIZATION_THRESHOLD = 100000  # Number of lines before using database


def has_part_notation(title: str) -> bool:
    """Check if a title contains part notation patterns.

    Args:
        title: Chapter title to check

    Returns:
        True if title contains part notation, False otherwise
    """
    if not title:  # Handle None or empty string
        return False

    # Early return on first match for better performance
    return any(pattern.search(title) for pattern in PART_PATTERNS)


# Use parse_num wrapper to maintain compatibility with existing code
def parse_num(raw: str | None) -> int | None:
    """Wrapper for shared parse_num function."""
    if raw is None:
        return None
    return parse_num_shared(raw)


def is_valid_chapter_line(line: str) -> bool:
    """
    Check if a line contains a valid chapter heading based on:
    1. Chapter word at start of line (or after special chars)
    2. Chapter word not in quotes
    """
    line_stripped = line.strip()
    lower_line = line_stripped.lower()

    # Check if line starts with quotes containing chapter
    if line_stripped.startswith(('"', "'")) and "chapter" in lower_line:
        quote_char = line_stripped[0]
        try:
            end_quote = line_stripped.index(quote_char, 1)
            if "chapter" in line_stripped[:end_quote].lower():
                return False  # Chapter word is in quotes
        except ValueError:
            pass

    # Check if chapter appears mid-sentence (not after special chars)
    chapter_pos = lower_line.find("chapter")
    if chapter_pos == -1:
        return True  # No chapter word, let regex decide

    if chapter_pos == 0:
        return True  # At start of line

    # Check what comes before chapter
    before_chapter = line_stripped[:chapter_pos].strip()

    # Special characters that can precede chapter
    if before_chapter and all(c in "#*>§[](){}|-–—•~/" or c.isspace() for c in before_chapter):
        return True  # After special chars/whitespace only

    # Check if preceded by quotes
    if before_chapter.endswith(('"', "'")):
        return False  # Chapter word likely in quotes

    return False  # Mid-sentence


def split_text_db(text: str, detect_headings: bool, log_issue_func: Optional[Callable[[str], None]] = None) -> tuple[list[tuple[str, str]], list[int]]:
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


def detect_issues(seq: list[int]) -> list[str]:
    """
    Updated algorithm provided by user: reports missing, repeats, swaps,
    out-of-place, duplicates.
    """
    if not seq:
        return []

    issues = []
    start, end = seq[0], seq[-1]
    prev_expected = start
    seen = set()
    reported_missing = set()

    for idx, v in enumerate(seq):
        # 1) Repeats: only on second+ occurrence
        if v in seen:
            # find nearest non-identical predecessor
            try:
                pred = next(x for x in reversed(seq[:idx]) if x != v)
            except StopIteration:
                # No non-identical predecessor found (all previous values are the same)
                # Use the first value in sequence, or 0 if this is the first
                pred = seq[0] if idx > 0 and seq[0] != v else 0
            # count run length from here
            run_len = 1
            j = idx
            while j + 1 < len(seq) and seq[j + 1] == v:
                run_len += 1
                j += 1
            t = "times" if run_len > 1 else "time"
            issues.append((idx, f"number {v} is repeated {run_len} {t} after number {pred}"))
        else:
            seen.add(v)

        # 2) Missing: jumped past some values
        if v > prev_expected:
            for m in range(prev_expected, v):
                if m not in reported_missing:
                    issues.append((idx, f"number {m} is missing"))
                    reported_missing.add(m)
            prev_expected = v + 1

        # 3) Exact hit
        elif v == prev_expected:
            prev_expected += 1

        # 4) Below expectation → swap or out-of-place
        else:  # v < prev_expected
            if idx > 0 and abs(seq[idx - 1] - v) == 1 and v < seq[idx - 1]:
                a, b = min(v, seq[idx - 1]), max(v, seq[idx - 1])
                issues.append((idx, f"number {a} is switched in place with number {b}"))
                issues.append((idx, f"number {b} is switched in place with number {a}"))
            else:
                issues.append((idx, f"number {v} is out of place after number {seq[idx - 1]}"))
            prev_expected = v + 1

    # tail missing
    for m in range(prev_expected, end + 1):
        if m not in reported_missing:
            issues.append((len(seq), f"number {m} is missing"))

    issues.sort(key=lambda x: x[0])
    return [msg for _, msg in issues]
