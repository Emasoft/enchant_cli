#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Gitleaks wrapper functionality
"""

import os
import signal
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from rich.console import Console

from .utils import (
    SAFE_MARKER,
    TIMEOUT_DEFAULT,
    console,
    get_gitleaks_processes,
    get_lockfile_path,
    get_project_hash,
    is_safe_process,
    kill_process,
)


class GitleaksWrapper:
    """Memory-safe wrapper for gitleaks."""

    def __init__(self, timeout: int = TIMEOUT_DEFAULT, verbose: bool = False, max_retries: int = 1):
        self.timeout = timeout
        self.verbose = verbose
        self.max_retries = max_retries
        self.session_id = self._generate_session_id()
        self.lockfile = get_lockfile_path()

    def _generate_session_id(self) -> str:
        """Generate unique session ID."""
        timestamp = int(datetime.now().timestamp())
        pid = os.getpid()
        project_hash = get_project_hash()[:8]
        return f"{timestamp}-{pid}-{project_hash}"

    def _check_running(self) -> bool:
        """Check if gitleaks is already running for this directory."""
        if self.lockfile.exists():
            try:
                with open(self.lockfile, "r") as f:
                    pid = int(f.read().strip())
                # Check if process is still alive
                os.kill(pid, 0)
                # Check if it's a safe process
                if is_safe_process(pid):
                    return True
                else:
                    # Not a safe process, remove stale lock
                    self.lockfile.unlink()
            except (OSError, ValueError):
                # Process doesn't exist or invalid PID
                self.lockfile.unlink()
        return False

    def _create_lockfile(self):
        """Create lockfile with current PID."""
        self.lockfile.write_text(str(os.getpid()))

    def _cleanup(self):
        """Clean up lockfile."""
        try:
            self.lockfile.unlink()
        except FileNotFoundError:
            pass

    def _kill_unsafe_processes(self):
        """Kill only unsafe gitleaks processes."""
        processes = get_gitleaks_processes()

        if not processes:
            console.print("[green]✅ No gitleaks processes found[/green]")
            return

        unsafe_processes = [p for p in processes if not p["is_safe"] and p["pid"] != os.getpid()]
        safe_processes = [p for p in processes if p["is_safe"]]

        console.print("\n[cyan]Found processes:[/cyan]")
        for proc in processes:
            if proc["pid"] == os.getpid():
                continue

            if proc["is_safe"]:
                console.print(f"  [green]✅ PID {proc['pid']}: SAFE (managed by gitleaks-safe)[/green]")
            else:
                console.print(f"  [yellow]⚠️  PID {proc['pid']}: UNSAFE[/yellow]")
                console.print(f"     CPU: {proc['cpu']:.1f}% | MEM: {proc['memory']:.1f}% | Elapsed: {proc['elapsed']}")

        console.print(f"\n[cyan]Summary: {len(safe_processes)} safe, {len(unsafe_processes)} unsafe processes[/cyan]")

        if unsafe_processes:
            console.print(f"[yellow]⚠️  Terminating {len(unsafe_processes)} unsafe gitleaks process(es)...[/yellow]")

            for proc in unsafe_processes:
                if kill_process(proc["pid"]):
                    console.print(f"  Terminated PID {proc['pid']}")
                else:
                    console.print(f"  [red]Failed to terminate PID {proc['pid']}[/red]")

            # Wait and force kill if needed
            time.sleep(1)
            remaining = [p for p in unsafe_processes if is_process_alive(p["pid"])]

            for proc in remaining:
                console.print(f"  [yellow]Force killing PID {proc['pid']}...[/yellow]")
                kill_process(proc["pid"], force=True)

            console.print("[green]✅ Cleaned up unsafe gitleaks processes[/green]")
        else:
            console.print("[green]✅ No unsafe processes to clean up[/green]")

    def run(self, args: List[str]) -> int:
        """Run gitleaks with safety wrapper."""
        console.print("[blue]🛡️  Gitleaks Safe Wrapper v2.0[/blue]")
        console.print(f"[cyan]Session ID: {self.session_id}[/cyan]")
        console.print(f"[cyan]Project: {Path.cwd()}[/cyan]\n")

        # Check if gitleaks is installed
        if not self._check_gitleaks_installed():
            return 1

        # Check if already running
        if self._check_running():
            console.print("[yellow]⚠️  A safe gitleaks instance is already running for this repository[/yellow]")
            console.print(f"Lock file: {self.lockfile}")
            console.print("If this is an error, remove the lock file and try again")
            return 1

        # Kill unsafe processes
        console.print("[blue]🔍 Scanning for unsafe gitleaks processes...[/blue]")
        self._kill_unsafe_processes()
        console.print()

        # Create lockfile
        self._create_lockfile()

        try:
            # Prepare command with safe marker
            env = os.environ.copy()
            env[SAFE_MARKER] = self.session_id

            cmd = ["gitleaks"]
            if self.verbose:
                cmd.append("--verbose")
            cmd.extend(args)

            console.print("[green]🔍 Running safe gitleaks scan...[/green]")
            console.print(f"Timeout: {self.timeout}s | Verbose: {self.verbose}")
            console.print(f"Command: {' '.join(cmd)}\n")

            # Run with retries
            for attempt in range(1, self.max_retries + 1):
                if attempt > 1:
                    console.print(f"[yellow]⚠️  Retry attempt {attempt} of {self.max_retries}[/yellow]")

                try:
                    result = subprocess.run(cmd, env=env, timeout=self.timeout, capture_output=False)

                    if result.returncode == 0:
                        console.print("[green]✅ No secrets detected by gitleaks[/green]")
                        return 0
                    else:
                        if attempt == self.max_retries:
                            console.print("[red]❌ Gitleaks detected potential secrets or encountered an error[/red]")
                            console.print(f"Exit code: {result.returncode}\n")
                            console.print("Please review the findings and either:")
                            console.print("1. Remove the secrets from your code")
                            console.print("2. Add false positives to .gitleaks.toml allowlist")
                            console.print("3. Run with verbose mode: GITLEAKS_VERBOSE=true")
                            return result.returncode

                except subprocess.TimeoutExpired:
                    console.print(f"[red]❌ Gitleaks scan timed out after {self.timeout} seconds[/red]")
                    console.print("You can increase the timeout by setting: export GITLEAKS_TIMEOUT=300")
                    return 124

        finally:
            self._cleanup()

        return 1

    def _check_gitleaks_installed(self) -> bool:
        """Check if gitleaks is installed."""
        try:
            subprocess.run(["gitleaks", "--version"], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            console.print("[red]❌ gitleaks is not installed in PATH[/red]")
            console.print("Please install it using one of these methods:\n")
            console.print("macOS:        brew install gitleaks")
            console.print("Ubuntu/Debian: sudo snap install gitleaks")
            console.print("Fedora:       sudo dnf install gitleaks")
            console.print("Arch:         yay -S gitleaks")
            console.print("Windows:      scoop install gitleaks\n")
            return False


def is_process_alive(pid: int) -> bool:
    """Check if a process is still alive."""
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False
