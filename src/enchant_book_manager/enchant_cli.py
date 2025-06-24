#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright 2025 Emasoft
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
# - Fixed architecture: Made enchant_cli.py the unified orchestrator
# - Removed incorrect translation functionality that belonged in cli_translator.py
# - Added proper 3-phase orchestration: rename -> translate -> epub
# - Integrated configuration management with preset support
# - Added progress tracking for each phase
# - Maintained iCloud sync, pricing manager integration
# - Refactored into smaller modules: cli_parser, workflow_orchestrator,
#   cli_batch_handler, cli_setup
#

from __future__ import annotations

import logging
import sys
from pathlib import Path

from .common_print_utils import safe_print
from .cli_parser import create_parser, validate_args
from .cli_setup import (
    setup_configuration,
    setup_logging,
    setup_global_services,
    setup_signal_handler,
    check_colorama,
)
from .workflow_orchestrator import process_novel_unified
from .cli_batch_handler import process_batch

APP_NAME = "EnChANT - English-Chinese Automatic Novel Translator"
APP_VERSION = "1.0.0"  # Semantic version (major.minor.patch)
MIN_PYTHON_VERSION_REQUIRED = "3.8"

# Note: model_pricing module is deprecated - using global_cost_tracker instead

# Global logger - will be initialized in main()
tolog: logging.Logger | None = None


def main() -> None:
    """Main entry point for the EnChANT CLI application."""
    global tolog

    # Set up configuration first
    config_manager, config = setup_configuration()

    # Set up logging based on config
    tolog = setup_logging(config)

    # Initialize global services
    setup_global_services(config)

    # Check colorama availability
    check_colorama(tolog)

    # Set up signal handling for graceful termination
    setup_signal_handler(tolog)

    # Create and configure argument parser
    parser = create_parser(config)
    args = parser.parse_args()

    # Update config with preset and command-line arguments
    config = config_manager.update_with_args(args)

    # Validate arguments
    validate_args(args, parser)

    # Log if --translated was provided
    if args.translated:
        tolog.info("--translated option provided, automatically skipping renaming and translation phases")

    # Process files using unified orchestration
    if args.batch:
        process_batch(args, tolog)
        return

    # Single file processing
    if args.filepath:
        file_path = Path(args.filepath)

        # Check if file exists
        if not file_path.exists():
            tolog.error(f"File not found: {file_path}")
            safe_print(f"[bold red]File not found: {file_path}[/bold red]")
            sys.exit(1)
    else:
        # Using --translated directly without filepath
        if args.translated:
            # Use the translated file's directory as the working directory
            file_path = Path(args.translated)
        else:
            # This shouldn't happen due to validation, but just in case
            tolog.error("No input file specified")
            safe_print("[bold red]No input file specified[/bold red]")
            sys.exit(1)

    # Process single file with unified processor
    tolog.info(f"Starting unified processing for file: {file_path}")

    try:
        success = process_novel_unified(file_path, args, tolog)

        if success:
            safe_print("[bold green]Novel processing completed successfully![/bold green]")
        else:
            safe_print("[bold yellow]Novel processing completed with some issues. Check logs for details.[/bold yellow]")
            sys.exit(1)

    except Exception as e:
        tolog.exception("Fatal error during novel processing")
        safe_print(f"[bold red]Fatal error: {e}[/bold red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
