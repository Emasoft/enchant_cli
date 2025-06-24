#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
# - Refactored to import prompts from separate modules
# - Split LOCAL and REMOTE prompts into separate files to reduce file size
# - This module now serves as a single import point for all prompts
#

"""
config_prompts.py - Translation prompts for ENCHANT presets
"""

from .config_prompts_local import (
    LOCAL_SYSTEM_PROMPT,
    LOCAL_USER_PROMPT_1ST,
    LOCAL_USER_PROMPT_2ND,
)
from .config_prompts_remote import (
    REMOTE_USER_PROMPT_1ST,
    REMOTE_USER_PROMPT_2ND,
)

# Re-export all prompts for backward compatibility
__all__ = [
    "LOCAL_SYSTEM_PROMPT",
    "LOCAL_USER_PROMPT_1ST",
    "LOCAL_USER_PROMPT_2ND",
    "REMOTE_USER_PROMPT_1ST",
    "REMOTE_USER_PROMPT_2ND",
]
