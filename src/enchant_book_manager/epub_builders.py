#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
# - Initial creation from make_epub.py refactoring
# - Contains XHTML/XML builders for EPUB components
# - Includes functions for building chapters, TOC, OPF, container.xml
# - Added proper XML generation using ElementTree
#

"""
epub_builders.py - EPUB component builders
==========================================

Provides functions to build various EPUB components including XHTML chapters,
TOC navigation, OPF package files, and other EPUB structural elements.
Uses ElementTree for proper XML generation and escaping.
"""

from __future__ import annotations

import html
from datetime import datetime, timezone
from typing import Optional, Any
from io import StringIO
import xml.etree.ElementTree as ET


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
    html_elem = ET.Element("{http://www.w3.org/1999/xhtml}html")

    # Head section
    head = ET.SubElement(html_elem, "{http://www.w3.org/1999/xhtml}head")
    title_elem = ET.SubElement(head, "{http://www.w3.org/1999/xhtml}title")
    title_elem.text = title

    link = ET.SubElement(head, "{http://www.w3.org/1999/xhtml}link")
    link.set("href", "../Styles/style.css")
    link.set("rel", "stylesheet")
    link.set("type", "text/css")

    # Body section
    body = ET.SubElement(html_elem, "{http://www.w3.org/1999/xhtml}body")
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
    tree = ET.ElementTree(html_elem)
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
    html_elem = ET.Element("{http://www.w3.org/1999/xhtml}html")

    # Head section
    head = ET.SubElement(html_elem, "{http://www.w3.org/1999/xhtml}head")
    title_elem = ET.SubElement(head, "{http://www.w3.org/1999/xhtml}title")
    title_elem.text = "Cover"

    style = ET.SubElement(head, "{http://www.w3.org/1999/xhtml}style")
    style.text = "html,body{margin:0;padding:0}img{max-width:100%;height:auto;display:block;margin:0 auto}"

    # Body section
    body = ET.SubElement(html_elem, "{http://www.w3.org/1999/xhtml}body")
    img = ET.SubElement(body, "{http://www.w3.org/1999/xhtml}img")
    img.set("src", f"../{img_rel}")
    img.set("alt", "Cover")

    # Generate string
    tree = ET.ElementTree(html_elem)
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


def build_style_css(custom_css: str | None = None) -> str:
    """Build CSS content, using custom CSS if provided.

    Args:
        custom_css: Optional custom CSS content

    Returns:
        CSS content string
    """
    if custom_css:
        return custom_css
    # Default CSS
    return "body{font-family:serif;line-height:1.4;margin:5%}h1{text-align:center;margin:2em 0 1em}p{text-indent:1.5em;margin:0 0 1em}img{max-width:100%;height:auto}"


def build_content_opf(
    title: str,
    author: str,
    manifest: list[str],
    spine: list[str],
    uid: str,
    cover_id: str | None,
    language: str = "en",
    metadata: dict[str, Any] | None = None,
) -> str:
    """Build OPF content with support for language and additional metadata.

    Args:
        title: Book title
        author: Book author
        manifest: List of manifest item strings
        spine: List of spine itemref strings
        uid: Unique identifier UUID
        cover_id: ID of cover image item (if any)
        language: Language code
        metadata: Optional metadata dict

    Returns:
        Complete OPF XML as string
    """
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


def build_toc_ncx(title: str, author: str, nav_points: list[str], uid: str) -> str:
    """Build Table of Contents NCX file.

    Args:
        title: Book title
        author: Book author
        nav_points: List of navPoint XML strings
        uid: Unique identifier UUID

    Returns:
        Complete NCX XML as string
    """
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
