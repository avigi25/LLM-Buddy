"""
Prompt Explorer panel — Visually-driven, automated conversational forking.

Treats LLM conversations as version-controlled, branchable structures.
Automatically syncs with the prompt database to build trees, and provides 
an interactive, draggable node map for branching and integration.

Improvements over v3.0:
  #1  Merge workflow — merge one branch into another
  #2  Rich fork dialog — capture trigger, reason, context at fork time
  #3  Fork at specific prompt index — right-click a prompt to fork there
  #4  Drag-and-drop prompt reordering & cross-branch moves
  #5  Explicit branch checkout — "git checkout" for incoming prompts
  #6  Search / filter across trees and branches
  #7  Fork-point context shown in details panel
  #8  Debounced position saves (no more per-drag full serialization)
  #9  Soft-delete with show/hide abandoned toggle
  #10 UX polish — dynamic node width, sortable headers, root styling
"""

import math
from datetime import datetime
from PySide6.QtCore import Qt, Signal, Slot, QRectF, QPointF, QTimer, QMimeData
from PySide6.QtGui import (
    QBrush, QColor, QPen, QFont, QPainterPath, QPainter,
    QAction, QTransform, QCursor, QKeySequence, QDrag
)
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QLabel, 
    QPushButton, QGraphicsView, QGraphicsScene, QGraphicsItem,
    QGraphicsPathItem, QMenu, QComboBox, QMessageBox,
    QFormLayout, QTextEdit, QLineEdit, QTreeWidget, QTreeWidgetItem,
    QInputDialog, QApplication, QDialog, QDialogButtonBox,
    QCheckBox, QAbstractItemView, QHeaderView, QGroupBox
)

from llm_buddy.core.forking import (
    ConversationTree, Branch, ForkPoint, 
    load_conversation_trees, save_conversation_trees,
    auto_detect_trees, BRANCH_STATUSES, FORK_TRIGGERS
)


# ==================================================================
# Improvement #2: Rich Fork Dialog
# ==================================================================

class ForkDialog(QDialog):
    """Multi-field dialog for creating a fork with full metadata."""

    def __init__(self, parent_branch_name: str, prompt_count: int,
                 default_index: int = -1, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Fork Branch")
        self.setMinimumWidth(420)
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel(
            f"<b>Forking from:</b> {parent_branch_name}"
        ))

        form = QFormLayout()

        self.edit_name = QLineEdit()
        self.edit_name.setPlaceholderText("e.g. 'Try alternative API approach'")
        form.addRow("Branch name:", self.edit_name)

        self.combo_trigger = QComboBox()
        for val, label in FORK_TRIGGERS:
            self.combo_trigger.addItem(label, val)
        # Default to "exploratory"
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

        # Fork index selector (#3)
        if prompt_count > 0:
            idx = default_index if 0 <= default_index < prompt_count else prompt_count - 1
            self.spin_index_label = QLabel(
                f"Fork after prompt <b>#{idx + 1}</b> of {prompt_count}")
            form.addRow("Fork point:", self.spin_index_label)
            self._fork_index = idx
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


# ==================================================================
# Improvement #1: Merge Dialog
# ==================================================================

class MergeDialog(QDialog):
    """Dialog to merge one branch into a chosen target."""

    def __init__(self, source_branch: Branch, tree: ConversationTree, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Merge Branch")
        self.setMinimumWidth(420)
        self._source = source_branch
        self._tree = tree

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(
            f"<b>Merge source:</b> {source_branch.name}  "
            f"({len(source_branch.prompt_ids)} prompts)"
        ))

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


# ------------------------------------------------------------------
# Visual Graph Components
# ------------------------------------------------------------------

class EdgeItem(QGraphicsPathItem):
    """Draws a smooth Bezier curve between two dynamic nodes."""
    def __init__(self, src_node, dst_node):
        super().__init__()
        self.src_node = src_node
        self.dst_node = dst_node
        self.setZValue(-1)
        self.setPen(QPen(QColor("#888888"), 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        self.update_path()

    def update_path(self):
        direction = "horizontal"
        if hasattr(self.src_node, "panel") and hasattr(self.src_node.panel, "_graph_view"):
            direction = getattr(self.src_node.panel._graph_view, "layout_direction", "horizontal")
        
        if direction == "horizontal":
            start = self.src_node.scenePos() + QPointF(self.src_node.width, self.src_node.height / 2)
            end = self.dst_node.scenePos() + QPointF(0, self.dst_node.height / 2)
            path = QPainterPath(start)
            dx = end.x() - start.x()
            cp_offset = max(dx * 0.5, 40)
            cp1 = QPointF(start.x() + cp_offset, start.y())
            cp2 = QPointF(end.x() - cp_offset, end.y())
            path.cubicTo(cp1, cp2, end)
        else:
            start = self.src_node.scenePos() + QPointF(self.src_node.width / 2, self.src_node.height)
            end = self.dst_node.scenePos() + QPointF(self.dst_node.width / 2, 0)
            path = QPainterPath(start)
            dy = end.y() - start.y()
            cp_offset = max(dy * 0.5, 40)
            cp1 = QPointF(start.x(), start.y() + cp_offset)
            cp2 = QPointF(end.x(), end.y() - cp_offset)
            path.cubicTo(cp1, cp2, end)
            
        self.setPath(path)


class NodeItem(QGraphicsItem):
    """Interactive, draggable visual node representing a conversation branch.

    Improvement #10: dynamic width based on name length, distinct root styling,
                     checkout indicator badge.
    """
    # --- #10: Dynamic width ---
    MIN_WIDTH = 180
    MAX_WIDTH = 300
    HEIGHT = 70
    CHAR_WIDTH = 8  # approximate px per character for sizing

    def __init__(self, branch: Branch, tree: ConversationTree, panel):
        super().__init__()
        self.branch = branch
        self.tree = tree
        self.panel = panel

        # --- #10: Compute dynamic width ---
        name_len = len(branch.name) * self.CHAR_WIDTH + 50
        self.width = max(self.MIN_WIDTH, min(name_len, self.MAX_WIDTH))
        self.height = self.HEIGHT

        self._is_root = (branch.parent_branch_id is None)
        self._is_checked_out = (tree.checked_out_branch_id == branch.id)
        
        self.setAcceptHoverEvents(True)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        
        self.is_hovered = False
        self._edges = []
        self._drag_start_pos = QPointF()

    def add_edge(self, edge: EdgeItem):
        self._edges.append(edge)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionHasChanged:
            for edge in self._edges:
                edge.update_path()
        return super().itemChange(change, value)

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        self.panel._is_dragging_node = True
        self._drag_start_pos = event.scenePos()

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        self.panel._is_dragging_node = False
        
        self.tree.updated_at = datetime.now()
        # --- #8: Debounced position save instead of immediate ---
        self.panel._queue_position_save(self.tree.id, self.branch.id, self.scenePos())
        
        delta = event.scenePos() - self._drag_start_pos
        length = abs(delta.x()) + abs(delta.y())
        if length < 5:
            self.panel.select_branch(self.branch.id)

    def boundingRect(self) -> QRectF:
        return QRectF(0, 0, self.width, self.height)

    def paint(self, painter: QPainter, option, widget=None):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        colors = {
            "active": QColor("#2196F3"),
            "completed": QColor("#4CAF50"),
            "abandoned": QColor("#9E9E9E"),
            "merged": QColor("#FF9800"),
        }
        base_color = colors.get(self.branch.status, QColor("#9E9E9E"))

        # --- #9: Dim hidden/soft-deleted nodes ---
        if self.branch.hidden:
            base_color = QColor("#CCCCCC")
        
        if self.isSelected():
            painter.setPen(QPen(base_color, 3))
            bg_color = base_color.lighter(180)
        elif self.is_hovered:
            painter.setPen(QPen(base_color, 2))
            bg_color = base_color.lighter(190)
        else:
            painter.setPen(QPen(base_color.darker(120), 1))
            bg_color = QColor("#ffffff")

        # --- #10: Distinct root styling — double border ---
        if self._is_root:
            painter.setPen(QPen(base_color, 3, Qt.PenStyle.SolidLine))

        painter.setBrush(QBrush(bg_color))
        painter.drawRoundedRect(self.boundingRect(), 8, 8)

        # --- #10: Root badge ---
        if self._is_root:
            painter.setBrush(QBrush(base_color.darker(110)))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(QRectF(4, 4, 16, 16), 3, 3)
            painter.setPen(QColor("#ffffff"))
            painter.setFont(QFont("Segoe UI", 7, QFont.Bold))
            painter.drawText(QRectF(4, 4, 16, 16), Qt.AlignmentFlag.AlignCenter, "R")
        
        # Status indicator dot
        painter.setBrush(QBrush(base_color))
        painter.setPen(Qt.PenStyle.NoPen)
        if not self._is_root:
            painter.drawEllipse(10, 10, 10, 10)

        # --- #5: Checkout indicator ---
        if self._is_checked_out:
            painter.setBrush(QBrush(QColor("#00C853")))
            painter.drawEllipse(int(self.width - 20), 6, 12, 12)
            painter.setPen(QColor("#ffffff"))
            painter.setFont(QFont("Segoe UI", 7, QFont.Bold))
            painter.drawText(QRectF(self.width - 20, 6, 12, 12),
                             Qt.AlignmentFlag.AlignCenter, "✓")

        # Branch name — #10: use full width, smarter truncation
        painter.setPen(QColor("#333333"))
        font = QFont("Segoe UI", 10, QFont.Bold)
        painter.setFont(font)
        
        max_chars = int((self.width - 40) / self.CHAR_WIDTH)
        display_name = self.branch.name
        if len(display_name) > max_chars:
            display_name = display_name[:max_chars - 1] + "…"
            
        painter.drawText(28, 20, display_name)
        
        font.setBold(False)
        font.setPointSize(8)
        painter.setFont(font)
        painter.setPen(QColor("#666666"))
        painter.drawText(12, 45, f"Prompts: {len(self.branch.prompt_ids)}")
        
        if self.branch.fork_point_id:
            fp = self.tree.get_fork_point(self.branch.fork_point_id)
            if fp:
                painter.drawText(12, 60, f"Trigger: {fp.trigger.capitalize()}")

    def hoverEnterEvent(self, event):
        self.is_hovered = True
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.update()

    def hoverLeaveEvent(self, event):
        self.is_hovered = False
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.update()

    def contextMenuEvent(self, event):
        menu = QMenu()
        
        # --- #5: Checkout action ---
        checkout_act = QAction("⬤ Checkout (receive new prompts)", menu)
        checkout_act.triggered.connect(lambda: self.panel._checkout_branch(self.tree, self.branch))
        if self._is_checked_out:
            checkout_act.setEnabled(False)
            checkout_act.setText("⬤ Checked out (current)")
        menu.addAction(checkout_act)
        menu.addSeparator()

        fork_act = QAction("🌱 Fork from here…", menu)
        fork_act.triggered.connect(lambda: self.panel._prompt_fork_creation(self.branch))
        menu.addAction(fork_act)

        # --- #1: Merge action ---
        merge_act = QAction("🔀 Merge into…", menu)
        merge_act.triggered.connect(lambda: self.panel._prompt_merge(self.branch))
        if len(self.tree.get_visible_branches()) < 2:
            merge_act.setEnabled(False)
        menu.addAction(merge_act)
        
        eadr_act = QAction("📝 Add eADR Note", menu)
        eadr_act.triggered.connect(lambda: self.panel._trigger_eadr_note(self.tree, self.branch))
        menu.addAction(eadr_act)
        
        menu.addSeparator()

        # --- #9: Soft-delete vs hard delete ---
        if not self.branch.hidden:
            hide_act = QAction("🫥 Archive Branch (soft delete)", menu)
            hide_act.triggered.connect(lambda: self.panel._soft_delete_branch(self.branch))
            if self.branch.parent_branch_id is None:
                hide_act.setEnabled(False)
            menu.addAction(hide_act)
        else:
            restore_act = QAction("♻️ Restore Branch", menu)
            restore_act.triggered.connect(lambda: self.panel._restore_branch(self.branch))
            menu.addAction(restore_act)

        delete_act = QAction("❌ Permanently Delete", menu)
        delete_act.triggered.connect(lambda: self.panel._delete_branch(self.branch))
        if self.branch.parent_branch_id is None:
            delete_act.setEnabled(False) 
        menu.addAction(delete_act)
            
        menu.exec(event.screenPos())


# ------------------------------------------------------------------
# Interactive Graph View
# ------------------------------------------------------------------

class TreeGraphView(QGraphicsView):
    """Draggable, zoomable canvas for the conversation tree."""
    def __init__(self, panel):
        super().__init__()
        self.panel = panel
        self.layout_direction = "vertical"
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.MinimalViewportUpdate)
        self.setBackgroundBrush(QBrush(QColor("#f4f6f9")))
        
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self._is_panning = False
        self._pan_start_pos = QPointF()
        self._node_items = {} 

    def draw_tree(self, tree: ConversationTree, preserve_viewport: bool = False,
                  show_hidden: bool = False, search_term: str = ""):
        """Rebuild the visual graph for *tree*.

        If *preserve_viewport* is True the current scene-rect is kept so
        that the caller can restore the viewport position afterwards
        without the coordinate space shifting underneath it.
        """
        old_scene_rect = self.sceneRect() if preserve_viewport else None

        self.scene.clear()
        self._node_items.clear()
        if not tree or not tree.branches:
            return

        if getattr(tree, "layout_positions", None) is None:
            tree.layout_positions = {}

        visible = tree.get_visible_branches(show_hidden=show_hidden)
        visible_ids = {b.id for b in visible}

        # --- #6: Highlight matches ---
        search_lower = search_term.strip().lower() if search_term else ""

        node_positions = {}
        y_counter = [0]

        def calc_positions(branch_id: str, depth: int) -> QPointF:
            children = [b for b in tree.get_child_branches(branch_id) if b.id in visible_ids]
            if not children:
                if self.layout_direction == "horizontal":
                    pos = QPointF(depth * 250, y_counter[0] * 120)
                else:
                    pos = QPointF(y_counter[0] * 220, depth * 150)
                y_counter[0] += 1
                node_positions[branch_id] = pos
                return pos

            child_y_sum = 0.0
            child_x_sum = 0.0
            for child in children:
                child_pos = calc_positions(child.id, depth + 1)
                child_y_sum += child_pos.y()
                child_x_sum += child_pos.x()
                
            if self.layout_direction == "horizontal":
                pos = QPointF(depth * 250, child_y_sum / max(len(children), 1))
            else:
                pos = QPointF(child_x_sum / max(len(children), 1), depth * 150)
                
            node_positions[branch_id] = pos
            return pos

        root_branch = tree.get_root_branch()
        if root_branch and root_branch.id in visible_ids:
            calc_positions(root_branch.id, 0)

        for branch in visible:
            node = NodeItem(branch, tree, self.panel)
            
            if branch.id in tree.layout_positions:
                px, py = tree.layout_positions[branch.id]
                node.setPos(QPointF(px, py))
            else:
                node.setPos(node_positions.get(branch.id, QPointF(0, 0)))

            # --- #6: Dim non-matching nodes during search ---
            if search_lower and search_lower not in branch.name.lower():
                node.setOpacity(0.35)

            self.scene.addItem(node)
            self._node_items[branch.id] = node

        for branch in visible:
            if branch.parent_branch_id and branch.parent_branch_id in self._node_items:
                src_node = self._node_items[branch.parent_branch_id]
                dst_node = self._node_items[branch.id]
                
                edge = EdgeItem(src_node, dst_node)
                self.scene.addItem(edge)
                
                src_node.add_edge(edge)
                dst_node.add_edge(edge)

        if old_scene_rect is not None and old_scene_rect.isValid():
            new_items_rect = self.scene.itemsBoundingRect().adjusted(-200, -200, 200, 200)
            self.scene.setSceneRect(old_scene_rect.united(new_items_rect))
        else:
            self.scene.setSceneRect(self.scene.itemsBoundingRect().adjusted(-200, -200, 200, 200))

    def select_node(self, branch_id: str, center_view: bool = True):
        for item in self.scene.selectedItems():
            item.setSelected(False)
        node = self._node_items.get(branch_id)
        if node:
            node.setSelected(True)
            if center_view:
                self.centerOn(node)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_F:
            self.panel._fit_to_view()
        elif event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            if self.panel._active_branch:
                self.panel._soft_delete_branch(self.panel._active_branch)
        else:
            super().keyPressEvent(event)

    def mousePressEvent(self, event):
        self.setFocus()
        if event.button() == Qt.MouseButton.MiddleButton:
            self._is_panning = True
            self._pan_start_pos = event.pos()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.MiddleButton:
            self._is_panning = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event):
        if self._is_panning:
            delta = event.pos() - self._pan_start_pos
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
            self._pan_start_pos = event.pos()
            event.accept()
            return
        super().mouseMoveEvent(event)

    def wheelEvent(self, event):
        zoom_in_factor = 1.15
        zoom_out_factor = 1 / zoom_in_factor
        current_scale = self.transform().m11()
        
        if event.angleDelta().y() > 0:
            if current_scale < 3.0:
                self.scale(zoom_in_factor, zoom_in_factor)
        else:
            if current_scale > 0.3:
                self.scale(zoom_out_factor, zoom_out_factor)


# ------------------------------------------------------------------
# Improvement #4: Drag-and-drop Prompt Tree
# ------------------------------------------------------------------

class PromptTreeWidget(QTreeWidget):
    """QTreeWidget subclass with drag-and-drop for prompt reordering
    and cross-branch moves via the panel."""

    prompt_moved = Signal(str, int, int)       # prompt_id, old_row, new_row
    prompt_dropped_external = Signal(str)       # prompt_id (dropped from outside)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        # --- #10: sortable headers ---
        self.setSortingEnabled(True)

    def dropEvent(self, event):
        """Emit reorder signal after internal move."""
        dragged_item = self.currentItem()
        if not dragged_item:
            super().dropEvent(event)
            return

        old_row = self.indexOfTopLevelItem(dragged_item)
        super().dropEvent(event)
        new_row = self.indexOfTopLevelItem(dragged_item)

        pid = dragged_item.data(0, Qt.ItemDataRole.UserRole)
        if pid and old_row != new_row and old_row >= 0 and new_row >= 0:
            self.prompt_moved.emit(pid, old_row, new_row)


# ------------------------------------------------------------------
# Main Panel
# ------------------------------------------------------------------

class ForkingPanel(QWidget):
    
    branch_forked = Signal(str, str, str, str)
    branch_merged = Signal(str, str, str)

    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self._mw = main_window
        self._trees: list[ConversationTree] = []
        self._active_tree: ConversationTree | None = None
        self._active_branch: Branch | None = None
        
        self._is_dragging_node = False

        # --- #9: Show/hide hidden branches toggle state ---
        self._show_hidden = False

        # --- #6: Current search term ---
        self._search_term = ""
        
        # Auto-save timer (text edits)
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(400)
        self._save_timer.timeout.connect(self._execute_save)

        # --- #8: Debounced position save timer ---
        self._pos_save_timer = QTimer(self)
        self._pos_save_timer.setSingleShot(True)
        self._pos_save_timer.setInterval(600)
        self._pos_save_timer.timeout.connect(self._flush_position_saves)
        self._pending_positions: dict[tuple, QPointF] = {}

        # Periodic sync
        self._sync_timer = QTimer(self)
        self._sync_timer.setInterval(30000)
        self._sync_timer.timeout.connect(self.refresh)
        
        self._build_ui()
        self.refresh()
        self._sync_timer.start()

    # ==============================================================
    # UI Construction
    # ==============================================================

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 1. Instantiate the graph view FIRST
        self._graph_view = TreeGraphView(self)
        
        # --- Toolbar row 1: tree selector + main actions ---
        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(8, 8, 8, 4)
        
        toolbar.addWidget(QLabel("<b>Tree:</b>"))
        self._tree_selector = QComboBox()
        self._tree_selector.setMinimumWidth(260)
        self._tree_selector.currentIndexChanged.connect(self._on_tree_changed)
        toolbar.addWidget(self._tree_selector)

        # --- #5: Checkout indicator label ---
        self._lbl_checkout = QLabel("")
        self._lbl_checkout.setStyleSheet(
            "color: #00C853; font-weight: bold; padding: 0 8px;")
        toolbar.addWidget(self._lbl_checkout)

        toolbar.addStretch()
        
        btn_refresh = QPushButton("↻ Sync")
        btn_refresh.setToolTip("Sync conversations from Prompt Database immediately")
        btn_refresh.clicked.connect(self.refresh)
        toolbar.addWidget(btn_refresh)
        
        btn_fit = QPushButton("⛶ Fit (F)")
        btn_fit.clicked.connect(self._fit_to_view)
        toolbar.addWidget(btn_fit)

        current_direction = getattr(self._graph_view, "layout_direction", "horizontal")
        initial_text = "⬍ Vertical" if current_direction == "vertical" else "⬌ Horizontal"
        self.btn_layout = QPushButton(initial_text) 
        self.btn_layout.setToolTip("Switch between Horizontal and Vertical branching")
        self.btn_layout.clicked.connect(self._toggle_layout)
        toolbar.addWidget(self.btn_layout)
        
        layout.addLayout(toolbar)

        # --- Toolbar row 2: search + toggles ---
        toolbar2 = QHBoxLayout()
        toolbar2.setContentsMargins(8, 0, 8, 8)

        # --- #6: Search bar ---
        toolbar2.addWidget(QLabel("🔍"))
        self._search_box = QLineEdit()
        self._search_box.setPlaceholderText("Filter branches by name…")
        self._search_box.setClearButtonEnabled(True)
        self._search_box.setMaximumWidth(280)
        self._search_box.textChanged.connect(self._on_search_changed)
        toolbar2.addWidget(self._search_box)

        # --- #9: Show hidden toggle ---
        self._chk_show_hidden = QCheckBox("Show archived")
        self._chk_show_hidden.setToolTip("Show soft-deleted / archived branches")
        self._chk_show_hidden.toggled.connect(self._on_show_hidden_toggled)
        toolbar2.addWidget(self._chk_show_hidden)

        toolbar2.addStretch()
        layout.addLayout(toolbar2)

        # --- Main splitter: graph | details ---
        self._splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(self._splitter, stretch=1)

        self._splitter.addWidget(self._graph_view)

        details_widget = QWidget()
        details_layout = QVBoxLayout(details_widget)
        details_layout.setContentsMargins(16, 12, 16, 12)
        
        self._lbl_branch_title = QLabel("<h2>Select a node</h2>")
        details_layout.addWidget(self._lbl_branch_title)

        # --- #7: Fork origin info ---
        self._fork_origin_group = QGroupBox("Fork Origin")
        fork_origin_layout = QFormLayout(self._fork_origin_group)
        self._lbl_fork_parent = QLabel("—")
        fork_origin_layout.addRow("Parent:", self._lbl_fork_parent)
        self._lbl_fork_trigger = QLabel("—")
        fork_origin_layout.addRow("Trigger:", self._lbl_fork_trigger)
        self._lbl_fork_reason = QLabel("—")
        self._lbl_fork_reason.setWordWrap(True)
        fork_origin_layout.addRow("Reason:", self._lbl_fork_reason)
        self._lbl_fork_context = QLabel("—")
        self._lbl_fork_context.setWordWrap(True)
        fork_origin_layout.addRow("Context:", self._lbl_fork_context)
        self._fork_origin_group.setVisible(False)
        details_layout.addWidget(self._fork_origin_group)
        
        form = QFormLayout()
        
        self._edit_name = QLineEdit()
        self._edit_name.textChanged.connect(self._queue_auto_save)
        form.addRow("Name:", self._edit_name)
        
        self._combo_status = QComboBox()
        self._combo_status.addItems([label for val, label in BRANCH_STATUSES])
        self._combo_status.currentIndexChanged.connect(self._queue_auto_save)
        form.addRow("Status:", self._combo_status)
        
        details_layout.addLayout(form)
        
        details_layout.addWidget(QLabel("<b>Branch Notes:</b>"))
        self._edit_notes = QTextEdit()
        self._edit_notes.textChanged.connect(self._queue_auto_save)
        details_layout.addWidget(self._edit_notes, stretch=1)
        
        details_layout.addWidget(QLabel("<b>Prompts in Branch:</b>"))
        # --- #4 & #10: PromptTreeWidget with DnD and sortable headers ---
        self._prompt_list = PromptTreeWidget()
        self._prompt_list.setHeaderLabels(["Date", "LLM", "Preview"])
        self._prompt_list.header().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self._prompt_list.itemDoubleClicked.connect(self._on_prompt_double_clicked)
        self._prompt_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self._prompt_list.customContextMenuRequested.connect(self._on_prompt_context_menu)
        self._prompt_list.prompt_moved.connect(self._on_prompt_reordered)
        details_layout.addWidget(self._prompt_list, stretch=2)
        
        action_row = QHBoxLayout()
        btn_fork = QPushButton("🌱 Fork Branch")
        btn_fork.setProperty("class", "primary")
        btn_fork.clicked.connect(lambda: self._prompt_fork_creation(self._active_branch))
        action_row.addWidget(btn_fork)

        # --- #1: Merge button ---
        btn_merge = QPushButton("🔀 Merge")
        btn_merge.clicked.connect(lambda: self._prompt_merge(self._active_branch))
        action_row.addWidget(btn_merge)
        
        btn_eadr = QPushButton("📝 eADR Note")
        btn_eadr.clicked.connect(lambda: self._trigger_eadr_note(self._active_tree, self._active_branch))
        action_row.addWidget(btn_eadr)
        
        details_layout.addLayout(action_row)
        
        self._details_widget = details_widget
        self._details_widget.setEnabled(False)
        self._splitter.addWidget(self._details_widget)
        
        self._splitter.setStretchFactor(0, 3)
        self._splitter.setStretchFactor(1, 1)

    # ==============================================================
    # Core Logic
    # ==============================================================

    def _fit_to_view(self):
        if self._graph_view.scene.items():
            self._graph_view.fitInView(
                self._graph_view.scene.itemsBoundingRect(),
                Qt.AspectRatioMode.KeepAspectRatio)

    # --- #8: Debounced position persistence ---

    def _queue_position_save(self, tree_id: str, branch_id: str, pos: QPointF):
        """Queue a position update; flushed after a short debounce."""
        tree = next((t for t in self._trees if t.id == tree_id), None)
        if not tree:
            return
        if getattr(tree, "layout_positions", None) is None:
            tree.layout_positions = {}
        tree.layout_positions[branch_id] = (float(pos.x()), float(pos.y()))
        self._pending_positions[(tree_id, branch_id)] = pos
        self._pos_save_timer.start()

    def _flush_position_saves(self):
        """Write all pending position changes in a single save."""
        if self._pending_positions:
            self._pending_positions.clear()
            save_conversation_trees(self._trees)

    # Keep the old name as a thin compat shim
    def persist_node_position(self, tree_id: str, branch_id: str, pos: QPointF):
        self._queue_position_save(tree_id, branch_id, pos)

    # ==============================================================
    # Refresh / Sync
    # ==============================================================

    def refresh(self):
        if getattr(self, "_is_dragging_node", False):
            return

        if self._save_timer.isActive():
            self._execute_save()

        # 1. SAVE VIEWPORT STATE
        saved_transform = self._graph_view.transform()
        viewport_rect = self._graph_view.viewport().rect()
        saved_center = self._graph_view.mapToScene(viewport_rect.center())
        self._graph_view.viewport().setUpdatesEnabled(False)

        active_tree_id = self._active_tree.id if self._active_tree else None
        active_branch_id = self._active_branch.id if self._active_branch else None

        self._trees = load_conversation_trees()
        
        db = getattr(self._mw, "prompt_database", None)
        suggestions = auto_detect_trees(db) if db else []
        
        existing_trees_by_cid = {}
        for t in self._trees:
            cid = getattr(t, "source_conversation_id", None)
            if not cid:
                for tag in getattr(t, "tags", []):
                    if isinstance(tag, str) and tag.startswith("cid:"):
                        cid = tag[4:]
                        break
            if not cid:
                cid = t.name
            existing_trees_by_cid[cid] = t

        trees_modified = False
        
        for sug in suggestions:
            cid = sug["conversation_id"]
            if not cid:
                continue
                
            if cid not in existing_trees_by_cid:
                new_tree = ConversationTree(name=cid, description=sug["sample_description"])
                new_tree.source_conversation_id = cid
                
                if not hasattr(new_tree, "tags"):
                    new_tree.tags = []
                new_tree.tags.append(f"cid:{cid}")
                
                root = new_tree.get_root_branch()
                root.prompt_ids = sug["prompt_ids"]
                self._trees.append(new_tree)
                existing_trees_by_cid[cid] = new_tree
                trees_modified = True
            else:
                tree = existing_trees_by_cid[cid]
                
                all_ids = set()
                for b in tree.branches:
                    all_ids.update(b.prompt_ids)
                
                new_prompts = [pid for pid in sug["prompt_ids"] if pid not in all_ids]
                if new_prompts:
                    # --- #5: Route new prompts to the checked-out branch ---
                    target_branch = tree.get_checked_out_branch()

                    if target_branch:
                        target_branch.prompt_ids.extend(new_prompts)
                        trees_modified = True

        if trees_modified:
            save_conversation_trees(self._trees)

        # --- Rebuild tree selector, filtering by search ---
        self._tree_selector.blockSignals(True)
        self._tree_selector.clear()
        
        restore_idx = 0
        search_lower = self._search_term.strip().lower()
        for idx, tree in enumerate(self._trees):
            display = f"{tree.name} ({len(tree.branches)} branches)"
            # --- #6: Filter tree selector ---
            if search_lower and search_lower not in tree.name.lower():
                # Check if any branch name matches
                if not any(search_lower in b.name.lower() for b in tree.branches):
                    continue
            self._tree_selector.addItem(display, tree.id)
            if active_tree_id and tree.id == active_tree_id:
                restore_idx = self._tree_selector.count() - 1
                self._active_tree = tree
                
        self._tree_selector.setCurrentIndex(restore_idx)
        self._tree_selector.blockSignals(False)
        
        if self._trees and not self._active_tree:
            self._active_tree = self._trees[0]
            self._tree_selector.setCurrentIndex(0)
            
        if self._active_tree:
            self._graph_view.draw_tree(
                self._active_tree,
                preserve_viewport=True,
                show_hidden=self._show_hidden,
                search_term=self._search_term)

        if active_branch_id and self._active_tree:
            self.select_branch(active_branch_id, center_view=False)

        # --- #5: Update checkout label ---
        self._update_checkout_label()

        # 2. RESTORE VIEWPORT STATE
        self._graph_view.setTransform(saved_transform)
        self._graph_view.centerOn(saved_center)
        self._graph_view.viewport().setUpdatesEnabled(True)

    def _on_tree_changed(self, index: int):
        if index < 0:
            return
        tree_id = self._tree_selector.itemData(index)
        tree = next((t for t in self._trees if t.id == tree_id), None)
        if not tree:
            return
        
        self._active_tree = tree
        self._active_branch = None
        self._details_widget.setEnabled(False)
        self._lbl_branch_title.setText("<h2>Select a node</h2>")
        self._fork_origin_group.setVisible(False)
        
        self._graph_view.draw_tree(
            self._active_tree,
            show_hidden=self._show_hidden,
            search_term=self._search_term)
        self._update_checkout_label()
        QTimer.singleShot(50, self._fit_to_view)

    # ==============================================================
    # Branch Selection & Details
    # ==============================================================

    def select_branch(self, branch_id: str, center_view: bool = True):
        if not self._active_tree:
            return
            
        self._active_branch = self._active_tree.get_branch(branch_id)
        if not self._active_branch:
            return
            
        self._graph_view.select_node(branch_id, center_view=center_view)

        self._details_widget.setEnabled(True)
        self._lbl_branch_title.setText(f"<h2>{self._active_branch.name}</h2>")
        
        self._edit_name.blockSignals(True)
        self._combo_status.blockSignals(True)
        self._edit_notes.blockSignals(True)
        
        self._edit_name.setText(self._active_branch.name)
        self._edit_notes.setPlainText(self._active_branch.notes)
        for i, (val, label) in enumerate(BRANCH_STATUSES):
            if val == self._active_branch.status:
                self._combo_status.setCurrentIndex(i)
                break
                
        self._edit_name.blockSignals(False)
        self._combo_status.blockSignals(False)
        self._edit_notes.blockSignals(False)

        # --- #7: Show fork-point context ---
        self._update_fork_origin_display()
        
        self._refresh_prompt_list()

    def _update_fork_origin_display(self):
        """Populate the fork-origin group box for the active branch."""
        branch = self._active_branch
        if not branch or not branch.fork_point_id or not self._active_tree:
            self._fork_origin_group.setVisible(False)
            return

        fp = self._active_tree.get_fork_point(branch.fork_point_id)
        if not fp:
            self._fork_origin_group.setVisible(False)
            return

        self._fork_origin_group.setVisible(True)
        parent = self._active_tree.get_branch(fp.parent_branch_id)
        self._lbl_fork_parent.setText(parent.name if parent else "—")

        trigger_label = fp.trigger
        for val, label in FORK_TRIGGERS:
            if val == fp.trigger:
                trigger_label = label
                break
        self._lbl_fork_trigger.setText(trigger_label)
        self._lbl_fork_reason.setText(fp.reason or "—")
        self._lbl_fork_context.setText(fp.context_summary or "—")

    def _refresh_prompt_list(self):
        self._prompt_list.setSortingEnabled(False)  # pause while loading
        self._prompt_list.clear()
        if not self._active_branch:
            return
            
        db = getattr(self._mw, "prompt_database", None)
        if not db:
            return
            
        for pid in self._active_branch.prompt_ids:
            p = db.get_prompt(pid)
            if p:
                date_str = p.timestamp.strftime("%m-%d %H:%M") if p.timestamp else "—"
                desc = p.description or (p.prompt_text[:40] + "…" if p.prompt_text else "—")
                item = QTreeWidgetItem([date_str, p.llm_used or "Unknown", desc])
                item.setData(0, Qt.ItemDataRole.UserRole, pid)
                self._prompt_list.addTopLevelItem(item)

        self._prompt_list.setSortingEnabled(True)

    def _on_prompt_double_clicked(self, item: QTreeWidgetItem, column: int):
        prompt_id = item.data(0, Qt.ItemDataRole.UserRole)
        if prompt_id and hasattr(self._mw, "open_prompt_viewer"):
            self._mw.open_prompt_viewer(prompt_id)

    # ==============================================================
    # Auto-save
    # ==============================================================

    def _queue_auto_save(self):
        self._save_timer.start()

    def _execute_save(self):
        if not self._active_branch or not self._active_tree:
            return
            
        self._active_branch.name = self._edit_name.text()
        self._active_branch.notes = self._edit_notes.toPlainText()
        self._active_branch.status = BRANCH_STATUSES[self._combo_status.currentIndex()][0]
        self._active_branch.updated_at = datetime.now()
        
        save_conversation_trees(self._trees)
        
        for item in self._graph_view.scene.items():
            if isinstance(item, NodeItem) and item.branch.id == self._active_branch.id:
                item.update()
                break

    # ==============================================================
    # Search & Filter (#6)
    # ==============================================================

    @Slot(str)
    def _on_search_changed(self, text: str):
        self._search_term = text
        if self._active_tree:
            self._graph_view.draw_tree(
                self._active_tree,
                preserve_viewport=True,
                show_hidden=self._show_hidden,
                search_term=self._search_term)

    # ==============================================================
    # Show/Hide archived (#9)
    # ==============================================================

    @Slot(bool)
    def _on_show_hidden_toggled(self, checked: bool):
        self._show_hidden = checked
        if self._active_tree:
            self._graph_view.draw_tree(
                self._active_tree,
                preserve_viewport=True,
                show_hidden=self._show_hidden,
                search_term=self._search_term)

    # ==============================================================
    # Prompt Context Menu & Actions
    # ==============================================================

    @Slot()
    def _toggle_layout(self):
        if self._graph_view.layout_direction == "horizontal":
            self._graph_view.layout_direction = "vertical"
            self.btn_layout.setText("⬍ Vertical")
        else:
            self._graph_view.layout_direction = "horizontal"
            self.btn_layout.setText("⬌ Horizontal")
            
        if self._active_tree:
            self._active_tree.layout_positions = {}
            self._graph_view.draw_tree(
                self._active_tree,
                show_hidden=self._show_hidden,
                search_term=self._search_term)
            self._fit_to_view()

    @Slot(object)
    def _on_prompt_context_menu(self, pos):
        item = self._prompt_list.itemAt(pos)
        if not item:
            return
            
        prompt_id = item.data(0, Qt.ItemDataRole.UserRole)
        row_index = self._prompt_list.indexOfTopLevelItem(item)
        
        menu = QMenu()

        restore_act = QAction("↩ Restore Prompt (Copy to Clipboard)", menu)
        restore_act.triggered.connect(lambda: self._restore_prompt(prompt_id))
        menu.addAction(restore_act)

        # --- #3: Fork from this specific prompt ---
        fork_here_act = QAction("🌱 Fork from this prompt…", menu)
        fork_here_act.triggered.connect(
            lambda: self._prompt_fork_creation(self._active_branch, fork_index=row_index))
        menu.addAction(fork_here_act)

        # --- #4: Move to another branch ---
        move_act = QAction("📦 Move to another branch…", menu)
        move_act.triggered.connect(lambda: self._move_prompt_to_branch(prompt_id))
        menu.addAction(move_act)

        menu.addSeparator()

        remove_act = QAction("🗑 Remove from this branch", menu)
        remove_act.triggered.connect(lambda: self._remove_prompt_from_branch(prompt_id))
        menu.addAction(remove_act)

        menu.exec(self._prompt_list.viewport().mapToGlobal(pos))
        
    def _restore_prompt(self, prompt_id: str):
        db = getattr(self._mw, "prompt_database", None)
        if not db:
            return
        
        prompt = db.get_prompt(prompt_id)
        if prompt:
            QApplication.clipboard().setText(prompt.prompt_text)
            self._mw.log(f"Prompt '{prompt.description}' restored to clipboard.")
            QMessageBox.information(
                self, "Prompt Restored",
                "Prompt text copied to clipboard! You can now paste it into your LLM.")

    # --- #4: Prompt reorder handler ---
    @Slot(str, int, int)
    def _on_prompt_reordered(self, prompt_id: str, old_row: int, new_row: int):
        """Handle drag-and-drop reorder within the current branch."""
        if not self._active_branch or not self._active_tree:
            return
        pids = self._active_branch.prompt_ids
        if 0 <= old_row < len(pids) and 0 <= new_row < len(pids):
            pids.insert(new_row, pids.pop(old_row))
            self._active_branch.updated_at = datetime.now()
            save_conversation_trees(self._trees)

    # --- #4: Move prompt to another branch ---
    def _move_prompt_to_branch(self, prompt_id: str):
        if not self._active_tree or not self._active_branch:
            return

        choices = []
        for branch in self._active_tree.get_visible_branches(show_hidden=self._show_hidden):
            if branch.id != self._active_branch.id:
                choices.append((f"{branch.name} ({len(branch.prompt_ids)} prompts)", branch))

        if not choices:
            QMessageBox.information(self, "No Targets", "No other visible branches to move to.")
            return

        labels = [c[0] for c in choices]
        chosen, ok = QInputDialog.getItem(
            self, "Move Prompt", "Move to branch:", labels, 0, False)
        if not ok:
            return

        _, target = choices[labels.index(chosen)]
        if self._active_tree.move_prompt(prompt_id, self._active_branch.id, target.id):
            save_conversation_trees(self._trees)
            self._refresh_prompt_list()
            self._mw.log(f"Prompt moved to '{target.name}'.")

    def _remove_prompt_from_branch(self, prompt_id: str):
        """Remove a prompt from the active branch (doesn't delete from DB)."""
        if not self._active_branch:
            return
        if prompt_id in self._active_branch.prompt_ids:
            self._active_branch.prompt_ids.remove(prompt_id)
            self._active_branch.updated_at = datetime.now()
            save_conversation_trees(self._trees)
            self._refresh_prompt_list()

    # ==============================================================
    # Checkout (#5)
    # ==============================================================

    def _checkout_branch(self, tree: ConversationTree, branch: Branch):
        if tree.checkout_branch(branch.id):
            save_conversation_trees(self._trees)
            self._update_checkout_label()
            self._mw.log(f"Checked out branch '{branch.name}' — new prompts will go here.")
            # Redraw to update the green badge
            self._graph_view.draw_tree(
                tree,
                preserve_viewport=True,
                show_hidden=self._show_hidden,
                search_term=self._search_term)

    def _update_checkout_label(self):
        if self._active_tree:
            co = self._active_tree.get_checked_out_branch()
            if co:
                self._lbl_checkout.setText(f"⬤ {co.name}")
                self._lbl_checkout.setToolTip(
                    f"New prompts will be added to: {co.name}")
            else:
                self._lbl_checkout.setText("")
        else:
            self._lbl_checkout.setText("")

    # ==============================================================
    # Integration Hooks
    # ==============================================================

    def add_prompt_to_branch(self, prompt_id: str):
        if not self._trees:
            QMessageBox.information(self, "No Trees", "Create/import a conversation tree first.")
            return

        choices = []
        for tree in self._trees:
            for branch in tree.get_visible_branches():
                choices.append((f"{tree.name} / {branch.name}", tree, branch))

        labels = [c[0] for c in choices]
        chosen, ok = QInputDialog.getItem(
            self, "Add to Branch", "Select a branch:", labels, 0, False
        )
        if not ok:
            return

        _, tree, branch = choices[labels.index(chosen)]
        if prompt_id in branch.prompt_ids:
            QMessageBox.information(self, "Already Added", "That prompt is already in the selected branch.")
            return

        branch.prompt_ids.append(prompt_id)
        
        tree.updated_at = datetime.now()
        save_conversation_trees(self._trees)
        self.refresh()

    # ==============================================================
    # Fork Creation (#2 + #3)
    # ==============================================================

    def _prompt_fork_creation(self, parent_branch: Branch, fork_index: int = -1):
        if not parent_branch or not self._active_tree:
            return

        prompt_count = len(parent_branch.prompt_ids)
        dlg = ForkDialog(
            parent_branch_name=parent_branch.name,
            prompt_count=prompt_count,
            default_index=fork_index,
            parent=self,
        )
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        vals = dlg.get_values()
        if not vals["name"]:
            QMessageBox.warning(self, "Name required", "Please provide a branch name.")
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
            save_conversation_trees(self._trees)
            self._graph_view.draw_tree(
                self._active_tree,
                show_hidden=self._show_hidden,
                search_term=self._search_term)
            self.select_branch(child.id)
            self.branch_forked.emit(
                self._active_tree.id, parent_branch.id,
                child.id, vals["trigger"])

    # ==============================================================
    # Merge (#1)
    # ==============================================================

    def _prompt_merge(self, source_branch: Branch):
        if not source_branch or not self._active_tree:
            return
        if len(self._active_tree.get_visible_branches()) < 2:
            QMessageBox.information(self, "Cannot Merge", "Need at least two visible branches.")
            return

        dlg = MergeDialog(source_branch, self._active_tree, parent=self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        vals = dlg.get_values()
        if not vals["target_branch_id"]:
            return

        ok = self._active_tree.merge_branch(
            source_branch_id=source_branch.id,
            target_branch_id=vals["target_branch_id"],
            merge_insights=vals["insights"],
            include_unique_prompts=vals["include_prompts"],
        )
        if ok:
            save_conversation_trees(self._trees)
            target = self._active_tree.get_branch(vals["target_branch_id"])
            self._mw.log(
                f"Merged '{source_branch.name}' → '{target.name if target else '?'}'.")
            self._graph_view.draw_tree(
                self._active_tree,
                show_hidden=self._show_hidden,
                search_term=self._search_term)
            if target:
                self.select_branch(target.id)
            self.branch_merged.emit(
                self._active_tree.id, source_branch.id,
                vals["target_branch_id"])

    # ==============================================================
    # eADR Integration
    # ==============================================================

    def _trigger_eadr_note(self, tree: ConversationTree, branch: Branch):
        if not tree or not branch:
            return
        
        context = f"[Branch: {branch.name} | Tree: {tree.name}]\n"
        
        if hasattr(self._mw, "_eadr_panel"):
            from llm_buddy.core.eadr import save_eadr_note
            project = self._mw._eadr_panel.project
            save_eadr_note(context + "Add your findings here...", project)
            self._mw._eadr_panel.refresh()
            self._mw.log(f"Auto-generated eADR note for branch '{branch.name}'.")
            self._mw._tabs.setCurrentWidget(self._mw._eadr_panel)

    # ==============================================================
    # Soft-delete (#9) & Hard Delete
    # ==============================================================

    def _soft_delete_branch(self, branch: Branch):
        """Archive a branch (soft-delete) — hide it but keep data."""
        if not self._active_tree or not branch:
            return
        if branch.parent_branch_id is None:
            QMessageBox.warning(self, "Cannot Archive", "The root branch cannot be archived.")
            return

        confirm = QMessageBox.question(
            self, "Archive Branch",
            f"Archive '{branch.name}' and its sub-branches?\n\n"
            "They will be hidden but can be restored later via "
            "'Show archived'.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        self._active_tree.soft_delete_branch(branch.id)
        save_conversation_trees(self._trees)

        self._active_branch = None
        self._details_widget.setEnabled(False)
        self._lbl_branch_title.setText("<h2>Select a node</h2>")
        self._fork_origin_group.setVisible(False)
        self._graph_view.draw_tree(
            self._active_tree,
            show_hidden=self._show_hidden,
            search_term=self._search_term)
        self._mw.log(f"Branch '{branch.name}' archived.")

    def _restore_branch(self, branch: Branch):
        """Restore a soft-deleted branch."""
        if not self._active_tree or not branch:
            return
        self._active_tree.restore_branch(branch.id)
        save_conversation_trees(self._trees)
        self._graph_view.draw_tree(
            self._active_tree,
            show_hidden=self._show_hidden,
            search_term=self._search_term)
        self._mw.log(f"Branch '{branch.name}' restored.")

    def _delete_branch(self, branch: Branch):
        """Permanently remove a branch and all sub-branches."""
        if not self._active_tree:
            return
            
        confirm = QMessageBox.question(
            self, "Permanently Delete", 
            f"⚠️ PERMANENTLY delete '{branch.name}' and all its sub-branches?\n\n"
            "This cannot be undone. Use 'Archive' for a safer alternative.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if confirm == QMessageBox.StandardButton.Yes:
            self._active_tree.remove_branch(branch.id)
            self._active_tree.updated_at = datetime.now()
            save_conversation_trees(self._trees)
            self._active_branch = None
            self._details_widget.setEnabled(False)
            self._lbl_branch_title.setText("<h2>Select a node</h2>")
            self._fork_origin_group.setVisible(False)
            self._graph_view.draw_tree(
                self._active_tree,
                show_hidden=self._show_hidden,
                search_term=self._search_term)
