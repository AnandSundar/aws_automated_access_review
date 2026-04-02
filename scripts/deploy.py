#!/usr/bin/env python3
"""
deploy.py - Cross-platform deployment script for AWS Automated Access Review

This script packages and deploys the Lambda function to AWS using CloudFormation.
It works on Windows, Linux, and macOS without requiring external zip commands.

Usage:
    python scripts/deploy.py --email <address> [options]

Options:
    --profile <name>       AWS profile to use
    --email <address>      Recipient email for reports (required)
    --stack-name <name>    CloudFormation stack name (default: aws-access-review)
    --template <path>      CloudFormation template path (default: templates/access-review.yaml)
    --region <region>      AWS region (default: us-east-1)
    --list-profiles        List available AWS profiles
    --help                 Display this help message
"""

import argparse
import os
import sys
import zipfile
import shutil
from pathlib import Path
from typing import Optional

try:
    import boto3
    from botocore.exceptions import ClientError, BotoCoreError
except ImportError:
    print("Error: boto3 is required. Install it with: pip install boto3")
    sys.exit(1)


class DeploymentError(Exception):
    """Custom exception for deployment errors."""

    pass


class Deployer:
    """Handles the deployment of the AWS Automated Access Review."""

    def __init__(
        self,
        profile: Optional[str] = None,
        email: Optional[str] = None,
        stack_name: str = "aws-access-review",
        template_path: str = "templates/access-review.yaml",
        region: str = "us-east-1",
    ):
        self.profile = profile
        self.email = email
        self.stack_name = stack_name
        self.template_path = template_path
        self.region = region
        self.session = self._create_session()
        self.cf_client = self.session.client("cloudformation", region_name=region)
        self.lambda_client = self.session.client("lambda", region_name=region)

        # Paths
        self.project_root = Path(__file__).parent.parent
        self.lambda_source_dir = self.project_root / "src" / "lambda"
        self.lambda_zip_path = self.project_root / "lambda.zip"
        self.template_file_path = self.project_root / template_path

    def _create_session(self) -> boto3.Session:
        """Create a boto3 session with optional profile."""
        if self.profile:
            return boto3.Session(profile_name=self.profile)
        return boto3.Session()

    @staticmethod
    def list_profiles() -> None:
        """List available AWS profiles."""
        try:
            profiles = boto3.Session().available_profiles
            if not profiles:
                print("No AWS profiles configured.")
            else:
                print("Available AWS profiles:")
                for profile in profiles:
                    print(f"  - {profile}")
        except Exception as e:
            print(f"Error listing AWS profiles: {e}")
            sys.exit(1)

    def validate_email(self) -> None:
        """Validate that email is provided."""
        if not self.email:
            raise DeploymentError("--email is required")

        # Basic email validation
        if "@" not in self.email or "." not in self.email.split("@")[-1]:
            raise DeploymentError(f"Invalid email address: {self.email}")

    def validate_template(self) -> None:
        """Validate that the template file exists."""
        if not self.template_file_path.exists():
            raise DeploymentError(
                f"Template file not found: {self.template_file_path}\n"
                f"Current working directory: {os.getcwd()}"
            )

    def validate_lambda_source(self) -> None:
        """Validate that the Lambda source directory exists."""
        if not self.lambda_source_dir.exists():
            raise DeploymentError(
                f"Lambda source directory not found: {self.lambda_source_dir}\n"
                f"Current working directory: {os.getcwd()}"
            )

    def create_lambda_zip(self) -> None:
        """Create a zip file of the Lambda code using Python's zipfile module."""
        print("--- Packaging Lambda ---")

        # Validate source directory
        self.validate_lambda_source()

        # Remove existing zip file if it exists
        if self.lambda_zip_path.exists():
            self.lambda_zip_path.unlink()

        # Create zip file
        with zipfile.ZipFile(self.lambda_zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(self.lambda_source_dir):
                # Skip __pycache__ directories
                dirs[:] = [d for d in dirs if d != "__pycache__"]

                for file in files:
                    # Skip .pyc files and other compiled files
                    if file.endswith(".pyc") or file.endswith(".pyo") or file.endswith(".pyd"):
                        continue

                    file_path = Path(root) / file
                    # Calculate relative path from lambda source directory
                    arcname = file_path.relative_to(self.lambda_source_dir)
                    zipf.write(file_path, arcname)

        # Get file size in MB
        file_size_mb = self.lambda_zip_path.stat().st_size / (1024 * 1024)
        print(f"Created Lambda package: {self.lambda_zip_path} ({file_size_mb:.2f} MB)")

    def deploy_stack(self) -> None:
        """Deploy the CloudFormation stack."""
        print("--- Deploying CloudFormation Stack ---")

        # Read template file
        try:
            with open(self.template_file_path, "r") as f:
                template_body = f.read()
        except Exception as e:
            raise DeploymentError(f"Error reading template file: {e}")

        # Deploy parameters
        params = {
            "StackName": self.stack_name,
            "TemplateBody": template_body,
            "Parameters": [{"ParameterKey": "RecipientEmail", "ParameterValue": self.email}],
            "Capabilities": ["CAPABILITY_IAM"],
        }

        try:
            response = self.cf_client.create_stack(**params)
            print(f"Stack creation initiated: {response['StackId']}")
            self._wait_for_stack_completion()
        except self.cf_client.exceptions.AlreadyExistsException:
            # Stack exists, update it
            print(f"Stack '{self.stack_name}' already exists. Updating...")
            params["UsePreviousTemplate"] = False
            response = self.cf_client.update_stack(**params)
            print(f"Stack update initiated: {response['StackId']}")
            self._wait_for_stack_completion()
        except ClientError as e:
            raise DeploymentError(f"Error deploying stack: {e}")

    def _wait_for_stack_completion(self, timeout: int = 1800) -> None:
        """Wait for stack operation to complete."""
        import time

        waiter = self.cf_client.get_waiter("stack_create_complete")

        try:
            print("Waiting for stack operation to complete...")
            waiter.wait(
                StackName=self.stack_name, WaiterConfig={"Delay": 30, "MaxAttempts": timeout // 30}
            )
            print(f"Stack operation completed successfully: {self.stack_name}")
        except Exception as e:
            # Check for update completion if create failed
            try:
                waiter = self.cf_client.get_waiter("stack_update_complete")
                waiter.wait(
                    StackName=self.stack_name,
                    WaiterConfig={"Delay": 30, "MaxAttempts": timeout // 30},
                )
                print(f"Stack update completed successfully: {self.stack_name}")
            except Exception as e:
                # Get stack events for debugging
                self._print_stack_events()
                raise DeploymentError(f"Stack operation failed: {e}")

    def _print_stack_events(self) -> None:
        """Print recent stack events for debugging."""
        try:
            events = self.cf_client.describe_stack_events(StackName=self.stack_name, MaxResults=10)
            print("\nRecent stack events:")
            for event in events["StackEvents"]:
                status = event.get("ResourceStatus", "UNKNOWN")
                resource_type = event.get("ResourceType", "Unknown")
                logical_id = event.get("LogicalResourceId", "Unknown")
                status_reason = event.get("ResourceStatusReason", "")
                print(f"  {status}: {resource_type} ({logical_id})")
                if status_reason:
                    print(f"    Reason: {status_reason}")
        except Exception as e:
            print(f"Could not retrieve stack events: {e}")

    def update_lambda_code(self) -> None:
        """Update the Lambda function code with the zip file."""
        print("--- Updating Lambda Code ---")

        # Get Lambda function name from CloudFormation
        try:
            response = self.cf_client.describe_stack_resource(
                StackName=self.stack_name, LogicalResourceId="AccessReviewFunction"
            )
            function_name = response["StackResourceDetail"]["PhysicalResourceId"]
            print(f"Found Lambda function: {function_name}")
        except ClientError as e:
            raise DeploymentError(f"Error getting Lambda function name: {e}")

        # Read zip file
        try:
            with open(self.lambda_zip_path, "rb") as f:
                zip_bytes = f.read()
        except Exception as e:
            raise DeploymentError(f"Error reading zip file: {e}")

        # Update Lambda function code
        try:
            response = self.lambda_client.update_function_code(
                FunctionName=function_name, ZipFile=zip_bytes
            )
            print(f"Lambda code updated: {function_name}")
            print(f"  Last modified: {response['LastModified']}")
            print(f"  Code size: {response['CodeSize']} bytes")
        except ClientError as e:
            raise DeploymentError(f"Error updating Lambda code: {e}")

    def display_outputs(self) -> None:
        """Display the CloudFormation stack outputs."""
        print("--- Deployment Complete ---")

        try:
            response = self.cf_client.describe_stacks(StackName=self.stack_name)
            stack = response["Stacks"][0]

            if "Outputs" in stack:
                print("\nStack Outputs:")
                for output in stack["Outputs"]:
                    key = output.get("OutputKey", "Unknown")
                    value = output.get("OutputValue", "N/A")
                    description = output.get("Description", "")
                    print(f"  {key}: {value}")
                    if description:
                        print(f"    ({description})")
            else:
                print("\nNo outputs defined for this stack.")
        except ClientError as e:
            print(f"Warning: Could not retrieve stack outputs: {e}")

    def cleanup(self) -> None:
        """Clean up temporary files."""
        if self.lambda_zip_path.exists():
            self.lambda_zip_path.unlink()
            print(f"Cleaned up: {self.lambda_zip_path}")

    def deploy(self, keep_zip: bool = False) -> None:
        """Execute the full deployment process."""
        try:
            # Validate inputs
            self.validate_email()
            self.validate_template()

            # Package Lambda
            self.create_lambda_zip()

            # Deploy stack
            self.deploy_stack()

            # Update Lambda code
            self.update_lambda_code()

            # Display outputs
            self.display_outputs()

            # Cleanup
            if not keep_zip:
                self.cleanup()

            print("\n✓ Deployment completed successfully!")

        except DeploymentError as e:
            print(f"\n✗ Deployment failed: {e}")
            sys.exit(1)
        except KeyboardInterrupt:
            print("\n\n✗ Deployment cancelled by user")
            sys.exit(1)
        except Exception as e:
            print(f"\n✗ Unexpected error: {e}")
            import traceback

            traceback.print_exc()
            sys.exit(1)


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Deploy AWS Automated Access Review to AWS Lambda",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Deploy with required email parameter
  python scripts/deploy.py --email admin@example.com
  
  # Deploy with custom profile and stack name
  python scripts/deploy.py --email admin@example.com --profile prod --stack-name my-access-review
  
  # Deploy to different region
  python scripts/deploy.py --email admin@example.com --region us-west-2
  
  # Use custom template
  python scripts/deploy.py --email admin@example.com --template templates/access-review-real.yaml
  
  # List available AWS profiles
  python scripts/deploy.py --list-profiles
        """,
    )

    parser.add_argument(
        "--profile", type=str, default=None, help="AWS profile to use (default: default profile)"
    )

    parser.add_argument(
        "--email", type=str, default=None, help="Recipient email for reports (required)"
    )

    parser.add_argument(
        "--stack-name",
        type=str,
        default="aws-access-review",
        help="CloudFormation stack name (default: aws-access-review)",
    )

    parser.add_argument(
        "--template",
        type=str,
        default="templates/access-review.yaml",
        help="CloudFormation template path (default: templates/access-review.yaml)",
    )

    parser.add_argument(
        "--region", type=str, default="us-east-1", help="AWS region (default: us-east-1)"
    )

    parser.add_argument(
        "--list-profiles", action="store_true", help="List available AWS profiles and exit"
    )

    parser.add_argument(
        "--keep-zip",
        action="store_true",
        help="Keep the Lambda zip file after deployment (useful for debugging)",
    )

    return parser.parse_args()


def main() -> None:
    """Main entry point."""
    args = parse_arguments()

    # Handle list-profiles
    if args.list_profiles:
        Deployer.list_profiles()
        return

    # Create deployer and execute deployment
    deployer = Deployer(
        profile=args.profile,
        email=args.email,
        stack_name=args.stack_name,
        template_path=args.template,
        region=args.region,
    )

    deployer.deploy(keep_zip=args.keep_zip)


if __name__ == "__main__":
    main()
