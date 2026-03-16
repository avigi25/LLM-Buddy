"""Rollback panel – restore files from combined backup files."""

import os

from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QStandardItemModel, QStandardItem, QColor, QSyntaxHighlighter, QTextCharFormat
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QLabel, QLineEdit, QPushButton, QTreeView, QPlainTextEdit,
    QGroupBox, QFileDialog, QMessageBox, QHeaderView,
)

from llm_buddy.core.rollback import parse_combined_file, restore_file, get_file_diff
from llm_buddy.paths import get_backup_dir
from llm_buddy.qt.theme import get_theme_colors, current_theme_name

class DiffHighlighter(QSyntaxHighlighter):
    """Highlights unified diff output to show additions and deletions in color."""
    
    def highlightBlock(self, text: str) -> None:
        # Fetch current theme colors dynamically so it respects theme switches
        colors = get_theme_colors(current_theme_name())
        
        if text.startswith('+') and not text.startswith('+++'):
            fmt = QTextCharFormat()
            fmt.setForeground(QColor(colors["success"]))
            self.setFormat(0, len(text), fmt)
            
        elif text.startswith('-') and not text.startswith('---'):
            fmt = QTextCharFormat()
            fmt.setForeground(QColor(colors["error"]))
            self.setFormat(0, len(text), fmt)
            
        elif text.startswith('@@') or text.startswith('+++') or text.startswith('---'):
            fmt = QTextCharFormat()
            fmt.setForeground(QColor(colors["accent"]))
            self.setFormat(0, len(text), fmt)

class RollbackPanel(QWidget):
    """Restore individual files from a combined backup file.

    Layout: top row (backup file picker) + horizontal splitter
    (file list | diff preview) + bottom restore button.
    """

    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self._mw = main_window
        self._backup_files: dict[str, str] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        top_row = QHBoxLayout()
        top_row.addWidget(QLabel("Backup File:"))
        self._path_edit = QLineEdit()
        self._path_edit.setPlaceholderText("Select a .md backup file...")
        top_row.addWidget(self._path_edit, stretch=1)

        btn_browse = QPushButton("Browse")
        btn_browse.setToolTip(
            "Open a file dialog to locate a combined backup (.md) file on disk")
        btn_browse.clicked.connect(self._browse)
        top_row.addWidget(btn_browse)

        btn_load = QPushButton("Load")
        btn_load.setToolTip(
            "Parse the selected backup file and list all restorable files.\n"
            "Each file is compared against its current version on disk\n"
            "to show whether it is Modified, Unchanged, or Missing.")
        btn_load.clicked.connect(self._load)
        top_row.addWidget(btn_load)
        layout.addLayout(top_row)

        splitter = QSplitter(Qt.Horizontal)

        # File list
        left = QGroupBox("Files to Restore")
        left_layout = QVBoxLayout(left)
        self._model = QStandardItemModel()
        self._model.setHorizontalHeaderLabels(["File Path", "Status"])
        self._tree = QTreeView()
        self._tree.setModel(self._model)
        self._tree.setRootIsDecorated(False)
        self._tree.setAlternatingRowColors(True)
        self._tree.setSelectionMode(QTreeView.ExtendedSelection)
        header = self._tree.header()
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.setStretchLastSection(True)
        header.resizeSection(0, 400)
        self._tree.selectionModel().selectionChanged.connect(
            self._show_diff)
        left_layout.addWidget(self._tree)

        sel_row = QHBoxLayout()
        btn_all = QPushButton("Select All")
        btn_all.clicked.connect(self._select_all)
        sel_row.addWidget(btn_all)
        btn_none = QPushButton("Deselect All")
        btn_none.clicked.connect(self._deselect_all)
        sel_row.addWidget(btn_none)
        btn_toggle = QPushButton("Toggle")
        btn_toggle.clicked.connect(self._toggle)
        sel_row.addWidget(btn_toggle)
        sel_row.addStretch()
        left_layout.addLayout(sel_row)

        splitter.addWidget(left)

        # Diff preview
        right = QGroupBox("Diff Preview")
        right_layout = QVBoxLayout(right)
        self._diff_text = QPlainTextEdit()
        self._diff_text.setReadOnly(True)
        self._diff_text.setLineWrapMode(QPlainTextEdit.NoWrap)
        self._highlighter = DiffHighlighter(self._diff_text.document())
        right_layout.addWidget(self._diff_text)
        splitter.addWidget(right)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        layout.addWidget(splitter, stretch=1)

        bot = QHBoxLayout()
        bot.addStretch()
        btn_restore = QPushButton("Restore Selected Files")
        btn_restore.setProperty("class", "primary")
        btn_restore.setToolTip(
            "Overwrite the current on-disk files with the versions\n"
            "stored in the loaded backup for every selected row")
        btn_restore.clicked.connect(self._restore)
        bot.addWidget(btn_restore)
        layout.addLayout(bot)

    # -- actions -------------------------------------------------------

    @Slot()
    def _browse(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Backup File", get_backup_dir(),
            "Markdown files (*.md);;All files (*.*)")
        if path:
            self._path_edit.setText(path)
            self._load()

    @Slot()
    def _load(self) -> None:
        path = self._path_edit.text().strip()
        if not path or not os.path.exists(path):
            QMessageBox.warning(self, "Error",
                                "Please select a valid backup file.")
            return

        self._backup_files = parse_combined_file(path)
        self._model.removeRows(0, self._model.rowCount())

        for fp, content in self._backup_files.items():
            if os.path.exists(fp):
                try:
                    with open(fp, "r", encoding="utf-8") as f:
                        current = f.read()
                    status = "Unchanged" if current == content else "Modified"
                except Exception:
                    status = "Error reading"
            else:
                status = "Missing"

            path_item = QStandardItem(fp)
            path_item.setEditable(False)
            path_item.setToolTip(fp)
            stat_item = QStandardItem(status)
            stat_item.setEditable(False)
            stat_item.setToolTip(status)
            if status == "Modified":
                colors = get_theme_colors(current_theme_name())
                stat_item.setForeground(QColor(colors["warning"]))
            elif status == "Missing":
                colors = get_theme_colors(current_theme_name())
                stat_item.setForeground(QColor(colors["error"]))
            self._model.appendRow([path_item, stat_item])

        self._mw.log(
            f"Loaded backup: {path} ({len(self._backup_files)} files)")

    @Slot()
    def _show_diff(self) -> None:
        indexes = self._tree.selectionModel().selectedRows()
        if not indexes:
            return
        fp = self._model.item(indexes[0].row(), 0).text()
        if fp not in self._backup_files:
            return
        diff = get_file_diff(fp, self._backup_files[fp])
        self._diff_text.setPlainText(diff)

    @Slot()
    def _select_all(self) -> None:
        sel = self._tree.selectionModel()
        for r in range(self._model.rowCount()):
            sel.select(self._model.index(r, 0),
                       sel.Select | sel.Rows)

    @Slot()
    def _deselect_all(self) -> None:
        self._tree.clearSelection()

    @Slot()
    def _toggle(self) -> None:
        sel = self._tree.selectionModel()
        for r in range(self._model.rowCount()):
            idx = self._model.index(r, 0)
            if sel.isSelected(idx):
                sel.select(idx, sel.Deselect | sel.Rows)
            else:
                sel.select(idx, sel.Select | sel.Rows)

    @Slot()
    def _restore(self) -> None:
        indexes = self._tree.selectionModel().selectedRows()
        if not indexes:
            QMessageBox.information(self, "Info",
                                    "No files selected for restore.")
            return
        selected = [self._model.item(idx.row(), 0).text()
                    for idx in indexes]

        answer = QMessageBox.question(
            self, "Confirm Restore",
            f"Restore {len(selected)} files?\n"
            "This will overwrite the current versions.",
            QMessageBox.Yes | QMessageBox.No)
        if answer != QMessageBox.Yes:
            return

        ok, err, err_files = 0, 0, []
        for fp in selected:
            if fp in self._backup_files:
                if restore_file(fp, self._backup_files[fp]):
                    ok += 1
                    self._mw.log(f"Restored file: {fp}")
                else:
                    err += 1
                    err_files.append(fp)
                    self._mw.log(f"Failed to restore: {fp}")

        # Refresh statuses in tree
        self._load()

        if err == 0:
            QMessageBox.information(
                self, "Success", f"Restored {ok} files successfully.")
        else:
            QMessageBox.warning(
                self, "Partial Success",
                f"Restored {ok} files.\nFailed: {err}.\nSee log.")
