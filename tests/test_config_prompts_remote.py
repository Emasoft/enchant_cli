#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test suite for config_prompts_remote module.
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from enchant_book_manager.config_prompts_remote import (
    REMOTE_USER_PROMPT_1ST,
    REMOTE_USER_PROMPT_2ND,
)


class TestRemotePrompts:
    """Test REMOTE preset prompts."""

    def test_remote_user_prompt_1st_exists(self):
        """Test that REMOTE_USER_PROMPT_1ST exists and is not empty."""
        assert REMOTE_USER_PROMPT_1ST is not None
        assert isinstance(REMOTE_USER_PROMPT_1ST, str)
        assert len(REMOTE_USER_PROMPT_1ST) > 0

    def test_remote_user_prompt_1st_content(self):
        """Test REMOTE_USER_PROMPT_1ST contains expected content."""
        # Check task description
        assert "[Task]" in REMOTE_USER_PROMPT_1ST
        assert "professional and helpful translator" in REMOTE_USER_PROMPT_1ST
        assert "proficient in languages and literature" in REMOTE_USER_PROMPT_1ST
        assert "excellent and refined english prose" in REMOTE_USER_PROMPT_1ST
        assert "translate the Chinese text" in REMOTE_USER_PROMPT_1ST

        # Check for translation rules section
        assert "[TRANSLATION RULES]" in REMOTE_USER_PROMPT_1ST
        assert "Translate directly the Chinese content" in REMOTE_USER_PROMPT_1ST
        assert "Do not omit any information" in REMOTE_USER_PROMPT_1ST
        assert "Do not leave any chinese character untranslated" in REMOTE_USER_PROMPT_1ST
        assert "Use romanization when a name has no english equivalent" in REMOTE_USER_PROMPT_1ST

        # Check for specific examples
        assert "唐舞桐" in REMOTE_USER_PROMPT_1ST
        assert "Tang Wutong (Dancing Willow)" in REMOTE_USER_PROMPT_1ST
        assert "元婴" in REMOTE_USER_PROMPT_1ST
        assert "Nascent Soul" in REMOTE_USER_PROMPT_1ST
        assert "修罗场" in REMOTE_USER_PROMPT_1ST
        assert "dramatic and chaotic situation" in REMOTE_USER_PROMPT_1ST
        assert "榜下捉婿" in REMOTE_USER_PROMPT_1ST
        assert "Chosing a Son-in-law From a List" in REMOTE_USER_PROMPT_1ST

        # Check for family terms rule
        assert "弟弟" in REMOTE_USER_PROMPT_1ST
        assert "younger brother" in REMOTE_USER_PROMPT_1ST

        # Check for quotes handling
        assert "curly quotes" in REMOTE_USER_PROMPT_1ST
        assert '""' in REMOTE_USER_PROMPT_1ST
        assert "''" in REMOTE_USER_PROMPT_1ST
        assert "通行證？" in REMOTE_USER_PROMPT_1ST
        assert "A pass?" in REMOTE_USER_PROMPT_1ST

    def test_remote_user_prompt_1st_rules(self):
        """Test that REMOTE_USER_PROMPT_1ST contains key translation rules."""
        # Key rules that should be present
        assert "wuxia and xianxia novels" in REMOTE_USER_PROMPT_1ST
        assert "daoist terminology" in REMOTE_USER_PROMPT_1ST
        assert "infer the meaning from the context" in REMOTE_USER_PROMPT_1ST
        assert "improve the fluency and clarity" in REMOTE_USER_PROMPT_1ST
        assert "gender of words and prepositions" in REMOTE_USER_PROMPT_1ST
        assert "Never summarize or omit any part" in REMOTE_USER_PROMPT_1ST
        assert "No chinese characters must appear in the output" in REMOTE_USER_PROMPT_1ST

    def test_remote_user_prompt_1st_formatting(self):
        """Test REMOTE_USER_PROMPT_1ST formatting."""
        # Should start with ;;
        assert REMOTE_USER_PROMPT_1ST.startswith(";;")

        # Should not have leading/trailing whitespace
        assert REMOTE_USER_PROMPT_1ST == REMOTE_USER_PROMPT_1ST.strip()

        # Should contain proper sections
        assert ";; [Task]" in REMOTE_USER_PROMPT_1ST or ";;[Task]" in REMOTE_USER_PROMPT_1ST
        assert "[TRANSLATION RULES]" in REMOTE_USER_PROMPT_1ST

    def test_remote_user_prompt_2nd_exists(self):
        """Test that REMOTE_USER_PROMPT_2ND exists and is not empty."""
        assert REMOTE_USER_PROMPT_2ND is not None
        assert isinstance(REMOTE_USER_PROMPT_2ND, str)
        assert len(REMOTE_USER_PROMPT_2ND) > 0

    def test_remote_user_prompt_2nd_content(self):
        """Test REMOTE_USER_PROMPT_2ND contains expected content."""
        # Check task description
        assert "[TASK]" in REMOTE_USER_PROMPT_2ND
        assert "helpful and professional translator" in REMOTE_USER_PROMPT_2ND
        assert "mix of english and chinese characters" in REMOTE_USER_PROMPT_2ND
        assert "Find all chinese words and characters" in REMOTE_USER_PROMPT_2ND
        assert "replace them with an accurate english translation" in REMOTE_USER_PROMPT_2ND

        # Check for editing rules section
        assert "[EDITING RULES]" in REMOTE_USER_PROMPT_2ND
        assert "Do not leave any chinese character untranslated" in REMOTE_USER_PROMPT_2ND
        assert "Use romanization when a name has no english equivalent" in REMOTE_USER_PROMPT_2ND
        assert "Do not add comments or annotations" in REMOTE_USER_PROMPT_2ND

        # Check for quotes handling
        assert "Convert all normal quotes pairs" in REMOTE_USER_PROMPT_2ND
        assert "curly quotes pairs" in REMOTE_USER_PROMPT_2ND
        assert '""' in REMOTE_USER_PROMPT_2ND
        assert "''" in REMOTE_USER_PROMPT_2ND
        assert "通行證？" in REMOTE_USER_PROMPT_2ND
        assert "A pass?" in REMOTE_USER_PROMPT_2ND

        # Check for genre-specific rules
        assert "xianxia/wuxia or daoist cultivation concepts" in REMOTE_USER_PROMPT_2ND
        assert "Output only the perfected english text" in REMOTE_USER_PROMPT_2ND

    def test_remote_user_prompt_2nd_formatting(self):
        """Test REMOTE_USER_PROMPT_2ND formatting."""
        # Should start with ;;
        assert REMOTE_USER_PROMPT_2ND.startswith(";;")

        # Should not have leading/trailing whitespace
        assert REMOTE_USER_PROMPT_2ND == REMOTE_USER_PROMPT_2ND.strip()

        # Should contain proper sections
        assert ";; [TASK]" in REMOTE_USER_PROMPT_2ND or ";;[TASK]" in REMOTE_USER_PROMPT_2ND
        assert "[EDITING RULES]" in REMOTE_USER_PROMPT_2ND

    def test_both_prompts_are_strings(self):
        """Test that both prompts are strings."""
        prompts = [REMOTE_USER_PROMPT_1ST, REMOTE_USER_PROMPT_2ND]
        for prompt in prompts:
            assert isinstance(prompt, str)

    def test_both_prompts_non_empty(self):
        """Test that both prompts are non-empty."""
        prompts = [REMOTE_USER_PROMPT_1ST, REMOTE_USER_PROMPT_2ND]
        for prompt in prompts:
            assert len(prompt) > 0

    def test_prompt_lengths(self):
        """Test that prompts have reasonable lengths."""
        # Both prompts should be substantial
        assert len(REMOTE_USER_PROMPT_1ST) > 1000  # First prompt is long
        assert len(REMOTE_USER_PROMPT_2ND) > 800  # Second prompt is also substantial

        # First prompt should be longer than second
        assert len(REMOTE_USER_PROMPT_1ST) > len(REMOTE_USER_PROMPT_2ND)

    def test_no_placeholder_text(self):
        """Test that prompts don't contain placeholder text."""
        prompts = [REMOTE_USER_PROMPT_1ST, REMOTE_USER_PROMPT_2ND]
        for prompt in prompts:
            assert "{text}" not in prompt
            assert "{{" not in prompt
            assert "}}" not in prompt
            assert "[INSERT" not in prompt
            assert "TODO" not in prompt

    def test_prompts_are_immutable(self):
        """Test that prompts are defined as constants (uppercase names)."""
        # This is more of a convention test
        import enchant_book_manager.config_prompts_remote as module

        # Check that all uppercase attributes that don't start with _ are strings
        for attr_name in dir(module):
            if attr_name.isupper() and not attr_name.startswith("_"):
                attr_value = getattr(module, attr_name)
                assert isinstance(attr_value, str), f"{attr_name} should be a string"

    def test_prompt_consistency(self):
        """Test consistency between prompts."""
        # Both prompts should use similar formatting style
        assert REMOTE_USER_PROMPT_1ST.startswith(";;")
        assert REMOTE_USER_PROMPT_2ND.startswith(";;")

        # Both should mention translation
        assert "translat" in REMOTE_USER_PROMPT_1ST.lower()
        assert "translat" in REMOTE_USER_PROMPT_2ND.lower()

        # Both should mention curly quotes
        assert "curly quotes" in REMOTE_USER_PROMPT_1ST
        assert "curly quotes" in REMOTE_USER_PROMPT_2ND

        # Both should mention chinese characters
        assert "chinese" in REMOTE_USER_PROMPT_1ST.lower()
        assert "chinese" in REMOTE_USER_PROMPT_2ND.lower()

    def test_module_imports(self):
        """Test that the module can be imported and exports are correct."""
        import enchant_book_manager.config_prompts_remote as module

        # Check that expected exports exist
        assert hasattr(module, "REMOTE_USER_PROMPT_1ST")
        assert hasattr(module, "REMOTE_USER_PROMPT_2ND")

        # Should not have REMOTE_SYSTEM_PROMPT (remote doesn't use system prompt)
        assert not hasattr(module, "REMOTE_SYSTEM_PROMPT")

    def test_unicode_handling(self):
        """Test that prompts handle unicode correctly."""
        # Check that Chinese example characters are present
        assert "唐舞桐" in REMOTE_USER_PROMPT_1ST
        assert "元婴" in REMOTE_USER_PROMPT_1ST
        assert "修罗场" in REMOTE_USER_PROMPT_1ST
        assert "榜下捉婿" in REMOTE_USER_PROMPT_1ST
        assert "弟弟" in REMOTE_USER_PROMPT_1ST
        assert "通行證？" in REMOTE_USER_PROMPT_1ST
        assert "通行證？" in REMOTE_USER_PROMPT_2ND

        # Ensure prompts are valid UTF-8
        for prompt in [REMOTE_USER_PROMPT_1ST, REMOTE_USER_PROMPT_2ND]:
            # This will raise if not valid UTF-8
            prompt.encode("utf-8").decode("utf-8")

    def test_specific_translation_examples(self):
        """Test that specific translation examples are present and correct."""
        # First prompt examples
        assert "唐舞桐` must be translated as: `Tang Wutong (Dancing Willow)`" in REMOTE_USER_PROMPT_1ST
        assert "元婴` must be translated as `Nascent Soul`" in REMOTE_USER_PROMPT_1ST
        assert "修罗场` can be translated as `dramatic and chaotic situation`" in REMOTE_USER_PROMPT_1ST
        assert "榜下捉婿` can be translated as `Chosing a Son-in-law From a List`" in REMOTE_USER_PROMPT_1ST

        # Quote examples in both prompts - check parts separately due to special characters
        assert "通行證？" in REMOTE_USER_PROMPT_1ST
        assert "A pass?" in REMOTE_USER_PROMPT_1ST
        assert "通行證？" in REMOTE_USER_PROMPT_2ND
        assert "A pass?" in REMOTE_USER_PROMPT_2ND

    def test_no_system_prompt(self):
        """Test that remote preset doesn't have a system prompt."""
        # Remote preset only uses user prompts, no system prompt
        import enchant_book_manager.config_prompts_remote as module

        # Ensure no system prompt is defined
        assert not hasattr(module, "REMOTE_SYSTEM_PROMPT")
        assert not hasattr(module, "SYSTEM_PROMPT")

    def test_editing_vs_translation_focus(self):
        """Test that prompts have different focuses."""
        # First prompt focuses on translation
        assert "translate the Chinese text" in REMOTE_USER_PROMPT_1ST
        assert "TRANSLATION RULES" in REMOTE_USER_PROMPT_1ST

        # Second prompt focuses on editing/fixing
        assert "Examine the following text" in REMOTE_USER_PROMPT_2ND
        assert "EDITING RULES" in REMOTE_USER_PROMPT_2ND
        assert "Find all chinese words and characters and replace them" in REMOTE_USER_PROMPT_2ND
