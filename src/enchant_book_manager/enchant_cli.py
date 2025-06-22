#!/usr/bin/env python3

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
#

from __future__ import annotations

import argparse
import datetime as dt
import logging
import os
import signal
import sys
from pathlib import Path
from typing import Any

import filelock
import yaml

from .common_print_utils import safe_print
from .common_utils import extract_book_info_from_path, sanitize_filename
from .common_yaml_utils import load_safe_yaml as load_yaml_safe
from .config_manager import ConfigManager, get_config
from .icloud_sync import ICloudSync

try:
    import colorama as cr
except ImportError:
    cr = None  # type: ignore[assignment]
    # tolog is not yet defined here, so we will log warning later in main if needed

APP_NAME = "EnChANT - English-Chinese Automatic Novel Translator"
APP_VERSION = "1.0.0"  # Semantic version (major.minor.patch)
MIN_PYTHON_VERSION_REQUIRED = "3.8"

# Note: model_pricing module is deprecated - using global_cost_tracker instead

# Import modules for the three phases
try:
    from .renamenovels import process_novel_file as rename_novel

    renaming_available = True
except ImportError:
    renaming_available = False

try:
    from .cli_translator import translate_novel

    translation_available = True
except ImportError:
    translation_available = False

try:
    from .epub_utils import create_epub_with_config, get_epub_config_from_book_info

    epub_available = True
except ImportError:
    epub_available = False

# Global variables - will be initialized in main()
tolog: logging.Logger = logging.getLogger(__name__)  # Initialize immediately to avoid None
icloud_sync: ICloudSync | None = None
# Cost tracking is now handled by global_cost_tracker from cost_tracker module

### ORCHESTRATION FUNCTIONS #####


def load_safe_yaml(path: Path) -> dict[str, Any] | None:
    """Safely load YAML file - wrapper for common utility with exception handling"""
    try:
        return load_yaml_safe(path)
    except ValueError as e:
        tolog.error(f"Error loading YAML from {path}: {e}")
        return None
    except Exception as e:
        tolog.error(f"Unexpected error loading YAML from {path}: {e}")
        return None


def process_novel_unified(file_path: Path, args: argparse.Namespace) -> bool:
    """
    Unified processing function for a single novel file with all three phases:
    1. Renaming (unless --skip-renaming)
    2. Translation (unless --skip-translating)
    3. EPUB generation (unless --skip-epub)

    Returns True if all enabled phases completed successfully
    """
    current_path = file_path

    # Create a progress file for this specific novel to track phases
    progress_file = file_path.parent / f".{file_path.stem}_progress.yml"

    # Load existing progress if resuming
    if args.resume and progress_file.exists():
        progress = load_safe_yaml(progress_file) or {}
    else:
        progress = {
            "original_file": str(file_path),
            "phases": {
                "renaming": {"status": "pending", "result": None},
                "translation": {"status": "pending", "result": None},
                "epub": {"status": "pending", "result": None},
            },
        }

    # Update current path from progress if available
    if progress["phases"]["renaming"]["status"] == "completed" and progress["phases"]["renaming"]["result"]:
        current_path = Path(progress["phases"]["renaming"]["result"])
        if current_path.exists():
            if tolog:
                tolog.info(f"Resuming with renamed file: {current_path.name}")
        else:
            current_path = file_path

    # Phase 1: Renaming
    if getattr(args, "skip_renaming", False):
        # Mark as skipped if not already completed
        if progress["phases"]["renaming"]["status"] != "completed":
            progress["phases"]["renaming"]["status"] = "skipped"
            tolog.info("Phase 1: Skipping renaming phase")
    elif not getattr(args, "skip_renaming", False) and progress["phases"]["renaming"]["status"] != "completed":
        tolog.info(f"Phase 1: Renaming file {file_path.name}")

        if not renaming_available:
            tolog.error("Renaming phase requested but renamenovels module not available")
            progress["phases"]["renaming"]["status"] = "failed"
            progress["phases"]["renaming"]["error"] = "Module not available"
        else:
            # Get API key for renaming
            api_key = getattr(args, "openai_api_key", None) or os.getenv("OPENROUTER_API_KEY")
            if not api_key:
                tolog.error("OpenRouter API key required for renaming. Use --openai-api-key or set OPENROUTER_API_KEY env var")
                progress["phases"]["renaming"]["status"] = "failed"
                progress["phases"]["renaming"]["error"] = "No API key"
            else:
                try:
                    # Use command line options if provided, otherwise defaults
                    rename_model = getattr(args, "rename_model", None) or "gpt-4o-mini"
                    rename_temperature = float(getattr(args, "rename_temperature", 0.0)) if hasattr(args, "rename_temperature") and args.rename_temperature is not None else 0.0
                    rename_dry_run = getattr(args, "rename_dry_run", False)

                    success, new_path, metadata = rename_novel(
                        file_path,
                        api_key=api_key,
                        model=rename_model,
                        temperature=rename_temperature,
                        dry_run=rename_dry_run,
                    )

                    if success and new_path:
                        current_path = new_path
                        progress["phases"]["renaming"]["status"] = "completed"
                        progress["phases"]["renaming"]["result"] = str(new_path)
                        tolog.info(f"File renamed to: {new_path.name}")
                    else:
                        tolog.warning(f"Renaming failed for {file_path.name}, continuing with original name")
                        progress["phases"]["renaming"]["status"] = "failed"

                except Exception as e:
                    tolog.error(f"Error during renaming: {e}")
                    progress["phases"]["renaming"]["status"] = "failed"
                    progress["phases"]["renaming"]["error"] = str(e)

        # Save progress
        try:
            try:
                with progress_file.open("w") as f:
                    yaml.safe_dump(progress, f)
            except (OSError, yaml.YAMLError) as e:
                tolog.error(f"Error saving batch progress: {e}")
                # Re-raise as this is critical for batch processing
                raise
        except (OSError, yaml.YAMLError) as e:
            tolog.error(f"Error saving progress file: {e}")
            # Continue anyway - progress tracking is not critical

    # Phase 2: Translation
    if getattr(args, "skip_translating", False):
        # Mark as skipped if not already completed
        if progress["phases"]["translation"]["status"] != "completed":
            progress["phases"]["translation"]["status"] = "skipped"
            tolog.info("Phase 2: Skipping translation phase")
    elif not getattr(args, "skip_translating", False) and progress["phases"]["translation"]["status"] != "completed":
        tolog.info(f"Phase 2: Translating {current_path.name}")

        if not translation_available:
            tolog.error("Translation phase requested but cli_translator module not available")
            progress["phases"]["translation"]["status"] = "failed"
            progress["phases"]["translation"]["error"] = "Module not available"
        else:
            try:
                # Call translation module
                success = translate_novel(
                    str(current_path),
                    encoding=getattr(args, "encoding", "utf-8"),
                    max_chars=getattr(args, "max_chars", 12000),
                    resume=args.resume,
                    create_epub=False,  # EPUB handled in phase 3
                    remote=getattr(args, "remote", False),
                )

                if success:
                    progress["phases"]["translation"]["status"] = "completed"
                    progress["phases"]["translation"]["result"] = "success"
                    tolog.info(f"Translation completed for {current_path.name}")
                else:
                    progress["phases"]["translation"]["status"] = "failed"
                    progress["phases"]["translation"]["error"] = "Translation failed"

            except Exception as e:
                tolog.error(f"Error during translation: {e}")
                progress["phases"]["translation"]["status"] = "failed"
                progress["phases"]["translation"]["error"] = str(e)

        # Save progress
        try:
            try:
                with progress_file.open("w") as f:
                    yaml.safe_dump(progress, f)
            except (OSError, yaml.YAMLError) as e:
                tolog.error(f"Error saving batch progress: {e}")
                # Re-raise as this is critical for batch processing
                raise
        except (OSError, yaml.YAMLError) as e:
            tolog.error(f"Error saving progress file: {e}")
            # Continue anyway - progress tracking is not critical

    # Phase 3: EPUB Generation
    if getattr(args, "skip_epub", False):
        # Mark as skipped if not already completed
        if progress["phases"]["epub"]["status"] != "completed":
            progress["phases"]["epub"]["status"] = "skipped"
            tolog.info("Phase 3: Skipping EPUB generation phase")
    elif not getattr(args, "skip_epub", False) and progress["phases"]["epub"]["status"] != "completed":
        tolog.info(f"Phase 3: Generating EPUB for {current_path.name}")

        if not epub_available:
            tolog.error("EPUB phase requested but make_epub module not available")
            progress["phases"]["epub"]["status"] = "failed"
            progress["phases"]["epub"]["error"] = "Module not available"
        else:
            try:
                # Check if --translated option was provided
                if hasattr(args, "translated") and args.translated:
                    # Use the provided translated file directly
                    translated_file = Path(args.translated)

                    # Extract book info from the translated file name or original file
                    book_info = extract_book_info_from_path(translated_file)
                    book_title = book_info.get("title_english", translated_file.stem)
                    book_author = book_info.get("author_english", "Unknown")

                    tolog.info(f"Using provided translated file: {translated_file}")
                else:
                    # Original logic: look for translated file in expected directory
                    # Extract book info from filename
                    book_info = extract_book_info_from_path(current_path)

                    # Find the output directory for this book
                    book_title = book_info.get("title_english", current_path.stem)
                    book_author = book_info.get("author_english", "Unknown")

                    # Look for translated chunks directory
                    safe_folder_name = sanitize_filename(f"{book_title} by {book_author}")
                    book_dir = current_path.parent / safe_folder_name

                    if book_dir.exists() and book_dir.is_dir():
                        # Look for the complete translated text file
                        translated_file_pattern = f"translated_{book_title} by {book_author}.txt"
                        translated_file = book_dir / translated_file_pattern
                    else:
                        translated_file = None

                if translated_file and translated_file.exists():
                    # Create EPUB output path
                    epub_name = sanitize_filename(book_title) + ".epub"
                    epub_path = current_path.parent / epub_name

                    # Get EPUB settings from configuration
                    config = get_config()
                    epub_settings = config.get("epub", {})

                    # Override with command line options
                    if hasattr(args, "epub_title") and args.epub_title:
                        book_title = args.epub_title
                    if hasattr(args, "epub_author") and args.epub_author:
                        book_author = args.epub_author

                    # Build book info for configuration
                    book_info_for_config = {
                        "title_english": book_title,
                        "author_english": book_author,
                        "title_chinese": book_info.get("title_chinese", ""),
                        "author_chinese": book_info.get("author_chinese", ""),
                    }

                    # Create EPUB configuration from book info and settings
                    epub_config = get_epub_config_from_book_info(book_info=book_info_for_config, epub_settings=epub_settings)

                    # Override EPUB config with command line options
                    if hasattr(args, "epub_language") and args.epub_language:
                        epub_config["language"] = args.epub_language
                    if hasattr(args, "no_toc") and args.no_toc:
                        epub_config["generate_toc"] = False
                    if hasattr(args, "no_validate") and args.no_validate:
                        epub_config["validate_chapters"] = False
                    if hasattr(args, "epub_strict") and args.epub_strict:
                        epub_config["strict_mode"] = True

                    # Handle cover image
                    if hasattr(args, "cover") and args.cover:
                        cover_path = Path(args.cover)
                        if cover_path.exists():
                            epub_config["cover_path"] = cover_path
                        else:
                            tolog.warning(f"Cover image not found: {args.cover}")

                    # Handle custom CSS
                    if hasattr(args, "custom_css") and args.custom_css:
                        css_path = Path(args.custom_css)
                        if css_path.exists():
                            epub_config["custom_css"] = css_path.read_text(encoding="utf-8")
                        else:
                            tolog.warning(f"Custom CSS file not found: {args.custom_css}")

                    # Handle metadata
                    if hasattr(args, "epub_metadata") and args.epub_metadata:
                        try:
                            import json

                            metadata = json.loads(args.epub_metadata)
                            epub_config["metadata"] = metadata
                        except json.JSONDecodeError as e:
                            tolog.warning(f"Invalid JSON in epub-metadata: {e}")

                    # Handle validate-only mode
                    if hasattr(args, "validate_only") and args.validate_only:
                        # Just validate, don't create EPUB
                        from .make_epub import create_epub_from_txt_file

                        success, issues = create_epub_from_txt_file(
                            translated_file,
                            output_path=epub_path,
                            title=book_title,
                            author=book_author,
                            cover_path=epub_config.get("cover_path"),
                            generate_toc=epub_config.get("generate_toc", True),
                            validate=True,
                            strict_mode=epub_config.get("strict_mode", False),
                            language=epub_config.get("language", "en"),
                            custom_css=epub_config.get("custom_css"),
                            metadata=epub_config.get("metadata"),
                        )
                        if issues:
                            tolog.info(f"Validation found {len(issues)} issues")
                            for issue in issues:
                                tolog.warning(f"  - {issue}")
                        else:
                            tolog.info("Validation passed with no issues")
                        progress["phases"]["epub"]["status"] = "skipped"
                        progress["phases"]["epub"]["result"] = "validate-only"
                    else:
                        # Create EPUB using the common utility
                        success, issues = create_epub_with_config(
                            txt_file_path=translated_file,
                            output_path=epub_path,
                            config=epub_config,
                            logger=tolog,
                        )

                    if success:
                        progress["phases"]["epub"]["status"] = "completed"
                        progress["phases"]["epub"]["result"] = str(epub_path)
                        tolog.info(f"EPUB created successfully: {epub_path}")

                        if issues:
                            tolog.warning(f"EPUB created with {len(issues)} validation warnings")
                            for issue in issues[:5]:
                                tolog.warning(f"  - {issue}")
                    else:
                        progress["phases"]["epub"]["status"] = "failed"
                        progress["phases"]["epub"]["error"] = f"EPUB creation failed: {'; '.join(issues[:3])}"
                        tolog.error(f"EPUB creation failed with {len(issues)} errors")
                else:
                    # Translated file not found
                    progress["phases"]["epub"]["status"] = "failed"
                    if hasattr(args, "translated") and args.translated:
                        progress["phases"]["epub"]["error"] = "Provided translated file not found"
                        tolog.error(f"Provided translated file not found: {args.translated}")
                    else:
                        progress["phases"]["epub"]["error"] = "No translation directory or file found"
                        tolog.warning("No translation output directory found or translated file missing")

            except Exception as e:
                tolog.error(f"Error during EPUB generation: {e}")
                progress["phases"]["epub"]["status"] = "failed"
                progress["phases"]["epub"]["error"] = str(e)

        # Save progress
        try:
            try:
                with progress_file.open("w") as f:
                    yaml.safe_dump(progress, f)
            except (OSError, yaml.YAMLError) as e:
                tolog.error(f"Error saving batch progress: {e}")
                # Re-raise as this is critical for batch processing
                raise
        except (OSError, yaml.YAMLError) as e:
            tolog.error(f"Error saving progress file: {e}")
            # Continue anyway - progress tracking is not critical

    # Clean up progress file if all phases completed successfully
    all_completed = all(phase["status"] in ("completed", "skipped") for phase in progress["phases"].values())
    if all_completed and progress_file.exists():
        try:
            progress_file.unlink()
            tolog.info("All phases completed, removed progress file")
        except (FileNotFoundError, PermissionError) as e:
            tolog.warning(f"Could not remove progress file: {e}")
            # Not critical - file will be overwritten next time

    return all_completed


def process_batch(args: argparse.Namespace) -> None:
    """Process batch of novel files using unified orchestration"""
    input_path = Path(args.filepath)
    if not input_path.exists() or not input_path.is_dir():
        tolog.error("Batch processing requires an existing directory path.")
        sys.exit(1)

    # Add file locking to prevent concurrent access
    lock_path = Path("translation_batch.lock")
    with filelock.FileLock(str(lock_path)):
        # Load or create batch progress
        progress_file = Path("translation_batch_progress.yml")
        history_file = Path("translations_chronology.yml")

        if progress_file.exists():
            progress = load_safe_yaml(progress_file) or {}
        else:
            progress = {
                "created": dt.datetime.now().isoformat(),
                "input_folder": str(input_path.resolve()),
                "files": [],
            }

        # Populate file list if not resuming
        if not progress.get("files"):
            files_sorted = sorted(input_path.glob("*.txt"), key=lambda x: x.name)
            for file in files_sorted:
                progress["files"].append(
                    {
                        "path": str(file.resolve()),
                        "status": "planned",
                        "end_time": None,
                        "retry_count": 0,
                    }
                )

        max_retries = 3

        # Process files
        for item in progress["files"]:
            if item["status"] == "completed":
                continue
            if item.get("retry_count", 0) >= max_retries:
                tolog.warning(f"Skipping {item['path']} after {max_retries} failed attempts.")
                item["status"] = "failed/skipped"
                continue

            item["status"] = "processing"
            item["start_time"] = dt.datetime.now().isoformat()
            try:
                with progress_file.open("w") as f:
                    yaml.safe_dump(progress, f)
            except (OSError, yaml.YAMLError) as e:
                tolog.error(f"Error saving batch progress: {e}")
                # Re-raise as this is critical for batch processing
                raise

            try:
                tolog.info(f"Processing: {Path(item['path']).name}")

                # Use unified processor
                success = process_novel_unified(Path(item["path"]), args)

                if success:
                    item["status"] = "completed"
                else:
                    raise Exception("One or more phases failed")

            except Exception as e:
                tolog.error(f"Failed to process {item['path']}: {str(e)}")
                item["status"] = "failed/skipped"
                item["error"] = str(e)
                item["retry_count"] = item.get("retry_count", 0) + 1
            finally:
                item["end_time"] = dt.datetime.now().isoformat()
                with progress_file.open("w") as f:
                    yaml.safe_dump(progress, f)

                # Move completed batch to history
                if all(file["status"] in ("completed", "failed/skipped") for file in progress["files"]):
                    try:
                        with history_file.open("a", encoding="utf-8") as f:
                            f.write("---\n")
                            yaml.safe_dump(progress, f, allow_unicode=True)
                    except (OSError, yaml.YAMLError) as e:
                        tolog.error(f"Error writing to history file: {e}")
                        # Continue anyway - history is not critical

                    try:
                        progress_file.unlink()
                    except (FileNotFoundError, PermissionError) as e:
                        tolog.error(f"Error deleting progress file: {e}")
                        # Continue anyway - file will be overwritten next time


###############################################
#               MAIN FUNCTION               #
###############################################


def setup_configuration() -> tuple[ConfigManager, dict[str, Any]]:
    """Load and validate configuration from config file."""
    import argparse

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
    """Set up logging based on configuration."""
    log_level = getattr(logging, config["logging"]["level"], logging.INFO)
    log_format = config["logging"]["format"]

    logging.basicConfig(level=log_level, format=log_format)
    global tolog
    tolog = logging.getLogger(__name__)

    # Set up file logging if enabled
    if config["logging"]["file_enabled"]:
        try:
            file_handler = logging.FileHandler(config["logging"]["file_path"])
            file_handler.setLevel(log_level)
            file_handler.setFormatter(logging.Formatter(log_format))
            tolog.addHandler(file_handler)
        except (OSError, PermissionError) as e:
            tolog.error(f"Failed to set up file logging to {config['logging']['file_path']}: {e}")
            # Continue without file logging

    return tolog


def setup_global_services(config: dict[str, Any]) -> None:
    """Initialize global services like iCloud sync."""
    global icloud_sync
    icloud_sync = ICloudSync(enabled=config["icloud"]["enabled"])
    # Cost tracking is now handled by global_cost_tracker

    # Note: MAXCHARS is handled by cli_translator module separately


def main() -> None:
    global tolog

    # Set up configuration first
    config_manager, config = setup_configuration()

    # Set up logging based on config
    setup_logging(config)

    # Initialize global services
    setup_global_services(config)

    # Warn if colorama is missing
    if cr is None:
        tolog.warning("colorama package not installed. Colored text may not work properly.")

    # Set up signal handling for graceful termination
    def signal_handler(sig: int, frame: Any) -> None:
        tolog.info("Interrupt received. Exiting gracefully.")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    # Parse command-line arguments
    import argparse

    parser = argparse.ArgumentParser(
        description="EnChANT - English-Chinese Automatic Novel Translator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
====================================================================================
USAGE EXAMPLES:
====================================================================================

SINGLE FILE PROCESSING:

  Full processing (rename + translate + EPUB):
    $ enchant-cli "我的小说.txt" --openai-api-key YOUR_KEY

  Translation only (skip renaming, generate EPUB):
    $ enchant-cli "My Novel.txt" --skip-renaming

  EPUB from any translated text file:
    $ enchant-cli --translated "path/to/translated.txt"

  Process renamed file (skip renaming phase):
    $ enchant-cli "Novel Title by Author Name.txt" --skip-renaming

  Just rename files (no translation or EPUB):
    $ enchant-cli "小说.txt" --skip-translating --skip-epub --openai-api-key YOUR_KEY

BATCH PROCESSING:

  Process entire directory:
    $ enchant-cli novels/ --batch --openai-api-key YOUR_KEY

  Resume interrupted batch:
    $ enchant-cli novels/ --batch --resume

  Batch with custom encoding:
    $ enchant-cli novels/ --batch --encoding gb18030

ADVANCED OPTIONS:

  Use remote API (OpenRouter) instead of local:
    $ enchant-cli novel.txt --remote
    $ export OPENROUTER_API_KEY=your_key_here

  Custom configuration file:
    $ enchant-cli novel.txt --config my_config.yml

  Use configuration preset:
    $ enchant-cli novel.txt --preset REMOTE

  Override model settings:
    $ enchant-cli novel.txt --model "gpt-4" --temperature 0.3

  Handle Big5 encoded files:
    $ enchant-cli "traditional_novel.txt" --encoding big5

  Custom chunk size for large files:
    $ enchant-cli huge_novel.txt --max-chars 5000

RENAMING OPTIONS:

  Custom model for renaming:
    $ enchant-cli novel.txt --rename-model "gpt-4" --openai-api-key YOUR_KEY

  Preview renaming without changes:
    $ enchant-cli novel.txt --rename-dry-run --openai-api-key YOUR_KEY

  Adjust metadata extraction:
    $ enchant-cli novel.txt --kb-to-read 50 --rename-temperature 0.5

EPUB OPTIONS:

  Custom title and author:
    $ enchant-cli --translated novel.txt --epub-title "My Title" --epub-author "My Author"

  Add cover image:
    $ enchant-cli --translated novel.txt --cover "cover.jpg"

  Custom CSS styling:
    $ enchant-cli --translated novel.txt --custom-css "style.css"

  Add metadata:
    $ enchant-cli --translated novel.txt --epub-metadata '{"publisher": "My Pub", "series": "My Series"}'

  Validate chapters only:
    $ enchant-cli --translated novel.txt --validate-only

  Disable TOC generation:
    $ enchant-cli --translated novel.txt --no-toc

  Strict validation mode:
    $ enchant-cli --translated novel.txt --epub-strict

PHASE COMBINATIONS:

  Rename only:
    $ enchant-cli "中文小说.txt" --skip-translating --skip-epub --openai-api-key YOUR_KEY

  Translate only (no rename, no EPUB):
    $ enchant-cli "Already Named Novel.txt" --skip-renaming --skip-epub

  EPUB only from translation directory:
    $ enchant-cli "Novel by Author.txt" --skip-renaming --skip-translating

  EPUB from external translated file:
    $ enchant-cli --translated "/path/to/translation.txt"

====================================================================================
PROCESSING PHASES:
====================================================================================
  1. RENAMING: Extract metadata and rename files (requires OpenRouter API key)
     Options: --rename-model, --rename-temperature, --kb-to-read, --rename-dry-run

  2. TRANSLATION: Translate Chinese text to English
     Options: --remote, --max-chars, --resume, --model, --temperature

  3. EPUB: Generate EPUB from translated novel
     Options: --epub-title, --epub-author, --cover, --epub-language, --custom-css,
              --epub-metadata, --no-toc, --no-validate, --epub-strict, --validate-only

SKIP FLAGS:
  --skip-renaming     Skip phase 1 (file renaming)
  --skip-translating  Skip phase 2 (translation)
  --skip-epub        Skip phase 3 (EPUB generation)

BEHAVIOR:
  • Each phase can be independently skipped
  • Skipped phases preserve existing data
  • --resume works with all phase combinations
  • Progress saved for batch operations
  • --translated allows EPUB from any text file

API KEYS:
  • Renaming requires OpenRouter API key (--openai-api-key or OPENROUTER_API_KEY env)
  • Translation uses local LM Studio by default (--remote for OpenRouter)
  • Remote translation requires OPENROUTER_API_KEY environment variable
""",
    )
    parser.add_argument(
        "filepath",
        type=str,
        nargs="?",
        help="Path to Chinese novel text file (single mode) or directory containing novels (batch mode). Optional when using --translated with --skip-renaming and --skip-translating",
    )

    parser.add_argument(
        "--config",
        type=str,
        default="enchant_config.yml",
        help="Path to configuration file (default: enchant_config.yml)",
    )

    parser.add_argument(
        "--preset",
        type=str,
        help="Configuration preset name (LOCAL, REMOTE, or custom preset)",
    )

    parser.add_argument(
        "--encoding",
        type=str,
        default=config["text_processing"]["default_encoding"],
        help=f"Character encoding of input files. Common: utf-8, gb2312, gb18030, big5 (default: {config['text_processing']['default_encoding']})",
    )

    parser.add_argument(
        "--max-chars",
        type=int,
        default=config["text_processing"]["max_chars_per_chunk"],
        help=f"Maximum characters per translation chunk. Affects API usage and memory (default: {config['text_processing']['max_chars_per_chunk']})",
    )

    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume interrupted translation. Single: continues from last chunk. Batch: uses progress file",
    )

    parser.add_argument(
        "--epub",
        action="store_true",
        help="Generate EPUB file after translation completes. Creates formatted e-book with table of contents",
    )

    parser.add_argument(
        "--batch",
        action="store_true",
        help="Batch mode: process all .txt files in the specified directory. Tracks progress automatically",
    )

    parser.add_argument(
        "--remote",
        action="store_true",
        help="Use remote OpenRouter API instead of local LM Studio. Requires OPENROUTER_API_KEY environment variable",
    )

    # Skip flags for different phases
    parser.add_argument("--skip-renaming", action="store_true", help="Skip the file renaming phase")
    parser.add_argument("--skip-translating", action="store_true", help="Skip the translation phase")
    parser.add_argument("--skip-epub", action="store_true", help="Skip the EPUB generation phase")

    # Translated file path for direct EPUB generation
    parser.add_argument(
        "--translated",
        type=str,
        help="Path to already translated text file for direct EPUB generation. Automatically implies --skip-renaming and --skip-translating. Makes filepath argument optional",
    )

    # API key for renaming (if not skipped)
    parser.add_argument(
        "--openai-api-key",
        type=str,
        help="OpenRouter API key for novel renaming (can also use OPENROUTER_API_KEY env var)",
    )

    # Add configuration override arguments
    parser.add_argument(
        "--timeout",
        type=int,
        help="API request timeout in seconds (overrides config/preset)",
    )

    parser.add_argument(
        "--max-retries",
        type=int,
        help="Maximum retry attempts for failed requests (overrides config/preset)",
    )

    parser.add_argument("--model", type=str, help="AI model name (overrides config/preset)")

    parser.add_argument("--endpoint", type=str, help="API endpoint URL (overrides config/preset)")

    parser.add_argument(
        "--temperature",
        type=float,
        help="AI model temperature (overrides config/preset)",
    )

    parser.add_argument(
        "--max-tokens",
        type=int,
        help="Maximum tokens per request (overrides config/preset)",
    )

    parser.add_argument(
        "--double-pass",
        action="store_true",
        help="Enable double-pass translation (overrides config/preset)",
    )

    # Renaming phase options
    parser.add_argument(
        "--rename-model",
        type=str,
        help="AI model for renaming phase (overrides config/preset)",
    )

    parser.add_argument(
        "--rename-temperature",
        type=float,
        help="Temperature for renaming phase (overrides config/preset)",
    )

    parser.add_argument(
        "--kb-to-read",
        type=int,
        default=35,
        help="KB to read from file start for metadata extraction (default: 35)",
    )

    parser.add_argument(
        "--rename-workers",
        type=int,
        help="Number of parallel workers for batch renaming (default: CPU count)",
    )

    parser.add_argument(
        "--rename-dry-run",
        action="store_true",
        help="Preview what files would be renamed without actually renaming them",
    )

    # EPUB generation options
    parser.add_argument(
        "--epub-title",
        type=str,
        help="Override book title for EPUB",
    )

    parser.add_argument(
        "--epub-author",
        type=str,
        help="Override author name for EPUB",
    )

    parser.add_argument(
        "--cover",
        type=str,
        help="Path to cover image file (.jpg/.jpeg/.png)",
    )

    parser.add_argument(
        "--epub-language",
        type=str,
        default="en",
        help="Language code for the EPUB (default: en)",
    )

    parser.add_argument(
        "--no-toc",
        action="store_true",
        help="Disable table of contents generation",
    )

    parser.add_argument(
        "--no-validate",
        action="store_true",
        help="Skip chapter validation",
    )

    parser.add_argument(
        "--epub-strict",
        action="store_true",
        help="Enable strict mode (abort on validation issues)",
    )

    parser.add_argument(
        "--custom-css",
        type=str,
        help="Path to custom CSS file for EPUB styling",
    )

    parser.add_argument(
        "--epub-metadata",
        type=str,
        help='Additional metadata in JSON format: {"publisher": "...", "description": "...", "series": "...", "series_index": "..."}',
    )

    parser.add_argument(
        "--json-log",
        type=str,
        help="Enable JSON logging for chapter validation issues (path to log file)",
    )

    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Just scan and validate chapters without creating EPUB",
    )

    args = parser.parse_args()

    # Update config with preset and command-line arguments
    config = config_manager.update_with_args(args)

    # If --translated is provided, automatically set skip flags
    if args.translated:
        args.skip_renaming = True
        args.skip_translating = True
        tolog.info("--translated option provided, automatically skipping renaming and translation phases")

        # Validate that the translated file exists
        translated_path = Path(args.translated)
        if not translated_path.exists():
            parser.error(f"Translated file not found: {args.translated}")
        if not translated_path.is_file():
            parser.error(f"Translated path is not a file: {args.translated}")

    # Check if filepath is required
    if not args.filepath:
        # filepath is optional when using --translated
        if not args.translated:
            parser.error("filepath is required unless using --translated option")

    # Process files using unified orchestration
    if args.batch:
        process_batch(args)
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
        success = process_novel_unified(file_path, args)

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
