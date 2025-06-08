#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test runner script for ENCHANT_BOOK_MANAGER

Usage:
    python tests/run_tests.py              # Run all tests with coverage
    python tests/run_tests.py --quick      # Run only fast tests
    python tests/run_tests.py --module translation_service  # Test specific module
    python tests/run_tests.py --html       # Generate HTML coverage report
"""

import sys
import os
import argparse
import subprocess
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def run_tests(args):
    """Run pytest with appropriate arguments"""
    # Base pytest command
    cmd = [sys.executable, "-m", "pytest"]
    
    # Add test directory
    test_dir = Path(__file__).parent
    cmd.append(str(test_dir))
    
    # Verbosity
    if args.verbose:
        cmd.append("-vv")
    else:
        cmd.append("-v")
    
    # Coverage options
    if not args.no_coverage:
        cmd.extend(["--cov=..", "--cov-report=term-missing"])
        
        if args.html:
            cmd.append("--cov-report=html")
            print("HTML coverage report will be generated in htmlcov/")
    
    # Module-specific testing
    if args.module:
        cmd.extend([
            f"--cov={args.module}",
            f"test_{args.module}.py"
        ])
    
    # Quick mode - skip slow tests
    if args.quick:
        cmd.extend(["-m", "not slow"])
    
    # Parallel execution
    if args.parallel:
        try:
            import pytest_xdist
            cmd.extend(["-n", "auto"])
        except ImportError:
            print("Warning: pytest-xdist not installed, running tests sequentially")
    
    # Show local variables in tracebacks
    if args.locals:
        cmd.append("--showlocals")
    
    # Stop on first failure
    if args.failfast:
        cmd.append("-x")
    
    # Run last failed tests
    if args.lf:
        cmd.append("--lf")
    
    # Additional pytest arguments
    if args.pytest_args:
        cmd.extend(args.pytest_args)
    
    # Print command
    print(f"Running: {' '.join(cmd)}")
    print("-" * 80)
    
    # Run tests
    result = subprocess.run(cmd, cwd=test_dir.parent)
    
    return result.returncode


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Run tests for ENCHANT_BOOK_MANAGER",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                    # Run all tests with coverage
  %(prog)s --quick           # Skip slow tests  
  %(prog)s --module translation_service  # Test specific module
  %(prog)s --html            # Generate HTML coverage report
  %(prog)s -xvs              # Stop on first failure with verbose output
  %(prog)s --lf              # Run last failed tests
  %(prog)s -- -k "test_cost" # Run tests matching pattern
"""
    )
    
    parser.add_argument(
        "--quick", "-q",
        action="store_true",
        help="Run only fast tests (skip slow/integration tests)"
    )
    
    parser.add_argument(
        "--module", "-m",
        help="Test specific module only"
    )
    
    parser.add_argument(
        "--html",
        action="store_true",
        help="Generate HTML coverage report"
    )
    
    parser.add_argument(
        "--no-coverage",
        action="store_true",
        help="Disable coverage reporting"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Increase verbosity"
    )
    
    parser.add_argument(
        "--parallel", "-p",
        action="store_true",
        help="Run tests in parallel (requires pytest-xdist)"
    )
    
    parser.add_argument(
        "--locals", "-l",
        action="store_true",
        help="Show local variables in tracebacks"
    )
    
    parser.add_argument(
        "--failfast", "-x",
        action="store_true",
        help="Stop on first test failure"
    )
    
    parser.add_argument(
        "--lf", "--last-failed",
        action="store_true",
        help="Run only tests that failed last time"
    )
    
    parser.add_argument(
        "pytest_args",
        nargs=argparse.REMAINDER,
        help="Additional arguments to pass to pytest"
    )
    
    args = parser.parse_args()
    
    # Check if pytest is installed
    try:
        import pytest
    except ImportError:
        print("Error: pytest not installed. Run: pip install pytest pytest-cov")
        sys.exit(1)
    
    # Run tests
    exit_code = run_tests(args)
    
    # Print summary
    print("-" * 80)
    if exit_code == 0:
        print("✅ All tests passed!")
    else:
        print("❌ Some tests failed!")
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()