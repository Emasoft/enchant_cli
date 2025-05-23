#!/usr/bin/env bash

# Return error if executed directly - MUST BE PLACED AT THE BEGINNING
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    echo "Error: This script cannot be executed directly. All DHT scripts can only be called by the DHT Launcher in the project root. Please run dhtl.sh (or dhtl.bat) followed by the action you want to execute. For more informations use dhtl.sh --help"
    exit 1
fi

# setup_package.sh - Minimal project structure initialization

set -e # Exit on error

echo "🚀 Initializing basic project structure..."

# Create essential directories
mkdir -p src/enchant_cli
mkdir -p tests/samples
mkdir -p .github/workflows

# Create minimal package files
touch src/enchant_cli/__init__.py
touch src/enchant_cli/enchant_cli.py
touch src/enchant_cli/translation_service.py
touch src/enchant_cli/utils.py # Add utils file
touch tests/__init__.py
touch tests/conftest.py
touch tests/test_cli.py
# touch tests/test_utils.py # Placeholder for future tests
# touch tests/test_translation_service.py # Placeholder for future tests

# Create minimal configuration files (content should be added manually or via other scripts)
touch pyproject.toml
touch setup.cfg
touch setup.py # Minimal setup.py for compatibility
touch README.md
touch LICENSE
touch .gitignore
touch requirements.txt
touch requirements-dev.txt
touch .bumpversion.toml
touch pytest.ini
touch MANIFEST.in
touch .pre-commit-config.yaml
touch uv.lock
touch .python-version

# Create sample test file (if it doesn't exist)
if [ ! -f tests/samples/test_sample.txt ]; then
    {
        echo "Test Sample Novel by Test Author (Test Author) - 测试样本小说 by 测试作者"
        echo ""
        echo "第一章 测试内容"
        echo ""
        echo "这是一个测试文件，包含几个简短的段落。主要目的是验证翻译工具的基本功能。"
        echo ""
        echo "第一段：你好世界！这是一个简单的问候语。"
        echo "第二段：今天的天气很好，适合出去散步。"
        echo "第三段：请将这段文字翻译成英文，不要添加额外内容。"
    } > tests/samples/test_sample.txt
    echo "Created minimal tests/samples/test_sample.txt"
fi

# Create basic docs file
if [ ! -f CLAUDE.md ]; then
    echo "# Project Environment & Development Guide" > CLAUDE.md
    echo "" >> CLAUDE.md
    echo "Comprehensive guide for project environment, development, and GitHub integration." >> CLAUDE.md
    echo "Created minimal CLAUDE.md"
fi


# Note: This script does NOT initialize git, create complex configs, or set secrets.
# It's intended only for the absolute basic file/directory structure.

echo "✅ Basic project structure created."
echo "ℹ️  Next steps:"
echo "   1. Populate configuration files (pyproject.toml, .bumpversion.toml, etc.)."
echo "   2. Add source code and tests."
echo "   3. Initialize git: 'git init && git add . && git commit -m \"Initial commit\"'"
