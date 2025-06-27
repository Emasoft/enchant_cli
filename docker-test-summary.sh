#!/bin/bash
# Run tests and show a nice summary

echo "🐳 EnChANT Book Manager - Docker Test Suite"
echo "==========================================="
echo ""

# Function to format test results
format_results() {
    local passed=$(grep -o "[0-9]* passed" | head -1 | cut -d' ' -f1)
    local failed=$(grep -o "[0-9]* failed" | head -1 | cut -d' ' -f1)
    local skipped=$(grep -o "[0-9]* skipped" | head -1 | cut -d' ' -f1)
    local errors=$(grep -o "[0-9]* error" | head -1 | cut -d' ' -f1)

    echo ""
    echo "📊 Test Results Summary:"
    echo "========================"
    [ -n "$passed" ] && echo "✅ Passed:  $passed"
    [ -n "$failed" ] && echo "❌ Failed:  $failed"
    [ -n "$skipped" ] && echo "⏭️  Skipped: $skipped"
    [ -n "$errors" ] && echo "🚨 Errors:  $errors"
}

# Run tests
echo "Running tests (this may take a few minutes)..."
echo ""

docker run --rm -t \
  -e OPENROUTER_API_KEY=${OPENROUTER_API_KEY:-test_key} \
  -e SKIP_LOCAL_MODE_TESTS=true \
  -v $(pwd)/htmlcov:/app/htmlcov \
  -v $(pwd)/test-results:/app/test-results \
  enchant_book_manager-test:latest \
  uv run pytest tests -c .github/pytest.ini \
    --tb=short \
    -q | tee /tmp/docker-test-output.log

# Format and display results
cat /tmp/docker-test-output.log | format_results

echo ""
echo "📁 Output Files:"
echo "================"
echo "📊 Coverage HTML: ./htmlcov/index.html"
echo "📄 JUnit XML: ./test-results/junit.xml"
echo "📈 Coverage XML: ./test-results/coverage.xml"

# Check if htmlcov was generated
if [ -f "./htmlcov/index.html" ]; then
    echo ""
    echo "✅ Coverage report generated successfully!"
fi
