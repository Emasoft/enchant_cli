#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test suite for cost_tracker module.
"""

import pytest
import threading
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import logging
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from enchant_book_manager.cost_tracker import CostTracker, global_cost_tracker


class TestCostTracker:
    """Test the CostTracker class."""

    def test_initialization(self):
        """Test CostTracker initialization."""
        tracker = CostTracker()
        assert tracker.total_cost == 0.0
        assert tracker.total_tokens == 0
        assert tracker.total_prompt_tokens == 0
        assert tracker.total_completion_tokens == 0
        assert tracker.request_count == 0
        assert hasattr(tracker, "_lock")

    def test_track_usage_with_cost(self):
        """Test tracking usage with cost information."""
        tracker = CostTracker()
        usage = {
            "cost": 0.001234,
            "prompt_tokens": 100,
            "completion_tokens": 50,
            "total_tokens": 150,
        }

        cost = tracker.track_usage(usage, "test.txt")

        assert cost == 0.001234
        assert tracker.total_cost == 0.001234
        assert tracker.total_tokens == 150
        assert tracker.total_prompt_tokens == 100
        assert tracker.total_completion_tokens == 50
        assert tracker.request_count == 1

    def test_track_usage_without_cost(self):
        """Test tracking usage without cost information."""
        tracker = CostTracker()
        usage = {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}

        cost = tracker.track_usage(usage)

        assert cost == 0.0
        assert tracker.total_cost == 0.0
        assert tracker.total_tokens == 150
        assert tracker.total_prompt_tokens == 100
        assert tracker.total_completion_tokens == 50
        assert tracker.request_count == 1

    def test_track_multiple_requests(self):
        """Test tracking multiple API requests."""
        tracker = CostTracker()

        # First request
        usage1 = {
            "cost": 0.001,
            "prompt_tokens": 100,
            "completion_tokens": 50,
            "total_tokens": 150,
        }
        tracker.track_usage(usage1)

        # Second request
        usage2 = {
            "cost": 0.002,
            "prompt_tokens": 200,
            "completion_tokens": 100,
            "total_tokens": 300,
        }
        tracker.track_usage(usage2)

        assert tracker.total_cost == 0.003
        assert tracker.total_tokens == 450
        assert tracker.total_prompt_tokens == 300
        assert tracker.total_completion_tokens == 150
        assert tracker.request_count == 2

    def test_get_summary(self):
        """Test getting cost tracking summary."""
        tracker = CostTracker()

        # Track some usage
        usage = {
            "cost": 0.005,
            "prompt_tokens": 500,
            "completion_tokens": 250,
            "total_tokens": 750,
        }
        tracker.track_usage(usage)
        tracker.track_usage(usage)  # Track twice

        summary = tracker.get_summary()

        assert summary["total_cost"] == 0.01
        assert summary["total_tokens"] == 1500
        assert summary["total_prompt_tokens"] == 1000
        assert summary["total_completion_tokens"] == 500
        assert summary["request_count"] == 2
        assert summary["average_cost_per_request"] == 0.005

    def test_get_summary_no_requests(self):
        """Test getting summary with no requests."""
        tracker = CostTracker()
        summary = tracker.get_summary()

        assert summary["total_cost"] == 0.0
        assert summary["total_tokens"] == 0
        assert summary["request_count"] == 0
        assert summary["average_cost_per_request"] == 0

    def test_reset(self):
        """Test resetting tracker state."""
        tracker = CostTracker()

        # Track some usage
        usage = {
            "cost": 0.005,
            "prompt_tokens": 500,
            "completion_tokens": 250,
            "total_tokens": 750,
        }
        tracker.track_usage(usage)

        # Reset
        tracker.reset()

        assert tracker.total_cost == 0.0
        assert tracker.total_tokens == 0
        assert tracker.total_prompt_tokens == 0
        assert tracker.total_completion_tokens == 0
        assert tracker.request_count == 0

    def test_thread_safety(self):
        """Test thread safety of cost tracking."""
        tracker = CostTracker()
        num_threads = 10
        requests_per_thread = 100

        def track_usage_thread():
            for _ in range(requests_per_thread):
                usage = {
                    "cost": 0.001,
                    "prompt_tokens": 10,
                    "completion_tokens": 5,
                    "total_tokens": 15,
                }
                tracker.track_usage(usage)

        threads = []
        for _ in range(num_threads):
            thread = threading.Thread(target=track_usage_thread)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Verify all requests were tracked correctly
        assert tracker.request_count == num_threads * requests_per_thread
        assert tracker.total_cost == pytest.approx(num_threads * requests_per_thread * 0.001)
        assert tracker.total_tokens == num_threads * requests_per_thread * 15

    @patch("enchant_book_manager.cost_tracker.logger")
    def test_logging_with_file_path(self, mock_logger):
        """Test logging behavior with file path."""
        tracker = CostTracker()
        usage = {
            "cost": 0.001234,
            "prompt_tokens": 100,
            "completion_tokens": 50,
            "total_tokens": 150,
        }

        tracker.track_usage(usage, "test_file.txt")

        # Check logging calls
        assert mock_logger.info.call_count == 3
        calls = mock_logger.info.call_args_list
        assert "test_file.txt" in calls[0][0][0]
        assert "150 tokens" in calls[0][0][0]
        assert "$0.001234" in calls[0][0][0]

    @patch("enchant_book_manager.cost_tracker.logger")
    def test_logging_without_file_path(self, mock_logger):
        """Test logging behavior without file path."""
        tracker = CostTracker()
        usage = {
            "cost": 0.001234,
            "prompt_tokens": 100,
            "completion_tokens": 50,
            "total_tokens": 150,
        }

        tracker.track_usage(usage)

        # Check logging calls
        assert mock_logger.info.call_count == 3
        calls = mock_logger.info.call_args_list
        assert "Request used" in calls[0][0][0]
        assert "150 tokens" in calls[0][0][0]

    @patch("enchant_book_manager.cost_tracker.logger")
    def test_logging_without_cost(self, mock_logger):
        """Test logging when cost is not available."""
        tracker = CostTracker()
        usage = {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}

        tracker.track_usage(usage)

        # Should log warning about missing cost
        mock_logger.warning.assert_called_once()
        assert "Cost information not available" in mock_logger.warning.call_args[0][0]

    def test_global_cost_tracker_instance(self):
        """Test that global_cost_tracker is properly initialized."""
        assert isinstance(global_cost_tracker, CostTracker)
        # Reset the global tracker in case other tests have used it
        global_cost_tracker.reset()
        assert global_cost_tracker.total_cost == 0.0
        assert global_cost_tracker.request_count == 0

    def test_track_usage_with_string_values(self):
        """Test tracking usage with string values that need conversion."""
        tracker = CostTracker()
        usage = {
            "cost": "0.001234",  # String instead of float
            "prompt_tokens": "100",  # String instead of int
            "completion_tokens": "50",
            "total_tokens": "150",
        }

        cost = tracker.track_usage(usage)

        assert cost == 0.001234
        assert tracker.total_tokens == 150
        assert tracker.total_prompt_tokens == 100
        assert tracker.total_completion_tokens == 50

    def test_track_usage_with_missing_fields(self):
        """Test tracking usage with missing fields."""
        tracker = CostTracker()
        usage = {
            "cost": 0.001
            # Missing token fields
        }

        cost = tracker.track_usage(usage)

        assert cost == 0.001
        assert tracker.total_cost == 0.001
        assert tracker.total_tokens == 0  # Defaults to 0
        assert tracker.total_prompt_tokens == 0
        assert tracker.total_completion_tokens == 0
        assert tracker.request_count == 1

    def test_concurrent_get_summary(self):
        """Test concurrent access to get_summary."""
        tracker = CostTracker()
        results = []

        def get_summary_thread():
            for _ in range(100):
                summary = tracker.get_summary()
                results.append(summary)
                # Also track some usage
                usage = {"cost": 0.001, "total_tokens": 10}
                tracker.track_usage(usage)

        threads = []
        for _ in range(5):
            thread = threading.Thread(target=get_summary_thread)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Verify all summaries are valid
        assert len(results) == 500
        for summary in results:
            assert isinstance(summary, dict)
            assert "total_cost" in summary
            assert "request_count" in summary
