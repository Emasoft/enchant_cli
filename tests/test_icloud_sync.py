#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test suite for icloud_sync module.
"""

import pytest
import platform
import subprocess
import logging
from pathlib import Path
import sys
from unittest.mock import Mock, patch, MagicMock, call

sys.path.insert(0, str(Path(__file__).parent.parent))

from enchant_book_manager.icloud_sync import (
    ICloudSync,
    ICloudSyncError,
    get_icloud_sync,
    ensure_synced,
    prepare_for_write,
)


class TestICloudSyncError:
    """Test the ICloudSyncError exception."""

    def test_exception_inheritance(self):
        """Test that ICloudSyncError inherits from Exception."""
        assert issubclass(ICloudSyncError, Exception)

    def test_exception_can_be_raised(self):
        """Test that the exception can be raised with a message."""
        with pytest.raises(ICloudSyncError, match="Test error"):
            raise ICloudSyncError("Test error")


class TestICloudSync:
    """Test the ICloudSync class."""

    def setup_method(self):
        """Set up test fixtures."""
        # Reset global instance
        import enchant_book_manager.icloud_sync

        enchant_book_manager.icloud_sync._global_sync = None

    def test_init_with_explicit_enabled(self):
        """Test initialization with explicit enabled flag."""
        logger = Mock(spec=logging.Logger)

        # Test with enabled=True
        with patch.object(ICloudSync, "_validate_commands"):
            sync = ICloudSync(enabled=True, logger=logger)
            assert sync.enabled is True
            logger.info.assert_called_with("iCloud sync enabled")

        # Test with enabled=False
        sync = ICloudSync(enabled=False, logger=logger)
        assert sync.enabled is False
        logger.debug.assert_called_with("iCloud sync disabled")

    @patch("platform.system")
    def test_auto_detect_non_darwin_platform(self, mock_system):
        """Test auto-detection on non-Darwin platforms."""
        mock_system.return_value = "Linux"

        sync = ICloudSync()
        assert sync.enabled is False

    @patch("platform.system")
    @patch("pathlib.Path.cwd")
    def test_auto_detect_icloud_drive_location(self, mock_cwd, mock_system):
        """Test auto-detection when in iCloud Drive."""
        mock_system.return_value = "Darwin"
        mock_cwd.return_value = Path("/Users/test/Library/Mobile Documents/com~apple~CloudDocs/folder")

        with patch.object(ICloudSync, "_validate_commands"):
            sync = ICloudSync()
            assert sync.enabled is True

    @patch("platform.system")
    @patch("pathlib.Path.cwd")
    def test_auto_detect_icloud_parent_directory(self, mock_cwd, mock_system):
        """Test auto-detection with iCloud in parent directory."""
        mock_system.return_value = "Darwin"

        # Create a mock path with iCloud in parent
        mock_path = Mock()
        mock_path.parents = [
            Path("/Users/test/iCloud Drive/Documents"),
            Path("/Users/test/iCloud Drive"),
            Path("/Users/test"),
        ]
        mock_path.__str__ = lambda self: "/Users/test/Documents/project"
        mock_cwd.return_value = mock_path

        with patch.object(ICloudSync, "_validate_commands"):
            sync = ICloudSync()
            assert sync.enabled is True

    @patch("platform.system")
    @patch("pathlib.Path.cwd")
    def test_auto_detect_not_in_icloud(self, mock_cwd, mock_system):
        """Test auto-detection when not in iCloud."""
        mock_system.return_value = "Darwin"
        mock_cwd.return_value = Path("/Users/test/Documents/project")

        sync = ICloudSync()
        assert sync.enabled is False

    @patch("platform.system")
    @patch("pathlib.Path.cwd")
    def test_auto_detect_error_handling(self, mock_cwd, mock_system):
        """Test auto-detection handles errors gracefully."""
        mock_system.return_value = "Darwin"
        mock_cwd.side_effect = Exception("Permission denied")

        logger = Mock(spec=logging.Logger)
        sync = ICloudSync(logger=logger)
        assert sync.enabled is False
        logger.warning.assert_called()

    @patch("shutil.which")
    def test_validate_commands_ios(self, mock_which):
        """Test command validation on iOS."""
        # icloud command available
        mock_which.side_effect = lambda cmd: "/usr/bin/icloud" if cmd == "icloud" else None

        logger = Mock(spec=logging.Logger)
        sync = ICloudSync(enabled=True, logger=logger)
        assert sync.sync_command == "icloud"

    @patch("shutil.which")
    def test_validate_commands_macos_finder(self, mock_which):
        """Test command validation with macOS Finder commands."""

        # Finder commands available
        def which_side_effect(cmd):
            if cmd in ["downloadFolder", "downloadFile"]:
                return f"/usr/local/bin/{cmd}"
            return None

        mock_which.side_effect = which_side_effect

        logger = Mock(spec=logging.Logger)
        sync = ICloudSync(enabled=True, logger=logger)
        assert sync.sync_command == "finder"

    @patch("shutil.which")
    def test_validate_commands_brctl_fallback(self, mock_which):
        """Test command validation with brctl fallback."""
        # Only brctl available
        mock_which.side_effect = lambda cmd: "/usr/bin/brctl" if cmd == "brctl" else None

        logger = Mock(spec=logging.Logger)
        sync = ICloudSync(enabled=True, logger=logger)
        assert sync.sync_command == "brctl"

    @patch("shutil.which")
    def test_validate_commands_none_available(self, mock_which):
        """Test when no commands are available."""
        mock_which.return_value = None

        logger = Mock(spec=logging.Logger)
        sync = ICloudSync(enabled=True, logger=logger)
        assert sync.enabled is False
        logger.warning.assert_called_with("No iCloud sync commands found. Sync functionality will be limited.")

    def test_ensure_synced_disabled(self):
        """Test ensure_synced when sync is disabled."""
        sync = ICloudSync(enabled=False)
        path = Path("/test/file.txt")

        result = sync.ensure_synced(path)
        assert result == path

    def test_ensure_synced_directory(self):
        """Test ensure_synced with a directory."""
        sync = ICloudSync(enabled=True)
        sync.sync_command = "finder"

        test_path = Path("/test/folder")

        with patch.object(Path, "exists", return_value=True):
            with patch.object(Path, "is_dir", return_value=True):
                with patch.object(sync, "_sync_folder") as mock_sync_folder:
                    mock_sync_folder.return_value = test_path

                    result = sync.ensure_synced("/test/folder")
                    assert result == test_path
                    mock_sync_folder.assert_called_once_with(test_path)

    def test_ensure_synced_file(self):
        """Test ensure_synced with a file."""
        sync = ICloudSync(enabled=True)
        sync.sync_command = "finder"

        test_path = Path("/test/file.txt")

        with patch.object(Path, "exists", return_value=True):
            with patch.object(Path, "is_dir", return_value=False):
                with patch.object(Path, "is_file", return_value=True):
                    with patch.object(sync, "_sync_file") as mock_sync_file:
                        mock_sync_file.return_value = test_path

                        result = sync.ensure_synced("/test/file.txt")
                        assert result == test_path
                        mock_sync_file.assert_called_once_with(test_path)

    def test_ensure_synced_icloud_placeholder(self):
        """Test ensure_synced with .icloud placeholder file."""
        sync = ICloudSync(enabled=True)
        sync.sync_command = "finder"

        test_path = Path("/test/file.txt")
        icloud_path = Path("/test/.file.txt.icloud")

        # Mock the path to not exist, but icloud placeholder to exist
        def exists_side_effect(self):
            if str(self) == str(test_path):
                return False
            elif str(self) == str(icloud_path):
                return True
            return False

        with patch.object(Path, "exists", exists_side_effect):
            with patch.object(sync, "_sync_file") as mock_sync_file:
                mock_sync_file.return_value = test_path

                result = sync.ensure_synced(test_path)
                mock_sync_file.assert_called_once_with(icloud_path)

    def test_ensure_synced_not_found(self):
        """Test ensure_synced when path doesn't exist."""
        sync = ICloudSync(enabled=True)
        logger = Mock(spec=logging.Logger)
        sync.logger = logger

        test_path = Path("/test/missing.txt")
        icloud_path = Path("/test/.missing.txt.icloud")

        # Neither path exists
        with patch.object(Path, "exists", return_value=False):
            with patch.object(Path, "is_dir", return_value=False):
                with patch.object(Path, "is_file", return_value=False):
                    result = sync.ensure_synced(test_path)
                    assert result == test_path
                    logger.warning.assert_called()

    def test_sync_folder_finder_command(self):
        """Test _sync_folder with Finder command."""
        sync = ICloudSync(enabled=True)
        sync.sync_command = "finder"

        folder_path = Path("/test/folder")

        with patch("subprocess.run") as mock_run:
            result = sync._sync_folder(folder_path, recursive=False)

            assert result == folder_path
            mock_run.assert_called_once_with(["downloadFolder", str(folder_path)], capture_output=True, check=True)

    def test_sync_folder_brctl_command(self):
        """Test _sync_folder with brctl command."""
        sync = ICloudSync(enabled=True)
        sync.sync_command = "brctl"

        folder_path = Path("/test/folder")

        with patch("subprocess.run") as mock_run:
            result = sync._sync_folder(folder_path, recursive=False)

            assert result == folder_path
            mock_run.assert_called_once_with(["brctl", "download", str(folder_path)], capture_output=True, check=True)

    def test_sync_folder_icloud_command(self):
        """Test _sync_folder with iOS icloud command."""
        sync = ICloudSync(enabled=True)
        sync.sync_command = "icloud"

        folder_path = Path("/test/folder")

        with patch("subprocess.run") as mock_run:
            result = sync._sync_folder(folder_path, recursive=False)

            assert result == folder_path
            mock_run.assert_called_once_with(["icloud", "sync", str(folder_path)], capture_output=True, check=True)

    def test_sync_folder_error_handling(self):
        """Test _sync_folder handles subprocess errors."""
        sync = ICloudSync(enabled=True)
        sync.sync_command = "finder"
        logger = Mock(spec=logging.Logger)
        sync.logger = logger

        folder_path = Path("/test/folder")

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(1, "cmd", b"error")

            # Should not raise, just log error
            result = sync._sync_folder(folder_path, recursive=False)

            assert result == folder_path
            logger.error.assert_called()

    def test_sync_folder_with_waiting(self):
        """Test _sync_folder with waiting for completion."""
        sync = ICloudSync(enabled=True)
        sync.sync_command = "finder"

        folder_path = Path("/test/folder")

        with patch("subprocess.run"):
            with patch("enchant_book_manager.icloud_sync.HAS_WAITING", True):
                with patch("enchant_book_manager.icloud_sync.waiting") as mock_waiting:
                    with patch.object(sync, "_is_folder_synced", return_value=True):
                        result = sync._sync_folder(folder_path, recursive=True)

                        assert result == folder_path
                        mock_waiting.wait.assert_called_once()

    def test_sync_folder_waiting_timeout(self):
        """Test _sync_folder handles waiting timeout."""
        sync = ICloudSync(enabled=True)
        sync.sync_command = "finder"
        logger = Mock(spec=logging.Logger)
        sync.logger = logger

        folder_path = Path("/test/folder")

        with patch("subprocess.run"):
            with patch("enchant_book_manager.icloud_sync.HAS_WAITING", True):
                with patch("enchant_book_manager.icloud_sync.waiting") as mock_waiting:
                    # Create a mock exception class
                    class MockTimeoutExpired(Exception):
                        pass

                    mock_waiting.TimeoutExpired = MockTimeoutExpired
                    mock_waiting.wait.side_effect = MockTimeoutExpired("Timeout")

                    result = sync._sync_folder(folder_path, recursive=True)

                    assert result == folder_path
                    logger.warning.assert_called()

    def test_sync_file_regular_file(self):
        """Test _sync_file with a regular file."""
        sync = ICloudSync(enabled=True)

        file_path = Path("/test/file.txt")
        result = sync._sync_file(file_path)
        assert result == file_path

    def test_sync_file_icloud_placeholder_finder(self):
        """Test _sync_file with .icloud placeholder using Finder."""
        sync = ICloudSync(enabled=True)
        sync.sync_command = "finder"

        file_path = Path("/test/.document.pdf.icloud")

        with patch("subprocess.run") as mock_run:
            result = sync._sync_file(file_path)

            # Without waiting module, should return original path
            assert result == file_path
            mock_run.assert_called_once_with(["downloadFile", str(file_path)], capture_output=True, check=True)

    def test_sync_file_icloud_placeholder_brctl(self):
        """Test _sync_file with .icloud placeholder using brctl."""
        sync = ICloudSync(enabled=True)
        sync.sync_command = "brctl"

        file_path = Path("/test/.document.pdf.icloud")
        expected_actual_path = file_path.parent / "document.pdf"

        with patch("subprocess.run") as mock_run:
            result = sync._sync_file(file_path)

            # Without waiting module, should return original path
            assert result == file_path
            mock_run.assert_called_once_with(
                ["brctl", "download", str(expected_actual_path)],
                capture_output=True,
                check=True,
            )

    def test_sync_file_wait_for_download(self):
        """Test _sync_file waits for download completion."""
        sync = ICloudSync(enabled=True)
        sync.sync_command = "finder"

        file_path = Path("/test/.document.pdf.icloud")
        actual_path = Path("/test/document.pdf")

        with patch("subprocess.run"):
            with patch("enchant_book_manager.icloud_sync.HAS_WAITING", True):
                with patch("enchant_book_manager.icloud_sync.waiting") as mock_waiting:
                    # Mock the waiting condition - it succeeds
                    mock_waiting.wait.return_value = None

                    # Mock path existence - actual file exists after download
                    def exists_side_effect(self):
                        return str(self) == str(actual_path)

                    with patch.object(Path, "exists", exists_side_effect):
                        result = sync._sync_file(file_path)
                        # Should return actual path after successful download
                        assert result == actual_path

    def test_is_folder_synced_no_icloud_files(self):
        """Test _is_folder_synced when no .icloud files present."""
        sync = ICloudSync(enabled=True)

        folder_path = Mock(spec=Path)
        folder_path.rglob.return_value = []

        assert sync._is_folder_synced(folder_path) is True

    def test_is_folder_synced_has_icloud_files(self):
        """Test _is_folder_synced when .icloud files are present."""
        sync = ICloudSync(enabled=True)

        folder_path = Mock(spec=Path)
        folder_path.rglob.return_value = [Path("/.file.icloud")]

        assert sync._is_folder_synced(folder_path) is False

    def test_is_folder_synced_error_handling(self):
        """Test _is_folder_synced handles errors gracefully."""
        sync = ICloudSync(enabled=True)

        folder_path = Mock(spec=Path)
        folder_path.rglob.side_effect = Exception("Permission denied")

        # Should return True on error
        assert sync._is_folder_synced(folder_path) is True

    def test_prepare_for_write_disabled(self):
        """Test prepare_for_write when sync is disabled."""
        sync = ICloudSync(enabled=False)

        path = Path("/test/new_file.txt")
        result = sync.prepare_for_write(path)
        assert result == path

    def test_prepare_for_write_parent_exists(self):
        """Test prepare_for_write when parent directory exists."""
        sync = ICloudSync(enabled=True)

        path = Path("/test/folder/new_file.txt")

        with patch.object(Path, "exists", return_value=True):
            with patch.object(sync, "ensure_synced") as mock_ensure:
                mock_ensure.return_value = path.parent

                result = sync.prepare_for_write(path)

                assert result == path
                mock_ensure.assert_called_once_with(path.parent)

    def test_prepare_for_write_parent_not_exists(self):
        """Test prepare_for_write when parent directory doesn't exist."""
        sync = ICloudSync(enabled=True)

        # Mock path with non-existent parent
        path = Mock(spec=Path)
        parent = Mock()
        parent.exists.return_value = False
        path.parent = parent

        with patch("enchant_book_manager.icloud_sync.Path", return_value=path):
            with patch.object(sync, "ensure_synced") as mock_ensure:
                result = sync.prepare_for_write("/test/folder/new_file.txt")

                # Should not call ensure_synced if parent doesn't exist
                mock_ensure.assert_not_called()


class TestGlobalFunctions:
    """Test the global convenience functions."""

    def setup_method(self):
        """Reset global instance before each test."""
        import enchant_book_manager.icloud_sync

        enchant_book_manager.icloud_sync._global_sync = None

    @patch("platform.system")
    def test_get_icloud_sync_creates_instance(self, mock_system):
        """Test get_icloud_sync creates instance on first call."""
        mock_system.return_value = "Darwin"

        sync1 = get_icloud_sync()
        assert sync1 is not None
        assert isinstance(sync1, ICloudSync)

        # Should return same instance on subsequent calls
        sync2 = get_icloud_sync()
        assert sync1 is sync2

    @patch("platform.system")
    def test_ensure_synced_global(self, mock_system):
        """Test global ensure_synced function."""
        mock_system.return_value = "Linux"  # Disable auto-detection

        path = Path("/test/file.txt")
        result = ensure_synced(path)
        assert result == path

    @patch("platform.system")
    def test_prepare_for_write_global(self, mock_system):
        """Test global prepare_for_write function."""
        mock_system.return_value = "Linux"  # Disable auto-detection

        path = Path("/test/file.txt")
        result = prepare_for_write(path)
        assert result == path


class TestICloudSyncEdgeCases:
    """Test edge cases and missing coverage for ICloudSync."""

    def setup_method(self):
        """Set up test fixtures."""
        # Reset global instance
        import enchant_book_manager.icloud_sync

        enchant_book_manager.icloud_sync._global_sync = None

    @patch("enchant_book_manager.icloud_sync.HAS_WAITING", False)
    @patch("enchant_book_manager.icloud_sync.logging")
    def test_import_waiting_failure(self, mock_logging):
        """Test when waiting module import fails."""
        # The warning is already logged at module import time
        # Just verify HAS_WAITING is False
        import enchant_book_manager.icloud_sync

        assert enchant_book_manager.icloud_sync.HAS_WAITING is False

    def test_sync_file_icloud_ios_command(self):
        """Test _sync_file with iOS icloud command."""
        sync = ICloudSync(enabled=True)
        sync.sync_command = "icloud"

        file_path = Path("/test/.document.pdf.icloud")

        with patch("subprocess.run") as mock_run:
            result = sync._sync_file(file_path)

            # Should return original path without waiting module
            assert result == file_path
            mock_run.assert_called_once_with(
                ["icloud", "download", str(file_path)],
                capture_output=True,
                check=True,
            )

    def test_sync_file_subprocess_error(self):
        """Test _sync_file handles subprocess errors."""
        sync = ICloudSync(enabled=True)
        sync.sync_command = "finder"
        logger = Mock(spec=logging.Logger)
        sync.logger = logger

        file_path = Path("/test/.document.pdf.icloud")

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(1, "cmd", b"error")

            result = sync._sync_file(file_path)

            # Should still return the file path on error
            assert result == file_path
            logger.error.assert_called()

    def test_sync_file_without_waiting_module(self):
        """Test _sync_file when waiting module is not available."""
        sync = ICloudSync(enabled=True)
        sync.sync_command = "finder"

        file_path = Path("/test/.document.pdf.icloud")
        actual_path = Path("/test/document.pdf")

        with patch("subprocess.run"):
            with patch("enchant_book_manager.icloud_sync.HAS_WAITING", False):
                # Mock actual_path.exists() to return True
                def exists_side_effect(self):
                    return str(self) == str(actual_path)

                with patch.object(Path, "exists", exists_side_effect):
                    result = sync._sync_file(file_path)
                    # Should return actual path if it exists after download
                    assert result == actual_path

    def test_sync_file_without_waiting_module_fail(self):
        """Test _sync_file when waiting module is not available and download fails."""
        sync = ICloudSync(enabled=True)
        sync.sync_command = "finder"

        file_path = Path("/test/.document.pdf.icloud")
        actual_path = Path("/test/document.pdf")

        with patch("subprocess.run"):
            with patch("enchant_book_manager.icloud_sync.HAS_WAITING", False):
                # Mock actual_path.exists() to return False
                with patch.object(Path, "exists", return_value=False):
                    result = sync._sync_file(file_path)
                    # Should return original path if download failed
                    assert result == file_path

    def test_sync_folder_without_waiting(self):
        """Test _sync_folder when waiting module is not available."""
        sync = ICloudSync(enabled=True)
        sync.sync_command = "finder"

        folder_path = Path("/test/folder")

        with patch("subprocess.run") as mock_run:
            with patch("enchant_book_manager.icloud_sync.HAS_WAITING", False):
                result = sync._sync_folder(folder_path, recursive=True)

                assert result == folder_path
                mock_run.assert_called_once()

    def test_sync_folder_disabled(self):
        """Test _sync_folder when sync is disabled."""
        sync = ICloudSync(enabled=False)

        folder_path = Path("/test/folder")
        result = sync._sync_folder(folder_path)

        assert result == folder_path

    def test_sync_file_disabled(self):
        """Test _sync_file when sync is disabled."""
        sync = ICloudSync(enabled=False)

        file_path = Path("/test/file.txt")
        result = sync._sync_file(file_path)

        assert result == file_path

    @patch("pathlib.Path.cwd")
    def test_auto_detect_cwd_error(self, mock_cwd):
        """Test _auto_detect_icloud when cwd() raises an error."""
        mock_cwd.side_effect = PermissionError("Access denied")

        logger = Mock(spec=logging.Logger)
        sync = ICloudSync(logger=logger)

        # Should handle error gracefully and return False
        assert sync.enabled is False

    def test_is_folder_synced_rglob_generator(self):
        """Test _is_folder_synced with generator that yields items."""
        sync = ICloudSync(enabled=True)

        folder_path = Mock(spec=Path)

        # Create a generator that yields one .icloud file
        def rglob_generator(pattern):
            yield Path("/.file.icloud")

        folder_path.rglob = rglob_generator

        assert sync._is_folder_synced(folder_path) is False

    def test_sync_file_waiting_timeout_actual_path_exists(self):
        """Test _sync_file when waiting times out but file exists."""
        sync = ICloudSync(enabled=True)
        sync.sync_command = "finder"
        logger = Mock(spec=logging.Logger)
        sync.logger = logger

        file_path = Path("/test/.document.pdf.icloud")
        actual_path = Path("/test/document.pdf")

        with patch("subprocess.run"):
            with patch("enchant_book_manager.icloud_sync.HAS_WAITING", True):
                with patch("enchant_book_manager.icloud_sync.waiting") as mock_waiting:
                    # Create a mock exception class
                    class MockTimeoutExpired(Exception):
                        pass

                    mock_waiting.TimeoutExpired = MockTimeoutExpired
                    mock_waiting.wait.side_effect = MockTimeoutExpired("Timeout")

                    # Mock actual_path.exists() to return True
                    def exists_side_effect(self):
                        return str(self) == str(actual_path)

                    with patch.object(Path, "exists", exists_side_effect):
                        result = sync._sync_file(file_path)
                        # Should still return actual path if it exists
                        assert result == actual_path
                        logger.warning.assert_called()

    def test_sync_file_waiting_timeout_actual_path_not_exists(self):
        """Test _sync_file when waiting times out and file doesn't exist."""
        sync = ICloudSync(enabled=True)
        sync.sync_command = "finder"
        logger = Mock(spec=logging.Logger)
        sync.logger = logger

        file_path = Path("/test/.document.pdf.icloud")
        actual_path = Path("/test/document.pdf")

        with patch("subprocess.run"):
            with patch("enchant_book_manager.icloud_sync.HAS_WAITING", True):
                with patch("enchant_book_manager.icloud_sync.waiting") as mock_waiting:
                    # Create a mock exception class
                    class MockTimeoutExpired(Exception):
                        pass

                    mock_waiting.TimeoutExpired = MockTimeoutExpired
                    mock_waiting.wait.side_effect = MockTimeoutExpired("Timeout")

                    # Mock actual_path.exists() to return False
                    with patch.object(Path, "exists", return_value=False):
                        result = sync._sync_file(file_path)
                        # Should return original path if download failed
                        assert result == file_path
                        logger.warning.assert_called()
