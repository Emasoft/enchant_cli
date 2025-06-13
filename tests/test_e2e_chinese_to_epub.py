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

import pytest
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

from enchant_cli import main as enchant_main


class TestE2EChineseToEPUB:
    """End-to-end tests for Chinese novel to English EPUB conversion"""
    
    @pytest.fixture
    def temp_workspace(self):
        """Create temporary workspace with test environment"""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            
            # Create test Chinese novels with different characteristics
            test_novels = {
                # Simple cultivation novel
                "修炼至尊.txt": """第一章：觉醒

林凡是一个普通的高中生，直到那一天，他觉醒了修炼天赋。

"天啊，这是什么力量？"林凡看着自己发光的双手，震惊不已。

从那一刻起，他的命运彻底改变了。他将踏上修炼之路，成为真正的强者。

第二章：第一次修炼

在神秘老者的指导下，林凡开始了他的第一次修炼。

"记住，修炼不仅仅是力量的提升，更是心境的磨练。"老者说道。

林凡点了点头，开始感受体内的灵气流动。

第三章：突破境界

经过一个月的刻苦修炼，林凡终于突破了第一个境界。

"我成功了！"林凡兴奋地喊道。

他感受到了前所未有的力量，这只是他修炼之路的开始。""",

                # Urban supernatural novel
                "都市异能王.txt": """第一章：意外觉醒

张伟是一名普通的上班族，但是一次意外让他获得了超能力。

那是一个雷雨交加的夜晚，张伟被闪电击中，却奇迹般地活了下来。

更神奇的是，他发现自己可以控制电流。

第二章：隐藏身份

为了不引起注意，张伟决定隐藏自己的能力。

"我必须小心，不能让任何人发现我的秘密。"他暗自想道。

白天，他依然是那个普通的上班族，但夜晚，他成为了城市的守护者。

第三章：初试身手

当张伟看到小偷抢劫老人时，他决定出手。

"住手！"张伟大喝一声，手中闪烁着电光。

小偷吓得丢下钱包就跑，从此，都市异能王的传说开始了。""",

                # Fantasy adventure
                "魔法学院.txt": """第一章：入学测试

艾莉是一个来自小村庄的女孩，但她拥有强大的魔法天赋。

在魔法学院的入学测试中，她展现了惊人的能力。

"这个女孩的魔法力量超乎想象。"院长惊讶地说道。

第二章：新的朋友

在学院里，艾莉结识了很多新朋友。

有擅长火魔法的汤姆，还有专精治疗术的莉莉。

"我们一起努力，成为最强的魔法师吧！"艾莉对朋友们说。

第三章：第一次任务

学院给新生们安排了第一次实战任务。

他们需要前往森林深处，清理那里的魔兽。

"这将是我们证明自己的机会。"艾莉握紧法杖，眼中充满决心。"""
            }
            
            # Create test novels
            for filename, content in test_novels.items():
                novel_path = workspace / filename
                novel_path.write_text(content, encoding='utf-8')
            
            # Create test config
            config_path = workspace / "test_config.yml"
            config_data = {
                'text_processing': {
                    'max_chars_per_chunk': 1500,
                    'default_encoding': 'utf-8',
                    'split_mode': 'PARAGRAPHS',
                    'split_method': 'paragraph'
                },
                'translation': {
                    'temperature': 0.0,
                    'max_tokens': 3000,
                    'local': {
                        'endpoint': 'http://localhost:1234/v1/chat/completions',
                        'model': 'qwen2.5:32b',
                        'timeout': 30
                    },
                    'remote': {
                        'endpoint': 'https://openrouter.ai/api/v1/chat/completions',
                        'model': 'deepseek/deepseek-chat', 
                        'timeout': 60
                    }
                },
                'icloud': {'enabled': False},
                'logging': {
                    'level': 'INFO',
                    'format': '%(asctime)s - %(levelname)s - %(message)s',
                    'file_enabled': False,
                    'file_path': 'enchant.log'
                },
                'pricing': {'enabled': True, 'save_report': False}
            }
            
            with open(config_path, 'w', encoding='utf-8') as f:
                yaml.dump(config_data, f, default_flow_style=False, allow_unicode=True)
            
            yield workspace
    
    @pytest.fixture
    def mock_openai_responses(self):
        """Mock OpenAI API responses for different novels"""
        return {
            "修炼至尊.txt": {
                'choices': [{
                    'message': {
                        'content': json.dumps({
                            'detected_language': 'Chinese',
                            'novel_title_original': '修炼至尊',
                            'author_name_original': '未知作者',
                            'novel_title_english': 'Cultivation Supreme',
                            'author_name_english': 'Unknown Author',
                            'author_name_romanized': 'Weizhi Zuozhe'
                        }, ensure_ascii=False)
                    }
                }],
                'usage': {'prompt_tokens': 200, 'completion_tokens': 80, 'total_tokens': 280}
            },
            "都市异能王.txt": {
                'choices': [{
                    'message': {
                        'content': json.dumps({
                            'detected_language': 'Chinese', 
                            'novel_title_original': '都市异能王',
                            'author_name_original': '未知作者',
                            'novel_title_english': 'Urban Ability King',
                            'author_name_english': 'Unknown Author',
                            'author_name_romanized': 'Weizhi Zuozhe'
                        }, ensure_ascii=False)
                    }
                }],
                'usage': {'prompt_tokens': 180, 'completion_tokens': 75, 'total_tokens': 255}
            },
            "魔法学院.txt": {
                'choices': [{
                    'message': {
                        'content': json.dumps({
                            'detected_language': 'Chinese',
                            'novel_title_original': '魔法学院', 
                            'author_name_original': '未知作者',
                            'novel_title_english': 'Magic Academy',
                            'author_name_english': 'Unknown Author',
                            'author_name_romanized': 'Weizhi Zuozhe'
                        }, ensure_ascii=False)
                    }
                }],
                'usage': {'prompt_tokens': 190, 'completion_tokens': 78, 'total_tokens': 268}
            }
        }
    
    @pytest.fixture
    def mock_translation_responses(self):
        """Mock translation API responses for different content"""
        return {
            # Response for cultivation novel
            "cultivation": {
                'choices': [{
                    'message': {
                        'content': """Chapter 1: Awakening

Lin Fan was an ordinary high school student, until that day when he awakened his cultivation talent.

"My God, what is this power?" Lin Fan looked at his glowing hands in shock.

From that moment, his destiny completely changed. He would embark on the path of cultivation and become a true powerhouse.

Chapter 2: First Cultivation

Under the guidance of a mysterious elder, Lin Fan began his first cultivation.

"Remember, cultivation is not just about power enhancement, but also mental refinement," the elder said.

Lin Fan nodded and began to feel the spiritual energy flowing within his body.

Chapter 3: Breaking Through Realms

After a month of hard cultivation, Lin Fan finally broke through his first realm.

"I succeeded!" Lin Fan shouted excitedly.

He felt unprecedented power - this was just the beginning of his cultivation journey."""
                    }
                }],
                'usage': {'prompt_tokens': 400, 'completion_tokens': 200, 'total_tokens': 600, 'cost': 0.003}
            },
            
            # Response for urban supernatural novel
            "urban": {
                'choices': [{
                    'message': {
                        'content': """Chapter 1: Accidental Awakening

Zhang Wei was an ordinary office worker, but an accident gave him superpowers.

It was a stormy night when Zhang Wei was struck by lightning but miraculously survived.

Even more miraculous was that he discovered he could control electric current.

Chapter 2: Hidden Identity

To avoid attention, Zhang Wei decided to hide his abilities.

"I must be careful not to let anyone discover my secret," he thought to himself.

During the day, he remained an ordinary office worker, but at night, he became the city's guardian.

Chapter 3: First Trial

When Zhang Wei saw a thief robbing an elderly person, he decided to act.

"Stop!" Zhang Wei shouted, lightning flickering in his hands.

The thief was so frightened he dropped the wallet and ran. Thus began the legend of the Urban Ability King."""
                    }
                }],
                'usage': {'prompt_tokens': 380, 'completion_tokens': 190, 'total_tokens': 570, 'cost': 0.0025}
            },
            
            # Response for fantasy novel
            "fantasy": {
                'choices': [{
                    'message': {
                        'content': """Chapter 1: Entrance Exam

Ally was a girl from a small village, but she possessed powerful magical talent.

In the Magic Academy's entrance exam, she displayed amazing abilities.

"This girl's magical power is beyond imagination," the headmaster said in surprise.

Chapter 2: New Friends

At the academy, Ally made many new friends.

There was Tom who excelled at fire magic, and Lily who specialized in healing arts.

"Let's work together to become the strongest mages!" Ally said to her friends.

Chapter 3: First Mission

The academy arranged the first practical mission for the new students.

They needed to venture deep into the forest and clear out the magical beasts there.

"This will be our chance to prove ourselves," Ally gripped her staff, her eyes filled with determination."""
                    }
                }],
                'usage': {'prompt_tokens': 370, 'completion_tokens': 185, 'total_tokens': 555, 'cost': 0.0023}
            }
        }

    def test_single_novel_complete_pipeline(self, temp_workspace, mock_openai_responses, mock_translation_responses):
        """Test complete pipeline for a single Chinese novel"""
        
        # Select test novel
        test_novel = temp_workspace / "修炼至尊.txt"
        config_file = temp_workspace / "test_config.yml"
        
        # Mock API responses
        responses = [
            Mock(json=lambda: mock_openai_responses["修炼至尊.txt"], raise_for_status=lambda: None),
            Mock(json=lambda: mock_translation_responses["cultivation"], raise_for_status=lambda: None)
        ]
        
        with patch('requests.post') as mock_post:
            mock_post.side_effect = responses
            
            # Set environment
            env = os.environ.copy()
            env['OPENAI_API_KEY'] = 'test_openai_key'
            
            # Run enchant_cli as subprocess to test actual CLI
            cmd = [
                sys.executable, str(project_root / "enchant_cli.py"),
                str(test_novel),
                "--config", str(config_file),
                "--openai-api-key", "test_openai_key"
            ]
            
            # For testing, we'll call the function directly
            sys.argv = cmd[1:]  # Set sys.argv for argparse
            
            with patch('sys.argv', cmd[1:]), \
                 patch.dict(os.environ, env):
                
                # Import and test after patching
                from enchant_cli import main as enchant_main
                
                try:
                    enchant_main()
                    success = True
                except SystemExit as e:
                    success = e.code == 0
                
                assert success
                
                # Verify outputs
                self._verify_complete_pipeline_outputs(temp_workspace, "Cultivation Supreme", "Unknown Author")

    def test_batch_processing_multiple_novels(self, temp_workspace, mock_openai_responses, mock_translation_responses):
        """Test batch processing of multiple Chinese novels"""
        
        config_file = temp_workspace / "test_config.yml"
        
        # Create response cycle for batch processing
        all_responses = []
        novels = ["修炼至尊.txt", "都市异能王.txt", "魔法学院.txt"]
        translation_types = ["cultivation", "urban", "fantasy"]
        
        for novel, trans_type in zip(novels, translation_types):
            all_responses.extend([
                Mock(json=lambda n=novel: mock_openai_responses[n], raise_for_status=lambda: None),
                Mock(json=lambda t=trans_type: mock_translation_responses[t], raise_for_status=lambda: None)
            ])
        
        with patch('requests.post') as mock_post:
            mock_post.side_effect = all_responses
            
            # Test batch processing
            cmd = [
                sys.executable, str(project_root / "enchant_cli.py"),
                str(temp_workspace),
                "--batch",
                "--config", str(config_file),
                "--openai-api-key", "test_openai_key"
            ]
            
            with patch('sys.argv', cmd[1:]), \
                 patch.dict(os.environ, {'OPENAI_API_KEY': 'test_openai_key'}):
                
                from enchant_cli import main as enchant_main
                
                try:
                    enchant_main()
                    success = True
                except SystemExit as e:
                    success = e.code == 0
                
                # Verify all three novels were processed
                expected_outputs = [
                    ("Cultivation Supreme", "Unknown Author"),
                    ("Urban Ability King", "Unknown Author"), 
                    ("Magic Academy", "Unknown Author")
                ]
                
                for title, author in expected_outputs:
                    self._verify_complete_pipeline_outputs(temp_workspace, title, author)

    def test_resume_functionality(self, temp_workspace, mock_openai_responses, mock_translation_responses):
        """Test resume functionality when process is interrupted"""
        
        test_novel = temp_workspace / "修炼至尊.txt"
        config_file = temp_workspace / "test_config.yml"
        
        # First run - complete only renaming phase
        with patch('requests.post') as mock_post:
            mock_post.return_value = Mock(
                json=lambda: mock_openai_responses["修炼至尊.txt"],
                raise_for_status=lambda: None
            )
            
            # Simulate interrupted process by only doing renaming
            cmd = [
                sys.executable, str(project_root / "enchant_cli.py"),
                str(test_novel),
                "--config", str(config_file),
                "--openai-api-key", "test_openai_key",
                "--skip-translating",
                "--skip-epub"
            ]
            
            with patch('sys.argv', cmd[1:]):
                from enchant_cli import main as enchant_main
                
                try:
                    enchant_main()
                except SystemExit:
                    pass
        
        # Verify renamed file exists
        renamed_files = list(temp_workspace.glob("Cultivation Supreme by Unknown Author*.txt"))
        assert len(renamed_files) == 1
        
        # Second run - resume with translation and EPUB
        with patch('requests.post') as mock_post:
            mock_post.return_value = Mock(
                json=lambda: mock_translation_responses["cultivation"],
                raise_for_status=lambda: None
            )
            
            cmd = [
                sys.executable, str(project_root / "enchant_cli.py"),
                str(test_novel),
                "--config", str(config_file),
                "--resume",
                "--skip-renaming"  # Skip since already done
            ]
            
            with patch('sys.argv', cmd[1:]):
                from enchant_cli import main as enchant_main
                
                try:
                    enchant_main()
                    success = True
                except SystemExit as e:
                    success = e.code == 0
                
                assert success
                self._verify_complete_pipeline_outputs(temp_workspace, "Cultivation Supreme", "Unknown Author")

    def test_epub_content_quality(self, temp_workspace, mock_openai_responses, mock_translation_responses):
        """Test quality and correctness of generated EPUB content"""
        
        test_novel = temp_workspace / "魔法学院.txt"
        config_file = temp_workspace / "test_config.yml"
        
        responses = [
            Mock(json=lambda: mock_openai_responses["魔法学院.txt"], raise_for_status=lambda: None),
            Mock(json=lambda: mock_translation_responses["fantasy"], raise_for_status=lambda: None)
        ]
        
        with patch('requests.post') as mock_post:
            mock_post.side_effect = responses
            
            cmd = [
                sys.executable, str(project_root / "enchant_cli.py"),
                str(test_novel),
                "--config", str(config_file),
                "--openai-api-key", "test_openai_key"
            ]
            
            with patch('sys.argv', cmd[1:]):
                from enchant_cli import main as enchant_main
                
                try:
                    enchant_main()
                except SystemExit:
                    pass
        
        # Find generated EPUB
        epub_files = list(temp_workspace.glob("*.epub"))
        assert len(epub_files) >= 1
        
        epub_file = next(f for f in epub_files if "Magic_Academy" in f.name)
        
        # Detailed EPUB content verification
        with zipfile.ZipFile(epub_file, 'r') as epub_zip:
            # Verify EPUB structure
            files = epub_zip.namelist()
            
            # Required EPUB files
            assert 'mimetype' in files
            assert 'META-INF/container.xml' in files
            assert 'OEBPS/content.opf' in files
            assert 'OEBPS/toc.ncx' in files
            assert 'OEBPS/Styles/style.css' in files
            
            # Chapter files
            chapter_files = [f for f in files if f.startswith('OEBPS/Text/chapter')]
            assert len(chapter_files) >= 3  # At least 3 chapters
            
            # Verify content.opf metadata
            content_opf = epub_zip.read('OEBPS/content.opf').decode('utf-8')
            assert 'Magic Academy' in content_opf
            assert 'Unknown Author' in content_opf
            assert 'en' in content_opf  # English language
            
            # Verify TOC structure
            toc_ncx = epub_zip.read('OEBPS/toc.ncx').decode('utf-8')
            assert 'Chapter 1: Entrance Exam' in toc_ncx
            assert 'Chapter 2: New Friends' in toc_ncx
            assert 'Chapter 3: First Mission' in toc_ncx
            
            # Verify chapter content is in English
            chapter1_content = epub_zip.read('OEBPS/Text/chapter1.xhtml').decode('utf-8')
            assert 'Ally was a girl from a small village' in chapter1_content
            assert 'magical talent' in chapter1_content
            assert 'Magic Academy' in chapter1_content
            
            # Verify proper HTML structure
            assert '<?xml version' in chapter1_content
            assert '<html xmlns=' in chapter1_content
            assert '<title>' in chapter1_content
            assert '</html>' in chapter1_content

    def test_error_handling_and_recovery(self, temp_workspace):
        """Test error handling and graceful recovery"""
        
        test_novel = temp_workspace / "修炼至尊.txt"
        config_file = temp_workspace / "test_config.yml"
        
        # Test with invalid API key
        with patch('requests.post') as mock_post:
            mock_post.side_effect = Exception("API Error")
            
            cmd = [
                sys.executable, str(project_root / "enchant_cli.py"),
                str(test_novel),
                "--config", str(config_file),
                "--openai-api-key", "invalid_key"
            ]
            
            with patch('sys.argv', cmd[1:]):
                from enchant_cli import main as enchant_main
                
                try:
                    enchant_main()
                    success = False
                except SystemExit as e:
                    success = e.code != 0  # Should exit with error
                
                assert success  # Should handle error gracefully

    def _verify_complete_pipeline_outputs(self, workspace: Path, expected_title: str, expected_author: str):
        """Verify all outputs from the complete pipeline are present and correct"""
        
        # 1. Verify renamed file exists
        safe_title = expected_title.replace(" ", "_")
        renamed_pattern = f"{expected_title} by {expected_author}*.txt"
        renamed_files = list(workspace.glob(renamed_pattern))
        assert len(renamed_files) >= 1, f"No renamed file found matching pattern: {renamed_pattern}"
        
        # 2. Verify translation directory exists
        translation_dir = workspace / f"{expected_title} by {expected_author}"
        assert translation_dir.exists(), f"Translation directory not found: {translation_dir}"
        
        # 3. Verify chapter files exist
        chapter_files = list(translation_dir.glob("*Chapter*.txt"))
        assert len(chapter_files) >= 3, f"Expected at least 3 chapter files, found {len(chapter_files)}"
        
        # 4. Verify combined translation file
        combined_file = translation_dir / f"translated_{expected_title} by {expected_author}.txt"
        assert combined_file.exists(), f"Combined translation file not found: {combined_file}"
        
        # 5. Verify EPUB file exists
        epub_pattern = f"{safe_title}*.epub"
        epub_files = list(workspace.glob(epub_pattern))
        assert len(epub_files) >= 1, f"No EPUB file found matching pattern: {epub_pattern}"
        
        epub_file = epub_files[0]
        
        # 6. Verify EPUB content
        with zipfile.ZipFile(epub_file, 'r') as epub_zip:
            files = epub_zip.namelist()
            
            # Basic EPUB structure
            assert 'mimetype' in files
            assert 'META-INF/container.xml' in files
            assert 'OEBPS/content.opf' in files
            assert 'OEBPS/toc.ncx' in files
            
            # Chapter content
            chapter_xhtml_files = [f for f in files if f.startswith('OEBPS/Text/chapter')]
            assert len(chapter_xhtml_files) >= 3
            
            # Verify metadata in content.opf
            content_opf = epub_zip.read('OEBPS/content.opf').decode('utf-8')
            assert expected_title in content_opf
            assert expected_author in content_opf
            
            # Verify TOC has English chapter titles
            toc_ncx = epub_zip.read('OEBPS/toc.ncx').decode('utf-8')
            assert 'Chapter' in toc_ncx  # Should have English chapter titles


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])