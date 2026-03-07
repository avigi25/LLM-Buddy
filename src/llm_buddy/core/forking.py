"""
Conversational Forking data model and persistence for LLM Buddy.

Implements the Conversational Forking (CF) method — a non-linear
context engineering approach that treats LLM conversations as
version-controlled, branchable structures rather than immutable
linear sequences.

Improvements over v3.0:
  - Merge workflow support (merge_branch method)
  - Explicit branch checkout tracking (checked_out_branch_id)
  - Soft-delete support (hidden flag on Branch)
"""

import json
import logging
import os
import uuid
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(os.getcwd(), "data")
os.makedirs(DATA_DIR, exist_ok=True)

# Update the default:
DEFAULT_TREES_PATH = os.path.join(DATA_DIR, "conversation_trees.json")

# =====================================================================
# Constants (value, display_label)
# =====================================================================

FORK_TRIGGERS = [
    ("error_cascade", "Error Cascade"),
    ("context_overflow", "Context Overflow"),
    ("exploratory", "Exploratory Branching"),
    ("optimization", "Optimization Opportunity"),
    ("other", "Other"),
]

BRANCH_STRATEGIES = [
    ("", "(none)"),
    ("divergent", "Divergent Exploration"),
    ("convergent", "Convergent Refinement"),
    ("parallel", "Parallel Processing"),
]

BRANCH_STATUSES = [
    ("active", "Active"),
    ("completed", "Completed"),
    ("abandoned", "Abandoned"),
    ("merged", "Merged"),
]

TREE_STATUSES = [
    ("active", "Active"),
    ("completed", "Completed"),
    ("archived", "Archived"),
]

# =====================================================================
# Helpers
# =====================================================================

def _parse_dt(s: str) -> Optional[datetime]:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s)
    except (ValueError, TypeError):
        return None

def _now_iso() -> str:
    return datetime.now().isoformat()

def _norm_pos(v):
    if isinstance(v, (list, tuple)) and len(v) >= 2:
        return (float(v[0]), float(v[1]))
    if isinstance(v, dict) and "x" in v and "y" in v:
        return (float(v["x"]), float(v["y"]))
    return None

# =====================================================================
# Data model
# =====================================================================

@dataclass
class ForkPoint:
    id: str = ""
    parent_branch_id: str = ""
    child_branch_id: str = ""
    prompt_id: str = ""
    fork_index: int = 0
    trigger: str = "other"
    reason: str = ""
    context_summary: str = ""
    key_artifacts: str = ""
    timestamp: Optional[datetime] = None

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())
        if self.timestamp is None:
            self.timestamp = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "parent_branch_id": self.parent_branch_id,
            "child_branch_id": self.child_branch_id,
            "prompt_id": self.prompt_id,
            "fork_index": self.fork_index,
            "trigger": self.trigger,
            "reason": self.reason,
            "context_summary": self.context_summary,
            "key_artifacts": self.key_artifacts,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ForkPoint":
        fp = cls()
        fp.id = d.get("id", str(uuid.uuid4()))
        fp.parent_branch_id = d.get("parent_branch_id", "")
        fp.child_branch_id = d.get("child_branch_id", "")
        fp.prompt_id = d.get("prompt_id", "")
        fp.fork_index = d.get("fork_index", 0)
        fp.trigger = d.get("trigger", "other")
        fp.reason = d.get("reason", "")
        fp.context_summary = d.get("context_summary", "")
        fp.key_artifacts = d.get("key_artifacts", "")
        ts = d.get("timestamp")
        fp.timestamp = _parse_dt(ts) if ts else datetime.now()
        return fp

@dataclass
class Branch:
    id: str = ""
    name: str = "main"
    strategy: str = ""
    status: str = "active"
    prompt_ids: List[str] = field(default_factory=list)
    parent_branch_id: Optional[str] = None
    fork_point_id: Optional[str] = None
    notes: str = ""
    outcome: str = ""
    merge_insights: str = ""
    session_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    # --- Improvement #9: Soft-delete support ---
    hidden: bool = False

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "strategy": self.strategy,
            "status": self.status,
            "prompt_ids": list(self.prompt_ids),
            "parent_branch_id": self.parent_branch_id,
            "fork_point_id": self.fork_point_id,
            "notes": self.notes,
            "outcome": self.outcome,
            "merge_insights": self.merge_insights,
            "session_id": self.session_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "hidden": self.hidden,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Branch":
        b = cls()
        b.id = d.get("id", str(uuid.uuid4()))
        b.name = d.get("name", "main")
        b.strategy = d.get("strategy", "")
        b.status = d.get("status", "active")
        b.prompt_ids = list(d.get("prompt_ids", []))
        b.parent_branch_id = d.get("parent_branch_id")
        b.fork_point_id = d.get("fork_point_id")
        b.notes = d.get("notes", "")
        b.outcome = d.get("outcome", "")
        b.merge_insights = d.get("merge_insights", "")
        b.session_id = d.get("session_id")
        ca = d.get("created_at")
        b.created_at = _parse_dt(ca) if ca else datetime.now()
        ua = d.get("updated_at")
        b.updated_at = _parse_dt(ua) if ua else datetime.now()
        b.hidden = d.get("hidden", False)
        return b

@dataclass
class ConversationTree:
    id: str = ""
    name: str = ""
    description: str = ""
    status: str = "active"
    branches: List[Branch] = field(default_factory=list)
    fork_points: List[ForkPoint] = field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    tags: List[str] = field(default_factory=list)
    source_conversation_id: Optional[str] = None
    layout_positions: Dict[str, Tuple[float, float]] = field(default_factory=dict)
    # --- Improvement #5: Explicit branch checkout ---
    checked_out_branch_id: Optional[str] = None

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()
        if not self.branches:
            root = Branch(name="main")
            self.branches.append(root)
            self.checked_out_branch_id = root.id

    def get_branch(self, branch_id: str) -> Optional[Branch]:
        for b in self.branches:
            if b.id == branch_id:
                return b
        return None

    def get_root_branch(self) -> Optional[Branch]:
        for b in self.branches:
            if b.parent_branch_id is None:
                return b
        return self.branches[0] if self.branches else None

    def get_child_branches(self, branch_id: str) -> List[Branch]:
        return [b for b in self.branches if b.parent_branch_id == branch_id]

    def get_visible_branches(self, show_hidden: bool = False) -> List[Branch]:
        """Return branches filtered by hidden state."""
        if show_hidden:
            return list(self.branches)
        return [b for b in self.branches if not b.hidden]

    def get_fork_point(self, fp_id: str) -> Optional[ForkPoint]:
        for fp in self.fork_points:
            if fp.id == fp_id:
                return fp
        return None

    def get_checked_out_branch(self) -> Optional[Branch]:
        """Return the currently checked-out branch, or fall back to root."""
        if self.checked_out_branch_id:
            b = self.get_branch(self.checked_out_branch_id)
            if b and not b.hidden:
                return b
        return self.get_root_branch()

    def checkout_branch(self, branch_id: str) -> bool:
        """Set the active/checked-out branch for receiving new prompts."""
        branch = self.get_branch(branch_id)
        if branch is None or branch.hidden:
            return False
        self.checked_out_branch_id = branch_id
        self.updated_at = datetime.now()
        return True

    def add_branch(
        self, name: str, parent_branch_id: str, fork_index: int, trigger: str = "other",
        reason: str = "", context_summary: str = "", key_artifacts: str = "",
        strategy: str = "", session_id: Optional[str] = None,
    ) -> Optional[Branch]:
        parent = self.get_branch(parent_branch_id)
        if parent is None:
            return None

        prompt_at_fork = ""
        inherited_prompts: List[str] = []
        if parent.prompt_ids and 0 <= fork_index < len(parent.prompt_ids):
            prompt_at_fork = parent.prompt_ids[fork_index]
            inherited_prompts = list(parent.prompt_ids[: fork_index + 1])
        elif parent.prompt_ids:
            fork_index = len(parent.prompt_ids) - 1
            prompt_at_fork = parent.prompt_ids[fork_index]
            inherited_prompts = list(parent.prompt_ids)

        new_branch = Branch(
            name=name, strategy=strategy, prompt_ids=inherited_prompts,
            parent_branch_id=parent_branch_id, session_id=session_id,
        )

        fork_point = ForkPoint(
            parent_branch_id=parent_branch_id, child_branch_id=new_branch.id,
            prompt_id=prompt_at_fork, fork_index=fork_index, trigger=trigger,
            reason=reason, context_summary=context_summary, key_artifacts=key_artifacts,
        )
        new_branch.fork_point_id = fork_point.id

        self.branches.append(new_branch)
        self.fork_points.append(fork_point)
        self.updated_at = datetime.now()
        return new_branch

    # --- Improvement #1: Merge workflow ---
    def merge_branch(
        self, source_branch_id: str, target_branch_id: str,
        merge_insights: str = "", include_unique_prompts: bool = True,
    ) -> bool:
        """Merge *source* into *target*.

        - Copies unique prompt IDs from source into target (if requested).
        - Sets source status to 'merged' and records insights.
        - Returns True on success.
        """
        source = self.get_branch(source_branch_id)
        target = self.get_branch(target_branch_id)
        if source is None or target is None:
            return False
        if source.id == target.id:
            return False

        if include_unique_prompts:
            existing = set(target.prompt_ids)
            for pid in source.prompt_ids:
                if pid not in existing:
                    target.prompt_ids.append(pid)
                    existing.add(pid)

        source.status = "merged"
        source.merge_insights = merge_insights
        source.updated_at = datetime.now()
        target.updated_at = datetime.now()
        self.updated_at = datetime.now()
        return True

    def remove_branch(self, branch_id: str) -> bool:
        branch = self.get_branch(branch_id)
        if branch is None or branch.parent_branch_id is None:
            return False

        children = self.get_child_branches(branch_id)
        for child in children:
            self.remove_branch(child.id)

        if branch.fork_point_id:
            self.fork_points = [fp for fp in self.fork_points if fp.id != branch.fork_point_id]

        self.branches = [b for b in self.branches if b.id != branch_id]

        # Fix checkout if we just removed the checked-out branch
        if self.checked_out_branch_id == branch_id:
            root = self.get_root_branch()
            self.checked_out_branch_id = root.id if root else None

        self.updated_at = datetime.now()
        return True

    # --- Improvement #9: Soft-delete ---
    def soft_delete_branch(self, branch_id: str) -> bool:
        """Hide a branch and its descendants without destroying data."""
        branch = self.get_branch(branch_id)
        if branch is None or branch.parent_branch_id is None:
            return False  # Cannot soft-delete root

        def _hide_recursive(bid: str):
            b = self.get_branch(bid)
            if b:
                b.hidden = True
                b.updated_at = datetime.now()
            for child in self.get_child_branches(bid):
                _hide_recursive(child.id)

        _hide_recursive(branch_id)

        if self.checked_out_branch_id == branch_id:
            root = self.get_root_branch()
            self.checked_out_branch_id = root.id if root else None

        self.updated_at = datetime.now()
        return True

    def restore_branch(self, branch_id: str) -> bool:
        """Un-hide a previously soft-deleted branch and its descendants."""
        branch = self.get_branch(branch_id)
        if branch is None:
            return False

        def _restore_recursive(bid: str):
            b = self.get_branch(bid)
            if b:
                b.hidden = False
                b.updated_at = datetime.now()
            for child in self.get_child_branches(bid):
                _restore_recursive(child.id)

        _restore_recursive(branch_id)
        self.updated_at = datetime.now()
        return True

    # --- Improvement #4: Move prompt between branches ---
    def move_prompt(self, prompt_id: str, from_branch_id: str, to_branch_id: str) -> bool:
        """Move a prompt from one branch to another."""
        src = self.get_branch(from_branch_id)
        dst = self.get_branch(to_branch_id)
        if not src or not dst:
            return False
        if prompt_id not in src.prompt_ids:
            return False
        src.prompt_ids.remove(prompt_id)
        if prompt_id not in dst.prompt_ids:
            dst.prompt_ids.append(prompt_id)
        src.updated_at = datetime.now()
        dst.updated_at = datetime.now()
        self.updated_at = datetime.now()
        return True

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "branches": [b.to_dict() for b in self.branches],
            "fork_points": [fp.to_dict() for fp in self.fork_points],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "tags": list(self.tags),
            "source_conversation_id": self.source_conversation_id,
            "checked_out_branch_id": self.checked_out_branch_id,
        }
        d["layout_positions"] = {
            bid: [pos[0], pos[1]] for bid, pos in (self.layout_positions or {}).items()
        }
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ConversationTree":
        tree = cls.__new__(cls)
        tree.id = d.get("id", str(uuid.uuid4()))
        tree.name = d.get("name", "")
        tree.description = d.get("description", "")
        tree.status = d.get("status", "active")
        tree.branches = [Branch.from_dict(b) for b in d.get("branches", [])]
        tree.fork_points = [ForkPoint.from_dict(fp) for fp in d.get("fork_points", [])]
        ca = d.get("created_at")
        tree.created_at = _parse_dt(ca) if ca else datetime.now()
        ua = d.get("updated_at")
        tree.updated_at = _parse_dt(ua) if ua else datetime.now()
        tree.tags = list(d.get("tags", []))
        tree.source_conversation_id = d.get("source_conversation_id")
        tree.checked_out_branch_id = d.get("checked_out_branch_id")
        
        if not tree.branches:
            tree.branches.append(Branch(name="main"))
            
        raw_positions = d.get("layout_positions") or {}
        normalized = {}
        if isinstance(raw_positions, dict):
            for k, v in raw_positions.items():
                p = _norm_pos(v)
                if p is not None:
                    normalized[str(k)] = p
        tree.layout_positions = normalized
        
        if not tree.source_conversation_id:
            for tag in getattr(tree, "tags", []) or []:
                if isinstance(tag, str) and tag.startswith("cid:"):
                    tree.source_conversation_id = tag[4:]
                    break

        # Ensure checkout is valid
        if tree.checked_out_branch_id:
            if not tree.get_branch(tree.checked_out_branch_id):
                tree.checked_out_branch_id = None
        if not tree.checked_out_branch_id and tree.branches:
            root = tree.get_root_branch()
            tree.checked_out_branch_id = root.id if root else tree.branches[0].id

        return tree

# =====================================================================
# Auto-detection helpers
# =====================================================================

def auto_detect_trees(prompt_database) -> List[Dict[str, Any]]:
    groups: Dict[str, List] = {}
    
    # SAFEGUARD: Catch unintialized databases during startup
    if not prompt_database or not hasattr(prompt_database, "prompts"):
        return []
        
    for p in prompt_database.prompts:
        cid = getattr(p, "conversation_id", None) or ""
        if not cid:
            continue
        groups.setdefault(cid, []).append(p)

    suggestions = []
    for cid, prompts in groups.items():
        prompts.sort(key=lambda p: p.timestamp)
        llms = list({p.llm_used for p in prompts if p.llm_used})
        suggestions.append({
            "conversation_id": cid,
            "prompt_count": len(prompts),
            "llms_used": llms,
            "first_timestamp": prompts[0].timestamp,
            "last_timestamp": prompts[-1].timestamp,
            "sample_description": prompts[0].description or prompts[0].prompt_text[:80],
            "prompt_ids": [p.id for p in prompts],
        })

    suggestions.sort(key=lambda s: s["last_timestamp"], reverse=True)
    return suggestions

# =====================================================================
# Persistence
# =====================================================================

def load_conversation_trees(path: Optional[str] = None) -> List[ConversationTree]:
    fpath = path or DEFAULT_TREES_PATH
    if not os.path.exists(fpath):
        return []
    try:
        with open(fpath, "r", encoding="utf-8") as f:
            data = json.load(f)
        return [ConversationTree.from_dict(d) for d in data]
    except Exception as e:
        logger.error("Error loading conversation trees: %s", e)
        return []

def save_conversation_trees(trees: List[ConversationTree], path: Optional[str] = None) -> bool:
    fpath = path or DEFAULT_TREES_PATH
    try:
        data = [t.to_dict() for t in trees]
        with open(fpath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        return True
    except Exception as e:
        logger.error("Error saving conversation trees: %s", e)
        return False
