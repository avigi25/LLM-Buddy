"""Auto-Backup panel – monitor files and trigger automatic backups."""

import json
import os
import fnmatch
from datetime import datetime

from PySide6.QtCore import Qt, Slot, QTimer, Signal
from PySide6.QtGui import QStandardItemModel, QStandardItem
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QLabel, QLineEdit, QSpinBox, QPushButton, QCheckBox,
    QTreeView, QGroupBox, QMessageBox, QFileDialog,
    QHeaderView, QSplitter,
)

from llm_buddy.core.backup import AutoBackupConfig, EnhancedFileChangeHandler
from llm_buddy.core.tokens import build_combined_text, count_tokens, count_tokens_in_file
from llm_buddy.paths import get_data_dir, get_backup_dir

try:
    from watchdog.observers import Observer
except ImportError:
    Observer = None


class BackupPanel(QWidget):
    """Auto-Backup management panel.

    Sub-tabs: Files & Folders | Settings | History.
    """

    # Emitted from watchdog background thread; Qt queues delivery
    # to the main thread automatically (queued connection).
    _backup_requested = Signal(int, object)  # (delay_ms, callback)

    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self._mw = main_window
        self._config = AutoBackupConfig()
        self._observer = None

        # Debounced backup scheduling via Qt Signal (thread-safe)
        self._debounce_timer = None
        self._backup_requested.connect(self._on_backup_requested)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        top_row = QHBoxLayout()
        self._chk_enabled = QCheckBox("Enable Auto-Backup")
        self._chk_enabled.toggled.connect(self._toggle)
        top_row.addWidget(self._chk_enabled)
        top_row.addSpacing(20)
        top_row.addWidget(QLabel("Status:"))
        self._status_label = QLabel("Inactive")
        self._status_label.setStyleSheet("color: red; font-weight: bold;")
        top_row.addWidget(self._status_label)
        top_row.addStretch()
        layout.addLayout(top_row)

        tabs = QTabWidget()
        layout.addWidget(tabs, stretch=1)

        tabs.addTab(self._build_files_tab(), "Files && Folders")
        tabs.addTab(self._build_settings_tab(), "Settings")
        tabs.addTab(self._build_history_tab(), "History")

        bot = QHBoxLayout()
        bot.addStretch()
        btn_refresh = QPushButton("Refresh Status")
        btn_refresh.clicked.connect(self._refresh_status)
        bot.addWidget(btn_refresh)
        btn_force = QPushButton("Force Backup Now")
        btn_force.clicked.connect(self._force_backup)
        bot.addWidget(btn_force)
        layout.addLayout(bot)

        self._load_settings()

    def _build_files_tab(self) -> QWidget:
        w = QWidget()
        lay = QHBoxLayout(w)

        # Monitored files
        file_group = QGroupBox("Monitored Files")
        fl = QVBoxLayout(file_group)
        self._files_model = QStandardItemModel()
        self._files_model.setHorizontalHeaderLabels(["File Path"])
        self._files_tree = QTreeView()
        self._files_tree.setModel(self._files_model)
        self._files_tree.setRootIsDecorated(False)
        self._files_tree.setSelectionMode(QTreeView.ExtendedSelection)
        self._files_tree.header().setSectionResizeMode(
            QHeaderView.Interactive)
        self._files_tree.header().setStretchLastSection(True)
        fl.addWidget(self._files_tree)
        fbtn = QHBoxLayout()
        b1 = QPushButton("Add Files")
        b1.clicked.connect(self._add_files)
        fbtn.addWidget(b1)
        b2 = QPushButton("Remove Selected")
        b2.clicked.connect(self._remove_files)
        fbtn.addWidget(b2)
        b3 = QPushButton("Add Current Selection")
        b3.clicked.connect(self._add_current_selection)
        fbtn.addWidget(b3)
        fl.addLayout(fbtn)
        lay.addWidget(file_group)

        # Monitored folders
        folder_group = QGroupBox("Monitored Folders")
        dl = QVBoxLayout(folder_group)
        self._folders_model = QStandardItemModel()
        self._folders_model.setHorizontalHeaderLabels(["Folder Path"])
        self._folders_tree = QTreeView()
        self._folders_tree.setModel(self._folders_model)
        self._folders_tree.setRootIsDecorated(False)
        self._folders_tree.setSelectionMode(QTreeView.ExtendedSelection)
        self._folders_tree.header().setSectionResizeMode(
            QHeaderView.Interactive)
        self._folders_tree.header().setStretchLastSection(True)
        dl.addWidget(self._folders_tree)
        dbtn = QHBoxLayout()
        d1 = QPushButton("Add Folder")
        d1.clicked.connect(self._add_folder)
        dbtn.addWidget(d1)
        d2 = QPushButton("Remove Selected")
        d2.clicked.connect(self._remove_folders)
        dbtn.addWidget(d2)
        dl.addLayout(dbtn)
        lay.addWidget(folder_group)
        return w

    def _build_settings_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(20, 20, 20, 20)

        def _row(label_text, widget):
            r = QHBoxLayout()
            r.addWidget(QLabel(label_text))
            r.addWidget(widget)
            r.addStretch()
            lay.addLayout(r)

        self._ignored_edit = QLineEdit()
        _row("Ignored File Patterns:", self._ignored_edit)

        self._min_change_spin = QSpinBox()
        self._min_change_spin.setRange(1, 10000)
        self._min_change_spin.setValue(self._config.min_token_change)
        _row("Min Token Change to Trigger Backup:", self._min_change_spin)

        self._cooldown_spin = QSpinBox()
        self._cooldown_spin.setRange(1, 60)
        self._cooldown_spin.setValue(self._config.cooldown_minutes)
        _row("Cooldown Between Backups (minutes):", self._cooldown_spin)

        self._max_backups_spin = QSpinBox()
        self._max_backups_spin.setRange(1, 500)
        self._max_backups_spin.setValue(self._config.max_backups)
        _row("Maximum Auto-Backups to Keep:", self._max_backups_spin)

        self._chk_notify = QCheckBox("Show Notifications When Backup Occurs")
        self._chk_notify.setChecked(self._config.notification_enabled)
        lay.addWidget(self._chk_notify)

        btn_save = QPushButton("Save Settings")
        btn_save.clicked.connect(self._save_settings)
        lay.addWidget(btn_save)
        lay.addStretch()
        return w

    def _build_history_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        self._hist_model = QStandardItemModel()
        self._hist_model.setHorizontalHeaderLabels(
            ["Date & Time", "Files Changed", "Token Changes", "Has Prompt"])
        self._hist_tree = QTreeView()
        self._hist_tree.setModel(self._hist_model)
        self._hist_tree.setRootIsDecorated(False)
        self._hist_tree.setAlternatingRowColors(True)
        hist_header = self._hist_tree.header()
        hist_header.setSectionResizeMode(QHeaderView.Interactive)
        hist_header.setStretchLastSection(True)
        hist_header.resizeSection(0, 160)
        lay.addWidget(self._hist_tree)
        return w

    @Slot(bool)
    def _toggle(self, enabled: bool) -> None:
        if enabled:
            self._start_monitoring()
        else:
            self._stop_monitoring()
        self._config.enabled = enabled
        self._save_settings()
        self._refresh_status()

    def _start_monitoring(self) -> None:
        if self._observer is not None:
            return
        if Observer is None:
            self._mw.log("watchdog not installed – cannot monitor files")
            QMessageBox.critical(
                self, "Error",
                "The 'watchdog' package is required for auto-backup.\n"
                "Install with: pip install watchdog")
            self._chk_enabled.setChecked(False)
            return
        try:
            handler = EnhancedFileChangeHandler(
                self._config,
                log_callback=self._mw.log,
                schedule_callback=self._schedule_on_main,
                trigger_backup_callback=self._trigger_backup,
                prompt_database=self._mw.prompt_database,
            )
            self._observer = Observer()
            for folder in self._config.monitor_folders:
                if os.path.isdir(folder):
                    self._observer.schedule(handler, folder, recursive=True)
                    self._mw.log(f"Monitoring folder: {folder}")
            for fp in self._config.monitor_files:
                if os.path.isfile(fp):
                    parent = os.path.dirname(fp)
                    if parent:
                        self._observer.schedule(
                            handler, parent, recursive=False)
                        self._mw.log(f"Monitoring file: {fp}")
            self._observer.start()
            self._mw.log("Auto-backup monitoring started")
        except Exception as e:
            self._mw.log(f"Error starting monitoring: {e}")
            QMessageBox.critical(self, "Error",
                                 f"Failed to start monitoring:\n{e}")
            self._chk_enabled.setChecked(False)

    def _stop_monitoring(self) -> None:
        if self._observer is None:
            return
        try:
            self._observer.stop()
            self._observer.join(timeout=5)
        except Exception as e:
            self._mw.log(f"Error stopping monitoring: {e}")
        self._observer = None
        self._mw.log("Auto-backup monitoring stopped")

    def _schedule_on_main(self, ms, fn, *args):
        """Called by watchdog from a background thread.

        Emits a Qt Signal which is delivered on the main thread,
        where debouncing is handled with a cancellable QTimer.
        """
        self._backup_requested.emit(ms, lambda: fn(*args))

    @Slot(int, object)
    def _on_backup_requested(self, delay_ms, fn):
        """Debounce backup requests on the main thread.

        Each new call cancels any pending timer, resetting the debounce
        window.  This coalesces rapid file changes into a single backup.
        """
        if self._debounce_timer is not None:
            self._debounce_timer.stop()
            self._debounce_timer.deleteLater()

        timer = QTimer(self)
        timer.setSingleShot(True)
        timer.timeout.connect(fn)
        timer.start(delay_ms)
        self._debounce_timer = timer

    def _restart_if_active(self) -> None:
        if self._observer:
            self._stop_monitoring()
            self._start_monitoring()

    @Slot()
    def _refresh_status(self) -> None:
        if self._observer and self._observer.is_alive():
            self._status_label.setText("Active")
            self._status_label.setStyleSheet(
                "color: green; font-weight: bold;")
        else:
            self._status_label.setText("Inactive")
            self._status_label.setStyleSheet(
                "color: red; font-weight: bold;")

    @Slot()
    def _add_files(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Select File(s) to Monitor", "",
            "All files (*.*)")
        for fp in paths:
            if fp not in self._config.monitor_files:
                self._config.monitor_files.append(fp)
                item = QStandardItem(fp)
                item.setEditable(False)
                item.setToolTip(fp)
                self._files_model.appendRow([item])
                self._mw.log(f"Added {fp} to monitored files")
        self._restart_if_active()

    @Slot()
    def _remove_files(self) -> None:
        indexes = self._files_tree.selectionModel().selectedRows()
        for idx in sorted(indexes, reverse=True):
            fp = self._files_model.item(idx.row(), 0).text()
            if fp in self._config.monitor_files:
                self._config.monitor_files.remove(fp)
            self._files_model.removeRow(idx.row())
            self._mw.log(f"Removed {fp} from monitored files")
        self._restart_if_active()

    @Slot()
    def _add_current_selection(self) -> None:
        for fp, _tok in self._mw.filtered_files:
            if fp not in self._config.monitor_files:
                self._config.monitor_files.append(fp)
                item = QStandardItem(fp)
                item.setEditable(False)
                item.setToolTip(fp)
                self._files_model.appendRow([item])
        for folder in self._mw.folders:
            if folder not in self._config.monitor_folders:
                self._config.monitor_folders.append(folder)
                item = QStandardItem(folder)
                item.setEditable(False)
                item.setToolTip(folder)
                self._folders_model.appendRow([item])
        self._mw.log("Added current selection to monitoring")
        self._restart_if_active()

    @Slot()
    def _add_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self, "Select Folder to Monitor")
        if folder and folder not in self._config.monitor_folders:
            self._config.monitor_folders.append(folder)
            item = QStandardItem(folder)
            item.setEditable(False)
            item.setToolTip(folder)
            self._folders_model.appendRow([item])
            self._mw.log(f"Added {folder} to monitored folders")
        self._restart_if_active()

    @Slot()
    def _remove_folders(self) -> None:
        indexes = self._folders_tree.selectionModel().selectedRows()
        for idx in sorted(indexes, reverse=True):
            fp = self._folders_model.item(idx.row(), 0).text()
            if fp in self._config.monitor_folders:
                self._config.monitor_folders.remove(fp)
            self._folders_model.removeRow(idx.row())
            self._mw.log(f"Removed {fp} from monitored folders")
        self._restart_if_active()

    @Slot()
    def _save_settings(self) -> None:
        self._config.ignored_patterns = [
            p.strip() for p in self._ignored_edit.text().split(",")
            if p.strip()]
        self._config.min_token_change = self._min_change_spin.value()
        self._config.cooldown_minutes = self._cooldown_spin.value()
        self._config.max_backups = self._max_backups_spin.value()
        self._config.notification_enabled = self._chk_notify.isChecked()
        try:
            with open(os.path.join(get_data_dir(), "auto_backup_settings.json"), "w",
                       encoding="utf-8") as f:
                json.dump(self._config.to_dict(), f, indent=4)
            self._mw.log("Auto-backup settings saved")
            self._restart_if_active()
        except Exception as e:
            self._mw.log(f"Error saving settings: {e}")

    def _load_settings(self) -> None:
        settings_path = os.path.join(get_data_dir(), "auto_backup_settings.json")
        if not os.path.exists(settings_path):
            self._ignored_edit.setText(
                ",".join(self._config.ignored_patterns))
            return
        try:
            with open(settings_path, "r",
                       encoding="utf-8") as f:
                settings = json.load(f)
            self._config.from_dict(settings)

            self._chk_enabled.setChecked(self._config.enabled)
            self._ignored_edit.setText(
                ",".join(self._config.ignored_patterns))
            self._min_change_spin.setValue(self._config.min_token_change)
            self._cooldown_spin.setValue(self._config.cooldown_minutes)
            self._max_backups_spin.setValue(self._config.max_backups)
            self._chk_notify.setChecked(
                self._config.notification_enabled)

            # Populate file/folder trees
            self._files_model.removeRows(
                0, self._files_model.rowCount())
            for fp in self._config.monitor_files:
                item = QStandardItem(fp)
                item.setEditable(False)
                item.setToolTip(fp)
                self._files_model.appendRow([item])
            self._folders_model.removeRows(
                0, self._folders_model.rowCount())
            for fp in self._config.monitor_folders:
                item = QStandardItem(fp)
                item.setEditable(False)
                item.setToolTip(fp)
                self._folders_model.appendRow([item])

            self._mw.log("Auto-backup settings loaded")
            if self._config.enabled:
                self._start_monitoring()
        except Exception as e:
            self._mw.log(f"Error loading settings: {e}")

    def _trigger_backup(self, changed_files) -> bool:
        """Create an auto-backup (called from file watcher)."""
        self._config.last_backup_time = datetime.now()

        active_prompt_info = ""
        if self._mw.prompt_database.active_prompt:
            prompt = self._mw.prompt_database.active_prompt
            for fp, tc in changed_files:
                if fp not in prompt.associated_files:
                    prompt.associated_files.append(fp)
                    prompt.file_changes[fp] = tc
            self._mw.prompt_database.save()
            active_prompt_info = (
                f"\nActive Prompt: "
                f"{prompt.description or 'Untitled'} ({prompt.llm_used})")

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        total_changes = sum(c for _, c in changed_files)
        backup_name = (
            f"auto_backup_{ts}_{len(changed_files)}files_"
            f"{total_changes}tokens.md")

        files_to_backup = [fp for fp, _ in changed_files]
        for fp in self._config.monitor_files:
            if fp not in files_to_backup and os.path.isfile(fp):
                files_to_backup.append(fp)

        header = (
            f"Auto-Backup generated on "
            f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"Changed files: {len(changed_files)}, "
            f"Total token changes: {total_changes}"
            f"{active_prompt_info}")
        if self._mw.prompt_database.active_prompt:
            header += ("\n\nPrompt Text:\n"
                       + self._mw.prompt_database.active_prompt.prompt_text)

        combined = build_combined_text(
            files_to_backup, header, "End of Auto-Backup")
        total_tokens = count_tokens(combined)

        output_dir = get_backup_dir()
        output_file = os.path.join(output_dir, backup_name)

        try:
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(combined)
            self._mw.log(f"Auto-backup created: {output_file}")

            prompt_info = ("Yes" if self._mw.prompt_database.active_prompt
                           else "No")
            # Add to history tree
            row = [
                QStandardItem(ts),
                QStandardItem(str(len(changed_files))),
                QStandardItem(str(total_changes)),
                QStandardItem(prompt_info),
            ]
            for item in row:
                item.setEditable(False)
            self._hist_model.insertRow(0, row)

            self._create_backup_eadr_note(
                backup_name, changed_files, total_tokens)
            self._prune_old()

            if self._config.notification_enabled:
                QMessageBox.information(
                    self, "Auto-Backup Complete",
                    f"Created backup with {len(changed_files)} "
                    f"changed files.\nTotal tokens: {total_tokens:,}")
            return True
        except Exception as e:
            self._mw.log(f"Error creating auto-backup: {e}")
            return False

    @Slot()
    def _force_backup(self) -> None:
        files_to_backup = []
        for fp in self._config.monitor_files:
            if os.path.isfile(fp):
                files_to_backup.append(fp)
        for folder in self._config.monitor_folders:
            if os.path.isdir(folder):
                for root, _, files in os.walk(folder):
                    for fn in files:
                        skip = any(
                            fnmatch.fnmatch(fn, pat)
                            for pat in self._config.ignored_patterns)
                        if not skip:
                            files_to_backup.append(os.path.join(root, fn))
        if not files_to_backup:
            QMessageBox.information(
                self, "No Files",
                "No files to backup. Add files or folders first.")
            return
        changed = [(fp, count_tokens_in_file(fp)) for fp in files_to_backup]
        if self._trigger_backup(changed):
            QMessageBox.information(
                self, "Success", "Manual backup completed successfully.")
        else:
            QMessageBox.critical(
                self, "Error", "Failed to create backup. See log.")

    def _create_backup_eadr_note(self, backup_name, changed_files,
                                  total_tokens):
        project = "Origin"
        if hasattr(self._mw, '_eadr_panel'):
            project = self._mw._eadr_panel.project
        note = (
            f"Auto-Backup Created: {backup_name}\n\n"
            f"Total files: {len(changed_files)}\n"
            f"Total tokens: {total_tokens:,}\n\n")
        if self._mw.prompt_database.active_prompt:
            p = self._mw.prompt_database.active_prompt
            note += (f"Active Prompt: {p.description or 'Untitled'}\n"
                     f"LLM Used: {p.llm_used}\n\n")
        note += "Changed files:\n"
        for fp, tc in changed_files:
            note += f"- {fp} ({tc:+,} tokens)\n"
        note_id = self._mw.prompt_database.add_eadr_note(note, project)
        if note_id >= 0:
            self._mw.log(f"eADR note created for auto-backup")
            if hasattr(self._mw, '_eadr_panel'):
                self._mw._eadr_panel.refresh()

    def _prune_old(self) -> None:
        backup_dir = get_backup_dir()
        if not os.path.exists(backup_dir):
            return
        auto_backups = []
        for fn in os.listdir(backup_dir):
            if fn.startswith("auto_backup_") and fn.endswith(".md"):
                fp = os.path.join(backup_dir, fn)
                auto_backups.append((fp, os.path.getmtime(fp)))
        auto_backups.sort(key=lambda x: x[1], reverse=True)
        for fp, _ in auto_backups[self._config.max_backups:]:
            try:
                os.remove(fp)
                self._mw.log(
                    f"Pruned old backup: {os.path.basename(fp)}")
            except Exception as e:
                self._mw.log(f"Error pruning {fp}: {e}")

    def stop(self) -> None:
        """Stop the observer (call on app close)."""
        if self._debounce_timer is not None:
            self._debounce_timer.stop()
        self._stop_monitoring()
