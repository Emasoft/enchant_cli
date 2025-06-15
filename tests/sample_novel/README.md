# Sample Novel Test Data

This directory contains test data for the Phase 3 chapter parsing test.

## Required Files

1. **translated_Global High Martial Arts by Eagle Eats Chick (Lǎo yīng chī xiǎo jī).txt**
   - The translated novel text file containing chapter headings to be parsed

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

```bash
uv run pytest tests/test_chapter_parsing_phase3.py -v -s
```