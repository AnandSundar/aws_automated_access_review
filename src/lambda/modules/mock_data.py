# Mock Data Module for AWS Automated Access Review - Dry Run Mode
# Provides realistic, professional-looking findings for interview demonstrations
from datetime import datetime, timezone, timedelta


def get_mock_iam_findings():
    """
    Returns realistic IAM security findings for demo purposes.
    """
    findings = [
        # CRITICAL Findings
        {
            "resource_id": "RootAccount",
            "resource_type": "IAM_ROOT",
            "service": "IAM",
            "severity": "CRITICAL",
            "finding": "Root account has active access keys present in environment.",
            "recommendation": "Immediately delete root account access keys. Use IAM users with temporary credentials instead.",
        },
        {
            "resource_id": "james.wilson@company.com",
            "resource_type": "IAM_USER",
            "service": "IAM",
            "severity": "CRITICAL",
            "finding": "User 'james.wilson@company.com' is missing MFA device enrollment.",
            "recommendation": "Enable MFA immediately for this user. This is a critical security risk.",
        },
        {
            "resource_id": "deploy-service-account",
            "resource_type": "IAM_USER",
            "service": "IAM",
            "severity": "CRITICAL",
            "finding": "Service account 'deploy-service-account' has console password with no MFA enabled.",
            "recommendation": "Enable MFA for programmatic service accounts or remove console access.",
        },
        {
            "resource_id": "SecurityAuditRole-Production",
            "resource_type": "IAM_ROLE",
            "service": "IAM",
            "severity": "CRITICAL",
            "finding": "Role 'SecurityAuditRole-Production' grants AdministratorAccess policy.",
            "recommendation": "Review and restrict permissions to only audit-related actions.",
        },
        # HIGH Findings
        {
            "resource_id": "admin-deploy-user",
            "resource_type": "IAM_USER",
            "service": "IAM",
            "severity": "HIGH",
            "finding": "User 'admin-deploy-user' has AdministratorAccess policy attached.",
            "recommendation": "Implement least privilege - create role-specific policies.",
        },
        {
            "resource_id": "DevOpsTeamPolicy",
            "resource_type": "IAM_POLICY",
            "service": "IAM",
            "severity": "HIGH",
            "finding": "Customer managed policy 'DevOpsTeamPolicy' allows s3:* on all resources.",
            "recommendation": "Restrict S3 permissions to specific buckets required for operations.",
        },
        {
            "resource_id": "AccountPasswordPolicy",
            "resource_type": "IAM_ACCOUNT_POLICY",
            "service": "IAM",
            "severity": "HIGH",
            "finding": "Password policy minimum length is 8 characters (recommend 14+).",
            "recommendation": "Update password policy to require minimum 14 characters with complexity.",
        },
        {
            "resource_id": "legacy-api-user",
            "resource_type": "IAM_USER",
            "service": "IAM",
            "severity": "HIGH",
            "finding": "User 'legacy-api-user' has unused access key created 180 days ago.",
            "recommendation": "Delete unused access keys. Implement key rotation every 90 days.",
        },
        {
            "resource_id": "CrossAccountAuditRole",
            "resource_type": "IAM_ROLE",
            "service": "IAM",
            "severity": "HIGH",
            "finding": "Cross-account role 'CrossAccountAuditRole' trusts 12 external accounts.",
            "recommendation": "Review and minimize external account access. Implement periodic access reviews.",
        },
        # MEDIUM Findings
        {
            "resource_id": "former-employee-0423",
            "resource_type": "IAM_USER",
            "service": "IAM",
            "severity": "MEDIUM",
            "finding": "User 'former-employee-0423' has not accessed console in 95 days.",
            "recommendation": "Disable or delete this inactive user account.",
        },
        {
            "resource_id": "PipelineExecutionRole",
            "resource_type": "IAM_ROLE",
            "service": "IAM",
            "severity": "MEDIUM",
            "finding": "Role 'PipelineExecutionRole' has not been used in 120 days.",
            "recommendation": "Review and delete unused IAM roles to reduce attack surface.",
        },
        {
            "resource_id": "DatabaseBackupRole",
            "resource_type": "IAM_ROLE",
            "service": "IAM",
            "severity": "MEDIUM",
            "finding": "Role 'DatabaseBackupRole' created 200 days ago and never used.",
            "recommendation": "Delete role if no longer needed or investigate deployment issues.",
        },
        {
            "resource_id": "StagingAccessRole",
            "resource_type": "IAM_ROLE",
            "service": "IAM",
            "severity": "MEDIUM",
            "finding": "Role 'StagingAccessRole' allows full EC2 access without conditions.",
            "recommendation": "Add condition keys to restrict to specific instances or tags.",
        },
        # LOW Findings
        {
            "resource_id": "ReadOnlyReportUser",
            "resource_type": "IAM_USER",
            "service": "IAM",
            "severity": "LOW",
            "finding": "User 'ReadOnlyReportUser' has password last used 60 days ago.",
            "recommendation": "Consider enabling password expiration policy for unused accounts.",
        },
        {
            "resource_id": "SupportCaseRole",
            "resource_type": "IAM_ROLE",
            "service": "IAM",
            "severity": "LOW",
            "finding": "Role 'SupportCaseRole' has not been used in 45 days.",
            "recommendation": "Review if AWS support access is still required.",
        },
    ]

    return findings


def get_mock_securityhub_findings():
    """
    Returns realistic Security Hub findings for demo purposes.
    Includes CIS benchmarks, security best practices, and compliance findings.
    """
    findings = [
        # CRITICAL - CIS Benchmarks
        {
            "resource_id": "arn:aws:iam::123456789012:root",
            "resource_type": "AWS_ACCOUNT",
            "service": "SecurityHub",
            "severity": "CRITICAL",
            "finding": "[CIS.1.1] Root account password not meeting complexity requirements.",
            "recommendation": "Enable strong password policy for root account with 14+ characters.",
        },
        {
            "resource_id": "arn:aws:iam::123456789012:user/admin",
            "resource_type": "IAM_USER",
            "service": "SecurityHub",
            "severity": "CRITICAL",
            "finding": "[CIS.1.2] MFA not enabled for root account.",
            "recommendation": "Enable MFA for root account immediately using hardware or virtual MFA.",
        },
        # HIGH - Security Best Practices
        {
            "resource_id": "arn:aws:s3:::company-sensitive-data",
            "resource_type": "S3_BUCKET",
            "service": "SecurityHub",
            "severity": "HIGH",
            "finding": "[Security.BestPractices] S3 bucket 'company-sensitive-data' allows public read access.",
            "recommendation": "Enable S3 Block Public Access and review bucket policies.",
        },
        {
            "resource_id": "arn:aws:ec2:us-east-1:123456789012:security-group/sg-0abc1234567890def",
            "resource_type": "SECURITY_GROUP",
            "service": "SecurityHub",
            "severity": "HIGH",
            "finding": "[Security.BestPractices] Security group allows unrestricted inbound traffic (0.0.0.0/0) on port 22.",
            "recommendation": "Restrict SSH access to specific IP ranges or use Systems Manager Session Manager.",
        },
        {
            "resource_id": "arn:aws:logs:us-east-1:123456789012:log-group:/aws/lambda/prod-*",
            "resource_type": "CLOUDWATCH_LOG",
            "service": "SecurityHub",
            "severity": "HIGH",
            "finding": "[CIS.2.1] CloudWatch log group '/aws/lambda/prod-*' has retention set to NEVER.",
            "recommendation": "Set log retention to meet compliance requirements (90-365 days).",
        },
        {
            "resource_id": "arn:aws:ec2:us-east-1:123456789012:instance/i-0abc1234567890def",
            "resource_type": "EC2_INSTANCE",
            "service": "SecurityHub",
            "severity": "HIGH",
            "finding": "[Security.BestPractices] EC2 instance 'prod-app-server-01' does not have IMDSv2 required.",
            "recommendation": "Enable IMDSv2 and require hop limit of 2 for EC2 instances.",
        },
        # MEDIUM - Configuration Issues
        {
            "resource_id": "arn:aws:cloudtrail:us-east-1:123456789012:trail/main-trail",
            "resource_type": "CLOUDTRAIL",
            "service": "SecurityHub",
            "severity": "MEDIUM",
            "finding": "[CIS.2.2] CloudTrail trail 'main-trail' is not integrated with CloudWatch Logs.",
            "recommendation": "Configure CloudTrail to deliver events to CloudWatch Logs for monitoring.",
        },
        {
            "resource_id": "arn:aws:guardduty:us-east-1:123456789012:detector/abc123",
            "resource_type": "GUARDDUTY",
            "service": "SecurityHub",
            "severity": "MEDIUM",
            "finding": "[Security.BestPractices] GuardDuty is not enabled in us-east-1 region.",
            "recommendation": "Enable GuardDuty across all regions for comprehensive threat detection.",
        },
        {
            "resource_id": "arn:aws:kms:us-east-1:123456789012:key/abc123def456",
            "resource_type": "KMS_KEY",
            "service": "SecurityHub",
            "severity": "MEDIUM",
            "finding": "[Security.BestPractices] KMS key 'customer-master-key' does not have key rotation enabled.",
            "recommendation": "Enable automatic key rotation for KMS keys to meet compliance requirements.",
        },
        {
            "resource_id": "arn:aws:lambda:us-east-1:123456789012:function:ProcessUserData",
            "resource_type": "LAMBDA_FUNCTION",
            "service": "SecurityHub",
            "severity": "MEDIUM",
            "finding": "[Security.BestPractices] Lambda function 'ProcessUserData' uses runtime python3.7 (deprecated).",
            "recommendation": "Update Lambda runtime to supported version (python3.9+).",
        },
        # LOW - Informational
        {
            "resource_id": "arn:aws:config:us-east-1:123456789012:config-rule/security-best-practices",
            "resource_type": "CONFIG_RULE",
            "service": "SecurityHub",
            "severity": "LOW",
            "finding": "[CIS.2.4] AWS Config is not enabled in ap-southeast-1 region.",
            "recommendation": "Enable AWS Config in all regions for complete compliance coverage.",
        },
        {
            "resource_id": "arn:aws:ssm:us-east-1:123456789012:parameter/db-connection-string",
            "resource_type": "SSM_PARAMETER",
            "service": "SecurityHub",
            "severity": "LOW",
            "finding": "[Security.BestPractices] SSM parameter '/prod/db-connection-string' is stored as SecureString.",
            "recommendation": "Continue using SecureString parameter type for sensitive data.",
        },
    ]

    return findings


def get_mock_access_analyzer_findings():
    """
    Returns realistic IAM Access Analyzer findings for demo purposes.
    """
    findings = [
        # CRITICAL - External Access
        {
            "resource_id": "arn:aws:s3:::company-finance-reports",
            "resource_type": "S3_BUCKET",
            "service": "AccessAnalyzer",
            "severity": "CRITICAL",
            "finding": "External access: S3 bucket 'company-finance-reports' accessible from any AWS account.",
            "recommendation": "Review bucket policy. Remove wildcard principal (*) from bucket access statements.",
        },
        {
            "resource_id": "arn:aws:sqs:us-east-1:123456789012:prod-audit-queue",
            "resource_type": "SQS_QUEUE",
            "service": "AccessAnalyzer",
            "severity": "CRITICAL",
            "finding": "External access: SQS queue 'prod-audit-queue' allows access from 5 unknown accounts.",
            "recommendation": "Review and restrict queue policy to known, trusted accounts only.",
        },
        # HIGH - Cross-Account Access
        {
            "resource_id": "arn:aws:iam::123456789012:role/ProdDatabaseAccessRole",
            "resource_type": "IAM_ROLE",
            "service": "AccessAnalyzer",
            "severity": "HIGH",
            "finding": "Cross-account access: Role 'ProdDatabaseAccessRole' grants access to 3 external AWS accounts.",
            "recommendation": "Verify all external account IDs are authorized. Implement regular access reviews.",
        },
        {
            "resource_id": "arn:aws:secretsmanager:us-east-1:123456789012:secret:prod/db-creds",
            "resource_type": "SECRETS_MANAGER",
            "service": "AccessAnalyzer",
            "severity": "HIGH",
            "finding": "External access: Secrets Manager secret 'prod/db-creds' accessible from account 987654321098.",
            "recommendation": "Review cross-account access. Use IAM policies to restrict secret access.",
        },
        {
            "resource_id": "arn:aws:lambda:us-east-1:123456789012:function:SharedProcessor",
            "resource_type": "LAMBDA_FUNCTION",
            "service": "AccessAnalyzer",
            "severity": "HIGH",
            "finding": "Cross-account access: Lambda function 'SharedProcessor' has resource-based policy allowing external invoke.",
            "recommendation": "Review and restrict invoke permissions to known accounts only.",
        },
        # MEDIUM - Public Access
        {
            "resource_id": "arn:aws:s3:::company-static-assets",
            "resource_type": "S3_BUCKET",
            "service": "AccessAnalyzer",
            "severity": "MEDIUM",
            "finding": "Public access: S3 bucket 'company-static-assets' policy allows public read for GetObject.",
            "recommendation": "If public access is intentional, ensure only non-sensitive assets are exposed.",
        },
        {
            "resource_id": "arn:aws:apigateway:us-east-1:/restapis/prod-api",
            "resource_type": "API_GATEWAY",
            "service": "AccessAnalyzer",
            "severity": "MEDIUM",
            "finding": "Cross-account access: API Gateway 'prod-api' has open access enabled (no API key required).",
            "recommendation": "Implement authentication (IAM, Cognito, or Lambda authorizer) for production APIs.",
        },
        # LOW - Unused Access
        {
            "resource_id": "arn:aws:iam::123456789012:role/DeveloperRole",
            "resource_type": "IAM_ROLE",
            "service": "AccessAnalyzer",
            "severity": "LOW",
            "finding": "Unused access: Role 'DeveloperRole' has never been assumed in the last 90 days.",
            "recommendation": "Review if this role is still needed. Consider removing unused roles.",
        },
        {
            "resource_id": "arn:aws:kms:us-east-1:123456789012:key/legacy-encryption-key",
            "resource_type": "KMS_KEY",
            "service": "AccessAnalyzer",
            "severity": "LOW",
            "finding": "External access: KMS key 'legacy-encryption-key' has grants to 2 external accounts.",
            "recommendation": "Review and revoke unnecessary KMS grants.",
        },
    ]

    return findings


def get_mock_cloudtrail_findings():
    """
    Returns realistic CloudTrail findings for demo purposes.
    """
    findings = [
        # CRITICAL
        {
            "resource_id": "arn:aws:cloudtrail:us-east-1:123456789012:trail/prod-trail",
            "resource_type": "CLOUDTRAIL",
            "service": "CloudTrail",
            "severity": "CRITICAL",
            "finding": "CloudTrail 'prod-trail' is disabled - no audit logging enabled for production.",
            "recommendation": "Re-enable CloudTrail immediately. Configure multi-region trail for comprehensive coverage.",
        },
        {
            "resource_id": "arn:aws:cloudtrail:us-east-1:123456789012:trail/main-trail",
            "resource_type": "CLOUDTRAIL",
            "service": "CloudTrail",
            "severity": "CRITICAL",
            "finding": "CloudTrail 'main-trail' is not logging AWS Management Console sign-in events.",
            "recommendation": "Enable include-global-service-events for complete audit coverage.",
        },
        # HIGH
        {
            "resource_id": "arn:aws:cloudtrail:us-east-1:123456789012:trail/dev-trail",
            "resource_type": "CLOUDTRAIL",
            "service": "CloudTrail",
            "severity": "HIGH",
            "finding": "CloudTrail 'dev-trail' is not integrated with CloudWatch Logs for real-time monitoring.",
            "recommendation": "Configure CloudTrail to deliver logs to CloudWatch Logs for alerting.",
        },
        {
            "resource_id": "arn:aws:cloudtrail:us-east-1:123456789012:trail/staging-trail",
            "resource_type": "CLOUDTRAIL",
            "service": "CloudTrail",
            "severity": "HIGH",
            "finding": "CloudTrail 'staging-trail' has file delivery encryption disabled ( KMS key not set).",
            "recommendation": "Enable SSE-KMS encryption for CloudTrail log file delivery.",
        },
        {
            "resource_id": "arn:aws:cloudtrail:us-east-1:123456789012:trail/audit-trail",
            "resource_type": "CLOUDTRAIL",
            "service": "CloudTrail",
            "severity": "HIGH",
            "finding": "Read/Write events not configured separately - all events treated equally.",
            "recommendation": "Configure separate trails for read-only and write events for better analysis.",
        },
        # MEDIUM
        {
            "resource_id": "arn:aws:cloudtrail:us-east-1:123456789012:trail/legacy-trail",
            "resource_type": "CLOUDTRAIL",
            "service": "CloudTrail",
            "severity": "MEDIUM",
            "finding": "CloudTrail 'legacy-trail' log file validation is not enabled.",
            "recommendation": "Enable log file integrity validation to detect log tampering.",
        },
        {
            "resource_id": "arn:aws:cloudtrail:us-east-1:123456789012:trail/main-trail",
            "resource_type": "CLOUDTRAIL",
            "service": "CloudTrail",
            "severity": "MEDIUM",
            "finding": "S3 bucket 'company-cloudtrail-logs' allows public access to log files.",
            "recommendation": "Ensure S3 bucket policy denies public access. Use bucket versioning.",
        },
        # LOW
        {
            "resource_id": "arn:aws:cloudtrail:us-east-1:123456789012:trail/ops-trail",
            "resource_type": "CLOUDTRAIL",
            "service": "CloudTrail",
            "severity": "LOW",
            "finding": "CloudTrail 'ops-trail' is configured in only 1 region (us-east-1).",
            "recommendation": "Consider enabling multi-region trail for complete coverage across all regions.",
        },
        {
            "resource_id": "arn:aws:cloudtrail:us-east-1:123456789012:trail/test-trail",
            "resource_type": "CLOUDTRAIL",
            "service": "CloudTrail",
            "severity": "LOW",
            "finding": "CloudTrail 'test-trail' has not delivered logs in 7 days - trail may be inactive.",
            "recommendation": "Verify if trail is still needed or investigate delivery issues.",
        },
    ]

    return findings


def get_all_mock_findings():
    """
    Returns all mock findings combined for dry-run mode.
    """
    all_findings = []
    all_findings.extend(get_mock_iam_findings())
    all_findings.extend(get_mock_securityhub_findings())
    all_findings.extend(get_mock_access_analyzer_findings())
    all_findings.extend(get_mock_cloudtrail_findings())

    return all_findings


def get_dry_run_summary():
    """
    Returns a summary of the dry-run mode configuration for display.
    """
    findings = get_all_mock_findings()

    severity_counts = {
        "CRITICAL": len([f for f in findings if f["severity"] == "CRITICAL"]),
        "HIGH": len([f for f in findings if f["severity"] == "HIGH"]),
        "MEDIUM": len([f for f in findings if f["severity"] == "MEDIUM"]),
        "LOW": len([f for f in findings if f["severity"] == "LOW"]),
    }

    return {
        "mode": "DRY_RUN",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": "Mock Data Generator v1.0",
        "total_findings": len(findings),
        "severity_breakdown": severity_counts,
        "description": "This is a demonstration mode with simulated AWS security findings for interview purposes.",
    }


def get_mock_narrative(findings):
    """
    Returns a pre-generated narrative for dry-run mode without calling Bedrock.
    This avoids AWS credential requirements for the demo mode.
    """
    severity_counts = {
        "CRITICAL": len([f for f in findings if f["severity"] == "CRITICAL"]),
        "HIGH": len([f for f in findings if f["severity"] == "HIGH"]),
        "MEDIUM": len([f for f in findings if f["severity"] == "MEDIUM"]),
        "LOW": len([f for f in findings if f["severity"] == "LOW"]),
    }

    narrative = f"""
EXECUTIVE SUMMARY - AWS Access Review Report
=============================================

This automated access review identified {severity_counts['CRITICAL']} critical, {severity_counts['HIGH']} high, 
{severity_counts['MEDIUM']} medium, and {severity_counts['LOW']} low severity security findings across your AWS environment.

OVERVIEW
--------
The assessment analyzed IAM users, roles, and policies; SecurityHub findings; Access Analyzer results; 
and CloudTrail access events to identify potential security risks and compliance violations.

CRITICAL FINDINGS
-----------------
The following critical issues require immediate attention:
1. Root account has active access keys - Immediate revocation recommended
2. Users without MFA enrollment - Enable MFA for all console users
3. Overly permissive IAM roles with AdministratorAccess - Implement least privilege
4. Service accounts with console access and no MFA - Remove unnecessary access

HIGH PRIORITY FINDINGS
---------------------
- Users with AdministratorAccess policy attached
- Roles allowing actions outside the AWS account
- Unused access keys that should be rotated or removed
- Missing password policies for IAM users

RECOMMENDATIONS
--------------
1. Enable MFA for all IAM users, especially those with console access
2. Remove unnecessary administrative permissions and implement least privilege
3. Rotate access keys every 90 days
4. Set up AWS Config rules to monitor for compliance violations
5. Implement AWS Identity Center for centralized access management

This report was generated in DRY-RUN mode using simulated data for demonstration purposes.
In production, this narrative would be generated using Amazon Bedrock (Claude) for more detailed insights.
"""
    return narrative.strip()
