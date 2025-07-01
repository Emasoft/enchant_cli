#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Utility functions for gitleaks-safe
"""

import hashlib
import os
import platform
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import psutil
from rich.console import Console
from rich.table import Table

console = Console()

# Constants
SAFE_MARKER = "GITLEAKS_SAFE_INSTANCE"
TIMEOUT_DEFAULT = 120  # 2 minutes
MAX_RETRIES_DEFAULT = 1
LOCKFILE_PREFIX = "gitleaks-safe-"


def get_platform_info() -> Dict[str, str]:
    """Get platform information for OS-specific operations."""
    system = platform.system().lower()

    if system == "darwin":
        return {"os": "macos", "system": system}
    elif system == "linux":
        # Try to detect distribution
        try:
            with open("/etc/os-release") as f:
                for line in f:
                    if line.startswith("ID="):
                        distro = line.strip().split("=")[1].strip('"')
                        return {"os": distro, "system": system}
        except:
            pass
        return {"os": "linux", "system": system}
    elif system == "windows":
        return {"os": "windows", "system": system}
    else:
        return {"os": "unknown", "system": system}


def get_project_hash(path: Optional[Path] = None) -> str:
    """Get a hash of the project path for lockfile naming."""
    if path is None:
        path = Path.cwd()
    return hashlib.md5(str(path).encode()).hexdigest()[:32]


def get_lockfile_path(project_path: Optional[Path] = None) -> Path:
    """Get the lockfile path for the current project."""
    project_hash = get_project_hash(project_path)
    tmpdir = os.environ.get("TMPDIR", "/tmp")
    return Path(tmpdir) / f"{LOCKFILE_PREFIX}{project_hash}.lock"


def is_docker() -> bool:
    """Check if running inside a Docker container."""
    return Path("/.dockerenv").exists() or any("docker" in line for line in Path("/proc/self/cgroup").read_text().splitlines() if Path("/proc/self/cgroup").exists())


def find_gitleaks_installations() -> List[Dict[str, str]]:
    """Find all gitleaks installations on the system."""
    installations = []
    seen_paths = set()

    # Check PATH
    result = subprocess.run(["which", "gitleaks"], capture_output=True, text=True)
    if result.returncode == 0 and result.stdout.strip():
        path = result.stdout.strip()
        if path not in seen_paths:
            seen_paths.add(path)
            installations.append(get_gitleaks_info(path))

    # Common installation locations
    common_paths = [
        "/usr/local/bin/gitleaks",
        "/usr/bin/gitleaks",
        "/opt/homebrew/bin/gitleaks",
        "/home/linuxbrew/.linuxbrew/bin/gitleaks",
        Path.home() / ".local/bin/gitleaks",
        Path.home() / "go/bin/gitleaks",
        "/snap/bin/gitleaks",
        Path.home() / ".cargo/bin/gitleaks",
        "/opt/gitleaks/bin/gitleaks",
    ]

    # Check node_modules
    for i in range(4):  # Check up to 3 levels up
        node_path = Path.cwd() / ("../" * i) / "node_modules/.bin/gitleaks"
        if node_path.exists():
            common_paths.append(node_path.resolve())

    for path in common_paths:
        path = Path(path)
        if path.exists() and path.is_file() and os.access(path, os.X_OK):
            str_path = str(path)
            if str_path not in seen_paths:
                seen_paths.add(str_path)
                installations.append(get_gitleaks_info(str_path))

    return installations


def get_gitleaks_info(path: str) -> Dict[str, str]:
    """Get information about a gitleaks installation."""
    info = {"path": path, "version": "unknown", "size": "unknown"}

    # Get version
    try:
        result = subprocess.run([path, "version"], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            info["version"] = result.stdout.strip()
    except:
        pass

    # Get size
    try:
        size = Path(path).stat().st_size
        info["size"] = format_file_size(size)
    except:
        pass

    return info


def format_file_size(size: int) -> str:
    """Format file size in human-readable format."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024.0:
            return f"{size:.1f}{unit}"
        size /= 1024.0
    return f"{size:.1f}TB"


def is_safe_process(pid: int) -> bool:
    """Check if a process is a safe gitleaks instance."""
    try:
        process = psutil.Process(pid)
        env = process.environ()
        return SAFE_MARKER in env
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return False


def get_gitleaks_processes() -> List[Dict]:
    """Get all gitleaks processes with detailed information."""
    processes = []

    for proc in psutil.process_iter(["pid", "name", "cmdline", "cpu_percent", "memory_percent", "create_time"]):
        try:
            if proc.info["cmdline"] and any("gitleaks" in arg for arg in proc.info["cmdline"]):
                elapsed = time.time() - proc.info["create_time"]
                processes.append({"pid": proc.info["pid"], "cpu": proc.info["cpu_percent"], "memory": proc.info["memory_percent"], "elapsed": format_elapsed_time(elapsed), "command": " ".join(proc.info["cmdline"]), "is_safe": is_safe_process(proc.info["pid"])})
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    return processes


def format_elapsed_time(seconds: float) -> str:
    """Format elapsed time in human-readable format."""
    if seconds < 60:
        return f"{int(seconds)}s"
    elif seconds < 3600:
        return f"{int(seconds // 60)}m {int(seconds % 60)}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"


def kill_process(pid: int, force: bool = False) -> bool:
    """Kill a process by PID."""
    try:
        process = psutil.Process(pid)
        if force:
            process.kill()  # SIGKILL
        else:
            process.terminate()  # SIGTERM
        return True
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return False


def check_docker_containers() -> List[Dict[str, any]]:
    """Check Docker containers for gitleaks processes."""
    containers_with_gitleaks = []

    # Check if docker is available
    try:
        result = subprocess.run(["docker", "--version"], capture_output=True)
        if result.returncode != 0:
            return containers_with_gitleaks
    except FileNotFoundError:
        return containers_with_gitleaks

    # Get running containers
    result = subprocess.run(["docker", "ps", "-q"], capture_output=True, text=True)
    if result.returncode != 0 or not result.stdout.strip():
        return containers_with_gitleaks

    container_ids = result.stdout.strip().split("\n")

    for container_id in container_ids:
        # Get container name
        result = subprocess.run(["docker", "inspect", "-f", "{{.Name}}", container_id], capture_output=True, text=True)
        container_name = result.stdout.strip().lstrip("/")

        # Check for gitleaks processes
        result = subprocess.run(["docker", "exec", container_id, "pgrep", "-f", "gitleaks"], capture_output=True, text=True)

        if result.returncode == 0 and result.stdout.strip():
            pids = result.stdout.strip().split("\n")
            containers_with_gitleaks.append({"id": container_id, "name": container_name, "pids": pids, "count": len(pids)})

    return containers_with_gitleaks


def kill_docker_processes(container_id: str, pids: List[str]) -> bool:
    """Kill gitleaks processes in a Docker container."""
    success = True
    for pid in pids:
        result = subprocess.run(["docker", "exec", container_id, "kill", "-TERM", pid], capture_output=True)
        if result.returncode != 0:
            # Try force kill
            result = subprocess.run(["docker", "exec", container_id, "kill", "-KILL", pid], capture_output=True)
            if result.returncode != 0:
                success = False
    return success


def display_process_table(processes: List[Dict], title: str = "Gitleaks Processes"):
    """Display processes in a nice table format."""
    if not processes:
        console.print(f"[green]✅ No {title.lower()} found[/green]")
        return

    table = Table(title=title)
    table.add_column("PID", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("CPU %", style="yellow")
    table.add_column("MEM %", style="yellow")
    table.add_column("Elapsed", style="blue")
    table.add_column("Command", style="white", overflow="fold")

    for proc in processes:
        status = "✅ SAFE" if proc.get("is_safe", False) else "⚠️  UNSAFE"
        status_style = "green" if proc.get("is_safe", False) else "yellow"

        table.add_row(str(proc["pid"]), f"[{status_style}]{status}[/{status_style}]", f"{proc['cpu']:.1f}", f"{proc['memory']:.1f}", proc["elapsed"], proc["command"][:80] + "..." if len(proc["command"]) > 80 else proc["command"])

    console.print(table)
