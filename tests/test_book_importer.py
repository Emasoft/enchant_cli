#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test suite for book_importer module.
"""

import pytest
import uuid
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call
import logging
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from enchant_book_manager.book_importer import (
    foreign_book_title_splitter,
    import_book_from_txt,
)


class TestForeignBookTitleSplitter:
    """Test the foreign_book_title_splitter function."""

    def test_full_format(self):
        """Test parsing full format: translated by author - original by author."""
        filename = "The Journey by John Doe - 修炼之旅 by 张三.txt"
        result = foreign_book_title_splitter(filename)

        assert result[0] == "修炼之旅"  # original_title
        assert result[1] == "The Journey"  # translated_title
        assert result[2] == " n.d. "  # transliterated_title
        assert result[3] == "张三"  # original_author
        assert result[4] == "John Doe"  # translated_author
        assert result[5] == " n.d. "  # transliterated_author

    def test_only_original(self):
        """Test parsing only original title and author."""
        filename = "修炼之旅 by 张三.txt"
        result = foreign_book_title_splitter(filename)

        assert result[0] == "修炼之旅"  # original_title
        assert result[1] == ""  # translated_title
        assert result[2] == " n.d. "  # transliterated_title
        assert result[3] == "张三"  # original_author
        assert result[4] == " n.d. "  # translated_author
        assert result[5] == " n.d. "  # transliterated_author

    def test_only_title_no_author(self):
        """Test parsing only title without author."""
        filename = "修炼之旅.txt"
        result = foreign_book_title_splitter(filename)

        assert result[0] == "修炼之旅"  # original_title
        assert result[1] == ""  # translated_title (empty when no dash separator)
        assert result[2] == " n.d. "  # transliterated_title
        assert result[3] == " n.d. "  # original_author
        assert result[4] == " n.d. "  # translated_author
        assert result[5] == " n.d. "  # transliterated_author

    def test_translated_only(self):
        """Test parsing only translated part."""
        filename = "The Journey by John Doe.txt"
        result = foreign_book_title_splitter(filename)

        assert result[0] == "The Journey"  # original_title (falls back)
        assert result[1] == ""  # translated_title (empty when no dash separator)
        assert result[2] == " n.d. "  # transliterated_title
        assert result[3] == "John Doe"  # original_author (falls back)
        assert result[4] == " n.d. "  # translated_author
        assert result[5] == " n.d. "  # transliterated_author

    def test_with_path(self):
        """Test parsing with full path."""
        filename = Path("/home/user/books/The Journey by John Doe - 修炼之旅 by 张三.txt")
        result = foreign_book_title_splitter(filename)

        assert result[0] == "修炼之旅"  # original_title
        assert result[1] == "The Journey"  # translated_title
        assert result[3] == "张三"  # original_author
        assert result[4] == "John Doe"  # translated_author

    def test_no_extension(self):
        """Test parsing filename without extension."""
        filename = "The Journey by John Doe - 修炼之旅 by 张三"
        result = foreign_book_title_splitter(filename)

        # Should still parse correctly
        assert result[0] == "修炼之旅"  # original_title
        assert result[1] == "The Journey"  # translated_title


class TestImportBookFromTxt:
    """Test the import_book_from_txt function."""

    @patch("enchant_book_manager.book_importer.uuid.uuid4")
    @patch("enchant_book_manager.book_importer.manual_commit")
    @patch("enchant_book_manager.book_importer.Variation")
    @patch("enchant_book_manager.book_importer.Chunk")
    @patch("enchant_book_manager.book_importer.Book")
    @patch("enchant_book_manager.book_importer.split_chinese_text_in_parts")
    @patch("enchant_book_manager.book_importer.remove_excess_empty_lines")
    @patch("enchant_book_manager.book_importer.decode_input_file_content")
    def test_import_new_book(
        self,
        mock_decode,
        mock_remove_lines,
        mock_split,
        mock_book,
        mock_chunk,
        mock_variation,
        mock_commit,
        mock_uuid,
    ):
        """Test importing a new book successfully."""
        # Setup mocks
        mock_decode.return_value = "Original Chinese text content"
        mock_remove_lines.return_value = "Cleaned Chinese text content"
        mock_split.return_value = ["Chunk 1 content", "Chunk 2 content"]

        mock_book.get_or_none.return_value = None  # No duplicate
        mock_book_instance = MagicMock()
        mock_book_instance.book_id = "book-uuid"
        mock_book.get_by_id.return_value = mock_book_instance

        # Generate different UUIDs for book, chunks, and variations
        mock_uuid.side_effect = [
            "book-uuid",
            "chunk1-uuid",
            "variation1-uuid",
            "chunk2-uuid",
            "variation2-uuid",
        ]

        logger = Mock(spec=logging.Logger)

        # Call function
        book_id = import_book_from_txt(
            "The Journey by John Doe - 修炼之旅 by 张三.txt",
            encoding="utf-8",
            max_chars=1000,
            logger=logger,
        )

        # Verify book was created
        assert book_id == "book-uuid"
        mock_book.create.assert_called_once()
        book_create_args = mock_book.create.call_args[1]
        assert book_create_args["book_id"] == "book-uuid"
        assert book_create_args["title"] == "The Journey"  # translated_title becomes title
        assert book_create_args["author"] == "John Doe"  # translated_author
        assert book_create_args["original_title"] == "修炼之旅"
        assert book_create_args["original_author"] == "张三"
        assert book_create_args["total_characters"] == len("Cleaned Chinese text content")

        # Verify chunks were created
        assert mock_chunk.create.call_count == 2
        chunk_calls = mock_chunk.create.call_args_list

        # First chunk
        assert chunk_calls[0][1]["chunk_id"] == "chunk1-uuid"
        assert chunk_calls[0][1]["book_id"] == "book-uuid"
        assert chunk_calls[0][1]["chunk_number"] == 1
        assert chunk_calls[0][1]["original_variation_id"] == "variation1-uuid"

        # Second chunk
        assert chunk_calls[1][1]["chunk_id"] == "chunk2-uuid"
        assert chunk_calls[1][1]["book_id"] == "book-uuid"
        assert chunk_calls[1][1]["chunk_number"] == 2
        assert chunk_calls[1][1]["original_variation_id"] == "variation2-uuid"

        # Verify variations were created
        assert mock_variation.create.call_count == 2
        variation_calls = mock_variation.create.call_args_list

        # First variation
        assert variation_calls[0][1]["variation_id"] == "variation1-uuid"
        assert variation_calls[0][1]["chunk_id"] == "chunk1-uuid"
        assert variation_calls[0][1]["text_content"] == "Chunk 1 content"
        assert variation_calls[0][1]["language"] == "original"
        assert variation_calls[0][1]["category"] == "original"

        # Verify commits were called
        assert mock_commit.call_count >= 3  # After book + after each chunk/variation

    @patch("enchant_book_manager.book_importer.Book")
    def test_import_duplicate_book(self, mock_book):
        """Test importing a book that already exists."""
        # Setup duplicate book
        duplicate_book = MagicMock()
        duplicate_book.book_id = "existing-book-id"
        mock_book.get_or_none.return_value = duplicate_book

        logger = Mock(spec=logging.Logger)

        # Call function
        book_id = import_book_from_txt("existing_book.txt", logger=logger)

        # Should return existing book ID
        assert book_id == "existing-book-id"
        logger.debug.assert_any_call("ERROR - Book with filename 'existing_book.txt' was already imported in db!")

        # Should not create new book
        mock_book.create.assert_not_called()

    @patch("enchant_book_manager.book_importer.manual_commit")
    @patch("enchant_book_manager.book_importer.Book")
    @patch("enchant_book_manager.book_importer.split_chinese_text_in_parts")
    @patch("enchant_book_manager.book_importer.decode_input_file_content")
    def test_import_book_create_exception(self, mock_decode, mock_split, mock_book, mock_commit):
        """Test handling exception during book creation."""
        # Setup mocks
        mock_decode.return_value = "Text content"
        mock_split.return_value = ["Chunk 1"]
        mock_book.get_or_none.return_value = None
        mock_book.create.side_effect = Exception("Database error")

        logger = Mock(spec=logging.Logger)

        # Call function - should handle exception
        with patch("enchant_book_manager.book_importer.uuid.uuid4", return_value="test-uuid"):
            import_book_from_txt("test.txt", logger=logger)

        # Verify exception was logged
        logger.debug.assert_any_call("An exception happened when creating a new variation original for a chunk:")
        logger.debug.assert_any_call("ERROR: Database error")

        # Verify commit was still called
        mock_commit.assert_called()

    @patch("enchant_book_manager.book_importer.uuid.uuid4")
    @patch("enchant_book_manager.book_importer.manual_commit")
    @patch("enchant_book_manager.book_importer.Variation")
    @patch("enchant_book_manager.book_importer.Chunk")
    @patch("enchant_book_manager.book_importer.Book")
    @patch("enchant_book_manager.book_importer.split_chinese_text_in_parts")
    @patch("enchant_book_manager.book_importer.decode_input_file_content")
    def test_import_chunk_create_exception(
        self,
        mock_decode,
        mock_split,
        mock_book,
        mock_chunk,
        mock_variation,
        mock_commit,
        mock_uuid,
    ):
        """Test handling exception during chunk creation."""
        # Setup mocks
        mock_decode.return_value = "Text"
        mock_split.return_value = ["Chunk 1", "Chunk 2"]
        mock_book.get_or_none.return_value = None
        mock_book.get_by_id.return_value = MagicMock(book_id="book-id")

        # First chunk fails, second succeeds
        mock_chunk.create.side_effect = [Exception("Chunk error"), None]

        mock_uuid.side_effect = [
            "book-id",
            "chunk1-id",
            "var1-id",
            "chunk2-id",
            "var2-id",
        ]

        logger = Mock(spec=logging.Logger)

        # Call function
        import_book_from_txt("test.txt", logger=logger)

        # Verify exception was logged for first chunk
        logger.debug.assert_any_call("An exception happened when creating chunk n.1 with ID var1-id. ")
        logger.debug.assert_any_call("ERROR: Chunk error")

        # Verify second chunk was still processed
        assert mock_chunk.create.call_count == 2
        assert mock_variation.create.call_count == 1  # Only second chunk gets variation

    @patch("enchant_book_manager.book_importer.uuid.uuid4")
    @patch("enchant_book_manager.book_importer.manual_commit")
    @patch("enchant_book_manager.book_importer.Variation")
    @patch("enchant_book_manager.book_importer.Chunk")
    @patch("enchant_book_manager.book_importer.Book")
    @patch("enchant_book_manager.book_importer.split_chinese_text_in_parts")
    @patch("enchant_book_manager.book_importer.decode_input_file_content")
    def test_import_variation_create_exception(
        self,
        mock_decode,
        mock_split,
        mock_book,
        mock_chunk,
        mock_variation,
        mock_commit,
        mock_uuid,
    ):
        """Test handling exception during variation creation."""
        # Setup mocks
        mock_decode.return_value = "Text"
        mock_split.return_value = ["Chunk 1"]
        mock_book.get_or_none.return_value = None
        mock_book.get_by_id.return_value = MagicMock(book_id="book-id")

        mock_variation.create.side_effect = Exception("Variation error")
        mock_uuid.side_effect = ["book-id", "chunk-id", "var-id"]

        logger = Mock(spec=logging.Logger)

        # Call function
        import_book_from_txt("test.txt", logger=logger)

        # Verify exception was logged
        logger.debug.assert_any_call("An exception happened when creating a new variation original for chunk n.1:")
        logger.debug.assert_any_call("ERROR: Variation error")

        # Verify commit was still called
        assert mock_commit.call_count >= 2

    def test_import_with_path_object(self):
        """Test importing with Path object instead of string."""
        with patch("enchant_book_manager.book_importer.Book") as mock_book:
            mock_book.get_or_none.return_value = None
            mock_book.get_by_id.return_value = MagicMock(book_id="test-id")

            with patch("enchant_book_manager.book_importer.decode_input_file_content") as mock_decode:
                mock_decode.return_value = "Content"

                with patch("enchant_book_manager.book_importer.split_chinese_text_in_parts") as mock_split:
                    mock_split.return_value = []

                    with patch(
                        "enchant_book_manager.book_importer.uuid.uuid4",
                        return_value="test-uuid",
                    ):
                        # Call with Path object
                        path = Path("/home/user/book.txt")
                        result = import_book_from_txt(path)

                        # Verify Path was handled correctly
                        mock_decode.assert_called_once_with(path, logger=None)
                        mock_book.get_or_none.assert_called_once()

                        # The import should succeed
                        assert result == "test-uuid"
