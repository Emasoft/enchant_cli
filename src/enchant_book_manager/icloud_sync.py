#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
icloud_sync.py - Module for handling iCloud synchronization on macOS and iOS
"""

import platform
import subprocess
import re
import logging
from pathlib import Path
from typing import Optional, Union
import shutil

# Try to import waiting, but make it optional
try:
    import waiting
    HAS_WAITING = True
except ImportError:
    HAS_WAITING = False
    logging.warning("'waiting' module not installed. Some iCloud sync features may be limited.")

class ICloudSyncError(Exception):
    """Custom exception for iCloud synchronization errors."""
    pass

class ICloudSync:
    """
    Handles iCloud synchronization for files and folders on macOS and iOS.
    Auto-detects if running on compatible platform and within iCloud Drive.
    """
    
    def __init__(self, enabled: Optional[bool] = None, logger: Optional[logging.Logger] = None):
        """
        Initialize iCloud sync handler.
        
        Args:
            enabled: Force enable/disable. If None, auto-detect based on platform and location.
            logger: Logger instance to use
        """
        self.logger = logger or logging.getLogger(__name__)
        
        if enabled is not None:
            self.enabled = enabled
        else:
            self.enabled = self._auto_detect_icloud()
        
        if self.enabled:
            self._validate_commands()
            self.logger.info("iCloud sync enabled")
        else:
            self.logger.debug("iCloud sync disabled")
    
    def _auto_detect_icloud(self) -> bool:
        """
        Auto-detect if we should enable iCloud sync based on:
        1. Platform (macOS or iOS)
        2. Whether we're running within iCloud Drive
        """
        # Check platform
        system = platform.system().lower()
        if system != 'darwin':  # macOS and iOS both report as Darwin
            self.logger.debug(f"Platform '{system}' does not support iCloud sync")
            return False
        
        # Check if we're in iCloud Drive
        try:
            cwd = Path.cwd()
            cwd_str = str(cwd)
            
            # Common iCloud Drive paths
            icloud_indicators = [
                '/Library/Mobile Documents/com~apple~CloudDocs',  # macOS
                '/private/var/mobile/Library/Mobile Documents',    # iOS
                'iCloud Drive',                                     # Generic
                'com~apple~CloudDocs',                             # Document container
            ]
            
            for indicator in icloud_indicators:
                if indicator in cwd_str:
                    self.logger.info(f"Detected iCloud Drive location: {cwd_str}")
                    return True
            
            # Check if any parent directory is in iCloud
            for parent in cwd.parents:
                if 'iCloud' in parent.name or 'CloudDocs' in str(parent):
                    self.logger.info(f"Detected iCloud parent directory: {parent}")
                    return True
                    
        except Exception as e:
            self.logger.warning(f"Error detecting iCloud location: {e}")
        
        return False
    
    def _validate_commands(self):
        """Ensure required iCloud sync commands are available."""
        # Check for iOS-specific commands first (a-Shell, etc.)
        ios_commands = ['icloud', 'brctl']  # Common iOS terminal commands
        for cmd in ios_commands:
            if shutil.which(cmd) is not None:
                self.sync_command = cmd
                self.logger.info(f"Using iOS iCloud command: {cmd}")
                return
        
        # Check for macOS Finder integration commands
        macos_commands = ['downloadFolder', 'downloadFile']
        available = [cmd for cmd in macos_commands if shutil.which(cmd) is not None]
        
        if available:
            self.sync_command = 'finder'  # Use Finder-based commands
            self.logger.info("Using macOS Finder iCloud commands")
            return
        
        # Fallback: Try using brctl (Bird) which is available on both platforms
        if shutil.which('brctl') is not None:
            self.sync_command = 'brctl'
            self.logger.info("Using brctl for iCloud sync")
            return
        
        self.logger.warning("No iCloud sync commands found. Sync functionality will be limited.")
        self.enabled = False
    
    def ensure_synced(self, path: Union[str, Path]) -> Path:
        """
        Ensure a file or directory is fully synced from iCloud.
        This is the main entry point for the sync functionality.
        
        Args:
            path: Path to file or directory
            
        Returns:
            Path object pointing to the synced file/directory
            
        Raises:
            ICloudSyncError: If sync fails
        """
        if not self.enabled:
            return Path(path)
        
        path = Path(path)
        
        if not path.exists() and not str(path).endswith('.icloud'):
            # Check if there's an iCloud placeholder
            icloud_path = path.parent / f".{path.name}.icloud"
            if icloud_path.exists():
                path = icloud_path
        
        if path.is_dir():
            return self._sync_folder(path)
        elif path.is_file() or str(path).endswith('.icloud'):
            return self._sync_file(path)
        else:
            self.logger.warning(f"Path '{path}' not found, skipping sync")
            return path
    
    def _sync_folder(self, folder_path: Path, recursive: bool = True) -> Path:
        """Force sync a folder from iCloud."""
        if not self.enabled:
            return folder_path
        
        self.logger.info(f"Syncing iCloud folder: {folder_path}")
        
        try:
            if self.sync_command == 'finder':
                # macOS Finder-based sync
                subprocess.run(['downloadFolder', str(folder_path)], 
                             capture_output=True, check=True)
            elif self.sync_command == 'brctl':
                # Use brctl download
                subprocess.run(['brctl', 'download', str(folder_path)], 
                             capture_output=True, check=True)
            elif self.sync_command == 'icloud':
                # iOS-specific command
                subprocess.run(['icloud', 'sync', str(folder_path)], 
                             capture_output=True, check=True)
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to sync folder {folder_path}: {e}")
            # Don't raise - continue anyway
        
        if recursive and HAS_WAITING:
            # Wait for all files to be downloaded
            try:
                waiting.wait(
                    lambda: self._is_folder_synced(folder_path),
                    timeout_seconds=300,
                    sleep_seconds=2,
                    waiting_for="iCloud folder sync"
                )
            except waiting.TimeoutExpired:
                self.logger.warning(f"Timeout waiting for folder sync: {folder_path}")
        
        return folder_path
    
    def _sync_file(self, file_path: Path) -> Path:
        """Force sync a single file from iCloud."""
        if not self.enabled:
            return file_path
        
        # Handle .icloud placeholder files
        if str(file_path).endswith('.icloud'):
            actual_name = re.sub(r'^\.(.+)\.icloud$', r'\1', file_path.name)
            actual_path = file_path.parent / actual_name
            
            self.logger.info(f"Syncing iCloud file: {file_path} -> {actual_path}")
            
            try:
                if self.sync_command == 'finder':
                    subprocess.run(['downloadFile', str(file_path)], 
                                 capture_output=True, check=True)
                elif self.sync_command == 'brctl':
                    subprocess.run(['brctl', 'download', str(file_path.parent / actual_name)], 
                                 capture_output=True, check=True)
                elif self.sync_command == 'icloud':
                    subprocess.run(['icloud', 'download', str(file_path)], 
                                 capture_output=True, check=True)
            except subprocess.CalledProcessError as e:
                self.logger.error(f"Failed to sync file {file_path}: {e}")
            
            # Wait for download if waiting is available
            if HAS_WAITING:
                try:
                    waiting.wait(
                        lambda: actual_path.exists() and not file_path.exists(),
                        timeout_seconds=120,
                        sleep_seconds=1,
                        waiting_for="iCloud file download"
                    )
                    return actual_path
                except waiting.TimeoutExpired:
                    self.logger.warning(f"Timeout waiting for file sync: {file_path}")
            
            # Check if download succeeded
            if actual_path.exists():
                return actual_path
            else:
                return file_path
        
        return file_path
    
    def _is_folder_synced(self, folder_path: Path) -> bool:
        """Check if folder is fully synced (no .icloud files)."""
        try:
            for item in folder_path.rglob('*.icloud'):
                return False
            return True
        except Exception:
            return True
    
    def prepare_for_write(self, path: Union[str, Path]) -> Path:
        """
        Prepare a path for writing by ensuring parent directory is synced.
        
        Args:
            path: Path where we want to write
            
        Returns:
            Path object ready for writing
        """
        if not self.enabled:
            return Path(path)
        
        path = Path(path)
        parent = path.parent
        
        if parent.exists():
            self.ensure_synced(parent)
        
        return path


# Global instance for convenience
_global_sync = None

def get_icloud_sync() -> ICloudSync:
    """Get or create global iCloud sync instance."""
    global _global_sync
    if _global_sync is None:
        _global_sync = ICloudSync()
    return _global_sync

def ensure_synced(path: Union[str, Path]) -> Path:
    """Convenience function to sync a path using global instance."""
    return get_icloud_sync().ensure_synced(path)

def prepare_for_write(path: Union[str, Path]) -> Path:
    """Convenience function to prepare a path for writing."""
    return get_icloud_sync().prepare_for_write(path)