# Development Plan - Code Quality Review

## Objective
Examine the codebase for errors, potential issues, duplicated code, antipatterns, bad-practices and missing/unimplemented things. Fix all issues conservatively.

## Phase 1: Analysis Tasks
- [ ] Search for TODO/FIXME/XXX/HACK comments
- [ ] Check for NotImplementedError or unimplemented stub functions
- [ ] Look for duplicate code patterns
- [ ] Check for missing docstrings
- [ ] Verify all functions have proper type annotations
- [ ] Check for antipatterns (bare except, mutable defaults, etc.)
- [ ] Look for hardcoded values that should be configurable
- [ ] Check for proper error handling
- [ ] Verify import organization
- [ ] Check for unused imports/variables
- [ ] Look for missing shebang lines
- [ ] Check test coverage and quality

## Phase 2: Issues Found

### 1. Missing Docstrings (High Priority)
- cli_translator.py: 16+ functions/classes missing docstrings
- translation_service.py: 11+ functions/classes missing docstrings  
- renamenovels.py: 8 functions missing docstrings
- make_epub.py: 8 functions missing docstrings
- enchant_cli.py: 2 functions missing docstrings
- cost_tracker.py: 1 function missing docstring
- epub_db_optimized.py: 2 classes missing docstrings

### 2. Duplicate Code (Medium Priority)
- sanitize_filename function duplicated in 3 files
- PARAGRAPH_DELIMITERS constant duplicated in 2 files
- PRESERVE_UNLIMITED constant duplicated in 2 files
- remove_excess_empty_lines function duplicated in 2 files
- normalize_spaces function duplicated in 2 files
- load_safe_yaml function duplicated in 2 files
- Similar retry mechanisms in multiple files
- Similar API request patterns in multiple files

### 3. Missing Return Type Annotations (Medium Priority)
- retry_with_tenacity in translation_service.py
- no_retry_call in translation_service.py
- Several functions in make_epub.py and renamenovels.py

### 4. Code Organization Issues (Low Priority)
- Some files are quite large (cli_translator.py, translation_service.py)
- Similar functionality scattered across multiple files

## Phase 3: Fix Implementation

### Priority 1: Add Missing Docstrings (CONSERVATIVE APPROACH)
1. Add docstrings to functions in cli_translator.py
2. Add docstrings to functions in translation_service.py
3. Add docstrings to other files

### Priority 2: Fix Duplicate Code (DEFERRED)
- Many duplications are actually methods vs functions or have slight variations
- Refactoring would require extensive changes and testing
- Better to leave as-is for now to avoid breaking changes

### Priority 2: Add Missing Docstrings
1. Add docstrings to all functions/classes in:
   - cli_translator.py (highest priority - core module)
   - translation_service.py (high priority - core module)
   - renamenovels.py
   - make_epub.py
   - Other files with missing docstrings

### Priority 3: Add Missing Type Annotations
1. Add return type annotations to:
   - retry_with_tenacity -> Callable
   - no_retry_call -> Any
   - Functions in make_epub.py
   - Functions in renamenovels.py

### Priority 4: Configuration Improvements
1. Make localhost URL configurable in translation_service.py
   - Move API_URL_LMSTUDIO to config file

## Phase 4: Testing
- [ ] Run all tests after fixes
- [ ] Update tests if needed
- [ ] Verify no regressions

## Status: Starting Phase 1