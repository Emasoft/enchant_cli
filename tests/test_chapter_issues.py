#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test suite for chapter_issues module.
"""

import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from enchant_book_manager.chapter_issues import detect_issues


class TestDetectIssues:
    """Test the detect_issues function."""

    def test_empty_sequence(self):
        """Test with empty sequence."""
        result = detect_issues([])
        assert result == []

    def test_perfect_sequence(self):
        """Test with perfect sequential numbers."""
        result = detect_issues([1, 2, 3, 4, 5])
        assert result == []

    def test_single_element(self):
        """Test with single element sequence."""
        result = detect_issues([5])
        assert result == []

    def test_missing_numbers_in_middle(self):
        """Test detection of missing numbers in the middle."""
        result = detect_issues([1, 2, 5, 6])
        assert result == ["number 3 is missing", "number 4 is missing"]

    def test_missing_numbers_at_end(self):
        """Test detection of missing numbers at the end."""
        result = detect_issues([1, 2, 3, 7])
        assert result == [
            "number 4 is missing",
            "number 5 is missing",
            "number 6 is missing",
        ]

    def test_repeated_numbers_simple(self):
        """Test detection of repeated numbers."""
        result = detect_issues([1, 2, 2, 3])
        assert result == [
            "number 2 is repeated 1 time after number 1",
            "number 2 is out of place after number 2",
        ]

    def test_repeated_numbers_multiple_times(self):
        """Test detection of numbers repeated multiple times."""
        result = detect_issues([1, 2, 3, 3, 3, 4])
        assert result == [
            "number 3 is repeated 2 times after number 2",
            "number 3 is out of place after number 3",
            "number 3 is repeated 1 time after number 2",
            "number 3 is out of place after number 3",
        ]

    def test_repeated_numbers_non_consecutive(self):
        """Test repeated numbers that are not consecutive."""
        result = detect_issues([1, 2, 3, 2, 4])
        assert result == [
            "number 2 is repeated 1 time after number 3",
            "number 2 is switched in place with number 3",
            "number 3 is switched in place with number 2",
            "number 3 is missing",
        ]

    def test_swapped_adjacent_numbers(self):
        """Test detection of swapped adjacent numbers."""
        result = detect_issues([1, 3, 2, 4])
        assert result == [
            "number 2 is missing",
            "number 2 is switched in place with number 3",
            "number 3 is switched in place with number 2",
            "number 3 is missing",
        ]

    def test_out_of_place_number(self):
        """Test detection of out-of-place numbers."""
        result = detect_issues([1, 2, 5, 3, 4])
        assert result == [
            "number 3 is missing",
            "number 4 is missing",
            "number 3 is out of place after number 5",
        ]

    def test_complex_sequence(self):
        """Test complex sequence with multiple issues."""
        # Missing 2, repeated 3, out of place 1
        result = detect_issues([1, 3, 3, 5, 1, 6])
        assert result == [
            "number 2 is missing",
            "number 3 is repeated 1 time after number 1",
            "number 3 is out of place after number 3",
            "number 4 is missing",
            "number 1 is repeated 1 time after number 5",
            "number 1 is out of place after number 5",
            "number 3 is missing",
            "number 5 is missing",
        ]

    def test_all_same_numbers(self):
        """Test sequence with all same numbers."""
        result = detect_issues([2, 2, 2, 2])
        assert result == [
            "number 2 is repeated 3 times after number 0",
            "number 2 is out of place after number 2",
            "number 2 is repeated 2 times after number 0",
            "number 2 is out of place after number 2",
            "number 2 is repeated 1 time after number 0",
            "number 2 is out of place after number 2",
        ]

    def test_descending_sequence(self):
        """Test descending sequence (all out of place)."""
        result = detect_issues([5, 4, 3, 2, 1])
        assert result == [
            "number 4 is switched in place with number 5",
            "number 5 is switched in place with number 4",
            "number 3 is switched in place with number 4",
            "number 4 is switched in place with number 3",
            "number 2 is switched in place with number 3",
            "number 3 is switched in place with number 2",
            "number 1 is switched in place with number 2",
            "number 2 is switched in place with number 1",
        ]

    def test_sequence_starting_from_zero(self):
        """Test sequence starting from 0."""
        result = detect_issues([0, 1, 3])
        assert result == ["number 2 is missing"]

    def test_sequence_with_negative_numbers(self):
        """Test sequence with negative numbers."""
        result = detect_issues([-2, -1, 0, 2])
        assert result == ["number 1 is missing"]

    def test_large_gap_in_sequence(self):
        """Test sequence with large gap."""
        result = detect_issues([1, 100])
        # Should report all missing numbers from 2 to 99
        assert len(result) == 98
        assert result[0] == "number 2 is missing"
        assert result[-1] == "number 99 is missing"

    def test_multiple_repeats_with_gaps(self):
        """Test multiple repeats with gaps."""
        result = detect_issues([1, 1, 3, 3, 5, 5])
        expected = [
            "number 1 is repeated 1 time after number 0",
            "number 1 is out of place after number 1",
            "number 2 is missing",
            "number 3 is repeated 1 time after number 1",
            "number 3 is out of place after number 3",
            "number 4 is missing",
            "number 5 is repeated 1 time after number 3",
            "number 5 is out of place after number 5",
        ]
        assert result == expected

    def test_complex_swap_pattern(self):
        """Test complex pattern with multiple swaps."""
        # 1, 3, 2, 5, 4, 6
        result = detect_issues([1, 3, 2, 5, 4, 6])
        assert "number 2 is switched in place with number 3" in result
        assert "number 3 is switched in place with number 2" in result
        assert "number 4 is switched in place with number 5" in result
        assert "number 5 is switched in place with number 4" in result

    def test_repeated_at_beginning(self):
        """Test repeated number at the beginning."""
        result = detect_issues([1, 1, 2, 3])
        assert result == [
            "number 1 is repeated 1 time after number 0",
            "number 1 is out of place after number 1",
        ]

    def test_mixed_issues_comprehensive(self):
        """Test comprehensive mix of all issue types."""
        # 1, missing 2, 3, 3 (repeat), 5 (missing 4), 2 (out of place), 7 (missing 6)
        result = detect_issues([1, 3, 3, 5, 2, 7])
        expected = [
            "number 2 is missing",
            "number 3 is repeated 1 time after number 1",
            "number 3 is out of place after number 3",
            "number 4 is missing",
            "number 2 is out of place after number 5",
            "number 3 is missing",
            "number 5 is missing",
            "number 6 is missing",
        ]
        assert result == expected

    def test_sequence_with_zero_gap(self):
        """Test sequence that includes both positive and negative with gap at zero."""
        result = detect_issues([-2, -1, 1, 2])
        assert result == ["number 0 is missing"]

    def test_single_out_of_place_at_end(self):
        """Test single out of place number at the end."""
        result = detect_issues([1, 2, 3, 4, 1])
        assert result == [
            "number 1 is repeated 1 time after number 4",
            "number 1 is out of place after number 4",
        ]

    def test_performance_with_large_sequence(self):
        """Test performance with large sequence."""
        # Create sequence 1-1000 with some issues
        seq = list(range(1, 501))  # 1-500
        seq.extend([250, 251, 252])  # Add some repeats
        seq.extend(list(range(501, 1001)))  # 501-1000

        result = detect_issues(seq)

        # Should find the 3 repeated numbers
        repeat_issues = [r for r in result if "repeated" in r]
        assert len(repeat_issues) == 3
        assert "number 250 is repeated 1 time after number 500" in result
        assert "number 251 is repeated 1 time after number 250" in result
        assert "number 252 is repeated 1 time after number 251" in result
