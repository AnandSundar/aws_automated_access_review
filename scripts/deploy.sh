#!/bin/bash
# deploy.sh - Packages and deploys the AWS Automated Access Review

set -e

# Default values
STACK_NAME="aws-access-review"
REGION="us-east-1"
EMAIL=""
PROFILE=""

# Parse arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --email) EMAIL="$2"; shift ;;
        --stack-name) STACK_NAME="$2"; shift ;;
        --region) REGION="$2"; shift ;;
        --profile) PROFILE="$2"; shift ;;
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
        *) echo "Unknown parameter: $1"; exit 1 ;;
    esac
    shift
done

if [ -z "$EMAIL" ]; then
    echo "Error: --email is required"
    exit 1
fi

# Build AWS CLI arguments
AWS_ARGS=""
if [ -n "$PROFILE" ]; then
    AWS_ARGS="--profile $PROFILE"
fi

echo "--- Packaging Lambda ---"
cd src/lambda
zip -r ../../lambda.zip .
cd ../..

echo "--- Deploying CloudFormation Stack ---"
aws cloudformation deploy \
    --template-file templates/access-review.yaml \
    --stack-name "$STACK_NAME" \
    --region "$REGION" \
    $AWS_ARGS \
    --parameter-overrides RecipientEmail="$EMAIL" \
    --capabilities CAPABILITY_IAM

echo "--- Updating Lambda Code ---"
aws lambda update-function-code \
    --function-name $(aws cloudformation describe-stack-resource --stack-name "$STACK_NAME" --logical-id AccessReviewFunction --query 'StackResourceDetail.PhysicalResourceId' --output text $AWS_ARGS) \
    --zip-file fileb://lambda.zip \
    --region "$REGION" \
    $AWS_ARGS

echo "--- Deployment Complete ---"
aws cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$REGION" $AWS_ARGS --query 'Stacks[0].Outputs'
