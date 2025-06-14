#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test suite for EPUB features that should be implemented.
Using TDD - writing tests for features before implementation.
"""

import unittest
from pathlib import Path
import tempfile
import shutil
import zipfile
import xml.etree.ElementTree as ET
from unittest.mock import patch, MagicMock

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestEPUBCustomization(unittest.TestCase):
    """Test EPUB customization features"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.test_file = Path(self.temp_dir) / "test_book.txt"
        self.test_file.write_text("Chapter 1\nTest content\n\nChapter 2\nMore content")
    
    def tearDown(self):
        shutil.rmtree(self.temp_dir)
    
    def test_custom_css_support(self):
        """Test that custom CSS can be provided and used"""
        from make_epub import create_epub_from_txt_file
        
        output_path = Path(self.temp_dir) / "test.epub"
        custom_css = """
        body { font-family: 'Noto Sans', sans-serif; }
        h1 { color: #333; }
        """
        
        # This should accept custom_css parameter
        success, issues = create_epub_from_txt_file(
            txt_file_path=self.test_file,
            output_path=output_path,
            title="Test Book",
            author="Test Author",
            custom_css=custom_css  # Currently not supported
        )
        
        # Verify CSS was applied
        with zipfile.ZipFile(output_path, 'r') as z:
            css_content = z.read('OEBPS/Styles/style.css').decode('utf-8')
            self.assertIn('Noto Sans', css_content)
    
    def test_language_configuration(self):
        """Test that language can be configured"""
        from make_epub import create_epub_from_txt_file
        
        output_path = Path(self.temp_dir) / "test.epub"
        
        # This should accept language parameter
        success, issues = create_epub_from_txt_file(
            txt_file_path=self.test_file,
            output_path=output_path,
            title="Test Book",
            author="Test Author",
            language="zh"  # Currently not supported
        )
        
        # Verify language in OPF
        with zipfile.ZipFile(output_path, 'r') as z:
            opf_content = z.read('OEBPS/content.opf').decode('utf-8')
            self.assertIn('<dc:language>zh</dc:language>', opf_content)
    
    def test_metadata_support(self):
        """Test that additional metadata can be added"""
        from make_epub import create_epub_from_txt_file
        
        output_path = Path(self.temp_dir) / "test.epub"
        metadata = {
            'publisher': 'Test Publisher',
            'description': 'Test description',
            'series': 'Test Series',
            'series_index': 1
        }
        
        # This should accept metadata parameter
        success, issues = create_epub_from_txt_file(
            txt_file_path=self.test_file,
            output_path=output_path,
            title="Test Book",
            author="Test Author",
            metadata=metadata  # Currently not supported
        )
        
        # Verify metadata in OPF
        with zipfile.ZipFile(output_path, 'r') as z:
            opf_content = z.read('OEBPS/content.opf').decode('utf-8')
            self.assertIn('Test Publisher', opf_content)
            self.assertIn('Test description', opf_content)


class TestLibraryBehavior(unittest.TestCase):
    """Test that make_epub behaves as a proper library"""
    
    def test_no_user_prompts(self):
        """Library functions should not prompt for user input"""
        from make_epub import ensure_dir_readable, ValidationError
        
        # Create a non-existent directory path
        bad_path = Path("/nonexistent/directory")
        
        # Should raise exception, not prompt user
        with self.assertRaises(ValidationError):
            ensure_dir_readable(bad_path)
    
    def test_validation_returns_errors(self):
        """Validation functions should return errors, not exit"""
        from make_epub import create_epub_from_txt_file
        
        # Test with non-existent file
        fake_file = Path("/nonexistent/file.txt")
        output_path = Path("/tmp/test.epub")
        
        # Should return failure and errors, not exit
        success, issues = create_epub_from_txt_file(
            txt_file_path=fake_file,
            output_path=output_path,
            title="Test",
            author="Test"
        )
        
        self.assertFalse(success)
        self.assertGreater(len(issues), 0)
        self.assertIn("not found", str(issues[0]))


class TestXMLGeneration(unittest.TestCase):
    """Test that all XML generation uses ElementTree"""
    
    def test_opf_uses_elementtree(self):
        """OPF generation should use ElementTree, not string concatenation"""
        from make_epub import build_content_opf_safe
        
        # This function should exist and use ElementTree
        manifest = ['<item id="test" href="test.xhtml"/>']
        spine = ['<itemref idref="test"/>']
        
        opf_tree = build_content_opf_safe(
            title="Test & Book",
            author="Test <Author>",
            manifest=manifest,
            spine=spine,
            uid="test-uuid",
            cover_id=None,
            language="en",
            metadata={}
        )
        
        # Should return ElementTree, not string
        self.assertIsInstance(opf_tree, ET.Element)
        
        # Verify proper escaping
        title_elem = opf_tree.find('.//{http://purl.org/dc/elements/1.1/}title')
        self.assertEqual(title_elem.text, "Test & Book")
    
    def test_ncx_uses_elementtree(self):
        """NCX generation should use ElementTree"""
        from make_epub import build_toc_ncx_safe
        
        # This function should exist and use ElementTree
        nav_points = [
            {'id': 'nav1', 'play_order': 1, 'title': 'Chapter 1', 'src': 'chapter1.xhtml'}
        ]
        
        ncx_tree = build_toc_ncx_safe(
            title="Test & Book",
            author="Test <Author>",
            nav_points=nav_points,
            uid="test-uuid"
        )
        
        # Should return ElementTree
        self.assertIsInstance(ncx_tree, ET.Element)


if __name__ == '__main__':
    unittest.main()