# Usage Guide

## Overview

This guide explains how to use the AWS Automated Access Review tool, including running reports manually, using CLI tools, interpreting reports, scheduling options, and customization options.

## Running Reports Manually

### Method 1: AWS Console

#### Invoke Lambda Function

1. Navigate to AWS Lambda in the AWS Console
2. Select the `aws-access-review-access-review` function
3. Click the **Test** tab
4. Create a new test event:

**For Dry-Run Mode (Demo):**
```json
{
  "dry_run": true,
  "format": "csv"
}
```

**For Full Execution:**
```json
{
  "format": "csv"
}
```

5. Click **Test** to invoke the function
6. View the execution result in the response

#### Monitor Execution

1. Click the **Monitor** tab
2. View **Invocations**, **Duration**, **Errors**, and **Throttles**
3. Click **View CloudWatch logs** to see detailed logs

### Method 2: AWS CLI

#### Basic Invocation

```bash
# Invoke Lambda with default settings
aws lambda invoke \
  --function-name aws-access-review-access-review \
  --payload '{}' \
  --cli-binary-format raw-in-base64-out \
  response.json

# View response
cat response.json
```

#### Dry-Run Mode

```bash
# Run in dry-run mode (uses mock data, no AWS API calls)
aws lambda invoke \
  --function-name aws-access-review-access-review \
  --payload '{"dry_run": true}' \
  --cli-binary-format raw-in-base64-out \
  response.json

cat response.json
```

#### Specify Report Format

```bash
# Generate CSV report (default)
aws lambda invoke \
  --function-name aws-access-review-access-review \
  --payload '{"format": "csv"}' \
  --cli-binary-format raw-in-base64-out \
  response.json

# Generate XLSX report
aws lambda invoke \
  --function-name aws-access-review-access-review \
  --payload '{"format": "xlsx"}' \
  --cli-binary-format raw-in-base64-out \
  response.json
```

#### Combined Options

```bash
# Dry-run with XLSX format
aws lambda invoke \
  --function-name aws-access-review-access-review \
  --payload '{"dry_run": true, "format": "xlsx"}' \
  --cli-binary-format raw-in-base64-out \
  response.json
```

### Method 3: Local Execution (Development)

#### Prerequisites

```bash
# Install dependencies
pip install -r requirements.txt

# Set AWS credentials (for non-dry-run mode)
aws configure
```

#### Run Locally

```bash
# Navigate to lambda directory
cd src/lambda

# Run in dry-run mode (no AWS credentials needed)
python -c "
import os
os.environ['DRY_RUN'] = 'true'
from index import lambda_handler
result = lambda_handler({'format': 'csv'}, None)
print('Report saved to:', result['body']['report_path'])
"

# Run with AWS credentials (requires valid AWS credentials)
python -c "
from index import lambda_handler
result = lambda_handler({'format': 'csv'}, None)
print('Report URL:', result['body']['report_url'])
"
```

## Using CLI Tools

The project includes CLI tools for local development and testing.

### Local Runner

The local runner allows you to execute the access review locally without deploying to AWS.

```bash
# Navigate to CLI directory
cd src/cli

# Run local runner
python local_runner.py --help

# Run with default settings (dry-run mode)
python local_runner.py

# Run with specific format
python local_runner.py --format xlsx

# Run with output directory
python local_runner.py --output ./reports

# Run in production mode (requires AWS credentials)
python local_runner.py --production
```

**Local Runner Options:**

| Option | Description | Default |
|--------|-------------|---------|
| `--format` | Report format (csv or xlsx) | csv |
| `--output` | Output directory for reports | ./reports |
| `--production` | Run in production mode (AWS API calls) | False |
| `--dry-run` | Run in dry-run mode (mock data) | True |
| `--verbose` | Enable verbose logging | False |

### Lambda Tester

The Lambda tester simulates AWS Lambda execution locally.

```bash
# Navigate to CLI directory
cd src/cli

# Run Lambda tester
python test_lambda.py --help

# Test with default event
python test_lambda.py

# Test with custom event
python test_lambda.py --event '{"dry_run": true, "format": "xlsx"}'

# Test with specific module
python test_lambda.py --module iam_findings

# Run tests in sequence
python test_lambda.py --all-modules
```

**Lambda Tester Options:**

| Option | Description | Default |
|--------|-------------|---------|
| `--event` | JSON event payload | {} |
| `--module` | Test specific module only | None |
| `--all-modules` | Test all modules individually | False |
| `--verbose` | Enable verbose logging | False |
| `--save-output` | Save output to file | False |

### Shell Scripts

The project includes shell scripts for common operations.

#### Run Report Script

```bash
# Make script executable (Linux/Mac)
chmod +x scripts/run_report.sh

# Run report with default settings
./scripts/run_report.sh

# Run report with XLSX format
./scripts/run_report.sh --format xlsx

# Run report in production mode
./scripts/run_report.sh --production
```

#### Check AWS Credentials Script

```bash
# Make script executable (Linux/Mac)
chmod +x scripts/check_aws_creds.sh

# Check AWS credentials
./scripts/check_aws_creds.sh
```

## Interpreting Reports

### Report Structure

Reports are generated in CSV or XLSX format with the following structure:

#### CSV Format

```csv
timestamp,source,resource_id,resource_type,finding_type,severity,description,recommendation,evidence
2024-01-01T00:00:00Z,IAM,user@example.com,User,MFA Missing,CRITICAL,User missing MFA enrollment,Enable MFA immediately,"{'user': 'user@example.com', 'console_access': true}"
2024-01-01T00:00:00Z,IAM,root,Root Account,Active Access Keys,CRITICAL,Root account has active access keys,Revoke immediately,"{'has_access_keys': true}"
```

#### XLSX Format

XLSX reports include multiple sheets:

1. **Summary**: High-level overview with finding counts
2. **Critical Findings**: All CRITICAL severity findings
3. **High Findings**: All HIGH severity findings
4. **Medium Findings**: All MEDIUM severity findings
5. **Low Findings**: All LOW severity findings
6. **All Findings**: Complete list of all findings

### Report Fields

| Field | Description | Example |
|-------|-------------|---------|
| `timestamp` | When the finding was detected | `2024-01-01T00:00:00Z` |
| `source` | AWS service that generated the finding | `IAM`, `SecurityHub`, `AccessAnalyzer`, `CloudTrail` |
| `resource_id` | Identifier of the affected resource | `user@example.com`, `role-name`, `bucket-name` |
| `resource_type` | Type of AWS resource | `User`, `Role`, `Policy`, `Bucket`, `Trail` |
| `finding_type` | Category of the finding | `MFA Missing`, `Admin Policy`, `Public Access` |
| `severity` | Severity level | `CRITICAL`, `HIGH`, `MEDIUM`, `LOW` |
| `description` | Human-readable description of the finding | `User missing MFA enrollment` |
| `recommendation` | Recommended action to remediate | `Enable MFA immediately` |
| `evidence` | JSON object with supporting evidence | `{'user': 'user@example.com'}` |

### Severity Levels

#### CRITICAL
Requires immediate attention. These findings represent serious security risks:

- Root account with active access keys
- Users with console access but no MFA
- Roles with AdministratorAccess policy
- Public S3 buckets with sensitive data
- Unencrypted S3 buckets

**Action**: Remediate within 24 hours

#### HIGH
Important security issues that should be addressed soon:

- Users with AdministratorAccess policy
- Roles allowing actions outside the AWS account
- Unused access keys (>90 days)
- Missing password policies
- CloudTrail not enabled in all regions

**Action**: Remediate within 1 week

#### MEDIUM
Moderate security concerns:

- Access keys not rotated in 90 days
- Users with multiple access keys
- Password policy not enforcing complexity
- CloudTrail logs not validated
- IAM policies with wildcard permissions

**Action**: Remediate within 1 month

#### LOW
Minor security issues or best practice recommendations:

- Users without tags
- Roles without descriptions
- Policies not used in 90 days
- Inconsistent naming conventions

**Action**: Address when convenient

### Sample Report Analysis

#### Executive Summary

The email includes an AI-generated executive summary:

```
EXECUTIVE SUMMARY - AWS Access Review Report
============================================

This automated access review identified 2 critical, 5 high, 8 medium, 
and 3 low severity security findings across your AWS environment.

OVERVIEW
--------
The assessment analyzed IAM users, roles, and policies; SecurityHub findings; 
Access Analyzer results; and CloudTrail access events to identify potential 
security risks and compliance violations.

CRITICAL FINDINGS
-----------------
The following critical issues require immediate attention:

1. Root account has active access keys
   → Recommendation: Immediate revocation recommended

2. User 'james.wilson@company.com' missing MFA enrollment
   → Recommendation: Enable MFA immediately for this user

HIGH PRIORITY FINDINGS
----------------------
- Users with AdministratorAccess policy attached: 3 found
- Roles allowing actions outside the AWS account: 5 found
- Unused access keys that should be rotated or removed: 7 found
- Missing password policies for IAM users: 2 found

RECOMMENDATIONS
---------------
1. Enable MFA for all IAM users, especially those with console access
2. Remove unnecessary administrative permissions and implement least privilege
3. Rotate access keys every 90 days
4. Set up AWS Config rules to monitor for compliance violations
5. Implement AWS Identity Center for centralized access management
```

#### Detailed Findings

Review the CSV/XLSX attachment for detailed findings:

1. **Sort by severity** to prioritize critical issues
2. **Filter by source** to focus on specific services
3. **Review recommendations** for remediation steps
4. **Check evidence** for supporting details

### Compliance Mapping

The report includes findings mapped to compliance frameworks:

| Finding | SOC 2 | CIS AWS | NIST 800-53 |
|---------|-------|---------|-------------|
| Root account MFA | CC6.1 | 1.1 | IA-2 |
| User MFA | CC6.1 | 1.13 | IA-2 |
| Admin policies | CC6.3 | 1.16 | AC-6 |
| CloudTrail enabled | CC7.2 | 2.1 | AU-2 |
| Public S3 buckets | CC6.6 | 2.1.3 | SC-7 |

## Scheduling Options

### EventBridge Scheduler

The tool uses EventBridge Scheduler for automated execution.

#### Default Schedule

Default: Monthly on the 1st at midnight UTC

```yaml
ScheduleExpression: cron(0 0 1 * ? *)
```

#### Schedule Expression Format

**Cron Expressions:**

```
cron(Minutes Hours Day-of-month Month Day-of-week Year)
```

| Field | Values | Wildcards |
|-------|--------|-----------|
| Minutes | 0-59 | , - * / |
| Hours | 0-23 | , - * / |
| Day-of-month | 1-31 | , - * ? L W |
| Month | 1-12 or JAN-DEC | , - * / |
| Day-of-week | 1-7 or SUN-SAT | , - * ? L # |
| Year | 1970-2199 | , - * / |

**Rate Expressions:**

```
rate(Value Unit)
```

| Unit | Description |
|------|-------------|
| minute | Every n minutes |
| hour | Every n hours |
| day | Every n days |

#### Common Schedule Examples

```bash
# Monthly on the 1st at midnight UTC
cron(0 0 1 * ? *)

# Monthly on the 1st at 9:00 AM UTC
cron(0 9 1 * ? *)

# Weekly on Monday at 9:00 AM UTC
cron(0 9 ? * MON *)

# Weekly on Friday at 5:00 PM UTC
cron(0 17 ? * FRI *)

# Daily at 8:00 AM UTC
cron(0 8 * * ? *)

# Daily at midnight UTC
cron(0 0 * * ? *)

# Every 6 hours
rate(6 hours)

# Every day at noon
rate(1 day)

# Every 30 minutes
rate(30 minutes)
```

#### Update Schedule

**Using AWS CLI:**

```bash
# Update CloudFormation stack with new schedule
aws cloudformation deploy \
  --template-file templates/access-review-real.yaml \
  --stack-name aws-access-review \
  --parameter-overrides \
    RecipientEmail=you@company.com \
    ScheduleExpression="cron(0 9 ? * MON *)" \
    DeploymentBucket=your-deployment-bucket \
    DeploymentKey=lambda-deployment.zip \
  --capabilities CAPABILITY_IAM
```

**Using AWS Console:**

1. Navigate to CloudFormation in the AWS Console
2. Select the `aws-access-review` stack
3. Click **Update** → **Edit parameters**
4. Update the `ScheduleExpression` parameter
5. Click **Next** → **Next** → **Update stack**

**Using EventBridge Directly:**

```bash
# Update EventBridge rule
aws events put-rule \
  --name aws-access-review-schedule \
  --schedule-expression "cron(0 9 ? * MON *)"
```

### Manual Trigger

You can also trigger the Lambda function manually at any time:

```bash
# Trigger immediately
aws lambda invoke \
  --function-name aws-access-review-access-review \
  --payload '{}' \
  --cli-binary-format raw-in-base64-out \
  response.json
```

### Disabling Schedule

To disable automatic scheduling:

```bash
# Disable EventBridge rule
aws events disable-rule \
  --name aws-access-review-schedule
```

To re-enable:

```bash
# Enable EventBridge rule
aws events enable-rule \
  --name aws-access-review-schedule
```

## Customization Options

### Report Format

#### CSV Format

Default format. Simple, human-readable, compatible with most tools.

```bash
# Generate CSV report
aws lambda invoke \
  --function-name aws-access-review-access-review \
  --payload '{"format": "csv"}' \
  --cli-binary-format raw-in-base64-out \
  response.json
```

#### XLSX Format

Enhanced format with multiple sheets and formatting.

```bash
# Generate XLSX report
aws lambda invoke \
  --function-name aws-access-review-access-review \
  --payload '{"format": "xlsx"}' \
  --cli-binary-format raw-in-base64-out \
  response.json
```

### Finding Modules

The tool collects findings from multiple modules. You can enable/disable modules:

#### Enable/Disable SCP Analysis

```bash
# Enable SCP analysis
aws cloudformation deploy \
  --template-file templates/access-review-real.yaml \
  --stack-name aws-access-review \
  --parameter-overrides \
    RecipientEmail=you@company.com \
    EnableSCPAnalysis=true \
    DeploymentBucket=your-deployment-bucket \
    DeploymentKey=lambda-deployment.zip \
  --capabilities CAPABILITY_IAM

# Disable SCP analysis
aws cloudformation deploy \
  --template-file templates/access-review-real.yaml \
  --stack-name aws-access-review \
  --parameter-overrides \
    RecipientEmail=you@company.com \
    EnableSCPAnalysis=false \
    DeploymentBucket=your-deployment-bucket \
    DeploymentKey=lambda-deployment.zip \
  --capabilities CAPABILITY_IAM
```

#### Custom Module Selection

Modify [`src/lambda/index.py`](../src/lambda/index.py:1) to enable/disable specific modules:

```python
# In lambda_handler function
# Comment out modules you don't want to run
with concurrent.futures.ThreadPoolExecutor() as executor:
    futures = {
        # executor.submit(get_iam_findings): "IAM",
        executor.submit(get_securityhub_findings): "SecurityHub",
        executor.submit(get_access_analyzer_findings): "AccessAnalyzer",
        executor.submit(get_cloudtrail_findings): "CloudTrail",
    }
```

### Bedrock Model Selection

The tool uses Claude 3 Sonnet by default. You can change the model:

```bash
# Update CloudFormation stack with new model
aws cloudformation deploy \
  --template-file templates/access-review-real.yaml \
  --stack-name aws-access-review \
  --parameter-overrides \
    RecipientEmail=you@company.com \
    BedrockRegion=us-east-1 \
    BedrockModelId=anthropic.claude-3-haiku-20240307-v1:0 \
    DeploymentBucket=your-deployment-bucket \
    DeploymentKey=lambda-deployment.zip \
  --capabilities CAPABILITY_IAM
```

**Available Bedrock Models:**

| Model ID | Description | Cost per 1K tokens |
|----------|-------------|-------------------|
| `anthropic.claude-3-sonnet-20240229-v1:0` | Balanced performance/cost | $0.003 (input) / $0.015 (output) |
| `anthropic.claude-3-haiku-20240307-v1:0` | Fast, cost-effective | $0.00025 (input) / $0.00125 (output) |
| `anthropic.claude-3-opus-20240229-v1:0` | Highest quality | $0.015 (input) / $0.075 (output) |

### Custom Severity Thresholds

Modify severity thresholds in individual finding modules.

#### Example: IAM Findings

Edit [`src/lambda/modules/iam_findings.py`](../src/lambda/modules/iam_findings.py:1):

```python
# Customize severity for root account keys
if root_has_keys:
    findings.append({
        'source': 'IAM',
        'resource_id': 'root',
        'resource_type': 'Root Account',
        'finding_type': 'Active Access Keys',
        'severity': 'CRITICAL',  # Change to HIGH if desired
        'description': 'Root account has active access keys',
        'recommendation': 'Revoke immediately',
        'evidence': {'has_access_keys': True}
    })
```

### Custom Email Template

See [Email Setup Guide](email-setup.md) for detailed email customization options.

### Custom Report Fields

Add custom fields to reports by modifying the finding schema.

#### Example: Add Compliance Tag

```python
# In finding modules
findings.append({
    'source': 'IAM',
    'resource_id': 'user@example.com',
    'resource_type': 'User',
    'finding_type': 'MFA Missing',
    'severity': 'CRITICAL',
    'description': 'User missing MFA enrollment',
    'recommendation': 'Enable MFA immediately',
    'evidence': {'user': 'user@example.com'},
    'compliance_tags': ['SOC2-CC6.1', 'CIS-1.13', 'NIST-IA-2']  # Custom field
})
```

Update [`src/lambda/modules/reporting.py`](../src/lambda/modules/reporting.py:1) to include custom fields in the report.

### Custom S3 Bucket

Use a custom S3 bucket name instead of auto-generated:

```bash
# Update CloudFormation stack with custom bucket name
aws cloudformation deploy \
  --template-file templates/access-review-real.yaml \
  --stack-name aws-access-review \
  --parameter-overrides \
    RecipientEmail=you@company.com \
    BucketName=my-custom-access-reports-bucket \
    DeploymentBucket=your-deployment-bucket \
    DeploymentKey=lambda-deployment.zip \
  --capabilities CAPABILITY_IAM
```

### Custom Lambda Configuration

Modify Lambda function settings:

```bash
# Update Lambda timeout
aws lambda update-function-configuration \
  --function-name aws-access-review-access-review \
  --timeout 900

# Update Lambda memory
aws lambda update-function-configuration \
  --function-name aws-access-review-access-review \
  --memory-size 1024

# Update Lambda environment variables
aws lambda update-function-configuration \
  --function-name aws-access-review-access-review \
  --environment Variables={
    REPORT_BUCKET="aws-access-review-access-reports",
    RECIPIENT_EMAIL="you@company.com",
    BEDROCK_REGION="us-east-1",
    BEDROCK_MODEL_ID="anthropic.claude-3-sonnet-20240229-v1:0",
    ENABLE_SCP_ANALYSIS="true",
    LOG_LEVEL="DEBUG"
  }
```

## Best Practices

### 1. Regular Reviews
- Schedule monthly access reviews
- Review reports promptly after generation
- Track remediation progress

### 2. Prioritize Findings
- Address CRITICAL findings immediately
- Create tickets for HIGH findings
- Plan remediation for MEDIUM/LOW findings

### 3. Maintain Audit Trail
- Keep reports for compliance audits
- Use S3 versioning for report history
- Document remediation actions

### 4. Continuous Improvement
- Review and update severity thresholds
- Add custom finding types as needed
- Integrate with ticketing systems

### 5. Security Considerations
- Never share presigned URLs publicly
- Use least-privilege IAM policies
- Monitor for unusual activity

### 6. Cost Management
- Monitor AWS costs regularly
- Optimize Lambda memory and timeout
- Use lifecycle rules for S3 cleanup

## Integration Examples

### JIRA Integration

Automatically create JIRA tickets for critical findings:

```python
# Add to lambda_handler in src/lambda/index.py
import requests

def create_jira_ticket(finding):
    """Create a JIRA ticket for a critical finding."""
    url = "https://your-domain.atlassian.net/rest/api/3/issue"
    auth = ("your-email@company.com", "your-api-token")
    
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    
    payload = {
        "fields": {
            "project": {"key": "SEC"},
            "summary": f"[CRITICAL] {finding['finding_type']}: {finding['resource_id']}",
            "description": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [
                            {
                                "type": "text",
                                "text": f"{finding['description']}\n\nRecommendation: {finding['recommendation']}"
                            }
                        ]
                    }
                ]
            },
            "issuetype": {"name": "Bug"},
            "priority": {"name": "Highest"}
        }
    }
    
    response = requests.post(url, json=payload, headers=headers, auth=auth)
    return response.json()

# Call after generating findings
for finding in findings:
    if finding['severity'] == 'CRITICAL':
        create_jira_ticket(finding)
```

### Slack Integration

Send notifications to Slack:

```python
# Add to lambda_handler in src/lambda/index.py
import requests

def send_slack_notification(summary):
    """Send summary to Slack."""
    webhook_url = "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
    
    payload = {
        "text": "AWS Access Review Complete",
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*AWS Access Review Report*\n\n{summary}"
                }
            }
        ]
    }
    
    requests.post(webhook_url, json=payload)

# Call after generating report
send_slack_notification(narrative)
```

### Splunk Integration

Send findings to Splunk:

```python
# Add to lambda_handler in src/lambda/index.py
import requests

def send_to_splunk(findings):
    """Send findings to Splunk HTTP Event Collector."""
    url = "https://your-splunk-instance:8088/services/collector/event"
    headers = {
        "Authorization": "Splunk YOUR-HEC-TOKEN"
    }
    
    for finding in findings:
        payload = {
            "event": finding,
            "sourcetype": "aws:access:review",
            "index": "security"
        }
        requests.post(url, json=payload, headers=headers)

# Call after generating findings
send_to_splunk(findings)
```

## Related Documentation
- [Deployment Guide](deployment.md)
- [Email Setup](email-setup.md)
- [Testing Guide](testing.md)
- [Troubleshooting](troubleshooting.md)
- [Architecture](architecture.md)
