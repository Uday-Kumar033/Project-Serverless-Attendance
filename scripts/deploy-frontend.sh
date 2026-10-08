#!/usr/bin/env bash
# Builds the React app and publishes it to S3 + CloudFront. Run after `terraform apply`.
set -euo pipefail
cd "$(dirname "$0")/.."
TF="terraform -chdir=infra"

API_URL="$($TF output -raw api_url)"
BUCKET="$($TF output -raw frontend_bucket)"
DIST="$($TF output -raw cloudfront_distribution_id)"
SITE="$($TF output -raw frontend_url)"
REGION="$($TF output -raw region)"

echo "VITE_API_URL=$API_URL" > frontend/.env.production

echo "Building the frontend..."
(cd frontend && npm install --no-audit --no-fund && npm run build)

echo "Uploading to S3..."
aws s3 sync frontend/dist "s3://$BUCKET" --region "$REGION" --delete --exclude index.html \
  --cache-control "public,max-age=31536000,immutable"
aws s3 cp frontend/dist/index.html "s3://$BUCKET/index.html" --region "$REGION" \
  --cache-control "no-cache" --content-type "text/html"

echo "Refreshing CloudFront..."
aws cloudfront create-invalidation --distribution-id "$DIST" --paths "/*" >/dev/null

echo
echo "Done. Open your app: $SITE"
echo "Teacher sign-up code: $($TF output -raw teacher_signup_code)"
