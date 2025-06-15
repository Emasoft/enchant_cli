#!/bin/bash
# Script to run the Phase 3 chapter parsing test

echo "======================================"
echo "Phase 3 Chapter Parsing Test"
echo "======================================"
echo ""
echo "This test verifies that enchant_cli.py correctly generates"
echo "an EPUB with proper chapter TOC from a full novel file."
echo ""
echo "Requirements:"
echo "- tests/sample_novel/translated_Global High Martial Arts by Eagle Eats Chick (Lǎo yīng chī xiǎo jī).txt"
echo "- tests/sample_novel/chapter_headings.txt"
echo ""

# Check if sample files exist
if [ ! -f "tests/sample_novel/translated_Global High Martial Arts by Eagle Eats Chick (Lǎo yīng chī xiǎo jī).txt" ]; then
    echo "ERROR: Sample novel file not found!"
    echo "Please ensure the test files are in tests/sample_novel/"
    exit 1
fi

if [ ! -f "tests/sample_novel/chapter_headings.txt" ]; then
    echo "ERROR: Chapter headings file not found!"
    echo "Please ensure the test files are in tests/sample_novel/"
    exit 1
fi

echo "Sample files found. Starting test..."
echo ""

# Run the test
uv run pytest tests/test_chapter_parsing_phase3.py -v -s

echo ""
echo "Test completed."