# Security Hub Findings Module for AWS Automated Access Review
import boto3

def get_securityhub_findings():
    """
    Pulls active findings from AWS Security Hub filtered by severity.
    """
    findings = []
    sh = boto3.client('securityhub')
    
    try:
        # Filter for active findings with CRITICAL or HIGH severity
        filters = {
            'RecordState': [{'Value': 'ACTIVE', 'Comparison': 'EQUALS'}],
            'SeverityLabel': [
                {'Value': 'CRITICAL', 'Comparison': 'EQUALS'},
                {'Value': 'HIGH', 'Comparison': 'EQUALS'}
            ],
            'WorkflowStatus': [{'Value': 'NEW', 'Comparison': 'EQUALS'}, {'Value': 'NOTIFIED', 'Comparison': 'EQUALS'}]
        }
        
        response = sh.get_findings(
            Filters=filters,
            MaxResults=20
        )
        
        for finding in response.get('Findings', []):
            resource_id = "Unknown"
            resource_type = "Unknown"
            
            if finding.get('Resources'):
                resource_id = finding['Resources'][0].get('Id', 'Unknown')
                resource_type = finding['Resources'][0].get('Type', 'Unknown')
            
            # Extract remediation URL if available
            remediation_url = finding.get('Remediation', {}).get('Recommendation', {}).get('Url', 'N/A')
            
            # Determine Service from ProductFields or Resource Type
            service = finding.get('ProductFields', {}).get('aws/securityhub/ProductName', 'Unknown')
            if service == 'Unknown' and ':' in resource_type:
                service = resource_type.split(':')[0]

            findings.append({
                'resource_id': resource_id,
                'resource_type': resource_type,
                'service': service,
                'severity': finding.get('Severity', {}).get('Label', 'UNKNOWN'),
                'finding': finding.get('Title', 'No Title'),
                'description': finding.get('Description', 'No Description'),
                'recommendation': f"See remediation: {remediation_url}"
            })
            
    except sh.exceptions.InvalidAccessException:
        print("Security Hub is not enabled in this account/region.")
    except Exception as e:
        print(f"Error fetching Security Hub findings: {e}")
        
    return findings
