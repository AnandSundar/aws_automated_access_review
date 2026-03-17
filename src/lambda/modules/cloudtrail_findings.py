# CloudTrail Findings Module for AWS Automated Access Review
import boto3

def get_cloudtrail_findings():
    """
    Verifies CloudTrail configuration and returns findings.
    """
    findings = []
    ct = boto3.client('cloudtrail')
    
    try:
        response = ct.describe_trails()
        trails = response.get('trailList', [])
        
        if not trails:
            findings.append({
                'resource_id': 'Account',
                'resource_type': 'AWS_ACCOUNT',
                'service': 'CloudTrail',
                'severity': 'CRITICAL',
                'finding': "No CloudTrail trail exists in the account.",
                'recommendation': "Create at least one multi-region CloudTrail trail."
            })
            return findings

        for trail in trails:
            trail_name = trail['Name']
            
            # 1. Multi-region check
            if not trail.get('IsMultiRegionTrail', False):
                findings.append({
                    'resource_id': trail_name,
                    'resource_type': 'CLOUDTRAIL_TRAIL',
                    'service': 'CloudTrail',
                    'severity': 'HIGH',
                    'finding': f"Trail {trail_name} is not multi-region.",
                    'recommendation': "Enable multi-region logging for full visibility."
                })
            
            # 2. Log file validation check
            if not trail.get('LogFileValidationEnabled', False):
                findings.append({
                    'resource_id': trail_name,
                    'resource_type': 'CLOUDTRAIL_TRAIL',
                    'service': 'CloudTrail',
                    'severity': 'HIGH',
                    'finding': f"Log file validation is disabled for trail {trail_name}.",
                    'recommendation': "Enable log file validation to ensure log integrity."
                })
            
            # 3. CloudWatch Logs integration check
            if not trail.get('CloudWatchLogsLogGroupArn'):
                findings.append({
                    'resource_id': trail_name,
                    'resource_type': 'CLOUDTRAIL_TRAIL',
                    'service': 'CloudTrail',
                    'severity': 'MEDIUM',
                    'finding': f"CloudWatch Logs integration is missing for trail {trail_name}.",
                    'recommendation': "Integrate CloudTrail with CloudWatch Logs for real-time monitoring."
                })
            
            # 4. S3 Bucket Access Logging (Requires S3 client check)
            s3 = boto3.client('s3')
            bucket_name = trail.get('S3BucketName')
            if bucket_name:
                try:
                    logging = s3.get_bucket_logging(Bucket=bucket_name)
                    if 'LoggingEnabled' not in logging:
                        findings.append({
                            'resource_id': bucket_name,
                            'resource_type': 'S3_BUCKET',
                            'service': 'S3',
                            'severity': 'MEDIUM',
                            'finding': f"Access logging is disabled on CloudTrail bucket {bucket_name}.",
                            'recommendation': "Enable S3 server access logging for the trail bucket."
                        })
                except Exception:
                    pass

    except Exception as e:
        print(f"Error checking CloudTrail: {e}")
        
    return findings
