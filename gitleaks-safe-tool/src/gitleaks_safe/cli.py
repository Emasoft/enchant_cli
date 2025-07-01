#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
CLI entry point for gitleaks-safe wrapper
"""

import os
import sys

import click

from .wrapper import GitleaksWrapper


@click.command(
    context_settings=dict(
        ignore_unknown_options=True,
        allow_extra_args=True,
    )
)
@click.pass_context
def main(ctx):
    """Memory-safe wrapper for gitleaks with multi-instance support.

    All arguments are passed through to gitleaks.

    Examples:

        gitleaks-safe detect --source .

        gitleaks-safe protect --staged

        GITLEAKS_TIMEOUT=300 gitleaks-safe detect --verbose
    """
    # Get configuration from environment
    timeout = int(os.environ.get("GITLEAKS_TIMEOUT", "120"))
    verbose = os.environ.get("GITLEAKS_VERBOSE", "false").lower() == "true"
    max_retries = int(os.environ.get("GITLEAKS_RETRIES", "1"))

    # Create wrapper and run
    wrapper = GitleaksWrapper(timeout=timeout, verbose=verbose, max_retries=max_retries)

    # Pass all arguments to gitleaks
    exit_code = wrapper.run(ctx.args)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
