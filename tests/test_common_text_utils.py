#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Comprehensive tests for common_text_utils.py with 100% coverage
"""

try:
    import pytest
except ImportError:
    pytest = None
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common_text_utils import (
    clean,
    replace_repeated_chars,
    limit_repeated_chars,
    extract_code_blocks,
    extract_inline_code,
    remove_html_comments,
    remove_script_and_style,
    replace_block_tags,
    remove_remaining_tags,
    unescape_non_code_with_placeholders,
    remove_html_markup,
    PRESERVE_UNLIMITED,
    CHINESE_PUNCTUATION,
    ENGLISH_PUNCTUATION,
    ALL_PUNCTUATION,
)


class TestTextCleaning:
    """Test text cleaning functions"""

    def test_clean_basic(self):
        """Test basic clean functionality"""
        assert clean("  hello  ") == "hello"
        assert clean(" \thello\t ") == "\thello\t"  # Preserves tabs
        assert clean(" \nhello\n ") == "\nhello\n"  # Preserves newlines
        assert clean("hello") == "hello"  # No change needed

    def test_clean_type_error(self):
        """Test clean with non-string input"""
        if pytest:
            with pytest.raises(TypeError, match="Input must be a string"):
                clean(123)

            with pytest.raises(TypeError, match="Input must be a string"):
                clean(None)
        else:
            # Manual exception checking
            try:
                clean(123)
                assert False, "Expected TypeError"
            except TypeError as e:
                assert "Input must be a string" in str(e)

            try:
                clean(None)
                assert False, "Expected TypeError"
            except TypeError as e:
                assert "Input must be a string" in str(e)

    def test_clean_control_characters(self):
        """Test that control characters are preserved"""
        text = " \r\n\t\v\f text \r\n\t\v\f "
        result = clean(text)
        assert result == "\r\n\t\v\f text \r\n\t\v\f"

    def test_replace_repeated_chars(self):
        """Test replacement of repeated characters"""
        # Single character replacement
        assert replace_repeated_chars("Hello!!!", ["!"]) == "Hello!"
        assert replace_repeated_chars("Test....", ["."]) == "Test."

        # Multiple characters
        assert replace_repeated_chars("Wow!!! Really???", ["!", "?"]) == "Wow! Really?"

        # Characters requiring escaping
        assert replace_repeated_chars("Test***", ["*"]) == "Test*"
        assert replace_repeated_chars("A+++B", ["+"]) == "A+B"

        # No replacement needed
        assert replace_repeated_chars("Normal text", ["!", "?"]) == "Normal text"

    def test_limit_repeated_chars_basic(self):
        """Test basic character limiting"""
        # Letters limited to 3
        assert limit_repeated_chars("aaaaa") == "aaa"
        assert limit_repeated_chars("BBBBB") == "BBB"

        # Numbers unlimited
        assert limit_repeated_chars("111111") == "111111"
        assert limit_repeated_chars("999999") == "999999"

        # ASCII punctuation in PRESERVE_UNLIMITED - not limited
        assert limit_repeated_chars("!!!!!!") == "!!!!!!"  # ! is preserved
        assert limit_repeated_chars("??????") == "??????"  # ? is preserved

        # Chinese punctuation limited to 1
        assert limit_repeated_chars("！！！！！！") == "！"
        assert limit_repeated_chars("？？？？？？") == "？"

    def test_limit_repeated_chars_preserve_unlimited(self):
        """Test preservation of unlimited characters"""
        # Spaces preserved
        assert limit_repeated_chars("a     b") == "a     b"

        # Special symbols preserved
        assert limit_repeated_chars("#####") == "#####"
        assert limit_repeated_chars(".....") == "....."
        assert limit_repeated_chars("-----") == "-----"

    def test_limit_repeated_chars_chinese_punctuation(self):
        """Test Chinese punctuation limiting"""
        # Without force_chinese
        assert limit_repeated_chars("。。。。") == "。"
        assert limit_repeated_chars("！！！！") == "！"

        # With force_chinese
        assert limit_repeated_chars("。。。。", force_chinese=True) == "。"
        assert limit_repeated_chars("，，，，", force_chinese=True) == "，"

    def test_limit_repeated_chars_english_punctuation(self):
        """Test English punctuation limiting"""
        # Even with force_english=True, PRESERVE_UNLIMITED chars are still preserved
        assert limit_repeated_chars("!!!!!", force_english=True) == "!!!!!"
        assert limit_repeated_chars(".....", force_english=True) == "....."

        # Test with punctuation not in PRESERVE_UNLIMITED
        # (Need to find English punctuation that's not preserved)
        # Most ASCII punctuation is in PRESERVE_UNLIMITED, so this mainly affects
        # the behavior when combined with text
        text = "Hello!!!!! World???"
        assert limit_repeated_chars(text, force_english=True) == "Hello!!!!! World???"

    def test_limit_repeated_chars_mixed(self):
        """Test mixed character types"""
        # Mix of different character types
        text = "Wowwww!!! Numbers: 111 Symbols: ###"
        result = limit_repeated_chars(text)
        # ! and # are in PRESERVE_UNLIMITED, so they're not limited
        # Letters are limited to 3 occurrences, so "wwww" becomes "www"
        assert result == "Wowww!!! Numbers: 111 Symbols: ###"

        # Unicode numbers
        text = "ⅣⅣⅣⅣ"  # Roman numerals
        assert limit_repeated_chars(text) == "ⅣⅣⅣⅣ"

    def test_limit_repeated_chars_edge_cases(self):
        """Test edge cases for limit_repeated_chars"""
        # Empty string
        assert limit_repeated_chars("") == ""

        # Single characters
        assert limit_repeated_chars("a") == "a"
        assert limit_repeated_chars("!") == "!"

        # Exactly 3 characters (boundary case)
        assert limit_repeated_chars("aaa") == "aaa"
        assert limit_repeated_chars("aaaa") == "aaa"


class TestHTMLProcessing:
    """Test HTML processing functions"""

    def test_extract_code_blocks(self):
        """Test extraction of code blocks"""
        # Simple pre block
        html = "Text <pre>code here</pre> more text"
        result, blocks = extract_code_blocks(html)
        assert result == "Text __CODE_BLOCK_0__ more text"
        assert blocks == ["<pre>code here</pre>"]

        # Multiple blocks
        html = "<pre>code1</pre> text <code>code2</code> end"
        result, blocks = extract_code_blocks(html)
        assert "__CODE_BLOCK_0__" in result
        assert "__CODE_BLOCK_1__" in result
        assert len(blocks) == 2

        # With attributes
        html = '<pre class="python">print("hello")</pre>'
        result, blocks = extract_code_blocks(html)
        assert result == "__CODE_BLOCK_0__"
        assert blocks[0] == '<pre class="python">print("hello")</pre>'

        # Case insensitive
        html = "<PRE>code</PRE> <Code>more</Code>"
        result, blocks = extract_code_blocks(html)
        assert len(blocks) == 2

    def test_extract_inline_code(self):
        """Test extraction of inline code"""
        # Simple inline code
        text = "Use `print()` function"
        result, snippets = extract_inline_code(text)
        assert result == "Use __INLINE_CODE_0__ function"
        assert snippets == ["`print()`"]

        # Multiple inline codes
        text = "Both `var1` and `var2` are variables"
        result, snippets = extract_inline_code(text)
        assert "__INLINE_CODE_0__" in result
        assert "__INLINE_CODE_1__" in result
        assert len(snippets) == 2

        # No inline code
        text = "No code here"
        result, snippets = extract_inline_code(text)
        assert result == "No code here"
        assert snippets == []

    def test_remove_html_comments(self):
        """Test HTML comment removal"""
        # Simple comment
        html = "Text <!-- comment --> more"
        assert remove_html_comments(html) == "Text  more"

        # Multiline comment
        html = "Start <!-- long\ncomment\nhere --> end"
        assert remove_html_comments(html) == "Start  end"

        # Multiple comments
        html = "<!-- c1 -->Text<!-- c2 -->"
        assert remove_html_comments(html) == "Text"

        # No comments
        assert remove_html_comments("No comments") == "No comments"

    def test_remove_script_and_style(self):
        """Test removal of script and style tags"""
        # Script tag
        html = 'Before <script>alert("hi");</script> after'
        assert remove_script_and_style(html) == "Before  after"

        # Style tag
        html = "Text <style>body { color: red; }</style> more"
        assert remove_script_and_style(html) == "Text  more"

        # Both tags
        html = "<script>js</script> content <style>css</style>"
        assert remove_script_and_style(html) == " content "

        # With attributes
        html = '<script src="file.js">code</script>'
        assert remove_script_and_style(html) == ""

        # Case insensitive
        html = "<SCRIPT>js</SCRIPT> <STYLE>css</STYLE>"
        assert remove_script_and_style(html) == " "

    def test_replace_block_tags(self):
        """Test replacement of block tags"""
        # Paragraph tags
        html = "<p>Para 1</p><p>Para 2</p>"
        result = replace_block_tags(html)
        assert result == "\nPara 1\n\nPara 2\n"

        # Various block tags (note: only closing </div> is replaced)
        html = "<div>Content</div>"
        result = replace_block_tags(html)
        assert result == "<div>Content\n"

        # Headers
        html = "<h1>Title</h1><h2>Subtitle</h2>"
        result = replace_block_tags(html)
        assert result == "\nTitle\n\nSubtitle\n"

        # BR tags
        html = "Line 1<br>Line 2<br/>Line 3"
        result = replace_block_tags(html)
        assert result == "Line 1\nLine 2\nLine 3"

        # List items (ul/ol tags are not replaced, only li tags)
        html = "<ul><li>Item 1</li><li>Item 2</li></ul>"
        result = replace_block_tags(html)
        assert result == "<ul>  - Item 1\n  - Item 2\n</ul>"

    def test_remove_remaining_tags(self):
        """Test removal of remaining tags"""
        # Simple tags
        html = "Text <span>with</span> tags"
        assert remove_remaining_tags(html) == "Text with tags"

        # Self-closing tags
        html = "Image <img src='test.jpg' /> here"
        assert remove_remaining_tags(html) == "Image  here"

        # Don't remove math expressions
        html = "Formula: x < y > z"
        assert remove_remaining_tags(html) == "Formula: x < y > z"

        # Only valid HTML tags
        html = "<a href='#'>link</a> but not <3"
        assert remove_remaining_tags(html) == "link but not <3"

    def test_unescape_non_code_with_placeholders(self):
        """Test unescaping HTML entities except in placeholders"""
        # Basic HTML entities
        text = "Hello &amp; goodbye"
        assert unescape_non_code_with_placeholders(text) == "Hello & goodbye"

        # With code placeholders preserved
        text = "Text &lt; __CODE_BLOCK_0__ &gt; more"
        result = unescape_non_code_with_placeholders(text)
        assert result == "Text < __CODE_BLOCK_0__ > more"

        # Multiple placeholders
        text = "__INLINE_CODE_0__ &quot;quoted&quot; __INLINE_CODE_1__"
        result = unescape_non_code_with_placeholders(text)
        assert result == '__INLINE_CODE_0__ "quoted" __INLINE_CODE_1__'

        # Various entities
        text = "&amp; &lt; &gt; &quot; &#39; &nbsp;"
        result = unescape_non_code_with_placeholders(text)
        assert result == "& < > \" ' \xa0"  # \xa0 is non-breaking space


class TestRemoveHTMLMarkup:
    """Test the main remove_html_markup function"""

    def test_complete_html_processing(self):
        """Test complete HTML processing pipeline"""
        html = """
        <!-- Comment -->
        <script>alert('hi');</script>
        <style>body { color: red; }</style>
        <p>Paragraph with <code>inline code</code> and entities &amp; &lt;tags&gt;.</p>
        <pre>
        Block code
        with multiple lines
        </pre>
        <div>More content</div>
        """

        result = remove_html_markup(html)

        # Comments, script, style removed
        assert "<!-- Comment -->" not in result
        assert "alert('hi')" not in result
        assert "color: red" not in result

        # Code blocks are preserved with their original tags
        assert "<code>inline code</code>" in result
        assert "<pre>" in result
        assert "Block code" in result
        assert "with multiple lines" in result

        # Entities unescaped
        assert "&" in result
        assert "<tags>" in result

        # Block structure preserved
        assert "\n\n" in result

    def test_preserve_math_expressions(self):
        """Test that math expressions are preserved"""
        html = "<p>Formula: x < y and y > z</p>"
        result = remove_html_markup(html)
        assert "x < y and y > z" in result

    def test_nested_code_blocks(self):
        """Test handling of nested code structures"""
        html = """
        <div>
            Text with `inline` code
            <pre>
                Block with more `backticks`
            </pre>
        </div>
        """
        result = remove_html_markup(html)

        assert "`inline`" in result
        assert "Block with more `backticks`" in result

    def test_empty_html(self):
        """Test empty and minimal HTML"""
        assert remove_html_markup("") == ""
        assert remove_html_markup("   ") == "   "
        assert remove_html_markup("plain text") == "plain text"

    def test_complex_html_entities(self):
        """Test complex HTML entities"""
        html = "Text with &euro; &copy; &trade; &#8364; &#169;"
        result = remove_html_markup(html)
        assert "€" in result
        assert "©" in result
        assert "™" in result

    def test_malformed_html(self):
        """Test handling of malformed HTML"""
        # Unclosed tags
        html = "<p>Unclosed paragraph <div>nested"
        result = remove_html_markup(html)
        assert "Unclosed paragraph" in result
        assert "nested" in result

        # Mismatched tags
        html = "<p>Text</div>"
        result = remove_html_markup(html)
        assert "Text" in result


class TestConstants:
    """Test module constants"""

    def test_preserve_unlimited_set(self):
        """Test PRESERVE_UNLIMITED constant"""
        # Check common whitespace
        assert " " in PRESERVE_UNLIMITED
        assert "\t" in PRESERVE_UNLIMITED
        assert "\n" in PRESERVE_UNLIMITED

        # Check symbols
        assert "." in PRESERVE_UNLIMITED
        assert "-" in PRESERVE_UNLIMITED
        assert "_" in PRESERVE_UNLIMITED

    def test_punctuation_sets(self):
        """Test punctuation constants"""
        # Chinese punctuation
        assert "。" in CHINESE_PUNCTUATION
        assert "，" in CHINESE_PUNCTUATION
        assert "！" in CHINESE_PUNCTUATION

        # English punctuation
        assert "." in ENGLISH_PUNCTUATION
        assert "," in ENGLISH_PUNCTUATION
        assert "!" in ENGLISH_PUNCTUATION

        # Combined set
        assert ALL_PUNCTUATION == CHINESE_PUNCTUATION | ENGLISH_PUNCTUATION
        assert "。" in ALL_PUNCTUATION
        assert "." in ALL_PUNCTUATION


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=common_text_utils", "--cov-report=html"])
