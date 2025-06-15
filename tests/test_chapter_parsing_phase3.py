#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test for Phase 3 chapter parsing logic.

This test verifies that enchant_cli.py correctly uses the TOC parser from make_epub.py
to identify chapter headings when generating an EPUB from the translated novel file.
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
                
        return chapters[:49]  # Only first 49 chapters
    
    def test_epub_toc_matches_expected_chapters(self, sample_novel_path, expected_chapters):
        """Test that the generated EPUB TOC matches expected chapter list"""
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a dummy file for the main argument
            dummy_file = Path(temp_dir) / "dummy.txt"
            dummy_file.write_text("dummy content")
            
            # Run enchant_cli.py to generate EPUB using existing TOC parser
            cmd = [
                sys.executable,
                str(project_root / "enchant_cli.py"),
                str(dummy_file),
                "--skip-renaming",
                "--skip-translating", 
                "--translated", str(sample_novel_path)
            ]
            
            # Run the command
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=temp_dir)
            
            # Find the generated EPUB file
            epub_files = list(Path(temp_dir).glob("*.epub"))
            assert len(epub_files) > 0, f"No EPUB file created. stdout: {result.stdout}\nstderr: {result.stderr}"
            
            epub_file = epub_files[0]
            
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
                
                # Verify we have at least 49 chapters
                assert len(actual_chapters) >= 49, \
                    f"Expected at least 49 chapters in TOC, found {len(actual_chapters)}. " \
                    f"First few: {actual_chapters[:5]}"
                
                # Compare first 49 chapters
                mismatches = []
                for i, expected in enumerate(expected_chapters[:49]):
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
                    f"Found duplicate chapters in TOC:\n" + "\n".join(duplicates)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])