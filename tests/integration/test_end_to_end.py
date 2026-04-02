"""
Integration tests for AWS Automated Access Review.

Tests the complete end-to-end workflow of the access review process.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import os
import sys

# Add the src/lambda directory to the path so we can import the modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src/lambda"))

from index import lambda_handler


@pytest.fixture
def mock_context():
    """Create a mock Lambda context object."""
    context = Mock()
    context.request_id = "test-request-id-123"
    context.function_name = "test-function"
    context.invoked_function_arn = (
        "arn:aws:lambda:us-east-1:123456789012:function:test-function"
    )
    return context


@pytest.fixture
def sample_iam_findings():
    """Provide sample IAM findings."""
    return [
        {
            "resource_id": "user-without-mfa",
            "resource_type": "IAM_USER",
            "service": "IAM",
            "severity": "CRITICAL",
            "finding": "User is missing MFA",
            "recommendation": "Enable MFA for this user",
        }
    ]


@pytest.fixture
def sample_securityhub_findings():
    """Provide sample Security Hub findings."""
    return [
        {
            "resource_id": "sg-12345678",
            "resource_type": "AWS::Ec2SecurityGroup",
            "service": "EC2",
            "severity": "HIGH",
            "finding": "Security group allows SSH from 0.0.0.0/0",
            "recommendation": "Restrict SSH access to specific IP ranges",
        }
    ]


@pytest.fixture
def sample_access_analyzer_findings():
    """Provide sample Access Analyzer findings."""
    return [
        {
            "resource_id": "arn:aws:s3:::my-public-bucket",
            "resource_type": "AWS::S3::Bucket",
            "service": "S3",
            "severity": "MEDIUM",
            "finding": "External access detected",
            "recommendation": "Review resource policy",
        }
    ]


@pytest.fixture
def sample_cloudtrail_findings():
    """Provide sample CloudTrail findings."""
    return [
        {
            "resource_id": "single-region-trail",
            "resource_type": "CLOUDTRAIL_TRAIL",
            "service": "CloudTrail",
            "severity": "HIGH",
            "finding": "Trail is not multi-region",
            "recommendation": "Enable multi-region logging",
        }
    ]


class TestEndToEndWorkflow:
    """Test cases for the complete end-to-end workflow."""

    @patch("index.send_report_email")
    @patch("index.generate_narrative")
    @patch("index.generate_report")
    @patch("index.get_cloudtrail_findings")
    @patch("index.get_access_analyzer_findings")
    @patch("index.get_securityhub_findings")
    @patch("index.get_iam_findings")
    @patch("index.is_dry_run")
    def test_complete_workflow_success(
        self,
        mock_is_dry_run,
        mock_iam,
        mock_sh,
        mock_aa,
        mock_ct,
        mock_generate_report,
        mock_narrative,
        mock_email,
        mock_context,
        sample_iam_findings,
        sample_securityhub_findings,
        sample_access_analyzer_findings,
        sample_cloudtrail_findings,
    ):
        """Test the complete workflow with all modules succeeding."""
        # Setup mocks
        mock_is_dry_run.return_value = False
        mock_iam.return_value = sample_iam_findings
        mock_sh.return_value = sample_securityhub_findings
        mock_aa.return_value = sample_access_analyzer_findings
        mock_ct.return_value = sample_cloudtrail_findings
        mock_generate_report.return_value = (
            "reports/test.csv",
            "https://s3.amazonaws.com/bucket/reports/test.csv",
        )
        mock_narrative.return_value = "AI-generated executive summary"
        mock_email.return_value = "message-id-123"

        # Mock S3 client for fetching CSV
        mock_s3 = MagicMock()
        mock_s3.get_object.return_value = {
            "Body": MagicMock(read=MagicMock(return_value=b"csv,content"))
        }

        with patch("boto3.client", return_value=mock_s3):
            with patch.dict(
                os.environ,
                {"REPORT_BUCKET": "test-bucket", "RECIPIENT_EMAIL": "test@example.com"},
            ):
                event = {"format": "csv"}
                result = lambda_handler(event, mock_context)

        # Verify the result
        assert result["statusCode"] == 200
        assert result["body"]["message"] == "Access Review Completed"
        assert "finding_counts" in result["body"]
        assert result["body"]["finding_counts"]["CRITICAL"] == 1
        assert result["body"]["finding_counts"]["HIGH"] == 2
        assert result["body"]["finding_counts"]["MEDIUM"] == 1
        assert (
            result["body"]["report_url"]
            == "https://s3.amazonaws.com/bucket/reports/test.csv"
        )
        assert result["body"]["email_message_id"] == "message-id-123"

        # Verify all modules were called
        mock_iam.assert_called_once()
        mock_sh.assert_called_once()
        mock_aa.assert_called_once()
        mock_ct.assert_called_once()
        mock_generate_report.assert_called_once()
        mock_narrative.assert_called_once()
        mock_email.assert_called_once()

    @patch("index.send_report_email")
    @patch("index.generate_narrative")
    @patch("index.generate_report")
    @patch("index.get_cloudtrail_findings")
    @patch("index.get_access_analyzer_findings")
    @patch("index.get_securityhub_findings")
    @patch("index.get_iam_findings")
    @patch("index.is_dry_run")
    def test_complete_workflow_with_module_failure(
        self,
        mock_is_dry_run,
        mock_iam,
        mock_sh,
        mock_aa,
        mock_ct,
        mock_generate_report,
        mock_narrative,
        mock_email,
        mock_context,
        sample_iam_findings,
        sample_cloudtrail_findings,
    ):
        """Test the complete workflow when one module fails."""
        from botocore.exceptions import ClientError

        # Setup mocks
        mock_is_dry_run.return_value = False
        mock_iam.return_value = sample_iam_findings
        mock_sh.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied"}}, "GetFindings"
        )
        mock_aa.return_value = []
        mock_ct.return_value = sample_cloudtrail_findings
        mock_generate_report.return_value = (
            "reports/test.csv",
            "https://s3.amazonaws.com/bucket/reports/test.csv",
        )
        mock_narrative.return_value = "AI-generated executive summary"
        mock_email.return_value = "message-id-123"

        # Mock S3 client
        mock_s3 = MagicMock()
        mock_s3.get_object.return_value = {
            "Body": MagicMock(read=MagicMock(return_value=b"csv,content"))
        }

        with patch("boto3.client", return_value=mock_s3):
            with patch.dict(
                os.environ,
                {"REPORT_BUCKET": "test-bucket", "RECIPIENT_EMAIL": "test@example.com"},
            ):
                event = {"format": "csv"}
                result = lambda_handler(event, mock_context)

        # Verify the workflow continues despite the failure
        assert result["statusCode"] == 200
        assert result["body"]["message"] == "Access Review Completed"
        # Should have findings from successful modules
        assert result["body"]["finding_counts"]["CRITICAL"] == 1
        assert result["body"]["finding_counts"]["HIGH"] == 1

    @patch("index.handle_dry_run")
    @patch("index.is_dry_run")
    def test_complete_workflow_dry_run_mode(
        self, mock_is_dry_run, mock_handle_dry_run, mock_context
    ):
        """Test the complete workflow in dry-run mode."""
        mock_is_dry_run.return_value = True
        mock_handle_dry_run.return_value = {
            "statusCode": 200,
            "body": {
                "mode": "DRY_RUN",
                "message": "Access Review Completed (Dry Run)",
                "total_findings": 5,
                "report_path": "/path/to/report.csv",
                "narrative_summary": "Test narrative...",
            },
        }

        event = {"dry_run": True, "format": "csv"}
        result = lambda_handler(event, mock_context)

        # Verify dry-run mode was used
        assert result["statusCode"] == 200
        assert result["body"]["mode"] == "DRY_RUN"
        mock_handle_dry_run.assert_called_once_with(event)

    @patch("index.send_report_email")
    @patch("index.generate_narrative")
    @patch("index.generate_report")
    @patch("index.get_cloudtrail_findings")
    @patch("index.get_access_analyzer_findings")
    @patch("index.get_securityhub_findings")
    @patch("index.get_iam_findings")
    @patch("index.is_dry_run")
    def test_complete_workflow_xlsx_format(
        self,
        mock_is_dry_run,
        mock_iam,
        mock_sh,
        mock_aa,
        mock_ct,
        mock_generate_report,
        mock_narrative,
        mock_email,
        mock_context,
    ):
        """Test the complete workflow with XLSX format."""
        mock_is_dry_run.return_value = False
        mock_iam.return_value = []
        mock_sh.return_value = []
        mock_aa.return_value = []
        mock_ct.return_value = []
        mock_generate_report.return_value = (
            "reports/test.xlsx",
            "https://s3.amazonaws.com/bucket/reports/test.xlsx",
        )
        mock_narrative.return_value = "AI-generated executive summary"
        mock_email.return_value = "message-id-123"

        # Mock S3 client
        mock_s3 = MagicMock()
        mock_s3.get_object.return_value = {
            "Body": MagicMock(read=MagicMock(return_value=b"xlsx,content"))
        }

        with patch("boto3.client", return_value=mock_s3):
            with patch.dict(
                os.environ,
                {"REPORT_BUCKET": "test-bucket", "RECIPIENT_EMAIL": "test@example.com"},
            ):
                event = {"format": "xlsx"}
                result = lambda_handler(event, mock_context)

        # Verify XLSX format was used
        assert result["statusCode"] == 200
        assert result["body"]["report_url"].endswith(".xlsx")
        call_args = mock_generate_report.call_args
        assert call_args[1]["format_type"] == "xlsx"

    @patch("index.send_report_email")
    @patch("index.generate_narrative")
    @patch("index.generate_report")
    @patch("index.get_cloudtrail_findings")
    @patch("index.get_access_analyzer_findings")
    @patch("index.get_securityhub_findings")
    @patch("index.get_iam_findings")
    @patch("index.is_dry_run")
    def test_complete_workflow_no_email_configured(
        self,
        mock_is_dry_run,
        mock_iam,
        mock_sh,
        mock_aa,
        mock_ct,
        mock_generate_report,
        mock_narrative,
        mock_email,
        mock_context,
    ):
        """Test the complete workflow when email is not configured."""
        mock_is_dry_run.return_value = False
        mock_iam.return_value = []
        mock_sh.return_value = []
        mock_aa.return_value = []
        mock_ct.return_value = []
        mock_generate_report.return_value = (
            "reports/test.csv",
            "https://s3.amazonaws.com/bucket/reports/test.csv",
        )
        mock_narrative.return_value = "AI-generated executive summary"

        # Mock S3 client
        mock_s3 = MagicMock()
        mock_s3.get_object.return_value = {
            "Body": MagicMock(read=MagicMock(return_value=b"csv,content"))
        }

        with patch("boto3.client", return_value=mock_s3):
            with patch.dict(os.environ, {"REPORT_BUCKET": "test-bucket"}, clear=True):
                event = {"format": "csv"}
                result = lambda_handler(event, mock_context)

        # Verify workflow completes without email
        assert result["statusCode"] == 200
        assert result["body"]["email_message_id"] is None
        mock_email.assert_not_called()

    @patch("index.send_report_email")
    @patch("index.generate_narrative")
    @patch("index.generate_report")
    @patch("index.get_cloudtrail_findings")
    @patch("index.get_access_analyzer_findings")
    @patch("index.get_securityhub_findings")
    @patch("index.get_iam_findings")
    @patch("index.is_dry_run")
    def test_complete_workflow_with_many_findings(
        self,
        mock_is_dry_run,
        mock_iam,
        mock_sh,
        mock_aa,
        mock_ct,
        mock_generate_report,
        mock_narrative,
        mock_email,
        mock_context,
    ):
        """Test the complete workflow with many findings."""
        # Create many findings
        many_findings = [
            {
                "resource_id": f"resource-{i}",
                "resource_type": "AWS::S3::Bucket",
                "service": "S3",
                "severity": "LOW",
                "finding": f"Finding {i}",
                "recommendation": "Fix it",
            }
            for i in range(100)
        ]

        mock_is_dry_run.return_value = False
        mock_iam.return_value = many_findings[:25]
        mock_sh.return_value = many_findings[25:50]
        mock_aa.return_value = many_findings[50:75]
        mock_ct.return_value = many_findings[75:100]
        mock_generate_report.return_value = (
            "reports/test.csv",
            "https://s3.amazonaws.com/bucket/reports/test.csv",
        )
        mock_narrative.return_value = "AI-generated executive summary"
        mock_email.return_value = "message-id-123"

        # Mock S3 client
        mock_s3 = MagicMock()
        mock_s3.get_object.return_value = {
            "Body": MagicMock(read=MagicMock(return_value=b"csv,content"))
        }

        with patch("boto3.client", return_value=mock_s3):
            with patch.dict(
                os.environ,
                {"REPORT_BUCKET": "test-bucket", "RECIPIENT_EMAIL": "test@example.com"},
            ):
                event = {"format": "csv"}
                result = lambda_handler(event, mock_context)

        # Verify workflow handles many findings
        assert result["statusCode"] == 200
        assert result["body"]["finding_counts"]["LOW"] == 100

    @patch("index.send_report_email")
    @patch("index.generate_narrative")
    @patch("index.generate_report")
    @patch("index.get_cloudtrail_findings")
    @patch("index.get_access_analyzer_findings")
    @patch("index.get_securityhub_findings")
    @patch("index.get_iam_findings")
    @patch("index.is_dry_run")
    def test_complete_workflow_narrative_generation_fails(
        self,
        mock_is_dry_run,
        mock_iam,
        mock_sh,
        mock_aa,
        mock_ct,
        mock_generate_report,
        mock_narrative,
        mock_email,
        mock_context,
    ):
        """Test the complete workflow when narrative generation fails."""
        mock_is_dry_run.return_value = False
        mock_iam.return_value = []
        mock_sh.return_value = []
        mock_aa.return_value = []
        mock_ct.return_value = []
        mock_generate_report.return_value = (
            "reports/test.csv",
            "https://s3.amazonaws.com/bucket/reports/test.csv",
        )
        mock_narrative.side_effect = Exception("Bedrock error")
        mock_email.return_value = "message-id-123"

        # Mock S3 client
        mock_s3 = MagicMock()
        mock_s3.get_object.return_value = {
            "Body": MagicMock(read=MagicMock(return_value=b"csv,content"))
        }

        with patch("boto3.client", return_value=mock_s3):
            with patch.dict(
                os.environ,
                {"REPORT_BUCKET": "test-bucket", "RECIPIENT_EMAIL": "test@example.com"},
            ):
                event = {"format": "csv"}

                # Should not raise an exception
                result = lambda_handler(event, mock_context)

        # Verify workflow handles narrative generation failure
        assert result["statusCode"] == 200
        # Email should still be sent with fallback narrative
        mock_email.assert_called_once()

    @patch("index.send_report_email")
    @patch("index.generate_narrative")
    @patch("index.generate_report")
    @patch("index.get_cloudtrail_findings")
    @patch("index.get_access_analyzer_findings")
    @patch("index.get_securityhub_findings")
    @patch("index.get_iam_findings")
    @patch("index.is_dry_run")
    def test_complete_workflow_report_generation_fails(
        self,
        mock_is_dry_run,
        mock_iam,
        mock_sh,
        mock_aa,
        mock_ct,
        mock_generate_report,
        mock_narrative,
        mock_email,
        mock_context,
    ):
        """Test the complete workflow when report generation fails."""
        mock_is_dry_run.return_value = False
        mock_iam.return_value = []
        mock_sh.return_value = []
        mock_aa.return_value = []
        mock_ct.return_value = []
        mock_generate_report.return_value = (None, None)
        mock_narrative.return_value = "AI-generated executive summary"

        # Mock S3 client
        mock_s3 = MagicMock()

        with patch("boto3.client", return_value=mock_s3):
            with patch.dict(
                os.environ,
                {"REPORT_BUCKET": "test-bucket", "RECIPIENT_EMAIL": "test@example.com"},
            ):
                event = {"format": "csv"}

                # Should not raise an exception
                result = lambda_handler(event, mock_context)

        # Verify workflow handles report generation failure
        assert result["statusCode"] == 200
        # Email should not be sent if report generation fails
        mock_email.assert_not_called()
