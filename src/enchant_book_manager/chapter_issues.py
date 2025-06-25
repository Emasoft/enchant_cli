#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
# - Created new module from chapter_detector.py refactoring
# - Contains issue detection logic for chapter sequences
# - Includes detect_issues function
#

"""
chapter_issues.py - Issue detection for chapter sequences
=========================================================

Contains functions to detect issues in chapter numbering sequences,
including missing numbers, repeats, swaps, and out-of-place chapters.
"""

from __future__ import annotations


def detect_issues(seq: list[int]) -> list[str]:
    """
    Updated algorithm provided by user: reports missing, repeats, swaps,
    out-of-place, duplicates.
    """
    if not seq:
        return []

    issues = []
    start, end = seq[0], seq[-1]
    prev_expected = start
    seen = set()
    reported_missing = set()

    for idx, v in enumerate(seq):
        # 1) Repeats: only on second+ occurrence
        if v in seen:
            # find nearest non-identical predecessor
            try:
                pred = next(x for x in reversed(seq[:idx]) if x != v)
            except StopIteration:
                # No non-identical predecessor found (all previous values are the same)
                # Use the first value in sequence, or 0 if this is the first
                pred = seq[0] if idx > 0 and seq[0] != v else 0
            # count run length from here
            run_len = 1
            j = idx
            while j + 1 < len(seq) and seq[j + 1] == v:
                run_len += 1
                j += 1
            t = "times" if run_len > 1 else "time"
            issues.append((idx, f"number {v} is repeated {run_len} {t} after number {pred}"))
        else:
            seen.add(v)

        # 2) Missing: jumped past some values
        if v > prev_expected:
            for m in range(prev_expected, v):
                if m not in reported_missing:
                    issues.append((idx, f"number {m} is missing"))
                    reported_missing.add(m)
            prev_expected = v + 1

        # 3) Exact hit
        elif v == prev_expected:
            prev_expected += 1

        # 4) Below expectation → swap or out-of-place
        else:  # v < prev_expected
            if idx > 0 and abs(seq[idx - 1] - v) == 1 and v < seq[idx - 1]:
                a, b = min(v, seq[idx - 1]), max(v, seq[idx - 1])
                issues.append((idx, f"number {a} is switched in place with number {b}"))
                issues.append((idx, f"number {b} is switched in place with number {a}"))
            else:
                issues.append((idx, f"number {v} is out of place after number {seq[idx - 1]}"))
            prev_expected = v + 1

    # tail missing
    for m in range(prev_expected, end + 1):
        if m not in reported_missing:
            issues.append((len(seq), f"number {m} is missing"))

    issues.sort(key=lambda x: x[0])
    return [msg for _, msg in issues]
