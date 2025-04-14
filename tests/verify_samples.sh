#!/usr/bin/env bash
set -euo pipefail

echo "🔍 Verifying test samples..."

# Check sample file exists
if [ ! -f tests/samples/test_sample.txt ]; then
  echo "❌ Error: Test sample file missing!"
  exit 1
fi

# Check sample file content
content=$(cat tests/samples/test_sample.txt)
if [[ ! "$content" =~ "测试内容" ]]; then
  echo "❌ Error: Test sample content invalid!"
  exit 1
fi

echo "✅ Test samples verified successfully"
