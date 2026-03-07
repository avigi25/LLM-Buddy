"""Preview panel for the Qt GUI.

Shows the combined text of all filtered files with live token counts.
Listens for ``files_changed`` signals to auto-refresh.
"""

from PySide6.QtCore import Slot
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPlainTextEdit,
)

from llm_buddy.core.tokens import (
    build_combined_text, build_content_only_text, count_tokens,
)


class PreviewPanel(QWidget):
    """Read-only preview of the combined file content with token counts."""

    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self._mw = main_window

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        self._text = QPlainTextEdit()
        self._text.setReadOnly(True)
        self._text.setLineWrapMode(QPlainTextEdit.WidgetWidth)
        layout.addWidget(self._text, stretch=1)

        token_row = QHBoxLayout()
        self._tok_with = QLabel("Tokens (with headers): 0")
        token_row.addWidget(self._tok_with)
        self._tok_without = QLabel("Tokens (without headers): 0")
        token_row.addWidget(self._tok_without)
        token_row.addStretch()
        layout.addLayout(token_row)

    @Slot(list)
    def update_preview(self, filtered_files=None) -> None:
        """Rebuild the preview text and token counts.

        *filtered_files* is a list of ``(path, tokens)`` tuples.
        If ``None``, uses ``main_window.filtered_files``.
        """
        filtered = filtered_files or self._mw.filtered_files
        file_paths = [p for p, _t in filtered]

        header = ""
        footer = ""
        if hasattr(self._mw, '_control_panel'):
            header = self._mw._control_panel.header
            footer = self._mw._control_panel.footer

        full_text = build_combined_text(file_paths, header, footer)
        self._text.setPlainText(full_text)

        full_tokens = count_tokens(full_text)
        content_only = build_content_only_text(file_paths)
        content_tokens = count_tokens(content_only)

        self._tok_with.setText(
            f"Tokens (with headers): {full_tokens:,}")
        self._tok_without.setText(
            f"Tokens (without headers): {content_tokens:,}")

        self._mw.log(
            f"Preview updated. Tokens (with headers): {full_tokens:,}; "
            f"(without): {content_tokens:,}")
