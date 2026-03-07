"""Main application window for LLM Buddy (PySide6).

Owns the shared application state (database, profiles, file lists)
and wires all panels together via Qt signals and slots.
"""

import os
import sys

from PySide6.QtCore import Qt, Signal, Slot, QTimer
from PySide6.QtGui import QAction, QKeySequence, QFont
from PySide6.QtWidgets import (
    QMainWindow, QSplitter, QTabWidget, QWidget, QVBoxLayout,
    QHBoxLayout, QLabel, QComboBox, QPushButton, QStatusBar,
    QInputDialog, QMessageBox,
)

from llm_buddy.core.database import PromptDatabase
from llm_buddy.core.profiles import load_profiles, save_profiles
from llm_buddy.qt.theme import THEMES, apply_theme
from llm_buddy.qt.panels.help_panel import HelpPanel, AboutPanel
from llm_buddy.qt.panels.log_panel import LogPanel
from llm_buddy.qt.panels.eadr_panel import EadrPanel
from llm_buddy.qt.panels.control_panel import ControlPanel
from llm_buddy.qt.panels.preview_panel import PreviewPanel
from llm_buddy.qt.panels.rollback_panel import RollbackPanel
from llm_buddy.qt.panels.compare_panel import ComparePanel
from llm_buddy.qt.panels.backup_panel import BackupPanel
from llm_buddy.qt.panels.capture_widgets import (
    ExtensionServerWidget, ProxyRecorderWidget,
)
from llm_buddy.qt.panels.prompts_panel import PromptsPanel
from llm_buddy.qt.panels.analytics_panel import AnalyticsPanel
from llm_buddy.qt.panels.sessions_panel import SessionsPanel
from llm_buddy.qt.panels.forking_panel import ForkingPanel


class LLMBuddyWindow(QMainWindow):
    """Top-level application window.

    Owns the shared application state (database, profiles) and
    wires panels together via Qt signals.
    """

    # Signals that panels can connect to
    log_message = Signal(str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("LLM Buddy \u2013 Prompt Recording & Management")
        self.resize(1200, 800)

        # ── Core state ───────────────────────────────────────────────
        self.profiles = load_profiles()
        self.current_profile = None
        self.folders: list[str] = []
        self.all_files: list[str] = []
        self.filtered_files: list[tuple[str, int]] = []
        self.backup_files: dict = {}

        self.allowed_extensions = (
            ".py,.kt,.xml,.html,.js,.txt,.md,.json,.css,"
            ".bat,.p12,.pem,.sh,.env,.R,.toml"
        )
        self.min_tokens = 0

        # Compute data paths at construction time (not module-import time)
        self.prompt_database = PromptDatabase()
        self.prompt_database.load()

        # ── Toolbar area ─────────────────────────────────────────────
        self._build_toolbar()

        # ── Central layout: splitter with control panel + tabs ───────
        self._splitter = QSplitter(Qt.Horizontal)
        self.setCentralWidget(self._splitter)

        # Left: control panel
        self._control_panel = ControlPanel(self)
        self._splitter.addWidget(self._control_panel)

        # Right: tab widget
        self._tabs = QTabWidget()
        self._tabs.setDocumentMode(True)  # cleaner tab rendering
        self._splitter.addWidget(self._tabs)
        self._splitter.setStretchFactor(0, 1)
        self._splitter.setStretchFactor(1, 2)

        # ── Panels ───────────────────────────────────────────────────
        self._log_panel = LogPanel()
        self._eadr_panel = EadrPanel(log_fn=self.log)
        self._preview_panel = PreviewPanel(self)
        self._rollback_panel = RollbackPanel(self)
        self._compare_panel = ComparePanel(self)
        self._backup_panel = BackupPanel(self)
        self._help_panel = HelpPanel()
        self._about_panel = AboutPanel()

        # Capture widgets (shared between main window and prompts panel)
        self._ext_widget = ExtensionServerWidget(self)
        self._proxy_widget = ProxyRecorderWidget(self)

        # Complex panels
        self._prompts_panel = PromptsPanel(
            self, self._ext_widget, self._proxy_widget)
        self._analytics_panel = AnalyticsPanel(self)
        self._sessions_panel = SessionsPanel(self)
        self._forking_panel = ForkingPanel(self)

        # ── Signal wiring ────────────────────────────────────────────
        # Log signal → Log panel
        self.log_message.connect(self._log_panel.append)

        # Control panel file changes → preview + status bar
        self._control_panel.files_changed.connect(
            self._preview_panel.update_preview)
        self._control_panel.files_changed.connect(self._update_file_status)

        # Tab change → lazy refresh for analytics/sessions
        self._tabs.currentChanged.connect(self._on_tab_changed)

        # eADR save → log
        self._eadr_panel.note_saved.connect(
            lambda: self.log("eADR note saved."))

        # Forking signals → auto eADR notes
        self._forking_panel.branch_forked.connect(self._on_branch_forked)
        self._forking_panel.branch_merged.connect(self._on_branch_merged)

        # ── Add tabs with icons (order matches original GUI) ─────────
        self._tabs.addTab(self._eadr_panel,      "\U0001f4dd eADR Notes")
        self._tabs.addTab(self._preview_panel,    "\U0001f441 Preview")
        self._tabs.addTab(self._log_panel,        "\U0001f4cb Logs")
        self._tabs.addTab(self._prompts_panel,    "\U0001f4ac Prompt Tracking")
        self._tabs.addTab(self._backup_panel,     "\U0001f4be Auto-Backup")
        self._tabs.addTab(self._rollback_panel,   "\u23ea Rollback")
        self._tabs.addTab(self._compare_panel,    "\U0001f50d Compare Files")
        self._tabs.addTab(self._analytics_panel,  "\U0001f4ca Analytics")
        self._tabs.addTab(self._sessions_panel,   "\U0001f9ea Sessions")
        self._tabs.addTab(self._forking_panel,    "\U0001f333 Prompt Explorer")
        self._tabs.addTab(self._help_panel,       "\u2753 Help")
        self._tabs.addTab(self._about_panel,      "\u2139 About")

        # Store tab indices for lazy-refresh logic
        self._tab_indices = {
            "analytics": self._tabs.indexOf(self._analytics_panel),
            "sessions": self._tabs.indexOf(self._sessions_panel),
            "prompts": self._tabs.indexOf(self._prompts_panel),
            "forking": self._tabs.indexOf(self._forking_panel),
        }

        # ── Menu bar ─────────────────────────────────────────────────
        self._build_menus()

        # ── Keyboard shortcuts ───────────────────────────────────────
        self._setup_shortcuts()

        # ── Status bar ───────────────────────────────────────────────
        self._status = QStatusBar()
        self.setStatusBar(self._status)

        # Permanent status widgets
        self._file_count_label = QLabel("Files: 0")
        self._file_count_label.setStyleSheet("padding: 0 8px;")
        self._prompt_count_label = QLabel("Prompts: 0")
        self._prompt_count_label.setStyleSheet("padding: 0 8px;")
        self._profile_label = QLabel("No profile")
        self._profile_label.setStyleSheet(
            "padding: 0 8px; font-style: italic;")

        self._status.addPermanentWidget(self._profile_label)
        self._status.addPermanentWidget(self._file_count_label)
        self._status.addPermanentWidget(self._prompt_count_label)
        self._status.showMessage("Ready", 3000)

        # Periodic prompt count refresh (every 10s)
        self._status_timer = QTimer(self)
        self._status_timer.timeout.connect(self._refresh_status_counts)
        self._status_timer.start(10_000)

        # ── Post-init ────────────────────────────────────────────────
        self._handle_cli_args()
        if self.all_files or self.folders:
            self._control_panel.apply_filters()
        self._refresh_status_counts()
        self.log("LLM Buddy started.")

    # ------------------------------------------------------------------
    # Toolbar (profile selector + theme)
    # ------------------------------------------------------------------
    def _build_toolbar(self):
        toolbar_widget = QWidget()
        layout = QHBoxLayout(toolbar_widget)
        layout.setContentsMargins(6, 4, 6, 4)

        # Profile selector
        lbl_profile = QLabel("Profile:")
        lbl_profile.setFont(QFont(lbl_profile.font().family(), -1, QFont.Bold))
        layout.addWidget(lbl_profile)
        self._profile_combo = QComboBox()
        self._profile_combo.setEditable(True)
        self._profile_combo.addItems(list(self.profiles.keys()))
        self._profile_combo.setMinimumWidth(160)
        self._profile_combo.setToolTip("Select or type a profile name")
        self._profile_combo.activated.connect(self._load_profile)
        layout.addWidget(self._profile_combo, stretch=1)

        btn_save = QPushButton("Save Profile")
        btn_save.setToolTip("Save current settings to the selected profile")
        btn_save.clicked.connect(self._save_profile)
        layout.addWidget(btn_save)

        btn_new = QPushButton("New Profile")
        btn_new.setToolTip("Create a new blank profile")
        btn_new.clicked.connect(self._new_profile)
        layout.addWidget(btn_new)

        layout.addSpacing(16)

        # Theme selector
        lbl_theme = QLabel("Theme:")
        lbl_theme.setFont(QFont(lbl_theme.font().family(), -1, QFont.Bold))
        layout.addWidget(lbl_theme)
        self._theme_combo = QComboBox()
        self._theme_combo.addItems(list(THEMES.keys()))
        self._theme_combo.setToolTip("Switch application colour theme")
        self._theme_combo.currentTextChanged.connect(self._change_theme)
        layout.addWidget(self._theme_combo)

        # Install as toolbar widget (sits above splitter)
        toolbar = self.addToolBar("Main")
        toolbar.setMovable(False)
        toolbar.addWidget(toolbar_widget)

    # ------------------------------------------------------------------
    # Menu bar
    # ------------------------------------------------------------------
    def _build_menus(self):
        menu_bar = self.menuBar()

        # File menu
        file_menu = menu_bar.addMenu("&File")

        act_combine = QAction("&Combine Scripts", self)
        act_combine.setShortcut(QKeySequence("Ctrl+Shift+C"))
        act_combine.triggered.connect(self._control_panel.combine_scripts)
        file_menu.addAction(act_combine)

        file_menu.addSeparator()

        act_clear_log = QAction("Clear &Log", self)
        act_clear_log.triggered.connect(self._log_panel.clear_log)
        file_menu.addAction(act_clear_log)

        file_menu.addSeparator()

        act_exit = QAction("E&xit", self)
        act_exit.setShortcut(QKeySequence("Ctrl+Q"))
        act_exit.triggered.connect(self.close)
        file_menu.addAction(act_exit)

        # View menu
        view_menu = menu_bar.addMenu("&View")
        for i in range(self._tabs.count()):
            tab_name = self._tabs.tabText(i)
            act = QAction(tab_name, self)
            # Ctrl+1 through Ctrl+0 for first 10 tabs
            if i < 10:
                key = str(i + 1) if i < 9 else "0"
                act.setShortcut(QKeySequence(f"Ctrl+{key}"))
            act.triggered.connect(
                lambda checked, idx=i: self._tabs.setCurrentIndex(idx))
            view_menu.addAction(act)

        # Theme menu
        theme_menu = menu_bar.addMenu("&Theme")
        for name in THEMES:
            act = QAction(name, self)
            act.triggered.connect(
                lambda checked, n=name: self._change_theme(n))
            theme_menu.addAction(act)

    # ------------------------------------------------------------------
    # Keyboard shortcuts
    # ------------------------------------------------------------------
    def _setup_shortcuts(self):
        """Register global keyboard shortcuts."""
        # These are declared via QAction shortcuts in _build_menus.
        # Additional non-menu shortcuts can be added here if needed.
        pass

    # ------------------------------------------------------------------
    # Tab change handler (lazy refresh)
    # ------------------------------------------------------------------
    @Slot(int)
    def _on_tab_changed(self, index: int) -> None:
        """Refresh data-heavy panels when their tab is activated."""
        tab_name = self._tabs.tabText(index)
        # Guard: may fire during init before all attrs exist
        if hasattr(self, "_status"):
            self._status.showMessage(f"Switched to {tab_name}", 2000)
        if not hasattr(self, "_tab_indices"):
            return

        if index == self._tab_indices.get("analytics"):
            if hasattr(self._analytics_panel, "refresh"):
                self._analytics_panel.refresh()
        elif index == self._tab_indices.get("sessions"):
            if hasattr(self._sessions_panel, "_refresh_session_tree"):
                self._sessions_panel._refresh_session_tree()
        elif index == self._tab_indices.get("prompts"):
            if hasattr(self._prompts_panel, "refresh_prompt_history"):
                # Reload from disk to pick up newly captured prompts
                self.prompt_database.load()
                self._prompts_panel.refresh_prompt_history()
        elif index == self._tab_indices.get("forking"):
            if hasattr(self._forking_panel, "refresh"):
                self._forking_panel.refresh()

    # ------------------------------------------------------------------
    # Status bar updates
    # ------------------------------------------------------------------
    @Slot(object)
    def _update_file_status(self, files) -> None:
        """Update status bar when file list changes."""
        count = len(files) if files else 0
        total_tokens = sum(t for _, t in files) if files else 0
        self._file_count_label.setText(
            f"Files: {count}  |  Tokens: {total_tokens:,}")

    def _refresh_status_counts(self) -> None:
        """Periodically refresh prompt count in status bar."""
        try:
            prompt_count = len(self.prompt_database.prompts)
            self._prompt_count_label.setText(f"Prompts: {prompt_count}")
        except Exception:
            pass

        if self.current_profile:
            self._profile_label.setText(f"Profile: {self.current_profile}")
        else:
            self._profile_label.setText("No profile")

    # ------------------------------------------------------------------
    # Logging helper
    # ------------------------------------------------------------------
    def log(self, message: str) -> None:
        """Convenience method for logging from the main window."""
        self.log_message.emit(message)

    # ------------------------------------------------------------------
    # Forking → eADR auto-notes
    # ------------------------------------------------------------------

    @Slot(str, str, str, str)
    def _on_branch_forked(self, tree_name: str, parent_name: str,
                          child_name: str, trigger: str) -> None:
        """Auto-create an eADR note when a branch is forked."""
        from llm_buddy.core.eadr import save_eadr_note
        project = self._eadr_panel.project
        note = (
            f"[CF Fork] Branch '{child_name}' forked from "
            f"'{parent_name}' in tree '{tree_name}'.\n"
            f"Trigger: {trigger}"
        )
        save_eadr_note(note, project)
        self._eadr_panel.refresh()
        self.log(f"eADR auto-note: fork '{child_name}' recorded.")

    @Slot(str, str, str)
    def _on_branch_merged(self, tree_name: str, branch_name: str,
                          insights: str) -> None:
        """Auto-create an eADR note when a branch is merged."""
        from llm_buddy.core.eadr import save_eadr_note
        project = self._eadr_panel.project
        note = (
            f"[CF Merge] Branch '{branch_name}' merged "
            f"in tree '{tree_name}'.\n"
        )
        if insights:
            note += f"Insights: {insights}"
        save_eadr_note(note, project)
        self._eadr_panel.refresh()
        self.log(f"eADR auto-note: merge '{branch_name}' recorded.")

    # ------------------------------------------------------------------
    # Theme
    # ------------------------------------------------------------------
    @Slot(str)
    def _change_theme(self, name: str) -> None:
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance()
        if app:
            apply_theme(app, name)
            # Keep theme combo in sync if changed from menu
            if self._theme_combo.currentText() != name:
                self._theme_combo.blockSignals(True)
                self._theme_combo.setCurrentText(name)
                self._theme_combo.blockSignals(False)
            self.log(f"Theme changed to: {name}")

    # ------------------------------------------------------------------
    # Profile management
    # ------------------------------------------------------------------
    @Slot(int)
    def _load_profile(self, _index: int = 0) -> None:
        prof_name = self._profile_combo.currentText().strip()
        if prof_name not in self.profiles:
            return
        prof = self.profiles[prof_name]
        self.folders = prof.get("folders", [])
        self.all_files = prof.get("files", [])
        self.allowed_extensions = prof.get(
            "allowed_extensions", self.allowed_extensions)
        self.min_tokens = prof.get("min_tokens", self.min_tokens)
        self.current_profile = prof_name

        # Sync control panel fields with profile data
        self._control_panel.set_extensions(self.allowed_extensions)
        self._control_panel.set_min_tokens(self.min_tokens)
        if hasattr(self._control_panel, "set_header"):
            self._control_panel.set_header(prof.get("header", ""))
        if hasattr(self._control_panel, "set_footer"):
            self._control_panel.set_footer(prof.get("footer", ""))

        self.log(f"Loaded profile '{prof_name}'.")
        self._refresh_status_counts()
        # Re-apply filters to reflect new data
        self._control_panel.apply_filters()

    @Slot()
    def _save_profile(self) -> None:
        prof_name = self._profile_combo.currentText().strip()
        if not prof_name:
            QMessageBox.warning(self, "Error", "Enter a valid profile name.")
            return
        self.profiles[prof_name] = {
            "folders": self.folders,
            "files": self.all_files,
            "allowed_extensions": self.allowed_extensions,
            "min_tokens": self.min_tokens,
            "header": getattr(self._control_panel, "header_text", ""),
            "footer": getattr(self._control_panel, "footer_text", ""),
        }
        save_profiles(self.profiles)
        # Refresh combo items
        self._profile_combo.clear()
        self._profile_combo.addItems(list(self.profiles.keys()))
        self._profile_combo.setCurrentText(prof_name)
        self.current_profile = prof_name
        self._refresh_status_counts()
        self.log(f"Profile '{prof_name}' saved.")

    @Slot()
    def _new_profile(self) -> None:
        name, ok = QInputDialog.getText(
            self, "New Profile", "Enter new profile name:")
        if ok and name.strip():
            name = name.strip()
            self._profile_combo.setCurrentText(name)
            self.folders = []
            self.all_files = []
            self.filtered_files = []
            self.current_profile = name
            self._refresh_status_counts()
            self.log(f"New profile '{name}' created.")
            self._control_panel.apply_filters()

    # ------------------------------------------------------------------
    # CLI arguments
    # ------------------------------------------------------------------
    def _handle_cli_args(self) -> None:
        for path in sys.argv[1:]:
            if os.path.isfile(path):
                self.all_files.append(path)
                self.log(f"Added via command-line: {path}")
            elif os.path.isdir(path):
                self.folders.append(path)
                self.log(f"Added folder via command-line: {path}")

    # ------------------------------------------------------------------
    # Close handler
    # ------------------------------------------------------------------
    def closeEvent(self, event):
        """Clean up resources on window close."""
        self.log("Shutting down...")

        # Stop periodic status refresh
        self._status_timer.stop()

        # Stop extension server
        self._ext_widget.stop_server()

        # Stop proxy and ensure system proxy is disabled
        self._proxy_widget.stop_proxy()

        # Stop auto-backup observer
        self._backup_panel.stop()

        event.accept()

