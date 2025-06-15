# Sample Novel Test Data

This directory contains test data for the Phase 3 chapter parsing test.

## Important Note

**The test uses the FULL novel file (600K+ lines, ~30MB) without any truncation or sampling.**
This ensures the program works correctly with real-world novel sizes.

## Required Files

1. **translated_Global High Martial Arts by Eagle Eats Chick (Lǎo yīng chī xiǎo jī).txt**
   - The complete translated novel text file (632,710 lines)
   - Contains chapter headings to be parsed by the TOC parser

2. **chapter_headings.txt**
   - Expected chapter headings in the format:
   ```
   Chapter Number
   Line Number
   Found String

   1
   58
   Chapter One: The Script Is Wrong

   2
   232
   Chapter Two: Must Take the Martial Arts Examination!
   ```

## Test Purpose

The test verifies that enchant_cli.py (using make_epub.py's TOC parser) correctly:
- Identifies chapter headings from the translated text
- Generates an EPUB with proper table of contents
- Matches the first 49 chapters exactly as expected
- Avoids parsing false positives (e.g., "in this chapter")
- Ensures no duplicate chapters in the TOC

## Running the Test

Using the provided script (recommended):
```bash
./run_chapter_parsing_test.sh
```

Or directly with pytest:
```bash
uv run pytest tests/test_chapter_parsing_phase3.py -v -s
```

## Test Performance

The test processes the full novel file to generate an EPUB. Expected performance:
- EPUB generation: 2-5 minutes (depending on system)
- Memory usage: ~500MB peak
- Output EPUB size: ~250MB

A temporary directory `temp_test_chapter_parsing/` is created in the repo root and cleaned up after the test.