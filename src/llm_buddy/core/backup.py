"""
Auto-backup configuration and file change monitoring for LLM Buddy.
"""

import fnmatch
import hashlib
import logging
import os
from datetime import datetime, timedelta

from watchdog.events import FileSystemEventHandler

from llm_buddy.core.tokens import count_tokens_in_file

logger = logging.getLogger(__name__)


class AutoBackupConfig:
    """Configuration class for auto-backup settings."""

    def __init__(self):
        self.enabled = False
        self.monitor_folders = []
        self.monitor_files = []
        self.ignored_patterns = ["*.tmp", "*.bak", "*~"]
        self.min_token_change = 50
        self.cooldown_minutes = 5
        self.max_backups = 10
        self.notification_enabled = True
        self.last_backup_time = None
        self.file_hashes = {}  # {path: (hash, token_count)}

    def to_dict(self):
        """Convert configuration to dictionary for saving."""
        return {
            "enabled": self.enabled,
            "monitor_folders": self.monitor_folders,
            "monitor_files": self.monitor_files,
            "ignored_patterns": self.ignored_patterns,
            "min_token_change": self.min_token_change,
            "cooldown_minutes": self.cooldown_minutes,
            "max_backups": self.max_backups,
            "notification_enabled": self.notification_enabled,
        }

    def from_dict(self, config_dict):
        """Load configuration from dictionary."""
        self.enabled = config_dict.get("enabled", False)
        self.monitor_folders = config_dict.get("monitor_folders", [])
        self.monitor_files = config_dict.get("monitor_files", [])
        self.ignored_patterns = config_dict.get(
            "ignored_patterns", ["*.tmp", "*.bak", "*~"])
        self.min_token_change = config_dict.get("min_token_change", 50)
        self.cooldown_minutes = config_dict.get("cooldown_minutes", 5)
        self.max_backups = config_dict.get("max_backups", 10)
        self.notification_enabled = config_dict.get(
            "notification_enabled", True)


class EnhancedFileChangeHandler(FileSystemEventHandler):
    """Enhanced handler for file system events with prompt awareness.

    Uses callback functions instead of direct GUI references so that
    this class works with any GUI framework (or no GUI at all).

    Parameters
    ----------
    config : AutoBackupConfig
        Backup configuration (ignored patterns, cooldown, etc.).
    log_callback : callable(str), optional
        Called with log messages.
    schedule_callback : callable(int, callable), optional
        Schedules *callable* to run after *int* milliseconds on the
        main/GUI thread.  For tkinter pass ``master.after``; for
        PySide6 pass a ``QTimer.singleShot`` wrapper.
    trigger_backup_callback : callable(list[tuple[str, int]]), optional
        Called with ``(file_path, token_change)`` pairs when a backup
        should be triggered.
    prompt_database : optional
        If provided, changed files are associated with the active prompt.
    """

    def __init__(
        self,
        config,
        *,
        log_callback=None,
        schedule_callback=None,
        trigger_backup_callback=None,
        prompt_database=None,
    ):
        self.config = config
        self._log = log_callback or (lambda msg: None)
        self._schedule = schedule_callback or (lambda ms, fn: fn())
        self._trigger_backup = trigger_backup_callback or (lambda changes: None)
        self._prompt_database = prompt_database
        self.pending_changes = set()
        super().__init__()

    def on_modified(self, event):
        """Called when a file is modified."""
        if event.is_directory:
            return

        if not self._should_monitor_file(event.src_path):
            return

        self.pending_changes.add(event.src_path)
        self._log(f"Change detected in file: {event.src_path}")

        if not getattr(self, '_processing_scheduled', False):
            self._processing_scheduled = True
            self._schedule(1000, self._process_changes)

    def _should_monitor_file(self, file_path):
        """Check if the file should be monitored based on config."""
        if file_path in self.config.monitor_files:
            return True
        for folder in self.config.monitor_folders:
            if file_path.startswith(folder):
                for pattern in self.config.ignored_patterns:
                    if fnmatch.fnmatch(os.path.basename(file_path), pattern):
                        return False
                return True
        return False

    def _process_changes(self):
        """Process all pending file changes with prompt awareness."""
        self._processing_scheduled = False

        if not self.pending_changes:
            return

        # Check cooldown period
        if self.config.last_backup_time:
            elapsed = datetime.now() - self.config.last_backup_time
            if elapsed < timedelta(minutes=self.config.cooldown_minutes):
                remaining = (self.config.cooldown_minutes
                             - elapsed.total_seconds() / 60)
                self._log(
                    f"Cooldown period active. Next auto-backup available "
                    f"in {remaining:.1f} minutes")
                return

        # Associate changed files with active prompt
        if (self._prompt_database
                and self._prompt_database.active_prompt):
            for file_path in self.pending_changes:
                try:
                    current_tokens = count_tokens_in_file(file_path)
                    self._prompt_database.associate_file_with_active_prompt(
                        file_path, current_tokens)
                except Exception as e:
                    self._log(
                        f"Error processing prompt association "
                        f"for {file_path}: {e}")

        significant_changes = self._check_for_significant_changes()

        if significant_changes:
            self._trigger_backup(significant_changes)

        self.pending_changes.clear()

    def _check_for_significant_changes(self):
        """Check if changes are significant enough to trigger a backup."""
        significant_changes = []

        for file_path in self.pending_changes:
            try:
                with open(file_path, "rb") as f:
                    content = f.read()
                current_hash = hashlib.md5(content).hexdigest()
                current_tokens = count_tokens_in_file(file_path)

                if file_path in self.config.file_hashes:
                    prev_hash, prev_tokens = self.config.file_hashes[file_path]
                    if current_hash != prev_hash:
                        token_change = abs(current_tokens - prev_tokens)
                        if token_change >= self.config.min_token_change:
                            self._log(
                                f"Significant change detected in "
                                f"{file_path}: {token_change} tokens changed")
                            significant_changes.append(
                                (file_path, token_change))
                            # ONLY update the baseline if a backup is triggered
                            self.config.file_hashes[file_path] = (current_hash, current_tokens)
                else:
                    significant_changes.append((file_path, current_tokens))
                    self.config.file_hashes[file_path] = (current_hash, current_tokens)

                self.config.file_hashes[file_path] = (
                    current_hash, current_tokens)
            except Exception as e:
                self._log(
                    f"Error processing change for {file_path}: {e}")

        return significant_changes
