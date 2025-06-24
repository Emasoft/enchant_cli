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
cost_tracker.py - Unified cost tracking module for OpenRouter API responses
"""

import threading
from typing import Any, Optional
import logging

logger = logging.getLogger(__name__)


class CostTracker:
    """Thread-safe cost tracking for API usage"""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.total_cost = 0.0
        self.total_tokens = 0
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0
        self.request_count = 0

    def track_usage(self, usage: dict[str, Any], file_path: str | None = None) -> float:
        """
        Track API usage from OpenRouter response.

        Args:
            usage: Usage dict from API response
            file_path: Optional file path for logging

        Returns:
            Cost for this request
        """
        with self._lock:
            # OpenRouter provides cost directly
            cost = float(usage.get("cost", 0.0))
            prompt_tokens = int(usage.get("prompt_tokens", 0))
            completion_tokens = int(usage.get("completion_tokens", 0))
            total_tokens = int(usage.get("total_tokens", 0))

            if cost > 0:
                self.total_cost += cost
                self.request_count += 1
                self.total_tokens += total_tokens
                self.total_prompt_tokens += prompt_tokens
                self.total_completion_tokens += completion_tokens

                if file_path:
                    logger.info(f"File '{file_path}' used {total_tokens} tokens. Cost: ${cost:.6f}")
                else:
                    logger.info(f"Request used {total_tokens} tokens. Cost: ${cost:.6f}")

                logger.info(f"Cumulative cost: ${self.total_cost:.6f}")
                logger.info(f"Total requests so far: {self.request_count}")
            else:
                # Still track token usage even without cost
                self.request_count += 1
                self.total_tokens += total_tokens
                self.total_prompt_tokens += prompt_tokens
                self.total_completion_tokens += completion_tokens
                logger.warning("Cost information not available in response")

            return cost

    def get_summary(self) -> dict[str, Any]:
        """Get cost tracking summary"""
        with self._lock:
            return {
                "total_cost": self.total_cost,
                "total_tokens": self.total_tokens,
                "total_prompt_tokens": self.total_prompt_tokens,
                "total_completion_tokens": self.total_completion_tokens,
                "request_count": self.request_count,
                "average_cost_per_request": self.total_cost / self.request_count if self.request_count > 0 else 0,
            }

    def reset(self) -> None:
        """Reset all counters"""
        with self._lock:
            self.total_cost = 0.0
            self.total_tokens = 0
            self.total_prompt_tokens = 0
            self.total_completion_tokens = 0
            self.request_count = 0


# Global cost tracker instance
global_cost_tracker = CostTracker()
