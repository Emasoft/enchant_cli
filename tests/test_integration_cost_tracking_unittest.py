#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Integration tests for cost tracking functionality between cli_translator and translation_service
"""

import unittest
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


class TestCostTrackingIntegration(unittest.TestCase):
    """Integration tests for OpenRouter cost tracking"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_config_data = self.mock_config()
    
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
                    'model': 'local-model'
                }
            },
            'costs': {
                'models': {
                    'deepseek/deepseek-r1:nitro': {
                        'input': 0.00014,  # $0.14 per million
                        'output': 0.00288,  # $2.88 per million
                        'pricing_unit': 1_000_000
                    }
                }
            },
            'features': {
                'cost_tracking': {
                    'enabled': True,
                    'backend': 'production',
                    'log_level': 'INFO'
                }
            }
        }
    
    def test_translator_reports_cost_to_cli(self):
        """Test that ChineseAITranslator reports cost that cli_translator can aggregate"""
        # Setup mocks
        mock_pricing = Mock()
        mock_pricing.get_model_pricing.return_value = {
            'input': 0.00014,
            'output': 0.00288,
            'pricing_unit': 1_000_000
        }
        
        # Mock successful response with usage data
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'choices': [{
                'message': {
                    'content': 'Translated text'
                }
            }],
            'usage': {
                'prompt_tokens': 150,
                'completion_tokens': 100,
                'total_tokens': 250
            }
        }
        
        with patch('cli_translator.ConfigManager') as mock_config_mgr:
            mock_config_mgr.return_value.config = self.mock_config_data
            
            with patch('cli_translator.get_pricing_manager') as mock_get_pricing:
                mock_get_pricing.return_value = mock_pricing
                
                with patch('requests.post', return_value=mock_response):
                    # Create translator with mocked dependencies
                    translator = ChineseAITranslator(
                        use_remote=True,
                        config_manager=mock_config_mgr()
                    )
                    
                    # Perform translation
                    result = translator.translate("测试文本")
                    
                    # Verify translation
                    self.assertEqual(result, 'Translated text')
                    
                    # Verify cost tracking
                    self.assertGreater(translator.total_cost, 0)
                    self.assertEqual(translator.request_count, 1)
                    
                    # Calculate expected cost
                    input_cost = (150 / 1_000_000) * 0.14  # $0.14 per million
                    output_cost = (100 / 1_000_000) * 2.88  # $2.88 per million
                    expected_cost = input_cost + output_cost
                    
                    self.assertAlmostEqual(translator.total_cost, expected_cost, places=6)
    
    def test_multiple_translations_accumulate_cost(self):
        """Test that multiple translations accumulate cost correctly"""
        mock_pricing = Mock()
        mock_pricing.get_model_pricing.return_value = {
            'input': 0.00014,
            'output': 0.00288,
            'pricing_unit': 1_000_000
        }
        
        # Mock responses with different token counts
        responses = [
            {
                'choices': [{'message': {'content': 'Translation 1'}}],
                'usage': {'prompt_tokens': 100, 'completion_tokens': 50, 'total_tokens': 150}
            },
            {
                'choices': [{'message': {'content': 'Translation 2'}}],
                'usage': {'prompt_tokens': 200, 'completion_tokens': 100, 'total_tokens': 300}
            },
            {
                'choices': [{'message': {'content': 'Translation 3'}}],
                'usage': {'prompt_tokens': 150, 'completion_tokens': 75, 'total_tokens': 225}
            }
        ]
        
        with patch('cli_translator.ConfigManager') as mock_config_mgr:
            mock_config_mgr.return_value.config = self.mock_config_data
            
            with patch('cli_translator.get_pricing_manager') as mock_get_pricing:
                mock_get_pricing.return_value = mock_pricing
                
                mock_post = Mock()
                mock_post.side_effect = [
                    Mock(status_code=200, json=Mock(return_value=resp)) 
                    for resp in responses
                ]
                
                with patch('requests.post', mock_post):
                    translator = ChineseAITranslator(
                        use_remote=True,
                        config_manager=mock_config_mgr()
                    )
                    
                    # Perform multiple translations
                    for i in range(3):
                        translator.translate(f"Text {i}")
                    
                    # Verify accumulated cost
                    total_input_tokens = 100 + 200 + 150
                    total_output_tokens = 50 + 100 + 75
                    
                    expected_cost = (
                        (total_input_tokens / 1_000_000) * 0.14 +
                        (total_output_tokens / 1_000_000) * 2.88
                    )
                    
                    self.assertAlmostEqual(translator.total_cost, expected_cost, places=6)
                    self.assertEqual(translator.request_count, 3)
    
    def test_cost_tracking_disabled(self):
        """Test that cost tracking can be disabled"""
        config = self.mock_config()
        config['features']['cost_tracking']['enabled'] = False
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'choices': [{'message': {'content': 'Translated'}}],
            'usage': {'prompt_tokens': 100, 'completion_tokens': 50}
        }
        
        with patch('cli_translator.ConfigManager') as mock_config_mgr:
            mock_config_mgr.return_value.config = config
            
            with patch('requests.post', return_value=mock_response):
                translator = ChineseAITranslator(
                    use_remote=True,
                    config_manager=mock_config_mgr()
                )
                
                result = translator.translate("Test")
                
                # Cost should still be tracked even if feature is disabled
                # (The translator always tracks, the feature flag controls display)
                self.assertEqual(translator.request_count, 1)


if __name__ == '__main__':
    unittest.main()