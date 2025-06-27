#!/bin/bash
# Run tests in Docker and summarize results

echo "🐳 Running EnChANT Book Manager tests in Docker container..."
echo "=========================================================="
echo ""

# Ensure directories exist
mkdir -p htmlcov test-results

# Run the tests
docker run --rm \
  -e OPENROUTER_API_KEY=${OPENROUTER_API_KEY:-test_key} \
  -e SKIP_LOCAL_MODE_TESTS=true \
  -v $(pwd)/htmlcov:/app/htmlcov \
  -v $(pwd)/test-results:/app/test-results \
  enchant_book_manager-test:latest \
  uv run pytest tests -c .github/pytest.ini \
    --cov=src/enchant_book_manager \
    --cov-report=term \
    --cov-report=html \
    --cov-report=xml:test-results/coverage.xml \
    --junit-xml=test-results/junit.xml \
    -v \
    --tb=short

# Check exit code
EXIT_CODE=$?

echo ""
echo "=========================================================="
if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ All tests passed successfully!"
else
    echo "❌ Some tests failed. Exit code: $EXIT_CODE"
fi

echo ""
echo "📊 Test results:"
echo "  - Coverage HTML report: ./htmlcov/index.html"
echo "  - JUnit XML report: ./test-results/junit.xml"
echo "  - Coverage XML report: ./test-results/coverage.xml"

exit $EXIT_CODE
