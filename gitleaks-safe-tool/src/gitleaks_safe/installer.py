#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Git hooks installer for gitleaks-safe
"""

import os
import platform
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm
from rich.table import Table

from .utils import (
    check_docker_containers,
    find_gitleaks_installations,
    get_platform_info,
    is_docker,
)

console = Console()


class GitleaksInstaller:
    """Handles gitleaks installation across different platforms."""

    def __init__(self):
        self.platform_info = get_platform_info()

    def install(self) -> bool:
        """Install gitleaks for the current platform."""
        console.print(f"[blue]📥 Installing gitleaks for {self.platform_info['os']}...[/blue]")

        if is_docker():
            console.print("[yellow]🐳 Detected Docker environment[/yellow]")
            return self._install_docker()

        install_methods = {
            "macos": self._install_macos,
            "ubuntu": self._install_debian,
            "debian": self._install_debian,
            "fedora": self._install_redhat,
            "centos": self._install_redhat,
            "rhel": self._install_redhat,
            "arch": self._install_arch,
            "alpine": self._install_alpine,
            "windows": self._install_windows,
        }

        method = install_methods.get(self.platform_info["os"], self._install_generic)
        return method()

    def _install_macos(self) -> bool:
        """Install on macOS."""
        if shutil.which("brew"):
            console.print("Installing with Homebrew...")
            result = subprocess.run(["brew", "install", "gitleaks"], capture_output=True)
            return result.returncode == 0
        else:
            console.print("[red]❌ Homebrew not found[/red]")
            console.print("Install Homebrew from https://brew.sh or use binary installation")
            return self._install_binary("darwin", "x64" if platform.machine() == "x86_64" else "arm64")

    def _install_debian(self) -> bool:
        """Install on Debian/Ubuntu."""
        console.print("Installing for Debian/Ubuntu...")

        if shutil.which("snap"):
            result = subprocess.run(["sudo", "snap", "install", "gitleaks"], capture_output=True)
            if result.returncode == 0:
                return True

        # Fallback to binary
        console.print("Snap not available, using binary installation...")
        arch_map = {"x86_64": "x64", "aarch64": "arm64", "arm64": "arm64"}
        arch = platform.machine()
        if arch in arch_map:
            return self._install_binary("linux", arch_map[arch])
        else:
            console.print(f"[red]Unsupported architecture: {arch}[/red]")
            return False

    def _install_redhat(self) -> bool:
        """Install on RedHat/Fedora/CentOS."""
        console.print("Installing for RedHat/Fedora/CentOS...")

        for cmd in ["dnf", "yum"]:
            if shutil.which(cmd):
                result = subprocess.run(["sudo", cmd, "install", "-y", "gitleaks"], capture_output=True)
                if result.returncode == 0:
                    return True

        # Fallback to binary
        console.print("Package manager not found, using binary installation...")
        return self._install_binary("linux", "x64" if platform.machine() == "x86_64" else "arm64")

    def _install_arch(self) -> bool:
        """Install on Arch Linux."""
        console.print("Installing for Arch Linux...")

        for aur_helper in ["yay", "paru"]:
            if shutil.which(aur_helper):
                result = subprocess.run([aur_helper, "-S", "gitleaks"], capture_output=True)
                if result.returncode == 0:
                    return True

        console.print("[yellow]AUR helper not found, using binary installation...[/yellow]")
        return self._install_binary("linux", "x64" if platform.machine() == "x86_64" else "arm64")

    def _install_alpine(self) -> bool:
        """Install on Alpine Linux."""
        console.print("Installing for Alpine Linux...")
        result = subprocess.run(["apk", "add", "--no-cache", "gitleaks"], capture_output=True)
        return result.returncode == 0

    def _install_windows(self) -> bool:
        """Install on Windows."""
        console.print("Installing for Windows...")

        for pkg_manager in ["scoop", "choco"]:
            if shutil.which(pkg_manager):
                cmd = [pkg_manager, "install", "gitleaks"]
                result = subprocess.run(cmd, capture_output=True)
                if result.returncode == 0:
                    return True

        console.print("[red]Package manager not found[/red]")
        console.print("Install scoop from https://scoop.sh or chocolatey from https://chocolatey.org")
        return False

    def _install_docker(self) -> bool:
        """Install in Docker container."""
        console.print("Installing in Docker container...")
        arch_map = {"x86_64": "x64", "aarch64": "arm64", "arm64": "arm64"}
        arch = platform.machine()

        if arch in arch_map:
            return self._install_binary("linux", arch_map[arch])
        else:
            console.print(f"[red]Unsupported architecture: {arch}[/red]")
            return False

    def _install_generic(self) -> bool:
        """Generic installation fallback."""
        console.print("Attempting generic installation...")
        os_type = platform.system().lower()
        arch_map = {"x86_64": "x64", "amd64": "x64", "aarch64": "arm64", "arm64": "arm64"}
        arch = platform.machine()

        if arch in arch_map:
            return self._install_binary(os_type, arch_map[arch])
        else:
            console.print(f"[red]Unsupported architecture: {arch}[/red]")
            return False

    def _install_binary(self, os_type: str, arch: str) -> bool:
        """Install gitleaks from binary release."""
        console.print(f"Downloading gitleaks binary for {os_type}/{arch}...")

        try:
            # Get latest version
            result = subprocess.run(["curl", "-s", "https://api.github.com/repos/gitleaks/gitleaks/releases/latest"], capture_output=True, text=True)

            if result.returncode != 0:
                raise Exception("Failed to get latest version")

            import json

            data = json.loads(result.stdout)
            version = data["tag_name"].lstrip("v")

            url = f"https://github.com/gitleaks/gitleaks/releases/download/v{version}/gitleaks_{version}_{os_type}_{arch}.tar.gz"
            install_dir = "/usr/local/bin"

            # Check if we need sudo
            sudo_cmd = ["sudo"] if not os.access(install_dir, os.W_OK) else []

            console.print(f"Downloading from: {url}")

            # Download and install
            download_cmd = ["curl", "-sSfL", url]
            extract_cmd = sudo_cmd + ["tar", "-xz", "-C", install_dir, "gitleaks"]

            # Use pipe to download and extract
            download = subprocess.Popen(download_cmd, stdout=subprocess.PIPE)
            extract = subprocess.Popen(extract_cmd, stdin=download.stdout)
            download.stdout.close()
            extract.communicate()

            if extract.returncode == 0:
                # Make executable
                chmod_cmd = sudo_cmd + ["chmod", "+x", f"{install_dir}/gitleaks"]
                subprocess.run(chmod_cmd)

                console.print(f"[green]✅ Installed gitleaks to {install_dir}/gitleaks[/green]")
                return True
            else:
                raise Exception("Failed to extract gitleaks")

        except Exception as e:
            console.print(f"[red]Failed to install gitleaks: {e}[/red]")
            return False


class GitHooksInstaller:
    """Installs memory-safe git hooks."""

    def __init__(self, pre_commit: bool = False, pre_push: bool = True):
        self.pre_commit = pre_commit
        self.pre_push = pre_push
        self.git_root = self._find_git_root()

    def _find_git_root(self) -> Optional[Path]:
        """Find the git repository root."""
        try:
            result = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=True)
            return Path(result.stdout.strip())
        except subprocess.CalledProcessError:
            return None

    def install(self) -> bool:
        """Install git hooks."""
        if not self.git_root:
            console.print("[red]❌ Not in a git repository[/red]")
            return False

        hooks_dir = self.git_root / ".git" / "hooks"

        success = True
        if self.pre_commit:
            success &= self._install_hook("pre-commit", hooks_dir)

        if self.pre_push:
            success &= self._install_hook("pre-push", hooks_dir)

        return success

    def _install_hook(self, hook_name: str, hooks_dir: Path) -> bool:
        """Install a specific git hook."""
        hook_path = hooks_dir / hook_name

        # Backup existing hook
        if hook_path.exists():
            backup_path = hook_path.with_suffix(f".backup-{datetime.now().strftime('%Y%m%d-%H%M%S')}")
            shutil.copy2(hook_path, backup_path)
            console.print(f"[yellow]⚠️  Backed up existing {hook_name} hook to {backup_path.name}[/yellow]")

        # Determine gitleaks arguments
        gitleaks_args = "protect --staged" if hook_name == "pre-commit" else "protect"

        # Create hook content
        hook_content = f"""#!/bin/bash
# Git {hook_name} hook with memory-safe gitleaks integration
# Generated by gitleaks-safe Python tool

# Run gitleaks with safety wrapper
echo "🔍 Running gitleaks {hook_name} check (safe mode)..."

# Look for .gitleaks.toml in repo root
GIT_ROOT=$(git rev-parse --show-toplevel)
CONFIG_ARG=""
if [ -f "$GIT_ROOT/.gitleaks.toml" ]; then
    CONFIG_ARG="--config $GIT_ROOT/.gitleaks.toml"
fi

# Use the Python wrapper
gitleaks-safe {gitleaks_args} $CONFIG_ARG

exit_code=$?

# If you have other {hook_name} hooks, add them here
# For example:
# npm test
# rubocop
# etc.

exit $exit_code
"""

        # Write hook file
        hook_path.write_text(hook_content)
        hook_path.chmod(0o755)

        console.print(f"[green]✅ Installed {hook_name} hook[/green]")
        return True


@click.command()
@click.option("--pre-commit", is_flag=True, help="Install pre-commit hook")
@click.option("--pre-push", is_flag=True, help="Install pre-push hook")
@click.option("--both", is_flag=True, help="Install both hooks")
@click.option("--non-interactive", "-n", is_flag=True, help="Don't prompt for input")
def main(pre_commit: bool, pre_push: bool, both: bool, non_interactive: bool):
    """Install memory-safe git hooks for gitleaks."""

    # Print header
    console.print(Panel.fit("[bold blue]🚀 Gitleaks Safe Git Hooks Installer v2.0[/bold blue]\n" "[cyan]Python-based multi-instance support[/cyan]", border_style="blue"))

    # Determine which hooks to install
    if both:
        install_pre_commit = True
        install_pre_push = True
    elif pre_commit:
        install_pre_commit = True
        install_pre_push = False
    elif pre_push:
        install_pre_commit = False
        install_pre_push = True
    else:
        # Default: pre-push only
        install_pre_commit = False
        install_pre_push = True

    # Show current installations
    console.print("\n[blue]📍 Checking for existing gitleaks installations...[/blue]")
    installations = find_gitleaks_installations()

    if installations:
        table = Table(title="Gitleaks Installations Found")
        table.add_column("Path", style="cyan")
        table.add_column("Version", style="green")
        table.add_column("Size", style="yellow")

        for inst in installations:
            table.add_row(inst["path"], inst["version"], inst["size"])

        console.print(table)
    else:
        console.print("[yellow]No gitleaks installations found[/yellow]")

    # Check if gitleaks is in PATH
    if not shutil.which("gitleaks"):
        console.print("\n[yellow]⚠️  Gitleaks is not installed in PATH[/yellow]")

        if non_interactive:
            console.print("[blue]Installing gitleaks automatically...[/blue]")
            should_install = True
        else:
            should_install = Confirm.ask("Would you like to install gitleaks now?", default=False)

        if should_install:
            installer = GitleaksInstaller()
            if installer.install():
                console.print("[green]✅ Gitleaks installation successful[/green]")

                # Verify installation
                result = subprocess.run(["gitleaks", "version"], capture_output=True, text=True)
                if result.returncode == 0:
                    console.print(f"Version: {result.stdout.strip()}")
            else:
                console.print("[red]❌ Failed to install gitleaks[/red]")
                console.print("Please install gitleaks manually and run this installer again.")
                sys.exit(1)
        else:
            console.print("[red]❌ Gitleaks is required[/red]")
            sys.exit(1)
    else:
        console.print("\n[green]✅ Gitleaks is already installed[/green]")
        result = subprocess.run(["gitleaks", "version"], capture_output=True, text=True)
        if result.returncode == 0:
            console.print(f"Version: {result.stdout.strip()}")

    # Check Docker containers
    console.print("\n[blue]🐳 Checking Docker containers...[/blue]")
    docker_containers = check_docker_containers()
    if docker_containers:
        console.print(f"[yellow]Found gitleaks in {len(docker_containers)} container(s)[/yellow]")
        for container in docker_containers:
            console.print(f"  - {container['name']}: {container['count']} process(es)")
    else:
        console.print("[green]No gitleaks processes found in containers[/green]")

    # Install git hooks
    console.print("\n[blue]📝 Installing git hooks...[/blue]")

    hooks_installer = GitHooksInstaller(pre_commit=install_pre_commit, pre_push=install_pre_push)

    if hooks_installer.install():
        console.print("\n[green]✅ Installation complete![/green]")

        # Show what was installed
        console.print("\n[cyan]Installed hooks:[/cyan]")
        if install_pre_commit:
            console.print("  ✓ pre-commit - runs on 'git commit'")
        if install_pre_push:
            console.print("  ✓ pre-push - runs on 'git push'")

        # Show configuration options
        console.print("\n[cyan]Configuration:[/cyan]")
        console.print("  GITLEAKS_TIMEOUT=300     # Increase timeout to 5 minutes")
        console.print("  GITLEAKS_VERBOSE=true    # Enable verbose output")

        # Show usage
        console.print("\n[cyan]Usage:[/cyan]")
        console.print("  Normal git operations will now use safe gitleaks checks")
        console.print("  Manual scan: gitleaks-safe detect --source .")
        console.print("  Cleanup: cleanup-gitleaks")

        console.print("\n[yellow]⚠️  Note:[/yellow] Pre-push hooks are recommended over pre-commit")
        console.print("   to avoid running gitleaks too frequently during development.")
    else:
        console.print("\n[red]❌ Installation failed[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
