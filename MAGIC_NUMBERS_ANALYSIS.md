# Magic Numbers Report - ENCHANT Book Manager

This report identifies all hardcoded numeric values (magic numbers) in the codebase that should be replaced with named constants for better maintainability and readability.

## Summary

Found multiple magic numbers across the codebase related to:
- Timeouts and delays
- Retry configurations
- File size limits
- Character limits
- Batch processing sizes
- API configuration values
- Formatting parameters

## Detailed Findings

### 1. Timeout Values

**icloud_sync.py**
- Line 212: `timeout_seconds=300` - iCloud folder sync timeout (5 minutes)
- Line 213: `sleep_seconds=2` - iCloud sync check interval
- Line 260: `timeout_seconds=120` - iCloud file download timeout (2 minutes)
- Line 261: `sleep_seconds=1` - iCloud file check interval

**translation_constants.py** ✓ (Already using constants)
- Line 25: `CONNECTION_TIMEOUT = 60`
- Line 26: `RESPONSE_TIMEOUT = 480`

**config_schema.py** (Default values in YAML template)
- Lines 71, 107, 172, 185: `connection_timeout: 30`
- Lines 73, 109, 174, 187: `response_timeout: 300`
- Lines 287: `sync_timeout: 300`
- Line 290: `sync_check_interval: 2`

### 2. Retry Configuration

**rename_api_client.py**
- Line 75: `max_wait=10.0` - Max retry wait for rename API
- Line 112: `timeout=10` - Request timeout for rename API

**translation_orchestrator.py**
- Line 45: `DEFAULT_MAX_CHUNK_RETRIES = 10` ✓ (Already a constant)
- Line 46: `MAX_RETRY_WAIT_SECONDS = 60` ✓ (Already a constant)

**common_utils.py** (Default parameters)
- Lines 147, 224: `max_attempts: int = 10`
- Lines 149, 226: `max_wait: float = 60.0`
- Lines 150, 227: `min_wait: float = 1.0`
- Line 148, 225: `base_wait: float = 1.0`

### 3. File Size Limits

**rename_file_processor.py**
- Line 35: `MIN_FILE_SIZE_KB = 100` ✓ (Already a constant)
- Line 36: `CONTENT_NUMBER_OF_CHARACTERS_HARD_LIMIT = 1500` ✓ (Already a constant)
- Line 37: `DEFAULT_KB_TO_READ = 35` ✓ (Already a constant)
- Line 61: `file_path.stat().st_size >= MIN_FILE_SIZE_KB * 1024`

**common_file_utils.py**
- Line 101: `sample_size = 32 * 1024` - Default sample size (32KB)
- Line 176: `32 * 1024` - Sample size for preview mode
- Line 155: `file_size_kb = file_path.stat().st_size / 1024`
- Line 164: `bytes_to_read = preview_kb * 1024`
- Line 247: `min_file_size_kb: int = 100` - Default parameter
- Line 248: `max_chars: int = 1500` - Default parameter

**common_constants.py** ✓ (Already using constants)
- Line 70: `MIN_FILE_SIZE_KB = 35`
- Line 71: `MAX_FILE_SIZE_MB = 100`

### 4. Character/Token Limits

**translation_constants.py** ✓ (Already using constants)
- Line 24: `DEFAULT_CHUNK_SIZE = 12000`
- Line 27: `DEFAULT_MAX_TOKENS = 4000`

**text_splitter.py**
- Line 44: `DEFAULT_MAX_CHARS = 11999` ✓ (Already a constant)

**common_constants.py** ✓ (Already using constants)
- Line 48: `DEFAULT_MAX_CHARS = 12000`

**cli_translator.py**
- Line 93: `max_chars: int = 12000` - Default parameter

**api_clients.py**
- Line 180: `"temperature": kwargs.get("temperature", 0.1)` - Default temperature
- Line 240: `"temperature": kwargs.get("temperature", 0.1)` - Default temperature

### 5. Batch Processing

**epub_db_optimized.py**
- Lines 115, 129, 132: `1000` - Batch size for database operations

**translation_orchestrator.py**
- Lines 125, 137, 138, 158, 159, 175, 176, 245, 246: `max_length=50` and `max_length=100` - Filename sanitization limits

### 6. Validation Thresholds

**text_validators.py**
- Line 55: `threshold: float = 0.1` - Default Latin charset threshold (10%)
- Line 93: `max_allowed: int = 4` - Maximum allowed character repetitions
- Line 153: `threshold=0.05` - Stricter Latin charset check (5%)
- Line 165: `chinese_chars[:10]` - Limit Chinese characters shown in error

**common_constants.py** ✓ (Already using constants)
- Line 66: `MIN_ENCODING_CONFIDENCE = 0.7`
- Line 67: `MIN_TRANSLATION_LENGTH_RATIO = 0.3`

### 7. UI/Display Configuration

**epub_builders.py**
- Line 142: `max-width:100%` - CSS value
- Line 201: `line-height:1.4`, `margin:5%`, `margin:2em 0 1em`, `text-indent:1.5em`, etc. - CSS values

**text_processing.py**
- Line 136: `char * min(count, 3)` - Maximum character repetition
- Line 143: `max_empty_lines: int = 2` - Default max empty lines

### 8. Version and Temperature Settings

**cli_translator.py**
- Line 54: `APP_VERSION = "0.1.0"` ✓ (Already a constant, though should use __version__)

**renamenovels.py**
- Line 52: `VERSION = "1.3.1"` ✓ (Already a constant)
- Line 129: `"temperature": 0.0` - Default temperature for rename

**config_preset_validator.py**
- Line 207: `float_val > 2.0` - Temperature maximum validation

### 9. Miscellaneous

**common_utils.py**
- Line 63: `max_length: int = 255` - Default max filename length
- Line 279: `wait_time = max(0, time_limit - elapsed - 1)` - The `1` could be a constant

**epub_toc_enhanced.py**
- Line 202: `current_depth: int = 1` - Default TOC depth

## Recommendations

### High Priority (Create New Constants)

1. **icloud_sync.py** - Create constants for:
   ```python
   ICLOUD_FOLDER_SYNC_TIMEOUT = 300  # 5 minutes
   ICLOUD_FOLDER_SYNC_CHECK_INTERVAL = 2
   ICLOUD_FILE_SYNC_TIMEOUT = 120  # 2 minutes
   ICLOUD_FILE_SYNC_CHECK_INTERVAL = 1
   ```

2. **common_file_utils.py** - Create constants for:
   ```python
   DEFAULT_SAMPLE_SIZE_KB = 32  # 32KB for encoding detection
   BYTES_PER_KB = 1024
   ```

3. **epub_db_optimized.py** - Create constant for:
   ```python
   DB_INSERT_BATCH_SIZE = 1000
   ```

4. **api_clients.py** - Create constant for:
   ```python
   DEFAULT_TRANSLATION_TEMPERATURE = 0.1
   ```

5. **translation_orchestrator.py** - Create constants for:
   ```python
   MAX_FILENAME_LENGTH_SHORT = 50
   MAX_FILENAME_LENGTH_FULL = 100
   ```

6. **config_preset_validator.py** - Create constant for:
   ```python
   MAX_TEMPERATURE_VALUE = 2.0
   ```

7. **text_processing.py** - Create constants for:
   ```python
   MAX_REPEATED_CHAR_DISPLAY = 3
   DEFAULT_MAX_EMPTY_LINES = 2
   ```

8. **text_validators.py** - Create constants for:
   ```python
   DEFAULT_LATIN_CHARSET_THRESHOLD = 0.1  # 10%
   STRICT_LATIN_CHARSET_THRESHOLD = 0.05  # 5%
   DEFAULT_MAX_CHAR_REPETITIONS = 4
   MAX_CHINESE_CHARS_IN_ERROR = 10
   ```

### Medium Priority (Consider Extracting)

1. CSS values in **epub_builders.py** could be moved to a CSS template file or constants
2. Default parameter values that appear in multiple places should be centralized
3. Time-related calculations (like `elapsed - 1`) could use named constants for clarity

### Low Priority (Already Good)

1. Constants already defined in `common_constants.py`, `translation_constants.py`, `text_constants.py`, and `epub_constants.py`
2. Version strings (though they should ideally use `__version__` from package metadata)
3. YAML configuration defaults in `config_schema.py` (these are meant to be user-configurable)

## Next Steps

1. Create a new module `magic_constants.py` to consolidate all the new constants
2. Update all files to import and use these constants
3. Add documentation for each constant explaining its purpose and acceptable range
4. Consider creating configuration classes for related constants (e.g., `ICloudConfig`, `BatchProcessingConfig`)
5. Add validation to ensure constants are within acceptable ranges
