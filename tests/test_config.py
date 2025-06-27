#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Test configuration module that adapts to different environments."""

import os
import sys
from typing import Dict, Any


def get_test_profile() -> str:
    """Get the current test profile (local, remote, or full)."""
    return os.environ.get("TEST_PROFILE", "local")


def is_running_in_ci() -> bool:
    """Check if tests are running in CI environment."""
    return bool(os.environ.get("CI") or os.environ.get("GITHUB_ACTIONS"))


def is_running_in_docker() -> bool:
    """Check if tests are running inside Docker."""
    return os.path.exists("/.dockerenv") or os.environ.get("TEST_PROFILE") is not None


def get_test_config() -> Dict[str, Any]:
    """Get test configuration based on the current environment."""
    profile = get_test_profile()
    is_ci = is_running_in_ci()

    # Base configuration
    config = {
        "profile": profile,
        "is_ci": is_ci,
        "is_docker": is_running_in_docker(),
        "skip_remote_tests": os.environ.get("SKIP_REMOTE_TESTS", "false").lower() == "true",
        "skip_local_tests": os.environ.get("SKIP_LOCAL_MODE_TESTS", "false").lower() == "true",
    }

    # Profile-specific settings
    if profile == "remote" or is_ci:
        config.update(
            {
                "max_retries": 2,
                "timeout": 30,  # Increased from 5 to 30 seconds for API calls
                "skip_heavy_tests": True,
                "skip_integration_tests": False,
                "verbose": False,
            }
        )
    elif profile == "local":
        config.update(
            {
                "max_retries": 10,
                "timeout": 60,
                "skip_heavy_tests": False,
                "skip_integration_tests": False,
                "verbose": True,
            }
        )
    else:  # full profile
        config.update(
            {
                "max_retries": 5,
                "timeout": 300,
                "skip_heavy_tests": False,
                "skip_integration_tests": False,
                "verbose": True,
            }
        )

    return config


# Global test configuration
TEST_CONFIG = get_test_config()


def should_skip_test(test_type: str) -> bool:
    """Check if a test should be skipped based on configuration."""
    if test_type == "remote" and TEST_CONFIG["skip_remote_tests"]:
        return True
    if test_type == "local" and TEST_CONFIG["skip_local_tests"]:
        return True
    if test_type == "heavy" and TEST_CONFIG.get("skip_heavy_tests", False):
        return True
    if test_type == "integration" and TEST_CONFIG.get("skip_integration_tests", False):
        return True
    return False


def get_retry_count() -> int:
    """Get the number of retries for the current profile."""
    return TEST_CONFIG["max_retries"]


def get_timeout() -> int:
    """Get the timeout value for the current profile."""
    return TEST_CONFIG["timeout"]
