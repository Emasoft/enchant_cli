#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Test for cloning a GitHub repo and building it with uv."""

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import pytest

from test_config import should_skip_test, get_timeout


class TestProjectBuild(unittest.TestCase):
    """Test cloning and building a project with uv."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp(prefix="enchant_test_")
        self.original_dir = os.getcwd()

    def tearDown(self):
        """Clean up test environment."""
        os.chdir(self.original_dir)
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    @pytest.mark.timeout(get_timeout() * 2)  # Double timeout for clone+build
    @pytest.mark.skipif(should_skip_test("heavy"), reason="Skipping heavy tests")
    def test_clone_and_build_enchant_project(self):
        """Test cloning the EnChANT project and building it."""
        os.chdir(self.temp_dir)

        # Clone the repository (using local path for testing)
        project_root = Path(__file__).parent.parent
        test_project_dir = Path(self.temp_dir) / "enchant_test"

        # Copy the project to simulate a clone
        shutil.copytree(
            project_root,
            test_project_dir,
            ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc", ".venv", "htmlcov"),
        )

        os.chdir(test_project_dir)

        # Test 1: Check if uv is available
        result = subprocess.run(["uv", "--version"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, "uv should be installed")

        # Test 2: Initialize virtual environment
        result = subprocess.run(["uv", "venv"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, f"Failed to create venv: {result.stderr}")
        self.assertTrue(Path(".venv").exists(), "Virtual environment should be created")

        # Test 3: Sync dependencies
        result = subprocess.run(["uv", "sync"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, f"Failed to sync dependencies: {result.stderr}")

        # Test 4: Build the project
        result = subprocess.run(["uv", "build"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, f"Failed to build project: {result.stderr}")

        # Verify build artifacts
        dist_dir = Path("dist")
        self.assertTrue(dist_dir.exists(), "dist directory should exist")

        # Check for wheel and sdist
        wheels = list(dist_dir.glob("*.whl"))
        sdists = list(dist_dir.glob("*.tar.gz"))

        self.assertTrue(len(wheels) > 0, "At least one wheel should be built")
        self.assertTrue(len(sdists) > 0, "At least one sdist should be built")

        # Test 5: Install the built package
        wheel_path = wheels[0]
        result = subprocess.run(["uv", "pip", "install", str(wheel_path)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, f"Failed to install wheel: {result.stderr}")

        # Test 6: Verify the package can be imported
        result = subprocess.run(
            [
                "uv",
                "run",
                "python",
                "-c",
                "import enchant_book_manager; print(enchant_book_manager.__version__)",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, f"Failed to import package: {result.stderr}")
        self.assertTrue(result.stdout.strip(), "Should output version")

    @pytest.mark.timeout(get_timeout())
    def test_uv_project_commands(self):
        """Test various uv project commands."""
        os.chdir(self.temp_dir)

        # Test uv init
        result = subprocess.run(["uv", "init", "test_project", "--lib"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, f"Failed to init project: {result.stderr}")

        test_project = Path(self.temp_dir) / "test_project"
        self.assertTrue(test_project.exists(), "Project directory should be created")

        os.chdir(test_project)

        # Check created files
        expected_files = ["pyproject.toml", "README.md", "src/test_project/__init__.py"]
        for file in expected_files:
            self.assertTrue(Path(file).exists(), f"{file} should exist")

        # Test adding a dependency
        result = subprocess.run(["uv", "add", "click"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, f"Failed to add dependency: {result.stderr}")

        # Verify dependency was added
        with open("pyproject.toml", "r") as f:
            content = f.read()
            self.assertIn("click", content, "click should be in dependencies")

        # Test building the new project
        result = subprocess.run(["uv", "build"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, f"Failed to build new project: {result.stderr}")

    @pytest.mark.skipif(not os.environ.get("TEST_GITHUB_REPO"), reason="TEST_GITHUB_REPO not set")
    @pytest.mark.timeout(get_timeout() * 3)  # Triple timeout for network operations
    def test_clone_real_github_repo(self):
        """Test cloning and building a real GitHub repository."""
        repo_url = os.environ.get("TEST_GITHUB_REPO", "https://github.com/example/repo.git")

        os.chdir(self.temp_dir)

        # Clone the repository
        result = subprocess.run(["git", "clone", repo_url, "cloned_repo"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, f"Failed to clone repo: {result.stderr}")

        os.chdir("cloned_repo")

        # Set up and build
        commands = [["uv", "venv"], ["uv", "sync"], ["uv", "build"]]

        for cmd in commands:
            result = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, f"Command {' '.join(cmd)} failed: {result.stderr}")


if __name__ == "__main__":
    unittest.main()
