#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test helper utilities for creating realistic test fixtures.
"""

import tempfile
import shutil
from pathlib import Path
from typing import Tuple, Optional
import logging

from enchant_book_manager.models import (
    Book,
    Chunk,
    Variation,
    VARIATION_DB,
    BOOK_DB,
    CHUNK_DB,
)


class DatabaseTestHelper:
    """Helper class for setting up test databases with realistic data.

    Note: Class name doesn't start with 'Test' to avoid pytest collection warnings.
    """

    def __init__(self):
        self.temp_dir = None
        self.original_book_db = None
        self.original_chunk_db = None
        self.original_variation_db = None

    def setup(self) -> Path:
        """Set up a temporary test database."""
        # Create temporary directory
        self.temp_dir = tempfile.mkdtemp()

        # Save original database contents
        self.original_book_db = BOOK_DB.copy()
        self.original_chunk_db = CHUNK_DB.copy()
        self.original_variation_db = VARIATION_DB.copy()

        # Clear databases for testing
        BOOK_DB.clear()
        CHUNK_DB.clear()
        VARIATION_DB.clear()

        return Path(self.temp_dir)

    def teardown(self):
        """Clean up test database and restore original."""
        # Restore original database contents
        if self.original_book_db is not None:
            BOOK_DB.clear()
            BOOK_DB.update(self.original_book_db)

        if self.original_chunk_db is not None:
            CHUNK_DB.clear()
            CHUNK_DB.update(self.original_chunk_db)

        if self.original_variation_db is not None:
            VARIATION_DB.clear()
            VARIATION_DB.update(self.original_variation_db)

        if self.temp_dir:
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def create_test_book(
        self,
        title: str = "Test Novel",
        author: str = "Test Author",
        language: str = "zh",
        num_chunks: int = 3,
        chunk_size: int = 100,
    ) -> Tuple[Book, list[Chunk]]:
        """Create a test book with chunks containing realistic Chinese text."""
        # Generate a unique book ID
        book_id = f"book_{len(BOOK_DB) + 1}"

        # Create book
        book = Book(
            book_id=book_id,
            title=title,
            original_title=title,
            translated_title=title,
            transliterated_title=title,
            author=author,
            original_author=author,
            translated_author=author,
            transliterated_author=author,
            source_file=f"/test/{title}.txt",
            total_characters=0,
        )

        # Save book to database
        BOOK_DB[book_id] = book

        # Sample Chinese text patterns
        chinese_samples = [
            "第一章 初遇\n\n这是一个晴朗的早晨，阳光透过窗帘洒在地板上。李明走进了咖啡厅，看到了坐在角落里的她。",
            "第二章 相识\n\n时间过得很快，他们已经认识了三个月。每天的交谈让彼此更加了解，友谊也在慢慢加深。",
            "第三章 离别\n\n分别的日子终于到来了。机场里，两人默默相视，千言万语都化作了一个拥抱。",
        ]

        chunks = []
        for i in range(num_chunks):
            # Use sample text or generate based on chunk number
            content = chinese_samples[i % len(chinese_samples)]
            if len(content) < chunk_size:
                # Pad with more Chinese text if needed
                content += f"\n\n故事继续发展着，第{i + 1}部分的内容正在展开。" * ((chunk_size - len(content)) // 30)

            # Create variation for the original text
            variation_id = f"var_{book_id}_chunk_{i + 1}"
            chunk_id = f"chunk_{book_id}_{i + 1}"
            variation = Variation(
                variation_id=variation_id,
                book_id=book_id,
                chunk_id=chunk_id,
                chunk_number=i + 1,
                language=language,
                category="original",
                text_content=content[:chunk_size],
            )
            VARIATION_DB[variation_id] = variation

            # Create chunk
            chunk_id = f"chunk_{book_id}_{i + 1}"
            chunk = Chunk(
                chunk_id=chunk_id,
                book_id=book_id,
                chunk_number=i + 1,
                original_variation_id=variation_id,
            )
            chunk.char_count = len(content[:chunk_size])
            CHUNK_DB[chunk_id] = chunk
            chunks.append(chunk)

        # Update book's chunks list
        book.chunks = chunks

        return book, chunks


class MockTranslator:
    """A mock translator that returns realistic translations."""

    def __init__(
        self,
        fail_on_chunks: Optional[list[int]] = None,
        return_empty_on_chunks: Optional[list[int]] = None,
    ):
        self.fail_on_chunks = fail_on_chunks or []
        self.return_empty_on_chunks = return_empty_on_chunks or []
        self.translation_count = 0
        self.chunk_translations = {}
        self.is_remote = True
        self.request_count = 0
        self.MODEL_NAME = "test-model"

    def translate(self, text: str, is_last_chunk: bool = False) -> Optional[str]:
        """Translate Chinese text to English."""
        self.translation_count += 1
        self.request_count += 1

        # Determine chunk number from translation count
        chunk_number = self.translation_count

        # Check if we should fail this chunk
        if chunk_number in self.fail_on_chunks:
            return None

        # Check if we should return empty
        if chunk_number in self.return_empty_on_chunks:
            return "   "  # Whitespace only

        # Generate realistic translation based on input
        if "第一章" in text:
            translation = "Chapter 1: First Meeting\n\nIt was a clear morning, sunlight streaming through the curtains onto the floor. Li Ming walked into the coffee shop and saw her sitting in the corner."
        elif "第二章" in text:
            translation = "Chapter 2: Getting to Know Each Other\n\nTime flew by quickly, they had known each other for three months now. Daily conversations deepened their understanding, and their friendship slowly grew stronger."
        elif "第三章" in text:
            translation = "Chapter 3: Farewell\n\nThe day of parting finally arrived. At the airport, the two looked at each other silently, thousands of words condensed into a single embrace."
        else:
            # Generic translation
            translation = f"This is the translated content for chunk {chunk_number}. The story continues to unfold in this section."

        self.chunk_translations[chunk_number] = translation
        return translation

    def format_cost_summary(self) -> str:
        """Format cost summary."""
        return f"Test Model Usage:\nRequests: {self.request_count}\nEstimated Cost: ${self.request_count * 0.01:.2f}"


def create_test_logger() -> logging.Logger:
    """Create a test logger that captures log messages."""
    logger = logging.getLogger("test_logger")
    logger.setLevel(logging.DEBUG)

    # Clear any existing handlers
    logger.handlers.clear()

    # Add a handler that stores messages
    handler = logging.StreamHandler()
    handler.setLevel(logging.DEBUG)
    logger.addHandler(handler)

    # Add attribute to store messages
    logger.messages = []

    # Override log methods to capture messages
    original_log = logger._log

    def capturing_log(level, msg, args, **kwargs):
        logger.messages.append((level, msg % args if args else msg))
        original_log(level, msg, args, **kwargs)

    logger._log = capturing_log

    return logger
