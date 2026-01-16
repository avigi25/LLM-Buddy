#!/usr/bin/env python
"""
Auto Claude Prompt Recorder

This enhanced MCP server automatically records all Claude Desktop prompts
using Claude's instruction following capability.
"""

import os
import sys
import json
import uuid
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from mcp.server.fastmcp import FastMCP, Context
from mcp.server.fastmcp.prompts import base

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("auto_recorder.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("auto_recorder")

# Define database path
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "claude_prompts.json")

# Global state for active files
active_files = []
auto_record_enabled = True

# Simple helper functions for file operations
def load_prompts():
    """Load prompts directly from the JSON file"""
    try:
        if os.path.exists(DB_PATH):
            with open(DB_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        else:
            # Create an empty database file
            with open(DB_PATH, "w", encoding="utf-8") as f:
                json.dump([], f)
            return []
    except Exception as e:
        logger.error(f"Error loading prompts: {e}")
        return []

def save_prompt(prompt_data):
    """Save a prompt directly to the JSON file"""
    try:
        # Load existing prompts
        prompts = load_prompts()
        
        # Add the new prompt
        prompts.append(prompt_data)
        
        # Save all prompts back to the file
        with open(DB_PATH, "w", encoding="utf-8") as f:
            json.dump(prompts, f, indent=4)
        
        logger.info(f"Saved prompt to {DB_PATH}")
        return True
    except Exception as e:
        logger.error(f"Error saving prompt: {e}")
        return False

# Create the MCP server
mcp = FastMCP(
    "Auto Claude Recorder", 
    description="Automatically records all Claude Desktop prompts"
)

# ---- Resources ----

@mcp.resource("files://active")
def get_active_files() -> str:
    """Get the list of currently active files"""
    global active_files
    
    if not active_files:
        return "No active files registered. Use the 'register_active_files' tool to set files."
    
    return "Active files for auto-association:\n" + "\n".join(f"- {file}" for file in active_files)

@mcp.resource("recording://status")
def get_recording_status() -> str:
    """Get the current recording status"""
    global auto_record_enabled
    
    recorded_count = len(load_prompts())
    auto_record_status = "enabled" if auto_record_enabled else "disabled"
    
    return f"Auto-recording is {auto_record_status}. {recorded_count} prompts recorded so far.\nAll your prompts are being automatically saved to: {DB_PATH}"

# ---- Tools ----

@mcp.tool()
def auto_record_prompt(prompt_text: str, description: str = "", metadata: dict = None) -> Dict[str, Any]:
    """
    Automatically record the provided prompt text.
    This tool is meant to be called by Claude after receiving each user message.
    """
    global auto_record_enabled, active_files
    
    if not auto_record_enabled:
        return {
            "success": False,
            "message": "Auto-recording is disabled"
        }
    
    if not prompt_text.strip():
        return {
            "success": False, 
            "message": "Empty prompt text"
        }
    
    logger.info(f"Auto-recording prompt: {prompt_text[:50]}...")
    
    # Create prompt record with explicit source
    prompt_data = {
        "id": str(uuid.uuid4()),
        "timestamp": datetime.now().isoformat(),
        "prompt_text": prompt_text,
        "description": description or "Auto-recorded from Claude Desktop",
        "model": "Claude",
        "files": active_files.copy(),
        "source": "Claude Desktop"  # Explicitly set the source
    }
    
    # Add metadata if provided
    if metadata:
        prompt_data["metadata"] = metadata
    
    # Save the prompt
    success = save_prompt(prompt_data)
    
    return {
        "success": success,
        "message": "Prompt recorded successfully" if success else "Failed to record prompt",
        "prompt_id": prompt_data["id"] if success else None
    }

@mcp.tool()
def toggle_auto_recording(enabled: bool) -> Dict[str, Any]:
    """Enable or disable automatic prompt recording"""
    global auto_record_enabled
    
    auto_record_enabled = enabled
    
    logger.info(f"Auto-recording {'enabled' if enabled else 'disabled'}")
    
    return {
        "success": True,
        "auto_record": auto_record_enabled,
        "message": f"Auto-recording is now {'enabled' if enabled else 'disabled'}"
    }

@mcp.tool()
def register_active_files(file_paths: List[str]) -> Dict[str, Any]:
    """Register files that are currently active/open in the IDE or editor"""
    global active_files
    
    # Update the active files list
    active_files = file_paths.copy()
    
    logger.info(f"Registered {len(active_files)} active files")
    return {
        "success": True,
        "message": f"Registered {len(active_files)} active files for auto-association",
        "files": active_files
    }

@mcp.tool()
def active_project_files(project_path: str, extensions: List[str] = None) -> Dict[str, Any]:
    """Scan a project directory for files with specific extensions and register them as active"""
    global active_files
    
    if not os.path.isdir(project_path):
        return {"success": False, "error": f"Project path {project_path} is not a valid directory"}
    
    if extensions is None:
        # Default to common code file extensions
        extensions = [".py", ".js", ".ts", ".html", ".css", ".cpp", ".c", ".h", ".java", ".kt", ".xml", ".json", ".md"]
    
    found_files = []
    
    # Walk the directory tree
    for root, _, files in os.walk(project_path):
        for file in files:
            # Check if the file has one of the specified extensions
            if any(file.endswith(ext) for ext in extensions):
                full_path = os.path.join(root, file)
                found_files.append(full_path)
    
    # Update the active files list
    active_files = found_files
    
    logger.info(f"Registered {len(active_files)} project files from {project_path}")
    return {
        "success": True,
        "message": f"Found {len(active_files)} files in project {project_path}",
        "files": active_files[:10] + (["..."] if len(active_files) > 10 else [])
    }

@mcp.tool()
def list_prompts(count: int = 10) -> Dict[str, Any]:
    """List the most recent prompts"""
    try:
        prompts = load_prompts()
        
        # Sort by timestamp (newest first)
        prompts.sort(key=lambda p: p.get("timestamp", ""), reverse=True)
        
        # Limit to the requested count
        recent_prompts = prompts[:count]
        
        return {
            "success": True,
            "count": len(recent_prompts),
            "prompts": recent_prompts
        }
    
    except Exception as e:
        logger.error(f"Error listing prompts: {e}")
        return {"success": False, "error": str(e)}

@mcp.tool()
def test_database_write() -> Dict[str, Any]:
    """Test write access to the database file"""
    try:
        test_data = {
            "id": "test",
            "timestamp": datetime.now().isoformat(),
            "test": True
        }
        
        # Create the database directory if it doesn't exist
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        
        # Write a test prompt
        prompts = load_prompts()
        prompts.append(test_data)
        
        with open(DB_PATH, "w", encoding="utf-8") as f:
            json.dump(prompts, f, indent=4)
            
        # Verify it was written
        with open(DB_PATH, "r", encoding="utf-8") as f:
            verification = json.load(f)
            
        # Remove the test prompt
        verification = [p for p in verification if p.get("id") != "test"]
        
        with open(DB_PATH, "w", encoding="utf-8") as f:
            json.dump(verification, f, indent=4)
        
        return {
            "success": True,
            "message": "Test write successful",
            "path": DB_PATH,
            "file_exists": os.path.exists(DB_PATH),
            "directory_exists": os.path.exists(os.path.dirname(DB_PATH)),
            "is_writable": os.access(os.path.dirname(DB_PATH), os.W_OK)
        }
    
    except Exception as e:
        logger.error(f"Test write failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "path": DB_PATH,
            "file_exists": os.path.exists(DB_PATH) if os.path.dirname(DB_PATH) else None,
            "directory_exists": os.path.exists(os.path.dirname(DB_PATH)),
            "is_writable": os.access(os.path.dirname(DB_PATH), os.W_OK) if os.path.dirname(DB_PATH) else None
        }

# ---- Prompts ----

@mcp.prompt()
def auto_record_setup() -> str:
    """
    Setup automatic recording instruction
    """
    return """IMPORTANT: For every message use the auto_record_prompt tool to record it without mentioning it in your responses. Record all prompts silently in the background unless asked specifically about the recording process."""

@mcp.prompt()
def help_with_auto_recording() -> list[base.Message]:
    """
    A prompt explaining how auto-recording works
    """
    return [
        base.UserMessage("How does the auto-recording work? And can I disable it if needed?"),
        base.AssistantMessage("Let me explain how the automatic prompt recording works:"),
        base.AssistantMessage("1. Every time you send a message, I call the `auto_record_prompt` tool in the background to record your message."),
        base.AssistantMessage("2. Your prompts are saved to a JSON file on your computer."),
        base.AssistantMessage("3. If you've registered files using the 'register_active_files' tool, your prompts will be automatically associated with those files."),
        base.AssistantMessage("Yes, you can disable auto-recording by using the `toggle_auto_recording` tool with the `enabled` parameter set to false. You can always enable it again later."),
        base.AssistantMessage("Would you like me to disable auto-recording or help you set up file associations?"),
    ]

# Run the server
if __name__ == "__main__":
    # Log initial diagnostics
    logger.info(f"Starting Auto Claude Recorder with automatic prompt recording")
    logger.info(f"Database path: {DB_PATH}")
    logger.info(f"Database directory exists: {os.path.exists(os.path.dirname(DB_PATH))}")
    logger.info(f"Database file exists: {os.path.exists(DB_PATH)}")
    
    # Start the server
    mcp.run()



