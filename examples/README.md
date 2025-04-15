# Example Files for Enchant CLI

This directory contains example input files that can be used to test the Enchant CLI Translator.

## Sample Files

- Chinese novel excerpts
- Text files with various formatting
- Empty files for testing edge cases

## Usage

You can use these files to test the translator:

```bash
# Translate a single example file
enchant_cli examples/example_file.txt -o output.txt

# Batch translate all examples
enchant_cli --batch examples/ -o translated/
```

These files are included as reference examples only and are not installed with the package.