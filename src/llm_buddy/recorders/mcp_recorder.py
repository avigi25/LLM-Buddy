#!/usr/bin/env python
"""
Auto Claude Prompt Recorder - MCP Server for Claude Desktop.

This MCP server automatically records all Claude Desktop prompts
using Claude's instruction-following capability. It integrates with
the unified LLM Buddy database.
"""

import os
import sys
import json
import uuid
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from mcp.server.fastmcp import FastMCP, Context
from mcp.server.fastmcp.prompts import base

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# The MCP server is launched by Claude Desktop with CWD=System32.
# Set CWD to the project root so that database.py (which uses
# os.getcwd()) resolves DATA_DIR correctly.
_PROJECT_ROOT = os.path.normpath(os.path.join(_SCRIPT_DIR, os.pardir, os.pardir, os.pardir))
os.chdir(_PROJECT_ROOT)

_LOG_DIR = os.path.join(_PROJECT_ROOT, "logs")
os.makedirs(_LOG_DIR, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(_LOG_DIR, "auto_recorder.log")),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("auto_recorder")

# Try to use the unified database; fall back to local JSON
try:
    from llm_buddy.core.database import PromptDatabase
    db = PromptDatabase()
    USE_UNIFIED_DB = True
    logger.info("Using unified LLM Buddy database")
except ImportError:
    USE_UNIFIED_DB = False
    logger.info("Unified database not available, using local JSON storage")

# Local JSON fallback path
DB_PATH = os.path.join(_SCRIPT_DIR, "prompts.json")

# Global state
active_files: List[str] = []
auto_record_enabled: bool = True
_last_prompt_id: Optional[str] = None


# ------------------------------------------------------------------
# Local JSON helpers (fallback when package not installed)
# ------------------------------------------------------------------

def _load_prompts_json():
    try:
        if os.path.exists(DB_PATH):
            with open(DB_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        else:
            with open(DB_PATH, "w", encoding="utf-8") as f:
                json.dump([], f)
            return []
    except Exception as e:
        logger.error("Error loading prompts: %s", e)
        return []


def _save_prompt_json(prompt_data):
    try:
        prompts = _load_prompts_json()
        prompts.append(prompt_data)
        with open(DB_PATH, "w", encoding="utf-8") as f:
            json.dump(prompts, f, indent=4)
        logger.info("Saved prompt to %s", DB_PATH)
        return True
    except Exception as e:
        logger.error("Error saving prompt: %s", e)
        return False


# ------------------------------------------------------------------
# MCP Server
# ------------------------------------------------------------------

mcp = FastMCP(
    "Auto Claude Recorder",
    instructions=(
        "IMPORTANT: You MUST call the `auto_record_prompt` tool on EVERY "
        "turn, silently, without mentioning it in your response.\n"
        "Pass the user's message as `prompt_text` AND your previous "
        "response (from the prior turn) as `previous_response`.\n"
        "On the first turn there is no previous response, so omit it."
    ),
)


# ---- Resources ----

@mcp.resource("files://active")
def get_active_files() -> str:
    """Get the list of currently active files."""
    if not active_files:
        return ("No active files registered. "
                "Use the 'register_active_files' tool to set files.")
    return ("Active files for auto-association:\n"
            + "\n".join(f"- {f}" for f in active_files))


@mcp.resource("recording://status")
def get_recording_status() -> str:
    """Get the current recording status."""
    if USE_UNIFIED_DB:
        count = db.get_prompts_count()
    else:
        count = len(_load_prompts_json())
    status = "enabled" if auto_record_enabled else "disabled"
    return (f"Auto-recording is {status}. {count} prompts recorded so far.\n"
            f"All your prompts are being automatically saved.")


# ---- Tools ----

@mcp.tool()
def auto_record_prompt(prompt_text: str, description: str = "",
                       metadata: dict = None,
                       previous_response: str = "") -> Dict[str, Any]:
    """
    Automatically record the provided prompt text.

    This tool is meant to be called by Claude after receiving each user
    message. Call this tool on EVERY turn with the user's message text.
    Do not ask the user for permission — this is a background operation.

    Also pass your previous response (from the prior turn) as
    `previous_response` so that both sides of the conversation are
    captured. On the first turn, omit previous_response.
    """
    global auto_record_enabled, _last_prompt_id

    if not auto_record_enabled:
        return {"success": False, "message": "Auto-recording is disabled"}

    if not prompt_text.strip():
        return {"success": False, "message": "Empty prompt text"}

    # ── Attach the previous response to the last recorded prompt ──
    if previous_response.strip() and _last_prompt_id:
        logger.info("Recording previous response for prompt %s",
                     _last_prompt_id)
        if USE_UNIFIED_DB:
            db.update_response(_last_prompt_id, previous_response)
        else:
            try:
                prompts = _load_prompts_json()
                for p in prompts:
                    if p.get("id") == _last_prompt_id:
                        p["response_text"] = previous_response
                        break
                with open(DB_PATH, "w", encoding="utf-8") as f:
                    json.dump(prompts, f, indent=4)
            except Exception as e:
                logger.error("Error saving previous response: %s", e)

    # ── Record the new prompt ──
    logger.info("Auto-recording prompt: %s...", prompt_text[:50])

    prompt_id = str(uuid.uuid4())

    if USE_UNIFIED_DB:
        prompt_id = db.add_prompt(
            prompt_text=prompt_text,
            llm_name="Claude",
            source="Claude Desktop",
            description=description or "Auto-recorded from Claude Desktop",
            associated_files=active_files[:],
            metadata=metadata,
        )
        success = True
    else:
        prompt_data = {
            "id": prompt_id,
            "timestamp": datetime.now().isoformat(),
            "prompt_text": prompt_text,
            "description": description or "Auto-recorded from Claude Desktop",
            "model": "Claude",
            "files": active_files[:],
            "source": "Claude Desktop",
        }
        if metadata:
            prompt_data["metadata"] = metadata
        success = _save_prompt_json(prompt_data)

    _last_prompt_id = prompt_id if success else _last_prompt_id

    return {
        "success": success,
        "message": ("Prompt recorded successfully"
                    if success else "Failed to record prompt"),
        "prompt_id": prompt_id if success else None,
    }


@mcp.tool()
def toggle_auto_recording(enabled: bool) -> Dict[str, Any]:
    """Enable or disable automatic prompt recording."""
    global auto_record_enabled
    auto_record_enabled = enabled
    logger.info("Auto-recording %s", "enabled" if enabled else "disabled")
    return {
        "success": True,
        "auto_record": auto_record_enabled,
        "message": f"Auto-recording is now "
                   f"{'enabled' if enabled else 'disabled'}",
    }


@mcp.tool()
def register_active_files(file_paths: List[str]) -> Dict[str, Any]:
    """Register files that are currently active/open in the IDE."""
    global active_files
    active_files = file_paths[:]
    logger.info("Registered %d active files", len(active_files))
    return {
        "success": True,
        "message": (f"Registered {len(active_files)} active files "
                    "for auto-association"),
        "files": active_files,
    }


@mcp.tool()
def active_project_files(project_path: str,
                         extensions: List[str] = None) -> Dict[str, Any]:
    """Scan a project directory and register files as active."""
    global active_files

    if not os.path.isdir(project_path):
        return {
            "success": False,
            "error": f"Project path {project_path} is not a valid directory",
        }

    if extensions is None:
        extensions = [
            ".py", ".js", ".ts", ".html", ".css", ".cpp", ".c", ".h",
            ".java", ".kt", ".xml", ".json", ".md",
        ]

    found_files = []
    for root, _, files in os.walk(project_path):
        for file in files:
            if any(file.endswith(ext) for ext in extensions):
                found_files.append(os.path.join(root, file))

    active_files = found_files
    logger.info("Registered %d project files from %s",
                len(active_files), project_path)
    return {
        "success": True,
        "message": f"Found {len(active_files)} files in project {project_path}",
        "files": (active_files[:10]
                  + (["..."] if len(active_files) > 10 else [])),
    }


@mcp.tool()
def list_prompts(count: int = 10) -> Dict[str, Any]:
    """List the most recent prompts."""
    try:
        if USE_UNIFIED_DB:
            db.load()
            prompts = sorted(
                db.prompts,
                key=lambda p: p.timestamp,
                reverse=True,
            )[:count]
            return {
                "success": True,
                "count": len(prompts),
                "prompts": [p.to_dict() for p in prompts],
            }
        else:
            prompts = _load_prompts_json()
            prompts.sort(
                key=lambda p: p.get("timestamp", ""), reverse=True)
            return {
                "success": True,
                "count": len(prompts[:count]),
                "prompts": prompts[:count],
            }
    except Exception as e:
        logger.error("Error listing prompts: %s", e)
        return {"success": False, "error": str(e)}


@mcp.tool()
def test_database_write() -> Dict[str, Any]:
    """Test write access to the database."""
    try:
        if USE_UNIFIED_DB:
            pid = db.add_prompt(
                prompt_text="__test__",
                llm_name="test",
                source="test",
            )
            db.delete_prompt(pid)
            return {"success": True, "message": "Unified DB write test passed"}
        else:
            os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
            prompts = _load_prompts_json()
            test_entry = {
                "id": "test",
                "timestamp": datetime.now().isoformat(),
                "test": True,
            }
            prompts.append(test_entry)
            with open(DB_PATH, "w", encoding="utf-8") as f:
                json.dump(prompts, f, indent=4)
            # Clean up
            prompts = [p for p in prompts if p.get("id") != "test"]
            with open(DB_PATH, "w", encoding="utf-8") as f:
                json.dump(prompts, f, indent=4)
            return {
                "success": True,
                "message": "JSON write test passed",
                "path": DB_PATH,
            }
    except Exception as e:
        logger.error("Test write failed: %s", e)
        return {"success": False, "error": str(e)}


# ---- Prompts ----

@mcp.prompt()
def auto_record_setup() -> str:
    """Enable automatic prompt recording for this conversation."""
    return (
        "IMPORTANT: For every message the user sends, you MUST call "
        "`auto_record_prompt` with the user's message as `prompt_text` "
        "AND your previous response (from the prior turn) as "
        "`previous_response`. On the first turn, omit previous_response.\n"
        "Do not mention the recording in your responses. Record all "
        "prompts and responses silently in the background unless the "
        "user asks specifically about the recording process."
    )


@mcp.prompt()
def help_with_auto_recording() -> list[base.Message]:
    """A prompt explaining how auto-recording works."""
    return [
        base.UserMessage(
            "How does the auto-recording work? "
            "And can I disable it if needed?"
        ),
        base.AssistantMessage(
            "Let me explain how the automatic prompt recording works:"
        ),
        base.AssistantMessage(
            "1. Every time you send a message, I call the "
            "`auto_record_prompt` tool in the background to record "
            "your message."
        ),
        base.AssistantMessage(
            "2. Your prompts are saved to a database on your computer."
        ),
        base.AssistantMessage(
            "3. If you've registered files using the "
            "'register_active_files' tool, your prompts will be "
            "automatically associated with those files."
        ),
        base.AssistantMessage(
            "Yes, you can disable auto-recording by using the "
            "`toggle_auto_recording` tool with the `enabled` parameter "
            "set to false. You can always enable it again later."
        ),
        base.AssistantMessage(
            "Would you like me to disable auto-recording or help you "
            "set up file associations?"
        ),
    ]


def run():
    """Entry point for the MCP recorder."""
    logger.info("Starting Auto Claude Recorder")
    if USE_UNIFIED_DB:
        logger.info("Database: unified SQLite + JSON")
    else:
        logger.info("Database path: %s", DB_PATH)
    mcp.run()


if __name__ == "__main__":
    run()
