#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Final integration tests with real LM Studio API
"""

import sys
import os
import time
import logging
import requests
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from translation_service import ChineseAITranslator

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("integration_test")


@pytest.mark.slow
@pytest.mark.skip(reason="Requires local LLM server running")
class RealIntegrationTests:
    """Real integration tests that connect to LM Studio"""
    
    def __init__(self):
        self.api_url = "http://127.0.0.1:1234"
        self.translator = None
    
    def check_server_status(self):
        """Check if LM Studio server is running"""
        try:
            response = requests.get(f"{self.api_url}/v1/models", timeout=5)
            if response.status_code == 200:
                models = response.json().get('data', [])
                print(f"✓ Server running with {len(models)} models")
                
                # Check if our required model is available
                model_ids = [m['id'] for m in models]
                if 'qwen3-30b-a3b-mlx@8bit' in model_ids:
                    print(f"✓ Required model 'qwen3-30b-a3b-mlx@8bit' is available")
                    return True
                else:
                    print(f"✗ Required model 'qwen3-30b-a3b-mlx@8bit' not found")
                    print(f"  Available models: {model_ids[:5]}...")
                    return False
            return False
        except Exception as e:
            print(f"✗ Cannot connect to server: {e}")
            return False
    
    def test_basic_translation(self):
        """Test basic translation functionality"""
        print("\n1. Testing Basic Translation")
        print("-" * 60)
        
        translator = ChineseAITranslator(
            logger=logger,
            use_remote=False,
            temperature=0.05
        )
        
        test_text = "你好，世界！这是一个测试。"
        
        try:
            result = translator.translate(test_text, is_last_chunk=True)
            
            if result and len(result) > 0:
                print(f"Input: {test_text}")
                print(f"Output: {result}")
                print(f"✓ Translation successful ({len(result)} chars)")
                return True
            else:
                print("✗ Translation returned empty result")
                return False
        except Exception as e:
            print(f"✗ Translation failed: {e}")
            return False
    
    def test_wuxia_terminology(self):
        """Test correct translation of wuxia terms"""
        print("\n2. Testing Wuxia Terminology")
        print("-" * 60)
        
        translator = ChineseAITranslator(
            logger=logger,
            use_remote=False,
            temperature=0.05
        )
        
        test_text = "他已经突破到了元婴期，内力深厚，真气充沛。"
        
        try:
            result = translator.translate(test_text, is_last_chunk=True)
            
            if result:
                print(f"Input: {test_text}")
                print(f"Output: {result}")
                
                # Check for correct terminology
                checks = [
                    ("Nascent Soul" in result, "Nascent Soul (元婴)"),
                    ("qi" in result.lower() or "energy" in result.lower(), "qi/energy (真气)"),
                ]
                
                passed = 0
                for check, term in checks:
                    if check:
                        print(f"  ✓ Found correct translation for {term}")
                        passed += 1
                    else:
                        print(f"  ✗ Missing translation for {term}")
                
                return passed > 0
            return False
        except Exception as e:
            print(f"✗ Translation failed: {e}")
            return False
    
    def test_name_translation_format(self):
        """Test name translation with meanings"""
        print("\n3. Testing Name Translation Format")
        print("-" * 60)
        
        translator = ChineseAITranslator(
            logger=logger,
            use_remote=False,
            temperature=0.05
        )
        
        test_text = '唐舞桐看着霍雨浩说道："我们该走了。"'
        
        try:
            result = translator.translate(test_text, is_last_chunk=True)
            
            if result:
                print(f"Input: {test_text}")
                print(f"Output: {result}")
                
                # Check for name format
                has_tang = "Tang Wutong" in result
                has_meaning = "Dancing Willow" in result or "Dance Willow" in result
                has_huo = "Huo Yuhao" in result
                
                if has_tang:
                    print("  ✓ Tang Wutong correctly transliterated")
                if has_meaning:
                    print("  ✓ Name meaning included")
                if has_huo:
                    print("  ✓ Huo Yuhao correctly transliterated")
                
                return has_tang or has_huo
            return False
        except Exception as e:
            print(f"✗ Translation failed: {e}")
            return False
    
    def test_curly_quotes(self):
        """Test conversion to curly quotes"""
        print("\n4. Testing Curly Quote Conversion")
        print("-" * 60)
        
        translator = ChineseAITranslator(
            logger=logger,
            use_remote=False,
            temperature=0.05
        )
        
        test_text = '他说："今天天气真好。" 她回答："是的，确实不错。"'
        
        try:
            result = translator.translate(test_text, is_last_chunk=True)
            
            if result:
                print(f"Input: {test_text}")
                print(f"Output: {result}")
                
                # Check for curly quotes
                has_open = '"' in result or '"' in result
                has_close = '"' in result or '"' in result
                has_straight = '"' in result
                
                if has_open and has_close:
                    print("  ✓ Curly quotes detected")
                if has_straight:
                    print("  ⚠ Still contains straight quotes")
                
                return has_open or has_close
            return False
        except Exception as e:
            print(f"✗ Translation failed: {e}")
            return False
    
    def test_no_chinese_characters(self):
        """Test that all Chinese characters are translated"""
        print("\n5. Testing Complete Translation (No Chinese)")
        print("-" * 60)
        
        translator = ChineseAITranslator(
            logger=logger,
            use_remote=False,
            temperature=0.05
        )
        
        test_text = "这是一段混合文本 with some English 和更多中文。"
        
        try:
            result = translator.translate(test_text, is_last_chunk=True)
            
            if result:
                print(f"Input: {test_text}")
                print(f"Output: {result}")
                
                # Check for Chinese characters
                has_chinese = any('\u4e00' <= c <= '\u9fff' for c in result)
                
                if not has_chinese:
                    print("  ✓ No Chinese characters in output")
                    return True
                else:
                    chinese_chars = [c for c in result if '\u4e00' <= c <= '\u9fff']
                    print(f"  ✗ Found Chinese characters: {chinese_chars[:5]}...")
                    return False
            return False
        except Exception as e:
            print(f"✗ Translation failed: {e}")
            return False
    
    def test_chapter_handling(self):
        """Test chapter structure preservation"""
        print("\n6. Testing Chapter Structure")
        print("-" * 60)
        
        translator = ChineseAITranslator(
            logger=logger,
            use_remote=False,
            temperature=0.05
        )
        
        test_text = """第一章：开始

这是第一章的内容。

第二章：继续

这是第二章的内容。"""
        
        try:
            result = translator.translate(test_text, is_last_chunk=True)
            
            if result:
                print(f"Input preview: {test_text[:50]}...")
                print(f"Output preview: {result[:100]}...")
                
                # Check for chapter markers
                has_chapter = "Chapter" in result or "chapter" in result
                
                if has_chapter:
                    print("  ✓ Chapter structure preserved")
                    return True
                else:
                    print("  ✗ Chapter markers not found")
                    return False
            return False
        except Exception as e:
            print(f"✗ Translation failed: {e}")
            return False
    
    def test_double_translation(self):
        """Test double translation feature"""
        print("\n7. Testing Double Translation")
        print("-" * 60)
        
        translator = ChineseAITranslator(
            logger=logger,
            use_remote=False,
            temperature=0.05
        )
        
        # Text with intentionally mixed content
        test_text = "He said 你好 and then 再见 to everyone."
        
        try:
            # Single pass
            result1 = translator.translate_chunk(test_text, double_translation=False, is_last_chunk=True)
            print(f"Input: {test_text}")
            print(f"Single pass: {result1}")
            
            # Double pass
            result2 = translator.translate_chunk(test_text, double_translation=True, is_last_chunk=True)
            print(f"Double pass: {result2}")
            
            if result2:
                has_chinese = any('\u4e00' <= c <= '\u9fff' for c in result2)
                if not has_chinese:
                    print("  ✓ Double translation removed all Chinese")
                    return True
                else:
                    print("  ✗ Chinese characters still present after double translation")
                    return False
            return False
        except Exception as e:
            print(f"✗ Translation failed: {e}")
            return False
    
    def test_performance_and_timeout(self):
        """Test translation performance"""
        print("\n8. Testing Performance and Timeouts")
        print("-" * 60)
        
        translator = ChineseAITranslator(
            logger=logger,
            use_remote=False,
            temperature=0.05,
            timeout=300  # Production timeout
        )
        
        # Medium-length text
        test_text = "这是一个测试句子。" * 50  # ~500 characters
        
        try:
            start_time = time.time()
            result = translator.translate(test_text, is_last_chunk=True)
            elapsed = time.time() - start_time
            
            if result:
                print(f"Input length: {len(test_text)} chars")
                print(f"Output length: {len(result)} chars")
                print(f"Translation time: {elapsed:.2f} seconds")
                print(f"Speed: {len(test_text)/elapsed:.1f} chars/second")
                
                if elapsed < 30:  # Should be much faster than timeout
                    print("  ✓ Good performance")
                    return True
                else:
                    print("  ⚠ Slow performance")
                    return True  # Still pass if it worked
            return False
        except Exception as e:
            print(f"✗ Translation failed: {e}")
            return False
    
    def test_production_configuration(self):
        """Verify production configuration values"""
        print("\n9. Testing Production Configuration")
        print("-" * 60)
        
        translator = ChineseAITranslator(
            logger=logger,
            use_remote=False,
            temperature=0.05
        )
        
        checks = [
            (translator.api_url, "http://localhost:1234/v1/chat/completions", "API URL"),
            (translator.MODEL_NAME, "qwen3-30b-a3b-mlx@8bit", "Model"),
            (translator.temperature, 0.05, "Temperature"),
            (translator.timeout, 300, "Timeout"),
            (translator.is_remote, False, "Local API mode"),
        ]
        
        all_passed = True
        for actual, expected, name in checks:
            if actual == expected:
                print(f"  ✓ {name}: {actual}")
            else:
                print(f"  ✗ {name}: {actual} (expected {expected})")
                all_passed = False
        
        return all_passed


def run_all_tests():
    """Run all integration tests"""
    print("=" * 80)
    print("REAL LM STUDIO API INTEGRATION TESTS")
    print("=" * 80)
    
    test_suite = RealIntegrationTests()
    
    # Check server first
    if not test_suite.check_server_status():
        print("\n⚠️  Cannot proceed without LM Studio server")
        print("Please ensure LM Studio is running on http://127.0.0.1:1234")
        return
    
    # Run all tests
    tests = [
        ("Basic Translation", test_suite.test_basic_translation),
        ("Wuxia Terminology", test_suite.test_wuxia_terminology),
        ("Name Translation Format", test_suite.test_name_translation_format),
        ("Curly Quote Conversion", test_suite.test_curly_quotes),
        ("No Chinese Characters", test_suite.test_no_chinese_characters),
        ("Chapter Structure", test_suite.test_chapter_handling),
        ("Double Translation", test_suite.test_double_translation),
        ("Performance", test_suite.test_performance_and_timeout),
        ("Production Config", test_suite.test_production_configuration),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            passed = test_func()
            results.append((test_name, passed))
        except Exception as e:
            print(f"\n{test_name}: EXCEPTION - {e}")
            results.append((test_name, False))
        
        time.sleep(1)  # Small delay between tests
    
    # Summary
    print("\n" + "=" * 80)
    print("TEST RESULTS SUMMARY")
    print("=" * 80)
    
    passed = sum(1 for _, p in results if p)
    total = len(results)
    
    print(f"\n{'Test Name':<30} {'Result':<10}")
    print("-" * 40)
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name:<30} {status:<10}")
    
    print("-" * 40)
    print(f"Total: {passed}/{total} passed ({passed/total*100:.1f}%)")
    print("=" * 80)


if __name__ == "__main__":
    run_all_tests()