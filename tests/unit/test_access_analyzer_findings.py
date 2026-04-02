"""
Unit tests for Access Analyzer findings module.

Tests the get_access_analyzer_findings function in src/lambda/modules/access_analyzer_findings.py
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from botocore.exceptions import ClientError

# Add the src/lambda directory to the path so we can import the modules
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src/lambda"))

from modules.access_analyzer_findings import get_access_analyzer_findings


@pytest.fixture
def mock_access_analyzer_client():
    """Create a mock Access Analyzer client."""
    client = Mock()
    return client


@pytest.fixture
def sample_analyzers():
    """Provide sample analyzers."""
    return {
        "analyzers": [
            {
                "arn": "arn:aws:access-analyzer:us-east-1:123456789012:analyzer/MyAnalyzer",
                "name": "MyAnalyzer",
                "type": "ACCOUNT",
                "status": "ACTIVE",
                "createdAt": "2024-01-01T00:00:00Z",
            }
        ]
    }


@pytest.fixture
def sample_s3_finding():
    """Provide a sample S3 bucket finding."""
    return {
        "id": "finding-id-1",
        "resourceArn": "arn:aws:s3:::my-public-bucket",
        "resourceType": "AWS::S3::Bucket",
        "resourceOwnerAccount": "123456789012",
        "status": "ACTIVE",
        "createdAt": "2024-01-01T00:00:00Z",
        "updatedAt": "2024-01-01T00:00:00Z",
        "principal": {"AWS": ["arn:aws:iam::123456789012:root"]},
        "action": ["s3:GetObject"],
        "condition": {},
        "isPublic": True,
    }


@pytest.fixture
def sample_iam_role_finding():
    """Provide a sample IAM role finding."""
    return {
        "id": "finding-id-2",
        "resourceArn": "arn:aws:iam::123456789012:role/MyRole",
        "resourceType": "AWS::IAM::Role",
        "resourceOwnerAccount": "123456789012",
        "status": "ACTIVE",
        "createdAt": "2024-01-01T00:00:00Z",
        "updatedAt": "2024-01-01T00:00:00Z",
        "principal": {"AWS": ["*"]},
        "action": ["sts:AssumeRole"],
        "condition": {},
        "isPublic": False,
    }


@pytest.fixture
def sample_kms_key_finding():
    """Provide a sample KMS key finding."""
    return {
        "id": "finding-id-3",
        "resourceArn": "arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012",
        "resourceType": "AWS::KMS::Key",
        "resourceOwnerAccount": "123456789012",
        "status": "ACTIVE",
        "createdAt": "2024-01-01T00:00:00Z",
        "updatedAt": "2024-01-01T00:00:00Z",
        "principal": {"AWS": ["arn:aws:iam::123456789012:root"]},
        "action": ["kms:Decrypt"],
        "condition": {},
        "isPublic": False,
    }


@pytest.fixture
def sample_lambda_function_finding():
    """Provide a sample Lambda function finding."""
    return {
        "id": "finding-id-4",
        "resourceArn": "arn:aws:lambda:us-east-1:123456789012:function:MyFunction",
        "resourceType": "AWS::Lambda::Function",
        "resourceOwnerAccount": "123456789012",
        "status": "ACTIVE",
        "createdAt": "2024-01-01T00:00:00Z",
        "updatedAt": "2024-01-01T00:00:00Z",
        "principal": {"AWS": ["*"]},
        "action": ["lambda:InvokeFunction"],
        "condition": {},
        "isPublic": False,
    }


@pytest.fixture
def sample_sqs_queue_finding():
    """Provide a sample SQS queue finding."""
    return {
        "id": "finding-id-5",
        "resourceArn": "arn:aws:sqs:us-east-1:123456789012:MyQueue",
        "resourceType": "AWS::SQS::Queue",
        "resourceOwnerAccount": "123456789012",
        "status": "ACTIVE",
        "createdAt": "2024-01-01T00:00:00Z",
        "updatedAt": "2024-01-01T00:00:00Z",
        "principal": {"AWS": ["arn:aws:iam::123456789012:root"]},
        "action": ["sqs:SendMessage"],
        "condition": {},
        "isPublic": False,
    }


@pytest.fixture
def sample_ec2_instance_finding():
    """Provide a sample EC2 instance finding (should be filtered out)."""
    return {
        "id": "finding-id-6",
        "resourceArn": "arn:aws:ec2:us-east-1:123456789012:instance/i-1234567890abcdef0",
        "resourceType": "AWS::EC2::Instance",
        "resourceOwnerAccount": "123456789012",
        "status": "ACTIVE",
        "createdAt": "2024-01-01T00:00:00Z",
        "updatedAt": "2024-01-01T00:00:00Z",
        "principal": {"AWS": ["*"]},
        "action": ["ec2:DescribeInstances"],
        "condition": {},
        "isPublic": False,
    }


@pytest.fixture
def sample_archived_finding():
    """Provide a sample archived finding (should be filtered out)."""
    return {
        "id": "finding-id-7",
        "resourceArn": "arn:aws:s3:::my-bucket",
        "resourceType": "AWS::S3::Bucket",
        "resourceOwnerAccount": "123456789012",
        "status": "ARCHIVED",
        "createdAt": "2024-01-01T00:00:00Z",
        "updatedAt": "2024-01-01T00:00:00Z",
        "principal": {"AWS": ["*"]},
        "action": ["s3:GetObject"],
        "condition": {},
        "isPublic": True,
    }


class TestGetAccessAnalyzerFindingsSuccess:
    """Test cases for successful Access Analyzer findings retrieval."""

    @patch("modules.access_analyzer_findings.boto3.client")
    def test_get_s3_findings(
        self, mock_boto3_client, sample_analyzers, sample_s3_finding
    ):
        """Test retrieval of S3 bucket findings."""
        mock_aa = Mock()
        mock_aa.list_analyzers.return_value = sample_analyzers

        mock_paginator = Mock()
        mock_paginator.paginate.return_value = [[{"findings": [sample_s3_finding]}]]
        mock_aa.get_paginator.return_value = mock_paginator

        mock_boto3_client.return_value = mock_aa

        findings = get_access_analyzer_findings()

        assert len(findings) == 1
        assert findings[0]["resource_id"] == "arn:aws:s3:::my-public-bucket"
        assert findings[0]["resource_type"] == "AWS::S3::Bucket"
        assert findings[0]["service"] == "S3"
        assert "External access detected" in findings[0]["finding"]

    @patch("modules.access_analyzer_findings.boto3.client")
    def test_get_iam_role_findings(
        self, mock_boto3_client, sample_analyzers, sample_iam_role_finding
    ):
        """Test retrieval of IAM role findings."""
        mock_aa = Mock()
        mock_aa.list_analyzers.return_value = sample_analyzers

        mock_paginator = Mock()
        mock_paginator.paginate.return_value = [
            [{"findings": [sample_iam_role_finding]}]
        ]
        mock_aa.get_paginator.return_value = mock_paginator

        mock_boto3_client.return_value = mock_aa

        findings = get_access_analyzer_findings()

        assert len(findings) == 1
        assert findings[0]["resource_id"] == "arn:aws:iam::123456789012:role/MyRole"
        assert findings[0]["resource_type"] == "AWS::IAM::Role"
        assert findings[0]["service"] == "IAM"

    @patch("modules.access_analyzer_findings.boto3.client")
    def test_get_kms_key_findings(
        self, mock_boto3_client, sample_analyzers, sample_kms_key_finding
    ):
        """Test retrieval of KMS key findings."""
        mock_aa = Mock()
        mock_aa.list_analyzers.return_value = sample_analyzers

        mock_paginator = Mock()
        mock_paginator.paginate.return_value = [
            [{"findings": [sample_kms_key_finding]}]
        ]
        mock_aa.get_paginator.return_value = mock_paginator

        mock_boto3_client.return_value = mock_aa

        findings = get_access_analyzer_findings()

        assert len(findings) == 1
        assert findings[0]["resource_type"] == "AWS::KMS::Key"
        assert findings[0]["service"] == "KMS"

    @patch("modules.access_analyzer_findings.boto3.client")
    def test_get_lambda_function_findings(
        self, mock_boto3_client, sample_analyzers, sample_lambda_function_finding
    ):
        """Test retrieval of Lambda function findings."""
        mock_aa = Mock()
        mock_aa.list_analyzers.return_value = sample_analyzers

        mock_paginator = Mock()
        mock_paginator.paginate.return_value = [
            [{"findings": [sample_lambda_function_finding]}]
        ]
        mock_aa.get_paginator.return_value = mock_paginator

        mock_boto3_client.return_value = mock_aa

        findings = get_access_analyzer_findings()

        assert len(findings) == 1
        assert findings[0]["resource_type"] == "AWS::Lambda::Function"
        assert findings[0]["service"] == "Lambda"

    @patch("modules.access_analyzer_findings.boto3.client")
    def test_get_sqs_queue_findings(
        self, mock_boto3_client, sample_analyzers, sample_sqs_queue_finding
    ):
        """Test retrieval of SQS queue findings."""
        mock_aa = Mock()
        mock_aa.list_analyzers.return_value = sample_analyzers

        mock_paginator = Mock()
        mock_paginator.paginate.return_value = [
            [{"findings": [sample_sqs_queue_finding]}]
        ]
        mock_aa.get_paginator.return_value = mock_paginator

        mock_boto3_client.return_value = mock_aa

        findings = get_access_analyzer_findings()

        assert len(findings) == 1
        assert findings[0]["resource_type"] == "AWS::SQS::Queue"
        assert findings[0]["service"] == "SQS"

    @patch("modules.access_analyzer_findings.boto3.client")
    def test_get_multiple_findings(
        self,
        mock_boto3_client,
        sample_analyzers,
        sample_s3_finding,
        sample_iam_role_finding,
    ):
        """Test retrieval of multiple findings."""
        mock_aa = Mock()
        mock_aa.list_analyzers.return_value = sample_analyzers

        mock_paginator = Mock()
        mock_paginator.paginate.return_value = [
            [{"findings": [sample_s3_finding, sample_iam_role_finding]}]
        ]
        mock_aa.get_paginator.return_value = mock_paginator

        mock_boto3_client.return_value = mock_aa

        findings = get_access_analyzer_findings()

        assert len(findings) == 2
        assert any(f["resource_type"] == "AWS::S3::Bucket" for f in findings)
        assert any(f["resource_type"] == "AWS::IAM::Role" for f in findings)

    @patch("modules.access_analyzer_findings.boto3.client")
    def test_filters_out_non_target_resource_types(
        self, mock_boto3_client, sample_analyzers, sample_ec2_instance_finding
    ):
        """Test that non-target resource types are filtered out."""
        mock_aa = Mock()
        mock_aa.list_analyzers.return_value = sample_analyzers

        mock_paginator = Mock()
        mock_paginator.paginate.return_value = [
            [{"findings": [sample_ec2_instance_finding]}]
        ]
        mock_aa.get_paginator.return_value = mock_paginator

        mock_boto3_client.return_value = mock_aa

        findings = get_access_analyzer_findings()

        assert len(findings) == 0

    @patch("modules.access_analyzer_findings.boto3.client")
    def test_filters_out_archived_findings(
        self, mock_boto3_client, sample_analyzers, sample_archived_finding
    ):
        """Test that archived findings are filtered out."""
        mock_aa = Mock()
        mock_aa.list_analyzers.return_value = sample_analyzers

        mock_paginator = Mock()
        mock_paginator.paginate.return_value = [
            [{"findings": [sample_archived_finding]}]
        ]
        mock_aa.get_paginator.return_value = mock_paginator

        mock_boto3_client.return_value = mock_aa

        findings = get_access_analyzer_findings()

        assert len(findings) == 0

    @patch("modules.access_analyzer_findings.boto3.client")
    def test_handles_empty_findings_list(self, mock_boto3_client, sample_analyzers):
        """Test handling of empty findings list."""
        mock_aa = Mock()
        mock_aa.list_analyzers.return_value = sample_analyzers

        mock_paginator = Mock()
        mock_paginator.paginate.return_value = [[{"findings": []}]]
        mock_aa.get_paginator.return_value = mock_paginator

        mock_boto3_client.return_value = mock_aa

        findings = get_access_analyzer_findings()

        assert len(findings) == 0

    @patch("modules.access_analyzer_findings.boto3.client")
    def test_analyzer_arn_extraction(
        self, mock_boto3_client, sample_analyzers, sample_s3_finding
    ):
        """Test that analyzer ARN is correctly extracted."""
        mock_aa = Mock()
        mock_aa.list_analyzers.return_value = sample_analyzers

        mock_paginator = Mock()
        mock_paginator.paginate.return_value = [[{"findings": [sample_s3_finding]}]]
        mock_aa.get_paginator.return_value = mock_paginator

        mock_boto3_client.return_value = mock_aa

        findings = get_access_analyzer_findings()

        # Verify that list_analyzers was called
        mock_aa.list_analyzers.assert_called_once_with(type="ACCOUNT")

    @patch("modules.access_analyzer_findings.boto3.client")
    def test_filter_parameter(
        self, mock_boto3_client, sample_analyzers, sample_s3_finding
    ):
        """Test that filter parameter is set correctly."""
        mock_aa = Mock()
        mock_aa.list_analyzers.return_value = sample_analyzers

        mock_paginator = Mock()
        mock_paginator.paginate.return_value = [[{"findings": [sample_s3_finding]}]]
        mock_aa.get_paginator.return_value = mock_paginator

        mock_boto3_client.return_value = mock_aa

        findings = get_access_analyzer_findings()

        # Verify that paginate was called with correct filter
        mock_paginator.paginate.assert_called_once()
        call_args = mock_paginator.paginate.call_args
        assert "filter" in call_args[1]
        assert call_args[1]["filter"] == {"status": {"eq": ["ACTIVE"]}}


class TestNoAnalyzerFound:
    """Test cases when no analyzer is found."""

    @patch("modules.access_analyzer_findings.boto3.client")
    def test_no_analyzer_found(self, mock_boto3_client):
        """Test handling when no analyzer is found."""
        mock_aa = Mock()
        mock_aa.list_analyzers.return_value = {"analyzers": []}
        mock_boto3_client.return_value = mock_aa

        findings = get_access_analyzer_findings()

        assert len(findings) == 0


class TestErrorHandling:
    """Test cases for error handling."""

    @patch("modules.access_analyzer_findings.boto3.client")
    def test_generic_exception(self, mock_boto3_client, sample_analyzers):
        """Test handling of generic exceptions."""
        mock_aa = Mock()
        mock_aa.list_analyzers.return_value = sample_analyzers
        mock_aa.get_paginator.side_effect = Exception("Unexpected error")
        mock_boto3_client.return_value = mock_aa

        # Should not raise an exception, just log the error
        findings = get_access_analyzer_findings()
        assert isinstance(findings, list)

    @patch("modules.access_analyzer_findings.boto3.client")
    def test_client_error(self, mock_boto3_client, sample_analyzers):
        """Test handling of ClientError."""
        mock_aa = Mock()
        mock_aa.list_analyzers.return_value = sample_analyzers
        mock_aa.get_paginator.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Not authorized"}},
            "ListFindings",
        )
        mock_boto3_client.return_value = mock_aa

        # Should not raise an exception, just log the error
        findings = get_access_analyzer_findings()
        assert isinstance(findings, list)


class TestFindingTransformation:
    """Test cases for finding data transformation."""

    @patch("modules.access_analyzer_findings.boto3.client")
    def test_finding_structure(
        self, mock_boto3_client, sample_analyzers, sample_s3_finding
    ):
        """Test that findings are transformed to the correct structure."""
        mock_aa = Mock()
        mock_aa.list_analyzers.return_value = sample_analyzers

        mock_paginator = Mock()
        mock_paginator.paginate.return_value = [[{"findings": [sample_s3_finding]}]]
        mock_aa.get_paginator.return_value = mock_paginator

        mock_boto3_client.return_value = mock_aa

        findings = get_access_analyzer_findings()

        assert len(findings) == 1
        finding = findings[0]

        # Check required fields
        assert "resource_id" in finding
        assert "resource_type" in finding
        assert "service" in finding
        assert "severity" in finding
        assert "finding" in finding
        assert "recommendation" in finding

    @patch("modules.access_analyzer_findings.boto3.client")
    def test_service_extraction_from_resource_type(
        self, mock_boto3_client, sample_analyzers, sample_s3_finding
    ):
        """Test service extraction from resource type."""
        mock_aa = Mock()
        mock_aa.list_analyzers.return_value = sample_analyzers

        mock_paginator = Mock()
        mock_paginator.paginate.return_value = [[{"findings": [sample_s3_finding]}]]
        mock_aa.get_paginator.return_value = mock_paginator

        mock_boto3_client.return_value = mock_aa

        findings = get_access_analyzer_findings()

        # Should extract service from resource type (AWS::S3::Bucket -> S3)
        assert findings[0]["service"] == "S3"

    @patch("modules.access_analyzer_findings.boto3.client")
    def test_principal_in_finding(
        self, mock_boto3_client, sample_analyzers, sample_s3_finding
    ):
        """Test that principal information is included in the finding."""
        mock_aa = Mock()
        mock_aa.list_analyzers.return_value = sample_analyzers

        mock_paginator = Mock()
        mock_paginator.paginate.return_value = [[{"findings": [sample_s3_finding]}]]
        mock_aa.get_paginator.return_value = mock_paginator

        mock_boto3_client.return_value = mock_aa

        findings = get_access_analyzer_findings()

        assert len(findings) == 1
        assert "External access detected" in findings[0]["finding"]

    @patch("modules.access_analyzer_findings.boto3.client")
    def test_recommendation_text(
        self, mock_boto3_client, sample_analyzers, sample_s3_finding
    ):
        """Test that recommendation text is included."""
        mock_aa = Mock()
        mock_aa.list_analyzers.return_value = sample_analyzers

        mock_paginator = Mock()
        mock_paginator.paginate.return_value = [[{"findings": [sample_s3_finding]}]]
        mock_aa.get_paginator.return_value = mock_paginator

        mock_boto3_client.return_value = mock_aa

        findings = get_access_analyzer_findings()

        assert len(findings) == 1
        assert "Review resource policy" in findings[0]["recommendation"]

    @patch("modules.access_analyzer_findings.boto3.client")
    def test_severity_default(self, mock_boto3_client, sample_analyzers):
        """Test that severity defaults to MEDIUM when not specified."""
        finding_without_severity = {
            "id": "finding-id-8",
            "resourceArn": "arn:aws:s3:::my-bucket",
            "resourceType": "AWS::S3::Bucket",
            "resourceOwnerAccount": "123456789012",
            "status": "ACTIVE",
            "createdAt": "2024-01-01T00:00:00Z",
            "updatedAt": "2024-01-01T00:00:00Z",
            "principal": {"AWS": ["*"]},
            "action": ["s3:GetObject"],
            "condition": {},
            "isPublic": True,
        }

        mock_aa = Mock()
        mock_aa.list_analyzers.return_value = sample_analyzers

        mock_paginator = Mock()
        mock_paginator.paginate.return_value = [
            [{"findings": [finding_without_severity]}]
        ]
        mock_aa.get_paginator.return_value = mock_paginator

        mock_boto3_client.return_value = mock_aa

        findings = get_access_analyzer_findings()

        assert len(findings) == 1
        assert findings[0]["severity"] == "MEDIUM"
