"""
Unit tests for the main Lambda handler.

Tests the lambda_handler, is_dry_run, and handle_dry_run functions
in src/lambda/index.py
"""

import os
import pytest
from unittest.mock import Mock, patch, MagicMock
from botocore.exceptions import ClientError, BotoCoreError

# Add the src/lambda directory to the path so we can import the modules
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src/lambda"))

from index import lambda_handler, is_dry_run, handle_dry_run


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
def sample_findings():
    """Provide sample findings for testing."""
    return [
        {
            "resource_id": "test-resource-1",
            "resource_type": "IAM_USER",
            "service": "IAM",
            "severity": "CRITICAL",
            "finding": "Test critical finding",
            "recommendation": "Fix this issue",
        },
        {
            "resource_id": "test-resource-2",
            "resource_type": "S3_BUCKET",
            "service": "S3",
            "severity": "HIGH",
            "finding": "Test high finding",
            "recommendation": "Fix this issue too",
        },
    ]


class TestIsDryRun:
    """Test cases for the is_dry_run function."""

    def test_is_dry_run_with_env_variable_true(self):
        """Test dry-run detection when environment variable is set to true."""
        with patch.dict(os.environ, {"DRY_RUN": "true"}):
            assert is_dry_run({}) is True

    def test_is_dry_run_with_env_variable_true_uppercase(self):
        """Test dry-run detection with uppercase environment variable."""
        with patch.dict(os.environ, {"DRY_RUN": "TRUE"}):
            assert is_dry_run({}) is True

    def test_is_dry_run_with_env_variable_false(self):
        """Test dry-run detection when environment variable is set to false."""
        with patch.dict(os.environ, {"DRY_RUN": "false"}, clear=True):
            assert is_dry_run({}) is False

    def test_is_dry_run_with_env_variable_not_set(self):
        """Test dry-run detection when environment variable is not set."""
        with patch.dict(os.environ, {}, clear=True):
            assert is_dry_run({}) is False

    def test_is_dry_run_with_event_parameter_true(self):
        """Test dry-run detection when event parameter is true."""
        with patch.dict(os.environ, {}, clear=True):
            assert is_dry_run({"dry_run": True}) is True

    def test_is_dry_run_with_event_parameter_camel_case(self):
        """Test dry-run detection with camelCase event parameter."""
        with patch.dict(os.environ, {}, clear=True):
            assert is_dry_run({"dryRun": True}) is True

    def test_is_dry_run_with_event_parameter_false(self):
        """Test dry-run detection when event parameter is false."""
        with patch.dict(os.environ, {}, clear=True):
            assert is_dry_run({"dry_run": False}) is False

    def test_is_dry_run_with_no_parameters(self):
        """Test dry-run detection with no parameters set."""
        with patch.dict(os.environ, {}, clear=True):
            assert is_dry_run({}) is False

    def test_is_dry_run_with_none_event(self):
        """Test dry-run detection with None event."""
        with patch.dict(os.environ, {}, clear=True):
            assert is_dry_run(None) is False


class TestHandleDryRun:
    """Test cases for the handle_dry_run function."""

    @patch("index.generate_report")
    @patch("index.get_mock_narrative")
    @patch("index.get_dry_run_summary")
    @patch("index.get_all_mock_findings")
    def test_handle_dry_run_success(
        self,
        mock_get_findings,
        mock_get_summary,
        mock_get_narrative,
        mock_generate_report,
    ):
        """Test successful dry-run execution."""
        # Setup mocks
        mock_get_findings.return_value = [
            {"severity": "CRITICAL", "finding": "Test finding", "resource_id": "test"}
        ]
        mock_get_summary.return_value = {
            "timestamp": "2024-01-01T00:00:00",
            "source": "Dry Run",
            "description": "Test description",
            "severity_breakdown": {"CRITICAL": 1, "HIGH": 0, "MEDIUM": 0, "LOW": 0},
            "total_findings": 1,
        }
        mock_get_narrative.return_value = "Test narrative summary"
        mock_generate_report.return_value = (
            "/path/to/report.csv",
            "file:///path/to/report.csv",
        )

        event = {"format": "csv"}
        result = handle_dry_run(event)

        assert result["statusCode"] == 200
        assert result["body"]["mode"] == "DRY_RUN"
        assert "DRY RUN MODE" in result["body"]["message"]
        assert result["body"]["total_findings"] == 1
        assert result["body"]["report_path"] == "/path/to/report.csv"
        assert "narrative_summary" in result["body"]

    @patch("index.generate_report")
    @patch("index.get_mock_narrative")
    @patch("index.get_dry_run_summary")
    @patch("index.get_all_mock_findings")
    def test_handle_dry_run_xlsx_format(
        self,
        mock_get_findings,
        mock_get_summary,
        mock_get_narrative,
        mock_generate_report,
    ):
        """Test dry-run with XLSX format."""
        mock_get_findings.return_value = []
        mock_get_summary.return_value = {
            "timestamp": "2024-01-01T00:00:00",
            "source": "Dry Run",
            "description": "Test",
            "severity_breakdown": {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0},
            "total_findings": 0,
        }
        mock_get_narrative.return_value = "Test narrative"
        mock_generate_report.return_value = (
            "/path/to/report.xlsx",
            "file:///path/to/report.xlsx",
        )

        event = {"format": "xlsx"}
        result = handle_dry_run(event)

        assert result["statusCode"] == 200
        assert result["body"]["report_path"].endswith(".xlsx")

    @patch("index.generate_report")
    @patch("index.get_mock_narrative")
    @patch("index.get_dry_run_summary")
    @patch("index.get_all_mock_findings")
    def test_handle_dry_run_invalid_format_defaults_to_csv(
        self,
        mock_get_findings,
        mock_get_summary,
        mock_get_narrative,
        mock_generate_report,
    ):
        """Test dry-run with invalid format defaults to CSV."""
        mock_get_findings.return_value = []
        mock_get_summary.return_value = {
            "timestamp": "2024-01-01T00:00:00",
            "source": "Dry Run",
            "description": "Test",
            "severity_breakdown": {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0},
            "total_findings": 0,
        }
        mock_get_narrative.return_value = "Test narrative"
        mock_generate_report.return_value = (
            "/path/to/report.csv",
            "file:///path/to/report.csv",
        )

        event = {"format": "invalid"}
        result = handle_dry_run(event)

        assert result["statusCode"] == 200
        assert result["body"]["report_path"].endswith(".csv")

    @patch("index.generate_report")
    @patch("index.get_mock_narrative")
    @patch("index.get_dry_run_summary")
    @patch("index.get_all_mock_findings")
    def test_handle_dry_run_long_narrative_truncated(
        self,
        mock_get_findings,
        mock_get_summary,
        mock_get_narrative,
        mock_generate_report,
    ):
        """Test that long narratives are truncated in the response."""
        mock_get_findings.return_value = []
        mock_get_summary.return_value = {
            "timestamp": "2024-01-01T00:00:00",
            "source": "Dry Run",
            "description": "Test",
            "severity_breakdown": {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0},
            "total_findings": 0,
        }
        # Create a narrative longer than 500 characters
        long_narrative = "A" * 600
        mock_get_narrative.return_value = long_narrative
        mock_generate_report.return_value = (
            "/path/to/report.csv",
            "file:///path/to/report.csv",
        )

        event = {}
        result = handle_dry_run(event)

        assert len(result["body"]["narrative_summary"]) == 503  # 500 + '...'
        assert result["body"]["narrative_summary"].endswith("...")


class TestLambdaHandler:
    """Test cases for the lambda_handler function."""

    @patch("index.send_report_email")
    @patch("index.generate_narrative")
    @patch("index.generate_report")
    @patch("index.get_cloudtrail_findings")
    @patch("index.get_access_analyzer_findings")
    @patch("index.get_securityhub_findings")
    @patch("index.get_iam_findings")
    @patch("index.is_dry_run")
    def test_lambda_handler_normal_mode(
        self,
        mock_is_dry_run,
        mock_iam,
        mock_sh,
        mock_aa,
        mock_ct,
        mock_generate_report,
        mock_narrative,
        mock_email,
    ):
        """Test lambda handler in normal (non-dry-run) mode."""
        # Setup mocks
        mock_is_dry_run.return_value = False
        mock_iam.return_value = [
            {
                "severity": "CRITICAL",
                "finding": "IAM finding",
                "resource_id": "user1",
                "resource_type": "IAM_USER",
                "service": "IAM",
                "recommendation": "Fix",
            }
        ]
        mock_sh.return_value = []
        mock_aa.return_value = []
        mock_ct.return_value = []
        mock_generate_report.return_value = (
            "reports/test.csv",
            "https://s3.amazonaws.com/bucket/reports/test.csv",
        )
        mock_narrative.return_value = "AI-generated narrative"
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
                context = Mock()
                context.request_id = "test-request-id"

                result = lambda_handler(event, context)

        assert result["statusCode"] == 200
        assert result["body"]["message"] == "Access Review Completed"
        assert "finding_counts" in result["body"]
        assert result["body"]["email_message_id"] == "message-id-123"

    @patch("index.handle_dry_run")
    @patch("index.is_dry_run")
    def test_lambda_handler_dry_run_mode(self, mock_is_dry_run, mock_handle_dry_run):
        """Test lambda handler in dry-run mode."""
        mock_is_dry_run.return_value = True
        mock_handle_dry_run.return_value = {
            "statusCode": 200,
            "body": {"mode": "DRY_RUN", "message": "Dry run complete"},
        }

        event = {"dry_run": True}
        context = Mock()
        context.request_id = "test-request-id"

        result = lambda_handler(event, context)

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
    def test_lambda_handler_with_client_error(
        self,
        mock_is_dry_run,
        mock_iam,
        mock_sh,
        mock_aa,
        mock_ct,
        mock_generate_report,
        mock_narrative,
        mock_email,
    ):
        """Test lambda handler handles ClientError from modules."""
        mock_is_dry_run.return_value = False
        mock_iam.return_value = [
            {
                "severity": "CRITICAL",
                "finding": "IAM finding",
                "resource_id": "user1",
                "resource_type": "IAM_USER",
                "service": "IAM",
                "recommendation": "Fix",
            }
        ]
        mock_sh.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied"}}, "GetFindings"
        )
        mock_aa.return_value = []
        mock_ct.return_value = []
        mock_generate_report.return_value = (
            "reports/test.csv",
            "https://s3.amazonaws.com/bucket/reports/test.csv",
        )
        mock_narrative.return_value = "AI-generated narrative"
        mock_email.return_value = "message-id-123"

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
                context = Mock()
                context.request_id = "test-request-id"

                result = lambda_handler(event, context)

        assert result["statusCode"] == 200
        # Should still complete with findings from successful modules
        assert result["body"]["finding_counts"]["CRITICAL"] == 1

    @patch("index.send_report_email")
    @patch("index.generate_narrative")
    @patch("index.generate_report")
    @patch("index.get_cloudtrail_findings")
    @patch("index.get_access_analyzer_findings")
    @patch("index.get_securityhub_findings")
    @patch("index.get_iam_findings")
    @patch("index.is_dry_run")
    def test_lambda_handler_with_generic_exception(
        self,
        mock_is_dry_run,
        mock_iam,
        mock_sh,
        mock_aa,
        mock_ct,
        mock_generate_report,
        mock_narrative,
        mock_email,
    ):
        """Test lambda handler handles generic exceptions from modules."""
        mock_is_dry_run.return_value = False
        mock_iam.return_value = []
        mock_sh.return_value = []
        mock_aa.side_effect = Exception("Unexpected error")
        mock_ct.return_value = []
        mock_generate_report.return_value = (
            "reports/test.csv",
            "https://s3.amazonaws.com/bucket/reports/test.csv",
        )
        mock_narrative.return_value = "AI-generated narrative"
        mock_email.return_value = "message-id-123"

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
                context = Mock()
                context.request_id = "test-request-id"

                result = lambda_handler(event, context)

        assert result["statusCode"] == 200
        # Should continue despite the exception in one module

    @patch("index.send_report_email")
    @patch("index.generate_narrative")
    @patch("index.generate_report")
    @patch("index.get_cloudtrail_findings")
    @patch("index.get_access_analyzer_findings")
    @patch("index.get_securityhub_findings")
    @patch("index.get_iam_findings")
    @patch("index.is_dry_run")
    def test_lambda_handler_no_recipient_email(
        self,
        mock_is_dry_run,
        mock_iam,
        mock_sh,
        mock_aa,
        mock_ct,
        mock_generate_report,
        mock_narrative,
        mock_email,
    ):
        """Test lambda handler when recipient email is not configured."""
        mock_is_dry_run.return_value = False
        mock_iam.return_value = []
        mock_sh.return_value = []
        mock_aa.return_value = []
        mock_ct.return_value = []
        mock_generate_report.return_value = (
            "reports/test.csv",
            "https://s3.amazonaws.com/bucket/reports/test.csv",
        )
        mock_narrative.return_value = "AI-generated narrative"

        mock_s3 = MagicMock()
        mock_s3.get_object.return_value = {
            "Body": MagicMock(read=MagicMock(return_value=b"csv,content"))
        }

        with patch("boto3.client", return_value=mock_s3):
            with patch.dict(os.environ, {"REPORT_BUCKET": "test-bucket"}, clear=True):
                event = {"format": "csv"}
                context = Mock()
                context.request_id = "test-request-id"

                result = lambda_handler(event, context)

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
    def test_lambda_handler_severity_counts(
        self,
        mock_is_dry_run,
        mock_iam,
        mock_sh,
        mock_aa,
        mock_ct,
        mock_generate_report,
        mock_narrative,
        mock_email,
    ):
        """Test that severity counts are correctly calculated."""
        mock_is_dry_run.return_value = False
        mock_iam.return_value = [
            {
                "severity": "CRITICAL",
                "finding": "IAM finding",
                "resource_id": "user1",
                "resource_type": "IAM_USER",
                "service": "IAM",
                "recommendation": "Fix",
            },
            {
                "severity": "HIGH",
                "finding": "IAM finding 2",
                "resource_id": "user2",
                "resource_type": "IAM_USER",
                "service": "IAM",
                "recommendation": "Fix",
            },
        ]
        mock_sh.return_value = [
            {
                "severity": "HIGH",
                "finding": "SH finding",
                "resource_id": "resource1",
                "resource_type": "AWS::S3::Bucket",
                "service": "S3",
                "recommendation": "Fix",
            }
        ]
        mock_aa.return_value = [
            {
                "severity": "MEDIUM",
                "finding": "AA finding",
                "resource_id": "resource2",
                "resource_type": "AWS::IAM::Role",
                "service": "IAM",
                "recommendation": "Fix",
            }
        ]
        mock_ct.return_value = [
            {
                "severity": "LOW",
                "finding": "CT finding",
                "resource_id": "trail1",
                "resource_type": "CLOUDTRAIL_TRAIL",
                "service": "CloudTrail",
                "recommendation": "Fix",
            }
        ]
        mock_generate_report.return_value = (
            "reports/test.csv",
            "https://s3.amazonaws.com/bucket/reports/test.csv",
        )
        mock_narrative.return_value = "AI-generated narrative"
        mock_email.return_value = "message-id-123"

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
                context = Mock()
                context.request_id = "test-request-id"

                result = lambda_handler(event, context)

        assert result["statusCode"] == 200
        assert result["body"]["finding_counts"]["CRITICAL"] == 1
        assert result["body"]["finding_counts"]["HIGH"] == 2
        assert result["body"]["finding_counts"]["MEDIUM"] == 1
        assert result["body"]["finding_counts"]["LOW"] == 1

    @patch("index.send_report_email")
    @patch("index.generate_narrative")
    @patch("index.generate_report")
    @patch("index.get_cloudtrail_findings")
    @patch("index.get_access_analyzer_findings")
    @patch("index.get_securityhub_findings")
    @patch("index.get_iam_findings")
    @patch("index.is_dry_run")
    def test_lambda_handler_xlsx_format(
        self,
        mock_is_dry_run,
        mock_iam,
        mock_sh,
        mock_aa,
        mock_ct,
        mock_generate_report,
        mock_narrative,
        mock_email,
    ):
        """Test lambda handler with XLSX format."""
        mock_is_dry_run.return_value = False
        mock_iam.return_value = []
        mock_sh.return_value = []
        mock_aa.return_value = []
        mock_ct.return_value = []
        mock_generate_report.return_value = (
            "reports/test.xlsx",
            "https://s3.amazonaws.com/bucket/reports/test.xlsx",
        )
        mock_narrative.return_value = "AI-generated narrative"
        mock_email.return_value = "message-id-123"

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
                context = Mock()
                context.request_id = "test-request-id"

                result = lambda_handler(event, context)

        assert result["statusCode"] == 200
        mock_generate_report.assert_called_once()
        call_args = mock_generate_report.call_args
        assert call_args[1]["format_type"] == "xlsx"
