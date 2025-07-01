#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Cleanup utility for gitleaks processes
"""

import os
import sys
import time
from pathlib import Path
from typing import List

import click
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm
from rich.table import Table

from .utils import (
    check_docker_containers,
    display_process_table,
    find_gitleaks_installations,
    get_gitleaks_processes,
    kill_docker_processes,
    kill_process,
)

console = Console()


def cleanup_orphaned_lockfiles() -> int:
    """Clean up orphaned lock files."""
    tmpdir = Path(os.environ.get("TMPDIR", "/tmp"))
    lockfiles = list(tmpdir.glob("gitleaks-safe-*.lock"))

    orphaned = 0
    for lockfile in lockfiles:
        try:
            with open(lockfile, "r") as f:
                pid = int(f.read().strip())

            # Check if process exists
            try:
                os.kill(pid, 0)
            except OSError:
                # Process doesn't exist, remove lockfile
                lockfile.unlink()
                orphaned += 1
        except (ValueError, FileNotFoundError):
            # Invalid or missing lockfile
            try:
                lockfile.unlink()
                orphaned += 1
            except:
                pass

    return orphaned


@click.command()
@click.option("--force", "-f", is_flag=True, help="Skip confirmation prompts")
@click.option("--all", "-a", is_flag=True, help="Kill all gitleaks processes (including safe ones)")
def main(force: bool, all: bool):
    """Clean up gitleaks processes to prevent memory exhaustion."""

    # Print header
    console.print(Panel.fit("[bold blue]🧹 Gitleaks Process Cleanup Utility v2.0[/bold blue]\n" "[cyan]Smart cleanup that preserves safe instances[/cyan]", border_style="blue"))

    # Find installations
    console.print("\n[blue]📍 Gitleaks Installations:[/blue]")
    installations = find_gitleaks_installations()

    if installations:
        table = Table()
        table.add_column("Path", style="cyan")
        table.add_column("Version", style="green")
        table.add_column("Size", style="yellow")

        for inst in installations:
            table.add_row(inst["path"], inst["version"], inst["size"])

        console.print(table)
    else:
        console.print("[yellow]No gitleaks installations found[/yellow]")

    # Check Docker containers
    console.print("\n[blue]🐳 Docker Containers:[/blue]")
    docker_containers = check_docker_containers()

    if docker_containers:
        total_docker_processes = sum(c["count"] for c in docker_containers)
        console.print(f"[yellow]Found {total_docker_processes} gitleaks process(es) in {len(docker_containers)} container(s)[/yellow]")

        for container in docker_containers:
            console.print(f"  - {container['name']}: {container['count']} process(es)")
    else:
        console.print("[green]No gitleaks processes found in containers[/green]")

    # Get all gitleaks processes
    console.print("\n[blue]📊 Process Analysis:[/blue]")
    processes = get_gitleaks_processes()

    if not processes:
        console.print("[green]✅ No gitleaks processes found running[/green]")

        # Clean up orphaned lockfiles
        orphaned = cleanup_orphaned_lockfiles()
        if orphaned > 0:
            console.print(f"\n[green]✅ Cleaned up {orphaned} orphaned lock file(s)[/green]")

        return

    # Separate safe and unsafe processes
    safe_processes = [p for p in processes if p["is_safe"]]
    unsafe_processes = [p for p in processes if not p["is_safe"]]

    # Display processes
    if safe_processes:
        console.print(f"\n[cyan]Safe Processes ({len(safe_processes)}):[/cyan]")
        display_process_table(safe_processes, "Safe Processes")

    if unsafe_processes:
        console.print(f"\n[yellow]Unsafe Processes ({len(unsafe_processes)}):[/yellow]")
        display_process_table(unsafe_processes, "Unsafe Processes")

        # Calculate total memory
        total_mem = sum(p["memory"] for p in unsafe_processes)
        console.print(f"\n[yellow]Total memory usage by unsafe processes: {total_mem:.1f}%[/yellow]")

    # Determine what to kill
    if all:
        processes_to_kill = processes
        kill_message = f"terminate ALL {len(processes_to_kill)} gitleaks process(es)"
    else:
        processes_to_kill = unsafe_processes
        kill_message = f"terminate {len(processes_to_kill)} UNSAFE gitleaks process(es)"

    if not processes_to_kill:
        console.print("\n[green]✅ All running gitleaks processes are safe instances[/green]")
        console.print("No cleanup needed.")

        # Clean up orphaned lockfiles
        orphaned = cleanup_orphaned_lockfiles()
        if orphaned > 0:
            console.print(f"\n[green]✅ Cleaned up {orphaned} orphaned lock file(s)[/green]")

        return

    # Ask for confirmation
    if force or Confirm.ask(f"\nDo you want to {kill_message}?", default=False):
        console.print(f"\n[yellow]Terminating {'all' if all else 'unsafe'} processes...[/yellow]")

        # Kill processes
        for proc in processes_to_kill:
            if kill_process(proc["pid"]):
                console.print(f"  Terminated PID {proc['pid']}")
            else:
                console.print(f"  [red]Failed to terminate PID {proc['pid']}[/red]")

        # Wait and force kill if needed
        time.sleep(2)

        still_alive = []
        for proc in processes_to_kill:
            try:
                os.kill(proc["pid"], 0)
                still_alive.append(proc)
            except OSError:
                pass

        for proc in still_alive:
            console.print(f"  [yellow]Force killing PID {proc['pid']}...[/yellow]")
            kill_process(proc["pid"], force=True)

        console.print("[green]✅ Successfully terminated processes[/green]")

        # Clean up orphaned lockfiles
        console.print("\n[blue]Cleaning up orphaned lock files...[/blue]")
        orphaned = cleanup_orphaned_lockfiles()
        console.print(f"[green]✅ Cleaned up {orphaned} orphaned lock file(s)[/green]")
    else:
        console.print("[blue]Cancelled. No processes were terminated.[/blue]")

    # Docker cleanup
    if docker_containers and (force or Confirm.ask("\nAlso clean up gitleaks in Docker containers?", default=False)):
        console.print("\n[yellow]Cleaning Docker containers...[/yellow]")

        for container in docker_containers:
            console.print(f"  Cleaning container: {container['name']}")
            if kill_docker_processes(container["id"], container["pids"]):
                console.print("    [green]✓ Cleaned[/green]")
            else:
                console.print("    [red]✗ Failed[/red]")

        console.print("[green]✅ Docker containers cleaned[/green]")

    # Tips
    console.print("\n[blue]💡 Tips:[/blue]")
    console.print("- Use 'gitleaks-safe' to run gitleaks safely")
    console.print("- Safe instances can run concurrently across multiple projects")
    console.print("- Set GITLEAKS_TIMEOUT to increase scan timeout")
    console.print("- Install git hooks: install-safe-git-hooks")


if __name__ == "__main__":
    import os

    main()
