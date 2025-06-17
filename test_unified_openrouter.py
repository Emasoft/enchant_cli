#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test unified OpenRouter API for both renaming and translation
"""

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from renamenovels import process_novel_file
from translation_service import ChineseAITranslator
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_unified_api():
    """Test that both renaming and translation use OpenRouter API"""
    print("\n" + "="*70)
    print("TESTING UNIFIED OPENROUTER API")
    print("="*70)
    
    # Check for API key
    api_key = os.environ.get('OPENROUTER_API_KEY')
    if not api_key:
        print("❌ OPENROUTER_API_KEY not found in environment variables")
        print("   Please set: export OPENROUTER_API_KEY='your-key-here'")
        return False
    else:
        print(f"✅ OPENROUTER_API_KEY found (length: {len(api_key)})")
    
    # Test Phase 1: Renaming with OpenRouter
    print("\n" + "="*60)
    print("PHASE 1: Testing Renaming with OpenRouter")
    print("="*60)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        test_file = Path(temp_dir) / "都市异能王.txt"
        test_content = """第一章 觉醒异能

张伟是一个普通的上班族，但一场意外让他获得了超能力。

那是一个雷雨交加的夜晚，张伟被闪电击中却奇迹般地活了下来。

更神奇的是，他发现自己能控制电流。

"这是怎么回事？"张伟看着自己冒出电光的双手，心中充满震惊。
"""
        
        test_file.write_text(test_content, encoding='utf-8')
        print(f"✅ Created test file: {test_file.name}")
        
        try:
            # Temporarily disable iCloud to avoid command validation issues
            import renamenovels
            original_icloud = renamenovels.ICLOUD
            renamenovels.ICLOUD = False
            
            print("\n📝 Calling OpenRouter API for renaming...")
            success, new_path, metadata = process_novel_file(
                test_file,
                api_key,
                model="gpt-4o-mini",  # Will be mapped to openai/gpt-4o-mini
                temperature=0.0
            )
            
            if success and new_path != test_file:
                print(f"✅ Successfully renamed using OpenRouter:")
                print(f"   Original: {test_file.name}")
                print(f"   New name: {new_path.name}")
                if metadata:
                    print(f"   Title: {metadata.get('novel_title_english', 'N/A')}")
                    print(f"   Author: {metadata.get('author_name_english', 'N/A')}")
                phase1_success = True
            else:
                print("❌ Renaming failed")
                phase1_success = False
                
        except Exception as e:
            print(f"❌ Error during renaming: {e}")
            import traceback
            traceback.print_exc()
            phase1_success = False
        finally:
            # Restore original iCloud setting
            if 'original_icloud' in locals():
                renamenovels.ICLOUD = original_icloud
    
    # Test Phase 2: Translation with OpenRouter
    print("\n" + "="*60)
    print("PHASE 2: Testing Translation with OpenRouter")
    print("="*60)
    
    try:
        translator = ChineseAITranslator(
            logger=logger,
            use_remote=True,
            api_key=api_key,
            double_pass=False
        )
        
        print(f"📡 Using API: {translator.api_url}")
        print(f"🤖 Model: {translator.MODEL_NAME}")
        
        test_text = "这是一个测试。我们正在验证统一的API是否正常工作。"
        print(f"\n📝 Testing translation: '{test_text}'")
        
        result = translator.translate(test_text, is_last_chunk=True)
        
        if result:
            print(f"✅ Translation successful:")
            print(f"   Result: '{result}'")
            
            # Show cost tracking
            if translator.total_cost > 0:
                print(f"\n💰 Cost tracking working:")
                print(f"   Total cost: ${translator.total_cost:.6f}")
                print(f"   Total tokens: {translator.total_tokens}")
            
            phase2_success = True
        else:
            print("❌ Translation failed")
            phase2_success = False
            
    except Exception as e:
        print(f"❌ Error during translation: {e}")
        import traceback
        traceback.print_exc()
        phase2_success = False
    
    # Summary
    print("\n" + "="*70)
    print("UNIFIED OPENROUTER API TEST SUMMARY")
    print("="*70)
    print(f"Phase 1 (Renaming):    {'✅ PASSED' if phase1_success else '❌ FAILED'}")
    print(f"Phase 2 (Translation): {'✅ PASSED' if phase2_success else '❌ FAILED'}")
    print("\nBoth phases now use OpenRouter API with unified cost tracking!")
    print("="*70)
    
    return phase1_success and phase2_success

if __name__ == "__main__":
    success = test_unified_api()
    sys.exit(0 if success else 1)