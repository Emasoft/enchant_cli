#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test suite for EPUB customization features (CSS, language, metadata).
"""

import pytest
from pathlib import Path
import tempfile
import shutil
import zipfile
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from make_epub import create_epub_from_txt_file


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files"""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


@pytest.fixture
def test_file(temp_dir):
    """Create a test text file with sample content"""
    test_file = temp_dir / "test_book.txt"
    test_file.write_text("Chapter 1\nTest content\n\nChapter 2\nMore content")
    return test_file


@pytest.fixture
def sample_metadata():
    """Sample metadata for testing"""
    return {
        "publisher": "Test Publisher",
        "description": "Test description",
        "series": "Test Series",
        "series_index": 1,
    }


class TestEPUBCustomization:
    """Test EPUB customization features"""

    def test_custom_css_support(self, temp_dir, test_file):
        """Test that custom CSS can be provided and used"""
        output_path = temp_dir / "test.epub"
        custom_css = """
        body { font-family: 'Noto Sans', sans-serif; }
        h1 { color: #333; }
        p { line-height: 1.6; }
        """

        success, issues = create_epub_from_txt_file(
            txt_file_path=test_file,
            output_path=output_path,
            title="Test Book",
            author="Test Author",
            custom_css=custom_css,
        )

        assert success
        assert output_path.exists()

        # Verify CSS was applied
        with zipfile.ZipFile(output_path, "r") as z:
            css_content = z.read("OEBPS/Styles/style.css").decode("utf-8")
            assert "Noto Sans" in css_content
            assert "color: #333" in css_content
            assert "line-height: 1.6" in css_content

    def test_language_configuration(self, temp_dir, test_file):
        """Test that language can be configured"""
        output_path = temp_dir / "test.epub"

        success, issues = create_epub_from_txt_file(
            txt_file_path=test_file,
            output_path=output_path,
            title="Test Book",
            author="Test Author",
            language="zh",
        )

        assert success
        assert output_path.exists()

        # Verify language in OPF
        with zipfile.ZipFile(output_path, "r") as z:
            opf_content = z.read("OEBPS/content.opf").decode("utf-8")
            assert "<dc:language>zh</dc:language>" in opf_content

    def test_metadata_support(self, temp_dir, test_file, sample_metadata):
        """Test that additional metadata can be added"""
        output_path = temp_dir / "test.epub"

        success, issues = create_epub_from_txt_file(
            txt_file_path=test_file,
            output_path=output_path,
            title="Test Book",
            author="Test Author",
            metadata=sample_metadata,
        )

        assert success
        assert output_path.exists()

        # Verify metadata in OPF
        with zipfile.ZipFile(output_path, "r") as z:
            opf_content = z.read("OEBPS/content.opf").decode("utf-8")
            assert "Test Publisher" in opf_content
            assert "Test description" in opf_content
            assert "Test Series" in opf_content
            assert "calibre:series_index' content='1'" in opf_content

    def test_default_css_when_none_provided(self, temp_dir, test_file):
        """Test that default CSS is used when custom CSS is not provided"""
        output_path = temp_dir / "test.epub"

        success, issues = create_epub_from_txt_file(
            txt_file_path=test_file,
            output_path=output_path,
            title="Test Book",
            author="Test Author",
        )

        assert success

        # Verify default CSS was applied
        with zipfile.ZipFile(output_path, "r") as z:
            css_content = z.read("OEBPS/Styles/style.css").decode("utf-8")
            # Check for default CSS patterns
            assert "body{font-family:serif" in css_content
            assert "line-height:1.4" in css_content
            assert "text-indent:1.5em" in css_content

    def test_multiple_customizations_together(self, temp_dir, test_file):
        """Test combining language, CSS, and metadata customizations"""
        output_path = temp_dir / "test.epub"

        custom_css = "body { font-family: 'Source Han Sans', sans-serif; }"
        metadata = {
            "publisher": "EnChANT Publishing",
            "description": "A translated novel",
            "original_title": "测试小说",
            "original_author": "测试作者",
        }

        success, issues = create_epub_from_txt_file(
            txt_file_path=test_file,
            output_path=output_path,
            title="Test Novel",
            author="Test Author",
            language="en",
            custom_css=custom_css,
            metadata=metadata,
        )

        assert success

        with zipfile.ZipFile(output_path, "r") as z:
            # Check CSS
            css_content = z.read("OEBPS/Styles/style.css").decode("utf-8")
            assert "Source Han Sans" in css_content

            # Check OPF for language and metadata
            opf_content = z.read("OEBPS/content.opf").decode("utf-8")
            assert "<dc:language>en</dc:language>" in opf_content
            assert "EnChANT Publishing" in opf_content
            assert "A translated novel" in opf_content
