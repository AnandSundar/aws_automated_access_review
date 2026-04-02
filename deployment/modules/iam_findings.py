# IAM Findings Module for AWS Automated Access Review
import boto3
from datetime import datetime, timezone, timedelta


def get_iam_findings():
    """
    Performs IAM security checks and returns a list of findings.
    """
    findings = []
    iam = boto3.client("iam")

    # 1. Password Policy Check
    try:
        policy = iam.get_account_password_policy()["PasswordPolicy"]
        min_length = policy.get("MinimumPasswordLength", 0)
        require_symbols = policy.get("RequireSymbols", False)

        if min_length < 14 or not require_symbols:
            findings.append(
                {
                    "resource_id": "AccountPasswordPolicy",
                    "resource_type": "IAM_ACCOUNT_POLICY",
                    "service": "IAM",
                    "severity": "HIGH",
                    "finding": f"Password policy is weak (Length: {min_length}, Symbols: {require_symbols})",
                    "recommendation": "Update password policy to require at least 14 characters and symbols.",
                }
            )
    except iam.exceptions.NoSuchEntityException:
        findings.append(
            {
                "resource_id": "AccountPasswordPolicy",
                "resource_type": "IAM_ACCOUNT_POLICY",
                "service": "IAM",
                "severity": "HIGH",
                "finding": "No custom password policy defined.",
                "recommendation": "Define a password policy requiring at least 14 characters and symbols.",
            }
        )

    # 2. Root Account Access Keys
    try:
        summary = iam.get_account_summary()["SummaryMap"]
        if summary.get("AccountAccessKeysPresent", 0) > 0:
            findings.append(
                {
                    "resource_id": "RootAccount",
                    "resource_type": "IAM_ROOT",
                    "service": "IAM",
                    "severity": "CRITICAL",
                    "finding": "Root account has active access keys.",
                    "recommendation": "Delete root access keys and use IAM users/roles instead.",
                }
            )
    except Exception as e:
        print(f"Error checking root keys: {e}")

    # 3. User Checks (MFA, Admin, Console Activity)
    paginator = iam.get_paginator("list_users")
    for page in paginator.paginate():
        for user in page["Users"]:
            user_name = user["UserName"]

            # Check MFA
            mfa_devices = iam.list_mfa_devices(UserName=user_name)["MFADevices"]
            if not mfa_devices:
                findings.append(
                    {
                        "resource_id": user_name,
                        "resource_type": "IAM_USER",
                        "service": "IAM",
                        "severity": "CRITICAL",
                        "finding": f"User {user_name} is missing MFA.",
                        "recommendation": "Enable MFA for this user immediately.",
                    }
                )

            # Check AdministratorAccess
            attached_policies = iam.list_attached_user_policies(UserName=user_name)[
                "AttachedPolicies"
            ]
            is_admin = any(p["PolicyName"] == "AdministratorAccess" for p in attached_policies)
            if is_admin:
                findings.append(
                    {
                        "resource_id": user_name,
                        "resource_type": "IAM_USER",
                        "service": "IAM",
                        "severity": "HIGH",
                        "finding": f"User {user_name} has AdministratorAccess.",
                        "recommendation": "Review if this user strictly requires full administrator privileges.",
                    }
                )

            # Check Console Activity (>90 days)
            if "PasswordLastUsed" in user:
                last_used = user["PasswordLastUsed"]
                if (datetime.now(timezone.utc) - last_used).days > 90:
                    findings.append(
                        {
                            "resource_id": user_name,
                            "resource_type": "IAM_USER",
                            "service": "IAM",
                            "severity": "MEDIUM",
                            "finding": f"User {user_name} has not used the console in >90 days.",
                            "recommendation": "Consider disabling console access for inactive users.",
                        }
                    )

    # 4. Unused Roles (>90 days)
    role_paginator = iam.get_paginator("list_roles")
    for page in role_paginator.paginate():
        for role in page["Roles"]:
            role_name = role["RoleName"]

            # Skip AWS service roles
            if role["Path"].startswith("/aws-service-role/"):
                continue

            last_used_info = role.get("RoleLastUsed", {})
            last_used_date = last_used_info.get("LastUsedDate")

            if last_used_date:
                if (datetime.now(timezone.utc) - last_used_date).days > 90:
                    findings.append(
                        {
                            "resource_id": role_name,
                            "resource_type": "IAM_ROLE",
                            "service": "IAM",
                            "severity": "MEDIUM",
                            "finding": f"Role {role_name} has not been used in >90 days.",
                            "recommendation": "Review and delete unused IAM roles.",
                        }
                    )
            else:
                # If never used, check creation date
                create_date = role["CreateDate"]
                if (datetime.now(timezone.utc) - create_date).days > 90:
                    findings.append(
                        {
                            "resource_id": role_name,
                            "resource_type": "IAM_ROLE",
                            "service": "IAM",
                            "severity": "MEDIUM",
                            "finding": f"Role {role_name} was created >90 days ago and never used.",
                            "recommendation": "Delete roles that have never been used.",
                        }
                    )

    return findings
