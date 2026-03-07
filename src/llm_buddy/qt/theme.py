"""Theming and colour palette for the LLM Buddy Qt GUI.

Provides Light, Dark, and Blue accent themes with comprehensive QSS
styling for all standard widgets plus QPalette overrides for proper
dark-mode rendering of native controls.

Also exports reusable helper widgets:
- ``StatusBadge`` – a rounded-pill status indicator label
- ``get_theme_colors()`` – returns a color dict for the named theme
"""

from PySide6.QtCore import Qt, Property, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QColor, QPalette, QFont
from PySide6.QtWidgets import QApplication, QLabel, QFrame, QVBoxLayout

# ── Chart colour palette (Tableau 10) ────────────────────────────────
CHART_PALETTE = [
    "#4e79a7", "#f28e2b", "#e15759", "#76b7b2",
    "#59a14f", "#edc948", "#b07aa1", "#ff9da7",
    "#9c755f", "#bab0ac",
]

# Timeline event colours
EVENT_COLOURS = {
    "prompt": "#4e79a7",
    "note": "#59a14f",
    "backup": "#f28e2b",
    "file_change": "#e15759",
}

# Status colours (accessible from any module)
STATUS_GREEN = "#2e7d32"
STATUS_RED = "#c62828"
STATUS_ORANGE = "#ef6c00"
STATUS_GRAY = "#757575"


# ── Shared base fragments ────────────────────────────────────────────

_SHARED_WIDGET_RADIUS = "4px"

_SCROLLBAR_LIGHT = """
QScrollBar:vertical {
    background: #f0f0f0;
    width: 12px;
    margin: 0;
    border-radius: 6px;
}
QScrollBar::handle:vertical {
    background: #c0c0c0;
    min-height: 30px;
    border-radius: 5px;
    margin: 2px;
}
QScrollBar::handle:vertical:hover {
    background: #a0a0a0;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
QScrollBar:horizontal {
    background: #f0f0f0;
    height: 12px;
    margin: 0;
    border-radius: 6px;
}
QScrollBar::handle:horizontal {
    background: #c0c0c0;
    min-width: 30px;
    border-radius: 5px;
    margin: 2px;
}
QScrollBar::handle:horizontal:hover {
    background: #a0a0a0;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0;
}
"""

_SCROLLBAR_DARK = """
QScrollBar:vertical {
    background: #2a2a2a;
    width: 12px;
    margin: 0;
    border-radius: 6px;
}
QScrollBar::handle:vertical {
    background: #555;
    min-height: 30px;
    border-radius: 5px;
    margin: 2px;
}
QScrollBar::handle:vertical:hover {
    background: #777;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
QScrollBar:horizontal {
    background: #2a2a2a;
    height: 12px;
    margin: 0;
    border-radius: 6px;
}
QScrollBar::handle:horizontal {
    background: #555;
    min-width: 30px;
    border-radius: 5px;
    margin: 2px;
}
QScrollBar::handle:horizontal:hover {
    background: #777;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0;
}
"""

_TOOLTIP_LIGHT = """
QToolTip {
    background-color: #424242;
    color: #fff;
    border: 1px solid #616161;
    border-radius: 4px;
    padding: 4px 8px;
    font-size: 12px;
}
"""

_TOOLTIP_DARK = """
QToolTip {
    background-color: #f5f5f5;
    color: #212121;
    border: 1px solid #bdbdbd;
    border-radius: 4px;
    padding: 4px 8px;
    font-size: 12px;
}
"""


# ══════════════════════════════════════════════════════════════════════
# Light theme
# ══════════════════════════════════════════════════════════════════════

LIGHT_QSS = (
    _TOOLTIP_LIGHT
    + _SCROLLBAR_LIGHT
    + """
/* ── Window & containers ─────────────────────────────────────────── */
QMainWindow {
    background-color: #fafafa;
    color: #333;
}
QSplitter::handle {
    background: #e0e0e0;
    width: 3px;
}
QSplitter::handle:hover {
    background: #1976d2;
}

/* ── Labels ──────────────────────────────────────────────────────── */
QLabel {
    color: #333;
}

/* ── Tab widget ──────────────────────────────────────────────────── */
QTabWidget::pane {
    border: 1px solid #d0d0d0;
    border-radius: 4px;
    background: white;
}
QTabBar::tab {
    padding: 7px 18px;
    margin-right: 2px;
    border: 1px solid #d0d0d0;
    border-bottom: none;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    background: #f0f0f0;
    color: #555;
    font-size: 13px;
}
QTabBar::tab:hover {
    background: #e8e8e8;
    color: #333;
}
QTabBar::tab:selected {
    background: white;
    color: #1976d2;
    font-weight: bold;
    border-bottom: 2px solid #1976d2;
}

/* ── Group boxes ─────────────────────────────────────────────────── */
QGroupBox {
    font-weight: bold;
    font-size: 13px;
    border: 1px solid #d0d0d0;
    border-radius: 6px;
    margin-top: 10px;
    padding-top: 18px;
    color: #333;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    color: #1976d2;
}

/* ── Trees ───────────────────────────────────────────────────────── */
QTreeView {
    alternate-background-color: #f5f8ff;
    background-color: #ffffff;
    color: #333;
    border: 1px solid #d0d0d0;
    border-radius: 4px;
    font-size: 13px;
}
QTreeView::item {
    padding: 3px 0;
}
QTreeView::item:selected {
    background-color: #bbdefb;
    color: black;
}
QTreeView::item:hover {
    background-color: #e3f2fd;
}
QHeaderView::section {
    background-color: #f5f5f5;
    border: 1px solid #d0d0d0;
    border-left: none;
    padding: 5px 8px;
    font-weight: bold;
    font-size: 12px;
    color: #555;
}

/* ── Text areas ──────────────────────────────────────────────────── */
QPlainTextEdit, QTextBrowser {
    background-color: #ffffff;
    color: #333;
    border: 1px solid #d0d0d0;
    border-radius: 4px;
    font-size: 13px;
    selection-background-color: #bbdefb;
}
QPlainTextEdit:focus, QTextBrowser:focus {
    border: 1px solid #1976d2;
}

/* ── Buttons ─────────────────────────────────────────────────────── */
QPushButton {
    padding: 6px 16px;
    border: 1px solid #bdbdbd;
    border-radius: 4px;
    background-color: #f5f5f5;
    color: #333;
    font-size: 13px;
    min-height: 20px;
}
QPushButton:hover {
    background-color: #e3f2fd;
    border-color: #90caf9;
}
QPushButton:pressed {
    background-color: #bbdefb;
}
QPushButton:disabled {
    color: #aaa;
    background-color: #f0f0f0;
    border-color: #e0e0e0;
}
/* Primary action buttons (use setProperty("class", "primary") in code) */
QPushButton[class="primary"] {
    background-color: #1976d2;
    color: white;
    border: 1px solid #1565c0;
    font-weight: bold;
}
QPushButton[class="primary"]:hover {
    background-color: #1e88e5;
}
QPushButton[class="primary"]:pressed {
    background-color: #1565c0;
}
/* Danger buttons */
QPushButton[class="danger"] {
    background-color: #e53935;
    color: white;
    border: 1px solid #c62828;
}
QPushButton[class="danger"]:hover {
    background-color: #ef5350;
}

/* Capture source Start/Stop buttons (outline variants) */
QPushButton[class="start_action"] {
    background-color: transparent;
    color: #1976d2;
    border: 1px solid #1976d2;
    font-weight: bold;
}
QPushButton[class="start_action"]:hover {
    background-color: rgba(25, 118, 210, 0.10);
}
QPushButton[class="start_action"]:pressed {
    background-color: rgba(25, 118, 210, 0.20);
}
QPushButton[class="start_action"]:disabled {
    background-color: #f0f0f0;
    color: #aaa;
    border-color: #e0e0e0;
    font-weight: normal;
}

QPushButton[class="stop_action"] {
    background-color: transparent;
    color: #e53935;
    border: 1px solid #e53935;
    font-weight: bold;
}
QPushButton[class="stop_action"]:hover {
    background-color: rgba(229, 57, 53, 0.10);
}
QPushButton[class="stop_action"]:pressed {
    background-color: rgba(229, 57, 53, 0.20);
}
QPushButton[class="stop_action"]:disabled {
    background-color: #f0f0f0;
    color: #aaa;
    border-color: #e0e0e0;
    font-weight: normal;
}

/* ── Inputs ──────────────────────────────────────────────────────── */
QLineEdit, QComboBox, QSpinBox {
    padding: 5px 8px;
    border: 1px solid #d0d0d0;
    border-radius: 4px;
    background: white;
    color: #333;
    font-size: 13px;
    min-height: 18px;
}
QLineEdit:focus, QSpinBox:focus {
    border: 1px solid #1976d2;
}
QComboBox::drop-down {
    border: none;
    width: 24px;
}
QComboBox QAbstractItemView {
    background-color: #ffffff;
    color: #333;
    border: 1px solid #d0d0d0;
    border-radius: 4px;
    selection-background-color: #bbdefb;
    selection-color: black;
}
QCheckBox {
    spacing: 6px;
    font-size: 13px;
    color: #333;
}
QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border-radius: 3px;
    border: 1px solid #bdbdbd;
    background-color: #ffffff;
}
QCheckBox::indicator:checked {
    background-color: #1976d2;
    border-color: #1565c0;
}

/* ── Status bar ──────────────────────────────────────────────────── */
QStatusBar {
    background: #f5f5f5;
    border-top: 1px solid #e0e0e0;
    font-size: 12px;
    color: #666;
}

/* ── Progress bar ────────────────────────────────────────────────── */
QProgressBar {
    background-color: #f0f0f0;
    color: #333;
    border: 1px solid #d0d0d0;
    border-radius: 4px;
    text-align: center;
    font-size: 12px;
    min-height: 18px;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #1976d2, stop:1 #42a5f5);
    border-radius: 3px;
}

/* ── Menu bar ────────────────────────────────────────────────────── */
QMenuBar {
    background: #f5f5f5;
    color: #333;
    border-bottom: 1px solid #e0e0e0;
    font-size: 13px;
}
QMenuBar::item:selected {
    background: #e3f2fd;
    border-radius: 4px;
}
QMenu {
    background: white;
    color: #333;
    border: 1px solid #d0d0d0;
    border-radius: 4px;
    padding: 4px;
}
QMenu::item {
    padding: 6px 24px;
    border-radius: 3px;
}
QMenu::item:selected {
    background-color: #e3f2fd;
}

/* ── Toolbar ─────────────────────────────────────────────────────── */
QToolBar {
    background: #f5f5f5;
    border-bottom: 1px solid #e0e0e0;
    spacing: 4px;
    padding: 2px;
}

/* ── Dialogs ─────────────────────────────────────────────────────── */
QDialog {
    background-color: #fafafa;
    color: #333;
}
QMessageBox {
    background-color: #fafafa;
    color: #333;
}
QMessageBox QLabel {
    color: #333;
}
"""
)


# ══════════════════════════════════════════════════════════════════════
# Dark theme
# ══════════════════════════════════════════════════════════════════════

DARK_QSS = (
    _TOOLTIP_DARK
    + _SCROLLBAR_DARK
    + """
/* ── Window & containers ─────────────────────────────────────────── */
QMainWindow {
    background-color: #1e1e1e;
    color: #ddd;
}
QSplitter::handle {
    background: #3a3a3a;
    width: 3px;
}
QSplitter::handle:hover {
    background: #64b5f6;
}

/* ── Labels ──────────────────────────────────────────────────────── */
QLabel {
    color: #ddd;
}

/* ── Tab widget ──────────────────────────────────────────────────── */
QTabWidget::pane {
    border: 1px solid #444;
    border-radius: 4px;
    background: #1e1e1e;
}
QTabBar::tab {
    padding: 7px 18px;
    margin-right: 2px;
    border: 1px solid #444;
    border-bottom: none;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    background: #2d2d2d;
    color: #999;
    font-size: 13px;
}
QTabBar::tab:hover {
    background: #383838;
    color: #ccc;
}
QTabBar::tab:selected {
    background: #1e1e1e;
    color: #64b5f6;
    font-weight: bold;
    border-bottom: 2px solid #64b5f6;
}

/* ── Group boxes ─────────────────────────────────────────────────── */
QGroupBox {
    font-weight: bold;
    font-size: 13px;
    border: 1px solid #444;
    border-radius: 6px;
    margin-top: 10px;
    padding-top: 18px;
    color: #ddd;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    color: #64b5f6;
}

/* ── Trees ───────────────────────────────────────────────────────── */
QTreeView {
    alternate-background-color: #262626;
    background-color: #1e1e1e;
    border: 1px solid #444;
    border-radius: 4px;
    color: #ddd;
    font-size: 13px;
}
QTreeView::item {
    padding: 3px 0;
}
QTreeView::item:selected {
    background-color: #1565c0;
    color: white;
}
QTreeView::item:hover {
    background-color: #2a3a4a;
}
QHeaderView::section {
    background-color: #2d2d2d;
    border: 1px solid #444;
    border-left: none;
    padding: 5px 8px;
    font-weight: bold;
    font-size: 12px;
    color: #aaa;
}

/* ── Text areas ──────────────────────────────────────────────────── */
QPlainTextEdit, QTextBrowser {
    background-color: #1e1e1e;
    color: #ddd;
    border: 1px solid #444;
    border-radius: 4px;
    font-size: 13px;
    selection-background-color: #1565c0;
    selection-color: white;
}
QPlainTextEdit:focus, QTextBrowser:focus {
    border: 1px solid #64b5f6;
}

/* ── Buttons ─────────────────────────────────────────────────────── */
QPushButton {
    padding: 6px 16px;
    border: 1px solid #555;
    border-radius: 4px;
    background-color: #333;
    color: #ddd;
    font-size: 13px;
    min-height: 20px;
}
QPushButton:hover {
    background-color: #2a3a4a;
    border-color: #5a8abf;
}
QPushButton:pressed {
    background-color: #1565c0;
    color: white;
}
QPushButton:disabled {
    color: #666;
    background-color: #2a2a2a;
    border-color: #3a3a3a;
}
QPushButton[class="primary"] {
    background-color: #1565c0;
    color: white;
    border: 1px solid #0d47a1;
    font-weight: bold;
}
QPushButton[class="primary"]:hover {
    background-color: #1976d2;
}
QPushButton[class="primary"]:pressed {
    background-color: #0d47a1;
}
QPushButton[class="danger"] {
    background-color: #c62828;
    color: white;
    border: 1px solid #b71c1c;
}
QPushButton[class="danger"]:hover {
    background-color: #e53935;
}

/* Capture source Start/Stop buttons (outline variants) */
QPushButton[class="start_action"] {
    background-color: transparent;
    color: #64b5f6;
    border: 1px solid #64b5f6;
    font-weight: bold;
}
QPushButton[class="start_action"]:hover {
    background-color: rgba(100, 181, 246, 0.15);
}
QPushButton[class="start_action"]:pressed {
    background-color: rgba(100, 181, 246, 0.25);
}
QPushButton[class="start_action"]:disabled {
    background-color: #2a2a2a;
    color: #666;
    border-color: #3a3a3a;
    font-weight: normal;
}

QPushButton[class="stop_action"] {
    background-color: transparent;
    color: #ef5350;
    border: 1px solid #ef5350;
    font-weight: bold;
}
QPushButton[class="stop_action"]:hover {
    background-color: rgba(239, 83, 80, 0.15);
}
QPushButton[class="stop_action"]:pressed {
    background-color: rgba(239, 83, 80, 0.25);
}
QPushButton[class="stop_action"]:disabled {
    background-color: #2a2a2a;
    color: #666;
    border-color: #3a3a3a;
    font-weight: normal;
}

/* ── Inputs ──────────────────────────────────────────────────────── */
QLineEdit, QComboBox, QSpinBox {
    background-color: #2d2d2d;
    color: #ddd;
    border: 1px solid #555;
    border-radius: 4px;
    padding: 5px 8px;
    font-size: 13px;
    min-height: 18px;
}
QLineEdit:focus, QSpinBox:focus {
    border: 1px solid #64b5f6;
}
QComboBox::drop-down {
    border: none;
    width: 24px;
}
QComboBox QAbstractItemView {
    background-color: #2d2d2d;
    border: 1px solid #555;
    border-radius: 4px;
    color: #ddd;
    selection-background-color: #1565c0;
    selection-color: white;
}
QCheckBox {
    spacing: 6px;
    color: #ddd;
    font-size: 13px;
}
QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border-radius: 3px;
    border: 1px solid #666;
    background-color: #333;
}
QCheckBox::indicator:checked {
    background-color: #1565c0;
    border-color: #0d47a1;
}

/* ── Status bar ──────────────────────────────────────────────────── */
QStatusBar {
    background: #2d2d2d;
    border-top: 1px solid #444;
    color: #aaa;
    font-size: 12px;
}

/* ── Progress bar ────────────────────────────────────────────────── */
QProgressBar {
    border: 1px solid #444;
    border-radius: 4px;
    text-align: center;
    color: #ddd;
    font-size: 12px;
    background: #2a2a2a;
    min-height: 18px;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #1565c0, stop:1 #42a5f5);
    border-radius: 3px;
}

/* ── Menu bar ────────────────────────────────────────────────────── */
QMenuBar {
    background: #2d2d2d;
    border-bottom: 1px solid #444;
    color: #ddd;
    font-size: 13px;
}
QMenuBar::item:selected {
    background: #3a3a3a;
    border-radius: 4px;
}
QMenu {
    background: #2d2d2d;
    border: 1px solid #555;
    border-radius: 4px;
    padding: 4px;
    color: #ddd;
}
QMenu::item {
    padding: 6px 24px;
    border-radius: 3px;
}
QMenu::item:selected {
    background-color: #1565c0;
}

/* ── Toolbar ─────────────────────────────────────────────────────── */
QToolBar {
    background: #2d2d2d;
    border-bottom: 1px solid #444;
    spacing: 4px;
    padding: 2px;
}

/* ── Dialog ──────────────────────────────────────────────────────── */
QDialog {
    background-color: #1e1e1e;
    color: #ddd;
}
QMessageBox {
    background-color: #1e1e1e;
    color: #ddd;
}
QMessageBox QLabel {
    color: #ddd;
}
"""
)


# ══════════════════════════════════════════════════════════════════════
# Blue Accent theme (light base with blue accent colour)
# ══════════════════════════════════════════════════════════════════════

BLUE_ACCENT_QSS = (
    _TOOLTIP_LIGHT
    + _SCROLLBAR_LIGHT
    + """
/* ── Window & containers ─────────────────────────────────────────── */
QMainWindow {
    background-color: #e8eef7;
    color: #333;
}
QSplitter::handle {
    background: #c5cfe0;
    width: 3px;
}
QSplitter::handle:hover {
    background: #1565c0;
}

/* ── Labels ──────────────────────────────────────────────────────── */
QLabel {
    color: #333;
}

/* ── Tab widget ──────────────────────────────────────────────────── */
QTabWidget::pane {
    border: 1px solid #b0c4de;
    border-radius: 4px;
    background: #f0f4fa;
}
QTabBar::tab {
    padding: 7px 18px;
    margin-right: 2px;
    border: 1px solid #b0c4de;
    border-bottom: none;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    background: #dce6f5;
    color: #555;
    font-size: 13px;
}
QTabBar::tab:hover {
    background: #c8d8f0;
    color: #333;
}
QTabBar::tab:selected {
    background: #f0f4fa;
    color: #0d47a1;
    font-weight: bold;
    border-bottom: 2px solid #1565c0;
}

/* ── Group boxes ─────────────────────────────────────────────────── */
QGroupBox {
    font-weight: bold;
    font-size: 13px;
    border: 1px solid #b0c4de;
    border-radius: 6px;
    margin-top: 10px;
    padding-top: 18px;
    background: #f0f4fa;
    color: #333;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    color: #0d47a1;
}

/* ── Trees ───────────────────────────────────────────────────────── */
QTreeView {
    alternate-background-color: #e8eef7;
    background: #f5f8fc;
    border: 1px solid #b0c4de;
    border-radius: 4px;
    font-size: 13px;
    color: #333;
}
QTreeView::item { padding: 3px 0; }
QTreeView::item:selected { background-color: #90caf9; color: black; }
QTreeView::item:hover { background-color: #bbdefb; }
QHeaderView::section {
    background-color: #dce6f5;
    border: 1px solid #b0c4de;
    border-left: none;
    padding: 5px 8px;
    font-weight: bold;
    font-size: 12px;
    color: #3a5a8a;
}

/* ── Text areas ──────────────────────────────────────────────────── */
QPlainTextEdit, QTextBrowser {
    background: #fafcff;
    color: #333;
    border: 1px solid #b0c4de;
    border-radius: 4px;
    font-size: 13px;
    selection-background-color: #90caf9;
}
QPlainTextEdit:focus, QTextBrowser:focus {
    border: 1px solid #1565c0;
}

/* ── Buttons ─────────────────────────────────────────────────────── */
QPushButton {
    padding: 6px 16px;
    border: 1px solid #90a4c4;
    border-radius: 4px;
    background: #dce6f5;
    color: #333;
    font-size: 13px;
    min-height: 20px;
}
QPushButton:hover { background: #c8d8f0; border-color: #6a8ab8; color: #333; }
QPushButton:pressed { background: #90caf9; color: #333; }
QPushButton:disabled { color: #aaa; background: #e8eef7; border-color: #c5cfe0; }
QPushButton[class="primary"] {
    background: #1565c0; color: white;
    border: 1px solid #0d47a1; font-weight: bold;
}
QPushButton[class="primary"]:hover { background: #1976d2; color: white; }
QPushButton[class="danger"] {
    background: #e53935; color: white; border: 1px solid #c62828;
}

/* Capture source Start/Stop buttons (outline variants) */
QPushButton[class="start_action"] {
    background-color: transparent;
    color: #1565c0;
    border: 1px solid #1565c0;
    font-weight: bold;
}
QPushButton[class="start_action"]:hover {
    background-color: rgba(21, 101, 192, 0.12);
}
QPushButton[class="start_action"]:pressed {
    background-color: rgba(21, 101, 192, 0.22);
}
QPushButton[class="start_action"]:disabled {
    background-color: #e8eef7;
    color: #aaa;
    border-color: #c5cfe0;
    font-weight: normal;
}

QPushButton[class="stop_action"] {
    background-color: transparent;
    color: #e53935;
    border: 1px solid #e53935;
    font-weight: bold;
}
QPushButton[class="stop_action"]:hover {
    background-color: rgba(229, 57, 53, 0.12);
}
QPushButton[class="stop_action"]:pressed {
    background-color: rgba(229, 57, 53, 0.22);
}
QPushButton[class="stop_action"]:disabled {
    background-color: #e8eef7;
    color: #aaa;
    border-color: #c5cfe0;
    font-weight: normal;
}

/* ── Inputs ──────────────────────────────────────────────────────── */
QLineEdit, QComboBox, QSpinBox {
    padding: 5px 8px;
    border: 1px solid #b0c4de;
    border-radius: 4px;
    background: #fafcff;
    color: #333;
    font-size: 13px;
    min-height: 18px;
}
QLineEdit:focus, QSpinBox:focus { border: 1px solid #1565c0; }
QComboBox::drop-down { border: none; width: 24px; }
QComboBox QAbstractItemView {
    background: #fafcff;
    color: #333;
    border: 1px solid #b0c4de; border-radius: 4px;
    selection-background-color: #90caf9; selection-color: black;
}
QCheckBox { spacing: 6px; font-size: 13px; color: #333; }
QCheckBox::indicator {
    width: 16px; height: 16px; border-radius: 3px;
    border: 1px solid #90a4c4;
}
QCheckBox::indicator:checked { background: #1565c0; border-color: #0d47a1; }

/* ── Status bar ──────────────────────────────────────────────────── */
QStatusBar {
    background: #dce6f5;
    border-top: 1px solid #b0c4de;
    font-size: 12px; color: #555;
}

/* ── Progress bar ────────────────────────────────────────────────── */
QProgressBar {
    background: #fafcff;
    color: #333;
    border: 1px solid #b0c4de; border-radius: 4px;
    text-align: center; font-size: 12px; min-height: 18px;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 #0d47a1, stop:1 #42a5f5);
    border-radius: 3px;
}

/* ── Menus & Toolbars ────────────────────────────────────────────── */
QMenuBar { background: #dce6f5; color: #333; border-bottom: 1px solid #b0c4de; font-size: 13px; }
QMenuBar::item:selected { background: #c8d8f0; border-radius: 4px; }
QMenu {
    background: #f0f4fa; color: #333; border: 1px solid #b0c4de;
    border-radius: 4px; padding: 4px;
}
QMenu::item { padding: 6px 24px; border-radius: 3px; }
QMenu::item:selected { background-color: #bbdefb; }
QToolBar {
    background: #dce6f5; border-bottom: 1px solid #b0c4de;
    spacing: 4px; padding: 2px;
}

/* ── Dialogs ─────────────────────────────────────────────────────── */
QDialog {
    background-color: #e8eef7;
    color: #333;
}
QMessageBox {
    background-color: #e8eef7;
    color: #333;
}
QMessageBox QLabel {
    color: #333;
}
"""
)


# ══════════════════════════════════════════════════════════════════════
# Theme registry and application
# ══════════════════════════════════════════════════════════════════════

THEMES: dict[str, str] = {
    "Light": LIGHT_QSS,
    "Dark": DARK_QSS,
    "Blue Accent": BLUE_ACCENT_QSS,
}


def _build_dark_palette() -> QPalette:
    """Build a QPalette for dark mode that covers native dialogs and
    widgets that don't respect QSS alone."""
    p = QPalette()
    p.setColor(QPalette.Window, QColor("#1e1e1e"))
    p.setColor(QPalette.WindowText, QColor("#ddd"))
    p.setColor(QPalette.Base, QColor("#1e1e1e"))
    p.setColor(QPalette.AlternateBase, QColor("#262626"))
    p.setColor(QPalette.ToolTipBase, QColor("#f5f5f5"))
    p.setColor(QPalette.ToolTipText, QColor("#212121"))
    p.setColor(QPalette.Text, QColor("#ddd"))
    p.setColor(QPalette.Button, QColor("#333"))
    p.setColor(QPalette.ButtonText, QColor("#ddd"))
    p.setColor(QPalette.BrightText, QColor("#fff"))
    p.setColor(QPalette.Link, QColor("#64b5f6"))
    p.setColor(QPalette.Highlight, QColor("#1565c0"))
    p.setColor(QPalette.HighlightedText, QColor("#fff"))
    p.setColor(QPalette.PlaceholderText, QColor("#888"))
    # Disabled colours
    p.setColor(QPalette.Disabled, QPalette.WindowText, QColor("#666"))
    p.setColor(QPalette.Disabled, QPalette.Text, QColor("#666"))
    p.setColor(QPalette.Disabled, QPalette.ButtonText, QColor("#666"))
    return p

def _build_light_palette() -> QPalette:
    """Explicit light palette to override any stuck dark palette caching."""
    p = QPalette()
    p.setColor(QPalette.Window, QColor("#fafafa"))
    p.setColor(QPalette.WindowText, QColor("#333333"))
    p.setColor(QPalette.Base, QColor("#ffffff"))
    p.setColor(QPalette.AlternateBase, QColor("#f5f5f5"))
    p.setColor(QPalette.ToolTipBase, QColor("#333333"))
    p.setColor(QPalette.ToolTipText, QColor("#eeeeee"))
    p.setColor(QPalette.Text, QColor("#333333"))
    p.setColor(QPalette.Button, QColor("#f5f5f5"))
    p.setColor(QPalette.ButtonText, QColor("#333333"))
    p.setColor(QPalette.BrightText, QColor("#ffffff"))
    p.setColor(QPalette.Link, QColor("#1976d2"))
    p.setColor(QPalette.Highlight, QColor("#1976d2"))
    p.setColor(QPalette.HighlightedText, QColor("#ffffff"))
    p.setColor(QPalette.PlaceholderText, QColor("#888888"))
    # Disabled colours
    p.setColor(QPalette.Disabled, QPalette.WindowText, QColor("#aaaaaa"))
    p.setColor(QPalette.Disabled, QPalette.Text, QColor("#aaaaaa"))
    p.setColor(QPalette.Disabled, QPalette.ButtonText, QColor("#aaaaaa"))
    return p

def _build_blue_palette() -> QPalette:
    """Explicit blue accent palette to override any stuck dark palette caching."""
    p = QPalette()
    p.setColor(QPalette.Window, QColor("#e8eef7"))
    p.setColor(QPalette.WindowText, QColor("#333333"))
    p.setColor(QPalette.Base, QColor("#fafcff"))
    p.setColor(QPalette.AlternateBase, QColor("#dce6f5"))
    p.setColor(QPalette.ToolTipBase, QColor("#333333"))
    p.setColor(QPalette.ToolTipText, QColor("#eeeeee"))
    p.setColor(QPalette.Text, QColor("#333333"))
    p.setColor(QPalette.Button, QColor("#dce6f5"))
    p.setColor(QPalette.ButtonText, QColor("#333333"))
    p.setColor(QPalette.BrightText, QColor("#ffffff"))
    p.setColor(QPalette.Link, QColor("#1565c0"))
    p.setColor(QPalette.Highlight, QColor("#1565c0"))
    p.setColor(QPalette.HighlightedText, QColor("#ffffff"))
    p.setColor(QPalette.PlaceholderText, QColor("#888888"))
    # Disabled colours
    p.setColor(QPalette.Disabled, QPalette.WindowText, QColor("#aaaaaa"))
    p.setColor(QPalette.Disabled, QPalette.Text, QColor("#aaaaaa"))
    p.setColor(QPalette.Disabled, QPalette.ButtonText, QColor("#aaaaaa"))
    return p

def apply_theme(app: QApplication, name: str) -> None:
    """Apply a named theme to the application.

    Sets the QSS stylesheet and explicitly overwrites the QPalette
    for every theme so that native dialogs don't cache stale colors.
    """
    qss = THEMES.get(name, LIGHT_QSS)
    app.setStyleSheet(qss)

    if name == "Dark":
        app.setPalette(_build_dark_palette())
    elif name == "Blue Accent":
        app.setPalette(_build_blue_palette())
    else:
        app.setPalette(_build_light_palette())


# ══════════════════════════════════════════════════════════════════════
# Theme color dictionaries (for theme-aware HTML/widgets)
# ══════════════════════════════════════════════════════════════════════

_THEME_COLORS: dict[str, dict[str, str]] = {
    "Light": {
        "bg": "#fafafa", "fg": "#333333", "accent": "#1976d2",
        "border": "#d0d0d0", "card_bg": "#ffffff", "muted": "#888888",
        "card_border": "#e0e0e0", "success": "#2e7d32", "error": "#c62828",
        "warning": "#ef6c00", "hover": "#e3f2fd", "surface": "#f5f5f5",
    },
    "Dark": {
        "bg": "#1e1e1e", "fg": "#dddddd", "accent": "#64b5f6",
        "border": "#444444", "card_bg": "#2d2d2d", "muted": "#999999",
        "card_border": "#3a3a3a", "success": "#66bb6a", "error": "#ef5350",
        "warning": "#ffa726", "hover": "#2a3a4a", "surface": "#262626",
    },
    "Blue Accent": {
        "bg": "#e8eef7", "fg": "#333333", "accent": "#1565c0",
        "border": "#b0c4de", "card_bg": "#f0f4fa", "muted": "#888888",
        "card_border": "#c5cfe0", "success": "#2e7d32", "error": "#c62828",
        "warning": "#ef6c00", "hover": "#bbdefb", "surface": "#dce6f5",
    },
}


def get_theme_colors(name: str = "Light") -> dict[str, str]:
    """Return a color dict for the given theme name.

    Keys: bg, fg, accent, border, card_bg, muted, card_border,
    success, error, warning, hover, surface.
    """
    return _THEME_COLORS.get(name, _THEME_COLORS["Light"])


def current_theme_name() -> str:
    """Return the currently-active theme name by inspecting the app stylesheet."""
    app = QApplication.instance()
    if not app:
        return "Light"
    ss = app.styleSheet()
    if "#1e1e1e" in ss:
        return "Dark"
    if "#e8eef7" in ss:
        return "Blue Accent"
    return "Light"


# ══════════════════════════════════════════════════════════════════════
# StatusBadge – reusable rounded-pill status indicator
# ══════════════════════════════════════════════════════════════════════

class StatusBadge(QLabel):
    """Small rounded-pill label for status indicators.

    Usage::

        badge = StatusBadge()
        badge.set_status("running")          # green pill
        badge.set_status("stopped")          # red pill
        badge.set_status("paused")           # orange pill
        badge.set_status("connected")        # green pill
        badge.set_status("disconnected")     # red pill
        badge.set_status("idle", "#757575")  # custom color
    """

    _PRESETS: dict[str, tuple[str, str]] = {
        "running":      ("\u25cf Running",       STATUS_GREEN),
        "connected":    ("\u25cf Connected",      STATUS_GREEN),
        "active":       ("\u25cf Active",         STATUS_GREEN),
        "started":      ("\u25cf Started",        STATUS_GREEN),
        "paused":       ("\u23f8 Paused",         STATUS_ORANGE),
        "starting":     ("\u25cb Starting\u2026", STATUS_ORANGE),
        "stopped":      ("\u25cf Stopped",        STATUS_RED),
        "disconnected": ("\u25cf Disconnected",   STATUS_RED),
        "error":        ("\u25cf Error",          STATUS_RED),
        "idle":         ("\u25cb Idle",           STATUS_GRAY),
        "completed":    ("\u2713 Completed",      STATUS_GREEN),
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self._apply_style(STATUS_GRAY)
        self.setText("\u25cb Idle")

    def set_status(self, status: str, color: str | None = None) -> None:
        """Set the badge to a preset or custom status."""
        status_lower = status.lower()
        if status_lower in self._PRESETS:
            label, preset_color = self._PRESETS[status_lower]
            self.setText(label)
            self._apply_style(color or preset_color)
        else:
            self.setText(status)
            self._apply_style(color or STATUS_GRAY)

    def _apply_style(self, bg_color: str) -> None:
        self.setStyleSheet(
            f"background-color: {bg_color};"
            f"color: white;"
            f"border-radius: 10px;"
            f"padding: 3px 12px;"
            f"font-size: 11px;"
            f"font-weight: bold;"
        )


# ══════════════════════════════════════════════════════════════════════
# StatCard – animated stat display for dashboards
# ══════════════════════════════════════════════════════════════════════

class StatCard(QFrame):
    """Stylish stat card with a large number and small label.

    Usage::

        card = StatCard("Total Prompts", accent_color="#1976d2")
        card.set_value(142)       # animates count-up
        card.set_value("1.2M")    # sets text directly
    """

    def __init__(self, label: str, accent_color: str = "#1976d2",
                 parent=None):
        super().__init__(parent)
        self._accent = accent_color
        self._display_value = 0

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(2)

        self._value_label = QLabel("0")
        value_font = QFont()
        value_font.setPointSize(22)
        value_font.setBold(True)
        self._value_label.setFont(value_font)
        self._value_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self._value_label)

        self._desc_label = QLabel(label)
        desc_font = QFont()
        desc_font.setPointSize(10)
        self._desc_label.setFont(desc_font)
        self._desc_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self._desc_label)

        self._refresh_style()

    def _refresh_style(self) -> None:
        colors = get_theme_colors(current_theme_name())
        self.setStyleSheet(
            f"StatCard {{"
            f"  background-color: {colors['card_bg']};"
            f"  border: 1px solid {colors['card_border']};"
            f"  border-left: 4px solid {self._accent};"
            f"  border-radius: 8px;"
            f"}}"
        )
        self._desc_label.setStyleSheet(f"color: {colors['muted']};")

    # -- Animated count-up via QPropertyAnimation --

    def _get_display_value(self) -> int:
        return self._display_value

    def _set_display_value(self, val: int) -> None:
        self._display_value = val
        self._value_label.setText(f"{val:,}")

    displayValue = Property(int, _get_display_value, _set_display_value)

    def set_value(self, value, animate: bool = True) -> None:
        """Set the card's displayed value.

        If *value* is an ``int`` and *animate* is True, a smooth
        count-up animation plays.  Otherwise the text is set directly.
        """
        self._refresh_style()
        if isinstance(value, int) and animate:
            anim = QPropertyAnimation(self, b"displayValue", self)
            anim.setDuration(600)
            anim.setStartValue(self._display_value)
            anim.setEndValue(value)
            anim.setEasingCurve(QEasingCurve.OutCubic)
            anim.start(QPropertyAnimation.DeleteWhenStopped)
        elif isinstance(value, int):
            self._display_value = value
            self._value_label.setText(f"{value:,}")
        else:
            self._value_label.setText(str(value))
