#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Tests for enhanced TOC generation"""

import unittest
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from enchant_book_manager.epub_toc_enhanced import (
    EnhancedTocBuilder,
    TocEntry,
    build_enhanced_toc_ncx,
)


class TestEnhancedTocBuilder(unittest.TestCase):
    """Test enhanced TOC builder functionality"""

    def setUp(self):
        """Set up test data"""
        self.builder = EnhancedTocBuilder()

        # Test chapters with mixed hierarchy
        self.test_chapters = [
            ("Part I: The Beginning", "Content"),
            ("Chapter 1: Introduction", "Content"),
            ("Chapter 2: Getting Started", "Content"),
            ("Book 1: Foundation", "Content"),
            ("Chapter 3: Basic Concepts", "Content"),
            ("Chapter 4: Advanced Topics", "Content"),
            ("Part II: The Journey", "Content"),
            ("Section A: Preparation", "Content"),
            ("Chapter 5: Tools and Resources", "Content"),
            ("Chapter 6: Best Practices", "Content"),
        ]

    def test_toc_entry_to_ncx(self):
        """Test TocEntry NCX generation"""
        entry = TocEntry(title="Chapter 1: Test", href="Text/chapter1.xhtml", play_order=1, level=1)

        ncx = entry.to_ncx_navpoint()
        self.assertIn('<navPoint id="nav1" playOrder="1">', ncx)
        self.assertIn("<text>Chapter 1: Test</text>", ncx)
        self.assertIn('<content src="Text/chapter1.xhtml"/>', ncx)

    def test_toc_entry_to_nav_li(self):
        """Test TocEntry EPUB3 navigation list item generation"""
        # Test simple entry
        entry = TocEntry(title="Chapter 1: Test", href="Text/chapter1.xhtml", play_order=1, level=1)
        nav_li = entry.to_nav_li(depth=2)

        self.assertIn("    <li>", nav_li)  # depth=2 gives 4 spaces indent
        self.assertIn('<a href="Text/chapter1.xhtml">Chapter 1: Test</a>', nav_li)
        self.assertIn("</li>", nav_li)

        # Test entry with children
        child_entry = TocEntry(title="Section 1.1", href="Text/section1_1.xhtml", play_order=2, level=2)
        entry.children.append(child_entry)

        nav_li_with_children = entry.to_nav_li(depth=2)
        self.assertIn("<ol>", nav_li_with_children)
        self.assertIn("Section 1.1", nav_li_with_children)
        self.assertIn("</ol>", nav_li_with_children)

    def test_hierarchical_structure(self):
        """Test hierarchical TOC structure creation"""
        entries = self.builder.analyze_chapters(self.test_chapters)

        # Should have 2 top-level entries (Part I and Part II)
        self.assertEqual(len(entries), 2)

        # Part I should have children
        part1 = entries[0]
        self.assertEqual(part1.title, "Part I: The Beginning")
        self.assertTrue(len(part1.children) > 0)

        # Check for Book 1 under Part I
        book1 = None
        for child in part1.children:
            if child.title == "Book 1: Foundation":
                book1 = child
                break

        self.assertIsNotNone(book1)
        self.assertTrue(len(book1.children) > 0)

    def test_flat_nav_points(self):
        """Test flat navigation points for backward compatibility"""
        nav_points = self.builder.get_flat_nav_points(self.test_chapters[:3])

        self.assertEqual(len(nav_points), 3)
        self.assertIn('id="nav1"', nav_points[0])
        self.assertIn("Part I: The Beginning", nav_points[0])

    def test_max_depth_calculation(self):
        """Test maximum depth calculation"""
        entries = self.builder.analyze_chapters(self.test_chapters)
        max_depth = self.builder._calculate_max_depth(entries)

        # Should be at least 3 (Part -> Book/Section -> Chapter)
        self.assertGreaterEqual(max_depth, 3)

    def test_build_enhanced_toc_ncx(self):
        """Test complete NCX generation"""
        toc = build_enhanced_toc_ncx(
            self.test_chapters,
            "Test Book",
            "Test Author",
            "test-uid-123",
            hierarchical=True,
        )

        # Check basic structure
        self.assertIn("<?xml version='1.0' encoding='utf-8'?>", toc)
        self.assertIn("<ncx xmlns='http://www.daisy.org/z3986/2005/ncx/'", toc)

    def test_build_nav_xhtml(self):
        """Test EPUB3 navigation document generation"""
        nav_html = self.builder.build_nav_xhtml(self.test_chapters, "Test Book")

        # Check basic XHTML structure
        self.assertIn('<?xml version="1.0" encoding="utf-8"?>', nav_html)
        self.assertIn("<!DOCTYPE html>", nav_html)
        self.assertIn('<html xmlns="http://www.w3.org/1999/xhtml"', nav_html)
        self.assertIn('xmlns:epub="http://www.idpf.org/2007/ops"', nav_html)

        # Check navigation structure
        self.assertIn('<nav epub:type="toc" id="toc">', nav_html)
        self.assertIn("<h1>Table of Contents</h1>", nav_html)
        self.assertIn("<ol>", nav_html)
        self.assertIn("</ol>", nav_html)

        # Check title is properly escaped
        self.assertIn("<title>Test Book - Navigation</title>", nav_html)

        # Check that chapters are included
        self.assertIn("Part I: The Beginning", nav_html)
        self.assertIn("Chapter 1: Introduction", nav_html)

    def test_build_enhanced_toc_ncx_content(self):
        """Test NCX content details"""
        toc = build_enhanced_toc_ncx(
            self.test_chapters,
            "Test Book",
            "Test Author",
            "test-uid-123",
            hierarchical=True,
        )

        self.assertIn("<docTitle><text>Test Book</text></docTitle>", toc)
        self.assertIn("<docAuthor><text>Test Author</text></docAuthor>", toc)

        # Check hierarchical depth
        self.assertIn("dtb:depth", toc)
        self.assertNotIn("content='1'", toc)  # Should be more than 1

    def test_special_characters_escaping(self):
        """Test proper escaping of special characters"""
        special_chapters = [
            ('Chapter 1: <Special> & "Quoted"', "Content"),
            ("Chapter 2: Normal", "Content"),
        ]

        toc = build_enhanced_toc_ncx(
            special_chapters,
            "Test & Book",
            "Author <Name>",
            "test-uid",
            hierarchical=False,
        )

        # Check proper escaping
        self.assertIn("&lt;Special&gt; &amp; &quot;Quoted&quot;", toc)
        self.assertIn("Test &amp; Book", toc)
        self.assertIn("Author &lt;Name&gt;", toc)

    def test_empty_chapters(self):
        """Test handling of empty chapter list"""
        toc = build_enhanced_toc_ncx([], "Empty Book", "No Author", "empty-uid", hierarchical=True)

        self.assertIn("<navMap>", toc)
        self.assertIn("</navMap>", toc)


if __name__ == "__main__":
    unittest.main()
