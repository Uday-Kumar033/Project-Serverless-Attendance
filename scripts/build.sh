#!/usr/bin/env bash
# Packages the Lambda code + dependencies into build/package (Terraform zips it).
set -euo pipefail
cd "$(dirname "$0")/.."
rm -rf build/package && mkdir -p build/package
cp -r backend/common backend/functions build/package/
pip install -r backend/requirements.txt -t build/package \
  --platform manylinux2014_x86_64 --only-binary=:all: --python-version 3.12 --upgrade -q
echo "Built build/package"
