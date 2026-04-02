"""
Unit tests for CloudTrail findings module.

Tests the get_cloudtrail_findings function in src/lambda/modules/cloudtrail_findings.py
"""

import pytest
from unittest.mock import Mock, patch
from botocore.exceptions import ClientError

# Add the src/lambda directory to the path so we can import the modules
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src/lambda"))

from modules.cloudtrail_findings import get_cloudtrail_findings


@pytest.fixture
def mock_cloudtrail_client():
    """Create a mock CloudTrail client."""
    client = Mock()
    return client


@pytest.fixture
def mock_s3_client():
    """Create a mock S3 client."""
    client = Mock()
    return client


@pytest.fixture
def sample_trail_configured():
    """Provide a sample well-configured CloudTrail trail."""
    return {
        "Name": "my-trail",
        "S3BucketName": "my-cloudtrail-bucket",
        "IncludeGlobalServiceEvents": True,
        "IsMultiRegionTrail": True,
        "HomeRegion": "us-east-1",
        "TrailARN": "arn:aws:cloudtrail:us-east-1:123456789012:trail/my-trail",
        "LogFileValidationEnabled": True,
        "CloudWatchLogsLogGroupArn": "arn:aws:logs:us-east-1:123456789012:log-group:CloudTrail/APIActivity",
        "CloudWatchLogsRoleArn": "arn:aws:iam::123456789012:role/CloudTrailLogsRole",
        "HasCustomEventSelectors": False,
        "HasInsightSelectors": False,
        "IsOrganizationTrail": False,
    }


@pytest.fixture
def sample_trail_not_multiregion():
    """Provide a sample trail that is not multi-region."""
    return {
        "Name": "single-region-trail",
        "S3BucketName": "my-cloudtrail-bucket",
        "IncludeGlobalServiceEvents": True,
        "IsMultiRegionTrail": False,
        "HomeRegion": "us-east-1",
        "TrailARN": "arn:aws:cloudtrail:us-east-1:123456789012:trail/single-region-trail",
        "LogFileValidationEnabled": True,
        "CloudWatchLogsLogGroupArn": "arn:aws:logs:us-east-1:123456789012:log-group:CloudTrail/APIActivity",
        "CloudWatchLogsRoleArn": "arn:aws:iam::123456789012:role/CloudTrailLogsRole",
        "HasCustomEventSelectors": False,
        "HasInsightSelectors": False,
        "IsOrganizationTrail": False,
    }


@pytest.fixture
def sample_trail_no_validation():
    """Provide a sample trail without log file validation."""
    return {
        "Name": "no-validation-trail",
        "S3BucketName": "my-cloudtrail-bucket",
        "IncludeGlobalServiceEvents": True,
        "IsMultiRegionTrail": True,
        "HomeRegion": "us-east-1",
        "TrailARN": "arn:aws:cloudtrail:us-east-1:123456789012:trail/no-validation-trail",
        "LogFileValidationEnabled": False,
        "CloudWatchLogsLogGroupArn": "arn:aws:logs:us-east-1:123456789012:log-group:CloudTrail/APIActivity",
        "CloudWatchLogsRoleArn": "arn:aws:iam::123456789012:role/CloudTrailLogsRole",
        "HasCustomEventSelectors": False,
        "HasInsightSelectors": False,
        "IsOrganizationTrail": False,
    }


@pytest.fixture
def sample_trail_no_cloudwatch():
    """Provide a sample trail without CloudWatch Logs integration."""
    return {
        "Name": "no-cloudwatch-trail",
        "S3BucketName": "my-cloudtrail-bucket",
        "IncludeGlobalServiceEvents": True,
        "IsMultiRegionTrail": True,
        "HomeRegion": "us-east-1",
        "TrailARN": "arn:aws:cloudtrail:us-east-1:123456789012:trail/no-cloudwatch-trail",
        "LogFileValidationEnabled": True,
        "HasCustomEventSelectors": False,
        "HasInsightSelectors": False,
        "IsOrganizationTrail": False,
    }


@pytest.fixture
def sample_trail_bucket_no_logging():
    """Provide a sample trail with bucket that has no access logging."""
    return {
        "Name": "no-bucket-logging-trail",
        "S3BucketName": "my-cloudtrail-bucket",
        "IncludeGlobalServiceEvents": True,
        "IsMultiRegionTrail": True,
        "HomeRegion": "us-east-1",
        "TrailARN": "arn:aws:cloudtrail:us-east-1:123456789012:trail/no-bucket-logging-trail",
        "LogFileValidationEnabled": True,
        "CloudWatchLogsLogGroupArn": "arn:aws:logs:us-east-1:123456789012:log-group:CloudTrail/APIActivity",
        "CloudWatchLogsRoleArn": "arn:aws:iam::123456789012:role/CloudTrailLogsRole",
        "HasCustomEventSelectors": False,
        "HasInsightSelectors": False,
        "IsOrganizationTrail": False,
    }


class TestGetCloudTrailFindingsSuccess:
    """Test cases for successful CloudTrail findings retrieval."""

    @patch("modules.cloudtrail_findings.boto3.client")
    def test_well_configured_trail(self, mock_boto3_client, sample_trail_configured):
        """Test that a well-configured trail generates no findings."""
        mock_ct = Mock()
        mock_ct.describe_trails.return_value = {"trailList": [sample_trail_configured]}

        mock_s3 = Mock()
        mock_s3.get_bucket_logging.return_value = {
            "LoggingEnabled": {
                "TargetBucket": "logging-bucket",
                "TargetPrefix": "cloudtrail-logs/",
            }
        }

        def client_side_effect(service, **kwargs):
            if service == "cloudtrail":
                return mock_ct
            elif service == "s3":
                return mock_s3
            return Mock()

        mock_boto3_client.side_effect = client_side_effect

        findings = get_cloudtrail_findings()

        # Well-configured trail should generate no findings
        assert len(findings) == 0

    @patch("modules.cloudtrail_findings.boto3.client")
    def test_not_multiregion_trail(
        self, mock_boto3_client, sample_trail_not_multiregion
    ):
        """Test detection of non-multi-region trails."""
        mock_ct = Mock()
        mock_ct.describe_trails.return_value = {
            "trailList": [sample_trail_not_multiregion]
        }

        mock_s3 = Mock()
        mock_s3.get_bucket_logging.return_value = {
            "LoggingEnabled": {
                "TargetBucket": "logging-bucket",
                "TargetPrefix": "cloudtrail-logs/",
            }
        }

        def client_side_effect(service, **kwargs):
            if service == "cloudtrail":
                return mock_ct
            elif service == "s3":
                return mock_s3
            return Mock()

        mock_boto3_client.side_effect = client_side_effect

        findings = get_cloudtrail_findings()

        assert len(findings) == 1
        assert findings[0]["resource_id"] == "single-region-trail"
        assert findings[0]["resource_type"] == "CLOUDTRAIL_TRAIL"
        assert findings[0]["service"] == "CloudTrail"
        assert findings[0]["severity"] == "HIGH"
        assert "not multi-region" in findings[0]["finding"]

    @patch("modules.cloudtrail_findings.boto3.client")
    def test_no_log_file_validation(
        self, mock_boto3_client, sample_trail_no_validation
    ):
        """Test detection of trails without log file validation."""
        mock_ct = Mock()
        mock_ct.describe_trails.return_value = {
            "trailList": [sample_trail_no_validation]
        }

        mock_s3 = Mock()
        mock_s3.get_bucket_logging.return_value = {
            "LoggingEnabled": {
                "TargetBucket": "logging-bucket",
                "TargetPrefix": "cloudtrail-logs/",
            }
        }

        def client_side_effect(service, **kwargs):
            if service == "cloudtrail":
                return mock_ct
            elif service == "s3":
                return mock_s3
            return Mock()

        mock_boto3_client.side_effect = client_side_effect

        findings = get_cloudtrail_findings()

        assert len(findings) == 1
        assert findings[0]["resource_id"] == "no-validation-trail"
        assert findings[0]["severity"] == "HIGH"
        assert "Log file validation is disabled" in findings[0]["finding"]

    @patch("modules.cloudtrail_findings.boto3.client")
    def test_no_cloudwatch_integration(
        self, mock_boto3_client, sample_trail_no_cloudwatch
    ):
        """Test detection of trails without CloudWatch Logs integration."""
        mock_ct = Mock()
        mock_ct.describe_trails.return_value = {
            "trailList": [sample_trail_no_cloudwatch]
        }

        mock_s3 = Mock()
        mock_s3.get_bucket_logging.return_value = {
            "LoggingEnabled": {
                "TargetBucket": "logging-bucket",
                "TargetPrefix": "cloudtrail-logs/",
            }
        }

        def client_side_effect(service, **kwargs):
            if service == "cloudtrail":
                return mock_ct
            elif service == "s3":
                return mock_s3
            return Mock()

        mock_boto3_client.side_effect = client_side_effect

        findings = get_cloudtrail_findings()

        assert len(findings) == 1
        assert findings[0]["resource_id"] == "no-cloudwatch-trail"
        assert findings[0]["severity"] == "MEDIUM"
        assert "CloudWatch Logs integration is missing" in findings[0]["finding"]

    @patch("modules.cloudtrail_findings.boto3.client")
    def test_no_bucket_access_logging(
        self, mock_boto3_client, sample_trail_bucket_no_logging
    ):
        """Test detection of S3 buckets without access logging."""
        mock_ct = Mock()
        mock_ct.describe_trails.return_value = {
            "trailList": [sample_trail_bucket_no_logging]
        }

        mock_s3 = Mock()
        mock_s3.get_bucket_logging.return_value = {}  # No LoggingEnabled

        def client_side_effect(service, **kwargs):
            if service == "cloudtrail":
                return mock_ct
            elif service == "s3":
                return mock_s3
            return Mock()

        mock_boto3_client.side_effect = client_side_effect

        findings = get_cloudtrail_findings()

        assert len(findings) == 1
        assert findings[0]["resource_id"] == "my-cloudtrail-bucket"
        assert findings[0]["resource_type"] == "S3_BUCKET"
        assert findings[0]["service"] == "S3"
        assert findings[0]["severity"] == "MEDIUM"
        assert "Access logging is disabled" in findings[0]["finding"]

    @patch("modules.cloudtrail_findings.boto3.client")
    def test_multiple_trails(
        self, mock_boto3_client, sample_trail_configured, sample_trail_not_multiregion
    ):
        """Test handling of multiple trails."""
        mock_ct = Mock()
        mock_ct.describe_trails.return_value = {
            "trailList": [sample_trail_configured, sample_trail_not_multiregion]
        }

        mock_s3 = Mock()
        mock_s3.get_bucket_logging.return_value = {
            "LoggingEnabled": {
                "TargetBucket": "logging-bucket",
                "TargetPrefix": "cloudtrail-logs/",
            }
        }

        def client_side_effect(service, **kwargs):
            if service == "cloudtrail":
                return mock_ct
            elif service == "s3":
                return mock_s3
            return Mock()

        mock_boto3_client.side_effect = client_side_effect

        findings = get_cloudtrail_findings()

        # Only the non-multi-region trail should generate findings
        assert len(findings) == 1
        assert findings[0]["resource_id"] == "single-region-trail"

    @patch("modules.cloudtrail_findings.boto3.client")
    def test_multiple_issues_in_single_trail(self, mock_boto3_client):
        """Test detection of multiple issues in a single trail."""
        trail_with_multiple_issues = {
            "Name": "bad-trail",
            "S3BucketName": "my-cloudtrail-bucket",
            "IncludeGlobalServiceEvents": True,
            "IsMultiRegionTrail": False,
            "HomeRegion": "us-east-1",
            "TrailARN": "arn:aws:cloudtrail:us-east-1:123456789012:trail/bad-trail",
            "LogFileValidationEnabled": False,
            # No CloudWatchLogsLogGroupArn
            "HasCustomEventSelectors": False,
            "HasInsightSelectors": False,
            "IsOrganizationTrail": False,
        }

        mock_ct = Mock()
        mock_ct.describe_trails.return_value = {
            "trailList": [trail_with_multiple_issues]
        }

        mock_s3 = Mock()
        mock_s3.get_bucket_logging.return_value = {}

        def client_side_effect(service, **kwargs):
            if service == "cloudtrail":
                return mock_ct
            elif service == "s3":
                return mock_s3
            return Mock()

        mock_boto3_client.side_effect = client_side_effect

        findings = get_cloudtrail_findings()

        # Should have findings for: not multi-region, no validation, no cloudwatch, no bucket logging
        assert len(findings) == 4


class TestNoCloudTrail:
    """Test cases when no CloudTrail trail exists."""

    @patch("modules.cloudtrail_findings.boto3.client")
    def test_no_cloudtrail_trail(self, mock_boto3_client):
        """Test handling when no CloudTrail trail exists."""
        mock_ct = Mock()
        mock_ct.describe_trails.return_value = {"trailList": []}
        mock_boto3_client.return_value = mock_ct

        findings = get_cloudtrail_findings()

        assert len(findings) == 1
        assert findings[0]["resource_id"] == "Account"
        assert findings[0]["resource_type"] == "AWS_ACCOUNT"
        assert findings[0]["service"] == "CloudTrail"
        assert findings[0]["severity"] == "CRITICAL"
        assert "No CloudTrail trail exists" in findings[0]["finding"]


class TestErrorHandling:
    """Test cases for error handling."""

    @patch("modules.cloudtrail_findings.boto3.client")
    def test_generic_exception(self, mock_boto3_client):
        """Test handling of generic exceptions."""
        mock_ct = Mock()
        mock_ct.describe_trails.side_effect = Exception("Unexpected error")
        mock_boto3_client.return_value = mock_ct

        # Should not raise an exception, just log the error
        findings = get_cloudtrail_findings()
        assert isinstance(findings, list)

    @patch("modules.cloudtrail_findings.boto3.client")
    def test_client_error(self, mock_boto3_client):
        """Test handling of ClientError."""
        mock_ct = Mock()
        mock_ct.describe_trails.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Not authorized"}},
            "DescribeTrails",
        )
        mock_boto3_client.return_value = mock_ct

        # Should not raise an exception, just log the error
        findings = get_cloudtrail_findings()
        assert isinstance(findings, list)

    @patch("modules.cloudtrail_findings.boto3.client")
    def test_s3_bucket_logging_error(self, mock_boto3_client, sample_trail_configured):
        """Test handling of S3 bucket logging errors."""
        mock_ct = Mock()
        mock_ct.describe_trails.return_value = {"trailList": [sample_trail_configured]}

        mock_s3 = Mock()
        mock_s3.get_bucket_logging.side_effect = Exception("S3 error")

        def client_side_effect(service, **kwargs):
            if service == "cloudtrail":
                return mock_ct
            elif service == "s3":
                return mock_s3
            return Mock()

        mock_boto3_client.side_effect = client_side_effect

        # Should not raise an exception, just continue
        findings = get_cloudtrail_findings()
        assert isinstance(findings, list)

    @patch("modules.cloudtrail_findings.boto3.client")
    def test_trail_without_s3_bucket(self, mock_boto3_client):
        """Test handling of trail without S3 bucket name."""
        trail_without_bucket = {
            "Name": "trail-without-bucket",
            "IncludeGlobalServiceEvents": True,
            "IsMultiRegionTrail": True,
            "HomeRegion": "us-east-1",
            "TrailARN": "arn:aws:cloudtrail:us-east-1:123456789012:trail/trail-without-bucket",
            "LogFileValidationEnabled": True,
            "HasCustomEventSelectors": False,
            "HasInsightSelectors": False,
            "IsOrganizationTrail": False,
        }

        mock_ct = Mock()
        mock_ct.describe_trails.return_value = {"trailList": [trail_without_bucket]}
        mock_boto3_client.return_value = mock_ct

        # Should not raise an exception
        findings = get_cloudtrail_findings()
        assert isinstance(findings, list)


class TestFindingTransformation:
    """Test cases for finding data transformation."""

    @patch("modules.cloudtrail_findings.boto3.client")
    def test_finding_structure(self, mock_boto3_client, sample_trail_not_multiregion):
        """Test that findings are transformed to the correct structure."""
        mock_ct = Mock()
        mock_ct.describe_trails.return_value = {
            "trailList": [sample_trail_not_multiregion]
        }

        mock_s3 = Mock()
        mock_s3.get_bucket_logging.return_value = {
            "LoggingEnabled": {
                "TargetBucket": "logging-bucket",
                "TargetPrefix": "cloudtrail-logs/",
            }
        }

        def client_side_effect(service, **kwargs):
            if service == "cloudtrail":
                return mock_ct
            elif service == "s3":
                return mock_s3
            return Mock()

        mock_boto3_client.side_effect = client_side_effect

        findings = get_cloudtrail_findings()

        assert len(findings) == 1
        finding = findings[0]

        # Check required fields
        assert "resource_id" in finding
        assert "resource_type" in finding
        assert "service" in finding
        assert "severity" in finding
        assert "finding" in finding
        assert "recommendation" in finding

    @patch("modules.cloudtrail_findings.boto3.client")
    def test_recommendation_text(self, mock_boto3_client, sample_trail_not_multiregion):
        """Test that recommendation text is included."""
        mock_ct = Mock()
        mock_ct.describe_trails.return_value = {
            "trailList": [sample_trail_not_multiregion]
        }

        mock_s3 = Mock()
        mock_s3.get_bucket_logging.return_value = {
            "LoggingEnabled": {
                "TargetBucket": "logging-bucket",
                "TargetPrefix": "cloudtrail-logs/",
            }
        }

        def client_side_effect(service, **kwargs):
            if service == "cloudtrail":
                return mock_ct
            elif service == "s3":
                return mock_s3
            return Mock()

        mock_boto3_client.side_effect = client_side_effect

        findings = get_cloudtrail_findings()

        assert len(findings) == 1
        assert "Enable multi-region logging" in findings[0]["recommendation"]

    @patch("modules.cloudtrail_findings.boto3.client")
    def test_severity_levels(self, mock_boto3_client):
        """Test that different issues have appropriate severity levels."""
        trail_with_all_issues = {
            "Name": "bad-trail",
            "S3BucketName": "my-cloudtrail-bucket",
            "IncludeGlobalServiceEvents": True,
            "IsMultiRegionTrail": False,
            "HomeRegion": "us-east-1",
            "TrailARN": "arn:aws:cloudtrail:us-east-1:123456789012:trail/bad-trail",
            "LogFileValidationEnabled": False,
            "HasCustomEventSelectors": False,
            "HasInsightSelectors": False,
            "IsOrganizationTrail": False,
        }

        mock_ct = Mock()
        mock_ct.describe_trails.return_value = {"trailList": [trail_with_all_issues]}

        mock_s3 = Mock()
        mock_s3.get_bucket_logging.return_value = {}

        def client_side_effect(service, **kwargs):
            if service == "cloudtrail":
                return mock_ct
            elif service == "s3":
                return mock_s3
            return Mock()

        mock_boto3_client.side_effect = client_side_effect

        findings = get_cloudtrail_findings()

        # Check severity levels
        assert any(
            f["severity"] == "HIGH" and "multi-region" in f["finding"] for f in findings
        )
        assert any(
            f["severity"] == "HIGH" and "validation" in f["finding"] for f in findings
        )
        assert any(
            f["severity"] == "MEDIUM" and "CloudWatch" in f["finding"] for f in findings
        )
        assert any(
            f["severity"] == "MEDIUM" and "Access logging" in f["finding"]
            for f in findings
        )
