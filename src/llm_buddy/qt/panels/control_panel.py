"""Left-hand control panel for the Qt GUI.

Provides folder/file selection, filter controls, header/footer fields,
combine-scripts action, progress bar, and file/folder tree views.
"""

import os
from datetime import datetime

from PySide6.QtCore import Qt, Signal, Slot, QThread, QObject
from PySide6.QtGui import QStandardItemModel, QStandardItem
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
    QLineEdit, QPushButton, QProgressBar, QTreeView, QFileDialog,
    QMessageBox, QHeaderView,
)

from llm_buddy.core.tokens import (
    build_combined_text, count_tokens,
)
from llm_buddy.services.file_service import (
    scan_folder, filter_files,
    parse_extensions, parse_ignored_folders,
)


class _ScanWorker(QObject):
    """Scans folders in a background QThread."""

    progress = Signal(int, int)  # (current, total)
    file_found = Signal(str)
    finished = Signal(list)  # all found files

    def __init__(self, folders, allowed_ext, ignored):
        super().__init__()
        self._folders = folders
        self._ext = allowed_ext
        self._ignored = ignored

    @Slot()
    def run(self):
        found = []
        total = len(self._folders)
        for i, folder in enumerate(self._folders, 1):
            for path in scan_folder(folder, self._ext, self._ignored):
                if path not in found:
                    found.append(path)
                    self.file_found.emit(path)
            self.progress.emit(i, total)
        self.finished.emit(found)


class ControlPanel(QWidget):
    """Left-side control panel with file/folder management.

    Emits ``files_changed(list)`` when the filtered file list is updated,
    carrying a list of ``(path, tokens)`` tuples.
    """

    files_changed = Signal(list)

    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self._mw = main_window  # reference back for shared state
        self._scan_thread: QThread | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        sel_group = QGroupBox("Selection")
        sel_layout = QHBoxLayout(sel_group)
        btn_folder = QPushButton("Add Folder")
        btn_folder.clicked.connect(self._add_folder)
        sel_layout.addWidget(btn_folder)
        btn_files = QPushButton("Add File(s)")
        btn_files.clicked.connect(self._add_files)
        sel_layout.addWidget(btn_files)
        btn_scan = QPushButton("Scan Folders")
        btn_scan.setProperty("class", "primary")
        btn_scan.clicked.connect(self._scan_folders)
        sel_layout.addWidget(btn_scan)
        layout.addWidget(sel_group)

        filt_group = QGroupBox("Filters")
        filt_layout = QVBoxLayout(filt_group)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Extensions:"))
        self._ext_entry = QLineEdit(self._mw.allowed_extensions)
        self._ext_entry.setPlaceholderText("e.g. .py,.js,.ts,.md")
        self._ext_entry.setToolTip("Comma-separated file extensions to include")
        row1.addWidget(self._ext_entry, stretch=1)
        filt_layout.addLayout(row1)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Min Tokens:"))
        self._min_tok_entry = QLineEdit(str(self._mw.min_tokens))
        self._min_tok_entry.setMaximumWidth(80)
        self._min_tok_entry.setPlaceholderText("e.g. 50")
        self._min_tok_entry.setToolTip("Exclude files with fewer tokens than this")
        row2.addWidget(self._min_tok_entry)
        row2.addStretch()
        filt_layout.addLayout(row2)

        row3 = QHBoxLayout()
        row3.addWidget(QLabel("Ignore Folders:"))
        self._ignore_entry = QLineEdit(
            "node_modules, __pycache__, Archive, archive, venv, ex, .venv, .claude")
        self._ignore_entry.setPlaceholderText("e.g. node_modules, .git, __pycache__")
        self._ignore_entry.setToolTip("Comma-separated folder names to skip during scanning")
        row3.addWidget(self._ignore_entry, stretch=1)
        filt_layout.addLayout(row3)

        btn_apply = QPushButton("Apply Filters")
        btn_apply.clicked.connect(self.apply_filters)
        filt_layout.addWidget(btn_apply)
        layout.addWidget(filt_group)

        hf_group = QGroupBox("Header / Footer")
        hf_layout = QVBoxLayout(hf_group)
        r1 = QHBoxLayout()
        r1.addWidget(QLabel("Header:"))
        self._header_entry = QLineEdit()
        r1.addWidget(self._header_entry, stretch=1)
        hf_layout.addLayout(r1)
        r2 = QHBoxLayout()
        r2.addWidget(QLabel("Footer:"))
        self._footer_entry = QLineEdit()
        r2.addWidget(self._footer_entry, stretch=1)
        hf_layout.addLayout(r2)
        layout.addWidget(hf_group)

        action_row = QHBoxLayout()
        btn_combine = QPushButton("Combine Scripts")
        btn_combine.setProperty("class", "primary")
        btn_combine.clicked.connect(self._combine_scripts)
        action_row.addWidget(btn_combine)
        action_row.addStretch()
        layout.addLayout(action_row)

        self._progress = QProgressBar()
        self._progress.setTextVisible(True)
        self._progress.setFormat("%v / %m folders scanned")
        layout.addWidget(self._progress)

        file_group = QGroupBox("Selected Files")
        file_layout = QVBoxLayout(file_group)
        self._file_model = QStandardItemModel()
        self._file_model.setHorizontalHeaderLabels(["File Path", "Tokens"])
        self._file_tree = QTreeView()
        self._file_tree.setModel(self._file_model)
        self._file_tree.setRootIsDecorated(False)
        self._file_tree.setAlternatingRowColors(True)
        self._file_tree.setSelectionMode(QTreeView.ExtendedSelection)
        fh = self._file_tree.header()
        fh.setSectionResizeMode(QHeaderView.Interactive)
        fh.setStretchLastSection(True)
        fh.resizeSection(0, 300)

        self._file_empty_label = QLabel(
            "No files added yet\n\n"
            "Click  Add Folder  or  Add File(s)  to begin")
        self._file_empty_label.setAlignment(Qt.AlignCenter)
        self._file_empty_label.setStyleSheet(
            "color: palette(mid); padding: 24px;")
        file_layout.addWidget(self._file_empty_label)
        file_layout.addWidget(self._file_tree)
        btn_rm_file = QPushButton("Remove Selected File(s)")
        btn_rm_file.setProperty("class", "danger")
        btn_rm_file.clicked.connect(self._remove_selected_files)
        file_layout.addWidget(btn_rm_file)
        layout.addWidget(file_group, stretch=1)

        folder_group = QGroupBox("Selected Folders")
        folder_layout = QVBoxLayout(folder_group)
        self._folder_model = QStandardItemModel()
        self._folder_model.setHorizontalHeaderLabels(
            ["Folder Path", "Tokens"])
        self._folder_tree = QTreeView()
        self._folder_tree.setModel(self._folder_model)
        self._folder_tree.setRootIsDecorated(False)
        self._folder_tree.setAlternatingRowColors(True)
        self._folder_tree.setSelectionMode(QTreeView.ExtendedSelection)
        dh = self._folder_tree.header()
        dh.setSectionResizeMode(QHeaderView.Interactive)
        dh.setStretchLastSection(True)
        dh.resizeSection(0, 300)
        folder_layout.addWidget(self._folder_tree)
        btn_rm_folder = QPushButton("Remove Selected Folder(s)")
        btn_rm_folder.setProperty("class", "danger")
        btn_rm_folder.clicked.connect(self._remove_selected_folders)
        folder_layout.addWidget(btn_rm_folder)
        layout.addWidget(folder_group, stretch=1)

    # -- public accessors / mutators ------------------------------------

    @property
    def header(self) -> str:
        return self._header_entry.text()

    @property
    def header_text(self) -> str:
        """Alias used by main_window for profile save."""
        return self._header_entry.text()

    @property
    def footer(self) -> str:
        return self._footer_entry.text()

    @property
    def footer_text(self) -> str:
        """Alias used by main_window for profile save."""
        return self._footer_entry.text()

    @property
    def extensions_raw(self) -> str:
        return self._ext_entry.text()

    @property
    def ignored_folders_raw(self) -> str:
        return self._ignore_entry.text()

    def set_extensions(self, text: str) -> None:
        """Set the extensions filter field (called when loading a profile)."""
        self._ext_entry.setText(text)

    def set_min_tokens(self, value: int) -> None:
        """Set the min-tokens filter field."""
        self._min_tok_entry.setText(str(value))

    def set_header(self, text: str) -> None:
        """Set the header field (called when loading a profile)."""
        self._header_entry.setText(text)

    def set_footer(self, text: str) -> None:
        """Set the footer field (called when loading a profile)."""
        self._footer_entry.setText(text)

    def combine_scripts(self) -> None:
        """Public interface to trigger combine scripts (e.g. from menu)."""
        self._combine_scripts()

    # -- actions --------------------------------------------------------

    @Slot()
    def _add_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder and folder not in self._mw.folders:
            self._mw.folders.append(folder)
            self._mw.log(f"Added folder: {folder}")
            # Quick scan
            ext = parse_extensions(self._ext_entry.text())
            ign = parse_ignored_folders(self._ignore_entry.text())
            for path in scan_folder(folder, ext, ign):
                if path not in self._mw.all_files:
                    self._mw.all_files.append(path)
            self.apply_filters()

    @Slot()
    def _add_files(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Select File(s)", "",
            "Supported files (*.py *.kt *.xml *.html *.js *.txt *.md "
            "*.json *.css *.bat *.p12 *.pem *.sh *.env *.R *.toml);;"
            "All files (*.*)")
        for p in paths:
            if p not in self._mw.all_files:
                self._mw.all_files.append(p)
                self._mw.log(f"Added file: {p}")
        if paths:
            self.apply_filters()

    @Slot()
    def _scan_folders(self) -> None:
        if not self._mw.folders:
            self._mw.log("No folders to scan.")
            return
        ext = parse_extensions(self._ext_entry.text())
        ign = parse_ignored_folders(self._ignore_entry.text())

        self._scan_thread = QThread()
        worker = _ScanWorker(self._mw.folders, ext, ign)
        worker.moveToThread(self._scan_thread)
        self._scan_thread.started.connect(worker.run)
        worker.progress.connect(self._on_scan_progress)
        worker.file_found.connect(self._on_file_found)
        worker.finished.connect(self._on_scan_finished)
        worker.finished.connect(self._scan_thread.quit)
        # prevent GC
        self._scan_worker = worker
        self._scan_thread.start()

    @Slot(int, int)
    def _on_scan_progress(self, current, total):
        self._progress.setMaximum(total)
        self._progress.setValue(current)

    @Slot(str)
    def _on_file_found(self, path):
        if path not in self._mw.all_files:
            self._mw.all_files.append(path)

    @Slot(list)
    def _on_scan_finished(self, _found):
        self._progress.setValue(0)
        self._mw.log("Folder scanning complete.")
        self.apply_filters()

    @Slot()
    def apply_filters(self) -> None:
        """Re-filter files and update both tree views."""
        self._mw.allowed_extensions = self._ext_entry.text()
        try:
            self._mw.min_tokens = int(self._min_tok_entry.text())
        except (ValueError, TypeError):
            self._mw.min_tokens = 0

        ext = parse_extensions(self._mw.allowed_extensions)
        filtered = filter_files(
            self._mw.all_files, ext, self._mw.min_tokens)
        self._mw.filtered_files = filtered

        # Update file tree
        self._file_model.removeRows(0, self._file_model.rowCount())
        for path, tokens in filtered:
            path_item = QStandardItem(path)
            path_item.setEditable(False)
            path_item.setToolTip(path)
            tok_item = QStandardItem(f"{tokens:,}")
            tok_item.setEditable(False)
            tok_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self._file_model.appendRow([path_item, tok_item])

        has_files = self._file_model.rowCount() > 0
        self._file_empty_label.setVisible(not has_files)
        self._file_tree.setVisible(has_files)

        self._mw.log(f"Filter applied: {len(filtered)} files shown.")

        # Update folder tree — token counts based on the *filtered* list
        # (not a disk rescan) so that removing files is reflected.
        self._folder_model.removeRows(0, self._folder_model.rowCount())
        for folder in self._mw.folders:
            # Sum tokens of filtered files that belong to this folder
            folder_prefix = folder + os.sep
            tokens = sum(
                t for p, t in filtered
                if p.startswith(folder_prefix) or p.startswith(folder + "/")
            )
            f_item = QStandardItem(folder)
            f_item.setEditable(False)
            f_item.setToolTip(folder)
            t_item = QStandardItem(f"{tokens:,}")
            t_item.setEditable(False)
            t_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self._folder_model.appendRow([f_item, t_item])

        self.files_changed.emit(filtered)

    @Slot()
    def _remove_selected_files(self) -> None:
        indexes = self._file_tree.selectionModel().selectedRows()
        if not indexes:
            return
        paths_to_remove = []
        for idx in indexes:
            path = self._file_model.item(idx.row(), 0).text()
            paths_to_remove.append(path)
        for p in paths_to_remove:
            if p in self._mw.all_files:
                self._mw.all_files.remove(p)
            self._mw.log(f"Removed file: {p}")
        self.apply_filters()

    @Slot()
    def _remove_selected_folders(self) -> None:
        indexes = self._folder_tree.selectionModel().selectedRows()
        if not indexes:
            return
        folders_to_remove = []
        for idx in indexes:
            folder = self._folder_model.item(idx.row(), 0).text()
            folders_to_remove.append(folder)
        for folder in folders_to_remove:
            if folder in self._mw.folders:
                self._mw.folders.remove(folder)
            to_rm = [f for f in self._mw.all_files
                     if f.startswith(folder)]
            for f in to_rm:
                self._mw.all_files.remove(f)
            self._mw.log(f"Removed folder: {folder}")
        self.apply_filters()

    # -- Combine scripts -----------------------------------------------

    @Slot()
    def _combine_scripts(self) -> None:
        filtered = self._mw.filtered_files
        file_paths = [p for p, _t in filtered]
        if not file_paths:
            QMessageBox.warning(
                self, "Error", "No files selected after filtering.")
            return

        combined = build_combined_text(
            file_paths, self.header, self.footer)
        total_tokens = count_tokens(combined)

        default_dir = os.path.join(os.getcwd(), "backup")
        os.makedirs(default_dir, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"combined_scripts_{ts}_{total_tokens}tokens.md"

        output_file, _ = QFileDialog.getSaveFileName(
            self, "Save Combined Scripts As",
            os.path.join(default_dir, default_name),
            "Markdown files (*.md);;Text files (*.txt);;All files (*.*)")
        if not output_file:
            return

        try:
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(combined)
            self._mw.log(f"Combined file created: {output_file}")

            # Auto eADR note
            eadr_panel = self._mw.findChild(
                QWidget, "eadr_panel")  # type: ignore[arg-type]
            project = "Origin"
            user_note = ""
            if hasattr(self._mw, '_eadr_panel'):
                project = self._mw._eadr_panel.project
                user_note = self._mw._eadr_panel.note_text
                if user_note:
                    self._mw._eadr_panel.clear_editor()

            from llm_buddy.services.preview_service import (
                build_combine_eadr_note,
            )
            note_text = build_combine_eadr_note(
                folders=self._mw.folders,
                filtered_files=file_paths,
                allowed_extensions=self._mw.allowed_extensions,
                min_tokens=self._mw.min_tokens,
                ignored_folders=self._ignore_entry.text(),
                output_file=output_file,
                total_tokens=total_tokens,
                user_note=user_note,
            )
            note_id = self._mw.prompt_database.add_eadr_note(
                note_text, project)
            if note_id >= 0:
                self._mw.log(
                    "eADR note automatically created for combined scripts")
                if hasattr(self._mw, '_eadr_panel'):
                    self._mw._eadr_panel.refresh()

            QMessageBox.information(
                self, "Success",
                f"Combined file saved to:\n{output_file}")
        except Exception as e:
            self._mw.log(f"Error writing output file: {e}")
            QMessageBox.critical(
                self, "Error", f"Failed to save output file:\n{e}")
