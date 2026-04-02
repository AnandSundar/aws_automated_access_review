#!/bin/bash
# run_report.sh - Invokes the Lambda manually and tails logs

set -e

# Default values
STACK_NAME="aws-access-review"
REGION="us-east-1"
PROFILE=""

# Display help message
show_help() {
    cat << EOF
Usage: $0 [OPTIONS] [STACK_NAME] [REGION]

Invokes the Lambda function and displays the response and recent logs.

Arguments:
  STACK_NAME    CloudFormation stack name (default: aws-access-review)
  REGION        AWS region (default: us-east-1)

Options:
  --stack-name <name>    CloudFormation stack name (default: aws-access-review)
  --region <region>      AWS region (default: us-east-1)
  --profile <name>       AWS profile (optional)
  --list-profiles        List available AWS profiles
  --help                 Display this help message

Examples:
  $0 aws-access-review us-east-1
  $0 --stack-name aws-access-review --region us-east-1
  $0 --profile my-profile
  $0 aws-access-review us-east-1 --profile my-profile
EOF
}

# Parse arguments
POSITIONAL_ARGS=()
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --help)
            show_help
            exit 0
            ;;
        --stack-name)
            STACK_NAME="$2"
            shift 2
            ;;
        --region)
            REGION="$2"
            shift 2
            ;;
        --profile)
            PROFILE="$2"
            shift 2
            ;;
        --list-profiles)
            echo "Available AWS profiles:"
            if ! command -v aws &> /dev/null; then
                echo "Error: AWS CLI is not installed or not in PATH"
                exit 1
            fi
            PROFILES=$(aws configure list-profiles 2>&1)
            if [ $? -eq 0 ]; then
                if [ -z "$PROFILES" ]; then
                    echo "No AWS profiles configured."
                else
                    echo "$PROFILES"
                fi
            else
                echo "Error: Failed to list AWS profiles"
                echo "$PROFILES"
                exit 1
            fi
            exit 0
            ;;
        -*)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
        *)
            POSITIONAL_ARGS+=("$1")
            shift
            ;;
    esac
done

# Process positional arguments
if [ ${#POSITIONAL_ARGS[@]} -gt 0 ]; then
    STACK_NAME="${POSITIONAL_ARGS[0]}"
fi
if [ ${#POSITIONAL_ARGS[@]} -gt 1 ]; then
    REGION="${POSITIONAL_ARGS[1]}"
fi
if [ ${#POSITIONAL_ARGS[@]} -gt 2 ]; then
    echo "Warning: Extra positional arguments ignored"
fi

# Build AWS CLI arguments
AWS_ARGS=()
if [ -n "$PROFILE" ]; then
    AWS_ARGS+=(--profile "$PROFILE")
fi

echo "--- Finding Lambda Function ---"
FUNCTION_NAME=$(aws cloudformation describe-stack-resource --stack-name "$STACK_NAME" --logical-resource-id AccessReviewFunction --query 'StackResourceDetail.PhysicalResourceId' --output text "${AWS_ARGS[@]}")

echo "--- Invoking Lambda: $FUNCTION_NAME ---"
# Suppress stdout output (StatusCode) to avoid duplicate response display
aws lambda invoke \
    --function-name "$FUNCTION_NAME" \
    --region "$REGION" \
    "${AWS_ARGS[@]}" \
    response.json > /dev/null

echo "--- Response ---"
# Try to use Python's json.tool for pretty printing, fall back to raw JSON
if command -v python &> /dev/null; then
    python -m json.tool response.json
elif command -v python3 &> /dev/null; then
    python3 -m json.tool response.json
else
    cat response.json
fi

echo "--- Recent Logs ---"
# Build the logs filter command with proper argument handling
# Use MSYS_NO_PATHCONV=1 to prevent Git Bash from converting Unix paths to Windows paths
LOGS_CMD="aws logs filter-log-events --log-group-name /aws/lambda/$FUNCTION_NAME --region $REGION --limit 20"
if [ -n "$PROFILE" ]; then
    LOGS_CMD="$LOGS_CMD --profile $PROFILE"
fi
MSYS_NO_PATHCONV=1 $LOGS_CMD --query 'events[*].[timestamp,message]' --output table
