#!/usr/bin/env python3
"""
Script to parse and summarize GitHub Actions workflow logs.
Used by get_errorlogs.sh to provide better error summaries.
"""

import argparse
import os
import re
import sys
from pathlib import Path


def parse_error_patterns():
    """Define error patterns by severity."""
    patterns = {
        "critical": [
            r"Process completed with exit code [1-9]",
            r"fatal error",
            r"fatal:",
            r"FATAL ERROR",
            r"Assertion failed",
            r"Segmentation fault",
            r"core dumped",
            r"killed",
            r"ERROR:",
            r"Connection refused",
            r"panic",
            r"PANIC",
            r"assert",
            r"ASSERT",
            r"terminated",
            r"abort",
            r"SIGSEGV",
            r"SIGABRT",
            r"SIGILL",
            r"SIGFPE",
            r"Reached heap limit",
            r"JavaScript heap out of memory",
            r"allocation failed",
            r"FATAL",
            r"unhandled exception",
            r"Critical",
        ],
        "severe": [
            r"exit code [1-9]",
            r"failure:",
            r"failed with",
            r"FAILED",
            r"Exception",
            r"exception:",
            r"Error:",
            r"error:",
            r"undefined reference",
            r"Cannot find",
            r"not found",
            r"No such file",
            r"Permission denied",
            r"AccessDenied",
            r"Could not access",
            r"Cannot access",
            r"ImportError",
            r"ModuleNotFoundError",
            r"TypeError",
            r"ValueError",
            r"KeyError",
            r"AttributeError",
            r"AssertionError",
            r"UnboundLocalError",
            r"IndexError",
            r"SyntaxError",
            r"NameError",
            r"RuntimeError",
            r"unexpected",
            r"failed to",
            r"EACCES",
            r"EPERM",
            r"ENOENT",
            r"compilation failed",
            r"command failed",
            r"exited with code",
            r"timed out",
            r"Maximum execution time exceeded",
            r"Process terminated",
            r"Failed to install",
            r"npm ERR!",
            r"yarn error",
            r"Cannot resolve",
            r"Module build failed",
        ],
        "warning": [
            r"WARNING:",
            r"warning:",
            r"deprecated",
            r"Deprecated",
            r"DEPRECATED",
            r"fixme",
            r"FIXME",
            r"TODO",
            r"todo:",
            r"ignored",
            r"skipped",
            r"suspicious",
            r"insecure",
            r"unsafe",
            r"consider",
            r"recommended",
            r"inconsistent",
            r"possibly",
            r"PendingDeprecationWarning",
            r"FutureWarning",
            r"UserWarning",
            r"ResourceWarning",
            r"high memory usage",
            r"high cpu usage",
            r"possible memory leak",
            r"slow operation",
            r"optimization opportunity",
        ],
    }
    
    # Compile patterns for better performance
    compiled_patterns = {}
    for severity, pattern_list in patterns.items():
        compiled_patterns[severity] = [re.compile(pat, re.IGNORECASE) for pat in pattern_list]
    
    return compiled_patterns


def analyze_log_file(log_file):
    """Analyze a workflow log file and return a summary of errors."""
    error_patterns = parse_error_patterns()
    
    # Initialize counters
    counts = {
        "critical": 0,
        "severe": 0,
        "warning": 0,
        "lines": 0
    }
    
    # Initialize error storage
    errors = {
        "critical": [],
        "severe": [],
        "warning": []
    }
    
    # Process the file line by line
    try:
        with open(log_file, 'r', encoding='utf-8', errors='replace') as f:
            for line_num, line in enumerate(f, 1):
                counts["lines"] += 1
                line = line.strip()
                
                # Check each error pattern
                for severity, patterns in error_patterns.items():
                    for pattern in patterns:
                        if pattern.search(line):
                            counts[severity] += 1
                            
                            # Store the error with context (line number and text)
                            if len(errors[severity]) < 10:  # Limit to 10 errors per category
                                errors[severity].append((line_num, line))
                            
                            # Once we've matched a pattern for this severity, no need to check others
                            break
    except Exception as e:
        print(f"Error reading log file: {e}", file=sys.stderr)
        return None
    
    # Generate the summary
    summary = {
        "counts": counts,
        "errors": errors,
        "log_file": log_file
    }
    
    return summary


def detect_root_causes(log_file):
    """Detect potential root causes for workflow failures with enhanced diagnostics."""
    root_causes = []
    
    try:
        with open(log_file, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
            
            # Check for common root causes with mitigation suggestions
            if re.search(r"No space left on device|disk space|quota exceeded|file system.*full|insufficient space", content, re.IGNORECASE):
                root_causes.append("Disk space issue detected - Consider cleaning up build artifacts or using a larger runner")
                
            # Specialized detection for Node.js memory issues
            if re.search(r"JavaScript heap out of memory|Reached heap limit|--max-old-space-size|heap is too small|v8.*memory|node.*memory|FATAL ERROR: Reached heap limit", content, re.IGNORECASE):
                # Try to extract memory limit if present
                mem_limit_match = re.search(r"--max-old-space-size=(\d+)", content)
                if mem_limit_match:
                    current_limit = mem_limit_match.group(1)
                    root_causes.append(f"Node.js memory limit ({current_limit}MB) exceeded - Consider implementing process guardian or increasing limit")
                else:
                    root_causes.append("Node.js memory limit exceeded - Consider implementing process guardian with memory management")
            # General memory issues (if not already covered by Node.js specific detection)
            elif re.search(r"memory allocation|out of memory|cannot allocate|allocation failed|OOM|Killed", content, re.IGNORECASE):
                root_causes.append("Memory issue detected - Optimize memory usage or use a larger runner")
                
            if re.search(r"network.*timeout|connection.*refused|unreachable|DNS|proxy|firewall|socket.*timeout|host.*unreachable|TLS handshake|SSL certificate|name resolution", content, re.IGNORECASE):
                root_causes.append("Network connectivity issue detected - Check network settings or add retry mechanisms")
                
            if re.search(r"permission denied|access denied|unauthorized|forbidden|EACCES|EPERM|inadequate permissions|not allowed|restricted access", content, re.IGNORECASE):
                root_causes.append("Permission issue detected - Check access rights or GitHub token permissions")
                
            if re.search(r"version mismatch|incompatible|requires version|dependency|wrong version|version conflict|unsupported version|requires.*at least|not compatible", content, re.IGNORECASE):
                root_causes.append("Dependency or version compatibility issue detected - Verify dependency versions")
                
            if re.search(r"import error|module not found|cannot find module|unknown module|no module named|cannot import|required module", content, re.IGNORECASE):
                root_causes.append("Missing import or module - Ensure all required packages are installed")
                
            if re.search(r"timeout|timed out|deadline exceeded|cancelled|operation timed out|execution time exceeded|timeout.*exceeded", content, re.IGNORECASE):
                root_causes.append("Operation timeout detected - Increase timeouts or optimize slow processes")
                
            if re.search(r"syntax error|parsing error|unexpected token|invalid syntax|unexpected character|EOF.*expected|parse.*failed|unterminated string", content, re.IGNORECASE):
                root_causes.append("Syntax error detected - Check recent code changes for syntax issues")
                
            # GitHub-specific issues
            if re.search(r"Resource not accessible by integration|not authorized to perform|workflow cannot access secrets|secret.*not found|GITHUB_TOKEN permissions", content, re.IGNORECASE):
                root_causes.append("GitHub permissions issue - Check workflow permissions and repository settings")
            
            # Concurrent process issues
            if re.search(r"too many processes|process limit|thread limit exceeded|fork.*failed|cannot create.*thread|resource temporarily unavailable|too many open files", content, re.IGNORECASE):
                root_causes.append("Process resource limit reached - Implement a process guardian with queue")
                
            # Node.js dependency issues
            if re.search(r"npm ERR!|yarn error|package.*not found|Cannot resolve|Module build failed|Failed to resolve dependencies|dependency tree|node_modules.*missing", content, re.IGNORECASE):
                if re.search(r"404 Not Found|could not resolve|npm ERR! 404", content, re.IGNORECASE):
                    pkg_name = re.search(r"404.*?([a-zA-Z0-9@/_-]+)", content)
                    if pkg_name:
                        root_causes.append(f"npm dependency error - Package not found: {pkg_name.group(1)}")
                    else:
                        root_causes.append("npm dependency error - Package not found")
                elif re.search(r"peer dependency|npm ERR! peer dep missing", content, re.IGNORECASE):
                    root_causes.append("npm peer dependency conflict - Check compatible versions")
                else:
                    root_causes.append("Node.js dependency issues - Check package.json and lockfiles")
            
            # Test failures
            if ("Tests" in os.path.basename(log_file) or "test" in os.path.basename(log_file).lower()):
                # Look for pytest failures
                if "pytest" in content.lower() and re.search(r"failed=\d+", content):
                    test_count = re.search(r"failed=(\d+)", content)
                    if test_count:
                        root_causes.append(f"Test failures detected - {test_count.group(1)} tests failed")
                # Look for Jest/Mocha test failures
                elif re.search(r"Test Suites:\s+\d+\s+failed", content) or re.search(r"Tests:\s+\d+\s+failed", content):
                    test_suites = re.search(r"Test Suites:\s+(\d+)\s+failed", content)
                    tests = re.search(r"Tests:\s+(\d+)\s+failed", content)
                    if test_suites and tests:
                        root_causes.append(f"JavaScript test failures - {test_suites.group(1)} test suites and {tests.group(1)} tests failed")
                    elif test_suites:
                        root_causes.append(f"JavaScript test failures - {test_suites.group(1)} test suites failed")
                    elif tests:
                        root_causes.append(f"JavaScript test failures - {tests.group(1)} tests failed")
            
            # File system errors
            if re.search(r"ENOSPC|EMFILE|ENFILE", content):
                if "ENOSPC" in content:
                    root_causes.append("File system space exhausted - Free up disk space or use larger runner")
                if "EMFILE" in content:
                    root_causes.append("Too many open files - Implement process pooling or file handle management")
    
    except Exception as e:
        print(f"Error analyzing for root causes: {e}", file=sys.stderr)
    
    # Remove duplicates while preserving order
    unique_causes = []
    for cause in root_causes:
        if cause not in unique_causes:
            unique_causes.append(cause)
    
    if not unique_causes:
        unique_causes = ["No specific root cause identified automatically"]
    
    return unique_causes


def format_summary(summary, root_causes):
    """Format the error summary for output with enhanced formatting for Node.js issues."""
    if not summary:
        return "Failed to generate summary"
    
    # ANSI color codes
    RED = '\033[1;31m'
    YELLOW = '\033[1;33m'
    MAGENTA = '\033[1;35m'
    CYAN = '\033[1;36m'
    GREEN = '\033[1;32m'
    BOLD = '\033[1m'
    RESET = '\033[0m'
    
    output = []
    output.append(f"{CYAN}WORKFLOW ANALYSIS SUMMARY{RESET}")
    output.append(f"Log file: {summary['log_file']}")
    output.append(f"Total lines processed: {summary['counts']['lines']}")
    output.append("")
    
    # Error counts
    output.append(f"{CYAN}ERROR STATISTICS:{RESET}")
    output.append(f"{RED}Critical errors: {summary['counts']['critical']}{RESET}")
    output.append(f"{MAGENTA}Severe errors: {summary['counts']['severe']}{RESET}")
    output.append(f"{YELLOW}Warnings: {summary['counts']['warning']}{RESET}")
    output.append(f"Total issues: {summary['counts']['critical'] + summary['counts']['severe'] + summary['counts']['warning']}")
    output.append("")
    
    # Sample errors
    if summary['counts']['critical'] > 0:
        output.append(f"{RED}CRITICAL ERROR SAMPLES:{RESET}")
        for line_num, line in summary['errors']['critical']:
            output.append(f"Line {line_num}: {line}")
        output.append("")
    
    if summary['counts']['severe'] > 0:
        output.append(f"{MAGENTA}SEVERE ERROR SAMPLES:{RESET}")
        for line_num, line in summary['errors']['severe']:
            output.append(f"Line {line_num}: {line}")
        output.append("")
    
    # Root causes with enhanced formatting
    if root_causes:
        output.append(f"{CYAN}POSSIBLE ROOT CAUSES:{RESET}")
        
        # Check for Node.js specific issues
        has_node_memory_issue = any("Node.js memory limit" in cause for cause in root_causes)
        has_process_limit_issue = any("Process resource limit" in cause or "Too many" in cause for cause in root_causes)
        
        # Display root causes with formatting based on type
        for cause in root_causes:
            if "Node.js memory limit" in cause or "JavaScript heap out of memory" in cause:
                output.append(f"{RED}{BOLD}✱ {cause}{RESET}")
            elif "Process resource limit" in cause or "Too many" in cause:
                output.append(f"{MAGENTA}{BOLD}✱ {cause}{RESET}")
            else:
                output.append(f"✱ {cause}")
        
        # Add specialized recommendations for Node.js issues
        if has_node_memory_issue:
            output.append("")
            output.append(f"{BOLD}{RED}NODE.JS MEMORY MANAGEMENT RECOMMENDATIONS:{RESET}")
            output.append("1. Implement process guardian for Node.js processes")
            output.append("   - Use process_guardian.py to monitor and limit Node.js memory")
            output.append("   - Set up a wrapper script for all Node.js commands")
            output.append("2. Limit memory usage with NODE_OPTIONS")
            output.append("   - Set NODE_OPTIONS=\"--max-old-space-size=768\"")
            output.append("3. Implement process queuing")
            output.append("   - Limit concurrent Node.js processes to 2-3 maximum")
            
        if has_process_limit_issue:
            output.append("")
            output.append(f"{BOLD}{MAGENTA}PROCESS MANAGEMENT RECOMMENDATIONS:{RESET}")
            output.append("1. Implement process pooling and queuing")
            output.append("2. Reduce the number of concurrent processes")
            output.append("3. Set limits on file handles and other resources")
    else:
        output.append(f"{CYAN}No specific root cause identified automatically.{RESET}")
    
    return "\n".join(output)


def main():
    parser = argparse.ArgumentParser(description="Analyze GitHub Actions workflow logs")
    parser.add_argument("log_file", help="Path to the workflow log file")
    parser.add_argument("--json", action="store_true", help="Output in JSON format")
    parser.add_argument("--tsv", action="store_true", help="Output in TSV format (for shell scripts)")
    
    args = parser.parse_args()
    
    log_file = args.log_file
    if not Path(log_file).exists():
        print(f"Error: Log file '{log_file}' not found", file=sys.stderr)
        return 1
    
    summary = analyze_log_file(log_file)
    root_causes = detect_root_causes(log_file)
    
    if args.json:
        import json
        summary["root_causes"] = root_causes
        print(json.dumps(summary, indent=2))
    elif args.tsv:
        print(f"critical\t{summary['counts']['critical']}")
        print(f"severe\t{summary['counts']['severe']}")
        print(f"warning\t{summary['counts']['warning']}")
        print(f"total\t{summary['counts']['critical'] + summary['counts']['severe'] + summary['counts']['warning']}")
        print(f"lines\t{summary['counts']['lines']}")
        print(f"root_causes\t{';'.join(root_causes)}")
    else:
        print(format_summary(summary, root_causes))
    
    return 0


if __name__ == "__main__":
    sys.exit(main())