# Python Dependencies License Verification Report

## Summary Table

| Dependency | License Type | License Category | Special Requirements |
|------------|--------------|------------------|---------------------|
| chardet>=5.2.0 | LGPL v2+ | Copyleft | Source disclosure required for modifications |
| colorama>=0.4.6 | BSD 3-Clause | Permissive | Attribution required |
| filelock>=3.16.1 | Unlicense | Public Domain | No restrictions |
| peewee>=3.18.1 | MIT | Permissive | Attribution required |
| pyyaml>=6.0.2 | MIT | Permissive | Attribution required |
| requests>=2.32.4 | Apache 2.0 | Permissive | Attribution, state changes |
| rich>=14.0.0 | MIT | Permissive | Attribution required |
| tenacity>=9.1.2 | Apache 2.0 | Permissive | Attribution, state changes |
| waiting>=1.4.1 | BSD 3-Clause | Permissive | Attribution required |

## Detailed License Information

### 1. **chardet** (Character Encoding Detector)
- **License**: GNU Lesser General Public License v2 or later (LGPL v2+)
- **License Type**: Copyleft
- **Copyright**: Copyright (C) 2006, 2007, 2008 Mark Pilgrim
- **Repository**: https://github.com/chardet/chardet
- **Special Requirements**:
  - Must allow users to swap out the LGPL library
  - Source code disclosure required for modifications
  - Cannot be relicensed (maintainers confirmed this is impossible)
- **Alternative**: charset_normalizer (MIT licensed) for more permissive needs

### 2. **colorama** (Cross-platform Colored Terminal Text)
- **License**: BSD 3-Clause
- **License Type**: Permissive
- **Copyright**: Jonathan Hartley & Arnon Yaari, 2013-2020
- **Repository**: https://github.com/tartley/colorama
- **Attribution Requirements**: Include copyright notice and license text

### 3. **filelock** (Platform-independent File Locking)
- **License**: Unlicense (Public Domain)
- **License Type**: Public Domain
- **Maintainer**: Bernát Gábor
- **Repository**: https://github.com/tox-dev/filelock
- **Special Requirements**: None - completely unrestricted use

### 4. **peewee** (Lightweight ORM)
- **License**: MIT
- **License Type**: Permissive
- **Author**: Charles Leifer (coleifer)
- **Repository**: https://github.com/coleifer/peewee
- **Attribution Requirements**: Include copyright notice and license text

### 5. **pyyaml** (YAML Parser and Emitter)
- **License**: MIT
- **License Type**: Permissive
- **Original Author**: Kirill Simonov
- **Repository**: https://github.com/yaml/pyyaml
- **Maintainer**: YAML community
- **Attribution Requirements**: Include copyright notice and license text

### 6. **requests** (HTTP Library)
- **License**: Apache License 2.0
- **License Type**: Permissive
- **Original Author**: Kenneth Reitz
- **Repository**: https://github.com/psf/requests (originally kennethreitz/requests)
- **Special Requirements**:
  - Include NOTICE file if present
  - State changes made to the code
  - Include copy of Apache 2.0 license

### 7. **rich** (Rich Text Formatting)
- **License**: MIT
- **License Type**: Permissive
- **Author**: Will McGugan
- **Company**: Textualize
- **Repository**: https://github.com/Textualize/rich
- **Attribution Requirements**: Include copyright notice and license text

### 8. **tenacity** (Retrying Library)
- **License**: Apache License 2.0
- **License Type**: Permissive
- **Author**: Julien Danjou
- **Repository**: https://github.com/jd/tenacity
- **Special Requirements**:
  - Include NOTICE file if present
  - State changes made to the code
  - Include copy of Apache 2.0 license

### 9. **waiting** (Waiting Utility)
- **License**: BSD 3-Clause
- **License Type**: Permissive
- **Author**: Rotem Yaari (vmalloc)
- **Repository**: https://github.com/vmalloc/waiting
- **Attribution Requirements**: Include copyright notice and license text

## License Compatibility Assessment

### Permissive Licenses (Compatible)
- **MIT** (peewee, pyyaml, rich): Very permissive, only requires attribution
- **BSD 3-Clause** (colorama, waiting): Similar to MIT, requires attribution
- **Apache 2.0** (requests, tenacity): Permissive with patent grant, requires stating changes
- **Unlicense** (filelock): Public domain, no restrictions

### Copyleft License (Special Consideration)
- **LGPL v2+** (chardet): This is the only copyleft license in the dependencies
  - Requires that modifications to chardet itself be released under LGPL
  - When distributed as a standalone binary (e.g., with PyInstaller), users must be able to replace the chardet library
  - Does NOT require your entire application to be LGPL

## Recommendations

1. **For Maximum Compatibility**: Consider replacing `chardet` with `charset_normalizer` (MIT licensed) if LGPL requirements are problematic

2. **Attribution Requirements**: Create a LICENSES directory with:
   - Copy of each license text
   - Attribution notices for all dependencies
   - NOTICE files from Apache 2.0 licensed projects

3. **Distribution Considerations**:
   - If distributing as source code: No special LGPL concerns
   - If distributing as binary: Ensure LGPL compliance for chardet

4. **Documentation**: Include a clear statement about third-party licenses in your documentation

All dependencies except chardet use permissive licenses that are fully compatible with proprietary software distribution.
