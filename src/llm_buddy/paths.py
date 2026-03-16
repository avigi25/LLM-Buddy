"""Centralized path resolution for LLM Buddy.

Handles both development (editable install) and frozen (PyInstaller) modes.
All modules should use these functions instead of os.getcwd() for data paths.
"""

import os
import sys


def get_app_dir() -> str:
    """Return the application root directory.

    - Frozen (PyInstaller --onedir): directory containing the .exe
    - Development: current working directory
    """
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.getcwd()


def get_data_dir() -> str:
    """Return the data directory, creating it if needed."""
    data_dir = os.path.join(get_app_dir(), "data")
    os.makedirs(data_dir, exist_ok=True)
    return data_dir


def get_logs_dir() -> str:
    """Return the logs directory, creating it if needed."""
    logs_dir = os.path.join(get_app_dir(), "logs")
    os.makedirs(logs_dir, exist_ok=True)
    return logs_dir


def get_backup_dir() -> str:
    """Return the backup output directory, creating it if needed."""
    backup_dir = os.path.join(get_app_dir(), "backup")
    os.makedirs(backup_dir, exist_ok=True)
    return backup_dir


def get_extension_dir() -> str:
    """Return the path to the browser extension folder."""
    return os.path.join(get_app_dir(), "extension")


def get_bundle_dir() -> str:
    """Return the directory where bundled resources are located.

    - Frozen: sys._MEIPASS (PyInstaller extraction dir)
    - Development: current working directory
    """
    if getattr(sys, "frozen", False):
        return getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    return os.getcwd()
