# Access Analyzer Findings Module for AWS Automated Access Review
import boto3


def get_access_analyzer_findings():
    """
    Retrieves active findings from IAM Access Analyzer for specific resource types.
    """
    findings = []
    analyzer = boto3.client("accessanalyzer")

    try:
        # List analyzers to get the ARN of the first one found
        analyzers = analyzer.list_analyzers(type="ACCOUNT")
        if not analyzers.get("analyzers"):
            print("No IAM Access Analyzer found in this account.")
            return findings

        analyzer_arn = analyzers["analyzers"][0]["arn"]

        # List active findings
        paginator = analyzer.get_paginator("list_findings")
        for page in paginator.paginate(
            analyzerArn=analyzer_arn, filter={"status": {"eq": ["ACTIVE"]}}
        ):
            for finding in page["findings"]:
                resource_type = finding.get("resourceType", "Unknown")

                # Filter for specific resource types as requested
                target_types = [
                    "AWS::S3::Bucket",
                    "AWS::IAM::Role",
                    "AWS::KMS::Key",
                    "AWS::Lambda::Function",
                    "AWS::SQS::Queue",
                ]
                if resource_type in target_types:
                    findings.append(
                        {
                            "resource_id": finding.get("resource", "Unknown"),
                            "resource_type": resource_type,
                            "service": (
                                resource_type.split("::")[1]
                                if "::" in resource_type
                                else "AccessAnalyzer"
                            ),
                            "severity": finding.get("severity", "MEDIUM").upper(),
                            "finding": f"External access detected: {finding.get('principal', {})}",
                            "recommendation": "Review resource policy to ensure external access is intentional.",
                        }
                    )

    except Exception as e:
        print(f"Error fetching Access Analyzer findings: {e}")

    return findings
