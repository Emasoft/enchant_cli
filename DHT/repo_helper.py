#!/usr/bin/env python3
"""
Enhanced GitHub repository management and configuration utilities.

This module provides comprehensive functions to:
- Configure and manage GitHub repositories
- Set up repository secrets for CI/CD workflows
- Validate repository structure and connectivity
- Check remote configuration and branch tracking
- Verify GitHub authentication
- Manage GitHub workflow triggers
- Configure branch protection
- Handle repository initialization with proper defaults

Features:
- Auto-detection of repository settings from multiple sources
- Support for multiple repository configurations
- Smart URL parsing for different git providers
- Comprehensive secret management
- Branch tracking and protection verification
- Integration with GitHub CLI
- Recovery handling for common GitHub issues

Usage:
    python -m helpers.github.repo_helper --check-repo
    python -m helpers.github.repo_helper --setup-secrets
    python -m helpers.github.repo_helper --update-remote
    python -m helpers.github.repo_helper --verify-workflows
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path


# ANSI color codes for prettier output
COLORS = {
    "RED": "\033[0;31m",
    "GREEN": "\033[0;32m",
    "YELLOW": "\033[0;33m",
    "BLUE": "\033[0;34m",
    "MAGENTA": "\033[0;35m",
    "CYAN": "\033[0;36m",
    "RESET": "\033[0m",
    "BOLD": "\033[1m"
}


def print_colored(message, color=None, bold=False):
    """Print a message with optional ANSI color formatting."""
    color_code = COLORS.get(color.upper(), "") if color else ""
    bold_code = COLORS["BOLD"] if bold else ""
    reset_code = COLORS["RESET"] if color or bold else ""
    print(f"{bold_code}{color_code}{message}{reset_code}")


def print_info(message):
    """Print an informational message."""
    print_colored(f"ℹ️ {message}", "BLUE")


def print_success(message):
    """Print a success message."""
    print_colored(f"✅ {message}", "GREEN")


def print_warning(message):
    """Print a warning message."""
    print_colored(f"⚠️ {message}", "YELLOW")


def print_error(message, exit_code=None):
    """Print an error message and optionally exit with the given code."""
    print_colored(f"❌ {message}", "RED", bold=True)
    if exit_code is not None:
        sys.exit(exit_code)


def check_gh_cli_installed():
    """
    Check if GitHub CLI is installed and properly authenticated.
    
    Returns:
        bool: True if GitHub CLI is installed and authenticated, False otherwise
    """
    try:
        # Check if gh is installed
        result = subprocess.run(
            ["gh", "--version"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        
        if result.returncode != 0:
            print_error("GitHub CLI (gh) is not installed. Install from: https://cli.github.com")
            return False
        
        # Check if authenticated
        result = subprocess.run(
            ["gh", "auth", "status"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        
        if result.returncode != 0:
            print_error("Not authenticated with GitHub CLI. Run 'gh auth login' first.")
            return False
        
        return True
    except Exception:
        print_error("Error checking GitHub CLI installation.")
        return False


def get_repo_info():
    """
    Auto-detect information about the current GitHub repository from multiple sources.
    
    Returns:
        dict: Repository information including owner, name, full name, and URLs
    """
    repo_info = {
        "owner": None,
        "name": None,
        "full_name": None,
        "https_url": None,
        "ssh_url": None,
        "default_branch": "main",  # Default to main, will update if found
        "is_initialized": False
    }
    
    # First, check if we're actually in a git repo
    try:
        subprocess.check_output(
            ["git", "rev-parse", "--is-inside-work-tree"],
            stderr=subprocess.DEVNULL,
            universal_newlines=True
        )
        repo_info["is_initialized"] = True
    except subprocess.CalledProcessError:
        # Not a git repo yet, just return the basic info with initialized=False
        repo_info["name"] = os.path.basename(os.getcwd())
        return repo_info
    
    # Try to get repository info from git config
    try:
        origin_url = subprocess.check_output(
            ["git", "config", "--get", "remote.origin.url"],
            stderr=subprocess.DEVNULL,
            universal_newlines=True
        ).strip()
        
        # Extract owner and repo from the URL
        if "github.com" in origin_url:
            # Store the original URL
            if origin_url.startswith("git@"):
                repo_info["ssh_url"] = origin_url
                # Convert SSH to HTTPS format
                https_url = origin_url.replace("git@github.com:", "https://github.com/")
                if https_url.endswith(".git"):
                    https_url = https_url[:-4]
                repo_info["https_url"] = https_url
            else:
                repo_info["https_url"] = origin_url.replace(".git", "")
                # Convert HTTPS to SSH format
                ssh_url = origin_url.replace("https://github.com/", "git@github.com:")
                if not ssh_url.endswith(".git"):
                    ssh_url += ".git"
                repo_info["ssh_url"] = ssh_url
            
            # Extract owner/name from either format
            match = re.search(r"github\.com[:/]([^/]+)/([^/.]+)", origin_url)
            if match:
                repo_info["owner"] = match.group(1)
                repo_info["name"] = match.group(2)
                repo_info["full_name"] = f"{repo_info['owner']}/{repo_info['name']}"
    except subprocess.CalledProcessError:
        pass
    
    # If we still don't have the info, try to extract from pyproject.toml
    if not repo_info["full_name"] and Path("pyproject.toml").exists():
        try:
            with open("pyproject.toml", "r") as f:
                content = f.read()
                homepage_match = re.search(r'Homepage.*=.*"https://github.com/([^"]*)"', content)
                if homepage_match and "/" in homepage_match.group(1):
                    full_name = homepage_match.group(1)
                    owner, name = full_name.split("/", 1)
                    repo_info["owner"] = owner
                    repo_info["name"] = name
                    repo_info["full_name"] = full_name
                    repo_info["https_url"] = f"https://github.com/{full_name}"
                    repo_info["ssh_url"] = f"git@github.com:{full_name}.git"
        except Exception:
            pass
    
    # Try GitHub CLI as another fallback
    if not repo_info["full_name"] and check_gh_cli_installed():
        try:
            result = subprocess.check_output(
                ["gh", "repo", "view", "--json", "owner,name,defaultBranchRef"],
                stderr=subprocess.DEVNULL,
                universal_newlines=True
            )
            data = json.loads(result)
            repo_info["owner"] = data["owner"]["login"]
            repo_info["name"] = data["name"]
            repo_info["full_name"] = f"{repo_info['owner']}/{repo_info['name']}"
            repo_info["https_url"] = f"https://github.com/{repo_info['full_name']}"
            repo_info["ssh_url"] = f"git@github.com:{repo_info['full_name']}.git"
            
            # Get default branch if available
            if "defaultBranchRef" in data and data["defaultBranchRef"] and "name" in data["defaultBranchRef"]:
                repo_info["default_branch"] = data["defaultBranchRef"]["name"]
        except (subprocess.CalledProcessError, json.JSONDecodeError, KeyError):
            pass
    
    # Last resort: use current directory name as repo name
    if not repo_info["name"]:
        repo_info["name"] = os.path.basename(os.getcwd())
    
    # Try to get default branch from local git if we still don't have it
    if repo_info["is_initialized"] and repo_info["default_branch"] == "main":
        try:
            # Check if there's a local main branch
            result = subprocess.run(
                ["git", "show-ref", "--verify", "--quiet", "refs/heads/main"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            if result.returncode == 0:
                repo_info["default_branch"] = "main"
            else:
                # Check for master branch
                result = subprocess.run(
                    ["git", "show-ref", "--verify", "--quiet", "refs/heads/master"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                if result.returncode == 0:
                    repo_info["default_branch"] = "master"
        except Exception:
            pass
    
    return repo_info


def check_repo_exists(repo_full_name=None):
    """
    Check if a GitHub repository exists using the GitHub CLI.
    
    Args:
        repo_full_name: The full repository name (owner/repo)
        
    Returns:
        bool: True if the repository exists, False otherwise
    """
    if not check_gh_cli_installed():
        return False
        
    if not repo_full_name:
        repo_info = get_repo_info()
        repo_full_name = repo_info["full_name"]
        
    if not repo_full_name:
        print_error("Could not determine repository name")
        return False
    
    try:
        result = subprocess.run(
            ["gh", "repo", "view", repo_full_name],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        return result.returncode == 0
    except Exception:
        return False


def create_repo(repo_name=None, private=True, description=None, source=None):
    """
    Create a new GitHub repository with the GitHub CLI.
    
    Args:
        repo_name (str, optional): The repository name. If not provided, uses current directory name.
        private (bool): Whether the repository should be private
        description (str, optional): Optional repository description
        source (str, optional): Path to source directory for the repository
        
    Returns:
        bool: True if successful, False otherwise
    """
    if not check_gh_cli_installed():
        return False
    
    if not repo_name:
        repo_name = os.path.basename(os.getcwd())
    
    # Check if the repository already exists
    repo_info = get_repo_info()
    if repo_info["full_name"] and check_repo_exists(repo_info["full_name"]):
        print_warning(f"Repository {repo_info['full_name']} already exists.")
        return True
    
    try:
        cmd = ["gh", "repo", "create", repo_name]
        
        if private:
            cmd.append("--private")
        else:
            cmd.append("--public")
            
        if description:
            cmd.extend(["--description", description])
            
        if source:
            cmd.extend(["--source", source])
        
        # Add --remote=origin so it sets up the remote
        cmd.extend(["--remote", "origin"])
        
        result = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode == 0:
            print_success(f"Repository {repo_name} created successfully")
            return True
        else:
            print_error(f"Error creating repository: {result.stderr.decode()}")
            return False
    except subprocess.CalledProcessError as e:
        # Check if error is because repo already exists
        if "already exists" in e.stderr.decode():
            print_warning(f"Repository {repo_name} already exists on GitHub")
            return True
        else:
            print_error(f"Error creating repository: {e.stderr.decode()}")
            return False


def configure_remote(repo_full_name=None, remote_name="origin"):
    """
    Configure git remote for the repository.
    
    Args:
        repo_full_name (str, optional): The full repository name (owner/repo)
        remote_name (str): The name of the remote to configure
    
    Returns:
        bool: True if successful, False otherwise
    """
    # Get repository info
    if not repo_full_name:
        repo_info = get_repo_info()
        if repo_info["full_name"]:
            repo_full_name = repo_info["full_name"]
        else:
            print_error("Could not determine repository name")
            return False
    
    # Check if the remote already exists
    try:
        remote_url = subprocess.check_output(
            ["git", "remote", "get-url", remote_name],
            stderr=subprocess.DEVNULL,
            universal_newlines=True
        ).strip()
        
        # Check if it's already pointing to the right repository
        if repo_full_name.lower() in remote_url.lower():
            print_success(f"Remote {remote_name} already configured correctly")
            return True
        
        # Remote exists but points to the wrong repo, update it
        print_warning(f"Remote {remote_name} exists but points to {remote_url}")
        print_info(f"Updating remote {remote_name} to point to {repo_full_name}")
        
        try:
            subprocess.run(
                ["git", "remote", "set-url", remote_name, f"https://github.com/{repo_full_name}.git"],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE
            )
            print_success(f"Remote {remote_name} updated to https://github.com/{repo_full_name}.git")
            return True
        except subprocess.CalledProcessError as e:
            print_error(f"Error updating remote: {e.stderr.decode()}")
            return False
    except subprocess.CalledProcessError:
        # Remote doesn't exist, add it
        print_info(f"Remote {remote_name} not found, adding it")
        try:
            subprocess.run(
                ["git", "remote", "add", remote_name, f"https://github.com/{repo_full_name}.git"],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE
            )
            print_success(f"Remote {remote_name} added: https://github.com/{repo_full_name}.git")
            return True
        except subprocess.CalledProcessError as e:
            print_error(f"Error adding remote: {e.stderr.decode()}")
            return False


def setup_repo_secrets(repo_full_name=None, secrets=None):
    """
    Set up repository secrets on GitHub with improved handling.
    
    Args:
        repo_full_name (str, optional): The full repository name (owner/repo)
        secrets (dict, optional): Dictionary of secrets to set
        
    Returns:
        bool: True if successful, False otherwise
    """
    if not check_gh_cli_installed():
        return False
    
    if not repo_full_name:
        repo_info = get_repo_info()
        repo_full_name = repo_info["full_name"]
        
    if not repo_full_name:
        print_error("Could not determine repository name")
        return False
        
    if not secrets:
        # Get default secrets from environment with extended coverage
        secrets = {}
        
        # Critical API keys
        for key in ["OPENROUTER_API_KEY", "OPENAI_API_KEY", "CODECOV_API_TOKEN", "PYPI_API_TOKEN"]:
            if key in os.environ and os.environ[key]:
                secrets[key] = os.environ[key]
        
        # GitHub token-related secrets (if they exist)
        if "GITHUB_TOKEN" in os.environ and os.environ["GITHUB_TOKEN"]:
            secrets["GH_TOKEN"] = os.environ["GITHUB_TOKEN"]
            secrets["GITHUB_TOKEN"] = os.environ["GITHUB_TOKEN"]
    
    if not secrets:
        print_warning("No secrets found in environment variables")
        return False
    
    # First check which secrets already exist
    try:
        existing_secrets = []
        result = subprocess.run(
            ["gh", "secret", "list", "--repo", repo_full_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        
        if result.returncode == 0:
            # Parse secret names from output (format: NAME    UPDATED)
            for line in result.stdout.splitlines():
                if line.strip() and not line.startswith("NAME"):
                    secret_name = line.split()[0].strip()
                    existing_secrets.append(secret_name)
        
        print_info(f"Found {len(existing_secrets)} existing secrets")
        
    except Exception:
        print_warning("Could not retrieve existing secrets")
        existing_secrets = []
    
    # Set up each secret, tracking results
    success_count = 0
    failure_count = 0
    skipped_count = 0
    
    for key, value in secrets.items():
        if not value:
            print_warning(f"Secret {key} has no value, skipping")
            skipped_count += 1
            continue
        
        # Check if secret already exists
        if key in existing_secrets:
            print_info(f"Secret {key} already exists, updating")
        else:
            print_info(f"Setting up new secret: {key}")
            
        try:
            # Use --body flag for compatibility with all gh CLI versions
            cmd = ["gh", "secret", "set", key, "--repo", repo_full_name, "--body", value]
            result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            
            if result.returncode == 0:
                print_success(f"Secret {key} set successfully")
                success_count += 1
            else:
                print_error(f"Error setting secret {key}: {result.stderr.decode()}")
                failure_count += 1
        except Exception as e:
            print_error(f"Error setting secret {key}: {str(e)}")
            failure_count += 1
    
    # Report summary
    print_info(f"Secret setup complete: {success_count} successful, {failure_count} failed, {skipped_count} skipped")
    return failure_count == 0


def check_remote_configuration():
    """
    Check if the local repository is properly connected to a GitHub remote.
    
    Returns:
        dict: Status information about the remote configuration
    """
    result = {
        "has_remote": False,
        "remote_url": None,
        "matches_expected": False,
        "expected_url": None,
        "is_https": False,
        "is_ssh": False
    }
    
    # Check if remote origin exists
    try:
        remote_url = subprocess.check_output(
            ["git", "remote", "get-url", "origin"],
            stderr=subprocess.DEVNULL,
            universal_newlines=True
        ).strip()
        
        result["has_remote"] = True
        result["remote_url"] = remote_url
        result["is_ssh"] = remote_url.startswith("git@")
        result["is_https"] = remote_url.startswith("http")
        
        # Get expected repository from info
        repo_info = get_repo_info()
        if repo_info["full_name"]:
            # Create expected URLs in both formats
            https_url = f"https://github.com/{repo_info['full_name']}.git"
            ssh_url = f"git@github.com:{repo_info['full_name']}.git"
            
            # Store the appropriate one based on current format
            if result["is_ssh"]:
                result["expected_url"] = ssh_url
                result["matches_expected"] = remote_url == ssh_url
            else:
                result["expected_url"] = https_url
                result["matches_expected"] = remote_url == https_url
            
            # More flexible matching
            if not result["matches_expected"]:
                if repo_info["full_name"].lower() in remote_url.lower():
                    result["matches_expected"] = True
    except subprocess.CalledProcessError:
        pass
    
    return result


def verify_branch_setup(expected_branch=None):
    """
    Verify branch setup and tracking configuration.
    
    Args:
        expected_branch (str, optional): The expected branch name
        
    Returns:
        dict: Status information about branch setup
    """
    result = {
        "current_branch": None,
        "has_upstream": False,
        "upstream_branch": None,
        "tracked_remote": None,
        "is_detached": False,
        "default_branch": None
    }
    
    # Get repository info to determine default branch
    repo_info = get_repo_info()
    result["default_branch"] = repo_info["default_branch"]
    
    if expected_branch is None:
        expected_branch = repo_info["default_branch"]
    
    # Check if we're in detached HEAD state
    try:
        head_output = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            stderr=subprocess.DEVNULL,
            universal_newlines=True
        ).strip()
        
        if head_output == "HEAD":
            result["is_detached"] = True
            return result
    except subprocess.CalledProcessError:
        return result
    
    # Get current branch
    try:
        current_branch = subprocess.check_output(
            ["git", "branch", "--show-current"],
            stderr=subprocess.DEVNULL,
            universal_newlines=True
        ).strip()
        
        result["current_branch"] = current_branch
        
        # Check if branch has upstream tracking
        tracking_output = subprocess.check_output(
            ["git", "for-each-ref", "--format='%(upstream:short)'", f"refs/heads/{current_branch}"],
            stderr=subprocess.DEVNULL,
            universal_newlines=True
        ).strip().strip("'")
        
        if tracking_output:
            result["has_upstream"] = True
            result["upstream_branch"] = tracking_output
            result["tracked_remote"] = tracking_output.split("/")[0] if "/" in tracking_output else None
    except subprocess.CalledProcessError:
        pass
    
    return result


def check_branch_exists(branch_name, remote=False):
    """
    Check if a branch exists locally or remotely.
    
    Args:
        branch_name (str): The branch name to check
        remote (bool): Whether to check remote branches
        
    Returns:
        bool: True if the branch exists, False otherwise
    """
    try:
        if remote:
            # Check if the branch exists on the remote
            cmd = ["git", "ls-remote", "--exit-code", "--heads", "origin", branch_name]
        else:
            # Check if the branch exists locally
            cmd = ["git", "show-ref", "--verify", "--quiet", f"refs/heads/{branch_name}"]
        
        result = subprocess.run(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        return result.returncode == 0
    except Exception:
        return False


def create_branch(branch_name, base_branch=None):
    """
    Create a new branch and set it up for tracking.
    
    Args:
        branch_name (str): The name of the branch to create
        base_branch (str, optional): The base branch to create from
        
    Returns:
        bool: True if successful, False otherwise
    """
    # Get repo info to determine default branch if needed
    if not base_branch:
        repo_info = get_repo_info()
        base_branch = repo_info["default_branch"]
    
    # Check if the branch already exists
    if check_branch_exists(branch_name):
        print_info(f"Branch {branch_name} already exists locally")
        # Check if we're already on this branch
        branch_info = verify_branch_setup()
        if branch_info["current_branch"] == branch_name:
            return True
        
        # Switch to the branch
        try:
            subprocess.run(
                ["git", "checkout", branch_name],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE
            )
            print_success(f"Switched to existing branch {branch_name}")
            return True
        except subprocess.CalledProcessError as e:
            print_error(f"Error switching to branch {branch_name}: {e.stderr.decode()}")
            return False
    
    # Create the branch
    try:
        # First, make sure base branch exists
        if not check_branch_exists(base_branch):
            # Try to fetch it from remote
            if check_branch_exists(base_branch, remote=True):
                print_info(f"Fetching {base_branch} from remote")
                subprocess.run(
                    ["git", "fetch", "origin", base_branch],
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE
                )
                
                # Create local branch tracking remote
                subprocess.run(
                    ["git", "checkout", "-b", base_branch, f"origin/{base_branch}"],
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE
                )
            else:
                print_error(f"Base branch {base_branch} does not exist locally or remotely")
                return False
        
        # Now create the new branch
        subprocess.run(
            ["git", "checkout", "-b", branch_name, base_branch],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE
        )
        print_success(f"Created and switched to new branch {branch_name} based on {base_branch}")
        return True
    except subprocess.CalledProcessError as e:
        print_error(f"Error creating branch {branch_name}: {e.stderr.decode()}")
        return False


def push_branch(branch_name=None, set_upstream=True, force=False):
    """
    Push a branch to the remote with proper tracking.
    
    Args:
        branch_name (str, optional): The branch to push (current branch if None)
        set_upstream (bool): Whether to set up tracking
        force (bool): Whether to force push
        
    Returns:
        bool: True if successful, False otherwise
    """
    # If no branch specified, get current branch
    if not branch_name:
        branch_info = verify_branch_setup()
        branch_name = branch_info["current_branch"]
        
        if not branch_name:
            print_error("Could not determine current branch")
            return False
    
    # Check if branch already exists on remote
    remote_exists = check_branch_exists(branch_name, remote=True)
    
    # Construct the push command
    cmd = ["git", "push"]
    
    if force:
        cmd.append("--force")
    
    if set_upstream and not remote_exists:
        cmd.extend(["-u"])
    
    cmd.extend(["origin", branch_name])
    
    try:
        result = subprocess.run(
            cmd,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        if result.returncode == 0:
            if remote_exists:
                print_success(f"Pushed updates to branch {branch_name}")
            else:
                print_success(f"Pushed branch {branch_name} to remote and set up tracking")
            return True
        else:
            print_error(f"Error pushing branch: {result.stderr.decode()}")
            return False
    except subprocess.CalledProcessError as e:
        # Check for common errors and suggest solutions
        error_msg = e.stderr.decode()
        
        if "Updates were rejected because the remote contains work" in error_msg:
            print_error("Push rejected because remote has changes. Try:")
            print_info("1. Pull changes: git pull origin " + branch_name)
            print_info("2. Or use force push (if appropriate): --force")
        elif "Permission denied" in error_msg:
            print_error("Permission denied. Check your GitHub authentication.")
        else:
            print_error(f"Error pushing branch: {error_msg}")
        
        return False


def check_for_secret(secret_name, repo_full_name=None):
    """
    Check if a GitHub secret exists for a repository.
    
    Args:
        secret_name (str): The name of the secret to check
        repo_full_name (str, optional): The full repository name (owner/repo)
        
    Returns:
        bool: True if the secret exists, False otherwise
    """
    if not check_gh_cli_installed():
        return False
    
    if not repo_full_name:
        repo_info = get_repo_info()
        repo_full_name = repo_info["full_name"]
        
    if not repo_full_name:
        print_error("Could not determine repository name")
        return False
    
    try:
        result = subprocess.run(
            ["gh", "secret", "list", "--repo", repo_full_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        
        if result.returncode == 0:
            # Parse output to check for the secret
            return any(line.strip().startswith(secret_name) for line in result.stdout.splitlines())
        else:
            print_error(f"Error checking for secret: {result.stderr}")
            return False
    except Exception as e:
        print_error(f"Error checking for secret: {str(e)}")
        return False


def check_workflow_triggers(workflow_files=None):
    """
    Check if GitHub workflow files have workflow_dispatch triggers.
    
    Args:
        workflow_files (list, optional): List of workflow files to check
        
    Returns:
        dict: Results of workflow trigger checks
    """
    result = {
        "total": 0,
        "with_dispatch": 0,
        "missing_dispatch": 0,
        "files_missing_dispatch": []
    }
    
    # Build list of workflow files to check
    if not workflow_files:
        workflow_dir = Path(".github/workflows")
        if not workflow_dir.exists():
            return result
        
        workflow_files = list(workflow_dir.glob("*.yml")) + list(workflow_dir.glob("*.yaml"))
    
    result["total"] = len(workflow_files)
    
    # Check each workflow file
    for workflow_file in workflow_files:
        try:
            with open(workflow_file, "r") as f:
                content = f.read()
                
                # Check for workflow_dispatch trigger
                if "workflow_dispatch" in content:
                    result["with_dispatch"] += 1
                else:
                    result["missing_dispatch"] += 1
                    result["files_missing_dispatch"].append(str(workflow_file))
        except Exception:
            # Skip files with issues
            pass
    
    return result


def add_workflow_dispatch_trigger(workflow_file):
    """
    Add workflow_dispatch trigger to a GitHub workflow file.
    
    Args:
        workflow_file (str): Path to the workflow file
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        with open(workflow_file, "r") as f:
            content = f.read()
        
        # Skip if already has workflow_dispatch
        if "workflow_dispatch" in content:
            print_info(f"{workflow_file} already has workflow_dispatch trigger")
            return True
        
        # Identify the 'on:' section
        on_pattern = r"^on:"
        on_match = re.search(on_pattern, content, re.MULTILINE)
        
        if not on_match:
            print_error(f"Could not find 'on:' section in {workflow_file}")
            return False
        
        # Determine the pattern to add workflow_dispatch based on the format
        if re.search(r"^on:.*{", content, re.MULTILINE):
            # Object syntax for triggers
            modified_content = re.sub(
                r"(^on:.*{)",
                r"\1\n  workflow_dispatch: {},  # Added automatically",
                content,
                count=1,
                flags=re.MULTILINE
            )
        else:
            # List syntax for triggers
            modified_content = re.sub(
                r"(^on:.*$)",
                r"\1\n  workflow_dispatch:  # Added automatically\n    inputs:\n      reason:\n        description: 'Reason for manual trigger'\n        required: false\n        default: 'Triggered automatically'",
                content,
                count=1,
                flags=re.MULTILINE
            )
        
        # Write the modified content back
        with open(workflow_file, "w") as f:
            f.write(modified_content)
            
        print_success(f"Added workflow_dispatch trigger to {workflow_file}")
        return True
    except Exception as e:
        print_error(f"Error adding workflow_dispatch to {workflow_file}: {str(e)}")
        return False


def fix_workflow_triggers(auto_commit=False):
    """
    Check and fix workflow_dispatch triggers in all workflow files.
    
    Args:
        auto_commit (bool): Whether to automatically commit changes
        
    Returns:
        dict: Results of the fix operation
    """
    result = {
        "checked": 0,
        "fixed": 0,
        "failed": 0,
        "already_ok": 0
    }
    
    # Check current workflow files
    workflow_dir = Path(".github/workflows")
    if not workflow_dir.exists():
        print_warning("No .github/workflows directory found")
        return result
    
    workflow_files = list(workflow_dir.glob("*.yml")) + list(workflow_dir.glob("*.yaml"))
    result["checked"] = len(workflow_files)
    
    # Process each workflow file
    for workflow_file in workflow_files:
        try:
            with open(workflow_file, "r") as f:
                content = f.read()
                
            # Check if it already has workflow_dispatch
            if "workflow_dispatch" in content:
                result["already_ok"] += 1
                continue
            
            # Add workflow_dispatch trigger
            if add_workflow_dispatch_trigger(workflow_file):
                result["fixed"] += 1
            else:
                result["failed"] += 1
        except Exception as e:
            print_error(f"Error processing {workflow_file}: {str(e)}")
            result["failed"] += 1
    
    # Commit changes if requested and any fixes were made
    if auto_commit and result["fixed"] > 0:
        try:
            # Stage the changes
            subprocess.run(
                ["git", "add", ".github/workflows/*.yml", ".github/workflows/*.yaml"],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE
            )
            
            # Create the commit
            subprocess.run(
                ["git", "commit", "-m", "Add workflow_dispatch triggers to GitHub workflows [skip-tests]"],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE
            )
            
            print_success(f"Committed changes to {result['fixed']} workflow files")
        except subprocess.CalledProcessError as e:
            print_error(f"Error committing changes: {e.stderr.decode()}")
    
    return result


def trigger_workflow(workflow_name, branch=None, inputs=None):
    """
    Trigger a GitHub workflow using the GitHub CLI.
    
    Args:
        workflow_name (str): Name or filename of the workflow to trigger
        branch (str, optional): Branch to run the workflow on
        inputs (dict, optional): Input parameters for the workflow
        
    Returns:
        bool: True if successful, False otherwise
    """
    if not check_gh_cli_installed():
        return False
    
    # Get repository info
    repo_info = get_repo_info()
    
    # If branch not specified, use current branch
    if not branch:
        branch_info = verify_branch_setup()
        branch = branch_info["current_branch"]
        
        # Fallback to default branch if needed
        if not branch:
            branch = repo_info["default_branch"]
    
    # Build the command
    cmd = ["gh", "workflow", "run", workflow_name]
    
    if branch:
        cmd.extend(["--ref", branch])
    
    # Add inputs if provided
    if inputs:
        for key, value in inputs.items():
            cmd.extend(["-f", f"{key}={value}"])
    
    # Try to trigger the workflow
    try:
        result = subprocess.run(
            cmd,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        if result.returncode == 0:
            print_success(f"Triggered workflow {workflow_name} on branch {branch}")
            
            # Extract run ID if available
            run_id_match = re.search(r"Running.*ID (\d+)", result.stdout.decode())
            if run_id_match:
                run_id = run_id_match.group(1)
                print_info(f"Workflow run ID: {run_id}")
                return run_id
            
            return True
        else:
            print_error(f"Error triggering workflow: {result.stderr.decode()}")
            return False
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.decode()
        
        # Handle specific errors
        if "Workflow does not have workflow_dispatch" in error_msg:
            print_error(f"Workflow {workflow_name} does not have workflow_dispatch trigger")
            print_info("Consider running fix_workflow_triggers() to add workflow_dispatch triggers")
        else:
            print_error(f"Error triggering workflow: {error_msg}")
        
        return False


def wait_for_workflow_logs(run_id, timeout=60, silent=False):
    """
    Wait for a workflow run to complete and retrieve logs.
    
    Args:
        run_id (str): The workflow run ID
        timeout (int): Maximum time to wait in seconds
        silent (bool): Whether to suppress progress messages
        
    Returns:
        str: Path to the log file if successful, None otherwise
    """
    if not check_gh_cli_installed():
        return None
    
    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)
    
    # Wait for the workflow to start and/or complete
    start_time = time.time()
    wait_steps = min(timeout // 5, 10)  # Update at most 10 times
    
    for i in range(wait_steps):
        elapsed = time.time() - start_time
        if elapsed >= timeout:
            if not silent:
                print_warning(f"Timeout ({timeout}s) reached waiting for workflow run {run_id}")
            break
        
        if not silent:
            print_info(f"Waiting for workflow run {run_id} ({int(elapsed)}s/{timeout}s)...")
        
        # Check workflow status
        try:
            result = subprocess.run(
                ["gh", "run", "view", run_id, "--json", "status,conclusion"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            
            if result.returncode == 0:
                data = json.loads(result.stdout)
                status = data.get("status")
                conclusion = data.get("conclusion")
                
                if not silent:
                    print_info(f"Workflow status: {status}, conclusion: {conclusion}")
                
                # If completed, get logs
                if status == "completed" or elapsed >= timeout * 0.8:
                    break
            
            # Wait before checking again
            time.sleep(max(5, timeout / wait_steps))
        except Exception:
            if not silent:
                print_warning("Error checking workflow status, continuing...")
            time.sleep(5)
    
    # Get logs
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    log_file = f"logs/workflow_{run_id}_{timestamp}.log"
    
    try:
        with open(log_file, "w") as f:
            result = subprocess.run(
                ["gh", "run", "view", run_id, "--log"],
                stdout=f,
                stderr=subprocess.PIPE
            )
        
        if result.returncode == 0:
            if not silent:
                print_success(f"Saved workflow logs to {log_file}")
            return log_file
        else:
            if not silent:
                print_error(f"Error retrieving workflow logs: {result.stderr.decode()}")
            return None
    except Exception as e:
        if not silent:
            print_error(f"Error saving workflow logs: {str(e)}")
        return None


def install_bump_my_version(use_uv=True, force_reinstall=False):
    """
    Install bump-my-version using uv or pip, following best practices.
    
    Args:
        use_uv (bool): Whether to use uv tool run for installation
        force_reinstall (bool): Force reinstall even if already installed
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Check if bump-my-version is already installed and we're not forcing reinstall
        if not force_reinstall:
            # Try uv tool list first
            try:
                if use_uv:
                    result = subprocess.run(
                        ["uv", "tool", "list"],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        universal_newlines=True
                    )
                    if "bump-my-version" in result.stdout:
                        print_success("bump-my-version is already installed via uv")
                        return True
            except Exception:
                pass
            
            # Try checking directly
            try:
                result = subprocess.run(
                    ["bump-my-version", "--version"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                if result.returncode == 0:
                    print_success("bump-my-version is already installed")
                    return True
            except Exception:
                # Not found or not in PATH, continue with installation
                pass
        
        # Try to install with uv (preferred method)
        if use_uv:
            print_info("Installing bump-my-version using uv tool...")
            try:
                result = subprocess.run(
                    ["uv", "tool", "install", "bump-my-version"],
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                if result.returncode == 0:
                    print_success("Successfully installed bump-my-version using uv tool")
                    return True
            except subprocess.CalledProcessError as e:
                print_warning(f"Error installing with uv tool: {e.stderr.decode()}")
                print_info("Falling back to alternative installation methods...")
            except FileNotFoundError:
                print_warning("uv not found in PATH, falling back to alternative installation methods...")
        
        # First fallback: Use pip in current environment
        print_info("Trying to install bump-my-version using pip...")
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "bump-my-version"],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            if result.returncode == 0:
                print_success("Successfully installed bump-my-version using pip")
                return True
        except subprocess.CalledProcessError as e:
            print_warning(f"Error installing with pip: {e.stderr.decode()}")
        
        # Second fallback: pipx if available
        print_info("Trying to install bump-my-version using pipx...")
        try:
            result = subprocess.run(
                ["pipx", "install", "bump-my-version"],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            if result.returncode == 0:
                print_success("Successfully installed bump-my-version using pipx")
                return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            # pipx not available or failed, final fallback
            pass
        
        print_error("Failed to install bump-my-version using available methods")
        print_info("Please install manually with one of these commands:")
        print_info("  uv tool install bump-my-version")
        print_info("  pip install bump-my-version")
        print_info("  pipx install bump-my-version")
        return False
    except Exception as e:
        print_error(f"Unexpected error installing bump-my-version: {str(e)}")
        return False


def run_bump_my_version(args, use_uv=True):
    """
    Run bump-my-version with the given arguments using the proper approach.
    
    Args:
        args (list): List of arguments to pass to bump-my-version
        use_uv (bool): Whether to use uv tool run (recommended)
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Ensure bump-my-version is installed
        if not install_bump_my_version(use_uv):
            return False
        
        print_info(f"Running bump-my-version with args: {' '.join(args)}")
        
        # Try to run with uv tool run (preferred method)
        if use_uv:
            try:
                cmd = ["uv", "tool", "run", "bump-my-version"] + args
                result = subprocess.run(
                    cmd,
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                if result.returncode == 0:
                    print_success(f"Successfully ran bump-my-version: {result.stdout.decode().strip()}")
                    return True
            except subprocess.CalledProcessError as e:
                print_warning(f"Error running with uv tool: {e.stderr.decode()}")
                print_info("Falling back to direct execution...")
            except FileNotFoundError:
                print_warning("uv not found in PATH, falling back to direct execution...")
        
        # Fallback: Try direct execution
        try:
            cmd = ["bump-my-version"] + args
            result = subprocess.run(
                cmd,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            if result.returncode == 0:
                print_success(f"Successfully ran bump-my-version directly: {result.stdout.decode().strip()}")
                return True
        except subprocess.CalledProcessError as e:
            print_error(f"Error running bump-my-version: {e.stderr.decode()}")
        except FileNotFoundError:
            print_error("bump-my-version not found in PATH")
        
        return False
    except Exception as e:
        print_error(f"Unexpected error running bump-my-version: {str(e)}")
        return False


def bump_version(part="minor", allow_dirty=True, commit=True, tag=True, use_uv=True):
    """
    Bump the project version using bump-my-version.
    
    Args:
        part (str): Version part to bump (major, minor, patch)
        allow_dirty (bool): Allow dirty working directory
        commit (bool): Create a commit
        tag (bool): Create a tag
        use_uv (bool): Whether to use uv tool run (recommended)
    
    Returns:
        bool: True if successful, False otherwise
    """
    # Validate part
    if part not in ["major", "minor", "patch"]:
        print_error(f"Invalid version part: {part}. Use one of: major, minor, patch")
        return False
    
    # Build arguments
    args = ["bump", part]
    
    if allow_dirty:
        args.append("--allow-dirty")
    
    if commit:
        args.append("--commit")
    
    if tag:
        args.append("--tag")
    
    return run_bump_my_version(args, use_uv)


def main():
    """Command-line interface for GitHub repository management."""
    parser = argparse.ArgumentParser(
        description="Enhanced GitHub repository management utilities",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m helpers.github.repo_helper --check-repo
  python -m helpers.github.repo_helper --setup-secrets
  python -m helpers.github.repo_helper --create-repo --name my-repo --description "My project"
  python -m helpers.github.repo_helper --fix-workflows --commit
  python -m helpers.github.repo_helper --trigger tests.yml --branch main
  python -m helpers.github.repo_helper --wait-logs 12345678 --timeout 120
  python -m helpers.github.repo_helper --bump-version minor
"""
    )
    
    # Repository operations
    parser.add_argument("--info", action="store_true", help="Show repository information")
    parser.add_argument("--check-repo", action="store_true", help="Check if repository exists")
    parser.add_argument("--create-repo", action="store_true", help="Create a new repository")
    parser.add_argument("--name", help="Repository name")
    parser.add_argument("--description", help="Repository description")
    parser.add_argument("--private", action="store_true", help="Create private repository")
    
    # Remote and branch operations
    parser.add_argument("--check-remote", action="store_true", help="Check remote configuration")
    parser.add_argument("--update-remote", action="store_true", help="Update remote configuration")
    parser.add_argument("--check-branch", action="store_true", help="Check branch setup")
    parser.add_argument("--create-branch", metavar="NAME", help="Create a new branch")
    parser.add_argument("--base", metavar="BRANCH", help="Base branch for new branch")
    parser.add_argument("--push", action="store_true", help="Push current or specified branch")
    parser.add_argument("--force", action="store_true", help="Force push branch")
    
    # Secret management
    parser.add_argument("--setup-secrets", action="store_true", help="Set up repository secrets")
    parser.add_argument("--check-secret", metavar="NAME", help="Check if a secret exists")
    
    # Workflow management
    parser.add_argument("--check-workflows", action="store_true", help="Check workflow_dispatch triggers")
    parser.add_argument("--fix-workflows", action="store_true", help="Fix workflow_dispatch triggers")
    parser.add_argument("--commit", action="store_true", help="Commit workflow fixes")
    parser.add_argument("--trigger", metavar="WORKFLOW", help="Trigger a workflow")
    parser.add_argument("--branch", help="Branch for workflow trigger")
    parser.add_argument("--wait-logs", metavar="RUN_ID", help="Wait for workflow logs")
    parser.add_argument("--timeout", type=int, default=60, help="Timeout for waiting (seconds)")
    
    # Version management
    parser.add_argument("--bump-version", metavar="PART", 
                      choices=["major", "minor", "patch"], 
                      help="Bump version (major, minor, or patch)")
    parser.add_argument("--no-uv", action="store_true", help="Don't use uv for bump-my-version")
    parser.add_argument("--no-commit", action="store_true", help="Don't create a commit when bumping version")
    parser.add_argument("--no-tag", action="store_true", help="Don't create a tag when bumping version")
    parser.add_argument("--no-dirty", action="store_true", help="Don't allow dirty working directory")
    parser.add_argument("--install-bumpversion", action="store_true", help="Just install bump-my-version")
    
    args = parser.parse_args()
    
    # If no specific action is requested, show help
    if not any([args.info, args.check_repo, args.create_repo, args.check_remote, args.update_remote,
               args.check_branch, args.create_branch, args.push, args.setup_secrets, args.check_secret,
               args.check_workflows, args.fix_workflows, args.trigger, args.wait_logs, args.bump_version,
               args.install_bumpversion]):
        parser.print_help()
        return 0
    
    exit_code = 0
    
    # Get repository info (for most operations)
    repo_info = get_repo_info()
    
    # Show repository info
    if args.info:
        print_colored("Repository Information:", "CYAN", bold=True)
        print(f"Name:           {repo_info['name'] or 'Unknown'}")
        print(f"Owner:          {repo_info['owner'] or 'Unknown'}")
        print(f"Full name:      {repo_info['full_name'] or 'Unknown'}")
        print(f"HTTPS URL:      {repo_info['https_url'] or 'Unknown'}")
        print(f"SSH URL:        {repo_info['ssh_url'] or 'Unknown'}")
        print(f"Default branch: {repo_info['default_branch']}")
        print(f"Initialized:    {'Yes' if repo_info['is_initialized'] else 'No'}")
        
        # Check if repository exists on GitHub
        if repo_info["full_name"]:
            exists = check_repo_exists(repo_info["full_name"])
            print(f"Exists on GitHub: {'Yes' if exists else 'No'}")
    
    # Check if repository exists
    if args.check_repo:
        if repo_info["full_name"]:
            exists = check_repo_exists(repo_info["full_name"])
            if exists:
                print_success(f"Repository {repo_info['full_name']} exists on GitHub")
            else:
                print_warning(f"Repository {repo_info['full_name']} does not exist on GitHub")
                exit_code = 1
        else:
            print_error("Could not determine repository information")
            exit_code = 1
    
    # Create a new repository
    if args.create_repo:
        repo_name = args.name or repo_info["name"]
        if not repo_name:
            print_error("Repository name is required for creation")
            return 1
        
        if create_repo(repo_name, args.private, args.description):
            print_success(f"Repository {repo_name} created or already exists")
            
            # Configure remote if needed
            repo_full_name = f"{repo_info['owner'] or args.owner or 'unknown'}/{repo_name}"
            if not args.check_remote and not args.update_remote:
                configure_remote(repo_full_name)
        else:
            print_error(f"Failed to create repository {repo_name}")
            exit_code = 1
    
    # Check remote configuration
    if args.check_remote:
        remote_info = check_remote_configuration()
        
        if remote_info["has_remote"]:
            print_success(f"Remote URL: {remote_info['remote_url']}")
            
            if remote_info["expected_url"]:
                if remote_info["matches_expected"]:
                    print_success(f"Remote matches expected repository: {repo_info['full_name']}")
                else:
                    print_warning("Remote does not match expected repository")
                    print_info(f"Current:  {remote_info['remote_url']}")
                    print_info(f"Expected: {remote_info['expected_url']}")
                    exit_code = 1
        else:
            print_warning("No remote 'origin' configured")
            exit_code = 1
    
    # Update remote configuration
    if args.update_remote:
        if repo_info["full_name"]:
            if configure_remote(repo_info["full_name"]):
                print_success(f"Remote 'origin' configured for {repo_info['full_name']}")
            else:
                print_error("Failed to configure remote")
                exit_code = 1
        else:
            print_error("Could not determine repository information")
            exit_code = 1
    
    # Check branch setup
    if args.check_branch:
        branch_info = verify_branch_setup()
        
        if branch_info["is_detached"]:
            print_warning("Detached HEAD state detected")
            exit_code = 1
        elif branch_info["current_branch"]:
            print_success(f"Current branch: {branch_info['current_branch']}")
            
            if branch_info["has_upstream"]:
                print_success(f"Tracks: {branch_info['upstream_branch']}")
            else:
                print_warning("No upstream tracking configured")
                exit_code = 1
        else:
            print_error("Could not determine current branch")
            exit_code = 1
    
    # Create a new branch
    if args.create_branch:
        if create_branch(args.create_branch, args.base):
            print_success(f"Branch {args.create_branch} created and checked out")
            
            # Push if requested
            if args.push:
                if push_branch(args.create_branch, True, args.force):
                    print_success(f"Branch {args.create_branch} pushed to remote")
                else:
                    print_error(f"Failed to push branch {args.create_branch}")
                    exit_code = 1
        else:
            print_error(f"Failed to create branch {args.create_branch}")
            exit_code = 1
    
    # Push branch
    if args.push and not args.create_branch:
        if push_branch(args.branch, True, args.force):
            print_success(f"Branch {args.branch or 'current'} pushed to remote")
        else:
            print_error(f"Failed to push branch {args.branch or 'current'}")
            exit_code = 1
    
    # Set up repository secrets
    if args.setup_secrets:
        if repo_info["full_name"]:
            if setup_repo_secrets(repo_info["full_name"]):
                print_success(f"Secrets set up for {repo_info['full_name']}")
            else:
                print_warning("Some secrets could not be set up")
                exit_code = 1
        else:
            print_error("Could not determine repository information")
            exit_code = 1
    
    # Check if a specific secret exists
    if args.check_secret:
        if repo_info["full_name"]:
            if check_for_secret(args.check_secret, repo_info["full_name"]):
                print_success(f"Secret {args.check_secret} exists for {repo_info['full_name']}")
            else:
                print_warning(f"Secret {args.check_secret} does not exist for {repo_info['full_name']}")
                exit_code = 1
        else:
            print_error("Could not determine repository information")
            exit_code = 1
    
    # Check workflow_dispatch triggers
    if args.check_workflows:
        results = check_workflow_triggers()
        
        print_colored("Workflow Trigger Check:", "CYAN", bold=True)
        print(f"Total workflows:     {results['total']}")
        print(f"With workflow_dispatch: {results['with_dispatch']}")
        print(f"Missing workflow_dispatch: {results['missing_dispatch']}")
        
        if results["missing_dispatch"] > 0:
            print_warning("The following workflows are missing workflow_dispatch triggers:")
            for file in results["files_missing_dispatch"]:
                print(f"  - {file}")
            exit_code = 1
    
    # Fix workflow_dispatch triggers
    if args.fix_workflows:
        results = fix_workflow_triggers(args.commit)
        
        print_colored("Workflow Trigger Fix Results:", "CYAN", bold=True)
        print(f"Workflows checked: {results['checked']}")
        print(f"Already compliant: {results['already_ok']}")
        print(f"Fixed workflows:   {results['fixed']}")
        print(f"Failed to fix:     {results['failed']}")
        
        if results["fixed"] > 0:
            if args.commit:
                print_success(f"Fixed and committed {results['fixed']} workflow files")
            else:
                print_success(f"Fixed {results['fixed']} workflow files (changes not committed)")
                print_info("Use --commit to automatically commit the changes")
        
        if results["failed"] > 0:
            print_warning(f"Failed to fix {results['failed']} workflow files")
            exit_code = 1
    
    # Trigger a workflow
    if args.trigger:
        result = trigger_workflow(args.trigger, args.branch, {"reason": "Triggered via repo_helper script"})
        
        if result:
            if isinstance(result, str):
                print_success(f"Workflow {args.trigger} triggered with run ID: {result}")
                
                # Wait for logs if requested
                if args.wait_logs is None and args.timeout > 0:
                    print_info(f"Waiting for workflow logs (timeout: {args.timeout}s)...")
                    log_file = wait_for_workflow_logs(result, args.timeout)
                    
                    if log_file:
                        print_success(f"Workflow logs saved to {log_file}")
                    else:
                        print_warning("Failed to retrieve workflow logs")
            else:
                print_success(f"Workflow {args.trigger} triggered successfully")
        else:
            print_error(f"Failed to trigger workflow {args.trigger}")
            exit_code = 1
    
    # Wait for workflow logs
    if args.wait_logs:
        print_info(f"Waiting for workflow run {args.wait_logs} logs (timeout: {args.timeout}s)...")
        log_file = wait_for_workflow_logs(args.wait_logs, args.timeout)
        
        if log_file:
            print_success(f"Workflow logs saved to {log_file}")
        else:
            print_warning("Failed to retrieve workflow logs")
            exit_code = 1
    
    # Just install bump-my-version
    if args.install_bumpversion:
        print_info("Installing bump-my-version...")
        if install_bump_my_version(not args.no_uv, force_reinstall=True):
            print_success("Successfully installed bump-my-version")
        else:
            print_error("Failed to install bump-my-version")
            exit_code = 1
    
    # Bump version
    if args.bump_version:
        print_info(f"Bumping {args.bump_version} version...")
        
        # Prepare arguments based on flags
        use_uv = not args.no_uv
        commit = not args.no_commit
        tag = not args.no_tag
        allow_dirty = not args.no_dirty
        
        if bump_version(args.bump_version, allow_dirty, commit, tag, use_uv):
            print_success(f"Successfully bumped {args.bump_version} version")
        else:
            print_error(f"Failed to bump {args.bump_version} version")
            exit_code = 1
    
    return exit_code


if __name__ == "__main__":
    sys.exit(main())