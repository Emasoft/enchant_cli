#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
End-to-End test for complete Chinese novel to English EPUB conversion.

This test validates the entire pipeline:
1. Chinese novel with Chinese filename → 
2. Metadata extraction and English renaming → 
3. Chinese text translation to English → 
4. English EPUB with proper TOC

Mock external services to focus on integration testing.
"""

import unittest
import tempfile
import shutil
from pathlib import Path
import os
import sys
import subprocess
import yaml
import zipfile
import xml.etree.ElementTree as ET
from unittest.mock import Mock, patch, MagicMock
import json
import re

# Add project root to Python path  
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from enchant_cli import process_novel_unified, main as enchant_main
from renamenovels import process_novel_file
from make_epub import create_epub_from_txt_file


class TestE2EChineseToEpub(unittest.TestCase):
    """Test complete pipeline from Chinese novel to English EPUB"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_dir = tempfile.mkdtemp()
        self.test_path = Path(self.test_dir)
        
        # Create mock configuration
        self.config_content = {
            'translation': {
                'api_choice': 'openai',
                'api_keys': {
                    'openai': 'test-key'
                },
                'chunk_size': 1000,
                'max_workers': 1,
                'rate_limit': 1
            },
            'epub': {
                'generate_toc': True,
                'validate_chapters': True,
                'strict_mode': False,
                'language': 'en'
            }
        }
        
        # Write config file
        config_path = self.test_path / 'enchant_config.yml'
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(self.config_content, f)
    
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.test_dir)
    
    @patch('enchant_cli.get_translator_from_config')
    @patch('renamenovels.extract_metadata')
    def test_complete_chinese_to_english_epub_pipeline(self, mock_extract, mock_translator):
        """Test complete pipeline from Chinese file to English EPUB"""
        # Create Chinese novel file
        chinese_filename = "测试小说_作者名.txt"
        chinese_file_path = self.test_path / chinese_filename
        chinese_content = """第一章 开始

这是第一章的内容。

第二章 继续

这是第二章的内容。

第三章 结束

这是第三章的内容。"""
        
        chinese_file_path.write_text(chinese_content, encoding='utf-8')
        
        # Mock metadata extraction
        mock_extract.return_value = {
            'title': 'Test Novel',
            'author': 'Test Author',
            'original_title': '测试小说',
            'original_author': '作者名'
        }
        
        # Mock translator
        mock_translator_instance = Mock()
        mock_translator_instance.translate.side_effect = lambda text: {
            '第一章 开始': 'Chapter 1: Beginning',
            '这是第一章的内容。': 'This is the content of chapter one.',
            '第二章 继续': 'Chapter 2: Continue', 
            '这是第二章的内容。': 'This is the content of chapter two.',
            '第三章 结束': 'Chapter 3: End',
            '这是第三章的内容。': 'This is the content of chapter three.'
        }.get(text.strip(), f'Translated: {text}')
        mock_translator.return_value = mock_translator_instance
        
        # Step 1: Rename the file
        new_path = process_novel_file(chinese_file_path)
        self.assertTrue(new_path.exists())
        self.assertEqual(new_path.name, "Test Novel by Test Author.txt")
        
        # Step 2 & 3: Process with enchant (translate and create EPUB)
        with patch('enchant_cli.CONFIG_PATH', self.test_path / 'enchant_config.yml'):
            # Process the novel
            output_dir = self.test_path / "Test Novel by Test Author"
            success = process_novel_unified(
                input_path=new_path,
                output_dir=output_dir,
                create_epub=True,
                translate=True
            )
        
        self.assertTrue(success)
        
        # Verify EPUB was created
        epub_path = output_dir / "Test Novel by Test Author.epub"
        self.assertTrue(epub_path.exists())
        
        # Verify EPUB structure
        with zipfile.ZipFile(epub_path, 'r') as epub:
            # Check mimetype
            self.assertIn('mimetype', epub.namelist())
            self.assertEqual(epub.read('mimetype').decode('utf-8'), 'application/epub+zip')
            
            # Check content.opf
            self.assertIn('OEBPS/content.opf', epub.namelist())
            opf_content = epub.read('OEBPS/content.opf').decode('utf-8')
            self.assertIn('<dc:title>Test Novel</dc:title>', opf_content)
            self.assertIn('<dc:creator', opf_content)
            self.assertIn('Test Author', opf_content)
            self.assertIn('<dc:language>en</dc:language>', opf_content)
            
            # Check TOC
            self.assertIn('OEBPS/toc.ncx', epub.namelist())
            toc_content = epub.read('OEBPS/toc.ncx').decode('utf-8')
            self.assertIn('Chapter 1', toc_content)
            self.assertIn('Chapter 2', toc_content)
            self.assertIn('Chapter 3', toc_content)
            
            # Check chapter files exist
            chapter_files = [f for f in epub.namelist() if f.startswith('OEBPS/Text/') and f.endswith('.xhtml')]
            self.assertGreaterEqual(len(chapter_files), 3)


if __name__ == '__main__':
    unittest.main()