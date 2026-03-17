#!/bin/bash
# run_report.sh - Invokes the Lambda manually and tails logs

STACK_NAME=${1:-"aws-access-review"}
REGION=${2:-"us-east-1"}

echo "--- Finding Lambda Function ---"
FUNCTION_NAME=$(aws cloudformation describe-stack-resource --stack-name "$STACK_NAME" --logical-id AccessReviewFunction --query 'StackResourceDetail.PhysicalResourceId' --output text)

echo "--- Invoking Lambda: $FUNCTION_NAME ---"
aws lambda invoke \
    --function-name "$FUNCTION_NAME" \
    --region "$REGION" \
    response.json

echo "--- Response ---"
cat response.json | jq .

echo "--- Recent Logs ---"
aws logs tail "/aws/lambda/$FUNCTION_NAME" --region "$REGION" --limit 20
