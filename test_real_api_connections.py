#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test real API connections for Phase 1 (Renaming) and Phase 2 (Translation)
"""

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from renamenovels import process_novel_file, load_config
from translation_service import ChineseAITranslator
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_phase1_renaming():
    """Test Phase 1: Real API connection for novel renaming"""
    print("\n" + "="*60)
    print("PHASE 1: Testing Novel Renaming with Real API")
    print("="*60)
    
    # Check for API key
    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key:
        print("❌ OPENAI_API_KEY not found in environment variables")
        print("   Please set: export OPENAI_API_KEY='your-key-here'")
        return False
    else:
        print(f"✅ OPENAI_API_KEY found (length: {len(api_key)})")
    
    # Create test file
    with tempfile.TemporaryDirectory() as temp_dir:
        test_file = Path(temp_dir) / "修炼至尊.txt"
        test_content = """第一章 重生归来
        
        陈凡睁开眼睛，发现自己回到了十年前。
        
        "这是...我的大学宿舍？"他惊讶地看着周围熟悉的环境。
        
        重生了！他竟然重生了！
        
        前世，他在修真界苦修千年，最终在渡劫时身死道消。
        没想到，竟然回到了一切的起点。
        
        "既然上天给了我重来一次的机会，这一世，我定要走上巅峰！"
        """
        
        test_file.write_text(test_content, encoding='utf-8')
        print(f"\n✅ Created test file: {test_file.name}")
        
        # Test renaming
        try:
            # Load config (it will use defaults if not found)
            config = load_config()
            model = config.get('model', 'gpt-4o-mini')
            temperature = config.get('temperature', 0.0)
            kb_to_read = config.get('kb_to_read', 20)
            
            print("\n📝 Calling OpenAI API to extract title and author...")
            print(f"   Model: {model}")
            print(f"   Temperature: {temperature}")
            
            # Call the process_novel_file function
            renamed_path = process_novel_file(
                test_file,  # Path object
                api_key, 
                model, 
                temperature, 
                kb_to_read
            )
            
            if renamed_path and renamed_path != str(test_file):
                print(f"\n✅ Successfully renamed:")
                print(f"   Original: {test_file.name}")
                print(f"   New name: {Path(renamed_path).name}")
                return True
            else:
                print("\n❌ Renaming failed or no rename needed")
                return False
                
        except Exception as e:
            print(f"\n❌ Error during renaming: {e}")
            import traceback
            traceback.print_exc()
            return False

def test_phase2_translation():
    """Test Phase 2: Real API connection for translation"""
    print("\n" + "="*60)
    print("PHASE 2: Testing Translation with Real API (OpenRouter)")
    print("="*60)
    
    # Check for API key
    api_key = os.environ.get('OPENROUTER_API_KEY')
    if not api_key:
        print("❌ OPENROUTER_API_KEY not found in environment variables")
        print("   Please set: export OPENROUTER_API_KEY='your-key-here'")
        return False
    else:
        print(f"✅ OPENROUTER_API_KEY found (length: {len(api_key)})")
    
    # Test texts
    test_texts = {
        'short': "你好世界",
        'medium': "这是一个测试句子。我们需要验证翻译功能是否正常工作。",
        'wuxia': "他运转内力，将真气凝聚于丹田，准备突破元婴期的瓶颈。",
        'with_names': '唐舞桐微微一笑，对霍雨浩说道："师兄，我们该走了。"',
        'chapter': """第一章 开始

在一个风和日丽的早晨，小明走出了家门。他今天要去参加一个重要的会议。

"今天一定要成功！"他在心里默默地说道。"""
    }
    
    try:
        # Create translator with remote API
        translator = ChineseAITranslator(
            logger=logger,
            use_remote=True,
            api_key=api_key,
            double_pass=False  # Single pass for faster testing
        )
        
        print(f"\n📡 Using API: {translator.api_url}")
        print(f"🤖 Model: {translator.MODEL_NAME}")
        
        # Test each text
        all_passed = True
        for test_name, chinese_text in test_texts.items():
            print(f"\n📝 Testing {test_name}: '{chinese_text[:50]}...'")
            
            try:
                result = translator.translate(chinese_text, is_last_chunk=True)
                
                if result:
                    print(f"✅ Translation successful:")
                    print(f"   Result: '{result[:100]}...'")
                    
                    # Check if result is in English
                    if any('\u4e00' <= c <= '\u9fff' for c in result):
                        print("⚠️  Warning: Result still contains Chinese characters")
                        all_passed = False
                else:
                    print("❌ Translation returned empty result")
                    all_passed = False
                    
            except Exception as e:
                print(f"❌ Translation failed: {e}")
                all_passed = False
        
        # Show cost summary
        if translator.request_count > 0:
            print(f"\n💰 Cost Summary:")
            print(f"   Total requests: {translator.request_count}")
            print(f"   Total tokens: {translator.total_tokens}")
            print(f"   Total cost: ${translator.total_cost:.6f}")
            
        return all_passed
        
    except Exception as e:
        print(f"\n❌ Error creating translator: {e}")
        return False

def main():
    """Run all real API tests"""
    print("\n" + "="*70)
    print("ENCHANT BOOK MANAGER - REAL API CONNECTION TESTS")
    print("="*70)
    
    # Test Phase 1
    phase1_success = test_phase1_renaming()
    
    # Test Phase 2
    phase2_success = test_phase2_translation()
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    print(f"Phase 1 (Renaming):    {'✅ PASSED' if phase1_success else '❌ FAILED'}")
    print(f"Phase 2 (Translation): {'✅ PASSED' if phase2_success else '❌ FAILED'}")
    print("="*70)
    
    return phase1_success and phase2_success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)