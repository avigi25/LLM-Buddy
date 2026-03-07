"""
Profile persistence for LLM Buddy.

Profiles store user configurations (folders, extensions, header/footer, etc.)
as JSON on disk.
"""

import json
import logging
import os

logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(os.getcwd(), "data")
os.makedirs(DATA_DIR, exist_ok=True)

# Update the default:
DEFAULT_CONFIG_FILE = os.path.join(DATA_DIR, "profiles.json")


def load_profiles(config_file=None):
    """Load profiles from the JSON config file."""
    path = config_file or DEFAULT_CONFIG_FILE
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error("Error loading profiles: %s", e)
    return {}


def save_profiles(profiles, config_file=None):
    """Save profiles to the JSON config file."""
    path = config_file or DEFAULT_CONFIG_FILE
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(profiles, f, indent=4)
    except Exception as e:
        logger.error("Error saving profiles: %s", e)
