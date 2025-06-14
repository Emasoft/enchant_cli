#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test suite to ensure make_epub behaves as a proper library (no user prompts).
"""

import unittest
from pathlib import Path
import tempfile
import shutil
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from make_epub import (
    ensure_dir_readable, ensure_output_ok, ensure_cover_ok, 
    collect_chunks, ValidationError, create_epub_from_txt_file
)


class TestLibraryBehavior(unittest.TestCase):
    """Test that make_epub behaves as a proper library"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        shutil.rmtree(self.temp_dir)
    
    def test_ensure_dir_readable_no_prompts(self):
        """Library functions should not prompt for user input"""
        # Create a non-existent directory path
        bad_path = Path("/nonexistent/directory")
        
        # Should raise exception, not prompt user
        with self.assertRaises(ValidationError) as cm:
            ensure_dir_readable(bad_path)
        
        self.assertIn("not found or not a directory", str(cm.exception))
    
    def test_ensure_output_ok_no_prompts(self):
        """Output validation should raise exceptions, not prompt"""
        # Test with non-writable path
        bad_path = Path("/root/test.epub")
        
        with self.assertRaises(ValidationError) as cm:
            ensure_output_ok(bad_path, append=False)
        
        # Should mention permission or creation issue
        error_msg = str(cm.exception)
        self.assertTrue("Cannot create directory" in error_msg or "No write permission" in error_msg)
    
    def test_ensure_cover_ok_no_prompts(self):
        """Cover validation should raise exceptions, not prompt"""
        # Test with non-existent file
        bad_cover = Path("/nonexistent/cover.jpg")
        
        with self.assertRaises(ValidationError) as cm:
            ensure_cover_ok(bad_cover)
        
        self.assertIn("is not a file", str(cm.exception))
        
        # Test with wrong file type
        bad_type = Path(self.temp_dir) / "cover.txt"
        bad_type.write_text("not an image")
        
        with self.assertRaises(ValidationError) as cm:
            ensure_cover_ok(bad_type)
        
        self.assertIn("must be .jpg/.jpeg/.png", str(cm.exception))
    
    def test_collect_chunks_no_prompts(self):
        """Chunk collection should raise exceptions, not prompt"""
        # Empty directory
        empty_dir = Path(self.temp_dir) / "empty"
        empty_dir.mkdir()
        
        with self.assertRaises(ValidationError) as cm:
            collect_chunks(empty_dir)
        
        self.assertIn("No valid .txt chunks found", str(cm.exception))
    
    def test_create_epub_from_txt_file_validation_errors(self):
        """Main function should return errors, not exit"""
        # Test with non-existent file
        fake_file = Path("/nonexistent/file.txt")
        output_path = Path(self.temp_dir) / "test.epub"
        
        # Should raise ValidationError, not exit
        with self.assertRaises(ValidationError) as cm:
            create_epub_from_txt_file(
                txt_file_path=fake_file,
                output_path=output_path,
                title="Test",
                author="Test"
            )
        
        self.assertIn("Input file not found", str(cm.exception))
    
    def test_create_epub_with_invalid_cover(self):
        """Test handling of invalid cover image"""
        # Create test file
        test_file = Path(self.temp_dir) / "test.txt"
        test_file.write_text("Chapter 1\nTest content")
        
        # Create invalid cover (wrong type)
        bad_cover = Path(self.temp_dir) / "cover.txt"
        bad_cover.write_text("not an image")
        
        output_path = Path(self.temp_dir) / "test.epub"
        
        # Should raise ValidationError about cover
        with self.assertRaises(ValidationError) as cm:
            create_epub_from_txt_file(
                txt_file_path=test_file,
                output_path=output_path,
                title="Test",
                author="Test",
                cover_path=bad_cover
            )
        
        self.assertIn("Cover must be .jpg/.jpeg/.png", str(cm.exception))
    
    def test_validation_mode_returns_issues(self):
        """Validation mode should return issues list without creating EPUB"""
        # Create test file with chapter issues
        test_file = Path(self.temp_dir) / "test.txt"
        test_file.write_text("""
Chapter 1
First chapter

Chapter 3
Third chapter (missing chapter 2)

Chapter 5
Fifth chapter (missing chapter 4)
""")
        
        output_path = Path(self.temp_dir) / "test.epub"
        
        success, issues = create_epub_from_txt_file(
            txt_file_path=test_file,
            output_path=output_path,
            title="Test",
            author="Test",
            validate=True,
            strict_mode=False  # Don't fail, just report issues
        )
        
        # Should succeed but report issues
        self.assertTrue(success)
        self.assertGreater(len(issues), 0)
        self.assertTrue(any("missing" in issue for issue in issues))


if __name__ == '__main__':
    unittest.main()