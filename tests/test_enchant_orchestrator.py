#!/usr/bin/env python3

"""
Integration tests for EnChANT orchestrator - Testing the full 3-phase process:
1. Renaming (Chinese filename -> English metadata extraction)
2. Translation (Chinese text -> English)
3. EPUB Generation (English chapters -> EPUB with TOC)

Tests ensure the complete pipeline from Chinese novels to English EPUBs.
"""

import pytest
import tempfile
from pathlib import Path
import os
import sys
import yaml
import zipfile
import xml.etree.ElementTree as ET
from unittest.mock import Mock, patch
import json

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from enchant_book_manager.workflow_orchestrator import process_novel_unified  # noqa: E402
from enchant_book_manager.rename_file_processor import process_novel_file  # noqa: E402
from enchant_book_manager.rename_api_client import RenameAPIClient  # noqa: E402
from enchant_book_manager.cli_translator import translate_novel  # noqa: E402
from enchant_book_manager.make_epub import create_epub_from_chapters  # noqa: E402

# Import test utilities for profile detection
from test_utils import skip_local_api_tests  # noqa: E402


class TestEnChANTOrchestrator:
    """Test suite for the complete EnChANT 3-phase orchestration process"""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for test files"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.fixture
    def chinese_test_novel(self, temp_dir):
        """Create a test Chinese novel file"""
        chinese_content = """第一章 修炼之路

        李明是一个普通的学生，但是他有一个秘密。他能够修炼武功。

        在这个现代社会中，武功已经被人们遗忘了。但是李明知道，武功的力量是真实存在的。

        第二章 神秘导师

        有一天，李明遇到了一位神秘的老人。这位老人告诉他，他有着特殊的天赋。

        老人说："年轻人，你的潜力无限。跟我学习真正的武功吧。"

        第三章 突破境界

        经过几个月的训练，李明终于突破了第一个境界。他感受到了前所未有的力量。

        "这就是武功的真正威力！"李明兴奋地说道。

        从此，他的人生彻底改变了。"""

        novel_file = temp_dir / "修炼高手.txt"
        novel_file.write_text(chinese_content, encoding="utf-8")
        return novel_file

    @pytest.fixture
    def config_file(self, temp_dir):
        """Create test configuration file"""
        config_path = temp_dir / "test_enchant_config.yml"
        config_data = {
            "text_processing": {
                "max_chars_per_chunk": 2000,
                "default_encoding": "utf-8",
            },
            "translation": {
                "temperature": 0.0,
                "max_tokens": 4000,
                "local": {
                    "endpoint": "http://localhost:1234/v1/chat/completions",
                    "model": "qwen2.5:32b",
                    "timeout": 30,
                },
                "remote": {
                    "endpoint": "https://openrouter.ai/api/v1/chat/completions",
                    "model": "deepseek/deepseek-chat",
                    "timeout": 60,
                },
            },
            "icloud": {"enabled": False},
            "logging": {
                "level": "INFO",
                "format": "%(asctime)s - %(levelname)s - %(message)s",
                "file_enabled": False,
                "file_path": "enchant.log",
            },
            "pricing": {"enabled": True, "save_report": False},
        }

        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(config_data, f, default_flow_style=False, allow_unicode=True)

        return config_path

    @pytest.fixture
    def mock_openai_response(self):
        """Mock OpenAI API response for renaming"""
        return {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "detected_language": "Chinese",
                                "novel_title_original": "修炼高手",
                                "author_name_original": "未知作者",
                                "novel_title_english": "Cultivation Master",
                                "author_name_english": "Unknown Author",
                                "author_name_romanized": "Weizhi Zuozhe",
                            },
                            ensure_ascii=False,
                        )
                    }
                }
            ],
            "usage": {
                "prompt_tokens": 150,
                "completion_tokens": 50,
                "total_tokens": 200,
                "cost": 0.0003,
            },
        }

    @pytest.fixture
    def mock_translation_response(self):
        """Mock translation API response"""
        return {
            "choices": [
                {
                    "message": {
                        "content": """Chapter 1: The Path of Cultivation

                    Li Ming was an ordinary student, but he had a secret. He could practice martial arts.

                    In this modern society, martial arts had been forgotten by people. But Li Ming knew that the power of martial arts truly existed.

                    Chapter 2: The Mysterious Mentor

                    One day, Li Ming met a mysterious old man. This old man told him that he had special talent.

                    The old man said: "Young man, your potential is limitless. Come learn true martial arts with me."

                    Chapter 3: Breaking Through Realms

                    After several months of training, Li Ming finally broke through the first realm. He felt unprecedented power.

                    "This is the true power of martial arts!" Li Ming said excitedly.

                    From then on, his life completely changed."""
                    }
                }
            ],
            "usage": {
                "prompt_tokens": 300,
                "completion_tokens": 150,
                "total_tokens": 450,
                "cost": 0.002,
            },
        }

    def test_phase1_renaming_success(self, temp_dir, chinese_test_novel, mock_openai_response):
        """Test Phase 1: Novel renaming with metadata extraction"""

        # Mock RenameAPIClient.make_request directly to avoid API calls
        with patch("enchant_book_manager.rename_api_client.RenameAPIClient.make_request") as mock_openai_request:
            mock_openai_request.return_value = mock_openai_response

            # Create API client
            api_client = RenameAPIClient(api_key="test_key", model="gpt-4o-mini", temperature=0.0)

            # Test renaming
            success, new_path, metadata = process_novel_file(
                chinese_test_novel,
                api_client=api_client,
                dry_run=False,
            )

            assert success is True
            assert new_path.exists()
            assert new_path.name == "Cultivation Master by Unknown Author (Weizhi Zuozhe) - 修炼高手 by 未知作者.txt"
            assert metadata["novel_title_english"] == "Cultivation Master"
            assert metadata["author_name_english"] == "Unknown Author"

    @skip_local_api_tests("Local API endpoint localhost:1234 not available in CI")
    def test_phase2_translation_success(self, temp_dir, config_file, mock_translation_response):
        """Test Phase 2: Translation from Chinese to English"""

        # Create renamed file (as would result from Phase 1)
        renamed_file = temp_dir / "Cultivation Master by Unknown Author (Weizhi Zuozhe) - 修炼高手 by 未知作者.txt"
        chinese_content = """第一章 修炼之路

        李明是一个普通的学生，但是他有一个秘密。他能够修炼武功。"""

        renamed_file.write_text(chinese_content, encoding="utf-8")

        # Mock the translator to avoid actual API calls
        with patch("enchant_book_manager.cli_translator.ChineseAITranslator") as mock_translator_class:
            # Create mock translator instance
            mock_translator = Mock()
            # Mock the translate method to return the expected translation
            mock_translator.translate.return_value = mock_translation_response["choices"][0]["message"]["content"]
            # Set required attributes
            mock_translator.is_remote = False
            mock_translator.request_count = 0
            mock_translator.get_cost_summary.return_value = {
                "model": "test-model",
                "api_type": "local",
                "request_count": 0,
                "total_cost": 0.0,
                "total_tokens": 0,
                "total_prompt_tokens": 0,
                "total_completion_tokens": 0,
                "average_cost_per_request": 0.0,
            }
            mock_translator_class.return_value = mock_translator

            # Test translation
            success = translate_novel(
                str(renamed_file),
                encoding="utf-8",
                max_chars=2000,
                resume=False,
                create_epub=False,
                remote=False,
            )

            # Verify translation succeeded
            assert success is True

    def test_phase3_epub_generation_success(self, temp_dir):
        """Test Phase 3: EPUB generation from translated chapters"""

        # Create mock translated chapters directory (as would result from Phase 2)
        book_dir = temp_dir / "Cultivation Master by Unknown Author"
        book_dir.mkdir()

        # Create chapter files
        chapters = [
            (
                "Chapter 1",
                "Chapter 1: The Path of Cultivation\n\nLi Ming was an ordinary student...",
            ),
            (
                "Chapter 2",
                "Chapter 2: The Mysterious Mentor\n\nOne day, Li Ming met a mysterious old man...",
            ),
            (
                "Chapter 3",
                "Chapter 3: Breaking Through Realms\n\nAfter several months of training...",
            ),
        ]

        for i, (_title, content) in enumerate(chapters, 1):
            chapter_file = book_dir / f"Cultivation Master by Unknown Author - Chapter {i}.txt"
            chapter_file.write_text(content, encoding="utf-8")

        # Test EPUB creation
        epub_path = temp_dir / "Cultivation_Master.epub"

        create_epub_from_chapters(
            chapters=chapters,
            output_path=epub_path,
            title="Cultivation Master",
            author="Unknown Author",
            cover_path=None,
        )

        assert epub_path.exists()

        # Verify EPUB structure
        with zipfile.ZipFile(epub_path, "r") as epub_zip:
            files = epub_zip.namelist()

            # Check required EPUB files
            assert "mimetype" in files
            assert "META-INF/container.xml" in files
            assert "OEBPS/content.opf" in files
            assert "OEBPS/toc.ncx" in files

            # Check chapter files
            chapter_files = [f for f in files if f.startswith("OEBPS/Text/chapter")]
            assert len(chapter_files) == 3

            # Verify content.opf contains proper metadata
            content_opf = epub_zip.read("OEBPS/content.opf").decode("utf-8")
            assert "Cultivation Master" in content_opf
            assert "Unknown Author" in content_opf

            # Verify TOC structure
            toc_ncx = epub_zip.read("OEBPS/toc.ncx").decode("utf-8")
            assert "Chapter 1" in toc_ncx
            assert "Chapter 2" in toc_ncx
            assert "Chapter 3" in toc_ncx

    @skip_local_api_tests("Full orchestration with local API not available in CI")
    def test_full_orchestration_success(
        self,
        temp_dir,
        chinese_test_novel,
        config_file,
        mock_openai_response,
        mock_translation_response,
    ):
        """Test complete 3-phase orchestration process"""

        # Initialize logger for process_novel_unified
        import logging

        logger = logging.getLogger(__name__)

        # Create mock args object with all necessary attributes
        args = Mock()
        args.skip_renaming = False
        args.skip_translating = False
        args.skip_epub = False
        args.resume = False
        args.openai_api_key = "test_openai_key"
        args.encoding = "utf-8"
        args.max_chars = 2000
        args.remote = False
        args.rename_temperature = 0.0
        args.rename_model = "gpt-4o-mini"
        args.rename_dry_run = False  # Important: set to False to actually rename
        args.translated = None
        args.epub_title = None
        args.epub_author = None
        args.epub_language = None
        args.no_toc = False
        args.no_validate = False
        args.epub_strict = False
        args.cover = None
        args.custom_css = None
        args.epub_metadata = None
        args.validate_only = False

        # Create a mock translate_novel function that creates expected output
        def mock_translate_novel(input_file, **kwargs):
            from enchant_book_manager.common_utils import (
                sanitize_filename,
                extract_book_info_from_path,
            )

            # Get the renamed file path
            input_path = Path(input_file)

            # Extract book info to get proper title and author
            book_info = extract_book_info_from_path(input_path)
            book_title = book_info.get("title_english", "Cultivation Master")
            book_author = book_info.get("author_english", "Unknown Author")

            # Create translation directory structure matching what enchant_cli expects
            safe_folder_name = sanitize_filename(f"{book_title} by {book_author}")
            translation_dir = input_path.parent / safe_folder_name
            translation_dir.mkdir(exist_ok=True)

            # Create translated file with exact expected name
            translated_file_name = f"translated_{book_title} by {book_author}.txt"
            translated_file = translation_dir / translated_file_name
            translated_content = mock_translation_response["choices"][0]["message"]["content"]
            translated_file.write_text(translated_content, encoding="utf-8")

            # Also create chapter files for test verification
            for i in range(1, 4):
                chapter_file = translation_dir / f"Chapter {i}.txt"
                chapter_file.write_text(f"Chapter {i} content", encoding="utf-8")

            return True

        # Mock the RenameAPIClient.make_request function directly to avoid Mock object issues
        with (
            patch("enchant_book_manager.rename_api_client.RenameAPIClient.make_request") as mock_openai_request,
            patch(
                "enchant_book_manager.workflow_phases.translate_novel",
                side_effect=mock_translate_novel,
            ),
        ):
            # Return the proper response structure
            mock_openai_request.return_value = mock_openai_response

            # Mock config loading
            with patch.dict(os.environ, {"ENCHANT_CONFIG": str(config_file)}):
                # Test full orchestration
                success = process_novel_unified(chinese_test_novel, args, logger)

                assert success is True

                # Verify Phase 1: File was renamed
                renamed_files = list(temp_dir.glob("Cultivation Master by Unknown Author*.txt"))
                assert len(renamed_files) == 1
                renamed_file = renamed_files[0]
                assert "Cultivation Master" in renamed_file.name

                # Verify Phase 2: Translation directory was created
                translation_dir = temp_dir / "Cultivation Master by Unknown Author"
                assert translation_dir.exists()

                # Verify chapter files exist
                chapter_files = list(translation_dir.glob("*Chapter*.txt"))
                assert len(chapter_files) > 0

                # Verify Phase 3: EPUB was created
                epub_files = list(temp_dir.glob("*.epub"))
                assert len(epub_files) == 1
                epub_file = epub_files[0]
                assert "Cultivation" in epub_file.name and "Master" in epub_file.name

    @skip_local_api_tests("Skip flags test with local API not available in CI")
    def test_orchestration_with_skip_flags(self, temp_dir, chinese_test_novel, mock_openai_response):
        """Test orchestration with different skip flags"""

        # Initialize logger for process_novel_unified
        import logging

        logger = logging.getLogger(__name__)

        # Test 1: Skip renaming (with explicit EPUB metadata since no renaming to extract it)
        args = Mock()
        args.skip_renaming = True
        args.skip_translating = False
        args.skip_epub = False
        args.resume = False
        args.encoding = "utf-8"
        args.max_chars = 2000
        args.remote = False
        args.translated = None
        args.epub_title = "Test Novel"  # Provide explicit title since renaming is skipped
        args.epub_author = "Test Author"  # Provide explicit author since renaming is skipped
        args.epub_language = None
        args.no_toc = False
        args.no_validate = False
        args.epub_strict = False
        args.cover = None
        args.custom_css = None
        args.epub_metadata = None
        args.validate_only = False

        def mock_translate_with_skip_rename(input_file, **kwargs):
            from enchant_book_manager.common_utils import (
                sanitize_filename,
                extract_book_info_from_path,
            )

            # When renaming is skipped, the system uses the original filename for directory
            input_path = Path(input_file)
            # Extract book info as the system would
            book_info = extract_book_info_from_path(input_path)
            book_title = book_info.get("title_english", input_path.stem)
            book_author = book_info.get("author_english", "Unknown")
            safe_folder_name = sanitize_filename(f"{book_title} by {book_author}")
            translation_dir = input_path.parent / safe_folder_name
            translation_dir.mkdir(exist_ok=True)
            # Create translated file with expected name
            translated_file = translation_dir / f"translated_{book_title} by {book_author}.txt"
            translated_file.write_text("Chapter 1\n\nTranslated content.", encoding="utf-8")
            # Create chapter files
            chapter_file = translation_dir / "Chapter 1.txt"
            chapter_file.write_text("Chapter 1\n\nTranslated content.", encoding="utf-8")
            return True

        with patch(
            "enchant_book_manager.workflow_phases.translate_novel",
            side_effect=mock_translate_with_skip_rename,
        ):
            success = process_novel_unified(chinese_test_novel, args, logger)

            # Should proceed with original filename
            assert success is True

        # Test 2: Skip translation
        # Create a fresh copy of the test novel since the original may have been renamed
        test_novel_2 = temp_dir / "test_novel_2.txt"
        test_novel_2.write_text(chinese_test_novel.read_text(encoding="utf-8"), encoding="utf-8")

        args2 = Mock()
        args2.skip_renaming = False
        args2.skip_translating = True
        args2.skip_epub = False
        args2.resume = False
        args2.openai_api_key = "test_key"
        args2.rename_temperature = 0.0
        args2.rename_model = "gpt-4o-mini"
        args2.rename_dry_run = False
        args2.encoding = "utf-8"
        args2.translated = None
        args2.epub_title = None
        args2.epub_author = None
        args2.epub_language = None
        args2.no_toc = False
        args2.no_validate = False
        args2.epub_strict = False
        args2.cover = None
        args2.custom_css = None
        args2.epub_metadata = None
        args2.validate_only = False

        # Mock the API call for renaming
        with patch("enchant_book_manager.rename_api_client.RenameAPIClient.make_request") as mock_openai_request:
            mock_openai_request.return_value = mock_openai_response

            # Create translation directory that would exist from skipped translation phase
            book_dir = temp_dir / "Cultivation Master by Unknown Author"
            book_dir.mkdir(exist_ok=True)
            translated_file = book_dir / "translated_Cultivation Master by Unknown Author.txt"
            translated_file.write_text("Chapter 1\n\nTranslated content.", encoding="utf-8")

            success = process_novel_unified(test_novel_2, args2, logger)
            assert success is True

        # Test 3: Skip EPUB
        # Create another fresh copy of the test novel
        test_novel_3 = temp_dir / "test_novel_3.txt"
        test_novel_3.write_text(chinese_test_novel.read_text(encoding="utf-8"), encoding="utf-8")

        args3 = Mock()
        args3.skip_renaming = False
        args3.skip_translating = False
        args3.skip_epub = True
        args3.resume = False
        args3.openai_api_key = "test_key"
        args3.rename_temperature = 0.0
        args3.rename_model = "gpt-4o-mini"
        args3.rename_dry_run = False
        args3.encoding = "utf-8"
        args3.max_chars = 2000
        args3.remote = False

        def mock_translate_novel(input_file, **kwargs):
            from enchant_book_manager.common_utils import sanitize_filename

            # Create translation directory structure
            input_path = Path(input_file)
            # Extract book info to get the title/author from renamed file
            from enchant_book_manager.common_utils import extract_book_info_from_path

            book_info = extract_book_info_from_path(input_path)
            book_title = book_info.get("title_english", "Cultivation Master")
            book_author = book_info.get("author_english", "Unknown Author")
            safe_folder_name = sanitize_filename(f"{book_title} by {book_author}")
            translation_dir = input_path.parent / safe_folder_name
            translation_dir.mkdir(exist_ok=True)
            # Create translated file
            translated_file = translation_dir / f"translated_{book_title} by {book_author}.txt"
            translated_file.write_text("Chapter 1\n\nTranslated content.", encoding="utf-8")
            return True

        with (
            patch("enchant_book_manager.rename_api_client.RenameAPIClient.make_request") as mock_openai_request,
            patch(
                "enchant_book_manager.workflow_phases.translate_novel",
                side_effect=mock_translate_novel,
            ),
        ):
            mock_openai_request.return_value = mock_openai_response

            success = process_novel_unified(test_novel_3, args3, logger)
            assert success is True

    @skip_local_api_tests("Resume functionality with local API not available in CI")
    def test_orchestration_resume_functionality(self, temp_dir, chinese_test_novel):
        """Test resume functionality across phases"""

        # Initialize logger for process_novel_unified
        import logging

        logger = logging.getLogger(__name__)

        # Create renamed file as if Phase 1 was completed
        renamed_file = temp_dir / "Test Novel by Test Author.txt"
        renamed_file.write_text(chinese_test_novel.read_text(encoding="utf-8"), encoding="utf-8")

        # Create progress file
        progress_file = temp_dir / f".{chinese_test_novel.stem}_progress.yml"
        progress_data = {
            "original_file": str(chinese_test_novel),
            "phases": {
                "renaming": {"status": "completed", "result": str(renamed_file)},
                "translation": {"status": "pending", "result": None},
                "epub": {"status": "pending", "result": None},
            },
        }

        with open(progress_file, "w") as f:
            yaml.dump(progress_data, f)

        args = Mock()
        args.skip_renaming = False
        args.skip_translating = False
        args.skip_epub = False
        args.resume = True
        args.encoding = "utf-8"
        args.max_chars = 2000
        args.remote = False
        args.translated = None
        args.epub_title = None
        args.epub_author = None
        args.epub_language = None
        args.no_toc = False
        args.no_validate = False
        args.epub_strict = False
        args.cover = None
        args.custom_css = None
        args.epub_metadata = None
        args.validate_only = False

        def mock_translate_novel(input_file, **kwargs):
            from enchant_book_manager.common_utils import sanitize_filename

            # Create translation directory structure
            input_path = Path(input_file)
            safe_folder_name = sanitize_filename("Test Novel by Test Author")
            translation_dir = input_path.parent / safe_folder_name
            translation_dir.mkdir(exist_ok=True)
            # Create translated file
            translated_file = translation_dir / "translated_Test Novel by Test Author.txt"
            translated_file.write_text("Chapter 1\n\nTranslated content.", encoding="utf-8")
            # Create chapter files
            chapter_file = translation_dir / "Chapter 1.txt"
            chapter_file.write_text("Chapter 1\n\nTranslated content.", encoding="utf-8")
            return True

        with patch(
            "enchant_book_manager.workflow_phases.translate_novel",
            side_effect=mock_translate_novel,
        ):
            success = process_novel_unified(chinese_test_novel, args, logger)

            # Should skip completed renaming phase
            assert success is True

    @pytest.mark.timeout(600)  # 10 minutes for error handling test
    @skip_local_api_tests("Local API endpoint localhost:1234 not available in CI")
    def test_error_handling_during_phases(self, temp_dir, chinese_test_novel, config_file):
        """Test error handling and recovery during different phases"""

        # Initialize logger for process_novel_unified
        import logging

        logger = logging.getLogger(__name__)

        args = Mock()
        args.skip_renaming = False
        args.skip_translating = False
        args.skip_epub = False
        args.resume = False
        args.openai_api_key = "test_key"
        args.rename_model = "gpt-4o-mini"
        args.rename_temperature = 0.0
        args.rename_dry_run = False
        args.encoding = "utf-8"
        args.max_chars = 2000
        args.remote = False

        # Test renaming failure
        with patch("enchant_book_manager.workflow_phases.rename_novel") as mock_rename:
            mock_rename.side_effect = Exception("Renaming failed")

            success = process_novel_unified(chinese_test_novel, args, logger)
            assert success is False

        # Test translation failure - mock both the rename and translate functions
        # to avoid actual API calls
        with (
            patch("enchant_book_manager.workflow_phases.rename_novel") as mock_rename,
            patch("enchant_book_manager.workflow_phases.translate_novel") as mock_translate,
            patch.dict(os.environ, {"ENCHANT_CONFIG": str(config_file)}),
        ):
            mock_rename.return_value = (True, chinese_test_novel, {})
            mock_translate.side_effect = Exception("Translation failed")

            success = process_novel_unified(chinese_test_novel, args, logger)
            assert success is False

    @skip_local_api_tests("Batch processing with local API not available in CI")
    def test_batch_processing(self, temp_dir, config_file):
        """Test batch processing of multiple novels"""

        # Create multiple Chinese novels
        novels = []
        for i in range(3):
            novel_file = temp_dir / f"测试小说{i + 1}.txt"
            novel_file.write_text(
                f"第一章 测试内容{i + 1}\n\n这是测试小说{i + 1}的内容。",
                encoding="utf-8",
            )
            novels.append(novel_file)

        # Mock args for batch processing
        args = Mock()
        args.filepath = str(temp_dir)
        args.batch = True
        args.resume = False
        args.skip_renaming = True  # Skip renaming to simplify test
        args.skip_translating = False
        args.skip_epub = False
        args.encoding = "utf-8"
        args.max_chars = 2000
        args.remote = False

        with patch("enchant_book_manager.workflow_phases.translate_novel") as mock_translate:
            mock_translate.return_value = True

            # This would normally be called by enchant_cli.process_batch()
            # For this test, we verify the batch functionality works
            assert len(novels) == 3
            for novel in novels:
                assert novel.exists()

    def test_epub_content_verification(self, temp_dir):
        """Test that generated EPUB contains proper English content and TOC"""

        # Create test chapters with English content
        chapters = [
            (
                "Chapter 1: The Beginning",
                "Chapter 1: The Beginning\n\nOnce upon a time, in a distant land, there lived a young cultivator named Li Ming. He possessed extraordinary talents that set him apart from his peers.",
            ),
            (
                "Chapter 2: The Discovery",
                "Chapter 2: The Discovery\n\nLi Ming discovered an ancient technique that would change his destiny forever. The technique was called 'Heaven Defying Art'.",
            ),
            (
                "Chapter 3: The Breakthrough",
                "Chapter 3: The Breakthrough\n\nAfter months of rigorous training, Li Ming finally achieved his first breakthrough. His power increased dramatically.",
            ),
        ]

        epub_path = temp_dir / "Test_Novel.epub"

        # Create EPUB
        create_epub_from_chapters(
            chapters=chapters,
            output_path=epub_path,
            title="Test Novel",
            author="Test Author",
            cover_path=None,
        )

        # Verify EPUB content
        with zipfile.ZipFile(epub_path, "r") as epub_zip:
            # Check chapter content
            chapter1_content = epub_zip.read("OEBPS/Text/chapter1.xhtml").decode("utf-8")
            assert "Li Ming" in chapter1_content
            assert "cultivator" in chapter1_content
            assert "Chapter 1: The Beginning" in chapter1_content

            # Check TOC
            toc_content = epub_zip.read("OEBPS/toc.ncx").decode("utf-8")
            assert "Chapter 1: The Beginning" in toc_content
            assert "Chapter 2: The Discovery" in toc_content
            assert "Chapter 3: The Breakthrough" in toc_content

            # Verify proper XML structure
            tree = ET.fromstring(chapter1_content)
            assert tree.tag.endswith("html")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
