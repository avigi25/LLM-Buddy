#!/usr/bin/env python3
"""
Configure Claude Desktop to use the new MCP recorder

This script updates the Claude Desktop configuration file to use the new MCP recorder
instead of the old one. It creates a backup of the original configuration file.
"""

import os
import sys
import json
import logging
from pathlib import Path
import shutil
import platform

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("configure")

def find_claude_config():
    """Find Claude Desktop configuration file in common locations"""
    system = platform.system()
    possible_paths = []
    
    if system == "Windows":
        # Windows paths
        appdata = os.getenv("APPDATA")
        if appdata:
            possible_paths.append(os.path.join(appdata, "Claude", "config.json"))
            possible_paths.append(os.path.join(appdata, "Claude", "claude_desktop_config.json"))
        
        localappdata = os.getenv("LOCALAPPDATA")
        if localappdata:
            possible_paths.append(os.path.join(localappdata, "Claude", "config.json"))
            possible_paths.append(os.path.join(localappdata, "Claude", "claude_desktop_config.json"))
    
    elif system == "Darwin":  # macOS
        home = os.path.expanduser("~")
        possible_paths.append(os.path.join(home, "Library", "Application Support", "Claude", "config.json"))
        possible_paths.append(os.path.join(home, "Library", "Application Support", "Claude", "claude_desktop_config.json"))
    
    elif system == "Linux":
        home = os.path.expanduser("~")
        possible_paths.append(os.path.join(home, ".config", "Claude", "config.json"))
        possible_paths.append(os.path.join(home, ".config", "Claude", "claude_desktop_config.json"))
    
    for path in possible_paths:
        if os.path.exists(path):
            return path
    
    return None

def update_claude_config():
    """Update Claude Desktop configuration to use the new MCP recorder"""
    logger.info("Updating Claude Desktop configuration")
    
    # Find Claude Desktop configuration file
    config_file = find_claude_config()
    if not config_file:
        logger.error("Could not find Claude Desktop configuration file")
        config_file = input("Please enter the path to the Claude Desktop configuration file: ")
        if not os.path.exists(config_file):
            logger.error(f"File not found: {config_file}")
            return
    
    logger.info(f"Found Claude Desktop configuration file: {config_file}")
    
    # Create backup
    backup_file = f"{config_file}.backup"
    shutil.copy2(config_file, backup_file)
    logger.info(f"Created backup: {backup_file}")
    
    # Load configuration
    try:
        with open(config_file, "r", encoding="utf-8") as f:
            config = json.load(f)
        
        logger.info("Loaded Claude Desktop configuration")
    except Exception as e:
        logger.error(f"Error loading configuration: {e}")
        return
    
    # Get the path to the new MCP recorder
    current_dir = os.path.dirname(os.path.abspath(__file__))
    mcp_recorder_path = os.path.join(current_dir, "mcp_recorder.py")
    
    # Update configuration
    if "mcpServers" not in config:
        config["mcpServers"] = {}
    
    # Update or add prompt-recorder entry
    config["mcpServers"]["prompt-recorder"] = {
        "command": "python" if platform.system() == "Windows" else "python3",
        "args": [mcp_recorder_path]
    }
    
    logger.info(f"Updated configuration to use new MCP recorder at {mcp_recorder_path}")
    
    # Save configuration
    try:
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
        
        logger.info("Saved updated configuration")
        logger.info("Claude Desktop will now use the new MCP recorder")
        logger.info("Please restart Claude Desktop for the changes to take effect")
    except Exception as e:
        logger.error(f"Error saving configuration: {e}")
        logger.info(f"You can restore the backup from: {backup_file}")

if __name__ == "__main__":
    update_claude_config()
    print("\nConfiguration update complete. Press Enter to exit...")
    input()


