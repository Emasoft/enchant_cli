#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Integration tests for cost tracking functionality between cli_translator and translation_service
"""

try:
    import pytest
except ImportError:
    pytest = None
import json
import os
import sys
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# We need to mock these before importing cli_translator
with patch('cli_translator.ConfigManager'):
    with patch('cli_translator.ICloudSync'):
        with patch('cli_translator.get_pricing_manager'):
            from cli_translator import ChineseAITranslator


class TestCostTrackingIntegration:
    """Integration tests for OpenRouter cost tracking"""
    
    def mock_config(self):
        """Mock configuration for testing - using exact production values"""
        return {
            'translation': {
                'service': 'remote',
                'temperature': 0.3,  # Config default, overridden by translator to 0.05
                'max_tokens': 4000,
                'max_retries': 7,
                'retry_wait_base': 1.0,
                'retry_wait_max': 60.0,
                'remote': {
                    'endpoint': 'https://openrouter.ai/api/v1/chat/completions',
                    'model': 'deepseek/deepseek-r1:nitro',
                    'timeout': 300,
                    'connection_timeout': 30
                },
                'local': {
                    'endpoint': 'http://localhost:1234/v1/chat/completions',
                    'model': 'qwen3-30b-a3b-mlx@8bit',
                    'timeout': 300,
                    'connection_timeout': 30
                }
            },
            'text_processing': {
                'max_chars_per_chunk': 11999,
                'split_method': 'paragraph',
                'default_encoding': 'utf-8'
            },
            'pricing': {
                'enabled': True
            }
        }
    
    @pytest.mark.integration
    def test_remote_cost_tracking_single_request(self):
        """Test cost tracking for a single remote API request"""
        # Create translator
        translator = ChineseAITranslator(
            use_remote=True,
            api_key="test_key"
        )
        
        # Mock API response with cost data
        with patch('requests.post') as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = {
                'choices': [{
                    'message': {
                        'content': 'Translated text'
                    }
                }],
                'usage': {
                    'prompt_tokens': 100,
                    'completion_tokens': 50,
                    'total_tokens': 150,
                    'cost': 0.0015
                }
            }
            mock_response.raise_for_status = Mock()
            mock_post.return_value = mock_response
            
            # Make translation request
            result = translator.translate("中文文本")
            
            # Verify cost tracking
            assert translator.total_cost == 0.0015
            assert translator.total_tokens == 150
            assert translator.total_prompt_tokens == 100
            assert translator.total_completion_tokens == 50
            assert translator.request_count == 1
            
            # Verify usage tracking was enabled
            call_args = mock_post.call_args
            assert call_args[1]['json']['usage'] == {'include': True}
    
    @pytest.mark.integration
    def test_remote_cost_tracking_multiple_requests(self):
        """Test cumulative cost tracking across multiple requests"""
        translator = ChineseAITranslator(
            use_remote=True,
            api_key="test_key"
        )
        
        # Mock multiple API responses
        responses = [
            {
                'choices': [{'message': {'content': 'Translation 1'}}],
                'usage': {
                    'prompt_tokens': 100,
                    'completion_tokens': 50,
                    'total_tokens': 150,
                    'cost': 0.0015
                }
            },
            {
                'choices': [{'message': {'content': 'Translation 2'}}],
                'usage': {
                    'prompt_tokens': 200,
                    'completion_tokens': 100,
                    'total_tokens': 300,
                    'cost': 0.003
                }
            },
            {
                'choices': [{'message': {'content': 'Translation 3'}}],
                'usage': {
                    'prompt_tokens': 150,
                    'completion_tokens': 75,
                    'total_tokens': 225,
                    'cost': 0.00225
                }
            }
        ]
        
        with patch('requests.post') as mock_post:
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
            
            # Verify cumulative tracking
            assert translator.total_cost == 0.00675  # Sum of all costs
            assert translator.total_tokens == 675    # Sum of all tokens
            assert translator.total_prompt_tokens == 450
            assert translator.total_completion_tokens == 225
            assert translator.request_count == 3
    
    @pytest.mark.integration
    def test_cost_summary_formatting(self):
        """Test cost summary formatting for display"""
        translator = ChineseAITranslator(
            use_remote=True,
            api_key="test_key"
        )
        
        # Set test values
        with translator._cost_lock:
            translator.total_cost = 0.12345
            translator.total_tokens = 50000
            translator.total_prompt_tokens = 30000
            translator.total_completion_tokens = 20000
            translator.request_count = 25
            translator.MODEL_NAME = "deepseek/deepseek-r1:nitro"
        
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
    
    @pytest.mark.integration
    def test_cost_tracking_with_missing_cost_field(self):
        """Test handling of responses without cost information"""
        translator = ChineseAITranslator(
            use_remote=True,
            api_key="test_key"
        )
        
        with patch('requests.post') as mock_post:
            # Response without cost field
            mock_response = Mock()
            mock_response.json.return_value = {
                'choices': [{'message': {'content': 'Translation'}}],
                'usage': {
                    'prompt_tokens': 100,
                    'completion_tokens': 50,
                    'total_tokens': 150
                    # No 'cost' field
                }
            }
            mock_response.raise_for_status = Mock()
            mock_post.return_value = mock_response
            
            # Should not raise error
            result = translator.translate("Text")
            
            # Cost should remain 0, but tokens should be tracked
            assert translator.total_cost == 0.0
            assert translator.total_tokens == 150
            assert translator.request_count == 1
    
    @pytest.mark.integration
    def test_cost_tracking_thread_safety(self):
        """Test thread-safe cost accumulation"""
        import threading
        import time
        
        translator = ChineseAITranslator(
            use_remote=True,
            api_key="test_key"
        )
        
        # Function to simulate concurrent API calls
        def make_request(request_id):
            with patch('requests.post') as mock_post:
                mock_response = Mock()
                mock_response.json.return_value = {
                    'choices': [{'message': {'content': f'Translation {request_id}'}}],
                    'usage': {
                        'prompt_tokens': 100,
                        'completion_tokens': 50,
                        'total_tokens': 150,
                        'cost': 0.001
                    }
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
        
        # Verify thread-safe accumulation
        assert translator.total_cost == pytest.approx(0.01, rel=1e-9)  # 10 * 0.001
        assert translator.total_tokens == 1500  # 10 * 150
        assert translator.request_count == 10
    
    @pytest.mark.integration
    def test_cost_reset_functionality(self):
        """Test resetting cost tracking"""
        translator = ChineseAITranslator(
            use_remote=True,
            api_key="test_key"
        )
        
        # Set some values
        with translator._cost_lock:
            translator.total_cost = 1.0
            translator.total_tokens = 10000
            translator.total_prompt_tokens = 6000
            translator.total_completion_tokens = 4000
            translator.request_count = 50
        
        # Reset
        translator.reset_cost_tracking()
        
        # Verify all values reset
        assert translator.total_cost == 0.0
        assert translator.total_tokens == 0
        assert translator.total_prompt_tokens == 0
        assert translator.total_completion_tokens == 0
        assert translator.request_count == 0
    
    @pytest.mark.integration
    def test_local_api_no_cost_tracking(self):
        """Test that local API doesn't track costs"""
        translator = ChineseAITranslator(
            use_remote=False,
            pricing_manager=Mock()
        )
        
        with patch('requests.post') as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = {
                'choices': [{'message': {'content': 'Translation'}}],
                'usage': {
                    'prompt_tokens': 100,
                    'completion_tokens': 50,
                    'total_tokens': 150
                }
            }
            mock_response.raise_for_status = Mock()
            mock_post.return_value = mock_response
            
            result = translator.translate("Text")
            
            # No cost tracking for local API
            assert translator.total_cost == 0.0
            assert translator.request_count == 0
            
            # Verify usage was NOT requested
            call_args = mock_post.call_args
            assert 'usage' not in call_args[1]['json']
    
    @pytest.mark.integration
    def test_cost_summary_edge_cases(self):
        """Test cost summary with edge cases"""
        translator = ChineseAITranslator(
            use_remote=True,
            api_key="test_key"
        )
        
        # Test with zero requests
        summary = translator.format_cost_summary()
        assert "Total Requests: 0" in summary
        assert "Total Cost: $0.000000" in summary
        
        # Test with very small cost
        with translator._cost_lock:
            translator.total_cost = 0.000001
            translator.request_count = 1
        
        summary = translator.format_cost_summary()
        assert "$0.000001" in summary
    
    @pytest.mark.integration
    @pytest.mark.slow
    def test_cost_tracking_stress_test(self):
        """Stress test cost tracking with many concurrent requests"""
        translator = ChineseAITranslator(
            use_remote=True,
            api_key="test_key"
        )
        
        num_requests = 100
        cost_per_request = 0.001
        
        def make_concurrent_request(i):
            with patch('requests.post') as mock_post:
                mock_response = Mock()
                mock_response.json.return_value = {
                    'choices': [{'message': {'content': f'Translation {i}'}}],
                    'usage': {
                        'prompt_tokens': 10,
                        'completion_tokens': 5,
                        'total_tokens': 15,
                        'cost': cost_per_request
                    }
                }
                mock_response.raise_for_status = Mock()
                mock_post.return_value = mock_response
                
                translator.translate(f"Text {i}")
        
        # Use thread pool for concurrent requests
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(make_concurrent_request, i) 
                      for i in range(num_requests)]
            concurrent.futures.wait(futures)
        
        # Verify accurate tracking
        assert translator.total_cost == pytest.approx(
            num_requests * cost_per_request, rel=1e-9
        )
        assert translator.request_count == num_requests
        assert translator.total_tokens == num_requests * 15


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=translation_service,cli_translator"])