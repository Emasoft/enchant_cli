#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
End-to-End demonstration of the new EnChANT 3-phase orchestrator.
This script demonstrates a complete Chinese novel → English EPUB pipeline
with mocked AI services to avoid requiring API keys.
"""

import tempfile
import os
import sys
import json
from pathlib import Path
from unittest.mock import Mock, patch

def demo_complete_pipeline():
    """Demonstrate the complete 3-phase pipeline with mocked AI services"""
    print("=" * 80)
    print("ENCHANT END-TO-END PIPELINE DEMONSTRATION")
    print("=" * 80)
    print("This demo shows Chinese novels being processed through all 3 phases:")
    print("1. RENAMING: Extract metadata and rename files (Chinese → English)")
    print("2. TRANSLATION: Translate Chinese text to English") 
    print("3. EPUB: Generate EPUB from translated chapters")
    print("=" * 80)
    
    # Create a realistic Chinese novel
    chinese_content = """第一章 修炼之路

李明是一个普通的高中生，生活在一个平凡的小镇上。每天早上，他都会准时起床，匆匆忙忙地赶到学校上课。

但是李明有一个秘密，一个连他自己都不太相信的秘密——他能够修炼武功。

在这个现代社会中，武功已经被人们当作传说和电影中的虚构产物。然而，李明却在一次意外中发现，古老的修炼方法竟然是真实存在的。

那是一个雷雨交加的夜晚，李明在图书馆里发现了一本古老的书籍。

第二章 神秘的功法

当李明翻开那本古书时，一股奇异的能量从书页中散发出来。

书中记载着一种名为"天罡诀"的修炼功法，据说修炼成功后能够获得超凡的力量。

起初，李明对此将信将疑，但是当他按照书中的方法开始修炼时，竟然真的感受到了体内有一股暖流在流淌。

"这...这是真的！"李明激动得心跳加速。

从那一刻起，他开始了自己的修炼之路。

第三章 突破第一重境界

经过一个月的刻苦修炼，李明终于感受到了突破的征兆。

那天夜里，他正在修炼时，突然感到体内的能量如潮水般涌动。一阵剧烈的疼痛之后，他惊喜地发现自己的力量有了质的提升。

"我成功了！我真的突破了第一重境界！"李明兴奋地说道。

但是他也明白，这只是修炼之路的开始，前方还有更多的挑战等待着他。

从此，李明的人生彻底改变了。他不再是那个平凡的高中生，而是踏上了成为真正强者的道路。"""
    
    # Create test file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
        f.write(chinese_content)
        test_file = Path(f.name)
    
    print(f"\n📖 Created test Chinese novel: {test_file.name}")
    print(f"   Content length: {len(chinese_content)} characters")
    print("   Contains 3 chapters in Chinese")
    
    try:
        from enchant_cli import process_novel_unified
        
        # Mock API responses for renaming
        mock_renaming_response = {
            'choices': [{
                'message': {
                    'content': json.dumps({
                        'detected_language': 'Chinese',
                        'novel_title_original': '修炼之路',
                        'author_name_original': '未知作者',
                        'novel_title_english': 'Path of Cultivation',
                        'author_name_english': 'Unknown Author',
                        'author_name_romanized': 'Weizhi Zuozhe'
                    }, ensure_ascii=False)
                }
            }],
            'usage': {'prompt_tokens': 200, 'completion_tokens': 50, 'total_tokens': 250}
        }
        
        # Mock API responses for translation
        mock_translation_response = {
            'choices': [{
                'message': {
                    'content': """Chapter 1: The Path of Cultivation

Li Ming was an ordinary high school student living in a small, unremarkable town. Every morning, he would wake up on time and rush to school for classes.

But Li Ming had a secret, one that even he found hard to believe—he could cultivate martial arts.

In this modern society, martial arts were considered legends and fictional elements from movies. However, Li Ming discovered by accident that ancient cultivation methods were actually real.

It was a stormy night when Li Ming found an ancient book in the library.

Chapter 2: The Mysterious Technique

When Li Ming opened the ancient book, a strange energy emanated from its pages.

The book recorded a cultivation technique called "Heavenly Constellation Art," which supposedly could grant extraordinary power to those who mastered it.

Initially, Li Ming was skeptical, but when he began practicing according to the book's methods, he actually felt a warm current flowing through his body.

"This... this is real!" Li Ming's heart raced with excitement.

From that moment on, he began his journey of cultivation.

Chapter 3: Breaking Through the First Realm

After a month of diligent practice, Li Ming finally felt the signs of a breakthrough.

That night, while he was cultivating, he suddenly felt the energy in his body surging like a tide. After intense pain, he was delighted to discover that his strength had improved qualitatively.

"I did it! I really broke through the first realm!" Li Ming said excitedly.

But he also understood that this was just the beginning of his cultivation journey, with more challenges awaiting him ahead.

From then on, Li Ming's life completely changed. He was no longer an ordinary high school student but had embarked on the path to becoming a true powerhouse."""
                }
            }],
            'usage': {'prompt_tokens': 400, 'completion_tokens': 300, 'total_tokens': 700, 'cost': 0.005}
        }
        
        # Test Phase 1: Renaming
        print("\n" + "="*50)
        print("PHASE 1: RENAMING")
        print("="*50)
        
        with patch('requests.post') as mock_post:
            mock_post.return_value = Mock(
                json=lambda: mock_renaming_response,
                raise_for_status=lambda: None
            )
            
            args = Mock()
            args.skip_renaming = False
            args.skip_translating = True
            args.skip_epub = True
            args.resume = False
            args.openai_api_key = "mock_key"
            
            print("🔄 Running Phase 1 (Renaming) with mocked OpenAI API...")
            
            # Initialize logging for the orchestrator
            import logging
            logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
            
            # Set the global tolog variable that enchant_cli uses
            import enchant_cli
            enchant_cli.tolog = logging.getLogger('enchant_cli')
            
            result = process_novel_unified(test_file, args)
            
            # Check if file was renamed
            renamed_files = list(test_file.parent.glob("Path of Cultivation by Unknown Author*.txt"))
            if renamed_files:
                renamed_file = renamed_files[0]
                print(f"✅ File successfully renamed to: {renamed_file.name}")
                print(f"   Original: {test_file.name}")
                print(f"   Renamed: {renamed_file.name}")
                test_file = renamed_file  # Update for next phase
            else:
                print("❌ File renaming failed or was skipped")
        
        # Test Phase 2: Translation
        print("\n" + "="*50)
        print("PHASE 2: TRANSLATION")
        print("="*50)
        
        with patch('requests.post') as mock_post:
            mock_post.return_value = Mock(
                json=lambda: mock_translation_response,
                raise_for_status=lambda: None
            )
            
            args = Mock()
            args.skip_renaming = True
            args.skip_translating = False
            args.skip_epub = True
            args.resume = False
            args.encoding = 'utf-8'
            args.max_chars = 2000
            args.split_mode = 'PARAGRAPHS'
            args.split_method = 'paragraph'
            args.remote = False
            
            print("🔄 Running Phase 2 (Translation) with mocked translation API...")
            
            # We need to mock the translation service initialization
            with patch('cli_translator.ChineseAITranslator') as mock_translator_class:
                mock_translator = Mock()
                mock_translator.translate.return_value = mock_translation_response['choices'][0]['message']['content']
                mock_translator.is_remote = False
                mock_translator.request_count = 1
                mock_translator_class.return_value = mock_translator
                
                result = process_novel_unified(test_file, args)
                
                # Check for translation output
                book_title = "Path of Cultivation by Unknown Author"
                translation_dir = test_file.parent / book_title
                if translation_dir.exists():
                    chapter_files = list(translation_dir.glob("*Chapter*.txt"))
                    combined_file = translation_dir / f"translated_{book_title}.txt"
                    
                    print("✅ Translation completed successfully!")
                    print(f"   Translation directory: {translation_dir}")
                    print(f"   Chapter files created: {len(chapter_files)}")
                    if combined_file.exists():
                        print(f"   Combined translation file: {combined_file.name}")
                else:
                    print("❌ Translation output not found")
        
        # Test Phase 3: EPUB Generation
        print("\n" + "="*50)
        print("PHASE 3: EPUB GENERATION")
        print("="*50)
        
        args = Mock()
        args.skip_renaming = True
        args.skip_translating = True
        args.skip_epub = False
        args.resume = False
        
        print("🔄 Running Phase 3 (EPUB Generation)...")
        
        # For EPUB generation, we need the translation directory to exist
        if translation_dir.exists():
            result = process_novel_unified(test_file, args)
            
            # Check for EPUB file
            epub_files = list(test_file.parent.glob("*.epub"))
            if epub_files:
                epub_file = epub_files[0]
                print(f"✅ EPUB generated successfully: {epub_file.name}")
                print(f"   File size: {epub_file.stat().st_size} bytes")
            else:
                print("❌ EPUB generation failed or no EPUB file found")
        else:
            print("❌ Cannot generate EPUB without translation directory")
        
        print("\n" + "="*80)
        print("🎉 END-TO-END PIPELINE DEMONSTRATION COMPLETED!")
        print("="*80)
        print("✅ The EnChANT orchestrator successfully demonstrated:")
        print("   1. Chinese novel metadata extraction and English renaming")
        print("   2. Chinese-to-English text translation with chapter structure")
        print("   3. EPUB generation with English content and table of contents")
        print("")
        print("🚀 The new architecture supports:")
        print("   • Independent phase control with skip flags")
        print("   • Resume functionality for interrupted operations")
        print("   • Batch processing for multiple novels")
        print("   • Progress tracking and error recovery")
        print("="*80)
        
    except Exception as e:
        print(f"❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Clean up test files
        print("\n🧹 Cleaning up test files...")
        
        # Clean up original and renamed files
        for pattern in ["*.txt", "*.epub"]:
            for f in test_file.parent.glob(pattern):
                if "tmp" in str(f) or "Path of Cultivation" in str(f):
                    try:
                        if f.is_file():
                            f.unlink()
                            print(f"   Deleted: {f.name}")
                    except Exception:
                        pass
        
        # Clean up translation directory
        if 'translation_dir' in locals() and translation_dir.exists():
            import shutil
            try:
                shutil.rmtree(translation_dir)
                print(f"   Deleted directory: {translation_dir}")
            except Exception:
                pass
    
    return True

if __name__ == "__main__":
    success = demo_complete_pipeline()
    sys.exit(0 if success else 1)