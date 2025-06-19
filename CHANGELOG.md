# Changelog

All notable changes to EnChANT Book Manager will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-06-19

### Added
- Initial release of EnChANT Book Manager
- Three-phase processing pipeline: Renaming, Translation, and EPUB Generation
- Support for batch processing of multiple novels
- Resume capability for interrupted translations
- Cost tracking for API usage
- Chunk-based translation with retry mechanism
- Automatic chapter detection for EPUB generation
- Support for multiple file encodings (UTF-8, GB2312, GB18030, Big5)
- Comprehensive test suite with 90%+ pass rate
- GitHub Actions CI/CD pipeline with automated testing
- Super-Linter integration for code quality checks
- Pre-commit hooks for code formatting and security checks

### Security
- Gitleaks integration for preventing secret leaks
- API key management through environment variables
- Secure handling of authentication credentials

### Documentation
- Comprehensive README with usage examples
- API documentation for all modules
- Configuration guide for different deployment scenarios