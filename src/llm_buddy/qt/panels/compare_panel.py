"""Compare panel – diff any two text-based files or backup entries.

VSCode-style split view: File A on the left, File B on the right,
with inline background-colour diff highlighting and synchronised scrolling.
"""

import difflib
import os

from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QColor, QTextCharFormat, QTextBlockFormat, QTextCursor, QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QLabel, QLineEdit, QPushButton, QTextEdit,
    QGroupBox, QFileDialog, QMessageBox, QComboBox, QFrame,
)

from llm_buddy.core.rollback import (
    parse_combined_file, read_file_content,
)
from llm_buddy.qt.theme import get_theme_colors, current_theme_name

_SOURCE_STANDALONE = "Standalone File"
_SOURCE_BACKUP = "File Inside Backup"

# Diff line classification tags
_TAG_EQUAL    = "equal"
_TAG_REPLACE  = "replace"   # changed line (present on both sides)
_TAG_DELETE   = "delete"    # only in A
_TAG_INSERT   = "insert"    # only in B
_TAG_EMPTY    = "empty"     # padding line inserted for alignment


def _build_aligned_diff(
    lines_a: list[str],
    lines_b: list[str],
) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """Return *(aligned_a, aligned_b)*.

    Each element is a ``(line_text, tag)`` tuple where *tag* is one of the
    ``_TAG_*`` constants above.  Empty-string padding lines (``_TAG_EMPTY``)
    are inserted so that corresponding changed blocks align vertically.
    """
    matcher = difflib.SequenceMatcher(None, lines_a, lines_b, autojunk=False)
    aligned_a: list[tuple[str, str]] = []
    aligned_b: list[tuple[str, str]] = []

    for opcode, i1, i2, j1, j2 in matcher.get_opcodes():
        if opcode == "equal":
            for line in lines_a[i1:i2]:
                aligned_a.append((line, _TAG_EQUAL))
                aligned_b.append((line, _TAG_EQUAL))

        elif opcode == "replace":
            block_a = lines_a[i1:i2]
            block_b = lines_b[j1:j2]
            max_len = max(len(block_a), len(block_b))
            for k in range(max_len):
                a_line = block_a[k] if k < len(block_a) else ""
                b_line = block_b[k] if k < len(block_b) else ""
                aligned_a.append((a_line, _TAG_REPLACE if k < len(block_a) else _TAG_EMPTY))
                aligned_b.append((b_line, _TAG_REPLACE if k < len(block_b) else _TAG_EMPTY))

        elif opcode == "delete":
            for line in lines_a[i1:i2]:
                aligned_a.append((line, _TAG_DELETE))
                aligned_b.append(("", _TAG_EMPTY))

        elif opcode == "insert":
            for line in lines_b[j1:j2]:
                aligned_a.append(("", _TAG_EMPTY))
                aligned_b.append((line, _TAG_INSERT))

    return aligned_a, aligned_b


def _diff_colors(side: str) -> dict[str, QColor]:
    """Return background QColors for each tag on *side* ('a' or 'b').

    Colours adapt to the active theme (dark/light).
    """
    theme = current_theme_name()
    dark = (theme == "Dark")

    if dark:
        # Dark theme – VSCode-like muted colours
        return {
            _TAG_EQUAL:   QColor(0, 0, 0, 0),          # transparent
            _TAG_EMPTY:   QColor(40, 40, 40),
            _TAG_DELETE:  QColor(110, 35, 35),          # dark red
            _TAG_INSERT:  QColor(35, 80, 45),           # dark green
            _TAG_REPLACE: QColor(110, 35, 35) if side == "a" else QColor(35, 80, 45),
        }
    else:
        # Light theme
        return {
            _TAG_EQUAL:   QColor(0, 0, 0, 0),
            _TAG_EMPTY:   QColor(230, 230, 230),
            _TAG_DELETE:  QColor(255, 210, 210),        # light red
            _TAG_INSERT:  QColor(210, 240, 210),        # light green
            _TAG_REPLACE: QColor(255, 210, 210) if side == "a" else QColor(210, 240, 210),
        }


class _DiffPane(QWidget):
    """A labelled, read-only text pane used for one side of the diff view."""

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header bar
        self._header = QLabel(title)
        self._header.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self._header.setContentsMargins(6, 4, 6, 4)
        self._header.setStyleSheet(
            "font-weight: bold; font-size: 11px;"
            "background: palette(mid); border-bottom: 1px solid palette(dark);"
        )
        layout.addWidget(self._header)

        # Text area
        self._edit = QTextEdit()
        self._edit.setReadOnly(True)
        self._edit.setLineWrapMode(QTextEdit.NoWrap)
        self._edit.setFont(QFont("Courier New", 9))
        self._edit.setStyleSheet("border: none;")
        layout.addWidget(self._edit, stretch=1)

    def set_title(self, title: str) -> None:
        self._edit_title = title
        # Truncate long paths for the header label
        if len(title) > 80:
            title = "…" + title[-77:]
        self._header.setText(title)
        self._header.setToolTip(title)

    def scroll_bar(self):
        return self._edit.verticalScrollBar()

    def h_scroll_bar(self):
        return self._edit.horizontalScrollBar()

    def populate(self, aligned: list[tuple[str, str]], side: str) -> None:
        """Fill the pane with *aligned* ``(text, tag)`` lines and colour them."""
        colors = _diff_colors(side)
        edit = self._edit
        edit.clear()
        cursor = edit.textCursor()
        cursor.beginEditBlock()

        transparent = QColor(0, 0, 0, 0)
        first = True
        for text, tag in aligned:
            if not first:
                cursor.insertBlock()
            first = False

            # Block (background) format
            blk_fmt = QTextBlockFormat()
            bg = colors.get(tag, transparent)
            if bg != transparent:
                blk_fmt.setBackground(bg)
            cursor.setBlockFormat(blk_fmt)

            # Char format – use a slightly dimmer foreground for padding lines
            char_fmt = QTextCharFormat()
            if tag == _TAG_EMPTY:
                char_fmt.setForeground(QColor(100, 100, 100))
            cursor.setCharFormat(char_fmt)
            cursor.insertText(text)

        cursor.endEditBlock()

        # Scroll back to top after populating
        edit.moveCursor(QTextCursor.Start)


class _FilePicker(QWidget):
    """Reusable picker that can load a standalone file or a file from a backup."""

    def __init__(self, label: str, parent=None):
        super().__init__(parent)
        self._parsed: dict[str, str] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        grp = QGroupBox(label)
        grp_layout = QVBoxLayout(grp)
        grp_layout.setSpacing(4)

        # Row 1: source selector + path + browse
        row1 = QHBoxLayout()

        self._source = QComboBox()
        self._source.addItems([_SOURCE_STANDALONE, _SOURCE_BACKUP])
        self._source.setToolTip(
            "Choose whether this is a standalone file on disk\n"
            "or a specific file extracted from a combined backup")
        self._source.currentIndexChanged.connect(self._on_source_changed)
        row1.addWidget(self._source)

        self._path = QLineEdit()
        self._path.setPlaceholderText("Path to file or backup…")
        row1.addWidget(self._path, stretch=1)

        self._btn_browse = QPushButton("Browse")
        self._btn_browse.setToolTip("Browse for a file or backup on disk")
        self._btn_browse.clicked.connect(self._browse)
        row1.addWidget(self._btn_browse)
        grp_layout.addLayout(row1)

        # Row 2: entry selector (backup mode only)
        row2 = QHBoxLayout()
        self._entry_label = QLabel("Entry:")
        row2.addWidget(self._entry_label)
        self._entry_combo = QComboBox()
        self._entry_combo.setSizeAdjustPolicy(
            QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self._entry_combo.setMinimumContentsLength(40)
        self._entry_combo.setToolTip(
            "Select which file inside the backup to use for comparison")
        row2.addWidget(self._entry_combo, stretch=1)
        self._btn_load = QPushButton("Load Backup")
        self._btn_load.setToolTip(
            "Parse the backup file and populate the entry list\n"
            "so you can pick a specific file inside it")
        self._btn_load.clicked.connect(self._load_backup)
        row2.addWidget(self._btn_load)
        grp_layout.addLayout(row2)

        self._entry_label.setVisible(False)
        self._entry_combo.setVisible(False)
        self._btn_load.setVisible(False)

        layout.addWidget(grp)

    # -- visibility toggle -------------------------------------------------

    @Slot()
    def _on_source_changed(self, _index: int) -> None:
        is_backup = self._source.currentText() == _SOURCE_BACKUP
        self._entry_label.setVisible(is_backup)
        self._entry_combo.setVisible(is_backup)
        self._btn_load.setVisible(is_backup)

    # -- browse / load -----------------------------------------------------

    @Slot()
    def _browse(self) -> None:
        is_backup = self._source.currentText() == _SOURCE_BACKUP
        caption = "Select Backup File" if is_backup else "Select File"
        filt = ("Markdown files (*.md);;All files (*.*)"
                if is_backup else "All files (*.*)")
        path, _ = QFileDialog.getOpenFileName(self, caption, "", filt)
        if not path:
            return
        self._path.setText(path)
        if is_backup:
            self._load_backup()

    @Slot()
    def _load_backup(self) -> None:
        path = self._path.text().strip()
        if not path or not os.path.exists(path):
            QMessageBox.warning(self, "Error",
                                "Please select a valid backup file first.")
            return
        parsed = parse_combined_file(path)
        if not parsed:
            QMessageBox.warning(self, "Error",
                                "Could not parse any files from this backup.")
            return
        self._parsed = parsed
        self._entry_combo.clear()
        for fp in parsed:
            self._entry_combo.addItem(fp)

    # -- public helpers ----------------------------------------------------

    def resolve(self):
        """Return *(content, label)* or *(None, error_msg)*."""
        source = self._source.currentText()
        path = self._path.text().strip()
        if not path:
            return None, "No path specified."
        if source == _SOURCE_STANDALONE:
            content, err = read_file_content(path)
            if err:
                return None, err
            return content, path
        else:
            entry = self._entry_combo.currentText()
            if not entry or entry not in self._parsed:
                return None, "Please load the backup and select an entry first."
            label = f"{os.path.basename(path)} \u2192 {entry}"
            return self._parsed[entry], label

    def get_state(self) -> dict:
        return {
            "source_idx":  self._source.currentIndex(),
            "path":        self._path.text(),
            "parsed":      self._parsed.copy(),
            "items":       [self._entry_combo.itemText(i)
                            for i in range(self._entry_combo.count())],
            "entry_idx":   self._entry_combo.currentIndex(),
        }

    def set_state(self, state: dict) -> None:
        self._source.setCurrentIndex(state["source_idx"])
        self._path.setText(state["path"])
        self._parsed = state["parsed"]
        self._entry_combo.clear()
        self._entry_combo.addItems(state["items"])
        if state["entry_idx"] >= 0:
            self._entry_combo.setCurrentIndex(state["entry_idx"])


class _Legend(QWidget):
    """Compact horizontal colour legend for the diff view."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(12)
        layout.addStretch()
        self._swatches: list[QLabel] = []
        self._update()

    def _update(self) -> None:
        # Clear existing swatches
        while self._swatches:
            w = self._swatches.pop()
            w.deleteLater()

        dark = current_theme_name() == "Dark"
        entries = [
            ("Removed",  "#6e2323" if dark else "#ffd2d2"),
            ("Added",    "#23503a" if dark else "#d2f0d2"),
            ("Modified", "#6e2323" if dark else "#ffd2d2"),  # shown on left
            ("Padding",  "#282828" if dark else "#e6e6e6"),
        ]
        layout = self.layout()
        for label_text, color in entries:
            swatch = QLabel()
            swatch.setFixedSize(14, 14)
            swatch.setStyleSheet(
                f"background-color: {color}; border: 1px solid palette(mid); border-radius: 2px;")
            txt = QLabel(label_text)
            txt.setStyleSheet("font-size: 10px; color: palette(mid);")
            layout.addWidget(swatch)
            layout.addWidget(txt)
            self._swatches.extend([swatch, txt])
        layout.addStretch()


class ComparePanel(QWidget):
    """VSCode-style split-pane file comparison.

    The top section holds the two file pickers and action buttons.
    The bottom section is a horizontal QSplitter with two diff panes:
    File A (left) and File B (right), highlighting additions/deletions
    with background colours and keeping both panes scrolled in sync.
    """

    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self._mw = main_window
        self._sync_scroll = True   # guard against recursive scroll events

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        pickers_row = QHBoxLayout()
        pickers_row.setSpacing(6)
        self._picker_a = _FilePicker("File A  (left)", self)
        self._picker_b = _FilePicker("File B  (right)", self)
        pickers_row.addWidget(self._picker_a)
        pickers_row.addWidget(self._picker_b)
        layout.addLayout(pickers_row)

        action_row = QHBoxLayout()
        action_row.addStretch()

        btn_compare = QPushButton("⟳  Compare")
        btn_compare.setProperty("class", "primary")
        btn_compare.setToolTip("Compute and display the diff between File A and File B")
        btn_compare.clicked.connect(self._compare)
        action_row.addWidget(btn_compare)

        btn_swap = QPushButton("⇄  Swap A ↔ B")
        btn_swap.setToolTip("Swap the two file selections")
        btn_swap.clicked.connect(self._swap)
        action_row.addWidget(btn_swap)

        action_row.addStretch()
        layout.addLayout(action_row)

        self._legend = _Legend(self)
        layout.addWidget(self._legend)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(4)

        self._pane_a = _DiffPane("File A", self)
        self._pane_b = _DiffPane("File B", self)

        splitter.addWidget(self._pane_a)
        splitter.addWidget(self._pane_b)
        splitter.setSizes([1, 1])           # equal initial widths
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        layout.addWidget(splitter, stretch=1)

        self._stats = QLabel("")
        self._stats.setStyleSheet("font-size: 10px; color: palette(mid);")
        self._stats.setContentsMargins(4, 0, 4, 0)
        layout.addWidget(self._stats)

        self._pane_a.scroll_bar().valueChanged.connect(self._sync_v_from_a)
        self._pane_b.scroll_bar().valueChanged.connect(self._sync_v_from_b)
        self._pane_a.h_scroll_bar().valueChanged.connect(self._sync_h_from_a)
        self._pane_b.h_scroll_bar().valueChanged.connect(self._sync_h_from_b)

    @Slot(int)
    def _sync_v_from_a(self, value: int) -> None:
        if self._sync_scroll:
            self._sync_scroll = False
            self._pane_b.scroll_bar().setValue(value)
            self._sync_scroll = True

    @Slot(int)
    def _sync_v_from_b(self, value: int) -> None:
        if self._sync_scroll:
            self._sync_scroll = False
            self._pane_a.scroll_bar().setValue(value)
            self._sync_scroll = True

    @Slot(int)
    def _sync_h_from_a(self, value: int) -> None:
        if self._sync_scroll:
            self._sync_scroll = False
            self._pane_b.h_scroll_bar().setValue(value)
            self._sync_scroll = True

    @Slot(int)
    def _sync_h_from_b(self, value: int) -> None:
        if self._sync_scroll:
            self._sync_scroll = False
            self._pane_a.h_scroll_bar().setValue(value)
            self._sync_scroll = True

    # -- compare -----------------------------------------------------------

    @Slot()
    def _compare(self) -> None:
        res_a = self._picker_a.resolve()
        res_b = self._picker_b.resolve()

        if res_a[0] is None:
            QMessageBox.warning(self, "File A Error", res_a[1])
            return
        if res_b[0] is None:
            QMessageBox.warning(self, "File B Error", res_b[1])
            return

        content_a, label_a = res_a
        content_b, label_b = res_b

        lines_a = content_a.splitlines()
        lines_b = content_b.splitlines()

        aligned_a, aligned_b = _build_aligned_diff(lines_a, lines_b)

        self._pane_a.set_title(label_a)
        self._pane_b.set_title(label_b)

        self._pane_a.populate(aligned_a, side="a")
        self._pane_b.populate(aligned_b, side="b")

        # Build summary stats
        n_del     = sum(1 for _, t in aligned_a if t == _TAG_DELETE)
        n_ins     = sum(1 for _, t in aligned_b if t == _TAG_INSERT)
        n_replace = sum(1 for _, t in aligned_a if t == _TAG_REPLACE)
        n_equal   = sum(1 for _, t in aligned_a if t == _TAG_EQUAL)
        total     = len(lines_a) + len(lines_b)

        self._stats.setText(
            f"  Lines: {len(lines_a)} (A)  /  {len(lines_b)} (B)   │   "
            f"  ✕ {n_del} removed   +{n_ins} added   ~ {n_replace} changed   "
            f"= {n_equal} identical"
        )

        self._mw.log(
            f"Compared: {os.path.basename(label_a)}  vs  {os.path.basename(label_b)}  "
            f"[−{n_del}  +{n_ins}  ~{n_replace}]"
        )

    # -- swap --------------------------------------------------------------

    @Slot()
    def _swap(self) -> None:
        state_a = self._picker_a.get_state()
        state_b = self._picker_b.get_state()
        self._picker_a.set_state(state_b)
        self._picker_b.set_state(state_a)