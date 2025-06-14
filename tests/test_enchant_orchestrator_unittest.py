#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Integration tests for EnChANT orchestrator - Testing the full 3-phase process:
1. Renaming (Chinese filename -> English metadata extraction)
2. Translation (Chinese text -> English)  
3. EPUB Generation (English chapters -> EPUB with TOC)

Tests ensure the complete pipeline from Chinese novels to English EPUBs.
"""

import unittest
import tempfile
import shutil
from pathlib import Path
import os
import sys
import yaml
import zipfile
import xml.etree.ElementTree as ET
from unittest.mock import Mock, patch, MagicMock
import json

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from enchant_cli import process_novel_unified, main as enchant_main
from renamenovels import process_novel_file
from cli_translator import translate_novel
from make_epub import create_epub_from_txt_file


class TestEnchantOrchestrator(unittest.TestCase):
    """Test the complete EnChANT orchestration process"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.test_dir = tempfile.mkdtemp()
        self.test_path = Path(self.test_dir)
        
        # Create test config
        self.config = {
            'translation': {
                'api_choice': 'openai',
                'api_keys': {
                    'openai': 'test-key'
                },
                'chunk_size': 1000,
                'max_workers': 1
            },
            'epub': {
                'generate_toc': True,
                'validate_chapters': True
            }
        }
    
    def tearDown(self):
        """Clean up test fixtures"""
        shutil.rmtree(self.test_dir)
    
    @patch('enchant_cli.get_translator_from_config')
    def test_orchestrator_handles_all_phases(self, mock_get_translator):
        """Test that orchestrator properly handles all 3 phases"""
        # Create test novel
        test_novel = self.test_path / "Test Novel by Test Author.txt"
        test_novel.write_text("""Chapter 1: Beginning

This is the beginning of the story.

Chapter 2: Middle

This is the middle of the story.

Chapter 3: End

This is the end of the story.""", encoding='utf-8')
        
        # Mock translator
        mock_translator = Mock()
        mock_translator.translate.side_effect = lambda text: text  # Identity translation
        mock_get_translator.return_value = mock_translator
        
        # Process with orchestrator
        output_dir = self.test_path / "output"
        with patch('enchant_cli.CONFIG_PATH', self.test_path / 'config.yml'):
            # Write config
            with open(self.test_path / 'config.yml', 'w') as f:
                yaml.dump(self.config, f)
            
            success = process_novel_unified(
                input_path=test_novel,
                output_dir=output_dir,
                create_epub=True,
                translate=True
            )
        
        self.assertTrue(success)
        
        # Verify translation output exists
        translated_file = output_dir / "Test Novel by Test Author - Translated.txt"
        self.assertTrue(translated_file.exists())
        
        # Verify EPUB exists
        epub_file = output_dir / "Test Novel by Test Author.epub"
        self.assertTrue(epub_file.exists())
    
    @patch('enchant_cli.extract_metadata')
    def test_phase1_metadata_extraction(self, mock_extract):
        """Test Phase 1: Metadata extraction and renaming"""
        # Create Chinese filename
        chinese_file = self.test_path / "中文小说_作者.txt"
        chinese_file.write_text("Content", encoding='utf-8')
        
        # Mock metadata extraction
        mock_extract.return_value = {
            'title': 'Chinese Novel',
            'author': 'Author Name',
            'original_title': '中文小说',
            'original_author': '作者'
        }
        
        # Test renaming directly
        new_path = process_novel_file(chinese_file)
        
        self.assertTrue(new_path.exists())
        self.assertEqual(new_path.name, "Chinese Novel by Author Name.txt")
    
    def test_phase3_epub_generation(self):
        """Test Phase 3: EPUB generation from English text"""
        # Create English text file
        english_file = self.test_path / "test_novel.txt"
        english_file.write_text("""Chapter 1: Test Chapter

This is a test chapter.

Chapter 2: Another Chapter

This is another chapter.""", encoding='utf-8')
        
        # Generate EPUB
        epub_path = self.test_path / "test_novel.epub"
        success, issues = create_epub_from_txt_file(
            txt_file_path=english_file,
            output_path=epub_path,
            title="Test Novel",
            author="Test Author"
        )
        
        self.assertTrue(success)
        self.assertEqual(len(issues), 0)
        self.assertTrue(epub_path.exists())
        
        # Verify EPUB structure
        with zipfile.ZipFile(epub_path, 'r') as epub:
            self.assertIn('mimetype', epub.namelist())
            self.assertIn('OEBPS/content.opf', epub.namelist())
            self.assertIn('OEBPS/toc.ncx', epub.namelist())
    
    def test_error_handling_in_pipeline(self):
        """Test error handling throughout the pipeline"""
        # Test with non-existent file
        fake_file = self.test_path / "non_existent.txt"
        
        with patch('enchant_cli.CONFIG_PATH', self.test_path / 'config.yml'):
            # Write config
            with open(self.test_path / 'config.yml', 'w') as f:
                yaml.dump(self.config, f)
            
            success = process_novel_unified(
                input_path=fake_file,
                output_dir=self.test_path / "output",
                create_epub=True
            )
        
        self.assertFalse(success)


if __name__ == '__main__':
    unittest.main()