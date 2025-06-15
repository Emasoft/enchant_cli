#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test suite for XML generation using ElementTree.
"""

import pytest
from pathlib import Path
import xml.etree.ElementTree as ET
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from make_epub import (
    build_chap_xhtml, build_cover_xhtml, build_container_xml,
    build_content_opf, build_toc_ncx
)


class TestXMLGeneration:
    """Test that all XML generation uses ElementTree properly"""
    
    def test_chapter_xhtml_generation(self):
        """Test chapter XHTML generation with proper escaping"""
        title = "Chapter 1: Test & Escaping"
        body_html = "<p>This is a test with &amp; special chars</p>"
        
        result = build_chap_xhtml(title, body_html)
        
        # Should be valid XML
        assert '<?xml version="1.0" encoding="utf-8"?>' in result
        assert '<!DOCTYPE html>' in result
        
        # Parse to verify it's valid XML
        # Remove DOCTYPE declaration for parsing
        xml_content = result.split('<!DOCTYPE html>')[1].strip()
        root = ET.fromstring(xml_content)
        
        # Check namespace
        assert root.tag == '{http://www.w3.org/1999/xhtml}html'
        
        # Check title is properly escaped
        title_elem = root.find('.//{http://www.w3.org/1999/xhtml}title')
        assert title_elem.text == "Chapter 1: Test & Escaping"
        
        # Check h1 is properly escaped
        h1_elem = root.find('.//{http://www.w3.org/1999/xhtml}h1')
        assert h1_elem.text == "Chapter 1: Test & Escaping"
    
    def test_cover_xhtml_generation(self):
        """Test cover XHTML generation"""
        img_path = "Images/cover.jpg"
        
        result = build_cover_xhtml(img_path)
        
        # Should be valid XML
        assert '<?xml version="1.0" encoding="utf-8"?>' in result
        assert '<!DOCTYPE html>' in result
        
        # Parse to verify
        xml_content = result.split('<!DOCTYPE html>')[1].strip()
        root = ET.fromstring(xml_content)
        
        # Check image element
        img_elem = root.find('.//{http://www.w3.org/1999/xhtml}img')
        assert img_elem.get('src') == '../Images/cover.jpg'
        assert img_elem.get('alt') == 'Cover'
    
    def test_container_xml_generation(self):
        """Test container.xml generation"""
        result = build_container_xml()
        
        # Should be valid XML with declaration
        assert '<?xml version' in result
        
        # Parse to verify
        root = ET.fromstring(result)
        
        # Check namespace and structure
        assert root.tag == '{urn:oasis:names:tc:opendocument:xmlns:container}container'
        assert root.get('version') == '1.0'
        
        # Check rootfile
        rootfile = root.find('.//{urn:oasis:names:tc:opendocument:xmlns:container}rootfile')
        assert rootfile.get('full-path') == 'OEBPS/content.opf'
        assert rootfile.get('media-type') == 'application/oebps-package+xml'
    
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
        assert 'Test &amp; Book &lt;Special&gt;' in result
        assert 'Author &amp; Co.' in result
        assert 'Publisher &amp; Sons' in result
        assert 'A book with &lt;special&gt; characters' in result
        assert 'Series &amp; More' in result
        
        # Should include language
        assert '<dc:language>en</dc:language>' in result
        
        # Should include metadata
        assert '<dc:publisher>' in result
        assert '<dc:description>' in result
        assert "calibre:series' content='Series &amp; More'" in result
    
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
        assert 'Book &amp; Title' in result
        assert 'Author &lt;Name&gt;' in result
        
        # Should be valid XML structure
        assert '<?xml version' in result
        assert '<!DOCTYPE ncx' in result
        assert 'urn:uuid:test-uuid' in result
    
    def test_malformed_html_handling(self):
        """Test handling of malformed HTML in chapter content"""
        title = "Test Chapter"
        # Malformed HTML (unclosed tags, etc.)
        body_html = "<p>Test paragraph<br>with break"
        
        result = build_chap_xhtml(title, body_html)
        
        # Should still produce valid XML (fallback to text)
        assert '<?xml version="1.0" encoding="utf-8"?>' in result
        
        # Try to parse result - should not raise
        xml_content = result.split('<!DOCTYPE html>')[1].strip()
        root = ET.fromstring(xml_content)
        
        # Should have created some content
        body = root.find('.//{http://www.w3.org/1999/xhtml}body')
        assert body is not None
