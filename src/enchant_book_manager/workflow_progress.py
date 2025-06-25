#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
# - Initial creation from workflow_orchestrator.py refactoring
# - Extracted progress tracking and YAML utilities
# - Contains functions for saving/loading workflow progress
#

"""
workflow_progress.py - Progress tracking utilities for workflow orchestration
============================================================================

Provides utilities for tracking and persisting workflow progress across
the three phases of novel processing.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

from .common_yaml_utils import load_safe_yaml


def load_safe_yaml_wrapper(path: Path, logger: logging.Logger) -> dict[str, Any] | None:
    """
    Safely load YAML file - wrapper for common utility with exception handling.

    Args:
        path: Path to YAML file
        logger: Logger instance

    Returns:
        Loaded YAML data or None on error
    """
    try:
        return load_safe_yaml(path)
    except ValueError as e:
        logger.error(f"Error loading YAML from {path}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error loading YAML from {path}: {e}")
        return None


def save_progress(progress_file: Path, progress: dict[str, Any], logger: logging.Logger) -> None:
    """
    Save progress to YAML file.

    Args:
        progress_file: Path to progress file
        progress: Progress data to save
        logger: Logger instance
    """
    try:
        with progress_file.open("w") as f:
            yaml.safe_dump(progress, f)
    except (OSError, yaml.YAMLError) as e:
        logger.error(f"Error saving progress file: {e}")
        # Continue anyway - progress tracking is not critical


def create_initial_progress(file_path: Path) -> dict[str, Any]:
    """
    Create initial progress structure for a novel file.

    Args:
        file_path: Path to the novel file

    Returns:
        Initial progress dictionary
    """
    return {
        "original_file": str(file_path),
        "phases": {
            "renaming": {"status": "pending", "result": None},
            "translation": {"status": "pending", "result": None},
            "epub": {"status": "pending", "result": None},
        },
    }


def is_phase_completed(progress: dict[str, Any], phase: str) -> bool:
    """
    Check if a specific phase is completed.

    Args:
        progress: Progress dictionary
        phase: Phase name ('renaming', 'translation', or 'epub')

    Returns:
        True if phase is completed
    """
    phases = progress.get("phases", {})
    phase_data = phases.get(phase, {})
    status = phase_data.get("status", "")
    return bool(status == "completed")


def are_all_phases_completed(progress: dict[str, Any]) -> bool:
    """
    Check if all phases are completed or skipped.

    Args:
        progress: Progress dictionary

    Returns:
        True if all phases are completed or skipped
    """
    return all(phase["status"] in ("completed", "skipped") for phase in progress.get("phases", {}).values())


def get_progress_file_path(file_path: Path) -> Path:
    """
    Get the progress file path for a given novel file.

    Args:
        file_path: Path to the novel file

    Returns:
        Path to the progress file
    """
    return file_path.parent / f".{file_path.stem}_progress.yml"
