#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Common print utilities for console output with rich formatting support.
"""

import builtins
import re

# Try to import rich for enhanced printing
try:
    from rich import print
    rich_available = True
except ImportError:
    # Use standard print if rich isn't available
    print = builtins.print
    rich_available = False

def safe_print(*args, **kwargs) -> None:
    """Print with rich if available, else strip markup tags.
    
    This function provides a consistent interface for printing
    that works with or without the rich library installed.
    When rich is not available, it strips rich markup tags
    to provide clean plain text output.
    
    Args:
        *args: Arguments to print
        **kwargs: Keyword arguments for print function
    """
    if rich_available:
        print(*args, **kwargs)
    else:
        # Strip rich markup tags for plain text output
        text = " ".join(str(arg) for arg in args)
        clean_text = re.sub(r'\[/?[^]]+\]', '', text)
        builtins.print(clean_text)