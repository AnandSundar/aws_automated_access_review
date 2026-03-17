# Main Lambda Handler for AWS Automated Access Review
import os
import boto3
import concurrent.futures
from datetime import datetime
from botocore.exceptions import ClientError, BotoCoreError

# Import modules
from modules.iam_findings import get_iam_findings
from modules.securityhub_findings import get_securityhub_findings
from modules.access_analyzer_findings import get_access_analyzer_findings
from modules.cloudtrail_findings import get_cloudtrail_findings
from modules.narrative import generate_narrative
from modules.reporting import generate_report
from modules.email_utils import send_report_email

# Import mock data module for dry-run mode
from modules.mock_data import (
    get_all_mock_findings,
    get_dry_run_summary,
    get_mock_narrative,
)


def is_dry_run(event):
    """
    Check if dry-run mode is enabled.
    Can be triggered via:
    1. Environment variable: DRY_RUN=true
    2. Event parameter: event['dry_run'] = true
    """
    # Check environment variable
    if os.environ.get("DRY_RUN", "").lower() == "true":
        return True

    # Check event parameter
    if event and isinstance(event, dict):
        if event.get("dry_run", False) or event.get("dryRun", False):
            return True

    return False


def handle_dry_run(event):
    """
    Handle dry-run mode - returns mock findings for demonstration.
    """
    print("=" * 60)
    print("DRY RUN MODE ENABLED")
    print("Using mock data for demonstration purposes")
    print("=" * 60)

    # Get mock findings
    findings = get_all_mock_findings()
    summary = get_dry_run_summary()

    print(f"Generated {len(findings)} mock findings:")
    print(f"  - CRITICAL: {summary['severity_breakdown']['CRITICAL']}")
    print(f"  - HIGH: {summary['severity_breakdown']['HIGH']}")
    print(f"  - MEDIUM: {summary['severity_breakdown']['MEDIUM']}")
    print(f"  - LOW: {summary['severity_breakdown']['LOW']}")

    # Generate mock narrative (no Bedrock call needed in dry-run mode)
    mock_narrative = get_mock_narrative(findings)

    # Get report format from event (default to csv)
    report_format = "csv"
    if event and isinstance(event, dict):
        report_format = event.get("format", "csv").lower()
        if report_format not in ("csv", "xlsx"):
            report_format = "csv"

    # Generate report locally in 'reports' folder
    local_path, _ = generate_report(
        findings, format_type=report_format, local_mode=True
    )

    return {
        "statusCode": 200,
        "body": {
            "mode": "DRY_RUN",
            "message": "Access Review Completed (Dry Run - Demo Mode)",
            "timestamp": summary["timestamp"],
            "source": summary["source"],
            "description": summary["description"],
            "finding_counts": summary["severity_breakdown"],
            "total_findings": summary["total_findings"],
            "report_path": local_path,
            "report_url": f"file://{local_path}",
            "email_message_id": "demo-message-id-12345",
            "narrative_summary": (
                mock_narrative[:500] + "..."
                if len(mock_narrative) > 500
                else mock_narrative
            ),
        },
    }


def lambda_handler(event, context):
    """
    Orchestrates the automated access review process.

    Event parameters:
        - dry_run: Run in demo mode with mock data
        - format: Report format - 'csv' or 'xlsx' (default: 'csv')
    """
    print(f"Starting Access Review at {datetime.now().isoformat()}")
    print(
        f"AWS Request ID: {context.request_id if hasattr(context, 'request_id') else 'N/A'}"
    )

    # Check for dry-run mode
    if is_dry_run(event):
        return handle_dry_run(event)

    # Get report format from event (default to csv)
    report_format = "csv"
    if event and isinstance(event, dict):
        report_format = event.get("format", "csv").lower()
        if report_format not in ("csv", "xlsx"):
            report_format = "csv"
    print(f"Report format: {report_format}")

    # Initialize findings list
    findings = []

    # 1. Run finding modules in parallel
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = {
            executor.submit(get_iam_findings): "IAM",
            executor.submit(get_securityhub_findings): "SecurityHub",
            executor.submit(get_access_analyzer_findings): "AccessAnalyzer",
            executor.submit(get_cloudtrail_findings): "CloudTrail",
        }

        for future in concurrent.futures.as_completed(futures):
            module_name = futures[future]
            try:
                module_findings = future.result()
                print(f"Module {module_name} returned {len(module_findings)} findings.")
                findings.extend(module_findings)
            except (ClientError, BotoCoreError) as e:
                print(f"Module {module_name} failed with AWS error: {e}")
            except Exception as e:  # pylint: disable=broad-except
                # Catch other exceptions but log appropriately
                print(f"Module {module_name} failed: {e}")

    # 2. Generate Report and Upload to S3 (or save locally in dry-run mode)
    s3_key, presigned_url = generate_report(
        findings, format_type=report_format, local_mode=is_dry_run(event)
    )

    # 3. Generate Bedrock Narrative
    narrative = generate_narrative(findings)

    # 4. Send Email via SES
    recipient = os.environ.get("RECIPIENT_EMAIL")

    # We need the CSV content for the attachment
    # In a real scenario, we might read it back from S3 or pass it from reporting
    # For this demo, we'll re-generate the string or modify reporting to return it.
    # Let's assume reporting.py can provide the content or we fetch it.
    s3 = boto3.client("s3")
    csv_content = b""
    if s3_key:
        bucket = os.environ.get("REPORT_BUCKET")
        csv_obj = s3.get_object(Bucket=bucket, Key=s3_key)
        csv_content = csv_obj["Body"].read()

    email_id = None
    if recipient and csv_content:
        email_id = send_report_email(narrative, csv_content, recipient)

    # 5. Return Summary
    severity_counts = {
        "CRITICAL": len([f for f in findings if f["severity"] == "CRITICAL"]),
        "HIGH": len([f for f in findings if f["severity"] == "HIGH"]),
        "MEDIUM": len([f for f in findings if f["severity"] == "MEDIUM"]),
        "LOW": len([f for f in findings if f["severity"] == "LOW"]),
    }

    return {
        "statusCode": 200,
        "body": {
            "message": "Access Review Completed",
            "finding_counts": severity_counts,
            "report_url": presigned_url,
            "email_message_id": email_id,
        },
    }
