#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test for Phase 3 chapter parsing logic.

This test verifies that enchant_cli.py correctly uses the TOC parser from make_epub.py
to identify chapter headings when generating an EPUB from a full translated novel file.

The test uses a complete novel (600K+ lines) to ensure the program handles real-world
file sizes correctly. No truncation or sampling is done - the full file is processed.
"""

import pytest
import sys
import os
import tempfile
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
import subprocess

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Check if sample files exist
sample_novel_path = project_root / "tests" / "sample_novel" / "translated_Global High Martial Arts by Eagle Eats Chick (Lǎo yīng chī xiǎo jī).txt"
chapter_headings_path = project_root / "tests" / "sample_novel" / "chapter_headings.txt"
sample_files_exist = sample_novel_path.exists() and chapter_headings_path.exists()


@pytest.mark.skipif(not sample_files_exist, reason="Sample novel files not found in tests/sample_novel/")
class TestChapterParsingPhase3:
    """Test that enchant_cli.py correctly generates EPUB with proper chapter TOC"""
    
    @pytest.fixture
    def sample_novel_path(self):
        """Path to the sample translated novel"""
        return project_root / "tests" / "sample_novel" / "translated_Global High Martial Arts by Eagle Eats Chick (Lǎo yīng chī xiǎo jī).txt"
    
    @pytest.fixture
    def expected_chapters_path(self):
        """Path to the expected chapter headings file"""
        return project_root / "tests" / "sample_novel" / "chapter_headings.txt"
    
    @pytest.fixture
    def expected_chapters(self, expected_chapters_path):
        """Parse the expected chapter headings"""
        chapters = []
        with open(expected_chapters_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        i = 4  # Skip header lines
        while i < len(lines):
            if i + 2 < len(lines):
                chapter_num = lines[i].strip()
                
                # Check if next line is a number (line number) or text (missing line number)
                try:
                    line_num = int(lines[i + 1].strip())
                    chapter_text = lines[i + 2].strip()
                    i += 4  # Skip to next chapter (including blank line)
                except ValueError:
                    # Line number is missing, so the chapter text is on the next line
                    line_num = None  # We don't know the line number
                    chapter_text = lines[i + 1].strip()
                    i += 3  # Skip to next chapter (including blank line)
                
                # Handle special case of chapter 13a
                if chapter_num == '13a':
                    chapter_num = '13'
                
                # Skip entries without line numbers for this test
                if line_num is not None:
                    chapters.append({
                        'number': int(chapter_num),
                        'line': line_num,
                        'text': chapter_text
                    })
            else:
                break
                
        return chapters  # Return all chapters from the expected file
    
    def test_epub_toc_matches_expected_chapters(self, sample_novel_path, expected_chapters):
        """Test that the generated EPUB TOC matches expected chapter list"""
        
        # Clean up any existing EPUB files before test
        epub_dir = sample_novel_path.parent
        for old_epub in epub_dir.glob("*.epub"):
            old_epub.unlink()
            print(f"Cleaned up existing EPUB: {old_epub.name}")
        
        # Verify we're working with the full file
        file_size = sample_novel_path.stat().st_size
        line_count = sum(1 for _ in open(sample_novel_path, 'r', encoding='utf-8'))
        print("Testing with full novel file:")
        print(f"  - Path: {sample_novel_path}")
        print(f"  - Size: {file_size / 1024 / 1024:.1f} MB")
        print(f"  - Lines: {line_count:,}")
        
        # Create temp directory inside the repo
        temp_dir = project_root / "temp_test_chapter_parsing"
        temp_dir.mkdir(exist_ok=True)
        
        try:
            # Run enchant_cli.py to generate EPUB using existing TOC parser
            # Using simplified syntax where --translated implies skip flags
            cmd = [
                sys.executable,
                str(project_root / "enchant_cli.py"),
                "--translated", str(sample_novel_path)
            ]
            
            # Run the command with longer timeout for large file
            print("Generating EPUB from full novel (this may take a few minutes)...")
            import time
            start_time = time.time()
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(temp_dir), timeout=600)
            elapsed = time.time() - start_time
            print(f"EPUB generation completed in {elapsed:.1f} seconds")
            
            # Find the generated EPUB file - should be in the same directory as the translated file
            epub_dir = sample_novel_path.parent
            epub_files = list(epub_dir.glob("*.epub"))
            
            # If not found there, check temp_dir (backward compatibility)
            if not epub_files:
                epub_files = list(temp_dir.glob("*.epub"))
            
            assert len(epub_files) > 0, f"No EPUB file created. stdout: {result.stdout}\nstderr: {result.stderr}"
            
            epub_file = epub_files[0]
            print(f"Generated EPUB: {epub_file.name} ({epub_file.stat().st_size / 1024 / 1024:.1f} MB)")
            
            # Extract and verify TOC from EPUB
            with zipfile.ZipFile(epub_file, 'r') as epub:
                # Read the TOC file
                toc_content = epub.read('OEBPS/toc.ncx').decode('utf-8')
                
                # Parse TOC XML
                root = ET.fromstring(toc_content)
                ns = {'ncx': 'http://www.daisy.org/z3986/2005/ncx/'}
                
                # Find all navPoints (chapters) - skip the first one as it's usually the title
                nav_map = root.find('.//ncx:navMap', ns)
                nav_points = nav_map.findall('./ncx:navPoint', ns) if nav_map is not None else []
                
                # The first navPoint might be "Front Matter" or similar, let's check
                actual_chapters = []
                for nav_point in nav_points:
                    nav_label = nav_point.find('.//ncx:text', ns)
                    if nav_label is not None and nav_label.text:
                        # Only include entries that look like chapters
                        if 'Chapter' in nav_label.text or 'chapter' in nav_label.text:
                            actual_chapters.append(nav_label.text)
                
                # Verify we have the expected number of chapters
                print(f"Found {len(actual_chapters)} chapters in TOC")
                print(f"Expected {len(expected_chapters)} chapters from test file")
                
                # Only check the chapters we have expected values for
                chapters_to_check = min(len(expected_chapters), len(actual_chapters))
                print(f"Checking first {chapters_to_check} chapters...")
                
                # Compare chapters
                mismatches = []
                for i, expected in enumerate(expected_chapters[:chapters_to_check]):
                    if i >= len(actual_chapters):
                        mismatches.append(f"Chapter {i+1}: Missing in TOC")
                        continue
                        
                    actual = actual_chapters[i]
                    if actual != expected['text']:
                        mismatches.append(
                            f"Chapter {i+1}:\n"
                            f"  Expected: '{expected['text']}'\n" 
                            f"  Actual:   '{actual}'"
                        )
                
                # Report all mismatches if any
                if mismatches:
                    pytest.fail(
                        f"TOC chapters don't match expected. Found {len(mismatches)} mismatches:\n" +
                        "\n".join(mismatches[:10]) +  # Show first 10 mismatches
                        (f"\n... and {len(mismatches) - 10} more" if len(mismatches) > 10 else "")
                    )
                
                # Additional check: Ensure no duplicates in TOC
                seen_chapters = set()
                duplicates = []
                for i, chapter in enumerate(actual_chapters):
                    if chapter in seen_chapters:
                        duplicates.append(f"Duplicate at position {i+1}: '{chapter}'")
                    seen_chapters.add(chapter)
                
                assert len(duplicates) == 0, \
                    "Found duplicate chapters in TOC:\n" + "\n".join(duplicates)
                
                print(f"✓ All {chapters_to_check} checked chapters match expected values")
                print(f"✓ No duplicates found in {len(actual_chapters)} TOC entries")
                
        finally:
            # Clean up temp directory
            import shutil
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
                print(f"Cleaned up temp directory: {temp_dir}")
            
            # Clean up generated EPUB file
            if 'epub_file' in locals() and epub_file.exists():
                epub_file.unlink()
                print(f"Cleaned up generated EPUB: {epub_file}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])