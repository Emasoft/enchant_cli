#!/usr/bin/env python3
"""
Process Guardian Watchdog Service - Portable Version

This script provides targeted monitoring for Node.js and Python processes spawned
by the current project only. It automatically starts when a process
is launched and stops when all monitored processes terminate.

This approach is more efficient and less invasive than a system-wide
watchdog service, while remaining portable across different projects.

Usage:
    This script can be called directly or from wrapper scripts:
    python process-guardian-watchdog.py {start|run|register|unregister|stop|status}
"""

import os
import sys
import time
import signal
import importlib.util
import psutil
from pathlib import Path

# Determine script directory and project root
SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = None

# Try to find project root by looking for common project markers
current_dir = SCRIPT_DIR
while current_dir != current_dir.parent:
    if (current_dir / ".git").exists() or \
       (current_dir / "pyproject.toml").exists() or \
       (current_dir / "package.json").exists():
        PROJECT_ROOT = current_dir
        break
    current_dir = current_dir.parent

# Fall back to parent of script directory if no project root found
if PROJECT_ROOT is None:
    PROJECT_ROOT = SCRIPT_DIR.parent

# Store the SCRIPT_DIR as DHT_DIR and DHTL_DIR as parent
DHT_DIR = SCRIPT_DIR
DHTL_DIR = SCRIPT_DIR.parent

# Add potential module paths to Python path
paths_to_check = [
    str(SCRIPT_DIR),                     # Current script directory
    str(SCRIPT_DIR.parent),              # Parent directory
    str(PROJECT_ROOT),                   # Project root
    str(PROJECT_ROOT / "helpers"),       # Project helpers directory
    str(SCRIPT_DIR.parent / "helpers"),  # Parent helpers directory
    str(PROJECT_ROOT / "DHT"),           # Project DHT directory
    str(PROJECT_ROOT / "DHT" / "helpers")  # DHT helpers directory
]

# Add unique paths to Python path
for path in paths_to_check:
    if path not in sys.path and os.path.exists(path):
        sys.path.insert(0, path)

# Try to import ProcessGuardian from various possible locations
ProcessGuardian = None
import_locations = [
    "helpers.shell.process_guardian",
    "shell.process_guardian",
    "process_guardian",
    "DHT.helpers.shell.process_guardian",
    "DHT.process_guardian"
]

for module_path in import_locations:
    try:
        module = importlib.import_module(module_path)
        if hasattr(module, "ProcessGuardian"):
            ProcessGuardian = module.ProcessGuardian
            break
    except ImportError:
        continue

# If ProcessGuardian couldn't be imported, define a basic implementation
if ProcessGuardian is None:
    class ProcessGuardian:
        """
        Fallback ProcessGuardian implementation when the full version is not available.
        This provides basic process monitoring and control functionality.
        """
        def __init__(
            self, 
            timeout=900,
            max_memory_mb=1024,
            max_concurrent=3,
            max_total_memory_mb=3072,
            kill_duplicates=True,
            log_file=None
        ):
            """Initialize the fallback Process Guardian."""
            self.timeout = timeout
            self.max_memory_mb = max_memory_mb
            self.max_concurrent = max_concurrent
            self.max_total_memory_mb = max_total_memory_mb
            self.kill_duplicates = kill_duplicates
            self.log_file = log_file or os.path.join(os.path.expanduser("~"), ".process_guardian", "guardian.log")
            
            # Ensure log directory exists
            os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
            
            # Process tracking
            self.monitored_pids = set()
            
            # Configuration for different process types
            self.PROCESS_TYPE_CONFIGS = {
                "node": {
                    "max_memory_mb": 768,
                    "max_concurrent": 2,
                    "priority": 0
                },
                "python": {
                    "max_memory_mb": 512,
                    "max_concurrent": 3,
                    "priority": 5
                }
            }
            
            self.log("Initialized fallback ProcessGuardian (limited functionality)")
        
        def log(self, message, level="INFO"):
            """Log a message to the log file."""
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            log_entry = f"[{timestamp}] [{level}] {message}\n"
            
            try:
                with open(self.log_file, "a") as f:
                    f.write(log_entry)
            except Exception as e:
                print(f"Error writing to log: {e}", file=sys.stderr)
                print(log_entry, file=sys.stderr)
        
        def start_monitoring(self):
            """Start the monitoring process."""
            self.log("Started monitoring processes (fallback mode)")
        
        def cleanup(self):
            """Clean up resources."""
            self.log("Cleaned up resources (fallback mode)")

# Configuration with environment variable support
# Look for a .dhtl_cache directory in the project root or create a hidden dir in the script directory
CACHE_DIR = os.environ.get('DHTL_CACHE_DIR') or (
    PROJECT_ROOT / ".dhtl_cache" if (PROJECT_ROOT / ".dhtl_cache").exists() 
    else os.path.join(SCRIPT_DIR, ".process_guardian")
)
GUARDIAN_DIR = os.environ.get('DHTL_GUARDIAN_DIR') or CACHE_DIR
os.makedirs(GUARDIAN_DIR, exist_ok=True)

# Set up the process guardian directory to be specific to this project to avoid conflicts
GUARDIAN_LOG_DIR = os.path.join(GUARDIAN_DIR, "logs")
os.makedirs(GUARDIAN_LOG_DIR, exist_ok=True)

# Configuration files
PID_FILE = os.path.join(GUARDIAN_DIR, "process_watchdog.pid")
LOG_FILE = os.path.join(GUARDIAN_DIR, "process_watchdog.log")
ACTIVE_NODES_FILE = os.path.join(GUARDIAN_DIR, "active_nodes.txt")
ACTIVE_PYTHON_SCRIPTS_FILE = os.path.join(GUARDIAN_DIR, "active_py_scripts.txt")

# More conservative memory limits to optimize resource usage
# Process type configurations (with environment variable overrides)
NODE_CONFIG = {
    "memory_limit": int(os.environ.get('DHTL_NODE_MEMORY_LIMIT', 512)),      # MB (reduced from 768)
    "max_concurrent": int(os.environ.get('DHTL_NODE_MAX_CONCURRENT', 2)),    # count
    "max_total_memory": int(os.environ.get('DHTL_NODE_TOTAL_MEMORY', 1536))  # MB (reduced from 2048)
}

PYTHON_DEV_CONFIG = {
    "memory_limit": int(os.environ.get('DHTL_PYTHON_MEMORY_LIMIT', 384)),    # MB (reduced from 512)
    "max_concurrent": int(os.environ.get('DHTL_PYTHON_MAX_CONCURRENT', 3)),  # count
    "max_total_memory": int(os.environ.get('DHTL_PYTHON_TOTAL_MEMORY', 1152)) # MB (reduced from 1536)
}

def ensure_guardian_dir():
    """Ensure the guardian directory exists."""
    os.makedirs(GUARDIAN_DIR, exist_ok=True)

def read_active_nodes():
    """Read the list of active Node.js PIDs."""
    if not os.path.exists(ACTIVE_NODES_FILE):
        return []
    
    try:
        with open(ACTIVE_NODES_FILE, 'r') as f:
            return [int(line.strip()) for line in f.readlines() if line.strip().isdigit()]
    except Exception:
        return []

def write_active_nodes(pids):
    """Write the list of active Node.js PIDs."""
    ensure_guardian_dir()
    with open(ACTIVE_NODES_FILE, 'w') as f:
        for pid in pids:
            f.write(f"{pid}\n")

def add_active_node(pid):
    """Add a Node.js PID to the active list."""
    pids = read_active_nodes()
    if pid not in pids:
        pids.append(pid)
        write_active_nodes(pids)
    return len(pids)

def remove_active_node(pid):
    """Remove a Node.js PID from the active list."""
    pids = read_active_nodes()
    if pid in pids:
        pids.remove(pid)
        write_active_nodes(pids)
    return len(pids)

def read_active_py_scripts():
    """Read the list of active Python script PIDs."""
    if not os.path.exists(ACTIVE_PYTHON_SCRIPTS_FILE):
        return []
    
    try:
        with open(ACTIVE_PYTHON_SCRIPTS_FILE, 'r') as f:
            return [int(line.strip()) for line in f.readlines() if line.strip().isdigit()]
    except Exception:
        return []

def write_active_py_scripts(pids):
    """Write the list of active Python script PIDs."""
    ensure_guardian_dir()
    with open(ACTIVE_PYTHON_SCRIPTS_FILE, 'w') as f:
        for pid in pids:
            f.write(f"{pid}\n")

def add_active_py_script(pid):
    """Add a Python script PID to the active list."""
    pids = read_active_py_scripts()
    if pid not in pids:
        pids.append(pid)
        write_active_py_scripts(pids)
    return len(pids)

def remove_active_py_script(pid):
    """Remove a Python script PID from the active list."""
    pids = read_active_py_scripts()
    if pid in pids:
        pids.remove(pid)
        write_active_py_scripts(pids)
    return len(pids)

def has_active_processes():
    """Check if any monitored processes are active."""
    # First read the lists of processes
    node_pids = read_active_nodes()
    py_pids = read_active_py_scripts()
    
    # If no processes are registered, return False
    if not node_pids and not py_pids:
        return False
    
    # Check for at least one existing process (don't check all to be efficient)
    for pid in node_pids:
        if psutil.pid_exists(pid):
            try:
                # Check if the process is DHTL-related
                proc = psutil.Process(pid)
                cmdline = " ".join(proc.cmdline())
                if str(DHT_DIR) in cmdline or str(DHTL_DIR) in cmdline:
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
    
    for pid in py_pids:
        if psutil.pid_exists(pid):
            try:
                # Check if the process is DHTL-related
                proc = psutil.Process(pid)
                cmdline = " ".join(proc.cmdline())
                if str(DHT_DIR) in cmdline or str(DHTL_DIR) in cmdline:
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
    
    # No active processes found that are DHTL-related
    return False

def is_watchdog_running():
    """Check if the watchdog is running."""
    if not os.path.exists(PID_FILE):
        return False
    
    with open(PID_FILE, 'r') as f:
        try:
            pid = int(f.read().strip())
            return psutil.pid_exists(pid)
        except (ValueError, psutil.NoSuchProcess):
            return False

def run_watchdog():
    """Run the process guardian watchdog focused on project-scoped processes."""
    print(f"Starting Project-Scoped Process Guardian (PID: {os.getpid()})")
    
    # Create PID file
    ensure_guardian_dir()
    with open(PID_FILE, 'w') as f:
        f.write(str(os.getpid()))
        
    # Register our own process to keep the guardian running even with no other processes
    # This ensures it stays alive until explicitly stopped
    own_pid = os.getpid()
    # Use direct registration of our own PID with the internal flag to avoid circular dependency
    add_active_py_script(own_pid)
    
    # Set memory usage limits for this process to improve memory efficiency
    try:
        import resource
        # Get current limits
        current_soft, current_hard = resource.getrlimit(resource.RLIMIT_AS)
        
        # Only set if we can do so safely
        if current_hard == resource.RLIM_INFINITY:
            # System has no hard limit, we can set our own
            soft_limit = 100 * 1024 * 1024  # 100MB in bytes
            hard_limit = 150 * 1024 * 1024  # 150MB in bytes
            resource.setrlimit(resource.RLIMIT_AS, (soft_limit, hard_limit))
            print(f"- Set guardian memory limits: {soft_limit/1024/1024:.1f}MB soft, {hard_limit/1024/1024:.1f}MB hard")
        else:
            # System has a hard limit, use it but don't try to increase it
            soft_limit = min(current_hard, 100 * 1024 * 1024)  # Use smaller of system limit or 100MB
            print(f"- Set guardian memory soft limit: {soft_limit/1024/1024:.1f}MB (using existing hard limit)")
            resource.setrlimit(resource.RLIMIT_AS, (soft_limit, current_hard))
    except (ImportError, AttributeError, resource.error, ValueError):
        # Various platforms might have different limitations or errors
        print("- Memory limits not set (platform limitation or error)")
    
    # Use config from constants
    node_memory_limit = NODE_CONFIG["memory_limit"]
    node_max_concurrent = NODE_CONFIG["max_concurrent"]
    node_max_total_memory = NODE_CONFIG["max_total_memory"]
    
    py_memory_limit = PYTHON_DEV_CONFIG["memory_limit"]
    py_max_concurrent = PYTHON_DEV_CONFIG["max_concurrent"]
    py_max_total_memory = PYTHON_DEV_CONFIG["max_total_memory"]
    
    # Overall limit (set to sum of individual limits to be more conservative)
    max_total_memory = node_max_total_memory + py_max_total_memory
    
    # Optimize Python's garbage collector for lower memory usage
    # These settings make the GC more aggressive to reduce memory footprint
    import gc
    gc.set_threshold(100, 5, 5)  # More aggressive thresholds (default is 700, 10, 10)
    gc.enable()
    
    # Force immediate garbage collection to start with minimal memory
    gc.collect(2)
    
    # Show configuration
    print("Process Guardian Configuration:")
    print(f"- Node.js: {node_memory_limit}MB per process, max {node_max_concurrent} concurrent, {node_max_total_memory}MB total")
    print(f"- Python: {py_memory_limit}MB per process, max {py_max_concurrent} concurrent, {py_max_total_memory}MB total")
    print(f"- Combined max memory: {max_total_memory}MB")
    print("- Memory optimization: Enabled (aggressive GC)")
    
    # Handle node monitoring mode - automatically set by start-process-guardian.sh with --node-monitor flag
    node_monitor_mode = '--node-monitor' in sys.argv
    if node_monitor_mode:
        print("- Enhanced Node.js monitoring: Enabled")
        # In node monitor mode, give Node.js processes higher priority and increase limits
        node_max_concurrent += 1
        node_max_total_memory = int(node_max_total_memory * 1.2)  # Increase by 20%
    
    # Create a guardian with project-specific settings
    guardian = ProcessGuardian(
        timeout=900,  # 15 minutes
        max_memory_mb=max(node_memory_limit, py_memory_limit),  # Use the larger of the two limits
        max_concurrent=node_max_concurrent + py_max_concurrent - 1,  # Reduce by 1 to leave headroom for system
        max_total_memory_mb=max_total_memory,
        kill_duplicates=True,
        log_file=LOG_FILE
    )
    
    # Create process type configurations that match our constants
    # Don't modify the original ProcessGuardian code, but configure it with proper values
    guardian.PROCESS_TYPE_CONFIGS = {
        # Node.js processes
        "node": {
            "max_memory_mb": node_memory_limit,
            "max_concurrent": node_max_concurrent,
            "priority": 5 if node_monitor_mode else 0  # Higher priority in node monitor mode
        },
        "npm": {
            "max_memory_mb": node_memory_limit,
            "max_concurrent": 1,  # Limit npm to 1 concurrent for better stability
            "priority": 5 if node_monitor_mode else 0
        },
        # Python processes (only for dev scripts, not the main application)
        "python": {
            "max_memory_mb": py_memory_limit,
            "max_concurrent": py_max_concurrent,
            "priority": 0 if node_monitor_mode else 5  # Lower priority in node monitor mode
        }
    }
    
    # Helper function to clean up stale PIDs
    def clean_stale_pids(force_full_check=False):
        # Force garbage collection before checking PIDs to lower memory footprint
        gc.collect()
        
        # Only check a subset of PIDs on each iteration to reduce overhead
        # unless force_full_check is True
        check_all = force_full_check or getattr(clean_stale_pids, '_full_check_counter', 0) >= 5
        
        if check_all:
            # Reset the counter
            clean_stale_pids._full_check_counter = 0
            
            # Node.js PIDs - full check
            node_pids = read_active_nodes()
            valid_node_pids = []
            
            # Only keep PIDs for processes started by our DHTL script
            for pid in node_pids:
                if not psutil.pid_exists(pid):
                    continue
                
                try:
                    proc = psutil.Process(pid)
                    cmdline = " ".join(proc.cmdline())
                    # Only monitor processes that were started by dhtl.sh or from DHT directory
                    if (str(DHT_DIR) in cmdline or str(DHTL_DIR) in cmdline) and proc.is_running():
                        valid_node_pids.append(pid)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            
            if len(valid_node_pids) != len(node_pids):
                write_active_nodes(valid_node_pids)
                
            # Python script PIDs - full check
            py_pids = read_active_py_scripts()
            valid_py_pids = []
            
            # Only keep PIDs for processes started by our DHTL script
            for pid in py_pids:
                if not psutil.pid_exists(pid):
                    continue
                
                try:
                    proc = psutil.Process(pid)
                    cmdline = " ".join(proc.cmdline())
                    # Only monitor processes that were started by dhtl.sh or from DHT directory
                    if (str(DHT_DIR) in cmdline or str(DHTL_DIR) in cmdline) and proc.is_running():
                        valid_py_pids.append(pid)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            
            if len(valid_py_pids) != len(py_pids):
                write_active_py_scripts(valid_py_pids)
        else:
            # Increment the counter
            clean_stale_pids._full_check_counter = getattr(clean_stale_pids, '_full_check_counter', 0) + 1
            
            # Just read the current values without checking existence
            valid_node_pids = read_active_nodes()
            valid_py_pids = read_active_py_scripts()
            
        return valid_node_pids, valid_py_pids
    
    # Initialize last status time to control status message frequency and memory check frequency
    last_status_time = 0
    last_memory_check_time = 0
    memory_check_interval = 30  # Check memory every 30 seconds
    
    # Initialize memory usage tracking
    node_memory_usage = 0
    py_memory_usage = 0
    
    try:
        # Start monitoring
        guardian.start_monitoring()
        
        # Keep running until no more active processes
        while has_active_processes():
            # Clean up stale PIDs - do a full check periodically
            current_time = time.time()
            force_full_check = current_time - last_memory_check_time >= 120  # Full check every 2 minutes
            valid_node_pids, valid_py_pids = clean_stale_pids(force_full_check)
            
            # Log status occasionally (every 15 seconds to reduce overhead)
            if current_time - last_status_time >= 15 and (valid_node_pids or valid_py_pids):
                total_pids = len(valid_node_pids) + len(valid_py_pids)
                print(f"Currently monitoring {len(valid_node_pids)} Node.js and {len(valid_py_pids)} Python processes")
                
                # Only sample memory usage periodically to minimize overhead
                if current_time - last_memory_check_time >= memory_check_interval:
                    last_memory_check_time = current_time
                    
                    # Adaptive memory check interval - check less frequently when system has fewer processes
                    if len(valid_node_pids) + len(valid_py_pids) <= 3:
                        # Increase check interval when few processes are running
                        memory_check_interval = 60  # Check once per minute
                    else:
                        # Normal check interval when many processes are running
                        memory_check_interval = 30  # Check twice per minute
                    
                    # Use sampling to estimate memory usage instead of checking all processes
                    # Only check a small subset of processes to limit overhead
                    # For small process counts, check just one; for larger counts, check a small percentage
                    node_sample_size = min(1, len(valid_node_pids))
                    if len(valid_node_pids) > 5:
                        node_sample_size = min(2, len(valid_node_pids))
                    
                    py_sample_size = min(1, len(valid_py_pids))
                    if len(valid_py_pids) > 5:
                        py_sample_size = min(2, len(valid_py_pids))
                    
                    if node_sample_size > 0 or py_sample_size > 0:
                        # Reset memory usage if we're checking a non-zero amount of processes
                        node_memory = 0
                        py_memory = 0
                        
                        # Sample a subset of each process type
                        if node_sample_size > 0:
                            # Sample from the middle of the list to get a better representative
                            mid_idx = len(valid_node_pids) // 2
                            start_idx = max(0, mid_idx - node_sample_size // 2)
                            sample_pids = valid_node_pids[start_idx:start_idx + node_sample_size]
                            
                            for pid in sample_pids:
                                try:
                                    proc = psutil.Process(pid)
                                    mem_mb = proc.memory_info().rss / (1024 * 1024)
                                    node_memory += mem_mb
                                except (psutil.NoSuchProcess, psutil.AccessDenied):
                                    pass
                            
                            # Extrapolate to estimate total with a slight adjustment factor
                            # to account for memory variations (use 110% to be conservative)
                            if node_memory > 0 and len(valid_node_pids) > 0:
                                node_memory_usage = (node_memory / node_sample_size) * len(valid_node_pids) * 1.1
                        
                        if py_sample_size > 0:
                            # Sample from the middle of the list to get a better representative
                            mid_idx = len(valid_py_pids) // 2
                            start_idx = max(0, mid_idx - py_sample_size // 2)
                            sample_pids = valid_py_pids[start_idx:start_idx + py_sample_size]
                            
                            for pid in sample_pids:
                                try:
                                    proc = psutil.Process(pid)
                                    mem_mb = proc.memory_info().rss / (1024 * 1024)
                                    py_memory += mem_mb
                                except (psutil.NoSuchProcess, psutil.AccessDenied):
                                    pass
                                    
                            # Extrapolate to estimate total with a slight adjustment factor
                            if py_memory > 0 and len(valid_py_pids) > 0:
                                py_memory_usage = (py_memory / py_sample_size) * len(valid_py_pids) * 1.1
                    
                    # Print memory usage estimate (use cached values from last check if unavailable)
                    print(f"Estimated memory usage: Node.js: {node_memory_usage:.1f}MB, Python: {py_memory_usage:.1f}MB")
                    
                    # Evaluate total memory use and ensure process stays within budget
                    total_memory = node_memory_usage + py_memory_usage
                    if total_memory > 0.8 * max_total_memory:
                        print(f"⚠️ High memory usage: {total_memory:.1f}MB / {max_total_memory}MB (80%+)")
                    
                    # Force GC after memory check
                    gc.collect(2)
                
                # Update last status time
                last_status_time = current_time
            
            # Exit if no more active processes
            if not valid_node_pids and not valid_py_pids:
                print("No more active processes, shutting down guardian")
                break
                
            # Wait before checking again - use adaptive sleep based on number of processes
            # Sleep longer if fewer processes (saves CPU)
            total_proc_count = len(valid_node_pids) + len(valid_py_pids)
            if total_proc_count <= 2:
                sleep_time = 10  # Sleep longer with fewer processes
                # Make sure we clean up memory during idle periods
                gc.collect()
            elif total_proc_count <= 5:
                sleep_time = 7
            else:
                sleep_time = 5  # Check more frequently with many processes
                
            time.sleep(sleep_time)
            
    except KeyboardInterrupt:
        print("Watchdog service stopped by user")
    finally:
        # Clean up
        guardian.cleanup()
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)
        if os.path.exists(ACTIVE_NODES_FILE):
            os.remove(ACTIVE_NODES_FILE)
        if os.path.exists(ACTIVE_PYTHON_SCRIPTS_FILE):
            os.remove(ACTIVE_PYTHON_SCRIPTS_FILE)
        
        # Final garbage collection before exiting
        gc.collect()
        print("Process Guardian shut down")

def start_command():
    """Start the watchdog if not already running in a platform-independent way."""
    if is_watchdog_running():
        return
    
    # Create guardian directory if it doesn't exist
    ensure_guardian_dir()
    
    # Clean up any stale process files before starting
    # This prevents the guardian from shutting down immediately due to stale PIDs
    if os.path.exists(ACTIVE_NODES_FILE):
        os.remove(ACTIVE_NODES_FILE)
    if os.path.exists(ACTIVE_PYTHON_SCRIPTS_FILE):
        os.remove(ACTIVE_PYTHON_SCRIPTS_FILE)
    
    # Create empty files to start fresh
    write_active_nodes([])
    write_active_py_scripts([])
    
    # Cross-platform daemon approach
    is_windows = sys.platform.startswith('win')
    
    if is_windows:
        # Windows: Use subprocess to create a detached process
        try:
            import subprocess
            
            # Create detached process
            DETACHED_PROCESS = 0x00000008
            CREATE_NEW_PROCESS_GROUP = 0x00000200
            
            # Prepare stdout and stderr files
            stdout_path = os.path.join(GUARDIAN_DIR, 'watchdog.out')
            stderr_path = os.path.join(GUARDIAN_DIR, 'watchdog.err')
            
            # Create detached process
            subprocess.Popen(
                [sys.executable, __file__, 'run'],
                creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP,
                close_fds=True,
                stdout=open(stdout_path, 'a+'),
                stderr=open(stderr_path, 'a+'),
                stdin=open(os.devnull, 'r')
            )
            
            # Give the process time to start
            time.sleep(1)
            return
            
        except Exception as e:
            print(f"Error starting watchdog process on Windows: {e}")
            sys.exit(1)
    else:
        # Unix: Fork a child process
        try:
            pid = os.fork()
            if pid > 0:
                # Parent process returns immediately
                return
        except OSError as e:
            print(f"Error forking process: {e}")
            sys.exit(1)
        
        try:
            # Child process continues
            # Decouple from parent environment
            os.setsid()
            
            # Close standard file descriptors
            sys.stdout.flush()
            sys.stderr.flush()
            
            # Redirect standard file descriptors
            # Use os.devnull for cross-platform null device
            with open(os.devnull, 'r') as f:
                os.dup2(f.fileno(), sys.stdin.fileno())
            with open(os.path.join(GUARDIAN_DIR, 'watchdog.out'), 'a+') as f:
                os.dup2(f.fileno(), sys.stdout.fileno())
            with open(os.path.join(GUARDIAN_DIR, 'watchdog.err'), 'a+') as f:
                os.dup2(f.fileno(), sys.stderr.fileno())
            
            # Run the watchdog
            run_watchdog()
            sys.exit(0)
            
        except Exception as e:
            print(f"Error in child process: {e}")
            sys.exit(1)

def register_command(pid, process_type="node", internal=False):
    """Register a process with the watchdog.
    
    Args:
        pid: Process ID to register
        process_type: Type of process ('node' or 'python')
        internal: If True, this is an internal call and should skip certain checks
    """
    # Start the watchdog if not already running, but only if this is not an internal call
    if not internal and not is_watchdog_running():
        start_command()
        # Give it a moment to start
        time.sleep(1)
    
    # Verify this is a process we should be monitoring, unless it's an internal call
    if not internal:
        try:
            proc = psutil.Process(pid)
            cmdline = " ".join(proc.cmdline())
            
            # Only monitor processes that were started by dhtl.sh or from DHT directory
            if str(DHT_DIR) not in cmdline and str(DHTL_DIR) not in cmdline:
                print(f"⚠️ Process {pid} not started by dhtl.sh or from DHT directory - skipping registration")
                return 1
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            print(f"⚠️ Cannot access process {pid} - skipping registration")
            return 1
    
    # Register the PID based on process type
    if process_type.lower() == "python":
        count = add_active_py_script(pid)
        if not internal:
            print(f"Registered Python script process {pid}, now monitoring {count} Python processes")
    else:
        # Default to Node.js
        count = add_active_node(pid)
        if not internal:
            print(f"Registered Node.js process {pid}, now monitoring {count} Node.js processes")
    
    return 0

def unregister_command(pid, process_type="node"):
    """Unregister a process from the watchdog.
    
    Args:
        pid: Process ID to unregister
        process_type: Type of process ('node' or 'python')
    """
    if process_type.lower() == "python":
        remaining = remove_active_py_script(pid)
        print(f"Unregistered Python script process {pid}, {remaining} Python processes still monitored")
    else:
        # Default to Node.js
        remaining = remove_active_node(pid)
        print(f"Unregistered Node.js process {pid}, {remaining} Node.js processes still monitored")
    
    return 0

def stop_command():
    """Force stop the watchdog."""
    if not os.path.exists(PID_FILE):
        print("Process Guardian Watchdog is not running")
        return 1
    
    with open(PID_FILE, 'r') as f:
        try:
            pid = int(f.read().strip())
            if psutil.pid_exists(pid):
                os.kill(pid, signal.SIGTERM)
                print(f"Sent termination signal to Process Guardian Watchdog (PID {pid})")
                
                # Wait for it to terminate
                for _ in range(5):
                    if not psutil.pid_exists(pid):
                        break
                    time.sleep(1)
                    
                if psutil.pid_exists(pid):
                    os.kill(pid, signal.SIGKILL)
                    print(f"Force killed Process Guardian Watchdog (PID {pid})")
                
                # Clean up files
                if os.path.exists(PID_FILE):
                    os.remove(PID_FILE)
                if os.path.exists(ACTIVE_NODES_FILE):
                    os.remove(ACTIVE_NODES_FILE)
                    
                return 0
            else:
                print("Process Guardian Watchdog is not running (stale PID file)")
                if os.path.exists(PID_FILE):
                    os.remove(PID_FILE)
                return 1
        except (ValueError, psutil.NoSuchProcess):
            print("Invalid PID in watchdog PID file")
            if os.path.exists(PID_FILE):
                os.remove(PID_FILE)
            return 1

def status_command():
    """Check the status of the watchdog."""
    if not os.path.exists(PID_FILE):
        print("Process Guardian Watchdog is not running")
        return 1
    
    with open(PID_FILE, 'r') as f:
        try:
            pid = int(f.read().strip())
            if psutil.pid_exists(pid):
                process = psutil.Process(pid)
                print(f"Process Guardian Watchdog is running with PID {pid}")
                print(f"Memory usage: {process.memory_info().rss / (1024 * 1024):.2f} MB")
                print(f"CPU usage: {process.cpu_percent(interval=0.1):.1f}%")
                print(f"Started: {time.ctime(process.create_time())}")
                print(f"Running for: {time.time() - process.create_time():.0f} seconds")
                
                # Show monitored Node.js processes
                active_nodes = read_active_nodes()
                print(f"\nCurrently monitoring {len(active_nodes)} Node.js processes:")
                for i, node_pid in enumerate(active_nodes, 1):
                    if psutil.pid_exists(node_pid):
                        try:
                            node_proc = psutil.Process(node_pid)
                            print(f"  {i}. PID {node_pid}: {node_proc.name()} - Memory: {node_proc.memory_info().rss / (1024 * 1024):.2f} MB")
                        except psutil.NoSuchProcess:
                            print(f"  {i}. PID {node_pid}: (process no longer exists)")
                    else:
                        print(f"  {i}. PID {node_pid}: (process no longer exists)")
                
                # Show monitored Python processes
                active_py_scripts = read_active_py_scripts()
                print(f"\nCurrently monitoring {len(active_py_scripts)} Python processes:")
                for i, py_pid in enumerate(active_py_scripts, 1):
                    if psutil.pid_exists(py_pid):
                        try:
                            py_proc = psutil.Process(py_pid)
                            cmdline = " ".join(py_proc.cmdline())
                            if len(cmdline) > 60:
                                cmdline = cmdline[:57] + "..."
                            print(f"  {i}. PID {py_pid}: {py_proc.name()} - Memory: {py_proc.memory_info().rss / (1024 * 1024):.2f} MB")
                            print(f"     Command: {cmdline}")
                        except psutil.NoSuchProcess:
                            print(f"  {i}. PID {py_pid}: (process no longer exists)")
                    else:
                        print(f"  {i}. PID {py_pid}: (process no longer exists)")
                
                # Display configuration summary
                print("\nProcess Guardian Configuration:")
                print(f"- Node.js: {NODE_CONFIG['memory_limit']}MB per process, max {NODE_CONFIG['max_concurrent']} concurrent")
                print(f"- Python: {PYTHON_DEV_CONFIG['memory_limit']}MB per process, max {PYTHON_DEV_CONFIG['max_concurrent']} concurrent")
                
                return 0
            else:
                print("Process Guardian Watchdog is not running (stale PID file)")
                if os.path.exists(PID_FILE):
                    os.remove(PID_FILE)
                return 1
        except (ValueError, psutil.NoSuchProcess):
            print("Invalid PID in watchdog PID file")
            if os.path.exists(PID_FILE):
                os.remove(PID_FILE)
            return 1

def print_banner():
    """Print a banner with version and configuration info."""
    script_name = os.path.basename(__file__)
    project_name = PROJECT_ROOT.name if hasattr(PROJECT_ROOT, 'name') else os.path.basename(str(PROJECT_ROOT))
    
    print("\n" + "=" * 72)
    print("DHTL Process Guardian Watchdog - Portable Edition")
    print(f"Project: {project_name}")
    print(f"Location: {SCRIPT_DIR}")
    print(f"Cache directory: {GUARDIAN_DIR}")
    print("=" * 72)
    print(f"Node.js limits: {NODE_CONFIG['memory_limit']}MB/process, " 
          f"max {NODE_CONFIG['max_concurrent']} concurrent, "
          f"{NODE_CONFIG['max_total_memory']}MB total")
    print(f"Python limits: {PYTHON_DEV_CONFIG['memory_limit']}MB/process, "
          f"max {PYTHON_DEV_CONFIG['max_concurrent']} concurrent, "
          f"{PYTHON_DEV_CONFIG['max_total_memory']}MB total")
    print("=" * 72 + "\n")

def print_help():
    """Print help information."""
    script_name = os.path.basename(__file__)
    
    print("\nDHTL Process Guardian Watchdog - Portable Edition")
    print("\nCommands:")
    print(f"  {script_name} start              Start the watchdog daemon in the background")
    print(f"  {script_name} run                Run the watchdog in the foreground")
    print(f"  {script_name} register <pid> [type]   Register a process to be monitored")
    print(f"  {script_name} unregister <pid> [type] Unregister a monitored process")
    print(f"  {script_name} stop               Terminate the watchdog daemon")
    print(f"  {script_name} status             Show status of the watchdog and monitored processes")
    print(f"  {script_name} help               Show this help information")
    print()
    print("Process Types:")
    print("  node     Node.js processes (default)")
    print("  python   Python processes")
    print()
    print("Environment Variables:")
    print("  DHTL_CACHE_DIR              Override the cache directory")
    print("  DHTL_GUARDIAN_DIR           Override the guardian directory")
    print("  DHTL_NODE_MEMORY_LIMIT      Memory limit per Node.js process (MB)")
    print("  DHTL_NODE_MAX_CONCURRENT    Maximum concurrent Node.js processes")
    print("  DHTL_NODE_TOTAL_MEMORY      Maximum total memory for Node.js (MB)")
    print("  DHTL_PYTHON_MEMORY_LIMIT    Memory limit per Python process (MB)")
    print("  DHTL_PYTHON_MAX_CONCURRENT  Maximum concurrent Python processes")
    print("  DHTL_PYTHON_TOTAL_MEMORY    Maximum total memory for Python (MB)")
    print()
    print("Examples:")
    print(f"  {script_name} start                           # Start the watchdog daemon")
    print(f"  {script_name} register 1234 python            # Register Python process with PID 1234")
    print(f"  {script_name} status                          # Show current status")
    print(f"  DHTL_NODE_MEMORY_LIMIT=1024 {script_name} run # Run with custom memory limit")
    print()

if __name__ == "__main__":
    # Process command line arguments
    if len(sys.argv) < 2 or sys.argv[1] in ['-h', '--help', 'help']:
        print_help()
        sys.exit(0)
    
    command = sys.argv[1].lower()
    
    if command == "start":
        # Print banner before starting
        print_banner()
        print("Starting watchdog daemon...")
        start_command()
        print("Watchdog daemon started.")
    
    elif command == "run":
        # Print banner before running
        print_banner()
        print("Running watchdog in foreground (Ctrl+C to stop)...")
        run_watchdog()
    
    elif command == "register":
        if len(sys.argv) < 3:
            print("Error: Missing PID parameter.")
            print(f"Usage: {os.path.basename(__file__)} register <pid> [process_type]")
            print("       process_type can be 'node' (default) or 'python'")
            sys.exit(1)
        
        try:
            pid = int(sys.argv[2])
            # Get process type if provided
            process_type = "node"  # Default
            if len(sys.argv) > 3:
                process_type = sys.argv[3].lower()
                
            if process_type not in ["node", "python"]:
                print(f"Warning: Unknown process type '{process_type}'. Using default settings.")
                
            sys.exit(register_command(pid, process_type))
        except ValueError:
            print(f"Error: Invalid PID: {sys.argv[2]}")
            sys.exit(1)
    
    elif command == "unregister":
        if len(sys.argv) < 3:
            print("Error: Missing PID parameter.")
            print(f"Usage: {os.path.basename(__file__)} unregister <pid> [process_type]")
            print("       process_type can be 'node' (default) or 'python'")
            sys.exit(1)
        
        try:
            pid = int(sys.argv[2])
            # Get process type if provided
            process_type = "node"  # Default
            if len(sys.argv) > 3:
                process_type = sys.argv[3].lower()
                
            sys.exit(unregister_command(pid, process_type))
        except ValueError:
            print(f"Error: Invalid PID: {sys.argv[2]}")
            sys.exit(1)
    
    elif command == "stop":
        sys.exit(stop_command())
    
    elif command == "status":
        print_banner()
        sys.exit(status_command())
    
    else:
        print(f"Error: Unknown command: {command}")
        print_help()
        sys.exit(1)