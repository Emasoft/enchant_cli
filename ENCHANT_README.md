# EnChANT - English-Chinese Automatic Novel Translator

A unified tool for processing Chinese novels through three phases:
1. **Renaming** - AI-powered metadata extraction and file renaming
2. **Translation** - Chinese to English translation using AI
3. **EPUB Generation** - Create EPUB files from translated chapters

## Installation

```bash
pip install -r requirements.txt
```

## Quick Start

### Full Processing (All Phases)
```bash
./enchant_cli.py novel.txt --openai-api-key YOUR_KEY
```

### Translation Only (Skip Renaming)
```bash
./enchant_cli.py novel.txt --skip-renaming
```

### EPUB Generation Only (From Existing Translation)
```bash
./enchant_cli.py novel.txt --skip-renaming --skip-translating
```

## Command Line Options

### Core Arguments
- `filepath` - Path to Chinese novel file or directory (for batch)
- `--batch` - Process all .txt files in a directory
- `--resume` - Resume interrupted processing

### Skip Phases
- `--skip-renaming` - Skip the file renaming phase
- `--skip-translating` - Skip the translation phase  
- `--skip-epub` - Skip the EPUB generation phase

### Configuration
- `--openai-api-key` - API key for renaming phase (or set OPENROUTER_API_KEY env)
- `--remote` - Use remote translation API instead of local LM Studio
- `--encoding` - File encoding (default: utf-8)
- `--max_chars` - Maximum characters per chapter (default: 12000)

## Processing Phases

### 1. Renaming Phase
- Extracts novel title and author using AI
- Creates standardized filename format
- Format: `English Title by English Author (Romanized) - Original Title by Original Author.txt`

### 2. Translation Phase
- Splits novel into manageable chunks
- Translates using local LM Studio or remote API
- Saves individual chapter files
- Creates combined translated file

### 3. EPUB Phase
- Collects translated chapters
- Detects chapter headings and numbering
- Generates table of contents
- Creates EPUB file

## Resumability

Each phase tracks its progress independently:
- Progress saved in `.{filename}_progress.yml` files
- Use `--resume` to continue from last checkpoint
- Progress files auto-cleaned on successful completion
- Batch operations save progress in `translation_batch_progress.yml`

## Examples

### Batch Processing with Resume
```bash
# Start batch processing
./enchant_cli.py novels_folder --batch --openai-api-key YOUR_KEY

# If interrupted, resume where left off
./enchant_cli.py novels_folder --batch --resume
```

### Custom Phase Combinations
```bash
# Rename and translate only (no EPUB)
./enchant_cli.py novel.txt --skip-epub --openai-api-key YOUR_KEY

# Translate and create EPUB (no renaming)
./enchant_cli.py already_renamed_novel.txt --skip-renaming
```

### Using Remote Translation API
```bash
# Set OpenRouter API key
export OPENROUTER_API_KEY="your_key"

# Use remote translation
./enchant_cli.py novel.txt --remote --skip-renaming
```

## File Structure

After processing, files are organized as:
```
input_dir/
├── original_novel.txt
├── Renamed Novel by Author (Romanized) - 原标题 by 原作者.txt
├── Renamed Novel/
│   ├── Renamed Novel by Author - Chapter 1.txt
│   ├── Renamed Novel by Author - Chapter 2.txt
│   └── ...
├── translated_Renamed Novel by Author.txt
└── Renamed_Novel.epub
```

## Requirements

- Python 3.8+
- For local translation: LM Studio running on localhost:1234
- For renaming: OpenAI API key
- For remote translation: OpenRouter API key

## Notes

- The tool preserves paragraph structure and formatting
- Chapter detection handles various formats (Chapter 1, Chapter One, Chapter I)
- Missing or out-of-order chapters are reported but don't stop EPUB generation
- Use `--resume` to make processing fault-tolerant