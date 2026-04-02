"""
Unit tests for reporting module.

Tests the generate_report function and helper functions in src/lambda/modules/reporting.py
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, mock_open
import os
import csv
from io import StringIO

# Add the src/lambda directory to the path so we can import the modules
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src/lambda"))

from modules.reporting import (
    generate_report,
    _generate_local_report,
    _save_csv_locally,
    _generate_csv_report,
    HAS_OPENPYXL,
)


@pytest.fixture
def sample_findings():
    """Provide sample findings for testing."""
    return [
        {
            "resource_id": "user-without-mfa",
            "resource_type": "IAM_USER",
            "service": "IAM",
            "severity": "CRITICAL",
            "finding": "User is missing MFA",
            "recommendation": "Enable MFA for this user",
        },
        {
            "resource_id": "sg-12345678",
            "resource_type": "AWS::Ec2SecurityGroup",
            "service": "EC2",
            "severity": "HIGH",
            "finding": "Security group allows SSH from 0.0.0.0/0",
            "recommendation": "Restrict SSH access to specific IP ranges",
        },
        {
            "resource_id": "arn:aws:s3:::my-bucket",
            "resource_type": "AWS::S3::Bucket",
            "service": "S3",
            "severity": "MEDIUM",
            "finding": "S3 bucket lacks encryption",
            "recommendation": "Enable default encryption",
        },
    ]


@pytest.fixture
def mock_s3_client():
    """Create a mock S3 client."""
    client = Mock()
    return client


class TestGenerateReport:
    """Test cases for generate_report function."""

    @patch("modules.reporting._generate_local_report")
    def test_generate_report_local_mode(self, mock_generate_local, sample_findings):
        """Test report generation in local mode."""
        mock_generate_local.return_value = (
            "/path/to/report.csv",
            "/path/to/report.csv",
        )

        s3_key, url = generate_report(
            sample_findings, format_type="csv", local_mode=True
        )

        assert s3_key == "/path/to/report.csv"
        assert url == "/path/to/report.csv"
        mock_generate_local.assert_called_once_with(sample_findings, "csv")

    @patch("modules.reporting._generate_csv_report")
    @patch.dict(os.environ, {"REPORT_BUCKET": "test-bucket"})
    def test_generate_report_csv_s3_mode(self, mock_generate_csv, sample_findings):
        """Test CSV report generation in S3 mode."""
        mock_generate_csv.return_value = (
            "reports/test.csv",
            "https://s3.amazonaws.com/test-bucket/reports/test.csv",
        )

        s3_key, url = generate_report(
            sample_findings, format_type="csv", local_mode=False
        )

        assert s3_key == "reports/test.csv"
        assert url == "https://s3.amazonaws.com/test-bucket/reports/test.csv"
        mock_generate_csv.assert_called_once()

    @patch("modules.reporting._generate_xlsx_report")
    @patch.dict(os.environ, {"REPORT_BUCKET": "test-bucket"})
    def test_generate_report_xlsx_s3_mode(self, mock_generate_xlsx, sample_findings):
        """Test XLSX report generation in S3 mode."""
        if not HAS_OPENPYXL:
            pytest.skip("openpyxl not installed")

        mock_generate_xlsx.return_value = (
            "reports/test.xlsx",
            "https://s3.amazonaws.com/test-bucket/reports/test.xlsx",
        )

        s3_key, url = generate_report(
            sample_findings, format_type="xlsx", local_mode=False
        )

        assert s3_key == "reports/test.xlsx"
        assert url == "https://s3.amazonaws.com/test-bucket/reports/test.xlsx"
        mock_generate_xlsx.assert_called_once()

    @patch("modules.reporting._generate_local_report")
    @patch.dict(os.environ, {}, clear=True)
    def test_generate_report_no_bucket_uses_local(
        self, mock_generate_local, sample_findings
    ):
        """Test that report generation uses local mode when no bucket is configured."""
        mock_generate_local.return_value = (
            "/path/to/report.csv",
            "/path/to/report.csv",
        )

        s3_key, url = generate_report(
            sample_findings, format_type="csv", local_mode=False
        )

        assert s3_key == "/path/to/report.csv"
        assert url == "/path/to/report.csv"
        mock_generate_local.assert_called_once()

    @patch("modules.reporting._generate_csv_report")
    @patch.dict(os.environ, {"REPORT_BUCKET": "test-bucket"})
    def test_generate_report_invalid_format_defaults_to_csv(
        self, mock_generate_csv, sample_findings
    ):
        """Test that invalid format defaults to CSV."""
        mock_generate_csv.return_value = (
            "reports/test.csv",
            "https://s3.amazonaws.com/test-bucket/reports/test.csv",
        )

        s3_key, url = generate_report(
            sample_findings, format_type="invalid", local_mode=False
        )

        assert s3_key == "reports/test.csv"
        mock_generate_csv.assert_called_once()


class TestGenerateLocalReport:
    """Test cases for _generate_local_report function."""

    @patch("modules.reporting._save_csv_locally")
    @patch("os.makedirs")
    def test_generate_local_report_csv(
        self, mock_makedirs, mock_save_csv, sample_findings
    ):
        """Test local CSV report generation."""
        mock_save_csv.return_value = ("/path/to/report.csv", "/path/to/report.csv")

        filepath, url = _generate_local_report(sample_findings, "csv")

        assert filepath == "/path/to/report.csv"
        assert url == "/path/to/report.csv"
        mock_makedirs.assert_called_once()
        mock_save_csv.assert_called_once()

    @patch("modules.reporting._save_xlsx_locally")
    @patch("os.makedirs")
    def test_generate_local_report_xlsx(
        self, mock_makedirs, mock_save_xlsx, sample_findings
    ):
        """Test local XLSX report generation."""
        if not HAS_OPENPYXL:
            pytest.skip("openpyxl not installed")

        mock_save_xlsx.return_value = ("/path/to/report.xlsx", "/path/to/report.xlsx")

        filepath, url = _generate_local_report(sample_findings, "xlsx")

        assert filepath == "/path/to/report.xlsx"
        assert url == "/path/to/report.xlsx"
        mock_makedirs.assert_called_once()
        mock_save_xlsx.assert_called_once()


class TestSaveCsvLocally:
    """Test cases for _save_csv_locally function."""

    @patch("builtins.open", new_callable=mock_open)
    @patch("os.makedirs")
    def test_save_csv_locally_success(self, mock_makedirs, mock_file, sample_findings):
        """Test successful local CSV save."""
        filepath, url = _save_csv_locally(
            sample_findings, "/reports", "2024-01-01_12-00-00", "2024-01-01T12:00:00"
        )

        assert filepath.endswith(".csv")
        assert url == filepath
        mock_file.assert_called_once()

        # Verify CSV content
        handle = mock_file()
        written_content = "".join(call[0][0] for call in handle.write.call_args_list)

        # Check that headers are present
        assert "Timestamp" in written_content
        assert "ResourceID" in written_content
        assert "ResourceType" in written_content
        assert "Service" in written_content
        assert "Severity" in written_content
        assert "Finding" in written_content
        assert "Recommendation" in written_content

    @patch("builtins.open", new_callable=mock_open)
    @patch("os.makedirs")
    def test_save_csv_locally_with_missing_fields(self, mock_makedirs, mock_file):
        """Test CSV save with findings missing some fields."""
        incomplete_findings = [
            {
                "resource_id": "resource1",
                # Missing other fields
            }
        ]

        filepath, url = _save_csv_locally(
            incomplete_findings,
            "/reports",
            "2024-01-01_12-00-00",
            "2024-01-01T12:00:00",
        )

        assert filepath.endswith(".csv")
        mock_file.assert_called_once()


class TestGenerateCsvReport:
    """Test cases for _generate_csv_report function."""

    @patch("modules.reporting.boto3.client")
    @patch.dict(os.environ, {"REPORT_BUCKET": "test-bucket"})
    def test_generate_csv_report_success(self, mock_boto3_client, sample_findings):
        """Test successful CSV report generation and S3 upload."""
        mock_s3 = Mock()
        mock_s3.generate_presigned_url.return_value = (
            "https://s3.amazonaws.com/test-bucket/reports/test.csv?signature=xxx"
        )
        mock_boto3_client.return_value = mock_s3

        s3_key, url = _generate_csv_report(
            sample_findings, "test-bucket", "2024-01-01", "2024-01-01T12:00:00"
        )

        assert s3_key == "reports/2024-01-01/access-review-report.csv"
        assert url.startswith("https://s3.amazonaws.com/test-bucket/")
        assert "signature" in url

        # Verify S3 put_object was called
        mock_s3.put_object.assert_called_once()
        call_args = mock_s3.put_object.call_args
        assert call_args[1]["Bucket"] == "test-bucket"
        assert call_args[1]["Key"] == s3_key
        assert call_args[1]["ContentType"] == "text/csv"

        # Verify presigned URL was generated
        mock_s3.generate_presigned_url.assert_called_once()
        call_args = mock_s3.generate_presigned_url.call_args
        assert call_args[1]["Params"]["Bucket"] == "test-bucket"
        assert call_args[1]["Params"]["Key"] == s3_key
        assert call_args[1]["ExpiresIn"] == 604800  # 7 days

    @patch("modules.reporting.boto3.client")
    @patch.dict(os.environ, {"REPORT_BUCKET": "test-bucket"})
    def test_generate_csv_report_s3_error(self, mock_boto3_client, sample_findings):
        """Test CSV report generation with S3 error."""
        mock_s3 = Mock()
        mock_s3.put_object.side_effect = Exception("S3 error")
        mock_boto3_client.return_value = mock_s3

        s3_key, url = _generate_csv_report(
            sample_findings, "test-bucket", "2024-01-01", "2024-01-01T12:00:00"
        )

        # Should return None on error
        assert s3_key is None
        assert url is None

    @patch("modules.reporting.boto3.client")
    @patch.dict(os.environ, {"REPORT_BUCKET": "test-bucket"})
    def test_csv_content_structure(self, mock_boto3_client, sample_findings):
        """Test that CSV content has correct structure."""
        mock_s3 = Mock()
        mock_s3.generate_presigned_url.return_value = (
            "https://s3.amazonaws.com/test-bucket/reports/test.csv"
        )
        mock_boto3_client.return_value = mock_s3

        s3_key, url = _generate_csv_report(
            sample_findings, "test-bucket", "2024-01-01", "2024-01-01T12:00:00"
        )

        # Get the CSV content that was uploaded
        call_args = mock_s3.put_object.call_args
        csv_content = call_args[1]["Body"]

        # Parse and verify CSV structure
        csv_reader = csv.DictReader(StringIO(csv_content))
        rows = list(csv_reader)

        assert len(rows) == len(sample_findings)

        # Check first row
        assert rows[0]["ResourceID"] == "user-without-mfa"
        assert rows[0]["ResourceType"] == "IAM_USER"
        assert rows[0]["Service"] == "IAM"
        assert rows[0]["Severity"] == "CRITICAL"
        assert rows[0]["Finding"] == "User is missing MFA"
        assert rows[0]["Recommendation"] == "Enable MFA for this user"


class TestGenerateXlsxReport:
    """Test cases for _generate_xlsx_report function."""

    @patch("modules.reporting.boto3.client")
    @patch.dict(os.environ, {"REPORT_BUCKET": "test-bucket"})
    def test_generate_xlsx_report_success(self, mock_boto3_client, sample_findings):
        """Test successful XLSX report generation and S3 upload."""
        if not HAS_OPENPYXL:
            pytest.skip("openpyxl not installed")

        mock_s3 = Mock()
        mock_s3.generate_presigned_url.return_value = (
            "https://s3.amazonaws.com/test-bucket/reports/test.xlsx?signature=xxx"
        )
        mock_boto3_client.return_value = mock_s3

        s3_key, url = _generate_xlsx_report(
            sample_findings, "test-bucket", "2024-01-01", "2024-01-01T12:00:00"
        )

        assert s3_key == "reports/2024-01-01/access-review-report.xlsx"
        assert url.startswith("https://s3.amazonaws.com/test-bucket/")

        # Verify S3 put_object was called
        mock_s3.put_object.assert_called_once()
        call_args = mock_s3.put_object.call_args
        assert call_args[1]["Bucket"] == "test-bucket"
        assert call_args[1]["Key"] == s3_key
        assert (
            call_args[1]["ContentType"]
            == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    @patch("modules.reporting.boto3.client")
    @patch.dict(os.environ, {"REPORT_BUCKET": "test-bucket"})
    def test_generate_xlsx_report_s3_error(self, mock_boto3_client, sample_findings):
        """Test XLSX report generation with S3 error."""
        if not HAS_OPENPYXL:
            pytest.skip("openpyxl not installed")

        mock_s3 = Mock()
        mock_s3.put_object.side_effect = Exception("S3 error")
        mock_boto3_client.return_value = mock_s3

        s3_key, url = _generate_xlsx_report(
            sample_findings, "test-bucket", "2024-01-01", "2024-01-01T12:00:00"
        )

        # Should return None on error
        assert s3_key is None
        assert url is None


class TestReportContent:
    """Test cases for report content generation."""

    @patch("modules.reporting.boto3.client")
    @patch.dict(os.environ, {"REPORT_BUCKET": "test-bucket"})
    def test_csv_handles_empty_findings(self, mock_boto3_client):
        """Test CSV generation with empty findings list."""
        mock_s3 = Mock()
        mock_s3.generate_presigned_url.return_value = (
            "https://s3.amazonaws.com/test-bucket/reports/test.csv"
        )
        mock_boto3_client.return_value = mock_s3

        s3_key, url = _generate_csv_report(
            [], "test-bucket", "2024-01-01", "2024-01-01T12:00:00"
        )

        assert s3_key is not None
        assert url is not None

        # Get the CSV content
        call_args = mock_s3.put_object.call_args
        csv_content = call_args[1]["Body"]

        # Parse and verify CSV structure
        csv_reader = csv.DictReader(StringIO(csv_content))
        rows = list(csv_reader)

        # Should have header but no data rows
        assert len(rows) == 0

    @patch("modules.reporting.boto3.client")
    @patch.dict(os.environ, {"REPORT_BUCKET": "test-bucket"})
    def test_csv_handles_missing_fields(self, mock_boto3_client):
        """Test CSV generation with findings missing fields."""
        incomplete_findings = [
            {
                "resource_id": "resource1",
                # Missing other fields
            }
        ]

        mock_s3 = Mock()
        mock_s3.generate_presigned_url.return_value = (
            "https://s3.amazonaws.com/test-bucket/reports/test.csv"
        )
        mock_boto3_client.return_value = mock_s3

        s3_key, url = _generate_csv_report(
            incomplete_findings, "test-bucket", "2024-01-01", "2024-01-01T12:00:00"
        )

        assert s3_key is not None
        assert url is not None

    @patch("modules.reporting.boto3.client")
    @patch.dict(os.environ, {"REPORT_BUCKET": "test-bucket"})
    def test_csv_includes_timestamp(self, mock_boto3_client, sample_findings):
        """Test that CSV includes timestamp."""
        mock_s3 = Mock()
        mock_s3.generate_presigned_url.return_value = (
            "https://s3.amazonaws.com/test-bucket/reports/test.csv"
        )
        mock_boto3_client.return_value = mock_s3

        test_timestamp = "2024-01-01T12:00:00"
        s3_key, url = _generate_csv_report(
            sample_findings, "test-bucket", "2024-01-01", test_timestamp
        )

        # Get the CSV content
        call_args = mock_s3.put_object.call_args
        csv_content = call_args[1]["Body"]

        # Parse and verify CSV structure
        csv_reader = csv.DictReader(StringIO(csv_content))
        rows = list(csv_reader)

        # All rows should have the timestamp
        for row in rows:
            assert row["Timestamp"] == test_timestamp


class TestPresignedUrl:
    """Test cases for presigned URL generation."""

    @patch("modules.reporting.boto3.client")
    @patch.dict(os.environ, {"REPORT_BUCKET": "test-bucket"})
    def test_presigned_url_expiration(self, mock_boto3_client, sample_findings):
        """Test that presigned URL has correct expiration."""
        mock_s3 = Mock()
        mock_s3.generate_presigned_url.return_value = (
            "https://s3.amazonaws.com/test-bucket/reports/test.csv?signature=xxx"
        )
        mock_boto3_client.return_value = mock_s3

        s3_key, url = _generate_csv_report(
            sample_findings, "test-bucket", "2024-01-01", "2024-01-01T12:00:00"
        )

        # Verify presigned URL was called with correct expiration
        mock_s3.generate_presigned_url.assert_called_once()
        call_args = mock_s3.generate_presigned_url.call_args
        assert call_args[1]["ExpiresIn"] == 604800  # 7 days in seconds

    @patch("modules.reporting.boto3.client")
    @patch.dict(os.environ, {"REPORT_BUCKET": "test-bucket"})
    def test_presigned_url_parameters(self, mock_boto3_client, sample_findings):
        """Test that presigned URL has correct parameters."""
        mock_s3 = Mock()
        mock_s3.generate_presigned_url.return_value = (
            "https://s3.amazonaws.com/test-bucket/reports/test.csv?signature=xxx"
        )
        mock_boto3_client.return_value = mock_s3

        s3_key, url = _generate_csv_report(
            sample_findings, "test-bucket", "2024-01-01", "2024-01-01T12:00:00"
        )

        # Verify presigned URL parameters
        mock_s3.generate_presigned_url.assert_called_once()
        call_args = mock_s3.generate_presigned_url.call_args
        assert call_args[0][0] == "get_object"
        assert call_args[1]["Params"]["Bucket"] == "test-bucket"
        assert call_args[1]["Params"]["Key"] == s3_key
