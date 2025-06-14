#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test suite for EPUB customization features (CSS, language, metadata).
"""

import unittest
from pathlib import Path
import tempfile
import shutil
import zipfile
import xml.etree.ElementTree as ET
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from make_epub import create_epub_from_txt_file


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
        output_path = Path(self.temp_dir) / "test.epub"
        custom_css = """
        body { font-family: 'Noto Sans', sans-serif; }
        h1 { color: #333; }
        p { line-height: 1.6; }
        """
        
        success, issues = create_epub_from_txt_file(
            txt_file_path=self.test_file,
            output_path=output_path,
            title="Test Book",
            author="Test Author",
            custom_css=custom_css
        )
        
        self.assertTrue(success)
        self.assertTrue(output_path.exists())
        
        # Verify CSS was applied
        with zipfile.ZipFile(output_path, 'r') as z:
            css_content = z.read('OEBPS/Styles/style.css').decode('utf-8')
            self.assertIn('Noto Sans', css_content)
            self.assertIn('color: #333', css_content)
            self.assertIn('line-height: 1.6', css_content)
    
    def test_language_configuration(self):
        """Test that language can be configured"""
        output_path = Path(self.temp_dir) / "test.epub"
        
        success, issues = create_epub_from_txt_file(
            txt_file_path=self.test_file,
            output_path=output_path,
            title="Test Book",
            author="Test Author",
            language="zh"
        )
        
        self.assertTrue(success)
        self.assertTrue(output_path.exists())
        
        # Verify language in OPF
        with zipfile.ZipFile(output_path, 'r') as z:
            opf_content = z.read('OEBPS/content.opf').decode('utf-8')
            self.assertIn('<dc:language>zh</dc:language>', opf_content)
    
    def test_metadata_support(self):
        """Test that additional metadata can be added"""
        output_path = Path(self.temp_dir) / "test.epub"
        metadata = {
            'publisher': 'Test Publisher',
            'description': 'Test description',
            'series': 'Test Series',
            'series_index': 1
        }
        
        success, issues = create_epub_from_txt_file(
            txt_file_path=self.test_file,
            output_path=output_path,
            title="Test Book",
            author="Test Author",
            metadata=metadata
        )
        
        self.assertTrue(success)
        self.assertTrue(output_path.exists())
        
        # Verify metadata in OPF
        with zipfile.ZipFile(output_path, 'r') as z:
            opf_content = z.read('OEBPS/content.opf').decode('utf-8')
            self.assertIn('Test Publisher', opf_content)
            self.assertIn('Test description', opf_content)
            self.assertIn('Test Series', opf_content)
            self.assertIn("calibre:series_index' content='1'", opf_content)
    
    def test_default_css_when_none_provided(self):
        """Test that default CSS is used when custom CSS is not provided"""
        output_path = Path(self.temp_dir) / "test.epub"
        
        success, issues = create_epub_from_txt_file(
            txt_file_path=self.test_file,
            output_path=output_path,
            title="Test Book",
            author="Test Author"
        )
        
        self.assertTrue(success)
        
        # Verify default CSS was applied
        with zipfile.ZipFile(output_path, 'r') as z:
            css_content = z.read('OEBPS/Styles/style.css').decode('utf-8')
            # Check for default CSS patterns
            self.assertIn('body{font-family:serif', css_content)
            self.assertIn('line-height:1.4', css_content)
            self.assertIn('text-indent:1.5em', css_content)
    
    def test_multiple_customizations_together(self):
        """Test combining language, CSS, and metadata customizations"""
        output_path = Path(self.temp_dir) / "test.epub"
        
        custom_css = "body { font-family: 'Source Han Sans', sans-serif; }"
        metadata = {
            'publisher': 'EnChANT Publishing',
            'description': 'A translated novel',
            'original_title': '测试小说',
            'original_author': '测试作者'
        }
        
        success, issues = create_epub_from_txt_file(
            txt_file_path=self.test_file,
            output_path=output_path,
            title="Test Novel",
            author="Test Author",
            language="en",
            custom_css=custom_css,
            metadata=metadata
        )
        
        self.assertTrue(success)
        
        with zipfile.ZipFile(output_path, 'r') as z:
            # Check CSS
            css_content = z.read('OEBPS/Styles/style.css').decode('utf-8')
            self.assertIn('Source Han Sans', css_content)
            
            # Check OPF for language and metadata
            opf_content = z.read('OEBPS/content.opf').decode('utf-8')
            self.assertIn('<dc:language>en</dc:language>', opf_content)
            self.assertIn('EnChANT Publishing', opf_content)
            self.assertIn('A translated novel', opf_content)


if __name__ == '__main__':
    unittest.main()