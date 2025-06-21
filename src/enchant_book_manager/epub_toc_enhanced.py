#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
# - Initial implementation of enhanced TOC builder
# - Added hierarchical TOC support (Parts -> Books -> Sections -> Chapters)
# - Added proper XML escaping for special characters
# - Added EPUB3 navigation document support
# - Added backward compatibility with flat TOC structure
#

"""
Enhanced TOC generation for EPUB files.
Supports hierarchical structure and better chapter organization.
"""

from __future__ import annotations

import re
import html
from typing import List, Tuple, Optional
from dataclasses import dataclass, field


@dataclass
class TocEntry:
    """Represents a single TOC entry with support for nesting"""

    title: str
    href: str
    play_order: int
    level: int = 1
    children: List[TocEntry] = field(default_factory=list)

    def to_ncx_navpoint(self, depth: int = 0) -> str:
        """Convert to NCX navPoint XML"""
        indent = "  " * depth
        nav_id = f"nav{self.play_order}"

        result = f'{indent}<navPoint id="{nav_id}" playOrder="{self.play_order}">\n'
        result += f"{indent}  <navLabel><text>{html.escape(self.title)}</text></navLabel>\n"
        result += f'{indent}  <content src="{self.href}"/>\n'

        # Add children
        for child in self.children:
            result += child.to_ncx_navpoint(depth + 1)

        result += f"{indent}</navPoint>\n"
        return result

    def to_nav_li(self, depth: int = 0) -> str:
        """Convert to EPUB3 nav HTML list item"""
        indent = "  " * depth
        result = f'{indent}<li><a href="{self.href}">{html.escape(self.title)}</a>'

        if self.children:
            result += f"\n{indent}  <ol>\n"
            for child in self.children:
                result += child.to_nav_li(depth + 2)
            result += f"{indent}  </ol>\n{indent}"

        result += "</li>\n"
        return result


class EnhancedTocBuilder:
    """Build enhanced table of contents with hierarchical support"""

    def __init__(self) -> None:
        self.entries: List[TocEntry] = []
        self.play_order = 1

    def analyze_chapters(self, chapters: List[Tuple[str, str]]) -> List[TocEntry]:
        """
        Analyze chapters and build hierarchical TOC structure.
        Detects parts, books, sections, and regular chapters.
        """
        toc_entries = []
        current_part: Optional[TocEntry] = None
        current_book: Optional[TocEntry] = None

        # Patterns for different levels
        part_pattern = re.compile(r"^Part\s+(\w+)(?:\s*[:\-–—]\s*(.+))?", re.IGNORECASE)
        book_pattern = re.compile(r"^Book\s+(\w+)(?:\s*[:\-–—]\s*(.+))?", re.IGNORECASE)
        section_pattern = re.compile(r"^Section\s+(\w+)(?:\s*[:\-–—]\s*(.+))?", re.IGNORECASE)

        for idx, (title, _content) in enumerate(chapters, 1):
            href = f"Text/chapter{idx}.xhtml"

            # Check for part
            part_match = part_pattern.match(title)
            if part_match:
                current_part = TocEntry(title=title, href=href, play_order=self.play_order, level=1)
                self.play_order += 1
                toc_entries.append(current_part)
                current_book = None  # Reset book when new part starts
                continue

            # Check for book
            book_match = book_pattern.match(title)
            if book_match:
                current_book = TocEntry(title=title, href=href, play_order=self.play_order, level=2)
                self.play_order += 1

                if current_part:
                    current_part.children.append(current_book)
                else:
                    toc_entries.append(current_book)
                continue

            # Check for section
            section_match = section_pattern.match(title)
            if section_match:
                section_entry = TocEntry(title=title, href=href, play_order=self.play_order, level=3)
                self.play_order += 1

                if current_book:
                    current_book.children.append(section_entry)
                elif current_part:
                    current_part.children.append(section_entry)
                else:
                    toc_entries.append(section_entry)
                continue

            # Regular chapter
            chapter_entry = TocEntry(title=title, href=href, play_order=self.play_order, level=4)
            self.play_order += 1

            # Add to appropriate parent
            if current_book:
                current_book.children.append(chapter_entry)
            elif current_part:
                current_part.children.append(chapter_entry)
            else:
                toc_entries.append(chapter_entry)

        return toc_entries

    def build_ncx_toc(self, chapters: List[Tuple[str, str]], title: str, author: str, uid: str) -> str:
        """Build NCX format TOC with hierarchical structure"""
        toc_entries = self.analyze_chapters(chapters)

        # Calculate max depth
        max_depth = self._calculate_max_depth(toc_entries)

        nav_map_content = ""
        for entry in toc_entries:
            nav_map_content += entry.to_ncx_navpoint(1)

        return f"""<?xml version='1.0' encoding='utf-8'?>
<!DOCTYPE ncx PUBLIC '-//NISO//DTD ncx 2005-1//EN' 'http://www.daisy.org/z3986/2005/ncx-2005-1.dtd'>
<ncx xmlns='http://www.daisy.org/z3986/2005/ncx/' version='2005-1'>
<head>
  <meta name='dtb:uid' content='urn:uuid:{uid}'/>
  <meta name='dtb:depth' content='{max_depth}'/>
  <meta name='dtb:totalPageCount' content='0'/>
  <meta name='dtb:maxPageNumber' content='0'/>
</head>
<docTitle><text>{html.escape(title)}</text></docTitle>
<docAuthor><text>{html.escape(author)}</text></docAuthor>
<navMap>
{nav_map_content}</navMap>
</ncx>""".strip()

    def build_nav_xhtml(self, chapters: List[Tuple[str, str]], title: str) -> str:
        """Build EPUB3 navigation document with hierarchical structure"""
        toc_entries = self.analyze_chapters(chapters)

        nav_content = ""
        for entry in toc_entries:
            nav_content += entry.to_nav_li(2)

        return f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<head>
  <title>{html.escape(title)} - Navigation</title>
  <meta charset="utf-8"/>
</head>
<body>
  <nav epub:type="toc" id="toc">
    <h1>Table of Contents</h1>
    <ol>
{nav_content}    </ol>
  </nav>
</body>
</html>"""

    def _calculate_max_depth(self, entries: List[TocEntry], current_depth: int = 1) -> int:
        """Calculate maximum depth of TOC hierarchy"""
        max_depth = current_depth

        for entry in entries:
            if entry.children:
                child_depth = self._calculate_max_depth(entry.children, current_depth + 1)
                max_depth = max(max_depth, child_depth)

        return max_depth

    def get_flat_nav_points(self, chapters: List[Tuple[str, str]]) -> List[str]:
        """
        Get flat navigation points for backward compatibility.
        This is used when hierarchical TOC is not needed.
        """
        nav_points = []
        for idx, (title, _) in enumerate(chapters, 1):
            nav_points.append(f'<navPoint id="nav{idx}" playOrder="{idx}">' f"<navLabel><text>{html.escape(title)}</text></navLabel>" f'<content src="Text/chapter{idx}.xhtml"/>' f"</navPoint>")
        return nav_points


def build_enhanced_toc_ncx(
    chapters: List[Tuple[str, str]],
    title: str,
    author: str,
    uid: str,
    hierarchical: bool = True,
) -> str:
    """
    Build TOC in NCX format with optional hierarchical structure.

    Args:
        chapters: List of (title, content) tuples
        title: Book title
        author: Book author
        uid: Unique identifier
        hierarchical: Whether to build hierarchical TOC (default: True)

    Returns:
        NCX formatted TOC string
    """
    builder = EnhancedTocBuilder()

    if hierarchical:
        return builder.build_ncx_toc(chapters, title, author, uid)
    else:
        # Fallback to flat structure for compatibility
        nav_points = builder.get_flat_nav_points(chapters)
        return f"""<?xml version='1.0' encoding='utf-8'?>
<!DOCTYPE ncx PUBLIC '-//NISO//DTD ncx 2005-1//EN' 'http://www.daisy.org/z3986/2005/ncx-2005-1.dtd'>
<ncx xmlns='http://www.daisy.org/z3986/2005/ncx/' version='2005-1'>
<head>
  <meta name='dtb:uid' content='urn:uuid:{uid}'/>
  <meta name='dtb:depth' content='1'/>
  <meta name='dtb:totalPageCount' content='0'/>
  <meta name='dtb:maxPageNumber' content='0'/>
</head>
<docTitle><text>{html.escape(title)}</text></docTitle>
<docAuthor><text>{html.escape(author)}</text></docAuthor>
<navMap>
  {"  ".join(nav_points)}
</navMap>
</ncx>""".strip()
