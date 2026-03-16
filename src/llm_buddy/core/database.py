"""
Unified SQLite Database for LLM Buddy.

All persistent research data lives in one file (llm_buddy.db):
  prompts, file_associations, eadr_notes, sessions,
  conversation_trees, branches, fork_points, schema_version

On first launch a one-shot migration reads any pre-existing
prompts.db / JSON files and imports their data, then renames them
to *.migrated so they are never re-processed.

JSON is no longer written on every mutation.  Use export_json(path)
for an on-demand snapshot.
"""

import json
import logging
import os
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

from llm_buddy.paths import get_data_dir

_SCHEMA_VERSION = 2


def _default_db_path() -> str:
    return os.path.join(get_data_dir(), "llm_buddy.db")



class PromptRecord:
    """Represents a single prompt used with an LLM."""

    def __init__(self, prompt_text: str = "", llm_used: str = "Unknown",
                 description: str = ""):
        self.id: str = str(uuid.uuid4())
        self.timestamp: datetime = datetime.now()
        self.prompt_text: str = prompt_text
        self.llm_used: str = llm_used
        self.description: str = description
        self.associated_files: List[str] = []
        self.file_changes: Dict[str, int] = {}
        self.retroactive_notes: Dict[str, str] = {}
        self.response_text: str = ""
        self.source: str = "Unknown"
        self.model_name: Optional[str] = None
        self.url: Optional[str] = None
        self.conversation_id: Optional[str] = None
        self.metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for export."""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "prompt_text": self.prompt_text,
            "llm_used": self.llm_used,
            "model": self.llm_used,  # backward compat alias
            "description": self.description,
            "associated_files": self.associated_files,
            "files": self.associated_files,  # backward compat alias
            "file_changes": self.file_changes,
            "retroactive_notes": self.retroactive_notes,
            "source": self.source,
            "response_text": self.response_text,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PromptRecord":
        """Create PromptRecord from dictionary (JSON or SQLite row)."""
        record = cls()
        record.id = data.get("id", str(uuid.uuid4()))
        record.timestamp = _parse_timestamp(data.get("timestamp", ""))
        record.prompt_text = data.get("prompt_text") or ""
        record.llm_used = (data.get("llm_used") or data.get("model")
                           or data.get("llm_name", "Unknown"))
        record.description = data.get("description") or ""
        record.associated_files = (data.get("associated_files")
                                   or data.get("files") or [])
        record.file_changes = data.get("file_changes") or {}
        record.retroactive_notes = data.get("retroactive_notes") or {}
        record.response_text = data.get("response_text") or ""
        record.source = data.get("source") or "Unknown"
        record.model_name = data.get("model_name")
        record.url = data.get("url")
        record.conversation_id = data.get("conversation_id")
        metadata = data.get("metadata")
        if isinstance(metadata, str):
            try:
                record.metadata = json.loads(metadata)
            except (json.JSONDecodeError, TypeError):
                record.metadata = None
        else:
            record.metadata = metadata
        return record


@dataclass
class EadrNote:
    id: int
    timestamp: str
    project: str
    note: str


def _parse_timestamp(timestamp_str: str) -> datetime:
    """Parse a timestamp string with multiple format fallbacks."""
    if not timestamp_str:
        return datetime.now()
    try:
        return datetime.fromisoformat(timestamp_str)
    except (ValueError, TypeError):
        pass
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S.%f",
                "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f"):
        try:
            return datetime.strptime(timestamp_str, fmt)
        except ValueError:
            continue
    logger.warning("Could not parse timestamp: %s", timestamp_str)
    return datetime.now()



def _create_tables(conn: sqlite3.Connection) -> None:
    """Create all tables if they don't exist."""
    conn.executescript("""
        PRAGMA foreign_keys = ON;
        PRAGMA journal_mode = WAL;

        CREATE TABLE IF NOT EXISTS prompts (
            id              TEXT PRIMARY KEY,
            timestamp       TEXT NOT NULL,
            source          TEXT NOT NULL DEFAULT 'Unknown',
            llm_name        TEXT NOT NULL DEFAULT 'Unknown',
            model_name      TEXT,
            prompt_text     TEXT NOT NULL DEFAULT '',
            response_text   TEXT DEFAULT '',
            description     TEXT DEFAULT '',
            url             TEXT,
            conversation_id TEXT,
            metadata        TEXT
        );

        CREATE TABLE IF NOT EXISTS file_associations (
            prompt_id    TEXT,
            file_path    TEXT,
            token_change INTEGER DEFAULT 0,
            PRIMARY KEY (prompt_id, file_path),
            FOREIGN KEY (prompt_id) REFERENCES prompts(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS eadr_notes (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT    NOT NULL,
            project   TEXT    NOT NULL DEFAULT 'Origin',
            note      TEXT    NOT NULL
        );

        CREATE TABLE IF NOT EXISTS sessions (
            id             TEXT PRIMARY KEY,
            name           TEXT NOT NULL,
            project        TEXT,
            status         TEXT NOT NULL DEFAULT 'active',
            start_time     TEXT,
            end_time       TEXT,
            start_snapshot TEXT,
            end_snapshot   TEXT,
            summary        TEXT,
            notes          TEXT,
            paused_elapsed REAL DEFAULT 0,
            paused_at      TEXT
        );

        CREATE TABLE IF NOT EXISTS conversation_trees (
            id                     TEXT PRIMARY KEY,
            name                   TEXT,
            description            TEXT,
            status                 TEXT DEFAULT 'active',
            created_at             TEXT,
            updated_at             TEXT,
            tags                   TEXT,
            source_conversation_id TEXT,
            checked_out_branch_id  TEXT,
            layout_positions       TEXT
        );

        CREATE TABLE IF NOT EXISTS branches (
            id               TEXT PRIMARY KEY,
            tree_id          TEXT NOT NULL
                             REFERENCES conversation_trees(id) ON DELETE CASCADE,
            name             TEXT,
            strategy         TEXT,
            status           TEXT DEFAULT 'active',
            prompt_ids       TEXT,
            parent_branch_id TEXT,
            fork_point_id    TEXT,
            notes            TEXT,
            outcome          TEXT,
            merge_insights   TEXT,
            session_id       TEXT,
            created_at       TEXT,
            updated_at       TEXT,
            hidden           INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS fork_points (
            id               TEXT PRIMARY KEY,
            tree_id          TEXT NOT NULL
                             REFERENCES conversation_trees(id) ON DELETE CASCADE,
            parent_branch_id TEXT,
            child_branch_id  TEXT,
            prompt_id        TEXT,
            fork_index       INTEGER,
            trigger          TEXT,
            reason           TEXT,
            context_summary  TEXT,
            key_artifacts    TEXT,
            timestamp        TEXT
        );

        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER NOT NULL
        );
    """)
    # Seed schema version if empty
    cur = conn.execute("SELECT COUNT(*) FROM schema_version")
    if cur.fetchone()[0] == 0:
        conn.execute("INSERT INTO schema_version VALUES (?)",
                     (_SCHEMA_VERSION,))

    # Add response_text column to existing databases that predate it
    try:
        conn.execute(
            "ALTER TABLE prompts ADD COLUMN response_text TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass  # column already exists

    conn.commit()



def _run_migration(db_path: str) -> None:
    """Import old file-based data into the unified database.

    Runs only once: skipped if ``llm_buddy.db`` already exists or if
    no old files are present.  On success old files are renamed to
    ``*.migrated`` so they are never re-processed.  If the migration
    fails the partially-created db is deleted and old files remain
    intact.
    """
    data_dir = os.path.dirname(db_path) or "."
    old_sqlite = os.path.join(data_dir, "prompts.db")
    old_json = os.path.join(data_dir, "prompts.json")
    eadr_json = os.path.join(data_dir, "eadr_notes.json")
    sessions_json = os.path.join(data_dir, "sessions.json")
    trees_json = os.path.join(data_dir, "conversation_trees.json")

    old_files = [f for f in [old_sqlite, old_json, eadr_json,
                              sessions_json, trees_json]
                 if os.path.exists(f)]
    if not old_files:
        return
    if os.path.exists(db_path):
        return  # already migrated

    logger.info("One-shot migration → %s", db_path)
    try:
        _do_migrate(db_path, old_sqlite, old_json, eadr_json,
                    sessions_json, trees_json)
        for fp in old_files:
            try:
                os.rename(fp, fp + ".migrated")
            except Exception as e:
                logger.warning("Could not rename %s: %s", fp, e)
        logger.info("Migration complete.")
    except Exception as e:
        logger.error("Migration failed: %s", e, exc_info=True)
        if os.path.exists(db_path):
            try:
                os.remove(db_path)
            except Exception:
                pass


def _do_migrate(db_path: str, old_sqlite: str, old_json: str,
                eadr_json: str, sessions_json: str,
                trees_json: str) -> None:
    os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    _create_tables(conn)
    c = conn.cursor()

    try:
        if os.path.exists(old_sqlite):
            try:
                src = sqlite3.connect(old_sqlite)
                src.row_factory = sqlite3.Row
                rows = src.execute("SELECT * FROM prompts").fetchall()
                assoc = src.execute(
                    "SELECT * FROM file_associations").fetchall()
                src.close()
                for row in rows:
                    d = dict(row)
                    c.execute("""
                        INSERT OR IGNORE INTO prompts
                        (id, timestamp, source, llm_name, model_name,
                         prompt_text, response_text, description, url,
                         conversation_id, metadata)
                        VALUES (:id, :timestamp, :source, :llm_name,
                                :model_name, :prompt_text, :response_text,
                                :description, :url, :conversation_id,
                                :metadata)
                    """, {k: d.get(k) for k in (
                        "id", "timestamp", "source", "llm_name",
                        "model_name", "prompt_text", "response_text",
                        "description", "url", "conversation_id", "metadata")})
                for row in assoc:
                    d = dict(row)
                    c.execute("""
                        INSERT OR IGNORE INTO file_associations
                        (prompt_id, file_path, token_change)
                        VALUES (?, ?, ?)
                    """, (d["prompt_id"], d["file_path"],
                          d.get("token_change", 0)))
                logger.info("Migrated %d prompts from prompts.db",
                            len(rows))
            except Exception as e:
                logger.warning("prompts.db migration error: %s", e)

        if os.path.exists(old_json):
            try:
                with open(old_json, "r", encoding="utf-8") as f:
                    items = json.load(f)
                count = 0
                for item in items:
                    pid = item.get("id")
                    if not pid:
                        continue
                    c.execute("SELECT 1 FROM prompts WHERE id = ?", (pid,))
                    if c.fetchone():
                        continue
                    c.execute("""
                        INSERT OR IGNORE INTO prompts
                        (id, timestamp, source, llm_name, model_name,
                         prompt_text, response_text, description, url,
                         conversation_id, metadata)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (pid,
                          item.get("timestamp", datetime.now().isoformat()),
                          item.get("source", "Unknown"),
                          item.get("llm_used") or item.get("model",
                                                            "Unknown"),
                          item.get("model_name"),
                          item.get("prompt_text", ""),
                          item.get("response_text", ""),
                          item.get("description", ""),
                          item.get("url"),
                          item.get("conversation_id"),
                          json.dumps(item["metadata"])
                          if item.get("metadata") else None))
                    count += 1
                logger.info("Migrated %d unique prompts from prompts.json",
                            count)
            except Exception as e:
                logger.warning("prompts.json migration error: %s", e)

        if os.path.exists(eadr_json):
            try:
                with open(eadr_json, "r", encoding="utf-8") as f:
                    notes = json.load(f)
                for n in notes:
                    c.execute("""
                        INSERT INTO eadr_notes (timestamp, project, note)
                        VALUES (?, ?, ?)
                    """, (n.get("timestamp",
                                datetime.now().strftime(
                                    "%Y-%m-%d %H:%M:%S")),
                          n.get("project", "Origin"),
                          n.get("note", "")))
                logger.info("Migrated %d eADR notes", len(notes))
            except Exception as e:
                logger.warning("eadr_notes.json migration error: %s", e)

        if os.path.exists(sessions_json):
            try:
                with open(sessions_json, "r", encoding="utf-8") as f:
                    sessions = json.load(f)
                for s in sessions:
                    c.execute("""
                        INSERT OR IGNORE INTO sessions
                        (id, name, project, status, start_time, end_time,
                         start_snapshot, end_snapshot, summary, notes,
                         paused_elapsed, paused_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (s.get("id", str(uuid.uuid4())),
                          s.get("name", ""),
                          s.get("project", ""),
                          s.get("status", "completed"),
                          s.get("start_time"),
                          s.get("end_time"),
                          json.dumps(s["start_snapshot"])
                          if s.get("start_snapshot") else None,
                          json.dumps(s["end_snapshot"])
                          if s.get("end_snapshot") else None,
                          json.dumps(s["summary"])
                          if s.get("summary") else None,
                          s.get("notes", ""),
                          s.get("paused_elapsed", 0.0),
                          s.get("paused_at")))
                logger.info("Migrated %d sessions", len(sessions))
            except Exception as e:
                logger.warning("sessions.json migration error: %s", e)

        if os.path.exists(trees_json):
            try:
                with open(trees_json, "r", encoding="utf-8") as f:
                    trees = json.load(f)
                for t in trees:
                    tid = t.get("id", str(uuid.uuid4()))
                    c.execute("""
                        INSERT OR IGNORE INTO conversation_trees
                        (id, name, description, status, created_at,
                         updated_at, tags, source_conversation_id,
                         checked_out_branch_id, layout_positions)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (tid,
                          t.get("name", ""),
                          t.get("description", ""),
                          t.get("status", "active"),
                          t.get("created_at"),
                          t.get("updated_at"),
                          json.dumps(t.get("tags", [])),
                          t.get("source_conversation_id"),
                          t.get("checked_out_branch_id"),
                          json.dumps(t.get("layout_positions", {}))))
                    for b in t.get("branches", []):
                        c.execute("""
                            INSERT OR IGNORE INTO branches
                            (id, tree_id, name, strategy, status,
                             prompt_ids, parent_branch_id, fork_point_id,
                             notes, outcome, merge_insights, session_id,
                             created_at, updated_at, hidden)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                                    ?, ?, ?, ?)
                        """, (b.get("id", str(uuid.uuid4())),
                              tid,
                              b.get("name", "main"),
                              b.get("strategy", ""),
                              b.get("status", "active"),
                              json.dumps(b.get("prompt_ids", [])),
                              b.get("parent_branch_id"),
                              b.get("fork_point_id"),
                              b.get("notes", ""),
                              b.get("outcome", ""),
                              b.get("merge_insights", ""),
                              b.get("session_id"),
                              b.get("created_at"),
                              b.get("updated_at"),
                              1 if b.get("hidden") else 0))
                    for fp in t.get("fork_points", []):
                        c.execute("""
                            INSERT OR IGNORE INTO fork_points
                            (id, tree_id, parent_branch_id,
                             child_branch_id, prompt_id, fork_index,
                             trigger, reason, context_summary,
                             key_artifacts, timestamp)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (fp.get("id", str(uuid.uuid4())),
                              tid,
                              fp.get("parent_branch_id"),
                              fp.get("child_branch_id"),
                              fp.get("prompt_id"),
                              fp.get("fork_index", 0),
                              fp.get("trigger", "other"),
                              fp.get("reason", ""),
                              fp.get("context_summary", ""),
                              fp.get("key_artifacts", ""),
                              fp.get("timestamp")))
                logger.info("Migrated %d conversation trees", len(trees))
            except Exception as e:
                logger.warning(
                    "conversation_trees.json migration error: %s", e)

        conn.commit()
    except Exception:
        conn.rollback()
        conn.close()
        raise
    conn.close()



class PromptDatabase:
    """
    Unified database for storing all LLM Buddy research data.

    Supports two usage modes:
    - **Recorder mode** (proxy, MCP, API): call add_prompt() directly.
    - **GUI mode**: call load() to populate self.prompts, then use the
      in-memory list for display.  Mutations sync back to SQLite.
    """

    def __init__(self, db_path: Optional[str] = None):
        self.sqlite_path = db_path or _default_db_path()
        self.prompts: List[PromptRecord] = []
        self.active_prompt: Optional[PromptRecord] = None
        _run_migration(self.sqlite_path)
        self._initialize_db()

    def _initialize_db(self) -> None:
        db_dir = os.path.dirname(self.sqlite_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
        conn = sqlite3.connect(self.sqlite_path)
        _create_tables(conn)
        conn.close()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.sqlite_path)
        conn.execute("PRAGMA foreign_keys = ON")
        conn.row_factory = sqlite3.Row
        return conn

    def add_prompt(self, prompt_text: str = "",
                   llm_name: str = "Unknown",
                   source: str = "Unknown",
                   model_name: Optional[str] = None,
                   description: Optional[str] = None,
                   url: Optional[str] = None,
                   conversation_id: Optional[str] = None,
                   metadata: Optional[Dict[str, Any]] = None,
                   associated_files: Optional[List[str]] = None,
                   prompt_record: Optional[PromptRecord] = None,
                   ) -> str:
        """Add a new prompt; returns the prompt ID."""
        if prompt_record is not None:
            rec = prompt_record
        else:
            rec = PromptRecord(prompt_text, llm_name, description or "")
            rec.source = source
            rec.model_name = model_name
            rec.url = url
            rec.conversation_id = conversation_id
            rec.metadata = metadata
            if associated_files:
                rec.associated_files = list(associated_files)

        self._insert_sqlite(rec)
        self.prompts.append(rec)
        self.active_prompt = rec
        return rec.id

    def get_prompt(self, prompt_id: str) -> Optional[PromptRecord]:
        for p in self.prompts:
            if p.id == prompt_id:
                return p
        return self._get_from_sqlite(prompt_id)

    def get_recent_prompts(self, hours: int = 24) -> List[PromptRecord]:
        cutoff = datetime.now() - timedelta(hours=hours)
        return [p for p in self.prompts if p.timestamp > cutoff]

    def get_prompts_for_file(self, file_path: str) -> List[PromptRecord]:
        return [p for p in self.prompts
                if file_path in p.associated_files]

    def associate_file_with_active_prompt(self, file_path: str,
                                          token_change: int = 0) -> bool:
        if (self.active_prompt
                and file_path not in self.active_prompt.associated_files):
            self.active_prompt.associated_files.append(file_path)
            self.active_prompt.file_changes[file_path] = token_change
            self.save()
            return True
        return False

    def associate_files_with_prompt(self, prompt_id: str,
                                    file_paths: List[str],
                                    token_change: int = 0) -> bool:
        try:
            conn = self._connect()
            for fp in file_paths:
                conn.execute("""
                    INSERT OR REPLACE INTO file_associations
                    (prompt_id, file_path, token_change) VALUES (?, ?, ?)
                """, (prompt_id, fp, token_change))
            conn.commit()
            conn.close()
            rec = self.get_prompt(prompt_id)
            if rec:
                for fp in file_paths:
                    if fp not in rec.associated_files:
                        rec.associated_files.append(fp)
                        rec.file_changes[fp] = token_change
            return True
        except Exception as e:
            logger.error("Error associating files: %s", e)
            return False

    def update_response(self, prompt_id: str,
                        response_text: str) -> bool:
        try:
            conn = self._connect()
            conn.execute(
                "UPDATE prompts SET response_text = ? WHERE id = ?",
                (response_text, prompt_id))
            conn.commit()
            conn.close()
            for p in self.prompts:
                if p.id == prompt_id:
                    p.response_text = response_text
                    break
            return True
        except Exception as e:
            logger.error("Error updating response: %s", e)
            return False

    def update_conversation_id(self, prompt_id: str,
                               conversation_id: str) -> bool:
        """Update the conversation_id for a previously recorded prompt."""
        try:
            conn = self._connect()
            conn.execute(
                "UPDATE prompts SET conversation_id = ? WHERE id = ?",
                (conversation_id, prompt_id))
            conn.commit()
            conn.close()
            for p in self.prompts:
                if p.id == prompt_id:
                    p.conversation_id = conversation_id
                    break
            return True
        except Exception as e:
            logger.error("Error updating conversation_id: %s", e)
            return False

    def delete_prompt(self, prompt_id: str) -> bool:
        try:
            conn = self._connect()
            conn.execute("DELETE FROM file_associations WHERE prompt_id = ?",
                         (prompt_id,))
            conn.execute("DELETE FROM prompts WHERE id = ?", (prompt_id,))
            conn.commit()
            conn.close()
            self.prompts = [p for p in self.prompts if p.id != prompt_id]
            return True
        except Exception as e:
            logger.error("Error deleting prompt: %s", e)
            return False

    def clear_active_prompt(self) -> None:
        self.active_prompt = None

    def search_prompts(self, search_text: Optional[str] = None,
                       llm_name: Optional[str] = None,
                       source: Optional[str] = None,
                       file_path: Optional[str] = None,
                       start_date: Optional[str] = None,
                       end_date: Optional[str] = None,
                       limit: int = 100) -> List[Dict[str, Any]]:
        try:
            conn = self._connect()
            query = "SELECT DISTINCT p.* FROM prompts p"
            params: List[Any] = []
            where: List[str] = []

            if file_path:
                query += " LEFT JOIN file_associations fa ON p.id = fa.prompt_id"
                where.append("fa.file_path LIKE ?")
                params.append(f"%{file_path}%")
            if search_text:
                where.append(
                    "(p.prompt_text LIKE ? OR p.description LIKE ?)")
                params.extend([f"%{search_text}%", f"%{search_text}%"])
            if llm_name:
                where.append("p.llm_name = ?")
                params.append(llm_name)
            if source:
                where.append("p.source = ?")
                params.append(source)
            if start_date:
                where.append("p.timestamp >= ?")
                params.append(start_date)
            if end_date:
                where.append("p.timestamp <= ?")
                params.append(end_date)

            if where:
                query += " WHERE " + " AND ".join(where)
            query += " ORDER BY p.timestamp DESC LIMIT ?"
            params.append(limit)

            results = []
            for row in conn.execute(query, params).fetchall():
                d = dict(row)
                if d.get("metadata"):
                    try:
                        d["metadata"] = json.loads(d["metadata"])
                    except (json.JSONDecodeError, TypeError):
                        pass
                file_rows = conn.execute(
                    "SELECT file_path, token_change FROM file_associations "
                    "WHERE prompt_id = ?", (d["id"],)).fetchall()
                d["associated_files"] = [r["file_path"] for r in file_rows]
                d["file_changes"] = {r["file_path"]: r["token_change"]
                                     for r in file_rows}
                results.append(d)
            conn.close()
            return results
        except Exception as e:
            logger.error("Error searching prompts: %s", e)
            return []

    def get_prompts_count(self) -> int:
        try:
            conn = self._connect()
            count = conn.execute(
                "SELECT COUNT(*) FROM prompts").fetchone()[0]
            conn.close()
            return count
        except Exception as e:
            logger.error("Error getting prompts count: %s", e)
            return len(self.prompts)

    def load(self) -> bool:
        """Load prompts into memory from SQLite."""
        loaded: List[PromptRecord] = []
        try:
            conn = self._connect()
            for row in conn.execute(
                    "SELECT * FROM prompts ORDER BY timestamp").fetchall():
                d = dict(row)
                d["llm_used"] = d.pop("llm_name", "Unknown")
                file_rows = conn.execute(
                    "SELECT file_path, token_change FROM file_associations "
                    "WHERE prompt_id = ?", (d["id"],)).fetchall()
                d["associated_files"] = [r["file_path"] for r in file_rows]
                d["file_changes"] = {r["file_path"]: r["token_change"]
                                     for r in file_rows}
                loaded.append(PromptRecord.from_dict(d))
            conn.close()
        except Exception as e:
            logger.error("Error loading from SQLite: %s", e)

        self.prompts = loaded
        logger.info("Loaded %d prompts", len(self.prompts))
        return len(self.prompts) > 0

    def save(self) -> bool:
        """Persist all in-memory prompts to SQLite."""
        try:
            conn = self._connect()
            for rec in self.prompts:
                conn.execute("""
                    INSERT OR REPLACE INTO prompts
                    (id, timestamp, source, llm_name, model_name,
                     prompt_text, response_text, description, url,
                     conversation_id, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (rec.id, rec.timestamp.isoformat(), rec.source,
                      rec.llm_used, rec.model_name, rec.prompt_text,
                      rec.response_text, rec.description, rec.url,
                      rec.conversation_id,
                      json.dumps(rec.metadata) if rec.metadata else None))
                for fp in rec.associated_files:
                    conn.execute("""
                        INSERT OR REPLACE INTO file_associations
                        (prompt_id, file_path, token_change) VALUES (?, ?, ?)
                    """, (rec.id, fp, rec.file_changes.get(fp, 0)))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error("Error saving prompt database: %s", e)
            return False

    def export_json(self, path: str) -> bool:
        """Export all prompts to a JSON file (on-demand snapshot)."""
        try:
            data = [rec.to_dict() for rec in self.prompts]
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
            return True
        except Exception as e:
            logger.error("Error exporting JSON: %s", e)
            return False

    def import_from_json(self, json_path: Optional[str] = None) -> int:
        """Import prompts from a JSON file into SQLite."""
        if not json_path or not os.path.exists(json_path):
            return 0
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            count = 0
            for item in data:
                pid = item.get("id")
                if pid and not any(p.id == pid for p in self.prompts):
                    rec = PromptRecord.from_dict(item)
                    self._insert_sqlite(rec)
                    self.prompts.append(rec)
                    count += 1
            return count
        except Exception as e:
            logger.error("Error importing from JSON: %s", e)
            return 0

    def _insert_sqlite(self, rec: PromptRecord) -> None:
        try:
            conn = self._connect()
            conn.execute("""
                INSERT OR REPLACE INTO prompts
                (id, timestamp, source, llm_name, model_name,
                 prompt_text, response_text, description, url,
                 conversation_id, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (rec.id, rec.timestamp.isoformat(), rec.source,
                  rec.llm_used, rec.model_name, rec.prompt_text,
                  rec.response_text, rec.description, rec.url,
                  rec.conversation_id,
                  json.dumps(rec.metadata) if rec.metadata else None))
            for fp in rec.associated_files:
                conn.execute("""
                    INSERT OR REPLACE INTO file_associations
                    (prompt_id, file_path, token_change) VALUES (?, ?, ?)
                """, (rec.id, fp, rec.file_changes.get(fp, 0)))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error("Error inserting to SQLite: %s", e)

    def _get_from_sqlite(self, prompt_id: str) -> Optional[PromptRecord]:
        try:
            conn = self._connect()
            row = conn.execute(
                "SELECT * FROM prompts WHERE id = ?",
                (prompt_id,)).fetchone()
            if not row:
                conn.close()
                return None
            d = dict(row)
            d["llm_used"] = d.pop("llm_name", "Unknown")
            file_rows = conn.execute(
                "SELECT file_path, token_change FROM file_associations "
                "WHERE prompt_id = ?", (prompt_id,)).fetchall()
            d["associated_files"] = [r["file_path"] for r in file_rows]
            d["file_changes"] = {r["file_path"]: r["token_change"]
                                 for r in file_rows}
            conn.close()
            return PromptRecord.from_dict(d)
        except Exception as e:
            logger.error("Error getting prompt from SQLite: %s", e)
            return None

    def add_eadr_note(self, note: str,
                      project: str = "Origin") -> int:
        """Insert a new eADR note; returns the new row id."""
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            conn = self._connect()
            cur = conn.execute(
                "INSERT INTO eadr_notes (timestamp, project, note) "
                "VALUES (?, ?, ?)",
                (ts, project, note))
            note_id = cur.lastrowid
            conn.commit()
            conn.close()
            return note_id
        except Exception as e:
            logger.error("Error adding eADR note: %s", e)
            return -1

    def get_eadr_notes(self,
                       project: Optional[str] = None) -> List[EadrNote]:
        """Return all eADR notes, newest first."""
        try:
            conn = self._connect()
            if project:
                rows = conn.execute(
                    "SELECT id, timestamp, project, note FROM eadr_notes "
                    "WHERE project = ? ORDER BY id DESC",
                    (project,)).fetchall()
            else:
                rows = conn.execute(
                    "SELECT id, timestamp, project, note FROM eadr_notes "
                    "ORDER BY id DESC").fetchall()
            conn.close()
            return [EadrNote(id=r["id"], timestamp=r["timestamp"],
                             project=r["project"], note=r["note"])
                    for r in rows]
        except Exception as e:
            logger.error("Error loading eADR notes: %s", e)
            return []

    def delete_eadr_note(self, note_id: int) -> bool:
        """Delete an eADR note by its database ID."""
        try:
            conn = self._connect()
            conn.execute("DELETE FROM eadr_notes WHERE id = ?", (note_id,))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error("Error deleting eADR note: %s", e)
            return False

    def add_session(self, session) -> str:
        """Insert a new ResearchSession; returns its ID."""
        try:
            conn = self._connect()
            d = session.to_dict()
            conn.execute("""
                INSERT OR REPLACE INTO sessions
                (id, name, project, status, start_time, end_time,
                 start_snapshot, end_snapshot, summary, notes,
                 paused_elapsed, paused_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (d["id"], d["name"], d["project"], d["status"],
                  d["start_time"], d["end_time"],
                  json.dumps(d["start_snapshot"])
                  if d.get("start_snapshot") else None,
                  json.dumps(d["end_snapshot"])
                  if d.get("end_snapshot") else None,
                  json.dumps(d["summary"])
                  if d.get("summary") else None,
                  d["notes"], d["paused_elapsed"], d["paused_at"]))
            conn.commit()
            conn.close()
            return d["id"]
        except Exception as e:
            logger.error("Error adding session: %s", e)
            return ""

    def update_session(self, session) -> bool:
        """Upsert a ResearchSession (used for pause/resume/end)."""
        return bool(self.add_session(session))

    def get_sessions(self) -> list:
        """Return all sessions as ResearchSession objects."""
        from llm_buddy.core.sessions import ResearchSession
        try:
            conn = self._connect()
            rows = conn.execute(
                "SELECT * FROM sessions ORDER BY start_time").fetchall()
            conn.close()
            sessions = []
            for row in rows:
                d = dict(row)
                for key in ("start_snapshot", "end_snapshot", "summary"):
                    if d.get(key):
                        try:
                            d[key] = json.loads(d[key])
                        except (json.JSONDecodeError, TypeError):
                            d[key] = None
                sessions.append(ResearchSession.from_dict(d))
            return sessions
        except Exception as e:
            logger.error("Error loading sessions: %s", e)
            return []

    def get_active_session(self):
        """Return the currently active or paused session, or None."""
        for s in self.get_sessions():
            if s.status in ("active", "paused"):
                return s
        return None

    def delete_session(self, session_id: str) -> bool:
        try:
            conn = self._connect()
            conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error("Error deleting session: %s", e)
            return False

    def save_tree(self, tree) -> bool:
        """Upsert a ConversationTree and all its branches/fork_points."""
        try:
            conn = self._connect()
            d = tree.to_dict()
            tid = d["id"]

            # Upsert tree row
            conn.execute("""
                INSERT OR REPLACE INTO conversation_trees
                (id, name, description, status, created_at, updated_at,
                 tags, source_conversation_id, checked_out_branch_id,
                 layout_positions)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (tid, d["name"], d["description"], d["status"],
                  d["created_at"], d["updated_at"],
                  json.dumps(d.get("tags", [])),
                  d.get("source_conversation_id"),
                  d.get("checked_out_branch_id"),
                  json.dumps(d.get("layout_positions", {}))))

            # Replace branches: delete all then re-insert
            conn.execute("DELETE FROM branches WHERE tree_id = ?", (tid,))
            for b in d.get("branches", []):
                conn.execute("""
                    INSERT INTO branches
                    (id, tree_id, name, strategy, status, prompt_ids,
                     parent_branch_id, fork_point_id, notes, outcome,
                     merge_insights, session_id, created_at, updated_at,
                     hidden)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (b["id"], tid, b.get("name", "main"),
                      b.get("strategy", ""), b.get("status", "active"),
                      json.dumps(b.get("prompt_ids", [])),
                      b.get("parent_branch_id"), b.get("fork_point_id"),
                      b.get("notes", ""), b.get("outcome", ""),
                      b.get("merge_insights", ""), b.get("session_id"),
                      b.get("created_at"), b.get("updated_at"),
                      1 if b.get("hidden") else 0))

            # Replace fork_points
            conn.execute("DELETE FROM fork_points WHERE tree_id = ?", (tid,))
            for fp in d.get("fork_points", []):
                conn.execute("""
                    INSERT INTO fork_points
                    (id, tree_id, parent_branch_id, child_branch_id,
                     prompt_id, fork_index, trigger, reason,
                     context_summary, key_artifacts, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (fp["id"], tid, fp.get("parent_branch_id"),
                      fp.get("child_branch_id"), fp.get("prompt_id"),
                      fp.get("fork_index", 0), fp.get("trigger", "other"),
                      fp.get("reason", ""), fp.get("context_summary", ""),
                      fp.get("key_artifacts", ""), fp.get("timestamp")))

            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error("Error saving tree: %s", e)
            return False

    def load_trees(self) -> list:
        """Return all ConversationTree objects."""
        from llm_buddy.core.forking import ConversationTree
        try:
            conn = self._connect()
            tree_rows = conn.execute(
                "SELECT * FROM conversation_trees").fetchall()
            trees = []
            for trow in tree_rows:
                td = dict(trow)
                for key in ("tags", "layout_positions"):
                    if td.get(key):
                        try:
                            td[key] = json.loads(td[key])
                        except (json.JSONDecodeError, TypeError):
                            td[key] = [] if key == "tags" else {}

                branch_rows = conn.execute(
                    "SELECT * FROM branches WHERE tree_id = ?",
                    (td["id"],)).fetchall()
                td["branches"] = []
                for brow in branch_rows:
                    bd = dict(brow)
                    if bd.get("prompt_ids"):
                        try:
                            bd["prompt_ids"] = json.loads(bd["prompt_ids"])
                        except (json.JSONDecodeError, TypeError):
                            bd["prompt_ids"] = []
                    bd["hidden"] = bool(bd.get("hidden", 0))
                    td["branches"].append(bd)

                fp_rows = conn.execute(
                    "SELECT * FROM fork_points WHERE tree_id = ?",
                    (td["id"],)).fetchall()
                td["fork_points"] = [dict(r) for r in fp_rows]

                trees.append(ConversationTree.from_dict(td))
            conn.close()
            return trees
        except Exception as e:
            logger.error("Error loading trees: %s", e)
            return []

    def delete_tree(self, tree_id: str) -> bool:
        try:
            conn = self._connect()
            conn.execute(
                "DELETE FROM conversation_trees WHERE id = ?", (tree_id,))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error("Error deleting tree: %s", e)
            return False
