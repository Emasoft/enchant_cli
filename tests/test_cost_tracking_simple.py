#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simple cost tracking integration test
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import Mock, patch
from translation_service import ChineseAITranslator
from cost_tracker import global_cost_tracker


def test_remote_cost_tracking():
    """Test cost tracking for remote API"""
    # Reset global tracker before test
    global_cost_tracker.reset()
    print("\nTesting remote cost tracking...")
    
    # Create translator
    translator = ChineseAITranslator(
        use_remote=True,
        api_key="test_key",
        double_pass=False  # Disable double translation for testing
    )
    
    # Mock API response with cost data
    with patch('requests.post') as mock_post, \
         patch('time.sleep', return_value=None):
        mock_response = Mock()
        mock_response.json.return_value = {
            'choices': [{
                'message': {
                    'content': 'This is a much longer translated text in English. ' * 10  # Make it over 300 chars
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
        
        # Verify cost tracking through global tracker
        summary = global_cost_tracker.get_summary()
        assert summary['total_cost'] == 0.0015
        assert summary['total_tokens'] == 150
        assert summary['total_prompt_tokens'] == 100
        assert summary['total_completion_tokens'] == 50
        assert summary['request_count'] == 1
        
        # Verify usage tracking was enabled
        call_args = mock_post.call_args
        assert call_args[1]['json']['usage'] == {'include': True}
        
        print("✓ Single request cost tracking works correctly")
        
    # Test multiple requests
    print("\nTesting cumulative cost tracking...")
    
    # Make 3 more requests
    for i in range(3):
        with patch('requests.post') as mock_post, \
             patch('time.sleep', return_value=None):
            mock_response = Mock()
            mock_response.json.return_value = {
                'choices': [{'message': {'content': f'This is translation number {i}. ' * 20}}],
                'usage': {
                    'prompt_tokens': 200,
                    'completion_tokens': 100,
                    'total_tokens': 300,
                    'cost': 0.003
                }
            }
            mock_response.raise_for_status = Mock()
            mock_post.return_value = mock_response
            
            translator.translate(f"Text {i}")
    
    # Verify cumulative tracking
    summary = global_cost_tracker.get_summary()
    assert summary['total_cost'] == 0.0015 + (0.003 * 3)  # 0.0105
    assert summary['total_tokens'] == 150 + (300 * 3)     # 1050
    assert summary['request_count'] == 4
    
    print("✓ Cumulative cost tracking works correctly")
    
    # Test cost summary
    print("\nTesting cost summary...")
    summary = translator.get_cost_summary()
    assert summary['total_cost'] == 0.0105
    assert summary['total_tokens'] == 1050
    assert summary['request_count'] == 4
    assert summary['average_cost_per_request'] == 0.0105 / 4
    
    print("✓ Cost summary calculation works correctly")
    
    # Test reset
    print("\nTesting cost reset...")
    translator.reset_cost_tracking()
    summary = global_cost_tracker.get_summary()
    assert summary['total_cost'] == 0.0
    assert summary['request_count'] == 0
    
    print("✓ Cost reset works correctly")


def test_local_api_no_cost():
    """Test that local API doesn't track costs"""
    # Reset global tracker before test
    global_cost_tracker.reset()
    print("\nTesting local API (no cost tracking)...")
    
    translator = ChineseAITranslator(
        use_remote=False
    )
    
    with patch('requests.post') as mock_post, \
         patch('time.sleep', return_value=None):
        mock_response = Mock()
        mock_response.json.return_value = {
            'choices': [{'message': {'content': 'This is a long translation for local API testing. ' * 10}}],
            'usage': {
                'prompt_tokens': 100,
                'completion_tokens': 50,
                'total_tokens': 150
            }
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        result = translator.translate("Text")
        
        # For local API, cost should remain 0
        summary = translator.get_cost_summary()
        assert summary['total_cost'] == 0.0
        
        # Verify usage was NOT requested
        call_args = mock_post.call_args
        assert 'usage' not in call_args[1]['json']
        
        print("✓ Local API correctly doesn't track costs")


if __name__ == "__main__":
    print("Running cost tracking integration tests...")
    
    test_remote_cost_tracking()
    test_local_api_no_cost()
    
    print("\n✅ All cost tracking tests passed!")
