"""
Unit tests for Security Hub findings module.

Tests the get_securityhub_findings function in src/lambda/modules/securityhub_findings.py
"""

import pytest
from unittest.mock import Mock, patch
from botocore.exceptions import ClientError

# Add the src/lambda directory to the path so we can import the modules
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src/lambda"))

from modules.securityhub_findings import get_securityhub_findings


@pytest.fixture
def mock_securityhub_client():
    """Create a mock Security Hub client."""
    client = Mock()
    return client


@pytest.fixture
def sample_critical_finding():
    """Provide a sample CRITICAL severity finding."""
    return {
        "Id": "finding-id-1",
        "Title": "S3 Bucket Public Access",
        "Description": "S3 bucket allows public read access",
        "Severity": {"Label": "CRITICAL", "Original": 90},
        "RecordState": "ACTIVE",
        "WorkflowStatus": "NEW",
        "Resources": [
            {
                "Type": "AwsS3Bucket",
                "Id": "arn:aws:s3:::my-bucket",
                "Partition": "aws",
                "Region": "us-east-1",
            }
        ],
        "ProductFields": {
            "aws/securityhub/ProductName": "Security Hub",
            "aws/securityhub/CompanyName": "AWS",
        },
        "Remediation": {
            "Recommendation": {
                "Text": "Disable public access",
                "Url": "https://docs.aws.amazon.com/AmazonS3/latest/userguide/access-control-block-public-access.html",
            }
        },
    }


@pytest.fixture
def sample_high_finding():
    """Provide a sample HIGH severity finding."""
    return {
        "Id": "finding-id-2",
        "Title": "Security Group Open Port",
        "Description": "Security group allows SSH access from 0.0.0.0/0",
        "Severity": {"Label": "HIGH", "Original": 70},
        "RecordState": "ACTIVE",
        "WorkflowStatus": "NOTIFIED",
        "Resources": [
            {
                "Type": "AwsEc2SecurityGroup",
                "Id": "sg-12345678",
                "Partition": "aws",
                "Region": "us-east-1",
            }
        ],
        "ProductFields": {"aws/securityhub/ProductName": "Security Hub"},
        "Remediation": {
            "Recommendation": {
                "Text": "Restrict IP range",
                "Url": "https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/security-group-rules.html",
            }
        },
    }


@pytest.fixture
def sample_medium_finding():
    """Provide a sample MEDIUM severity finding (should be filtered out)."""
    return {
        "Id": "finding-id-3",
        "Title": "CloudTrail Logging Disabled",
        "Description": "CloudTrail is not enabled",
        "Severity": {"Label": "MEDIUM", "Original": 50},
        "RecordState": "ACTIVE",
        "WorkflowStatus": "NEW",
        "Resources": [
            {
                "Type": "AwsCloudTrailTrail",
                "Id": "arn:aws:cloudtrail:us-east-1:123456789012:trail/my-trail",
                "Partition": "aws",
                "Region": "us-east-1",
            }
        ],
        "ProductFields": {"aws/securityhub/ProductName": "Security Hub"},
    }


@pytest.fixture
def sample_suppressed_finding():
    """Provide a sample suppressed finding (should be filtered out)."""
    return {
        "Id": "finding-id-4",
        "Title": "Suppressed Finding",
        "Description": "This finding has been suppressed",
        "Severity": {"Label": "CRITICAL", "Original": 90},
        "RecordState": "ACTIVE",
        "WorkflowStatus": "SUPPRESSED",
        "Resources": [
            {
                "Type": "AwsS3Bucket",
                "Id": "arn:aws:s3:::my-bucket-2",
                "Partition": "aws",
                "Region": "us-east-1",
            }
        ],
        "ProductFields": {"aws/securityhub/ProductName": "Security Hub"},
    }


@pytest.fixture
def sample_archived_finding():
    """Provide a sample archived finding (should be filtered out)."""
    return {
        "Id": "finding-id-5",
        "Title": "Archived Finding",
        "Description": "This finding has been archived",
        "Severity": {"Label": "CRITICAL", "Original": 90},
        "RecordState": "ARCHIVED",
        "WorkflowStatus": "NEW",
        "Resources": [
            {
                "Type": "AwsS3Bucket",
                "Id": "arn:aws:s3:::my-bucket-3",
                "Partition": "aws",
                "Region": "us-east-1",
            }
        ],
        "ProductFields": {"aws/securityhub/ProductName": "Security Hub"},
    }


@pytest.fixture
def sample_finding_without_resources():
    """Provide a sample finding without resources."""
    return {
        "Id": "finding-id-6",
        "Title": "Finding Without Resources",
        "Description": "This finding has no resources",
        "Severity": {"Label": "CRITICAL", "Original": 90},
        "RecordState": "ACTIVE",
        "WorkflowStatus": "NEW",
        "Resources": [],
        "ProductFields": {"aws/securityhub/ProductName": "Security Hub"},
    }


@pytest.fixture
def sample_finding_without_product_fields():
    """Provide a sample finding without product fields."""
    return {
        "Id": "finding-id-7",
        "Title": "Finding Without Product Fields",
        "Description": "This finding has no product fields",
        "Severity": {"Label": "HIGH", "Original": 70},
        "RecordState": "ACTIVE",
        "WorkflowStatus": "NEW",
        "Resources": [
            {
                "Type": "AwsS3Bucket",
                "Id": "arn:aws:s3:::my-bucket-4",
                "Partition": "aws",
                "Region": "us-east-1",
            }
        ],
    }


class TestGetSecurityHubFindingsSuccess:
    """Test cases for successful Security Hub findings retrieval."""

    @patch("modules.securityhub_findings.boto3.client")
    def test_get_critical_findings(self, mock_boto3_client, sample_critical_finding):
        """Test retrieval of CRITICAL severity findings."""
        mock_sh = Mock()
        mock_sh.get_findings.return_value = {"Findings": [sample_critical_finding]}
        mock_boto3_client.return_value = mock_sh

        findings = get_securityhub_findings()

        assert len(findings) == 1
        assert findings[0]["severity"] == "CRITICAL"
        assert findings[0]["resource_id"] == "arn:aws:s3:::my-bucket"
        assert findings[0]["resource_type"] == "AwsS3Bucket"
        assert findings[0]["service"] == "Security Hub"
        assert "S3 Bucket Public Access" in findings[0]["finding"]
        assert "S3 bucket allows public read access" in findings[0]["description"]

    @patch("modules.securityhub_findings.boto3.client")
    def test_get_high_findings(self, mock_boto3_client, sample_high_finding):
        """Test retrieval of HIGH severity findings."""
        mock_sh = Mock()
        mock_sh.get_findings.return_value = {"Findings": [sample_high_finding]}
        mock_boto3_client.return_value = mock_sh

        findings = get_securityhub_findings()

        assert len(findings) == 1
        assert findings[0]["severity"] == "HIGH"
        assert findings[0]["resource_id"] == "sg-12345678"
        assert findings[0]["resource_type"] == "AwsEc2SecurityGroup"
        assert "Security Group Open Port" in findings[0]["finding"]

    @patch("modules.securityhub_findings.boto3.client")
    def test_get_multiple_findings(
        self, mock_boto3_client, sample_critical_finding, sample_high_finding
    ):
        """Test retrieval of multiple findings."""
        mock_sh = Mock()
        mock_sh.get_findings.return_value = {
            "Findings": [sample_critical_finding, sample_high_finding]
        }
        mock_boto3_client.return_value = mock_sh

        findings = get_securityhub_findings()

        assert len(findings) == 2
        assert any(f["severity"] == "CRITICAL" for f in findings)
        assert any(f["severity"] == "HIGH" for f in findings)

    @patch("modules.securityhub_findings.boto3.client")
    def test_filters_out_medium_severity(
        self, mock_boto3_client, sample_critical_finding, sample_medium_finding
    ):
        """Test that MEDIUM severity findings are filtered out."""
        mock_sh = Mock()
        mock_sh.get_findings.return_value = {
            "Findings": [sample_critical_finding, sample_medium_finding]
        }
        mock_boto3_client.return_value = mock_sh

        findings = get_securityhub_findings()

        assert len(findings) == 1
        assert findings[0]["severity"] == "CRITICAL"
        assert not any(f["severity"] == "MEDIUM" for f in findings)

    @patch("modules.securityhub_findings.boto3.client")
    def test_filters_out_suppressed_findings(
        self, mock_boto3_client, sample_critical_finding, sample_suppressed_finding
    ):
        """Test that SUPPRESSED workflow status findings are filtered out."""
        mock_sh = Mock()
        mock_sh.get_findings.return_value = {
            "Findings": [sample_critical_finding, sample_suppressed_finding]
        }
        mock_boto3_client.return_value = mock_sh

        findings = get_securityhub_findings()

        assert len(findings) == 1
        assert findings[0]["severity"] == "CRITICAL"

    @patch("modules.securityhub_findings.boto3.client")
    def test_filters_out_archived_findings(
        self, mock_boto3_client, sample_critical_finding, sample_archived_finding
    ):
        """Test that ARCHIVED record state findings are filtered out."""
        mock_sh = Mock()
        mock_sh.get_findings.return_value = {
            "Findings": [sample_critical_finding, sample_archived_finding]
        }
        mock_boto3_client.return_value = mock_sh

        findings = get_securityhub_findings()

        assert len(findings) == 1
        assert findings[0]["severity"] == "CRITICAL"

    @patch("modules.securityhub_findings.boto3.client")
    def test_handles_finding_without_resources(
        self, mock_boto3_client, sample_finding_without_resources
    ):
        """Test handling of findings without resources."""
        mock_sh = Mock()
        mock_sh.get_findings.return_value = {
            "Findings": [sample_finding_without_resources]
        }
        mock_boto3_client.return_value = mock_sh

        findings = get_securityhub_findings()

        assert len(findings) == 1
        assert findings[0]["resource_id"] == "Unknown"
        assert findings[0]["resource_type"] == "Unknown"

    @patch("modules.securityhub_findings.boto3.client")
    def test_handles_finding_without_product_fields(
        self, mock_boto3_client, sample_finding_without_product_fields
    ):
        """Test handling of findings without product fields."""
        mock_sh = Mock()
        mock_sh.get_findings.return_value = {
            "Findings": [sample_finding_without_product_fields]
        }
        mock_boto3_client.return_value = mock_sh

        findings = get_securityhub_findings()

        assert len(findings) == 1
        # Service should be extracted from resource type
        assert findings[0]["service"] == "AwsS3Bucket"

    @patch("modules.securityhub_findings.boto3.client")
    def test_includes_remediation_url(self, mock_boto3_client, sample_critical_finding):
        """Test that remediation URL is included in recommendation."""
        mock_sh = Mock()
        mock_sh.get_findings.return_value = {"Findings": [sample_critical_finding]}
        mock_boto3_client.return_value = mock_sh

        findings = get_securityhub_findings()

        assert len(findings) == 1
        assert "https://docs.aws.amazon.com/AmazonS3" in findings[0]["recommendation"]

    @patch("modules.securityhub_findings.boto3.client")
    def test_handles_empty_findings_list(self, mock_boto3_client):
        """Test handling of empty findings list."""
        mock_sh = Mock()
        mock_sh.get_findings.return_value = {"Findings": []}
        mock_boto3_client.return_value = mock_sh

        findings = get_securityhub_findings()

        assert len(findings) == 0

    @patch("modules.securityhub_findings.boto3.client")
    def test_max_results_parameter(self, mock_boto3_client, sample_critical_finding):
        """Test that MaxResults parameter is set correctly."""
        mock_sh = Mock()
        mock_sh.get_findings.return_value = {"Findings": [sample_critical_finding]}
        mock_boto3_client.return_value = mock_sh

        findings = get_securityhub_findings()

        mock_sh.get_findings.assert_called_once()
        call_kwargs = mock_sh.get_findings.call_args[1]
        assert "MaxResults" in call_kwargs
        assert call_kwargs["MaxResults"] == 20

    @patch("modules.securityhub_findings.boto3.client")
    def test_filters_parameter(self, mock_boto3_client, sample_critical_finding):
        """Test that filters are set correctly."""
        mock_sh = Mock()
        mock_sh.get_findings.return_value = {"Findings": [sample_critical_finding]}
        mock_boto3_client.return_value = mock_sh

        findings = get_securityhub_findings()

        mock_sh.get_findings.assert_called_once()
        call_kwargs = mock_sh.get_findings.call_args[1]
        assert "Filters" in call_kwargs

        filters = call_kwargs["Filters"]
        assert "RecordState" in filters
        assert "SeverityLabel" in filters
        assert "WorkflowStatus" in filters


class TestSecurityHubNotEnabled:
    """Test cases when Security Hub is not enabled."""

    @patch("modules.securityhub_findings.boto3.client")
    def test_security_hub_not_enabled(self, mock_boto3_client):
        """Test handling when Security Hub is not enabled."""
        mock_sh = Mock()
        mock_sh.exceptions.InvalidAccessException = type(
            "InvalidAccessException", (Exception,), {}
        )
        mock_sh.get_findings.side_effect = mock_sh.exceptions.InvalidAccessException(
            {}, "GetFindings"
        )
        mock_boto3_client.return_value = mock_sh

        findings = get_securityhub_findings()

        assert len(findings) == 0


class TestErrorHandling:
    """Test cases for error handling."""

    @patch("modules.securityhub_findings.boto3.client")
    def test_generic_exception(self, mock_boto3_client):
        """Test handling of generic exceptions."""
        mock_sh = Mock()
        mock_sh.get_findings.side_effect = Exception("Unexpected error")
        mock_boto3_client.return_value = mock_sh

        # Should not raise an exception, just log the error
        findings = get_securityhub_findings()
        assert isinstance(findings, list)

    @patch("modules.securityhub_findings.boto3.client")
    def test_client_error(self, mock_boto3_client):
        """Test handling of ClientError."""
        mock_sh = Mock()
        mock_sh.get_findings.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Not authorized"}},
            "GetFindings",
        )
        mock_boto3_client.return_value = mock_sh

        # Should not raise an exception, just log the error
        findings = get_securityhub_findings()
        assert isinstance(findings, list)


class TestFindingTransformation:
    """Test cases for finding data transformation."""

    @patch("modules.securityhub_findings.boto3.client")
    def test_finding_structure(self, mock_boto3_client, sample_critical_finding):
        """Test that findings are transformed to the correct structure."""
        mock_sh = Mock()
        mock_sh.get_findings.return_value = {"Findings": [sample_critical_finding]}
        mock_boto3_client.return_value = mock_sh

        findings = get_securityhub_findings()

        assert len(findings) == 1
        finding = findings[0]

        # Check required fields
        assert "resource_id" in finding
        assert "resource_type" in finding
        assert "service" in finding
        assert "severity" in finding
        assert "finding" in finding
        assert "description" in finding
        assert "recommendation" in finding

    @patch("modules.securityhub_findings.boto3.client")
    def test_service_extraction_from_product_fields(
        self, mock_boto3_client, sample_critical_finding
    ):
        """Test service extraction from ProductFields."""
        mock_sh = Mock()
        mock_sh.get_findings.return_value = {"Findings": [sample_critical_finding]}
        mock_boto3_client.return_value = mock_sh

        findings = get_securityhub_findings()

        assert findings[0]["service"] == "Security Hub"

    @patch("modules.securityhub_findings.boto3.client")
    def test_service_extraction_from_resource_type(
        self, mock_boto3_client, sample_finding_without_product_fields
    ):
        """Test service extraction from resource type when ProductFields is missing."""
        mock_sh = Mock()
        mock_sh.get_findings.return_value = {
            "Findings": [sample_finding_without_product_fields]
        }
        mock_boto3_client.return_value = mock_sh

        findings = get_securityhub_findings()

        # Should extract service from resource type (AwsS3Bucket -> AwsS3Bucket)
        assert findings[0]["service"] == "AwsS3Bucket"

    @patch("modules.securityhub_findings.boto3.client")
    def test_remediation_url_handling(self, mock_boto3_client):
        """Test handling of missing remediation URL."""
        finding_without_remediation = {
            "Id": "finding-id-8",
            "Title": "Finding Without Remediation",
            "Description": "This finding has no remediation",
            "Severity": {"Label": "CRITICAL", "Original": 90},
            "RecordState": "ACTIVE",
            "WorkflowStatus": "NEW",
            "Resources": [
                {
                    "Type": "AwsS3Bucket",
                    "Id": "arn:aws:s3:::my-bucket",
                    "Partition": "aws",
                    "Region": "us-east-1",
                }
            ],
            "ProductFields": {"aws/securityhub/ProductName": "Security Hub"},
        }

        mock_sh = Mock()
        mock_sh.get_findings.return_value = {"Findings": [finding_without_remediation]}
        mock_boto3_client.return_value = mock_sh

        findings = get_securityhub_findings()

        assert len(findings) == 1
        assert "N/A" in findings[0]["recommendation"]
