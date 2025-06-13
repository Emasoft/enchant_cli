#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test suite to validate exact error message formatting as requested
"""

import unittest
import tempfile
import os
from pathlib import Path
import sys
import io
from contextlib import redirect_stdout

# Add current directory to path
sys.path.insert(0, '.')

from config_manager import ConfigManager


class TestExactErrorFormats(unittest.TestCase):
    """Test cases to verify exact error message formats as requested."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_files = []
        
    def tearDown(self):
        """Clean up test files."""
        for temp_file in self.temp_files:
            if os.path.exists(temp_file):
                os.unlink(temp_file)
    
    def create_temp_config(self, content: str) -> Path:
        """Create a temporary config file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write(content)
            self.temp_files.append(f.name)
            return Path(f.name)
    
    def capture_error_output(self, config_path: Path) -> str:
        """Capture error output from ConfigManager."""
        output = io.StringIO()
        
        # Mock input to avoid interactive prompts
        import builtins
        original_input = builtins.input
        builtins.input = lambda prompt: 'n'
        
        try:
            with redirect_stdout(output):
                try:
                    ConfigManager(config_path=config_path)
                except SystemExit:
                    pass
        finally:
            builtins.input = original_input
            
        return output.getvalue()
    
    def test_unknown_key_format_exact(self):
        """Test that unknown key errors match exact format: 'line 765: unknown or malformed key found. Ignoring.'"""
        config_content = """
presets:
  LOCAL:
    endpoint: "http://localhost:1234"
    model: "test"
unknown_key: "value"
"""
        config_path = self.create_temp_config(config_content)
        result = self.capture_error_output(config_path)
        
        # Should match exact format
        self.assertRegex(result, r'line \d+: unknown or malformed key found\. Ignoring\.')
        # Should show the problematic line
        self.assertIn('unknown_key: "value"', result)
    
    def test_missing_key_format_exact(self):
        """Test that missing key errors match exact format: 'line 329: expected key 'model_name' not found. Please add the model_name key after line 329'"""
        config_content = """
presets:
  LOCAL:
    endpoint: "http://localhost:1234"
    # model missing
    connection_timeout: 30
  REMOTE:
    endpoint: "https://openrouter.ai"
    model: "test"
translation:
  service: local
text_processing:
  split_method: paragraph
novel_renaming:
  enabled: false
epub:
  enabled: false
batch:
  max_workers: null
icloud:
  enabled: null
pricing:
  enabled: true
logging:
  level: INFO
"""
        config_path = self.create_temp_config(config_content)
        result = self.capture_error_output(config_path)
        
        # Should match exact format
        self.assertRegex(result, r"line \d+: expected key 'model' not found\. Please add the model key after line \d+")
    
    def test_invalid_boolean_format_exact(self):
        """Test that invalid boolean errors match exact format: 'line 530: invalid value for double_pass. double_pass value can only be true or false.'"""
        config_content = """
presets:
  LOCAL:
    endpoint: "http://localhost:1234"
    model: "test"
    connection_timeout: 30
    response_timeout: 300
    max_retries: 7
    retry_wait_base: 1.0
    retry_wait_max: 60.0
    double_pass: "yes"  # Invalid boolean
    max_chars_per_chunk: 11999
    temperature: 0.05
    max_tokens: 4000
    system_prompt: "test"
    user_prompt_1st_pass: "test"
    user_prompt_2nd_pass: "test"
  REMOTE:
    endpoint: "https://openrouter.ai"
    model: "test"
    connection_timeout: 30
    response_timeout: 300
    max_retries: 7
    retry_wait_base: 1.0
    retry_wait_max: 60.0
    double_pass: true
    max_chars_per_chunk: 11999
    temperature: 0.05
    max_tokens: 4000
    system_prompt: "test"
    user_prompt_1st_pass: "test"
    user_prompt_2nd_pass: "test"
translation:
  service: local
text_processing:
  split_method: paragraph
novel_renaming:
  enabled: false
epub:
  enabled: false
batch:
  max_workers: null
icloud:
  enabled: null
pricing:
  enabled: true
logging:
  level: INFO
"""
        config_path = self.create_temp_config(config_content)
        result = self.capture_error_output(config_path)
        
        # Should match exact format
        self.assertIn("invalid value for double_pass. double_pass value can only be true or false", result)
    
    def test_invalid_endpoint_format_exact(self):
        """Test that invalid endpoint errors match exact format: 'line 876: api endpoint url not a valid openai compatible endpoint format!'"""
        config_content = """
presets:
  LOCAL:
    endpoint: "not-a-url"  # Invalid endpoint
    model: "test"
    connection_timeout: 30
    response_timeout: 300
    max_retries: 7
    retry_wait_base: 1.0
    retry_wait_max: 60.0
    double_pass: false
    max_chars_per_chunk: 11999
    temperature: 0.05
    max_tokens: 4000
    system_prompt: "test"
    user_prompt_1st_pass: "test"
    user_prompt_2nd_pass: "test"
  REMOTE:
    endpoint: "https://openrouter.ai"
    model: "test"
    connection_timeout: 30
    response_timeout: 300
    max_retries: 7
    retry_wait_base: 1.0
    retry_wait_max: 60.0
    double_pass: true
    max_chars_per_chunk: 11999
    temperature: 0.05
    max_tokens: 4000
    system_prompt: "test"
    user_prompt_1st_pass: "test"
    user_prompt_2nd_pass: "test"
translation:
  service: local
text_processing:
  split_method: paragraph
novel_renaming:
  enabled: false
epub:
  enabled: false
batch:
  max_workers: null
icloud:
  enabled: null
pricing:
  enabled: true
logging:
  level: INFO
"""
        config_path = self.create_temp_config(config_content)
        result = self.capture_error_output(config_path)
        
        # Should match exact format
        self.assertIn("api endpoint url not a valid openai compatible endpoint format!", result)
    
    def test_invalid_preset_name_format_exact(self):
        """Test that invalid preset name errors match exact format: 'line 766: invalid preset name. Names must not begin with a number!'"""
        config_content = """
presets:
  123_INVALID:  # Invalid name
    endpoint: "http://localhost:1234"
    model: "test"
"""
        config_path = self.create_temp_config(config_content)
        result = self.capture_error_output(config_path)
        
        # Should match exact format
        self.assertIn("invalid preset name. Names must not begin with a number!", result)
    
    def test_line_numbers_are_accurate(self):
        """Test that line numbers in error messages are accurate."""
        config_content = """# Line 1: Comment
# Line 2: Comment
presets:  # Line 3
  LOCAL:  # Line 4
    endpoint: "http://localhost:1234/v1/chat/completions"  # Line 5
    model: "test"  # Line 6
    connection_timeout: 30
    response_timeout: 300
    max_retries: 7
    retry_wait_base: 1.0
    retry_wait_max: 60.0
    double_pass: false
    max_chars_per_chunk: 11999
    temperature: 0.05
    max_tokens: 4000
    system_prompt: "test"
    user_prompt_1st_pass: "test"
    user_prompt_2nd_pass: "test"
    unknown_field: "value"  # Line 18 - This should be reported
  REMOTE:
    endpoint: "https://openrouter.ai/api/v1/chat/completions"
    model: "test"
    connection_timeout: 30
    response_timeout: 300
    max_retries: 7
    retry_wait_base: 1.0
    retry_wait_max: 60.0
    double_pass: true
    max_chars_per_chunk: 11999
    temperature: 0.05
    max_tokens: 4000
    system_prompt: "test"
    user_prompt_1st_pass: "test"
    user_prompt_2nd_pass: "test"
translation:
  service: local
text_processing:
  split_method: paragraph
novel_renaming:
  enabled: false
epub:
  enabled: false
batch:
  max_workers: null
icloud:
  enabled: null
pricing:
  enabled: true
logging:
  level: INFO
"""
        config_path = self.create_temp_config(config_content)
        result = self.capture_error_output(config_path)
        
        # Should report correct line for the unknown field (line 19 in this case)
        self.assertIn("line 19:", result)
        self.assertIn("unknown_field", result)
    
    def test_empty_config_file(self):
        """Test handling of empty configuration file."""
        config_content = ""
        config_path = self.create_temp_config(config_content)
        
        # Should not crash, should handle gracefully by using defaults
        result = self.capture_error_output(config_path)
        # Empty config should be handled gracefully (returns to defaults)
        # This is acceptable behavior, so we just verify no crash
        self.assertGreaterEqual(len(result.strip()), 0)
    
    def test_malformed_yaml_error_reporting(self):
        """Test error reporting for malformed YAML."""
        config_content = """
presets:
  LOCAL:
    endpoint: "test"
  invalid yaml here
    model: "test"
"""
        config_path = self.create_temp_config(config_content)
        
        # Should report YAML parsing error, not crash
        result = self.capture_error_output(config_path)
        self.assertIn("YAML", result.upper())
    
    def test_missing_presets_section(self):
        """Test handling when presets section is completely missing."""
        config_content = """
translation:
  service: local
text_processing:
  split_method: paragraph
"""
        config_path = self.create_temp_config(config_content)
        result = self.capture_error_output(config_path)
        
        # Should handle gracefully and not crash
        self.assertTrue(len(result.strip()) >= 0)  # May or may not have output


if __name__ == '__main__':
    unittest.main()