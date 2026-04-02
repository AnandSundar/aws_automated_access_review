# Testing Guide

## Overview

This guide covers testing the AWS Automated Access Review tool, including how to run tests, test structure overview, writing new tests, test coverage, and CI/CD integration.

## Test Structure

The project uses a comprehensive testing strategy with multiple test types:

```
tests/
├── __init__.py
├── unit/                 # Unit tests for individual modules
│   ├── __init__.py
│   ├── test_handler.py
│   ├── test_iam_findings.py
│   ├── test_securityhub_findings.py
│   ├── test_access_analyzer_findings.py
│   ├── test_cloudtrail_findings.py
│   ├── test_scp_findings.py
│   ├── test_narrative.py
│   ├── test_reporting.py
│   ├── test_email_utils.py
│   └── test_bedrock_integration.py
├── integration/          # Integration tests for end-to-end workflows
│   ├── __init__.py
│   └── test_end_to_end.py
└── style/                # Code style and linting tests
    ├── __init__.py
    └── test_code_style.py
```

### Test Types

#### Unit Tests
Test individual functions and modules in isolation.

**Location**: [`tests/unit/`](../tests/unit/)

**Purpose**: 
- Verify individual module functionality
- Test error handling
- Validate data transformations
- Mock AWS service calls

**Examples**:
- [`test_handler.py`](../tests/unit/test_handler.py:1) - Tests Lambda handler logic
- [`test_iam_findings.py`](../tests/unit/test_iam_findings.py:1) - Tests IAM findings collection
- [`test_reporting.py`](../tests/unit/test_reporting.py:1) - Tests report generation

#### Integration Tests
Test the complete workflow from start to finish.

**Location**: [`tests/integration/`](../tests/integration/)

**Purpose**:
- Verify end-to-end functionality
- Test module interactions
- Validate data flow
- Test with real AWS services (optional)

**Examples**:
- [`test_end_to_end.py`](../tests/integration/test_end_to_end.py:1) - Tests complete access review workflow

#### Style Tests
Verify code quality and adherence to standards.

**Location**: [`tests/style/`](../tests/style/)

**Purpose**:
- Enforce code style guidelines
- Check for linting issues
- Validate code formatting
- Ensure best practices

**Examples**:
- [`test_code_style.py`](../tests/style/test_code_style.py:1) - Tests code style compliance

## Running Tests

### Prerequisites

```bash
# Install test dependencies
pip install -r requirements-test.txt

# Install project dependencies
pip install -r requirements.txt

# Verify pytest installation
pytest --version
# Expected output: pytest 7.x.x
```

### Run All Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run with detailed output
pytest -vv
```

### Run Specific Test Files

```bash
# Run specific test file
pytest tests/unit/test_iam_findings.py

# Run multiple test files
pytest tests/unit/test_iam_findings.py tests/unit/test_reporting.py

# Run all unit tests
pytest tests/unit/

# Run all integration tests
pytest tests/integration/

# Run all style tests
pytest tests/style/
```

### Run Specific Test Functions

```bash
# Run specific test function
pytest tests/unit/test_iam_findings.py::test_get_iam_findings_success

# Run tests matching pattern
pytest -k "test_get_iam_findings"

# Run tests excluding pattern
pytest -k "not test_get_iam_findings"
```

### Run Tests with Coverage

```bash
# Run tests with coverage report
pytest --cov=src/lambda --cov=src/cli

# Generate HTML coverage report
pytest --cov=src/lambda --cov=src/cli --cov-report=html

# Generate XML coverage report (for CI/CD)
pytest --cov=src/lambda --cov=src/cli --cov-report=xml

# Show coverage in terminal
pytest --cov=src/lambda --cov=src/cli --cov-report=term-missing
```

**View HTML Coverage Report:**

```bash
# Open the HTML report
open htmlcov/index.html  # Mac
start htmlcov/index.html  # Windows
xdg-open htmlcov/index.html  # Linux
```

### Run Tests with Markers

Tests can be marked with custom markers for selective execution.

```bash
# Run tests marked as 'unit'
pytest -m unit

# Run tests marked as 'integration'
pytest -m integration

# Run tests marked as 'slow'
pytest -m slow

# Run tests not marked as 'slow'
pytest -m "not slow"
```

### Run Tests in Parallel

```bash
# Install pytest-xdist
pip install pytest-xdist

# Run tests in parallel (using all CPUs)
pytest -n auto

# Run tests with specific number of workers
pytest -n 4
```

### Run Tests with Debugging

```bash
# Drop into debugger on failure
pytest --pdb

# Drop into debugger on first failure
pytest --pdb -x

# Show local variables on failure
pytest -l

# Show print statements
pytest -s
```

## Test Configuration

### pytest.ini

The project uses [`pytest.ini`](../pytest.ini:1) for test configuration:

```ini
[pytest]
# Test discovery patterns
python_files = test_*.py
python_classes = Test*
python_functions = test_*

# Test paths
testpaths = tests

# Coverage configuration
addopts = 
    --verbose
    --strict-markers
    --tb=short
    --disable-warnings

# Markers
markers =
    unit: Unit tests
    integration: Integration tests
    slow: Slow running tests
    aws: Tests requiring AWS credentials
```

### Environment Variables

Tests use environment variables for configuration:

```bash
# Set environment variables for testing
export AWS_REGION=us-east-1
export AWS_ACCESS_KEY_ID=your-access-key
export AWS_SECRET_ACCESS_KEY=your-secret-key
export DRY_RUN=true

# Run tests with environment variables
AWS_REGION=us-east-1 pytest
```

### Test Fixtures

Tests use pytest fixtures for setup and teardown.

**Common Fixtures:**

```python
# In tests/conftest.py
import pytest
import boto3
from moto import mock_aws

@pytest.fixture
def mock_aws_credentials():
    """Mock AWS credentials for testing."""
    import os
    os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
    os.environ['AWS_SECURITY_TOKEN'] = 'testing'
    os.environ['AWS_SESSION_TOKEN'] = 'testing'
    os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'

@pytest.fixture
def mock_iam_client(mock_aws_credentials):
    """Mock IAM client for testing."""
    with mock_aws():
        yield boto3.client('iam', region_name='us-east-1')

@pytest.fixture
def sample_findings():
    """Sample findings for testing."""
    return [
        {
            'source': 'IAM',
            'resource_id': 'user@example.com',
            'resource_type': 'User',
            'finding_type': 'MFA Missing',
            'severity': 'CRITICAL',
            'description': 'User missing MFA enrollment',
            'recommendation': 'Enable MFA immediately',
            'evidence': {'user': 'user@example.com'}
        }
    ]
```

## Writing New Tests

### Test Structure

Follow this structure for new tests:

```python
import pytest
from unittest.mock import Mock, patch, MagicMock
from modules.iam_findings import get_iam_findings

class TestIAMFindings:
    """Test IAM findings module."""
    
    @pytest.fixture
    def mock_iam_client(self):
        """Mock IAM client."""
        with patch('boto3.client') as mock:
            client = Mock()
            mock.return_value = client
            yield client
    
    def test_get_iam_findings_success(self, mock_iam_client):
        """Test successful IAM findings collection."""
        # Arrange
        mock_iam_client.list_users.return_value = {
            'Users': [
                {'UserName': 'user1', 'UserId': 'user-id-1'},
                {'UserName': 'user2', 'UserId': 'user-id-2'}
            ]
        }
        mock_iam_client.list_mfa_devices.return_value = {
            'MFADevices': []
        }
        
        # Act
        findings = get_iam_findings()
        
        # Assert
        assert len(findings) == 2
        assert all(f['source'] == 'IAM' for f in findings)
        assert all(f['severity'] in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'] for f in findings)
    
    def test_get_iam_findings_no_users(self, mock_iam_client):
        """Test IAM findings with no users."""
        # Arrange
        mock_iam_client.list_users.return_value = {'Users': []}
        
        # Act
        findings = get_iam_findings()
        
        # Assert
        assert len(findings) == 0
    
    def test_get_iam_findings_error(self, mock_iam_client):
        """Test IAM findings with API error."""
        # Arrange
        mock_iam_client.list_users.side_effect = Exception('API Error')
        
        # Act & Assert
        with pytest.raises(Exception):
            get_iam_findings()
```

### Best Practices

1. **Use Descriptive Names**
   ```python
   # Good
   def test_get_iam_findings_returns_critical_for_missing_mfa(self):
       pass
   
   # Bad
   def test_1(self):
       pass
   ```

2. **Follow Arrange-Act-Assert Pattern**
   ```python
   def test_example(self):
       # Arrange - Set up test data
       data = {'key': 'value'}
       
       # Act - Execute the code being tested
       result = process_data(data)
       
       # Assert - Verify the result
       assert result == expected
   ```

3. **Use Fixtures for Common Setup**
   ```python
   @pytest.fixture
   def sample_data(self):
       return {'key': 'value'}
   
   def test_with_fixture(self, sample_data):
       assert sample_data['key'] == 'value'
   ```

4. **Mock External Dependencies**
   ```python
   @patch('boto3.client')
   def test_with_mock(self, mock_client):
       # Configure mock
       mock_client.return_value.list_users.return_value = {'Users': []}
       
       # Test code that uses boto3.client
       result = get_iam_findings()
       
       # Assert
       assert len(result) == 0
   ```

5. **Test Edge Cases**
   ```python
   def test_empty_list(self):
       assert process_list([]) == []
   
   def test_single_item(self):
       assert process_list([1]) == [1]
   
   def test_large_list(self):
       assert len(process_list(list(range(1000)))) == 1000
   ```

6. **Use Parametrized Tests**
   ```python
   @pytest.mark.parametrize("input,expected", [
       (1, 2),
       (2, 4),
       (3, 6),
   ])
   def test_multiply_by_two(self, input, expected):
       assert multiply_by_two(input) == expected
   ```

7. **Test Error Handling**
   ```python
   def test_invalid_input_raises_error(self):
       with pytest.raises(ValueError):
           process_data(None)
   
   def test_api_error_handling(self, mock_client):
       mock_client.list_users.side_effect = Exception('API Error')
       result = get_iam_findings()
       assert result == []  # Should handle error gracefully
   ```

### Test Examples

#### Example 1: Unit Test for Finding Module

```python
# tests/unit/test_iam_findings.py
import pytest
from unittest.mock import Mock, patch
from modules.iam_findings import get_iam_findings

@pytest.mark.unit
class TestIAMFindings:
    """Test IAM findings collection."""
    
    @pytest.fixture
    def mock_boto3_client(self):
        """Mock boto3 client."""
        with patch('modules.iam_findings.boto3.client') as mock:
            yield mock
    
    def test_get_iam_findings_returns_findings(self, mock_boto3_client):
        """Test that get_iam_findings returns findings."""
        # Arrange
        mock_client = Mock()
        mock_boto3_client.return_value = mock_client
        
        mock_client.list_users.return_value = {
            'Users': [
                {'UserName': 'test-user', 'UserId': 'user-id-123'}
            ]
        }
        mock_client.list_mfa_devices.return_value = {'MFADevices': []}
        mock_client.list_access_keys.return_value = {
            'AccessKeyMetadata': []
        }
        
        # Act
        findings = get_iam_findings()
        
        # Assert
        assert len(findings) > 0
        assert all('source' in f for f in findings)
        assert all('severity' in f for f in findings)
    
    def test_get_iam_findings_handles_empty_users(self, mock_boto3_client):
        """Test handling of empty user list."""
        # Arrange
        mock_client = Mock()
        mock_boto3_client.return_value = mock_client
        mock_client.list_users.return_value = {'Users': []}
        
        # Act
        findings = get_iam_findings()
        
        # Assert
        assert len(findings) == 0
```

#### Example 2: Integration Test

```python
# tests/integration/test_end_to_end.py
import pytest
from datetime import datetime
from index import lambda_handler

@pytest.mark.integration
class TestEndToEnd:
    """Test end-to-end access review workflow."""
    
    @pytest.mark.aws
    def test_full_workflow_dry_run(self):
        """Test complete workflow in dry-run mode."""
        # Arrange
        event = {
            'dry_run': True,
            'format': 'csv'
        }
        context = Mock()
        context.request_id = 'test-request-id'
        
        # Act
        result = lambda_handler(event, context)
        
        # Assert
        assert result['statusCode'] == 200
        assert result['body']['mode'] == 'DRY_RUN'
        assert 'finding_counts' in result['body']
        assert 'report_path' in result['body']
    
    @pytest.mark.aws
    def test_full_workflow_with_format(self):
        """Test workflow with different formats."""
        # Arrange
        event = {
            'dry_run': True,
            'format': 'xlsx'
        }
        context = Mock()
        context.request_id = 'test-request-id'
        
        # Act
        result = lambda_handler(event, context)
        
        # Assert
        assert result['statusCode'] == 200
        assert result['body']['report_path'].endswith('.xlsx')
```

#### Example 3: Style Test

```python
# tests/style/test_code_style.py
import pytest
import subprocess
import os

@pytest.mark.style
class TestCodeStyle:
    """Test code style compliance."""
    
    def test_flake8_compliance(self):
        """Test that code passes flake8 linting."""
        result = subprocess.run(
            ['flake8', 'src/lambda', 'src/cli'],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, f"Flake8 errors:\n{result.stdout}"
    
    def test_import_order(self):
        """Test that imports are properly ordered."""
        result = subprocess.run(
            ['isort', '--check-only', 'src/lambda', 'src/cli'],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, f"Import order errors:\n{result.stdout}"
    
    def test_no_print_statements(self):
        """Test that there are no print statements in production code."""
        # This is a simplified example
        # In practice, you might use a more sophisticated check
        for root, dirs, files in os.walk('src/lambda'):
            for file in files:
                if file.endswith('.py'):
                    filepath = os.path.join(root, file)
                    with open(filepath, 'r') as f:
                        content = f.read()
                        # Allow print in specific contexts
                        if 'print(' in content and 'lambda_handler' not in filepath:
                            # Check if it's in a test or debug context
                            if not any(x in content for x in ['# DEBUG', 'test_']):
                                pytest.fail(f"Print statement found in {filepath}")
```

## Test Coverage

### Current Coverage

The project aims for high test coverage across all modules:

| Module | Coverage Target | Current Coverage |
|--------|----------------|------------------|
| Lambda Handler | 90% | TBD |
| IAM Findings | 85% | TBD |
| SecurityHub Findings | 85% | TBD |
| Access Analyzer Findings | 85% | TBD |
| CloudTrail Findings | 85% | TBD |
| SCP Findings | 80% | TBD |
| Narrative Generation | 80% | TBD |
| Reporting | 90% | TBD |
| Email Utils | 85% | TBD |
| Bedrock Integration | 75% | TBD |

### Generating Coverage Reports

```bash
# Generate coverage report
pytest --cov=src/lambda --cov=src/cli --cov-report=html

# View coverage by module
pytest --cov=src/lambda --cov=src/cli --cov-report=term-missing

# Generate coverage badge
pytest --cov=src/lambda --cov=src/cli --cov-report=html --cov-report=term
```

### Improving Coverage

1. **Identify Uncovered Code**
   ```bash
   # Show missing lines
   pytest --cov=src/lambda --cov-report=term-missing
   ```

2. **Add Tests for Missing Lines**
   - Review the coverage report
   - Identify untested code paths
   - Write tests to cover those paths

3. **Focus on Critical Paths**
   - Error handling
   - Edge cases
   - Integration points

4. **Use Coverage Tools**
   ```bash
   # Interactive coverage report
   coverage html
   open htmlcov/index.html
   ```

## CI/CD Integration

### GitHub Actions

Create `.github/workflows/test.yml`:

```yaml
name: Tests

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  test:
    runs-on: ubuntu-latest
    
    strategy:
      matrix:
        python-version: [3.11]
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install -r requirements-test.txt
    
    - name: Run linting
      run: |
        flake8 src/ tests/
        isort --check-only src/ tests/
    
    - name: Run tests with coverage
      run: |
        pytest --cov=src/lambda --cov=src/cli --cov-report=xml --cov-report=term
    
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
        flags: unittests
        name: codecov-umbrella
    
    - name: Run integration tests
      if: github.event_name == 'push' && github.ref == 'refs/heads/main'
      env:
        AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
        AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
        AWS_REGION: us-east-1
      run: |
        pytest -m integration
```

### GitLab CI

Create `.gitlab-ci.yml`:

```yaml
stages:
  - test
  - coverage

test:
  stage: test
  image: python:3.11
  before_script:
    - pip install -r requirements.txt
    - pip install -r requirements-test.txt
  script:
    - flake8 src/ tests/
    - isort --check-only src/ tests/
    - pytest --cov=src/lambda --cov=src/cli --cov-report=xml
  coverage: '/TOTAL.*\s+(\d+%)$/'
  artifacts:
    reports:
      coverage_report:
        coverage_format: cobertura
        path: coverage.xml

integration:
  stage: test
  image: python:3.11
  before_script:
    - pip install -r requirements.txt
    - pip install -r requirements-test.txt
  script:
    - pytest -m integration
  only:
    - main
```

### Jenkins Pipeline

Create `Jenkinsfile`:

```groovy
pipeline {
    agent any
    
    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }
        
        stage('Install Dependencies') {
            steps {
                sh 'pip install -r requirements.txt'
                sh 'pip install -r requirements-test.txt'
            }
        }
        
        stage('Lint') {
            steps {
                sh 'flake8 src/ tests/'
                sh 'isort --check-only src/ tests/'
            }
        }
        
        stage('Unit Tests') {
            steps {
                sh 'pytest tests/unit/ --cov=src/lambda --cov=src/cli --cov-report=xml'
            }
        }
        
        stage('Integration Tests') {
            when {
                branch 'main'
            }
            steps {
                withCredentials([
                    string(credentialsId: 'aws-access-key-id', variable: 'AWS_ACCESS_KEY_ID'),
                    string(credentialsId: 'aws-secret-access-key', variable: 'AWS_SECRET_ACCESS_KEY')
                ]) {
                    sh 'pytest tests/integration/'
                }
            }
        }
        
        stage('Coverage Report') {
            steps {
                publishHTML(target: [
                    reportDir: 'htmlcov',
                    reportFiles: 'index.html',
                    reportName: 'Coverage Report'
                ])
            }
        }
    }
    
    post {
        always {
            junit 'test-results.xml'
        }
    }
}
```

## Testing Best Practices

### 1. Test Independence
Each test should be independent and not rely on other tests.

```python
# Good
def test_feature_a():
    assert feature_a() == expected

def test_feature_b():
    assert feature_b() == expected

# Bad
def test_feature_a_and_b():
    result_a = feature_a()
    result_b = feature_b(result_a)  # Depends on test order
    assert result_b == expected
```

### 2. Use Mocks for External Services
Never make real API calls in unit tests.

```python
# Good
@patch('boto3.client')
def test_with_mock(self, mock_client):
    mock_client.return_value.list_users.return_value = {'Users': []}
    result = get_iam_findings()
    assert len(result) == 0

# Bad
def test_with_real_api(self):
    result = get_iam_findings()  # Makes real API call
    assert len(result) >= 0
```

### 3. Test Both Success and Failure Cases
Don't just test the happy path.

```python
# Good
def test_success(self):
    assert process_data({'valid': True}) == 'success'

def test_failure(self):
    with pytest.raises(ValueError):
        process_data({'valid': False})

# Bad
def test_success_only(self):
    assert process_data({'valid': True}) == 'success'
```

### 4. Keep Tests Fast
Unit tests should run in seconds, not minutes.

```python
# Good - Uses mocks
@patch('boto3.client')
def test_fast(self, mock_client):
    # Runs in milliseconds
    pass

# Bad - Makes real API calls
def test_slow(self):
    # Runs in seconds or minutes
    pass
```

### 5. Use Descriptive Test Names
Test names should describe what they test.

```python
# Good
def test_get_iam_findings_returns_critical_for_users_without_mfa(self):
    pass

# Bad
def test_1(self):
    pass
```

### 6. Test Edge Cases
Don't forget to test edge cases.

```python
# Good
def test_empty_input(self):
    assert process_data([]) == []

def test_single_item(self):
    assert process_data([1]) == [1]

def test_large_input(self):
    assert process_data(list(range(10000))) == expected

# Bad
def test_normal_case_only(self):
    assert process_data([1, 2, 3]) == [1, 2, 3]
```

### 7. Use Fixtures for Common Setup
Avoid code duplication in tests.

```python
# Good
@pytest.fixture
def sample_data(self):
    return {'key': 'value'}

def test_with_fixture(self, sample_data):
    assert sample_data['key'] == 'value'

# Bad
def test_without_fixture(self):
    data = {'key': 'value'}
    assert data['key'] == 'value'

def test_without_fixture_2(self):
    data = {'key': 'value'}
    assert data['key'] == 'value'
```

## Troubleshooting Tests

### Issue: Tests Fail with Import Errors

**Symptoms**: `ModuleNotFoundError: No module named '...'`

**Solutions**:
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-test.txt
   ```

2. Check PYTHONPATH:
   ```bash
   export PYTHONPATH="${PYTHONPATH}:$(pwd)"
   ```

3. Run tests from project root:
   ```bash
   cd /path/to/project
   pytest
   ```

### Issue: Tests Fail with AWS Credential Errors

**Symptoms**: `botocore.exceptions.NoCredentialsError`

**Solutions**:
1. Use mocks for unit tests:
   ```python
   @patch('boto3.client')
   def test_with_mock(self, mock_client):
       pass
   ```

2. Set environment variables for integration tests:
   ```bash
   export AWS_ACCESS_KEY_ID=your-key
   export AWS_SECRET_ACCESS_KEY=your-secret
   pytest -m integration
   ```

3. Use dry-run mode:
   ```bash
   export DRY_RUN=true
   pytest
   ```

### Issue: Tests Are Slow

**Symptoms**: Tests take minutes to run

**Solutions**:
1. Use mocks instead of real API calls
2. Run tests in parallel:
   ```bash
   pytest -n auto
   ```
3. Skip slow tests:
   ```bash
   pytest -m "not slow"
   ```
4. Use pytest cache:
   ```bash
   pytest --cache-clear
   ```

### Issue: Coverage Report Shows 0%

**Symptoms**: Coverage report shows 0% coverage

**Solutions**:
1. Install pytest-cov:
   ```bash
   pip install pytest-cov
   ```

2. Run tests with coverage:
   ```bash
   pytest --cov=src/lambda --cov=src/cli
   ```

3. Check coverage configuration in `pytest.ini`

## Related Documentation
- [Deployment Guide](deployment.md)
- [Usage Guide](usage.md)
- [Troubleshooting](troubleshooting.md)
- [Architecture](architecture.md)
