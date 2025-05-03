#!/usr/bin/env python3
"""
Process Guardian - Robust process monitoring and control system

This module provides protection against runaway processes, memory leaks,
and duplicate processes spawned during build, publish, lint, and test operations.

Features:
- Process monitoring and resource tracking
- Prevention of duplicate process instances
- Automatic termination of processes exceeding memory limits
- Timeout enforcement for long-running processes
- Process cleanup and reporting
- Watchdog service for continuous monitoring

Usage:
    # Direct usage
    python -m helpers.shell.process_guardian --monitor "bump-my-version" --timeout 900 --max-memory 2048 -- command [args]
    
    # As a context manager in Python scripts
    with ProcessGuardian(process_name="bump-my-version", timeout=900, max_memory_mb=2048):
        subprocess.run(["command", "arg1", "arg2"])
        
    # As a CLI tool
    python -m helpers.shell.process_guardian --list  # List monitored processes
    python -m helpers.shell.process_guardian --kill-all  # Kill all monitored processes
"""

import argparse
import atexit
import gc
import json
import os
import psutil
import queue
import re
import signal
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union, Deque
from collections import deque


# Configuration constants
DEFAULT_TIMEOUT_SECONDS = 900  # 15 minutes
DEFAULT_MAX_MEMORY_MB = 1024  # 1 GB
GUARDIAN_STATE_DIR = os.path.expanduser("~/.process_guardian")
PROCESS_STATE_FILE = os.path.join(GUARDIAN_STATE_DIR, "monitored_processes.json")
PROCESS_LOG_FILE = os.path.join(GUARDIAN_STATE_DIR, "process_guardian.log")
CHECK_INTERVAL_SECONDS = 5  # Check processes every 5 seconds
MAX_CONCURRENT_PROCESSES = 3  # Maximum number of processes to run concurrently
MAX_TOTAL_MEMORY_MB = 3072  # Maximum total memory (3GB) across all processes
MAX_PROCESS_QUEUE_SIZE = 50  # Maximum processes in queue

# Special process type configurations - stricter limits for memory-intensive processes
PROCESS_TYPE_CONFIGS = {
    # Node.js has stricter memory limits
    "node": {
        "max_memory_mb": 768,
        "max_concurrent": 2,
        "priority": 0  # Lower priority (will be queued first)
    },
    # npm has stricter memory limits
    "npm": {
        "max_memory_mb": 768,
        "max_concurrent": 1,
        "priority": 0
    },
    # V8 process (used by Node.js)
    "v8": {
        "max_memory_mb": 768,
        "max_concurrent": 2,
        "priority": 0
    }
}
CRITICAL_PROCESSES = [
    "bump-my-version", 
    "pre-commit",
    "pytest",
    "tox",
    "uv",
    "pip",
    "coverage",
    "black",
    "flake8",
    "ruff",
    "mypy",
    "isort"
]


class ProcessGuardian:
    """
    Process Guardian monitors and controls processes to prevent runaway behavior.
    Uses a thread pool and queue system to limit concurrent processes.
    """
    def __init__(
        self, 
        process_name: str = None, 
        cmd_pattern: str = None,
        timeout: int = DEFAULT_TIMEOUT_SECONDS, 
        max_memory_mb: int = DEFAULT_MAX_MEMORY_MB,
        kill_duplicates: bool = True,
        log_file: str = PROCESS_LOG_FILE,
        max_concurrent: int = MAX_CONCURRENT_PROCESSES,
        max_total_memory_mb: int = MAX_TOTAL_MEMORY_MB
    ):
        """
        Initialize the Process Guardian.
        
        Args:
            process_name: Name of the process to monitor
            cmd_pattern: Command pattern to match (regex)
            timeout: Maximum allowed runtime in seconds
            max_memory_mb: Maximum allowed memory usage in MB
            kill_duplicates: Whether to kill duplicate instances
            log_file: Path to the log file
            max_concurrent: Maximum number of concurrent processes
            max_total_memory_mb: Maximum total memory across all processes
        """
        # Ensure state directory exists
        if not os.path.exists(GUARDIAN_STATE_DIR):
            os.makedirs(GUARDIAN_STATE_DIR, exist_ok=True)
            
        self.process_name = process_name
        self.cmd_pattern = cmd_pattern
        self.timeout = timeout
        self.max_memory_mb = max_memory_mb
        self.kill_duplicates = kill_duplicates
        self.log_file = log_file
        self.max_concurrent = max_concurrent
        self.max_total_memory_mb = max_total_memory_mb
        
        # Thread and process management
        self.monitored_pids = set()
        self.active_processes = {}  # pid -> process info dict
        self.process_queue = deque(maxlen=MAX_PROCESS_QUEUE_SIZE)
        self.lock = threading.Lock()
        self.monitor_thread = None
        self.queue_processor_thread = None
        self.stop_monitoring = threading.Event()
        self.process_pool = ThreadPoolExecutor(max_workers=max_concurrent)
        
        # Register cleanup on exit
        atexit.register(self.cleanup)
        
        # Initialize state
        self._load_state()
        
    def _load_state(self):
        """Load the state of monitored processes from disk."""
        try:
            if os.path.exists(PROCESS_STATE_FILE):
                with open(PROCESS_STATE_FILE, "r") as f:
                    state = json.load(f)
                    # Convert string PIDs back to integers
                    self.monitored_pids = set(int(pid) for pid in state.get("pids", []))
                    
                    # Clean up non-existent processes
                    self._cleanup_dead_processes()
        except Exception as e:
            self.log(f"Error loading state: {e}", level="ERROR")
            self.monitored_pids = set()
    
    def _save_state(self):
        """Save the state of monitored processes to disk."""
        try:
            with self.lock:
                state = {
                    "pids": list(self.monitored_pids),
                    "timestamp": datetime.now().isoformat()
                }
                
                with open(PROCESS_STATE_FILE, "w") as f:
                    json.dump(state, f)
        except Exception as e:
            self.log(f"Error saving state: {e}", level="ERROR")
    
    def _cleanup_dead_processes(self):
        """Remove dead processes from the monitored list."""
        with self.lock:
            active_pids = set()
            for pid in self.monitored_pids:
                try:
                    process = psutil.Process(pid)
                    if process.is_running():
                        active_pids.add(pid)
                except psutil.NoSuchProcess:
                    pass
            
            self.monitored_pids = active_pids
    
    def log(self, message: str, level: str = "INFO"):
        """
        Log a message to the log file.
        
        Args:
            message: The message to log
            level: Log level (INFO, WARNING, ERROR)
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] [{level}] {message}\n"
        
        try:
            with open(self.log_file, "a") as f:
                f.write(log_entry)
        except Exception as e:
            print(f"Error writing to log: {e}", file=sys.stderr)
            print(log_entry, file=sys.stderr)
    
    def _is_critical_process(self, process: psutil.Process) -> bool:
        """
        Check if the process is a critical one that should be monitored.
        
        Args:
            process: The process to check
            
        Returns:
            bool: True if this is a critical process
        """
        process_name = process.name().lower()
        
        # Check for specific process name match
        if self.process_name and self.process_name in process_name:
            return True
            
        # Check for specific command pattern match
        if self.cmd_pattern:
            cmdline = " ".join(process.cmdline())
            if re.search(self.cmd_pattern, cmdline, re.IGNORECASE):
                return True
        
        # Check for Node.js processes that require special monitoring
        for proc_type in PROCESS_TYPE_CONFIGS.keys():
            if proc_type in process_name:
                return True
        
        # Check against list of critical processes
        for critical_process in CRITICAL_PROCESSES:
            if critical_process in process_name:
                return True
                
            cmdline = " ".join(process.cmdline())
            if critical_process in cmdline.lower():
                return True
                
        return False
    
    def _find_duplicate_processes(self, cmd_pattern: str = None) -> List[psutil.Process]:
        """
        Find duplicate process instances for the same command.
        
        Args:
            cmd_pattern: Command pattern to search for
            
        Returns:
            List of duplicate processes
        """
        if not cmd_pattern and not self.cmd_pattern and not self.process_name:
            return []
            
        pattern = cmd_pattern or self.cmd_pattern
        
        # Group processes by command line - use PID as key for more memory-efficient storage
        cmd_groups = {}
        
        # Limit number of processes scanned in a single iteration to avoid memory spikes
        max_processes_per_batch = 50  # Reduced batch size for better memory control
        process_count = 0
        
        # Pre-filter for known process names to reduce scanning overhead
        process_filter = {}
        if self.process_name:
            process_filter['name'] = self.process_name
        
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time']):
            try:
                process_count += 1
                
                # Process in batches to control memory usage
                if process_count > max_processes_per_batch:
                    # Release resources between batches
                    gc.collect()
                    # Sleep a tiny bit to allow other processes to run
                    time.sleep(0.01)
                    process_count = 0
                
                # Skip if no command line (kernel processes, etc.)
                if not proc.info['cmdline']:
                    continue
                
                # Check if this is our monitored process - minimize string operations
                matches = False
                proc_name = proc.info['name'].lower()
                
                # Fast path for name matching
                if self.process_name and self.process_name in proc_name:
                    matches = True
                # Only check pattern if necessary
                elif pattern:
                    # Use first two elements of command line to minimize memory
                    cmd_parts = proc.info['cmdline']
                    if len(cmd_parts) > 0:
                        cmd = cmd_parts[0]
                        if len(cmd_parts) > 1:
                            cmd += " " + cmd_parts[1]
                        
                        if re.search(pattern, cmd, re.IGNORECASE):
                            matches = True
                
                if matches:
                    # Use the first element of cmdline as the signature to save memory
                    cmd_sig = proc.info['cmdline'][0] if proc.info['cmdline'] else ""
                    
                    # Group by command signature - store minimal information
                    if cmd_sig not in cmd_groups:
                        cmd_groups[cmd_sig] = []
                    
                    # Store only essential data, not the whole Process object
                    cmd_groups[cmd_sig].append({
                        'pid': proc.pid,
                        'create_time': proc.info['create_time']
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        # Force garbage collection after scanning
        gc.collect()
                
        # Find duplicates (more than one process with same command)
        duplicates = []
        for cmd_sig, procs in cmd_groups.items():
            if len(procs) > 1:
                # Sort by creation time (oldest first)
                procs.sort(key=lambda p: p['create_time'])
                
                # Keep the first process, mark the rest as duplicates
                for p in procs[1:]:
                    try:
                        # Create Process object only for those we actually need
                        duplicates.append(psutil.Process(p['pid']))
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
        
        # Cleanup to prevent memory leaks
        cmd_groups.clear()
        
        return duplicates
    
    def kill_process(self, pid: int, reason: str = "Unspecified"):
        """
        Kill a process safely with proper logging.
        
        Args:
            pid: The process ID to kill
            reason: Reason for killing the process
        """
        try:
            process = psutil.Process(pid)
            process_info = {
                "name": process.name(),
                "cmdline": " ".join(process.cmdline()),
                "memory_mb": process.memory_info().rss / (1024 * 1024),
                "cpu_percent": process.cpu_percent(),
                "create_time": datetime.fromtimestamp(process.create_time()).strftime('%Y-%m-%d %H:%M:%S'),
                "run_time": str(timedelta(seconds=time.time() - process.create_time()))
            }
            
            self.log(f"Killing process: {pid} ({process.name()}) - {reason}", level="WARNING")
            self.log(f"Process details: {json.dumps(process_info)}", level="INFO")
            
            # Try graceful termination first
            process.terminate()
            
            # Give it some time to exit
            gone, still_alive = psutil.wait_procs([process], timeout=3)
            
            if still_alive:
                # Force kill if still running
                for p in still_alive:
                    self.log(f"Process {p.pid} did not terminate gracefully, killing...", level="WARNING")
                    p.kill()
            
            # Remove from monitored processes
            with self.lock:
                if pid in self.monitored_pids:
                    self.monitored_pids.remove(pid)
                    self._save_state()
                    
            return True
        except psutil.NoSuchProcess:
            self.log(f"Process {pid} not found, may have already terminated", level="INFO")
            
            # Remove from monitored processes if it exists
            with self.lock:
                if pid in self.monitored_pids:
                    self.monitored_pids.remove(pid)
                    self._save_state()
                    
            return True
        except Exception as e:
            self.log(f"Error killing process {pid}: {e}", level="ERROR")
            return False
    
    def kill_processes_by_pattern(self, pattern: str) -> int:
        """
        Kill all processes matching a pattern.
        
        Args:
            pattern: Regular expression pattern to match against command line
            
        Returns:
            Number of processes killed
        """
        killed = 0
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmd = " ".join(proc.info['cmdline'])
                if re.search(pattern, cmd, re.IGNORECASE):
                    if self.kill_process(proc.info['pid'], f"Matched pattern: {pattern}"):
                        killed += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return killed
    
    def _get_process_type_limits(self, process_name):
        """
        Get memory and concurrency limits for a specific process type.
        
        Args:
            process_name: The name of the process
            
        Returns:
            dict: Memory and concurrency limits for this process type
        """
        process_name_lower = process_name.lower()
        
        # Check for process-specific configurations
        for proc_type, config in PROCESS_TYPE_CONFIGS.items():
            if proc_type in process_name_lower:
                return config
        
        # Return default values if no specific config
        return {
            "max_memory_mb": self.max_memory_mb,
            "max_concurrent": self.max_concurrent,
            "priority": 10  # Default priority (higher number = higher priority)
        }
        
    def _count_process_type_running(self, process_type):
        """
        Count how many processes of a specific type are running.
        
        Args:
            process_type: The type of process to count
            
        Returns:
            int: Number of running processes of this type
        """
        count = 0
        for _, info in self.active_processes.items():
            if process_type in info.get('name', '').lower():
                count += 1
        return count
    
    def _process_queue(self):
        """Process the queued processes based on available slots and memory."""
        while not self.stop_monitoring.is_set():
            try:
                # Start with garbage collection to free memory
                gc.collect()
                
                # Calculate current resource usage
                with self.lock:
                    current_processes = len(self.active_processes)
                    
                    # Calculate total memory usage of active processes
                    total_memory_mb = 0
                    pids_to_remove = []
                    
                    # Count processes by type (initialize with empty counters)
                    process_type_counts = {proc_type: 0 for proc_type in PROCESS_TYPE_CONFIGS.keys()}
                    node_processes_count = 0
                    
                    # Process checking in batches to limit memory usage
                    batch_size = 10
                    active_pids = list(self.active_processes.keys())
                    
                    # Process in smaller batches
                    for idx in range(0, len(active_pids), batch_size):
                        # Take a batch of PIDs
                        pid_batch = active_pids[idx:idx+batch_size]
                        
                        for pid in pid_batch:
                            try:
                                if pid not in self.active_processes:
                                    continue
                                    
                                if not psutil.pid_exists(pid):
                                    pids_to_remove.append(pid)
                                    continue
                                    
                                proc = psutil.Process(pid)
                                info = self.active_processes[pid]
                                
                                # Only sample memory every N checks to reduce overhead for well-behaved processes
                                # Use cached value most of the time
                                check_flag = getattr(self, '_memory_check_flag', 0)
                                if check_flag % 3 == 0:  # Sample every 3rd check
                                    try:
                                        memory_mb = proc.memory_info().rss / (1024 * 1024)
                                        # Update the memory info
                                        self.active_processes[pid]['memory_mb'] = memory_mb
                                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                                        # Use previous value if we can't get current
                                        memory_mb = info.get('memory_mb', 0)
                                else:
                                    # Use cached value
                                    memory_mb = info.get('memory_mb', 0)
                                    
                                total_memory_mb += memory_mb
                                
                                # Determine process type and limits
                                proc_name = info.get('name', '').lower()
                                proc_type_limits = self._get_process_type_limits(proc_name)
                                max_memory_for_type = proc_type_limits["max_memory_mb"]
                                
                                # Count by type - only count once per process
                                for proc_type in PROCESS_TYPE_CONFIGS.keys():
                                    if proc_type in proc_name:
                                        process_type_counts[proc_type] += 1
                                        
                                        # Special tracking for Node.js processes
                                        if proc_type in ['node', 'npm', 'v8']:
                                            node_processes_count += 1
                                        
                                        # Don't count multiple process types
                                        break
                                
                                # Check if process exceeds its type-specific memory limit
                                if memory_mb > max_memory_for_type:
                                    self.kill_process(pid, f"Memory limit exceeded: {memory_mb:.2f}MB > {max_memory_for_type}MB (limit for {proc_name})")
                                    pids_to_remove.append(pid)
                                    
                                # Check if process exceeds time limit
                                runtime = time.time() - info.get('start_time', 0)
                                if runtime > self.timeout:
                                    self.kill_process(pid, f"Timeout exceeded: {timedelta(seconds=runtime)} > {timedelta(seconds=self.timeout)}")
                                    pids_to_remove.append(pid)
                            
                            except (psutil.NoSuchProcess, psutil.AccessDenied):
                                pids_to_remove.append(pid)
                        
                        # Update memory check flag
                        self._memory_check_flag = check_flag + 1
                    
                    # Remove terminated processes
                    for pid in pids_to_remove:
                        if pid in self.active_processes:
                            del self.active_processes[pid]
                    
                    # Check if total memory is approaching the limit, kill lowest priority processes if needed
                    if total_memory_mb > self.max_total_memory_mb * 0.85:  # If using more than 85% of allowed memory
                        self.log(f"High memory usage detected: {total_memory_mb:.2f}MB > {self.max_total_memory_mb * 0.85:.2f}MB", level="WARNING")
                        
                        # Sort active processes by priority (lower number = lower priority)
                        # Only build the priority list when needed to save memory
                        processes_by_priority = []
                        for pid, info in self.active_processes.items():
                            proc_name = info.get('name', '').lower()
                            proc_type_limits = self._get_process_type_limits(proc_name)
                            processes_by_priority.append({
                                'pid': pid,
                                'name': proc_name,
                                'priority': proc_type_limits['priority'],
                                'memory_mb': info.get('memory_mb', 0)
                            })
                        
                        # Sort by priority ascending, memory descending
                        processes_by_priority.sort(key=lambda p: (p['priority'], -p['memory_mb']))
                        
                        # Kill lowest priority processes until we're under the threshold
                        for proc in processes_by_priority:
                            if total_memory_mb <= self.max_total_memory_mb * 0.7:  # Stop when under 70%
                                break
                                
                            pid = proc['pid']
                            if pid in self.active_processes:
                                memory_mb = self.active_processes[pid].get('memory_mb', 0)
                                self.kill_process(pid, f"Killed low priority process to free memory (priority={proc['priority']})")
                                total_memory_mb -= memory_mb
                        
                        # Clean up the priority list
                        processes_by_priority.clear()
                    
                    # Check if we can start more processes
                    available_slots = max(0, self.max_concurrent - current_processes)
                    available_memory = max(0, self.max_total_memory_mb - total_memory_mb)
                    
                    # Log resource status less frequently to reduce log size (with rate limiting)
                    # Only log if there are queued processes or if resources are limited
                    current_time = time.time()
                    last_log_time = getattr(self, '_last_queue_log_time', 0)
                    
                    if (self.process_queue and (available_slots == 0 or available_memory < self.max_memory_mb) and 
                            current_time - last_log_time >= 30):  # Log at most every 30 seconds
                        
                        self.log(
                            f"Resource status: {current_processes}/{self.max_concurrent} processes, "
                            f"{total_memory_mb:.2f}MB/{self.max_total_memory_mb}MB memory used, "
                            f"Node.js processes: {node_processes_count}, "
                            f"{len(self.process_queue)} processes queued",
                            level="INFO"
                        )
                        self._last_queue_log_time = current_time
                    
                    # Sort queue by priority if needed - avoid sorting on every iteration
                    queue_sort_needed = getattr(self, '_queue_sort_needed', True)
                    queue_last_modified = getattr(self, '_queue_last_modified', 0)
                    
                    if queue_sort_needed and len(self.process_queue) > 1 and current_time - queue_last_modified >= 10:
                        # Convert to list for sorting
                        queue_list = list(self.process_queue)
                        
                        # Sort by priority (higher number = higher priority)
                        def get_priority(proc_info):
                            proc_name = proc_info.get('name', '').lower()
                            return self._get_process_type_limits(proc_name)['priority']
                            
                        queue_list.sort(key=get_priority, reverse=True)
                        
                        # Update queue
                        self.process_queue = deque(queue_list, maxlen=self.process_queue.maxlen)
                        self._queue_sort_needed = False
                        self._queue_last_modified = current_time
                    
                    # If we have both slots and memory available, start queued processes
                    processes_started = 0
                    retry_queue_items = []
                    
                    # Process only a limited number of queue items per iteration
                    max_queue_items_to_process = min(available_slots, len(self.process_queue), 5)
                    
                    for _ in range(max_queue_items_to_process):
                        if not self.process_queue:
                            break
                            
                        # Get next candidate process from queue
                        process_info = self.process_queue.popleft()
                        pid = process_info['pid']
                        proc_name = process_info.get('name', '').lower()
                        
                        # Skip if process doesn't exist anymore
                        if not psutil.pid_exists(pid):
                            continue
                        
                        # Get process type limits
                        proc_type_limits = self._get_process_type_limits(proc_name)
                        max_memory_for_proc = proc_type_limits["max_memory_mb"]
                        max_concurrent_for_type = proc_type_limits["max_concurrent"]
                        
                        # Check if we have enough memory for this process
                        if available_memory < max_memory_for_proc:
                            # Not enough memory, save for later
                            retry_queue_items.append(process_info)
                            continue
                            
                        # Check if we've reached the limit for this process type
                        skip_for_type_limit = False
                        for proc_type in PROCESS_TYPE_CONFIGS.keys():
                            if proc_type in proc_name:
                                type_count = process_type_counts.get(proc_type, 0)
                                if type_count >= max_concurrent_for_type:
                                    self.log(f"Reached concurrency limit for {proc_type} processes: {type_count}/{max_concurrent_for_type}", level="INFO")
                                    # Skip but keep in queue
                                    retry_queue_items.append(process_info)
                                    skip_for_type_limit = True
                                    break
                                    
                        if skip_for_type_limit:
                            continue
                        
                        # If we got here, we can run this process
                        # Add to active processes
                        self.active_processes[pid] = {
                            'name': process_info['name'],
                            'cmdline': process_info['cmdline'],
                            'memory_mb': process_info.get('memory_mb', 0),
                            'start_time': time.time()
                        }
                        
                        # Update process counts
                        for proc_type in PROCESS_TYPE_CONFIGS.keys():
                            if proc_type in proc_name:
                                process_type_counts[proc_type] += 1
                                break
                        
                        self.log(f"Started queued process: {pid} ({process_info['name']}) - {process_info['cmdline']}")
                        
                        # Update available resources
                        available_slots -= 1
                        available_memory -= max_memory_for_proc
                        processes_started += 1
                        
                        # Mark queue as needing re-sort
                        self._queue_sort_needed = True
                    
                    # Add back processes we couldn't start
                    for item in retry_queue_items:
                        self.process_queue.append(item)
                    
                    # Clean up
                    retry_queue_items.clear()
                        
                # Save state after queue processing, but not on every iteration
                if processes_started > 0 or len(pids_to_remove) > 0:
                    self._save_state()
                
            except Exception as e:
                self.log(f"Error in queue processor thread: {e}", level="ERROR")
                import traceback
                self.log(traceback.format_exc(), level="ERROR")
                
            # Wait before checking again - use a slightly longer interval
            # to reduce CPU usage for queue processing
            self.stop_monitoring.wait(CHECK_INTERVAL_SECONDS * 0.75)
    
    def monitor_processes(self):
        """Monitor processes and enforce limits."""
        while not self.stop_monitoring.is_set():
            try:
                # Free up memory before scanning
                gc.collect()
                
                # Calculate current resource usage
                with self.lock:
                    total_memory_mb = sum(info.get('memory_mb', 0) for info in self.active_processes.values())
                
                # Limit number of processes scanned in a single iteration to avoid memory spikes
                max_processes_per_batch = 50
                process_count = 0
                
                # Check all processes in the system
                for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'memory_info', 'create_time']):
                    try:
                        process_count += 1
                        
                        # Process in batches to control memory usage
                        if process_count > max_processes_per_batch:
                            # Release resources between batches
                            gc.collect()
                            # Wait a bit to allow memory stabilization
                            time.sleep(0.1)
                            process_count = 0
                        
                        # Skip if it's not our process
                        if not self._is_critical_process(proc):
                            continue
                            
                        pid = proc.pid
                        
                        # Skip if already monitored
                        with self.lock:
                            if pid in self.monitored_pids:
                                continue
                        
                        # Get process info
                        try:
                            memory_mb = proc.memory_info().rss / (1024 * 1024)
                            cmd_parts = proc.cmdline()
                            cmd_str = " ".join(cmd_parts[:2]) + ("..." if len(cmd_parts) > 2 else "")
                            name = proc.name()
                            create_time = proc.create_time()
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            continue
                        
                        # Add to monitored processes
                        with self.lock:
                            self.monitored_pids.add(pid)
                            
                            # Create process info dict
                            process_info = {
                                'pid': pid,
                                'name': name,
                                'cmdline': cmd_str,
                                'memory_mb': memory_mb,
                                'create_time': create_time
                            }
                            
                            # Check if we have resources to run this process immediately
                            if (len(self.active_processes) < self.max_concurrent and 
                                total_memory_mb + memory_mb <= self.max_total_memory_mb):
                                
                                # Add to active processes
                                self.active_processes[pid] = {
                                    'name': name,
                                    'cmdline': cmd_str,
                                    'memory_mb': memory_mb,
                                    'start_time': time.time()
                                }
                                
                                total_memory_mb += memory_mb
                                self.log(f"Started monitoring process: {pid} ({name}) - {cmd_str}")
                            else:
                                # Add to queue if not full
                                if len(self.process_queue) < self.process_queue.maxlen:
                                    self.process_queue.append(process_info)
                                    self.log(f"Queued process for later execution: {pid} ({name}) - {cmd_str}")
                                else:
                                    # Queue is full, need to kill this process
                                    self.kill_process(pid, "Process queue full, cannot accommodate more processes")
                        
                        # Save state periodically
                        self._save_state()
                            
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
                        
                # Free up memory before handling duplicates
                gc.collect()
                
                # Handle duplicate processes if needed, but limit frequency
                if self.kill_duplicates:
                    duplicates = self._find_duplicate_processes()
                    for proc in duplicates:
                        self.kill_process(proc.pid, "Duplicate process instance")
                
                # Clean up dead processes
                self._cleanup_dead_processes()
                
                # Save state
                self._save_state()
                
            except Exception as e:
                self.log(f"Error in monitor thread: {e}", level="ERROR")
                import traceback
                self.log(traceback.format_exc(), level="ERROR")
                
            # Wait before checking again
            self.stop_monitoring.wait(CHECK_INTERVAL_SECONDS)
    
    def start_monitoring(self):
        """Start the monitoring and queue processor threads."""
        if self.monitor_thread is None or not self.monitor_thread.is_alive():
            self.stop_monitoring.clear()
            self.monitor_thread = threading.Thread(target=self.monitor_processes, daemon=True)
            self.monitor_thread.start()
            self.log("Started monitoring thread")
            
        if self.queue_processor_thread is None or not self.queue_processor_thread.is_alive():
            self.queue_processor_thread = threading.Thread(target=self._process_queue, daemon=True)
            self.queue_processor_thread.start()
            self.log("Started queue processor thread")
    
    def stop_monitoring_thread(self):
        """Stop the monitoring and queue processor threads."""
        if self.stop_monitoring is not None:
            self.stop_monitoring.set()
            
        if self.monitor_thread and self.monitor_thread.is_alive():
            try:
                self.monitor_thread.join(timeout=10)
                self.log("Stopped monitoring thread")
            except Exception as e:
                self.log(f"Error stopping monitoring thread: {e}", level="ERROR")
            
        if self.queue_processor_thread and self.queue_processor_thread.is_alive():
            try:
                self.queue_processor_thread.join(timeout=10)
                self.log("Stopped queue processor thread")
            except Exception as e:
                self.log(f"Error stopping queue processor thread: {e}", level="ERROR")
    
    def cleanup(self):
        """Clean up resources."""
        try:
            # Stop all threads
            self.stop_monitoring_thread()
            
            # Shutdown thread pool
            if hasattr(self, 'process_pool') and self.process_pool:
                self.process_pool.shutdown(wait=False)
                
            # Save final state
            self._save_state()
            
            # Release memory
            gc.collect()
            
        except Exception as e:
            self.log(f"Error during cleanup: {e}", level="ERROR")
            import traceback
            self.log(traceback.format_exc(), level="ERROR")
    
    def __enter__(self):
        """Start monitoring when used as a context manager."""
        self.start_monitoring()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop monitoring when exiting the context manager."""
        self.cleanup()
        
    @classmethod
    def kill_all_monitored(cls):
        """Kill all currently monitored processes."""
        guardian = cls()
        count = 0
        
        with guardian.lock:
            for pid in list(guardian.monitored_pids):
                if guardian.kill_process(pid, "Manual kill_all_monitored request"):
                    count += 1
                    
        guardian.log(f"Killed {count} monitored processes")
        return count
    
    @classmethod
    def list_monitored(cls):
        """List all currently monitored processes."""
        guardian = cls()
        processes = []
        
        with guardian.lock:
            # Make a copy of the pids set to avoid modification during iteration
            pids_to_check = list(guardian.monitored_pids)
            
        # Process in smaller batches to limit memory usage
        batch_size = 20
        for i in range(0, len(pids_to_check), batch_size):
            batch = pids_to_check[i:i+batch_size]
            for pid in batch:
                try:
                    proc = psutil.Process(pid)
                    # Get command line with truncation to avoid excessive memory usage
                    cmd_parts = proc.cmdline()
                    cmd_str = " ".join(cmd_parts[:2]) + ("..." if len(cmd_parts) > 2 else "")
                    
                    processes.append({
                        "pid": pid,
                        "name": proc.name(),
                        "cmdline": cmd_str,
                        "memory_mb": proc.memory_info().rss / (1024 * 1024),
                        "cpu_percent": proc.cpu_percent(),
                        "create_time": datetime.fromtimestamp(proc.create_time()).strftime('%Y-%m-%d %H:%M:%S'),
                        "run_time": str(timedelta(seconds=time.time() - proc.create_time()))
                    })
                except psutil.NoSuchProcess:
                    # Remove non-existent process
                    with guardian.lock:
                        if pid in guardian.monitored_pids:
                            guardian.monitored_pids.remove(pid)
            
            # Force garbage collection between batches
            gc.collect()
            
        # Save state after processing
        guardian._save_state()
        return processes


def process_guardian_wrapper(args=None):
    """
    Command-line interface for ProcessGuardian.
    
    Args:
        args: Command line arguments
    """
    parser = argparse.ArgumentParser(description='Process Guardian - Monitor and control processes')
    
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--monitor', help='Process name to monitor')
    group.add_argument('--cmd-pattern', help='Command line pattern to monitor (regex)')
    group.add_argument('--list', action='store_true', help='List monitored processes')
    group.add_argument('--kill-all', action='store_true', help='Kill all monitored processes')
    
    parser.add_argument('--timeout', type=int, default=DEFAULT_TIMEOUT_SECONDS, 
                        help=f'Maximum allowed runtime in seconds (default: {DEFAULT_TIMEOUT_SECONDS}s)')
    parser.add_argument('--max-memory', type=int, default=DEFAULT_MAX_MEMORY_MB, 
                        help=f'Maximum allowed memory usage in MB (default: {DEFAULT_MAX_MEMORY_MB}MB)')
    parser.add_argument('--max-concurrent', type=int, default=MAX_CONCURRENT_PROCESSES,
                        help=f'Maximum number of concurrent processes (default: {MAX_CONCURRENT_PROCESSES})')
    parser.add_argument('--max-total-memory', type=int, default=MAX_TOTAL_MEMORY_MB,
                        help=f'Maximum total memory across all processes in MB (default: {MAX_TOTAL_MEMORY_MB}MB)')
    parser.add_argument('--no-kill-duplicates', action='store_true', 
                        help='Do not kill duplicate process instances')
    parser.add_argument('--log-file', default=PROCESS_LOG_FILE, 
                        help=f'Path to the log file (default: {PROCESS_LOG_FILE})')
    parser.add_argument('command', nargs='*', help='Command to execute with arguments')
    
    if args is None:
        args = parser.parse_args()
    else:
        args = parser.parse_args(args)
    
    if args.list:
        processes = ProcessGuardian.list_monitored()
        if processes:
            print(f"Monitored Processes ({len(processes)}):")
            for i, proc in enumerate(processes, 1):
                print(f"{i}. PID: {proc['pid']} - {proc['name']}")
                print(f"   Command: {proc['cmdline']}")
                print(f"   Memory: {proc['memory_mb']:.2f} MB")
                print(f"   CPU: {proc['cpu_percent']:.1f}%")
                print(f"   Started: {proc['create_time']}")
                print(f"   Running for: {proc['run_time']}")
                print()
        else:
            print("No monitored processes found")
        return 0
    
    if args.kill_all:
        count = ProcessGuardian.kill_all_monitored()
        print(f"Killed {count} monitored processes")
        return 0
    
    # Start Process Guardian
    guardian = ProcessGuardian(
        process_name=args.monitor,
        cmd_pattern=args.cmd_pattern,
        timeout=args.timeout,
        max_memory_mb=args.max_memory,
        max_concurrent=args.max_concurrent,
        max_total_memory_mb=args.max_total_memory,
        kill_duplicates=not args.no_kill_duplicates,
        log_file=args.log_file
    )
    
    # Start monitoring thread
    guardian.start_monitoring()
    
    # Run command if provided
    if args.command:
        try:
            cmd = args.command
            print(f"Running command: {' '.join(cmd)}")
            
            # Run the process and wait for it to complete
            process = subprocess.Popen(cmd)
            
            # Add process to monitored list
            with guardian.lock:
                guardian.monitored_pids.add(process.pid)
                guardian._save_state()
            
            # Wait for the process to complete
            exit_code = process.wait()
            
            return exit_code
        except KeyboardInterrupt:
            print("Process interrupted by user")
            return 130  # Standard exit code for SIGINT
        except Exception as e:
            print(f"Error running command: {e}")
            return 1
        finally:
            # Clean up the guardian
            guardian.cleanup()
    else:
        # Just run the monitor in the foreground
        try:
            print("Process Guardian is running in the foreground (Ctrl+C to exit)")
            print(f"Monitoring: {'Processes: ' + args.monitor if args.monitor else 'Pattern: ' + args.cmd_pattern if args.cmd_pattern else 'All critical processes'}")
            print(f"Timeout: {timedelta(seconds=args.timeout)}, Max Memory: {args.max_memory} MB")
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nProcess Guardian stopped by user")
        finally:
            guardian.cleanup()
            
    return 0


if __name__ == "__main__":
    sys.exit(process_guardian_wrapper())