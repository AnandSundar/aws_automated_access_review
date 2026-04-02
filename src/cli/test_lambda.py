#!/usr/bin/env python3
"""
Lambda function tester for AWS Automated Access Review.

This CLI tool allows you to test the Lambda function locally by:
- Loading test events from JSON files
- Using default test events
- Simulating Lambda context
- Displaying results in a readable format
- Providing timing information

Usage:
    python -m cli.test_lambda --event test_event.json
    python -m cli.test_lambda --dry-run --format xlsx
    python -m cli.test_lambda --verbose
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
    """Mock Lambda context object for local testing."""

    def __init__(self, request_id=None):
        self.request_id = request_id or f"test-{int(time.time())}"
        self.function_name = "aws-automated-access-review-test"
        self.function_version = "$LATEST"
        self.invoked_function_arn = "arn:aws:lambda:us-east-1:123456789012:function:test"
        self.memory_limit_in_mb = 256
        self.remaining_time_in_millis = 300000

    def get_remaining_time_in_millis(self):
        return self.remaining_time_in_millis


# Default test events
DEFAULT_EVENTS = {
    "dry_run_csv": {
        "dry_run": True,
        "format": "csv",
    },
    "dry_run_xlsx": {
        "dry_run": True,
        "format": "xlsx",
    },
    "production_csv": {
        "dry_run": False,
        "format": "csv",
    },
    "production_xlsx": {
        "dry_run": False,
        "format": "xlsx",
    },
}


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
        description="Test AWS Automated Access Review Lambda function locally",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test with default dry-run event
  python -m cli.test_lambda --dry-run

  # Test with default dry-run event and XLSX format
  python -m cli.test_lambda --dry-run --format xlsx

  # Test with custom event file
  python -m cli.test_lambda --event my_test_event.json

  # Test with specific AWS profile
  python -m cli.test_lambda --dry-run --profile my-aws-profile

  # Test with verbose output
  python -m cli.test_lambda --dry-run --verbose

  # List available default events
  python -m cli.test_lambda --list-events

  # List available AWS profiles
  python -m cli.test_lambda --list-profiles
        """,
    )

    parser.add_argument(
        "--event",
        type=str,
        default=None,
        help="Path to JSON file containing test event",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Use default dry-run event (overrides --event)",
    )

    parser.add_argument(
        "--format",
        choices=["csv", "xlsx"],
        default="csv",
        help="Report format for default events (default: csv)",
    )

    parser.add_argument(
        "--profile",
        type=str,
        default=None,
        help="AWS profile to use (default: default profile)",
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output",
    )

    parser.add_argument(
        "--list-events",
        action="store_true",
        help="List available default test events and exit",
    )

    parser.add_argument(
        "--list-profiles",
        action="store_true",
        help="List all available AWS profiles and exit",
    )

    parser.add_argument(
        "--request-id",
        type=str,
        default=None,
        help="Custom request ID for the Lambda context",
    )

    return parser.parse_args()


def list_default_events():
    """List available default test events."""
    print()
    print("Available Default Test Events:")
    print("=" * 70)
    for name, event in DEFAULT_EVENTS.items():
        print(f"\n{name}:")
        print(json.dumps(event, indent=2))
    print()


def load_event_from_file(file_path):
    """Load test event from JSON file."""
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Event file not found: {file_path}")

    if not path.is_file():
        raise ValueError(f"Path is not a file: {file_path}")

    try:
        with open(path, "r", encoding="utf-8") as f:
            event = json.load(f)
        return event
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in event file: {e}")


def get_event(args):
    """Get test event based on arguments."""
    # List events and exit if requested
    if args.list_events:
        list_default_events()
        sys.exit(0)

    # Use dry-run event if specified
    if args.dry_run:
        event_key = f"dry_run_{args.format}"
        return DEFAULT_EVENTS[event_key].copy()

    # Load from file if specified
    if args.event:
        return load_event_from_file(args.event)

    # Default to dry-run CSV event
    return DEFAULT_EVENTS["dry_run_csv"].copy()


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

    if args.verbose:
        print(f"AWS Configuration:")
        if args.profile:
            print(f"  Profile: {args.profile}")
        else:
            print(f"  Profile: default")
        print()


def print_progress(message):
    """Print progress message."""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")


def print_event(event, verbose=False):
    """Print the test event."""
    print()
    print("=" * 70)
    print("TEST EVENT")
    print("=" * 70)
    print(json.dumps(event, indent=2))
    print()


def print_context(context, verbose=False):
    """Print the Lambda context."""
    if verbose:
        print()
        print("=" * 70)
        print("LAMBDA CONTEXT")
        print("=" * 70)
        print(f"Request ID: {context.request_id}")
        print(f"Function Name: {context.function_name}")
        print(f"Function Version: {context.function_version}")
        print(f"Invoked Function ARN: {context.invoked_function_arn}")
        print(f"Memory Limit: {context.memory_limit_in_mb} MB")
        print(f"Remaining Time: {context.get_remaining_time_in_millis()} ms")
        print()


def print_result(result, elapsed_time, verbose=False):
    """Print Lambda handler result in a readable format."""
    print()
    print("=" * 70)
    print("LAMBDA FUNCTION RESULT")
    print("=" * 70)

    # Print timing information
    print(f"Execution Time: {elapsed_time:.3f} seconds")
    print()

    # Print status code
    status_code = result.get("statusCode", "N/A")
    status_emoji = "✅" if status_code == 200 else "❌"
    print(f"{status_emoji} Status Code: {status_code}")
    print()

    # Print body
    body = result.get("body", {})

    # Print mode
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

    # Print source if available
    if "source" in body:
        print(f"Source: {body['source']}")
        print()

    # Print description if available
    if "description" in body:
        print(f"Description: {body['description']}")
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
    if report_path or report_url:
        print("Report Information:")
        if report_path:
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
        # Print narrative with indentation
        for line in narrative.split("\n"):
            print(f"  {line}")
        print()

    # Print full response in verbose mode
    if verbose:
        print("=" * 70)
        print("FULL RESPONSE")
        print("=" * 70)
        print(json.dumps(result, indent=2))
        print()


def handle_error(error, verbose=False):
    """Handle and display errors gracefully."""
    print()
    print("=" * 70)
    print("ERROR OCCURRED")
    print("=" * 70)
    print(f"Error Type: {type(error).__name__}")
    print(f"Error Message: {str(error)}")
    print()

    if verbose:
        import traceback

        print("=" * 70)
        print("TRACEBACK")
        print("=" * 70)
        traceback.print_exc()
        print()


def validate_result(result):
    """Validate the Lambda function result."""
    errors = []

    if not isinstance(result, dict):
        errors.append("Result is not a dictionary")
        return errors

    if "statusCode" not in result:
        errors.append("Missing 'statusCode' in result")

    if "body" not in result:
        errors.append("Missing 'body' in result")

    body = result.get("body", {})
    if not isinstance(body, dict):
        errors.append("'body' is not a dictionary")

    return errors


def main():
    """Main entry point for the Lambda tester."""
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
    print("AWS AUTOMATED ACCESS REVIEW - LAMBDA TESTER")
    print("=" * 70)
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

    # Get test event
    try:
        event = get_event(args)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error loading event: {e}")
        return 1

    # Create mock context
    context = MockContext(request_id=args.request_id)

    # Print test configuration
    print("Test Configuration:")
    print(f"  Event Source: {'File' if args.event else 'Default'}")
    if args.event:
        print(f"  Event File: {args.event}")
    else:
        print(f"  Event Type: {'Dry Run' if args.dry_run else 'Default'}")
    print(f"  Request ID: {context.request_id}")
    if args.profile:
        print(f"  AWS Profile: {args.profile}")
    print(f"  Verbose: {args.verbose}")
    print()

    # Print event
    print_event(event, verbose=args.verbose)

    # Print context
    print_context(context, verbose=args.verbose)

    # Run the Lambda handler
    print_progress("Invoking Lambda function...")

    try:
        start_time = time.time()
        result = lambda_handler(event, context)
        elapsed_time = time.time() - start_time

        print_progress(f"Lambda function executed in {elapsed_time:.3f} seconds")

        # Validate result
        validation_errors = validate_result(result)
        if validation_errors:
            print_progress(f"Warning: Result validation failed: {validation_errors}")

        # Print results
        print_result(result, elapsed_time, verbose=args.verbose)

        # Check for errors in the response
        status_code = result.get("statusCode", 500)
        if status_code != 200:
            print(f"Warning: Lambda returned non-200 status code: {status_code}")
            return 1

        return 0

    except KeyboardInterrupt:
        print()
        print_progress("Test interrupted by user")
        return 130

    except Exception as e:
        print_progress(f"Lambda function failed: {str(e)}")
        handle_error(e, verbose=args.verbose)
        return 1


if __name__ == "__main__":
    sys.exit(main())
