#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test runner for all tests without requiring pytest
"""

import sys
import os
import traceback
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Color codes for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'
BOLD = '\033[1m'

def run_test_method(test_obj, method_name):
    """Run a single test method and return success status"""
    try:
        method = getattr(test_obj, method_name)
        method()
        return True, None
    except Exception as e:
        return False, str(e)

def run_test_class(class_obj, class_name):
    """Run all test methods in a test class"""
    print(f"\n{BLUE}Running {class_name}{RESET}")
    print("=" * 60)
    
    test_instance = class_obj()
    passed = 0
    failed = 0
    
    # Get all test methods
    test_methods = [m for m in dir(test_instance) if m.startswith('test_')]
    
    for method_name in test_methods:
        success, error = run_test_method(test_instance, method_name)
        if success:
            print(f"{GREEN}✓{RESET} {method_name}")
            passed += 1
        else:
            print(f"{RED}✗{RESET} {method_name}: {error}")
            failed += 1
    
    return passed, failed

def run_test_file(file_path):
    """Run all tests in a single test file"""
    print(f"\n{BOLD}{BLUE}Testing {file_path.name}{RESET}")
    print("=" * 80)
    
    # Import the test module
    module_name = file_path.stem
    spec = None
    
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
    except Exception as e:
        print(f"{RED}Failed to import {file_path.name}: {e}{RESET}")
        traceback.print_exc()
        return 0, 1
    
    total_passed = 0
    total_failed = 0
    
    # Find all test classes
    for item_name in dir(module):
        item = getattr(module, item_name)
        if isinstance(item, type) and item_name.startswith('Test'):
            passed, failed = run_test_class(item, item_name)
            total_passed += passed
            total_failed += failed
    
    return total_passed, total_failed

def main():
    """Run all tests"""
    print(f"{BOLD}Running All Tests{RESET}")
    print("=" * 80)
    
    # Find all test files
    test_dir = Path("tests")
    test_files = sorted(test_dir.glob("test_*.py"))
    
    if not test_files:
        print(f"{YELLOW}No test files found in {test_dir}{RESET}")
        return 1
    
    total_passed = 0
    total_failed = 0
    file_results = []
    
    for test_file in test_files:
        try:
            passed, failed = run_test_file(test_file)
            total_passed += passed
            total_failed += failed
            file_results.append((test_file.name, passed, failed))
        except Exception as e:
            print(f"{RED}Error running {test_file.name}: {e}{RESET}")
            traceback.print_exc()
            file_results.append((test_file.name, 0, 1))
            total_failed += 1
    
    # Print summary
    print(f"\n{BOLD}Test Summary{RESET}")
    print("=" * 80)
    
    for filename, passed, failed in file_results:
        status = f"{GREEN}PASSED{RESET}" if failed == 0 else f"{RED}FAILED{RESET}"
        print(f"{filename:<40} {passed:>4} passed, {failed:>4} failed  [{status}]")
    
    print("=" * 80)
    print(f"{BOLD}Total:{RESET} {total_passed} passed, {total_failed} failed")
    
    if total_failed == 0:
        print(f"\n{GREEN}{BOLD}All tests passed!{RESET}")
        return 0
    else:
        print(f"\n{RED}{BOLD}{total_failed} tests failed!{RESET}")
        return 1

if __name__ == "__main__":
    sys.exit(main())