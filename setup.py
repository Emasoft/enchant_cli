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

# Create a copy of the sample in src directory to ensure it's included in wheel
src_sample_dir = "src/enchant_cli/samples"
if not os.path.exists(src_sample_dir):
    os.makedirs(src_sample_dir, exist_ok=True)

# Copy the sample file to the package directory
shutil.copy2(sample_file, os.path.join(src_sample_dir, "test_sample.txt"))

# Include test samples
setup(
    include_package_data=True,
    package_data={
        "enchant_cli": ["samples/*.txt"],  # Include samples within the package
    },
    data_files=[
        ("tests/samples", ["tests/samples/test_sample.txt"]),
    ],
)