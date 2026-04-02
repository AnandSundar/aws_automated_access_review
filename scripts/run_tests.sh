#!/bin/bash
# Script to run tests with pytest
# Supports coverage reporting, verbose output, and running specific test files

set -e  # Exit on error

# Default values
COVERAGE=false
VERBOSE=false
TEST_FILE=""
SHOW_HELP=false

# Display help message
show_help() {
    cat << EOF
Usage: ./scripts/run_tests.sh [options]

Run tests with pytest.

Options:
  --coverage       Generate coverage report
  --verbose        Verbose output
  --file <file>    Run specific test file
  --help           Display this help message

Examples:
  ./scripts/run_tests.sh                          # Run all tests
  ./scripts/run_tests.sh --coverage               # Run tests with coverage
  ./scripts/run_tests.sh --verbose                # Run tests with verbose output
  ./scripts/run_tests.sh --file tests/unit/test_handler.py  # Run specific file
  ./scripts/run_tests.sh --coverage --verbose     # Run tests with coverage and verbose output

EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --coverage)
            COVERAGE=true
            shift
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        --file)
            TEST_FILE="$2"
            shift 2
            ;;
        --help)
            SHOW_HELP=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Show help if requested
if [ "$SHOW_HELP" = true ]; then
    show_help
    exit 0
fi

# Build pytest command
PYTEST_CMD="pytest"

# Add verbose flag if specified
if [ "$VERBOSE" = true ]; then
    PYTEST_CMD="$PYTEST_CMD -v"
fi

# Add coverage if specified
if [ "$COVERAGE" = true ]; then
    PYTEST_CMD="$PYTEST_CMD --cov=src/lambda --cov=src/cli --cov=deployment --cov-report=term-missing --cov-report=html"
fi

# Add test file if specified
if [ -n "$TEST_FILE" ]; then
    if [ ! -f "$TEST_FILE" ]; then
        echo "Error: Test file not found: $TEST_FILE"
        exit 1
    fi
    PYTEST_CMD="$PYTEST_CMD $TEST_FILE"
else
    # Run all tests if no specific file is provided
    PYTEST_CMD="$PYTEST_CMD tests/"
fi

# Display test configuration
echo "========================================"
echo "Running Tests"
echo "========================================"
echo "Coverage: $COVERAGE"
echo "Verbose: $VERBOSE"
if [ -n "$TEST_FILE" ]; then
    echo "Test File: $TEST_FILE"
else
    echo "Test Scope: All tests"
fi
echo "========================================"
echo ""

# Run pytest
echo "Executing: $PYTEST_CMD"
echo ""

# Execute the command and capture exit code
if eval $PYTEST_CMD; then
    EXIT_CODE=0
else
    EXIT_CODE=$?
fi

echo ""
echo "========================================"
echo "Test Results Summary"
echo "========================================"
if [ $EXIT_CODE -eq 0 ]; then
    echo "✓ All tests passed successfully!"
else
    echo "✗ Tests failed with exit code: $EXIT_CODE"
fi
echo "========================================"

# Exit with the appropriate status code
exit $EXIT_CODE
