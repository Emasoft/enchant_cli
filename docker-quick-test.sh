#!/bin/bash
# Quick Docker test runner that skips heavy tests

echo "🐳 Running quick Docker tests (skipping heavy E2E tests)..."
echo "=========================================================="

# Run tests excluding heavy ones
docker run --rm \
  -e OPENROUTER_API_KEY=test_key \
  -e SKIP_LOCAL_MODE_TESTS=true \
  enchant_book_manager-test:latest \
  uv run pytest tests \
    -c .github/pytest.ini \
    --ignore=tests/test_e2e_chinese_to_epub.py \
    --ignore=tests/test_real_integration_final.py \
    --ignore=tests/test_remote_api_integration.py \
    -v \
    --tb=short \
    --durations=10

EXIT_CODE=$?

echo ""
echo "=========================================================="
if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ All quick tests passed!"
else
    echo "❌ Some tests failed. Exit code: $EXIT_CODE"
fi

exit $EXIT_CODE
