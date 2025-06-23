#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test utilities for EnChANT Book Manager.

Provides utilities for test environment detection and configuration.
"""

import os
import sys
import pytest
from typing import Callable, Any


def is_ci_environment() -> bool:
    """
    Detect if tests are running in CI/GitHub Actions environment.

    Returns:
        bool: True if running in CI, False if running locally
    """
    return any(
        [
            os.environ.get("CI") == "true",
            os.environ.get("GITHUB_ACTIONS") == "true",
            os.environ.get("GITHUB_WORKFLOW"),
            os.environ.get("GITHUB_RUN_ID"),
        ]
    )


def is_local_environment() -> bool:
    """
    Detect if tests are running in local development environment.

    Returns:
        bool: True if running locally, False if running in CI
    """
    return not is_ci_environment()


def get_test_profile() -> str:
    """
    Get the current test profile.

    Returns:
        str: "REMOTE-CI" if in GitHub Actions, "LOCAL" otherwise
    """
    return "REMOTE-CI" if is_ci_environment() else "LOCAL"


def skip_if_ci(reason: str = "Skipped in CI environment") -> Callable:
    """
    Decorator to skip tests in CI environment.

    Args:
        reason: Reason for skipping the test

    Returns:
        pytest.mark.skipif decorator
    """
    return pytest.mark.skipif(is_ci_environment(), reason=f"{reason} (profile: REMOTE-CI)")


def skip_if_local(reason: str = "Skipped in local environment") -> Callable:
    """
    Decorator to skip tests in local environment.

    Args:
        reason: Reason for skipping the test

    Returns:
        pytest.mark.skipif decorator
    """
    return pytest.mark.skipif(is_local_environment(), reason=f"{reason} (profile: LOCAL)")


def skip_local_api_tests(reason: str = "Local API not available in CI") -> Callable:
    """
    Decorator to skip tests that require local API (e.g., localhost:1234).

    Args:
        reason: Reason for skipping the test

    Returns:
        pytest.mark.skipif decorator
    """
    return skip_if_ci(reason)


def requires_openrouter_api() -> Callable:
    """
    Decorator for tests that require OpenRouter API key.

    Skips test if OPENROUTER_API_KEY is not set.

    Returns:
        pytest.mark.skipif decorator
    """
    return pytest.mark.skipif(not os.environ.get("OPENROUTER_API_KEY"), reason="OPENROUTER_API_KEY not set")


def requires_openai_api() -> Callable:
    """
    Decorator for tests that require OpenAI API key.

    Skips test if OPENAI_API_KEY is not set.

    Returns:
        pytest.mark.skipif decorator
    """
    return pytest.mark.skipif(not os.environ.get("OPENAI_API_KEY"), reason="OPENAI_API_KEY not set")


# Configuration for different test profiles
TEST_CONFIG = {
    "LOCAL": {
        "max_retries": 10,
        "timeout": 60,
        "api_timeout": 30,
        "run_local_api_tests": True,
        "run_remote_api_tests": True,
        "verbose": True,
    },
    "REMOTE-CI": {
        "max_retries": 2,  # Fewer retries in CI for speed
        "timeout": 5,  # Shorter timeout in CI
        "api_timeout": 10,
        "run_local_api_tests": False,  # Skip local API tests
        "run_remote_api_tests": True,
        "verbose": False,
    },
}


def get_test_config(key: str, default: Any = None) -> Any:
    """
    Get test configuration value based on current profile.

    Args:
        key: Configuration key to retrieve
        default: Default value if key not found

    Returns:
        Configuration value for current profile
    """
    profile = get_test_profile()
    config = TEST_CONFIG.get(profile, TEST_CONFIG["LOCAL"])
    return config.get(key, default)


# Print test profile information when module is imported
if __name__ != "__main__":
    profile = get_test_profile()
    if "pytest" in sys.modules:
        print(f"\n🧪 Test Profile: {profile}")
        print(f"   CI Environment: {is_ci_environment()}")
        print(f"   Local API Tests: {'Enabled' if get_test_config('run_local_api_tests') else 'Disabled'}")
        print(f"   Max Retries: {get_test_config('max_retries')}")
        print(f"   Timeout: {get_test_config('timeout')}s\n")
