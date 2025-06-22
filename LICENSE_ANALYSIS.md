# License Analysis for ENCHANT_BOOK_MANAGER Dependencies

## Summary

Analysis of Python dependencies from pyproject.toml for license compatibility with MIT and Apache-2.0 licenses.

## Dependencies License Information

| Package | Version | License | MIT Compatible | Apache-2.0 Compatible | Notes |
|---------|---------|---------|----------------|----------------------|-------|
| chardet | >=5.2.0 | LGPL-2.1+ | ⚠️ | ⚠️ | Requires special handling - see notes below |
| colorama | >=0.4.6 | BSD-3-Clause | ✅ | ✅ | Permissive, no issues |
| filelock | >=3.16.1 | Public Domain | ✅ | ✅ | Most permissive possible |
| peewee | >=3.18.1 | MIT | ✅ | ✅ | Same as project, no issues |
| pyyaml | >=6.0.2 | MIT | ✅ | ✅ | Same as project, no issues |
| requests | >=2.32.4 | Apache-2.0 | ✅ | ✅ | Same as one option, no issues |
| rich | >=14.0.0 | MIT | ✅ | ✅ | Same as project, no issues |
| tenacity | >=9.1.2 | Apache-2.0 | ✅ | ✅ | Same as one option, no issues |
| waiting | >=1.4.1 | BSD-3-Clause | ✅ | ✅ | Permissive, no issues |

## License Details

### 1. **chardet** - LGPL-2.1+ (GNU Lesser General Public License v2.1 or later)
- **Description**: Universal character encoding detector
- **Compatibility Concerns**: LGPL is a copyleft license that has specific requirements
- **Requirements**:
  - Must include LGPL license text
  - If you modify chardet itself, you must release those modifications under LGPL
  - Dynamic linking is generally OK without affecting your license
  - Static linking or incorporating source code directly would require LGPL compliance
- **Recommendation**: Use as a regular pip dependency (dynamic linking) to avoid license conflicts

### 2. **colorama** - BSD-3-Clause
- **Description**: Cross-platform colored terminal text
- **Requirements**: Include copyright notice and BSD-3-Clause license text
- **No compatibility issues**

### 3. **filelock** - Public Domain
- **Description**: Platform-independent file locking
- **Requirements**: None - public domain is the most permissive
- **No compatibility issues**

### 4. **peewee** - MIT
- **Description**: Small, expressive ORM
- **Requirements**: Include MIT license text and copyright notice
- **No compatibility issues**

### 5. **pyyaml** - MIT
- **Description**: YAML parser and emitter
- **Requirements**: Include MIT license text and copyright notice
- **No compatibility issues**

### 6. **requests** - Apache-2.0
- **Description**: HTTP library
- **Requirements**: Include Apache-2.0 license text and NOTICE file if present
- **No compatibility issues**

### 7. **rich** - MIT
- **Description**: Rich text and beautiful formatting in the terminal
- **Requirements**: Include MIT license text and copyright notice
- **No compatibility issues**

### 8. **tenacity** - Apache-2.0
- **Description**: General-purpose retrying library
- **Requirements**: Include Apache-2.0 license text and NOTICE file if present
- **No compatibility issues**

### 9. **waiting** - BSD-3-Clause
- **Description**: Utility for waiting for stuff to happen
- **Requirements**: Include copyright notice and BSD-3-Clause license text
- **No compatibility issues**

## Recommendations

1. **For chardet (LGPL)**:
   - Keep it as a regular pip dependency (don't vendor or statically link)
   - Include the LGPL license text in your license notices
   - Consider alternatives if you need to embed/vendor dependencies:
     - `charset-normalizer` (MIT license) - drop-in replacement
     - `cchardet` (MPL-1.1/GPL-2.0/LGPL-2.1) - faster but same license family

2. **License Notices**: Create a `THIRD_PARTY_LICENSES` or `NOTICE` file that includes:
   - All dependency licenses
   - Copyright notices as required by BSD and MIT licenses
   - Special mention of LGPL for chardet

3. **Dual Licensing**: Your current MIT/Apache-2.0 dual license is compatible with all dependencies except for special handling needed for chardet.

## Alternative to chardet (if needed)

If you want to avoid LGPL entirely, consider replacing chardet with:
- **charset-normalizer** (MIT) - Pure Python, drop-in replacement
  ```toml
  charset-normalizer>=3.0.0  # Instead of chardet
  ```

## Conclusion

All dependencies are compatible with MIT and Apache-2.0 dual licensing, with the exception of chardet which requires special consideration due to its LGPL license. As long as chardet is used as a standard dependency (not vendored or statically linked), there are no license conflicts.
