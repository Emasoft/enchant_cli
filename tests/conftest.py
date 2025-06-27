#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pytest configuration and shared fixtures for all tests
"""

import pytest
import sys
import os
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch

# Add src directory to path so we can import our modules
src_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
sys.path.insert(0, src_dir)

# Import test configuration
from test_config import TEST_CONFIG, should_skip_test


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files"""
    temp_path = tempfile.mkdtemp()
    yield Path(temp_path)
    shutil.rmtree(temp_path)


@pytest.fixture
def mock_logger():
    """Create a mock logger for testing"""
    logger = Mock()
    logger.info = Mock()
    logger.debug = Mock()
    logger.warning = Mock()
    logger.error = Mock()
    logger.exception = Mock()
    return logger


@pytest.fixture
def sample_chinese_text():
    """Sample Chinese text for testing"""
    return """第一章 开始

    这是一段中文文本。包含各种标点符号！！！还有问号？？？

    "对话内容，" 他说道。

    第二章 继续

    更多内容。。。。。。
    """


@pytest.fixture
def sample_english_text():
    """Sample English text for testing"""
    return """Chapter 1: The Beginning

    This is some English text. With various punctuation!!!
    And questions???

    "Dialogue content," he said.

    Chapter 2: Continuing

    More content......
    """


@pytest.fixture
def sample_html():
    """Sample HTML for testing"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test Page</title>
        <style>
            body { font-family: Arial; }
        </style>
        <script>
            console.log('test');
        </script>
    </head>
    <body>
        <!-- This is a comment -->
        <h1>Title</h1>
        <p>This is a paragraph with <code>inline code</code> and
           <a href="#">a link</a>.</p>
        <pre>
        This is preformatted text
        with multiple lines
        </pre>
        <div>
            <span>Nested &amp; escaped &lt;content&gt;</span>
        </div>
    </body>
    </html>
    """


@pytest.fixture
def mock_api_response():
    """Mock API response for translation tests"""
    return {
        "choices": [{"message": {"content": "This is the translated English text."}}],
        "usage": {
            "prompt_tokens": 150,
            "completion_tokens": 75,
            "total_tokens": 225,
            "cost": 0.00225,
        },
    }


@pytest.fixture(autouse=True)
def reset_environment():
    """Reset environment variables before each test"""
    env_backup = os.environ.copy()
    yield
    os.environ.clear()
    os.environ.update(env_backup)


@pytest.fixture
def mock_requests_post():
    """Mock requests.post for API tests"""
    with patch("requests.post") as mock_post:
        yield mock_post


# Configure pytest options
def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line("markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')")
    config.addinivalue_line("markers", "integration: marks tests as integration tests")


# Coverage configuration
def pytest_collection_modifyitems(config, items):
    """Add markers to tests based on their names and skip based on profile"""
    for item in items:
        # Mark integration tests
        if "integration" in item.nodeid:
            item.add_marker(pytest.mark.integration)
            if should_skip_test("integration"):
                item.add_marker(pytest.mark.skip(reason="Skipping integration tests in this profile"))

        # Mark slow tests
        if "slow" in item.nodeid or "stress" in item.nodeid:
            item.add_marker(pytest.mark.slow)
            if should_skip_test("heavy"):
                item.add_marker(pytest.mark.skip(reason="Skipping heavy tests in this profile"))

        # Skip remote tests if configured
        if "remote" in item.nodeid and should_skip_test("remote"):
            item.add_marker(pytest.mark.skip(reason="Skipping remote tests in this profile"))

        # Skip local tests if configured
        if "local" in item.nodeid and should_skip_test("local"):
            item.add_marker(pytest.mark.skip(reason="Skipping local tests in this profile"))
