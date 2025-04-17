"""Setup script for enchant-cli package."""

import os
import shutil

from setuptools import setup

# This setup.py is minimal and delegates to pyproject.toml
# The only reason to customize it is to handle special cases

# Ensure test samples directory exists
if not os.path.exists("tests/samples"):
    os.makedirs("tests/samples", exist_ok=True)

# Make sure the test sample file exists
sample_file = "tests/samples/test_sample.txt"
if not os.path.exists(sample_file):
    with open(sample_file, "w", encoding="utf-8") as f:
        f.write("Test Sample Novel by Test Author (Test Author) - 测试样本小说 by 测试作者\n\n")
        f.write("第一章 测试内容\n\n")
        f.write("这是一个测试文件，包含几个简短的段落。主要目的是验证翻译工具的基本功能。\n\n")
        f.write("第一段：你好世界！这是一个简单的问候语。\n")
        f.write("第二段：今天的天气很好，适合出去散步。\n")
        f.write("第三段：请将这段文字翻译成英文，不要添加额外内容。")

# Create directories for samples to be included in wheel and sdist
sample_dirs = [
    "src/enchant_cli/samples",            # Main package samples (for import)
    "src/enchant_cli/tests/samples",      # Test samples inside package (will be included in wheel)
]

# Create all sample directories
for dir_path in sample_dirs:
    if not os.path.exists(dir_path):
        os.makedirs(dir_path, exist_ok=True)

# Copy the sample file to all package directories
for dir_path in sample_dirs:
    shutil.copy2(sample_file, os.path.join(dir_path, "test_sample.txt"))

# Include test samples
setup(
    include_package_data=True,
    package_data={
        "enchant_cli": ["samples/*.txt", "tests/samples/*.txt"],  # Include both sample directories in package
        "": ["tests/samples/*.txt"],                              # Include test samples from root
    },
    data_files=[
        ("share/enchant-cli/tests/samples", ["tests/samples/test_sample.txt"]),
        ("share/enchant-cli/sample", ["src/enchant_cli/samples/test_sample.txt"]),  # Also include in data_files
    ],
)
