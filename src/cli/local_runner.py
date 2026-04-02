#!/usr/bin/env python3
"""
Local runner for AWS Automated Access Review.

This CLI tool allows you to run the access review locally with either:
- Dry-run mode: Uses mock data for demonstration
- Production mode: Uses real AWS credentials to analyze actual AWS resources

Usage:
    python -m cli.local_runner --dry-run --format xlsx
    python -m cli.local_runner --format csv --region us-west-2 --profile my-profile
"""

import argparse
import sys
import os
import json
import time
import subprocess
from datetime import datetime
from pathlib import Path

# Add the parent directory to the path to import lambda modules
sys.path.insert(0, str(Path(__file__).parent.parent / "lambda"))

from index import lambda_handler


class MockContext:
    """Mock Lambda context object for local execution."""

    def __init__(self):
        self.request_id = f"local-{int(time.time())}"
        self.function_name = "aws-automated-access-review-local"
        self.function_version = "$LATEST"
        self.invoked_function_arn = "arn:aws:lambda:us-east-1:123456789012:function:local"
        self.memory_limit_in_mb = 256
        self.remaining_time_in_millis = 300000

    def get_remaining_time_in_millis(self):
        return self.remaining_time_in_millis


def list_aws_profiles():
    """List all available AWS profiles from AWS configuration."""
    try:
        result = subprocess.run(
            ["aws", "configure", "list-profiles"],
            capture_output=True,
            text=True,
            check=True,
        )
        profiles = result.stdout.strip().split("\n")
        return profiles
    except subprocess.CalledProcessError as e:
        print(f"Error listing AWS profiles: {e.stderr}")
        return []
    except FileNotFoundError:
        print("Error: AWS CLI is not installed or not in PATH")
        return []


def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Run AWS Automated Access Review locally",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run in dry-run mode with mock data
  python -m cli.local_runner --dry-run

  # Run in dry-run mode with XLSX output
  python -m cli.local_runner --dry-run --format xlsx

  # Run in production mode with specific AWS profile
  python -m cli.local_runner --profile my-aws-profile --region us-west-2

  # Run with verbose output
  python -m cli.local_runner --dry-run --verbose

  # List available AWS profiles
  python -m cli.local_runner --list-profiles
        """,
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run in dry-run mode using mock data (no AWS API calls)",
    )

    parser.add_argument(
        "--format",
        choices=["csv", "xlsx"],
        default="xlsx",
        help="Output format for the report (default: xlsx)",
    )

    parser.add_argument(
        "--output",
        type=str,
        default="./access_report",
        help="Output file path prefix (default: ./access_report)",
    )

    parser.add_argument(
        "--region",
        type=str,
        default="us-east-1",
        help="AWS region (default: us-east-1)",
    )

    parser.add_argument(
        "--profile",
        type=str,
        default=None,
        help="AWS profile to use (default: default profile)",
    )

    parser.add_argument(
        "--list-profiles",
        action="store_true",
        help="List all available AWS profiles and exit",
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output",
    )

    return parser.parse_args()


def setup_aws_config(args):
    """Setup AWS configuration based on command-line arguments."""
    if args.profile:
        # Verify the profile exists
        profiles = list_aws_profiles()
        if profiles and args.profile not in profiles:
            raise ValueError(
                f"AWS profile '{args.profile}' not found. "
                f"Available profiles: {', '.join(profiles)}"
            )
        os.environ["AWS_PROFILE"] = args.profile

    os.environ["AWS_DEFAULT_REGION"] = args.region

    if args.verbose:
        print(f"AWS Configuration:")
        print(f"  Region: {args.region}")
        if args.profile:
            print(f"  Profile: {args.profile}")
        print()


def create_event(args):
    """Create Lambda event object from command-line arguments."""
    event = {
        "dry_run": args.dry_run,
        "format": args.format,
        "output_prefix": args.output,
    }
    return event


def print_progress(message):
    """Print progress message."""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")


def print_result(result, verbose=False):
    """Print Lambda handler result in a readable format."""
    print()
    print("=" * 70)
    print("ACCESS REVIEW COMPLETED")
    print("=" * 70)

    status_code = result.get("statusCode", "N/A")
    print(f"Status Code: {status_code}")
    print()

    body = result.get("body", {})

    # Print mode information
    mode = body.get("mode", "PRODUCTION")
    print(f"Mode: {mode}")
    print()

    # Print message
    message = body.get("message", "No message")
    print(f"Message: {message}")
    print()

    # Print timestamp if available
    if "timestamp" in body:
        print(f"Timestamp: {body['timestamp']}")
        print()

    # Print finding counts
    finding_counts = body.get("finding_counts", {})
    if finding_counts:
        print("Finding Counts:")
        for severity in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
            count = finding_counts.get(severity, 0)
            if count > 0 or verbose:
                print(f"  {severity}: {count}")
        total_findings = body.get("total_findings", sum(finding_counts.values()))
        print(f"  TOTAL: {total_findings}")
        print()

    # Print report information
    report_path = body.get("report_path")
    report_url = body.get("report_url")
    if report_path:
        print("Report Information:")
        print(f"  Local Path: {report_path}")
        if report_url:
            print(f"  URL: {report_url}")
        print()

    # Print email information if available
    email_id = body.get("email_message_id")
    if email_id:
        print(f"Email Message ID: {email_id}")
        print()

    # Print narrative summary if available
    narrative = body.get("narrative_summary")
    if narrative:
        print("Narrative Summary:")
        print(f"  {narrative}")
        print()

    # Print additional information in verbose mode
    if verbose:
        print("Full Response:")
        print(json.dumps(result, indent=2))
        print()


def handle_error(error, verbose=False):
    """Handle and display errors gracefully."""
    print()
    print("=" * 70)
    print("ERROR OCCURRED")
    print("=" * 70)
    print(f"Error: {str(error)}")
    print()

    if verbose:
        import traceback

        print("Traceback:")
        traceback.print_exc()
        print()


def main():
    """Main entry point for the local runner."""
    args = parse_arguments()

    # Handle --list-profiles option
    if args.list_profiles:
        print()
        print("=" * 70)
        print("AVAILABLE AWS PROFILES")
        print("=" * 70)
        print()
        profiles = list_aws_profiles()
        if profiles:
            for profile in profiles:
                print(f"  - {profile}")
            print()
            print(f"Total profiles: {len(profiles)}")
            print()
        else:
            print("  No AWS profiles found or AWS CLI not available")
            print()
        return 0

    print()
    print("=" * 70)
    print("AWS AUTOMATED ACCESS REVIEW - LOCAL RUNNER")
    print("=" * 70)
    print()

    # Display configuration
    print("Configuration:")
    print(f"  Dry Run: {args.dry_run}")
    print(f"  Format: {args.format}")
    print(f"  Output: {args.output}")
    print(f"  Region: {args.region}")
    if args.profile:
        print(f"  Profile: {args.profile}")
    print(f"  Verbose: {args.verbose}")
    print()

    # Setup AWS configuration
    try:
        setup_aws_config(args)
    except ValueError as e:
        print(f"Error: {e}")
        print()
        print("Tip: Use --list-profiles to see available AWS profiles")
        print()
        return 1
    except Exception as e:
        print(f"Warning: Could not setup AWS configuration: {e}")
        print()

    # Create Lambda event
    event = create_event(args)

    if args.verbose:
        print("Event:")
        print(json.dumps(event, indent=2))
        print()

    # Create mock context
    context = MockContext()

    if args.verbose:
        print("Context:")
        print(f"  Request ID: {context.request_id}")
        print(f"  Function Name: {context.function_name}")
        print()

    # Run the Lambda handler
    print_progress("Starting access review...")

    try:
        start_time = time.time()
        result = lambda_handler(event, context)
        elapsed_time = time.time() - start_time

        print_progress(f"Access review completed in {elapsed_time:.2f} seconds")

        # Print results
        print_result(result, verbose=args.verbose)

        # Check for errors in the response
        status_code = result.get("statusCode", 500)
        if status_code != 200:
            print(f"Warning: Lambda returned non-200 status code: {status_code}")
            return 1

        return 0

    except KeyboardInterrupt:
        print()
        print_progress("Access review interrupted by user")
        return 130

    except Exception as e:
        print_progress(f"Access review failed: {str(e)}")
        handle_error(e, verbose=args.verbose)
        return 1


if __name__ == "__main__":
    sys.exit(main())
