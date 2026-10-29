#!/usr/bin/env bash
# Empaqueta el código y sus dependencias para Lambda (Python 3.12, arm64) en dist/lambda.zip.
# Uso: ./scripts/build_lambda.sh
set -euo pipefail
cd "$(dirname "$0")/.."
BUILD="${BUILD_DIR:-build/lambda}"
rm -rf "$BUILD" && mkdir -p "$BUILD" dist
uv export --no-dev --no-hashes --no-emit-project --format requirements-txt > build/requirements.txt
uv pip install -r build/requirements.txt --target "$BUILD" \
  --python-platform aarch64-manylinux_2_28 --python-version 3.12 --only-binary :all: --quiet
# boto3/botocore ya vienen en el runtime de Lambda
rm -rf "$BUILD"/boto3* "$BUILD"/botocore* "$BUILD"/s3transfer*
cp -r mp_core mcp_server aws_lambda web config run.sh "$BUILD"/
find "$BUILD" -name "__pycache__" -type d -prune -exec rm -rf {} +
rm -f dist/lambda.zip
(cd "$BUILD" && zip -qr9 ../../dist/lambda.zip .)
echo "dist/lambda.zip: $(du -h dist/lambda.zip | cut -f1) comprimido, $(du -sh "$BUILD" | cut -f1) descomprimido"
