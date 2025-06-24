#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
# - Initial creation from enchant_cli.py refactoring
# - Extracted configuration and initialization logic
# - Contains setup functions for configuration, logging, and global services
#

"""
cli_setup.py - CLI setup and initialization
==========================================

Handles initialization of configuration, logging, and global services
for the EnChANT CLI application.
"""

from __future__ import annotations

import argparse
import logging
import signal
import sys
from pathlib import Path
from typing import Any, Tuple

from .config_manager import ConfigManager
from .icloud_sync import ICloudSync

# Global services
icloud_sync: ICloudSync | None = None


def setup_configuration() -> Tuple[ConfigManager, dict[str, Any]]:
    """Load and validate configuration from config file.

    Returns:
        Tuple of (ConfigManager instance, configuration dictionary)
    """
    # Pre-parse to get config file path
    preset_parser = argparse.ArgumentParser(add_help=False)
    preset_parser.add_argument("--config", type=str, default="enchant_config.yml")
    preset_parser.add_argument("--preset", type=str, help="Configuration preset name")
    preset_args, _ = preset_parser.parse_known_args()

    # Load configuration with preset support
    try:
        config_manager = ConfigManager(config_path=Path(preset_args.config))
        config = config_manager.config

        # Apply preset if specified
        if preset_args.preset:
            if not config_manager.apply_preset(preset_args.preset):
                print(f"Failed to apply preset: {preset_args.preset}")
                sys.exit(1)
            config = config_manager.config

        return config_manager, config
    except ValueError as e:
        print(f"Configuration error: {e}")
        print("Please fix the configuration file or delete it to regenerate defaults.")
        sys.exit(1)


def setup_logging(config: dict[str, Any]) -> logging.Logger:
    """Set up logging based on configuration.

    Args:
        config: Configuration dictionary

    Returns:
        Configured logger instance
    """
    log_level = getattr(logging, config["logging"]["level"], logging.INFO)
    log_format = config["logging"]["format"]

    logging.basicConfig(level=log_level, format=log_format)
    logger = logging.getLogger(__name__)

    # Set up file logging if enabled
    if config["logging"]["file_enabled"]:
        try:
            file_handler = logging.FileHandler(config["logging"]["file_path"])
            file_handler.setLevel(log_level)
            file_handler.setFormatter(logging.Formatter(log_format))
            logger.addHandler(file_handler)
        except (OSError, PermissionError) as e:
            logger.error(f"Failed to set up file logging to {config['logging']['file_path']}: {e}")
            # Continue without file logging

    return logger


def setup_global_services(config: dict[str, Any]) -> None:
    """Initialize global services like iCloud sync.

    Args:
        config: Configuration dictionary
    """
    global icloud_sync
    icloud_sync = ICloudSync(enabled=config["icloud"]["enabled"])
    # Cost tracking is now handled by global_cost_tracker


def setup_signal_handler(logger: logging.Logger) -> None:
    """Set up signal handling for graceful termination.

    Args:
        logger: Logger instance
    """

    def signal_handler(sig: int, frame: Any) -> None:
        logger.info("Interrupt received. Exiting gracefully.")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)


def check_colorama(logger: logging.Logger) -> None:
    """Check if colorama is available and log warning if not.

    Args:
        logger: Logger instance
    """
    try:
        import colorama  # noqa: F401
    except ImportError:
        logger.warning("colorama package not installed. Colored text may not work properly.")
