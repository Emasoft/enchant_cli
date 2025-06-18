#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test suite for proper XML generation using ElementTree.
"""

import xml.etree.ElementTree as ET
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestXMLGenerationElementTree:
    """Test XML generation using ElementTree instead of string concatenation"""
    
    def test_chapter_xhtml_generation(self):
        """Test generating chapter XHTML using ElementTree"""
        # Create the XHTML structure
        html = ET.Element('html', xmlns='http://www.w3.org/1999/xhtml')
        
        # Head element
        head = ET.SubElement(html, 'head')
        ET.SubElement(head, 'title').text = "Chapter 1: Test Chapter"
        link = ET.SubElement(head, 'link')
        link.set('href', '../Styles/style.css')
        link.set('rel', 'stylesheet')
        link.set('type', 'text/css')
        
        # Body element
        body = ET.SubElement(html, 'body')
        ET.SubElement(body, 'h1').text = "Chapter 1: Test Chapter"
        
        # Add paragraphs
        p1 = ET.SubElement(body, 'p')
        p1.text = "This is the first paragraph."
        
        p2 = ET.SubElement(body, 'p')
        p2.text = "This is the second paragraph with "
        em = ET.SubElement(p2, 'em')
        em.text = "emphasis"
        em.tail = "."
        
        # Convert to string
        ET.register_namespace('', 'http://www.w3.org/1999/xhtml')
        tree = ET.ElementTree(html)
        
        # Verify structure
        assert html.tag == 'html'
        assert html.get('xmlns') == 'http://www.w3.org/1999/xhtml'
        assert head.find('title').text == "Chapter 1: Test Chapter"
        assert body.find('h1').text == "Chapter 1: Test Chapter"
    
    def test_special_character_escaping(self):
        """Test that special characters are properly escaped"""
        # Characters that need escaping
        test_title = "Test & Book <with> \"quotes\" and 'apostrophes'"
        test_attr = "attribute with \"quotes\" & special <chars>"
        
        # Create element
        html = ET.Element('html')
        head = ET.SubElement(html, 'head')
        title_elem = ET.SubElement(head, 'title')
        title_elem.text = test_title
        
        # Add an attribute to test attribute escaping
        head.set('data-test', test_attr)
        
        # Convert to string
        xml_str = ET.tostring(html, encoding='unicode')
        
        # Verify text content escaping (& and < > are escaped, quotes are not in text)
        assert "Test &amp; Book" in xml_str
        assert "&lt;with&gt;" in xml_str
        # In text content, quotes don't need escaping
        assert '"quotes"' in xml_str
        
        # Verify attribute escaping (quotes ARE escaped in attributes)
        assert 'data-test="attribute with &quot;quotes&quot; &amp; special &lt;chars&gt;"' in xml_str
        
        # Parse back and verify content is preserved
        parsed = ET.fromstring(xml_str)
        parsed_title = parsed.find('.//title').text
        assert parsed_title == test_title
        parsed_attr = parsed.find('.//head').get('data-test')
        assert parsed_attr == test_attr
    
    def test_opf_generation(self):
        """Test OPF file generation using ElementTree"""
        # Define namespaces
        ns = {
            'opf': 'http://www.idpf.org/2007/opf',
            'dc': 'http://purl.org/dc/elements/1.1/'
        }
        
        # Register namespaces
        for prefix, uri in ns.items():
            ET.register_namespace(prefix, uri)
        
        # Create package element
        package = ET.Element(
            '{http://www.idpf.org/2007/opf}package',
            version='2.0',
            attrib={'unique-identifier': 'BookID'}
        )
        
        # Metadata
        metadata = ET.SubElement(package, '{http://www.idpf.org/2007/opf}metadata')
        metadata.set('{http://www.w3.org/2000/xmlns/}dc', ns['dc'])
        metadata.set('{http://www.w3.org/2000/xmlns/}opf', ns['opf'])
        
        # Add metadata elements
        ET.SubElement(metadata, '{%s}title' % ns['dc']).text = "Test Book"
        creator = ET.SubElement(metadata, '{%s}creator' % ns['dc'])
        creator.text = "Test Author"
        creator.set('{%s}role' % ns['opf'], 'aut')
        
        ET.SubElement(metadata, '{%s}language' % ns['dc']).text = "en"
        identifier = ET.SubElement(metadata, '{%s}identifier' % ns['dc'])
        identifier.text = "urn:uuid:test-uuid"
        identifier.set('id', 'BookID')
        
        # Manifest
        manifest = ET.SubElement(package, '{http://www.idpf.org/2007/opf}manifest')
        
        # Add items
        item1 = ET.SubElement(manifest, '{http://www.idpf.org/2007/opf}item')
        item1.set('id', 'ncx')
        item1.set('href', 'toc.ncx')
        item1.set('media-type', 'application/x-dtbncx+xml')
        
        # Spine
        spine = ET.SubElement(package, '{http://www.idpf.org/2007/opf}spine')
        spine.set('toc', 'ncx')
        
        # Verify structure
        assert package.tag == '{http://www.idpf.org/2007/opf}package'
        assert package.get('version') == '2.0'
        
        # Find elements using namespaces
        title_elem = package.find('.//{%s}title' % ns['dc'])
        assert title_elem.text == "Test Book"
    
    def test_ncx_generation(self):
        """Test NCX (Navigation Control) file generation"""
        # NCX namespace
        ncx_ns = 'http://www.daisy.org/z3986/2005/ncx/'
        ET.register_namespace('', ncx_ns)
        
        # Create NCX structure
        ncx = ET.Element('{%s}ncx' % ncx_ns, version='2005-1')
        
        # Head
        head = ET.SubElement(ncx, '{%s}head' % ncx_ns)
        
        meta_uid = ET.SubElement(head, '{%s}meta' % ncx_ns)
        meta_uid.set('name', 'dtb:uid')
        meta_uid.set('content', 'urn:uuid:test-uuid')
        
        # DocTitle
        doc_title = ET.SubElement(ncx, '{%s}docTitle' % ncx_ns)
        ET.SubElement(doc_title, '{%s}text' % ncx_ns).text = "Test Book"
        
        # NavMap
        nav_map = ET.SubElement(ncx, '{%s}navMap' % ncx_ns)
        
        # Add navigation points
        for i in range(1, 4):
            nav_point = ET.SubElement(nav_map, '{%s}navPoint' % ncx_ns)
            nav_point.set('id', f'nav{i}')
            nav_point.set('playOrder', str(i))
            
            nav_label = ET.SubElement(nav_point, '{%s}navLabel' % ncx_ns)
            ET.SubElement(nav_label, '{%s}text' % ncx_ns).text = f"Chapter {i}"
            
            content = ET.SubElement(nav_point, '{%s}content' % ncx_ns)
            content.set('src', f'Text/chapter{i}.xhtml')
        
        # Verify structure
        assert len(nav_map) == 3
        first_nav = nav_map[0]
        assert first_nav.get('playOrder') == '1'
