"""eADR (Elaborated Action Design Research) notes panel for the Qt GUI."""

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QKeySequence, QShortcut, QStandardItemModel, QStandardItem
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QLabel, QLineEdit, QPushButton, QPlainTextEdit, QTextBrowser,
    QTreeView, QGroupBox, QMessageBox, QHeaderView,
)


class EadrPanel(QWidget):
    """eADR note management panel.

    Provides:
    - Project name field
    - Note editor for new notes
    - History tree showing all saved notes
    - Read-only display of selected note content
    """

    note_saved = Signal()  # emitted after a note is saved

    def __init__(self, log_fn=None, toast_fn=None, db=None, parent=None):
        super().__init__(parent)
        self._log = log_fn or (lambda m: None)
        self._show_toast = toast_fn or (lambda msg, level="info": None)
        self._db = db
        self._notes: list = []  # cached EadrNote list (newest-first)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        proj_row = QHBoxLayout()
        proj_row.addWidget(QLabel("Project:"))
        self._project_entry = QLineEdit("Origin")
        self._project_entry.setMaximumWidth(200)
        proj_row.addWidget(self._project_entry)
        proj_row.addStretch()
        layout.addLayout(proj_row)

        splitter = QSplitter(Qt.Vertical)
        layout.addWidget(splitter, stretch=1)

        editor_group = QGroupBox("New Note")
        editor_layout = QVBoxLayout(editor_group)
        self._note_edit = QPlainTextEdit()
        self._note_edit.setPlaceholderText("Type your eADR note here...")
        editor_layout.addWidget(self._note_edit)

        btn_row = QHBoxLayout()
        btn_save = QPushButton("Save Note")
        btn_save.setProperty("class", "primary")
        btn_save.clicked.connect(self._save_note)
        btn_row.addWidget(btn_save)
        btn_clear = QPushButton("Clear")
        btn_clear.clicked.connect(self._note_edit.clear)
        btn_row.addWidget(btn_clear)
        btn_row.addStretch()
        editor_layout.addLayout(btn_row)
        splitter.addWidget(editor_group)

        bottom = QSplitter(Qt.Horizontal)

        # History tree
        history_group = QGroupBox("Note History")
        history_layout = QVBoxLayout(history_group)
        self._model = QStandardItemModel()
        self._model.setHorizontalHeaderLabels(["Date & Time", "Project"])
        self._tree = QTreeView()
        self._tree.setModel(self._model)
        self._tree.setRootIsDecorated(False)
        self._tree.setAlternatingRowColors(True)
        self._tree.setSelectionMode(QTreeView.SingleSelection)
        header = self._tree.header()
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.setStretchLastSection(True)
        header.resizeSection(0, 180)
        self._tree.selectionModel().selectionChanged.connect(
            self._on_selection_changed)
        history_layout.addWidget(self._tree)
        bottom.addWidget(history_group)

        # Display area
        display_group = QGroupBox("Note Content")
        display_layout = QVBoxLayout(display_group)
        self._display = QTextBrowser()
        self._display.setPlaceholderText("Select a note to view its content.")
        display_layout.addWidget(self._display)

        self._btn_delete = QPushButton("Delete Selected Note")
        self._btn_delete.setProperty("class", "danger")
        self._btn_delete.setEnabled(False)
        self._btn_delete.clicked.connect(self._delete_note)
        display_layout.addWidget(self._btn_delete)
        bottom.addWidget(display_group)

        splitter.addWidget(bottom)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)

        self._refresh_history()

        sc_save = QShortcut(QKeySequence("Ctrl+S"), self)
        sc_save.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        sc_save.activated.connect(self._save_note)

    @property
    def project(self) -> str:
        return self._project_entry.text().strip() or "Origin"

    @property
    def note_text(self) -> str:
        """Return text currently in the editor (used by combine-scripts)."""
        return self._note_edit.toPlainText().strip()

    def clear_editor(self) -> None:
        self._note_edit.clear()

    def set_db(self, db) -> None:
        """Set the database reference after construction."""
        self._db = db
        self._refresh_history()

    # -- internal slots ------------------------------------------------

    @Slot()
    def _save_note(self) -> None:
        text = self._note_edit.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "Empty Note",
                                "Please enter a note before saving.")
            return
        project = self.project
        if self._db is None:
            QMessageBox.critical(self, "Error",
                                 "Database not available.")
            return
        note_id = self._db.add_eadr_note(text, project)
        if note_id >= 0:
            self._log(f"eADR note saved for project: {project}")
            self._note_edit.clear()
            self._refresh_history()
            self.note_saved.emit()
            self._show_toast("eADR note saved.", "success")
        else:
            QMessageBox.critical(self, "Error", "Failed to save eADR note.")

    @Slot()
    def _refresh_history(self) -> None:
        if self._db is not None:
            self._notes = self._db.get_eadr_notes()
        else:
            self._notes = []
        self._model.removeRows(0, self._model.rowCount())
        for note in self._notes:  # already newest-first from db
            ts_item = QStandardItem(note.timestamp)
            ts_item.setEditable(False)
            ts_item.setToolTip(note.timestamp)
            proj_item = QStandardItem(note.project)
            proj_item.setEditable(False)
            proj_item.setToolTip(note.project)
            self._model.appendRow([ts_item, proj_item])
        self._btn_delete.setEnabled(False)
        self._display.clear()

    def refresh(self) -> None:
        """Public method so other panels can trigger a refresh."""
        self._refresh_history()

    @Slot()
    def _on_selection_changed(self) -> None:
        indexes = self._tree.selectionModel().selectedRows()
        if not indexes:
            self._btn_delete.setEnabled(False)
            self._display.clear()
            return
        row = indexes[0].row()
        if 0 <= row < len(self._notes):
            note = self._notes[row]
            html = (
                f"<b>Project:</b> {note.project}<br>"
                f"<b>Date &amp; Time:</b> {note.timestamp}<br><br>"
                f"<pre>{note.note}</pre>"
            )
            self._display.setHtml(html)
            self._btn_delete.setEnabled(True)

    @Slot()
    def _delete_note(self) -> None:
        indexes = self._tree.selectionModel().selectedRows()
        if not indexes:
            return
        row = indexes[0].row()
        if row < 0 or row >= len(self._notes):
            return
        note = self._notes[row]

        answer = QMessageBox.question(
            self, "Confirm Deletion",
            "Are you sure you want to delete this note?\n"
            "This action cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return

        if self._db and self._db.delete_eadr_note(note.id):
            self._log(
                f"Deleted note from {note.timestamp} "
                f"for project '{note.project}'")
            self._refresh_history()
            self._show_toast("Note deleted.", "info")
        else:
            QMessageBox.critical(self, "Error", "Failed to delete note.")
