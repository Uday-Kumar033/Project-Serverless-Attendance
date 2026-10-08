#!/usr/bin/env bash
# Packages the Lambda code + dependencies into build/package (Terraform zips it).
set -euo pipefail
cd "$(dirname "$0")/.."
PY="$(command -v python3 || command -v python || true)"
[ -n "$PY" ] || { echo "Python is not installed (need 3.9+)."; exit 1; }
rm -rf build/package && mkdir -p build/package
cp -r backend/common backend/functions build/package/
"$PY" -m pip install -r backend/requirements.txt -t build/package \
  --platform manylinux2014_x86_64 --only-binary=:all: --python-version 3.12 --upgrade -q
echo "Built build/package"
