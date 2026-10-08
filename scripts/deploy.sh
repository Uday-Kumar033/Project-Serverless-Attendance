#!/usr/bin/env bash
# One command to deploy everything: backend + database + CloudFront + frontend.
# Extra arguments go to `terraform apply`, e.g.  bash scripts/deploy.sh -var otp_delivery=log
set -euo pipefail
cd "$(dirname "$0")/.."

for tool in terraform aws node npm; do
  command -v "$tool" >/dev/null || { echo "Missing tool: $tool (see README, Prerequisites)"; exit 1; }
done
aws sts get-caller-identity >/dev/null || { echo "AWS is not configured. Run: aws configure"; exit 1; }

bash scripts/build.sh
terraform -chdir=infra init -input=false
terraform -chdir=infra apply "$@"
bash scripts/deploy-frontend.sh
