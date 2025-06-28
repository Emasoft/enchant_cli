#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test suite for config_prompts_local module.
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from enchant_book_manager.config_prompts_local import (
    LOCAL_SYSTEM_PROMPT,
    LOCAL_USER_PROMPT_1ST,
    LOCAL_USER_PROMPT_2ND,
)


class TestLocalPrompts:
    """Test LOCAL preset prompts."""

    def test_local_system_prompt_exists(self):
        """Test that LOCAL_SYSTEM_PROMPT exists and is not empty."""
        assert LOCAL_SYSTEM_PROMPT is not None
        assert isinstance(LOCAL_SYSTEM_PROMPT, str)
        assert len(LOCAL_SYSTEM_PROMPT) > 0

    def test_local_system_prompt_content(self):
        """Test LOCAL_SYSTEM_PROMPT contains expected content."""
        # Check for key phrases that should be in the system prompt
        assert "professional, authentic machine translation engine" in LOCAL_SYSTEM_PROMPT
        assert "You do not judge the text you translate" in LOCAL_SYSTEM_PROMPT
        assert "You do not abridge, censor or summarize" in LOCAL_SYSTEM_PROMPT
        assert "translate accurately the whole content" in LOCAL_SYSTEM_PROMPT
        assert "rich and literary english vocabulary" in LOCAL_SYSTEM_PROMPT

        # Check for rule references
        assert "MANDATORY rules" in LOCAL_SYSTEM_PROMPT
        assert "wuxia and xianxia novels" in LOCAL_SYSTEM_PROMPT
        assert "Nascent Soul" in LOCAL_SYSTEM_PROMPT
        assert "curly quotes" in LOCAL_SYSTEM_PROMPT
        assert "transliterate the chinese characters" in LOCAL_SYSTEM_PROMPT

        # Check for adult content handling
        assert "adult audience" in LOCAL_SYSTEM_PROMPT
        assert "sex scenes accurately" in LOCAL_SYSTEM_PROMPT
        assert "DO NOT censor" in LOCAL_SYSTEM_PROMPT

    def test_local_system_prompt_rules(self):
        """Test that LOCAL_SYSTEM_PROMPT contains all numbered rules."""
        # Check for specific rule numbers
        for i in range(1, 23):  # Rules 1-22
            assert f"{i}." in LOCAL_SYSTEM_PROMPT

        # Check specific rule examples
        assert "元婴" in LOCAL_SYSTEM_PROMPT
        assert "唐舞桐" in LOCAL_SYSTEM_PROMPT
        assert "Tang Wutong (Dancing Willow)" in LOCAL_SYSTEM_PROMPT

    def test_local_system_prompt_formatting(self):
        """Test LOCAL_SYSTEM_PROMPT formatting."""
        # Should start and end with ;; markers
        assert LOCAL_SYSTEM_PROMPT.startswith(";;")
        assert LOCAL_SYSTEM_PROMPT.endswith(";;")

        # Should not have leading/trailing whitespace
        assert LOCAL_SYSTEM_PROMPT == LOCAL_SYSTEM_PROMPT.strip()

    def test_local_user_prompt_1st_exists(self):
        """Test that LOCAL_USER_PROMPT_1ST exists and is not empty."""
        assert LOCAL_USER_PROMPT_1ST is not None
        assert isinstance(LOCAL_USER_PROMPT_1ST, str)
        assert len(LOCAL_USER_PROMPT_1ST) > 0

    def test_local_user_prompt_1st_content(self):
        """Test LOCAL_USER_PROMPT_1ST contains expected content."""
        assert "professional english translation" in LOCAL_USER_PROMPT_1ST
        assert "following input text" in LOCAL_USER_PROMPT_1ST

    def test_local_user_prompt_1st_formatting(self):
        """Test LOCAL_USER_PROMPT_1ST formatting."""
        # Should start with ;;
        assert LOCAL_USER_PROMPT_1ST.startswith(";;")

        # Should not have leading/trailing whitespace
        assert LOCAL_USER_PROMPT_1ST == LOCAL_USER_PROMPT_1ST.strip()

    def test_local_user_prompt_2nd_exists(self):
        """Test that LOCAL_USER_PROMPT_2ND exists and is not empty."""
        assert LOCAL_USER_PROMPT_2ND is not None
        assert isinstance(LOCAL_USER_PROMPT_2ND, str)
        assert len(LOCAL_USER_PROMPT_2ND) > 0

    def test_local_user_prompt_2nd_content(self):
        """Test LOCAL_USER_PROMPT_2ND contains expected content."""
        assert "Examine the following text" in LOCAL_USER_PROMPT_2ND
        assert "mix of english and chinese characters" in LOCAL_USER_PROMPT_2ND
        assert "correct the badly translated text" in LOCAL_USER_PROMPT_2ND
        assert "Find all chinese words and characters" in LOCAL_USER_PROMPT_2ND
        assert "replace them with an accurate english translation" in LOCAL_USER_PROMPT_2ND
        assert "Find all normal quotes pairs" in LOCAL_USER_PROMPT_2ND
        assert "replace them with curly quotes pairs" in LOCAL_USER_PROMPT_2ND

        # Check for example
        assert "唐舞桐" in LOCAL_USER_PROMPT_2ND
        assert "Tang Wutong (Dancing Willow)" in LOCAL_USER_PROMPT_2ND

        # Check for rules
        assert "NO summaries" in LOCAL_USER_PROMPT_2ND
        assert "NO Chinese characters" in LOCAL_USER_PROMPT_2ND
        assert "No censoring" in LOCAL_USER_PROMPT_2ND

    def test_local_user_prompt_2nd_formatting(self):
        """Test LOCAL_USER_PROMPT_2ND formatting."""
        # Should start with ;;
        assert LOCAL_USER_PROMPT_2ND.startswith(";;")

        # Should not have leading/trailing whitespace
        assert LOCAL_USER_PROMPT_2ND == LOCAL_USER_PROMPT_2ND.strip()

    def test_all_prompts_are_strings(self):
        """Test that all prompts are strings."""
        prompts = [LOCAL_SYSTEM_PROMPT, LOCAL_USER_PROMPT_1ST, LOCAL_USER_PROMPT_2ND]
        for prompt in prompts:
            assert isinstance(prompt, str)

    def test_all_prompts_non_empty(self):
        """Test that all prompts are non-empty."""
        prompts = [LOCAL_SYSTEM_PROMPT, LOCAL_USER_PROMPT_1ST, LOCAL_USER_PROMPT_2ND]
        for prompt in prompts:
            assert len(prompt) > 0

    def test_prompt_lengths(self):
        """Test that prompts have reasonable lengths."""
        # System prompt should be the longest
        assert len(LOCAL_SYSTEM_PROMPT) > len(LOCAL_USER_PROMPT_1ST)
        assert len(LOCAL_SYSTEM_PROMPT) > len(LOCAL_USER_PROMPT_2ND)

        # User prompts should be relatively short
        assert len(LOCAL_USER_PROMPT_1ST) < 200  # First prompt is short
        assert len(LOCAL_USER_PROMPT_2ND) < 900  # Second prompt is medium

    def test_no_placeholder_text(self):
        """Test that prompts don't contain placeholder text."""
        prompts = [LOCAL_SYSTEM_PROMPT, LOCAL_USER_PROMPT_1ST, LOCAL_USER_PROMPT_2ND]
        for prompt in prompts:
            assert "{text}" not in prompt
            assert "{{" not in prompt
            assert "}}" not in prompt
            assert "[INSERT" not in prompt
            assert "TODO" not in prompt

    def test_prompts_are_immutable(self):
        """Test that prompts are defined as constants (uppercase names)."""
        # This is more of a convention test
        import enchant_book_manager.config_prompts_local as module

        # Check that all uppercase attributes that don't start with _ are strings
        for attr_name in dir(module):
            if attr_name.isupper() and not attr_name.startswith("_"):
                attr_value = getattr(module, attr_name)
                assert isinstance(attr_value, str), f"{attr_name} should be a string"

    def test_prompt_consistency(self):
        """Test consistency between prompts."""
        # Both user prompts should use similar formatting style
        assert LOCAL_USER_PROMPT_1ST.startswith(";;")
        assert LOCAL_USER_PROMPT_2ND.startswith(";;")

        # Second prompt should reference similar concepts as system prompt
        assert "curly quotes" in LOCAL_SYSTEM_PROMPT
        assert "curly quotes" in LOCAL_USER_PROMPT_2ND

        assert "chinese characters" in LOCAL_SYSTEM_PROMPT.lower()
        assert "chinese characters" in LOCAL_USER_PROMPT_2ND.lower()

    def test_module_imports(self):
        """Test that the module can be imported and exports are correct."""
        import enchant_book_manager.config_prompts_local as module

        # Check that expected exports exist
        assert hasattr(module, "LOCAL_SYSTEM_PROMPT")
        assert hasattr(module, "LOCAL_USER_PROMPT_1ST")
        assert hasattr(module, "LOCAL_USER_PROMPT_2ND")

    def test_unicode_handling(self):
        """Test that prompts handle unicode correctly."""
        # Check that Chinese example characters are present
        assert "元婴" in LOCAL_SYSTEM_PROMPT
        assert "唐舞桐" in LOCAL_SYSTEM_PROMPT
        assert "唐舞桐" in LOCAL_USER_PROMPT_2ND

        # Ensure prompts are valid UTF-8
        for prompt in [
            LOCAL_SYSTEM_PROMPT,
            LOCAL_USER_PROMPT_1ST,
            LOCAL_USER_PROMPT_2ND,
        ]:
            # This will raise if not valid UTF-8
            prompt.encode("utf-8").decode("utf-8")
