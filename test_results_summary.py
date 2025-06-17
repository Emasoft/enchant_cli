#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script to generate a nicely formatted test results table
"""

import subprocess
import re
import sys


def get_test_results():
    """Run pytest and collect test results"""
    print("Running tests and collecting results...")
    
    cmd = ["uv", "run", "pytest", "-v", "--tb=no", "--no-header"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    tests = []
    for line in result.stdout.splitlines():
        # Match test result lines
        match = re.match(r'(tests/.*?)::(.*?)::(.*?)\s+(PASSED|FAILED|SKIPPED|ERROR)', line)
        if match:
            file_path, class_name, test_name, status = match.groups()
            tests.append({
                'file': file_path.split('/')[-1],
                'class': class_name,
                'test': test_name,
                'status': status
            })
    
    return tests


def get_test_description(file_path, class_name, test_name):
    """Extract test description from docstring"""
    try:
        # Read the test file and find the test method
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Look for the test method and its docstring
        pattern = rf'def {test_name}\(.*?\):\s*"""(.*?)"""'
        match = re.search(pattern, content, re.DOTALL)
        if match:
            docstring = match.group(1).strip()
            # Get first line of docstring
            first_line = docstring.split('\n')[0].strip()
            return first_line if first_line else test_name
    except:
        pass
    
    # Fallback: convert test name to readable format
    return test_name.replace('test_', '').replace('_', ' ').title()


def print_results_table(tests):
    """Print results in a nicely formatted table"""
    # Group by status
    passed = [t for t in tests if t['status'] == 'PASSED']
    failed = [t for t in tests if t['status'] == 'FAILED']
    skipped = [t for t in tests if t['status'] == 'SKIPPED']
    errors = [t for t in tests if t['status'] == 'ERROR']
    
    # Print summary
    total = len(tests)
    print(f"\n{'='*80}")
    print(f"TEST RESULTS SUMMARY")
    print(f"{'='*80}")
    print(f"Total Tests: {total}")
    print(f"✅ Passed: {len(passed)} ({len(passed)/total*100:.1f}%)")
    print(f"❌ Failed: {len(failed)} ({len(failed)/total*100:.1f}%)")
    print(f"⏭️  Skipped: {len(skipped)} ({len(skipped)/total*100:.1f}%)")
    print(f"🔥 Errors: {len(errors)} ({len(errors)/total*100:.1f}%)")
    print(f"{'='*80}\n")
    
    # Define table structure
    print("╔" + "═"*50 + "╦" + "═"*60 + "╦" + "═"*10 + "╗")
    print("║" + " Test Function".ljust(50) + "║" + " Description".ljust(60) + "║" + " Status".ljust(10) + "║")
    print("╠" + "═"*50 + "╬" + "═"*60 + "╬" + "═"*10 + "╣")
    
    # Print failed tests first (most important)
    if failed:
        for test in failed[:20]:  # Show first 20 failed tests
            test_name = f"{test['class']}::{test['test']}"[:48]
            desc = get_test_description(f"tests/{test['file']}", test['class'], test['test'])[:58]
            status = "❌ FAIL"
            print(f"║ {test_name:<48} ║ {desc:<58} ║ {status:<8} ║")
        
        if len(failed) > 20:
            print(f"║ {'... and ' + str(len(failed) - 20) + ' more failed tests':<48} ║ {'':<58} ║ {'':<8} ║")
    
    # Show some passed tests
    if passed:
        print("╠" + "═"*50 + "╬" + "═"*60 + "╬" + "═"*10 + "╣")
        for test in passed[:10]:  # Show first 10 passed tests
            test_name = f"{test['class']}::{test['test']}"[:48]
            desc = get_test_description(f"tests/{test['file']}", test['class'], test['test'])[:58]
            status = "✅ PASS"
            print(f"║ {test_name:<48} ║ {desc:<58} ║ {status:<8} ║")
        
        if len(passed) > 10:
            print(f"║ {'... and ' + str(len(passed) - 10) + ' more passing tests':<48} ║ {'':<58} ║ {'':<8} ║")
    
    print("╚" + "═"*50 + "╩" + "═"*60 + "╩" + "═"*10 + "╝")
    
    # Print specific test categories
    print("\n🐌 Slow Tests (typically skipped on CI):")
    slow_tests = [
        "test_real_translation_local",
        "test_real_wuxia_translation", 
        "test_real_name_translation",
        "test_epub_toc_matches_expected_chapters"
    ]
    
    for test in tests:
        if any(slow in test['test'] for slow in slow_tests):
            print(f"  - {test['class']}::{test['test']} ({test['status']})")


if __name__ == "__main__":
    tests = get_test_results()
    print_results_table(tests)