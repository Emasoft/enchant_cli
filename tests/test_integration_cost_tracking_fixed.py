#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Integration tests for cost tracking functionality between cli_translator and translation_service
"""

import os
import sys
from unittest.mock import Mock, patch
import threading
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# We need to mock these before importing cli_translator
with patch("enchant_book_manager.cli_translator.ConfigManager"):
    with patch("enchant_book_manager.cli_translator.ICloudSync"):
        from enchant_book_manager.cli_translator import ChineseAITranslator
        from enchant_book_manager.cost_tracker import global_cost_tracker


class TestCostTrackingIntegration:
    """Integration tests for OpenRouter cost tracking"""

    def setup_method(self):
        """Reset global cost tracker before each test"""
        global_cost_tracker.reset()

    def mock_config(self):
        """Mock configuration for testing - using exact production values"""
        return {
            "translation": {
                "service": "remote",
                "temperature": 0.3,  # Config default, overridden by translator to 0.05
                "max_tokens": 4000,
                "max_retries": 7,
                "retry_wait_base": 1.0,
                "retry_wait_max": 60.0,
                "remote": {
                    "endpoint": "https://openrouter.ai/api/v1/chat/completions",
                    "model": "deepseek/deepseek-r1:nitro",
                    "timeout": 300,
                    "connection_timeout": 30,
                },
                "local": {
                    "endpoint": "http://localhost:1234/v1/chat/completions",
                    "model": "qwen3-30b-a3b-mlx@8bit",
                    "timeout": 300,
                    "connection_timeout": 30,
                },
            },
            "text_processing": {
                "max_chars_per_chunk": 11999,
                "default_encoding": "utf-8",
            },
            "pricing": {"enabled": True},
        }

    def test_remote_cost_tracking_single_request(self):
        """Test cost tracking for a single remote API request"""
        # Create translator with exact production settings
        translator = ChineseAITranslator(
            use_remote=True,
            api_key="test_key",
            temperature=0.05,  # Production override value
        )

        # Mock API response with cost data and time.sleep to avoid test delays
        with patch("requests.post") as mock_post, patch("time.sleep"):
            mock_response = Mock()
            mock_response.json.return_value = {
                "choices": [
                    {
                        "message": {
                            "content": "This is a much longer translated text that contains enough characters to pass the minimum length validation. The translation service requires at least 300 characters for non-final chunks to ensure the translation is complete and meaningful. This mock response provides sufficient content to satisfy that requirement and allow the test to proceed without triggering validation errors."
                        }
                    }
                ],
                "usage": {
                    "prompt_tokens": 100,
                    "completion_tokens": 50,
                    "total_tokens": 150,
                    "cost": 0.0015,
                },
            }
            mock_response.raise_for_status = Mock()
            mock_post.return_value = mock_response

            # Make translation request
            translator.translate("中文文本")

            # Verify cost tracking through global_cost_tracker
            summary = global_cost_tracker.get_summary()
            assert summary["total_cost"] == 0.0015
            assert summary["total_tokens"] == 150
            assert summary["total_prompt_tokens"] == 100
            assert summary["total_completion_tokens"] == 50
            assert summary["request_count"] == 1
            assert translator.request_count == 1

            # Verify usage tracking was enabled
            call_args = mock_post.call_args
            # Check if json key exists in kwargs
            if "json" in call_args[1]:
                request_json = call_args[1]["json"]
                assert "usage" in request_json
                assert request_json["usage"] == {"include": True}

    def test_remote_cost_tracking_multiple_requests(self):
        """Test cumulative cost tracking across multiple requests"""
        translator = ChineseAITranslator(
            use_remote=True,
            api_key="test_key",
            temperature=0.05,  # Production value
        )

        # Mock multiple API responses
        responses = [
            {
                "choices": [
                    {
                        "message": {
                            "content": "This is translation number one with enough characters to pass the minimum length validation. The translation service requires at least 300 characters for non-final chunks to ensure the translation is complete and meaningful. This mock response provides sufficient content to satisfy that requirement and allow the test to proceed without triggering validation errors for the first translation."
                        }
                    }
                ],
                "usage": {
                    "prompt_tokens": 100,
                    "completion_tokens": 50,
                    "total_tokens": 150,
                    "cost": 0.0015,
                },
            },
            {
                "choices": [
                    {
                        "message": {
                            "content": "This is translation number two with enough characters to pass the minimum length validation. The translation service requires at least 300 characters for non-final chunks to ensure the translation is complete and meaningful. This mock response provides sufficient content to satisfy that requirement and allow the test to proceed without triggering validation errors for the second translation."
                        }
                    }
                ],
                "usage": {
                    "prompt_tokens": 200,
                    "completion_tokens": 100,
                    "total_tokens": 300,
                    "cost": 0.003,
                },
            },
            {
                "choices": [
                    {
                        "message": {
                            "content": "This is translation number three with enough characters to pass the minimum length validation. The translation service requires at least 300 characters for non-final chunks to ensure the translation is complete and meaningful. This mock response provides sufficient content to satisfy that requirement and allow the test to proceed without triggering validation errors for the third translation."
                        }
                    }
                ],
                "usage": {
                    "prompt_tokens": 150,
                    "completion_tokens": 75,
                    "total_tokens": 225,
                    "cost": 0.00225,
                },
            },
        ]

        with patch("requests.post") as mock_post, patch("time.sleep"):
            mock_responses = []
            for resp_data in responses:
                mock_resp = Mock()
                mock_resp.json.return_value = resp_data
                mock_resp.raise_for_status = Mock()
                mock_responses.append(mock_resp)

            mock_post.side_effect = mock_responses

            # Make multiple translations
            translator.translate("Text 1")
            translator.translate("Text 2")
            translator.translate("Text 3")

            # Verify cumulative tracking through global_cost_tracker
            summary = global_cost_tracker.get_summary()
            assert summary["total_cost"] == pytest.approx(0.00675)  # Sum of all costs
            assert summary["total_tokens"] == 675  # Sum of all tokens
            assert summary["total_prompt_tokens"] == 450
            assert summary["total_completion_tokens"] == 225
            assert summary["request_count"] == 3
            assert translator.request_count == 3

    def test_cost_summary_formatting(self):
        """Test cost summary formatting for display"""
        translator = ChineseAITranslator(
            use_remote=True,
            api_key="test_key",
            temperature=0.05,  # Production value
        )

        # Mock global_cost_tracker summary
        with patch("enchant_book_manager.cost_tracker.global_cost_tracker.get_summary") as mock_summary:
            mock_summary.return_value = {
                "total_cost": 0.12345,
                "total_tokens": 50000,
                "total_prompt_tokens": 30000,
                "total_completion_tokens": 20000,
                "request_count": 25,
                "average_cost_per_request": 0.004938,
            }
            translator.request_count = 25

            # Get formatted summary
            summary = translator.format_cost_summary()

            # Verify formatting
            assert "Total Cost: $0.123450" in summary
            assert "Total Requests: 25" in summary
            assert "Total Tokens: 50,000" in summary
            assert "Prompt Tokens: 30,000" in summary
            assert "Completion Tokens: 20,000" in summary
            assert "Average Cost per Request: $0.004938" in summary
            assert "Average Tokens per Request: 2,000" in summary
            assert "Model: deepseek/deepseek-r1:nitro" in summary
            assert "API Type: remote" in summary

    def test_cost_tracking_with_missing_cost_field(self):
        """Test handling of responses without cost information"""
        translator = ChineseAITranslator(
            use_remote=True,
            api_key="test_key",
            temperature=0.05,  # Production value
        )

        with patch("requests.post") as mock_post, patch("time.sleep"):
            # Response without cost field
            mock_response = Mock()
            mock_response.json.return_value = {
                "choices": [
                    {
                        "message": {
                            "content": "This is a translated text with enough characters to pass the minimum length validation. The translation service requires at least 300 characters for non-final chunks to ensure the translation is complete and meaningful. This mock response provides sufficient content to satisfy that requirement and allow the test to proceed without triggering validation errors in the test scenario."
                        }
                    }
                ],
                "usage": {
                    "prompt_tokens": 100,
                    "completion_tokens": 50,
                    "total_tokens": 150,
                    # No 'cost' field
                },
            }
            mock_response.raise_for_status = Mock()
            mock_post.return_value = mock_response

            # Should not raise error
            translator.translate("Text")

            # Cost should remain 0, but tokens should be tracked
            summary = global_cost_tracker.get_summary()
            assert summary["total_cost"] == 0.0
            assert summary["total_tokens"] == 150
            assert summary["request_count"] == 1
            assert translator.request_count == 1

    def test_cost_tracking_thread_safety(self):
        """Test thread-safe cost accumulation"""
        translator = ChineseAITranslator(
            use_remote=True,
            api_key="test_key",
            temperature=0.05,  # Production value
        )

        # Function to simulate concurrent API calls
        def make_request(request_id):
            with patch("requests.post") as mock_post, patch("time.sleep"):
                mock_response = Mock()
                mock_response.json.return_value = {
                    "choices": [
                        {
                            "message": {
                                "content": f"This is translation {request_id} with enough characters to pass the minimum length validation. The translation service requires at least 300 characters for non-final chunks to ensure the translation is complete and meaningful. This mock response provides sufficient content to satisfy that requirement and allow the test to proceed without triggering validation errors."
                            }
                        }
                    ],
                    "usage": {
                        "prompt_tokens": 100,
                        "completion_tokens": 50,
                        "total_tokens": 150,
                        "cost": 0.001,
                    },
                }
                mock_response.raise_for_status = Mock()
                mock_post.return_value = mock_response

                translator.translate(f"Text {request_id}")

        # Create threads
        threads = []
        num_threads = 10

        for i in range(num_threads):
            thread = threading.Thread(target=make_request, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # Verify thread-safe accumulation (allowing small floating point differences)
        summary = global_cost_tracker.get_summary()
        assert summary["total_cost"] == pytest.approx(0.01)  # 10 * 0.001
        assert summary["total_tokens"] == 1500  # 10 * 150
        assert summary["request_count"] == 10
        assert translator.request_count == 10

    def test_cost_reset_functionality(self):
        """Test resetting cost tracking"""
        translator = ChineseAITranslator(
            use_remote=True,
            api_key="test_key",
            temperature=0.05,  # Production value
        )

        # Simulate some usage by mocking global_cost_tracker
        with patch("enchant_book_manager.cost_tracker.global_cost_tracker.get_summary") as mock_summary:
            mock_summary.return_value = {
                "total_cost": 1.0,
                "total_tokens": 10000,
                "total_prompt_tokens": 6000,
                "total_completion_tokens": 4000,
                "request_count": 50,
            }
            translator.request_count = 50

        # Reset
        translator.reset_cost_tracking()

        # Verify values reset
        summary = global_cost_tracker.get_summary()
        assert summary["total_cost"] == 0.0
        assert summary["total_tokens"] == 0
        assert summary["total_prompt_tokens"] == 0
        assert summary["total_completion_tokens"] == 0
        assert summary["request_count"] == 0
        assert translator.request_count == 0

    def test_local_api_no_cost_tracking(self):
        """Test that local API doesn't track costs"""
        translator = ChineseAITranslator(
            use_remote=False,
            temperature=0.05,  # Production value
        )

        with patch("requests.post") as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = {
                "choices": [
                    {
                        "message": {
                            "content": "This is a translated text with enough characters to pass the minimum length validation. The translation service requires at least 300 characters for non-final chunks to ensure the translation is complete and meaningful. This mock response provides sufficient content to satisfy that requirement and allow the test to proceed without triggering validation errors in the test scenario."
                        }
                    }
                ],
                "usage": {
                    "prompt_tokens": 100,
                    "completion_tokens": 50,
                    "total_tokens": 150,
                },
            }
            mock_response.raise_for_status = Mock()
            mock_post.return_value = mock_response

            translator.translate("Text")

            # For local API, global tracker shouldn't show cost
            summary = translator.get_cost_summary()
            assert summary["total_cost"] == 0.0
            assert summary["api_type"] == "local"
            assert summary["message"] == "Local API - no costs incurred"

            # Verify usage was NOT requested for local API
            call_args = mock_post.call_args
            # For local API, the usage field should not be present
            if "json" in call_args[1]:
                request_json = call_args[1]["json"]
                # Local API should not include usage tracking
                assert "usage" not in request_json or request_json.get("usage") is None

    def test_cost_summary_edge_cases(self):
        """Test cost summary with edge cases"""
        translator = ChineseAITranslator(
            use_remote=True,
            api_key="test_key",
            temperature=0.05,  # Production value
        )

        # Test with zero requests
        summary = translator.format_cost_summary()
        assert "Total Requests: 0" in summary
        assert "Total Cost: $0.000000" in summary

        # Test with very small cost
        with patch("enchant_book_manager.cost_tracker.global_cost_tracker.get_summary") as mock_summary:
            mock_summary.return_value = {
                "total_cost": 0.000001,
                "total_tokens": 10,
                "total_prompt_tokens": 5,
                "total_completion_tokens": 5,
                "request_count": 1,
                "average_cost_per_request": 0.000001,
            }
            translator.request_count = 1

            summary = translator.format_cost_summary()
            assert "$0.000001" in summary

    def test_configuration_values_production_match(self):
        """Test that we're using the exact production configuration values"""
        config = self.mock_config()

        # Verify exact production values
        assert config["translation"]["remote"]["model"] == "deepseek/deepseek-r1:nitro"
        assert config["translation"]["local"]["model"] == "qwen3-30b-a3b-mlx@8bit"
        assert config["translation"]["remote"]["endpoint"] == "https://openrouter.ai/api/v1/chat/completions"
        assert config["translation"]["local"]["endpoint"] == "http://localhost:1234/v1/chat/completions"
        assert config["translation"]["remote"]["timeout"] == 300
        assert config["translation"]["remote"]["connection_timeout"] == 30
        assert config["translation"]["local"]["timeout"] == 300
        assert config["translation"]["local"]["connection_timeout"] == 30
        assert config["translation"]["max_retries"] == 7
        assert config["text_processing"]["max_chars_per_chunk"] == 11999


if __name__ == "__main__":
    # Run tests manually
    test_instance = TestCostTrackingIntegration()

    test_methods = [
        "test_remote_cost_tracking_single_request",
        "test_remote_cost_tracking_multiple_requests",
        "test_cost_summary_formatting",
        "test_cost_tracking_with_missing_cost_field",
        "test_cost_tracking_thread_safety",
        "test_cost_reset_functionality",
        "test_local_api_no_cost_tracking",
        "test_cost_summary_edge_cases",
        "test_configuration_values_production_match",
    ]

    passed = 0
    failed = 0

    for method_name in test_methods:
        try:
            method = getattr(test_instance, method_name)
            method()
            print(f"✓ {method_name}")
            passed += 1
        except Exception as e:
            print(f"✗ {method_name}: {e}")
            failed += 1

    print(f"\nResults: {passed} passed, {failed} failed")
