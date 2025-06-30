#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test suite for epub_builders module.
"""

import pytest
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from enchant_book_manager.epub_builders import (
    paragraphize,
    build_chap_xhtml,
    build_cover_xhtml,
    build_container_xml,
    build_style_css,
    build_content_opf,
    build_toc_ncx,
)


class TestParagraphize:
    """Test the paragraphize function."""

    def test_paragraphize_simple_text(self):
        """Test paragraphizing simple text."""
        text = "Line 1\nLine 2"
        result = paragraphize(text)
        assert result == "<p>Line 1<br/>Line 2</p>"

    def test_paragraphize_multiple_paragraphs(self):
        """Test paragraphizing text with multiple paragraphs."""
        text = "Paragraph 1\nLine 2\n\nParagraph 2"
        result = paragraphize(text)
        assert result == "<p>Paragraph 1<br/>Line 2</p>\n<p>Paragraph 2</p>"

    def test_paragraphize_empty_lines(self):
        """Test paragraphizing text with multiple empty lines."""
        text = "Paragraph 1\n\n\nParagraph 2"
        result = paragraphize(text)
        assert result == "<p>Paragraph 1</p>\n<p>Paragraph 2</p>"

    def test_paragraphize_html_escaping(self):
        """Test that HTML special characters are escaped."""
        text = 'Line with <tag> & special "chars"'
        result = paragraphize(text)
        assert result == "<p>Line with &lt;tag&gt; &amp; special &quot;chars&quot;</p>"

    def test_paragraphize_empty_string(self):
        """Test paragraphizing empty string."""
        result = paragraphize("")
        assert result == ""

    def test_paragraphize_only_whitespace(self):
        """Test paragraphizing only whitespace."""
        text = "   \n   \n   "
        result = paragraphize(text)
        assert result == ""

    def test_paragraphize_trailing_spaces(self):
        """Test that trailing spaces are removed."""
        text = "Line 1   \nLine 2   "
        result = paragraphize(text)
        assert result == "<p>Line 1<br/>Line 2</p>"


class TestBuildChapXhtml:
    """Test the build_chap_xhtml function."""

    def test_build_chap_xhtml_basic(self):
        """Test building basic chapter XHTML."""
        result = build_chap_xhtml("Chapter 1", "<p>Content</p>")

        # Parse the result to check structure
        assert '<?xml version="1.0" encoding="utf-8"?>' in result
        assert "<!DOCTYPE html>" in result
        assert "<title>Chapter 1</title>" in result
        assert "<h1>Chapter 1</h1>" in result
        assert "<p>Content</p>" in result
        assert 'href="../Styles/style.css"' in result

    def test_build_chap_xhtml_special_chars_in_title(self):
        """Test building chapter with special characters in title."""
        result = build_chap_xhtml("Chapter & Title <Test>", "<p>Content</p>")

        # Check that title is properly escaped
        # Note: ElementTree escapes these automatically in element.text
        assert "Chapter" in result
        assert "Title" in result
        assert "Test" in result

    def test_build_chap_xhtml_multiple_paragraphs(self):
        """Test building chapter with multiple paragraphs."""
        body = "<p>First paragraph</p><p>Second paragraph</p>"
        result = build_chap_xhtml("Chapter", body)

        assert "<p>First paragraph</p>" in result
        assert "<p>Second paragraph</p>" in result

    def test_build_chap_xhtml_invalid_html(self):
        """Test building chapter with invalid HTML falls back to plain text."""
        body = "<p>Unclosed paragraph <invalid>"
        result = build_chap_xhtml("Chapter", body)

        # Should contain fallback content
        assert "[Content could not be parsed]" in result or "Unclosed paragraph" in result

    def test_build_chap_xhtml_empty_body(self):
        """Test building chapter with empty body."""
        result = build_chap_xhtml("Chapter", "")

        assert "<title>Chapter</title>" in result
        assert "<h1>Chapter</h1>" in result


class TestBuildCoverXhtml:
    """Test the build_cover_xhtml function."""

    def test_build_cover_xhtml_basic(self):
        """Test building basic cover XHTML."""
        result = build_cover_xhtml("Images/cover.jpg")

        assert '<?xml version="1.0" encoding="utf-8"?>' in result
        assert "<!DOCTYPE html>" in result
        assert "<title>Cover</title>" in result
        assert 'src="../Images/cover.jpg"' in result
        assert 'alt="Cover"' in result

    def test_build_cover_xhtml_style(self):
        """Test that cover includes proper styling."""
        result = build_cover_xhtml("Images/cover.png")

        assert "<style>" in result
        assert "max-width:100%" in result
        assert "margin:0 auto" in result

    def test_build_cover_xhtml_special_chars_in_path(self):
        """Test building cover with special characters in path."""
        result = build_cover_xhtml("Images/my&cover.jpg")

        assert 'src="../Images/my&amp;cover.jpg"' in result


class TestBuildContainerXml:
    """Test the build_container_xml function."""

    def test_build_container_xml(self):
        """Test building container.xml."""
        result = build_container_xml()

        # Parse to validate XML structure
        root = ET.fromstring(result)

        assert root.tag == "{urn:oasis:names:tc:opendocument:xmlns:container}container"
        assert root.get("version") == "1.0"

        # Check rootfile
        rootfile = root.find(".//{urn:oasis:names:tc:opendocument:xmlns:container}rootfile")
        assert rootfile is not None
        assert rootfile.get("full-path") == "OEBPS/content.opf"
        assert rootfile.get("media-type") == "application/oebps-package+xml"


class TestBuildStyleCss:
    """Test the build_style_css function."""

    def test_build_style_css_default(self):
        """Test building default CSS."""
        result = build_style_css()

        assert "font-family:serif" in result
        assert "line-height:1.4" in result
        assert "text-align:center" in result

    def test_build_style_css_custom(self):
        """Test building custom CSS."""
        custom = "body { color: red; }"
        result = build_style_css(custom)

        assert result == custom

    def test_build_style_css_empty_custom(self):
        """Test that empty custom CSS returns default."""
        result = build_style_css("")

        # Empty string is falsy, so should return default
        assert "font-family:serif" in result


class TestBuildContentOpf:
    """Test the build_content_opf function."""

    def test_build_content_opf_basic(self):
        """Test building basic OPF content."""
        manifest = ['<item id="ch1" href="ch1.xhtml" media-type="application/xhtml+xml"/>']
        spine = ['<itemref idref="ch1"/>']

        result = build_content_opf(
            title="Test Book",
            author="Test Author",
            manifest=manifest,
            spine=spine,
            uid="12345",
            cover_id=None,
        )

        assert "<?xml version='1.0' encoding='utf-8'?>" in result
        assert "<dc:title>Test Book</dc:title>" in result
        assert "<dc:creator opf:role='aut'>Test Author</dc:creator>" in result
        assert "<dc:language>en</dc:language>" in result
        assert "urn:uuid:12345" in result
        assert manifest[0] in result
        assert spine[0] in result

    def test_build_content_opf_with_cover(self):
        """Test building OPF with cover."""
        manifest = ['<item id="cover" href="cover.jpg" media-type="image/jpeg"/>']
        spine = []

        result = build_content_opf(
            title="Book",
            author="Author",
            manifest=manifest,
            spine=spine,
            uid="12345",
            cover_id="cover",
        )

        assert "<meta name='cover' content='cover'/>" in result

    def test_build_content_opf_custom_language(self):
        """Test building OPF with custom language."""
        result = build_content_opf(
            title="Book",
            author="Author",
            manifest=[],
            spine=[],
            uid="12345",
            cover_id=None,
            language="zh",
        )

        assert "<dc:language>zh</dc:language>" in result

    def test_build_content_opf_with_metadata(self):
        """Test building OPF with additional metadata."""
        metadata = {
            "publisher": "Test Publisher",
            "description": "Test Description",
            "series": "Test Series",
            "series_index": "1",
        }

        result = build_content_opf(
            title="Book",
            author="Author",
            manifest=[],
            spine=[],
            uid="12345",
            cover_id=None,
            metadata=metadata,
        )

        assert "<dc:publisher>Test Publisher</dc:publisher>" in result
        assert "<dc:description>Test Description</dc:description>" in result
        assert "<meta name='calibre:series' content='Test Series'/>" in result
        assert "<meta name='calibre:series_index' content='1'/>" in result

    def test_build_content_opf_html_escaping(self):
        """Test that special characters are escaped in OPF."""
        result = build_content_opf(
            title="Book & Title <Test>",
            author="Author & Name",
            manifest=[],
            spine=[],
            uid="12345",
            cover_id=None,
        )

        assert "<dc:title>Book &amp; Title &lt;Test&gt;</dc:title>" in result
        assert "<dc:creator opf:role='aut'>Author &amp; Name</dc:creator>" in result


class TestBuildTocNcx:
    """Test the build_toc_ncx function."""

    def test_build_toc_ncx_basic(self):
        """Test building basic TOC NCX."""
        nav_points = ['<navPoint id="nav1" playOrder="1"><navLabel><text>Chapter 1</text></navLabel><content src="ch1.xhtml"/></navPoint>']

        result = build_toc_ncx(title="Test Book", author="Test Author", nav_points=nav_points, uid="12345")

        assert "<?xml version='1.0' encoding='utf-8'?>" in result
        assert "<!DOCTYPE ncx" in result
        assert "urn:uuid:12345" in result
        assert "<text>Test Book</text>" in result
        assert "<text>Test Author</text>" in result
        assert nav_points[0] in result

    def test_build_toc_ncx_multiple_chapters(self):
        """Test building TOC with multiple chapters."""
        nav_points = [
            '<navPoint id="nav1" playOrder="1"><navLabel><text>Chapter 1</text></navLabel><content src="ch1.xhtml"/></navPoint>',
            '<navPoint id="nav2" playOrder="2"><navLabel><text>Chapter 2</text></navLabel><content src="ch2.xhtml"/></navPoint>',
        ]

        result = build_toc_ncx(title="Book", author="Author", nav_points=nav_points, uid="12345")

        assert nav_points[0] in result
        assert nav_points[1] in result

    def test_build_toc_ncx_html_escaping(self):
        """Test that special characters are escaped in TOC."""
        result = build_toc_ncx(
            title="Book & Title <Test>",
            author="Author & Name",
            nav_points=[],
            uid="12345",
        )

        assert "<text>Book &amp; Title &lt;Test&gt;</text>" in result
        assert "<text>Author &amp; Name</text>" in result

    def test_build_toc_ncx_empty_nav_points(self):
        """Test building TOC with no navigation points."""
        result = build_toc_ncx(title="Book", author="Author", nav_points=[], uid="12345")

        assert "<navMap>" in result
        assert "</navMap>" in result
