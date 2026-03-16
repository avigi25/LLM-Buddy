"""
Prompt Explorer panel — Prompt-centric conversational forking visualization.

Each individual prompt is a node in the tree graph. Selecting a node shows
its full text and LLM response in the sidebar. New prompts are automatically
added to the checked-out branch; forking creates diverging paths from a
shared ancestor prompt.

Tree layout:
  - Time flows top-to-bottom (workflow direction).
  - Each branch occupies its own column.
  - Fork edges (dashed) connect the fork-point prompt to the first unique
    prompt of each child branch.
  - Sequential edges (solid) connect consecutive prompts within a branch.
"""

from datetime import datetime
from typing import List, Optional

from PySide6.QtCore import Qt, Signal, Slot, QRectF, QPointF, QTimer
from PySide6.QtGui import (
    QBrush, QColor, QPen, QFont, QPainter, QPainterPath, QAction, QPalette,
)
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QLabel,
    QPushButton, QGraphicsView, QGraphicsScene, QGraphicsItem,
    QGraphicsPathItem, QMenu, QComboBox, QMessageBox,
    QFormLayout, QTextEdit, QLineEdit, QInputDialog, QApplication,
    QDialog, QDialogButtonBox, QCheckBox, QGroupBox, QFrame,
)

from llm_buddy.core.forking import (
    ConversationTree, Branch, ForkPoint,
    auto_detect_trees, build_tree_with_forks, BRANCH_STATUSES, FORK_TRIGGERS,
)
from llm_buddy.qt.theme import get_theme_colors, current_theme_name



class ForkDialog(QDialog):
    """Multi-field dialog for creating a fork with full metadata."""

    def __init__(self, parent_branch_name: str, prompt_count: int,
                 default_index: int = -1, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Fork Branch")
        self.setMinimumWidth(420)
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel(f"<b>Forking from:</b> {parent_branch_name}"))

        form = QFormLayout()

        self.edit_name = QLineEdit()
        self.edit_name.setPlaceholderText("e.g. 'Try alternative API approach'")
        form.addRow("Branch name:", self.edit_name)

        self.combo_trigger = QComboBox()
        for val, label in FORK_TRIGGERS:
            self.combo_trigger.addItem(label, val)
        for i, (val, _) in enumerate(FORK_TRIGGERS):
            if val == "exploratory":
                self.combo_trigger.setCurrentIndex(i)
                break
        form.addRow("Trigger:", self.combo_trigger)

        self.edit_reason = QLineEdit()
        self.edit_reason.setPlaceholderText("Why are you branching here?")
        form.addRow("Reason:", self.edit_reason)

        self.edit_context = QTextEdit()
        self.edit_context.setPlaceholderText(
            "Key context to carry forward (artifacts, decisions, constraints)…")
        self.edit_context.setMaximumHeight(80)
        form.addRow("Context:", self.edit_context)

        if prompt_count > 0:
            idx = default_index if 0 <= default_index < prompt_count else prompt_count - 1
            self._fork_index = idx
            form.addRow("Fork after prompt:", QLabel(f"<b>#{idx + 1}</b> of {prompt_count}"))
        else:
            self._fork_index = 0

        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.edit_name.setFocus()

    @property
    def fork_index(self) -> int:
        return self._fork_index

    def get_values(self) -> dict:
        return {
            "name": self.edit_name.text().strip(),
            "trigger": self.combo_trigger.currentData(),
            "reason": self.edit_reason.text().strip(),
            "context_summary": self.edit_context.toPlainText().strip(),
            "fork_index": self._fork_index,
        }



class MergeDialog(QDialog):
    """Dialog to merge one branch into a chosen target."""

    def __init__(self, source_branch: Branch, tree: ConversationTree, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Merge Branch")
        self.setMinimumWidth(420)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(
            f"<b>Merge source:</b> {source_branch.name}  "
            f"({len(source_branch.prompt_ids)} prompts)"))

        form = QFormLayout()
        self.combo_target = QComboBox()
        for b in tree.get_visible_branches():
            if b.id != source_branch.id:
                self.combo_target.addItem(
                    f"{b.name}  ({len(b.prompt_ids)} prompts)", b.id)
        form.addRow("Merge into:", self.combo_target)

        self.chk_copy_prompts = QCheckBox("Copy unique prompts into target")
        self.chk_copy_prompts.setChecked(True)
        form.addRow("", self.chk_copy_prompts)

        self.edit_insights = QTextEdit()
        self.edit_insights.setPlaceholderText(
            "What did you learn from this branch? Key takeaways…")
        self.edit_insights.setMaximumHeight(100)
        form.addRow("Merge insights:", self.edit_insights)

        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_values(self) -> dict:
        return {
            "target_branch_id": self.combo_target.currentData(),
            "include_prompts": self.chk_copy_prompts.isChecked(),
            "insights": self.edit_insights.toPlainText().strip(),
        }


# One color per branch (cycles if > 10 branches)
BRANCH_PALETTE = [
    QColor("#1565C0"),  # Deep Blue
    QColor("#2E7D32"),  # Deep Green
    QColor("#B71C1C"),  # Deep Red
    QColor("#6A1B9A"),  # Deep Purple
    QColor("#E65100"),  # Deep Orange
    QColor("#00695C"),  # Deep Teal
    QColor("#AD1457"),  # Deep Pink
    QColor("#4E342E"),  # Deep Brown
    QColor("#37474F"),  # Blue Grey
    QColor("#F9A825"),  # Amber (dark)
]



class PromptNodeItem(QGraphicsItem):
    """A prompt displayed as a rounded card in the tree graph."""

    NODE_W = 230
    NODE_H = 95

    def __init__(self, prompt, branch: Branch, color: QColor,
                 is_fork_point: bool, panel):
        super().__init__()
        self.prompt = prompt
        self.branch = branch
        self.color = color
        self.is_fork_point = is_fork_point
        self.panel = panel
        self._edges: list = []
        self.is_hovered = False

        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setAcceptHoverEvents(True)

    def add_edge(self, edge) -> None:
        self._edges.append(edge)

    def boundingRect(self) -> QRectF:
        return QRectF(0, 0, self.NODE_W, self.NODE_H)

    def paint(self, painter: QPainter, option, widget=None) -> None:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(0, 0, self.NODE_W, self.NODE_H)

        if self.isSelected():
            bg = self.color.lighter(190)
            border_pen = QPen(self.color, 3)
        elif self.is_hovered:
            bg = self.color.lighter(200)
            border_pen = QPen(self.color, 2)
        else:
            bg = QApplication.palette().color(QPalette.Base)
            border_pen = QPen(self.color.darker(110), 1.5)

        painter.setPen(border_pen)
        painter.setBrush(QBrush(bg))
        painter.drawRoundedRect(rect, 7, 7)

        if self.is_fork_point:
            painter.setPen(QPen(self.color, 1.5, Qt.PenStyle.DashLine))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(rect.adjusted(-5, -5, 5, 5), 10, 10)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(self.color))
        painter.drawRoundedRect(QRectF(0, 0, 6, self.NODE_H), 3, 3)
        painter.drawRect(QRectF(3, 0, 3, self.NODE_H))   # square off right edge

        ts = self.prompt.timestamp.strftime("%m/%d %H:%M") if self.prompt.timestamp else ""
        llm = (self.prompt.llm_used or "")[:16]
        painter.setPen(QApplication.palette().color(QPalette.PlaceholderText))
        painter.setFont(QFont("Segoe UI", 7))
        painter.drawText(QRectF(13, 5, self.NODE_W - 17, 14),
                         Qt.AlignmentFlag.AlignLeft,
                         f"{ts}  ·  {llm}")

        text = (self.prompt.prompt_text or self.prompt.description or "(no text)")
        painter.setPen(QApplication.palette().color(QPalette.Text))
        painter.setFont(QFont("Segoe UI", 8))
        painter.drawText(
            QRectF(13, 22, self.NODE_W - 17, 55),
            Qt.AlignmentFlag.AlignLeft | Qt.TextFlag.TextWordWrap,
            text[:200],
        )

        if self.prompt.response_text:
            painter.setPen(Qt.PenStyle.NoPen)
            dot_color = QColor(get_theme_colors(current_theme_name())["success"])
            painter.setBrush(QBrush(dot_color))
            painter.drawEllipse(
                QRectF(self.NODE_W - 14, self.NODE_H - 14, 8, 8))

    def hoverEnterEvent(self, event) -> None:
        self.is_hovered = True
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.update()

    def hoverLeaveEvent(self, event) -> None:
        self.is_hovered = False
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.update()

    def mouseReleaseEvent(self, event) -> None:
        super().mouseReleaseEvent(event)
        if event.button() == Qt.MouseButton.LeftButton:
            self.panel.select_prompt(self.prompt.id, self.branch.id)

    def contextMenuEvent(self, event) -> None:
        menu = QMenu()

        act_fork = QAction("Fork from here…", menu)
        act_fork.triggered.connect(
            lambda: self.panel._fork_from_prompt(self.branch, self.prompt.id))
        menu.addAction(act_fork)

        tree = self.panel._active_tree
        act_checkout = QAction("Checkout this branch", menu)
        act_checkout.triggered.connect(
            lambda: self.panel._checkout_branch(tree, self.branch))
        if tree and tree.checked_out_branch_id == self.branch.id:
            act_checkout.setEnabled(False)
            act_checkout.setText("✓ Already checked out")
        menu.addAction(act_checkout)

        menu.addSeparator()

        act_copy = QAction("Copy prompt text", menu)
        act_copy.triggered.connect(
            lambda: QApplication.clipboard().setText(self.prompt.prompt_text or ""))
        menu.addAction(act_copy)

        act_copy_r = QAction("Copy response text", menu)
        act_copy_r.setEnabled(bool(self.prompt.response_text))
        act_copy_r.triggered.connect(
            lambda: QApplication.clipboard().setText(self.prompt.response_text or ""))
        menu.addAction(act_copy_r)

        menu.exec(event.screenPos())



class EdgeItem(QGraphicsPathItem):
    """Smooth cubic Bezier connecting two PromptNodeItems top-to-bottom."""

    def __init__(self, src: PromptNodeItem, dst: PromptNodeItem,
                 color: QColor, dashed: bool = False):
        super().__init__()
        self.src = src
        self.dst = dst
        self.setZValue(-1)
        style = Qt.PenStyle.DashLine if dashed else Qt.PenStyle.SolidLine
        width = 1.8 if dashed else 1.5
        self.setPen(QPen(color, width, style,
                         Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        self._update_path()

    def _update_path(self) -> None:
        w = self.src.NODE_W
        h = self.src.NODE_H
        start = self.src.scenePos() + QPointF(w / 2, h)
        end   = self.dst.scenePos() + QPointF(self.dst.NODE_W / 2, 0)

        path = QPainterPath(start)
        dy = end.y() - start.y()
        dx = abs(end.x() - start.x())
        # Vertical pull proportional to both dy and horizontal distance
        pull = max(abs(dy) * 0.45, dx * 0.3, 30)
        cp1 = QPointF(start.x(), start.y() + pull)
        cp2 = QPointF(end.x(),   end.y()   - pull)
        path.cubicTo(cp1, cp2, end)
        self.setPath(path)



class BranchLabelItem(QGraphicsItem):
    W, H = 180, 26

    def __init__(self, branch: Branch, color: QColor):
        super().__init__()
        self.branch = branch
        self.color = color

    def boundingRect(self) -> QRectF:
        return QRectF(0, 0, self.W, self.H)

    def paint(self, painter: QPainter, option, widget=None) -> None:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(self.color.lighter(175)))
        painter.drawRoundedRect(self.boundingRect(), 5, 5)
        painter.setPen(self.color.darker(140))
        font = QFont("Segoe UI", 8, QFont.Weight.Bold)
        painter.setFont(font)
        name = self.branch.name
        if len(name) > 22:
            name = name[:20] + "…"
        painter.drawText(self.boundingRect(), Qt.AlignmentFlag.AlignCenter, name)



class TreeGraphView(QGraphicsView):
    """Zoomable, pannable canvas that draws individual prompts as nodes."""

    # Layout constants
    NODE_W  = PromptNodeItem.NODE_W
    NODE_H  = PromptNodeItem.NODE_H
    H_GAP   = 60    # horizontal gap between branch columns
    V_GAP   = 28    # vertical gap between sequential prompts
    TOP_PAD = 48    # vertical padding above first row (room for branch labels)

    COL_STEP = NODE_W + H_GAP
    ROW_STEP = NODE_H + V_GAP

    def __init__(self, panel):
        super().__init__()
        self.panel = panel
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.MinimalViewportUpdate)
        self.setBackgroundBrush(
            QBrush(QApplication.palette().color(QPalette.Window)))
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self._is_panning = False
        self._pan_start = QPointF()
        self._prompt_items: dict = {}   # prompt_id -> PromptNodeItem

    @Slot(str)
    def update_theme(self, _name: str = "") -> None:
        """Re-apply the scene background and repaint all nodes for the new theme."""
        self.setBackgroundBrush(
            QBrush(QApplication.palette().color(QPalette.Window)))
        self._scene.update()


    def draw_prompt_tree(self, tree: ConversationTree, db,
                         show_hidden: bool = False,
                         search_term: str = "") -> None:
        """Rebuild the visual graph for *tree*."""
        self._scene.clear()
        self._prompt_items.clear()

        if not tree or not db:
            return

        visible = tree.get_visible_branches(show_hidden=show_hidden)
        if not visible:
            return

        color_map: dict = {}
        for i, b in enumerate(tree.branches):
            color_map[b.id] = BRANCH_PALETTE[i % len(BRANCH_PALETTE)]

        col_map, start_row_map = self._compute_layout(tree, visible)

        # Build Y positions based on tree structure, not timestamps.
        # Each branch's unique prompts start at the row after the fork point.
        # This ensures forked prompts appear next to where they diverged.
        pid_to_y: dict = {}
        # First: assign rows to root branch prompts (sequential from row 0)
        root_branch = tree.get_root_branch()
        if root_branch and root_branch.id in {b.id for b in visible}:
            for i, pid in enumerate(root_branch.prompt_ids):
                pid_to_y[pid] = i * self.ROW_STEP + self.TOP_PAD

        # Then: assign rows to child branches starting from their fork point
        def _assign_branch_rows(branch):
            if branch.parent_branch_id is None:
                return  # root already assigned
            fp = tree.get_fork_point(branch.fork_point_id) if branch.fork_point_id else None
            uids = self.unique_prompt_ids(tree, branch)
            # Start row: one row after the fork point in the parent
            start_row = start_row_map.get(branch.id, 0)
            for i, pid in enumerate(uids):
                pid_to_y[pid] = (start_row + i) * self.ROW_STEP + self.TOP_PAD
            # Recurse into children of this branch
            for child in tree.get_child_branches(branch.id):
                if child.id in {b.id for b in visible}:
                    _assign_branch_rows(child)

        if root_branch:
            for child in tree.get_child_branches(root_branch.id):
                if child.id in {b.id for b in visible}:
                    _assign_branch_rows(child)

        fork_prompt_ids = {fp.prompt_id for fp in tree.fork_points if fp.prompt_id}

        search_lower = search_term.strip().lower()

        for branch in visible:
            col      = col_map.get(branch.id, 0)
            start_r  = start_row_map.get(branch.id, 0)
            uids     = self.unique_prompt_ids(tree, branch)
            color    = color_map.get(branch.id, BRANCH_PALETTE[0])
            x        = col * self.COL_STEP

            if not uids:
                continue

            # branch column label — anchored to the first prompt's temporal Y
            label = BranchLabelItem(branch, color)
            first_y = pid_to_y.get(uids[0], start_r * self.ROW_STEP + self.TOP_PAD)
            label.setPos(QPointF(
                x + (self.NODE_W - label.W) / 2,
                first_y - label.H - 6,
            ))
            self._scene.addItem(label)

            prev_item: Optional[PromptNodeItem] = None
            for i, pid in enumerate(uids):
                p = db.get_prompt(pid)
                if p is None:
                    continue

                y = pid_to_y.get(pid, (start_r + i) * self.ROW_STEP + self.TOP_PAD)
                node = PromptNodeItem(p, branch, color, pid in fork_prompt_ids, self.panel)
                node.setPos(QPointF(x, y))

                if search_lower and \
                        search_lower not in (p.prompt_text or "").lower() and \
                        search_lower not in (p.description or "").lower():
                    node.setOpacity(0.3)

                self._scene.addItem(node)
                self._prompt_items[pid] = node

                if prev_item is not None:
                    edge = EdgeItem(prev_item, node, color, dashed=False)
                    self._scene.addItem(edge)

                prev_item = node

        for branch in visible:
            if branch.parent_branch_id is None:
                continue
            fp = tree.get_fork_point(branch.fork_point_id) if branch.fork_point_id else None
            if fp is None:
                continue

            parent = tree.get_branch(branch.parent_branch_id)
            if parent is None:
                continue

            # The prompt in the parent branch AT the fork index
            if 0 <= fp.fork_index < len(parent.prompt_ids):
                parent_pid  = parent.prompt_ids[fp.fork_index]
                parent_node = self._prompt_items.get(parent_pid)

                uids = self.unique_prompt_ids(tree, branch)
                if uids:
                    child_node = self._prompt_items.get(uids[0])
                    if parent_node and child_node:
                        color = color_map.get(branch.id, QColor("#888888"))
                        edge = EdgeItem(parent_node, child_node, color, dashed=True)
                        self._scene.addItem(edge)

        rect = self._scene.itemsBoundingRect()
        self._scene.setSceneRect(rect.adjusted(-80, -80, 80, 80))

    def select_node(self, prompt_id: str, center: bool = True) -> None:
        for item in self._scene.selectedItems():
            item.setSelected(False)
        node = self._prompt_items.get(prompt_id)
        if node:
            node.setSelected(True)
            if center:
                self.centerOn(node)


    @staticmethod
    def unique_prompt_ids(tree: ConversationTree, branch: Branch) -> List[str]:
        """Return prompt IDs that are unique to *branch* (not inherited from parent)."""
        if branch.parent_branch_id is None:
            return list(branch.prompt_ids)
        fp = tree.get_fork_point(branch.fork_point_id) if branch.fork_point_id else None
        if fp is None:
            return list(branch.prompt_ids)
        return list(branch.prompt_ids[fp.fork_index + 1:])

    def _compute_layout(self, tree: ConversationTree,
                        visible: List[Branch]) -> tuple:
        """
        Compute column and start_row for each branch (git-style layout).

        Every branch gets its own column so that prompts never overlap.
        Root is always column 0; child branches get columns 1, 2, …
        in DFS order.

        Start row: root starts at 0; a child branch's unique prompts begin
        at (parent_start_row + fork_index + 1).
        """
        visible_ids = {b.id for b in visible}
        col_map: dict  = {}
        row_map: dict  = {}
        col_ctr = [0]

        def _start_row(branch: Branch) -> int:
            if branch.parent_branch_id is None:
                return 0
            parent = tree.get_branch(branch.parent_branch_id)
            if parent is None:
                return 0
            fp = tree.get_fork_point(branch.fork_point_id) if branch.fork_point_id else None
            idx = fp.fork_index if fp else max(0, len(parent.prompt_ids) - 1)
            return row_map.get(branch.parent_branch_id, 0) + idx + 1

        def dfs(bid: str) -> None:
            if bid not in visible_ids:
                return
            branch = tree.get_branch(bid)
            if branch is None:
                return

            row_map[bid] = _start_row(branch)
            # Each branch gets its own column (git-style, no overlap)
            col_map[bid] = float(col_ctr[0])
            col_ctr[0] += 1

            for child in tree.get_child_branches(bid):
                if child.id in visible_ids:
                    dfs(child.id)

        root = tree.get_root_branch()
        if root and root.id in visible_ids:
            dfs(root.id)

        return col_map, row_map


    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_F:
            self.panel._fit_to_view()
        else:
            super().keyPressEvent(event)

    def mousePressEvent(self, event) -> None:
        self.setFocus()
        if event.button() == Qt.MouseButton.MiddleButton:
            self._is_panning = True
            self._pan_start = event.pos()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.MiddleButton:
            self._is_panning = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._is_panning:
            delta = event.pos() - self._pan_start
            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - delta.y())
            self._pan_start = event.pos()
            event.accept()
            return
        super().mouseMoveEvent(event)

    def wheelEvent(self, event) -> None:
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        current = self.transform().m11()
        if (factor > 1 and current < 3.5) or (factor < 1 and current > 0.15):
            self.scale(factor, factor)



class ForkingPanel(QWidget):

    branch_forked = Signal(str, str, str, str)   # tree, parent, child, trigger
    branch_merged = Signal(str, str, str)         # tree, source, insights

    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self._mw = main_window
        self._trees: List[ConversationTree] = []
        self._active_tree: Optional[ConversationTree] = None
        self._active_prompt_id: Optional[str] = None
        self._active_branch_id: Optional[str] = None
        self._show_hidden = False
        self._search_term = ""

        # Periodic auto-sync timer
        self._sync_timer = QTimer(self)
        self._sync_timer.setInterval(30_000)
        self._sync_timer.timeout.connect(self.refresh)

        self._build_ui()
        self.refresh()
        self._sync_timer.start()
        QTimer.singleShot(0, self._init_splitter_sizes)

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        self._graph_view = TreeGraphView(self)

        tb1 = QHBoxLayout()
        tb1.setContentsMargins(8, 8, 8, 4)

        tb1.addWidget(QLabel("<b>Conversation:</b>"))
        self._tree_selector = QComboBox()
        self._tree_selector.setMinimumWidth(300)
        self._tree_selector.currentIndexChanged.connect(self._on_tree_changed)
        tb1.addWidget(self._tree_selector)

        self._lbl_checkout = QLabel("")
        self._lbl_checkout.setStyleSheet(
            "color: #2E7D32; font-weight: bold; padding: 0 8px;")
        tb1.addWidget(self._lbl_checkout)

        tb1.addStretch()

        btn_sync = QPushButton("↻ Sync")
        btn_sync.setToolTip("Pull new prompts from the database now")
        btn_sync.clicked.connect(self.refresh)
        tb1.addWidget(btn_sync)

        btn_fit = QPushButton("⛶ Fit  (F)")
        btn_fit.clicked.connect(self._fit_to_view)
        tb1.addWidget(btn_fit)

        root.addLayout(tb1)

        tb2 = QHBoxLayout()
        tb2.setContentsMargins(8, 0, 8, 8)

        tb2.addWidget(QLabel("🔍"))
        self._search_box = QLineEdit()
        self._search_box.setPlaceholderText("Filter prompts by text…")
        self._search_box.setClearButtonEnabled(True)
        self._search_box.setMaximumWidth(280)
        self._search_box.textChanged.connect(self._on_search_changed)
        tb2.addWidget(self._search_box)

        self._chk_hidden = QCheckBox("Show archived branches")
        self._chk_hidden.setToolTip("Include soft-deleted branches")
        self._chk_hidden.toggled.connect(self._on_show_hidden_toggled)
        tb2.addWidget(self._chk_hidden)

        tb2.addStretch()

        btn_fork = QPushButton("🌱 Fork from selection")
        btn_fork.setToolTip("Create a new branch diverging from the selected prompt")
        btn_fork.clicked.connect(self._fork_from_selection)
        tb2.addWidget(btn_fork)

        btn_merge = QPushButton("🔀 Merge branch")
        btn_merge.setToolTip("Merge the selected prompt's branch into another")
        btn_merge.clicked.connect(self._merge_from_selection)
        tb2.addWidget(btn_merge)

        root.addLayout(tb2)

        self._splitter = QSplitter(Qt.Orientation.Horizontal)
        self._splitter.setChildrenCollapsible(False)
        self._splitter.setHandleWidth(6)
        root.addWidget(self._splitter, stretch=1)

        self._splitter.addWidget(self._graph_view)

        sidebar = QWidget()
        sidebar.setMinimumWidth(360)
        sl = QVBoxLayout(sidebar)
        sl.setContentsMargins(12, 12, 12, 12)
        sl.setSpacing(8)

        # Context header
        self._lbl_context = QLabel("<i>Select a prompt node to read its content</i>")
        self._lbl_context.setWordWrap(True)
        sl.addWidget(self._lbl_context)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)
        sl.addWidget(sep)

        # Prompt text
        sl.addWidget(QLabel("<b>Prompt:</b>"))
        self._txt_prompt = QTextEdit()
        self._txt_prompt.setReadOnly(True)
        self._txt_prompt.setPlaceholderText("Prompt text will appear here…")
        self._txt_prompt.setMinimumHeight(110)
        sl.addWidget(self._txt_prompt, stretch=3)

        # Response text
        sl.addWidget(QLabel("<b>LLM Response:</b>"))
        self._txt_response = QTextEdit()
        self._txt_response.setReadOnly(True)
        self._txt_response.setPlaceholderText(
            "LLM response will appear here…\n\n"
            "(Responses are captured by the Proxy or MCP recorder. "
            "The Chrome extension captures prompts only.)")
        self._txt_response.setMinimumHeight(110)
        sl.addWidget(self._txt_response, stretch=3)

        # Metadata group
        self._meta_group = QGroupBox("Metadata")
        mf = QFormLayout(self._meta_group)
        mf.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        self._lbl_ts      = QLabel("—")
        self._lbl_llm     = QLabel("—")
        self._lbl_source  = QLabel("—")
        self._lbl_branch  = QLabel("—")
        mf.addRow("Timestamp:", self._lbl_ts)
        mf.addRow("LLM:",       self._lbl_llm)
        mf.addRow("Source:",    self._lbl_source)
        mf.addRow("Branch:",    self._lbl_branch)
        sl.addWidget(self._meta_group)

        # Fork origin group (hidden unless branch is a fork)
        self._fork_group = QGroupBox("Fork Origin")
        ff = QFormLayout(self._fork_group)
        ff.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        self._lbl_fork_parent  = QLabel("—")
        self._lbl_fork_trigger = QLabel("—")
        self._lbl_fork_reason  = QLabel("—")
        self._lbl_fork_reason.setWordWrap(True)
        ff.addRow("Parent branch:", self._lbl_fork_parent)
        ff.addRow("Trigger:",       self._lbl_fork_trigger)
        ff.addRow("Reason:",        self._lbl_fork_reason)
        self._fork_group.setVisible(False)
        sl.addWidget(self._fork_group)

        # Action buttons
        acts = QHBoxLayout()

        self._btn_checkout = QPushButton("⬤ Checkout Branch")
        self._btn_checkout.setToolTip("New prompts go to this branch")
        self._btn_checkout.clicked.connect(self._checkout_from_selection)
        acts.addWidget(self._btn_checkout)

        self._btn_eadr = QPushButton("📝 eADR Note")
        self._btn_eadr.clicked.connect(self._eadr_from_selection)
        acts.addWidget(self._btn_eadr)

        self._btn_copy = QPushButton("📋 Copy Prompt")
        self._btn_copy.clicked.connect(self._copy_prompt_from_selection)
        acts.addWidget(self._btn_copy)

        sl.addLayout(acts)

        self._sidebar = sidebar
        self._sidebar.setEnabled(False)
        self._splitter.addWidget(sidebar)

        self._splitter.setStretchFactor(0, 2)
        self._splitter.setStretchFactor(1, 1)

    def _init_splitter_sizes(self) -> None:
        total = max(self.width(), 1100)
        sw = max(360, int(total * 0.33))
        self._splitter.setSizes([total - sw, sw])


    def refresh(self) -> None:
        """Sync trees from the prompt database, rebuild selector + graph."""
        # Save viewport so we can restore after redraw
        saved_transform = self._graph_view.transform()
        center = self._graph_view.mapToScene(
            self._graph_view.viewport().rect().center())
        self._graph_view.viewport().setUpdatesEnabled(False)

        active_tree_id = self._active_tree.id if self._active_tree else None

        self._trees = self._mw.prompt_database.load_trees()
        db = getattr(self._mw, "prompt_database", None)
        suggestions = auto_detect_trees(db) if db else []

        sug_by_cid = {s["conversation_id"]: s for s in suggestions
                      if s.get("conversation_id")}

        # Build existing-tree lookup by conversation ID
        existing: dict = {}
        for t in self._trees:
            cid = self._get_tree_cid(t)
            if cid:
                existing[cid] = t

        modified = False

        for sug in suggestions:
            cid = sug.get("conversation_id")
            if not cid:
                continue
            newest_ts = sug.get("last_timestamp") or datetime.now()

            # Resolve full prompt objects for fork detection
            sug_prompts = [db.get_prompt(pid) for pid in sug["prompt_ids"]]
            sug_prompts = [p for p in sug_prompts if p is not None]

            if cid not in existing:
                # Create a new tree for this conversation
                desc = sug.get("sample_description", "")
                new_tree = ConversationTree(
                    name=desc[:60] or cid,
                    description=desc,
                )
                new_tree.source_conversation_id = cid
                if not hasattr(new_tree, "tags"):
                    new_tree.tags = []
                if f"cid:{cid}" not in new_tree.tags:
                    new_tree.tags.append(f"cid:{cid}")

                # Use fork detection to build branches from prompt metadata
                if build_tree_with_forks(new_tree, sug_prompts, db):
                    pass  # tree populated with fork-aware branches
                else:
                    # Fallback: linear assignment to root branch
                    root = new_tree.get_root_branch()
                    root.prompt_ids = list(sug["prompt_ids"])
                    root.updated_at = newest_ts

                new_tree.updated_at = newest_ts
                self._trees.append(new_tree)
                existing[cid] = new_tree
                modified = True
            else:
                # Update existing tree with any new prompts (fork-aware)
                tree = existing[cid]
                if build_tree_with_forks(tree, sug_prompts, db):
                    tree.updated_at = newest_ts
                    modified = True

        # Sort trees newest-first
        def _sort_key(t: ConversationTree):
            cid = self._get_tree_cid(t)
            sug = sug_by_cid.get(cid) if cid else None
            sug_ts = sug.get("last_timestamp") if sug else None
            tree_ts = getattr(t, "updated_at", None) or getattr(t, "created_at", None)
            return sug_ts or tree_ts or datetime.min

        self._trees.sort(key=_sort_key, reverse=True)

        if modified:
            db = getattr(self._mw, "prompt_database", None)
            if db:
                for tree in self._trees:
                    db.save_tree(tree)

        # Rebuild the tree selector combo
        self._tree_selector.blockSignals(True)
        self._tree_selector.clear()

        restore_idx = 0
        search = self._search_term.strip().lower()

        for tree in self._trees:
            if search and search not in tree.name.lower():
                continue
            root_b = tree.get_root_branch()
            # Count all unique prompts across every branch
            all_pids: set = set()
            for b in tree.branches:
                all_pids.update(b.prompt_ids)
            n_prompts = len(all_pids)
            n_branches = len(tree.branches)
            label = (f"{tree.name}  "
                     f"[{n_prompts} prompts · {n_branches} branch{'es' if n_branches != 1 else ''}]")
            self._tree_selector.addItem(label, tree.id)
            if active_tree_id and tree.id == active_tree_id:
                restore_idx = self._tree_selector.count() - 1

        self._tree_selector.setCurrentIndex(
            restore_idx if self._tree_selector.count() else -1)
        self._tree_selector.blockSignals(False)

        # Restore active tree
        if not self._active_tree and self._tree_selector.count():
            first_id = self._tree_selector.itemData(0)
            self._active_tree = next(
                (t for t in self._trees if t.id == first_id), None)

        self._redraw_graph()
        self._update_checkout_label()

        self._graph_view.setTransform(saved_transform)
        self._graph_view.centerOn(center)
        self._graph_view.viewport().setUpdatesEnabled(True)


    @staticmethod
    def _get_tree_cid(tree: ConversationTree) -> Optional[str]:
        cid = getattr(tree, "source_conversation_id", None)
        if cid:
            return cid
        for tag in getattr(tree, "tags", []):
            if isinstance(tag, str) and tag.startswith("cid:"):
                return tag[4:]
        return None

    def _redraw_graph(self) -> None:
        if not self._active_tree:
            return
        db = getattr(self._mw, "prompt_database", None)
        self._graph_view.draw_prompt_tree(
            self._active_tree, db,
            show_hidden=self._show_hidden,
            search_term=self._search_term,
        )

    def _fit_to_view(self) -> None:
        if self._graph_view._scene.items():
            self._graph_view.fitInView(
                self._graph_view._scene.itemsBoundingRect(),
                Qt.AspectRatioMode.KeepAspectRatio)


    @Slot(int)
    def _on_tree_changed(self, index: int) -> None:
        if index < 0:
            return
        tree_id = self._tree_selector.itemData(index)
        tree = next((t for t in self._trees if t.id == tree_id), None)
        if not tree:
            return

        self._active_tree = tree
        self._active_prompt_id = None
        self._active_branch_id = None
        self._sidebar.setEnabled(False)
        self._lbl_context.setText("<i>Select a prompt node to read its content</i>")
        self._fork_group.setVisible(False)

        self._redraw_graph()
        self._update_checkout_label()
        QTimer.singleShot(50, self._fit_to_view)


    def select_prompt(self, prompt_id: str, branch_id: str) -> None:
        """Called by PromptNodeItem on click — populate the sidebar."""
        db = getattr(self._mw, "prompt_database", None)
        if not db or not self._active_tree:
            return

        p = db.get_prompt(prompt_id)
        if not p:
            return

        branch = self._active_tree.get_branch(branch_id)
        if not branch:
            return

        self._active_prompt_id = prompt_id
        self._active_branch_id = branch_id

        self._graph_view.select_node(prompt_id)
        self._sidebar.setEnabled(True)

        uids = TreeGraphView.unique_prompt_ids(self._active_tree, branch)
        try:
            pos = uids.index(prompt_id) + 1
        except ValueError:
            pos = "?"
        self._lbl_context.setText(
            f"<b>{branch.name}</b>  ·  prompt {pos} of {len(uids)}")

        self._txt_prompt.setPlainText(
            p.prompt_text or "(no prompt text recorded)")
        self._txt_response.setPlainText(
            p.response_text or "(no response captured for this prompt)")

        ts = p.timestamp.strftime("%Y-%m-%d  %H:%M:%S") if p.timestamp else "—"
        self._lbl_ts.setText(ts)
        self._lbl_llm.setText(p.llm_used or "—")
        self._lbl_source.setText(p.source or "—")
        self._lbl_branch.setText(branch.name)

        if branch.fork_point_id:
            fp = self._active_tree.get_fork_point(branch.fork_point_id)
            if fp:
                parent_b = self._active_tree.get_branch(fp.parent_branch_id)
                self._lbl_fork_parent.setText(parent_b.name if parent_b else "—")
                trigger_label = fp.trigger
                for val, label in FORK_TRIGGERS:
                    if val == fp.trigger:
                        trigger_label = label
                        break
                self._lbl_fork_trigger.setText(trigger_label)
                self._lbl_fork_reason.setText(fp.reason or "—")
                self._fork_group.setVisible(True)
            else:
                self._fork_group.setVisible(False)
        else:
            self._fork_group.setVisible(False)


    @Slot(str)
    def _on_search_changed(self, text: str) -> None:
        self._search_term = text
        self._redraw_graph()

    @Slot(bool)
    def _on_show_hidden_toggled(self, checked: bool) -> None:
        self._show_hidden = checked
        self._redraw_graph()


    def _checkout_branch(self, tree: ConversationTree, branch: Branch) -> None:
        if not tree or not branch:
            return
        if tree.checkout_branch(branch.id):
            self._mw.prompt_database.save_tree(tree)
            self._update_checkout_label()
            self._redraw_graph()
            if hasattr(self._mw, "log"):
                self._mw.log(
                    f"Checked out '{branch.name}' — new prompts go here.")

    def _checkout_from_selection(self) -> None:
        if not self._active_tree or not self._active_branch_id:
            return
        branch = self._active_tree.get_branch(self._active_branch_id)
        self._checkout_branch(self._active_tree, branch)

    def _update_checkout_label(self) -> None:
        if self._active_tree:
            co = self._active_tree.get_checked_out_branch()
            if co:
                self._lbl_checkout.setText(f"⬤  active: {co.name}")
                self._lbl_checkout.setToolTip(
                    f"New prompts will be added to: {co.name}")
                return
        self._lbl_checkout.setText("")


    def _fork_from_prompt(self, branch: Branch, prompt_id: str) -> None:
        """Fork from a specific prompt (right-click context menu)."""
        if not branch or not self._active_tree:
            return
        try:
            fork_index = branch.prompt_ids.index(prompt_id)
        except ValueError:
            fork_index = max(0, len(branch.prompt_ids) - 1)
        self._do_fork(branch, fork_index)

    def _fork_from_selection(self) -> None:
        """Fork from the currently selected prompt (toolbar button)."""
        if not self._active_branch_id or not self._active_tree:
            QMessageBox.information(
                self, "No selection",
                "Click a prompt node in the graph first, then press Fork.")
            return
        branch = self._active_tree.get_branch(self._active_branch_id)
        if not branch:
            return
        if self._active_prompt_id and self._active_prompt_id in branch.prompt_ids:
            fork_index = branch.prompt_ids.index(self._active_prompt_id)
        else:
            fork_index = max(0, len(branch.prompt_ids) - 1)
        self._do_fork(branch, fork_index)

    def _do_fork(self, parent_branch: Branch, fork_index: int) -> None:
        dlg = ForkDialog(
            parent_branch_name=parent_branch.name,
            prompt_count=len(parent_branch.prompt_ids),
            default_index=fork_index,
            parent=self,
        )
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        vals = dlg.get_values()
        if not vals["name"]:
            QMessageBox.warning(self, "Name required",
                                "Please enter a name for the new branch.")
            return

        child = self._active_tree.add_branch(
            name=vals["name"],
            parent_branch_id=parent_branch.id,
            fork_index=vals["fork_index"],
            trigger=vals["trigger"],
            reason=vals["reason"],
            context_summary=vals["context_summary"],
        )
        if child:
            self._active_tree.updated_at = datetime.now()
            self._mw.prompt_database.save_tree(self._active_tree)
            self._redraw_graph()
            self.branch_forked.emit(
                self._active_tree.name, parent_branch.name,
                child.name, vals["trigger"])
            if hasattr(self._mw, "log"):
                self._mw.log(
                    f"Forked '{parent_branch.name}' → new branch '{child.name}'.")


    def _merge_from_selection(self) -> None:
        if not self._active_branch_id or not self._active_tree:
            QMessageBox.information(
                self, "No selection",
                "Select a prompt node first to identify the branch to merge.")
            return
        branch = self._active_tree.get_branch(self._active_branch_id)
        if branch:
            self._do_merge(branch)

    def _do_merge(self, source: Branch) -> None:
        if len(self._active_tree.get_visible_branches()) < 2:
            QMessageBox.information(
                self, "Cannot merge", "Need at least two branches.")
            return
        dlg = MergeDialog(source, self._active_tree, parent=self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        vals = dlg.get_values()
        if not vals["target_branch_id"]:
            return
        ok = self._active_tree.merge_branch(
            source_branch_id=source.id,
            target_branch_id=vals["target_branch_id"],
            merge_insights=vals["insights"],
            include_unique_prompts=vals["include_prompts"],
        )
        if ok:
            self._mw.prompt_database.save_tree(self._active_tree)
            self._redraw_graph()
            target = self._active_tree.get_branch(vals["target_branch_id"])
            self.branch_merged.emit(
                self._active_tree.name, source.name, vals["insights"])
            if hasattr(self._mw, "log"):
                self._mw.log(
                    f"Merged '{source.name}' → '{target.name if target else '?'}'.")


    def _eadr_from_selection(self) -> None:
        if not self._active_tree or not self._active_branch_id:
            return
        branch = self._active_tree.get_branch(self._active_branch_id)
        if not branch:
            return
        if hasattr(self._mw, "_eadr_panel"):
            ctx = f"[Branch: {branch.name} | Tree: {self._active_tree.name}]\n"
            self._mw.prompt_database.add_eadr_note(
                ctx + "Add findings here…",
                self._mw._eadr_panel.project)
            self._mw._eadr_panel.refresh()
            self._mw._tabs.setCurrentWidget(self._mw._eadr_panel)


    def _copy_prompt_from_selection(self) -> None:
        db = getattr(self._mw, "prompt_database", None)
        if not db or not self._active_prompt_id:
            return
        p = db.get_prompt(self._active_prompt_id)
        if p:
            QApplication.clipboard().setText(p.prompt_text or "")
            if hasattr(self._mw, "log"):
                self._mw.log("Prompt text copied to clipboard.")
