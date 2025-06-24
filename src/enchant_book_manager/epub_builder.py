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
# - Extracted shared constants and utilities to epub_constants.py to avoid duplication with make_epub.py
# - Removed duplicated conversion tables and functions (roman_to_int, words_to_int, parse_num)
# - Now imports shared utilities from epub_constants module
#

"""
epub_builder.py - Module for building EPUB files from translated novel chapters
"""

import re
import html
import tempfile
import zipfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
import logging

# Import shared constants and utilities
from .epub_constants import (
    ENCODING,
    MIMETYPE,
    WORD_NUMS,
    FILENAME_RE,
    roman_to_int,
    words_to_int,
)

HEADING_RE = re.compile(
    rf"^[^\w]*\s*chapter\s+" rf"(?:(?P<num_d>\d+)|(?P<num_r>[ivxlcdm]+)|" rf"(?P<num_w>(?:{WORD_NUMS})(?:[-\s](?:{WORD_NUMS}))*))" rf"\b(?P<rest>.*)$",
    re.IGNORECASE,
)


def detect_chapter_issues(seq: list[int]) -> list[tuple[int, str]]:
    """
    Detect issues in chapter sequence (missing, out of order, duplicates).
    Returns list of (position, issue_description) tuples.
    """
    issues: list[tuple[int, str]] = []
    if not seq:
        return issues

    start, end = seq[0], seq[-1]
    prev_expected = start
    seen = set()
    reported_missing = set()

    for idx, v in enumerate(seq):
        # Check for repeats
        if v in seen:
            # Find nearest non-identical predecessor
            pred = None
            for x in reversed(seq[:idx]):
                if x != v:
                    pred = x
                    break
            if pred is not None:
                # Count run length
                run_len = 1
                j = idx
                while j + 1 < len(seq) and seq[j + 1] == v:
                    run_len += 1
                    j += 1
                t = "times" if run_len > 1 else "time"
                issues.append((idx, f"Chapter {v} is repeated {run_len} {t} after Chapter {pred}"))
        else:
            seen.add(v)

        # Check for missing chapters
        if v > prev_expected:
            for m in range(prev_expected + 1, v):
                if m not in reported_missing:
                    issues.append((idx, f"Chapter {m} is missing"))
                    reported_missing.add(m)
            prev_expected = v + 1

        # Exact hit
        elif v == prev_expected:
            prev_expected += 1

        # Out of order
        else:  # v < prev_expected
            if idx > 0 and abs(seq[idx - 1] - v) == 1 and v < seq[idx - 1]:
                a, b = min(v, seq[idx - 1]), max(v, seq[idx - 1])
                issues.append((idx, f"Chapter {a} is switched in place with Chapter {b}"))
                issues.append((idx, f"Chapter {b} is switched in place with Chapter {a}"))
            else:
                issues.append((idx, f"Chapter {v} is out of place after Chapter {seq[idx - 1]}"))
            prev_expected = v + 1

    # Check for missing chapters at the end
    for m in range(prev_expected, end + 1):
        if m not in reported_missing:
            issues.append((len(seq), f"Chapter {m} is missing"))

    issues.sort(key=lambda x: x[0])
    return issues


def split_text(text: str, detect_headings: bool = True) -> tuple[list[tuple[str, str, str]], list[int]]:
    """
    Split text into chapters based on headings.
    Returns: ([(toc_title, original_heading, chapter_text), ...], [chapter_numbers])
    """
    if not detect_headings:
        return [("Full Text", "", text)], []

    chapters = []
    chapter_nums = []
    current_toc_title = None
    current_original_heading = ""
    current_text: list[str] = []

    for line in text.split("\n"):
        # Check if line is a chapter heading
        match = HEADING_RE.match(line.strip())
        if match:
            # Save previous chapter if exists
            if current_toc_title is not None:
                chapters.append(
                    (
                        current_toc_title,
                        current_original_heading,
                        "\n".join(current_text),
                    )
                )

            # Extract chapter number
            if match.group("num_d"):
                num = int(match.group("num_d"))
            elif match.group("num_r"):
                num = roman_to_int(match.group("num_r"))
            elif match.group("num_w"):
                num = words_to_int(match.group("num_w"))
            else:
                num = None

            if num is not None:
                chapter_nums.append(num)
                rest = match.group("rest").strip()
                # Create formatted title for TOC only
                toc_title = f"Chapter {num}" + (f": {rest}" if rest else "")
                current_toc_title = toc_title
                current_original_heading = line.strip()
                # Start new chapter text (without the heading)
                current_text = []
            else:
                # Not a valid chapter heading, add to current text
                if current_text or line.strip():
                    current_text.append(line)
        else:
            # Regular text line
            if current_text or line.strip():
                current_text.append(line)

    # Save last chapter
    if current_toc_title is not None:
        chapters.append((current_toc_title, current_original_heading, "\n".join(current_text)))
    elif current_text:
        # No chapters detected, return full text
        chapters.append(("Full Text", "", "\n".join(current_text)))

    return chapters, chapter_nums


def paragraphize(text: str) -> str:
    """Convert plain text to HTML paragraphs."""
    paragraphs = []
    current = []

    for line in text.split("\n"):
        line = line.strip()
        if line:
            current.append(html.escape(line))
        elif current:
            paragraphs.append("<p>" + " ".join(current) + "</p>")
            current = []

    if current:
        paragraphs.append("<p>" + " ".join(current) + "</p>")

    return "\n".join(paragraphs)


def collect_chapter_files(input_dir: Path) -> dict[int, Path]:
    """Collect chapter files from directory, return {chapter_num: file_path}."""
    chapters = {}

    for file_path in input_dir.glob("*.txt"):
        match = FILENAME_RE.match(file_path.name)
        if match:
            num = int(match.group("num"))
            chapters[num] = file_path

    return chapters


def create_epub_from_chapters(
    chapters: list[tuple[str, str, str]],
    output_path: Path,
    title: str,
    author: str,
    cover_path: Path | None = None,
    language: str = "en",
) -> None:
    """Create EPUB file from chapter list with (toc_title, original_heading, html_content)."""
    book_id = str(uuid.uuid4())

    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)

        # Create directory structure
        (tmppath / "META-INF").mkdir()
        (tmppath / "OEBPS").mkdir()

        # Write mimetype
        (tmppath / "mimetype").write_text(MIMETYPE, encoding="ascii")

        # Write container.xml
        container_xml = """<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
    <rootfiles>
        <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
    </rootfiles>
</container>"""
        (tmppath / "META-INF" / "container.xml").write_text(container_xml, encoding=ENCODING)

        # Generate spine and manifest items
        manifest_items = []
        spine_items = []

        # Add cover if provided
        if cover_path and cover_path.exists():
            ext = cover_path.suffix.lower()
            mime = "image/jpeg" if ext in [".jpg", ".jpeg"] else "image/png"
            (tmppath / "OEBPS" / "cover.jpg").write_bytes(cover_path.read_bytes())
            manifest_items.append(f'<item id="cover-image" href="cover.jpg" media-type="{mime}"/>')

            # Create cover HTML
            cover_html = """<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
    <title>Cover</title>
    <style type="text/css">
        img { max-width: 100%; }
    </style>
</head>
<body>
    <div><img src="cover.jpg" alt="Cover"/></div>
</body>
</html>"""
            (tmppath / "OEBPS" / "cover.xhtml").write_text(cover_html, encoding=ENCODING)
            manifest_items.append('<item id="cover" href="cover.xhtml" media-type="application/xhtml+xml"/>')
            spine_items.append('<itemref idref="cover"/>')

        # Write chapters
        toc_items = []
        for i, (toc_title, original_heading, chap_html) in enumerate(chapters):
            chap_id = f"chapter{i + 1}"
            chap_file = f"{chap_id}.xhtml"

            # Use original heading if available, otherwise use TOC title
            display_heading = original_heading if original_heading else toc_title

            chap_content = f"""<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
    <title>{html.escape(toc_title)}</title>
</head>
<body>
    <h1>{html.escape(display_heading)}</h1>
    {chap_html}
</body>
</html>"""
            (tmppath / "OEBPS" / chap_file).write_text(chap_content, encoding=ENCODING)

            manifest_items.append(f'<item id="{chap_id}" href="{chap_file}" media-type="application/xhtml+xml"/>')
            spine_items.append(f'<itemref idref="{chap_id}"/>')
            toc_items.append((chap_id, toc_title))

        # Write NCX (table of contents)
        ncx_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
    <head>
        <meta name="dtb:uid" content="{book_id}"/>
        <meta name="dtb:depth" content="1"/>
        <meta name="dtb:totalPageCount" content="0"/>
        <meta name="dtb:maxPageNumber" content="0"/>
    </head>
    <docTitle>
        <text>{html.escape(title)}</text>
    </docTitle>
    <navMap>"""

        for i, (chap_id, chap_title) in enumerate(toc_items):
            ncx_content += f"""
        <navPoint id="navPoint-{i + 1}" playOrder="{i + 1}">
            <navLabel>
                <text>{html.escape(chap_title)}</text>
            </navLabel>
            <content src="{chap_id}.xhtml"/>
        </navPoint>"""

        ncx_content += """
    </navMap>
</ncx>"""
        (tmppath / "OEBPS" / "toc.ncx").write_text(ncx_content, encoding=ENCODING)
        manifest_items.append('<item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>')

        # Write content.opf
        opf_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" unique-identifier="BookId" version="2.0">
    <metadata xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:opf="http://www.idpf.org/2007/opf">
        <dc:identifier id="BookId">{book_id}</dc:identifier>
        <dc:title>{html.escape(title)}</dc:title>
        <dc:creator>{html.escape(author)}</dc:creator>
        <dc:language>{language}</dc:language>
        <dc:date>{datetime.now(timezone.utc).strftime("%Y-%m-%d")}</dc:date>
        <meta name="generator" content="EnChANT"/>
    </metadata>
    <manifest>
        {" ".join(manifest_items)}
    </manifest>
    <spine toc="ncx">
        {" ".join(spine_items)}
    </spine>
</package>"""
        (tmppath / "OEBPS" / "content.opf").write_text(opf_content, encoding=ENCODING)

        # Create EPUB zip
        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
            # mimetype must be first and uncompressed
            zf.write(tmppath / "mimetype", "mimetype", compress_type=zipfile.ZIP_STORED)

            # Add all other files
            for file_path in tmppath.rglob("*"):
                if file_path.is_file() and file_path.name != "mimetype":
                    arc_name = str(file_path.relative_to(tmppath))
                    zf.write(file_path, arc_name)


def build_epub_from_directory(
    input_dir: Path,
    output_path: Path,
    title: str | None = None,
    author: str | None = None,
    cover_path: Path | None = None,
    detect_toc: bool = True,
    strict: bool = True,
    logger: logging.Logger | None = None,
) -> tuple[bool, list[str]]:
    """
    Build EPUB from directory of chapter files.
    Returns: (success, list_of_issues)
    """
    if logger is None:
        logger = logging.getLogger(__name__)

    # Collect chapter files
    chapters_dict = collect_chapter_files(input_dir)
    if not chapters_dict:
        return False, ["No chapter files found in directory"]

    # Read and combine chapters
    full_text = ""
    for num in sorted(chapters_dict.keys()):
        try:
            chapter_text = chapters_dict[num].read_text(encoding=ENCODING)
            full_text += chapter_text + "\n"
        except Exception as e:
            logger.error(f"Error reading chapter {num}: {e}")
            if strict:
                return False, [f"Error reading chapter {num}: {e}"]

    # Split text and detect chapters
    chapter_blocks, chapter_nums = split_text(full_text, detect_toc)
    chapters = [(toc_title, original_heading, paragraphize(text)) for toc_title, original_heading, text in chapter_blocks]

    # Detect issues
    issues = []
    if chapter_nums:
        issue_list = detect_chapter_issues(chapter_nums)
        issues = [msg for _, msg in issue_list]

        if issues:
            for issue in issues:
                logger.warning(f"Chapter issue: {issue}")

            if strict:
                return False, issues

    # Extract default title/author from first file if not provided
    if not title or not author:
        first_file = chapters_dict[min(chapters_dict.keys())]
        match = FILENAME_RE.match(first_file.name)
        if match:
            title = title or match.group("title")
            author = author or match.group("author")
        else:
            title = title or "Unknown Title"
            author = author or "Unknown Author"

    # Create EPUB
    try:
        create_epub_from_chapters(chapters, output_path, title, author, cover_path)
        return True, issues
    except Exception as e:
        logger.error(f"Error creating EPUB: {e}")
        return False, issues + [f"Error creating EPUB: {e}"]
