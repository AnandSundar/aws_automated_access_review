#!/bin/bash
# deploy.sh - Packages and deploys the AWS Automated Access Review

set -e

# Default values
STACK_NAME="aws-access-review"
REGION="us-east-1"
EMAIL=""

# Parse arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --email) EMAIL="$2"; shift ;;
        --stack-name) STACK_NAME="$2"; shift ;;
        --region) REGION="$2"; shift ;;
        *) echo "Unknown parameter: $1"; exit 1 ;;
    esac
    shift
done

if [ -z "$EMAIL" ]; then
    echo "Error: --email is required"
    exit 1
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
    --parameter-overrides RecipientEmail="$EMAIL" \
    --capabilities CAPABILITY_IAM

echo "--- Updating Lambda Code ---"
aws lambda update-function-code \
    --function-name $(aws cloudformation describe-stack-resource --stack-name "$STACK_NAME" --logical-id AccessReviewFunction --query 'StackResourceDetail.PhysicalResourceId' --output text) \
    --zip-file fileb://lambda.zip \
    --region "$REGION"

echo "--- Deployment Complete ---"
aws cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$REGION" --query 'Stacks[0].Outputs'
