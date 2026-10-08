#!/usr/bin/env bash
# Creates (once) a private S3 bucket that stores Terraform's state, then initialises Terraform with it.
# Safe to run again. Needed so your computer and GitHub Actions share the same state.
set -euo pipefail
cd "$(dirname "$0")/.."

ACCOUNT="$(aws sts get-caller-identity --query Account --output text)"
REGION="${STATE_REGION:-ap-south-1}"
BUCKET="attendance-tfstate-${ACCOUNT}"

if ! aws s3api head-bucket --bucket "$BUCKET" 2>/dev/null; then
  echo "Creating state bucket $BUCKET in $REGION..."
  if [ "$REGION" = "us-east-1" ]; then
    aws s3api create-bucket --bucket "$BUCKET" --region "$REGION" >/dev/null
  else
    aws s3api create-bucket --bucket "$BUCKET" --region "$REGION" \
      --create-bucket-configuration "LocationConstraint=$REGION" >/dev/null
  fi
  aws s3api put-bucket-versioning --bucket "$BUCKET" --versioning-configuration Status=Enabled
  aws s3api put-bucket-encryption --bucket "$BUCKET" --server-side-encryption-configuration \
    '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'
  aws s3api put-public-access-block --bucket "$BUCKET" --public-access-block-configuration \
    BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
fi

terraform -chdir=infra init -input=false -migrate-state -force-copy \
  -backend-config="bucket=$BUCKET" -backend-config="region=$REGION"
