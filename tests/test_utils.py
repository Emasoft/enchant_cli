import pytest
from pathlib import Path
import sys
import logging # Added import

# Add src directory to Python path if needed, though pytest often handles this
SRC_DIR = str(Path(__file__).parent.parent / "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

# Import functions to test from utils
from enchant_cli.utils import (
    clean,
    replace_repeated_chars,
    limit_repeated_chars,
    remove_html_markup,
    normalize_spaces,
    remove_excess_empty_lines,
    strip_urls,
    is_markdown,
    detect_file_encoding,
    decode_input_file_content,
    split_on_punctuation_contextual,
    clean_adverts,
    is_latin_charset,
    foreign_book_title_splitter, # Import the function from utils
    PRESERVE_UNLIMITED,
    ALL_PUNCTUATION,
    PARAGRAPH_DELIMITERS,
    SENTENCE_ENDING,
    CLOSING_QUOTES,
    NON_BREAKING,
)

# --- Test Data ---
SAMPLE_HTML = """
<p>This is <b>bold</b> text.</p>
<!-- This is a comment -->
<script>alert('hello');</script>
<pre><code>
def greet():
    print("Hello")
</code></pre>
<p>Another paragraph with an <a href="http://example.com">url</a> and `inline code`.</p>
<p>Line breaks<br>here.</p>
<div>Div content</div>
Multiple   spaces.
"""

SAMPLE_CHINESE_TEXT = """
第一章 测试内容

这是一个测试文件，包含几个简短的段落。主要目的是验证翻译工具的基本功能。

第一段：你好世界！这是一个简单的问候语。
第二段：今天的天气很好，适合出去散步。
第三段：请将这段文字翻译成英文，不要添加额外内容。

网址：www.34gc.net 吉米小说网（www.jimixs.com）txt电子书下载

重复。。。！！！？？？、、、"""

# --- Tests ---

def test_clean():
    assert clean("  hello world  ") == "hello world"
    assert clean("\t\n hello \r\n") == "\t\n hello \r\n" # Strips only spaces, preserves others
    assert clean("no extra space") == "no extra space"
    with pytest.raises(TypeError):
        clean(123)

def test_replace_repeated_chars():
    assert replace_repeated_chars("Helloooo!!!", "o!") == "Hello!" # Corrected expected
    assert replace_repeated_chars(".....", ".") == "....." # '.' is in PRESERVE_UNLIMITED, so no change
    assert replace_repeated_chars("、、、、", "、") == "、"
    assert replace_repeated_chars("aaaaa", "a") == "a"

def test_limit_repeated_chars():
    assert limit_repeated_chars("Helloooo!!!!") == "Hellooo!!!" # Limit non-punctuation to 3, punctuation to 1
    assert limit_repeated_chars("......") == "......" # '.' is preserved
    assert limit_repeated_chars("、、、、") == "、" # Chinese punctuation limited to 1
    assert limit_repeated_chars("aaaaa") == "aaa" # Limit others to 3
    assert limit_repeated_chars("11111") == "11111" # Numbers are preserved

def test_remove_html_markup():
    cleaned = remove_html_markup(SAMPLE_HTML)
    assert "<b>" not in cleaned
    assert "<!--" not in cleaned
    assert "<script>" not in cleaned
    assert "alert('hello')" not in cleaned # Script content removed
    assert "url" in cleaned # Check for link text, not href, as <a> tag is removed
    assert "<pre>" not in cleaned # Pre tags themselves removed
    assert 'def greet():' in cleaned # Pre content preserved
    assert '`inline code`' in cleaned # Inline code preserved
    assert "Line breaks\nhere." in cleaned # <br> replaced with newline
    assert "Div content" in cleaned # Div content kept, tags removed - Check content only
    assert "Multiple   spaces." in cleaned # Expect multiple spaces before normalization

def test_normalize_spaces():
    assert normalize_spaces("  hello   world  \n\n  next   line  ") == "hello world\n\nnext line"
    assert normalize_spaces("\n\n") == "\n\n" # Preserves empty lines

def test_remove_excess_empty_lines():
    assert remove_excess_empty_lines("a\n\n\nb\n\n\n\nc\n\n\n\n\nd") == "a\n\n\nb\n\n\n\nc\n\n\n\nd"
    assert remove_excess_empty_lines("a\n\nb\nc") == "a\n\nb\nc"

def test_strip_urls():
    text = "Visit http://example.com or https://test.org/path?q=1 and email me@domain.com"
    cleaned = strip_urls(text)
    assert "http://example.com" not in cleaned
    assert "https://test.org/path?q=1" not in cleaned
    assert "me@domain.com" not in cleaned
    assert "Visit  or  and email " in cleaned # Expect extra spaces

def test_is_markdown():
    assert is_markdown("This has *italic* text.")
    assert is_markdown("`inline code`")
    assert is_markdown("```\ncode block\n```")
    assert is_markdown("[link](http://example.com)")
    assert not is_markdown("Just plain text.")
    assert not is_markdown("http://example.com") # URLs alone are stripped first

def test_detect_file_encoding(tmp_path):
    # UTF-8
    utf8_file = tmp_path / "test_utf8.txt"
    utf8_file.write_text("你好世界", encoding="utf-8")
    assert detect_file_encoding(utf8_file) == "utf-8"

    # GB18030
    gb_file = tmp_path / "test_gb.txt"
    gb_file.write_text("你好世界", encoding="gb18030")
    # Chardet might detect GBK or GB2312 as well, which are subsets
    detected_gb = detect_file_encoding(gb_file)
    assert detected_gb is None or detected_gb.lower().startswith("gb") # Allow None if confidence is low

    # ASCII
    ascii_file = tmp_path / "test_ascii.txt"
    ascii_file.write_text("Hello world", encoding="ascii")
    assert detect_file_encoding(ascii_file) == "ascii"

def test_decode_input_file_content(tmp_path, caplog):
    logger = logging.getLogger("test_decode")
    # UTF-8
    utf8_file = tmp_path / "test_utf8.txt"
    utf8_file.write_text("你好世界", encoding="utf-8")
    assert decode_input_file_content(utf8_file, logger) == "你好世界"

    # GB18030
    gb_file = tmp_path / "test_gb.txt"
    gb_file.write_text("你好世界", encoding="gb18030")
    assert decode_input_file_content(gb_file, logger) == "你好世界"

    # Test fallback and error handling (simulate bad detection)
    bad_detect_file = tmp_path / "bad_detect.txt"
    # Write GB18030 bytes but pretend it's UTF-8 initially
    content_bytes = "你好世界".encode("gb18030")
    bad_detect_file.write_bytes(content_bytes)

    # Mock detect_file_encoding to return wrong encoding first
    original_detect = sys.modules['enchant_cli.utils'].detect_file_encoding
    mock_detect_call_count = 0 # Use a local variable for count
    def mock_detect(*args, **kwargs):
        nonlocal mock_detect_call_count
        if mock_detect_call_count == 0:
            mock_detect_call_count += 1
            return 'utf-8' # Wrong encoding
        return original_detect(*args, **kwargs) # Correct on retry/fallback
    # mock_detect.call_count = 0 # Not needed with nonlocal
    sys.modules['enchant_cli.utils'].detect_file_encoding = mock_detect

    caplog.set_level(logging.DEBUG)
    decoded_content = decode_input_file_content(bad_detect_file, logger)
    assert decoded_content == "你好世界"
    assert "Falling back to GB18030" in caplog.text

    # Restore original function
    sys.modules['enchant_cli.utils'].detect_file_encoding = original_detect


def test_split_on_punctuation_contextual():
    text = "第一段。第二段！第三段？\n第四段，仍然是第四段。第五段「引用」结束。\n\n第六段..."
    paragraphs = split_on_punctuation_contextual(text)
    # Expected splits: after 。, !, ?, \n, 」, \n\n, ...
    # Note: The function adds \n\n after each paragraph.
    assert len(paragraphs) >= 6 # Exact count depends on how trailing ... is handled
    assert paragraphs[0].strip() == "第一段。"
    assert paragraphs[1].strip() == "第二段！"
    assert paragraphs[2].strip() == "第三段？"
    # Paragraph 4 might be split differently depending on interpretation,
    # but it should contain "第四段，仍然是第四段。"
    assert "第四段，仍然是第四段。" in paragraphs[3].strip()
    assert paragraphs[4].strip().endswith("结束。") # Check if quote handling is correct
    # The '...' should have been reduced to '.' by replace_repeated_chars
    assert paragraphs[5].strip() == "第六段."

    # Test edge case with space before newline trigger
    text_space = "句子结束。 “新段落开始”"
    paragraphs_space = split_on_punctuation_contextual(text_space)
    assert len(paragraphs_space) == 2
    assert paragraphs_space[0].strip() == "句子结束。"
    assert paragraphs_space[1].strip() == "“新段落开始”"

def test_clean_adverts():
    text = "Some text. 吉米小说网 (www.jimixs.com) txt电子书下载 More text."
    cleaned = clean_adverts(text)
    assert "吉米小说网" not in cleaned
    assert "www.jimixs.com" not in cleaned
    assert "Some text.   More text." in cleaned # Ad replaced with space

    text2 = "Another example 网址:www.34gc.net end."
    cleaned2 = clean_adverts(text2)
    assert "www.34gc.net" not in cleaned2
    # Check with potential multiple spaces resulting from replacement
    assert "Another example  end." in cleaned2 # Expect two spaces

def test_is_latin_charset():
    assert is_latin_charset("Hello world")
    assert not is_latin_charset("你好世界")
    assert not is_latin_charset("Hello 世界") # Ratio 2/5=0.4 > 0.3 threshold, so expect False
    assert not is_latin_charset("你好 world") # Mostly non-Latin
    assert is_latin_charset("Résumé") # Includes Latin-1 Supplement
    assert not is_latin_charset("你好，世界！") # Punctuation doesn't make it Latin

# Test cases for foreign_book_title_splitter (now imported from utils)
@pytest.mark.parametrize("filename, expected", [
    ("Translated Title by Translated Author - Original Title by Original Author.txt",
     ("Translated Title", "Original Title", "", "Translated Author", "Original Author", "")),
    ("My Novel by John Doe (Jon Do) - 我的小说 by 张三.epub",
     ("My Novel", "我的小说", "", "John Doe", "张三", "")),
    ("Just A Title by Some Author.txt",
     ("Just A Title", "Just A Title", "", "Some Author", "Some Author", "")),
    ("Title Only - Original Title Only.txt",
     ("Title Only", "Original Title Only", "", "Unknown Author", "Unknown Author", "")),
    ("Title by Author (Romanization).txt",
     ("Title", "Title", "", "Author", "Author", "")),
    ("No Author - Original Title by Original Author.txt",
     ("No Author", "Original Title", "", "Unknown Author", "Original Author", "")),
    ("Translated Title by Translated Author - No Author Original.txt",
     ("Translated Title", "No Author Original", "", "Translated Author", "Unknown Author", "")),
    ("Basic Name.txt",
     ("Basic Name", "Basic Name", "", "Unknown Author", "Unknown Author", "")),
    ("Another - Test.txt",
     ("Another", "Test", "", "Unknown Author", "Unknown Author", "")),
])
def test_foreign_book_title_splitter(filename, expected):
    result = foreign_book_title_splitter(filename)
    assert result == expected
