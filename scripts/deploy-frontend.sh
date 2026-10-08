#!/usr/bin/env bash
# Builds the React app and publishes it to the EC2 web server. Run after `terraform apply`.
set -euo pipefail
export MSYS_NO_PATHCONV=1   # stops Git Bash on Windows from rewriting /paths in arguments
cd "$(dirname "$0")/.."
TF="terraform -chdir=infra"

API_URL="$($TF output -raw api_url)"
BUCKET="$($TF output -raw frontend_bucket)"
INSTANCE="$($TF output -raw web_instance_id)"
SITE="$($TF output -raw frontend_url)"
REGION="$($TF output -raw region)"

echo "VITE_API_URL=$API_URL" > frontend/.env.production

echo "Building the frontend..."
(cd frontend && npm install --no-audit --no-fund && npm run build)

echo "Uploading to S3..."
aws s3 sync frontend/dist "s3://$BUCKET" --region "$REGION" --delete

echo "Waiting for the web server to be ready (the first time this can take a few minutes)..."
for i in $(seq 1 40); do
  STATUS="$(aws ssm describe-instance-information --region "$REGION" \
    --filters "Key=InstanceIds,Values=$INSTANCE" \
    --query 'InstanceInformationList[0].PingStatus' --output text 2>/dev/null || true)"
  [ "$STATUS" = "Online" ] && break
  sleep 10
done
[ "$STATUS" = "Online" ] || { echo "The server did not become ready. See Troubleshooting in the README."; exit 1; }

echo "Copying files onto the server..."
CMD_ID="$(aws ssm send-command --region "$REGION" --instance-ids "$INSTANCE" \
  --document-name AWS-RunShellScript \
  --parameters "commands=\"cloud-init status --wait || true\",\"aws s3 sync s3://$BUCKET /var/www/app --delete --region $REGION\",\"chown -R nginx:nginx /var/www/app\",\"systemctl reload nginx\"" \
  --query Command.CommandId --output text)"
aws ssm wait command-executed --region "$REGION" --command-id "$CMD_ID" --instance-id "$INSTANCE"

echo
echo "Done. Open your app: $SITE"
echo "Teacher sign-up code: $($TF output -raw teacher_signup_code)"
