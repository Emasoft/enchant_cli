# Refactoring Log

This log tracks all code movements and changes during the refactoring process.

## Date: 2025-06-25

### Module: common_text_utils.py (20KB → target: ~2-3 modules under 10KB each)

#### Preparation Phase:
- [x] Read entire file
- [x] Create backup: common_text_utils.py.bak
- [x] Create element checklist
- [x] Plan module structure
- [x] Identify dependencies

#### Planned Module Structure:

**Module 1: text_constants.py (~2KB)**
- All constants (PRESERVE_UNLIMITED, CHINESE_PUNCTUATION, etc.)
- Used by both text processing and HTML processing functions

**Module 2: text_processing.py (~8KB)**
- clean()
- replace_repeated_chars()
- limit_repeated_chars()
- remove_excess_empty_lines()
- normalize_spaces()
- clean_adverts()
- Imports: text_constants

**Module 3: html_processing.py (~8KB)**
- extract_code_blocks()
- extract_inline_code()
- remove_html_comments()
- remove_script_and_style()
- replace_block_tags()
- remove_remaining_tags()
- unescape_non_code_with_placeholders()
- remove_html_markup()
- Imports: None (self-contained)

**Updated common_text_utils.py (~1KB)**
- Wrapper imports from all three modules for backward compatibility

#### Dependencies to Update:
- translation_service.py (imports clean, normalize_spaces)
- cli_translator.py (imports limit_repeated_chars)
- text_validators.py (imports PRESERVE_UNLIMITED)
- enchant_cli.py (imports clean)
- epub_builder.py (imports remove_html_markup)
- text_processor.py (imports clean_adverts)
- Any test files that import from common_text_utils

#### Element Checklist:

**Constants (7 items):**
1. PRESERVE_UNLIMITED (set) - moved_to_text_constants.py
2. CHINESE_PUNCTUATION (set) - moved_to_text_constants.py
3. ENGLISH_PUNCTUATION (set) - moved_to_text_constants.py
4. SENTENCE_ENDING (set) - moved_to_text_constants.py
5. CLOSING_QUOTES (set) - moved_to_text_constants.py
6. NON_BREAKING (set) - moved_to_text_constants.py
7. ALL_PUNCTUATION (derived set) - moved_to_text_constants.py

**Text Processing Functions (6 items):**
8. clean() - moved_to_text_processing.py
9. replace_repeated_chars() - moved_to_text_processing.py
10. limit_repeated_chars() - moved_to_text_processing.py
11. remove_excess_empty_lines() - moved_to_text_processing.py
12. normalize_spaces() - moved_to_text_processing.py
13. clean_adverts() - moved_to_text_processing.py

**HTML Processing Functions (8 items):**
14. extract_code_blocks() - moved_to_html_processing.py
15. extract_inline_code() - moved_to_html_processing.py
16. remove_html_comments() - moved_to_html_processing.py
17. remove_script_and_style() - moved_to_html_processing.py
18. replace_block_tags() - moved_to_html_processing.py
19. remove_remaining_tags() - moved_to_html_processing.py
20. unescape_non_code_with_placeholders() - moved_to_html_processing.py
21. remove_html_markup() - moved_to_html_processing.py

#### Implementation Phase:
- [x] Move elements to new modules
  - Created text_constants.py (4KB)
  - Created text_processing.py (12KB)
  - Created html_processing.py (8KB)
  - Updated common_text_utils.py to wrapper (4KB)
- [x] Update imports in all dependent files
  - No updates needed - backward compatibility maintained
- [x] Test each change
  - Linting passed
  - Type checking passed
  - Import test passed
- [x] Commit atomically

#### Verification Phase:
- [ ] Run all tests
- [ ] Verify no lost functionality
- [ ] Check file sizes

---
