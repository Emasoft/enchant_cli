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

"""
Common print utilities for console output with rich formatting support.
"""

import builtins
import re
from typing import Any

# Try to import rich for enhanced printing
try:
    from rich import print

    rich_available = True
except ImportError:
    # Use standard print if rich isn't available
    print = builtins.print  # type: ignore[assignment]
    rich_available = False


def safe_print(*args: Any, **kwargs: Any) -> None:
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
        clean_text = re.sub(r"\[/?[^]]+\]", "", text)
        builtins.print(clean_text)
