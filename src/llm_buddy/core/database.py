"""
Unified Prompt Database for LLM Buddy.

Provides PromptRecord and PromptDatabase as the single source of truth
for all prompt storage across the GUI, MCP recorder, proxy recorder,
and Flask API server.

Supports dual storage: SQLite (primary) with JSON backup for backward
compatibility with Claude Desktop integration.
"""

import os
import json
import uuid
import sqlite3
import logging
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(os.getcwd(), "data")
os.makedirs(DATA_DIR, exist_ok=True)

# Update the defaults:
DEFAULT_SQLITE_PATH = os.path.join(DATA_DIR, "prompts.db")
DEFAULT_JSON_PATH = os.path.join(DATA_DIR, "prompts.json")


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
        """Convert to dictionary for JSON storage."""
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

        # Parse timestamp with robust fallback
        timestamp_str = data.get("timestamp", "")
        record.timestamp = _parse_timestamp(timestamp_str)

        record.prompt_text = data.get("prompt_text") or ""
        record.llm_used = data.get("llm_used") or data.get("model") or data.get("llm_name", "Unknown")
        record.description = data.get("description") or ""
        record.associated_files = data.get("associated_files") or data.get("files") or []
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


class PromptDatabase:
    """
    Unified database for storing prompts from all sources.

    Supports two usage modes:
    - **Recorder mode** (proxy, MCP, API): call add_prompt() directly,
      data goes to SQLite + JSON.
    - **GUI mode**: call load() to populate self.prompts list, then use
      the in-memory list for display. Mutations sync back to storage.
    """

    def __init__(self, sqlite_path: Optional[str] = None,
                 json_path: Optional[str] = None):
        self.sqlite_path = sqlite_path or DEFAULT_SQLITE_PATH
        self.json_path = json_path or DEFAULT_JSON_PATH
        self._json_lock = threading.Lock()
        self._migrate_legacy_json()
        self.prompts: List[PromptRecord] = []
        self.active_prompt: Optional[PromptRecord] = None
        self._initialize_db()

    # ------------------------------------------------------------------
    # Legacy migration
    # ------------------------------------------------------------------

    def _migrate_legacy_json(self) -> None:
        """Rename claude_prompts.json -> prompts.json if the old file exists."""
        if self.json_path != DEFAULT_JSON_PATH:
            return  # custom path, don't touch
        legacy = os.path.join(os.path.dirname(self.json_path),
                              "claude_prompts.json")
        if os.path.exists(legacy) and not os.path.exists(self.json_path):
            os.rename(legacy, self.json_path)
            logger.info("Migrated %s -> %s", legacy, self.json_path)

    # ------------------------------------------------------------------
    # Database initialization
    # ------------------------------------------------------------------

    def _initialize_db(self) -> None:
        """Create SQLite tables if they don't exist."""
        db_dir = os.path.dirname(self.sqlite_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)

        conn = sqlite3.connect(self.sqlite_path)
        conn.execute("PRAGMA journal_mode=WAL")
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS prompts (
                id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                source TEXT NOT NULL DEFAULT 'Unknown',
                llm_name TEXT NOT NULL DEFAULT 'Unknown',
                model_name TEXT,
                prompt_text TEXT NOT NULL DEFAULT '',
                response_text TEXT DEFAULT '',
                description TEXT DEFAULT '',
                url TEXT,
                conversation_id TEXT,
                metadata TEXT
            )
        """)
        # Migration: add response_text column to existing databases
        try:
            cursor.execute(
                "ALTER TABLE prompts ADD COLUMN response_text TEXT DEFAULT ''")
        except sqlite3.OperationalError:
            pass  # column already exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS file_associations (
                prompt_id TEXT,
                file_path TEXT,
                token_change INTEGER DEFAULT 0,
                PRIMARY KEY (prompt_id, file_path),
                FOREIGN KEY (prompt_id) REFERENCES prompts(id)
            )
        """)
        conn.commit()
        conn.close()

    # ------------------------------------------------------------------
    # Core CRUD (used by both recorders and GUI)
    # ------------------------------------------------------------------

    def add_prompt(self, prompt_text: str = "", llm_name: str = "Unknown",
                   source: str = "Unknown",
                   model_name: Optional[str] = None,
                   description: Optional[str] = None,
                   url: Optional[str] = None,
                   conversation_id: Optional[str] = None,
                   metadata: Optional[Dict[str, Any]] = None,
                   associated_files: Optional[List[str]] = None,
                   prompt_record: Optional[PromptRecord] = None) -> str:
        """
        Add a new prompt to the database.

        Can be called either with individual fields (recorder style) or
        with a pre-built PromptRecord (GUI style).

        Returns the prompt ID.
        """
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

        # Write to SQLite
        self._insert_sqlite(rec)

        # Write to JSON for backward compatibility
        self._add_to_json(rec)

        # Keep in-memory list in sync
        self.prompts.append(rec)
        self.active_prompt = rec

        return rec.id

    def get_prompt(self, prompt_id: str) -> Optional[PromptRecord]:
        """Get prompt by ID from in-memory list or SQLite."""
        # Try in-memory first
        for p in self.prompts:
            if p.id == prompt_id:
                return p
        # Fallback to SQLite
        return self._get_from_sqlite(prompt_id)

    def get_recent_prompts(self, hours: int = 24) -> List[PromptRecord]:
        """Get prompts from the last N hours."""
        cutoff = datetime.now() - timedelta(hours=hours)
        return [p for p in self.prompts if p.timestamp > cutoff]

    def get_prompts_for_file(self, file_path: str) -> List[PromptRecord]:
        """Get all prompts that affected a specific file."""
        return [p for p in self.prompts if file_path in p.associated_files]

    def associate_file_with_active_prompt(self, file_path: str,
                                          token_change: int = 0) -> bool:
        """Associate a file with the currently active prompt."""
        if self.active_prompt and file_path not in self.active_prompt.associated_files:
            self.active_prompt.associated_files.append(file_path)
            self.active_prompt.file_changes[file_path] = token_change
            self.save()
            return True
        return False

    def associate_files_with_prompt(self, prompt_id: str,
                                     file_paths: List[str],
                                     token_change: int = 0) -> bool:
        """Associate multiple files with a prompt by ID."""
        try:
            conn = sqlite3.connect(self.sqlite_path)
            cursor = conn.cursor()
            for fp in file_paths:
                cursor.execute("""
                    INSERT OR REPLACE INTO file_associations
                    (prompt_id, file_path, token_change) VALUES (?, ?, ?)
                """, (prompt_id, fp, token_change))
            conn.commit()
            conn.close()

            # Update in-memory
            rec = self.get_prompt(prompt_id)
            if rec:
                for fp in file_paths:
                    if fp not in rec.associated_files:
                        rec.associated_files.append(fp)
                        rec.file_changes[fp] = token_change

            self._update_json_associations(prompt_id, file_paths)
            return True
        except Exception as e:
            logger.error("Error associating files: %s", e)
            return False

    def update_response(self, prompt_id: str,
                        response_text: str) -> bool:
        """Update a prompt's response text."""
        try:
            conn = sqlite3.connect(self.sqlite_path)
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE prompts SET response_text = ? WHERE id = ?",
                (response_text, prompt_id))
            conn.commit()
            conn.close()

            # Update in-memory
            for p in self.prompts:
                if p.id == prompt_id:
                    p.response_text = response_text
                    break

            # Update JSON
            self._update_json_field(prompt_id, "response_text",
                                    response_text)
            return True
        except Exception as e:
            logger.error("Error updating response: %s", e)
            return False

    def delete_prompt(self, prompt_id: str) -> bool:
        """Delete a prompt by ID from all storage."""
        try:
            conn = sqlite3.connect(self.sqlite_path)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM file_associations WHERE prompt_id = ?",
                           (prompt_id,))
            cursor.execute("DELETE FROM prompts WHERE id = ?", (prompt_id,))
            conn.commit()
            conn.close()

            self.prompts = [p for p in self.prompts if p.id != prompt_id]
            self._remove_from_json(prompt_id)
            return True
        except Exception as e:
            logger.error("Error deleting prompt: %s", e)
            return False

    def clear_active_prompt(self) -> None:
        """Clear the active prompt."""
        self.active_prompt = None

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def search_prompts(self, search_text: Optional[str] = None,
                       llm_name: Optional[str] = None,
                       source: Optional[str] = None,
                       file_path: Optional[str] = None,
                       start_date: Optional[str] = None,
                       end_date: Optional[str] = None,
                       limit: int = 100) -> List[Dict[str, Any]]:
        """Search prompts with various filters using SQLite."""
        try:
            conn = sqlite3.connect(self.sqlite_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            query = "SELECT DISTINCT p.* FROM prompts p"
            params: List[Any] = []
            where_clauses: List[str] = []

            if file_path:
                query += " LEFT JOIN file_associations fa ON p.id = fa.prompt_id"
                where_clauses.append("fa.file_path LIKE ?")
                params.append(f"%{file_path}%")
            if search_text:
                where_clauses.append(
                    "(p.prompt_text LIKE ? OR p.description LIKE ?)")
                params.extend([f"%{search_text}%", f"%{search_text}%"])
            if llm_name:
                where_clauses.append("p.llm_name = ?")
                params.append(llm_name)
            if source:
                where_clauses.append("p.source = ?")
                params.append(source)
            if start_date:
                where_clauses.append("p.timestamp >= ?")
                params.append(start_date)
            if end_date:
                where_clauses.append("p.timestamp <= ?")
                params.append(end_date)

            if where_clauses:
                query += " WHERE " + " AND ".join(where_clauses)
            query += " ORDER BY p.timestamp DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)
            results = []
            for row in cursor.fetchall():
                d = dict(row)
                if d.get("metadata"):
                    try:
                        d["metadata"] = json.loads(d["metadata"])
                    except (json.JSONDecodeError, TypeError):
                        pass
                cursor.execute(
                    "SELECT file_path, token_change FROM file_associations "
                    "WHERE prompt_id = ?", (d["id"],))
                file_rows = cursor.fetchall()
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
        """Get the total number of prompts in the database."""
        try:
            conn = sqlite3.connect(self.sqlite_path)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM prompts")
            count = cursor.fetchone()[0]
            conn.close()
            return count
        except Exception as e:
            logger.error("Error getting prompts count: %s", e)
            return len(self.prompts)

    # ------------------------------------------------------------------
    # Load / Save (GUI mode)
    # ------------------------------------------------------------------

    def load(self) -> bool:
        """
        Load prompts into the in-memory list from all sources.

        Merges SQLite DB, JSON file, and Claude Desktop prompts,
        de-duplicating by prompt ID.
        """
        seen_ids: set = set()
        loaded: List[PromptRecord] = []

        # Load from SQLite
        try:
            conn = sqlite3.connect(self.sqlite_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM prompts ORDER BY timestamp")
            for row in cursor.fetchall():
                d = dict(row)
                d["llm_used"] = d.pop("llm_name", "Unknown")
                cursor.execute(
                    "SELECT file_path, token_change FROM file_associations "
                    "WHERE prompt_id = ?", (d["id"],))
                file_rows = cursor.fetchall()
                d["associated_files"] = [r["file_path"] for r in file_rows]
                d["file_changes"] = {r["file_path"]: r["token_change"]
                                     for r in file_rows}
                rec = PromptRecord.from_dict(d)
                if rec.id not in seen_ids:
                    loaded.append(rec)
                    seen_ids.add(rec.id)
            conn.close()
        except Exception as e:
            logger.error("Error loading from SQLite: %s", e)

        # Load from JSON (Claude Desktop prompts + legacy data)
        # Also merge fields (e.g. response_text) into records already
        # loaded from SQLite, since the JSON may have been updated by a
        # separate process (Flask API server) after the SQLite write.
        loaded_by_id: Dict[str, PromptRecord] = {r.id: r for r in loaded}
        for json_path in self._json_paths():
            try:
                if not os.path.exists(json_path):
                    continue
                with open(json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for item in data:
                    pid = item.get("id")
                    if not pid:
                        continue
                    if pid in seen_ids:
                        # Merge: fill in any empty fields from JSON
                        existing = loaded_by_id.get(pid)
                        if existing:
                            json_resp = item.get("response_text") or ""
                            if json_resp and not existing.response_text:
                                existing.response_text = json_resp
                            json_desc = item.get("description") or ""
                            if json_desc and not existing.description:
                                existing.description = json_desc
                    else:
                        rec = PromptRecord.from_dict(item)
                        # Set source from JSON if present
                        if "source" in item:
                            rec.source = item["source"]
                        elif json_path.endswith("prompts.json"):
                            rec.source = "Claude Desktop"
                        loaded.append(rec)
                        loaded_by_id[rec.id] = rec
                        seen_ids.add(rec.id)
            except Exception as e:
                logger.error("Error loading from %s: %s", json_path, e)

        self.prompts = loaded
        logger.info("Loaded %d prompts from all sources", len(self.prompts))
        return len(self.prompts) > 0

    def save(self) -> bool:
        """Save all in-memory prompts to both SQLite and JSON."""
        try:
            # Save to SQLite
            conn = sqlite3.connect(self.sqlite_path)
            cursor = conn.cursor()
            for rec in self.prompts:
                cursor.execute("""
                    INSERT OR REPLACE INTO prompts
                    (id, timestamp, source, llm_name, model_name,
                     prompt_text, response_text, description, url,
                     conversation_id, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    rec.id, rec.timestamp.isoformat(), rec.source,
                    rec.llm_used, rec.model_name, rec.prompt_text,
                    rec.response_text,
                    rec.description, rec.url, rec.conversation_id,
                    json.dumps(rec.metadata) if rec.metadata else None,
                ))
                # Save file associations
                for fp in rec.associated_files:
                    tc = rec.file_changes.get(fp, 0)
                    cursor.execute("""
                        INSERT OR REPLACE INTO file_associations
                        (prompt_id, file_path, token_change) VALUES (?, ?, ?)
                    """, (rec.id, fp, tc))
            conn.commit()
            conn.close()

            # Save to JSON
            self._save_json()
            return True
        except Exception as e:
            logger.error("Error saving prompt database: %s", e)
            return False

    def import_from_json(self, json_path: Optional[str] = None) -> int:
        """Import prompts from a JSON file into SQLite."""
        json_file = json_path or self.json_path
        if not os.path.exists(json_file):
            return 0
        try:
            with open(json_file, "r", encoding="utf-8") as f:
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

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _json_paths(self) -> List[str]:
        """Return list of JSON paths to check for prompts."""
        paths = [self.json_path]
        # Also check for prompt_database.json in working dir
        pdb = os.path.join(os.getcwd(), "prompt_database.json")
        if pdb != self.json_path:
            paths.append(pdb)
        return paths

    def _insert_sqlite(self, rec: PromptRecord) -> None:
        """Insert a single PromptRecord into SQLite."""
        try:
            conn = sqlite3.connect(self.sqlite_path)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO prompts
                (id, timestamp, source, llm_name, model_name,
                 prompt_text, response_text, description, url,
                 conversation_id, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                rec.id, rec.timestamp.isoformat(), rec.source,
                rec.llm_used, rec.model_name, rec.prompt_text,
                rec.response_text,
                rec.description, rec.url, rec.conversation_id,
                json.dumps(rec.metadata) if rec.metadata else None,
            ))
            for fp in rec.associated_files:
                tc = rec.file_changes.get(fp, 0)
                cursor.execute("""
                    INSERT OR REPLACE INTO file_associations
                    (prompt_id, file_path, token_change) VALUES (?, ?, ?)
                """, (rec.id, fp, tc))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error("Error inserting to SQLite: %s", e)

    def _get_from_sqlite(self, prompt_id: str) -> Optional[PromptRecord]:
        """Fetch a single prompt from SQLite by ID."""
        try:
            conn = sqlite3.connect(self.sqlite_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM prompts WHERE id = ?", (prompt_id,))
            row = cursor.fetchone()
            if not row:
                conn.close()
                return None
            d = dict(row)
            d["llm_used"] = d.pop("llm_name", "Unknown")
            cursor.execute(
                "SELECT file_path, token_change FROM file_associations "
                "WHERE prompt_id = ?", (prompt_id,))
            file_rows = cursor.fetchall()
            d["associated_files"] = [r["file_path"] for r in file_rows]
            d["file_changes"] = {r["file_path"]: r["token_change"]
                                 for r in file_rows}
            conn.close()
            return PromptRecord.from_dict(d)
        except Exception as e:
            logger.error("Error getting prompt from SQLite: %s", e)
            return None

    def _add_to_json(self, rec: PromptRecord) -> None:
        """Append a prompt to the JSON file."""
        with self._json_lock:
            try:
                prompts = []
                if os.path.exists(self.json_path):
                    with open(self.json_path, "r", encoding="utf-8") as f:
                        prompts = json.load(f)

                entry = {
                    "id": rec.id,
                    "timestamp": rec.timestamp.isoformat(),
                    "prompt_text": rec.prompt_text,
                    "response_text": rec.response_text,
                    "description": rec.description or f"Prompt from {rec.llm_used}",
                    "model": rec.llm_used,
                    "files": rec.associated_files,
                    "source": rec.source,
                }
                prompts.append(entry)

                json_dir = os.path.dirname(self.json_path)
                if json_dir:
                    os.makedirs(json_dir, exist_ok=True)
                with open(self.json_path, "w", encoding="utf-8") as f:
                    json.dump(prompts, f, indent=4)
            except Exception as e:
                logger.error("Error adding to JSON: %s", e)

    def _save_json(self) -> None:
        """Save all in-memory prompts to the JSON file."""
        with self._json_lock:
            try:
                data = []
                for rec in self.prompts:
                    data.append({
                        "id": rec.id,
                        "timestamp": rec.timestamp.isoformat(),
                        "prompt_text": rec.prompt_text,
                        "response_text": rec.response_text,
                        "description": rec.description,
                        "model": rec.llm_used,
                        "files": rec.associated_files,
                        "source": rec.source,
                    })
                json_dir = os.path.dirname(self.json_path)
                if json_dir:
                    os.makedirs(json_dir, exist_ok=True)
                with open(self.json_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4)
            except Exception as e:
                logger.error("Error saving JSON: %s", e)

    def _update_json_associations(self, prompt_id: str,
                                   file_paths: List[str]) -> None:
        """Update file associations in the JSON database."""
        with self._json_lock:
            try:
                if not os.path.exists(self.json_path):
                    return
                with open(self.json_path, "r", encoding="utf-8") as f:
                    prompts = json.load(f)
                for prompt in prompts:
                    if prompt.get("id") == prompt_id:
                        existing = set(prompt.get("files", []))
                        existing.update(file_paths)
                        prompt["files"] = list(existing)
                        break
                with open(self.json_path, "w", encoding="utf-8") as f:
                    json.dump(prompts, f, indent=4)
            except Exception as e:
                logger.error("Error updating JSON associations: %s", e)

    def _remove_from_json(self, prompt_id: str) -> None:
        """Remove a prompt from the JSON file."""
        with self._json_lock:
            try:
                if not os.path.exists(self.json_path):
                    return
                with open(self.json_path, "r", encoding="utf-8") as f:
                    prompts = json.load(f)
                prompts = [p for p in prompts if p.get("id") != prompt_id]
                with open(self.json_path, "w", encoding="utf-8") as f:
                    json.dump(prompts, f, indent=4)
            except Exception as e:
                logger.error("Error removing from JSON: %s", e)

    def _update_json_field(self, prompt_id: str, field: str,
                           value: Any) -> None:
        """Update a single field for a prompt in the JSON file."""
        with self._json_lock:
            try:
                if not os.path.exists(self.json_path):
                    return
                with open(self.json_path, "r", encoding="utf-8") as f:
                    prompts = json.load(f)
                for prompt in prompts:
                    if prompt.get("id") == prompt_id:
                        prompt[field] = value
                        break
                with open(self.json_path, "w", encoding="utf-8") as f:
                    json.dump(prompts, f, indent=4)
            except Exception as e:
                logger.error("Error updating JSON field: %s", e)
