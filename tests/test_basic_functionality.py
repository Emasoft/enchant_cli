#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Basic functionality tests without retry complications
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Disable retries for testing
import tenacity


def no_retry_call(self, fn, *args, **kwargs):
    return fn(*args, **kwargs)


tenacity.Retrying.__call__ = no_retry_call

from translation_service import ChineseAITranslator, is_latin_charset
from common_text_utils import clean, limit_repeated_chars, remove_html_markup
from cost_tracker import global_cost_tracker


def test_basic_initialization():
    """Test basic translator initialization"""
    # Reset global cost tracker before test
    global_cost_tracker.reset()

    # Local translator
    translator = ChineseAITranslator(use_remote=False)
    assert not translator.is_remote
    assert translator.request_count == 0
    # Check global cost tracker instead of translator.total_cost
    summary = global_cost_tracker.get_summary()
    assert summary["total_cost"] == 0.0
    print("✓ Local translator initialized correctly")

    # Remote translator
    translator = ChineseAITranslator(use_remote=True, api_key="test_key")
    assert translator.is_remote
    assert translator.api_key == "test_key"
    # Check global cost tracker
    summary = global_cost_tracker.get_summary()
    assert summary["total_cost"] == 0.0
    print("✓ Remote translator initialized correctly")


def test_text_processing():
    """Test text processing functions"""
    # Test clean function
    assert clean("  hello  ") == "hello"
    assert clean(" \thello\t ") == "\thello\t"
    print("✓ clean() function works correctly")

    # Test limit_repeated_chars
    assert limit_repeated_chars("aaaaa") == "aaa"
    assert limit_repeated_chars("111111") == "111111"  # Numbers unlimited
    assert limit_repeated_chars("。。。。") == "。"
    print("✓ limit_repeated_chars() function works correctly")

    # Test is_latin_charset
    assert is_latin_charset("Hello World") == True
    assert is_latin_charset("你好世界") == False
    assert is_latin_charset("Hello 世界") == False
    print("✓ is_latin_charset() function works correctly")


def test_html_processing():
    """Test HTML processing"""
    # Test basic HTML removal
    html = "<p>Hello world</p>"
    result = remove_html_markup(html)
    assert "<p>" not in result
    assert "Hello world" in result

    # Test script and style removal
    html2 = "<script>alert('test')</script>Text<style>body{}</style>"
    result2 = remove_html_markup(html2)
    assert "alert" not in result2
    assert "Text" in result2
    assert "body" not in result2

    # Test entity unescaping
    html3 = "<p>Hello &amp; goodbye</p>"
    result3 = remove_html_markup(html3)
    assert "Hello & goodbye" in result3

    print("✓ remove_html_markup() function works correctly")


def test_cost_tracking():
    """Test cost tracking functionality"""
    # Reset global tracker
    global_cost_tracker.reset()

    translator = ChineseAITranslator(use_remote=True, api_key="test_key")

    # Simulate API response with cost tracking
    usage_data = {
        "cost": 0.05,
        "total_tokens": 1000,
        "prompt_tokens": 600,
        "completion_tokens": 400,
    }
    # Track usage through global tracker
    global_cost_tracker.track_usage(usage_data)
    global_cost_tracker.track_usage({"cost": 0.0, "total_tokens": 0})  # Second request

    summary = translator.get_cost_summary()
    assert summary["total_cost"] == 0.05
    assert summary["total_tokens"] == 1000
    assert summary["request_count"] == 2
    assert summary["average_cost_per_request"] == 0.025
    print("✓ Cost tracking works correctly")

    # Test reset
    translator.reset_cost_tracking()
    summary = global_cost_tracker.get_summary()
    assert summary["total_cost"] == 0.0
    assert summary["request_count"] == 0
    print("✓ Cost reset works correctly")


def test_remove_thinking_block():
    """Test thinking block removal"""
    translator = ChineseAITranslator(use_remote=False)

    text = "Hello <think>internal thoughts</think> world"
    result = translator.remove_thinking_block(text)
    assert result == "Hello  world"

    text = "Start <thinking>thoughts</thinking>\nEnd"
    result = translator.remove_thinking_block(text)
    assert result == "Start End"
    print("✓ Thinking block removal works correctly")


def test_format_cost_summary():
    """Test cost summary formatting"""
    # Reset global tracker
    global_cost_tracker.reset()

    translator = ChineseAITranslator(use_remote=True, api_key="test")
    translator.MODEL_NAME = "test-model"

    # Simulate API responses with cost tracking
    for i in range(5):
        usage_data = {
            "cost": 0.03,  # 0.15 total for 5 requests
            "total_tokens": 1000,
            "prompt_tokens": 600,
            "completion_tokens": 400,
        }
        global_cost_tracker.track_usage(usage_data)

    summary = translator.format_cost_summary()
    assert "Total Cost: $0.150000" in summary
    assert "Total Requests: 5" in summary
    assert "Total Tokens: 5,000" in summary
    assert "Model: test-model" in summary
    print("✓ Cost summary formatting works correctly")


if __name__ == "__main__":
    print("Running basic functionality tests...\n")

    test_basic_initialization()
    test_text_processing()
    test_html_processing()
    test_cost_tracking()
    test_remove_thinking_block()
    test_format_cost_summary()

    print("\n✅ All basic tests passed!")
