#!/usr/bin/env python3
"""
Log analysis and error classification tool for GitHub Actions workflow logs.

This module provides functions to:
- Analyze workflow logs for errors and warnings
- Classify issues by severity
- Identify root causes of failures
- Generate structured summary reports

Usage:
    python -m helpers.errors.log_analyzer /path/to/log_file.log [--json] [--tsv]
"""

import argparse
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
    """Detect potential root causes for workflow failures."""
    root_causes = []
    
    try:
        with open(log_file, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
            
            # Check for common root causes
            if re.search(r"No space left on device|disk space|quota exceeded", content, re.IGNORECASE):
                root_causes.append("Disk space issue detected - runner may have run out of disk space")
                
            if re.search(r"memory allocation|out of memory|cannot allocate|allocation failed|OOM|Killed", content, re.IGNORECASE):
                root_causes.append("Memory issue detected - process may have run out of memory")
                
            if re.search(r"network.*timeout|connection.*refused|unreachable|DNS|proxy|firewall", content, re.IGNORECASE):
                root_causes.append("Network connectivity issue detected - check network settings or dependencies")
                
            if re.search(r"permission denied|access denied|unauthorized|forbidden|EACCES", content, re.IGNORECASE):
                root_causes.append("Permission issue detected - check access rights or secrets")
                
            if re.search(r"version mismatch|incompatible|requires version|dependency", content, re.IGNORECASE):
                root_causes.append("Dependency or version compatibility issue detected")
                
            if re.search(r"import error|module not found|cannot find module|unknown module", content, re.IGNORECASE):
                root_causes.append("Missing import or module - check package installation")
                
            if re.search(r"timeout|timed out|deadline exceeded|cancelled", content, re.IGNORECASE):
                root_causes.append("Operation timeout detected - workflow may have exceeded time limits")
                
            if re.search(r"syntax error|parsing error|unexpected token", content, re.IGNORECASE):
                root_causes.append("Syntax error detected - check recent code changes")
            
            # GitHub-specific issues
            if re.search(r"Resource not accessible by integration|not authorized to perform", content, re.IGNORECASE):
                root_causes.append("Authorization issue - check GitHub token permissions")
                
            if re.search(r"workflow cannot access secrets|secret.*not found", content, re.IGNORECASE):
                root_causes.append("Secret access issue - check if required secrets are properly configured")
    
    except Exception as e:
        print(f"Error analyzing for root causes: {e}", file=sys.stderr)
    
    return root_causes


def format_summary(summary, root_causes):
    """Format the error summary for output."""
    if not summary:
        return "Failed to generate summary"
    
    # ANSI color codes
    RED = '\033[1;31m'
    YELLOW = '\033[1;33m'
    MAGENTA = '\033[1;35m'
    CYAN = '\033[1;36m'
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
    
    # Root causes
    if root_causes:
        output.append(f"{CYAN}POSSIBLE ROOT CAUSES:{RESET}")
        for cause in root_causes:
            output.append(f"- {cause}")
    else:
        output.append(f"{CYAN}No specific root cause identified automatically.{RESET}")
    
    return "\n".join(output)


def analyze_and_report(log_file, output_format="text"):
    """Analyze a log file and generate a report in the specified format."""
    # Validate log file
    log_path = Path(log_file)
    if not log_path.exists():
        return f"Error: Log file '{log_file}' not found", 1
    
    # Analyze the log
    summary = analyze_log_file(log_file)
    root_causes = detect_root_causes(log_file)
    
    # Generate report in requested format
    if output_format == "json":
        import json
        summary["root_causes"] = root_causes
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
    else:
        # Default to text format
        return format_summary(summary, root_causes), 0


def main():
    parser = argparse.ArgumentParser(description="Analyze GitHub Actions workflow logs")
    parser.add_argument("log_file", help="Path to the workflow log file")
    parser.add_argument("--json", action="store_true", help="Output in JSON format")
    parser.add_argument("--tsv", action="store_true", help="Output in TSV format (for shell scripts)")
    
    args = parser.parse_args()
    
    # Determine output format
    if args.json:
        output_format = "json"
    elif args.tsv:
        output_format = "tsv"
    else:
        output_format = "text"
    
    # Analyze and report
    report, exit_code = analyze_and_report(args.log_file, output_format)
    print(report)
    
    return exit_code


if __name__ == "__main__":
    sys.exit(main())