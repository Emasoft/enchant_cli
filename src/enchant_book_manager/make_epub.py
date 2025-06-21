#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
# - Fixed missing import of epub_db module (removed fallback to non-existent module)
# - Removed unused variables: has_parts (line 494) and has_letter_suffix (lines 497-500)
# - Extracted shared constants and utilities to epub_constants.py to avoid duplication
# - Added DB_OPTIMIZATION_THRESHOLD constant instead of magic number
# - Simplified database fallback logic
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

import argparse
import html
import json
import os
import re
import shutil
import sys
import tempfile
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
import xml.etree.ElementTree as ET

# Import shared constants and utilities
from .epub_constants import (
    ENCODING,
    MIMETYPE,
    WORD_NUMS,
    FILENAME_RE,
    parse_num as parse_num_shared,
)

# Import database module for fast chapter indexing
try:
    from .epub_db_optimized import process_text_optimized

    DB_OPTIMIZED = True
except ImportError:
    # Database optimization not available
    DB_OPTIMIZED = False

# Import enhanced TOC builder
try:
    from .epub_toc_enhanced import build_enhanced_toc_ncx

    TOC_ENHANCED = True
except ImportError:
    TOC_ENHANCED = False


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
def parse_num(raw: Optional[str]) -> Optional[int]:
    """Wrapper for shared parse_num function."""
    if raw is None:
        return None
    return parse_num_shared(raw)


# ──────────────────────────── logging ──────────────────────────── #


def _log_path() -> Path:
    """
    Generate log file path with timestamp.

    Returns:
        Path object for error log file
    """
    return Path.cwd() / f"errors_{datetime.now():%Y%m%d_%H%M%S}.log"


_ERROR_LOG: Optional[Path] = None
_JSON_LOG: Optional[Path] = None


def log_issue(msg: str, obj: Optional[Dict[str, Any]] = None) -> None:
    """
    Append msg (and obj if requested) to per-run log files.

    Creates log files with timestamp if they don't exist.

    Args:
        msg: Message to log
        obj: Optional object to log as JSON
    """
    global _ERROR_LOG
    if _ERROR_LOG is None:
        _ERROR_LOG = _log_path()
    with _ERROR_LOG.open("a", encoding=ENCODING) as fh:
        fh.write(f"[{datetime.now().isoformat()}] {msg}\n")
    if _JSON_LOG and obj is not None:
        with _JSON_LOG.open("a", encoding=ENCODING) as jf:
            jf.write(json.dumps(obj, ensure_ascii=False) + "\n")


# ─────────────────── anomaly detector (updated) ─────────────────── #


def detect_issues(seq: List[int]) -> List[str]:
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


# ─────────────────── split text & collapse dup headings ─────────────────── #


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


def split_text_db(text: str, detect_headings: bool) -> Tuple[List[Tuple[str, str]], List[int]]:
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
        log_issue(f"Database processing failed: {e}")
        return split_text(text, detect_headings, force_no_db=True)


def split_text(text: str, detect_headings: bool, force_no_db: bool = False) -> Tuple[List[Tuple[str, str]], List[int]]:
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
    DB_OPTIMIZATION_THRESHOLD = 100000  # Number of lines before using database
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
    raw_chapters: List[Tuple[str, str, Optional[int]]] = []
    seq = []
    buf = []
    cur_title = None
    cur_num = None  # Track the current chapter's number
    front_done = False
    last_num: Optional[int] = None
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
            if "chapter" in line.lower() and not is_valid_chapter_line(line):
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
    chapter_groups: Dict[int, List[Tuple[str, str, Optional[int]]]] = {}
    chapter_index: Dict[Tuple[Optional[int], str], int] = {}  # Map (num, title) to index for O(1) lookup

    # Group chapters by their number and build index
    for idx, (title, content, num) in enumerate(raw_chapters):
        if num is not None:
            if num not in chapter_groups:
                chapter_groups[num] = []
            chapter_groups[num].append((title, content, num))
            chapter_index[(num, title)] = idx

    # Analyze each group to determine if sub-numbering is needed
    needs_subnumbering: Dict[int, bool] = {}

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
                chapter_idx: Optional[int] = chapter_index.get((num, title))
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
    part_counters: Dict[int, int] = {}

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


# ───────────── plain text → XHTML ───────────── #


def paragraphize(txt: str) -> str:
    """
    Convert plain text to HTML paragraphs.

    Groups lines into paragraphs, preserving line breaks within paragraphs.
    Empty lines separate paragraphs.

    Args:
        txt: Plain text to convert

    Returns:
        HTML with paragraph tags
    """
    out, buf = [], []
    for ln in txt.splitlines():
        if ln.rstrip():
            buf.append(html.escape(ln.rstrip()))
        elif buf:
            out.append("<p>" + "<br/>".join(buf) + "</p>")
            buf.clear()
    if buf:
        out.append("<p>" + "<br/>".join(buf) + "</p>")
    return "\n".join(out)


# ───────────── XHTML / EPUB fragment builders ───────────── #


def build_chap_xhtml(title: str, body_html: str) -> str:
    """
    Build chapter XHTML using ElementTree for proper XML handling.

    Creates valid XHTML with proper namespace handling and escaping.

    Args:
        title: Chapter title
        body_html: HTML content for chapter body

    Returns:
        Complete XHTML document as string
    """
    # Register XHTML namespace
    ET.register_namespace("", "http://www.w3.org/1999/xhtml")

    # Create root element
    html = ET.Element("{http://www.w3.org/1999/xhtml}html")

    # Head section
    head = ET.SubElement(html, "{http://www.w3.org/1999/xhtml}head")
    title_elem = ET.SubElement(head, "{http://www.w3.org/1999/xhtml}title")
    title_elem.text = title

    link = ET.SubElement(head, "{http://www.w3.org/1999/xhtml}link")
    link.set("href", "../Styles/style.css")
    link.set("rel", "stylesheet")
    link.set("type", "text/css")

    # Body section
    body = ET.SubElement(html, "{http://www.w3.org/1999/xhtml}body")
    h1 = ET.SubElement(body, "{http://www.w3.org/1999/xhtml}h1")
    h1.text = title

    # Parse body HTML and append
    # We need to wrap in a div to parse the HTML fragments
    try:
        wrapped = f'<div xmlns="http://www.w3.org/1999/xhtml">{body_html}</div>'
        body_content = ET.fromstring(wrapped)
        # Move all children from wrapper to body
        for child in body_content:
            body.append(child)
    except (ET.ParseError, Exception):
        # Fallback: create a single paragraph with escaped content
        p = ET.SubElement(body, "{http://www.w3.org/1999/xhtml}p")
        # Strip any HTML tags and use plain text
        import re

        plain_text = re.sub(r"<[^>]+>", "", body_html)
        p.text = plain_text or "[Content could not be parsed]"

    # Generate string with XML declaration and DOCTYPE
    tree = ET.ElementTree(html)
    from io import StringIO

    output = StringIO()
    tree.write(output, encoding="unicode", method="xml")

    # Add XML declaration and DOCTYPE manually
    result = '<?xml version="1.0" encoding="utf-8"?>\n'
    result += "<!DOCTYPE html>\n"
    result += output.getvalue()

    return result


def build_cover_xhtml(img_rel: str) -> str:
    """
    Build cover XHTML using ElementTree.

    Creates minimal cover page with centered image.

    Args:
        img_rel: Relative path to cover image

    Returns:
        Complete XHTML document for cover page
    """
    # Register XHTML namespace
    ET.register_namespace("", "http://www.w3.org/1999/xhtml")

    # Create root element
    html = ET.Element("{http://www.w3.org/1999/xhtml}html")

    # Head section
    head = ET.SubElement(html, "{http://www.w3.org/1999/xhtml}head")
    title_elem = ET.SubElement(head, "{http://www.w3.org/1999/xhtml}title")
    title_elem.text = "Cover"

    style = ET.SubElement(head, "{http://www.w3.org/1999/xhtml}style")
    style.text = "html,body{margin:0;padding:0}img{max-width:100%;height:auto;display:block;margin:0 auto}"

    # Body section
    body = ET.SubElement(html, "{http://www.w3.org/1999/xhtml}body")
    img = ET.SubElement(body, "{http://www.w3.org/1999/xhtml}img")
    img.set("src", f"../{img_rel}")
    img.set("alt", "Cover")

    # Generate string
    tree = ET.ElementTree(html)
    from io import StringIO

    output = StringIO()
    tree.write(output, encoding="unicode", method="xml")

    # Add XML declaration and DOCTYPE
    result = '<?xml version="1.0" encoding="utf-8"?>\n'
    result += "<!DOCTYPE html>\n"
    result += output.getvalue()

    return result


def build_container_xml() -> str:
    """
    Build container.xml using ElementTree.

    Creates the EPUB container XML that points to the OPF file.

    Returns:
        Container XML as string
    """
    # Register namespace
    container_ns = "urn:oasis:names:tc:opendocument:xmlns:container"
    ET.register_namespace("", container_ns)

    # Create container element
    container = ET.Element(f"{{{container_ns}}}container", version="1.0")

    # Add rootfiles
    rootfiles = ET.SubElement(container, f"{{{container_ns}}}rootfiles")
    rootfile = ET.SubElement(rootfiles, f"{{{container_ns}}}rootfile")
    rootfile.set("full-path", "OEBPS/content.opf")
    rootfile.set("media-type", "application/oebps-package+xml")

    # Generate string
    return ET.tostring(container, encoding="unicode", method="xml", xml_declaration=True)


def build_style_css(custom_css: Optional[str] = None) -> str:
    """Build CSS content, using custom CSS if provided."""
    if custom_css:
        return custom_css
    # Default CSS
    return "body{font-family:serif;line-height:1.4;margin:5%}" "h1{text-align:center;margin:2em 0 1em}" "p{text-indent:1.5em;margin:0 0 1em}" "img{max-width:100%;height:auto}"


def build_content_opf(
    title: str,
    author: str,
    manifest: List[str],
    spine: List[str],
    uid: str,
    cover_id: Optional[str],
    language: str = "en",
    metadata: Optional[Dict[str, Any]] = None,
) -> str:
    """Build OPF content with support for language and additional metadata."""
    date = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    meta_cover = f"\n    <meta name='cover' content='{cover_id}'/>" if cover_id else ""

    # Build additional metadata
    extra_meta = ""
    if metadata:
        if metadata.get("publisher"):
            extra_meta += f"\n    <dc:publisher>{html.escape(metadata['publisher'])}</dc:publisher>"
        if metadata.get("description"):
            extra_meta += f"\n    <dc:description>{html.escape(metadata['description'])}</dc:description>"
        if metadata.get("series"):
            extra_meta += f"\n    <meta name='calibre:series' content='{html.escape(metadata['series'])}'/>"
        if metadata.get("series_index"):
            extra_meta += f"\n    <meta name='calibre:series_index' content='{metadata['series_index']}'/>"

    return f"""<?xml version='1.0' encoding='utf-8'?>
<package xmlns='http://www.idpf.org/2007/opf' unique-identifier='BookID' version='2.0'>
  <metadata xmlns:dc='http://purl.org/dc/elements/1.1/' xmlns:opf='http://www.idpf.org/2007/opf'>
    <dc:title>{html.escape(title)}</dc:title>
    <dc:creator opf:role='aut'>{html.escape(author)}</dc:creator>
    <dc:language>{html.escape(language)}</dc:language>
    <dc:identifier id='BookID'>urn:uuid:{uid}</dc:identifier>
    <dc:date>{date}</dc:date>{meta_cover}{extra_meta}
  </metadata>
  <manifest>
        {"\n        ".join(manifest)}
  </manifest>
  <spine toc='ncx'>
        {"\n        ".join(spine)}
  </spine>
</package>""".strip()


def build_toc_ncx(title: str, author: str, nav_points: List[str], uid: str) -> str:
    return f"""<?xml version='1.0' encoding='utf-8'?>
<!DOCTYPE ncx PUBLIC '-//NISO//DTD ncx 2005-1//EN' 'http://www.daisy.org/z3986/2005/ncx-2005-1.dtd'>
<ncx xmlns='http://www.daisy.org/z3986/2005/ncx/' version='2005-1'><head>
  <meta name='dtb:uid' content='urn:uuid:{uid}'/><meta name='dtb:depth' content='1'/>
  <meta name='dtb:totalPageCount' content='0'/><meta name='dtb:maxPageNumber' content='0'/></head>
<docTitle><text>{html.escape(title)}</text></docTitle>
<docAuthor><text>{html.escape(author)}</text></docAuthor>
<navMap>
    {"\n    ".join(nav_points)}
</navMap></ncx>""".strip()


# ───────────── retry-loop filesystem helpers ───────────── #


class ValidationError(Exception): ...


def ensure_dir_readable(p: Path) -> None:
    """
    Ensure directory is readable.

    Checks existence, directory status, and read permissions.

    Args:
        p: Path to directory

    Raises:
        ValidationError: If directory is not readable
    """
    if not p.exists() or not p.is_dir():
        raise ValidationError(f"Directory '{p}' not found or not a directory.")
    if not os.access(p, os.R_OK):
        raise ValidationError(f"No read permission for '{p}'.")
    try:
        list(p.iterdir())
    except OSError as e:
        raise ValidationError(f"Cannot read directory '{p}': {e}")


def ensure_output_ok(path: Path, append: bool) -> None:
    """
    Ensure output path is writable.

    Checks write permissions and handles append vs overwrite scenarios.

    Args:
        path: Output file path
        append: Whether appending to existing file

    Raises:
        ValidationError: If output path is not writable
    """
    if append:
        if path.suffix.lower() != ".epub" or not (path.exists() and os.access(path, os.W_OK)):
            raise ValidationError(f"Cannot write EPUB '{path}'.")
    else:
        target = path.parent if path.suffix.lower() == ".epub" else path
        try:
            target.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            raise ValidationError(f"Cannot create directory '{target}': {e}")
        if not os.access(target, os.W_OK):
            raise ValidationError(f"No write permission for '{target}'.")


def ensure_cover_ok(p: Path) -> None:
    """Ensure cover file is valid. Raises ValidationError if not."""
    if not p.is_file():
        raise ValidationError(f"Cover '{p}' is not a file.")
    if p.suffix.lower() not in {".jpg", ".jpeg", ".png"}:
        raise ValidationError("Cover must be .jpg/.jpeg/.png.")
    if not os.access(p, os.R_OK):
        raise ValidationError(f"No read permission for '{p}'.")


def collect_chunks(folder: Path) -> Dict[int, Path]:
    """Collect chapter chunks from folder. Raises ValidationError if none found."""
    mapping: Dict[int, Path] = {}
    issues: List[str] = []

    for f in folder.glob("*.txt"):
        try:
            if f.is_symlink() and not f.resolve().exists():
                issues.append(f"Broken symlink: {f}")
                continue
            m = FILENAME_RE.match(f.name)
            if not m:
                issues.append(f"Malformed filename: {f.name}")
                continue
            idx = int(m.group("num"))
            if f.stat().st_size == 0:
                issues.append(f"Empty file: {f.name}")
                continue
            mapping[idx] = f
        except OSError as e:
            issues.append(f"OS error on {f}: {e}")

    if not mapping:
        error_msg = "No valid .txt chunks found."
        if issues:
            error_msg += f" Issues: {'; '.join(issues[:3])}"
            if len(issues) > 3:
                error_msg += f" ... and {len(issues) - 3} more"
        raise ValidationError(error_msg)

    # Log issues but don't fail
    for msg in issues:
        log_issue(msg)

    return mapping


# ───────────── EPUB creation helpers ───────────── #


def write_new_epub(
    chaps: List[Tuple[str, str]],
    out: Path,
    title: str,
    author: str,
    cover: Optional[Path],
    language: str = "en",
    custom_css: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    uid = str(uuid.uuid4())
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        (tmp / "META-INF").mkdir()
        oebps = tmp / "OEBPS"
        (oebps / "Text").mkdir(parents=True)
        (oebps / "Styles").mkdir()
        if cover:
            (oebps / "Images").mkdir()

        (tmp / "META-INF" / "container.xml").write_text(build_container_xml(), ENCODING)
        (oebps / "Styles" / "style.css").write_text(build_style_css(custom_css), ENCODING)

        manifest = [
            "<item id='ncx' href='toc.ncx' media-type='application/x-dtbncx+xml'/>",
            "<item id='css' href='Styles/style.css' media-type='text/css'/>",
        ]
        spine, nav = [], []
        cover_id = None

        if cover:
            cover_id = "cover-img"
            img_rel = f"Images/{cover.name}"
            shutil.copy2(cover, oebps / img_rel)
            mime = "image/jpeg" if cover.suffix.lower() in {".jpg", ".jpeg"} else "image/png"
            manifest.append(f"<item id='{cover_id}' href='{img_rel}' media-type='{mime}'/>")
            (oebps / "Text" / "cover.xhtml").write_text(build_cover_xhtml(img_rel), ENCODING)
            manifest.append("<item id='coverpage' href='Text/cover.xhtml' media-type='application/xhtml+xml'/>")
            spine.append("<itemref idref='coverpage' linear='yes'/>")

        for idx, (title_, body_html) in enumerate(chaps, 1):
            xhtml = f"Text/chapter{idx}.xhtml"
            (oebps / xhtml).write_text(build_chap_xhtml(title_, body_html), ENCODING)
            manifest.append(f"<item id='chap{idx}' href='{xhtml}' media-type='application/xhtml+xml'/>")
            spine.append(f"<itemref idref='chap{idx}'/>")
            nav.append(f"<navPoint id='nav{idx}' playOrder='{idx}'><navLabel><text>{html.escape(title_)}</text></navLabel><content src='{xhtml}'/></navPoint>")

        (oebps / "content.opf").write_text(
            build_content_opf(title, author, manifest, spine, uid, cover_id, language, metadata),
            ENCODING,
        )

        # Use enhanced TOC builder if available
        if TOC_ENHANCED:
            # Pass full chapter data for hierarchical analysis
            toc_content = build_enhanced_toc_ncx(chaps, title, author, uid, hierarchical=True)
            (oebps / "toc.ncx").write_text(toc_content, ENCODING)
        else:
            (oebps / "toc.ncx").write_text(build_toc_ncx(title, author, nav, uid), ENCODING)

        with zipfile.ZipFile(out, "w") as z:
            z.writestr("mimetype", MIMETYPE, zipfile.ZIP_STORED)
            for root, _, files in os.walk(tmp):
                for f in files:
                    fp = Path(root) / f
                    rel = fp.relative_to(tmp).as_posix()
                    if rel == "mimetype":
                        continue
                    z.write(fp, rel, zipfile.ZIP_DEFLATED)


def extend_epub(epub: Path, new: List[Tuple[str, str]]) -> None:
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        with zipfile.ZipFile(epub) as z:
            z.extractall(tmp)

        oebps = tmp / "OEBPS"
        textdir = oebps / "Text"
        next_idx = 1 + max(
            (int(m.group(1)) for p in textdir.glob("chapter*.xhtml") if (m := re.search(r"chapter(\d+)\.xhtml", p.name))),
            default=0,
        )

        ns_opf = {"opf": "http://www.idpf.org/2007/opf"}
        ns_ncx = {"ncx": "http://www.daisy.org/z3986/2005/ncx/"}
        opf = ET.parse(oebps / "content.opf")
        manifest = opf.find("opf:manifest", ns_opf)
        spine = opf.find("opf:spine", ns_opf)
        ncx = ET.parse(oebps / "toc.ncx")
        navmap = ncx.find("ncx:navMap", ns_ncx)

        if manifest is None or spine is None or navmap is None:
            raise ValueError("Invalid EPUB structure: missing manifest, spine, or navMap")

        play = max(
            (int(n.get("playOrder", "0")) for n in navmap.findall("ncx:navPoint", ns_ncx)),
            default=0,
        )

        for title_, body_html in new:
            xhtml = f"Text/chapter{next_idx}.xhtml"
            (oebps / xhtml).write_text(build_chap_xhtml(title_, body_html), ENCODING)
            ET.SubElement(
                manifest,
                "{http://www.idpf.org/2007/opf}item",
                {
                    "id": f"chap{next_idx}",
                    "href": xhtml,
                    "media-type": "application/xhtml+xml",
                },
            )
            ET.SubElement(
                spine,
                "{http://www.idpf.org/2007/opf}itemref",
                {"idref": f"chap{next_idx}"},
            )
            play += 1
            np = ET.SubElement(
                navmap,
                "{http://www.daisy.org/z3986/2005/ncx/}navPoint",
                {"id": f"nav{next_idx}", "playOrder": str(play)},
            )
            nl = ET.SubElement(np, "{http://www.daisy.org/z3986/2005/ncx/}navLabel")
            ET.SubElement(nl, "{http://www.daisy.org/z3986/2005/ncx/}text").text = title_
            ET.SubElement(np, "{http://www.daisy.org/z3986/2005/ncx/}content", {"src": xhtml})
            next_idx += 1

        opf.write(oebps / "content.opf", ENCODING, xml_declaration=True)
        ncx.write(oebps / "toc.ncx", ENCODING, xml_declaration=True)

        tmp_epub = epub.with_suffix(".tmp.epub")
        with zipfile.ZipFile(tmp_epub, "w") as z:
            z.writestr("mimetype", MIMETYPE, zipfile.ZIP_STORED)
            for root, _, files in os.walk(tmp):
                for f in files:
                    fp = Path(root) / f
                    rel = fp.relative_to(tmp).as_posix()
                    if rel == "mimetype":
                        continue
                    z.write(fp, rel, zipfile.ZIP_DEFLATED)
        shutil.move(tmp_epub, epub)


# ───────────────────────── Module API ─────────────────────────


def create_epub_from_chapters(
    chapters: List[Tuple[str, str]],
    output_path: Path,
    title: str,
    author: str,
    cover_path: Optional[Path] = None,
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
    cover_path: Optional[Path] = None,
    generate_toc: bool = True,
    validate: bool = True,
    strict_mode: bool = False,
    language: str = "en",
    custom_css: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Tuple[bool, List[str]]:
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
        raise ValidationError(f"Error reading input file: {e}")

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
    title: Optional[str] = None,
    author: Optional[str] = None,
    cover_path: Optional[Path] = None,
    detect_headings: bool = True,
    validate_only: bool = False,
    strict: bool = True,
) -> List[str]:
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


def parse_add(val: str) -> Tuple[int, bool]:
    m = re.fullmatch(r"(\d+)(\+)?", val)
    if not m:
        raise argparse.ArgumentTypeError("--add must be N or N+")
    return int(m.group(1)), bool(m.group(2))


def main() -> None:
    ap = argparse.ArgumentParser(description="TXT chunks → EPUB builder / validator")
    ap.add_argument("input_dir", type=Path, help="Directory with .txt chunks")
    ap.add_argument("-o", "--output", type=Path, required=True, help="Output directory or .epub")
    ap.add_argument("--title", help="Override book title")
    ap.add_argument("--author", help="Override author")
    ap.add_argument("--toc", action="store_true", help="Detect chapter headings and build TOC")
    ap.add_argument("--cover", type=Path, help="Cover image (jpg/png)")
    ap.add_argument(
        "--add",
        type=parse_add,
        metavar="N[+]",
        help="Append chunk N (or N+) to existing EPUB",
    )
    ap.add_argument("--validate-only", action="store_true", help="Only scan & report issues")
    ap.add_argument("--no-strict", action="store_true", help="Soft mode (don't abort on issues)")
    ap.add_argument("--json-log", type=Path, help="Write JSON-lines issue log")
    args = ap.parse_args()

    global _JSON_LOG
    _JSON_LOG = args.json_log

    append = args.add is not None
    add_start, add_plus = args.add if append else (None, False)

    ensure_dir_readable(args.input_dir)
    ensure_output_ok(args.output, append)
    if args.cover:
        if append:
            sys.exit("--cover only valid when creating a new EPUB.")
        ensure_cover_ok(args.cover)

    chunks = collect_chunks(args.input_dir)

    selected = {n: p for n, p in chunks.items() if add_start is not None and (n == add_start or (add_plus and n >= add_start))} if append else chunks
    if append and not selected:
        sys.exit(f"No chunks ≥ {add_start} found.")

    full_text = "\n".join(selected[i].read_text(ENCODING) for i in sorted(selected))
    chap_blocks, seq = split_text(full_text, args.toc)
    chapters = [(t, paragraphize(b)) for t, b in chap_blocks]
    msgs = detect_issues(seq)
    for m in msgs:
        log_issue(m, {"msg": m})

    if args.validate_only:
        print("✅ no issues" if not msgs else f"⚠ {len(msgs)} issue(s) – see {_ERROR_LOG}")
        sys.exit(1 if msgs else 0)

    if msgs and not args.no_strict:
        print(f"❌ {len(msgs)} issue(s) – aborting (strict mode).")
        sys.exit(2)

    if append:
        extend_epub(args.output, chapters)
        result = f"Appended {len(chapters)} chapter(s) to '{args.output}'."
    else:
        first = chunks[min(chunks)]
        def_title, def_author = ("Untitled", "Unknown")
        match = FILENAME_RE.match(first.name)
        if match:
            def_title, def_author = match.group("title"), match.group("author")
        title = args.title or def_title
        author = args.author or def_author
        safe = re.sub(r"[^A-Za-z0-9_]+", "_", title).strip("_") or "book"
        epub_path = args.output if args.output.suffix.lower() == ".epub" else args.output / f"{safe}.epub"
        write_new_epub(chapters, epub_path, title, author, args.cover)
        result = f"EPUB created at: {epub_path}"

    summary = "✅ validation clean" if not msgs else f"⚠ {len(msgs)} issue(s) – see {_ERROR_LOG}"
    print(f"{result}  {summary}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nCancelled by user.")
