#!/bin/bash
# Script to clean up AWS resources and local artifacts
# Deletes CloudFormation stack, S3 buckets, Lambda functions, and local artifacts

set -e  # Exit on error

# Default values
STACK_NAME="aws-access-review"
REGION="us-east-1"
PROFILE=""
EMPTY_BUCKET=false
DELETE_BUCKET=false
CLEAN_LOCAL=false
SHOW_HELP=false

# Display help message
show_help() {
    cat << EOF
Usage: ./scripts/cleanup.sh [options]

Clean up AWS resources and local artifacts for the AWS Automated Access Review tool.

Options:
  --stack-name <name>    CloudFormation stack name (default: aws-access-review)
  --region <region>      AWS region (default: us-east-1)
  --profile <profile>    AWS profile to use (default: default profile)
  --empty-bucket         Empty S3 bucket before deletion
  --delete-bucket        Delete S3 bucket
  --clean-local          Clean local artifacts
  --list-profiles        List available AWS profiles and exit
  --help                 Display this help message

Examples:
  ./scripts/cleanup.sh                          # Show what would be cleaned up
  ./scripts/cleanup.sh --delete-bucket          # Delete S3 bucket
  ./scripts/cleanup.sh --empty-bucket --delete-bucket  # Empty and delete S3 bucket
  ./scripts/cleanup.sh --clean-local            # Clean local artifacts only
  ./scripts/cleanup.sh --delete-bucket --clean-local  # Full cleanup
  ./scripts/cleanup.sh --profile my-profile     # Use specific AWS profile

Note: This script will prompt for confirmation before performing destructive operations.

EOF
}

# Function to prompt for confirmation
confirm() {
    local prompt="$1"
    local response
    
    while true; do
        read -p "$prompt (y/n): " response
        case $response in
            [Yy]*)
                return 0
                ;;
            [Nn]*)
                return 1
                ;;
            *)
                echo "Please answer yes or no."
                ;;
        esac
    done
}

# Function to delete CloudFormation stack
delete_cloudformation_stack() {
    echo "Checking CloudFormation stack: $STACK_NAME"
    
    if aws cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$REGION" $AWS_ARGS &>/dev/null; then
        echo "✓ Stack exists: $STACK_NAME"
        
        if confirm "Do you want to delete the CloudFormation stack '$STACK_NAME'?"; then
            echo "Deleting CloudFormation stack: $STACK_NAME"
            aws cloudformation delete-stack --stack-name "$STACK_NAME" --region "$REGION" $AWS_ARGS
            
            echo "Waiting for stack deletion to complete..."
            aws cloudformation wait stack-delete-complete --stack-name "$STACK_NAME" --region "$REGION" $AWS_ARGS
            
            echo "✓ CloudFormation stack deleted successfully"
        else
            echo "⊙ CloudFormation stack deletion skipped"
        fi
    else
        echo "⊙ CloudFormation stack does not exist: $STACK_NAME"
    fi
}

# Function to empty S3 bucket
empty_s3_bucket() {
    local bucket_name="$1"
    
    echo "Checking S3 bucket: $bucket_name"
    
    if aws s3 ls "s3://$bucket_name" --region "$REGION" $AWS_ARGS &>/dev/null; then
        echo "✓ Bucket exists: $bucket_name"
        
        # Check if bucket is empty
        OBJECT_COUNT=$(aws s3 ls "s3://$bucket_name" --recursive --region "$REGION" $AWS_ARGS | wc -l)
        
        if [ "$OBJECT_COUNT" -eq 0 ]; then
            echo "⊙ Bucket is already empty"
        else
            echo "Bucket contains $OBJECT_COUNT object(s)"
            
            if confirm "Do you want to empty the S3 bucket '$bucket_name'?"; then
                echo "Emptying S3 bucket: $bucket_name"
                aws s3 rm "s3://$bucket_name" --recursive --region "$REGION" $AWS_ARGS
                echo "✓ S3 bucket emptied successfully"
            else
                echo "⊙ S3 bucket emptying skipped"
            fi
        fi
    else
        echo "⊙ S3 bucket does not exist: $bucket_name"
    fi
}

# Function to delete S3 bucket
delete_s3_bucket() {
    local bucket_name="$1"
    
    echo "Checking S3 bucket: $bucket_name"
    
    if aws s3 ls "s3://$bucket_name" --region "$REGION" $AWS_ARGS &>/dev/null; then
        echo "✓ Bucket exists: $bucket_name"
        
        # Check if bucket is empty
        OBJECT_COUNT=$(aws s3 ls "s3://$bucket_name" --recursive --region "$REGION" $AWS_ARGS | wc -l)
        
        if [ "$OBJECT_COUNT" -gt 0 ]; then
            if [ "$EMPTY_BUCKET" = true ]; then
                echo "Emptying bucket before deletion..."
                aws s3 rm "s3://$bucket_name" --recursive --region "$REGION" $AWS_ARGS
            else
                echo "✗ Bucket is not empty. Use --empty-bucket to empty it first."
                return 1
            fi
        fi
        
        if confirm "Do you want to delete the S3 bucket '$bucket_name'?"; then
            echo "Deleting S3 bucket: $bucket_name"
            aws s3 rb "s3://$bucket_name" --region "$REGION" $AWS_ARGS
            echo "✓ S3 bucket deleted successfully"
        else
            echo "⊙ S3 bucket deletion skipped"
        fi
    else
        echo "⊙ S3 bucket does not exist: $bucket_name"
    fi
}

# Function to delete Lambda function
delete_lambda_function() {
    local function_name="$1"
    
    echo "Checking Lambda function: $function_name"
    
    if aws lambda get-function --function-name "$function_name" --region "$REGION" $AWS_ARGS &>/dev/null; then
        echo "✓ Lambda function exists: $function_name"
        
        if confirm "Do you want to delete the Lambda function '$function_name'?"; then
            echo "Deleting Lambda function: $function_name"
            aws lambda delete-function --function-name "$function_name" --region "$REGION" $AWS_ARGS
            echo "✓ Lambda function deleted successfully"
        else
            echo "⊙ Lambda function deletion skipped"
        fi
    else
        echo "⊙ Lambda function does not exist: $function_name"
    fi
}

# Function to clean local artifacts
clean_local_artifacts() {
    echo "Cleaning local artifacts..."
    
    # Clean Python cache
    if [ -d "__pycache__" ]; then
        echo "Removing __pycache__ directories..."
        find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
        echo "✓ Python cache removed"
    else
        echo "⊙ No __pycache__ directories found"
    fi
    
    # Clean .pyc files
    if find . -name "*.pyc" | grep -q .; then
        echo "Removing .pyc files..."
        find . -name "*.pyc" -delete
        echo "✓ .pyc files removed"
    else
        echo "⊙ No .pyc files found"
    fi
    
    # Clean .pytest_cache
    if [ -d ".pytest_cache" ]; then
        echo "Removing .pytest_cache..."
        rm -rf .pytest_cache
        echo "✓ .pytest_cache removed"
    else
        echo "⊙ No .pytest_cache found"
    fi
    
    # Clean coverage reports
    if [ -d "htmlcov" ]; then
        echo "Removing htmlcov..."
        rm -rf htmlcov
        echo "✓ htmlcov removed"
    else
        echo "⊙ No htmlcov found"
    fi
    
    if [ -f ".coverage" ]; then
        echo "Removing .coverage..."
        rm -f .coverage
        echo "✓ .coverage removed"
    else
        echo "⊙ No .coverage found"
    fi
    
    # Clean dist and build directories
    if [ -d "dist" ]; then
        echo "Removing dist..."
        rm -rf dist
        echo "✓ dist removed"
    else
        echo "⊙ No dist found"
    fi
    
    if [ -d "build" ]; then
        echo "Removing build..."
        rm -rf build
        echo "✓ build removed"
    else
        echo "⊙ No build found"
    fi
    
    # Clean .egg-info directories
    if find . -name "*.egg-info" -type d | grep -q .; then
        echo "Removing .egg-info directories..."
        find . -name "*.egg-info" -type d -exec rm -rf {} + 2>/dev/null || true
        echo "✓ .egg-info directories removed"
    else
        echo "⊙ No .egg-info directories found"
    fi
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
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
        --empty-bucket)
            EMPTY_BUCKET=true
            shift
            ;;
        --delete-bucket)
            DELETE_BUCKET=true
            shift
            ;;
        --clean-local)
            CLEAN_LOCAL=true
            shift
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
        --help)
            SHOW_HELP=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Show help if requested
if [ "$SHOW_HELP" = true ]; then
    show_help
    exit 0
fi

# Build AWS CLI arguments
AWS_ARGS=""
if [ -n "$PROFILE" ]; then
    AWS_ARGS="--profile $PROFILE"
fi

# Display cleanup configuration
echo "========================================"
echo "AWS Resource Cleanup"
echo "========================================"
echo "Stack Name: $STACK_NAME"
echo "Region: $REGION"
if [ -n "$PROFILE" ]; then
    echo "Profile: $PROFILE"
fi
echo "Empty S3 Bucket: $EMPTY_BUCKET"
echo "Delete S3 Bucket: $DELETE_BUCKET"
echo "Clean Local Artifacts: $CLEAN_LOCAL"
echo "========================================"
echo ""

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo "Error: AWS CLI is not installed"
    exit 1
fi

# Check if AWS credentials are configured
if ! aws sts get-caller-identity $AWS_ARGS &> /dev/null; then
    echo "Error: AWS credentials are not configured"
    echo "Please configure AWS credentials using 'aws configure' or by setting environment variables"
    exit 1
fi

# Get AWS account ID
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text $AWS_ARGS)
echo "AWS Account ID: $AWS_ACCOUNT_ID"
echo ""

# Perform cleanup operations
echo "Starting cleanup operations..."
echo ""

# Delete CloudFormation stack
delete_cloudformation_stack
echo ""

# Delete S3 bucket if requested
if [ "$DELETE_BUCKET" = true ]; then
    # Try to get bucket name from CloudFormation stack outputs
    BUCKET_NAME=$(aws cloudformation describe-stacks \
        --stack-name "$STACK_NAME" \
        --region "$REGION" \
        $AWS_ARGS \
        --query 'Stacks[0].Outputs[?OutputKey==`ReportsBucketName`].OutputValue' \
        --output text 2>/dev/null || echo "")
    
    if [ -n "$BUCKET_NAME" ] && [ "$BUCKET_NAME" != "None" ]; then
        delete_s3_bucket "$BUCKET_NAME"
    else
        echo "⊙ No S3 bucket found in CloudFormation stack outputs"
    fi
    echo ""
fi

# Clean local artifacts if requested
if [ "$CLEAN_LOCAL" = true ]; then
    clean_local_artifacts
    echo ""
fi

# Display cleanup summary
echo "========================================"
echo "Cleanup Summary"
echo "========================================"
echo "✓ Cleanup operations completed"
echo ""
echo "Note: Some resources may take time to be fully deleted."
echo "You can verify the cleanup by running:"
if [ -n "$PROFILE" ]; then
    echo "  aws cloudformation list-stacks --region $REGION --profile $PROFILE"
    echo "  aws s3 ls --region $REGION --profile $PROFILE"
    echo "  aws lambda list-functions --region $REGION --profile $PROFILE"
else
    echo "  aws cloudformation list-stacks --region $REGION"
    echo "  aws s3 ls --region $REGION"
    echo "  aws lambda list-functions --region $REGION"
fi
echo "========================================"
echo ""
