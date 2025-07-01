#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
gitleaks-safe - Memory-safe git hooks for gitleaks with multi-instance support
==============================================================================

A Python implementation of memory-safe wrappers for gitleaks that prevents
system crashes from concurrent processes and memory exhaustion.
"""

__version__ = "2.0.0"
__all__ = ["cli", "installer", "cleanup", "wrapper", "utils"]
