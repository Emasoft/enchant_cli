#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test suite to ensure make_epub behaves as a proper library (no user prompts).
"""

import pytest
from pathlib import Path
import tempfile
import shutil
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.enchant_book_manager.make_epub import (
    ensure_dir_readable,
    ensure_output_ok,
    ensure_cover_ok,
    collect_chunks,
    ValidationError,
    create_epub_from_txt_file,
)


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests"""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


class TestLibraryBehavior:
    """Test that make_epub behaves as a proper library"""

    def test_ensure_dir_readable_no_prompts(self):
        """Library functions should not prompt for user input"""
        # Create a non-existent directory path
        bad_path = Path("/nonexistent/directory")

        # Should raise exception, not prompt user
        with pytest.raises(ValidationError) as excinfo:
            ensure_dir_readable(bad_path)

        assert "not found or not a directory" in str(excinfo.value)

    def test_ensure_output_ok_no_prompts(self):
        """Output validation should raise exceptions, not prompt"""
        # Test with non-writable path
        bad_path = Path("/root/test.epub")

        with pytest.raises(ValidationError) as excinfo:
            ensure_output_ok(bad_path, append=False)

        # Should mention permission or creation issue
        error_msg = str(excinfo.value)
        assert (
            "Cannot create directory" in error_msg or "No write permission" in error_msg
        )

    def test_ensure_cover_ok_no_prompts(self, temp_dir):
        """Cover validation should raise exceptions, not prompt"""
        # Test with non-existent file
        bad_cover = Path("/nonexistent/cover.jpg")

        with pytest.raises(ValidationError) as excinfo:
            ensure_cover_ok(bad_cover)

        assert "is not a file" in str(excinfo.value)

        # Test with wrong file type
        bad_type = temp_dir / "cover.txt"
        bad_type.write_text("not an image")

        with pytest.raises(ValidationError) as excinfo:
            ensure_cover_ok(bad_type)

        assert "must be .jpg/.jpeg/.png" in str(excinfo.value)

    def test_collect_chunks_no_prompts(self, temp_dir):
        """Chunk collection should raise exceptions, not prompt"""
        # Empty directory
        empty_dir = temp_dir / "empty"
        empty_dir.mkdir()

        with pytest.raises(ValidationError) as excinfo:
            collect_chunks(empty_dir)

        assert "No valid .txt chunks found" in str(excinfo.value)

    def test_create_epub_from_txt_file_validation_errors(self, temp_dir):
        """Main function should return errors, not exit"""
        # Test with non-existent file
        fake_file = Path("/nonexistent/file.txt")
        output_path = temp_dir / "test.epub"

        # Should raise ValidationError, not exit
        with pytest.raises(ValidationError) as excinfo:
            create_epub_from_txt_file(
                txt_file_path=fake_file,
                output_path=output_path,
                title="Test",
                author="Test",
            )

        assert "Input file not found" in str(excinfo.value)

    def test_create_epub_with_invalid_cover(self, temp_dir):
        """Test handling of invalid cover image"""
        # Create test file
        test_file = temp_dir / "test.txt"
        test_file.write_text("Chapter 1\nTest content")

        # Create invalid cover (wrong type)
        bad_cover = temp_dir / "cover.txt"
        bad_cover.write_text("not an image")

        output_path = temp_dir / "test.epub"

        # Should raise ValidationError about cover
        with pytest.raises(ValidationError) as excinfo:
            create_epub_from_txt_file(
                txt_file_path=test_file,
                output_path=output_path,
                title="Test",
                author="Test",
                cover_path=bad_cover,
            )

        assert "Cover must be .jpg/.jpeg/.png" in str(excinfo.value)

    def test_validation_mode_returns_issues(self, temp_dir):
        """Validation mode should return issues list without creating EPUB"""
        # Create test file with chapter issues
        test_file = temp_dir / "test.txt"
        test_file.write_text("""
Chapter 1
First chapter

Chapter 3
Third chapter (missing chapter 2)

Chapter 5
Fifth chapter (missing chapter 4)
""")

        output_path = temp_dir / "test.epub"

        success, issues = create_epub_from_txt_file(
            txt_file_path=test_file,
            output_path=output_path,
            title="Test",
            author="Test",
            validate=True,
            strict_mode=False,  # Don't fail, just report issues
        )

        # Should succeed but report issues
        assert success
        assert len(issues) > 0
        assert any("missing" in issue for issue in issues)
