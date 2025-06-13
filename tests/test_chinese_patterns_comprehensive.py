#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Comprehensive test for Chinese chapter pattern detection.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from make_epub import split_text

# Test mixed English and Chinese content
test_content = """
Some front matter before the first chapter.

Chapter 1
This is the first chapter in English.
It has multiple paragraphs.

第二章
这是第二章的中文内容。
也有多个段落。

Chapter Three - The Journey Continues
Back to English for chapter three.
With a subtitle this time.

第4章 新的开始
第四章又是中文，带有副标题。

Chapter V
Roman numerals work too.

第六章
第六章继续。

Chapter Seven: The Final Test
Word numbers are supported.

第八章：最后的考验
中文章节也可以有副标题。

第100章
三位数的章节。

第一千零一章
大数字章节。
"""

chapters, seq = split_text(test_content, detect_headings=True)

print(f"Total chapters detected: {len(chapters)}")
print(f"Chapter sequence: {seq}")
print("\nChapter titles:")
for i, (title, content) in enumerate(chapters):
    preview = content[:50].replace('\n', ' ')
    if len(content) > 50:
        preview += "..."
    print(f"{i+1}. {title} - '{preview}'")

# Verify the sequence
expected_seq = [1, 2, 3, 4, 5, 6, 7, 8, 100, 1001]
if seq == expected_seq:
    print("\n✓ Chapter sequence matches expected!")
else:
    print(f"\n✗ Chapter sequence mismatch!")
    print(f"  Expected: {expected_seq}")
    print(f"  Got: {seq}")