# Function Consolidation Plan for EnChANT

## Analysis of Similar Functions

### 1. Text Cleaning Functions

#### `clean(text: str) -> str`
- **Location**: cli_translator.py, translation_service.py
- **Status**: IDENTICAL - can be moved as-is
- **Purpose**: Strips leading/trailing spaces only, preserves control characters

#### `replace_repeated_chars(text: str, chars) -> str`
- **Location**: cli_translator.py, translation_service.py
- **Status**: IDENTICAL - can be moved as-is
- **Purpose**: Replace repeated occurrences of specific characters with single occurrence

#### `limit_repeated_chars(text, force_chinese=False, force_english=False)`
- **Location**: cli_translator.py, translation_service.py
- **Status**: IDENTICAL - can be moved as-is
- **Purpose**: Complex rules for limiting character repetitions based on type

### 2. HTML Processing Functions

#### `remove_html_markup(html_str: str) -> str`
- **Location**: cli_translator.py, translation_service.py
- **Status**: IDENTICAL - can be moved as-is
- **Purpose**: Comprehensive HTML cleaning while preserving code blocks

#### Related HTML functions (all identical):
- `extract_code_blocks(html_str: str)`
- `extract_inline_code(text: str)`
- `remove_html_comments(html_str: str)`
- `remove_script_and_style(html_str: str)`
- `replace_block_tags(html_str: str)`
- `remove_remaining_tags(html_str: str)`
- `unescape_non_code_with_placeholders(text: str)`

### 3. File Encoding/Decoding Functions

#### Encoding Detection
- **cli_translator.py**: `detect_file_encoding(file_path: Path) -> str`
  - Uses UniversalDetector
  - Reads file line by line
  - Returns encoding string

- **novel_renamer.py**: Part of `decode_file_content`
  - Uses chardet.detect
  - Reads limited bytes
  - Has confidence threshold

#### File Content Decoding
- **cli_translator.py**: `decode_input_file_content(input_file: Path) -> str`
  - Reads entire file
  - Uses tolog for logging
  - Falls back to GB18030
  - Always returns content (with replacement chars if needed)

- **novel_renamer.py**: `decode_file_content(file_path: Path, kb_to_read: int) -> Optional[str]`
  - Reads limited content (kb_to_read)
  - Checks minimum file size
  - Returns None on failure
  - Truncates to character limit
  - Uses logging module

## Consolidation Strategy

### Phase 1: Direct Moves (Identical Functions)

Move these functions to `common_utils.py` without modification:
```python
# Text processing
- clean(text: str) -> str
- replace_repeated_chars(text: str, chars) -> str
- limit_repeated_chars(text, force_chinese=False, force_english=False)

# HTML processing
- remove_html_markup(html_str: str) -> str
- extract_code_blocks(html_str: str)
- extract_inline_code(text: str)
- remove_html_comments(html_str: str)
- remove_script_and_style(html_str: str)
- replace_block_tags(html_str: str)
- remove_remaining_tags(html_str: str)
- unescape_non_code_with_placeholders(text: str)
```

### Phase 2: Parameterized Consolidation

#### Unified File Decoding Function
```python
def decode_file_content(
    file_path: Path,
    mode: str = 'full',  # 'full' or 'preview'
    preview_kb: int = 35,
    min_file_size_kb: Optional[int] = None,
    encoding_detector: str = 'auto',  # 'universal', 'chardet', 'auto'
    confidence_threshold: float = 0.7,
    fallback_encoding: str = 'gb18030',
    truncate_chars: Optional[int] = None,
    logger: Optional[logging.Logger] = None,
    raise_on_error: bool = True
) -> Optional[str]:
    """
    Unified file content decoder with configurable behavior.
    
    Parameters:
    - mode: 'full' reads entire file, 'preview' reads limited content
    - preview_kb: KB to read in preview mode
    - min_file_size_kb: Minimum file size (returns None if smaller)
    - encoding_detector: Method to detect encoding
    - confidence_threshold: Minimum confidence for chardet
    - fallback_encoding: Encoding to try if detection fails
    - truncate_chars: Truncate result to this many characters
    - logger: Logger instance (uses module logger if None)
    - raise_on_error: If False, returns None on error instead of raising
    """
```

#### Unified Encoding Detection Function
```python
def detect_file_encoding(
    file_path: Path,
    method: str = 'universal',  # 'universal', 'chardet', 'auto'
    sample_size: Optional[int] = None,  # bytes to sample (None = adaptive)
    confidence_threshold: float = 0.0,
    logger: Optional[logging.Logger] = None
) -> Tuple[str, float]:
    """
    Detect file encoding using specified method.
    
    Returns: (encoding, confidence)
    """
```

### Phase 3: Module-Specific Wrappers

Create convenience wrappers in each module that call the unified functions with appropriate parameters:

```python
# In cli_translator.py
def decode_input_file_content(input_file: Path) -> str:
    return decode_file_content(
        input_file,
        mode='full',
        encoding_detector='universal',
        logger=tolog,
        raise_on_error=True
    )

# In novel_renamer.py  
def decode_file_preview(file_path: Path, kb_to_read: int = 35) -> Optional[str]:
    return decode_file_content(
        file_path,
        mode='preview',
        preview_kb=kb_to_read,
        min_file_size_kb=MIN_FILE_SIZE_KB,
        encoding_detector='chardet',
        truncate_chars=CONTENT_NUMBER_OF_CHARACTERS_HARD_LIMIT,
        logger=logging.getLogger(__name__),
        raise_on_error=False
    )
```

### Implementation Order

1. **Create new common_text_utils.py** for text/HTML functions
2. **Create new common_file_utils.py** for file operations
3. **Move identical functions first** (Phase 1)
4. **Implement parameterized functions** (Phase 2)
5. **Update imports and create wrappers** (Phase 3)
6. **Test thoroughly** before removing originals

### Benefits

- Eliminates code duplication
- Maintains exact behavior for each module
- Allows future enhancements in one place
- Clear parameter names document differences
- Type hints improve code clarity