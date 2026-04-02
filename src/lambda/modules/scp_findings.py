# SCP Findings Module for AWS Automated Access Review
"""
This module analyzes AWS Organizations Service Control Policies (SCPs) to identify
security risks and compliance issues. It checks for overly permissive policies,
missing SCPs on OUs/accounts, and provides actionable recommendations.
"""
import boto3
from typing import List, Dict, Any


def get_scp_findings() -> List[Dict[str, Any]]:
    """
    Performs SCP security checks and returns a list of findings.

    This function analyzes Service Control Policies in AWS Organizations to identify:
    - Overly permissive SCPs (e.g., wildcard actions)
    - Missing SCPs on OUs or accounts
    - Inconsistent policy enforcement across the organization

    Returns:
        List[Dict[str, Any]]: A list of finding dictionaries, each containing:
            - resource_id: The SCP ID or OU/Account ID
            - resource_type: "SCP", "OU", or "Account"
            - service: "Organizations"
            - severity: "CRITICAL", "HIGH", "MEDIUM", or "LOW"
            - finding: Type of the finding
            - description: Detailed description of the finding
            - recommendation: Actionable recommendation
            - evidence: Evidence supporting the finding

    Note:
        This function gracefully handles cases where AWS Organizations is not enabled
        in the account, returning an empty list in such scenarios.
    """
    findings = []

    try:
        # Initialize Organizations client
        org = boto3.client("organizations")

        # Check if Organizations is enabled
        try:
            org.describe_organization()
        except org.exceptions.AWSOrganizationsNotInUseException:
            print("AWS Organizations is not enabled in this account.")
            return findings

        # Get organization root and OUs
        roots = org.list_roots()["Roots"]
        if not roots:
            findings.append(
                {
                    "resource_id": "Organization",
                    "resource_type": "Organization",
                    "service": "Organizations",
                    "severity": "CRITICAL",
                    "finding": "No organization root found",
                    "description": "Unable to retrieve organization root. Organizations may not be properly configured.",
                    "recommendation": "Verify AWS Organizations is properly configured and has at least one root.",
                    "evidence": "list_roots() returned empty list",
                }
            )
            return findings

        root_id = roots[0]["Id"]

        # Get all SCPs in the organization
        all_scps = _get_all_scps(org)

        # Check for overly permissive SCPs
        for scp in all_scps:
            scp_id = scp["Id"]
            scp_name = scp["Name"]
            policy_document = scp.get("Content", {})

            # Check for wildcard actions
            wildcard_findings = _check_wildcard_actions(
                scp_id, scp_name, policy_document
            )
            findings.extend(wildcard_findings)

            # Check for overly permissive NotAction
            notaction_findings = _check_wildcard_notactions(
                scp_id, scp_name, policy_document
            )
            findings.extend(notaction_findings)

            # Check for missing Resource constraints
            resource_findings = _check_missing_resource_constraints(
                scp_id, scp_name, policy_document
            )
            findings.extend(resource_findings)

        # Get all OUs and check for missing SCPs
        ou_findings = _check_ous_for_missing_scps(org, root_id, all_scps)
        findings.extend(ou_findings)

        # Get all accounts and check for missing SCPs
        account_findings = _check_accounts_for_missing_scps(org, root_id, all_scps)
        findings.extend(account_findings)

        # Check for policy attachment consistency
        consistency_findings = _check_policy_attachment_consistency(
            org, root_id, all_scps
        )
        findings.extend(consistency_findings)

    except Exception as e:
        print(f"Error checking SCPs: {e}")
        findings.append(
            {
                "resource_id": "Organization",
                "resource_type": "Organization",
                "service": "Organizations",
                "severity": "LOW",
                "finding": "Unable to complete SCP analysis",
                "description": f"An error occurred while analyzing Service Control Policies: {str(e)}",
                "recommendation": "Verify IAM permissions for organizations:ListPolicies, organizations:ListTargetsForPolicy, organizations:ListRoots, organizations:ListOrganizationalUnitsForParent, organizations:ListAccountsForParent",
                "evidence": str(e),
            }
        )

    return findings


def _get_all_scps(org) -> List[Dict[str, Any]]:
    """
    Retrieve all Service Control Policies in the organization.

    Args:
        org: Boto3 Organizations client

    Returns:
        List of SCP dictionaries with policy details
    """
    scps = []
    paginator = org.get_paginator("list_policies")

    for page in paginator.paginate(Filter="SERVICE_CONTROL_POLICY"):
        for policy in page["Policies"]:
            policy_id = policy["Id"]
            policy_name = policy["Name"]

            # Get the full policy document
            policy_detail = org.describe_policy(PolicyId=policy_id)
            policy_content = policy_detail["Policy"]["Content"]

            scps.append(
                {
                    "Id": policy_id,
                    "Name": policy_name,
                    "Arn": policy["Arn"],
                    "Description": policy.get("Description", ""),
                    "Content": policy_content,
                }
            )

    return scps


def _check_wildcard_actions(
    scp_id: str, scp_name: str, policy_document: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Check for wildcard (*) actions in SCP statements.

    Args:
        scp_id: The SCP ID
        scp_name: The SCP name
        policy_document: The policy document content

    Returns:
        List of findings for wildcard actions
    """
    findings = []
    statements = policy_document.get("Statement", [])

    for i, statement in enumerate(statements):
        effect = statement.get("Effect", "")
        actions = statement.get("Action", [])

        # Handle both single action and list of actions
        if isinstance(actions, str):
            actions = [actions]

        if effect == "Deny":
            # Check for wildcard Deny (this is actually good - prevents all actions)
            if "*" in actions:
                findings.append(
                    {
                        "resource_id": scp_id,
                        "resource_type": "SCP",
                        "service": "Organizations",
                        "severity": "LOW",
                        "finding": "SCP uses wildcard Deny action",
                        "description": f'SCP "{scp_name}" contains a statement with "Action": "*" and Effect: Deny. This is a restrictive pattern.',
                        "recommendation": "Review if this overly restrictive policy is intentional. Consider specifying exact actions to deny.",
                        "evidence": f'Statement {i+1}: Action: ["*"], Effect: Deny',
                    }
                )

        elif effect == "Allow":
            # Check for wildcard Allow (this is a security risk)
            if "*" in actions:
                findings.append(
                    {
                        "resource_id": scp_id,
                        "resource_type": "SCP",
                        "service": "Organizations",
                        "severity": "CRITICAL",
                        "finding": "SCP uses wildcard Allow action",
                        "description": f'SCP "{scp_name}" contains a statement with "Action": "*" and Effect: Allow. This allows all actions and defeats the purpose of SCPs.',
                        "recommendation": "Replace wildcard actions with specific service and action names. SCPs should be restrictive, not permissive.",
                        "evidence": f'Statement {i+1}: Action: ["*"], Effect: Allow',
                    }
                )

    return findings


def _check_wildcard_notactions(
    scp_id: str, scp_name: str, policy_document: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Check for wildcard (*) in NotAction, which can be overly permissive.

    Args:
        scp_id: The SCP ID
        scp_name: The SCP name
        policy_document: The policy document content

    Returns:
        List of findings for wildcard NotActions
    """
    findings = []
    statements = policy_document.get("Statement", [])

    for i, statement in enumerate(statements):
        effect = statement.get("Effect", "")
        notactions = statement.get("NotAction", [])

        # Handle both single NotAction and list of NotActions
        if isinstance(notactions, str):
            notactions = [notactions]

        if notactions:
            if effect == "Allow" and "*" in notactions:
                findings.append(
                    {
                        "resource_id": scp_id,
                        "resource_type": "SCP",
                        "service": "Organizations",
                        "severity": "CRITICAL",
                        "finding": "SCP uses wildcard NotAction with Allow",
                        "description": f'SCP "{scp_name}" contains "NotAction": "*" with Effect: Allow. This effectively allows all actions except those explicitly denied, which is overly permissive.',
                        "recommendation": "Replace NotAction with explicit Action list. Avoid using NotAction with wildcards in SCPs.",
                        "evidence": f'Statement {i+1}: NotAction: ["*"], Effect: Allow',
                    }
                )
            elif effect == "Deny" and "*" in notactions:
                findings.append(
                    {
                        "resource_id": scp_id,
                        "resource_type": "SCP",
                        "service": "Organizations",
                        "severity": "HIGH",
                        "finding": "SCP uses wildcard NotAction with Deny",
                        "description": f'SCP "{scp_name}" contains "NotAction": "*" with Effect: Deny. This denies nothing and allows all actions.',
                        "recommendation": "Review the intent of this policy. If the goal is to deny specific actions, use Action instead of NotAction.",
                        "evidence": f'Statement {i+1}: NotAction: ["*"], Effect: Deny',
                    }
                )

    return findings


def _check_missing_resource_constraints(
    scp_id: str, scp_name: str, policy_document: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Check for missing Resource constraints in SCP statements.

    Args:
        scp_id: The SCP ID
        scp_name: The SCP name
        policy_document: The policy document content

    Returns:
        List of findings for missing Resource constraints
    """
    findings = []
    statements = policy_document.get("Statement", [])

    for i, statement in enumerate(statements):
        # SCPs don't support Resource element, but if someone tries to use it,
        # it will be ignored. This is a common mistake.
        if "Resource" in statement:
            findings.append(
                {
                    "resource_id": scp_id,
                    "resource_type": "SCP",
                    "service": "Organizations",
                    "severity": "MEDIUM",
                    "finding": "SCP contains Resource element (will be ignored)",
                    "description": f'SCP "{scp_name}" contains a Resource element in statement {i+1}. SCPs do not support the Resource element - it will be ignored.',
                    "recommendation": "Remove the Resource element from SCPs. SCPs control actions across all resources.",
                    "evidence": f'Statement {i+1}: Resource: {statement.get("Resource")}',
                }
            )

    return findings


def _check_ous_for_missing_scps(
    org, root_id: str, all_scps: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Check OUs for missing SCP attachments.

    Args:
        org: Boto3 Organizations client
        root_id: The organization root ID
        all_scps: List of all SCPs in the organization

    Returns:
        List of findings for OUs without SCPs
    """
    findings = []

    def traverse_ous(parent_id: str, path: str = ""):
        """Recursively traverse OUs and check for SCPs."""
        paginator = org.get_paginator("list_organizational_units_for_parent")

        for page in paginator.paginate(ParentId=parent_id):
            for ou in page["OrganizationalUnits"]:
                ou_id = ou["Id"]
                ou_name = ou["Name"]
                full_path = f"{path}/{ou_name}" if path else ou_name

                # Check for attached SCPs
                attached_scps = []
                scp_paginator = org.get_paginator("list_policies_for_target")

                for scp_page in scp_paginator.paginate(
                    TargetId=ou_id, Filter="SERVICE_CONTROL_POLICY"
                ):
                    attached_scps.extend(scp_page["Policies"])

                # If no SCPs are attached and there are SCPs available in the org
                if not attached_scps and all_scps:
                    findings.append(
                        {
                            "resource_id": ou_id,
                            "resource_type": "OU",
                            "service": "Organizations",
                            "severity": "MEDIUM",
                            "finding": "OU has no SCPs attached",
                            "description": f'OU "{full_path}" ({ou_id}) has no Service Control Policies attached. This may lead to inconsistent security controls.',
                            "recommendation": "Consider attaching appropriate SCPs to this OU to enforce consistent security boundaries.",
                            "evidence": f"OU Path: {full_path}, Available SCPs in org: {len(all_scps)}",
                        }
                    )
                elif not attached_scps and not all_scps:
                    findings.append(
                        {
                            "resource_id": ou_id,
                            "resource_type": "OU",
                            "service": "Organizations",
                            "severity": "LOW",
                            "finding": "OU has no SCPs and no SCPs exist in organization",
                            "description": f'OU "{full_path}" ({ou_id}) has no SCPs attached, and no SCPs exist in the organization.',
                            "recommendation": "Consider creating and attaching SCPs to enforce security boundaries across the organization.",
                            "evidence": f"OU Path: {full_path}",
                        }
                    )

                # Recursively check child OUs
                traverse_ous(ou_id, full_path)

    # Start traversal from root
    traverse_ous(root_id)

    return findings


def _check_accounts_for_missing_scps(
    org, root_id: str, all_scps: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Check accounts for missing SCP attachments.

    Args:
        org: Boto3 Organizations client
        root_id: The organization root ID
        all_scps: List of all SCPs in the organization

    Returns:
        List of findings for accounts without SCPs
    """
    findings = []

    def traverse_and_collect_accounts(parent_id: str, path: str = ""):
        """Recursively traverse OUs and collect all accounts."""
        accounts = []

        # Get accounts directly under this parent
        account_paginator = org.get_paginator("list_accounts_for_parent")
        for page in account_paginator.paginate(ParentId=parent_id):
            for account in page["Accounts"]:
                accounts.append({"account": account, "path": path})

        # Get child OUs and recurse
        ou_paginator = org.get_paginator("list_organizational_units_for_parent")
        for page in ou_paginator.paginate(ParentId=parent_id):
            for ou in page["OrganizationalUnits"]:
                ou_name = ou["Name"]
                full_path = f"{path}/{ou_name}" if path else ou_name
                accounts.extend(traverse_and_collect_accounts(ou["Id"], full_path))

        return accounts

    # Collect all accounts
    all_accounts = traverse_and_collect_accounts(root_id)

    # Check each account for SCPs
    for account_info in all_accounts:
        account = account_info["account"]
        account_id = account["Id"]
        account_name = account.get("Name", "Unknown")
        account_email = account.get("Email", "Unknown")
        path = account_info["path"]

        # Check for attached SCPs
        attached_scps = []
        scp_paginator = org.get_paginator("list_policies_for_target")

        for scp_page in scp_paginator.paginate(
            TargetId=account_id, Filter="SERVICE_CONTROL_POLICY"
        ):
            attached_scps.extend(scp_page["Policies"])

        # If no SCPs are attached and there are SCPs available in the org
        if not attached_scps and all_scps:
            findings.append(
                {
                    "resource_id": account_id,
                    "resource_type": "Account",
                    "service": "Organizations",
                    "severity": "MEDIUM",
                    "finding": "Account has no SCPs attached",
                    "description": f'Account "{account_name}" ({account_id}, {account_email}) at path "{path}" has no Service Control Policies attached.',
                    "recommendation": "Consider attaching appropriate SCPs to this account or its parent OU to enforce consistent security boundaries.",
                    "evidence": f"Account: {account_name}, Email: {account_email}, Path: {path}, Available SCPs in org: {len(all_scps)}",
                }
            )

    return findings


def _check_policy_attachment_consistency(
    org, root_id: str, all_scps: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Check for consistency in SCP attachments across the organization.

    Args:
        org: Boto3 Organizations client
        root_id: The organization root ID
        all_scps: List of all SCPs in the organization

    Returns:
        List of findings for policy attachment inconsistencies
    """
    findings = []

    # Check if any SCPs are not attached anywhere
    if all_scps:
        for scp in all_scps:
            scp_id = scp["Id"]
            scp_name = scp["Name"]

            # Get all targets for this SCP
            targets = []
            target_paginator = org.get_paginator("list_targets_for_policy")

            for page in target_paginator.paginate(PolicyId=scp_id):
                targets.extend(page["Targets"])

            if not targets:
                findings.append(
                    {
                        "resource_id": scp_id,
                        "resource_type": "SCP",
                        "service": "Organizations",
                        "severity": "LOW",
                        "finding": "SCP is not attached to any target",
                        "description": f'SCP "{scp_name}" ({scp_id}) exists but is not attached to any root, OU, or account.',
                        "recommendation": "Attach this SCP to appropriate targets if it should be enforced, or delete it if it is no longer needed.",
                        "evidence": f"SCP Name: {scp_name}, SCP ID: {scp_id}",
                    }
                )

    return findings
