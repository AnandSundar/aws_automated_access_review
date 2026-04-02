#!/usr/bin/env python3
"""
Script to run tests with pytest
Supports coverage reporting, verbose output, and running specific test files
"""

import sys
import subprocess
import argparse
from pathlib import Path


def show_help():
    """Display help message"""
    help_text = """
Usage: python scripts/run_tests.py [options]

Run tests with pytest.

Options:
  --coverage       Generate coverage report
  --verbose        Verbose output
  --file <file>    Run specific test file
  --help           Display this help message

Examples:
  python scripts/run_tests.py                          # Run all tests
  python scripts/run_tests.py --coverage               # Run tests with coverage
  python scripts/run_tests.py --verbose                # Run tests with verbose output
  python scripts/run_tests.py --file tests/unit/test_handler.py  # Run specific file
  python scripts/run_tests.py --coverage --verbose     # Run tests with coverage and verbose output
"""
    print(help_text)


def main():
    """Main function to run tests"""
    parser = argparse.ArgumentParser(description="Run tests with pytest", add_help=False)
    parser.add_argument("--coverage", action="store_true", help="Generate coverage report")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    parser.add_argument("--file", type=str, help="Run specific test file")
    parser.add_argument("--help", action="store_true", help="Display this help message")

    args = parser.parse_args()

    # Show help if requested
    if args.help:
        show_help()
        return 0

    # Build pytest command
    pytest_cmd = [sys.executable, "-m", "pytest"]

    # Add verbose flag if specified
    if args.verbose:
        pytest_cmd.append("-v")

    # Add coverage if specified
    if args.coverage:
        pytest_cmd.extend(
            [
                "--cov=src/lambda",
                "--cov=src/cli",
                "--cov=deployment",
                "--cov-report=term-missing",
                "--cov-report=html",
            ]
        )

    # Add test file if specified
    if args.file:
        test_file = Path(args.file)
        if not test_file.exists():
            print(f"Error: Test file not found: {args.file}")
            return 1
        pytest_cmd.append(args.file)
    else:
        # Run all tests if no specific file is provided
        pytest_cmd.append("tests/")

    # Display test configuration
    print("=" * 40)
    print("Running Tests")
    print("=" * 40)
    print(f"Coverage: {args.coverage}")
    print(f"Verbose: {args.verbose}")
    if args.file:
        print(f"Test File: {args.file}")
    else:
        print("Test Scope: All tests")
    print("=" * 40)
    print()

    # Run pytest
    print(f"Executing: {' '.join(pytest_cmd)}")
    print()

    # Execute the command and capture exit code
    try:
        result = subprocess.run(pytest_cmd, check=False)
        exit_code = result.returncode
    except Exception as e:
        print(f"Error running pytest: {e}")
        exit_code = 1

    print()
    print("=" * 40)
    print("Test Results Summary")
    print("=" * 40)
    if exit_code == 0:
        print("[PASS] All tests passed successfully!")
    else:
        print(f"[FAIL] Tests failed with exit code: {exit_code}")
    print("=" * 40)

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
