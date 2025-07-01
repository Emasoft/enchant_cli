#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test suite for retry_utils module.
"""

import pytest
from unittest.mock import Mock, patch
import requests
import time

from enchant_book_manager.retry_utils import (
    network_retry,
    file_io_retry,
    database_retry,
    api_retry,
    critical_network_retry,
    critical_file_retry,
    quick_retry,
)


class TestNetworkRetry:
    """Test the network_retry decorator preset."""

    def test_network_retry_success(self):
        """Test successful operation without retries."""
        mock_func = Mock(return_value="success")

        @network_retry()
        def test_func():
            return mock_func()

        result = test_func()
        assert result == "success"
        assert mock_func.call_count == 1

    def test_network_retry_on_connection_error(self):
        """Test retry on ConnectionError."""
        mock_func = Mock(side_effect=[requests.ConnectionError(), "success"])

        @network_retry(max_attempts=3, max_wait=1.0)
        def test_func():
            return mock_func()

        result = test_func()
        assert result == "success"
        assert mock_func.call_count == 2

    def test_network_retry_on_timeout(self):
        """Test retry on Timeout error."""
        mock_func = Mock(side_effect=[requests.Timeout(), requests.Timeout(), "success"])

        @network_retry(max_attempts=5, max_wait=1.0)
        def test_func():
            return mock_func()

        result = test_func()
        assert result == "success"
        assert mock_func.call_count == 3

    def test_network_retry_max_attempts_exceeded(self):
        """Test failure after max attempts."""
        mock_func = Mock(side_effect=requests.ConnectionError())

        @network_retry(max_attempts=2, max_wait=1.0)
        def test_func():
            return mock_func()

        with pytest.raises(requests.ConnectionError):
            test_func()

        assert mock_func.call_count == 2


class TestFileIORetry:
    """Test the file_io_retry decorator preset."""

    def test_file_io_retry_success(self):
        """Test successful file operation."""
        mock_func = Mock(return_value="file_content")

        @file_io_retry()
        def read_file():
            return mock_func()

        result = read_file()
        assert result == "file_content"
        assert mock_func.call_count == 1

    def test_file_io_retry_on_permission_error(self):
        """Test retry on PermissionError."""
        mock_func = Mock(side_effect=[PermissionError(), "success"])

        @file_io_retry(max_attempts=3, max_wait=1.0)
        def write_file():
            return mock_func()

        result = write_file()
        assert result == "success"
        assert mock_func.call_count == 2

    def test_file_io_retry_on_os_error(self):
        """Test retry on OSError."""
        mock_func = Mock(side_effect=[OSError("Disk full"), OSError("Disk full"), "success"])

        @file_io_retry(max_attempts=5, max_wait=1.0)
        def save_file():
            return mock_func()

        result = save_file()
        assert result == "success"
        assert mock_func.call_count == 3


class TestDatabaseRetry:
    """Test the database_retry decorator preset."""

    def test_database_retry_success(self):
        """Test successful database operation."""
        mock_func = Mock(return_value={"id": 1, "name": "test"})

        @database_retry()
        def get_record():
            return mock_func()

        result = get_record()
        assert result == {"id": 1, "name": "test"}
        assert mock_func.call_count == 1

    def test_database_retry_on_key_error(self):
        """Test retry on KeyError (for in-memory DB)."""
        mock_func = Mock(side_effect=[KeyError("Not found"), {"id": 1}])

        @database_retry(max_attempts=3, max_wait=1.0)
        def get_book():
            return mock_func()

        result = get_book()
        assert result == {"id": 1}
        assert mock_func.call_count == 2

    def test_database_retry_on_runtime_error(self):
        """Test retry on RuntimeError (thread conflicts)."""
        mock_func = Mock(side_effect=[RuntimeError("Lock timeout"), "success"])

        @database_retry(max_attempts=3, max_wait=1.0)
        def update_record():
            return mock_func()

        result = update_record()
        assert result == "success"
        assert mock_func.call_count == 2


class TestAPIRetry:
    """Test the api_retry decorator preset."""

    def test_api_retry_success(self):
        """Test successful API call."""
        mock_func = Mock(return_value={"status": "ok"})

        @api_retry()
        def call_api():
            return mock_func()

        result = call_api()
        assert result == {"status": "ok"}
        assert mock_func.call_count == 1

    def test_api_retry_on_http_error(self):
        """Test retry on HTTPError."""
        mock_func = Mock(side_effect=[requests.HTTPError("500"), {"status": "ok"}])

        @api_retry(max_attempts=3, max_wait=1.0)
        def call_api():
            return mock_func()

        result = call_api()
        assert result == {"status": "ok"}
        assert mock_func.call_count == 2

    def test_api_retry_with_timeout(self):
        """Test API retry respects timeout."""
        call_count = 0

        @api_retry(max_attempts=10, max_wait=5.0, timeout=2.0)
        def slow_api():
            nonlocal call_count
            call_count += 1
            time.sleep(0.6)  # Each attempt takes 0.6 seconds
            raise requests.ConnectionError()

        start_time = time.time()
        with pytest.raises(requests.ConnectionError):
            slow_api()

        elapsed = time.time() - start_time
        # Should timeout after ~2 seconds, allowing for 3-4 attempts
        assert elapsed < 3.0
        assert call_count <= 4


class TestConvenienceAliases:
    """Test the convenience alias decorators."""

    def test_critical_network_retry(self):
        """Test critical_network_retry exits on failure."""
        mock_func = Mock(side_effect=requests.ConnectionError())

        @critical_network_retry()
        def critical_operation():
            return mock_func()

        with patch("sys.exit") as mock_exit:
            critical_operation()
            mock_exit.assert_called_once_with(1)

    def test_critical_file_retry(self):
        """Test critical_file_retry exits on failure."""
        mock_func = Mock(side_effect=PermissionError())

        @critical_file_retry()
        def critical_file_op():
            return mock_func()

        with patch("sys.exit") as mock_exit:
            critical_file_op()
            mock_exit.assert_called_once_with(1)

    def test_quick_retry(self):
        """Test quick_retry with limited attempts."""
        mock_func = Mock(side_effect=[ValueError(), ValueError(), "success"])

        @quick_retry()
        def quick_operation():
            return mock_func()

        result = quick_operation()
        assert result == "success"
        assert mock_func.call_count == 3

        # Test failure after 3 attempts
        mock_func.reset_mock()
        mock_func.side_effect = ValueError()

        @quick_retry()
        def failing_operation():
            return mock_func()

        with pytest.raises(ValueError):
            failing_operation()

        assert mock_func.call_count == 3


class TestRetryWithLogger:
    """Test retry decorators with logger integration."""

    def test_network_retry_with_logger(self):
        """Test that retry uses logger from self if available."""

        class APIClient:
            def __init__(self):
                self.logger = Mock()
                self.call_count = 0

            @network_retry(max_attempts=3, max_wait=1.0)
            def make_request(self):
                self.call_count += 1
                if self.call_count < 2:
                    raise requests.ConnectionError("Network error")
                return "success"

        client = APIClient()
        result = client.make_request()

        assert result == "success"
        assert client.call_count == 2
        # Logger should have been called for retry attempts
        assert client.logger.warning.called
