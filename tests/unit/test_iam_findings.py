"""
Unit tests for IAM findings module.

Tests the get_iam_findings function in src/lambda/modules/iam_findings.py
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone, timedelta
from botocore.exceptions import ClientError

# Add the src/lambda directory to the path so we can import the modules
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src/lambda"))

from modules.iam_findings import get_iam_findings


@pytest.fixture
def mock_iam_client():
    """Create a mock IAM client."""
    client = Mock()
    return client


@pytest.fixture
def sample_password_policy():
    """Provide a sample password policy."""
    return {
        "PasswordPolicy": {
            "MinimumPasswordLength": 12,
            "RequireSymbols": False,
            "RequireNumbers": True,
            "RequireUppercaseCharacters": True,
            "RequireLowercaseCharacters": True,
        }
    }


@pytest.fixture
def strong_password_policy():
    """Provide a strong password policy."""
    return {
        "PasswordPolicy": {
            "MinimumPasswordLength": 16,
            "RequireSymbols": True,
            "RequireNumbers": True,
            "RequireUppercaseCharacters": True,
            "RequireLowercaseCharacters": True,
        }
    }


@pytest.fixture
def sample_users():
    """Provide sample IAM users."""
    return {
        "Users": [
            {
                "UserName": "user-without-mfa",
                "UserId": "AIDACKCEVSQ6C2EXAMPLE",
                "Arn": "arn:aws:iam::123456789012:user/user-without-mfa",
                "CreateDate": datetime(2024, 1, 1, tzinfo=timezone.utc),
                "PasswordLastUsed": datetime(2024, 1, 15, tzinfo=timezone.utc),
            },
            {
                "UserName": "user-with-admin",
                "UserId": "AIDACKCEVSQ6C2EXAMPLE2",
                "Arn": "arn:aws:iam::123456789012:user/user-with-admin",
                "CreateDate": datetime(2024, 1, 1, tzinfo=timezone.utc),
                "PasswordLastUsed": datetime(2024, 1, 15, tzinfo=timezone.utc),
            },
            {
                "UserName": "user-inactive",
                "UserId": "AIDACKCEVSQ6C2EXAMPLE3",
                "Arn": "arn:aws:iam::123456789012:user/user-inactive",
                "CreateDate": datetime(2023, 1, 1, tzinfo=timezone.utc),
                "PasswordLastUsed": datetime(2023, 6, 1, tzinfo=timezone.utc),  # >90 days ago
            },
            {
                "UserName": "user-good",
                "UserId": "AIDACKCEVSQ6C2EXAMPLE4",
                "Arn": "arn:aws:iam::123456789012:user/user-good",
                "CreateDate": datetime(2024, 1, 1, tzinfo=timezone.utc),
                "PasswordLastUsed": datetime(2024, 1, 15, tzinfo=timezone.utc),
            },
        ]
    }


@pytest.fixture
def sample_roles():
    """Provide sample IAM roles."""
    return {
        "Roles": [
            {
                "RoleName": "unused-role",
                "RoleId": "AROACKCEVSQ6C2EXAMPLE",
                "Arn": "arn:aws:iam::123456789012:role/unused-role",
                "CreateDate": datetime(2023, 1, 1, tzinfo=timezone.utc),
                "Path": "/",
                "RoleLastUsed": {
                    "LastUsedDate": datetime(2023, 6, 1, tzinfo=timezone.utc),
                    "Region": "us-east-1",
                },
            },
            {
                "RoleName": "never-used-role",
                "RoleId": "AROACKCEVSQ6C2EXAMPLE2",
                "Arn": "arn:aws:iam::123456789012:role/never-used-role",
                "CreateDate": datetime(2023, 1, 1, tzinfo=timezone.utc),
                "Path": "/",
            },
            {
                "RoleName": "aws-service-role/test",
                "RoleId": "AROACKCEVSQ6C2EXAMPLE3",
                "Arn": "arn:aws:iam::123456789012:role/aws-service-role/test",
                "CreateDate": datetime(2023, 1, 1, tzinfo=timezone.utc),
                "Path": "/aws-service-role/",
            },
            {
                "RoleName": "active-role",
                "RoleId": "AROACKCEVSQ6C2EXAMPLE4",
                "Arn": "arn:aws:iam::123456789012:role/active-role",
                "CreateDate": datetime(2024, 1, 1, tzinfo=timezone.utc),
                "Path": "/",
                "RoleLastUsed": {
                    "LastUsedDate": datetime(2024, 1, 15, tzinfo=timezone.utc),
                    "Region": "us-east-1",
                },
            },
        ]
    }


class TestPasswordPolicyCheck:
    """Test cases for password policy checks."""

    @patch("modules.iam_findings.boto3.client")
    def test_weak_password_policy(
        self, mock_boto3_client, sample_password_policy, sample_users, sample_roles
    ):
        """Test detection of weak password policy."""
        mock_iam = Mock()
        mock_iam.get_account_password_policy.return_value = sample_password_policy
        mock_iam.get_account_summary.return_value = {"SummaryMap": {"AccountAccessKeysPresent": 0}}
        mock_iam.get_paginator.return_value.paginate.return_value = [sample_users]
        mock_iam.list_mfa_devices.return_value = {"MFADevices": []}
        mock_iam.list_attached_user_policies.return_value = {"AttachedPolicies": []}
        mock_iam.get_paginator.return_value.paginate.return_value = [sample_roles]
        mock_boto3_client.return_value = mock_iam

        findings = get_iam_findings()

        password_policy_findings = [
            f for f in findings if f["resource_id"] == "AccountPasswordPolicy"
        ]
        assert len(password_policy_findings) == 1
        assert password_policy_findings[0]["severity"] == "HIGH"
        assert "Password policy is weak" in password_policy_findings[0]["finding"]

    @patch("modules.iam_findings.boto3.client")
    def test_strong_password_policy(
        self, mock_boto3_client, strong_password_policy, sample_users, sample_roles
    ):
        """Test that strong password policy doesn't generate findings."""
        mock_iam = Mock()
        mock_iam.get_account_password_policy.return_value = strong_password_policy
        mock_iam.get_account_summary.return_value = {"SummaryMap": {"AccountAccessKeysPresent": 0}}
        mock_iam.get_paginator.return_value.paginate.return_value = [sample_users]
        mock_iam.list_mfa_devices.return_value = {"MFADevices": []}
        mock_iam.list_attached_user_policies.return_value = {"AttachedPolicies": []}
        mock_iam.get_paginator.return_value.paginate.return_value = [sample_roles]
        mock_boto3_client.return_value = mock_iam

        findings = get_iam_findings()

        password_policy_findings = [
            f for f in findings if f["resource_id"] == "AccountPasswordPolicy"
        ]
        assert len(password_policy_findings) == 0

    @patch("modules.iam_findings.boto3.client")
    def test_no_password_policy(self, mock_boto3_client, sample_users, sample_roles):
        """Test detection when no custom password policy exists."""
        mock_iam = Mock()
        mock_iam.get_account_password_policy.side_effect = (
            mock_iam.exceptions.NoSuchEntityException({}, "GetAccountPasswordPolicy")
        )
        mock_iam.get_account_summary.return_value = {"SummaryMap": {"AccountAccessKeysPresent": 0}}
        mock_iam.get_paginator.return_value.paginate.return_value = [sample_users]
        mock_iam.list_mfa_devices.return_value = {"MFADevices": []}
        mock_iam.list_attached_user_policies.return_value = {"AttachedPolicies": []}
        mock_iam.get_paginator.return_value.paginate.return_value = [sample_roles]
        mock_boto3_client.return_value = mock_iam

        findings = get_iam_findings()

        password_policy_findings = [
            f for f in findings if f["resource_id"] == "AccountPasswordPolicy"
        ]
        assert len(password_policy_findings) == 1
        assert "No custom password policy defined" in password_policy_findings[0]["finding"]


class TestRootAccountAccessKeys:
    """Test cases for root account access key checks."""

    @patch("modules.iam_findings.boto3.client")
    def test_root_account_has_access_keys(
        self, mock_boto3_client, strong_password_policy, sample_users, sample_roles
    ):
        """Test detection of root account access keys."""
        mock_iam = Mock()
        mock_iam.get_account_password_policy.return_value = strong_password_policy
        mock_iam.get_account_summary.return_value = {"SummaryMap": {"AccountAccessKeysPresent": 1}}
        mock_iam.get_paginator.return_value.paginate.return_value = [sample_users]
        mock_iam.list_mfa_devices.return_value = {"MFADevices": []}
        mock_iam.list_attached_user_policies.return_value = {"AttachedPolicies": []}
        mock_iam.get_paginator.return_value.paginate.return_value = [sample_roles]
        mock_boto3_client.return_value = mock_iam

        findings = get_iam_findings()

        root_findings = [f for f in findings if f["resource_id"] == "RootAccount"]
        assert len(root_findings) == 1
        assert root_findings[0]["severity"] == "CRITICAL"
        assert "Root account has active access keys" in root_findings[0]["finding"]

    @patch("modules.iam_findings.boto3.client")
    def test_root_account_no_access_keys(
        self, mock_boto3_client, strong_password_policy, sample_users, sample_roles
    ):
        """Test when root account has no access keys."""
        mock_iam = Mock()
        mock_iam.get_account_password_policy.return_value = strong_password_policy
        mock_iam.get_account_summary.return_value = {"SummaryMap": {"AccountAccessKeysPresent": 0}}
        mock_iam.get_paginator.return_value.paginate.return_value = [sample_users]
        mock_iam.list_mfa_devices.return_value = {"MFADevices": []}
        mock_iam.list_attached_user_policies.return_value = {"AttachedPolicies": []}
        mock_iam.get_paginator.return_value.paginate.return_value = [sample_roles]
        mock_boto3_client.return_value = mock_iam

        findings = get_iam_findings()

        root_findings = [f for f in findings if f["resource_id"] == "RootAccount"]
        assert len(root_findings) == 0


class TestUserMFA:
    """Test cases for user MFA checks."""

    @patch("modules.iam_findings.boto3.client")
    def test_user_without_mfa(
        self, mock_boto3_client, strong_password_policy, sample_users, sample_roles
    ):
        """Test detection of users without MFA."""
        mock_iam = Mock()
        mock_iam.get_account_password_policy.return_value = strong_password_policy
        mock_iam.get_account_summary.return_value = {"SummaryMap": {"AccountAccessKeysPresent": 0}}

        # Mock paginator for users
        mock_paginator = Mock()
        mock_paginator.paginate.return_value = [sample_users]
        mock_iam.get_paginator.return_value = mock_paginator

        # Mock MFA devices - user-without-mfa has no MFA
        def list_mfa_devices_side_effect(UserName):
            if UserName == "user-without-mfa":
                return {"MFADevices": []}
            elif UserName == "user-good":
                return {"MFADevices": [{"SerialNumber": "arn:aws:iam::123456789012:mfa/user-good"}]}
            return {"MFADevices": []}

        mock_iam.list_mfa_devices.side_effect = list_mfa_devices_side_effect
        mock_iam.list_attached_user_policies.return_value = {"AttachedPolicies": []}
        mock_iam.get_paginator.return_value.paginate.return_value = [sample_roles]
        mock_boto3_client.return_value = mock_iam

        findings = get_iam_findings()

        mfa_findings = [f for f in findings if "MFA" in f["finding"] and "missing" in f["finding"]]
        assert len(mfa_findings) >= 1
        assert any(f["resource_id"] == "user-without-mfa" for f in mfa_findings)


class TestUserAdminAccess:
    """Test cases for user administrator access checks."""

    @patch("modules.iam_findings.boto3.client")
    def test_user_with_admin_access(
        self, mock_boto3_client, strong_password_policy, sample_users, sample_roles
    ):
        """Test detection of users with AdministratorAccess."""
        mock_iam = Mock()
        mock_iam.get_account_password_policy.return_value = strong_password_policy
        mock_iam.get_account_summary.return_value = {"SummaryMap": {"AccountAccessKeysPresent": 0}}

        mock_paginator = Mock()
        mock_paginator.paginate.return_value = [sample_users]
        mock_iam.get_paginator.return_value = mock_paginator

        mock_iam.list_mfa_devices.return_value = {"MFADevices": []}

        def list_attached_user_policies_side_effect(UserName):
            if UserName == "user-with-admin":
                return {
                    "AttachedPolicies": [
                        {
                            "PolicyName": "AdministratorAccess",
                            "PolicyArn": "arn:aws:iam::aws:policy/AdministratorAccess",
                        }
                    ]
                }
            return {"AttachedPolicies": []}

        mock_iam.list_attached_user_policies.side_effect = list_attached_user_policies_side_effect
        mock_iam.get_paginator.return_value.paginate.return_value = [sample_roles]
        mock_boto3_client.return_value = mock_iam

        findings = get_iam_findings()

        admin_findings = [f for f in findings if "AdministratorAccess" in f["finding"]]
        assert len(admin_findings) >= 1
        assert any(f["resource_id"] == "user-with-admin" for f in admin_findings)


class TestUserConsoleActivity:
    """Test cases for user console activity checks."""

    @patch("modules.iam_findings.boto3.client")
    def test_inactive_user(
        self, mock_boto3_client, strong_password_policy, sample_users, sample_roles
    ):
        """Test detection of inactive users (>90 days)."""
        mock_iam = Mock()
        mock_iam.get_account_password_policy.return_value = strong_password_policy
        mock_iam.get_account_summary.return_value = {"SummaryMap": {"AccountAccessKeysPresent": 0}}

        mock_paginator = Mock()
        mock_paginator.paginate.return_value = [sample_users]
        mock_iam.get_paginator.return_value = mock_paginator

        mock_iam.list_mfa_devices.return_value = {"MFADevices": []}
        mock_iam.list_attached_user_policies.return_value = {"AttachedPolicies": []}
        mock_iam.get_paginator.return_value.paginate.return_value = [sample_roles]
        mock_boto3_client.return_value = mock_iam

        findings = get_iam_findings()

        inactive_findings = [
            f for f in findings if "not used the console in >90 days" in f["finding"]
        ]
        assert len(inactive_findings) >= 1
        assert any(f["resource_id"] == "user-inactive" for f in inactive_findings)


class TestUnusedRoles:
    """Test cases for unused role checks."""

    @patch("modules.iam_findings.boto3.client")
    def test_unused_role(
        self, mock_boto3_client, strong_password_policy, sample_users, sample_roles
    ):
        """Test detection of unused roles (>90 days)."""
        mock_iam = Mock()
        mock_iam.get_account_password_policy.return_value = strong_password_policy
        mock_iam.get_account_summary.return_value = {"SummaryMap": {"AccountAccessKeysPresent": 0}}
        mock_iam.get_paginator.return_value.paginate.return_value = [sample_users]
        mock_iam.list_mfa_devices.return_value = {"MFADevices": []}
        mock_iam.list_attached_user_policies.return_value = {"AttachedPolicies": []}

        mock_paginator = Mock()
        mock_paginator.paginate.return_value = [sample_roles]
        mock_iam.get_paginator.return_value = mock_paginator
        mock_boto3_client.return_value = mock_iam

        findings = get_iam_findings()

        unused_role_findings = [f for f in findings if "not been used in >90 days" in f["finding"]]
        assert len(unused_role_findings) >= 1
        assert any(f["resource_id"] == "unused-role" for f in unused_role_findings)

    @patch("modules.iam_findings.boto3.client")
    def test_never_used_role(
        self, mock_boto3_client, strong_password_policy, sample_users, sample_roles
    ):
        """Test detection of roles never used (>90 days old)."""
        mock_iam = Mock()
        mock_iam.get_account_password_policy.return_value = strong_password_policy
        mock_iam.get_account_summary.return_value = {"SummaryMap": {"AccountAccessKeysPresent": 0}}
        mock_iam.get_paginator.return_value.paginate.return_value = [sample_users]
        mock_iam.list_mfa_devices.return_value = {"MFADevices": []}
        mock_iam.list_attached_user_policies.return_value = {"AttachedPolicies": []}

        mock_paginator = Mock()
        mock_paginator.paginate.return_value = [sample_roles]
        mock_iam.get_paginator.return_value = mock_paginator
        mock_boto3_client.return_value = mock_iam

        findings = get_iam_findings()

        never_used_findings = [f for f in findings if "never used" in f["finding"]]
        assert len(never_used_findings) >= 1
        assert any(f["resource_id"] == "never-used-role" for f in never_used_findings)

    @patch("modules.iam_findings.boto3.client")
    def test_aws_service_role_skipped(
        self, mock_boto3_client, strong_password_policy, sample_users, sample_roles
    ):
        """Test that AWS service roles are skipped."""
        mock_iam = Mock()
        mock_iam.get_account_password_policy.return_value = strong_password_policy
        mock_iam.get_account_summary.return_value = {"SummaryMap": {"AccountAccessKeysPresent": 0}}
        mock_iam.get_paginator.return_value.paginate.return_value = [sample_users]
        mock_iam.list_mfa_devices.return_value = {"MFADevices": []}
        mock_iam.list_attached_user_policies.return_value = {"AttachedPolicies": []}

        mock_paginator = Mock()
        mock_paginator.paginate.return_value = [sample_roles]
        mock_iam.get_paginator.return_value = mock_paginator
        mock_boto3_client.return_value = mock_iam

        findings = get_iam_findings()

        # Should not have findings for aws-service-role
        service_role_findings = [f for f in findings if f["resource_id"] == "aws-service-role/test"]
        assert len(service_role_findings) == 0


class TestErrorHandling:
    """Test cases for error handling."""

    @patch("modules.iam_findings.boto3.client")
    def test_client_error_on_account_summary(self, mock_boto3_client, strong_password_policy):
        """Test handling of ClientError when getting account summary."""
        mock_iam = Mock()
        mock_iam.get_account_password_policy.return_value = strong_password_policy
        mock_iam.get_account_summary.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Not authorized"}},
            "GetAccountSummary",
        )
        mock_boto3_client.return_value = mock_iam

        # Should not raise an exception, just log the error
        findings = get_iam_findings()
        assert isinstance(findings, list)

    @patch("modules.iam_findings.boto3.client")
    def test_generic_exception(self, mock_boto3_client, strong_password_policy):
        """Test handling of generic exceptions."""
        mock_iam = Mock()
        mock_iam.get_account_password_policy.return_value = strong_password_policy
        mock_iam.get_account_summary.side_effect = Exception("Unexpected error")
        mock_boto3_client.return_value = mock_iam

        # Should not raise an exception
        findings = get_iam_findings()
        assert isinstance(findings, list)


class TestIntegration:
    """Integration tests for multiple checks."""

    @patch("modules.iam_findings.boto3.client")
    def test_multiple_findings_generated(
        self, mock_boto3_client, sample_password_policy, sample_users, sample_roles
    ):
        """Test that multiple findings are generated correctly."""
        mock_iam = Mock()
        mock_iam.get_account_password_policy.return_value = sample_password_policy
        mock_iam.get_account_summary.return_value = {"SummaryMap": {"AccountAccessKeysPresent": 1}}

        mock_paginator = Mock()
        mock_paginator.paginate.return_value = [sample_users]
        mock_iam.get_paginator.return_value = mock_paginator

        mock_iam.list_mfa_devices.return_value = {"MFADevices": []}

        def list_attached_user_policies_side_effect(UserName):
            if UserName == "user-with-admin":
                return {
                    "AttachedPolicies": [
                        {
                            "PolicyName": "AdministratorAccess",
                            "PolicyArn": "arn:aws:iam::aws:policy/AdministratorAccess",
                        }
                    ]
                }
            return {"AttachedPolicies": []}

        mock_iam.list_attached_user_policies.side_effect = list_attached_user_policies_side_effect

        mock_paginator_roles = Mock()
        mock_paginator_roles.paginate.return_value = [sample_roles]
        mock_iam.get_paginator.return_value = mock_paginator_roles
        mock_boto3_client.return_value = mock_iam

        findings = get_iam_findings()

        # Should have findings for:
        # - Weak password policy
        # - Root account keys
        # - Users without MFA
        # - User with admin access
        # - Inactive user
        # - Unused roles
        assert len(findings) > 0

        # Check for specific finding types
        finding_types = [f["finding"] for f in findings]
        assert any("Password policy" in ft for ft in finding_types)
        assert any("Root account" in ft for ft in finding_types)
        assert any("MFA" in ft for ft in finding_types)
