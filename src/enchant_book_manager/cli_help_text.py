#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
# - Created new module to hold CLI help text
# - Extracted from cli_parser.py to reduce file size
#

"""
cli_help_text.py - Help text and usage examples for EnChANT CLI
===============================================================

Contains the detailed help text and usage examples for the command-line interface.
"""


def get_epilog_text() -> str:
    """Get the epilog help text for the argument parser.

    Returns:
        The formatted epilog text with usage examples
    """
    return """
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
"""
