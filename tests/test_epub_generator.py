#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test suite for epub_generator module.
"""

import pytest
import tempfile
import zipfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, mock_open, call
import xml.etree.ElementTree as ET
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from enchant_book_manager.epub_generator import write_new_epub, extend_epub


class TestWriteNewEpub:
    """Test the write_new_epub function."""

    def setup_method(self):
        """Set up test fixtures."""
        self.chapters = [
            ("Chapter 1", "<p>Content of chapter 1</p>"),
            ("Chapter 2", "<p>Content of chapter 2</p>"),
        ]
        self.title = "Test Book"
        self.author = "Test Author"

    @patch("enchant_book_manager.epub_generator.TOC_ENHANCED", False)
    @patch("enchant_book_manager.epub_generator.uuid.uuid4")
    @patch("enchant_book_manager.epub_generator.build_container_xml")
    @patch("enchant_book_manager.epub_generator.build_style_css")
    @patch("enchant_book_manager.epub_generator.build_chap_xhtml")
    @patch("enchant_book_manager.epub_generator.build_content_opf")
    @patch("enchant_book_manager.epub_generator.build_toc_ncx")
    def test_write_new_epub_basic(
        self,
        mock_toc,
        mock_opf,
        mock_chap,
        mock_css,
        mock_container,
        mock_uuid,
    ):
        """Test basic EPUB creation without cover."""
        # Setup mocks
        mock_uuid.return_value = "test-uuid-1234"
        mock_container.return_value = '<?xml version="1.0"?><container/>'
        mock_css.return_value = "body { font-size: 14px; }"
        mock_chap.side_effect = ["<html>Chapter 1</html>", "<html>Chapter 2</html>"]
        mock_opf.return_value = '<?xml version="1.0"?><package/>'
        mock_toc.return_value = '<?xml version="1.0"?><ncx/>'

        # Create temporary output file
        with tempfile.NamedTemporaryFile(suffix=".epub", delete=False) as tmp_file:
            output_path = Path(tmp_file.name)

        try:
            # Execute
            write_new_epub(self.chapters, output_path, self.title, self.author, None)

            # Verify the EPUB file was created
            assert output_path.exists()

            # Verify content builders were called
            mock_container.assert_called_once()
            mock_css.assert_called_once_with(None)
            assert mock_chap.call_count == 2
            mock_chap.assert_any_call("Chapter 1", "<p>Content of chapter 1</p>")
            mock_chap.assert_any_call("Chapter 2", "<p>Content of chapter 2</p>")

            # Verify opf was called with correct parameters
            mock_opf.assert_called_once()
            opf_args = mock_opf.call_args[0]
            assert opf_args[0] == self.title
            assert opf_args[1] == self.author
            assert opf_args[4] == "test-uuid-1234"
            assert opf_args[5] is None  # No cover
            assert opf_args[6] == "en"  # Default language

            # Verify toc was called
            mock_toc.assert_called_once()
            toc_args = mock_toc.call_args[0]
            assert toc_args[0] == self.title
            assert toc_args[1] == self.author
            assert toc_args[3] == "test-uuid-1234"

            # Verify ZIP structure
            with zipfile.ZipFile(output_path, "r") as z:
                namelist = z.namelist()
                assert "mimetype" in namelist
                assert "META-INF/container.xml" in namelist
                assert "OEBPS/content.opf" in namelist
                assert "OEBPS/toc.ncx" in namelist
                assert "OEBPS/Styles/style.css" in namelist
                assert "OEBPS/Text/chapter1.xhtml" in namelist
                assert "OEBPS/Text/chapter2.xhtml" in namelist

                # Verify mimetype content
                assert z.read("mimetype").decode() == "application/epub+zip"

        finally:
            # Cleanup
            if output_path.exists():
                output_path.unlink()

    @patch("enchant_book_manager.epub_generator.TOC_ENHANCED", False)
    @patch("enchant_book_manager.epub_generator.uuid.uuid4")
    @patch("enchant_book_manager.epub_generator.build_container_xml")
    @patch("enchant_book_manager.epub_generator.build_style_css")
    @patch("enchant_book_manager.epub_generator.build_chap_xhtml")
    @patch("enchant_book_manager.epub_generator.build_content_opf")
    @patch("enchant_book_manager.epub_generator.build_toc_ncx")
    @patch("enchant_book_manager.epub_generator.build_cover_xhtml")
    @patch("enchant_book_manager.epub_generator.shutil.copy2")
    def test_write_new_epub_with_cover(
        self,
        mock_copy,
        mock_cover_xhtml,
        mock_toc,
        mock_opf,
        mock_chap,
        mock_css,
        mock_container,
        mock_uuid,
    ):
        """Test EPUB creation with cover image."""
        # Setup mocks
        mock_uuid.return_value = "test-uuid-1234"
        mock_container.return_value = '<?xml version="1.0"?><container/>'
        mock_css.return_value = "css"
        mock_chap.return_value = "<html>Chapter</html>"
        mock_opf.return_value = '<?xml version="1.0"?><package/>'
        mock_toc.return_value = '<?xml version="1.0"?><ncx/>'
        mock_cover_xhtml.return_value = "<html>Cover</html>"

        # Create temporary cover image
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as cover_file:
            cover_path = Path(cover_file.name)
            cover_file.write(b"fake image data")

        # Create temporary output file
        with tempfile.NamedTemporaryFile(suffix=".epub", delete=False) as tmp_file:
            output_path = Path(tmp_file.name)

        try:
            # Execute
            write_new_epub(
                self.chapters[:1],
                output_path,
                self.title,
                self.author,
                cover_path,
            )

            # Verify cover was processed
            mock_copy.assert_called_once()
            copy_args = mock_copy.call_args[0]
            assert copy_args[0] == cover_path

            # Verify cover XHTML was built
            mock_cover_xhtml.assert_called_once_with(f"Images/{cover_path.name}")

            # Verify opf was called with cover_id
            mock_opf.assert_called_once()
            opf_args = mock_opf.call_args[0]
            assert opf_args[5] == "cover-img"  # cover_id

            # Verify ZIP contains cover files
            with zipfile.ZipFile(output_path, "r") as z:
                namelist = z.namelist()
                assert "OEBPS/Text/cover.xhtml" in namelist

        finally:
            # Cleanup
            if output_path.exists():
                output_path.unlink()
            if cover_path.exists():
                cover_path.unlink()

    @patch("enchant_book_manager.epub_generator.TOC_ENHANCED", False)
    @patch("enchant_book_manager.epub_generator.uuid.uuid4")
    @patch("enchant_book_manager.epub_generator.build_container_xml")
    @patch("enchant_book_manager.epub_generator.build_style_css")
    @patch("enchant_book_manager.epub_generator.build_chap_xhtml")
    @patch("enchant_book_manager.epub_generator.build_content_opf")
    @patch("enchant_book_manager.epub_generator.build_toc_ncx")
    def test_write_new_epub_with_custom_options(
        self,
        mock_toc,
        mock_opf,
        mock_chap,
        mock_css,
        mock_container,
        mock_uuid,
    ):
        """Test EPUB creation with custom language, CSS, and metadata."""
        # Setup custom options
        custom_css = "body { color: blue; }"
        language = "zh"
        metadata = {
            "publisher": "Test Publisher",
            "description": "Test Description",
        }

        # Setup mocks
        mock_uuid.return_value = "test-uuid"
        mock_container.return_value = "<container/>"
        mock_css.return_value = "custom css"
        mock_chap.return_value = "<html/>"
        mock_opf.return_value = "<package/>"
        mock_toc.return_value = "<ncx/>"

        with tempfile.NamedTemporaryFile(suffix=".epub", delete=False) as tmp_file:
            output_path = Path(tmp_file.name)

        try:
            # Execute
            write_new_epub(
                self.chapters[:1],
                output_path,
                self.title,
                self.author,
                None,
                language=language,
                custom_css=custom_css,
                metadata=metadata,
            )

            # Verify custom CSS was passed
            mock_css.assert_called_once_with(custom_css)

            # Verify language and metadata were passed
            mock_opf.assert_called_once()
            opf_args = mock_opf.call_args[0]
            assert opf_args[6] == language
            assert opf_args[7] == metadata

        finally:
            if output_path.exists():
                output_path.unlink()

    @patch("enchant_book_manager.epub_generator.TOC_ENHANCED", True)
    @patch("enchant_book_manager.epub_generator.build_enhanced_toc_ncx")
    @patch("enchant_book_manager.epub_generator.uuid.uuid4")
    @patch("enchant_book_manager.epub_generator.build_container_xml")
    @patch("enchant_book_manager.epub_generator.build_style_css")
    @patch("enchant_book_manager.epub_generator.build_chap_xhtml")
    @patch("enchant_book_manager.epub_generator.build_content_opf")
    def test_write_new_epub_with_enhanced_toc(
        self,
        mock_opf,
        mock_chap,
        mock_css,
        mock_container,
        mock_uuid,
        mock_enhanced_toc,
    ):
        """Test EPUB creation with enhanced TOC builder."""
        # Setup mocks
        mock_uuid.return_value = "test-uuid"
        mock_container.return_value = "<container/>"
        mock_css.return_value = "css"
        mock_chap.return_value = "<html/>"
        mock_opf.return_value = "<package/>"
        mock_enhanced_toc.return_value = "<ncx>Enhanced</ncx>"

        with tempfile.NamedTemporaryFile(suffix=".epub", delete=False) as tmp_file:
            output_path = Path(tmp_file.name)

        try:
            # Execute
            write_new_epub(
                self.chapters,
                output_path,
                self.title,
                self.author,
                None,
            )

            # Verify enhanced TOC was used
            mock_enhanced_toc.assert_called_once_with(
                self.chapters,
                self.title,
                self.author,
                "test-uuid",
                hierarchical=True,
            )

        finally:
            if output_path.exists():
                output_path.unlink()


class TestExtendEpub:
    """Test the extend_epub function."""

    def setup_method(self):
        """Set up test fixtures."""
        self.new_chapters = [
            ("New Chapter 1", "<p>New content 1</p>"),
            ("New Chapter 2", "<p>New content 2</p>"),
        ]

    def create_test_epub(self, path):
        """Create a minimal test EPUB file."""
        with zipfile.ZipFile(path, "w") as z:
            # Add mimetype
            z.writestr("mimetype", "application/epub+zip", zipfile.ZIP_STORED)

            # Add container.xml
            z.writestr(
                "META-INF/container.xml",
                """<?xml version="1.0"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>""",
            )

            # Add content.opf
            z.writestr(
                "OEBPS/content.opf",
                """<?xml version="1.0"?>
<package xmlns="http://www.idpf.org/2007/opf">
  <manifest>
    <item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>
    <item id="chap1" href="Text/chapter1.xhtml" media-type="application/xhtml+xml"/>
  </manifest>
  <spine>
    <itemref idref="chap1"/>
  </spine>
</package>""",
            )

            # Add toc.ncx
            z.writestr(
                "OEBPS/toc.ncx",
                """<?xml version="1.0"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/">
  <navMap>
    <navPoint id="nav1" playOrder="1">
      <navLabel><text>Chapter 1</text></navLabel>
      <content src="Text/chapter1.xhtml"/>
    </navPoint>
  </navMap>
</ncx>""",
            )

            # Add chapter
            z.writestr("OEBPS/Text/chapter1.xhtml", "<html><body>Chapter 1</body></html>")

    @patch("enchant_book_manager.epub_generator.build_chap_xhtml")
    def test_extend_epub_success(self, mock_build_chap):
        """Test successful EPUB extension."""
        # Setup mock
        mock_build_chap.side_effect = [
            "<html>New Chapter 1</html>",
            "<html>New Chapter 2</html>",
        ]

        with tempfile.NamedTemporaryFile(suffix=".epub", delete=False) as tmp_file:
            epub_path = Path(tmp_file.name)

        try:
            # Create test EPUB
            self.create_test_epub(epub_path)

            # Execute
            extend_epub(epub_path, self.new_chapters)

            # Verify the EPUB still exists
            assert epub_path.exists()

            # Verify new chapters were built
            assert mock_build_chap.call_count == 2
            mock_build_chap.assert_any_call("New Chapter 1", "<p>New content 1</p>")
            mock_build_chap.assert_any_call("New Chapter 2", "<p>New content 2</p>")

            # Verify EPUB contains new chapters
            with zipfile.ZipFile(epub_path, "r") as z:
                namelist = z.namelist()
                assert "OEBPS/Text/chapter2.xhtml" in namelist
                assert "OEBPS/Text/chapter3.xhtml" in namelist

                # Verify content.opf was updated
                content_opf = z.read("OEBPS/content.opf").decode("utf-8")
                assert "chap2" in content_opf
                assert "chap3" in content_opf

                # Verify toc.ncx was updated
                toc_ncx = z.read("OEBPS/toc.ncx").decode("utf-8")
                assert "nav2" in toc_ncx
                assert "nav3" in toc_ncx

        finally:
            if epub_path.exists():
                epub_path.unlink()

    def test_extend_epub_invalid_structure(self):
        """Test extending EPUB with invalid structure."""
        with tempfile.NamedTemporaryFile(suffix=".epub", delete=False) as tmp_file:
            epub_path = Path(tmp_file.name)

        try:
            # Create invalid EPUB (missing navMap)
            with zipfile.ZipFile(epub_path, "w") as z:
                z.writestr("mimetype", "application/epub+zip")
                z.writestr(
                    "OEBPS/content.opf",
                    """<?xml version="1.0"?>
<package xmlns="http://www.idpf.org/2007/opf">
  <manifest/>
  <spine/>
</package>""",
                )
                z.writestr(
                    "OEBPS/toc.ncx",
                    """<?xml version="1.0"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/">
</ncx>""",
                )

            # Execute and expect ValueError
            with pytest.raises(ValueError, match="Invalid EPUB structure"):
                extend_epub(epub_path, self.new_chapters)

        finally:
            if epub_path.exists():
                epub_path.unlink()

    @patch("enchant_book_manager.epub_generator.build_chap_xhtml")
    def test_extend_epub_no_existing_chapters(self, mock_build_chap):
        """Test extending EPUB with no existing chapters."""
        # Setup mock
        mock_build_chap.return_value = "<html>New Chapter</html>"

        with tempfile.NamedTemporaryFile(suffix=".epub", delete=False) as tmp_file:
            epub_path = Path(tmp_file.name)

        try:
            # Create EPUB without chapters
            with zipfile.ZipFile(epub_path, "w") as z:
                z.writestr("mimetype", "application/epub+zip")
                # Create Text directory by adding a dummy file
                z.writestr("OEBPS/Text/.gitkeep", "")
                z.writestr(
                    "OEBPS/content.opf",
                    """<?xml version="1.0"?>
<package xmlns="http://www.idpf.org/2007/opf">
  <manifest/>
  <spine/>
</package>""",
                )
                z.writestr(
                    "OEBPS/toc.ncx",
                    """<?xml version="1.0"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/">
  <navMap/>
</ncx>""",
                )

            # Execute
            extend_epub(epub_path, self.new_chapters[:1])

            # Verify the first new chapter starts at index 1
            with zipfile.ZipFile(epub_path, "r") as z:
                namelist = z.namelist()
                assert "OEBPS/Text/chapter1.xhtml" in namelist

        finally:
            if epub_path.exists():
                epub_path.unlink()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
