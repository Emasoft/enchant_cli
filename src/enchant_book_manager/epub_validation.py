#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
# - Initial creation from make_epub.py refactoring
# - Contains validation functions and file system helpers
# - Includes error handling and logging utilities
#

"""
epub_validation.py - EPUB validation and filesystem utilities
============================================================

Provides validation functions for EPUB creation including directory checks,
file permissions, and format validation. Also includes logging utilities.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from .epub_constants import FILENAME_RE

# ──────────────────────────── logging ──────────────────────────── #


def _log_path() -> Path:
    """
    Generate log file path with timestamp.

    Returns:
        Path object for error log file
    """
    return Path.cwd() / f"errors_{datetime.now():%Y%m%d_%H%M%S}.log"


_ERROR_LOG: Path | None = None
_JSON_LOG: Path | None = None


def log_issue(msg: str, obj: dict[str, Any] | None = None) -> None:
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
    with _ERROR_LOG.open("a", encoding="utf-8") as fh:
        fh.write(f"[{datetime.now().isoformat()}] {msg}\n")
    if _JSON_LOG and obj is not None:
        with _JSON_LOG.open("a", encoding="utf-8") as jf:
            jf.write(json.dumps(obj, ensure_ascii=False) + "\n")


def set_json_log(path: Path) -> None:
    """Set the JSON log file path.

    Args:
        path: Path for JSON log file
    """
    global _JSON_LOG
    _JSON_LOG = path


# ───────────── validation helpers ───────────── #


class ValidationError(Exception):
    """Raised when validation fails."""

    pass


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
        raise ValidationError(f"Cannot read directory '{p}': {e}") from e


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
            raise ValidationError(f"Cannot create directory '{target}': {e}") from e
        if not os.access(target, os.W_OK):
            raise ValidationError(f"No write permission for '{target}'.")


def ensure_cover_ok(p: Path) -> None:
    """Ensure cover file is valid.

    Args:
        p: Path to cover file

    Raises:
        ValidationError: If cover is not valid
    """
    if not p.is_file():
        raise ValidationError(f"Cover '{p}' is not a file.")
    if p.suffix.lower() not in {".jpg", ".jpeg", ".png"}:
        raise ValidationError("Cover must be .jpg/.jpeg/.png.")
    if not os.access(p, os.R_OK):
        raise ValidationError(f"No read permission for '{p}'.")


def collect_chunks(folder: Path) -> dict[int, Path]:
    """Collect chapter chunks from folder.

    Args:
        folder: Directory containing chapter files

    Returns:
        Dictionary mapping chapter index to file path

    Raises:
        ValidationError: If no valid chunks found
    """
    mapping: dict[int, Path] = {}
    issues: list[str] = []

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
