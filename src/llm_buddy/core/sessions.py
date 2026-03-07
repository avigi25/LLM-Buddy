"""
Research session model and persistence for LLM Buddy.

A *research session* is a named, bounded period of work (e.g.
"eADR Cycle 3: Agent Independence Testing") that groups prompts,
file changes, eADR notes, and backups into a coherent unit.

On session close the tool auto-generates a structured summary that
serves as an exportable "methods appendix" for each iteration cycle.
"""

import json
import logging
import os
import uuid
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from llm_buddy.core.eadr import load_eadr_notes

logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(os.getcwd(), "data")
os.makedirs(DATA_DIR, exist_ok=True)

# Update the default:
DEFAULT_SESSIONS_PATH = os.path.join(DATA_DIR, "sessions.json")


# =====================================================================
# Data model
# =====================================================================

@dataclass
class ResearchSession:
    """A single research session.

    Status lifecycle: ``active`` → ``paused`` ↔ ``active`` → ``completed``

    When paused, ``paused_elapsed`` accumulates the seconds of active
    work so far and ``paused_at`` records when the pause began.  On
    resume, those are folded back into the running total.
    """

    id: str = ""
    name: str = ""
    project: str = ""
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    status: str = "active"  # "active" | "paused" | "completed"
    start_snapshot: Dict[str, Any] = field(default_factory=dict)
    end_snapshot: Optional[Dict[str, Any]] = None
    summary: Optional[Dict[str, Any]] = None
    notes: str = ""
    # Pause tracking: accumulated active seconds before the current
    # pause, and the timestamp of the most recent pause.
    paused_elapsed: float = 0.0
    paused_at: Optional[datetime] = None

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())
        if self.start_time is None:
            self.start_time = datetime.now()

    # -- pause / resume ------------------------------------------------

    def pause(self) -> None:
        """Pause a running session, freezing the elapsed clock."""
        if self.status != "active":
            return
        now = datetime.now()
        # Add the time since start (or last resume) to the accumulator
        ref = self.paused_at or self.start_time or now
        # On first pause, ref == start_time, so this is total active so far.
        # After a resume, paused_at is cleared and start_time stays
        # the same, so we instead track via _active_seconds_since_resume.
        self.paused_elapsed = self.active_seconds
        self.paused_at = now
        self.status = "paused"

    def resume(self) -> None:
        """Resume a paused session."""
        if self.status != "paused":
            return
        self.paused_at = None
        # Shift start_time forward so that (now - start_time) matches
        # the real active duration stored in paused_elapsed.
        # On next tick: active_seconds = paused_elapsed + (now - start_time)
        # So we want (now - new_start_time) == 0 at this moment.
        self.start_time = datetime.now()
        self.status = "active"

    @property
    def active_seconds(self) -> float:
        """Total *active* (un-paused) seconds for this session."""
        if self.start_time is None:
            return self.paused_elapsed
        if self.status == "paused":
            # Frozen: return the value stored at pause time
            return self.paused_elapsed
        if self.status == "completed":
            end = self.end_time or datetime.now()
            return self.paused_elapsed + (end - self.start_time).total_seconds()
        # Running
        return self.paused_elapsed + (
            datetime.now() - self.start_time).total_seconds()

    # -- serialisation -------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serialisable dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "project": self.project,
            "start_time": self.start_time.isoformat()
                          if self.start_time else None,
            "end_time": self.end_time.isoformat()
                        if self.end_time else None,
            "status": self.status,
            "start_snapshot": self.start_snapshot,
            "end_snapshot": self.end_snapshot,
            "summary": self.summary,
            "notes": self.notes,
            "paused_elapsed": self.paused_elapsed,
            "paused_at": self.paused_at.isoformat()
                         if self.paused_at else None,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ResearchSession":
        """Create from dictionary."""
        session = cls()
        session.id = d.get("id", str(uuid.uuid4()))
        session.name = d.get("name", "")
        session.project = d.get("project", "")
        session.status = d.get("status", "completed")
        session.start_snapshot = d.get("start_snapshot", {})
        session.end_snapshot = d.get("end_snapshot")
        session.summary = d.get("summary")
        session.notes = d.get("notes", "")
        session.paused_elapsed = d.get("paused_elapsed", 0.0)

        st = d.get("start_time")
        session.start_time = _parse_dt(st) if st else datetime.now()
        et = d.get("end_time")
        session.end_time = _parse_dt(et) if et else None
        pa = d.get("paused_at")
        session.paused_at = _parse_dt(pa) if pa else None

        return session

    @property
    def duration_str(self) -> str:
        """Human-readable *active* duration (excludes paused time)."""
        total_secs = int(self.active_seconds)
        if total_secs < 0:
            return "\u2014"
        hours, rem = divmod(total_secs, 3600)
        mins, secs = divmod(rem, 60)
        if hours:
            return f"{hours}h {mins}m"
        if mins:
            return f"{mins}m {secs}s"
        return f"{secs}s"

    @property
    def is_running(self) -> bool:
        """True if the session is active (not paused, not completed)."""
        return self.status == "active"


# =====================================================================
# Persistence
# =====================================================================

def load_sessions(path: Optional[str] = None) -> List[ResearchSession]:
    """Load all sessions from JSON file."""
    fpath = path or DEFAULT_SESSIONS_PATH
    if not os.path.exists(fpath):
        return []
    try:
        with open(fpath, "r", encoding="utf-8") as f:
            data = json.load(f)
        return [ResearchSession.from_dict(d) for d in data]
    except Exception as e:
        logger.error("Error loading sessions: %s", e)
        return []


def save_sessions(sessions: List[ResearchSession],
                  path: Optional[str] = None) -> bool:
    """Save all sessions to JSON file."""
    fpath = path or DEFAULT_SESSIONS_PATH
    try:
        data = [s.to_dict() for s in sessions]
        with open(fpath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        return True
    except Exception as e:
        logger.error("Error saving sessions: %s", e)
        return False


def get_active_session(
        sessions: List[ResearchSession]) -> Optional[ResearchSession]:
    """Return the currently active or paused session, if any."""
    for s in sessions:
        if s.status in ("active", "paused"):
            return s
    return None


# =====================================================================
# Snapshot & diff
# =====================================================================

def capture_snapshot(prompt_db, eadr_path=None,
                     backup_config=None) -> Dict[str, Any]:
    """Capture the current state for later comparison.

    Parameters
    ----------
    prompt_db : PromptDatabase instance
    eadr_path : path to eadr_notes.json (or None for default)
    backup_config : AutoBackupConfig instance (or None)
    """
    prompt_ids = [p.id for p in prompt_db.prompts]

    notes = []
    try:
        notes = load_eadr_notes(eadr_path)
    except Exception:
        pass

    note_timestamps = [n.get("timestamp", "") for n in notes]

    file_hashes: Dict[str, Any] = {}
    if backup_config and hasattr(backup_config, "file_hashes"):
        file_hashes = dict(backup_config.file_hashes)

    return {
        "prompt_count": len(prompt_ids),
        "prompt_ids": prompt_ids,
        "note_count": len(notes),
        "note_timestamps": note_timestamps,
        "file_hashes": file_hashes,
        "timestamp": datetime.now().isoformat(),
    }


def compute_session_diff(start_snapshot: Dict[str, Any],
                         end_snapshot: Dict[str, Any],
                         prompt_db) -> Dict[str, Any]:
    """Compute what changed between start and end snapshots.

    Returns a dict with counts and lists suitable for summary
    generation.
    """
    start_ids = set(start_snapshot.get("prompt_ids", []))
    end_ids = set(end_snapshot.get("prompt_ids", []))
    new_ids = end_ids - start_ids

    # Gather details from the prompts that were added this session
    llm_counter: Counter = Counter()
    total_prompt_tokens = 0
    total_response_tokens = 0
    for p in prompt_db.prompts:
        if p.id in new_ids:
            llm_counter[p.llm_used] += 1
            total_prompt_tokens += len(p.prompt_text or "")
            total_response_tokens += len(
                getattr(p, "response_text", "") or "")

    # File changes
    start_hashes = start_snapshot.get("file_hashes", {})
    end_hashes = end_snapshot.get("file_hashes", {})
    files_changed = []
    for fp in end_hashes:
        if end_hashes.get(fp) != start_hashes.get(fp):
            files_changed.append(fp)
    # Also include files that existed in start but not end (deleted)
    for fp in start_hashes:
        if fp not in end_hashes and fp not in files_changed:
            files_changed.append(fp)

    new_note_count = (
        end_snapshot.get("note_count", 0)
        - start_snapshot.get("note_count", 0)
    )

    return {
        "new_prompt_count": len(new_ids),
        "new_prompt_ids": list(new_ids),
        "new_note_count": max(new_note_count, 0),
        "files_changed": files_changed,
        "llms_used": dict(llm_counter),
        "total_prompt_tokens": total_prompt_tokens,
        "total_response_tokens": total_response_tokens,
    }


# =====================================================================
# Markdown summary
# =====================================================================

def generate_session_summary_markdown(
        session: ResearchSession,
        diff: Dict[str, Any]) -> str:
    """Produce an exportable Markdown methods-appendix summary."""
    lines: List[str] = []

    lines.append(f"# Research Session: {session.name}")
    lines.append("")
    lines.append(f"**Project:** {session.project or '(not set)'}")

    start_str = (session.start_time.strftime("%Y-%m-%d %H:%M")
                 if session.start_time else "—")
    end_str = (session.end_time.strftime("%Y-%m-%d %H:%M")
               if session.end_time else "—")
    lines.append(
        f"**Period:** {start_str} \u2013 {end_str} ({session.duration_str})")
    lines.append(f"**Status:** {session.status.capitalize()}")
    lines.append("")

    # Summary
    lines.append("## Summary")
    lines.append("")
    lines.append(
        f"- **Prompts issued:** {diff.get('new_prompt_count', 0)}")
    llms = diff.get("llms_used", {})
    lines.append(
        f"- **LLMs used:** {', '.join(llms.keys()) if llms else 'None'}")
    lines.append(
        f"- **Files changed:** {len(diff.get('files_changed', []))}")
    lines.append(
        f"- **eADR notes created:** {diff.get('new_note_count', 0)}")
    lines.append(
        f"- **Total prompt characters:** "
        f"{diff.get('total_prompt_tokens', 0):,}")
    lines.append(
        f"- **Total response characters:** "
        f"{diff.get('total_response_tokens', 0):,}")
    lines.append("")

    # LLM breakdown table
    if llms:
        lines.append("## LLM Usage Breakdown")
        lines.append("")
        lines.append("| LLM | Prompts |")
        lines.append("|-----|---------|")
        for llm, count in sorted(llms.items(),
                                  key=lambda x: x[1], reverse=True):
            lines.append(f"| {llm} | {count} |")
        lines.append("")

    # Files changed
    changed = diff.get("files_changed", [])
    if changed:
        lines.append("## Files Changed")
        lines.append("")
        for fp in changed:
            lines.append(f"- `{fp}`")
        lines.append("")

    # Session notes
    if session.notes:
        lines.append("## Session Notes")
        lines.append("")
        lines.append(session.notes)
        lines.append("")

    return "\n".join(lines)


# =====================================================================
# Helpers
# =====================================================================

def _parse_dt(s: str) -> Optional[datetime]:
    """Parse an ISO timestamp string into a datetime."""
    if not s:
        return None
    try:
        return datetime.fromisoformat(s)
    except (ValueError, TypeError):
        pass
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%d %H:%M:%S.%f"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None
