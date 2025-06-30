#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test suite for config_prompts module.
"""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

import enchant_book_manager.config_prompts as config_prompts


class TestConfigPrompts:
    """Test config_prompts module imports and exports."""

    def test_module_imports(self):
        """Test that all expected imports are available."""
        # Test that the module itself can be imported
        assert config_prompts is not None

    def test_local_prompts_imported(self):
        """Test that LOCAL prompts are imported correctly."""
        assert hasattr(config_prompts, "LOCAL_SYSTEM_PROMPT")
        assert hasattr(config_prompts, "LOCAL_USER_PROMPT_1ST")
        assert hasattr(config_prompts, "LOCAL_USER_PROMPT_2ND")

    def test_remote_prompts_imported(self):
        """Test that REMOTE prompts are imported correctly."""
        assert hasattr(config_prompts, "REMOTE_USER_PROMPT_1ST")
        assert hasattr(config_prompts, "REMOTE_USER_PROMPT_2ND")

    def test_all_exports(self):
        """Test that __all__ contains all expected exports."""
        assert hasattr(config_prompts, "__all__")
        expected_exports = [
            "LOCAL_SYSTEM_PROMPT",
            "LOCAL_USER_PROMPT_1ST",
            "LOCAL_USER_PROMPT_2ND",
            "REMOTE_USER_PROMPT_1ST",
            "REMOTE_USER_PROMPT_2ND",
        ]
        assert set(config_prompts.__all__) == set(expected_exports)

    def test_prompt_types(self):
        """Test that all prompts are strings."""
        # All prompts should be strings
        assert isinstance(config_prompts.LOCAL_SYSTEM_PROMPT, str)
        assert isinstance(config_prompts.LOCAL_USER_PROMPT_1ST, str)
        assert isinstance(config_prompts.LOCAL_USER_PROMPT_2ND, str)
        assert isinstance(config_prompts.REMOTE_USER_PROMPT_1ST, str)
        assert isinstance(config_prompts.REMOTE_USER_PROMPT_2ND, str)

    def test_prompt_content_not_empty(self):
        """Test that prompts are not empty strings."""
        assert len(config_prompts.LOCAL_SYSTEM_PROMPT) > 0
        assert len(config_prompts.LOCAL_USER_PROMPT_1ST) > 0
        assert len(config_prompts.LOCAL_USER_PROMPT_2ND) > 0
        assert len(config_prompts.REMOTE_USER_PROMPT_1ST) > 0
        assert len(config_prompts.REMOTE_USER_PROMPT_2ND) > 0

    def test_local_system_prompt_content(self):
        """Test that LOCAL_SYSTEM_PROMPT contains expected keywords."""
        prompt = config_prompts.LOCAL_SYSTEM_PROMPT
        # Should mention translator or translation
        assert "translat" in prompt.lower()

    def test_prompt_structure_format(self):
        """Test that prompts have expected structure."""
        # First pass prompts should mention translation
        assert "translat" in config_prompts.LOCAL_USER_PROMPT_1ST.lower()
        assert "translat" in config_prompts.REMOTE_USER_PROMPT_1ST.lower()

        # Second pass prompts should mention some form of refinement
        assert any(word in config_prompts.LOCAL_USER_PROMPT_2ND.lower() for word in ["correct", "fix", "refine", "improve", "examine"])
        assert any(word in config_prompts.REMOTE_USER_PROMPT_2ND.lower() for word in ["correct", "fix", "refine", "improve", "examine"])

    def test_import_from_module(self):
        """Test that we can import directly from the module."""
        from enchant_book_manager.config_prompts import (
            LOCAL_SYSTEM_PROMPT,
            LOCAL_USER_PROMPT_1ST,
            LOCAL_USER_PROMPT_2ND,
            REMOTE_USER_PROMPT_1ST,
            REMOTE_USER_PROMPT_2ND,
        )

        # Verify all imports work
        assert LOCAL_SYSTEM_PROMPT is not None
        assert LOCAL_USER_PROMPT_1ST is not None
        assert LOCAL_USER_PROMPT_2ND is not None
        assert REMOTE_USER_PROMPT_1ST is not None
        assert REMOTE_USER_PROMPT_2ND is not None

    def test_backward_compatibility(self):
        """Test that the module maintains backward compatibility."""
        # The module serves as a single import point, so all prompts
        # should be accessible through it
        all_attrs = dir(config_prompts)

        # Check all expected prompts are present
        expected_prompts = [
            "LOCAL_SYSTEM_PROMPT",
            "LOCAL_USER_PROMPT_1ST",
            "LOCAL_USER_PROMPT_2ND",
            "REMOTE_USER_PROMPT_1ST",
            "REMOTE_USER_PROMPT_2ND",
        ]

        for prompt_name in expected_prompts:
            assert prompt_name in all_attrs
            # And they should be accessible
            assert getattr(config_prompts, prompt_name) is not None

    def test_no_extra_exports(self):
        """Test that only expected items are in __all__."""
        # Get all public attributes (not starting with _)
        public_attrs = [attr for attr in dir(config_prompts) if not attr.startswith("_")]

        # Remove module metadata
        module_metadata = [
            "__builtins__",
            "__cached__",
            "__doc__",
            "__file__",
            "__loader__",
            "__name__",
            "__package__",
            "__spec__",
        ]
        for meta in module_metadata:
            if meta in public_attrs:
                public_attrs.remove(meta)

        # All remaining public attributes should be in __all__
        for attr in public_attrs:
            if attr != "__all__":  # Except __all__ itself
                assert attr in config_prompts.__all__

    def test_prompts_unique(self):
        """Test that all prompts are unique."""
        prompts = [
            config_prompts.LOCAL_SYSTEM_PROMPT,
            config_prompts.LOCAL_USER_PROMPT_1ST,
            config_prompts.LOCAL_USER_PROMPT_2ND,
            config_prompts.REMOTE_USER_PROMPT_1ST,
            config_prompts.REMOTE_USER_PROMPT_2ND,
        ]

        # All prompts should be unique
        assert len(prompts) == len(set(prompts))
