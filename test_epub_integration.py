#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script to verify the refactored EPUB creation integration
"""

import sys
import os
from pathlib import Path
import tempfile

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from make_epub import create_epub_from_txt_file

# Color codes for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'
BOLD = '\033[1m'

def create_test_novel():
    """Create a test novel with chapter markers"""
    content = """Chapter 1 - The Beginning

It was a dark and stormy night. The protagonist walked through the rain, 
wondering what adventures awaited them.

This is the first paragraph of the story.

This is the second paragraph with more details about the setting.

Chapter 2 - The Journey

The next morning brought clear skies and new hope. Our hero set out on
their journey with determination.

The path was long and winding, but they pressed on.

Chapter 3 - The Discovery

After many days of travel, they finally reached the ancient temple.
What they found inside would change everything.

The secrets of the past were about to be revealed.

Chapter 4 - The Challenge

But gaining the knowledge would not be easy. A great trial awaited
anyone who dared to enter the inner sanctum.

Our hero steeled themselves for what was to come.

Chapter 5 - The Resolution

In the end, wisdom and courage prevailed. The hero emerged victorious,
forever changed by their experience.

And so the story came to its conclusion, but the journey would live on
in memory.
"""
    return content

def test_epub_creation():
    """Test creating EPUB from complete text file"""
    print(f"\n{BOLD}Testing EPUB Creation from Complete Text File{RESET}")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        # Create test text file
        txt_file = tmpdir / "test_novel.txt"
        txt_file.write_text(create_test_novel(), encoding='utf-8')
        print(f"{GREEN}✓{RESET} Created test text file: {txt_file.name}")
        
        # Create EPUB
        epub_file = tmpdir / "test_novel.epub"
        
        try:
            success, issues = create_epub_from_txt_file(
                txt_file_path=txt_file,
                output_path=epub_file,
                title="Test Novel",
                author="Test Author",
                cover_path=None,
                generate_toc=True,
                validate=True,
                strict_mode=False
            )
            
            if success:
                print(f"{GREEN}✓{RESET} EPUB created successfully")
                
                if issues:
                    print(f"{YELLOW}⚠{RESET} Validation warnings:")
                    for issue in issues:
                        print(f"  - {issue}")
                else:
                    print(f"{GREEN}✓{RESET} No validation issues found")
                
                # Check if EPUB file exists and has content
                if epub_file.exists():
                    size = epub_file.stat().st_size
                    print(f"{GREEN}✓{RESET} EPUB file created: {size:,} bytes")
                    
                    # Verify it's a valid ZIP file (EPUB format)
                    import zipfile
                    try:
                        with zipfile.ZipFile(epub_file, 'r') as zf:
                            files = zf.namelist()
                            print(f"{GREEN}✓{RESET} Valid EPUB/ZIP structure with {len(files)} files")
                            
                            # Check for required EPUB files
                            required = ['mimetype', 'META-INF/container.xml', 'OEBPS/content.opf', 'OEBPS/toc.ncx']
                            for req in required:
                                if req in files:
                                    print(f"{GREEN}✓{RESET} Found required file: {req}")
                                else:
                                    print(f"{RED}✗{RESET} Missing required file: {req}")
                            
                            # Check for chapters
                            chapters = [f for f in files if 'chapter' in f and f.endswith('.xhtml')]
                            print(f"{GREEN}✓{RESET} Found {len(chapters)} chapter files")
                            
                    except Exception as e:
                        print(f"{RED}✗{RESET} Error reading EPUB: {e}")
                else:
                    print(f"{RED}✗{RESET} EPUB file not created")
                    
            else:
                print(f"{RED}✗{RESET} EPUB creation failed")
                for issue in issues:
                    print(f"  - {issue}")
                    
        except Exception as e:
            print(f"{RED}✗{RESET} Exception during EPUB creation: {e}")
            import traceback
            traceback.print_exc()

def test_chapter_detection():
    """Test chapter detection from text"""
    print(f"\n{BOLD}Testing Chapter Detection{RESET}")
    print("=" * 60)
    
    test_cases = [
        ("Chapter 1", True),
        ("Chapter 10", True),
        ("Chapter 100", True),
        ("CHAPTER 5", True),
        ("Chapter One", True),
        ("Chapter Twenty-Three", True),
        ("Chapter IX", True),
        ("Not a chapter", False),
        ("Chapter", False),
    ]
    
    from make_epub import HEADING_RE
    
    for text, should_match in test_cases:
        match = HEADING_RE.match(text)
        matched = match is not None
        
        if matched == should_match:
            print(f"{GREEN}✓{RESET} '{text}' - {'matched' if matched else 'not matched'} as expected")
        else:
            print(f"{RED}✗{RESET} '{text}' - expected {'match' if should_match else 'no match'}, got {'match' if matched else 'no match'}")

def test_empty_file():
    """Test handling of empty text file"""
    print(f"\n{BOLD}Testing Empty File Handling{RESET}")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        # Create empty text file
        txt_file = tmpdir / "empty.txt"
        txt_file.write_text("", encoding='utf-8')
        
        epub_file = tmpdir / "empty.epub"
        
        try:
            success, issues = create_epub_from_txt_file(
                txt_file_path=txt_file,
                output_path=epub_file,
                title="Empty Book",
                author="No One",
                generate_toc=False,
                validate=False
            )
            
            if success:
                print(f"{GREEN}✓{RESET} Empty file handled gracefully")
            else:
                print(f"{YELLOW}⚠{RESET} Empty file resulted in failure (may be expected)")
                
        except Exception as e:
            print(f"{RED}✗{RESET} Exception with empty file: {e}")

def main():
    """Run all tests"""
    print(f"{BOLD}{BLUE}EPUB Integration Tests{RESET}")
    print("=" * 80)
    
    test_chapter_detection()
    test_epub_creation()
    test_empty_file()
    
    print(f"\n{GREEN}{BOLD}All tests completed!{RESET}")

if __name__ == "__main__":
    main()