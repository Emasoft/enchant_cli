#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Real API integration tests that connect to actual services
Requires: LM Studio running on localhost:1234
"""

import sys
import os
import time
import requests
from pathlib import Path
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from translation_service import ChineseAITranslator
from cli_translator import split_chinese_text_in_parts


@pytest.mark.slow
@pytest.mark.skip(reason="Requires local LLM server running")
class TestRealAPIIntegration:
    """Integration tests that connect to real APIs"""
    
    local_api_url = "http://127.0.0.1:1234/v1/chat/completions"
    test_texts = {
        'short': "你好世界",
        'medium': "这是一个测试句子。我们需要验证翻译功能是否正常工作。",
        'long': """第一章：开始
            
            在一个风和日丽的早晨，小明走出了家门。他今天要去参加一个重要的会议。
            路上的风景很美，但他没有心情欣赏。他的心里充满了紧张和期待。
            
            "今天一定要成功！"他在心里默默地说道。
            
            会议室里已经坐满了人。大家都在等待着他的到来。""",
            'wuxia': "他运转内力，将真气凝聚于丹田，准备突破元婴期的瓶颈。",
            'with_names': '唐舞桐微微一笑，对霍雨浩说道："师兄，我们该走了。"'
        }
    
    def check_local_server(self):
        """Check if local LM Studio server is running"""
        try:
            response = requests.get("http://127.0.0.1:1234/v1/models", timeout=5)
            if response.status_code == 200:
                models = response.json()
                print(f"✓ Local server is running with {len(models.get('data', []))} models available")
                if models.get('data'):
                    print(f"  Available models: {[m['id'] for m in models['data']]}")
                return True
            else:
                print(f"✗ Local server returned status code: {response.status_code}")
                return False
        except requests.exceptions.ConnectionError:
            print("✗ Cannot connect to local server at http://127.0.0.1:1234")
            return False
        except Exception as e:
            print(f"✗ Error checking local server: {e}")
            return False
    
    def test_local_api_basic_translation(self):
        """Test basic translation with local API"""
        translator = ChineseAITranslator(
            use_remote=False,
            temperature=0.05  # Production value
        )
        
        # Test short text
        print("\nTesting short text translation...")
        try:
            result = translator.translate(self.test_texts['short'])
            print(f"  Input: {self.test_texts['short']}")
            print(f"  Output: {result}")
            
            # Verify it's English
            if result and all(ord(c) < 128 or c in " .,!?'\"" for c in result):
                print("  ✓ Translation appears to be in English")
                return True
            else:
                print("  ✗ Translation contains non-English characters or is empty")
                return False
        except Exception as e:
            print(f"  ✗ Translation failed: {e}")
            return False
    
    def test_local_api_wuxia_terminology(self):
        """Test that wuxia terminology is translated correctly"""
        translator = ChineseAITranslator(
            use_remote=False,
            temperature=0.05
        )
        
        print("\nTesting wuxia terminology translation...")
        try:
            result = translator.translate(self.test_texts['wuxia'])
            print(f"  Input: {self.test_texts['wuxia']}")
            print(f"  Output: {result}")
            
            # Check for correct terminology
            if result and "Nascent Soul" in result:
                print("  ✓ Correctly translated 元婴 as 'Nascent Soul'")
                return True
            else:
                print("  ✗ Wuxia terminology not translated correctly")
                return False
        except Exception as e:
            print(f"  ✗ Translation failed: {e}")
            return False
    
    def test_local_api_name_translation(self):
        """Test that names are transliterated with meanings"""
        translator = ChineseAITranslator(
            use_remote=False,
            temperature=0.05
        )
        
        print("\nTesting name translation with meanings...")
        try:
            result = translator.translate(self.test_texts['with_names'])
            print(f"  Input: {self.test_texts['with_names']}")
            print(f"  Output: {result}")
            
            # Check for name transliteration
            if result and "Tang Wutong" in result and ("Dancing Willow" in result or "Dance Willow" in result):
                print("  ✓ Name translated with meaning in parentheses")
                return True
            else:
                print("  ✗ Name translation format incorrect")
                return False
        except Exception as e:
            print(f"  ✗ Translation failed: {e}")
            return False
    
    def test_local_api_quotes_formatting(self):
        """Test that quotes are converted to curly quotes"""
        translator = ChineseAITranslator(
            use_remote=False,
            temperature=0.05
        )
        
        print("\nTesting quote formatting...")
        try:
            result = translator.translate(self.test_texts['with_names'])
            print(f"  Checking quote marks in output...")
            
            # Check for curly quotes
            if result and ('"' in result or '"' in result):
                print("  ✓ Curly quotes detected in output")
                return True
            elif result and '"' in result:
                print("  ✗ Regular quotes found instead of curly quotes")
                return False
            else:
                print("  ✗ No quotes found in output")
                return False
        except Exception as e:
            print(f"  ✗ Translation failed: {e}")
            return False
    
    def test_local_api_long_text_handling(self):
        """Test translation of longer text"""
        translator = ChineseAITranslator(
            use_remote=False,
            temperature=0.05
        )
        
        print("\nTesting long text translation...")
        try:
            start_time = time.time()
            result = translator.translate(self.test_texts['long'])
            elapsed = time.time() - start_time
            
            print(f"  Input length: {len(self.test_texts['long'])} characters")
            print(f"  Output length: {len(result) if result else 0} characters")
            print(f"  Translation time: {elapsed:.2f} seconds")
            
            if result and len(result) > 50:
                print("  ✓ Long text translated successfully")
                # Check for chapter preservation
                if "Chapter" in result or "chapter" in result:
                    print("  ✓ Chapter heading preserved")
                return True
            else:
                print("  ✗ Translation too short or empty")
                return False
        except Exception as e:
            print(f"  ✗ Translation failed: {e}")
            return False
    
    def test_local_api_double_translation(self):
        """Test double translation feature"""
        translator = ChineseAITranslator(
            use_remote=False,
            temperature=0.05
        )
        
        print("\nTesting double translation (first pass + refinement)...")
        
        # Create text with mixed Chinese that needs double pass
        mixed_text = "He said 你好 and then continued with 世界和平 in his speech."
        
        try:
            # Single pass
            single_result = translator.translate_chunk(mixed_text, double_translation=False)
            print(f"  Single pass result: {single_result}")
            
            # Double pass
            double_result = translator.translate_chunk(mixed_text, double_translation=True)
            print(f"  Double pass result: {double_result}")
            
            # Check if double pass removed Chinese characters
            chinese_in_single = any('\u4e00' <= c <= '\u9fff' for c in single_result) if single_result else False
            chinese_in_double = any('\u4e00' <= c <= '\u9fff' for c in double_result) if double_result else False
            
            if double_result and not chinese_in_double:
                print("  ✓ Double translation removed all Chinese characters")
                return True
            else:
                print("  ✗ Double translation still contains Chinese characters")
                return False
        except Exception as e:
            print(f"  ✗ Translation failed: {e}")
            return False
    
    def test_chunk_processing_integration(self):
        """Test integration between chunk splitting and translation"""
        # Create a text that will split into multiple chunks
        long_chinese_text = "这是第一段。\n\n" * 1000  # Create ~12000 characters
        
        print("\nTesting chunk processing integration...")
        print(f"  Creating text with ~{len(long_chinese_text)} characters...")
        
        # Split into chunks
        chunks = split_chinese_text_in_parts(long_chinese_text, max_chars=11999)
        print(f"  Split into {len(chunks)} chunks")
        
        if len(chunks) > 1:
            # Test translating first chunk
            translator = ChineseAITranslator(
                use_remote=False,
                temperature=0.05
            )
            
            try:
                result = translator.translate(chunks[0], is_last_chunk=False)
                if result:
                    print(f"  ✓ First chunk translated successfully ({len(result)} chars)")
                    return True
                else:
                    print("  ✗ Chunk translation returned empty result")
                    return False
            except Exception as e:
                print(f"  ✗ Chunk translation failed: {e}")
                return False
        else:
            print("  ✗ Text not split into multiple chunks")
            return False
    
    def test_api_timeout_handling(self):
        """Test timeout handling"""
        translator = ChineseAITranslator(
            use_remote=False,
            temperature=0.05
        )
        
        print("\nTesting timeout handling...")
        
        # Create very long text that might timeout
        huge_text = "这是一个非常长的测试文本。" * 500
        
        try:
            start_time = time.time()
            result = translator.translate_messages(huge_text)
            elapsed = time.time() - start_time
            
            print(f"  Translation completed in {elapsed:.2f} seconds")
            
            if elapsed < 300:  # Production timeout is 300 seconds
                print("  ✓ Translation completed within timeout limit")
                return True
            else:
                print("  ✗ Translation took too long")
                return False
        except Exception as e:
            if "timeout" in str(e).lower():
                print("  ✓ Timeout exception handled correctly")
                return True
            else:
                print(f"  ✗ Unexpected error: {e}")
                return False
    
    def test_production_configuration_values(self):
        """Verify production configuration values are used"""
        translator = ChineseAITranslator(
            use_remote=False,
            temperature=0.05
        )
        
        print("\nVerifying production configuration values...")
        
        checks = [
            (translator.api_url == "http://localhost:1234/v1/chat/completions", "API URL"),
            (translator.MODEL_NAME == "qwen3-30b-a3b-mlx@8bit", "Model name"),
            (translator.temperature == 0.05, "Temperature"),
            (translator.timeout == 300, "Response timeout"),
            (hasattr(translator, 'max_retries') and translator.max_retries == 7, "Max retries")
        ]
        
        all_passed = True
        for check, name in checks:
            if check:
                print(f"  ✓ {name} matches production value")
            else:
                print(f"  ✗ {name} does not match production value")
                all_passed = False
        
        return all_passed


def run_integration_tests():
    """Run all integration tests"""
    test_suite = TestRealAPIIntegration()
    
    print("=" * 80)
    print("REAL API INTEGRATION TESTS")
    print("=" * 80)
    
    # First check if server is available
    if not test_suite.check_local_server():
        print("\n⚠️  Local server not available. Please ensure LM Studio is running.")
        return
    
    # Run all tests
    tests = [
        ('Basic Translation', test_suite.test_local_api_basic_translation),
        ('Wuxia Terminology', test_suite.test_local_api_wuxia_terminology),
        ('Name Translation', test_suite.test_local_api_name_translation),
        ('Quote Formatting', test_suite.test_local_api_quotes_formatting),
        ('Long Text Handling', test_suite.test_local_api_long_text_handling),
        ('Double Translation', test_suite.test_local_api_double_translation),
        ('Chunk Processing', test_suite.test_chunk_processing_integration),
        ('Timeout Handling', test_suite.test_api_timeout_handling),
        ('Production Config', test_suite.test_production_configuration_values),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        print(f"\n{'=' * 60}")
        print(f"Running: {test_name}")
        print("=" * 60)
        
        try:
            if test_func():
                passed += 1
                print(f"\n✅ {test_name} PASSED")
            else:
                failed += 1
                print(f"\n❌ {test_name} FAILED")
        except Exception as e:
            failed += 1
            print(f"\n❌ {test_name} FAILED with exception: {e}")
    
    print("\n" + "=" * 80)
    print(f"INTEGRATION TEST SUMMARY")
    print("=" * 80)
    print(f"Total Tests: {len(tests)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Success Rate: {(passed/len(tests)*100):.1f}%")
    print("=" * 80)


if __name__ == "__main__":
    run_integration_tests()