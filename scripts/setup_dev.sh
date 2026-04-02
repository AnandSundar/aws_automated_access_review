#!/bin/bash
# Script to set up the development environment
# Checks Python version, creates virtual environment, and installs dependencies

set -e  # Exit on error

# Default values
VENV_NAME="venv"
SKIP_VENV=false
SHOW_HELP=false

# Display help message
show_help() {
    cat << EOF
Usage: ./scripts/setup_dev.sh [options]

Set up the development environment for the AWS Automated Access Review tool.

Options:
  --venv <name>    Specify virtual environment name (default: venv)
  --skip-venv      Skip virtual environment creation
  --help           Display this help message

Examples:
  ./scripts/setup_dev.sh                          # Set up with default venv
  ./scripts/setup_dev.sh --venv .venv             # Use custom venv name
  ./scripts/setup_dev.sh --skip-venv              # Skip venv creation

EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --venv)
            VENV_NAME="$2"
            shift 2
            ;;
        --skip-venv)
            SKIP_VENV=true
            shift
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

# Display setup configuration
echo "========================================"
echo "Development Environment Setup"
echo "========================================"
echo "Virtual Environment: $VENV_NAME"
echo "Skip VENV Creation: $SKIP_VENV"
echo "========================================"
echo ""

# Check Python version
echo "Checking Python version..."
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

echo "Found Python version: $PYTHON_VERSION"

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 11 ]); then
    echo "Error: Python 3.11 or higher is required"
    echo "Current version: $PYTHON_VERSION"
    exit 1
fi

echo "✓ Python version check passed (3.11+)"
echo ""

# Create virtual environment if not skipped
if [ "$SKIP_VENV" = false ]; then
    echo "Checking virtual environment..."
    if [ -d "$VENV_NAME" ]; then
        echo "Virtual environment already exists: $VENV_NAME"
    else
        echo "Creating virtual environment: $VENV_NAME"
        python3 -m venv "$VENV_NAME"
        echo "✓ Virtual environment created successfully"
    fi
    echo ""
    
    # Activate virtual environment
    echo "Activating virtual environment..."
    source "$VENV_NAME/bin/activate"
    echo "✓ Virtual environment activated"
    echo ""
else
    echo "Skipping virtual environment creation"
    echo ""
fi

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip
echo "✓ pip upgraded"
echo ""

# Install runtime dependencies
echo "Installing runtime dependencies from requirements.txt..."
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
    echo "✓ Runtime dependencies installed"
else
    echo "Warning: requirements.txt not found"
fi
echo ""

# Install test dependencies
echo "Installing test dependencies from requirements-test.txt..."
if [ -f "requirements-test.txt" ]; then
    pip install -r requirements-test.txt
    echo "✓ Test dependencies installed"
else
    echo "Warning: requirements-test.txt not found"
fi
echo ""

# Verify installation
echo "Verifying installation..."
echo ""

# Check if pytest is installed
if command -v pytest &> /dev/null; then
    PYTEST_VERSION=$(pytest --version | head -n 1)
    echo "✓ pytest is installed: $PYTEST_VERSION"
else
    echo "✗ pytest is not installed"
    exit 1
fi

# Check if boto3 is installed
if python3 -c "import boto3" 2>/dev/null; then
    BOTO3_VERSION=$(python3 -c "import boto3; print(boto3.__version__)")
    echo "✓ boto3 is installed: version $BOTO3_VERSION"
else
    echo "✗ boto3 is not installed"
    exit 1
fi

# Check if botocore is installed
if python3 -c "import botocore" 2>/dev/null; then
    BOTOCORE_VERSION=$(python3 -c "import botocore; print(botocore.__version__)")
    echo "✓ botocore is installed: version $BOTOCORE_VERSION"
else
    echo "✗ botocore is not installed"
    exit 1
fi

echo ""
echo "========================================"
echo "Setup Summary"
echo "========================================"
echo "✓ Python version: $PYTHON_VERSION"
if [ "$SKIP_VENV" = false ]; then
    echo "✓ Virtual environment: $VENV_NAME (activated)"
else
    echo "⊙ Virtual environment: skipped"
fi
echo "✓ Runtime dependencies: installed"
echo "✓ Test dependencies: installed"
echo "✓ pytest: installed"
echo "✓ boto3: installed"
echo "✓ botocore: installed"
echo "========================================"
echo ""
echo "Development environment is ready!"
echo ""
if [ "$SKIP_VENV" = false ]; then
    echo "To activate the virtual environment in the future, run:"
    echo "  source $VENV_NAME/bin/activate"
    echo ""
fi
echo "To run tests, execute:"
echo "  ./scripts/run_tests.sh"
echo ""
