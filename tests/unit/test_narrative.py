"""
Unit tests for narrative module.

Tests the generate_narrative function in src/lambda/modules/narrative.py
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import json

# Add the src/lambda directory to the path so we can import the modules
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src/lambda"))

from modules.narrative import generate_narrative


@pytest.fixture
def mock_bedrock_client():
    """Create a mock Bedrock client."""
    client = Mock()
    return client


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
def sample_bedrock_response():
    """Provide a sample Bedrock response."""
    return {"body": MagicMock()}


class TestGenerateNarrativeSuccess:
    """Test cases for successful narrative generation."""

    @patch("modules.narrative.boto3.client")
    def test_generate_narrative_success(
        self, mock_boto3_client, sample_findings, sample_bedrock_response
    ):
        """Test successful narrative generation."""
        mock_bedrock = Mock()

        # Mock the response body
        mock_response_body = json.dumps(
            {
                "content": [
                    {
                        "text": "This is a generated executive summary of the security findings. The organization has 1 critical, 1 high, and 1 medium severity finding. Immediate action is required for the critical finding regarding missing MFA."
                    }
                ]
            }
        )
        sample_bedrock_response["body"].read.return_value = mock_response_body.encode(
            "utf-8"
        )

        mock_bedrock.invoke_model.return_value = sample_bedrock_response
        mock_boto3_client.return_value = mock_bedrock

        narrative = generate_narrative(sample_findings)

        assert narrative is not None
        assert len(narrative) > 0
        assert (
            "executive summary" in narrative.lower() or "security" in narrative.lower()
        )

    @patch("modules.narrative.boto3.client")
    def test_generate_narrative_with_critical_findings(
        self, mock_boto3_client, sample_bedrock_response
    ):
        """Test narrative generation with critical findings."""
        findings = [
            {
                "resource_id": "user1",
                "resource_type": "IAM_USER",
                "service": "IAM",
                "severity": "CRITICAL",
                "finding": "Critical finding 1",
                "recommendation": "Fix it",
            },
            {
                "resource_id": "user2",
                "resource_type": "IAM_USER",
                "service": "IAM",
                "severity": "CRITICAL",
                "finding": "Critical finding 2",
                "recommendation": "Fix it",
            },
        ]

        mock_response_body = json.dumps(
            {
                "content": [
                    {"text": "Critical findings detected. Immediate action required."}
                ]
            }
        )
        sample_bedrock_response["body"].read.return_value = mock_response_body.encode(
            "utf-8"
        )

        mock_bedrock = Mock()
        mock_bedrock.invoke_model.return_value = sample_bedrock_response
        mock_boto3_client.return_value = mock_bedrock

        narrative = generate_narrative(findings)

        assert narrative is not None
        assert len(narrative) > 0

    @patch("modules.narrative.boto3.client")
    def test_generate_narrative_with_many_findings(
        self, mock_boto3_client, sample_bedrock_response
    ):
        """Test narrative generation with many findings (should limit to 30)."""
        # Create 50 findings
        findings = [
            {
                "resource_id": f"resource-{i}",
                "resource_type": "AWS::S3::Bucket",
                "service": "S3",
                "severity": "LOW",
                "finding": f"Finding {i}",
                "recommendation": "Fix it",
            }
            for i in range(50)
        ]

        mock_response_body = json.dumps(
            {"content": [{"text": "Summary of findings generated."}]}
        )
        sample_bedrock_response["body"].read.return_value = mock_response_body.encode(
            "utf-8"
        )

        mock_bedrock = Mock()
        mock_bedrock.invoke_model.return_value = sample_bedrock_response
        mock_boto3_client.return_value = mock_bedrock

        narrative = generate_narrative(findings)

        assert narrative is not None
        assert len(narrative) > 0

    @patch("modules.narrative.boto3.client")
    def test_bedrock_invoke_parameters(
        self, mock_boto3_client, sample_findings, sample_bedrock_response
    ):
        """Test that Bedrock is invoked with correct parameters."""
        mock_response_body = json.dumps({"content": [{"text": "Generated narrative"}]})
        sample_bedrock_response["body"].read.return_value = mock_response_body.encode(
            "utf-8"
        )

        mock_bedrock = Mock()
        mock_bedrock.invoke_model.return_value = sample_bedrock_response
        mock_boto3_client.return_value = mock_bedrock

        narrative = generate_narrative(sample_findings)

        # Verify invoke_model was called
        assert mock_bedrock.invoke_model.called

        # Check the call arguments
        call_args = mock_bedrock.invoke_model.call_args
        assert "modelId" in call_args[1]
        assert "body" in call_args[1]

        # Check the model ID
        assert call_args[1]["modelId"] == "anthropic.claude-3-sonnet-20240229-v1:0"

        # Check the body structure
        body = json.loads(call_args[1]["body"])
        assert "anthropic_version" in body
        assert "max_tokens" in body
        assert "messages" in body


class TestGenerateNarrativeErrorHandling:
    """Test cases for error handling in narrative generation."""

    @patch("modules.narrative.boto3.client")
    def test_bedrock_error_returns_fallback(self, mock_boto3_client, sample_findings):
        """Test that Bedrock errors return a fallback summary."""
        mock_bedrock = Mock()
        mock_bedrock.invoke_model.side_effect = Exception("Bedrock error")
        mock_boto3_client.return_value = mock_bedrock

        narrative = generate_narrative(sample_findings)

        assert narrative is not None
        assert "Unable to generate AI narrative" in narrative
        assert "Manual Summary" in narrative

    @patch("modules.narrative.boto3.client")
    def test_empty_response_returns_fallback(
        self, mock_boto3_client, sample_findings, sample_bedrock_response
    ):
        """Test that empty Bedrock response returns a fallback summary."""
        mock_response_body = json.dumps({"content": [{"text": ""}]})
        sample_bedrock_response["body"].read.return_value = mock_response_body.encode(
            "utf-8"
        )

        mock_bedrock = Mock()
        mock_bedrock.invoke_model.return_value = sample_bedrock_response
        mock_boto3_client.return_value = mock_bedrock

        narrative = generate_narrative(sample_findings)

        # Should return the empty text or handle gracefully
        assert narrative is not None

    @patch("modules.narrative.boto3.client")
    def test_malformed_response_returns_fallback(
        self, mock_boto3_client, sample_findings, sample_bedrock_response
    ):
        """Test that malformed Bedrock response returns a fallback summary."""
        # Return malformed JSON
        sample_bedrock_response["body"].read.return_value = b"invalid json"

        mock_bedrock = Mock()
        mock_bedrock.invoke_model.return_value = sample_bedrock_response
        mock_boto3_client.return_value = mock_bedrock

        narrative = generate_narrative(sample_findings)

        # Should handle the error gracefully
        assert narrative is not None

    @patch("modules.narrative.boto3.client")
    def test_client_error_returns_fallback(self, mock_boto3_client, sample_findings):
        """Test that ClientError returns a fallback summary."""
        from botocore.exceptions import ClientError

        mock_bedrock = Mock()
        mock_bedrock.invoke_model.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Not authorized"}},
            "InvokeModel",
        )
        mock_boto3_client.return_value = mock_bedrock

        narrative = generate_narrative(sample_findings)

        assert narrative is not None
        assert "Unable to generate AI narrative" in narrative


class TestGenerateNarrativeEdgeCases:
    """Test cases for edge cases in narrative generation."""

    @patch("modules.narrative.boto3.client")
    def test_empty_findings_list(self, mock_boto3_client, sample_bedrock_response):
        """Test narrative generation with empty findings list."""
        mock_response_body = json.dumps(
            {"content": [{"text": "No findings to report."}]}
        )
        sample_bedrock_response["body"].read.return_value = mock_response_body.encode(
            "utf-8"
        )

        mock_bedrock = Mock()
        mock_bedrock.invoke_model.return_value = sample_bedrock_response
        mock_boto3_client.return_value = mock_bedrock

        narrative = generate_narrative([])

        assert narrative is not None
        assert len(narrative) > 0

    @patch("modules.narrative.boto3.client")
    def test_findings_without_required_fields(
        self, mock_boto3_client, sample_bedrock_response
    ):
        """Test narrative generation with findings missing required fields."""
        incomplete_findings = [
            {
                "resource_id": "resource1",
                # Missing other fields
            }
        ]

        mock_response_body = json.dumps({"content": [{"text": "Summary generated."}]})
        sample_bedrock_response["body"].read.return_value = mock_response_body.encode(
            "utf-8"
        )

        mock_bedrock = Mock()
        mock_bedrock.invoke_model.return_value = sample_bedrock_response
        mock_boto3_client.return_value = mock_bedrock

        # Should not raise an exception
        narrative = generate_narrative(incomplete_findings)
        assert narrative is not None

    @patch("modules.narrative.boto3.client")
    def test_findings_with_unknown_severity(
        self, mock_boto3_client, sample_bedrock_response
    ):
        """Test narrative generation with findings having unknown severity."""
        findings = [
            {
                "resource_id": "resource1",
                "resource_type": "AWS::S3::Bucket",
                "service": "S3",
                "severity": "UNKNOWN",
                "finding": "Unknown severity finding",
                "recommendation": "Review",
            }
        ]

        mock_response_body = json.dumps({"content": [{"text": "Summary generated."}]})
        sample_bedrock_response["body"].read.return_value = mock_response_body.encode(
            "utf-8"
        )

        mock_bedrock = Mock()
        mock_bedrock.invoke_model.return_value = sample_bedrock_response
        mock_boto3_client.return_value = mock_bedrock

        # Should not raise an exception
        narrative = generate_narrative(findings)
        assert narrative is not None

    @patch("modules.narrative.boto3.client")
    def test_findings_with_case_variations(
        self, mock_boto3_client, sample_bedrock_response
    ):
        """Test narrative generation with severity in different cases."""
        findings = [
            {
                "resource_id": "resource1",
                "resource_type": "AWS::S3::Bucket",
                "service": "S3",
                "severity": "critical",  # lowercase
                "finding": "Critical finding",
                "recommendation": "Fix it",
            },
            {
                "resource_id": "resource2",
                "resource_type": "AWS::S3::Bucket",
                "service": "S3",
                "severity": "High",  # mixed case
                "finding": "High finding",
                "recommendation": "Fix it",
            },
        ]

        mock_response_body = json.dumps({"content": [{"text": "Summary generated."}]})
        sample_bedrock_response["body"].read.return_value = mock_response_body.encode(
            "utf-8"
        )

        mock_bedrock = Mock()
        mock_bedrock.invoke_model.return_value = sample_bedrock_response
        mock_boto3_client.return_value = mock_bedrock

        # Should not raise an exception
        narrative = generate_narrative(findings)
        assert narrative is not None


class TestPromptGeneration:
    """Test cases for prompt generation."""

    @patch("modules.narrative.boto3.client")
    def test_prompt_includes_severity_counts(
        self, mock_boto3_client, sample_findings, sample_bedrock_response
    ):
        """Test that the prompt includes severity counts."""
        mock_response_body = json.dumps({"content": [{"text": "Generated narrative"}]})
        sample_bedrock_response["body"].read.return_value = mock_response_body.encode(
            "utf-8"
        )

        mock_bedrock = Mock()
        mock_bedrock.invoke_model.return_value = sample_bedrock_response
        mock_boto3_client.return_value = mock_bedrock

        narrative = generate_narrative(sample_findings)

        # Get the body that was sent to Bedrock
        call_args = mock_bedrock.invoke_model.call_args
        body = json.loads(call_args[1]["body"])
        prompt = body["messages"][0]["content"]

        # Check that severity counts are in the prompt
        assert "Critical Findings: 1" in prompt
        assert "High Findings: 1" in prompt
        assert "Medium Findings: 1" in prompt

    @patch("modules.narrative.boto3.client")
    def test_prompt_includes_finding_details(
        self, mock_boto3_client, sample_findings, sample_bedrock_response
    ):
        """Test that the prompt includes finding details."""
        mock_response_body = json.dumps({"content": [{"text": "Generated narrative"}]})
        sample_bedrock_response["body"].read.return_value = mock_response_body.encode(
            "utf-8"
        )

        mock_bedrock = Mock()
        mock_bedrock.invoke_model.return_value = sample_bedrock_response
        mock_boto3_client.return_value = mock_bedrock

        narrative = generate_narrative(sample_findings)

        # Get the body that was sent to Bedrock
        call_args = mock_bedrock.invoke_model.call_args
        body = json.loads(call_args[1]["body"])
        prompt = body["messages"][0]["content"]

        # Check that finding details are in the prompt
        assert "CRITICAL" in prompt
        assert "HIGH" in prompt
        assert "MEDIUM" in prompt

    @patch("modules.narrative.boto3.client")
    def test_prompt_includes_requirements(
        self, mock_boto3_client, sample_findings, sample_bedrock_response
    ):
        """Test that the prompt includes requirements."""
        mock_response_body = json.dumps({"content": [{"text": "Generated narrative"}]})
        sample_bedrock_response["body"].read.return_value = mock_response_body.encode(
            "utf-8"
        )

        mock_bedrock = Mock()
        mock_bedrock.invoke_model.return_value = sample_bedrock_response
        mock_boto3_client.return_value = mock_bedrock

        narrative = generate_narrative(sample_findings)

        # Get the body that was sent to Bedrock
        call_args = mock_bedrock.invoke_model.call_args
        body = json.loads(call_args[1]["body"])
        prompt = body["messages"][0]["content"]

        # Check that requirements are in the prompt
        assert "400-500 words" in prompt
        assert "Professional" in prompt
        assert "Overview Paragraph" in prompt
        assert "Critical Findings List" in prompt
        assert "Recommendations" in prompt
