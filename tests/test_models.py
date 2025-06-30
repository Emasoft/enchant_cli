#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test suite for models module.
"""

import pytest
from pathlib import Path
import sys
import threading
import time

sys.path.insert(0, str(Path(__file__).parent.parent))

from enchant_book_manager.models import (
    TranslationState,
    Field,
    Book,
    Chunk,
    Variation,
    BOOK_DB,
    CHUNK_DB,
    VARIATION_DB,
    manual_commit,
)


class TestTranslationState:
    """Test the TranslationState enum."""

    def test_enum_values(self):
        """Test enum values are defined correctly."""
        assert TranslationState.PENDING.value == 1
        assert TranslationState.RUNNING.value == 2
        assert TranslationState.CANCELLED.value == 3
        assert TranslationState.ERROR.value == 4
        assert TranslationState.SUCCESS.value == 5

    def test_enum_names(self):
        """Test enum names are accessible."""
        assert TranslationState.PENDING.name == "PENDING"
        assert TranslationState.RUNNING.name == "RUNNING"
        assert TranslationState.CANCELLED.name == "CANCELLED"
        assert TranslationState.ERROR.name == "ERROR"
        assert TranslationState.SUCCESS.name == "SUCCESS"

    def test_enum_comparison(self):
        """Test enum comparison."""
        assert TranslationState.PENDING == TranslationState.PENDING
        assert TranslationState.PENDING != TranslationState.RUNNING


class TestField:
    """Test the Field descriptor class."""

    def test_field_descriptor_get(self):
        """Test Field descriptor get operation."""

        # Create a test class using Field
        class TestClass:
            test_field = Field("test_field")

        obj = TestClass()
        obj.test_field = "test_value"

        assert obj.test_field == "test_value"

    def test_field_descriptor_set(self):
        """Test Field descriptor set operation."""

        class TestClass:
            test_field = Field("test_field")

        obj = TestClass()
        obj.test_field = "initial"
        assert obj.test_field == "initial"

        obj.test_field = "updated"
        assert obj.test_field == "updated"

    def test_field_descriptor_class_access(self):
        """Test Field descriptor when accessed from class."""

        class TestClass:
            test_field = Field("test_field")

        # Accessing from class should return the descriptor itself
        assert isinstance(TestClass.test_field, Field)

    def test_field_descriptor_comparison(self):
        """Test Field descriptor comparison."""

        class TestClass:
            test_field = Field("test_field")

        # Create comparison function
        compare_func = TestClass.test_field == "test_value"

        obj1 = TestClass()
        obj1.test_field = "test_value"
        assert compare_func(obj1) is True

        obj2 = TestClass()
        obj2.test_field = "other_value"
        assert compare_func(obj2) is False

    def test_field_descriptor_unset(self):
        """Test Field descriptor with unset attribute."""

        class TestClass:
            test_field = Field("test_field")

        obj = TestClass()
        # Unset field should return None
        assert obj.test_field is None


class TestBook:
    """Test the Book class."""

    def setup_method(self):
        """Clear the database before each test."""
        BOOK_DB.clear()
        CHUNK_DB.clear()
        VARIATION_DB.clear()

    def test_book_initialization(self):
        """Test Book initialization."""
        book = Book(
            book_id="test-id",
            title="Test Title",
            original_title="原标题",
            translated_title="Translated Title",
            transliterated_title="Pinyin Title",
            author="Test Author",
            original_author="原作者",
            translated_author="Translated Author",
            transliterated_author="Pinyin Author",
            source_file="test.txt",
            total_characters=1000,
        )

        assert book.book_id == "test-id"
        assert book.title == "Test Title"
        assert book.original_title == "原标题"
        assert book.translated_title == "Translated Title"
        assert book.transliterated_title == "Pinyin Title"
        assert book.author == "Test Author"
        assert book.original_author == "原作者"
        assert book.translated_author == "Translated Author"
        assert book.transliterated_author == "Pinyin Author"
        assert book.source_file == "test.txt"
        assert book.total_characters == 1000
        assert book.chunks == []

    def test_book_create(self):
        """Test Book.create() method."""
        book = Book.create(
            book_id="created-id",
            title="Created Title",
            original_title="创建标题",
            translated_title="Created Title Trans",
            author="Created Author",
            source_file="created.txt",
            total_characters=500,
        )

        assert isinstance(book, Book)
        assert book.book_id == "created-id"
        assert book.title == "Created Title"
        assert book.original_title == "创建标题"
        assert book.source_file == "created.txt"
        assert book.total_characters == 500

        # Verify it was added to database
        assert BOOK_DB["created-id"] == book

    def test_book_create_with_defaults(self):
        """Test Book.create() with missing fields uses defaults."""
        book = Book.create(book_id="minimal-id")

        assert book.book_id == "minimal-id"
        assert book.title == ""
        assert book.original_title == ""
        assert book.translated_title == ""
        assert book.transliterated_title == ""
        assert book.author == ""
        assert book.original_author == ""
        assert book.translated_author == ""
        assert book.transliterated_author == ""
        assert book.source_file == ""
        assert book.total_characters == 0

    def test_book_get_by_id(self):
        """Test Book.get_by_id() method."""
        # Create a book
        book = Book.create(book_id="find-me", title="Find Me")

        # Find it by ID
        found = Book.get_by_id("find-me")
        assert found == book
        assert found.title == "Find Me"

    def test_book_get_by_id_not_found(self):
        """Test Book.get_by_id() with non-existent ID."""
        with pytest.raises(KeyError, match="Book with id non-existent not found"):
            Book.get_by_id("non-existent")

    def test_book_get_or_none_found(self):
        """Test Book.get_or_none() when book is found."""
        # Create some books
        book1 = Book.create(book_id="book1", source_file="file1.txt")
        book2 = Book.create(book_id="book2", source_file="file2.txt")

        # Find by source_file using Field descriptor
        found = Book.get_or_none(Book.source_file == "file2.txt")
        assert found == book2

    def test_book_get_or_none_not_found(self):
        """Test Book.get_or_none() when book is not found."""
        Book.create(book_id="book1", source_file="file1.txt")

        # Search for non-existent file
        found = Book.get_or_none(Book.source_file == "non-existent.txt")
        assert found is None

    def test_book_get_or_none_custom_condition(self):
        """Test Book.get_or_none() with custom condition."""
        Book.create(book_id="book1", title="Short")
        Book.create(book_id="book2", title="Very Long Title")

        # Find book with title longer than 10 characters
        found = Book.get_or_none(lambda book: len(book.title) > 10)
        assert found is not None
        assert found.title == "Very Long Title"

    def test_book_chunks_list(self):
        """Test that chunks are added to book's chunks list."""
        book = Book.create(book_id="book-with-chunks")

        # Create chunks for this book
        chunk1 = Chunk.create("chunk1", "book-with-chunks", 1, "var1")
        chunk2 = Chunk.create("chunk2", "book-with-chunks", 2, "var2")

        assert len(book.chunks) == 2
        assert chunk1 in book.chunks
        assert chunk2 in book.chunks


class TestChunk:
    """Test the Chunk class."""

    def setup_method(self):
        """Clear the database before each test."""
        BOOK_DB.clear()
        CHUNK_DB.clear()
        VARIATION_DB.clear()

    def test_chunk_initialization(self):
        """Test Chunk initialization."""
        chunk = Chunk(
            chunk_id="chunk-id",
            book_id="book-id",
            chunk_number=1,
            original_variation_id="var-id",
        )

        assert chunk.chunk_id == "chunk-id"
        assert chunk.book_id == "book-id"
        assert chunk.chunk_number == 1
        assert chunk.original_variation_id == "var-id"

    def test_chunk_create(self):
        """Test Chunk.create() method."""
        # First create a book
        book = Book.create(book_id="test-book")

        # Create chunk
        chunk = Chunk.create(
            chunk_id="test-chunk",
            book_id="test-book",
            chunk_number=1,
            original_variation_id="test-var",
        )

        assert isinstance(chunk, Chunk)
        assert chunk.chunk_id == "test-chunk"
        assert chunk.book_id == "test-book"
        assert chunk.chunk_number == 1
        assert chunk.original_variation_id == "test-var"

        # Verify it was added to database
        assert CHUNK_DB["test-chunk"] == chunk

        # Verify it was added to book's chunks list
        assert chunk in book.chunks

    def test_chunk_create_book_not_found(self):
        """Test Chunk.create() when book doesn't exist."""
        # This should NOT raise an error anymore - it's handled gracefully
        chunk = Chunk.create(
            chunk_id="orphan-chunk",
            book_id="non-existent-book",
            chunk_number=1,
            original_variation_id="var",
        )

        # Verify the chunk was created
        assert chunk.chunk_id == "orphan-chunk"
        assert chunk.book_id == "non-existent-book"
        assert chunk.chunk_number == 1
        assert chunk.original_variation_id == "var"

        # Verify it's in the database
        assert CHUNK_DB["orphan-chunk"] == chunk


class TestVariation:
    """Test the Variation class."""

    def setup_method(self):
        """Clear the database before each test."""
        BOOK_DB.clear()
        CHUNK_DB.clear()
        VARIATION_DB.clear()

    def test_variation_initialization(self):
        """Test Variation initialization."""
        variation = Variation(
            variation_id="var-id",
            book_id="book-id",
            chunk_id="chunk-id",
            chunk_number=1,
            language="original",
            category="original",
            text_content="Test content",
        )

        assert variation.variation_id == "var-id"
        assert variation.book_id == "book-id"
        assert variation.chunk_id == "chunk-id"
        assert variation.chunk_number == 1
        assert variation.language == "original"
        assert variation.category == "original"
        assert variation.text_content == "Test content"

    def test_variation_create(self):
        """Test Variation.create() method."""
        variation = Variation.create(
            variation_id="created-var",
            book_id="test-book",
            chunk_id="test-chunk",
            chunk_number=2,
            language="english",
            category="translated",
            text_content="Translated text",
        )

        assert isinstance(variation, Variation)
        assert variation.variation_id == "created-var"
        assert variation.book_id == "test-book"
        assert variation.chunk_id == "test-chunk"
        assert variation.chunk_number == 2
        assert variation.language == "english"
        assert variation.category == "translated"
        assert variation.text_content == "Translated text"

        # Verify it was added to database
        assert VARIATION_DB["created-var"] == variation

    def test_variation_create_with_defaults(self):
        """Test Variation.create() with missing fields uses defaults."""
        variation = Variation.create(variation_id="minimal-var")

        assert variation.variation_id == "minimal-var"
        assert variation.book_id == ""
        assert variation.chunk_id == ""
        assert variation.chunk_number == 0
        assert variation.language == ""
        assert variation.category == ""
        assert variation.text_content == ""


class TestDatabases:
    """Test the in-memory database dictionaries."""

    def setup_method(self):
        """Clear the database before each test."""
        BOOK_DB.clear()
        CHUNK_DB.clear()
        VARIATION_DB.clear()

    def test_databases_are_dictionaries(self):
        """Test that databases are dictionaries."""
        assert isinstance(BOOK_DB, dict)
        assert isinstance(CHUNK_DB, dict)
        assert isinstance(VARIATION_DB, dict)

    def test_databases_start_empty(self):
        """Test that databases start empty after clear."""
        assert len(BOOK_DB) == 0
        assert len(CHUNK_DB) == 0
        assert len(VARIATION_DB) == 0

    def test_multiple_items_in_database(self):
        """Test storing multiple items in databases."""
        # Create multiple books
        book1 = Book.create(book_id="book1")
        book2 = Book.create(book_id="book2")
        book3 = Book.create(book_id="book3")

        assert len(BOOK_DB) == 3
        assert "book1" in BOOK_DB
        assert "book2" in BOOK_DB
        assert "book3" in BOOK_DB

        # Create chunks
        chunk1 = Chunk.create("chunk1", "book1", 1, "var1")
        chunk2 = Chunk.create("chunk2", "book1", 2, "var2")

        assert len(CHUNK_DB) == 2

        # Create variations
        var1 = Variation.create(variation_id="var1", chunk_id="chunk1")
        var2 = Variation.create(variation_id="var2", chunk_id="chunk2")

        assert len(VARIATION_DB) == 2


class TestManualCommit:
    """Test the manual_commit function."""

    def test_manual_commit_runs(self):
        """Test that manual_commit can be called without error."""
        # Should not raise any exception
        manual_commit()

        # Call it multiple times
        for _ in range(10):
            manual_commit()


class TestIntegration:
    """Integration tests for the models working together."""

    def setup_method(self):
        """Clear the database before each test."""
        BOOK_DB.clear()
        CHUNK_DB.clear()
        VARIATION_DB.clear()

    def test_complete_book_structure(self):
        """Test creating a complete book with chunks and variations."""
        # Create a book
        book = Book.create(
            book_id="full-book",
            title="Complete Book",
            original_title="完整的书",
            author="Test Author",
            source_file="complete.txt",
            total_characters=10000,
        )

        # Create chunks for the book
        chunks = []
        for i in range(3):
            chunk = Chunk.create(
                chunk_id=f"chunk-{i}",
                book_id="full-book",
                chunk_number=i + 1,
                original_variation_id=f"orig-var-{i}",
            )
            chunks.append(chunk)

        # Create original variations
        for i, chunk in enumerate(chunks):
            Variation.create(
                variation_id=f"orig-var-{i}",
                book_id="full-book",
                chunk_id=chunk.chunk_id,
                chunk_number=chunk.chunk_number,
                language="chinese",
                category="original",
                text_content=f"原始文本 {i}",
            )

        # Create translated variations
        for i, chunk in enumerate(chunks):
            Variation.create(
                variation_id=f"trans-var-{i}",
                book_id="full-book",
                chunk_id=chunk.chunk_id,
                chunk_number=chunk.chunk_number,
                language="english",
                category="translated",
                text_content=f"Translated text {i}",
            )

        # Verify complete structure
        assert len(book.chunks) == 3
        assert len(CHUNK_DB) == 3
        assert len(VARIATION_DB) == 6  # 3 original + 3 translated

        # Verify chunk numbers
        for i, chunk in enumerate(book.chunks):
            assert chunk.chunk_number == i + 1

    def test_field_descriptor_in_queries(self):
        """Test using Field descriptor for complex queries."""
        # Create books with different attributes
        Book.create(
            book_id="book1",
            source_file="novel1.txt",
            title="Short",
            total_characters=1000,
        )
        Book.create(
            book_id="book2",
            source_file="novel2.txt",
            title="Medium Length Title",
            total_characters=5000,
        )
        Book.create(
            book_id="book3",
            source_file="novel3.txt",
            title="Very Very Long Title Indeed",
            total_characters=10000,
        )

        # Test various query conditions

        # Find by exact source_file match
        book = Book.get_or_none(Book.source_file == "novel2.txt")
        assert book is not None
        assert book.book_id == "book2"

        # Find by custom condition (title length)
        long_title_book = Book.get_or_none(lambda b: len(b.title) > 20)
        assert long_title_book is not None
        assert long_title_book.book_id == "book3"

        # Find by character count
        large_book = Book.get_or_none(lambda b: b.total_characters >= 10000)
        assert large_book is not None
        assert large_book.book_id == "book3"

        # Complex condition
        medium_book = Book.get_or_none(lambda b: 4000 < b.total_characters < 6000 and "Medium" in b.title)
        assert medium_book is not None
        assert medium_book.book_id == "book2"


class TestThreadSafety:
    """Test thread safety of database operations."""

    def setup_method(self):
        """Clear the database before each test."""
        BOOK_DB.clear()
        CHUNK_DB.clear()
        VARIATION_DB.clear()

    def test_concurrent_book_creation(self):
        """Test creating books from multiple threads."""
        errors = []
        created_ids = []

        def create_books(thread_id: int):
            """Create books in a thread."""
            try:
                for i in range(10):
                    book_id = f"book-{thread_id}-{i}"
                    book = Book.create(book_id=book_id, title=f"Book {thread_id}-{i}", source_file=f"file{thread_id}-{i}.txt", total_characters=thread_id * 1000 + i)
                    created_ids.append(book_id)
                    # Small delay to increase chance of race conditions
                    time.sleep(0.001)
            except Exception as e:
                errors.append(e)

        # Create multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=create_books, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Check results
        assert len(errors) == 0, f"Thread errors: {errors}"
        assert len(BOOK_DB) == 50  # 5 threads * 10 books each

        # Verify all books were created correctly
        for book_id in created_ids:
            assert book_id in BOOK_DB
            book = BOOK_DB[book_id]
            assert book.book_id == book_id

    def test_concurrent_chunk_creation(self):
        """Test creating chunks from multiple threads."""
        # First create a book
        book = Book.create(book_id="shared-book", title="Shared Book")

        errors = []

        def create_chunks(thread_id: int):
            """Create chunks in a thread."""
            try:
                for i in range(10):
                    chunk = Chunk.create(chunk_id=f"chunk-{thread_id}-{i}", book_id="shared-book", chunk_number=thread_id * 10 + i, original_variation_id=f"var-{thread_id}-{i}")
                    time.sleep(0.001)
            except Exception as e:
                errors.append(e)

        # Create multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=create_chunks, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # Check results
        assert len(errors) == 0, f"Thread errors: {errors}"
        assert len(CHUNK_DB) == 50
        assert len(book.chunks) == 50

    def test_concurrent_reads_and_writes(self):
        """Test concurrent reads and writes to the database."""
        # Pre-populate some books
        for i in range(10):
            Book.create(book_id=f"existing-{i}", source_file=f"file{i}.txt")

        errors = []
        read_results = []

        def reader_thread():
            """Thread that reads from database."""
            try:
                for _ in range(20):
                    # Try various read operations
                    book = Book.get_or_none(lambda b: b.source_file == "file5.txt")
                    if book:
                        read_results.append(book.book_id)

                    # Also try get_by_id
                    try:
                        book = Book.get_by_id("existing-3")
                        read_results.append(book.book_id)
                    except KeyError:
                        pass

                    time.sleep(0.001)
            except Exception as e:
                errors.append(("reader", e))

        def writer_thread(thread_id: int):
            """Thread that writes to database."""
            try:
                for i in range(10):
                    Book.create(book_id=f"new-{thread_id}-{i}", title=f"New Book {thread_id}-{i}", source_file=f"new{thread_id}-{i}.txt")
                    time.sleep(0.002)
            except Exception as e:
                errors.append(("writer", e))

        # Start mixed reader and writer threads
        threads = []

        # 3 reader threads
        for _ in range(3):
            thread = threading.Thread(target=reader_thread)
            threads.append(thread)
            thread.start()

        # 2 writer threads
        for i in range(2):
            thread = threading.Thread(target=writer_thread, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # Check results
        assert len(errors) == 0, f"Thread errors: {errors}"

        # Should have original 10 + 20 new books
        assert len(BOOK_DB) == 30

        # Read results should be consistent
        assert len(read_results) > 0
