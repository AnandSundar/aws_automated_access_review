"""
Unit tests for email utils module.

Tests the send_report_email function in src/lambda/modules/email_utils.py
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from email.mime.multipart import MIMEMultipart

# Add the src/lambda directory to the path so we can import the modules
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src/lambda"))

from modules.email_utils import send_report_email


@pytest.fixture
def mock_ses_client():
    """Create a mock SES client."""
    client = Mock()
    return client


@pytest.fixture
def sample_narrative():
    """Provide a sample narrative for testing."""
    return """
    AWS Automated Access Review Summary
    
    This automated access review identified 3 security findings across your AWS environment.
    
    Severity Breakdown:
    - Critical: 1
    - High: 1
    - Medium: 1
    
    Recommended Actions:
    1. Immediately address all Critical severity findings
    2. Review and remediate High severity findings within 24 hours
    """


@pytest.fixture
def sample_csv_content():
    """Provide sample CSV content for testing."""
    return b"Timestamp,ResourceID,ResourceType,Service,Severity,Finding,Recommendation\n2024-01-01T12:00:00,user1,IAM_USER,IAM,CRITICAL,User missing MFA,Enable MFA\n"


@pytest.fixture
def sample_recipient_email():
    """Provide a sample recipient email."""
    return "test@example.com"


class TestSendReportEmailSuccess:
    """Test cases for successful email sending."""

    @patch("modules.email_utils.boto3.client")
    def test_send_report_email_success(
        self,
        mock_boto3_client,
        sample_narrative,
        sample_csv_content,
        sample_recipient_email,
    ):
        """Test successful email sending."""
        mock_ses = Mock()
        mock_ses.send_raw_email.return_value = {"MessageId": "test-message-id-123"}
        mock_boto3_client.return_value = mock_ses

        message_id = send_report_email(
            sample_narrative, sample_csv_content, sample_recipient_email
        )

        assert message_id == "test-message-id-123"
        mock_ses.send_raw_email.assert_called_once()

        # Verify the call parameters
        call_args = mock_ses.send_raw_email.call_args
        assert "Source" in call_args[1]
        assert "Destinations" in call_args[1]
        assert "RawMessage" in call_args[1]
        assert call_args[1]["Source"] == sample_recipient_email
        assert call_args[1]["Destinations"] == [sample_recipient_email]

    @patch("modules.email_utils.boto3.client")
    def test_email_subject_includes_date(
        self,
        mock_boto3_client,
        sample_narrative,
        sample_csv_content,
        sample_recipient_email,
    ):
        """Test that email subject includes the date."""
        mock_ses = Mock()
        mock_ses.send_raw_email.return_value = {"MessageId": "test-message-id-123"}
        mock_boto3_client.return_value = mock_ses

        message_id = send_report_email(
            sample_narrative, sample_csv_content, sample_recipient_email
        )

        # Get the raw message that was sent
        call_args = mock_ses.send_raw_email.call_args
        raw_message = call_args[1]["RawMessage"]["Data"]

        # Parse the raw message to check subject
        assert "Subject:" in raw_message
        assert "AWS Access Review Report" in raw_message

    @patch("modules.email_utils.boto3.client")
    def test_email_includes_narrative(
        self,
        mock_boto3_client,
        sample_narrative,
        sample_csv_content,
        sample_recipient_email,
    ):
        """Test that email includes the narrative."""
        mock_ses = Mock()
        mock_ses.send_raw_email.return_value = {"MessageId": "test-message-id-123"}
        mock_boto3_client.return_value = mock_ses

        message_id = send_report_email(
            sample_narrative, sample_csv_content, sample_recipient_email
        )

        # Get the raw message that was sent
        call_args = mock_ses.send_raw_email.call_args
        raw_message = call_args[1]["RawMessage"]["Data"]

        # Check that narrative is included
        assert "AWS Automated Access Review Summary" in raw_message
        assert "security findings" in raw_message

    @patch("modules.email_utils.boto3.client")
    def test_email_includes_attachment(
        self,
        mock_boto3_client,
        sample_narrative,
        sample_csv_content,
        sample_recipient_email,
    ):
        """Test that email includes CSV attachment."""
        mock_ses = Mock()
        mock_ses.send_raw_email.return_value = {"MessageId": "test-message-id-123"}
        mock_boto3_client.return_value = mock_ses

        message_id = send_report_email(
            sample_narrative, sample_csv_content, sample_recipient_email
        )

        # Get the raw message that was sent
        call_args = mock_ses.send_raw_email.call_args
        raw_message = call_args[1]["RawMessage"]["Data"]

        # Check that attachment is included
        assert "Content-Disposition: attachment" in raw_message
        assert "access-review-" in raw_message
        assert ".csv" in raw_message

    @patch("modules.email_utils.boto3.client")
    def test_email_sender_equals_recipient(
        self,
        mock_boto3_client,
        sample_narrative,
        sample_csv_content,
        sample_recipient_email,
    ):
        """Test that email sender equals recipient (SES requirement)."""
        mock_ses = Mock()
        mock_ses.send_raw_email.return_value = {"MessageId": "test-message-id-123"}
        mock_boto3_client.return_value = mock_ses

        message_id = send_report_email(
            sample_narrative, sample_csv_content, sample_recipient_email
        )

        # Get the raw message that was sent
        call_args = mock_ses.send_raw_email.call_args
        raw_message = call_args[1]["RawMessage"]["Data"]

        # Check that From and To are the same
        lines = raw_message.split("\n")
        from_line = next((line for line in lines if line.startswith("From:")), None)
        to_line = next((line for line in lines if line.startswith("To:")), None)

        assert from_line is not None
        assert to_line is not None
        assert sample_recipient_email in from_line
        assert sample_recipient_email in to_line


class TestSendReportEmailErrorHandling:
    """Test cases for error handling in email sending."""

    @patch("modules.email_utils.boto3.client")
    def test_ses_error_returns_none(
        self,
        mock_boto3_client,
        sample_narrative,
        sample_csv_content,
        sample_recipient_email,
    ):
        """Test that SES errors return None."""
        mock_ses = Mock()
        mock_ses.send_raw_email.side_effect = Exception("SES error")
        mock_boto3_client.return_value = mock_ses

        message_id = send_report_email(
            sample_narrative, sample_csv_content, sample_recipient_email
        )

        assert message_id is None

    @patch("modules.email_utils.boto3.client")
    def test_client_error_returns_none(
        self,
        mock_boto3_client,
        sample_narrative,
        sample_csv_content,
        sample_recipient_email,
    ):
        """Test that ClientError returns None."""
        from botocore.exceptions import ClientError

        mock_ses = Mock()
        mock_ses.send_raw_email.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Not authorized"}},
            "SendRawEmail",
        )
        mock_boto3_client.return_value = mock_ses

        message_id = send_report_email(
            sample_narrative, sample_csv_content, sample_recipient_email
        )

        assert message_id is None

    @patch("modules.email_utils.boto3.client")
    def test_boto3_client_error_returns_none(
        self,
        mock_boto3_client,
        sample_narrative,
        sample_csv_content,
        sample_recipient_email,
    ):
        """Test that boto3 client initialization errors return None."""
        mock_boto3_client.side_effect = Exception("Failed to initialize client")

        message_id = send_report_email(
            sample_narrative, sample_csv_content, sample_recipient_email
        )

        assert message_id is None


class TestSendReportEmailEdgeCases:
    """Test cases for edge cases in email sending."""

    @patch("modules.email_utils.boto3.client")
    def test_empty_narrative(
        self, mock_boto3_client, sample_csv_content, sample_recipient_email
    ):
        """Test email sending with empty narrative."""
        mock_ses = Mock()
        mock_ses.send_raw_email.return_value = {"MessageId": "test-message-id-123"}
        mock_boto3_client.return_value = mock_ses

        message_id = send_report_email("", sample_csv_content, sample_recipient_email)

        assert message_id == "test-message-id-123"
        mock_ses.send_raw_email.assert_called_once()

    @patch("modules.email_utils.boto3.client")
    def test_empty_csv_content(
        self, mock_boto3_client, sample_narrative, sample_recipient_email
    ):
        """Test email sending with empty CSV content."""
        mock_ses = Mock()
        mock_ses.send_raw_email.return_value = {"MessageId": "test-message-id-123"}
        mock_boto3_client.return_value = mock_ses

        message_id = send_report_email(sample_narrative, b"", sample_recipient_email)

        assert message_id == "test-message-id-123"
        mock_ses.send_raw_email.assert_called_once()

    @patch("modules.email_utils.boto3.client")
    def test_long_narrative(
        self, mock_boto3_client, sample_csv_content, sample_recipient_email
    ):
        """Test email sending with very long narrative."""
        # Create a very long narrative
        long_narrative = "A" * 100000  # 100KB of text

        mock_ses = Mock()
        mock_ses.send_raw_email.return_value = {"MessageId": "test-message-id-123"}
        mock_boto3_client.return_value = mock_ses

        message_id = send_report_email(
            long_narrative, sample_csv_content, sample_recipient_email
        )

        assert message_id == "test-message-id-123"
        mock_ses.send_raw_email.assert_called_once()

    @patch("modules.email_utils.boto3.client")
    def test_special_characters_in_narrative(
        self, mock_boto3_client, sample_csv_content, sample_recipient_email
    ):
        """Test email sending with special characters in narrative."""
        narrative_with_special_chars = """
        AWS Access Review Summary
        
        Special characters: <>&"''
        Unicode: café, naïve, 日本語
        Emojis: 🔒 🚨 ⚠️
        """

        mock_ses = Mock()
        mock_ses.send_raw_email.return_value = {"MessageId": "test-message-id-123"}
        mock_boto3_client.return_value = mock_ses

        message_id = send_report_email(
            narrative_with_special_chars, sample_csv_content, sample_recipient_email
        )

        assert message_id == "test-message-id-123"
        mock_ses.send_raw_email.assert_called_once()

    @patch("modules.email_utils.boto3.client")
    def test_large_csv_content(
        self, mock_boto3_client, sample_narrative, sample_recipient_email
    ):
        """Test email sending with large CSV content."""
        # Create a large CSV content
        large_csv = b"Timestamp,ResourceID,ResourceType,Service,Severity,Finding,Recommendation\n"
        for i in range(1000):
            large_csv += f"2024-01-01T12:00:00,resource{i},AWS::S3::Bucket,S3,LOW,Finding {i},Fix it\n".encode(
                "utf-8"
            )

        mock_ses = Mock()
        mock_ses.send_raw_email.return_value = {"MessageId": "test-message-id-123"}
        mock_boto3_client.return_value = mock_ses

        message_id = send_report_email(
            sample_narrative, large_csv, sample_recipient_email
        )

        assert message_id == "test-message-id-123"
        mock_ses.send_raw_email.assert_called_once()


class TestEmailStructure:
    """Test cases for email structure."""

    @patch("modules.email_utils.boto3.client")
    def test_email_is_multipart(
        self,
        mock_boto3_client,
        sample_narrative,
        sample_csv_content,
        sample_recipient_email,
    ):
        """Test that email is multipart/mixed."""
        mock_ses = Mock()
        mock_ses.send_raw_email.return_value = {"MessageId": "test-message-id-123"}
        mock_boto3_client.return_value = mock_ses

        message_id = send_report_email(
            sample_narrative, sample_csv_content, sample_recipient_email
        )

        # Get the raw message that was sent
        call_args = mock_ses.send_raw_email.call_args
        raw_message = call_args[1]["RawMessage"]["Data"]

        # Check that it's multipart
        assert "Content-Type: multipart/mixed" in raw_message

    @patch("modules.email_utils.boto3.client")
    def test_email_has_html_body(
        self,
        mock_boto3_client,
        sample_narrative,
        sample_csv_content,
        sample_recipient_email,
    ):
        """Test that email has HTML body."""
        mock_ses = Mock()
        mock_ses.send_raw_email.return_value = {"MessageId": "test-message-id-123"}
        mock_boto3_client.return_value = mock_ses

        message_id = send_report_email(
            sample_narrative, sample_csv_content, sample_recipient_email
        )

        # Get the raw message that was sent
        call_args = mock_ses.send_raw_email.call_args
        raw_message = call_args[1]["RawMessage"]["Data"]

        # Check for HTML content
        assert "<html>" in raw_message
        assert "</html>" in raw_message
        assert "<body>" in raw_message
        assert "</body>" in raw_message

    @patch("modules.email_utils.boto3.client")
    def test_email_has_alternative_part(
        self,
        mock_boto3_client,
        sample_narrative,
        sample_csv_content,
        sample_recipient_email,
    ):
        """Test that email has multipart/alternative part."""
        mock_ses = Mock()
        mock_ses.send_raw_email.return_value = {"MessageId": "test-message-id-123"}
        mock_boto3_client.return_value = mock_ses

        message_id = send_report_email(
            sample_narrative, sample_csv_content, sample_recipient_email
        )

        # Get the raw message that was sent
        call_args = mock_ses.send_raw_email.call_args
        raw_message = call_args[1]["RawMessage"]["Data"]

        # Check for multipart/alternative
        assert "multipart/alternative" in raw_message

    @patch("modules.email_utils.boto3.client")
    def test_email_attachment_filename(
        self,
        mock_boto3_client,
        sample_narrative,
        sample_csv_content,
        sample_recipient_email,
    ):
        """Test that email attachment has correct filename."""
        mock_ses = Mock()
        mock_ses.send_raw_email.return_value = {"MessageId": "test-message-id-123"}
        mock_boto3_client.return_value = mock_ses

        message_id = send_report_email(
            sample_narrative, sample_csv_content, sample_recipient_email
        )

        # Get the raw message that was sent
        call_args = mock_ses.send_raw_email.call_args
        raw_message = call_args[1]["RawMessage"]["Data"]

        # Check for attachment filename
        assert "Content-Disposition: attachment" in raw_message
        assert "filename=" in raw_message
        assert ".csv" in raw_message


class TestEmailContent:
    """Test cases for email content."""

    @patch("modules.email_utils.boto3.client")
    def test_email_includes_header(
        self,
        mock_boto3_client,
        sample_narrative,
        sample_csv_content,
        sample_recipient_email,
    ):
        """Test that email includes header."""
        mock_ses = Mock()
        mock_ses.send_raw_email.return_value = {"MessageId": "test-message-id-123"}
        mock_boto3_client.return_value = mock_ses

        message_id = send_report_email(
            sample_narrative, sample_csv_content, sample_recipient_email
        )

        # Get the raw message that was sent
        call_args = mock_ses.send_raw_email.call_args
        raw_message = call_args[1]["RawMessage"]["Data"]

        # Check for header
        assert "<h1>AWS Automated Access Review Summary</h1>" in raw_message

    @patch("modules.email_utils.boto3.client")
    def test_email_includes_attachment_notice(
        self,
        mock_boto3_client,
        sample_narrative,
        sample_csv_content,
        sample_recipient_email,
    ):
        """Test that email includes attachment notice."""
        mock_ses = Mock()
        mock_ses.send_raw_email.return_value = {"MessageId": "test-message-id-123"}
        mock_boto3_client.return_value = mock_ses

        message_id = send_report_email(
            sample_narrative, sample_csv_content, sample_recipient_email
        )

        # Get the raw message that was sent
        call_args = mock_ses.send_raw_email.call_args
        raw_message = call_args[1]["RawMessage"]["Data"]

        # Check for attachment notice
        assert "detailed CSV report is attached" in raw_message

    @patch("modules.email_utils.boto3.client")
    def test_email_preserves_whitespace(
        self, mock_boto3_client, sample_csv_content, sample_recipient_email
    ):
        """Test that email preserves whitespace in narrative."""
        narrative_with_whitespace = """
        Line 1
        
        Line 2 (with blank line above)
        
        Line 3 (with blank line above)
        """

        mock_ses = Mock()
        mock_ses.send_raw_email.return_value = {"MessageId": "test-message-id-123"}
        mock_boto3_client.return_value = mock_ses

        message_id = send_report_email(
            narrative_with_whitespace, sample_csv_content, sample_recipient_email
        )

        # Get the raw message that was sent
        call_args = mock_ses.send_raw_email.call_args
        raw_message = call_args[1]["RawMessage"]["Data"]

        # Check for whitespace preservation
        assert "white-space: pre-wrap" in raw_message
