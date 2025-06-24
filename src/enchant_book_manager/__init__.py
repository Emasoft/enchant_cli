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

"""
EnChANT - English-Chinese Automatic Novel Translator

A comprehensive Chinese novel translation and EPUB generation system.
"""

__version__ = "1.0.0"
__author__ = "Emasoft"
__email__ = "713559+Emasoft@users.noreply.github.com"
__license__ = "Apache-2.0"

# Main modules
from . import cli_translator
from . import translation_service
from . import renamenovels
from . import make_epub
from . import enchant_cli

# Utility modules
from . import common_constants
from . import common_text_utils
from . import common_yaml_utils
from . import common_utils
from . import common_file_utils
from . import common_print_utils

# Support modules
from . import config_manager
from . import cost_tracker
from . import icloud_sync
from . import epub_builder
from . import epub_utils

# New refactored modules
from . import models
from . import text_processor
from . import text_splitter
from . import file_handler
from . import book_importer
from . import translation_orchestrator
from . import batch_processor
from . import cost_logger

__all__ = [
    "cli_translator",
    "translation_service",
    "renamenovels",
    "make_epub",
    "enchant_cli",
    "common_constants",
    "common_text_utils",
    "common_yaml_utils",
    "common_utils",
    "common_file_utils",
    "common_print_utils",
    "config_manager",
    "cost_tracker",
    "icloud_sync",
    "epub_builder",
    "epub_utils",
    "models",
    "text_processor",
    "text_splitter",
    "file_handler",
    "book_importer",
    "translation_orchestrator",
    "batch_processor",
    "cost_logger",
]
