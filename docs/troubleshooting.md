# Troubleshooting Guide

## Overview

This guide helps you diagnose and resolve common issues with the AWS Automated Access Review tool. It covers error messages, debugging tips, and solutions to frequent problems.

## Common Issues and Solutions

### Deployment Issues

#### Issue: CloudFormation Stack Creation Fails

**Symptoms**:
```
Stack creation failed: The following resource(s) failed to create: [ResourceName]
```

**Possible Causes**:
1. Insufficient IAM permissions
2. Resource name conflicts
3. Invalid parameter values
4. Service quota limits exceeded

**Solutions**:

1. **Check IAM Permissions**:
   ```bash
   # Verify you have necessary permissions
   aws iam list-attached-role-policies --role-name $USER
   
   # Ensure you can create CloudFormation stacks
   aws cloudformation create-stack --stack-name test-stack \
     --template-body '{"Resources":{}}' \
     --capabilities CAPABILITY_IAM
   ```

2. **Check Resource Names**:
   ```bash
   # Check if bucket name already exists
   aws s3 ls | grep your-bucket-name
   
   # Check if Lambda function name exists
   aws lambda list-functions | grep your-function-name
   ```

3. **Validate Parameters**:
   ```bash
   # Validate email format
   aws ses verify-email-identity --email-address you@company.com
   
   # Validate Bedrock model exists
   aws bedrock list-foundation-models --region us-east-1
   ```

4. **Check Service Quotas**:
   ```bash
   # Check Lambda quota
   aws service-quotas list-service-quotas \
     --service-code lambda \
     --quota-code L-99999999
   
   # Check S3 quota
   aws service-quotas list-service-quotas \
     --service-code s3 \
     --quota-code L-99999999
   ```

#### Issue: CloudFormation Rollback

**Symptoms**:
```
Stack creation failed and rolled back
```

**Solutions**:

1. **View Error Details**:
   ```bash
   # Get stack events
   aws cloudformation describe-stack-events \
     --stack-name aws-access-review \
     --max-items 20
   
   # Get specific resource status
   aws cloudformation describe-stack-resources \
     --stack-name aws-access-review
   ```

2. **Check CloudFormation Logs**:
   ```bash
   # Enable CloudFormation debugging
   aws cloudformation update-stack \
     --stack-name aws-access-review \
     --use-previous-template \
     --parameters ParameterKey=EnableTerminationProtection,ParameterValue=false \
     --capabilities CAPABILITY_IAM
   ```

3. **Delete and Recreate**:
   ```bash
   # Delete failed stack
   aws cloudformation delete-stack --stack-name aws-access-review
   
   # Wait for deletion to complete
   aws cloudformation wait stack-delete-complete \
     --stack-name aws-access-review
   
   # Recreate stack
   aws cloudformation deploy \
     --template-file templates/access-review-real.yaml \
     --stack-name aws-access-review \
     --parameter-overrides \
       RecipientEmail=you@company.com \
     --capabilities CAPABILITY_IAM
   ```

### Lambda Execution Issues

#### Issue: Lambda Timeout

**Symptoms**:
```
Task timed out after 300.00 seconds
```

**Solutions**:

1. **Increase Lambda Timeout**:
   ```bash
   aws lambda update-function-configuration \
     --function-name aws-access-review-access-review \
     --timeout 900
   ```

2. **Increase Lambda Memory**:
   ```bash
   aws lambda update-function-configuration \
     --function-name aws-access-review-access-review \
     --memory-size 1024
   ```

3. **Check for Slow Operations**:
   ```bash
   # View CloudWatch logs
   aws logs tail /aws/lambda/aws-access-review-access-review --follow
   
   # Look for slow module executions
   grep "Module.*returned.*findings" logs
   ```

4. **Optimize Code**:
   - Reduce API calls
   - Use pagination efficiently
   - Implement caching
   - Parallelize independent operations

#### Issue: Lambda Out of Memory

**Symptoms**:
```
Runtime exited without providing a reason
Memory Size: 512 MB
Max Memory Used: 512 MB
```

**Solutions**:

1. **Increase Memory Allocation**:
   ```bash
   aws lambda update-function-configuration \
     --function-name aws-access-review-access-review \
     --memory-size 2048
   ```

2. **Check Memory Usage**:
   ```bash
   # View memory usage in CloudWatch
   aws cloudwatch get-metric-statistics \
     --namespace AWS/Lambda \
     --metric-name Duration \
     --dimensions Name=FunctionName,Value=aws-access-review-access-review \
     --start-time 2024-01-01T00:00:00Z \
     --end-time 2024-01-02T00:00:00Z \
     --period 3600 \
     --statistics Average
   ```

3. **Optimize Memory Usage**:
   - Process data in chunks
   - Use generators instead of lists
   - Clear unused variables
   - Use efficient data structures

#### Issue: Lambda Permission Denied

**Symptoms**:
```
AccessDeniedException: User: arn:aws:iam::123456789012:role/... is not authorized to perform: ...
```

**Solutions**:

1. **Check IAM Role Permissions**:
   ```bash
   # Get Lambda role
   ROLE_ARN=$(aws lambda get-function-configuration \
     --function-name aws-access-review-access-review \
     --query Role --output text)
   
   # Get role policies
   aws iam list-attached-role-policies --role-name $(basename $ROLE_ARN)
   
   # Get inline policies
   aws iam list-role-policies --role-name $(basename $ROLE_ARN)
   ```

2. **Verify Required Permissions**:
   ```bash
   # Simulate policy
   aws iam simulate-principal-policy \
     --policy-source-arn $ROLE_ARN \
     --action-names iam:ListUsers securityhub:GetFindings \
     --resource-arns "*"
   ```

3. **Update IAM Role**:
   ```bash
   # Add missing permissions
   aws iam put-role-policy \
     --role-name $(basename $ROLE_ARN) \
     --policy-name AdditionalPermissions \
     --policy-document '{
         "Version": "2012-10-17",
         "Statement": [
             {
                 "Effect": "Allow",
                 "Action": "iam:ListUsers",
                 "Resource": "*"
             }
         ]
     }'
   ```

### AWS Service Integration Issues

#### Issue: IAM Access Denied

**Symptoms**:
```
botocore.exceptions.ClientError: An error occurred (AccessDenied) when calling the ListUsers operation
```

**Solutions**:

1. **Verify IAM Permissions**:
   ```bash
   # Check if role has IAM permissions
   aws iam get-role-policy \
     --role-name aws-access-review-lambda-execution-role \
     --policy-name AccessReviewPermissions
   ```

2. **Test IAM Access**:
   ```bash
   # Assume the Lambda role and test
   aws sts assume-role \
     --role-arn arn:aws:iam::123456789012:role/aws-access-review-lambda-execution-role \
     --role-session-name test
   
   # Use the returned credentials to test IAM access
   export AWS_ACCESS_KEY_ID=...
   export AWS_SECRET_ACCESS_KEY=...
   export AWS_SESSION_TOKEN=...
   
   aws iam list-users
   ```

3. **Check Service Control Policies**:
   ```bash
   # If using AWS Organizations, check SCPs
   aws organizations list-policies \
     --filter SERVICE_CONTROL_POLICY
   ```

#### Issue: Security Hub Access Denied

**Symptoms**:
```
botocore.exceptions.ClientError: An error occurred (AccessDeniedException) when calling the GetFindings operation
```

**Solutions**:

1. **Enable Security Hub**:
   ```bash
   # Enable Security Hub in the account
   aws securityhub enable-security-hub
   ```

2. **Verify Security Hub Permissions**:
   ```bash
   # Check if role has Security Hub permissions
   aws iam get-role-policy \
     --role-name aws-access-review-lambda-execution-role \
     --policy-name AccessReviewPermissions | grep securityhub
   ```

3. **Test Security Hub Access**:
   ```bash
   # Test Security Hub API
   aws securityhub get-findings
   ```

#### Issue: Access Analyzer Not Configured

**Symptoms**:
```
botocore.exceptions.ClientError: An error occurred (ResourceNotFoundException) when calling the ListFindings operation
```

**Solutions**:

1. **Create Access Analyzer**:
   ```bash
   # Create account-level analyzer
   aws accessanalyzer create-analyzer \
     --analyzer-name my-analyzer \
     --type ACCOUNT
   ```

2. **Verify Analyzer Exists**:
   ```bash
   # List analyzers
   aws accessanalyzer list-analyzers
   
   # Get analyzer details
   aws accessanalyzer get-analyzer \
     --analyzer-arn arn:aws:access-analyzer:region:account-id:analyzer/my-analyzer
   ```

3. **Wait for Analyzer Initialization**:
   ```bash
   # Analyzers may take time to initialize
   # Check status
   aws accessanalyzer get-analyzer \
     --analyzer-arn arn:aws:access-analyzer:region:account-id:analyzer/my-analyzer \
     --query status
   ```

#### Issue: CloudTrail Not Enabled

**Symptoms**:
```
No CloudTrail trails found in the account
```

**Solutions**:

1. **Create CloudTrail**:
   ```bash
   # Create S3 bucket for logs
   aws s3 mb s3://my-cloudtrail-logs-bucket
   
   # Create CloudTrail
   aws cloudtrail create-trail \
     --name my-trail \
     --s3-bucket-name my-cloudtrail-logs-bucket \
     --is-multi-region-trail
   
   # Start logging
   aws cloudtrail start-logging --name my-trail
   ```

2. **Verify CloudTrail Configuration**:
   ```bash
   # List trails
   aws cloudtrail list-trails
   
   # Get trail status
   aws cloudtrail get-trail-status --name my-trail
   ```

### Amazon Bedrock Issues

#### Issue: Bedrock Access Denied

**Symptoms**:
```
botocore.exceptions.ClientError: An error occurred (AccessDeniedException) when calling the InvokeModel operation
```

**Solutions**:

1. **Enable Bedrock Model Access**:
   - Go to AWS Console → Amazon Bedrock
   - Navigate to Model access
   - Enable Claude 3 Sonnet model
   - Wait for access to be granted

2. **Verify Bedrock Permissions**:
   ```bash
   # Check if role has Bedrock permissions
   aws iam get-role-policy \
     --role-name aws-access-review-lambda-execution-role \
     --policy-name AccessReviewPermissions | grep bedrock
   ```

3. **Test Bedrock Access**:
   ```bash
   # List available models
   aws bedrock list-foundation-models --region us-east-1
   
   # Test model invocation
   aws bedrock invoke-model \
     --model-id anthropic.claude-3-sonnet-20240229-v1:0 \
     --body '{"prompt":"Hello","max_tokens_to_sample":100}' \
     --region us-east-1
   ```

4. **Check Region Availability**:
   ```bash
   # Verify Bedrock is available in the region
   aws bedrock list-foundation-models --region us-east-1
   ```

#### Issue: Bedrock Model Not Found

**Symptoms**:
```
botocore.exceptions.ClientError: An error occurred (ResourceNotFoundException) when calling the InvokeModel operation
```

**Solutions**:

1. **Verify Model ID**:
   ```bash
   # List available models
   aws bedrock list-foundation-models --region us-east-1 \
     --query 'modelSummaries[?contains(modelId, `claude`)].modelId' \
     --output table
   ```

2. **Update Model ID**:
   ```bash
   # Update Lambda environment variable
   aws lambda update-function-configuration \
     --function-name aws-access-review-access-review \
     --environment Variables={
       BEDROCK_MODEL_ID="anthropic.claude-3-sonnet-20240229-v1:0"
     }
   ```

3. **Use Available Model**:
   ```bash
   # If Claude is not available, use alternative model
   aws lambda update-function-configuration \
     --function-name aws-access-review-access-review \
     --environment Variables={
       BEDROCK_MODEL_ID="amazon.titan-text-express-v1"
     }
   ```

### Amazon SES Issues

#### Issue: Email Not Received

**Symptoms**: Report generated but email not delivered

**Solutions**:

1. **Check Email Verification**:
   ```bash
   # Check verification status
   aws ses get-identity-verification-attributes \
     --identities you@company.com
   ```

2. **Check SES Sending Limits**:
   ```bash
   # Get send quota
   aws ses get-send-quota
   
   # Get send statistics
   aws ses get-send-statistics
   ```

3. **Check SES Sandbox Mode**:
   ```bash
   # Check if account is in sandbox
   aws ses get-account-sending-enabled
   ```

4. **Check CloudWatch Logs**:
   ```bash
   # View Lambda logs for email errors
   aws logs tail /aws/lambda/aws-access-review-access-review --follow
   ```

5. **Check Spam Folder**:
   - Email may be in recipient's spam folder
   - Ask recipient to mark as "Not Spam"

#### Issue: SES Bounce Received

**Symptoms**: Email bounced back

**Solutions**:

1. **Check Bounce Reason**:
   ```bash
   # View bounce notifications in SNS
   aws sns list-subscriptions-by-topic \
     --topic-arn arn:aws:sns:region:account-id:ses-bounces
   ```

2. **Verify Recipient Email**:
   ```bash
   # Test email delivery
   aws ses send-email \
     --from you@company.com \
     --to recipient@company.com \
     --subject "Test Email" \
     --text "This is a test email."
   ```

3. **Remove Invalid Emails**: Update recipient list to remove bounced addresses

### S3 Issues

#### Issue: S3 Access Denied

**Symptoms**:
```
botocore.exceptions.ClientError: An error occurred (AccessDenied) when calling the PutObject operation
```

**Solutions**:

1. **Check Bucket Policy**:
   ```bash
   # Get bucket policy
   aws s3api get-bucket-policy --bucket your-bucket-name
   ```

2. **Check Bucket Permissions**:
   ```bash
   # Check if Lambda role has S3 permissions
   aws iam get-role-policy \
     --role-name aws-access-review-lambda-execution-role \
     --policy-name AccessReviewPermissions | grep s3
   ```

3. **Verify Bucket Exists**:
   ```bash
   # List buckets
   aws s3 ls
   
   # Check specific bucket
   aws s3 ls s3://your-bucket-name
   ```

4. **Check Bucket Region**:
   ```bash
   # Get bucket location
   aws s3api get-bucket-location --bucket your-bucket-name
   ```

#### Issue: S3 Bucket Not Found

**Symptoms**:
```
botocore.exceptions.ClientError: An error occurred (NoSuchBucket) when calling the PutObject operation
```

**Solutions**:

1. **Create Bucket**:
   ```bash
   # Create bucket
   aws s3 mb s3://your-bucket-name
   
   # Or update CloudFormation stack to create bucket
   aws cloudformation deploy \
     --template-file templates/access-review-real.yaml \
     --stack-name aws-access-review \
     --parameter-overrides \
       BucketName=your-bucket-name \
     --capabilities CAPABILITY_IAM
   ```

2. **Verify Bucket Name**:
   ```bash
   # Check environment variable
   aws lambda get-function-configuration \
     --function-name aws-access-review-access-review \
     --query Environment.Variables.REPORT_BUCKET
   ```

### EventBridge Issues

#### Issue: EventBridge Rule Not Triggering

**Symptoms**: Scheduled Lambda execution not occurring

**Solutions**:

1. **Check Rule Status**:
   ```bash
   # Get rule details
   aws events describe-rule --name aws-access-review-schedule
   ```

2. **Enable Rule**:
   ```bash
   # Enable rule if disabled
   aws events enable-rule --name aws-access-review-schedule
   ```

3. **Check Schedule Expression**:
   ```bash
   # Verify schedule is correct
   aws events describe-rule --name aws-access-review-schedule \
     --query ScheduleExpression
   ```

4. **Test Rule Manually**:
   ```bash
   # Test rule by sending test event
   aws events put-events \
     --entries '[{
       "Source": "com.mycompany.test",
       "DetailType": "TestEvent",
       "Detail": "{\"test\": \"data\"}"
     }]'
   ```

## Debugging Tips

### Enable Debug Logging

```bash
# Update Lambda environment to enable debug logging
aws lambda update-function-configuration \
  --function-name aws-access-review-access-review \
  --environment Variables={
    LOG_LEVEL="DEBUG"
  }
```

### View CloudWatch Logs

```bash
# Tail logs in real-time
aws logs tail /aws/lambda/aws-access-review-access-review --follow

# Get specific log stream
LOG_STREAM=$(aws logs describe-log-streams \
  --log-group-name /aws/lambda/aws-access-review-access-review \
  --order-by LastEventTime \
  --descending \
  --max-items 1 \
  --query 'logStreams[0].logStreamName' \
  --output text)

aws logs get-log-events \
  --log-group-name /aws/lambda/aws-access-review-access-review \
  --log-stream-name $LOG_STREAM \
  --limit 100
```

### Use AWS X-Ray

```bash
# Enable X-Ray tracing
aws lambda update-function-configuration \
  --function-name aws-access-review-access-review \
  --tracing-config Mode=Active

# View traces in AWS Console
# Or use AWS CLI
aws xray get-trace-summaries \
  --start-time 2024-01-01T00:00:00Z \
  --end-time 2024-01-02T00:00:00Z
```

### Test Locally

```bash
# Run Lambda locally
cd src/lambda

# Set environment variables
export REPORT_BUCKET=your-bucket-name
export RECIPIENT_EMAIL=you@company.com
export BEDROCK_REGION=us-east-1
export BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0

# Run handler
python -c "
from index import lambda_handler
result = lambda_handler({'dry_run': True}, None)
print(result)
"
```

### Use Dry-Run Mode

```bash
# Test without making AWS API calls
aws lambda invoke \
  --function-name aws-access-review-access-review \
  --payload '{"dry_run": true}' \
  --cli-binary-format raw-in-base64-out \
  response.json

cat response.json
```

## Error Messages and Meanings

### Common Error Messages

| Error Message | Meaning | Solution |
|---------------|---------|----------|
| `AccessDenied` | Insufficient IAM permissions | Check and update IAM role permissions |
| `ResourceNotFoundException` | Resource doesn't exist | Verify resource exists and is accessible |
| `TimeoutError` | Operation took too long | Increase Lambda timeout or optimize code |
| `ThrottlingException` | API rate limit exceeded | Implement exponential backoff or request quota increase |
| `ValidationException` | Invalid input parameters | Validate and correct input parameters |
| `ServiceUnavailable` | AWS service is down | Wait and retry, check AWS status page |
| `CredentialsError` | Invalid AWS credentials | Verify AWS credentials are correct |
| `NoSuchBucket` | S3 bucket doesn't exist | Create bucket or update bucket name |
| `EmailNotVerified` | Email not verified in SES | Verify email address in SES console |

### Lambda-Specific Errors

| Error | Meaning | Solution |
|-------|---------|----------|
| `Runtime.ExitError` | Lambda crashed | Check logs for unhandled exceptions |
| `HandlerNotFound` | Handler function not found | Verify handler name in Lambda configuration |
| `ImportModuleError` | Module import failed | Check dependencies and deployment package |
| `UserInitiated` | Lambda was stopped by user | Check if Lambda was manually stopped |

## Getting Help

### AWS Support

1. **AWS Trusted Advisor**:
   - Check for security best practices
   - Review service limits
   - Identify cost optimization opportunities

2. **AWS Support Center**:
   - Create support cases
   - Track case status
   - View technical resources

3. **AWS Forums**:
   - Search for similar issues
   - Post questions to the community
   - Get help from AWS experts

### Project Resources

1. **GitHub Issues**:
   - Report bugs
   - Request features
   - Ask questions

2. **Documentation**:
   - [Architecture Guide](architecture.md)
   - [Deployment Guide](deployment.md)
   - [Usage Guide](usage.md)
   - [Email Setup Guide](email-setup.md)
   - [Testing Guide](testing.md)

3. **Code Examples**:
   - Review test files for examples
   - Check [`src/lambda/`](../src/lambda/) for implementation details
   - Examine [`deployment/`](../deployment/) for deployment patterns

### Community Resources

1. **AWS Documentation**:
   - [AWS Lambda Documentation](https://docs.aws.amazon.com/lambda/)
   - [Amazon SES Documentation](https://docs.aws.amazon.com/ses/)
   - [Amazon Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)

2. **Stack Overflow**:
   - Tag questions with `aws-lambda`, `amazon-ses`, `amazon-bedrock`
   - Search for similar issues

3. **Reddit**:
   - r/aws
   - r/devops
   - r/SecurityEngineering

### Professional Support

1. **AWS Partners**:
   - Certified AWS partners can provide professional services
   - Look for partners with security and compliance expertise

2. **Consultants**:
   - Cloud security consultants
   - DevOps consultants
   - GRC consultants

3. **Training**:
   - AWS certification courses
   - Cloud security training
   - DevOps training

## Preventive Measures

### Regular Maintenance

1. **Monitor CloudWatch Alarms**:
   - Set up alarms for Lambda errors
   - Monitor execution duration
   - Track error rates

2. **Review Logs Regularly**:
   - Check for unusual patterns
   - Identify recurring issues
   - Track performance metrics

3. **Update Dependencies**:
   - Keep Python packages updated
   - Update AWS SDK versions
   - Review security advisories

### Best Practices

1. **Use Dry-Run Mode for Testing**:
   - Test changes in dry-run mode first
   - Verify functionality before production deployment

2. **Implement Rollback Procedures**:
   - Keep previous versions of deployment packages
   - Document rollback steps
   - Test rollback procedures

3. **Document Customizations**:
   - Keep track of custom changes
   - Document configuration parameters
   - Maintain change logs

4. **Regular Security Reviews**:
   - Review IAM permissions regularly
   - Audit access logs
   - Update security policies

### Monitoring and Alerting

1. **Set Up CloudWatch Dashboards**:
   - Create dashboards for key metrics
   - Monitor Lambda performance
   - Track error rates

2. **Configure SNS Notifications**:
   - Set up alerts for critical errors
   - Notify team members of issues
   - Integrate with incident management systems

3. **Implement Health Checks**:
   - Create health check endpoints
   - Monitor service availability
   - Automate recovery procedures

## Related Documentation
- [Architecture](architecture.md)
- [Deployment Guide](deployment.md)
- [Email Setup](email-setup.md)
- [Usage Guide](usage.md)
- [Testing Guide](testing.md)
