#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
model_pricing.py - Model pricing calculation and tracking

DEPRECATED: This module is no longer used. The project now uses the unified 
cost_tracker.py module which gets cost information directly from OpenRouter API 
responses instead of fetching pricing data from BerriAI/litellm.

This file is kept for reference only and will be removed in a future version.
All cost tracking should use global_cost_tracker from cost_tracker.py instead.
"""

import json
import logging
import requests
from typing import Dict, Optional, Tuple
from pathlib import Path
from datetime import datetime
import threading
from tenacity import retry, stop_after_attempt, wait_exponential

class ModelPricingManager:
    """Manages model pricing information and cost calculations."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize pricing manager."""
        self.logger = logger or logging.getLogger(__name__)
        self.pricing_data = {}
        self.cumulative_cost = 0.0
        self.cost_lock = threading.Lock()
        self.session_costs = []  # Track individual costs for reporting
        self._load_pricing_data()
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    def _load_pricing_data(self):
        """Load model pricing data from LiteLLM database."""
        urls = [
            'https://raw.githubusercontent.com/BerriAI/litellm/main/model_prices_and_context_window.json',
            'https://cdn.jsdelivr.net/gh/BerriAI/litellm@main/model_prices_and_context_window.json',
            'https://raw.fastgit.org/BerriAI/litellm/main/model_prices_and_context_window.json'
        ]
        
        for url in urls:
            try:
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                self.pricing_data = response.json()
                self.logger.info(f"Loaded model pricing data from {url}")
                return
            except Exception as e:
                self.logger.warning(f"Failed to load pricing from {url}: {e}")
        
        # Load from local cache if available
        cache_path = Path("model_pricing_cache.json")
        if cache_path.exists():
            try:
                with open(cache_path, 'r') as f:
                    self.pricing_data = json.load(f)
                self.logger.info("Loaded pricing data from local cache")
            except Exception as e:
                self.logger.error(f"Failed to load local pricing cache: {e}")
                self.pricing_data = {}
        else:
            self.logger.warning("No pricing data available")
    
    def save_pricing_cache(self):
        """Save pricing data to local cache."""
        if self.pricing_data:
            try:
                with open("model_pricing_cache.json", 'w') as f:
                    json.dump(self.pricing_data, f, indent=2)
                self.logger.debug("Saved pricing data to cache")
            except Exception as e:
                self.logger.error(f"Failed to save pricing cache: {e}")
    
    def calculate_cost(self, model: str, prompt_tokens: int, 
                      completion_tokens: int) -> Tuple[float, Dict[str, float]]:
        """
        Calculate cost for a model usage.
        
        Args:
            model: Model name
            prompt_tokens: Number of input tokens
            completion_tokens: Number of output tokens
            
        Returns:
            Tuple of (total_cost, cost_breakdown)
        """
        # Handle model name variations
        model_key = self._normalize_model_name(model)
        
        if model_key not in self.pricing_data:
            self.logger.warning(f"No pricing data for model: {model}")
            return 0.0, {}
        
        pricing = self.pricing_data[model_key]
        
        # Get costs per token
        input_cost_per_token = pricing.get('input_cost_per_token', 0.0)
        output_cost_per_token = pricing.get('output_cost_per_token', 0.0)
        
        # Calculate costs
        input_cost = prompt_tokens * input_cost_per_token
        output_cost = completion_tokens * output_cost_per_token
        total_cost = input_cost + output_cost
        
        # Update cumulative cost
        with self.cost_lock:
            self.cumulative_cost += total_cost
            self.session_costs.append({
                'timestamp': datetime.now().isoformat(),
                'model': model,
                'prompt_tokens': prompt_tokens,
                'completion_tokens': completion_tokens,
                'total_tokens': prompt_tokens + completion_tokens,
                'input_cost': input_cost,
                'output_cost': output_cost,
                'total_cost': total_cost
            })
        
        return total_cost, {
            'input_cost': input_cost,
            'output_cost': output_cost,
            'input_cost_per_token': input_cost_per_token,
            'output_cost_per_token': output_cost_per_token
        }
    
    def _normalize_model_name(self, model: str) -> str:
        """Normalize model name for pricing lookup."""
        # Common model name mappings
        mappings = {
            'gpt-4o-mini': 'gpt-4o-mini',
            'gpt-4o': 'gpt-4o-2024-08-06',
            'gpt-4': 'gpt-4',
            'gpt-3.5-turbo': 'gpt-3.5-turbo',
            'deepseek-chat': 'deepseek/deepseek-chat',
            'deepseek/deepseek-chat': 'deepseek/deepseek-chat',
            'deepseek/deepseek-r1:nitro': 'deepseek/deepseek-chat',  # Map r1:nitro to chat pricing
            'local-model': 'local-model',  # For local models, no cost
        }
        
        # Direct mapping
        if model in mappings:
            return mappings[model]
        
        # Try to find in pricing data
        for key in self.pricing_data:
            if model.lower() in key.lower() or key.lower() in model.lower():
                return key
        
        return model
    
    def get_session_summary(self) -> Dict:
        """Get summary of costs for current session."""
        with self.cost_lock:
            if not self.session_costs:
                return {
                    'total_cost': 0.0,
                    'total_requests': 0,
                    'total_tokens': 0,
                    'by_model': {}
                }
            
            by_model = {}
            for cost in self.session_costs:
                model = cost['model']
                if model not in by_model:
                    by_model[model] = {
                        'requests': 0,
                        'total_tokens': 0,
                        'total_cost': 0.0
                    }
                by_model[model]['requests'] += 1
                by_model[model]['total_tokens'] += cost['total_tokens']
                by_model[model]['total_cost'] += cost['total_cost']
            
            return {
                'total_cost': self.cumulative_cost,
                'total_requests': len(self.session_costs),
                'total_tokens': sum(c['total_tokens'] for c in self.session_costs),
                'by_model': by_model
            }
    
    def reset_session(self):
        """Reset session costs."""
        with self.cost_lock:
            self.cumulative_cost = 0.0
            self.session_costs = []
    
    def save_session_report(self, filepath: Optional[Path] = None):
        """Save detailed session report."""
        if filepath is None:
            filepath = Path(f"cost_report_{datetime.now():%Y%m%d_%H%M%S}.json")
        
        summary = self.get_session_summary()
        summary['details'] = self.session_costs
        
        try:
            with open(filepath, 'w') as f:
                json.dump(summary, f, indent=2)
            self.logger.info(f"Saved cost report to {filepath}")
        except Exception as e:
            self.logger.error(f"Failed to save cost report: {e}")
    
    def format_cost_summary(self) -> str:
        """Format cost summary for display."""
        summary = self.get_session_summary()
        
        lines = [
            "=== Cost Summary ===",
            f"Total Cost: ${summary['total_cost']:.6f}",
            f"Total Requests: {summary['total_requests']}",
            f"Total Tokens: {summary['total_tokens']:,}",
            ""
        ]
        
        if summary['by_model']:
            lines.append("By Model:")
            for model, stats in summary['by_model'].items():
                lines.append(f"  {model}:")
                lines.append(f"    Requests: {stats['requests']}")
                lines.append(f"    Tokens: {stats['total_tokens']:,}")
                lines.append(f"    Cost: ${stats['total_cost']:.6f}")
        
        return "\n".join(lines)


# Global instance
_pricing_manager = None

def get_pricing_manager() -> ModelPricingManager:
    """Get or create global pricing manager."""
    global _pricing_manager
    if _pricing_manager is None:
        _pricing_manager = ModelPricingManager()
    return _pricing_manager

def calculate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Calculate cost for model usage."""
    cost, _ = get_pricing_manager().calculate_cost(model, prompt_tokens, completion_tokens)
    return cost

def get_cost_summary() -> str:
    """Get formatted cost summary."""
    return get_pricing_manager().format_cost_summary()