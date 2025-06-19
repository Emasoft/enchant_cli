=== GitHub Actions Workflow Error Summary ===

## Main Issues Found:

### 1. CI Workflow Failures:
- **Ruff Format Check**: 11 files need reformatting
  - tests/test_enchant_orchestrator.py
  - tests/test_part_notation_detection.py
  - tests/test_real_integration_final.py
  - tests/test_translation_service_real.py
  - And 7 other files

### 2. Security Vulnerabilities (pip-audit):
- **vllm 0.8.5.post1**: Multiple vulnerabilities, needs update to 0.9.0
- **torch 2.6.0**: Security issues found
- **urllib3 2.4.0**: Needs update to 2.5.0
- **requests 2.32.3**: Needs update to 2.32.4
- **protobuf 4.25.7**: Needs update

### 3. Test Failures:
- Tests timing out in remote mode (60s timeout exceeded)
- E2E tests failing due to API connectivity issues

### 4. Pre-commit Workflow:
- actionlint installation failing (download issue)

### 5. Super-Linter:
- Running but taking longer than expected
- May have additional linting issues not visible in truncated logs
