#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitHub Actions test environment configuration.

This module sets up the test environment for CI/CD pipelines,
specifically configuring tests to run in remote-only mode.
"""

import os
import sys

# Set environment variable to indicate we're in CI
os.environ["CI"] = "true"
os.environ["GITHUB_ACTIONS"] = "true"

# Disable local mode testing
os.environ["SKIP_LOCAL_MODE_TESTS"] = "true"

# Set a dummy API key for tests (not a real key)
os.environ["OPENROUTER_API_KEY"] = os.environ.get("OPENROUTER_API_KEY", "test_api_key_for_ci")

# Reduce timeouts for CI
os.environ["TEST_TIMEOUT"] = "30"

print("GitHub Actions test environment configured:")
print(f"- CI: {os.environ.get('CI')}")
print(f"- GITHUB_ACTIONS: {os.environ.get('GITHUB_ACTIONS')}")
print(f"- SKIP_LOCAL_MODE_TESTS: {os.environ.get('SKIP_LOCAL_MODE_TESTS')}")
print(f"- OPENROUTER_API_KEY: {'***' if os.environ.get('OPENROUTER_API_KEY') else 'Not set'}")
print(f"- TEST_TIMEOUT: {os.environ.get('TEST_TIMEOUT')}")