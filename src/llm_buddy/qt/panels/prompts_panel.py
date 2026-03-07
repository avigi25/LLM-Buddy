"""Prompt Tracking panel for the Qt GUI.

PySide6 port of the tkinter PromptsMixin.  Provides prompt recording,
history browsing, file association management, active-prompt tracking,
export, and retroactive association via a modal dialog.
"""

import os
from datetime import datetime
from typing import Optional

from PySide6.QtCore import Qt, Slot, QTimer
from PySide6.QtGui import QStandardItemModel, QStandardItem, QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
    QLineEdit, QComboBox, QPlainTextEdit, QCheckBox,
    QPushButton, QTabWidget, QTreeView, QTextBrowser,
    QSplitter, QHeaderView, QMessageBox, QFileDialog,
    QInputDialog, QDialog, QRadioButton, QButtonGroup,
    QSpinBox, QScrollArea, QAbstractItemView,
)

from llm_buddy.core.database import PromptRecord
from llm_buddy.core.eadr import save_eadr_note

# Type-only imports for constructor params
from llm_buddy.qt.panels.capture_widgets import (
    ExtensionServerWidget,
    ProxyRecorderWidget,
)


class PromptsPanel(QWidget):
    """Prompt tracking panel with capture sources, entry form, history,
    file associations, detail display, and action buttons.
    """

    def __init__(
        self,
        main_window,
        extension_widget: ExtensionServerWidget,
        proxy_widget: ProxyRecorderWidget,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self._mw = main_window
        self._ext_widget = extension_widget
        self._proxy_widget = proxy_widget

        # Track last-selected prompt id for stable refresh
        self._selected_prompt_id: Optional[str] = None
        # Track which sub-tree had focus for Set Active / Delete
        self._last_focused_tree: Optional[QTreeView] = None

        self._build_ui()

        # Auto-refresh timer (polls DB for new prompts from MCP / proxy / ext)
        self._auto_refresh_timer = QTimer(self)
        self._auto_refresh_timer.setInterval(10_000)
        self._auto_refresh_timer.timeout.connect(self._auto_refresh_tick)
        self._auto_refresh_timer.start()

        # Initial population
        self.refresh_prompt_history()
        self.refresh_file_list()
        self.update_active_prompt_display()

    # ==================================================================
    # UI construction
    # ==================================================================

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(4, 4, 4, 4)

        # Use a scroll area so the panel never clips on small windows
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        # Make the scroll area and its inner container transparent so
        # the tab pane background shows through, matching other tabs.
        scroll.setStyleSheet("QScrollArea { background: transparent; }")
        container = QWidget()
        container.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        scroll.setWidget(container)

        # ── Capture Sources ──────────────────────────────────────────
        capture_group = QGroupBox("Capture Sources")
        cap_lay = QVBoxLayout(capture_group)
        hint = QLabel(
            "Prompts are captured automatically when a source is "
            "running. Start a source below, or record manually."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: gray;")
        cap_lay.addWidget(hint)
        cap_lay.addWidget(self._ext_widget)
        cap_lay.addWidget(self._proxy_widget)
        layout.addWidget(capture_group)

        # ── New Prompt entry ─────────────────────────────────────────
        entry_group = QGroupBox("New Prompt")
        eg = QVBoxLayout(entry_group)

        # Row 1: description
        r1 = QHBoxLayout()
        r1.addWidget(QLabel("Description:"))
        self._desc_edit = QLineEdit()
        r1.addWidget(self._desc_edit, stretch=1)
        eg.addLayout(r1)

        # Row 2: LLM used
        r2 = QHBoxLayout()
        r2.addWidget(QLabel("LLM Used:"))
        self._llm_combo = QComboBox()
        self._llm_combo.addItems(
            ["Claude", "GPT-4", "GPT-3.5", "Llama", "Other"])
        self._llm_combo.setCurrentText("Claude")
        r2.addWidget(self._llm_combo, stretch=1)
        eg.addLayout(r2)

        # Row 3: prompt text
        eg.addWidget(QLabel("Prompt Text:"))
        self._prompt_edit = QPlainTextEdit()
        self._prompt_edit.setPlaceholderText("Enter your prompt here...")
        self._prompt_edit.setMinimumHeight(100)
        eg.addWidget(self._prompt_edit)

        # Row 4: files checkbox
        self._use_all_files_cb = QCheckBox(
            "Use All Currently Selected Files")
        self._use_all_files_cb.setChecked(True)
        eg.addWidget(self._use_all_files_cb)

        # Row 5: buttons
        btn_row = QHBoxLayout()
        btn_record = QPushButton("Record Prompt")
        btn_record.setProperty("class", "primary")
        btn_record.clicked.connect(self._record_prompt)
        btn_row.addWidget(btn_record)
        btn_clear = QPushButton("Clear")
        btn_clear.clicked.connect(self._clear_prompt_fields)
        btn_row.addWidget(btn_clear)
        btn_row.addStretch()
        eg.addLayout(btn_row)

        layout.addWidget(entry_group)

        # ── Active Prompt indicator ──────────────────────────────────
        active_group = QGroupBox("Active Prompt")
        ag = QHBoxLayout(active_group)
        self._active_label = QLabel("No active prompt")
        font = self._active_label.font()
        font.setItalic(True)
        font.setPointSize(10)
        self._active_label.setFont(font)
        ag.addWidget(self._active_label, stretch=1)
        btn_clear_active = QPushButton("Clear Active Prompt")
        btn_clear_active.clicked.connect(self._clear_active_prompt)
        ag.addWidget(btn_clear_active)
        layout.addWidget(active_group)

        # ── Sub-tabs (history / file associations) ───────────────────
        splitter = QSplitter(Qt.Vertical)

        self._sub_tabs = QTabWidget()

        # -- Prompt History tab --
        history_w = QWidget()
        hw_lay = QVBoxLayout(history_w)
        hw_lay.setContentsMargins(0, 0, 0, 0)

        self._history_model = QStandardItemModel()
        self._history_model.setHorizontalHeaderLabels(
            ["Date & Time", "LLM", "Description", "Files", "Source"])
        self._history_tree = QTreeView()
        self._history_tree.setModel(self._history_model)
        self._history_tree.setRootIsDecorated(False)
        self._history_tree.setAlternatingRowColors(True)
        self._history_tree.setSelectionMode(QTreeView.SingleSelection)
        self._history_tree.setEditTriggers(QTreeView.NoEditTriggers)
        self._history_tree.header().setSectionResizeMode(
            QHeaderView.Interactive)
        self._history_tree.selectionModel().selectionChanged.connect(
            self._on_history_selection)
        # Track focus for Set Active / Delete
        self._history_tree.clicked.connect(
            lambda: self._set_last_focused(self._history_tree))
        hw_lay.addWidget(self._history_tree)
        self._sub_tabs.addTab(history_w, "Prompt History")

        # -- File Associations tab --
        fa_w = QWidget()
        fa_lay = QVBoxLayout(fa_w)
        fa_lay.setContentsMargins(0, 0, 0, 0)

        sel_row = QHBoxLayout()
        sel_row.addWidget(QLabel("Select File:"))
        self._file_combo = QComboBox()
        self._file_combo.setSizeAdjustPolicy(
            QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self._file_combo.setMinimumContentsLength(40)
        self._file_combo.currentIndexChanged.connect(self._show_file_prompts)
        sel_row.addWidget(self._file_combo, stretch=1)
        btn_refresh_files = QPushButton("Refresh")
        btn_refresh_files.clicked.connect(self.refresh_file_list)
        sel_row.addWidget(btn_refresh_files)
        fa_lay.addLayout(sel_row)

        self._file_model = QStandardItemModel()
        self._file_model.setHorizontalHeaderLabels(
            ["Date & Time", "LLM", "Description", "Files", "Source"])
        self._file_tree = QTreeView()
        self._file_tree.setModel(self._file_model)
        self._file_tree.setRootIsDecorated(False)
        self._file_tree.setAlternatingRowColors(True)
        self._file_tree.setSelectionMode(QTreeView.SingleSelection)
        self._file_tree.setEditTriggers(QTreeView.NoEditTriggers)
        self._file_tree.header().setSectionResizeMode(
            QHeaderView.Interactive)
        self._file_tree.selectionModel().selectionChanged.connect(
            self._on_file_tree_selection)
        self._file_tree.clicked.connect(
            lambda: self._set_last_focused(self._file_tree))
        fa_lay.addWidget(self._file_tree)
        self._sub_tabs.addTab(fa_w, "File Associations")

        splitter.addWidget(self._sub_tabs)

        # ── Detail view ──────────────────────────────────────────────
        detail_group = QGroupBox("Prompt Details")
        dg = QVBoxLayout(detail_group)
        self._detail_browser = QTextBrowser()
        self._detail_browser.setPlaceholderText(
            "Select a prompt to view its details.")
        self._detail_browser.setOpenExternalLinks(False)
        dg.addWidget(self._detail_browser)
        splitter.addWidget(detail_group)

        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        layout.addWidget(splitter, stretch=1)

        # ── Action buttons ───────────────────────────────────────────
        action_row = QHBoxLayout()
        btn_set_active = QPushButton("Set as Active Prompt")
        btn_set_active.clicked.connect(self._set_active_prompt)
        action_row.addWidget(btn_set_active)

        btn_export = QPushButton("Export Prompt History")
        btn_export.clicked.connect(self._export_prompt_history)
        action_row.addWidget(btn_export)

        btn_retro = QPushButton("Retroactive Association")
        btn_retro.clicked.connect(self._open_retroactive_dialog)
        action_row.addWidget(btn_retro)

        btn_add_to_branch = QPushButton("Add to Branch")
        btn_add_to_branch.setToolTip(
            "Add selected prompt to a conversation branch "
            "(Prompt Explorer tab)")
        btn_add_to_branch.clicked.connect(self._add_to_branch)
        action_row.addWidget(btn_add_to_branch)

        action_row.addStretch()

        btn_delete = QPushButton("Delete Selected Prompt")
        btn_delete.clicked.connect(self._delete_prompt)
        action_row.addWidget(btn_delete)

        layout.addLayout(action_row)

        outer.addWidget(scroll)

    # ==================================================================
    # Focus tracking helper
    # ==================================================================

    def _set_last_focused(self, tree: QTreeView) -> None:
        self._last_focused_tree = tree

    def _active_tree(self) -> Optional[QTreeView]:
        """Return whichever tree the user last clicked in."""
        return self._last_focused_tree

    # ==================================================================
    # Auto-refresh (for capture sources)
    # ==================================================================

    def start_auto_refresh(self) -> None:
        """Called by capture widgets when a source starts."""
        if not self._auto_refresh_timer.isActive():
            self._auto_refresh_timer.start()

    @Slot()
    def _auto_refresh_tick(self) -> None:
        ext_on = self._ext_widget._status.text() == "Running"
        proxy_on = "Running" in self._proxy_widget._status.text()
        # Always reload — MCP recorder runs externally (via Claude
        # Desktop) and has no in-app status widget.
        prev_count = len(self._mw.prompt_database.prompts)
        self._mw.prompt_database.load()
        if len(self._mw.prompt_database.prompts) != prev_count:
            self.refresh_prompt_history()

    # ==================================================================
    # Prompt CRUD
    # ==================================================================

    @Slot()
    def _record_prompt(self) -> None:
        """Record a new prompt and set it as active."""
        prompt_text = self._prompt_edit.toPlainText().strip()
        if not prompt_text:
            QMessageBox.warning(
                self, "Empty Prompt",
                "Please enter prompt text before recording.")
            return

        description = self._desc_edit.text().strip()
        llm_used = self._llm_combo.currentText()
        record = PromptRecord(prompt_text, llm_used, description)

        if self._use_all_files_cb.isChecked():
            for fp_tuple in self._mw.filtered_files:
                # filtered_files is a list of (path, tokens) tuples
                fp = fp_tuple[0] if isinstance(fp_tuple, (list, tuple)) else fp_tuple
                record.associated_files.append(fp)

        self._mw.prompt_database.add_prompt(prompt_record=record)
        self._mw.log(f"Recorded new prompt: {description or 'Untitled'}")
        self.refresh_prompt_history()
        self.update_active_prompt_display()
        self._clear_prompt_fields()

        QMessageBox.information(
            self, "Prompt Recorded",
            "Prompt has been recorded and set as active.\n\n"
            "Any files modified now will be associated with this prompt.")

    @Slot()
    def _clear_prompt_fields(self) -> None:
        self._desc_edit.clear()
        self._prompt_edit.clear()

    @Slot()
    def _delete_prompt(self) -> None:
        tree = self._active_tree()
        if tree is None:
            return
        model = tree.model()
        indexes = tree.selectionModel().selectedRows()
        if not indexes:
            return

        answer = QMessageBox.question(
            self, "Confirm Deletion",
            "Are you sure you want to delete this prompt record?\n"
            "This action cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return

        row = indexes[0].row()
        prompt_id = model.item(row, 0).data(Qt.UserRole)
        if prompt_id is None:
            return

        db = self._mw.prompt_database
        prompt = db.get_prompt(prompt_id)
        if prompt is None:
            return

        if db.active_prompt and db.active_prompt.id == prompt_id:
            db.clear_active_prompt()
            self.update_active_prompt_display()

        db.delete_prompt(prompt_id)
        self._mw.log(
            f"Deleted prompt: {prompt.description or 'Untitled'}")
        self.refresh_prompt_history()
        self._show_file_prompts()
        self._detail_browser.clear()

    # ==================================================================
    # Cross-tab: Add to Branch (Prompt Explorer)
    # ==================================================================

    @Slot()
    def _add_to_branch(self) -> None:
        """Send the selected prompt to the Prompt Explorer panel."""
        tree = self._active_tree()
        if tree is None:
            return
        model = tree.model()
        indexes = tree.selectionModel().selectedRows()
        if not indexes:
            QMessageBox.information(
                self, "No Selection",
                "Select a prompt first.")
            return

        row = indexes[0].row()
        prompt_id = model.item(row, 0).data(Qt.UserRole)
        if not prompt_id:
            return

        # Delegate to the Prompt Explorer panel
        forking_panel = getattr(self._mw, "_forking_panel", None)
        if forking_panel is None:
            QMessageBox.warning(
                self, "Unavailable",
                "Prompt Explorer panel not found.")
            return

        forking_panel.add_prompt_to_branch(prompt_id)

    # ==================================================================
    # History / detail views
    # ==================================================================

    def refresh_prompt_history(self) -> None:
        """Reload the prompt history tree from the database."""
        # Remember current selection
        sel_indexes = self._history_tree.selectionModel().selectedRows()
        prev_id = None
        if sel_indexes:
            prev_id = self._history_model.item(
                sel_indexes[0].row(), 0)
            prev_id = prev_id.data(Qt.UserRole) if prev_id else None

        self._history_model.removeRows(0, self._history_model.rowCount())

        sorted_prompts = sorted(
            self._mw.prompt_database.prompts,
            key=lambda p: p.timestamp, reverse=True)

        restore_row = -1
        for idx, prompt in enumerate(sorted_prompts):
            ts = prompt.timestamp.strftime("%Y-%m-%d %H:%M")
            fc = str(len(prompt.associated_files))
            source = self._infer_source(prompt)

            ts_item = QStandardItem(ts)
            ts_item.setData(prompt.id, Qt.UserRole)
            ts_item.setEditable(False)
            ts_item.setToolTip(ts)

            llm_item = QStandardItem(prompt.llm_used)
            llm_item.setEditable(False)

            desc_item = QStandardItem(prompt.description)
            desc_item.setEditable(False)
            desc_item.setToolTip(prompt.description)

            fc_item = QStandardItem(fc)
            fc_item.setEditable(False)

            src_item = QStandardItem(source)
            src_item.setEditable(False)

            self._history_model.appendRow(
                [ts_item, llm_item, desc_item, fc_item, src_item])

            if prompt.id == prev_id:
                restore_row = idx

        # Restore selection
        if restore_row >= 0:
            sel_index = self._history_model.index(restore_row, 0)
            self._history_tree.selectionModel().select(
                sel_index,
                self._history_tree.selectionModel().ClearAndSelect
                | self._history_tree.selectionModel().Rows,
            )
            self._show_prompt_detail(prev_id)

    @staticmethod
    def _infer_source(prompt: PromptRecord) -> str:
        """Heuristic to determine a prompt's origin."""
        if hasattr(prompt, "source") and prompt.source and prompt.source != "Unknown":
            return prompt.source

        desc = (prompt.description or "").lower()
        llm = prompt.llm_used or ""

        if "auto-recorded from claude desktop" in desc:
            return "Claude Desktop"
        if "browser extension" in desc or "captured" in desc:
            return "Browser Extension"
        if "proxy" in desc:
            return "Proxy"
        if llm == "Claude" and any(
            k in desc for k in ("mcp", "auto-recorded", "claude desktop")
        ):
            return "Claude Desktop"
        if any(k in desc for k in ("web", "browser", "via", "claude.ai")):
            return "Browser Extension"
        if any(n in llm for n in ("ChatGPT", "Gemini", "Perplexity")):
            return "Browser Extension"
        return "Manual"

    def _show_prompt_detail(self, prompt_id: str) -> None:
        """Populate the detail browser for the given prompt ID."""
        prompt = self._mw.prompt_database.get_prompt(prompt_id)
        if not prompt:
            self._detail_browser.clear()
            return

        lines = []
        lines.append(f"<b>Description:</b> {prompt.description}")
        lines.append(
            f"<b>Date &amp; Time:</b> "
            f"{prompt.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"<b>LLM Used:</b> {prompt.llm_used}")
        lines.append(f"<b>Source:</b> {self._infer_source(prompt)}")
        lines.append("")

        lines.append("<b>Associated Files:</b>")
        if prompt.associated_files:
            for fp in prompt.associated_files:
                change = prompt.file_changes.get(fp, "Unknown")
                lines.append(f"&nbsp;&nbsp;- {fp} (Token change: {change})")
        else:
            lines.append("&nbsp;&nbsp;No associated files")

        if hasattr(prompt, "retroactive_notes") and prompt.retroactive_notes:
            lines.append("")
            lines.append("<b>Retroactive Associations:</b>")
            for ts, nd in prompt.retroactive_notes.items():
                files = nd.get("files", [])
                notes = nd.get("notes", "")
                lines.append(f"&nbsp;&nbsp;- {ts}: {len(files)} files")
                lines.append(f"&nbsp;&nbsp;&nbsp;&nbsp;Note: {notes}")

        lines.append("")
        lines.append("<b>--- Prompt (Input) ---</b>")
        lines.append(f"<pre>{prompt.prompt_text or ''}</pre>")

        response = getattr(prompt, "response_text", "") or ""
        lines.append("")
        lines.append("<b>--- Response (Output) ---</b>")
        if response:
            lines.append(f"<pre>{response}</pre>")
        else:
            lines.append("(No response captured)")

        self._detail_browser.setHtml("<br>".join(lines))

    @Slot()
    def _on_history_selection(self) -> None:
        indexes = self._history_tree.selectionModel().selectedRows()
        if not indexes:
            return
        row = indexes[0].row()
        item = self._history_model.item(row, 0)
        if item:
            prompt_id = item.data(Qt.UserRole)
            self._selected_prompt_id = prompt_id
            self._set_last_focused(self._history_tree)
            self._show_prompt_detail(prompt_id)

    @Slot()
    def _on_file_tree_selection(self) -> None:
        indexes = self._file_tree.selectionModel().selectedRows()
        if not indexes:
            return
        row = indexes[0].row()
        item = self._file_model.item(row, 0)
        if item:
            prompt_id = item.data(Qt.UserRole)
            self._selected_prompt_id = prompt_id
            self._set_last_focused(self._file_tree)
            self._show_prompt_detail(prompt_id)

    # ==================================================================
    # File association helpers
    # ==================================================================

    @Slot()
    def refresh_file_list(self) -> None:
        """Refresh the file combo for the File Associations tab."""
        all_files: set = set()
        for fp_tuple in self._mw.filtered_files:
            fp = fp_tuple[0] if isinstance(fp_tuple, (list, tuple)) else fp_tuple
            all_files.add(fp)
        for p in self._mw.prompt_database.prompts:
            all_files.update(p.associated_files)

        prev = self._file_combo.currentText()
        self._file_combo.blockSignals(True)
        self._file_combo.clear()
        self._file_combo.addItems(sorted(all_files))
        self._file_combo.blockSignals(False)

        # Restore or pick first
        idx = self._file_combo.findText(prev)
        if idx >= 0:
            self._file_combo.setCurrentIndex(idx)
        elif self._file_combo.count() > 0:
            self._file_combo.setCurrentIndex(0)
        self._show_file_prompts()

    @Slot()
    def _show_file_prompts(self) -> None:
        """Show prompts associated with the selected file."""
        self._file_model.removeRows(0, self._file_model.rowCount())
        fp = self._file_combo.currentText()
        if not fp:
            return

        file_prompts = self._mw.prompt_database.get_prompts_for_file(fp)
        for prompt in sorted(
            file_prompts, key=lambda p: p.timestamp, reverse=True
        ):
            ts = prompt.timestamp.strftime("%Y-%m-%d %H:%M")
            fc = str(len(prompt.associated_files))
            source = self._infer_source(prompt)

            ts_item = QStandardItem(ts)
            ts_item.setData(prompt.id, Qt.UserRole)
            ts_item.setEditable(False)
            ts_item.setToolTip(ts)

            llm_item = QStandardItem(prompt.llm_used)
            llm_item.setEditable(False)

            desc_item = QStandardItem(prompt.description)
            desc_item.setEditable(False)
            desc_item.setToolTip(prompt.description)

            fc_item = QStandardItem(fc)
            fc_item.setEditable(False)

            src_item = QStandardItem(source)
            src_item.setEditable(False)

            self._file_model.appendRow(
                [ts_item, llm_item, desc_item, fc_item, src_item])

    # ==================================================================
    # Active prompt
    # ==================================================================

    @Slot()
    def _set_active_prompt(self) -> None:
        tree = self._active_tree()
        if tree is None:
            QMessageBox.information(
                self, "No Selection",
                "Please select a prompt to set as active.")
            return

        indexes = tree.selectionModel().selectedRows()
        if not indexes:
            QMessageBox.information(
                self, "No Selection",
                "Please select a prompt to set as active.")
            return

        row = indexes[0].row()
        model = tree.model()
        prompt_id = model.item(row, 0).data(Qt.UserRole)
        prompt = self._mw.prompt_database.get_prompt(prompt_id)
        if prompt:
            self._mw.prompt_database.active_prompt = prompt
            self.update_active_prompt_display()
            self._mw.log(
                f"Set active prompt: {prompt.description or 'Untitled'}")
            QMessageBox.information(
                self, "Active Prompt Set",
                "Selected prompt has been set as active.\n\n"
                "Any files modified now will be associated with this prompt.")

    @Slot()
    def _clear_active_prompt(self) -> None:
        if self._mw.prompt_database.active_prompt:
            self._mw.prompt_database.clear_active_prompt()
            self.update_active_prompt_display()
            self._mw.log("Cleared active prompt")

    def update_active_prompt_display(self) -> None:
        """Update the active-prompt label."""
        ap = self._mw.prompt_database.active_prompt
        if ap:
            desc = ap.description or "Untitled"
            ts = ap.timestamp.strftime("%Y-%m-%d %H:%M")
            self._active_label.setText(
                f"Active Prompt: {desc} ({ts}, {ap.llm_used})")
            font = self._active_label.font()
            font.setItalic(False)
            font.setBold(True)
            font.setPointSize(10)
            self._active_label.setFont(font)
            self._active_label.setStyleSheet("color: green;")
        else:
            self._active_label.setText("No active prompt")
            font = self._active_label.font()
            font.setItalic(True)
            font.setBold(False)
            font.setPointSize(10)
            self._active_label.setFont(font)
            self._active_label.setStyleSheet("color: black;")

    # ==================================================================
    # Export
    # ==================================================================

    @Slot()
    def _export_prompt_history(self) -> None:
        """Export prompt history to a markdown file."""
        output_dir = "prompts"
        os.makedirs(output_dir, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = os.path.join(output_dir, f"prompt_history_{ts}.md")

        try:
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(
                    f"# Prompt History Export\nGenerated: "
                    f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

                sorted_prompts = sorted(
                    self._mw.prompt_database.prompts,
                    key=lambda p: p.timestamp, reverse=True)

                for i, prompt in enumerate(sorted_prompts, 1):
                    f.write(
                        f"## {i}. "
                        f"{prompt.description or 'Untitled Prompt'}\n\n")
                    f.write(
                        f"- **Date & Time:** "
                        f"{prompt.timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"- **LLM Used:** {prompt.llm_used}\n")
                    f.write(f"- **ID:** {prompt.id}\n\n")
                    f.write("### Prompt Text (Input)\n\n```\n")
                    f.write(prompt.prompt_text)
                    f.write("\n```\n\n")

                    response = getattr(prompt, "response_text", "") or ""
                    if response:
                        f.write("### Response (Output)\n\n```\n")
                        f.write(response)
                        f.write("\n```\n\n")

                    f.write("### Associated Files\n\n")
                    if prompt.associated_files:
                        for fp in prompt.associated_files:
                            change = prompt.file_changes.get(fp, "Unknown")
                            f.write(
                                f"- `{fp}` (Token change: {change})\n")
                    else:
                        f.write("No files associated with this prompt.\n")

                    if (hasattr(prompt, "retroactive_notes")
                            and prompt.retroactive_notes):
                        f.write("\n### Retroactive Associations\n\n")
                        for rts, nd in prompt.retroactive_notes.items():
                            f.write(
                                f"**{rts}**\n\n"
                                f"- Token Change: {nd['token_change']}\n")
                            f.write(
                                f"- Notes: {nd['notes']}\n- Files:\n")
                            for rf in nd["files"]:
                                f.write(f"  - `{rf}`\n")
                    f.write("\n---\n\n")

            self._mw.log(f"Exported prompt history to {output_file}")
            QMessageBox.information(
                self, "Export Complete",
                f"Prompt history has been exported to:\n{output_file}")

        except Exception as e:
            self._mw.log(f"Error exporting prompt history: {e}")
            QMessageBox.critical(
                self, "Export Error",
                f"Failed to export prompt history:\n{e}")

    # ==================================================================
    # Retroactive Association dialog
    # ==================================================================

    @Slot()
    def _open_retroactive_dialog(self) -> None:
        db = self._mw.prompt_database
        if not db.prompts:
            QMessageBox.information(
                self, "No Prompts",
                "No prompts have been recorded yet. "
                "Please record a prompt first.")
            return

        dlg = _RetroactiveDialog(self._mw, self, parent=self)
        dlg.exec()

        # Refresh after dialog closes
        self.refresh_prompt_history()
        self.refresh_file_list()


# =====================================================================
# Retroactive Association dialog
# =====================================================================

class _RetroactiveDialog(QDialog):
    """Modal dialog for retroactively associating files with a prompt."""

    def __init__(self, main_window, panel: PromptsPanel,
                 parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._mw = main_window
        self._panel = panel
        self.setWindowTitle("Retroactive Prompt Association")
        self.resize(800, 600)
        self.setModal(True)

        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        db = self._mw.prompt_database

        # ── 1. Prompt selection ──────────────────────────────────────
        pf = QGroupBox("Select Prompt")
        pf_lay = QHBoxLayout(pf)
        self._prompt_combo = QComboBox()
        self._prompt_options = []
        for p in db.prompts:
            label = (
                f"{p.description or 'Untitled'} "
                f"({p.timestamp.strftime('%Y-%m-%d %H:%M')})")
            self._prompt_combo.addItem(label)
            self._prompt_options.append(p)
        pf_lay.addWidget(self._prompt_combo, stretch=1)
        btn_view = QPushButton("View Prompt Details")
        btn_view.clicked.connect(self._view_prompt_details)
        pf_lay.addWidget(btn_view)
        layout.addWidget(pf)

        # ── 2. File selection ────────────────────────────────────────
        ff = QGroupBox("Select Files to Associate")
        ff_lay = QVBoxLayout(ff)

        # Source radio buttons
        source_row = QHBoxLayout()
        self._source_group = QButtonGroup(self)
        rb_current = QRadioButton("Use Current Selection")
        rb_current.setChecked(True)
        rb_all = QRadioButton("Use All Files")
        rb_manual = QRadioButton("Select Files Manually")
        self._source_group.addButton(rb_current, 0)
        self._source_group.addButton(rb_all, 1)
        self._source_group.addButton(rb_manual, 2)
        source_row.addWidget(rb_current)
        source_row.addWidget(rb_all)
        source_row.addWidget(rb_manual)
        source_row.addStretch()
        ff_lay.addLayout(source_row)
        self._source_group.idClicked.connect(self._update_file_list)

        # File tree
        self._file_model = QStandardItemModel()
        self._file_model.setHorizontalHeaderLabels(["File Path", "Selected"])
        self._file_tree = QTreeView()
        self._file_tree.setModel(self._file_model)
        self._file_tree.setRootIsDecorated(False)
        self._file_tree.setAlternatingRowColors(True)
        self._file_tree.setEditTriggers(QTreeView.NoEditTriggers)
        ft_header = self._file_tree.header()
        ft_header.setSectionResizeMode(QHeaderView.Interactive)
        ft_header.setStretchLastSection(False)
        ft_header.setSectionResizeMode(0, QHeaderView.Stretch)
        ft_header.resizeSection(1, 70)
        ff_lay.addWidget(self._file_tree)

        # Selection buttons
        sel_btns = QHBoxLayout()
        btn_sel_all = QPushButton("Select All")
        btn_sel_all.clicked.connect(self._select_all_files)
        sel_btns.addWidget(btn_sel_all)
        btn_desel_all = QPushButton("Deselect All")
        btn_desel_all.clicked.connect(self._deselect_all_files)
        sel_btns.addWidget(btn_desel_all)
        btn_add = QPushButton("Add Files...")
        btn_add.clicked.connect(self._add_files)
        sel_btns.addWidget(btn_add)
        sel_btns.addStretch()
        ff_lay.addLayout(sel_btns)

        layout.addWidget(ff, stretch=1)

        # ── 3. Association details ───────────────────────────────────
        nf = QGroupBox("Association Details")
        nf_lay = QVBoxLayout(nf)

        token_row = QHBoxLayout()
        token_row.addWidget(QLabel("Estimated Token Change:"))
        self._token_combo = QComboBox()
        self._token_combo.addItems(
            ["Auto", "Minor (<50)", "Moderate (50-200)",
             "Major (>200)", "Custom"])
        self._token_combo.currentTextChanged.connect(
            self._on_token_option_changed)
        token_row.addWidget(self._token_combo)
        token_row.addStretch()
        nf_lay.addLayout(token_row)

        # Custom token spinbox (hidden by default)
        self._custom_row = QHBoxLayout()
        self._custom_row_widget = QWidget()
        cr_lay = QHBoxLayout(self._custom_row_widget)
        cr_lay.setContentsMargins(0, 0, 0, 0)
        cr_lay.addWidget(QLabel("Custom Token Change:"))
        self._custom_spin = QSpinBox()
        self._custom_spin.setRange(-10000, 10000)
        self._custom_spin.setValue(0)
        cr_lay.addWidget(self._custom_spin)
        cr_lay.addStretch()
        self._custom_row_widget.setVisible(False)
        nf_lay.addWidget(self._custom_row_widget)

        nf_lay.addWidget(QLabel("Notes:"))
        self._notes_edit = QPlainTextEdit()
        self._notes_edit.setMaximumHeight(80)
        nf_lay.addWidget(self._notes_edit)

        layout.addWidget(nf)

        # ── 4. Dialog buttons ────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_cancel)
        btn_row.addStretch()
        btn_associate = QPushButton("Associate Files with Prompt")
        btn_associate.clicked.connect(self._perform_association)
        btn_row.addWidget(btn_associate)
        layout.addLayout(btn_row)

        # Populate initial file list
        self._update_file_list(0)

    # -- helpers -------------------------------------------------------

    @Slot(int)
    def _on_token_option_changed(self, text: str) -> None:
        self._custom_row_widget.setVisible(
            self._token_combo.currentText() == "Custom")

    @Slot(int)
    def _update_file_list(self, source_id: int) -> None:
        self._file_model.removeRows(0, self._file_model.rowCount())
        files = []

        if source_id == 0:  # current selection
            for fp_tuple in self._mw.filtered_files:
                fp = fp_tuple[0] if isinstance(fp_tuple, (list, tuple)) else fp_tuple
                files.append(fp)
        elif source_id == 1:  # all files
            s = set()
            for fp_tuple in self._mw.filtered_files:
                fp = fp_tuple[0] if isinstance(fp_tuple, (list, tuple)) else fp_tuple
                s.add(fp)
            for folder in self._mw.folders:
                for root, _, fnames in os.walk(folder):
                    for fn in fnames:
                        s.add(os.path.join(root, fn))
            files = sorted(s)
        # source_id == 2 (manual) starts empty

        for fp in files:
            self._add_file_row(fp, selected=True)

    def _add_file_row(self, fp: str, selected: bool = True) -> None:
        path_item = QStandardItem(fp)
        path_item.setEditable(False)
        path_item.setToolTip(fp)
        sel_item = QStandardItem("\u2713" if selected else " ")
        sel_item.setEditable(False)
        self._file_model.appendRow([path_item, sel_item])

    @Slot()
    def _select_all_files(self) -> None:
        for row in range(self._file_model.rowCount()):
            self._file_model.item(row, 1).setText("\u2713")

    @Slot()
    def _deselect_all_files(self) -> None:
        for row in range(self._file_model.rowCount()):
            self._file_model.item(row, 1).setText(" ")

    @Slot()
    def _add_files(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Select File(s) to Associate")
        existing = set()
        for row in range(self._file_model.rowCount()):
            existing.add(self._file_model.item(row, 0).text())
        for fp in paths:
            if fp not in existing:
                self._add_file_row(fp, selected=True)

    @Slot()
    def _view_prompt_details(self) -> None:
        idx = self._prompt_combo.currentIndex()
        if idx < 0 or idx >= len(self._prompt_options):
            return
        prompt = self._prompt_options[idx]

        dd = QDialog(self)
        dd.setWindowTitle("Prompt Details")
        dd.resize(600, 400)
        dd.setModal(True)
        lay = QVBoxLayout(dd)

        lay.addWidget(QLabel(
            f"<b>Description:</b> {prompt.description or 'Untitled'}"))
        lay.addWidget(QLabel(
            f"<b>Date & Time:</b> "
            f"{prompt.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"))
        lay.addWidget(QLabel(
            f"<b>LLM Used:</b> {prompt.llm_used}"))

        pg = QGroupBox("Prompt Text")
        pg_lay = QVBoxLayout(pg)
        pt = QTextBrowser()
        pt.setPlainText(prompt.prompt_text or "")
        pg_lay.addWidget(pt)
        lay.addWidget(pg, stretch=1)

        if prompt.associated_files:
            ag = QGroupBox("Currently Associated Files")
            ag_lay = QVBoxLayout(ag)
            ft = QTextBrowser()
            for fp in prompt.associated_files:
                ft.append(f"\u2022 {fp}")
            ag_lay.addWidget(ft)
            lay.addWidget(ag)

        btn_close = QPushButton("Close")
        btn_close.clicked.connect(dd.accept)
        lay.addWidget(btn_close, alignment=Qt.AlignCenter)
        dd.exec()

    @Slot()
    def _perform_association(self) -> None:
        idx = self._prompt_combo.currentIndex()
        db = self._mw.prompt_database
        if idx < 0 or idx >= len(self._prompt_options):
            QMessageBox.critical(self, "Error",
                                 "Please select a valid prompt.")
            return
        prompt = self._prompt_options[idx]

        # Gather selected files
        selected_files = []
        for row in range(self._file_model.rowCount()):
            if self._file_model.item(row, 1).text() == "\u2713":
                selected_files.append(
                    self._file_model.item(row, 0).text())

        if not selected_files:
            QMessageBox.warning(
                self, "No Files Selected",
                "Please select at least one file to associate "
                "with the prompt.")
            return

        # Determine token change
        token_map = {
            "Auto": 100,
            "Minor (<50)": 25,
            "Moderate (50-200)": 100,
            "Major (>200)": 300,
            "Custom": self._custom_spin.value(),
        }
        token_change = token_map.get(
            self._token_combo.currentText(), 100)

        # Associate
        newly_added = 0
        for fp in selected_files:
            if fp not in prompt.associated_files:
                prompt.associated_files.append(fp)
                prompt.file_changes[fp] = token_change
                newly_added += 1
        db.save()

        # Save notes / eADR
        notes = self._notes_edit.toPlainText().strip()
        if notes:
            if not hasattr(prompt, "retroactive_notes"):
                prompt.retroactive_notes = {}
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            prompt.retroactive_notes[ts] = {
                "files": selected_files,
                "token_change": token_change,
                "notes": notes,
            }
            db.save()

            note_text = (
                f"Retroactive Prompt Association\n\n"
                f"Prompt: {prompt.description or 'Untitled'}\n"
                f"Date: {ts}\nFiles associated: {len(selected_files)}\n\n"
                f"User Notes:\n{notes}\n\nFiles:\n")
            for fp in selected_files:
                note_text += f"- {fp}\n"

            eadr_panel = getattr(self._mw, "_eadr_panel", None)
            project = (eadr_panel.project
                       if eadr_panel else "Origin")
            save_eadr_note(note_text, project)
            if eadr_panel:
                eadr_panel.refresh()

        QMessageBox.information(
            self, "Association Complete",
            f"Successfully associated {newly_added} new files with "
            f"the prompt.\n"
            f"{len(selected_files) - newly_added} files were already "
            f"associated.")
        self.accept()
