#!/bin/bash
# Convenience script to run tests in Docker container

# Exit on error
set -e

# Check if OPENROUTER_API_KEY is set
if [ -z "$OPENROUTER_API_KEY" ]; then
    echo "Warning: OPENROUTER_API_KEY is not set. Remote API tests will be skipped."
    echo "To run all tests, set the environment variable:"
    echo "  export OPENROUTER_API_KEY=your_api_key"
    echo ""
fi

echo "🐳 Building Docker image for tests..."
docker-compose build test

echo ""
echo "🧪 Running tests in Docker container..."
docker-compose run --rm test

echo ""
echo "✅ Tests completed! Check the results above."
echo ""
echo "📊 Coverage report available at: ./htmlcov/index.html"
echo "📄 JUnit XML report available at: ./test-results/junit.xml"
