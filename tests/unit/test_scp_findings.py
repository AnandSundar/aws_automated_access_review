"""
Unit tests for SCP findings module.

Tests the get_scp_findings function and helper functions in src/lambda/modules/scp_findings.py
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from botocore.exceptions import ClientError

# Add the src/lambda directory to the path so we can import the modules
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src/lambda"))

from modules.scp_findings import (
    get_scp_findings,
    _get_all_scps,
    _check_wildcard_actions,
    _check_wildcard_notactions,
    _check_missing_resource_constraints,
)


@pytest.fixture
def mock_organizations_client():
    """Create a mock Organizations client."""
    client = Mock()
    return client


@pytest.fixture
def sample_root():
    """Provide a sample organization root."""
    return {
        "Id": "r-1234",
        "Arn": "arn:aws:organizations::123456789012:root/o-123456/r-1234",
        "Name": "Root",
        "PolicyTypes": [{"Type": "SERVICE_CONTROL_POLICY", "Status": "ENABLED"}],
    }


@pytest.fixture
def sample_scp_wildcard_allow():
    """Provide a sample SCP with wildcard Allow action."""
    return {
        "Id": "p-1234",
        "Arn": "arn:aws:organizations::123456789012:policy/o-123456/p-1234",
        "Name": "WildcardAllowPolicy",
        "Description": "Policy with wildcard Allow",
        "Type": "SERVICE_CONTROL_POLICY",
        "AwsManaged": False,
        "Content": {
            "Version": "2012-10-17",
            "Statement": [
                {"Sid": "AllowAll", "Effect": "Allow", "Action": "*", "Resource": "*"}
            ],
        },
    }


@pytest.fixture
def sample_scp_wildcard_deny():
    """Provide a sample SCP with wildcard Deny action."""
    return {
        "Id": "p-5678",
        "Arn": "arn:aws:organizations::123456789012:policy/o-123456/p-5678",
        "Name": "WildcardDenyPolicy",
        "Description": "Policy with wildcard Deny",
        "Type": "SERVICE_CONTROL_POLICY",
        "AwsManaged": False,
        "Content": {
            "Version": "2012-10-17",
            "Statement": [
                {"Sid": "DenyAll", "Effect": "Deny", "Action": "*", "Resource": "*"}
            ],
        },
    }


@pytest.fixture
def sample_scp_specific_actions():
    """Provide a sample SCP with specific actions."""
    return {
        "Id": "p-9012",
        "Arn": "arn:aws:organizations::123456789012:policy/o-123456/p-9012",
        "Name": "SpecificActionsPolicy",
        "Description": "Policy with specific actions",
        "Type": "SERVICE_CONTROL_POLICY",
        "AwsManaged": False,
        "Content": {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "AllowS3",
                    "Effect": "Allow",
                    "Action": ["s3:GetObject", "s3:PutObject"],
                    "Resource": "*",
                }
            ],
        },
    }


@pytest.fixture
def sample_scp_notaction_wildcard():
    """Provide a sample SCP with wildcard NotAction."""
    return {
        "Id": "p-3456",
        "Arn": "arn:aws:organizations::123456789012:policy/o-123456/p-3456",
        "Name": "NotActionWildcardPolicy",
        "Description": "Policy with wildcard NotAction",
        "Type": "SERVICE_CONTROL_POLICY",
        "AwsManaged": False,
        "Content": {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "NotActionAllow",
                    "Effect": "Allow",
                    "NotAction": "*",
                    "Resource": "*",
                }
            ],
        },
    }


@pytest.fixture
def sample_scp_with_resource():
    """Provide a sample SCP with Resource element (will be ignored)."""
    return {
        "Id": "p-7890",
        "Arn": "arn:aws:organizations::123456789012:policy/o-123456/p-7890",
        "Name": "ResourceElementPolicy",
        "Description": "Policy with Resource element",
        "Type": "SERVICE_CONTROL_POLICY",
        "AwsManaged": False,
        "Content": {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "AllowSpecificResource",
                    "Effect": "Allow",
                    "Action": "s3:GetObject",
                    "Resource": "arn:aws:s3:::my-bucket/*",
                }
            ],
        },
    }


class TestCheckWildcardActions:
    """Test cases for _check_wildcard_actions function."""

    def test_wildcard_allow_action(self, sample_scp_wildcard_allow):
        """Test detection of wildcard Allow actions."""
        findings = _check_wildcard_actions(
            sample_scp_wildcard_allow["Id"],
            sample_scp_wildcard_allow["Name"],
            sample_scp_wildcard_allow["Content"],
        )

        assert len(findings) == 1
        assert findings[0]["severity"] == "CRITICAL"
        assert "wildcard Allow action" in findings[0]["finding"]
        assert "p-1234" in findings[0]["resource_id"]

    def test_wildcard_deny_action(self, sample_scp_wildcard_deny):
        """Test detection of wildcard Deny actions."""
        findings = _check_wildcard_actions(
            sample_scp_wildcard_deny["Id"],
            sample_scp_wildcard_deny["Name"],
            sample_scp_wildcard_deny["Content"],
        )

        assert len(findings) == 1
        assert findings[0]["severity"] == "LOW"
        assert "wildcard Deny action" in findings[0]["finding"]

    def test_specific_actions_no_finding(self, sample_scp_specific_actions):
        """Test that specific actions don't generate findings."""
        findings = _check_wildcard_actions(
            sample_scp_specific_actions["Id"],
            sample_scp_specific_actions["Name"],
            sample_scp_specific_actions["Content"],
        )

        assert len(findings) == 0

    def test_single_action_string(self):
        """Test handling of single action as string."""
        policy_document = {
            "Version": "2012-10-17",
            "Statement": [{"Effect": "Allow", "Action": "*", "Resource": "*"}],
        }

        findings = _check_wildcard_actions("p-test", "TestPolicy", policy_document)

        assert len(findings) == 1
        assert findings[0]["severity"] == "CRITICAL"

    def test_multiple_statements(self):
        """Test handling of multiple statements."""
        policy_document = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": ["s3:GetObject", "s3:PutObject"],
                    "Resource": "*",
                },
                {"Effect": "Allow", "Action": "*", "Resource": "*"},
            ],
        }

        findings = _check_wildcard_actions("p-test", "TestPolicy", policy_document)

        assert len(findings) == 1
        assert findings[0]["severity"] == "CRITICAL"


class TestCheckWildcardNotActions:
    """Test cases for _check_wildcard_notactions function."""

    def test_wildcard_notaction_allow(self, sample_scp_notaction_wildcard):
        """Test detection of wildcard NotAction with Allow."""
        findings = _check_wildcard_notactions(
            sample_scp_notaction_wildcard["Id"],
            sample_scp_notaction_wildcard["Name"],
            sample_scp_notaction_wildcard["Content"],
        )

        assert len(findings) == 1
        assert findings[0]["severity"] == "CRITICAL"
        assert "wildcard NotAction with Allow" in findings[0]["finding"]

    def test_wildcard_notaction_deny(self):
        """Test detection of wildcard NotAction with Deny."""
        policy_document = {
            "Version": "2012-10-17",
            "Statement": [{"Effect": "Deny", "NotAction": "*", "Resource": "*"}],
        }

        findings = _check_wildcard_notactions("p-test", "TestPolicy", policy_document)

        assert len(findings) == 1
        assert findings[0]["severity"] == "HIGH"
        assert "wildcard NotAction with Deny" in findings[0]["finding"]

    def test_no_notaction_no_finding(self, sample_scp_specific_actions):
        """Test that absence of NotAction doesn't generate findings."""
        findings = _check_wildcard_notactions(
            sample_scp_specific_actions["Id"],
            sample_scp_specific_actions["Name"],
            sample_scp_specific_actions["Content"],
        )

        assert len(findings) == 0


class TestCheckMissingResourceConstraints:
    """Test cases for _check_missing_resource_constraints function."""

    def test_resource_element_detected(self, sample_scp_with_resource):
        """Test detection of Resource element in SCP."""
        findings = _check_missing_resource_constraints(
            sample_scp_with_resource["Id"],
            sample_scp_with_resource["Name"],
            sample_scp_with_resource["Content"],
        )

        assert len(findings) == 1
        assert findings[0]["severity"] == "MEDIUM"
        assert "Resource element" in findings[0]["finding"]
        assert "will be ignored" in findings[0]["finding"]

    def test_no_resource_element_no_finding(self, sample_scp_specific_actions):
        """Test that absence of Resource element doesn't generate findings."""
        findings = _check_missing_resource_constraints(
            sample_scp_specific_actions["Id"],
            sample_scp_specific_actions["Name"],
            sample_scp_specific_actions["Content"],
        )

        assert len(findings) == 0


class TestGetAllScps:
    """Test cases for _get_all_scps function."""

    @patch("modules.scp_findings.boto3.client")
    def test_get_all_scps_success(self, mock_boto3_client, sample_scp_wildcard_allow):
        """Test successful retrieval of all SCPs."""
        mock_org = Mock()

        # Mock paginator
        mock_paginator = Mock()
        mock_paginator.paginate.return_value = [
            {
                "Policies": [
                    {
                        "Id": sample_scp_wildcard_allow["Id"],
                        "Arn": sample_scp_wildcard_allow["Arn"],
                        "Name": sample_scp_wildcard_allow["Name"],
                        "Description": sample_scp_wildcard_allow["Description"],
                        "Type": "SERVICE_CONTROL_POLICY",
                        "AwsManaged": False,
                    }
                ]
            }
        ]
        mock_org.get_paginator.return_value = mock_paginator

        mock_org.describe_policy.return_value = {
            "Policy": {
                "PolicySummary": {
                    "Id": sample_scp_wildcard_allow["Id"],
                    "Arn": sample_scp_wildcard_allow["Arn"],
                    "Name": sample_scp_wildcard_allow["Name"],
                    "Description": sample_scp_wildcard_allow["Description"],
                    "Type": "SERVICE_CONTROL_POLICY",
                    "AwsManaged": False,
                },
                "Content": sample_scp_wildcard_allow["Content"],
            }
        }

        mock_boto3_client.return_value = mock_org

        scps = _get_all_scps(mock_org)

        assert len(scps) == 1
        assert scps[0]["Id"] == sample_scp_wildcard_allow["Id"]
        assert scps[0]["Name"] == sample_scp_wildcard_allow["Name"]
        assert "Content" in scps[0]

    @patch("modules.scp_findings.boto3.client")
    def test_get_all_scps_empty(self, mock_boto3_client):
        """Test handling when no SCPs exist."""
        mock_org = Mock()

        mock_paginator = Mock()
        mock_paginator.paginate.return_value = [{"Policies": []}]
        mock_org.get_paginator.return_value = mock_paginator

        mock_boto3_client.return_value = mock_org

        scps = _get_all_scps(mock_org)

        assert len(scps) == 0


class TestGetScpFindings:
    """Test cases for get_scp_findings function."""

    @patch("modules.scp_findings.boto3.client")
    def test_organizations_not_enabled(self, mock_boto3_client):
        """Test handling when AWS Organizations is not enabled."""
        mock_org = Mock()
        mock_org.exceptions.AWSOrganizationsNotInUseException = type(
            "AWSOrganizationsNotInUseException", (Exception,), {}
        )
        mock_org.describe_organization.side_effect = (
            mock_org.exceptions.AWSOrganizationsNotInUseException(
                {}, "DescribeOrganization"
            )
        )
        mock_boto3_client.return_value = mock_org

        findings = get_scp_findings()

        assert len(findings) == 0

    @patch("modules.scp_findings.boto3.client")
    def test_no_root_found(self, mock_boto3_client):
        """Test handling when no organization root is found."""
        mock_org = Mock()
        mock_org.describe_organization.return_value = {
            "Organization": {"Id": "o-123456"}
        }
        mock_org.list_roots.return_value = {"Roots": []}
        mock_boto3_client.return_value = mock_org

        findings = get_scp_findings()

        assert len(findings) == 1
        assert findings[0]["severity"] == "CRITICAL"
        assert "No organization root found" in findings[0]["finding"]

    @patch("modules.scp_findings.boto3.client")
    def test_wildcard_allow_detected(
        self, mock_boto3_client, sample_root, sample_scp_wildcard_allow
    ):
        """Test detection of wildcard Allow in SCPs."""
        mock_org = Mock()
        mock_org.describe_organization.return_value = {
            "Organization": {"Id": "o-123456"}
        }
        mock_org.list_roots.return_value = {"Roots": [sample_root]}

        # Mock paginator for policies
        mock_paginator = Mock()
        mock_paginator.paginate.return_value = [
            {
                "Policies": [
                    {
                        "Id": sample_scp_wildcard_allow["Id"],
                        "Arn": sample_scp_wildcard_allow["Arn"],
                        "Name": sample_scp_wildcard_allow["Name"],
                        "Description": sample_scp_wildcard_allow["Description"],
                        "Type": "SERVICE_CONTROL_POLICY",
                        "AwsManaged": False,
                    }
                ]
            }
        ]
        mock_org.get_paginator.return_value = mock_paginator

        mock_org.describe_policy.return_value = {
            "Policy": {
                "PolicySummary": {
                    "Id": sample_scp_wildcard_allow["Id"],
                    "Arn": sample_scp_wildcard_allow["Arn"],
                    "Name": sample_scp_wildcard_allow["Name"],
                    "Description": sample_scp_wildcard_allow["Description"],
                    "Type": "SERVICE_CONTROL_POLICY",
                    "AwsManaged": False,
                },
                "Content": sample_scp_wildcard_allow["Content"],
            }
        }

        # Mock OU and account checks
        mock_org.list_organizational_units_for_parent.return_value = {
            "OrganizationalUnits": []
        }
        mock_org.list_accounts_for_parent.return_value = {"Accounts": []}
        mock_org.list_targets_for_policy.return_value = {"Targets": []}

        mock_boto3_client.return_value = mock_org

        findings = get_scp_findings()

        assert len(findings) >= 1
        wildcard_findings = [
            f for f in findings if "wildcard Allow action" in f["finding"]
        ]
        assert len(wildcard_findings) == 1
        assert wildcard_findings[0]["severity"] == "CRITICAL"

    @patch("modules.scp_findings.boto3.client")
    def test_generic_exception_handling(self, mock_boto3_client):
        """Test handling of generic exceptions."""
        mock_org = Mock()
        mock_org.describe_organization.side_effect = Exception("Unexpected error")
        mock_boto3_client.return_value = mock_org

        findings = get_scp_findings()

        # Should return a finding about the error
        assert len(findings) >= 1
        assert any("Unable to complete SCP analysis" in f["finding"] for f in findings)

    @patch("modules.scp_findings.boto3.client")
    def test_client_error_handling(self, mock_boto3_client):
        """Test handling of ClientError."""
        mock_org = Mock()
        mock_org.describe_organization.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Not authorized"}},
            "DescribeOrganization",
        )
        mock_boto3_client.return_value = mock_org

        findings = get_scp_findings()

        # Should return a finding about the error
        assert len(findings) >= 1


class TestFindingStructure:
    """Test cases for finding data structure."""

    def test_finding_has_required_fields(self, sample_scp_wildcard_allow):
        """Test that findings have all required fields."""
        findings = _check_wildcard_actions(
            sample_scp_wildcard_allow["Id"],
            sample_scp_wildcard_allow["Name"],
            sample_scp_wildcard_allow["Content"],
        )

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
        assert "evidence" in finding

    def test_finding_values(self, sample_scp_wildcard_allow):
        """Test that finding values are correct."""
        findings = _check_wildcard_actions(
            sample_scp_wildcard_allow["Id"],
            sample_scp_wildcard_allow["Name"],
            sample_scp_wildcard_allow["Content"],
        )

        finding = findings[0]
        assert finding["resource_id"] == "p-1234"
        assert finding["resource_type"] == "SCP"
        assert finding["service"] == "Organizations"
        assert finding["severity"] == "CRITICAL"
        assert "WildcardAllowPolicy" in finding["description"]


class TestEdgeCases:
    """Test cases for edge cases."""

    def test_empty_policy_document(self):
        """Test handling of empty policy document."""
        findings = _check_wildcard_actions("p-test", "TestPolicy", {})
        assert len(findings) == 0

    def test_policy_without_statements(self):
        """Test handling of policy without statements."""
        policy_document = {"Version": "2012-10-17"}
        findings = _check_wildcard_actions("p-test", "TestPolicy", policy_document)
        assert len(findings) == 0

    def test_statement_without_effect(self):
        """Test handling of statement without Effect."""
        policy_document = {
            "Version": "2012-10-17",
            "Statement": [{"Action": "*", "Resource": "*"}],
        }
        findings = _check_wildcard_actions("p-test", "TestPolicy", policy_document)
        assert len(findings) == 0

    def test_statement_without_action(self):
        """Test handling of statement without Action."""
        policy_document = {
            "Version": "2012-10-17",
            "Statement": [{"Effect": "Allow", "Resource": "*"}],
        }
        findings = _check_wildcard_actions("p-test", "TestPolicy", policy_document)
        assert len(findings) == 0

    def test_multiple_wildcards_in_different_statements(self):
        """Test handling of multiple wildcards in different statements."""
        policy_document = {
            "Version": "2012-10-17",
            "Statement": [
                {"Effect": "Allow", "Action": "*", "Resource": "*"},
                {"Effect": "Deny", "Action": "*", "Resource": "*"},
            ],
        }
        findings = _check_wildcard_actions("p-test", "TestPolicy", policy_document)
        assert len(findings) == 2
        assert any(f["severity"] == "CRITICAL" for f in findings)
        assert any(f["severity"] == "LOW" for f in findings)
