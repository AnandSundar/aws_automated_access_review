# Email Setup Guide

## Overview

This guide covers Amazon SES (Simple Email Service) configuration for the AWS Automated Access Review tool. The tool uses SES to email reports with CSV/XLSX attachments to designated stakeholders.

## Amazon SES Overview

Amazon SES is a cloud-based email sending service designed to help digital marketers and application developers send marketing, notification, and transactional emails. It's a reliable, cost-effective service for businesses of all sizes.

### Key Features
- **High Deliverability**: Built-in reputation and deliverability features
- **Cost-Effective**: Pay-as-you-go pricing with generous free tier
- **Scalable**: Handle from a few to millions of emails per day
- **Secure**: Support for DKIM, SPF, and DMARC
- **Integrated**: Native AWS service integration

## Prerequisites

1. **AWS Account** with SES enabled
2. **Verified Email Address** or Domain
3. **Production Access** (for sending to external recipients)
4. **IAM Permissions** to manage SES identities

## SES Account Status

### Sandbox Mode (Default)
New SES accounts start in sandbox mode with restrictions:
- Can only send to verified email addresses
- Can only send from verified email addresses
- Maximum 200 emails per 24-hour period
- Maximum 1 email per second

### Production Access
Request production access to:
- Send to any email address
- Higher sending limits (up to millions per day)
- Increased sending rate (up to 90 emails per second)

## Email Verification

### Verify an Email Address

#### Using AWS CLI

```bash
# Verify a single email address
aws ses verify-email-identity \
  --email-address you@company.com

# Expected output:
# {
#     "ResponseMetadata": {
#         "RequestId": "..."
#     }
# }
```

#### Using AWS Console

1. Navigate to Amazon SES in the AWS Console
2. Go to **Configuration** → **Verified identities**
3. Click **Create identity**
4. Select **Email address**
5. Enter the email address
6. Click **Create identity**
7. Check your email inbox for verification email
8. Click the verification link

#### Check Verification Status

```bash
# Check verification status
aws ses get-identity-verification-attributes \
  --identities you@company.com

# Expected output:
# {
#     "VerificationAttributes": {
#         "you@company.com": {
#             "VerificationStatus": "Success",
#             "VerificationToken": "..."
#         }
#     }
# }
```

Possible statuses:
- `Success`: Email is verified and ready to use
- `Pending`: Verification email sent, awaiting confirmation
- `Failed`: Verification failed, retry verification
- `TemporaryFailure`: Temporary issue, retry later
- `NotStarted`: Verification not initiated

### Verify a Domain

For organizations, verify an entire domain to send from any email address under that domain.

#### Using AWS CLI

```bash
# Verify a domain
aws ses verify-domain-identity \
  --domain example.com

# Expected output:
# {
#     "VerificationToken": "..."
# }
```

#### Using AWS Console

1. Navigate to Amazon SES in the AWS Console
2. Go to **Configuration** → **Verified identities**
3. Click **Create identity**
4. Select **Domain**
5. Enter the domain name (e.g., `example.com`)
6. Click **Create identity**
7. Add the DNS records to your domain's DNS configuration

#### DNS Records Required

After initiating domain verification, add these DNS records:

**TXT Record for Verification:**
```
Name: _amazonses.example.com
Type: TXT
Value: [verification-token-from-SES]
```

**TXT Record for SPF (Recommended):**
```
Name: example.com
Type: TXT
Value: "v=spf1 include:amazonses.com ~all"
```

**CNAME Record for DKIM (Recommended):**
```
Name: [selector]._domainkey.example.com
Type: CNAME
Value: [selector].dkim.amazonses.com
```

#### Check Domain Verification Status

```bash
# Check verification status
aws ses get-identity-verification-attributes \
  --identities example.com

# Check DKIM attributes
aws ses get-identity-dkim-attributes \
  --identities example.com

# Check mail from domain
aws ses get-identity-mail-from-domain-attributes \
  --identities example.com
```

## Requesting Production Access

### When to Request Production Access

Request production access when you need to:
- Send emails to unverified recipients
- Send more than 200 emails per day
- Send faster than 1 email per second
- Use the tool in a production environment

### How to Request Production Access

#### Using AWS Console

1. Navigate to Amazon SES in the AWS Console
2. Go to **Configuration** → **Sending limits**
3. Click **Request production access**
4. Complete the request form:
   - **Use Case Description**: Describe your use case
   - **Website URL**: Provide your website URL
   - **Email Types**: Select types of emails you'll send
   - **Expected Volume**: Estimate daily/monthly volume
5. Submit the request

#### Sample Use Case Description

```
We are using the AWS Automated Access Review tool to send monthly 
security compliance reports to our security team and stakeholders. 
These reports contain IAM access findings, security recommendations, 
and compliance evidence for SOC 2 audits. Expected volume: 1-5 
emails per month to 5-10 verified recipients.
```

### Production Access Review Process

1. **Submission**: Submit your request
2. **Review**: AWS reviews your request (typically 1-2 business days)
3. **Approval**: You'll receive email notification
4. **Limits Updated**: Your sending limits are automatically increased

### After Approval

```bash
# Check your new sending limits
aws ses get-account-sending-enabled

# Get sending quota
aws ses get-send-quota

# Expected output:
# {
#     "Max24HourSend": 10000,
#     "MaxSendRate": 5.0,
#     "SentLast24Hours": 0
# }
```

## Email Configuration

### Update Recipient Email

#### Using CloudFormation

```bash
# Update the CloudFormation stack with new email
aws cloudformation deploy \
  --template-file templates/access-review-real.yaml \
  --stack-name aws-access-review \
  --parameter-overrides \
    RecipientEmail=new-email@company.com \
    DeploymentBucket=your-deployment-bucket \
    DeploymentKey=lambda-deployment.zip \
  --capabilities CAPABILITY_IAM
```

#### Using AWS Console

1. Navigate to CloudFormation in the AWS Console
2. Select the `aws-access-review` stack
3. Click **Update** → **Edit parameters**
4. Update the `RecipientEmail` parameter
5. Click **Next** → **Next** → **Update stack**

### Configure Sender Email

By default, the tool uses the verified recipient email as the sender. To configure a custom sender:

1. Verify the sender email address in SES
2. Update the Lambda function environment variables:

```bash
# Update Lambda environment variables
aws lambda update-function-configuration \
  --function-name aws-access-review-access-review \
  --environment Variables={
    REPORT_BUCKET="aws-access-review-access-reports",
    RECIPIENT_EMAIL="recipient@company.com",
    SENDER_EMAIL="sender@company.com",
    BEDROCK_REGION="us-east-1",
    BEDROCK_MODEL_ID="anthropic.claude-3-sonnet-20240229-v1:0",
    ENABLE_SCP_ANALYSIS="true",
    LOG_LEVEL="INFO"
  }
```

3. Update the email sending code in [`src/lambda/modules/email_utils.py`](../src/lambda/modules/email_utils.py:1):

```python
# Update the Source parameter in send_email function
response = client.send_raw_email(
    Source=os.environ.get('SENDER_EMAIL', os.environ.get('RECIPIENT_EMAIL')),
    Destinations=[recipient],
    RawMessage={'Data': message}
)
```

## Email Template Customization

### Default Email Template

The tool sends emails with the following structure:

```
Subject: AWS Access Review Report - [Date]

Body:
[AI-generated narrative summary]

Attachment: access_review_YYYYMMDD_HHMMSS.csv
```

### Customize Email Subject

Edit [`src/lambda/modules/email_utils.py`](../src/lambda/modules/email_utils.py:1):

```python
def send_report_email(narrative, csv_content, recipient):
    # ... existing code ...
    
    # Customize subject line
    subject = f"AWS Access Review Report - {datetime.now().strftime('%Y-%m-%d')}"
    
    # Add severity to subject if critical findings exist
    critical_count = len([f for f in findings if f['severity'] == 'CRITICAL'])
    if critical_count > 0:
        subject = f"[CRITICAL] {subject}"
    
    # ... rest of the code ...
```

### Customize Email Body

Edit [`src/lambda/modules/email_utils.py`](../src/lambda/modules/email_utils.py:1):

```python
def send_report_email(narrative, csv_content, recipient):
    # ... existing code ...
    
    # Customize email body
    body = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; }}
            .header {{ background-color: #ff9900; color: white; padding: 20px; }}
            .content {{ padding: 20px; }}
            .footer {{ background-color: #f0f0f0; padding: 10px; text-align: center; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>AWS Access Review Report</h1>
            <p>Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
        <div class="content">
            <h2>Executive Summary</h2>
            {narrative}
            
            <h2>Report Details</h2>
            <ul>
                <li>Total Findings: {len(findings)}</li>
                <li>Critical: {critical_count}</li>
                <li>High: {high_count}</li>
                <li>Medium: {medium_count}</li>
                <li>Low: {low_count}</li>
            </ul>
        </div>
        <div class="footer">
            <p>This is an automated report from the AWS Automated Access Review tool.</p>
        </div>
    </body>
    </html>
    """
    
    # ... rest of the code ...
```

### Add Multiple Recipients

To send reports to multiple recipients:

```python
def send_report_email(narrative, csv_content, recipients):
    """
    Send report email to multiple recipients.
    
    Args:
        narrative: AI-generated narrative summary
        csv_content: Report CSV content as bytes
        recipients: List of email addresses
    """
    client = boto3.client('ses')
    
    # Create email message
    message = MIMEMultipart()
    message['Subject'] = f"AWS Access Review Report - {datetime.now().strftime('%Y-%m-%d')}"
    message['From'] = os.environ.get('SENDER_EMAIL', recipients[0])
    message['To'] = ', '.join(recipients)
    
    # ... rest of the code ...
    
    # Send to all recipients
    response = client.send_raw_email(
        Source=message['From'],
        Destinations=recipients,
        RawMessage={'Data': message.as_string()}
    )
```

Update the Lambda handler to pass multiple recipients:

```python
# In src/lambda/index.py
recipients = os.environ.get('RECIPIENT_EMAILS', '').split(',')
if recipient and csv_content:
    email_id = send_report_email(narrative, csv_content, recipients)
```

## Sending Limits and Quotas

### Default Sending Limits

| Limit Type | Sandbox Mode | Production Mode |
|------------|--------------|-----------------|
| Daily Sending Limit | 200 emails | 10,000+ emails (customizable) |
| Maximum Send Rate | 1 email/second | 5-90 emails/second (customizable) |
| Recipients | Verified only | Any email address |

### Check Current Quotas

```bash
# Get send quota
aws ses get-send-quota

# Get send statistics
aws ses get-send-statistics

# Expected output:
# {
#     "Max24HourSend": 10000,
#     "MaxSendRate": 5.0,
#     "SentLast24Hours": 5
# }
```

### Request Increased Limits

If you need higher limits:

1. Navigate to Amazon SES in the AWS Console
2. Go to **Configuration** → **Sending limits**
3. Click **Request a sending limit increase**
4. Complete the request form:
   - **Desired Daily Sending Limit**: Enter your desired limit
   - **Desired Maximum Send Rate**: Enter your desired rate
   - **Use Case Description**: Explain why you need the increase
5. Submit the request

### Monitor Sending Activity

```bash
# Get send statistics
aws ses get-send-statistics

# Expected output:
# {
#     "SendDataPoints": [
#         {
#             "Timestamp": "2024-01-01T00:00:00Z",
#             "DeliveryAttempts": 5,
#             "Bounces": 0,
#             "Complaints": 0,
#             "Rejects": 0
#         }
#     ]
# }
```

## Email Delivery Optimization

### Improve Deliverability

#### 1. Set Up SPF Records

Add this TXT record to your domain's DNS:

```
Name: example.com
Type: TXT
Value: "v=spf1 include:amazonses.com ~all"
```

#### 2. Set Up DKIM

DKIM (DomainKeys Identified Mail) adds a cryptographic signature to your emails:

```bash
# Enable DKIM for a domain
aws ses verify-domain-dkim \
  --domain example.com

# This returns three CNAME records to add to your DNS
```

Add these CNAME records to your DNS:

```
Name: [selector1]._domainkey.example.com
Type: CNAME
Value: [selector1].dkim.amazonses.com

Name: [selector2]._domainkey.example.com
Type: CNAME
Value: [selector2].dkim.amazonses.com

Name: [selector3]._domainkey.example.com
Type: CNAME
Value: [selector3].dkim.amazonses.com
```

#### 3. Set Up DMARC

DMARC (Domain-based Message Authentication, Reporting, and Conformance) policies:

```
Name: _dmarc.example.com
Type: TXT
Value: "v=DMARC1; p=quarantine; rua=mailto:dmarc@example.com"
```

DMARC policy options:
- `p=none`: Monitor only, don't take action
- `p=quarantine`: Send suspicious emails to spam
- `p=reject`: Reject suspicious emails

### Monitor Bounces and Complaints

```bash
# List verified identities
aws ses list-verified-email-identities

# Get bounce statistics
aws ses get-send-statistics --query 'SendDataPoints[*].Bounces'

# Get complaint statistics
aws ses get-send-statistics --query 'SendDataPoints[*].Complaints'
```

### Set Up Bounce and Complaint Notifications

#### Using SNS

```bash
# Create SNS topic for bounces
aws sns create-topic \
  --name ses-bounces

# Create SNS topic for complaints
aws sns create-topic \
  --name ses-complaints

# Configure SES to publish bounces to SNS
aws ses set-identity-feedback-forwarding-enabled \
  --identity you@company.com \
  --forwarding-enabled

aws ses set-identity-notification-topic \
  --identity you@company.com \
  --notification-type Bounce \
  --sns-topic arn:aws:sns:region:account-id:ses-bounces

aws ses set-identity-notification-topic \
  --identity you@company.com \
  --notification-type Complaint \
  --sns-topic arn:aws:sns:region:account-id:ses-complaints
```

## Troubleshooting Email Delivery

### Issue: Email Not Received

**Symptoms**: Report generated but email not delivered

**Troubleshooting Steps**:

1. **Check Verification Status**
   ```bash
   aws ses get-identity-verification-attributes \
     --identities you@company.com
   ```
   Ensure status is `Success`

2. **Check Sending Limits**
   ```bash
   aws ses get-send-quota
   ```
   Ensure you haven't exceeded daily limit

3. **Check Send Statistics**
   ```bash
   aws ses get-send-statistics
   ```
   Look for bounces or rejects

4. **Check CloudWatch Logs**
   ```bash
   # Get Lambda logs
   aws logs tail /aws/lambda/aws-access-review-access-review --follow
   ```

5. **Check Spam Folder**
   - Email may be in recipient's spam folder
   - Ask recipient to mark as "Not Spam"

6. **Verify SES is Not in Sandbox**
   - Sandbox mode only allows sending to verified addresses
   - Request production access if needed

### Issue: Email in Spam Folder

**Symptoms**: Email delivered but marked as spam

**Solutions**:

1. **Set Up SPF, DKIM, and DMARC** (see above)
2. **Use a Verified Domain** instead of individual email
3. **Improve Email Content**:
   - Avoid spam trigger words
   - Include plain text version
   - Keep subject line relevant
4. **Monitor Reputation**:
   ```bash
   # Check your sending reputation
   aws ses get-account-sending-enabled
   ```

### Issue: Bounce Received

**Symptoms**: Email bounced back

**Types of Bounces**:

- **Hard Bounce**: Permanent failure (invalid email, domain doesn't exist)
- **Soft Bounce**: Temporary failure (mailbox full, server down)

**Solutions**:

1. **Check Bounce Reason**:
   ```bash
   # View bounce notifications in SNS
   aws sns subscribe \
     --topic-arn arn:aws:sns:region:account-id:ses-bounces \
     --protocol email \
     --notification-endpoint you@company.com
   ```

2. **Remove Invalid Emails**: Update recipient list to remove bounced addresses

3. **Retry Soft Bounces**: The tool will automatically retry on next run

### Issue: Complaint Received

**Symptoms**: Recipient marked email as spam

**Solutions**:

1. **Investigate Complaint**: Check why recipient marked as spam
2. **Unsubscribe Option**: Provide easy unsubscribe mechanism
3. **Review Content**: Ensure email content is relevant and expected
4. **Monitor Complaint Rate**: Keep complaint rate below 0.1%

### Issue: Rate Limit Exceeded

**Symptoms**: Error: "Maximum sending rate exceeded"

**Solutions**:

1. **Check Current Rate**:
   ```bash
   aws ses get-send-quota
   ```

2. **Request Rate Increase**: Follow steps in "Request Increased Limits" section

3. **Implement Throttling**: Add delay between emails if sending multiple

4. **Use SES Sending Pooling**: Distribute sending across multiple identities

## Email Security Best Practices

### 1. Never Send Credentials
- Never include AWS access keys or secrets in emails
- Use presigned URLs for secure report sharing
- Reports are already stored securely in S3

### 2. Use Verified Identities Only
- Always verify sender and recipient emails
- Use domain verification for organizations
- Regularly audit verified identities

### 3. Monitor Sending Activity
- Set up CloudWatch alarms for unusual activity
- Monitor bounce and complaint rates
- Review send statistics regularly

### 4. Implement Rate Limiting
- Respect SES sending limits
- Implement backoff on errors
- Monitor for abuse

### 5. Use Encryption
- SES supports TLS for email transmission
- Reports are encrypted at rest in S3
- Use presigned URLs with expiration

### 6. Compliance Considerations
- GDPR: Ensure consent for email communications
- CAN-SPAM: Include physical address and unsubscribe option
- SOC 2: Maintain audit trail of email communications

## Cost Considerations

### SES Pricing

| Usage | Cost |
|-------|------|
| First 62,000 emails/month | Free |
| Additional emails | $0.10 per 1,000 emails |
| Additional attachments | $0.12 per 1,000 attachments (GB) |

### Cost Optimization Tips

1. **Use Free Tier**: Stay within 62,000 emails/month
2. **Optimize Attachments**: Compress reports before attaching
3. **Batch Recipients**: Send one email to multiple recipients
4. **Monitor Usage**: Set up CloudWatch alarms for cost tracking

### Estimate Monthly Cost

For typical usage (1-5 emails/month):
- **Emails**: 5 × $0.10/1,000 = $0.0005
- **Attachments**: 5 × 0.1 MB × $0.12/1,000 = $0.00006
- **Total**: ~$0.001/month (negligible)

## Testing Email Configuration

### Test Email Sending

```bash
# Send a test email using AWS CLI
aws ses send-email \
  --from you@company.com \
  --to recipient@company.com \
  --subject "Test Email from SES" \
  --text "This is a test email from Amazon SES."

# Expected output:
# {
#     "MessageId": "..."
# }
```

### Test with Lambda

```bash
# Invoke Lambda with dry-run mode (no actual email sent in dry-run)
aws lambda invoke \
  --function-name aws-access-review-access-review \
  --payload '{"dry_run": true}' \
  --cli-binary-format raw-in-base64-out \
  response.json

# Invoke Lambda without dry-run (sends actual email)
aws lambda invoke \
  --function-name aws-access-review-access-review \
  --payload '{}' \
  --cli-binary-format raw-in-base64-out \
  response.json
```

### Verify Email Receipt

1. Check recipient inbox
2. Check spam folder
3. Verify email content and attachment
4. Check email headers for authentication (SPF, DKIM)

## Related Documentation
- [Deployment Guide](deployment.md)
- [Usage Guide](usage.md)
- [Troubleshooting](troubleshooting.md)
- [Architecture](architecture.md)
