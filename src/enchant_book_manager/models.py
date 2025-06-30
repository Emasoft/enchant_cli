#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright (c) 2025 Emasoft
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
#
# CHANGELOG:
# - Extracted data models from cli_translator.py
# - Added TranslationState enum
# - Added Book, Chunk, Variation classes
# - Added Field descriptor class
# - Added in-memory database dictionaries
#

"""Data models for the EnChANT Book Manager translation system."""

from __future__ import annotations

import enum
from typing import Any


class TranslationState(enum.Enum):
    """A description of the worker's current state."""

    PENDING = 1
    """Translation task is initialized, but not running."""
    RUNNING = 2
    """Translation task is running."""
    CANCELLED = 3
    """Translation task is not running, and was cancelled."""
    ERROR = 4
    """Translation task is not running, and exited with an error."""
    SUCCESS = 5
    """Translation task is not running, and completed successfully."""


class Field:
    """
    Simple descriptor class for field access in in-memory database.

    Allows attribute-style access and comparison operations.
    """

    def __init__(self, name: str) -> None:
        self.name = name

    def __get__(self, instance: Any, owner: type) -> Any:
        if instance is None:
            return self
        return instance.__dict__.get(self.name)

    def __set__(self, instance: Any, value: Any) -> None:
        instance.__dict__[self.name] = value

    def __eq__(self, other: Any) -> Any:
        # When used in a class-level comparison (e.g., Book.source_file == filename),
        # return a lambda that checks whether the instance's attribute equals 'other'.
        return lambda instance: getattr(instance, self.name, None) == other


class Book:
    """
    Represents a book in the translation system.

    Stores metadata about the book including titles, authors, and source file info.
    """

    # Using Field descriptor for source_file to support query comparisons
    source_file = Field("source_file")

    def __init__(
        self,
        book_id: str,
        title: str,
        original_title: str,
        translated_title: str,
        transliterated_title: str,
        author: str,
        original_author: str,
        translated_author: str,
        transliterated_author: str,
        source_file: str,
        total_characters: int,
    ) -> None:
        self.book_id = book_id
        self.title = title
        self.original_title = original_title
        self.translated_title = translated_title
        self.transliterated_title = transliterated_title
        self.author = author
        self.original_author = original_author
        self.translated_author = translated_author
        self.transliterated_author = transliterated_author
        self.source_file = source_file
        self.total_characters = total_characters
        self.chunks: list[Chunk] = []  # List to hold Chunk instances

    @classmethod
    def create(cls, **kwargs: Any) -> Book:
        """
        Create a new Book instance and add it to the database.

        Args:
            **kwargs: Book attributes (book_id, title, authors, etc.)

        Returns:
            The created Book instance
        """
        book = cls(
            book_id=kwargs.get("book_id", ""),
            title=kwargs.get("title", ""),
            original_title=kwargs.get("original_title", ""),
            translated_title=kwargs.get("translated_title", ""),
            transliterated_title=kwargs.get("transliterated_title", ""),
            author=kwargs.get("author", ""),
            original_author=kwargs.get("original_author", ""),
            translated_author=kwargs.get("translated_author", ""),
            transliterated_author=kwargs.get("transliterated_author", ""),
            source_file=kwargs.get("source_file", ""),
            total_characters=kwargs.get("total_characters", 0),
        )
        BOOK_DB[book.book_id] = book
        return book

    @classmethod
    def get_or_none(cls, condition: Any) -> Book | None:
        """
        Find a book matching the given condition.

        Args:
            condition: A callable that returns True for matching books

        Returns:
            The first matching Book instance or None
        """
        for book in BOOK_DB.values():
            if condition(book):
                return book
        return None

    @classmethod
    def get_by_id(cls, book_id: str) -> Book:
        """
        Get a book by its ID.

        Args:
            book_id: The book's unique identifier

        Returns:
            The Book instance

        Raises:
            KeyError: If book not found
        """
        book = BOOK_DB.get(book_id)
        if book is None:
            raise KeyError(f"Book with id {book_id} not found")
        return book


class Chunk:
    """
    Represents a text chunk of a book for translation.

    Books are split into chunks for manageable translation.
    """

    def __init__(self, chunk_id: str, book_id: str, chunk_number: int, original_variation_id: str) -> None:
        self.chunk_id = chunk_id
        self.book_id = book_id
        self.chunk_number = chunk_number
        self.original_variation_id = original_variation_id

    @classmethod
    def create(cls, chunk_id: str, book_id: str, chunk_number: int, original_variation_id: str) -> Chunk:
        """
        Create a new chunk and add it to the database.

        Args:
            chunk_id: Unique identifier for the chunk
            book_id: ID of the book this chunk belongs to
            chunk_number: Sequential number of this chunk
            original_variation_id: ID of the original text variation

        Returns:
            The created chunk instance
        """
        chunk = cls(chunk_id, book_id, chunk_number, original_variation_id)
        CHUNK_DB[chunk_id] = chunk
        # Also add the chunk to the corresponding Book's chunks list
        try:
            book = Book.get_by_id(book_id)
            book.chunks.append(chunk)
        except KeyError:
            # Book might not exist yet in some edge cases
            pass
        return chunk


class Variation:
    """
    Represents a text variation (original or translated) of a chunk.

    Stores the actual text content and metadata about language and category.
    """

    def __init__(
        self,
        variation_id: str,
        book_id: str,
        chunk_id: str,
        chunk_number: int,
        language: str,
        category: str,
        text_content: str,
    ) -> None:
        self.variation_id = variation_id
        self.book_id = book_id
        self.chunk_id = chunk_id
        self.chunk_number = chunk_number
        self.language = language
        self.category = category
        self.text_content = text_content

    @classmethod
    def create(cls, **kwargs: Any) -> Variation:
        """
        Create a new Variation instance and add it to the database.

        Args:
            **kwargs: Variation attributes (variation_id, text_content, etc.)

        Returns:
            The created Variation instance
        """
        variation = cls(
            variation_id=kwargs.get("variation_id", ""),
            book_id=kwargs.get("book_id", ""),
            chunk_id=kwargs.get("chunk_id", ""),
            chunk_number=kwargs.get("chunk_number", 0),
            language=kwargs.get("language", ""),
            category=kwargs.get("category", ""),
            text_content=kwargs.get("text_content", ""),
        )
        VARIATION_DB[variation.variation_id] = variation
        return variation


# In-memory "database" dictionaries
BOOK_DB: dict[str, Book] = {}
CHUNK_DB: dict[str, Chunk] = {}
VARIATION_DB: dict[str, Variation] = {}


def manual_commit() -> None:
    """
    Simulate a database commit (no-op for in-memory storage).
    """
    # Simulate a database commit. In this simple implementation, changes are already in memory.
    pass
