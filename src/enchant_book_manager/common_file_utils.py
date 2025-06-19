#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
common_file_utils.py - Shared file handling utilities for EnChANT modules

This module provides unified file encoding detection and content decoding
with configurable behavior for different use cases.
"""

import logging
from pathlib import Path
from typing import Optional, Tuple
import chardet
from chardet.universaldetector import UniversalDetector

# Default logger
logger = logging.getLogger(__name__)


def detect_file_encoding(
    file_path: Path,
    method: str = "universal",  # 'universal', 'chardet', 'auto'
    sample_size: Optional[int] = None,  # bytes to sample (None = adaptive)
    confidence_threshold: float = 0.0,
    logger: Optional[logging.Logger] = None,
) -> Tuple[str, float]:
    """
    Detect file encoding using specified method.

    Parameters:
    - file_path: Path to the file to analyze
    - method: Detection method to use
      - 'universal': Use UniversalDetector (reads line by line)
      - 'chardet': Use chardet.detect (reads sample)
      - 'auto': Try chardet first, fall back to universal if confidence low
    - sample_size: Bytes to read for chardet method (None = 32KB default)
    - confidence_threshold: Minimum confidence (only used with 'auto')
    - logger: Logger instance (uses module logger if None)

    Returns: (encoding, confidence) tuple
    """
    if logger is None:
        logger = globals()["logger"]

    if method == "universal":
        return _detect_with_universal(file_path, logger)
    elif method == "chardet":
        return _detect_with_chardet(file_path, sample_size, logger)
    elif method == "auto":
        # Try chardet first
        encoding, confidence = _detect_with_chardet(file_path, sample_size, logger)
        if confidence >= confidence_threshold and encoding:
            return encoding, confidence
        # Fall back to universal if confidence too low
        logger.debug(
            f"Chardet confidence {confidence} below threshold {confidence_threshold}, trying UniversalDetector"
        )
        return _detect_with_universal(file_path, logger)
    else:
        raise ValueError(f"Unknown detection method: {method}")


def _detect_with_universal(
    file_path: Path, logger: logging.Logger
) -> Tuple[str, float]:
    """Detect encoding using UniversalDetector (line by line reading)."""
    detector = UniversalDetector()
    try:
        with file_path.open("rb") as f:
            for line in f:
                detector.feed(line)
                if detector.done:
                    break
            detector.close()
            result = detector.result
            encoding = result.get("encoding", "utf-8")
            confidence = result.get("confidence", 0.0)
            logger.debug(f"UniversalDetector: {encoding} (confidence: {confidence})")
            return encoding, confidence
    except Exception as e:
        logger.error(f"Error detecting encoding with UniversalDetector: {e}")
        return "utf-8", 0.0


def _detect_with_chardet(
    file_path: Path, sample_size: Optional[int], logger: logging.Logger
) -> Tuple[str, float]:
    """Detect encoding using chardet.detect (sample reading)."""
    if sample_size is None:
        sample_size = 32 * 1024  # 32KB default

    try:
        with file_path.open("rb") as f:
            raw_data = f.read(sample_size)

        result = chardet.detect(raw_data)
        encoding = result.get("encoding", "utf-8")
        confidence = result.get("confidence", 0.0)
        logger.debug(f"chardet.detect: {encoding} (confidence: {confidence})")
        return encoding, confidence
    except Exception as e:
        logger.error(f"Error detecting encoding with chardet: {e}")
        return "utf-8", 0.0


def decode_file_content(
    file_path: Path,
    mode: str = "full",  # 'full' or 'preview'
    preview_kb: int = 35,
    min_file_size_kb: Optional[int] = None,
    encoding_detector: str = "auto",  # 'universal', 'chardet', 'auto'
    confidence_threshold: float = 0.7,
    fallback_encodings: list = None,
    truncate_chars: Optional[int] = None,
    logger: Optional[logging.Logger] = None,
    raise_on_error: bool = True,
) -> Optional[str]:
    """
    Unified file content decoder with configurable behavior.

    Parameters:
    - file_path: Path to the file to decode
    - mode: 'full' reads entire file, 'preview' reads limited content
    - preview_kb: KB to read in preview mode
    - min_file_size_kb: Minimum file size (returns None if smaller)
    - encoding_detector: Method to detect encoding
    - confidence_threshold: Minimum confidence for chardet
    - fallback_encodings: List of encodings to try if detection fails
    - truncate_chars: Truncate result to this many characters
    - logger: Logger instance (uses module logger if None)
    - raise_on_error: If False, returns None on error instead of raising

    Returns: Decoded content or None (if raise_on_error=False and error occurs)
    """
    if logger is None:
        logger = globals()["logger"]

    if fallback_encodings is None:
        fallback_encodings = ["gb18030", "gbk", "utf-8", "utf-16", "big5"]

    try:
        # Check file size if required
        if min_file_size_kb is not None:
            file_size_kb = file_path.stat().st_size / 1024
            if file_size_kb < min_file_size_kb:
                logger.warning(
                    f"File '{file_path}' is smaller than {min_file_size_kb} KB. Skipping."
                )
                if raise_on_error:
                    raise ValueError(
                        f"File too small: {file_size_kb:.1f} KB < {min_file_size_kb} KB"
                    )
                return None

        # Determine how much to read
        if mode == "preview":
            bytes_to_read = preview_kb * 1024
        else:
            bytes_to_read = None  # Read entire file

        # Read the file data
        with file_path.open("rb") as f:
            if bytes_to_read:
                raw_data = f.read(bytes_to_read)
            else:
                raw_data = f.read()

        # Detect encoding
        sample_size = min(len(raw_data), 32 * 1024) if mode == "preview" else None
        encoding, confidence = detect_file_encoding(
            file_path,
            method=encoding_detector,
            sample_size=sample_size,
            confidence_threshold=confidence_threshold,
            logger=logger,
        )

        logger.debug(f"Detected encoding: {encoding} (confidence: {confidence})")

        # Try to decode with detected encoding
        content = None
        if encoding and (
            confidence >= confidence_threshold or encoding_detector == "universal"
        ):
            try:
                content = raw_data.decode(encoding)
                logger.debug(f"Successfully decoded with {encoding}")
            except UnicodeDecodeError as e:
                logger.debug(f"Failed to decode with detected encoding {encoding}: {e}")

        # Try fallback encodings if needed
        if content is None:
            logger.debug(f"Trying fallback encodings: {fallback_encodings}")
            for enc in fallback_encodings:
                try:
                    content = raw_data.decode(enc)
                    logger.debug(f"Successfully decoded with fallback encoding: {enc}")
                    break
                except UnicodeDecodeError:
                    continue

        # If still no success, try with error replacement
        if content is None:
            logger.warning(
                f"All encodings failed, using {fallback_encodings[0]} with error replacement"
            )
            content = raw_data.decode(fallback_encodings[0], errors="replace")

        # Truncate if requested
        if truncate_chars and len(content) > truncate_chars:
            content = content[:truncate_chars]
            logger.debug(f"Truncated content to {truncate_chars} characters")

        return content

    except Exception as e:
        logger.error(f"Error reading file '{file_path}': {e}")
        if raise_on_error:
            raise
        return None


# Convenience functions that match original module interfaces


def decode_full_file(file_path: Path, logger: Optional[logging.Logger] = None) -> str:
    """
    Read and decode entire file content (cli_translator.py style).
    Always returns content (with replacement chars if needed).
    """
    return decode_file_content(
        file_path,
        mode="full",
        encoding_detector="universal",
        logger=logger,
        raise_on_error=True,
    )


def decode_file_preview(
    file_path: Path,
    kb_to_read: int = 35,
    min_file_size_kb: int = 100,
    max_chars: int = 1500,
    logger: Optional[logging.Logger] = None,
) -> Optional[str]:
    """
    Read and decode limited file content for preview (novel_renamer.py style).
    Returns None on errors or if file is too small.
    """
    return decode_file_content(
        file_path,
        mode="preview",
        preview_kb=kb_to_read,
        min_file_size_kb=min_file_size_kb,
        encoding_detector="chardet",
        confidence_threshold=0.7,
        truncate_chars=max_chars,
        logger=logger,
        raise_on_error=False,
    )
