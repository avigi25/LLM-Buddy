"""Log panel for the LLM Buddy Qt GUI.

Rich log output with severity-based coloring, search/filter toolbar,
auto-scroll toggle, and monospace formatting.
"""

import re
from datetime import datetime

from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QFont, QTextCursor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QLineEdit, QCheckBox, QLabel, QPushButton,
)

from llm_buddy.qt.theme import get_theme_colors, current_theme_name

# Severity detection patterns
_ERROR_RE = re.compile(
    r"\b(error|fail|exception|critical|fatal)\b", re.IGNORECASE)
_WARN_RE = re.compile(
    r"\b(warn|warning|caution)\b", re.IGNORECASE)
_SUCCESS_RE = re.compile(
    r"\b(started|success|saved|recorded|completed|connected|loaded)\b",
    re.IGNORECASE)


class LogPanel(QWidget):
    """Rich log output panel with severity coloring and search.

    Other panels call :meth:`append` (or connect signals) to add log
    messages. The timestamp is prepended automatically.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._all_entries: list[tuple[str, str]] = []  # (html, plain)
        self._auto_scroll = True

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(6, 4, 6, 4)

        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText(
            "\U0001f50d Filter logs\u2026")
        self._search_edit.setClearButtonEnabled(True)
        self._search_edit.textChanged.connect(self._apply_filter)
        toolbar.addWidget(self._search_edit, stretch=1)

        self._auto_scroll_cb = QCheckBox("Auto-scroll")
        self._auto_scroll_cb.setChecked(True)
        self._auto_scroll_cb.toggled.connect(self._set_auto_scroll)
        toolbar.addWidget(self._auto_scroll_cb)

        self._count_label = QLabel("0 entries")
        self._count_label.setStyleSheet("color: gray; padding: 0 8px;")
        toolbar.addWidget(self._count_label)

        btn_clear = QPushButton("Clear")
        btn_clear.setProperty("class", "danger")
        btn_clear.clicked.connect(self.clear_log)
        toolbar.addWidget(btn_clear)

        layout.addLayout(toolbar)

        self._text = QTextEdit()
        self._text.setReadOnly(True)
        self._text.setFont(QFont("Consolas", 10))
        self._text.setLineWrapMode(QTextEdit.WidgetWidth)
        layout.addWidget(self._text)

    @Slot(str)
    def append(self, message: str) -> None:
        """Append a timestamped, severity-colored message."""
        ts = datetime.now().strftime("%H:%M:%S")
        plain = f"{ts} \u2013 {message}"

        # Detect severity and pick color
        colors = get_theme_colors(current_theme_name())
        if _ERROR_RE.search(message):
            color = colors["error"]
            icon = "\U0001f534"
        elif _WARN_RE.search(message):
            color = colors["warning"]
            icon = "\U0001f7e0"
        elif _SUCCESS_RE.search(message):
            color = colors["success"]
            icon = "\U0001f7e2"
        else:
            color = colors["muted"]
            icon = "\u2022"

        html = (
            f'<div style="margin:1px 0; padding:2px 4px;">'
            f'<span style="color:{colors["muted"]}">{ts}</span> '
            f'{icon} '
            f'<span style="color:{color}">{message}</span>'
            f'</div>'
        )
        self._all_entries.append((html, plain))
        self._count_label.setText(f"{len(self._all_entries)} entries")

        # If filter is active, only append if it matches
        filter_text = self._search_edit.text().strip().lower()
        if filter_text and filter_text not in plain.lower():
            return

        self._text.append(html)
        if self._auto_scroll:
            self._text.moveCursor(QTextCursor.End)

    def clear_log(self) -> None:
        self._all_entries.clear()
        self._text.clear()
        self._count_label.setText("0 entries")

    @Slot(str)
    def _apply_filter(self, text: str) -> None:
        """Re-render log entries matching the filter."""
        needle = text.strip().lower()
        self._text.clear()
        for html, plain in self._all_entries:
            if not needle or needle in plain.lower():
                self._text.append(html)
        if self._auto_scroll:
            self._text.moveCursor(QTextCursor.End)

    @Slot(bool)
    def _set_auto_scroll(self, enabled: bool) -> None:
        self._auto_scroll = enabled
        if enabled:
            self._text.moveCursor(QTextCursor.End)
