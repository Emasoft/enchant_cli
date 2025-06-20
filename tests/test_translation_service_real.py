#!/usr/bin/env python3
"""
Real API tests for translation_service.py - minimal mocking
"""

import logging
import threading
import time
import sys
import os
import tempfile
from pathlib import Path
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.enchant_book_manager.translation_service import (
    ChineseAITranslator,
    is_latin_char,
    is_latin_charset,
)


@pytest.mark.slow
@pytest.mark.skip(reason="Requires local LLM server running at localhost:1234")
class TestChineseAITranslatorReal:
    """Real API tests for ChineseAITranslator"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test suite"""
        self.logger = logging.getLogger("test_real")
        logging.basicConfig(level=logging.INFO)

    def test_init_local_real(self):
        """Test local translator initialization with real values"""
        translator = ChineseAITranslator(logger=self.logger, use_remote=False, temperature=0.05)

        # Check real configuration values
        assert translator.api_url == "http://localhost:1234/v1/chat/completions"
        assert translator.MODEL_NAME == "qwen3-30b-a3b-mlx@8bit"
        assert translator.temperature == 0.05
        assert translator.timeout == 300  # Production timeout
        assert not translator.is_remote

        return True

    def test_real_translation_local(self):
        """Test actual translation with local API"""
        translator = ChineseAITranslator(logger=self.logger, use_remote=False, temperature=0.05)

        # Test with real Chinese text
        test_text = "你好，世界！这是一个真实的测试。"

        try:
            result = translator.translate(test_text, is_last_chunk=True)

            # Verify result
            assert result is not None, "Translation returned None"
            assert len(result) > 0, "Translation is empty"
            assert not any("\u4e00" <= c <= "\u9fff" for c in result), "Result contains Chinese"

            print(f"✓ Real translation: '{test_text}' -> '{result}'")
            return True
        except Exception as e:
            print(f"✗ Translation failed: {e}")
            return False

    def test_remove_thinking_block_real(self):
        """Test thinking block removal with real translator"""
        translator = ChineseAITranslator(logger=self.logger, use_remote=False, temperature=0.05)

        # Test various thinking block formats
        test_cases = [
            ("<think>internal thoughts</think>Hello world", "Hello world"),
            ("<thinking>thoughts\nmore</thinking>\nText", "Text"),
            ("Start<think>mid</think>End", "StartEnd"),
        ]

        all_passed = True
        for input_text, expected in test_cases:
            result = translator.remove_thinking_block(input_text)
            if result.strip() == expected.strip():
                print("✓ Removed thinking block correctly")
            else:
                print(f"✗ Expected '{expected}', got '{result}'")
                all_passed = False

        return all_passed

    def test_real_wuxia_translation(self):
        """Test wuxia terminology translation with real API"""
        translator = ChineseAITranslator(logger=self.logger, use_remote=False, temperature=0.05)

        # Wuxia text with specific terms
        test_text = "他的修为已达元婴期，丹田中真气充沛。"

        try:
            result = translator.translate(test_text, is_last_chunk=True)

            # Check for correct terminology
            checks = [
                ("Nascent Soul" in result, "元婴 -> Nascent Soul"),
                (
                    "dantian" in result.lower() or "elixir field" in result.lower(),
                    "丹田 terminology",
                ),
                (
                    "qi" in result.lower() or "energy" in result.lower(),
                    "真气 terminology",
                ),
            ]

            passed = 0
            for check, desc in checks:
                if check:
                    print(f"✓ {desc}")
                    passed += 1
                else:
                    print(f"✗ {desc} not found")

            return passed >= 2  # At least 2 out of 3
        except Exception as e:
            print(f"✗ Translation failed: {e}")
            return False

    def test_real_name_translation(self):
        """Test name translation with real API"""
        translator = ChineseAITranslator(logger=self.logger, use_remote=False, temperature=0.05)

        # Text with names that should include meanings
        test_text = '唐舞桐对霍雨浩说："我们走吧。"'

        try:
            result = translator.translate(test_text, is_last_chunk=True)

            # Check name format
            has_tang = "Tang Wutong" in result
            has_meaning = any(phrase in result for phrase in ["Dancing Willow", "Dance Willow", "Dancing Paulownia"])
            has_quotes = '"' in result or '"' in result

            print(f"Result: {result}")
            if has_tang:
                print("✓ Name transliterated")
            if has_meaning:
                print("✓ Name meaning included")
            if has_quotes:
                print("✓ Curly quotes used")

            assert has_tang, "Translation failed to include Tang Wutong"
        except Exception as e:
            print(f"✗ Translation failed: {e}")
            assert False, f"Translation failed: {e}"

    def test_real_double_translation(self):
        """Test double translation with real API"""
        translator = ChineseAITranslator(logger=self.logger, use_remote=False, temperature=0.05)

        # Mixed text that needs double pass
        mixed_text = "Hello 世界, this is a 测试 message."

        try:
            # Single pass
            single = translator.translate_chunk(mixed_text, double_translation=False, is_last_chunk=True)
            print(f"Single pass: {single}")

            # Double pass
            double = translator.translate_chunk(mixed_text, double_translation=True, is_last_chunk=True)
            print(f"Double pass: {double}")

            # Check if double pass removed Chinese
            double_has_chinese = any("\u4e00" <= c <= "\u9fff" for c in double) if double else True

            if not double_has_chinese:
                print("✓ Double translation removed all Chinese")
            else:
                print("✗ Chinese still present after double translation")
                assert False, "Chinese still present after double translation"
        except Exception as e:
            print(f"✗ Translation failed: {e}")
            assert False, f"Translation failed: {e}"

    def test_translate_file_real(self):
        """Test file translation with real API"""
        translator = ChineseAITranslator(logger=self.logger, use_remote=False, temperature=0.05)

        # Create temporary test files
        with tempfile.TemporaryDirectory() as tmpdir:
            input_file = Path(tmpdir) / "test_input.txt"
            output_file = Path(tmpdir) / "test_output.txt"

            # Write Chinese text
            test_content = "这是一个文件翻译测试。\n第二行内容。"
            input_file.write_text(test_content, encoding="utf-8")

            try:
                # Translate file
                translator.translate_file(str(input_file), str(output_file), is_last_chunk=True)

                # Check output
                if output_file.exists():
                    output_content = output_file.read_text(encoding="utf-8")

                    # Verify translation
                    has_chinese = any("\u4e00" <= c <= "\u9fff" for c in output_content)

                    if not has_chinese and len(output_content) > 0:
                        print("✓ File translated successfully")
                        print(f"  Input: {test_content}")
                        print(f"  Output: {output_content}")
                    else:
                        print("✗ File translation incomplete")
                        assert False, "File translation incomplete"
                else:
                    print("✗ Output file not created")
                    assert False, "Output file not created"
            except Exception as e:
                print(f"✗ File translation failed: {e}")
                assert False, f"File translation failed: {e}"

    def test_cost_tracking_local(self):
        """Test that local API doesn't track costs"""
        translator = ChineseAITranslator(logger=self.logger, use_remote=False, temperature=0.05)

        # Make a real translation
        try:
            translator.translate("测试", is_last_chunk=True)

            # Local API should not track costs
            assert translator.total_cost == 0.0
            assert translator.request_count == 0

            print("✓ Local API correctly doesn't track costs")
        except Exception as e:
            print(f"✗ Test failed: {e}")
            assert False, f"Test failed: {e}"

    def test_real_performance(self):
        """Test translation performance with real API"""
        translator = ChineseAITranslator(logger=self.logger, use_remote=False, temperature=0.05)

        # Test with various text lengths
        test_texts = [
            ("Short", "你好"),
            ("Medium", "这是一个中等长度的测试句子，包含多个词汇。"),
            ("Long", "这是一个很长的段落。" * 20),
        ]

        all_passed = True
        for name, text in test_texts:
            try:
                start = time.time()
                result = translator.translate(text, is_last_chunk=True)
                elapsed = time.time() - start

                if result:
                    speed = len(text) / elapsed
                    print(f"✓ {name} text ({len(text)} chars) in {elapsed:.2f}s = {speed:.1f} chars/s")
                else:
                    print(f"✗ {name} text translation failed")
                    all_passed = False
            except Exception as e:
                print(f"✗ {name} text error: {e}")
                all_passed = False

        assert all_passed, "Not all performance tests passed"

    def test_thread_safety_real(self):
        """Test thread safety with real concurrent translations"""
        translator = ChineseAITranslator(logger=self.logger, use_remote=False, temperature=0.05)

        results = []
        errors = []

        def translate_task(text, index):
            try:
                result = translator.translate(text, is_last_chunk=True)
                results.append((index, result))
            except Exception as e:
                errors.append((index, str(e)))

        # Create threads
        threads = []
        test_texts = ["测试一", "测试二", "测试三"]

        for i, text in enumerate(test_texts):
            thread = threading.Thread(target=translate_task, args=(text, i))
            threads.append(thread)
            thread.start()

        # Wait for all
        for thread in threads:
            thread.join(timeout=30)

        # Check results
        if errors:
            print(f"✗ Thread errors: {errors}")
            assert False, f"Thread errors: {errors}"

        if len(results) == len(test_texts):
            print(f"✓ All {len(test_texts)} concurrent translations completed")
        else:
            print(f"✗ Only {len(results)}/{len(test_texts)} translations completed")
            assert False, f"Only {len(results)}/{len(test_texts)} translations completed"


class TestUtilityFunctionsReal:
    """Test utility functions with real data"""

    def test_is_latin_char_comprehensive(self):
        """Test Latin character detection comprehensively"""
        test_cases = [
            # Basic Latin
            ("A", True, "Basic Latin"),
            ("z", True, "Basic Latin"),
            ("5", True, "Digit"),
            # Extended Latin
            ("é", True, "Latin with accent"),
            ("ñ", True, "Latin with tilde"),
            ("ü", True, "Latin with umlaut"),
            ("œ", True, "Latin ligature"),
            # Non-Latin
            ("中", False, "Chinese"),
            ("あ", False, "Japanese Hiragana"),
            ("א", False, "Hebrew"),
            ("🙂", False, "Emoji"),
            ("∑", False, "Math symbol"),
        ]

        all_passed = True
        for char, expected, desc in test_cases:
            result = is_latin_char(char)
            if result == expected:
                print(f"✓ {desc}: '{char}' -> {result}")
            else:
                print(f"✗ {desc}: '{char}' expected {expected}, got {result}")
                all_passed = False

        assert all_passed, "Not all test cases passed"

    def test_is_latin_charset_real_texts(self):
        """Test charset detection with real text samples"""
        test_cases = [
            # Pure English
            ("Hello World! This is a test.", True, "Pure English"),
            ("Testing 123 with numbers.", True, "English with numbers"),
            # Mixed content
            ("Hello 世界", False, "English + Chinese"),
            ("Test 测试", False, "Mixed languages"),
            # Pure non-Latin
            ("你好世界", False, "Pure Chinese"),
            ("こんにちは", False, "Pure Japanese"),
            ("مرحبا", False, "Pure Arabic"),
            # Edge cases
            ("", True, "Empty string"),
            ("   ", True, "Only spaces"),
            ("123.45", True, "Numbers and punctuation"),
            ("\n\t", True, "Only whitespace"),
        ]

        all_passed = True
        for text, expected, desc in test_cases:
            result = is_latin_charset(text)
            if result == expected:
                print(f"✓ {desc}: {result}")
            else:
                print(f"✗ {desc}: expected {expected}, got {result}")
                all_passed = False

        assert all_passed, "Not all test cases passed"


def run_all_real_tests():
    """Run all real API tests"""
    print("=" * 80)
    print("REAL API TESTS FOR TRANSLATION SERVICE")
    print("=" * 80)

    # Check server first
    import requests

    try:
        response = requests.get("http://127.0.0.1:1234/v1/models", timeout=5)
        if response.status_code != 200:
            print("⚠️  LM Studio server not responding properly")
            return
    except Exception as e:
        print(f"⚠️  Cannot connect to LM Studio server at http://127.0.0.1:1234: {e}")
        print("Please ensure LM Studio is running")
        return

    # Initialize test suites
    translator_tests = TestChineseAITranslatorReal()
    utility_tests = TestUtilityFunctionsReal()

    # Run all tests
    tests = [
        # Translator tests
        ("Init Local Real", translator_tests.test_init_local_real),
        ("Real Translation", translator_tests.test_real_translation_local),
        ("Remove Thinking Block", translator_tests.test_remove_thinking_block_real),
        ("Wuxia Translation", translator_tests.test_real_wuxia_translation),
        ("Name Translation", translator_tests.test_real_name_translation),
        ("Double Translation", translator_tests.test_real_double_translation),
        ("File Translation", translator_tests.test_translate_file_real),
        ("Cost Tracking Local", translator_tests.test_cost_tracking_local),
        ("Performance", translator_tests.test_real_performance),
        ("Thread Safety", translator_tests.test_thread_safety_real),
        # Utility tests
        ("Latin Char Detection", utility_tests.test_is_latin_char_comprehensive),
        ("Latin Charset Detection", utility_tests.test_is_latin_charset_real_texts),
    ]

    results = []

    for test_name, test_func in tests:
        print(f"\n{'=' * 60}")
        print(f"Running: {test_name}")
        print("=" * 60)

        try:
            passed = test_func()
            results.append((test_name, passed))
        except Exception as e:
            print(f"✗ Exception: {e}")
            import traceback

            traceback.print_exc()
            results.append((test_name, False))

        time.sleep(0.5)  # Small delay between tests

    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)

    passed = sum(1 for _, p in results if p)
    total = len(results)

    print(f"\n{'Test Name':<30} {'Result':<10}")
    print("-" * 40)
    for test_name, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{test_name:<30} {status}")

    print("-" * 40)
    print(f"Total: {passed}/{total} passed ({passed / total * 100:.1f}%)")
    print("=" * 80)


if __name__ == "__main__":
    run_all_real_tests()
