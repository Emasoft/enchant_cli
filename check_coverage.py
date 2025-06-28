#!/usr/bin/env python3
"""Quick script to check test coverage."""

import subprocess
import sys

# Run pytest with coverage
result = subprocess.run(["uv", "run", "pytest", "--cov=src/enchant_book_manager", "--cov-report=", "-q"], capture_output=True, text=True)

# Generate coverage report
coverage_result = subprocess.run(["uv", "run", "coverage", "report", "--skip-covered", "--sort=cover"], capture_output=True, text=True)

print("Modules with less than 100% coverage:")
print("=" * 70)
lines = coverage_result.stdout.strip().split("\n")
for line in lines:
    if line.startswith("src/") and "100%" not in line:
        print(line)

print("\n" + "=" * 70)
print("Total coverage summary:")
total_line = [line for line in lines if line.startswith("TOTAL")]
if total_line:
    print(total_line[0])
