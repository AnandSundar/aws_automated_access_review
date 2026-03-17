#!/bin/bash
# check_aws_creds.sh - Validates AWS environment for the tool

echo "--- Checking AWS Credentials ---"
if aws sts get-caller-identity > /dev/null 2>&1; then
    echo "[PASS] AWS Credentials are active"
else
    echo "[FAIL] AWS Credentials not found or expired"
    exit 1
fi

echo "--- Checking Security Hub ---"
if aws securityhub get-enabled-standards > /dev/null 2>&1; then
    echo "[PASS] Security Hub is enabled"
else
    echo "[FAIL] Security Hub is NOT enabled"
fi

echo "--- Checking IAM Access Analyzer ---"
if [ $(aws accessanalyzer list-analyzers --query 'analyzers' --output text | wc -l) -gt 0 ]; then
    echo "[PASS] IAM Access Analyzer exists"
else
    echo "[FAIL] No IAM Access Analyzer found"
fi

echo "--- Checking SES Verified Identities ---"
if [ $(aws ses list-verified-email-addresses --query 'VerifiedEmailAddresses' --output text | wc -w) -gt 0 ]; then
    echo "[PASS] SES has verified identities"
else
    echo "[FAIL] No SES verified identities found"
fi
