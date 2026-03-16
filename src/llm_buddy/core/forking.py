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

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


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


def auto_detect_trees(prompt_database) -> List[Dict[str, Any]]:
    groups: Dict[str, List] = {}
    
    # SAFEGUARD: Catch unintialized databases during startup
    if not prompt_database or not hasattr(prompt_database, "prompts"):
        return []
        
    for p in prompt_database.prompts:
        cid = getattr(p, "conversation_id", None) or ""
        if not cid:
            # Backward-compat: group old extension prompts recorded before the
            # conversationId fix by their URL path (stable within a conversation).
            if getattr(p, "source", "") == "Browser Extension" and getattr(p, "url", ""):
                from urllib.parse import urlparse
                parsed = urlparse(p.url)
                cid = parsed.netloc + parsed.path
            else:
                continue
        # Normalize Gemini fallback IDs so proxy ("gemini.google.com/")
        # and extension ("gemini.google.com/app") group together.
        if cid in ("gemini.google.com/", "gemini.google.com"):
            cid = "gemini.google.com/app"
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


def build_tree_with_forks(tree: ConversationTree, prompts, db) -> bool:
    """Detect forks in a list of prompts and build branches accordingly.

    Each prompt is independently placed on the correct branch based on its
    metadata — the function never relies on "checked-out branch" state to
    decide placement.

    Strategies (tried in order for each prompt):
    1. ``parent_message_id`` — if another prompt already shares the same
       parent, fork.  Otherwise, find the branch whose tip was the most
       recently placed prompt (its response generated this parent_message_id)
       and append there.
    2. ``messages_count`` — find the branch whose tip messages_count equals
       ``this_prompt.messages_count - 2``.  If none match but a branch has
       a *higher* count, the user went back → fork.
    3. Fallback — append to the root branch.

    Returns True if the tree was modified.
    """
    if not prompts:
        return False

    existing_ids: set = set()
    for b in tree.branches:
        existing_ids.update(b.prompt_ids)

    new_prompts = [p for p in prompts if p.id not in existing_ids]
    if not new_prompts:
        return False

    root = tree.get_root_branch()
    if root is None:
        return False

    # --- Lookup: parent_message_id → [(branch, prompt_index)] ---
    # Tracks which prompts reply to which parent messages.
    pmid_locs: Dict[str, List[tuple]] = {}

    # --- Lookup: branch_id → messages_count of last prompt ---
    tip_mc: Dict[str, int] = {}

    # --- Lookup: branch_id → timestamp of the most recently placed prompt ---
    # Used to determine which branch a new prompt continues when its
    # parent_message_id is new (i.e. it's a linear continuation, not a fork).
    tip_ts: Dict[str, Any] = {}

    def _index_branch(branch):
        """Add all prompts in *branch* to the lookup maps."""
        for idx, pid in enumerate(branch.prompt_ids):
            p = db.get_prompt(pid)
            if not p:
                continue
            if p.metadata:
                pmid = p.metadata.get("parent_message_id")
                if pmid:
                    pmid_locs.setdefault(pmid, []).append((branch, idx))
                mc = p.metadata.get("messages_count")
                if mc is not None:
                    tip_mc[branch.id] = mc
            # Always track the latest timestamp per branch
            ts = p.timestamp
            if ts and (branch.id not in tip_ts or ts > tip_ts[branch.id]):
                tip_ts[branch.id] = ts

    for branch in tree.branches:
        _index_branch(branch)

    def _append_to_branch(branch, prompt, parent_msg_id, msg_count):
        """Helper: append *prompt* to *branch* and update lookup maps."""
        branch.prompt_ids.append(prompt.id)
        branch.updated_at = prompt.timestamp
        if parent_msg_id:
            pmid_locs.setdefault(parent_msg_id, []).append(
                (branch, len(branch.prompt_ids) - 1))
        if msg_count is not None:
            tip_mc[branch.id] = msg_count
        tip_ts[branch.id] = prompt.timestamp

    modified = False

    for prompt in new_prompts:
        meta = prompt.metadata or {}
        parent_msg_id = meta.get("parent_message_id")
        msg_count = meta.get("messages_count")
        placed = False

        # ----------------------------------------------------------
        # Strategy 1: parent_message_id
        # ----------------------------------------------------------
        if parent_msg_id:
            siblings = pmid_locs.get(parent_msg_id, [])
            if siblings:
                # Another prompt already replies to the same parent → fork.
                # The fork point is one index BEFORE the existing sibling
                # (i.e., the prompt whose *response* is the shared parent).
                sib_branch, sib_idx = siblings[0]
                fork_idx = max(0, sib_idx - 1)

                branch_num = len(tree.branches)
                new_branch = tree.add_branch(
                    name=f"branch-{branch_num}",
                    parent_branch_id=sib_branch.id,
                    fork_index=fork_idx,
                    trigger="auto_detected",
                    reason="Shared parent_message_id",
                )
                if new_branch:
                    new_branch.prompt_ids.append(prompt.id)
                    pmid_locs.setdefault(parent_msg_id, []).append(
                        (new_branch, len(new_branch.prompt_ids) - 1))
                    if msg_count is not None:
                        tip_mc[new_branch.id] = msg_count
                    tip_ts[new_branch.id] = prompt.timestamp
                    modified = True
                    placed = True
            else:
                # No sibling — this parent_message_id is new.  This prompt
                # is a linear continuation of whichever branch's tip prompt
                # generated the response.  Since we don't store response
                # message IDs, we use the heuristic: the branch whose tip
                # was placed most recently (chronologically) before this
                # prompt is the one the user is currently on.
                if tip_ts:
                    best_branch = None
                    best_ts = None
                    for branch in tree.branches:
                        ts = tip_ts.get(branch.id)
                        if ts is not None and ts < prompt.timestamp:
                            if best_ts is None or ts > best_ts:
                                best_ts = ts
                                best_branch = branch
                    if best_branch is not None:
                        _append_to_branch(best_branch, prompt,
                                          parent_msg_id, msg_count)
                        modified = True
                        placed = True

        # ----------------------------------------------------------
        # Strategy 2: messages_count
        # ----------------------------------------------------------
        if not placed and msg_count is not None:
            # Find a branch whose tip messages_count == msg_count - 2.
            # That branch is the natural linear continuation target.
            continuation_branch = None
            for branch in tree.branches:
                btmc = tip_mc.get(branch.id)
                if btmc is not None and btmc == msg_count - 2:
                    continuation_branch = branch
                    break

            if continuation_branch is not None:
                _append_to_branch(continuation_branch, prompt,
                                  parent_msg_id, msg_count)
                modified = True
                placed = True
            else:
                # No branch has the expected tip count.
                # If msg_count is LESS than the highest tip, user went back.
                max_mc = max(tip_mc.values()) if tip_mc else 0
                if max_mc > 0 and msg_count <= max_mc:
                    # Find the fork point: the branch and prompt whose
                    # messages_count is closest to (but <=) msg_count - 2.
                    best_branch = None
                    best_idx = 0
                    best_diff = float("inf")
                    target_mc = msg_count - 2  # the prompt we're replying to
                    for branch in tree.branches:
                        for idx, pid in enumerate(branch.prompt_ids):
                            p = db.get_prompt(pid)
                            if p and p.metadata:
                                p_mc = p.metadata.get("messages_count")
                                if p_mc is not None and p_mc <= target_mc:
                                    diff = target_mc - p_mc
                                    if diff < best_diff:
                                        best_diff = diff
                                        best_branch = branch
                                        best_idx = idx

                    if best_branch is not None:
                        # Check if best_idx is the tip — if so, just append
                        if best_idx == len(best_branch.prompt_ids) - 1:
                            _append_to_branch(best_branch, prompt,
                                              parent_msg_id, msg_count)
                            modified = True
                            placed = True
                        else:
                            # Fork from best_idx
                            branch_num = len(tree.branches)
                            new_branch = tree.add_branch(
                                name=f"branch-{branch_num}",
                                parent_branch_id=best_branch.id,
                                fork_index=best_idx,
                                trigger="auto_detected",
                                reason="messages_count regression",
                            )
                            if new_branch:
                                new_branch.prompt_ids.append(prompt.id)
                                tip_mc[new_branch.id] = msg_count
                                if parent_msg_id:
                                    pmid_locs.setdefault(
                                        parent_msg_id, []).append(
                                        (new_branch,
                                         len(new_branch.prompt_ids) - 1))
                                tip_ts[new_branch.id] = prompt.timestamp
                                modified = True
                                placed = True

        # ----------------------------------------------------------
        # Fallback: append to root
        # ----------------------------------------------------------
        if not placed:
            _append_to_branch(root, prompt, parent_msg_id, msg_count)
            modified = True

    if modified:
        tree.updated_at = new_prompts[-1].timestamp

    return modified

