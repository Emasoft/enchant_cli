#!/usr/bin/env python3
"""
Enhanced log analysis and error classification tool for GitHub Actions workflow logs.

This module provides comprehensive tools to:
- Analyze workflow logs for errors and warnings
- Classify issues by severity (critical, severe, warning)
- Identify root causes of failures with AI-enhanced analysis
- Generate structured summary reports
- Search across log files for patterns
- Find and manage workflow logs
- Extract workflow statistics and trends

Features:
- Enhanced diagnostics for complex GitHub Actions issues
- Repository auto-detection 
- Workflow categorization (test, release, lint, docs)
- Support for multiple output formats (text, JSON, TSV, HTML)
- Log management and cleanup
- Workflow run history analysis

Usage:
    python -m helpers.errors.log_analyzer analyze /path/to/log_file.log
    python -m helpers.errors.log_analyzer find --id 123456789
    python -m helpers.errors.log_analyzer latest
    python -m helpers.errors.log_analyzer search "error pattern"
    python -m helpers.errors.log_analyzer stats
    python -m helpers.errors.log_analyzer repo
"""

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Constants for error classification
ERROR_PATTERN_CRITICAL = r"Process completed with exit code [1-9]|fatal error|fatal:|FATAL ERROR|Assertion failed|Segmentation fault|core dumped|killed|ERROR:|Connection refused|panic|PANIC|assert|ASSERT|terminated|abort|SIGSEGV|SIGABRT|SIGILL|SIGFPE|Reached heap limit|JavaScript heap out of memory|allocation failed|FATAL|unhandled exception|Critical"
ERROR_PATTERN_SEVERE = r"exit code [1-9]|failure:|failed with|FAILED|Exception|exception:|Error:|error:|undefined reference|Cannot find|not found|No such file|Permission denied|AccessDenied|Could not access|Cannot access|ImportError|ModuleNotFoundError|TypeError|ValueError|KeyError|AttributeError|AssertionError|UnboundLocalError|IndexError|SyntaxError|NameError|RuntimeError|unexpected|failed to|EACCES|EPERM|ENOENT|compilation failed|command failed|exited with code|timed out|Maximum execution time exceeded|Process terminated|Failed to install|npm ERR!|yarn error|Cannot resolve|Module build failed"
ERROR_PATTERN_WARNING = r"WARNING:|warning:|deprecated|Deprecated|DEPRECATED|fixme|FIXME|TODO|todo:|ignored|skipped|suspicious|insecure|unsafe|consider|recommended|inconsistent|possibly|PendingDeprecationWarning|FutureWarning|UserWarning|ResourceWarning|high memory usage|high cpu usage|possible memory leak|slow operation|optimization opportunity"

# ANSI color codes for terminal output
COLORS = {
    "RED": "\033[0;31m",
    "GREEN": "\033[0;32m",
    "YELLOW": "\033[0;33m",
    "BLUE": "\033[0;34m",
    "MAGENTA": "\033[0;35m",
    "CYAN": "\033[0;36m",
    "RESET": "\033[0m",
    "BOLD": "\033[1m",
    "UNDERLINE": "\033[4m"
}


def parse_error_patterns():
    """
    Define error patterns by severity with optimized compilation.
    
    Returns:
        dict: Dictionary containing compiled regex patterns for each severity level
    """
    patterns = {
        "critical": ERROR_PATTERN_CRITICAL,
        "severe": ERROR_PATTERN_SEVERE,
        "warning": ERROR_PATTERN_WARNING
    }
    
    # Compile patterns for better performance
    compiled_patterns = {}
    for severity, pattern in patterns.items():
        compiled_patterns[severity] = re.compile(pattern, re.IGNORECASE)
    
    return compiled_patterns


def detect_repository_info():
    """
    Auto-detect repository information from git config, project files, or environment.
    
    Returns:
        tuple: (repo_owner, repo_name, repo_full_name)
    """
    # Try to get repository info from git config
    try:
        origin_url = subprocess.check_output(
            ["git", "config", "--get", "remote.origin.url"], 
            stderr=subprocess.STDOUT
        ).decode('utf-8').strip()
        
        # Parse different git URL formats
        if "github.com" in origin_url:
            # Handle SSH format: git@github.com:owner/repo.git
            if "@" in origin_url:
                match = re.search(r"github\.com[:/]([^/]+)/([^/.]+)", origin_url)
            # Handle HTTPS format: https://github.com/owner/repo.git
            else:
                match = re.search(r"github\.com/([^/]+)/([^/.]+)", origin_url)
                
            if match:
                repo_owner = match.group(1)
                repo_name = match.group(2)
                return repo_owner, repo_name, f"{repo_owner}/{repo_name}"
    except subprocess.CalledProcessError:
        pass
        
    # Try to extract from pyproject.toml
    pyproject_path = "pyproject.toml"
    if os.path.isfile(pyproject_path):
        try:
            with open(pyproject_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Look for GitHub URL in project configuration
            homepage_match = re.search(r'Homepage.*=.*"https://github.com/([^/]+)/([^/"]+)"', content)
            if homepage_match:
                repo_owner = homepage_match.group(1)
                repo_name = homepage_match.group(2)
                return repo_owner, repo_name, f"{repo_owner}/{repo_name}"
        except Exception:
            pass
            
    # Try GitHub CLI if available
    try:
        repo_info = subprocess.check_output(
            ["gh", "repo", "view", "--json", "owner,name"], 
            stderr=subprocess.DEVNULL
        ).decode('utf-8').strip()
        
        try:
            data = json.loads(repo_info)
            repo_owner = data.get("owner", {}).get("login")
            repo_name = data.get("name")
            
            if repo_owner and repo_name:
                return repo_owner, repo_name, f"{repo_owner}/{repo_name}"
        except json.JSONDecodeError:
            # Try parsing the non-JSON output format
            owner_match = re.search(r'"owner":\s*"([^"]+)"', repo_info)
            name_match = re.search(r'"name":\s*"([^"]+)"', repo_info)
            
            if owner_match and name_match:
                repo_owner = owner_match.group(1)
                repo_name = name_match.group(1)
                return repo_owner, repo_name, f"{repo_owner}/{repo_name}"
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    
    # Last resort: use current directory name as repo name
    repo_name = os.path.basename(os.getcwd())
    repo_owner = "unknown"
    return repo_owner, repo_name, f"{repo_owner}/{repo_name}"


def detect_workflow_categories():
    """
    Detect and categorize available workflows in the repository.
    
    Returns:
        dict: Dictionary with workflow categories (test, release, lint, docs, other)
    """
    workflows = {
        "all": [],
        "test": [],
        "release": [],
        "lint": [],
        "docs": [],
        "other": []
    }
    
    # Check for workflow files in standard location
    if os.path.isdir(".github/workflows"):
        for file in os.listdir(".github/workflows"):
            if not file.endswith(('.yml', '.yaml')):
                continue
                
            workflows["all"].append(file)
            
            # Try to categorize by filename patterns
            if re.search(r"test|ci|check", file, re.IGNORECASE):
                workflows["test"].append(file)
            elif re.search(r"release|publish|deploy|build|package", file, re.IGNORECASE):
                workflows["release"].append(file)
            elif re.search(r"lint|format|style|quality", file, re.IGNORECASE):
                workflows["lint"].append(file)
            elif re.search(r"doc", file, re.IGNORECASE):
                workflows["docs"].append(file)
            else:
                # If not matched by name, try content-based categorization
                try:
                    file_path = os.path.join(".github/workflows", file)
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                    if re.search(r"test|pytest|unittest|jest|spec|check", content, re.IGNORECASE):
                        workflows["test"].append(file)
                    elif re.search(r"release|deploy|publish|build|package|version", content, re.IGNORECASE):
                        workflows["release"].append(file)
                    elif re.search(r"lint|format|style|prettier|eslint|black|flake8|ruff|quality", content, re.IGNORECASE):
                        workflows["lint"].append(file)
                    elif re.search(r"doc|sphinx|mkdocs|javadoc|doxygen|documentation", content, re.IGNORECASE):
                        workflows["docs"].append(file)
                    else:
                        workflows["other"].append(file)
                except Exception:
                    workflows["other"].append(file)
    
    # If no workflows found, use default fallbacks
    if not workflows["all"]:
        workflows["all"] = ["tests.yml", "auto_release.yml", "lint.yml", "docs.yml"]
        workflows["test"] = ["tests.yml"]
        workflows["release"] = ["auto_release.yml"]
        workflows["lint"] = ["lint.yml"]
        workflows["docs"] = ["docs.yml"]
    
    return workflows


def analyze_log_file(log_file):
    """
    Analyze a workflow log file and return a comprehensive summary of errors.
    
    Args:
        log_file (str): Path to the log file
        
    Returns:
        dict: Analysis results with error counts, samples, and metadata
    """
    error_patterns = parse_error_patterns()
    
    # Initialize counters
    counts = {
        "critical": 0,
        "severe": 0,
        "warning": 0,
        "lines": 0
    }
    
    # Initialize error storage with line numbers and context
    errors = {
        "critical": [],
        "severe": [],
        "warning": []
    }
    
    # Extract metadata from filename
    workflow_name = "Unknown"
    run_id = "Unknown"
    timestamp = "Unknown"
    
    # Try to extract from filename format: workflow_ID_TIMESTAMP.log
    file_name = os.path.basename(log_file)
    file_parts = file_name.split('_')
    if len(file_parts) >= 3:
        run_id = file_parts[1]
        
        # Try to parse timestamp
        try:
            timestamp_part = file_parts[2].split('.')[0]  # Format: YYYYMMDD-HHMMSS
            timestamp = datetime.strptime(timestamp_part, "%Y%m%d-%H%M%S").strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            pass
    
    # Process the file
    try:
        with open(log_file, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
            
            # Try to determine workflow name from content
            for name in ["Tests", "Auto Release", "Lint", "Docs"]:
                if re.search(name, content, re.IGNORECASE):
                    workflow_name = name
                    break
            
            # Process line by line for detailed error matching
            lines = content.splitlines()
            counts["lines"] = len(lines)
            
            # First pass: identify stack traces and multi-line error blocks
            error_blocks = []
            current_block = None
            stack_trace_patterns = [
                r"at\s+[A-Za-z0-9_$.]+\s+\(.*:\d+:\d+\)",  # JavaScript stack traces
                r"File \".*\", line \d+",                  # Python stack traces
                r"Traceback \(most recent call last\)",     # Python traceback start
                r"Stack trace:",                           # Generic stack trace marker
                r"([a-zA-Z0-9/._-]+):(\d+)(?::(\d+))?",    # File:line:column references
                r"^\s+at\s+.*$",                           # Node.js stack trace lines
                r"^\s+from\s+.*:\d+:in\s+.*$"              # Ruby stack traces
            ]
            
            # Compile stack trace patterns
            stack_trace_regex = re.compile("|".join(f"({pattern})" for pattern in stack_trace_patterns))
            
            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                
                # Check if this line is part of a stack trace
                is_stack_trace_line = bool(stack_trace_regex.search(line))
                
                # Check if this line contains an error by severity
                error_severity = None
                for severity, pattern in error_patterns.items():
                    if pattern.search(line):
                        error_severity = severity
                        break
                
                # Handle line based on error and stack trace detection
                if error_severity:
                    # Start a new error block
                    current_block = {
                        "start": line_num,
                        "end": line_num,
                        "severity": error_severity,
                        "line": line
                    }
                    error_blocks.append(current_block)
                    counts[error_severity] += 1
                    
                elif is_stack_trace_line and current_block and line_num - current_block["end"] <= 3:
                    # Extend the current error block to include this stack trace line
                    current_block["end"] = line_num
                    
                elif current_block and line_num - current_block["end"] <= 1 and len(line) > 0:
                    # Include adjacent non-empty lines in the error block for context
                    current_block["end"] = line_num
                    
                else:
                    # Not part of an error block
                    current_block = None
            
            # Second pass: extract contexts for identified error blocks
            for block in error_blocks:
                severity = block["severity"]
                line_num = block["start"]
                end_num = block["end"]
                
                # Get context including the entire error block plus some surrounding lines
                context_start = max(0, block["start"] - 3)
                context_end = min(len(lines), block["end"] + 3)
                context = []
                
                for ctx_line_num in range(context_start, context_end):
                    ctx_line = lines[ctx_line_num].strip()
                    
                    # Mark error block lines specially
                    if ctx_line_num + 1 >= block["start"] and ctx_line_num + 1 <= block["end"]:
                        if ctx_line_num + 1 == line_num:
                            context.append((ctx_line_num + 1, f"→ {ctx_line}"))
                        else:
                            context.append((ctx_line_num + 1, f"❯ {ctx_line}"))
                    else:
                        context.append((ctx_line_num + 1, ctx_line))
                
                # Store the error with context (limit samples to avoid overwhelming)
                if len(errors[severity]) < 10:
                    errors[severity].append({
                        "line_num": line_num,
                        "line": block["line"],
                        "context": context,
                        "block_start": block["start"],
                        "block_end": block["end"]
                    })
            
            # If no error blocks were found, fallback to simple line-by-line scanning
            if sum(counts.values()) - counts["lines"] == 0:
                for line_num, line in enumerate(lines, 1):
                    line = line.strip()
                    
                    # Check for errors by severity
                    for severity, pattern in error_patterns.items():
                        if pattern.search(line):
                            counts[severity] += 1
                            
                            # Get some context around the error
                            context_start = max(0, line_num - 3)
                            context_end = min(len(lines), line_num + 3)
                            context = []
                            
                            for ctx_line_num in range(context_start, context_end):
                                ctx_line = lines[ctx_line_num].strip()
                                if ctx_line_num + 1 == line_num:
                                    # Mark the actual error line
                                    context.append((ctx_line_num + 1, f"→ {ctx_line}"))
                                else:
                                    context.append((ctx_line_num + 1, ctx_line))
                            
                            # Store the error with context
                            if len(errors[severity]) < 10:
                                errors[severity].append({
                                    "line_num": line_num,
                                    "line": line,
                                    "context": context
                                })
                            
                            # Once matched for a severity, no need to check others
                            break
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error reading log file: {str(e)}",
            "log_file": log_file
        }
    
    # Generate the summary
    summary = {
        "status": "success",
        "log_file": log_file,
        "workflow_name": workflow_name,
        "run_id": run_id,
        "timestamp": timestamp,
        "counts": counts,
        "errors": errors
    }
    
    return summary


def detect_root_causes(log_file):
    """
    Detect potential root causes for workflow failures with enhanced diagnostics.
    
    Args:
        log_file (str): Path to the log file
        
    Returns:
        list: Detected root causes with explanations and suggested mitigations
    """
    root_causes = []
    
    # Define common patterns with descriptive names and mitigation suggestions
    common_causes = [
        ("Disk space issue", r"No space left on device|disk space|quota exceeded|file system.*full|insufficient space", 
         "Consider cleaning up build artifacts or using a larger runner with more disk space"),
        
        ("Memory issue", r"memory allocation|out of memory|cannot allocate|allocation failed|OOM|Killed|Reached heap limit|heap.*memory|JavaScript heap out of memory", 
         "Optimize memory usage, use memory limits, or consider using a larger runner"),
        
        ("Node.js memory limit exceeded", r"JavaScript heap out of memory|Reached heap limit|--max-old-space-size|heap is too small|v8.*memory|node.*memory|FATAL ERROR: Reached heap limit", 
         "Increase Node.js memory limit or implement process management with queue system"),
        
        ("Network connectivity issue", r"network.*timeout|connection.*refused|unreachable|DNS|proxy|firewall|socket.*timeout|host.*unreachable|TLS handshake|SSL certificate|name resolution", 
         "Check network settings, firewall rules, or add retry mechanisms for network operations"),
        
        ("Permission issue", r"permission denied|access denied|unauthorized|forbidden|EACCES|EPERM|inadequate permissions|not allowed|restricted access", 
         "Check access rights, file/directory permissions, or GitHub token permissions"),
        
        ("Version compatibility issue", r"version mismatch|incompatible|requires version|dependency|wrong version|version conflict|unsupported version|requires.*at least|not compatible", 
         "Verify dependency versions match requirements and check compatibility between packages"),
        
        ("Missing module or import", r"import error|module not found|cannot find module|unknown module|no module named|cannot import|required module", 
         "Ensure all required packages are installed and imports use correct paths"),
        
        ("Operation timeout", r"timeout|timed out|deadline exceeded|cancelled|operation timed out|execution time exceeded|timeout.*exceeded", 
         "Increase operation timeout limits or optimize slow processes"),
        
        ("Syntax error", r"syntax error|parsing error|unexpected token|invalid syntax|unexpected character|EOF.*expected|parse.*failed|unterminated string", 
         "Check recent code changes for syntax issues"),
        
        ("Git or checkout issue", r"failed to fetch|shallow update not allowed|repository not found|cannot checkout|git checkout.*failed|git clone.*failed|git fetch.*error|git pull.*error", 
         "Verify repository access permissions and Git configuration"),
        
        ("API rate limit", r"API rate limit|too many requests|429|rate limit exceeded|request limit|throttled|retry after", 
         "Implement rate limiting or wait periods between API calls"),
        
        ("Pipeline concurrency", r"waiting for a runner|no runners online|all runners busy|queue.*full|no available runners|waiting for an available host", 
         "Consider using self-hosted runners or adjusting workflow timing"),
        
        ("Authentication issue", r"authentication failed|not authenticated|unauthorized|credentials|permission|token expired|invalid token|login.*failed|invalid credentials", 
         "Check credentials, token validity, and authentication configuration"),
        
        ("Configuration error", r"config(uration)? (error|invalid|missing)|invalid yaml|malformed|expected format|yaml.*error|invalid.*configuration|config.*syntax", 
         "Verify configuration file syntax and schema compliance"),
        
        ("File not found", r"file not found|no such file|missing file|could not find|not exist|does not exist|cannot open file|no such file or directory", 
         "Check file paths and ensure required files are included in repository"),
        
        ("GitHub-specific errors", r"Resource not accessible by integration|not authorized to perform|workflow cannot access secrets|secret.*not found|GITHUB_TOKEN permissions", 
         "Check GitHub workflow permissions, secrets access, and repository settings"),
         
        ("Concurrent process overload", r"too many processes|process limit|thread limit exceeded|fork.*failed|cannot create.*thread|resource temporarily unavailable|too many open files", 
         "Implement process pooling/queuing or reduce parallelism"),
         
        ("Node.js dependency issues", r"npm ERR!|yarn error|package.*not found|Cannot resolve|Module build failed|Failed to resolve dependencies|dependency tree|node_modules.*missing", 
         "Check package.json, lockfiles, and ensure all dependencies are correctly installed"),
         
        ("Babel/Webpack build errors", r"babel.*error|webpack.*error|transpile.*failed|Failed to compile|Module parse failed|Module not found|Cannot find module|Unexpected token", 
         "Review build configuration and dependency compatibility"),
         
        ("ESLint/TypeScript errors", r"ESLint|typescript|TS\d+|Type error|Property.*does not exist|Cannot find name|is not assignable to type|is not a module", 
         "Fix type errors and ensure proper TypeScript configuration")
    ]
    
    try:
        with open(log_file, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
            
            # Check for each cause pattern
            for cause_name, pattern, suggestion in common_causes:
                if re.search(pattern, content, re.IGNORECASE):
                    root_causes.append(f"{cause_name} - {suggestion}")
            
            # Specialized detection for Node.js heap memory issues
            if re.search(r"JavaScript heap out of memory|Reached heap limit|FATAL ERROR: Reached heap limit", content, re.IGNORECASE):
                # Try to extract memory limit if present
                mem_limit_match = re.search(r"--max-old-space-size=(\d+)", content)
                if mem_limit_match:
                    current_limit = mem_limit_match.group(1)
                    root_causes.append(f"Node.js memory limit ({current_limit}MB) exceeded - Consider implementing process guardian or increasing limit")
                else:
                    root_causes.append("Node.js memory limit exceeded - Consider implementing process guardian with memory management")
            
            # Add specialized GitHub Actions specific detection
            if "Tests" in os.path.basename(log_file) or "test" in os.path.basename(log_file).lower():
                # Look for pytest failures
                if "pytest" in content.lower() and re.search(r"failed=\d+", content):
                    test_count = re.search(r"failed=(\d+)", content)
                    if test_count:
                        root_causes.append(f"Test failures detected - {test_count.group(1)} tests failed")
                    else:
                        root_causes.append("Test failures detected")
                
                # Look for Jest/Mocha test failures
                elif re.search(r"Test Suites:\s+\d+\s+failed", content) or re.search(r"Tests:\s+\d+\s+failed", content):
                    test_suites = re.search(r"Test Suites:\s+(\d+)\s+failed", content)
                    tests = re.search(r"Tests:\s+(\d+)\s+failed", content)
                    if test_suites and tests:
                        root_causes.append(f"JavaScript test failures detected - {test_suites.group(1)} test suites and {tests.group(1)} tests failed")
                    elif test_suites:
                        root_causes.append(f"JavaScript test failures detected - {test_suites.group(1)} test suites failed")
                    elif tests:
                        root_causes.append(f"JavaScript test failures detected - {tests.group(1)} tests failed")
                    else:
                        root_causes.append("JavaScript test failures detected")
            
            # Look for dependency issues
            if re.search(r"pip.*install", content, re.IGNORECASE) and "error" in content.lower():
                dep_name = re.search(r"pip.*install.*?([a-zA-Z0-9_-]+).*?error", content, re.IGNORECASE)
                if dep_name:
                    root_causes.append(f"Python dependency issue - Failed to install {dep_name.group(1)}")
                else:
                    root_causes.append("Python dependency installation issues - pip encountered errors")
            
            # More detailed Node.js dependency issues
            if re.search(r"npm (ERR|error)", content, re.IGNORECASE):
                if re.search(r"404 Not Found|could not resolve|npm ERR! 404", content, re.IGNORECASE):
                    pkg_name = re.search(r"404.*?([a-zA-Z0-9@/_-]+)", content)
                    if pkg_name:
                        root_causes.append(f"npm dependency error - Package not found: {pkg_name.group(1)}")
                    else:
                        root_causes.append("npm dependency error - Package not found")
                elif re.search(r"peer dependency|npm ERR! peer dep missing", content, re.IGNORECASE):
                    root_causes.append("npm peer dependency conflict - Check compatible versions")
                elif re.search(r"npm ERR! Maximum call stack|heap.*exceeded", content, re.IGNORECASE):
                    root_causes.append("npm memory issue - Operation requires more memory")
            
            # Specialized detection for concurrent process issues
            if re.search(r"resource temporarily unavailable|too many open files|cannot fork|cannot create process", content, re.IGNORECASE):
                root_causes.append("Process resource limit reached - Implement a process guardian with queue")
                
            # Look for file system and file access patterns
            if re.search(r"ENOSPC|EMFILE|ENFILE", content):
                if "ENOSPC" in content:
                    root_causes.append("File system space exhausted - Free up disk space or use larger runner")
                if "EMFILE" in content:
                    root_causes.append("Too many open files - Implement process pooling or file handle management")
                if "ENFILE" in content:
                    root_causes.append("System file table overflow - Reduce concurrent file operations")
    
    except Exception as e:
        return [f"Error analyzing for root causes: {str(e)}"]
    
    # Remove duplicates while preserving order
    unique_causes = []
    for cause in root_causes:
        if cause not in unique_causes:
            unique_causes.append(cause)
    
    if not unique_causes:
        unique_causes = ["No specific root cause identified automatically"]
    
    return unique_causes


def classify_log_errors(log_file, output_file=None):
    """
    Analyze a log file and classify errors by severity, with optional output file.
    
    Args:
        log_file (str): Path to the log file
        output_file (str, optional): Path to write detailed output
        
    Returns:
        dict: Classification results with error counts and examples
    """
    if not os.path.isfile(log_file):
        return {"status": "error", "message": f"Log file not found: {log_file}"}
    
    # Get analysis results
    summary = analyze_log_file(log_file)
    
    # Add root causes
    root_causes = detect_root_causes(log_file)
    summary["root_causes"] = root_causes
    
    # Calculate total issues
    summary["total_issues"] = sum(summary["counts"].values()) - summary["counts"]["lines"]
    
    # Write to output file if specified
    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("ERROR CLASSIFICATION SUMMARY\n")
            f.write(f"Log file: {log_file}\n")
            f.write(f"Workflow: {summary['workflow_name']}\n")
            f.write(f"Run ID: {summary['run_id']}\n")
            f.write(f"Timestamp: {summary['timestamp']}\n")
            f.write(f"Classification timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("="*50 + "\n\n")
            
            f.write("CRITICAL ERRORS:\n")
            f.write("="*50 + "\n")
            if summary["errors"]["critical"]:
                for i, err in enumerate(summary["errors"]["critical"]):
                    f.write(f">>> Critical error at line {err['line_num']}:\n")
                    for ctx_line_num, ctx_line in err["context"]:
                        f.write(f"{ctx_line}\n")
                    f.write("-"*50 + "\n")
            else:
                f.write("None found\n")
            f.write("\n")
            
            f.write("SEVERE ERRORS:\n")
            f.write("="*50 + "\n")
            if summary["errors"]["severe"]:
                for i, err in enumerate(summary["errors"]["severe"]):
                    f.write(f">>> Severe error at line {err['line_num']}:\n")
                    for ctx_line_num, ctx_line in err["context"]:
                        f.write(f"{ctx_line}\n")
                    f.write("-"*50 + "\n")
            else:
                f.write("None found\n")
            f.write("\n")
            
            f.write("WARNINGS:\n")
            f.write("="*50 + "\n")
            if summary["errors"]["warning"]:
                for i, err in enumerate(summary["errors"]["warning"]):
                    f.write(f">>> Warning at line {err['line_num']}:\n")
                    f.write(f"{err['line']}\n")
                    f.write("-"*50 + "\n")
            else:
                f.write("None found\n")
            f.write("\n")
            
            f.write("ERROR SUMMARY STATISTICS:\n")
            f.write("="*50 + "\n")
            f.write(f"Critical Errors: {summary['counts']['critical']}\n")
            f.write(f"Severe Errors: {summary['counts']['severe']}\n")
            f.write(f"Warnings: {summary['counts']['warning']}\n")
            f.write(f"Total Issues: {summary['total_issues']}\n\n")
            
            f.write("POSSIBLE ROOT CAUSES:\n")
            f.write("="*50 + "\n")
            for cause in root_causes:
                f.write(f"✱ {cause}\n")
                
            # Add next steps if there are errors
            if summary['total_issues'] > 0:
                f.write("\n")
                f.write("RECOMMENDED NEXT STEPS:\n")
                f.write("="*50 + "\n")
                
                if summary['counts']['critical'] > 0:
                    f.write("1. Focus on resolving critical errors first\n")
                elif summary['counts']['severe'] > 0:
                    f.write("1. Address the severe errors identified\n")
                
                # Specific recommendations based on root causes
                for cause in root_causes:
                    if "Disk space" in cause:
                        f.write("- Check GitHub Actions runner disk space utilization\n")
                        f.write("- Consider cleaning up build artifacts or using larger runners\n")
                    elif "Memory" in cause:
                        f.write("- Optimize memory usage in your build/test processes\n")
                        f.write("- Consider using a larger runner with more memory\n")
                    elif "Network" in cause:
                        f.write("- Check external service dependencies and timeouts\n")
                        f.write("- Consider adding retries for network operations\n")
                    elif "Permission" in cause:
                        f.write("- Verify GitHub token permissions and repository secrets\n")
                    elif "Version" in cause:
                        f.write("- Check for dependency version conflicts\n")
                        f.write("- Ensure your lockfile (package-lock.json, yarn.lock, etc.) is up to date\n")
                    elif "Missing module" in cause:
                        f.write("- Verify all required dependencies are installed\n")
                        f.write("- Check import/require paths for typos\n")
    
    return summary


def find_workflow_logs(logs_dir="logs", workflow_id=None, after_timestamp=None, max_logs=50):
    """
    Find workflow log files, optionally filtered by workflow ID or timestamp.
    
    Args:
        logs_dir (str): Directory containing log files
        workflow_id (str, optional): Filter by workflow run ID
        after_timestamp (str, optional): Filter logs after this timestamp (format: YYYYMMDD-HHMMSS)
        max_logs (int, optional): Maximum number of logs to return
        
    Returns:
        list: Matching log file paths
    """
    if not os.path.isdir(logs_dir):
        # Try to create the directory
        try:
            os.makedirs(logs_dir)
        except Exception:
            return []
        return []
    
    log_files = []
    
    # Walk through the logs directory
    for file in os.listdir(logs_dir):
        if not file.startswith('workflow_') or not file.endswith('.log'):
            continue
        
        # Skip error or classified files
        if file.endswith('.errors') or file.endswith('.classified'):
            continue
            
        # Extract workflow ID from filename (format: workflow_ID_TIMESTAMP.log)
        file_parts = file.split('_')
        if len(file_parts) < 3:
            continue
            
        file_workflow_id = file_parts[1]
        
        # Filter by workflow ID if specified
        if workflow_id and file_workflow_id != workflow_id:
            continue
            
        # Extract timestamp if needed for filtering
        if after_timestamp:
            try:
                timestamp_part = file_parts[2].split('.')[0]  # Format: YYYYMMDD-HHMMSS
                if timestamp_part < after_timestamp:
                    continue
            except (IndexError, ValueError):
                continue
                
        log_files.append(os.path.join(logs_dir, file))
    
    # Sort by timestamp (newest first)
    log_files.sort(reverse=True)
    
    # Limit number of logs returned
    return log_files[:max_logs]


def get_latest_workflow_logs(logs_dir="logs", count=3):
    """
    Get the most recent workflow log files.
    
    Args:
        logs_dir (str): Directory containing log files
        count (int): Number of logs to return
        
    Returns:
        list: Most recent log file paths
    """
    all_logs = find_workflow_logs(logs_dir)
    return all_logs[:count]


def find_logs_after_last_commit(logs_dir="logs", workflow_name=None, count=1):
    """
    Find workflow logs created after the last git commit.
    
    Args:
        logs_dir (str): Directory containing log files
        workflow_name (str, optional): Filter by workflow name
        count (int): Number of logs to return
        
    Returns:
        list: Log file paths after the last commit
    """
    # Get the date of the last commit
    try:
        last_commit_date = subprocess.check_output(
            ["git", "log", "-1", "--format=%cd", "--date=format:%Y%m%d-%H%M%S"], 
            stderr=subprocess.DEVNULL
        ).decode('utf-8').strip()
    except Exception:
        # If git command fails, use a old date to return all logs
        last_commit_date = "20000101-000000"
    
    all_logs = find_workflow_logs(logs_dir)
    if not all_logs:
        return []
    
    # Filter logs after the last commit date and optionally by workflow name
    recent_logs = []
    for log_file in all_logs:
        # Extract timestamp from filename
        file_parts = os.path.basename(log_file).split('_')
        if len(file_parts) >= 3:
            timestamp = file_parts[2].split('.')[0]  # Format: YYYYMMDD-HHMMSS
            
            # Check if log is newer than last commit
            if timestamp > last_commit_date:
                # If workflow name is specified, check file contents
                if workflow_name:
                    try:
                        with open(log_file, 'r', encoding='utf-8', errors='replace') as f:
                            content = f.read(10000)  # Read only the first part to check for workflow name
                            if re.search(workflow_name, content, re.IGNORECASE):
                                recent_logs.append(log_file)
                    except Exception:
                        continue
                else:
                    recent_logs.append(log_file)
    
    # Return the specified number of logs
    return recent_logs[:count]


def search_log_files(logs_dir="logs", search_pattern=None, case_sensitive=False, max_results=50):
    """
    Search across log files for a specific pattern.
    
    Args:
        logs_dir (str): Directory containing log files
        search_pattern (str): Regular expression pattern to search for
        case_sensitive (bool): Whether to use case-sensitive matching
        max_results (int): Maximum number of results to return per file
        
    Returns:
        dict: Search results with matching lines
    """
    if not search_pattern:
        return {"status": "error", "message": "Search pattern is required"}
    
    all_logs = find_workflow_logs(logs_dir)
    if not all_logs:
        return {"status": "error", "message": "No log files found"}
    
    results = {}
    total_matches = 0
    
    # Compile search pattern
    flags = 0 if case_sensitive else re.IGNORECASE
    try:
        pattern = re.compile(search_pattern, flags)
    except re.error as e:
        return {"status": "error", "message": f"Invalid search pattern: {e}"}
    
    # Search each log file
    for log_file in all_logs:
        try:
            with open(log_file, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
            
            # Find all matches with context
            matches = []
            for match in pattern.finditer(content):
                # Get a few lines of context around the match
                start_pos = max(0, match.start() - 100)
                end_pos = min(len(content), match.end() + 100)
                
                # Find line boundaries
                line_start = content.rfind('\n', start_pos, match.start())
                if line_start == -1:
                    line_start = start_pos
                else:
                    line_start += 1  # Skip the newline character
                
                line_end = content.find('\n', match.end(), end_pos)
                if line_end == -1:
                    line_end = end_pos
                
                context = content[line_start:line_end].strip()
                matches.append(context)
                
                if len(matches) >= max_results:
                    break
            
            # If we found matches, add to results
            if matches:
                file_name = os.path.basename(log_file)
                # Try to extract workflow name and run ID
                workflow_name = "Unknown"
                run_id = "Unknown"
                
                # Try to determine workflow name from content
                for name in ["Tests", "Auto Release", "Lint", "Docs"]:
                    if re.search(name, content, re.IGNORECASE):
                        workflow_name = name
                        break
                
                # Extract run ID from filename
                file_parts = file_name.split('_')
                if len(file_parts) >= 2:
                    run_id = file_parts[1]
                
                results[log_file] = {
                    "matches": matches,
                    "count": len(matches),
                    "workflow_name": workflow_name,
                    "run_id": run_id
                }
                total_matches += len(matches)
        except Exception as e:
            # Skip files with errors
            continue
    
    return {
        "status": "success",
        "search_pattern": search_pattern,
        "case_sensitive": case_sensitive,
        "total_matches": total_matches,
        "files_with_matches": len(results),
        "results": results
    }


def generate_log_statistics(logs_dir="logs"):
    """
    Generate statistics from log files.
    
    Args:
        logs_dir (str): Directory containing log files
        
    Returns:
        dict: Statistics about the log files
    """
    if not os.path.isdir(logs_dir):
        return {"status": "error", "message": "Logs directory not found"}
    
    stats = {
        "total_logs": 0,
        "error_logs": 0,
        "test_logs": 0,
        "release_logs": 0,
        "other_logs": 0,
        "total_size_bytes": 0,
        "recent_logs": []
    }
    
    # Process all log files
    all_logs = find_workflow_logs(logs_dir)
    
    for log_file in all_logs:
        stats["total_logs"] += 1
        
        # Get file size
        try:
            stats["total_size_bytes"] += os.path.getsize(log_file)
        except Exception:
            pass
        
        # Check if it has errors
        if os.path.exists(f"{log_file}.errors") and os.path.getsize(f"{log_file}.errors") > 0:
            stats["error_logs"] += 1
        
        # Try to determine log type
        try:
            with open(log_file, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read(10000)  # Read only the first part to check for workflow name
                
            if re.search(r"Tests|test|pytest|unittest|jest|mocha|check", content, re.IGNORECASE):
                stats["test_logs"] += 1
            elif re.search(r"release|deploy|publish|build|package|version", content, re.IGNORECASE):
                stats["release_logs"] += 1
            else:
                stats["other_logs"] += 1
        except Exception:
            stats["other_logs"] += 1
    
    # Get most recent logs
    stats["recent_logs"] = get_latest_workflow_logs(logs_dir, 5)
    
    # Get logs after last commit
    stats["logs_after_commit"] = find_logs_after_last_commit(logs_dir, count=10)
    
    # Calculate size in MB
    stats["total_size_mb"] = stats["total_size_bytes"] / (1024 * 1024)
    
    return stats


def cleanup_old_logs(logs_dir="logs", max_age_days=30, max_total_logs=50, dry_run=False):
    """
    Clean up old log files.
    
    Args:
        logs_dir (str): Directory containing log files
        max_age_days (int): Maximum age in days for log files
        max_total_logs (int): Maximum total log files to keep
        dry_run (bool): If True, just show what would be deleted
        
    Returns:
        dict: Clean up results
    """
    if not os.path.isdir(logs_dir):
        return {"status": "error", "message": "Logs directory not found"}
    
    results = {
        "old_logs": [],
        "total_size_bytes": 0,
        "deleted_files": [],
        "kept_files": [],
        "dry_run": dry_run
    }
    
    # Get all log files with their timestamps
    all_logs = []
    current_time = datetime.now()
    
    for file in os.listdir(logs_dir):
        if file.startswith('workflow_') and (file.endswith('.log') or file.endswith('.errors') or file.endswith('.classified')):
            file_path = os.path.join(logs_dir, file)
            
            # Extract timestamp from filename (format: workflow_ID_YYYYMMDD-HHMMSS.log)
            timestamp = None
            try:
                file_parts = file.split('_')
                if len(file_parts) >= 3:
                    timestamp_part = file_parts[2].split('.')[0]  # Format: YYYYMMDD-HHMMSS
                    timestamp = datetime.strptime(timestamp_part, "%Y%m%d-%H%M%S")
            except Exception:
                # If can't parse timestamp, use file modification time
                timestamp = datetime.fromtimestamp(os.path.getmtime(file_path))
            
            file_size = os.path.getsize(file_path)
            age_days = (current_time - timestamp).days if timestamp else 0
            
            all_logs.append({
                "path": file_path,
                "timestamp": timestamp,
                "size": file_size,
                "age_days": age_days
            })
    
    # Find logs older than max_age_days
    old_logs = [log for log in all_logs if log["age_days"] > max_age_days]
    
    for log in old_logs:
        results["old_logs"].append(log["path"])
        results["total_size_bytes"] += log["size"]
    
    # If we need to remove more logs to stay under max_total_logs
    non_old_logs = [log for log in all_logs if log["age_days"] <= max_age_days]
    all_logs_sorted = sorted(all_logs, key=lambda x: x["timestamp"] if x["timestamp"] else datetime.min)
    
    logs_to_delete = len(all_logs) - max_total_logs
    if logs_to_delete > 0:
        # Delete oldest logs first
        additional_logs = all_logs_sorted[:logs_to_delete]
        for log in additional_logs:
            if log["path"] not in results["old_logs"]:
                results["old_logs"].append(log["path"])
                results["total_size_bytes"] += log["size"]
    
    # Delete logs if not dry run
    if not dry_run:
        for log_path in results["old_logs"]:
            try:
                os.remove(log_path)
                results["deleted_files"].append(log_path)
            except Exception as e:
                results["error"] = str(e)
    
    results["total_size_mb"] = results["total_size_bytes"] / (1024 * 1024)
    results["kept_files"] = len(all_logs) - len(results["old_logs"])
    
    return results


def format_output_for_terminal(result, color_output=True):
    """
    Format analysis results for terminal display with optional ANSI colors.
    
    Args:
        result (dict): Analysis results to format
        color_output (bool): Whether to use ANSI color codes
        
    Returns:
        str: Formatted output for terminal
    """
    if not color_output:
        RESET = ""
        RED = ""
        GREEN = ""
        YELLOW = ""
        BLUE = ""
        MAGENTA = ""
        CYAN = ""
        BOLD = ""
    else:
        RESET = COLORS["RESET"]
        RED = COLORS["RED"]
        GREEN = COLORS["GREEN"]
        YELLOW = COLORS["YELLOW"]
        BLUE = COLORS["BLUE"]
        MAGENTA = COLORS["MAGENTA"]
        CYAN = COLORS["CYAN"]
        BOLD = COLORS["BOLD"]
    
    lines = []
    
    # Check for error status
    if result.get("status") == "error":
        lines.append(f"{RED}ERROR: {result['message']}{RESET}")
        return "\n".join(lines)
    
    # Format header
    lines.append(f"{BOLD}{CYAN}WORKFLOW LOG ANALYSIS{RESET}")
    lines.append(f"Log file: {result['log_file']}")
    
    if result.get("workflow_name") and result.get("workflow_name") != "Unknown":
        lines.append(f"Workflow: {result['workflow_name']}")
    
    if result.get("run_id") and result.get("run_id") != "Unknown":
        lines.append(f"Run ID: {result['run_id']}")
    
    if result.get("timestamp") and result.get("timestamp") != "Unknown":
        lines.append(f"Timestamp: {result['timestamp']}")
    
    lines.append("")
    
    # Format error statistics
    lines.append(f"{BOLD}{CYAN}ERROR STATISTICS:{RESET}")
    counts = result["counts"]
    lines.append(f"{RED}Critical Errors: {counts['critical']}{RESET}")
    lines.append(f"{MAGENTA}Severe Errors: {counts['severe']}{RESET}")
    lines.append(f"{YELLOW}Warnings: {counts['warning']}{RESET}")
    total_issues = counts['critical'] + counts['severe'] + counts['warning']
    lines.append(f"Total Issues: {total_issues}")
    lines.append("")
    
    # Display error samples
    if counts['critical'] > 0:
        lines.append(f"{BOLD}{RED}CRITICAL ERROR SAMPLES:{RESET}")
        for err in result["errors"]["critical"][:5]:  # Limit to first 5
            lines.append(f"{RED}Line {err['line_num']}:{RESET} {err['line']}")
            
            # Add a few lines of context
            for ctx_line_num, ctx_line in err["context"]:
                if ctx_line_num == err['line_num']:
                    lines.append(f"   {RED}→ {ctx_line}{RESET}")
                else:
                    lines.append(f"     {ctx_line}")
            
            lines.append("-" * 50)
        lines.append("")
    
    if counts['severe'] > 0:
        lines.append(f"{BOLD}{MAGENTA}SEVERE ERROR SAMPLES:{RESET}")
        for err in result["errors"]["severe"][:3]:  # Limit to first 3
            lines.append(f"{MAGENTA}Line {err['line_num']}:{RESET} {err['line']}")
            lines.append("-" * 50)
        lines.append("")
    
    # Display root causes
    if result.get("root_causes"):
        lines.append(f"{BOLD}{CYAN}POSSIBLE ROOT CAUSES:{RESET}")
        for cause in result["root_causes"]:
            lines.append(f"✱ {cause}")
        lines.append("")
    
    # Recommendations if there are issues
    if total_issues > 0:
        lines.append(f"{BOLD}{CYAN}RECOMMENDATIONS:{RESET}")
        
        if counts['critical'] > 0:
            lines.append(f"1. {BOLD}Address critical errors first:{RESET}")
            
            # Process recommendations based on root causes
            has_node_memory_issue = False
            has_process_limit_issue = False
            
            for cause in result.get("root_causes", []):
                # Extract core recommendations from the root causes
                if "Node.js memory limit exceeded" in cause or "JavaScript heap out of memory" in cause:
                    has_node_memory_issue = True
                elif "Process resource limit" in cause or "Concurrent process overload" in cause:
                    has_process_limit_issue = True
                
                # Add standard recommendations based on pattern matching
                if "Disk space" in cause:
                    lines.append("   - Check GitHub Actions runner disk space")
                    lines.append("   - Consider using larger runners or cleaning build artifacts")
                elif "Memory issue" in cause and not has_node_memory_issue:
                    lines.append("   - Optimize memory usage or use a larger runner")
                elif "Network" in cause:
                    lines.append("   - Check external service dependencies")
                    lines.append("   - Consider adding network operation retries")
                elif "Permission" in cause:
                    lines.append("   - Verify GitHub token permissions and repository secrets")
                elif "npm dependency" in cause or "Node.js dependency" in cause:
                    lines.append("   - Check package.json and package-lock.json for inconsistencies")
                    lines.append("   - Verify all dependencies are correctly installed")
            
            # Special detailed handling for Node.js memory issues
            if has_node_memory_issue:
                lines.append(f"{RED}   Node.js Memory Management Recommendations:{RESET}")
                lines.append("   1. Implement process guardian for Node.js")
                lines.append("      - Use helpers/shell/process_guardian.py to monitor Node.js processes")
                lines.append("      - Set up a wrapper script for Node.js commands")
                lines.append("   2. Set memory limits for Node.js processes")
                lines.append("      - Use NODE_OPTIONS=\"--max-old-space-size=768\" to limit memory usage")
                lines.append("      - Consider using lower limits like 512MB if appropriate")
                lines.append("   3. Implement process queuing to limit concurrent Node.js processes")
                lines.append("      - Use a thread pool and process queue in process_guardian.py")
                lines.append("      - Set a maximum of 2-3 concurrent Node.js processes")
            
            # Special handling for process limit issues
            if has_process_limit_issue:
                lines.append(f"{MAGENTA}   Process Management Recommendations:{RESET}")
                lines.append("   1. Implement process pooling and queuing")
                lines.append("   2. Reduce the number of concurrent processes")
                lines.append("   3. Set limits on file handles and other resources")
        
        elif counts['severe'] > 0:
            lines.append(f"1. {BOLD}Investigate severe errors:{RESET}")
            lines.append("   - Check for dependency conflicts or version issues")
            lines.append("   - Look for configuration problems")
            
            # Add specific guidance based on error patterns
            for err in result["errors"]["severe"][:2]:  # Just check a couple examples
                if "npm ERR!" in err.get("line", ""):
                    lines.append("   - Check for npm-related issues:")
                    lines.append("     • Review package.json dependencies")
                    lines.append("     • Verify node_modules integrity")
                    lines.append("     • Consider using npm ci instead of npm install")
                elif "test" in err.get("line", "").lower() and "fail" in err.get("line", "").lower():
                    lines.append("   - Examine failed tests and fix test-specific issues")
                    lines.append("     • Check test fixtures and mocked dependencies")
                    lines.append("     • Verify test environment configuration")
    
    return "\n".join(lines)


def analyze_and_report(log_file, output_format="text"):
    """
    Analyze a log file and generate a report in the specified format.
    
    Args:
        log_file (str): Path to the log file
        output_format (str): Output format (text, json, tsv, html)
        
    Returns:
        tuple: (report_content, exit_code)
    """
    # Validate log file
    log_path = Path(log_file)
    if not log_path.exists():
        return f"Error: Log file '{log_file}' not found", 1
    
    # Analyze the log
    try:
        summary = analyze_log_file(log_file)
        root_causes = detect_root_causes(log_file)
        
        # Add root causes to summary
        summary["root_causes"] = root_causes
        
        # Generate report in requested format
        if output_format == "json":
            return json.dumps(summary, indent=2), 0
            
        elif output_format == "tsv":
            tsv_output = []
            tsv_output.append(f"critical\t{summary['counts']['critical']}")
            tsv_output.append(f"severe\t{summary['counts']['severe']}")
            tsv_output.append(f"warning\t{summary['counts']['warning']}")
            tsv_output.append(f"total\t{summary['counts']['critical'] + summary['counts']['severe'] + summary['counts']['warning']}")
            tsv_output.append(f"lines\t{summary['counts']['lines']}")
            tsv_output.append(f"root_causes\t{';'.join(root_causes)}")
            return "\n".join(tsv_output), 0
            
        elif output_format == "html":
            html_output = ["<html><head><title>Workflow Log Analysis</title>",
                           "<style>",
                           "body {font-family: Arial, sans-serif; margin: 20px;}",
                           "h1 {color: #333;}",
                           "h2 {color: #0066cc;}",
                           ".critical {color: #cc0000; font-weight: bold;}",
                           ".severe {color: #cc3300;}",
                           ".warning {color: #cc9900;}",
                           ".code {font-family: monospace; background-color: #f5f5f5; padding: 10px; border-radius: 5px;}",
                           "</style></head><body>",
                           "<h1>Workflow Log Analysis</h1>",
                           f"<p><strong>Log file:</strong> {summary['log_file']}</p>",
                           f"<p><strong>Workflow:</strong> {summary['workflow_name']}</p>",
                           f"<p><strong>Run ID:</strong> {summary['run_id']}</p>",
                           f"<p><strong>Timestamp:</strong> {summary['timestamp']}</p>",
                           "<h2>Error Statistics</h2>",
                           f"<p class='critical'>Critical Errors: {summary['counts']['critical']}</p>",
                           f"<p class='severe'>Severe Errors: {summary['counts']['severe']}</p>",
                           f"<p class='warning'>Warnings: {summary['counts']['warning']}</p>"]
            
            # Add error samples
            if summary['counts']['critical'] > 0:
                html_output.append("<h2>Critical Error Samples</h2>")
                for err in summary["errors"]["critical"]:
                    html_output.append("<div class='code'>")
                    html_output.append(f"<p class='critical'>Line {err['line_num']}: {err['line']}</p>")
                    html_output.append("</div>")
            
            # Add root causes
            html_output.append("<h2>Possible Root Causes</h2><ul>")
            for cause in root_causes:
                html_output.append(f"<li>{cause}</li>")
            html_output.append("</ul>")
            
            html_output.append("</body></html>")
            return "\n".join(html_output), 0
            
        else:
            # Default to text format with ANSI colors
            return format_output_for_terminal(summary), 0
    except Exception as e:
        return f"Error analyzing log: {str(e)}", 1


def main():
    """
    Main function for command-line usage with enhanced subcommands.
    """
    parser = argparse.ArgumentParser(
        description="Comprehensive GitHub Actions workflow log analysis tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m helpers.errors.log_analyzer analyze logs/workflow_12345678.log
  python -m helpers.errors.log_analyzer find --id 12345678
  python -m helpers.errors.log_analyzer latest --count 5
  python -m helpers.errors.log_analyzer search "error pattern"
  python -m helpers.errors.log_analyzer cleanup --age 15 --dry-run
  python -m helpers.errors.log_analyzer stats
  python -m helpers.errors.log_analyzer repo
""")
    
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # analyze command
    analyze_parser = subparsers.add_parser("analyze", help="Analyze a log file")
    analyze_parser.add_argument("log_file", help="Path to the log file")
    analyze_parser.add_argument("--output", "-o", help="Output file for detailed analysis")
    analyze_parser.add_argument("--format", choices=["text", "json", "tsv", "html"], default="text",
                            help="Output format")
    analyze_parser.add_argument("--no-color", action="store_true", help="Disable colored output")
    
    # find command
    find_parser = subparsers.add_parser("find", help="Find workflow logs")
    find_parser.add_argument("--id", help="Filter by workflow run ID")
    find_parser.add_argument("--after", help="Filter logs after timestamp (YYYYMMDD-HHMMSS)")
    find_parser.add_argument("--dir", default="logs", help="Logs directory")
    find_parser.add_argument("--count", type=int, default=5, help="Maximum number of logs to return")
    
    # latest command
    latest_parser = subparsers.add_parser("latest", help="Get latest logs")
    latest_parser.add_argument("--dir", default="logs", help="Logs directory")
    latest_parser.add_argument("--count", type=int, default=3, help="Number of logs to return")
    latest_parser.add_argument("--after-commit", action="store_true", help="Only show logs after last commit")
    
    # search command
    search_parser = subparsers.add_parser("search", help="Search across log files")
    search_parser.add_argument("pattern", help="Regular expression pattern to search for")
    search_parser.add_argument("--case-sensitive", action="store_true", help="Use case-sensitive matching")
    search_parser.add_argument("--max-results", type=int, default=50, help="Maximum results per file")
    search_parser.add_argument("--dir", default="logs", help="Logs directory")
    
    # stats command
    stats_parser = subparsers.add_parser("stats", help="Generate statistics about log files")
    stats_parser.add_argument("--dir", default="logs", help="Logs directory")
    
    # cleanup command
    cleanup_parser = subparsers.add_parser("cleanup", help="Clean up old log files")
    cleanup_parser.add_argument("--age", type=int, default=30, help="Maximum age in days")
    cleanup_parser.add_argument("--max-logs", type=int, default=50, help="Maximum total logs to keep")
    cleanup_parser.add_argument("--dry-run", action="store_true", help="Just show what would be deleted")
    cleanup_parser.add_argument("--dir", default="logs", help="Logs directory")
    
    # repo command
    subparsers.add_parser("repo", help="Detect repository information")
    
    # Parse arguments
    args = parser.parse_args()
    
    # Handle command not specified
    if not args.command:
        parser.print_help()
        return 1
    
    # Process commands
    if args.command == "analyze":
        if not args.log_file:
            print("Error: Log file path is required")
            return 1
            
        result = classify_log_errors(args.log_file, args.output)
        
        if result["status"] == "error":
            print(f"Error: {result['message']}")
            return 1
            
        if args.format == "json":
            print(json.dumps(result, indent=2))
        elif args.format == "tsv":
            print(f"critical\t{result['counts']['critical']}")
            print(f"severe\t{result['counts']['severe']}")
            print(f"warning\t{result['counts']['warning']}")
            print(f"total\t{result['total_issues']}")
            print(f"root_causes\t{';'.join(result['root_causes'])}")
        else:
            # Text format with optional colors
            print(format_output_for_terminal(result, not args.no_color))
        
    elif args.command == "find":
        logs_dir = args.dir
        logs = find_workflow_logs(logs_dir, args.id, args.after, args.count)
        
        if not logs:
            print("No matching log files found")
            return 0
            
        print(f"Found {len(logs)} matching log file(s):")
        for log in logs:
            print(f"- {log}")
            
    elif args.command == "latest":
        logs_dir = args.dir
        
        if args.after_commit:
            logs = find_logs_after_last_commit(logs_dir, count=args.count)
            source = "after last commit"
        else:
            logs = get_latest_workflow_logs(logs_dir, args.count)
            source = "by timestamp"
        
        if not logs:
            print(f"No log files found {source}")
            return 0
            
        print(f"Latest {len(logs)} log file(s) {source}:")
        for log in logs:
            print(f"- {log}")
            
    elif args.command == "search":
        results = search_log_files(args.dir, args.pattern, args.case_sensitive, args.max_results)
        
        if results["status"] == "error":
            print(f"Error: {results['message']}")
            return 1
            
        print(f"Found {results['total_matches']} matches in {results['files_with_matches']} files")
        
        for log_file, data in results["results"].items():
            print(f"\nFile: {log_file}")
            print(f"Workflow: {data['workflow_name']}, Run ID: {data['run_id']}")
            print(f"Matches: {data['count']}")
            print("="*50)
            
            for i, match in enumerate(data["matches"]):
                print(f"{i+1}. {match}")
                print("-"*30)
                
    elif args.command == "stats":
        stats = generate_log_statistics(args.dir)
        
        if "status" in stats and stats["status"] == "error":
            print(f"Error: {stats['message']}")
            return 1
            
        print("Log Files Statistics:")
        print("="*50)
        print(f"Total log files:        {stats['total_logs']}")
        print(f"Files with errors:      {stats['error_logs']}")
        print(f"Test workflow logs:     {stats['test_logs']}")
        print(f"Release workflow logs:  {stats['release_logs']}")
        print(f"Other workflow logs:    {stats['other_logs']}")
        print(f"Total log size:         {stats['total_size_mb']:.2f} MB")
        
        if stats.get('recent_logs'):
            print("\nMost recent logs:")
            for log in stats['recent_logs']:
                print(f"- {log}")
                
        if stats.get('logs_after_commit'):
            print("\nLogs after last commit:")
            for log in stats['logs_after_commit']:
                print(f"- {log}")
                
    elif args.command == "cleanup":
        results = cleanup_old_logs(args.dir, args.age, args.max_logs, args.dry_run)
        
        if "status" in results and results["status"] == "error":
            print(f"Error: {results['message']}")
            return 1
            
        print(f"Found {len(results['old_logs'])} log files older than {args.age} days")
        print(f"Total size: {results['total_size_mb']:.2f} MB")
        
        if results["dry_run"]:
            print("\nDry run mode - no files deleted")
            if results["old_logs"]:
                print("Would delete the following files:")
                for log in results["old_logs"]:
                    print(f"- {log}")
        else:
            print(f"\nDeleted {len(results['deleted_files'])} files")
            print(f"Kept {results['kept_files']} files")
            
    elif args.command == "repo":
        owner, name, full_name = detect_repository_info()
        
        print("Repository Information:")
        print("="*50)
        print(f"Owner:      {owner}")
        print(f"Name:       {name}")
        print(f"Full name:  {full_name}")
        
        # Also try to detect workflows
        workflows = detect_workflow_categories()
        
        print("\nWorkflows:")
        print("="*50)
        if workflows["test"]:
            print(f"Test workflows:     {', '.join(workflows['test'])}")
        if workflows["release"]:
            print(f"Release workflows:  {', '.join(workflows['release'])}")
        if workflows["lint"]:
            print(f"Lint workflows:     {', '.join(workflows['lint'])}")
        if workflows["docs"]:
            print(f"Docs workflows:     {', '.join(workflows['docs'])}")
        if workflows["other"]:
            print(f"Other workflows:    {', '.join(workflows['other'])}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())