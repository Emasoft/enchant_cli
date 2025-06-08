#!/usr/bin/env python3
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
from difflib import SequenceMatcher
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import xml.etree.ElementTree as ET


# ────────────────────────── regexes & tables ────────────────────────── #

FILENAME_RE = re.compile(
    r"^(?P<title>.+?)\s+by\s+(?P<author>.+?)\s+-\s+Chapter\s+(?P<num>\d+)\.txt$",
    re.IGNORECASE,
)

WORD_NUMS = (
    "one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|"
    "thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|"
    "twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred|thousand"
)

HEADING_RE = re.compile(
    rf"^[^\w]*\s*chapter\s+"
    rf"(?:(?P<num_d>\d+)|(?P<num_r>[ivxlcdm]+)|"
    rf"(?P<num_w>(?:{WORD_NUMS})(?:[-\s](?:{WORD_NUMS}))*))"
    rf"\b(?P<rest>.*)$",
    re.IGNORECASE,
)

_SINGLE = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4,
    "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
    "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13,
    "fourteen": 14, "fifteen": 15, "sixteen": 16,
    "seventeen": 17, "eighteen": 18, "nineteen": 19,
}
_TENS = {
    "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50,
    "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
}
_SCALES = {"hundred": 100, "thousand": 1000}
_ROMAN = {"i": 1, "v": 5, "x": 10, "l": 50, "c": 100, "d": 500, "m": 1000}

ENCODING = "utf-8"
MIMETYPE = "application/epub+zip"


# ──────────────────────────── logging ──────────────────────────── #

def _log_path() -> Path:
    return Path.cwd() / f"errors_{datetime.now():%Y%m%d_%H%M%S}.log"

_ERROR_LOG: Optional[Path] = None
_JSON_LOG: Optional[Path] = None


def log_issue(msg: str, obj: Optional[dict] = None) -> None:
    """Append *msg* (and *obj* if requested) to per-run log files."""
    global _ERROR_LOG
    if _ERROR_LOG is None:
        _ERROR_LOG = _log_path()
    with _ERROR_LOG.open("a", encoding=ENCODING) as fh:
        fh.write(f"[{datetime.now().isoformat()}] {msg}\n")
    if _JSON_LOG and obj is not None:
        with _JSON_LOG.open("a", encoding=ENCODING) as jf:
            jf.write(json.dumps(obj, ensure_ascii=False) + "\n")


# ─────────────────── numeral conversion helpers ─────────────────── #

def roman_to_int(s: str) -> int:
    total = prev = 0
    for ch in reversed(s.lower()):
        val = _ROMAN[ch]
        total = total - val if val < prev else total + val
        prev = val
    return total

def words_to_int(text: str) -> int:
    tokens = re.split(r"[ \t\-]+", text.lower())
    total = curr = 0
    for tok in tokens:
        if tok in _SINGLE:
            curr += _SINGLE[tok]
        elif tok in _TENS:
            curr += _TENS[tok]
        elif tok in _SCALES:
            curr = max(curr, 1) * _SCALES[tok]
            if tok == "thousand":
                total += curr
                curr = 0
        else:
            raise ValueError
    return total + curr

def parse_num(raw: str) -> Optional[int]:
    if raw.isdigit():
        return int(raw)
    if re.fullmatch(r"[ivxlcdm]+", raw, re.IGNORECASE):
        return roman_to_int(raw)
    try:
        return words_to_int(raw)
    except ValueError:
        return None


# ─────────────────── anomaly detector (updated) ─────────────────── #

def detect_issues(seq: List[int]) -> List[str]:
    """
    Updated algorithm provided by user: reports missing, repeats, swaps,
    out-of-place, duplicates.
    """
    issues = []
    start, end = seq[0], seq[-1]
    prev_expected = start
    seen = set()
    reported_missing = set()

    for idx, v in enumerate(seq):
        # 1) Repeats: only on second+ occurrence
        if v in seen:
            # find nearest non-identical predecessor
            pred = next(x for x in reversed(seq[:idx]) if x != v)
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
            for m in range(prev_expected + 1, v):
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

def split_text(text: str, detect_headings: bool) -> Tuple[List[Tuple[str, str]], List[int]]:
    """
    Returns (chapters, seq) collapsing adjacent duplicate headings separated
    only by blank lines.
    """
    if not detect_headings:
        return [("Content", text)], []

    chapters, seq, buf = [], [], []
    cur_title = None
    front_done = False
    last_num: Optional[int] = None
    blank_only = True

    for line in text.splitlines():
        m = HEADING_RE.match(line.strip())
        if m:
            num = parse_num(m.group("num_d") or m.group("num_r") or m.group("num_w"))
            if num is None:
                buf.append(line)
                blank_only = False
                continue
            if last_num == num and blank_only:
                buf.clear()
                continue
            last_num = num
            blank_only = True

            if not front_done:
                if buf:
                    chapters.append(("Front Matter", "\n".join(buf).strip()))
                    buf.clear()
                front_done = True

            if cur_title:
                chapters.append((cur_title, "\n".join(buf).strip()))
                buf.clear()

            subtitle = (m.group("rest") or "").strip()
            cur_title = f"Chapter {num}{(' – ' + subtitle) if subtitle else ''}"
            seq.append(num)
        else:
            buf.append(line)
            if line.strip():
                blank_only = False

    if cur_title:
        chapters.append((cur_title, "\n".join(buf).strip()))
    elif buf:
        chapters.append(("Content", "\n".join(buf).strip()))
    return chapters, seq


# ───────────── plain text → XHTML ───────────── #

def paragraphize(txt: str) -> str:
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
    return f"""<?xml version='1.0' encoding='utf-8'?>
<!DOCTYPE html>
<html xmlns='http://www.w3.org/1999/xhtml'>
<head>
  <title>{html.escape(title)}</title>
  <link href='../Styles/style.css' rel='stylesheet' type='text/css'/>
</head>
<body>
  <h1>{html.escape(title)}</h1>
  {body_html}
</body>
</html>""".strip()

def build_cover_xhtml(img_rel: str) -> str:
    return f"""<?xml version='1.0' encoding='utf-8'?>
<!DOCTYPE html>
<html xmlns='http://www.w3.org/1999/xhtml'>
<head>
  <title>Cover</title>
  <style>html,body{{margin:0;padding:0}}img{{max-width:100%;height:auto;display:block;margin:0 auto}}</style>
</head>
<body>
  <img src='../{html.escape(img_rel)}' alt='Cover'/>
</body>
</html>""".strip()

def build_container_xml() -> str:
    return ("<?xml version='1.0' encoding='utf-8'?><container version='1.0' "
            "xmlns='urn:oasis:names:tc:opendocument:xmlns:container'><rootfiles>"
            "<rootfile full-path='OEBPS/content.opf' media-type='application/oebps-package+xml'/>"
            "</rootfiles></container>")

def build_style_css() -> str:
    return ("body{font-family:serif;line-height:1.4;margin:5%}"
            "h1{text-align:center;margin:2em 0 1em}"
            "p{text-indent:1.5em;margin:0 0 1em}"
            "img{max-width:100%;height:auto}")

def build_content_opf(title: str, author: str,
                      manifest: List[str], spine: List[str],
                      uid: str, cover_id: Optional[str]) -> str:
    date = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    meta_cover = f"\n    <meta name='cover' content='{cover_id}'/>" if cover_id else ""
    return f"""<?xml version='1.0' encoding='utf-8'?>
<package xmlns='http://www.idpf.org/2007/opf' unique-identifier='BookID' version='2.0'>
  <metadata xmlns:dc='http://purl.org/dc/elements/1.1/' xmlns:opf='http://www.idpf.org/2007/opf'>
    <dc:title>{html.escape(title)}</dc:title>
    <dc:creator opf:role='aut'>{html.escape(author)}</dc:creator>
    <dc:language>en</dc:language>
    <dc:identifier id='BookID'>urn:uuid:{uid}</dc:identifier>
    <dc:date>{date}</dc:date>{meta_cover}
  </metadata>
  <manifest>
        {"\n        ".join(manifest)}
  </manifest>
  <spine toc='ncx'>
        {"\n        ".join(spine)}
  </spine>
</package>""".strip()

def build_toc_ncx(title: str, author: str,
                  nav_points: List[str], uid: str) -> str:
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
    while True:
        try:
            if not p.exists() or not p.is_dir():
                raise ValidationError(f"Directory '{p}' not found or not a directory.")
            if not os.access(p, os.R_OK):
                raise ValidationError(f"No read permission for '{p}'.")
            list(p.iterdir())
            return
        except (OSError, ValidationError) as e:
            log_issue(str(e))
            if input("Retry directory check? [r/N] > ").lower() != "r":
                sys.exit(1)

def ensure_output_ok(path: Path, append: bool) -> None:
    while True:
        try:
            if append:
                if path.suffix.lower() != ".epub" or not (path.exists() and os.access(path, os.W_OK)):
                    raise ValidationError(f"Cannot write EPUB '{path}'.")
            else:
                target = path.parent if path.suffix.lower()==".epub" else path
                target.mkdir(parents=True, exist_ok=True)
                if not os.access(target, os.W_OK):
                    raise ValidationError(f"No write permission for '{target}'.")
            return
        except (OSError, ValidationError) as e:
            log_issue(str(e))
            if input("Retry output check? [r/N] > ").lower() != "r":
                sys.exit(1)

def ensure_cover_ok(p: Path) -> None:
    while True:
        try:
            if not p.is_file():
                raise ValidationError(f"Cover '{p}' is not a file.")
            if p.suffix.lower() not in {".jpg",".jpeg",".png"}:
                raise ValidationError("Cover must be .jpg/.jpeg/.png.")
            if not os.access(p, os.R_OK):
                raise ValidationError(f"No read permission for '{p}'.")
            return
        except (OSError, ValidationError) as e:
            log_issue(str(e))
            if input("Retry cover check? [r/N] > ").lower() != "r":
                sys.exit(1)

def collect_chunks(folder: Path) -> Dict[int, Path]:
    while True:
        mapping: Dict[int, Path] = {}
        issues: List[str] = []
        try:
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
                raise ValidationError("No valid .txt chunks found.")
            for msg in issues:
                log_issue(msg)
            return mapping
        except ValidationError as e:
            log_issue(str(e))
            if input("Retry chunk scan? [r/N] > ").lower() != "r":
                sys.exit(1)


# ───────────── EPUB creation helpers ───────────── #

def write_new_epub(chaps: List[Tuple[str,str]], out: Path,
                   title: str, author: str, cover: Optional[Path]) -> None:
    uid = str(uuid.uuid4())
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        (tmp/"META-INF").mkdir()
        oebps = tmp/"OEBPS"
        (oebps/"Text").mkdir(parents=True)
        (oebps/"Styles").mkdir()
        if cover:
            (oebps/"Images").mkdir()

        (tmp/"META-INF"/"container.xml").write_text(build_container_xml(), ENCODING)
        (oebps/"Styles"/"style.css").write_text(build_style_css(), ENCODING)

        manifest = [
            "<item id='ncx' href='toc.ncx' media-type='application/x-dtbncx+xml'/>",
            "<item id='css' href='Styles/style.css' media-type='text/css'/>",
        ]
        spine, nav = [], []
        cover_id = None

        if cover:
            cover_id = "cover-img"
            img_rel = f"Images/{cover.name}"
            shutil.copy2(cover, oebps/img_rel)
            mime = "image/jpeg" if cover.suffix.lower() in {".jpg",".jpeg"} else "image/png"
            manifest.append(f"<item id='{cover_id}' href='{img_rel}' media-type='{mime}'/>")
            (oebps/"Text"/"cover.xhtml").write_text(build_cover_xhtml(img_rel), ENCODING)
            manifest.append("<item id='coverpage' href='Text/cover.xhtml' media-type='application/xhtml+xml'/>")
            spine.append("<itemref idref='coverpage' linear='yes'/>")

        for idx, (title_, body_html) in enumerate(chaps, 1):
            xhtml = f"Text/chapter{idx}.xhtml"
            (oebps/xhtml).write_text(build_chap_xhtml(title_, body_html), ENCODING)
            manifest.append(f"<item id='chap{idx}' href='{xhtml}' media-type='application/xhtml+xml'/>")
            spine.append(f"<itemref idref='chap{idx}'/>")
            nav.append(f"<navPoint id='nav{idx}' playOrder='{idx}'><navLabel><text>{html.escape(title_)}</text></navLabel><content src='{xhtml}'/></navPoint>")

        (oebps/"content.opf").write_text(build_content_opf(title, author, manifest, spine, uid, cover_id), ENCODING)
        (oebps/"toc.ncx").write_text(build_toc_ncx(title, author, nav, uid), ENCODING)

        with zipfile.ZipFile(out, "w") as z:
            z.writestr("mimetype", MIMETYPE, zipfile.ZIP_STORED)
            for root,_,files in os.walk(tmp):
                for f in files:
                    fp = Path(root)/f
                    rel = fp.relative_to(tmp).as_posix()
                    if rel == "mimetype":
                        continue
                    z.write(fp, rel, zipfile.ZIP_DEFLATED)

def extend_epub(epub: Path, new: List[Tuple[str,str]]) -> None:
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        with zipfile.ZipFile(epub) as z:
            z.extractall(tmp)

        oebps = tmp/"OEBPS"
        textdir = oebps/"Text"
        next_idx = 1 + max((int(m.group(1)) for p in textdir.glob("chapter*.xhtml")
                            if (m:=re.search(r"chapter(\d+)\.xhtml", p.name))), default=0)

        ns_opf = {"opf":"http://www.idpf.org/2007/opf"}
        ns_ncx = {"ncx":"http://www.daisy.org/z3986/2005/ncx/"}
        opf = ET.parse(oebps/"content.opf")
        manifest = opf.find("opf:manifest", ns_opf)
        spine = opf.find("opf:spine", ns_opf)
        ncx = ET.parse(oebps/"toc.ncx")
        navmap = ncx.find("ncx:navMap", ns_ncx)
        play = max((int(n.get("playOrder","0")) for n in navmap.findall("ncx:navPoint", ns_ncx)), default=0)

        for title_, body_html in new:
            xhtml = f"Text/chapter{next_idx}.xhtml"
            (oebps/xhtml).write_text(build_chap_xhtml(title_, body_html), ENCODING)
            ET.SubElement(manifest, "{http://www.idpf.org/2007/opf}item",
                          {"id":f"chap{next_idx}", "href":xhtml, "media-type":"application/xhtml+xml"})
            ET.SubElement(spine, "{http://www.idpf.org/2007/opf}itemref", {"idref":f"chap{next_idx}"})
            play += 1
            np = ET.SubElement(navmap, "{http://www.daisy.org/z3986/2005/ncx/}navPoint",
                               {"id":f"nav{next_idx}", "playOrder":str(play)})
            nl = ET.SubElement(np, "{http://www.daisy.org/z3986/2005/ncx/}navLabel")
            ET.SubElement(nl, "{http://www.daisy.org/z3986/2005/ncx/}text").text = title_
            ET.SubElement(np, "{http://www.daisy.org/z3986/2005/ncx/}content", {"src":xhtml})
            next_idx += 1

        opf.write(oebps/"content.opf", ENCODING, xml_declaration=True)
        ncx.write(oebps/"toc.ncx", ENCODING, xml_declaration=True)

        tmp_epub = epub.with_suffix(".tmp.epub")
        with zipfile.ZipFile(tmp_epub, "w") as z:
            z.writestr("mimetype", MIMETYPE, zipfile.ZIP_STORED)
            for root,_,files in os.walk(tmp):
                for f in files:
                    fp = Path(root)/f
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
    detect_headings: bool = True
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
        if cover_path.suffix.lower() not in {'.jpg', '.jpeg', '.png'}:
            raise ValidationError("Cover must be .jpg/.jpeg/.png")
    
    # Process chapters - convert text to HTML
    processed_chapters = []
    for chap_title, chap_content in chapters:
        # Convert plain text to HTML paragraphs
        html_content = paragraphize(chap_content)
        processed_chapters.append((chap_title, html_content))
    
    # Create the EPUB
    write_new_epub(processed_chapters, output_path, title, author, cover_path)


def create_epub_from_directory(
    input_dir: Path,
    output_path: Path,
    title: Optional[str] = None,
    author: Optional[str] = None,
    cover_path: Optional[Path] = None,
    detect_headings: bool = True,
    validate_only: bool = False,
    strict: bool = True
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

def parse_add(val: str) -> Tuple[int,bool]:
    m = re.fullmatch(r"(\d+)(\+)?", val)
    if not m:
        raise argparse.ArgumentTypeError("--add must be N or N+")
    return int(m.group(1)), bool(m.group(2))

def main() -> None:
    ap = argparse.ArgumentParser(description="TXT chunks → EPUB builder / validator")
    ap.add_argument("input_dir", type=Path, help="Directory with .txt chunks")
    ap.add_argument("-o","--output", type=Path, required=True, help="Output directory or .epub")
    ap.add_argument("--title", help="Override book title")
    ap.add_argument("--author", help="Override author")
    ap.add_argument("--toc", action="store_true", help="Detect chapter headings and build TOC")
    ap.add_argument("--cover", type=Path, help="Cover image (jpg/png)")
    ap.add_argument("--add", type=parse_add, metavar="N[+]", help="Append chunk N (or N+) to existing EPUB")
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

    selected = ({n:p for n,p in chunks.items()
                 if n == add_start or (add_plus and n >= add_start)}
                if append else chunks)
    if append and not selected:
        sys.exit(f"No chunks ≥ {add_start} found.")

    full_text = "\n".join(selected[i].read_text(ENCODING) for i in sorted(selected))
    chap_blocks, seq = split_text(full_text, args.toc)
    chapters = [(t, paragraphize(b)) for t,b in chap_blocks]
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
        def_title, def_author = ("Untitled","Unknown")
        if m:=FILENAME_RE.match(first.name):
            def_title, def_author = m.group("title"), m.group("author")
        title = args.title or def_title
        author = args.author or def_author
        safe = re.sub(r"[^A-Za-z0-9_]+","_", title).strip("_") or "book"
        epub_path = args.output if args.output.suffix.lower()==".epub" else args.output/f"{safe}.epub"
        write_new_epub(chapters, epub_path, title, author, args.cover)
        result = f"EPUB created at: {epub_path}"

    summary = "✅ validation clean" if not msgs else f"⚠ {len(msgs)} issue(s) – see {_ERROR_LOG}"
    print(f"{result}  {summary}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nCancelled by user.")
        
        