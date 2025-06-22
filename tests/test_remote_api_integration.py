#!/usr/bin/env python3
"""
Integration tests for remote API functionality using OpenRouter.
These tests require OPENROUTER_API_KEY environment variable to be set.
"""

import os
import sys
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from enchant_book_manager.translation_service import ChineseAITranslator
from enchant_book_manager.renamenovels import process_novel_file
from enchant_book_manager.enchant_cli import process_novel_unified
from enchant_book_manager.cost_tracker import global_cost_tracker


@pytest.mark.remote
@pytest.mark.skipif(not os.getenv("OPENROUTER_API_KEY"), reason="OPENROUTER_API_KEY environment variable not set")
class TestRemoteAPIIntegration:
    """Test suite for remote API integration with OpenRouter"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup for each test"""
        # Reset global cost tracker
        global_cost_tracker.reset()

    def test_remote_translation_basic(self):
        """Test basic translation using remote OpenRouter API"""
        translator = ChineseAITranslator(use_remote=True, temperature=0.0)

        # Simple Chinese text
        test_text = "你好，世界！"

        result = translator.translate(test_text, is_last_chunk=True)

        assert result is not None
        assert len(result) > 0
        assert "Hello" in result or "hello" in result
        assert "world" in result or "World" in result

        # Check cost tracking
        summary = global_cost_tracker.get_summary()
        assert summary["request_count"] > 0
        assert summary["total_cost"] > 0

    def test_remote_translation_with_names(self):
        """Test translation of Chinese names using remote API"""
        translator = ChineseAITranslator(use_remote=True, temperature=0.0)

        # Text with Chinese names
        test_text = "李明和王芳是好朋友。"

        result = translator.translate(test_text, is_last_chunk=True)

        assert result is not None
        assert "Li Ming" in result or "Li" in result
        assert "Wang Fang" in result or "Wang" in result

    def test_remote_renaming_api(self):
        """Test novel renaming using remote OpenRouter API"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create test Chinese novel file
            novel_file = temp_path / "修炼高手.txt"
            novel_file.write_text("第一章 开始修炼\n\n张三开始了他的修炼之路。", encoding="utf-8")

            # Test renaming with remote API
            api_key = os.getenv("OPENROUTER_API_KEY")
            success, new_path, metadata = process_novel_file(novel_file, api_key=api_key, model="gpt-4o-mini", temperature=0.0, dry_run=False)

            assert success is True
            assert new_path is not None
            assert new_path.exists()
            assert metadata is not None
            assert "novel_title_english" in metadata

            # Check cost tracking
            summary = global_cost_tracker.get_summary()
            assert summary["request_count"] > 0
            assert summary["total_cost"] > 0

    def test_remote_full_orchestration(self):
        """Test full orchestration with remote API for translation"""
        import os

        original_cwd = os.getcwd()

        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)

                # Change to temp directory so translation output goes there
                os.chdir(temp_path)

                # Create test Chinese novel file
                novel_file = temp_path / "测试小说.txt"
                novel_file.write_text("第一章 开始\n\n这是一个测试。\n\n第二章 继续\n\n故事继续发展。", encoding="utf-8")

                # Mock args for orchestration
                from unittest.mock import Mock

                args = Mock()
                args.skip_renaming = True  # Skip renaming to save API calls
                args.skip_translating = False
                args.skip_epub = True  # Skip EPUB to focus on translation
                args.resume = False
                args.encoding = "utf-8"
                args.max_chars = 2000
                args.remote = True  # Use remote API
                args.translated = None

                # Test orchestration with remote translation
                success = process_novel_unified(novel_file, args)

                assert success is True

                # Check that translation output was created
                # When skip_renaming is True, an empty title creates "by n.d" directory
                # Look for directories created in the current (temp) directory
                subdirs = [d for d in Path.cwd().iterdir() if d.is_dir() and d.name != "__pycache__"]
                assert len(subdirs) > 0, f"No translation directory was created. CWD contents: {list(Path.cwd().iterdir())}"

                # Check that the translation directory contains translated files
                translation_dir = subdirs[0]
                txt_files = list(translation_dir.glob("*.txt"))
                assert len(txt_files) > 0, f"No translated text files found in {translation_dir}"

                # Check cost tracking
                summary = global_cost_tracker.get_summary()
                assert summary["request_count"] > 0
                assert summary["total_cost"] > 0
        finally:
            # Restore original directory
            os.chdir(original_cwd)

    def test_remote_cost_tracking_accuracy(self):
        """Test that cost tracking is accurate for remote API calls"""
        translator = ChineseAITranslator(use_remote=True, temperature=0.0)

        # Reset tracker
        global_cost_tracker.reset()

        # Make multiple translation requests
        test_texts = ["这是第一个测试。", "这是第二个测试。", "这是第三个测试。"]

        for text in test_texts:
            result = translator.translate(text, is_last_chunk=True)
            assert result is not None

        # Verify cost tracking
        summary = global_cost_tracker.get_summary()
        # With double-pass translation, each text generates 2 API requests
        expected_requests = len(test_texts) * 2 if translator.double_pass else len(test_texts)
        assert summary["request_count"] == expected_requests
        assert summary["total_cost"] > 0
        assert summary["total_tokens"] > 0
        assert summary["average_cost_per_request"] > 0

    def test_remote_error_handling(self):
        """Test error handling with invalid API key"""
        # Temporarily set invalid API key
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "invalid_key"}):
            translator = ChineseAITranslator(use_remote=True, temperature=0.0)

            # This should raise an exception due to invalid API key
            # The retry mechanism may cause SystemExit on critical failures
            with pytest.raises((Exception, SystemExit)):
                translator.translate("测试文本", is_last_chunk=True)


@pytest.mark.remote
@pytest.mark.skipif(not os.getenv("OPENROUTER_API_KEY"), reason="OPENROUTER_API_KEY environment variable not set")
class TestRemoteAPIPerformance:
    """Performance tests for remote API"""

    def test_remote_api_timeout_handling(self):
        """Test timeout handling for remote API calls"""
        # Create translator with very short timeout
        translator = ChineseAITranslator(use_remote=True, temperature=0.0)
        translator.timeout = 0.001  # 1ms timeout to force timeout

        # This should timeout or exit due to critical error
        # The retry mechanism may cause SystemExit on critical failures
        with pytest.raises((Exception, SystemExit)) as exc_info:
            translator.translate("这是一个很长的测试文本，需要一些时间来翻译。", is_last_chunk=True)

        # Check that it's a timeout-related error or SystemExit from critical failure
        if isinstance(exc_info.value, SystemExit):
            # This is expected due to retry exhaustion on critical operations
            assert True
        else:
            assert "timeout" in str(exc_info.value).lower() or "timed out" in str(exc_info.value).lower()

    def test_remote_concurrent_requests(self):
        """Test concurrent requests to remote API"""
        import threading
        import time

        translator = ChineseAITranslator(use_remote=True, temperature=0.0)
        results = []
        errors = []

        def translate_text(text, index):
            try:
                start = time.time()
                result = translator.translate(text, is_last_chunk=True)
                elapsed = time.time() - start
                results.append((index, result, elapsed))
            except Exception as e:
                errors.append((index, str(e)))

        # Create threads for concurrent requests
        threads = []
        test_texts = ["这是第一个并发测试。", "这是第二个并发测试。", "这是第三个并发测试。"]

        for i, text in enumerate(test_texts):
            thread = threading.Thread(target=translate_text, args=(text, i))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=60)

        # Verify results
        assert len(results) + len(errors) == len(test_texts)
        assert len(errors) == 0, f"Concurrent requests failed: {errors}"

        # All results should be valid
        for index, result, elapsed in results:
            assert result is not None
            assert len(result) > 0
            assert elapsed > 0
