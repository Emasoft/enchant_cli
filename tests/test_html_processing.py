#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test suite for html_processing module.
"""

import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from enchant_book_manager.html_processing import (
    extract_code_blocks,
    extract_inline_code,
    remove_html_comments,
    remove_script_and_style,
    replace_block_tags,
    remove_remaining_tags,
    unescape_non_code_with_placeholders,
    remove_html_markup,
)


class TestExtractCodeBlocks:
    """Test the extract_code_blocks function."""

    def test_extract_pre_blocks(self):
        """Test extracting <pre> blocks."""
        html = "Text before <pre>code content</pre> text after"
        result, blocks = extract_code_blocks(html)

        assert result == "Text before __CODE_BLOCK_0__ text after"
        assert len(blocks) == 1
        assert blocks[0] == "<pre>code content</pre>"

    def test_extract_code_blocks_basic(self):
        """Test extracting <code> blocks."""
        html = "Text before <code>inline code</code> text after"
        result, blocks = extract_code_blocks(html)

        assert result == "Text before __CODE_BLOCK_0__ text after"
        assert len(blocks) == 1
        assert blocks[0] == "<code>inline code</code>"

    def test_extract_multiple_blocks(self):
        """Test extracting multiple code blocks."""
        html = "<pre>block1</pre> text <code>block2</code> more <pre>block3</pre>"
        result, blocks = extract_code_blocks(html)

        # <pre> blocks are extracted first, then <code> blocks
        assert result == "__CODE_BLOCK_0__ text __CODE_BLOCK_2__ more __CODE_BLOCK_1__"
        assert len(blocks) == 3
        assert blocks[0] == "<pre>block1</pre>"
        assert blocks[1] == "<pre>block3</pre>"
        assert blocks[2] == "<code>block2</code>"

    def test_extract_blocks_with_attributes(self):
        """Test extracting blocks with attributes."""
        html = '<pre class="language-python">def foo():</pre>'
        result, blocks = extract_code_blocks(html)

        assert result == "__CODE_BLOCK_0__"
        assert blocks[0] == '<pre class="language-python">def foo():</pre>'

    def test_extract_nested_content(self):
        """Test extracting blocks with nested content."""
        html = "<pre><code>nested code</code></pre>"
        result, blocks = extract_code_blocks(html)

        assert result == "__CODE_BLOCK_0__"
        assert blocks[0] == "<pre><code>nested code</code></pre>"

    def test_extract_multiline_blocks(self):
        """Test extracting multiline blocks."""
        html = """<pre>
line1
line2
line3
</pre>"""
        result, blocks = extract_code_blocks(html)

        assert "__CODE_BLOCK_0__" in result
        assert "line1" in blocks[0]
        assert "line2" in blocks[0]
        assert "line3" in blocks[0]

    def test_extract_empty_blocks(self):
        """Test extracting empty blocks."""
        html = "<pre></pre><code></code>"
        result, blocks = extract_code_blocks(html)

        assert result == "__CODE_BLOCK_0____CODE_BLOCK_1__"
        assert len(blocks) == 2
        assert blocks[0] == "<pre></pre>"
        assert blocks[1] == "<code></code>"

    def test_case_insensitive_extraction(self):
        """Test case-insensitive tag extraction."""
        html = "<PRE>upper</PRE> <Code>mixed</Code>"
        result, blocks = extract_code_blocks(html)

        assert result == "__CODE_BLOCK_0__ __CODE_BLOCK_1__"
        assert len(blocks) == 2


class TestExtractInlineCode:
    """Test the extract_inline_code function."""

    def test_extract_single_backtick(self):
        """Test extracting single backtick code."""
        text = "Use `code` here"
        result, snippets = extract_inline_code(text)

        assert result == "Use __INLINE_CODE_0__ here"
        assert len(snippets) == 1
        assert snippets[0] == "`code`"

    def test_extract_multiple_inline(self):
        """Test extracting multiple inline code snippets."""
        text = "Use `foo()` and `bar()` functions"
        result, snippets = extract_inline_code(text)

        assert result == "Use __INLINE_CODE_0__ and __INLINE_CODE_1__ functions"
        assert len(snippets) == 2
        assert snippets[0] == "`foo()`"
        assert snippets[1] == "`bar()`"

    def test_no_inline_code(self):
        """Test with no inline code."""
        text = "No code here"
        result, snippets = extract_inline_code(text)

        assert result == "No code here"
        assert len(snippets) == 0

    def test_empty_backticks(self):
        """Test that empty backticks are not extracted."""
        text = "Empty `` here"
        result, snippets = extract_inline_code(text)

        assert result == "Empty `` here"
        assert len(snippets) == 0

    def test_nested_backticks_not_supported(self):
        """Test that nested backticks are not supported."""
        text = "Code `with `nested` backticks`"
        result, snippets = extract_inline_code(text)

        # Extracts two separate inline code segments
        # The last backticks` gets consumed by the second match
        assert result == "Code __INLINE_CODE_0__nested__INLINE_CODE_1__"
        assert len(snippets) == 2
        assert snippets[0] == "`with `"
        assert snippets[1] == "` backticks`"


class TestRemoveHtmlComments:
    """Test the remove_html_comments function."""

    def test_remove_simple_comment(self):
        """Test removing a simple HTML comment."""
        html = "Before <!-- comment --> after"
        result = remove_html_comments(html)
        assert result == "Before  after"

    def test_remove_multiline_comment(self):
        """Test removing multiline comments."""
        html = """Before
<!-- This is a
multiline
comment -->
after"""
        result = remove_html_comments(html)
        assert "<!--" not in result
        assert "multiline" not in result
        assert "Before" in result
        assert "after" in result

    def test_remove_multiple_comments(self):
        """Test removing multiple comments."""
        html = "<!-- first -->Text<!-- second -->More"
        result = remove_html_comments(html)
        assert result == "TextMore"

    def test_no_comments(self):
        """Test with no comments."""
        html = "No comments here"
        result = remove_html_comments(html)
        assert result == "No comments here"

    def test_empty_comment(self):
        """Test removing empty comment."""
        html = "Text <!----> here"
        result = remove_html_comments(html)
        assert result == "Text  here"


class TestRemoveScriptAndStyle:
    """Test the remove_script_and_style function."""

    def test_remove_script_tags(self):
        """Test removing script tags."""
        html = 'Before <script>alert("test");</script> after'
        result = remove_script_and_style(html)
        assert result == "Before  after"

    def test_remove_style_tags(self):
        """Test removing style tags."""
        html = "Before <style>body { color: red; }</style> after"
        result = remove_script_and_style(html)
        assert result == "Before  after"

    def test_remove_both_tags(self):
        """Test removing both script and style tags."""
        html = "<script>js</script> Text <style>css</style>"
        result = remove_script_and_style(html)
        assert result == " Text "

    def test_multiline_content(self):
        """Test removing multiline script/style."""
        html = """<script>
function test() {
    return true;
}
</script>
<style>
.class {
    color: blue;
}
</style>"""
        result = remove_script_and_style(html)
        assert "function" not in result
        assert "color" not in result
        assert result.strip() == ""

    def test_case_insensitive_removal(self):
        """Test case-insensitive tag removal."""
        html = "<SCRIPT>js</SCRIPT> <Style>css</Style>"
        result = remove_script_and_style(html)
        assert result == " "

    def test_tags_with_attributes(self):
        """Test removing tags with attributes."""
        html = '<script src="app.js">content</script>'
        result = remove_script_and_style(html)
        assert "content" not in result
        assert "app.js" not in result


class TestReplaceBlockTags:
    """Test the replace_block_tags function."""

    def test_replace_paragraph_tags(self):
        """Test replacing paragraph tags."""
        html = "<p>First paragraph</p><p>Second paragraph</p>"
        result = replace_block_tags(html)
        assert "\nFirst paragraph\n\nSecond paragraph\n" == result

    def test_replace_br_tags(self):
        """Test replacing br tags."""
        html = "Line1<br>Line2<br/>Line3"
        result = replace_block_tags(html)
        assert "Line1\nLine2\nLine3" == result

    def test_replace_div_tags(self):
        """Test replacing div tags."""
        html = "<div>Content</div><div>More</div>"
        result = replace_block_tags(html)
        assert result == "<div>Content\n<div>More\n"

    def test_replace_list_items(self):
        """Test replacing list items."""
        html = "<li>Item 1</li><li>Item 2</li>"
        result = replace_block_tags(html)
        assert "  - Item 1\n  - Item 2\n" == result

    def test_replace_headers(self):
        """Test replacing header tags."""
        html = "<h1>Title</h1>Content<h2>Subtitle</h2>"
        result = replace_block_tags(html)
        assert "\nTitle\nContent\nSubtitle\n" == result

    def test_replace_table_elements(self):
        """Test replacing table elements."""
        html = "<tr><td>Cell1</td><td>Cell2</td></tr>"
        result = replace_block_tags(html)
        assert result == "<tr><td>Cell1\t<td>Cell2\t\n"

    def test_replace_blockquote(self):
        """Test replacing blockquote tags."""
        html = "<blockquote>Quote text</blockquote>"
        result = replace_block_tags(html)
        assert "\nQuote text\n" == result

    def test_removes_comments_and_scripts(self):
        """Test that comments and scripts are removed."""
        html = "<!-- comment --><script>js</script><p>Text</p>"
        result = replace_block_tags(html)
        assert "<!--" not in result
        assert "script" not in result
        assert "Text" in result


class TestRemoveRemainingTags:
    """Test the remove_remaining_tags function."""

    def test_remove_simple_tags(self):
        """Test removing simple HTML tags."""
        html = "Text with <b>bold</b> and <i>italic</i>"
        result = remove_remaining_tags(html)
        assert result == "Text with bold and italic"

    def test_preserve_math_expressions(self):
        """Test that math expressions are preserved."""
        html = "Formula: x < y and a > b"
        result = remove_remaining_tags(html)
        assert result == "Formula: x < y and a > b"

    def test_remove_tags_with_attributes(self):
        """Test removing tags with attributes."""
        html = '<span class="highlight">text</span>'
        result = remove_remaining_tags(html)
        assert result == "text"

    def test_remove_self_closing_tags(self):
        """Test removing self-closing tags."""
        html = 'Image: <img src="test.jpg" />'
        result = remove_remaining_tags(html)
        assert result == "Image: "

    def test_preserve_invalid_tags(self):
        """Test that invalid tags (math expressions) are preserved."""
        html = "Math: x < 5 and y > 3"
        result = remove_remaining_tags(html)
        assert result == "Math: x < 5 and y > 3"


class TestUnescapeNonCodeWithPlaceholders:
    """Test the unescape_non_code_with_placeholders function."""

    def test_unescape_html_entities(self):
        """Test unescaping HTML entities."""
        text = "Text with &lt;brackets&gt; and &amp;"
        result = unescape_non_code_with_placeholders(text)
        assert result == "Text with <brackets> and &"

    def test_preserve_code_placeholders(self):
        """Test that code placeholders are preserved."""
        text = "Text &lt;tag&gt; __CODE_BLOCK_0__ more &amp;"
        result = unescape_non_code_with_placeholders(text)
        assert result == "Text <tag> __CODE_BLOCK_0__ more &"

    def test_preserve_inline_placeholders(self):
        """Test that inline code placeholders are preserved."""
        text = "&quot;quoted&quot; __INLINE_CODE_0__ &apos;text&apos;"
        result = unescape_non_code_with_placeholders(text)
        assert result == "\"quoted\" __INLINE_CODE_0__ 'text'"

    def test_multiple_placeholders(self):
        """Test with multiple placeholders."""
        text = "__CODE_BLOCK_0__ &lt; __INLINE_CODE_0__ &gt; __CODE_BLOCK_1__"
        result = unescape_non_code_with_placeholders(text)
        assert result == "__CODE_BLOCK_0__ < __INLINE_CODE_0__ > __CODE_BLOCK_1__"

    def test_no_entities(self):
        """Test with no HTML entities."""
        text = "Plain text __CODE_BLOCK_0__ more"
        result = unescape_non_code_with_placeholders(text)
        assert result == text


class TestRemoveHtmlMarkup:
    """Test the main remove_html_markup function."""

    def test_complete_html_processing(self):
        """Test complete HTML processing pipeline."""
        html = """
        <!-- Comment -->
        <script>alert('test');</script>
        <style>body { color: red; }</style>
        <h1>Title</h1>
        <p>Paragraph with <b>bold</b> and <code>inline code</code>.</p>
        <pre>
        Block code
        with multiple lines
        </pre>
        <div>Content &lt;escaped&gt;</div>
        """

        result = remove_html_markup(html)

        # Comments, scripts, styles should be removed
        assert "<!--" not in result
        assert "alert" not in result
        assert "color: red" not in result

        # Text content should be preserved
        assert "Title" in result
        assert "Paragraph with bold" in result
        assert "<code>inline code</code>" in result  # Code blocks preserved
        assert "<pre>" in result  # Pre blocks preserved
        assert "Block code" in result
        assert "Content <escaped>" in result  # Entities unescaped

    def test_preserve_code_blocks(self):
        """Test that code blocks are preserved."""
        html = "<p>Text</p><pre><code>preserved code</code></pre><p>More</p>"
        result = remove_html_markup(html)

        assert "<pre><code>preserved code</code></pre>" in result
        assert "Text" in result
        assert "More" in result

    def test_preserve_inline_code(self):
        """Test that inline code is preserved."""
        html = "Use `command` to run"
        result = remove_html_markup(html)
        assert result == "Use `command` to run"

    def test_math_expressions_preserved(self):
        """Test that math expressions are preserved."""
        html = "<p>Formula: x < y and a > b</p>"
        result = remove_html_markup(html)
        assert "x < y" in result
        assert "a > b" in result

    def test_empty_html(self):
        """Test with empty HTML."""
        assert remove_html_markup("") == ""

    def test_plain_text(self):
        """Test with plain text (no HTML)."""
        text = "Just plain text"
        assert remove_html_markup(text) == text

    def test_complex_nested_structure(self):
        """Test with complex nested HTML."""
        html = """
        <div class="container">
            <h2>Section</h2>
            <ul>
                <li>Item with <code>code</code></li>
                <li>Item with <a href="#">link</a></li>
            </ul>
            <blockquote>
                Quote with &quot;entities&quot;
            </blockquote>
        </div>
        """

        result = remove_html_markup(html)

        assert "Section" in result
        assert "  - Item with <code>code</code>" in result
        assert "  - Item with link" in result
        assert 'Quote with "entities"' in result

    def test_whitespace_preservation(self):
        """Test that meaningful whitespace is preserved."""
        html = "<p>Text   with   spaces</p>"
        result = remove_html_markup(html)
        assert "Text   with   spaces" in result
