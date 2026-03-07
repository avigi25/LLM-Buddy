"""Configure Claude Desktop to use LLM Buddy's MCP recorder."""

import os
import sys
import json
import shutil
import platform
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("configure")


def find_claude_config():
    """Find Claude Desktop configuration file in common locations."""
    system = platform.system()
    possible_paths = []

    if system == "Windows":
        appdata = os.getenv("APPDATA")
        if appdata:
            possible_paths.append(
                os.path.join(appdata, "Claude", "claude_desktop_config.json"))
            possible_paths.append(
                os.path.join(appdata, "Claude", "config.json"))
        localappdata = os.getenv("LOCALAPPDATA")
        if localappdata:
            possible_paths.append(
                os.path.join(localappdata, "Claude", "claude_desktop_config.json"))
            possible_paths.append(
                os.path.join(localappdata, "Claude", "config.json"))

    elif system == "Darwin":
        home = os.path.expanduser("~")
        possible_paths.append(os.path.join(
            home, "Library", "Application Support",
            "Claude", "claude_desktop_config.json"))
        possible_paths.append(os.path.join(
            home, "Library", "Application Support",
            "Claude", "config.json"))

    elif system == "Linux":
        home = os.path.expanduser("~")
        possible_paths.append(os.path.join(
            home, ".config", "Claude", "claude_desktop_config.json"))
        possible_paths.append(os.path.join(
            home, ".config", "Claude", "config.json"))

    for path in possible_paths:
        if os.path.exists(path):
            return path

    return None


def update_claude_config():
    """Update Claude Desktop configuration to use the MCP recorder."""
    logger.info("Updating Claude Desktop configuration")

    config_file = find_claude_config()
    if not config_file:
        logger.warning("Could not find Claude Desktop configuration file.")
        config_file = input(
            "Please enter the path to the Claude Desktop config file: ").strip()
        if not config_file or not os.path.exists(config_file):
            logger.error(f"File not found: {config_file}")
            return

    logger.info(f"Found config: {config_file}")

    # Create backup
    backup_file = f"{config_file}.backup"
    shutil.copy2(config_file, backup_file)
    logger.info(f"Backup created: {backup_file}")

    # Load
    try:
        with open(config_file, "r", encoding="utf-8") as f:
            config = json.load(f)
    except Exception as e:
        logger.error(f"Error loading configuration: {e}")
        return

    # Locate the MCP recorder file without importing it (which would
    # fail if the 'mcp' package isn't installed).
    import importlib.util
    spec = importlib.util.find_spec("llm_buddy.recorders.mcp_recorder")
    if spec is None or spec.origin is None:
        logger.error("Could not locate mcp_recorder.py in the package.")
        return
    mcp_recorder_path = spec.origin

    # Update
    if "mcpServers" not in config:
        config["mcpServers"] = {}

    python_cmd = "python" if platform.system() == "Windows" else "python3"
    config["mcpServers"]["prompt-recorder"] = {
        "command": python_cmd,
        "args": [mcp_recorder_path],
    }
    logger.info(f"MCP recorder path: {mcp_recorder_path}")

    # Save
    try:
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
        logger.info("Configuration saved successfully.")
        logger.info("Please restart Claude Desktop for changes to take effect.")
    except Exception as e:
        logger.error(f"Error saving configuration: {e}")
        logger.info(f"Restore backup from: {backup_file}")


if __name__ == "__main__":
    update_claude_config()
    print("\nConfiguration update complete. Press Enter to exit...")
    input()
