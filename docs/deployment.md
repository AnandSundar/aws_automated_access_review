# Deployment Guide

## Overview

This guide provides step-by-step instructions for deploying the AWS Automated Access Review tool to your AWS account. The deployment uses AWS CloudFormation for infrastructure-as-code, ensuring reproducible and version-controlled deployments.

## Prerequisites

### Required Tools

1. **AWS CLI** (version 2.x or later)
   ```bash
   aws --version
   # Expected output: aws-cli/2.x.x
   ```

2. **Python 3.11+**
   ```bash
   python --version
   # Expected output: Python 3.11.x or higher
   ```

3. **Git** (for cloning the repository)
   ```bash
   git --version
   ```

### AWS Account Requirements

1. **AWS Account** with appropriate permissions
2. **IAM Permissions** to create:
   - CloudFormation stacks
   - Lambda functions
   - IAM roles and policies
   - S3 buckets
   - EventBridge rules
   - SNS topics
   - SQS queues
   - CloudWatch alarms

3. **Service Quotas**:
   - Lambda: At least 1 concurrent execution
   - S3: Sufficient storage for reports
   - SES: Email sending quota (default: 62,000/month free tier)
   - Bedrock: Access to Claude 3 Sonnet model

### Regional Requirements

- **Primary Region**: Any AWS region
- **Bedrock Region**: Must be a region where Bedrock is available:
  - `us-east-1` (N. Virginia) - Recommended
  - `us-west-2` (Oregon)
  - `eu-west-1` (Ireland)
  - `ap-northeast-1` (Tokyo)

### Email Requirements

- **Verified Email Address**: Recipient email must be verified in Amazon SES
- **Domain Verification** (optional): Verify entire domain for multiple recipients

## Deployment Options

The project provides two CloudFormation templates:

1. **`templates/access-review.yaml`** - Demo/Quick Start template
   - Minimal configuration
   - Good for testing and proof-of-concept
   - Basic security settings

2. **`templates/access-review-real.yaml`** - Production template
   - Enhanced security hardening
   - Comprehensive monitoring
   - Dead Letter Queue
   - CloudWatch alarms
   - SNS notifications
   - Recommended for production use

## Step-by-Step Deployment

### Step 1: Clone the Repository

```bash
git clone https://github.com/yourusername/aws_automated_access_review.git
cd aws_automated_access_review
```

### Step 2: Set Up Python Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Linux/Mac:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Step 3: Verify AWS Credentials

```bash
# Check AWS CLI configuration
aws configure list

# Verify identity
aws sts get-caller-identity

# Expected output:
# {
#     "UserId": "AIDAI...",
#     "Account": "123456789012",
#     "Arn": "arn:aws:iam::123456789012:user/your-username"
# }
```

If not configured, run:
```bash
aws configure
# Enter your AWS Access Key ID
# Enter your AWS Secret Access Key
# Enter default region (e.g., us-east-1)
# Enter default output format (json)
```

### Step 4: Verify Amazon SES Email

Before deployment, verify your recipient email in Amazon SES:

```bash
# Verify email address
aws ses verify-email-identity --email-address you@company.com

# Check verification status
aws ses get-identity-verification-attributes \
  --identities you@company.com
```

**Important**: Check your email inbox (and spam folder) for a verification email from AWS. Click the confirmation link to enable email delivery.

### Step 5: Package Lambda Code

The CloudFormation template requires the Lambda code to be packaged and uploaded to S3.

#### Option A: Using the Deployment Script

```bash
# Make the script executable (Linux/Mac)
chmod +x scripts/deploy.sh

# Run the deployment script
./scripts/deploy.sh
```

#### Option B: Manual Packaging

```bash
# Create a deployment package
cd src/lambda
zip -r ../lambda-deployment.zip . -x "*.pyc" "__pycache__/*" "tests/*"
cd ..

# Upload to S3 (create bucket if needed)
aws s3 mb s3://your-deployment-bucket-name
aws s3 cp lambda-deployment.zip s3://your-deployment-bucket-name/
```

### Step 6: Deploy with CloudFormation

#### Deploy Production Template (Recommended)

```bash
aws cloudformation deploy \
  --template-file templates/access-review-real.yaml \
  --stack-name aws-access-review \
  --parameter-overrides \
    RecipientEmail=you@company.com \
    ScheduleExpression="cron(0 0 1 * ? *)" \
    BedrockRegion=us-east-1 \
    BedrockModelId=anthropic.claude-3-sonnet-20240229-v1:0 \
    EnableSCPAnalysis=true \
    BucketName="" \
  --capabilities CAPABILITY_IAM \
  --tags Environment=Production,Project=AccessReview
```

#### Deploy Demo Template

```bash
aws cloudformation deploy \
  --template-file templates/access-review.yaml \
  --stack-name aws-access-review-demo \
  --parameter-overrides \
    RecipientEmail=you@company.com \
  --capabilities CAPABILITY_IAM
```

### Step 7: Monitor Deployment

```bash
# Check stack status
aws cloudformation describe-stacks \
  --stack-name aws-access-review \
  --query 'Stacks[0].StackStatus'

# Watch events
aws cloudformation describe-stack-events \
  --stack-name aws-access-review \
  --max-items 10
```

Expected status: `CREATE_COMPLETE` or `UPDATE_COMPLETE`

### Step 8: Verify Deployment

#### Check Created Resources

```bash
# Get stack outputs
aws cloudformation describe-stacks \
  --stack-name aws-access-review \
  --query 'Stacks[0].Outputs'
```

Expected outputs:
- `BucketName`: S3 bucket for reports
- `BucketArn`: S3 bucket ARN
- `LambdaArn`: Lambda function ARN
- `LambdaName`: Lambda function name
- `ScheduleExpression`: Cron schedule
- `NotificationTopicArn`: SNS topic ARN
- `DLQUrl`: Dead Letter Queue URL

#### Verify Lambda Function

```bash
# Get Lambda function details
aws lambda get-function \
  --function-name aws-access-review-access-review

# Check Lambda configuration
aws lambda get-function-configuration \
  --function-name aws-access-review-access-review
```

#### Verify EventBridge Rule

```bash
# List rules
aws events list-rules \
  --name-prefix aws-access-review

# Get rule details
aws events describe-rule \
  --name aws-access-review-schedule
```

#### Verify S3 Bucket

```bash
# List buckets
aws s3 ls

# Check bucket configuration
aws s3api get-bucket-encryption \
  --bucket $(aws cloudformation describe-stacks \
    --stack-name aws-access-review \
    --query 'Stacks[0].Outputs[?OutputKey==`BucketName`].OutputValue' \
    --output text)

aws s3api get-bucket-versioning \
  --bucket $(aws cloudformation describe-stacks \
    --stack-name aws-access-review \
    --query 'Stacks[0].Outputs[?OutputKey==`BucketName`].OutputValue' \
    --output text)
```

### Step 9: Test the Deployment

#### Test Dry-Run Mode (No AWS API Calls)

```bash
# Invoke Lambda with dry-run parameter
aws lambda invoke \
  --function-name aws-access-review-access-review \
  --payload '{"dry_run": true}' \
  --cli-binary-format raw-in-base64-out \
  response.json

# Check response
cat response.json
```

Expected response:
```json
{
  "statusCode": 200,
  "body": {
    "mode": "DRY_RUN",
    "message": "Access Review Completed (Dry Run - Demo Mode)",
    "finding_counts": {
      "CRITICAL": 2,
      "HIGH": 5,
      "MEDIUM": 8,
      "LOW": 3
    },
    "total_findings": 18,
    "report_path": "reports/access_review_YYYYMMDD_HHMMSS.csv",
    "report_url": "file://reports/access_review_YYYYMMDD_HHMMSS.csv"
  }
}
```

#### Test Full Execution

```bash
# Invoke Lambda without dry-run
aws lambda invoke \
  --function-name aws-access-review-access-review \
  --payload '{}' \
  --cli-binary-format raw-in-base64-out \
  response.json

# Check response
cat response.json
```

Expected response:
```json
{
  "statusCode": 200,
  "body": {
    "message": "Access Review Completed",
    "finding_counts": {
      "CRITICAL": 0,
      "HIGH": 3,
      "MEDIUM": 5,
      "LOW": 2
    },
    "report_url": "https://...",
    "email_message_id": "..."
  }
}
```

## Configuration Parameters

### CloudFormation Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `RecipientEmail` | String | Required | Email address to receive reports (must be SES verified) |
| `ScheduleExpression` | String | `cron(0 0 1 * ? *)` | EventBridge schedule (cron or rate expression) |
| `BedrockRegion` | String | `us-east-1` | AWS region for Bedrock service |
| `BedrockModelId` | String | `anthropic.claude-3-sonnet-20240229-v1:0` | Bedrock model ID for narrative generation |
| `EnableSCPAnalysis` | String | `true` | Enable Service Control Policy analysis |
| `BucketName` | String | `""` (auto-generated) | Custom S3 bucket name (leave empty for auto-generated) |
| `DeploymentBucket` | String | Required | S3 bucket containing Lambda deployment package |
| `DeploymentKey` | String | Required | S3 key for Lambda deployment package |

### Schedule Expression Examples

```bash
# Monthly on the 1st at midnight UTC
cron(0 0 1 * ? *)

# Weekly on Monday at 9:00 AM UTC
cron(0 9 ? * MON *)

# Daily at 8:00 AM UTC
cron(0 8 * * ? *)

# Every 6 hours
rate(6 hours)

# Every day at noon
rate(1 day)
```

### Environment Variables

The Lambda function uses these environment variables (set by CloudFormation):

| Variable | Description | Example |
|----------|-------------|---------|
| `REPORT_BUCKET` | S3 bucket name for reports | `aws-access-review-access-reports` |
| `RECIPIENT_EMAIL` | Email recipient | `you@company.com` |
| `BEDROCK_REGION` | Bedrock service region | `us-east-1` |
| `BEDROCK_MODEL_ID` | Bedrock model identifier | `anthropic.claude-3-sonnet-20240229-v1:0` |
| `ENABLE_SCP_ANALYSIS` | Enable SCP analysis | `true` |
| `LOG_LEVEL` | Logging level | `INFO` |

## Post-Deployment Verification

### 1. Check CloudWatch Logs

```bash
# Get log group name
LOG_GROUP="/aws/lambda/aws-access-review-access-review"

# List log streams
aws logs describe-log-streams \
  --log-group-name "$LOG_GROUP" \
  --order-by LastEventTime \
  --descending \
  --max-items 1

# Get latest log events
LOG_STREAM=$(aws logs describe-log-streams \
  --log-group-name "$LOG_GROUP" \
  --order-by LastEventTime \
  --descending \
  --max-items 1 \
  --query 'logStreams[0].logStreamName' \
  --output text)

aws logs get-log-events \
  --log-group-name "$LOG_GROUP" \
  --log-stream-name "$LOG_STREAM" \
  --limit 50
```

### 2. Verify S3 Report

```bash
# List objects in report bucket
BUCKET=$(aws cloudformation describe-stacks \
  --stack-name aws-access-review \
  --query 'Stacks[0].Outputs[?OutputKey==`BucketName`].OutputValue' \
  --output text)

aws s3 ls s3://$BUCKET/

# Download latest report
LATEST_REPORT=$(aws s3 ls s3://$BUCKET/ | sort -r | head -1 | awk '{print $4}')
aws s3 cp s3://$BUCKET/$LATEST_REPORT ./

# View report
cat $LATEST_REPORT
```

### 3. Verify Email Delivery

Check your email inbox for the access review report. If not received:

```bash
# Check SES send statistics
aws ses get-send-statistics

# Check SES identity verification
aws ses get-identity-verification-attributes \
  --identities you@company.com
```

### 4. Verify CloudWatch Alarms

```bash
# List alarms
aws cloudwatch describe-alarms \
  --alarm-names-prefix aws-access-review

# Check alarm status
aws cloudwatch describe-alarms \
  --alarm-names aws-access-review-lambda-errors \
  --query 'MetricAlarms[0].StateValue'
```

### 5. Verify SNS Topic

```bash
# Get topic ARN
TOPIC_ARN=$(aws cloudformation describe-stacks \
  --stack-name aws-access-review \
  --query 'Stacks[0].Outputs[?OutputKey==`NotificationTopicArn`].OutputValue' \
  --output text)

# List topic subscriptions
aws sns list-subscriptions-by-topic \
  --topic-arn $TOPIC_ARN
```

## Updating the Deployment

### Update Lambda Code

```bash
# Rebuild deployment package
cd src/lambda
zip -r ../lambda-deployment.zip . -x "*.pyc" "__pycache__/*" "tests/*"
cd ..

# Upload to S3
aws s3 cp lambda-deployment.zip s3://your-deployment-bucket-name/

# Update CloudFormation stack
aws cloudformation deploy \
  --template-file templates/access-review-real.yaml \
  --stack-name aws-access-review \
  --parameter-overrides \
    RecipientEmail=you@company.com \
    DeploymentBucket=your-deployment-bucket-name \
    DeploymentKey=lambda-deployment.zip \
  --capabilities CAPABILITY_IAM
```

### Update Configuration

```bash
# Update schedule to weekly
aws cloudformation deploy \
  --template-file templates/access-review-real.yaml \
  --stack-name aws-access-review \
  --parameter-overrides \
    RecipientEmail=you@company.com \
    ScheduleExpression="cron(0 9 ? * MON *)" \
    DeploymentBucket=your-deployment-bucket-name \
    DeploymentKey=lambda-deployment.zip \
  --capabilities CAPABILITY_IAM
```

### Update Email Recipient

```bash
# Verify new email
aws ses verify-email-identity --email-address new-email@company.com

# Update stack
aws cloudformation deploy \
  --template-file templates/access-review-real.yaml \
  --stack-name aws-access-review \
  --parameter-overrides \
    RecipientEmail=new-email@company.com \
    DeploymentBucket=your-deployment-bucket-name \
    DeploymentKey=lambda-deployment.zip \
  --capabilities CAPABILITY_IAM
```

## Rollback

### Rollback to Previous Version

```bash
# List stack changesets
aws cloudformation list-change-sets \
  --stack-name aws-access-review

# Rollback to previous successful deployment
aws cloudformation rollback-stack \
  --stack-name aws-access-review
```

### Delete Stack

```bash
# Delete CloudFormation stack
aws cloudformation delete-stack \
  --stack-name aws-access-review

# Monitor deletion
aws cloudformation describe-stacks \
  --stack-name aws-access-review \
  --query 'Stacks[0].StackStatus'

# Clean up S3 bucket (if not deleted by CloudFormation)
BUCKET=$(aws cloudformation describe-stacks \
  --stack-name aws-access-review \
  --query 'Stacks[0].Outputs[?OutputKey==`BucketName`].OutputValue' \
  --output text)

aws s3 rb s3://$BUCKET --force
```

## Troubleshooting Deployment Issues

### Issue: CloudFormation Rollback

**Symptoms**: Stack creation fails and rolls back

**Solutions**:
1. Check CloudFormation events for specific error:
   ```bash
   aws cloudformation describe-stack-events \
     --stack-name aws-access-review \
     --max-items 20
   ```

2. Common causes:
   - **IAM permissions**: Ensure you have permissions to create all resources
   - **S3 bucket**: Verify deployment bucket exists and is accessible
   - **SES verification**: Confirm email is verified
   - **Bedrock access**: Ensure Bedrock is enabled in the region

### Issue: Lambda Timeout

**Symptoms**: Lambda function times out during execution

**Solutions**:
1. Increase Lambda timeout:
   ```bash
   aws lambda update-function-configuration \
     --function-name aws-access-review-access-review \
     --timeout 900
   ```

2. Increase Lambda memory:
   ```bash
   aws lambda update-function-configuration \
     --function-name aws-access-review-access-review \
     --memory-size 1024
   ```

3. Check CloudWatch logs for bottlenecks

### Issue: Email Not Received

**Symptoms**: Report generated but email not delivered

**Solutions**:
1. Verify SES email verification:
   ```bash
   aws ses get-identity-verification-attributes \
     --identities you@company.com
   ```

2. Check SES sending statistics:
   ```bash
   aws ses get-send-statistics
   ```

3. Check spam folder
4. Verify SES is not in sandbox mode (production accounts only)

### Issue: Bedrock Access Denied

**Symptoms**: Narrative generation fails with access error

**Solutions**:
1. Enable Bedrock model access:
   - Go to AWS Console → Amazon Bedrock
   - Navigate to Model access
   - Enable Claude 3 Sonnet model

2. Verify IAM permissions:
   ```bash
   aws iam get-role-policy \
     --role-name aws-access-review-lambda-execution-role \
     --policy-name AccessReviewPermissions
   ```

3. Check region compatibility:
   ```bash
   aws bedrock list-foundation-models \
     --region us-east-1
   ```

### Issue: S3 Access Denied

**Symptoms**: Report upload fails

**Solutions**:
1. Verify bucket policy:
   ```bash
   aws s3api get-bucket-policy \
     --bucket $BUCKET
   ```

2. Check Lambda IAM role permissions
3. Verify bucket exists and is in same region as Lambda

## Cost Estimation

### Monthly Cost Breakdown

| Resource | Usage | Cost (USD) |
|----------|-------|------------|
| Lambda | 2-3 minutes/month | $0.00 (free tier) |
| S3 Storage | ~10 MB reports | $0.01 |
| SES Email | 1 email/month | $0.00 (free tier) |
| Bedrock | ~1,000 tokens | $0.50 - $1.00 |
| CloudWatch Logs | ~5 MB logs | $0.00 (free tier) |
| CloudWatch Alarms | 2 alarms | $0.00 (free tier) |
| SNS Topic | 1 topic | $0.00 (free tier) |
| SQS DLQ | Minimal usage | $0.00 (free tier) |
| **Total** | | **~$1.00/month** |

### Cost Optimization Tips

1. **Lambda**: Use reserved concurrency to control costs
2. **S3**: Enable lifecycle rules to delete old reports
3. **Bedrock**: Optimize prompt length to reduce token usage
4. **CloudWatch**: Adjust log retention period (default: 30 days)
5. **SES**: Use domain verification for multiple recipients

## Security Best Practices

### 1. Use Separate AWS Account
Deploy security tools in a dedicated security account to prevent privilege escalation.

### 2. Enable MFA
Require MFA for all IAM users who can modify the deployment.

### 3. Use IAM Roles
Never use access keys for Lambda execution; use IAM roles instead.

### 4. Enable Encryption
- S3: Server-side encryption enabled by default
- Optional: Use customer-managed KMS keys

### 5. Monitor Access
- Enable CloudTrail for the account
- Set up CloudWatch alarms for suspicious activity
- Review IAM access regularly

### 6. Least Privilege
The Lambda role has minimal required permissions. Do not add unnecessary permissions.

### 7. Regular Updates
- Keep Lambda dependencies updated
- Review and update CloudFormation template regularly
- Monitor AWS service updates and deprecations

## Multi-Account Deployment

For organizations with multiple AWS accounts:

### 1. Centralized Deployment
Deploy in a centralized security account and use cross-account roles.

### 2. Cross-Account IAM Role
Create IAM roles in target accounts that the Lambda can assume:

```yaml
# Target account IAM role
AssumeRolePolicyDocument:
  Version: '2012-10-17'
  Statement:
    - Effect: Allow
      Principal:
        AWS: arn:aws:iam::SECURITY_ACCOUNT_ID:role/AccessReviewRole
      Action: sts:AssumeRole
```

### 3. Organizations Integration
Use AWS Organizations to deploy across all accounts automatically.

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Deploy Access Review

on:
  push:
    branches: [main]
  workflow_dispatch:

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1
      
      - name: Package Lambda
        run: |
          cd src/lambda
          zip -r ../../lambda-deployment.zip . -x "*.pyc" "__pycache__/*" "tests/*"
      
      - name: Upload to S3
        run: |
          aws s3 cp lambda-deployment.zip s3://your-deployment-bucket/
      
      - name: Deploy CloudFormation
        run: |
          aws cloudformation deploy \
            --template-file templates/access-review-real.yaml \
            --stack-name aws-access-review \
            --parameter-overrides \
              RecipientEmail=${{ secrets.RECIPIENT_EMAIL }} \
              DeploymentBucket=your-deployment-bucket \
              DeploymentKey=lambda-deployment.zip \
            --capabilities CAPABILITY_IAM
```

## Related Documentation
- [Architecture](architecture.md)
- [Email Setup](email-setup.md)
- [Usage Guide](usage.md)
- [Testing Guide](testing.md)
- [Troubleshooting](troubleshooting.md)
