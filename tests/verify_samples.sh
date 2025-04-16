#!/usr/bin/env bash
set -euo pipefail

echo "🔍 Verifying test samples..."

# Check original sample file exists
if [ ! -f tests/samples/test_sample.txt ]; then
  echo "❌ Error: Original test sample file missing!"
  exit 1
fi

# Check original sample file content
content=$(cat tests/samples/test_sample.txt)
if [[ ! "$content" =~ "测试内容" ]]; then
  echo "❌ Error: Original test sample content invalid!"
  exit 1
fi

# For wheel verification, check if the file was included in wheel
if [ -d "dist" ]; then
  # Check if wheel exists
  WHEEL_FILE=$(find dist -name "*.whl" 2>/dev/null | head -1)
  if [ -n "$WHEEL_FILE" ]; then
    echo "ℹ️ Checking wheel file: $WHEEL_FILE"
    
    # Try using unzip to check contents of wheel - look for ANY test_sample.txt
    if unzip -l "$WHEEL_FILE" | grep -q 'test_sample.txt'; then
      echo "✅ Test sample file found in wheel package at locations:"
      unzip -l "$WHEEL_FILE" | grep 'test_sample.txt'
    else
      echo "⚠️ Test sample file missing from wheel package."
      echo "⚠️ Check MANIFEST.in and include_package_data in setup.py/pyproject.toml."
    fi
  else
    echo "⚠️ No wheel file found to verify."
  fi
  
  # Check if sdist exists
  SDIST_FILE=$(find dist -name "*.tar.gz" 2>/dev/null | head -1)
  if [ -n "$SDIST_FILE" ]; then
    echo "ℹ️ Checking sdist file: $SDIST_FILE"
    
    # Try using tar to check contents
    if tar -ztf "$SDIST_FILE" | grep -q 'tests/samples/test_sample.txt'; then
      echo "✅ Test sample file found in sdist package."
    else
      echo "⚠️ Test sample file missing from sdist package."
      echo "⚠️ Check MANIFEST.in."
    fi
  else
    echo "⚠️ No sdist file found to verify."
  fi
fi

echo "✅ Test samples verification completed"
