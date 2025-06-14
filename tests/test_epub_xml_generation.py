#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test suite for XML generation using ElementTree.
"""

import unittest
from pathlib import Path
import xml.etree.ElementTree as ET
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from make_epub import (
    build_chap_xhtml, build_cover_xhtml, build_container_xml,
    build_content_opf, build_toc_ncx
)


class TestXMLGeneration(unittest.TestCase):
    """Test that all XML generation uses ElementTree properly"""
    
    def test_chapter_xhtml_generation(self):
        """Test chapter XHTML generation with proper escaping"""
        title = "Chapter 1: Test & Escaping"
        body_html = "<p>This is a test with &amp; special chars</p>"
        
        result = build_chap_xhtml(title, body_html)
        
        # Should be valid XML
        self.assertIn('<?xml version="1.0" encoding="utf-8"?>', result)
        self.assertIn('<!DOCTYPE html>', result)
        
        # Parse to verify it's valid XML
        # Remove DOCTYPE declaration for parsing
        xml_content = result.split('<!DOCTYPE html>')[1].strip()
        root = ET.fromstring(xml_content)
        
        # Check namespace
        self.assertEqual(root.tag, '{http://www.w3.org/1999/xhtml}html')
        
        # Check title is properly escaped
        title_elem = root.find('.//{http://www.w3.org/1999/xhtml}title')
        self.assertEqual(title_elem.text, "Chapter 1: Test & Escaping")
        
        # Check h1 is properly escaped
        h1_elem = root.find('.//{http://www.w3.org/1999/xhtml}h1')
        self.assertEqual(h1_elem.text, "Chapter 1: Test & Escaping")
    
    def test_cover_xhtml_generation(self):
        """Test cover XHTML generation"""
        img_path = "Images/cover.jpg"
        
        result = build_cover_xhtml(img_path)
        
        # Should be valid XML
        self.assertIn('<?xml version="1.0" encoding="utf-8"?>', result)
        self.assertIn('<!DOCTYPE html>', result)
        
        # Parse to verify
        xml_content = result.split('<!DOCTYPE html>')[1].strip()
        root = ET.fromstring(xml_content)
        
        # Check image element
        img_elem = root.find('.//{http://www.w3.org/1999/xhtml}img')
        self.assertEqual(img_elem.get('src'), '../Images/cover.jpg')
        self.assertEqual(img_elem.get('alt'), 'Cover')
    
    def test_container_xml_generation(self):
        """Test container.xml generation"""
        result = build_container_xml()
        
        # Should be valid XML with declaration
        self.assertIn('<?xml version', result)
        
        # Parse to verify
        root = ET.fromstring(result)
        
        # Check namespace and structure
        self.assertEqual(root.tag, '{urn:oasis:names:tc:opendocument:xmlns:container}container')
        self.assertEqual(root.get('version'), '1.0')
        
        # Check rootfile
        rootfile = root.find('.//{urn:oasis:names:tc:opendocument:xmlns:container}rootfile')
        self.assertEqual(rootfile.get('full-path'), 'OEBPS/content.opf')
        self.assertEqual(rootfile.get('media-type'), 'application/oebps-package+xml')
    
    def test_content_opf_with_special_chars(self):
        """Test OPF generation with special characters"""
        title = "Test & Book <Special>"
        author = "Author & Co."
        manifest = ['<item id="test" href="test.xhtml"/>']
        spine = ['<itemref idref="test"/>']
        uid = "test-uuid"
        cover_id = "cover-img"
        language = "en"
        metadata = {
            'publisher': 'Publisher & Sons',
            'description': 'A book with <special> characters',
            'series': 'Series & More',
            'series_index': 1
        }
        
        result = build_content_opf(title, author, manifest, spine, uid, cover_id, language, metadata)
        
        # Should contain properly escaped characters
        self.assertIn('Test &amp; Book &lt;Special&gt;', result)
        self.assertIn('Author &amp; Co.', result)
        self.assertIn('Publisher &amp; Sons', result)
        self.assertIn('A book with &lt;special&gt; characters', result)
        self.assertIn('Series &amp; More', result)
        
        # Should include language
        self.assertIn('<dc:language>en</dc:language>', result)
        
        # Should include metadata
        self.assertIn('<dc:publisher>', result)
        self.assertIn('<dc:description>', result)
        self.assertIn("calibre:series' content='Series &amp; More'", result)
    
    def test_toc_ncx_with_special_chars(self):
        """Test NCX generation with special characters"""
        title = "Book & Title"
        author = "Author <Name>"
        nav_points = [
            '<navPoint id="nav1" playOrder="1"><navLabel><text>Chapter &amp; 1</text></navLabel><content src="chapter1.xhtml"/></navPoint>'
        ]
        uid = "test-uuid"
        
        result = build_toc_ncx(title, author, nav_points, uid)
        
        # Should contain properly escaped characters
        self.assertIn('Book &amp; Title', result)
        self.assertIn('Author &lt;Name&gt;', result)
        
        # Should be valid XML structure
        self.assertIn('<?xml version', result)
        self.assertIn('<!DOCTYPE ncx', result)
        self.assertIn('urn:uuid:test-uuid', result)
    
    def test_malformed_html_handling(self):
        """Test handling of malformed HTML in chapter content"""
        title = "Test Chapter"
        # Malformed HTML (unclosed tags, etc.)
        body_html = "<p>Test paragraph<br>with break"
        
        result = build_chap_xhtml(title, body_html)
        
        # Should still produce valid XML (fallback to text)
        self.assertIn('<?xml version="1.0" encoding="utf-8"?>', result)
        
        # Try to parse result - should not raise
        xml_content = result.split('<!DOCTYPE html>')[1].strip()
        root = ET.fromstring(xml_content)
        
        # Should have created some content
        body = root.find('.//{http://www.w3.org/1999/xhtml}body')
        self.assertIsNotNone(body)


if __name__ == '__main__':
    unittest.main()