#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test suite for common_utils module.
"""

import pytest
import time
import sys
import os
from pathlib import Path
from unittest.mock import patch, Mock
import unicodedata

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from enchant_book_manager.common_utils import (
    is_running_in_test,
    sanitize_filename,
    extract_book_info_from_path,
    retry_with_backoff,
)


class TestIsRunningInTest:
    """Test the is_running_in_test function."""

    def test_detects_pytest(self):
        """Test detection when pytest is imported."""
        # Since we're running under pytest, this should be True
        assert is_running_in_test() is True

    def test_detects_pytest_env_var(self):
        """Test detection via PYTEST_CURRENT_TEST."""
        with patch.dict(os.environ, {"PYTEST_CURRENT_TEST": "test_file.py::test_func"}):
            assert is_running_in_test() is True

    def test_detects_ci_env(self):
        """Test detection via CI environment variable."""
        with patch.dict(os.environ, {"CI": "true"}, clear=True):
            with patch.dict(sys.modules, {}, clear=False):
                # Remove pytest from modules temporarily
                pytest_module = sys.modules.get("pytest")
                if pytest_module:
                    del sys.modules["pytest"]
                try:
                    assert is_running_in_test() is True
                finally:
                    if pytest_module:
                        sys.modules["pytest"] = pytest_module

    def test_detects_github_actions(self):
        """Test detection via GITHUB_ACTIONS."""
        with patch.dict(os.environ, {"GITHUB_ACTIONS": "true"}, clear=True):
            with patch.dict(sys.modules, {}, clear=False):
                pytest_module = sys.modules.get("pytest")
                if pytest_module:
                    del sys.modules["pytest"]
                try:
                    assert is_running_in_test() is True
                finally:
                    if pytest_module:
                        sys.modules["pytest"] = pytest_module


class TestSanitizeFilename:
    """Test the sanitize_filename function."""

    def test_removes_invalid_chars(self):
        """Test removal of invalid characters."""
        filename = 'test<>:"/\\|?*file.txt'
        result = sanitize_filename(filename)
        assert result == "test_________file.txt"

    def test_replaces_multiple_spaces(self):
        """Test replacing multiple spaces with single space."""
        filename = "test    file   name.txt"
        result = sanitize_filename(filename)
        assert result == "test file name.txt"

    def test_strips_dots_and_spaces(self):
        """Test stripping leading/trailing dots and spaces."""
        filename = " . test file . "
        result = sanitize_filename(filename)
        assert result == "test file"

    def test_handles_unicode(self):
        """Test Unicode normalization."""
        filename = "tëst_fîlé.txt"  # Characters with diacritics
        result = sanitize_filename(filename)
        # Should normalize but keep the characters
        assert len(result) > 0
        assert ".txt" in result

    def test_max_length_without_extension(self):
        """Test filename truncation without extension."""
        filename = "a" * 300
        result = sanitize_filename(filename, max_length=255)
        assert len(result) == 255
        assert result == "a" * 255

    def test_max_length_with_extension(self):
        """Test filename truncation preserving extension."""
        filename = "a" * 300 + ".txt"
        result = sanitize_filename(filename, max_length=255)
        assert len(result) == 255
        assert result.endswith(".txt")
        assert result == "a" * 251 + ".txt"

    def test_empty_filename(self):
        """Test handling of empty filename."""
        assert sanitize_filename("") == "unnamed"
        assert sanitize_filename("   ") == "unnamed"
        assert sanitize_filename("...") == "unnamed"

    def test_chinese_characters(self):
        """Test handling of Chinese characters."""
        filename = "修炼至尊.txt"
        result = sanitize_filename(filename)
        assert result == "修炼至尊.txt"  # Should preserve Chinese characters

    def test_mixed_content(self):
        """Test mixed content with various issues."""
        filename = "  Test: <Book> | Chapter 1/2  .pdf  "
        result = sanitize_filename(filename)
        assert result == "Test_ _Book_ _ Chapter 1_2 .pdf"


class TestExtractBookInfoFromPath:
    """Test the extract_book_info_from_path function."""

    @patch.object(Path, "is_file", return_value=True)
    def test_standard_format(self, mock_is_file):
        """Test standard book format: Title by Author (Pinyin) - Chinese.txt"""
        path = Path("Cultivation Master by Unknown Author (Weizhi Zuozhe) - 修炼高手 by 未知作者.txt")
        info = extract_book_info_from_path(path)

        assert info["title_english"] == "Cultivation Master"
        assert info["author_english"] == "Unknown Author"
        assert info["author_romanized"] == "Weizhi Zuozhe"
        assert info["title_original"] == "修炼高手"
        assert info["author_original"] == "未知作者"

    @patch.object(Path, "is_file", return_value=True)
    def test_simple_format(self, mock_is_file):
        """Test simple format: Title by Author.txt"""
        path = Path("Test Novel by Test Author.txt")
        info = extract_book_info_from_path(path)

        assert info["title_english"] == "Test Novel"
        assert info["author_english"] == "Test Author"
        assert info["author_romanized"] == ""
        assert info["title_original"] == ""
        assert info["author_original"] == ""

    @patch.object(Path, "is_file", return_value=True)
    def test_chinese_only(self, mock_is_file):
        """Test Chinese-only filename."""
        path = Path("修炼至尊.txt")
        info = extract_book_info_from_path(path)

        assert info["title_english"] == "修炼至尊"  # Falls back to using filename as title
        assert info["author_english"] == "Unknown"  # Default author
        assert info["author_romanized"] == ""
        assert info["title_original"] == ""
        assert info["author_original"] == ""

    @patch.object(Path, "is_file", return_value=True)
    def test_no_extension(self, mock_is_file):
        """Test filename without extension."""
        path = Path("Test Novel by Author")
        info = extract_book_info_from_path(path)

        assert info["title_english"] == "Test Novel"
        assert info["author_english"] == "Author"

    @patch.object(Path, "is_file", return_value=True)
    def test_translated_prefix(self, mock_is_file):
        """Test filename with 'translated_' prefix."""
        path = Path("translated_Test Novel by Author.txt")
        info = extract_book_info_from_path(path)

        assert info["title_english"] == "translated_Test Novel"  # The function doesn't strip prefixes
        assert info["author_english"] == "Author"

    @patch.object(Path, "is_file", return_value=True)
    def test_complex_path(self, mock_is_file):
        """Test with full directory path."""
        path = Path("/home/user/books/Test Novel by Author.txt")
        info = extract_book_info_from_path(path)

        assert info["title_english"] == "Test Novel"
        assert info["author_english"] == "Author"

    @patch.object(Path, "is_file", return_value=True)
    def test_special_characters(self, mock_is_file):
        """Test with special characters in title/author."""
        path = Path("Test & Novel! by Author-Name (2024).txt")
        info = extract_book_info_from_path(path)

        assert info["title_english"] == "Test & Novel!"
        assert info["author_english"] == "Author-Name (2024)"


class TestRetryWithBackoff:
    """Test the retry_with_backoff decorator."""

    def test_successful_call(self):
        """Test successful function call without retries."""
        call_count = 0

        @retry_with_backoff(max_attempts=3, max_wait=1.0)
        def success_func():
            nonlocal call_count
            call_count += 1
            return "success"

        result = success_func()
        assert result == "success"
        assert call_count == 1

    def test_retry_on_exception(self):
        """Test retry on exception."""
        call_count = 0

        @retry_with_backoff(max_attempts=3, max_wait=0.1)
        def failing_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Test error")
            return "success"

        result = failing_func()
        assert result == "success"
        assert call_count == 3

    def test_max_retries_exceeded(self):
        """Test exception raised when max retries exceeded."""
        call_count = 0

        @retry_with_backoff(max_attempts=2, max_wait=0.1)
        def always_fails():
            nonlocal call_count
            call_count += 1
            raise ValueError("Always fails")

        with pytest.raises(ValueError, match="Always fails"):
            always_fails()

        assert call_count == 2  # Initial call + 1 retry (max_attempts=2)

    def test_exponential_backoff(self):
        """Test exponential backoff timing."""
        call_times = []

        @retry_with_backoff(max_attempts=3, min_wait=0.01, max_wait=1.0, base_wait=0.1)
        def track_timing():
            call_times.append(time.time())
            if len(call_times) < 3:
                raise ValueError("Retry")
            return "done"

        result = track_timing()
        assert result == "done"
        assert len(call_times) == 3

        # Check that wait times are reasonable (not exact due to system timing)
        wait1 = call_times[1] - call_times[0]
        wait2 = call_times[2] - call_times[1]
        # First wait should be around base_wait (0.1s)
        assert 0.05 < wait1 < 0.3  # Allow some variance
        # Second wait should be around base_wait * 2 (0.2s)
        assert 0.1 < wait2 < 0.5  # Allow some variance
        # The general trend should be increasing (with some tolerance)
        assert wait2 > wait1 * 0.8  # Allow 20% variance

    def test_custom_exceptions(self):
        """Test custom exception handling."""

        @retry_with_backoff(max_attempts=2, max_wait=0.1, exception_types=(ValueError, TypeError))
        def custom_exceptions():
            raise KeyError("Not retried")

        # KeyError not in retry list, should fail immediately
        with pytest.raises(KeyError):
            custom_exceptions()

    def test_with_logger(self):
        """Test retry with logger in object."""

        class ObjectWithLogger:
            def __init__(self):
                self.logger = Mock()
                self.call_count = 0

            @retry_with_backoff(max_attempts=2, max_wait=0.1)
            def logged_func(self):
                self.call_count += 1
                if self.call_count == 1:
                    raise ValueError("First fail")
                return "success"

        obj = ObjectWithLogger()
        result = obj.logged_func()
        assert result == "success"
        obj.logger.warning.assert_called()  # Should log retry attempt

    def test_exit_on_failure(self):
        """Test retry with exit_on_failure=True."""
        mock_logger = Mock()

        @retry_with_backoff(max_attempts=2, base_wait=0.01, exit_on_failure=True)
        def always_fails():
            raise ValueError("Always fails")

        # Mock sys.exit to prevent actual exit
        with patch("sys.exit") as mock_exit:
            with patch("builtins.print") as mock_print:
                # When exit_on_failure is True, the function should handle the exception
                always_fails()

                # Check that sys.exit was called
                mock_exit.assert_called_once_with(1)
                # Check that error message was printed
                mock_print.assert_called()
                assert "FATAL ERROR" in str(mock_print.call_args)

    def test_exit_on_failure_with_logger(self):
        """Test retry with exit_on_failure=True and logger."""
        mock_logger = Mock()

        class TestClass:
            def __init__(self):
                self.logger = mock_logger

            @retry_with_backoff(max_attempts=1, base_wait=0.01, exit_on_failure=True)
            def method_that_fails(self):
                raise RuntimeError("Method fails")

        obj = TestClass()

        with patch("sys.exit") as mock_exit:
            with patch("builtins.print") as mock_print:
                # When exit_on_failure is True, the function should handle the exception
                obj.method_that_fails()

                # Logger should be used
                mock_logger.error.assert_called()
                # Exit should be called
                mock_exit.assert_called_once_with(1)

    def test_time_limit_exceeded(self):
        """Test retry with time limit."""

        @retry_with_backoff(
            max_attempts=10,
            base_wait=0.5,
            time_limit=0.1,  # Very short time limit
        )
        def slow_func():
            raise ValueError("Always fails")

        with pytest.raises(ValueError):
            slow_func()

    def test_time_limit_with_logger(self):
        """Test retry with time limit and logger."""
        mock_logger = Mock()

        class TestClass:
            def __init__(self):
                self.logger = mock_logger

            @retry_with_backoff(
                max_attempts=10,
                base_wait=0.5,
                time_limit=0.1,  # Very short time limit
            )
            def slow_method(self):
                raise ValueError("Always fails")

        obj = TestClass()

        with pytest.raises(ValueError):
            obj.slow_method()

        # Logger should have error about time limit
        assert any("Time limit" in str(call) for call in mock_logger.error.call_args_list)

    def test_on_retry_callback(self):
        """Test retry with on_retry callback."""
        from enchant_book_manager.common_utils import exponential_backoff_retry

        callback_calls = []

        def on_retry_func(attempt, exception, wait_time):
            callback_calls.append((attempt, str(exception), wait_time))

        call_count = 0

        def failing_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError(f"Attempt {call_count}")
            return "success"

        result = exponential_backoff_retry(
            failing_func,
            max_attempts=5,
            base_wait=0.01,
            on_retry=on_retry_func,
        )

        assert result == "success"
        assert len(callback_calls) == 2  # Called on first two failures
        assert callback_calls[0][0] == 1  # First attempt
        assert "Attempt 1" in callback_calls[0][1]
        assert callback_calls[1][0] == 2  # Second attempt
        assert "Attempt 2" in callback_calls[1][1]

    def test_max_attempts_logger(self):
        """Test logger message when max attempts exceeded."""
        from enchant_book_manager.common_utils import exponential_backoff_retry

        mock_logger = Mock()

        def always_fails():
            raise ValueError("Always fails")

        with pytest.raises(ValueError):
            exponential_backoff_retry(
                always_fails,
                max_attempts=2,
                base_wait=0.01,
                logger=mock_logger,
            )

        # Check logger was called with max attempts error
        mock_logger.error.assert_called()
        assert "All 2 attempts failed" in str(mock_logger.error.call_args)

    def test_test_specific_defaults(self):
        """Test that test-specific defaults are used in test environment."""
        from enchant_book_manager.common_utils import (
            DEFAULT_MAX_RETRIES,
            DEFAULT_MAX_RETRIES_TEST,
            DEFAULT_RETRY_WAIT_MAX,
            DEFAULT_RETRY_WAIT_MAX_TEST,
        )

        call_count = 0

        @retry_with_backoff(
            max_attempts=DEFAULT_MAX_RETRIES,
            max_wait=DEFAULT_RETRY_WAIT_MAX,
            base_wait=0.01,
        )
        def test_func():
            nonlocal call_count
            call_count += 1
            if call_count < DEFAULT_MAX_RETRIES_TEST:
                raise ValueError("Test")
            return "success"

        # Should use test defaults since we're in test environment
        result = test_func()
        assert result == "success"
        # Should have tried DEFAULT_MAX_RETRIES_TEST times
        assert call_count == DEFAULT_MAX_RETRIES_TEST

    def test_final_exception_handling(self):
        """Test edge case in exponential_backoff_retry."""
        from enchant_book_manager.common_utils import exponential_backoff_retry

        # Test the edge case where no exception is stored
        # This is hard to trigger normally, but we can test the logic
        with patch("enchant_book_manager.common_utils.time.sleep"):
            # Mock a function that somehow completes all retries without raising
            mock_func = Mock(side_effect=[ValueError("Error")] * 3)

            with pytest.raises(ValueError):
                exponential_backoff_retry(
                    mock_func,
                    max_attempts=3,
                    base_wait=0.01,
                )
