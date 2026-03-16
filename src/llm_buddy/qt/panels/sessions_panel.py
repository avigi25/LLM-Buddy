"""Research Sessions panel for the Qt GUI.

Allows the user to start/end named research sessions that group
prompts, file changes, and eADR notes into bounded work periods.
On session close an exportable "methods appendix" summary is
generated automatically.

Supports pause/resume and protects against accidental session end
with a confirmation dialog and a "Reopen" option.
"""

import logging
import os
from datetime import datetime

from PySide6.QtCore import Qt, Signal, Slot, QTimer
from PySide6.QtGui import QFont, QKeySequence, QShortcut, QStandardItem, QStandardItemModel
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QTreeView,
    QVBoxLayout,
    QWidget,
)

from llm_buddy.core.sessions import (
    ResearchSession,
    capture_snapshot,
    compute_session_diff,
    generate_session_summary_markdown,
)
from llm_buddy.qt.theme import get_theme_colors, current_theme_name

logger = logging.getLogger(__name__)



class _SummaryDialog(QDialog):
    """Modal dialog that displays a session summary in monospace text."""

    def __init__(self, session: ResearchSession, md_text: str,
                 export_fn, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Session Summary \u2013 {session.name}")
        self.resize(700, 550)

        self._md_text = md_text
        self._session = session
        self._export_fn = export_fn

        layout = QVBoxLayout(self)

        # Read-only monospace text area
        self._text_edit = QPlainTextEdit()
        self._text_edit.setReadOnly(True)
        self._text_edit.setFont(QFont("Consolas", 10))
        self._text_edit.setPlainText(md_text)
        layout.addWidget(self._text_edit)

        # Button row
        btn_layout = QHBoxLayout()

        btn_copy = QPushButton("Copy to Clipboard")
        btn_copy.clicked.connect(self._copy_to_clipboard)
        btn_layout.addWidget(btn_copy)

        btn_export = QPushButton("Export .md")
        btn_export.clicked.connect(self._export)
        btn_layout.addWidget(btn_export)

        btn_layout.addStretch()

        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.accept)
        btn_layout.addWidget(btn_close)

        layout.addLayout(btn_layout)

    @Slot()
    def _copy_to_clipboard(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self._md_text)
        QMessageBox.information(self, "Copied",
                                "Summary copied to clipboard.")

    @Slot()
    def _export(self):
        self._export_fn(self._session, self._md_text)



class SessionsPanel(QWidget):
    """Research session management panel.

    Provides start/pause/resume/end session controls, live elapsed-time
    and prompt counters, session notes, and a history table with
    context-menu actions (view summary, export markdown, reopen, delete).
    """

    # Emitted every second while a session is active/paused.
    # Args: session_name (str), elapsed_str (str), is_paused (bool)
    # Emitted with empty strings when no session is active.
    session_state_changed = Signal(str, str, bool)

    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self._mw = main_window

        self._sessions: list[ResearchSession] = []
        self._active_session: ResearchSession | None = None
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._update_session_timer)

        # Load persisted sessions
        db = self._mw.prompt_database
        self._sessions = db.get_sessions()
        self._active_session = next(
            (s for s in self._sessions if s.status in ("active", "paused")), None)

        self._build_ui()
        self._refresh_session_tree()

        # Restore active-session UI if one was running (or paused)
        if self._active_session:
            self._set_active_session_ui(self._active_session)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        active_group = QGroupBox("Active Session")
        active_layout = QVBoxLayout(active_group)

        btn_row = QHBoxLayout()
        self._btn_start = QPushButton("Start Session")
        self._btn_start.setProperty("class", "primary")
        self._btn_start.clicked.connect(self.start_new_session)
        btn_row.addWidget(self._btn_start)

        self._btn_pause = QPushButton("\u23f8 Pause")
        self._btn_pause.setEnabled(False)
        self._btn_pause.setToolTip("Pause the session timer")
        self._btn_pause.clicked.connect(self._toggle_pause)
        btn_row.addWidget(self._btn_pause)

        self._btn_end = QPushButton("End Session")
        self._btn_end.setProperty("class", "danger")
        self._btn_end.setEnabled(False)
        self._btn_end.clicked.connect(self.end_current_session)
        btn_row.addWidget(self._btn_end)

        btn_row.addStretch()
        active_layout.addLayout(btn_row)

        # Status info row
        info_row = QHBoxLayout()
        self._name_label = QLabel("No active session")
        font = self._name_label.font()
        font.setBold(True)
        font.setPointSize(font.pointSize() + 1)
        self._name_label.setFont(font)
        info_row.addWidget(self._name_label)

        # Prominent monospace timer display
        self._elapsed_label = QLabel("")
        timer_font = QFont("Consolas", 18)
        timer_font.setBold(True)
        self._elapsed_label.setFont(timer_font)
        self._elapsed_label.setStyleSheet(
            "padding: 4px 16px;"
            "border: 1px solid palette(mid);"
            "border-radius: 6px;"
            "background: palette(base);"
        )
        self._elapsed_label.setMinimumWidth(160)
        self._elapsed_label.setAlignment(Qt.AlignCenter)
        info_row.addWidget(self._elapsed_label)

        self._prompt_label = QLabel("")
        prompt_font = QFont()
        prompt_font.setBold(True)
        self._prompt_label.setFont(prompt_font)
        info_row.addWidget(self._prompt_label)

        self._status_label = QLabel("")
        info_row.addWidget(self._status_label)

        info_row.addStretch()
        active_layout.addLayout(info_row)

        layout.addWidget(active_group)

        notes_group = QGroupBox("Session Notes")
        notes_layout = QVBoxLayout(notes_group)
        self._notes_edit = QPlainTextEdit()
        self._notes_edit.setMaximumHeight(100)
        notes_layout.addWidget(self._notes_edit)
        layout.addWidget(notes_group)

        history_group = QGroupBox("Session History")
        history_layout = QVBoxLayout(history_group)

        self._history_model = QStandardItemModel()
        self._history_model.setHorizontalHeaderLabels(
            ["Session Name", "Date", "Duration", "Prompts", "Status"])

        self._history_tree = QTreeView()
        self._history_tree.setModel(self._history_model)
        self._history_tree.setRootIsDecorated(False)
        self._history_tree.setAlternatingRowColors(True)
        self._history_tree.setSelectionMode(QTreeView.SingleSelection)
        self._history_tree.setSelectionBehavior(QTreeView.SelectRows)

        header = self._history_tree.header()
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.setStretchLastSection(True)
        header.resizeSection(0, 250)
        header.resizeSection(1, 100)
        header.resizeSection(2, 90)
        header.resizeSection(3, 70)

        self._history_tree.doubleClicked.connect(
            self._on_double_click)
        self._history_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self._history_tree.customContextMenuRequested.connect(
            self._on_context_menu)

        self._sessions_empty_label = QLabel(
            "No sessions yet\n\n"
            "Click  Start Session  to begin tracking your workflow")
        self._sessions_empty_label.setAlignment(Qt.AlignCenter)
        self._sessions_empty_label.setStyleSheet(
            "color: palette(mid); padding: 24px;")
        history_layout.addWidget(self._sessions_empty_label)
        history_layout.addWidget(self._history_tree)

        # Bottom button row
        bottom_row = QHBoxLayout()
        btn_view = QPushButton("View Summary")
        btn_view.clicked.connect(self._ctx_view_summary)
        bottom_row.addWidget(btn_view)

        btn_export = QPushButton("Export Markdown")
        btn_export.clicked.connect(self._ctx_export_markdown)
        bottom_row.addWidget(btn_export)

        self._btn_reopen = QPushButton("Reopen")
        self._btn_reopen.setToolTip(
            "Reopen a completed session if it was ended by mistake")
        self._btn_reopen.clicked.connect(self._ctx_reopen_session)
        bottom_row.addWidget(self._btn_reopen)

        btn_delete = QPushButton("Delete")
        btn_delete.setProperty("class", "danger")
        btn_delete.clicked.connect(self._ctx_delete_session)
        bottom_row.addWidget(btn_delete)

        bottom_row.addStretch()
        history_layout.addLayout(bottom_row)

        layout.addWidget(history_group, stretch=1)

        sc_session = QShortcut(QKeySequence("Ctrl+Shift+S"), self)
        sc_session.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        sc_session.activated.connect(self._shortcut_session_toggle)

    @Slot()
    def _shortcut_session_toggle(self):
        """Ctrl+Shift+S: start a new session or pause/resume the active one."""
        if self._active_session:
            self._toggle_pause()
        else:
            self.start_new_session()

    @Slot()
    def start_new_session(self):
        """Prompt for a name and start a new research session."""
        if self._active_session:
            QMessageBox.warning(
                self, "Session Active",
                f"A session is already running: "
                f"'{self._active_session.name}'.\n"
                f"End it before starting a new one.")
            return

        name, ok = QInputDialog.getText(
            self, "New Research Session",
            "Enter a name for this session\n"
            "(e.g. 'eADR Cycle 3: Agent Independence Testing'):")
        if not ok or not name.strip():
            return
        name = name.strip()

        # Capture starting snapshot
        backup_cfg = getattr(self._mw._backup_panel, "_config", None) if hasattr(self._mw, "_backup_panel") else None
        snapshot = capture_snapshot(
            self._mw.prompt_database, db=self._mw.prompt_database,
            backup_config=backup_cfg)

        # Determine project name
        project = ""
        if hasattr(self._mw, "_eadr_panel"):
            project = self._mw._eadr_panel.project
        if not project and hasattr(self._mw, "current_profile"):
            project = self._mw.current_profile or ""

        session = ResearchSession(
            name=name,
            project=project,
            start_snapshot=snapshot,
            status="active",
        )

        self._sessions.append(session)
        self._active_session = session
        self._mw.prompt_database.add_session(session)

        self._set_active_session_ui(session)
        self._refresh_session_tree()
        self._mw.log(f"Research session started: '{name}'")

    @Slot()
    def _toggle_pause(self):
        """Pause or resume the active session."""
        if not self._active_session:
            return

        if self._active_session.status == "active":
            self._active_session.pause()
            self._btn_pause.setText("\u25b6 Resume")
            self._btn_pause.setToolTip("Resume the session timer")
            self._status_label.setText("\u23f8 Paused")
            colors = get_theme_colors(current_theme_name())
            self._status_label.setStyleSheet(
                f"color: {colors['warning']}; font-weight: bold;")
            self._elapsed_label.setStyleSheet(
                "color: palette(mid);"
                "padding: 4px 16px;"
                "border: 1px solid palette(mid);"
                "border-radius: 6px;"
                "background: palette(base);")
            self._timer.stop()
            self._mw.log(
                f"Session paused: '{self._active_session.name}'")
        elif self._active_session.status == "paused":
            self._active_session.resume()
            self._btn_pause.setText("\u23f8 Pause")
            self._btn_pause.setToolTip("Pause the session timer")
            self._status_label.setText("")
            self._status_label.setStyleSheet("")
            colors = get_theme_colors(current_theme_name())
            self._elapsed_label.setStyleSheet(
                f"color: {colors['success']};"
                "padding: 4px 16px;"
                "border: 1px solid palette(mid);"
                "border-radius: 6px;"
                "background: palette(base);")
            self._timer.start()
            self._mw.log(
                f"Session resumed: '{self._active_session.name}'")

        self._mw.prompt_database.update_session(self._active_session)
        self._update_session_timer()
        self._refresh_session_tree()

    @Slot()
    def end_current_session(self):
        """End the active session with a confirmation dialog."""
        if not self._active_session:
            return

        reply = QMessageBox.question(
            self, "End Session",
            f"End the session '{self._active_session.name}'?\n\n"
            f"Duration so far: {self._active_session.duration_str}\n\n"
            f"You can reopen the session from the history if needed.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No)
        if reply != QMessageBox.Yes:
            return

        # If paused, resume briefly so end_time math is clean
        if self._active_session.status == "paused":
            self._active_session.resume()

        # Save notes
        self._active_session.notes = self._notes_edit.toPlainText().strip()

        # Capture ending snapshot
        backup_cfg = getattr(self._mw._backup_panel, "_config", None) if hasattr(self._mw, "_backup_panel") else None
        end_snap = capture_snapshot(
            self._mw.prompt_database, db=self._mw.prompt_database,
            backup_config=backup_cfg)

        self._active_session.end_snapshot = end_snap
        self._active_session.end_time = datetime.now()
        self._active_session.status = "completed"

        # Compute diff
        diff = compute_session_diff(
            self._active_session.start_snapshot,
            end_snap,
            self._mw.prompt_database)
        self._active_session.summary = diff
        self._mw.prompt_database.update_session(self._active_session)

        # Generate markdown summary
        md = generate_session_summary_markdown(self._active_session, diff)

        self._mw.log(
            f"Research session ended: '{self._active_session.name}' "
            f"({diff.get('new_prompt_count', 0)} prompts, "
            f"{len(diff.get('files_changed', []))} files changed)")

        # Show summary dialog
        self._show_summary_dialog(self._active_session, md)

        # Reset UI
        self._clear_active_session_ui()
        self._active_session = None
        self._refresh_session_tree()

    def _set_active_session_ui(self, session: ResearchSession):
        """Update widgets to reflect an active or paused session."""
        self._btn_start.setEnabled(False)
        self._btn_end.setEnabled(True)
        self._btn_pause.setEnabled(True)
        self._name_label.setText(session.name)

        # Set pause button state and timer color
        if session.status == "paused":
            self._btn_pause.setText("\u25b6 Resume")
            self._btn_pause.setToolTip("Resume the session timer")
            self._status_label.setText("\u23f8 Paused")
            colors = get_theme_colors(current_theme_name())
            self._status_label.setStyleSheet(
                f"color: {colors['warning']}; font-weight: bold;")
            self._elapsed_label.setStyleSheet(
                "color: palette(mid);"
                "padding: 4px 16px;"
                "border: 1px solid palette(mid);"
                "border-radius: 6px;"
                "background: palette(base);")
        else:
            self._btn_pause.setText("\u23f8 Pause")
            self._btn_pause.setToolTip("Pause the session timer")
            self._status_label.setText("")
            self._status_label.setStyleSheet("")
            colors = get_theme_colors(current_theme_name())
            self._elapsed_label.setStyleSheet(
                f"color: {colors['success']};"
                "padding: 4px 16px;"
                "border: 1px solid palette(mid);"
                "border-radius: 6px;"
                "background: palette(base);")

        # Restore notes
        self._notes_edit.clear()
        if session.notes:
            self._notes_edit.setPlainText(session.notes)

        # Start the elapsed-time ticker (only if running)
        self._update_session_timer()
        if session.status == "active":
            self._timer.start()

    def _clear_active_session_ui(self):
        """Reset widgets to the no-active-session state."""
        self._timer.stop()
        self._btn_start.setEnabled(True)
        self._btn_end.setEnabled(False)
        self._btn_pause.setEnabled(False)
        self._btn_pause.setText("\u23f8 Pause")
        self._elapsed_label.setStyleSheet(
            "padding: 4px 16px;"
            "border: 1px solid palette(mid);"
            "border-radius: 6px;"
            "background: palette(base);")
        self._name_label.setText("No active session")
        self._elapsed_label.setText("")
        self._prompt_label.setText("")
        self._status_label.setText("")
        self._status_label.setStyleSheet("")
        self._notes_edit.clear()
        self.session_state_changed.emit("", "", False)

    @Slot()
    def _update_session_timer(self):
        """Refresh elapsed time and prompt delta labels."""
        if not self._active_session:
            self.session_state_changed.emit("", "", False)
            return

        # Format as HH:MM:SS for the prominent timer display
        secs = self._active_session.active_seconds
        h, remainder = divmod(int(secs), 3600)
        m, s = divmod(remainder, 60)
        elapsed_str = f"{h:02d}:{m:02d}:{s:02d}"
        self._elapsed_label.setText(elapsed_str)

        start_count = self._active_session.start_snapshot.get(
            "prompt_count", 0)
        current_count = len(self._mw.prompt_database.prompts)
        delta = current_count - start_count
        self._prompt_label.setText(f"\U0001f4ac {delta} prompts")

        is_paused = self._active_session.status == "paused"
        self.session_state_changed.emit(
            self._active_session.name, elapsed_str, is_paused)

    def _refresh_session_tree(self):
        """Rebuild the history model from the sessions list."""
        self._history_model.removeRows(0, self._history_model.rowCount())

        has_sessions = bool(self._sessions)
        self._sessions_empty_label.setVisible(not has_sessions)
        self._history_tree.setVisible(has_sessions)

        for session in reversed(self._sessions):
            date_str = (session.start_time.strftime("%Y-%m-%d")
                        if session.start_time else "\u2014")

            prompt_count = ""
            if session.summary:
                prompt_count = str(
                    session.summary.get("new_prompt_count", ""))
            elif session.status in ("active", "paused"):
                start_count = session.start_snapshot.get("prompt_count", 0)
                current = len(self._mw.prompt_database.prompts)
                prompt_count = f"{current - start_count}+"

            name_item = QStandardItem(session.name)
            name_item.setEditable(False)
            name_item.setData(session.id, Qt.UserRole)
            name_item.setToolTip(session.name)

            date_item = QStandardItem(date_str)
            date_item.setEditable(False)
            date_item.setToolTip(date_str)

            dur_item = QStandardItem(session.duration_str)
            dur_item.setEditable(False)
            dur_item.setToolTip(session.duration_str)

            prompt_item = QStandardItem(prompt_count)
            prompt_item.setEditable(False)
            prompt_item.setTextAlignment(Qt.AlignCenter)

            status_text = session.status.capitalize()
            if session.status == "paused":
                status_text = "\u23f8 Paused"
            status_item = QStandardItem(status_text)
            status_item.setEditable(False)
            status_item.setTextAlignment(Qt.AlignCenter)

            self._history_model.appendRow(
                [name_item, date_item, dur_item, prompt_item, status_item])

    def _get_selected_session(self) -> ResearchSession | None:
        """Return the ResearchSession for the currently selected row."""
        indexes = self._history_tree.selectionModel().selectedRows()
        if not indexes:
            QMessageBox.information(self, "No Selection",
                                    "Please select a session first.")
            return None
        row = indexes[0].row()
        item = self._history_model.item(row, 0)
        sid = item.data(Qt.UserRole)
        for s in self._sessions:
            if s.id == sid:
                return s
        return None

    @Slot()
    def _on_double_click(self, _index):
        """View summary on double-click."""
        self._ctx_view_summary()

    @Slot()
    def _on_context_menu(self, pos):
        """Show right-click context menu on the history tree."""
        index = self._history_tree.indexAt(pos)
        if not index.isValid():
            return
        self._history_tree.selectionModel().select(
            index, self._history_tree.selectionModel().ClearAndSelect
            | self._history_tree.selectionModel().Rows)

        session = self._get_selected_session()
        if not session:
            return

        menu = QMenu(self)
        menu.addAction("View Summary", self._ctx_view_summary)
        menu.addAction("Export Markdown", self._ctx_export_markdown)
        if session.status == "completed":
            menu.addSeparator()
            menu.addAction("Reopen Session", self._ctx_reopen_session)
        menu.addSeparator()
        menu.addAction("Delete", self._ctx_delete_session)
        menu.exec(self._history_tree.viewport().mapToGlobal(pos))

    @Slot()
    def _ctx_view_summary(self):
        """Show the full summary for the selected session."""
        session = self._get_selected_session()
        if not session:
            return
        if session.status in ("active", "paused"):
            QMessageBox.information(
                self, "Session Active",
                "This session is still active. End it first to "
                "generate a summary.")
            return
        diff = session.summary or {}
        md = generate_session_summary_markdown(session, diff)
        self._show_summary_dialog(session, md)

    @Slot()
    def _ctx_export_markdown(self):
        """Export the selected session summary as a .md file."""
        session = self._get_selected_session()
        if not session:
            return
        if session.status in ("active", "paused"):
            QMessageBox.information(
                self, "Session Active",
                "End the session before exporting.")
            return
        diff = session.summary or {}
        md = generate_session_summary_markdown(session, diff)
        self._export_session_markdown(session, md)

    @Slot()
    def _ctx_reopen_session(self):
        """Reopen a completed session (undo accidental end)."""
        session = self._get_selected_session()
        if not session:
            return
        if session.status != "completed":
            QMessageBox.information(
                self, "Not Completed",
                "Only completed sessions can be reopened.")
            return
        if self._active_session:
            QMessageBox.warning(
                self, "Session Active",
                f"A session is already active: "
                f"'{self._active_session.name}'.\n"
                f"End it before reopening another.")
            return

        reply = QMessageBox.question(
            self, "Reopen Session",
            f"Reopen session '{session.name}'?\n\n"
            f"The session timer will resume from where it left off "
            f"and the end-session summary will be cleared.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No)
        if reply != QMessageBox.Yes:
            return

        # Restore to active state, preserving accumulated elapsed time
        session.paused_elapsed = session.active_seconds
        session.status = "active"
        session.end_time = None
        session.end_snapshot = None
        session.summary = None
        session.paused_at = None
        # Set start_time to now so active_seconds = paused_elapsed + new
        session.start_time = datetime.now()

        self._active_session = session
        self._mw.prompt_database.update_session(session)
        self._set_active_session_ui(session)
        self._refresh_session_tree()
        self._mw.log(f"Session reopened: '{session.name}'")

    @Slot()
    def _ctx_delete_session(self):
        """Delete the selected session after confirmation."""
        session = self._get_selected_session()
        if not session:
            return
        if session.status in ("active", "paused"):
            QMessageBox.warning(
                self, "Cannot Delete",
                "Cannot delete an active or paused session. "
                "End it first.")
            return

        reply = QMessageBox.question(
            self, "Delete Session",
            f"Delete session '{session.name}'?\n"
            f"This cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No)
        if reply != QMessageBox.Yes:
            return

        self._sessions = [s for s in self._sessions if s.id != session.id]
        self._mw.prompt_database.delete_session(session.id)
        self._refresh_session_tree()
        self._mw.log(f"Deleted session: '{session.name}'")

    def _show_summary_dialog(self, session: ResearchSession, md_text: str):
        """Open a modal dialog displaying the session summary."""
        dlg = _SummaryDialog(
            session, md_text,
            export_fn=self._export_session_markdown,
            parent=self)
        dlg.exec()

    def _export_session_markdown(self, session: ResearchSession,
                                 md_text: str):
        """Save the summary markdown to a user-chosen file."""
        safe_name = "".join(
            c if c.isalnum() or c in " _-" else "_"
            for c in session.name)
        date_str = (session.start_time.strftime("%Y%m%d")
                    if session.start_time else "undated")
        default_name = f"{safe_name}_{date_str}.md"

        path, _ = QFileDialog.getSaveFileName(
            self, "Export Session Summary",
            default_name,
            "Markdown files (*.md);;All files (*.*)")
        if not path:
            return

        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(md_text)
            self._mw.log(f"Exported session summary to {path}")
            self._mw.show_toast(
                f"Session summary saved to: {os.path.basename(path)}",
                "success")
        except Exception as e:
            logger.error("Error exporting session: %s", e)
            self._mw.log(f"Error exporting session: {e}")
            QMessageBox.critical(self, "Export Error", str(e))
