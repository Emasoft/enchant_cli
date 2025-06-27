#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# syntax=docker/dockerfile:1.10
# Base image with Python 3.12
FROM python:3.12-slim

# Install uv
# The installer requires curl (and certificates) to download the release archive
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Download the latest installer
ADD https://astral.sh/uv/install.sh /uv-installer.sh

# Run the installer then remove it
RUN sh /uv-installer.sh && rm /uv-installer.sh

# Ensure uv is in the PATH
ENV PATH="/root/.local/bin:$PATH"

# Verify uv installation
RUN uv --version

# Set up the app directory
WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Copy from the cache instead of linking since it's a mounted volume
ENV UV_LINK_MODE=copy

# Install the project's dependencies using the lockfile and settings
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

# Copy the project files
COPY pyproject.toml uv.lock ./
COPY src/ ./src/
COPY tests/ ./tests/
COPY .github/pytest.ini ./.github/

# Sync the project with dev dependencies for testing
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --group dev

# Set environment variables for testing
ENV PYTHONPATH="/app/src:$PYTHONPATH"
ENV SKIP_LOCAL_MODE_TESTS=true

# Default command runs tests
CMD ["uv", "run", "pytest", "tests", "-c", ".github/pytest.ini", "--cov=src/enchant_book_manager", "--cov-report=term", "--cov-report=html", "-v"]
