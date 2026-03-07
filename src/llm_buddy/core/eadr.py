"""
eADR (Elaborated Action Design Research) note management for LLM Buddy.

Provides CRUD operations for timestamped research notes stored as JSON.
"""

import json
import logging
import os
from datetime import datetime

logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(os.getcwd(), "data")
os.makedirs(DATA_DIR, exist_ok=True)

# Update the default:
NOTES_FILE = os.path.join(DATA_DIR, "eadr_notes.json")


def load_eadr_notes(notes_file=None):
    """Load existing eADR notes from file."""
    path = notes_file or NOTES_FILE
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error("Error loading eADR notes: %s", e)
    return []


def save_eadr_note(note_text, project_name="Origin", notes_file=None):
    """Save a new eADR note with timestamp and project name."""
    path = notes_file or NOTES_FILE
    notes = load_eadr_notes(path)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    new_note = {
        "timestamp": timestamp,
        "project": project_name,
        "note": note_text,
    }
    notes.append(new_note)

    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(notes, f, indent=4)
        return True
    except Exception as e:
        logger.error("Error saving eADR note: %s", e)
        return False


def delete_eadr_note(note_index, notes_file=None):
    """
    Delete a specific eADR note by its index.

    Returns (success, deleted_note) tuple.
    """
    path = notes_file or NOTES_FILE
    notes = load_eadr_notes(path)

    if 0 <= note_index < len(notes):
        deleted_note = notes.pop(note_index)
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(notes, f, indent=4)
            return True, deleted_note
        except Exception as e:
            logger.error("Error saving eADR notes after deletion: %s", e)
            return False, None
    return False, None
