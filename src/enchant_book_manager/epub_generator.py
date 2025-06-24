#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
# - Initial creation from make_epub.py refactoring
# - Contains EPUB creation functions: write_new_epub and extend_epub
# - Manages EPUB file structure and ZIP packaging
#

"""
epub_generator.py - EPUB file generation and extension
=====================================================

Handles creation of new EPUB files and extending existing ones with additional chapters.
Manages the EPUB file structure including META-INF, OEBPS directories and proper ZIP packaging.
"""

from __future__ import annotations

import os
import re
import shutil
import tempfile
import uuid
import zipfile
from pathlib import Path
from typing import Optional, Any
import xml.etree.ElementTree as ET

from .epub_constants import ENCODING, MIMETYPE
from .epub_builders import (
    build_container_xml,
    build_style_css,
    build_content_opf,
    build_toc_ncx,
    build_chap_xhtml,
    build_cover_xhtml,
)

# Import enhanced TOC builder
try:
    from .epub_toc_enhanced import build_enhanced_toc_ncx

    TOC_ENHANCED = True
except ImportError:
    TOC_ENHANCED = False


def write_new_epub(
    chaps: list[tuple[str, str]],
    out: Path,
    title: str,
    author: str,
    cover: Path | None,
    language: str = "en",
    custom_css: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Create a new EPUB file from chapters.

    Args:
        chaps: List of (title, html_content) tuples for each chapter
        out: Output path for the EPUB file
        title: Book title
        author: Book author
        cover: Optional path to cover image
        language: Language code (default: 'en')
        custom_css: Optional custom CSS content
        metadata: Optional metadata dict with keys like 'publisher', 'description', etc.
    """
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
            import html

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


def extend_epub(epub: Path, new: list[tuple[str, str]]) -> None:
    """Extend an existing EPUB with new chapters.

    Args:
        epub: Path to existing EPUB file
        new: List of (title, html_content) tuples for new chapters

    Raises:
        ValueError: If EPUB structure is invalid
    """
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
