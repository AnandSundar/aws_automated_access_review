"""
Unit tests for Bedrock integration module.

Tests the generate_narrative_summary and helper functions in src/lambda/bedrock_integration.py
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import json
import time

# Add the src/lambda directory to the path so we can import the modules
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src/lambda"))

from bedrock_integration import (
    generate_narrative_summary,
    _invoke_bedrock_with_retry,
    _invoke_bedrock,
    _format_findings_for_bedrock,
    _generate_fallback_summary,
    validate_config,
    DEFAULT_CONFIG,
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
def mock_bedrock_response():
    """Provide a mock Bedrock response."""
    return {"body": MagicMock()}


class TestGenerateNarrativeSummary:
    """Test cases for generate_narrative_summary function."""

    @patch("bedrock_integration._invoke_bedrock_with_retry")
    @patch("bedrock_integration._format_findings_for_bedrock")
    def test_generate_narrative_summary_success(
        self, mock_format, mock_invoke, sample_findings
    ):
        """Test successful narrative generation."""
        mock_format.return_value = "Test prompt"
        mock_invoke.return_value = "Generated narrative summary"

        narrative = generate_narrative_summary(sample_findings)

        assert narrative == "Generated narrative summary"
        mock_format.assert_called_once()
        mock_invoke.assert_called_once()

    @patch("bedrock_integration._generate_fallback_summary")
    @patch("bedrock_integration._invoke_bedrock_with_retry")
    @patch("bedrock_integration._format_findings_for_bedrock")
    def test_generate_narrative_summary_with_error(
        self, mock_format, mock_invoke, mock_fallback, sample_findings
    ):
        """Test narrative generation with error falls back to fallback."""
        mock_format.return_value = "Test prompt"
        mock_invoke.side_effect = Exception("Bedrock error")
        mock_fallback.return_value = "Fallback summary"

        narrative = generate_narrative_summary(sample_findings)

        assert narrative == "Fallback summary"
        mock_fallback.assert_called_once_with(sample_findings)

    @patch("bedrock_integration._generate_fallback_summary")
    @patch("bedrock_integration._invoke_bedrock_with_retry")
    @patch("bedrock_integration._format_findings_for_bedrock")
    def test_generate_narrative_summary_empty_findings(
        self, mock_format, mock_invoke, mock_fallback
    ):
        """Test narrative generation with empty findings."""
        narrative = generate_narrative_summary([])

        assert "No security findings available" in narrative
        mock_format.assert_not_called()
        mock_invoke.assert_not_called()
        mock_fallback.assert_not_called()

    @patch("bedrock_integration._invoke_bedrock_with_retry")
    @patch("bedrock_integration._format_findings_for_bedrock")
    def test_generate_narrative_summary_with_custom_config(
        self, mock_format, mock_invoke, sample_findings
    ):
        """Test narrative generation with custom config."""
        custom_config = {
            "model_id": "anthropic.claude-3-opus-20240229-v1:0",
            "max_tokens": 3000,
            "temperature": 0.5,
        }
        mock_format.return_value = "Test prompt"
        mock_invoke.return_value = "Generated narrative"

        narrative = generate_narrative_summary(sample_findings, custom_config)

        assert narrative == "Generated narrative"
        # Verify that custom config was used
        call_args = mock_invoke.call_args
        assert call_args[1]["model_id"] == "anthropic.claude-3-opus-20240229-v1:0"
        assert call_args[1]["max_tokens"] == 3000
        assert call_args[1]["temperature"] == 0.5


class TestInvokeBedrockWithRetry:
    """Test cases for _invoke_bedrock_with_retry function."""

    @patch("bedrock_integration._invoke_bedrock")
    def test_invoke_bedrock_with_retry_success_first_attempt(self, mock_invoke):
        """Test successful invocation on first attempt."""
        mock_invoke.return_value = "Success"

        result = _invoke_bedrock_with_retry("Test prompt", DEFAULT_CONFIG)

        assert result == "Success"
        assert mock_invoke.call_count == 1

    @patch("bedrock_integration.time.sleep")
    @patch("bedrock_integration._invoke_bedrock")
    def test_invoke_bedrock_with_retry_success_after_retry(
        self, mock_invoke, mock_sleep
    ):
        """Test successful invocation after retry."""
        mock_invoke.side_effect = [Exception("ThrottlingException"), "Success"]

        result = _invoke_bedrock_with_retry("Test prompt", DEFAULT_CONFIG)

        assert result == "Success"
        assert mock_invoke.call_count == 2
        mock_sleep.assert_called_once()

    @patch("bedrock_integration.time.sleep")
    @patch("bedrock_integration._invoke_bedrock")
    def test_invoke_bedrock_with_retry_exhausted_retries(self, mock_invoke, mock_sleep):
        """Test that exhausted retries raise exception."""
        mock_invoke.side_effect = Exception("ThrottlingException")

        with pytest.raises(Exception):
            _invoke_bedrock_with_retry("Test prompt", DEFAULT_CONFIG)

        assert mock_invoke.call_count == 3  # max_retries default
        assert mock_sleep.call_count == 2

    @patch("bedrock_integration._invoke_bedrock")
    def test_invoke_bedrock_with_retry_non_retryable_error(self, mock_invoke):
        """Test that non-retryable errors are not retried."""
        mock_invoke.side_effect = Exception("AccessDenied")

        with pytest.raises(Exception):
            _invoke_bedrock_with_retry("Test prompt", DEFAULT_CONFIG)

        assert mock_invoke.call_count == 1

    @patch("bedrock_integration.time.sleep")
    @patch("bedrock_integration._invoke_bedrock")
    def test_invoke_bedrock_with_retry_exponential_backoff(
        self, mock_invoke, mock_sleep
    ):
        """Test that retry uses exponential backoff."""
        mock_invoke.side_effect = [
            Exception("ThrottlingException"),
            Exception("ThrottlingException"),
            "Success",
        ]

        result = _invoke_bedrock_with_retry("Test prompt", DEFAULT_CONFIG)

        assert result == "Success"
        assert mock_invoke.call_count == 3

        # Check sleep delays: 1.0, 2.0
        assert mock_sleep.call_args_list[0][0][0] == 1.0
        assert mock_sleep.call_args_list[1][0][0] == 2.0


class TestInvokeBedrock:
    """Test cases for _invoke_bedrock function."""

    @patch("bedrock_integration.boto3.client")
    def test_invoke_bedrock_success(self, mock_boto3_client, mock_bedrock_response):
        """Test successful Bedrock invocation."""
        mock_response_body = json.dumps({"content": [{"text": "Generated narrative"}]})
        mock_bedrock_response["body"].read.return_value = mock_response_body.encode(
            "utf-8"
        )

        mock_bedrock = Mock()
        mock_bedrock.invoke_model.return_value = mock_bedrock_response
        mock_boto3_client.return_value = mock_bedrock

        result = _invoke_bedrock("Test prompt", DEFAULT_CONFIG)

        assert result == "Generated narrative"
        mock_bedrock.invoke_model.assert_called_once()

    @patch("bedrock_integration.boto3.client")
    def test_invoke_bedrock_client_init_error(self, mock_boto3_client):
        """Test Bedrock client initialization error."""
        mock_boto3_client.side_effect = Exception("Failed to initialize client")

        with pytest.raises(Exception) as exc_info:
            _invoke_bedrock("Test prompt", DEFAULT_CONFIG)

        assert "Bedrock client initialization failed" in str(exc_info.value)

    @patch("bedrock_integration.boto3.client")
    def test_invoke_bedrock_api_error(self, mock_boto3_client, mock_bedrock_response):
        """Test Bedrock API error."""
        mock_bedrock = Mock()
        mock_bedrock.invoke_model.side_effect = Exception("API error")
        mock_boto3_client.return_value = mock_bedrock

        with pytest.raises(Exception):
            _invoke_bedrock("Test prompt", DEFAULT_CONFIG)

    @patch("bedrock_integration.boto3.client")
    def test_invoke_bedrock_empty_response(
        self, mock_boto3_client, mock_bedrock_response
    ):
        """Test Bedrock empty response."""
        mock_response_body = json.dumps({"content": [{"text": ""}]})
        mock_bedrock_response["body"].read.return_value = mock_response_body.encode(
            "utf-8"
        )

        mock_bedrock = Mock()
        mock_bedrock.invoke_model.return_value = mock_bedrock_response
        mock_boto3_client.return_value = mock_bedrock

        with pytest.raises(Exception) as exc_info:
            _invoke_bedrock("Test prompt", DEFAULT_CONFIG)

        assert "Empty response" in str(exc_info.value)

    @patch("bedrock_integration.boto3.client")
    def test_invoke_bedrock_malformed_response(
        self, mock_boto3_client, mock_bedrock_response
    ):
        """Test Bedrock malformed response."""
        mock_response_body = json.dumps({"content": []})
        mock_bedrock_response["body"].read.return_value = mock_response_body.encode(
            "utf-8"
        )

        mock_bedrock = Mock()
        mock_bedrock.invoke_model.return_value = mock_bedrock_response
        mock_boto3_client.return_value = mock_bedrock

        with pytest.raises(Exception) as exc_info:
            _invoke_bedrock("Test prompt", DEFAULT_CONFIG)

        assert "Unexpected response format" in str(exc_info.value)

    @patch("bedrock_integration.boto3.client")
    def test_invoke_bedrock_with_custom_region(
        self, mock_boto3_client, mock_bedrock_response
    ):
        """Test Bedrock invocation with custom region."""
        mock_response_body = json.dumps({"content": [{"text": "Generated narrative"}]})
        mock_bedrock_response["body"].read.return_value = mock_response_body.encode(
            "utf-8"
        )

        mock_bedrock = Mock()
        mock_bedrock.invoke_model.return_value = mock_bedrock_response
        mock_boto3_client.return_value = mock_bedrock

        config = DEFAULT_CONFIG.copy()
        config["region"] = "us-west-2"

        result = _invoke_bedrock("Test prompt", config)

        assert result == "Generated narrative"
        mock_boto3_client.assert_called_with("bedrock-runtime", region_name="us-west-2")


class TestFormatFindingsForBedrock:
    """Test cases for _format_findings_for_bedrock function."""

    def test_format_findings_for_bedrock_basic(self, sample_findings):
        """Test basic findings formatting."""
        prompt = _format_findings_for_bedrock(sample_findings, DEFAULT_CONFIG)

        assert "Senior AWS Security Architect" in prompt
        assert "Critical Findings: 1" in prompt
        assert "High Findings: 1" in prompt
        assert "Medium Findings: 1" in prompt
        assert "Low Findings: 0" in prompt

    def test_format_findings_for_bedrock_includes_findings(self, sample_findings):
        """Test that formatted prompt includes finding details."""
        prompt = _format_findings_for_bedrock(sample_findings, DEFAULT_CONFIG)

        assert "CRITICAL: User is missing MFA on user-without-mfa" in prompt
        assert "HIGH: Security group allows SSH from 0.0.0.0/0 on sg-12345678" in prompt
        assert "MEDIUM: S3 bucket lacks encryption on arn:aws:s3:::my-bucket" in prompt

    def test_format_findings_for_bedrock_limits_findings(self):
        """Test that formatted prompt limits findings to max_findings_for_context."""
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

        prompt = _format_findings_for_bedrock(findings, DEFAULT_CONFIG)

        # Should only include 30 findings (default max)
        finding_lines = [line for line in prompt.split("\n") if "LOW:" in line]
        assert len(finding_lines) == 30

    def test_format_findings_for_bedrock_with_custom_max(self):
        """Test formatted prompt with custom max_findings_for_context."""
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

        config = DEFAULT_CONFIG.copy()
        config["max_findings_for_context"] = 10

        prompt = _format_findings_for_bedrock(findings, config)

        # Should only include 10 findings
        finding_lines = [line for line in prompt.split("\n") if "LOW:" in line]
        assert len(finding_lines) == 10

    def test_format_findings_for_bedrock_includes_requirements(self, sample_findings):
        """Test that formatted prompt includes requirements."""
        prompt = _format_findings_for_bedrock(sample_findings, DEFAULT_CONFIG)

        assert "400-500 words" in prompt
        assert "Professional" in prompt
        assert "Overview Paragraph" in prompt
        assert "Critical Findings List" in prompt
        assert "Recommendations" in prompt

    def test_format_findings_for_bedrock_with_missing_severity(self):
        """Test formatted prompt with findings missing severity."""
        findings = [
            {
                "resource_id": "resource1",
                "resource_type": "AWS::S3::Bucket",
                "service": "S3",
                "finding": "Test finding",
                "recommendation": "Fix it",
            }
        ]

        prompt = _format_findings_for_bedrock(findings, DEFAULT_CONFIG)

        # Should default to LOW
        assert "Low Findings: 1" in prompt


class TestGenerateFallbackSummary:
    """Test cases for _generate_fallback_summary function."""

    def test_generate_fallback_summary_basic(self, sample_findings):
        """Test basic fallback summary generation."""
        summary = _generate_fallback_summary(sample_findings)

        assert "SECURITY ACCESS REVIEW SUMMARY" in summary
        assert "3 security findings" in summary
        assert "Critical: 1" in summary
        assert "High: 1" in summary
        assert "Medium: 1" in summary

    def test_generate_fallback_summary_empty_findings(self):
        """Test fallback summary with empty findings."""
        summary = _generate_fallback_summary([])

        assert "0 security findings" in summary
        assert "Critical: 0" in summary

    def test_generate_fallback_summary_includes_recommendations(self, sample_findings):
        """Test that fallback summary includes recommendations."""
        summary = _generate_fallback_summary(sample_findings)

        assert "Recommended Actions" in summary
        assert "Immediately address all Critical severity findings" in summary
        assert "Review and remediate High severity findings" in summary

    def test_generate_fallback_summary_with_all_severities(self):
        """Test fallback summary with all severity levels."""
        findings = [
            {
                "resource_id": f"resource{i}",
                "resource_type": "AWS::S3::Bucket",
                "service": "S3",
                "severity": severity,
                "finding": f"{severity} finding",
                "recommendation": "Fix it",
            }
            for i, severity in enumerate(["CRITICAL", "HIGH", "MEDIUM", "LOW"])
        ]

        summary = _generate_fallback_summary(findings)

        assert "Critical: 1" in summary
        assert "High: 1" in summary
        assert "Medium: 1" in summary
        assert "Low: 1" in summary


class TestValidateConfig:
    """Test cases for validate_config function."""

    def test_validate_config_valid(self):
        """Test validation of valid config."""
        config = {
            "model_id": "anthropic.claude-3-sonnet-20240229-v1:0",
            "max_tokens": 2000,
            "temperature": 0.7,
            "max_retries": 3,
            "retry_delay": 1.0,
            "max_findings_for_context": 30,
        }

        result = validate_config(config)

        assert result is True

    def test_validate_config_invalid_max_tokens(self):
        """Test validation of invalid max_tokens."""
        config = {"max_tokens": -1}

        result = validate_config(config)

        assert result is False

    def test_validate_config_invalid_temperature(self):
        """Test validation of invalid temperature."""
        config = {"temperature": 1.5}

        result = validate_config(config)

        assert result is False

    def test_validate_config_invalid_max_retries(self):
        """Test validation of invalid max_retries."""
        config = {"max_retries": -1}

        result = validate_config(config)

        assert result is False

    def test_validate_config_invalid_retry_delay(self):
        """Test validation of invalid retry_delay."""
        config = {"retry_delay": -1.0}

        result = validate_config(config)

        assert result is False

    def test_validate_config_invalid_max_findings(self):
        """Test validation of invalid max_findings_for_context."""
        config = {"max_findings_for_context": 0}

        result = validate_config(config)

        assert result is False

    def test_validate_config_unknown_keys(self):
        """Test validation with unknown keys."""
        config = {"unknown_key": "value", "max_tokens": 2000}

        result = validate_config(config)

        # Should still return True, but log warning
        assert result is True

    def test_validate_config_empty(self):
        """Test validation of empty config."""
        result = validate_config({})

        assert result is True


class TestDefaultConfig:
    """Test cases for DEFAULT_CONFIG."""

    def test_default_config_structure(self):
        """Test that DEFAULT_CONFIG has correct structure."""
        assert "model_id" in DEFAULT_CONFIG
        assert "region" in DEFAULT_CONFIG
        assert "max_tokens" in DEFAULT_CONFIG
        assert "temperature" in DEFAULT_CONFIG
        assert "max_retries" in DEFAULT_CONFIG
        assert "retry_delay" in DEFAULT_CONFIG
        assert "max_findings_for_context" in DEFAULT_CONFIG

    def test_default_config_values(self):
        """Test that DEFAULT_CONFIG has correct values."""
        assert DEFAULT_CONFIG["model_id"] == "anthropic.claude-3-sonnet-20240229-v1:0"
        assert DEFAULT_CONFIG["region"] == "us-east-1"
        assert DEFAULT_CONFIG["max_tokens"] == 2000
        assert DEFAULT_CONFIG["temperature"] == 0.7
        assert DEFAULT_CONFIG["max_retries"] == 3
        assert DEFAULT_CONFIG["retry_delay"] == 1.0
        assert DEFAULT_CONFIG["max_findings_for_context"] == 30

    def test_default_config_types(self):
        """Test that DEFAULT_CONFIG has correct types."""
        assert isinstance(DEFAULT_CONFIG["model_id"], str)
        assert isinstance(DEFAULT_CONFIG["region"], str)
        assert isinstance(DEFAULT_CONFIG["max_tokens"], int)
        assert isinstance(DEFAULT_CONFIG["temperature"], float)
        assert isinstance(DEFAULT_CONFIG["max_retries"], int)
        assert isinstance(DEFAULT_CONFIG["retry_delay"], float)
        assert isinstance(DEFAULT_CONFIG["max_findings_for_context"], int)
