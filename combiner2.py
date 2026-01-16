#             & "C:/Program Files/Python311/python.exe" z:/Projects/llmbuddy/combiner2.py
# File eadr file will be in the folder it ran so for example: PS C:\Users\antho> & "C:/Program Files/Python311/python.exe" z:/projects/combiner2.py
# the eadr file will be in the C:\Users\antho folder.

import os
import sys
import json
import threading
import difflib
import re
import uuid
import hashlib
import fnmatch
import time
from datetime import datetime, timedelta
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext, simpledialog
from venv import logger
import tiktoken
import subprocess
import socket
import webbrowser
import requests
from urllib.parse import urljoin
import sqlite3

# You'll need to install the watchdog library:
# pip install watchdog
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# -------------------------------
# Configuration Persistence
# -------------------------------
CONFIG_FILE = "profiles.json"

def load_profiles():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading profiles: {e}")
    return {}

def save_profiles(profiles):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(profiles, f, indent=4)
    except Exception as e:
        print(f"Error saving profiles: {e}")

# -------------------------------
# Core Text Building and Token Counting
# -------------------------------
def build_combined_text(selected_files, header, footer):
    lines = []
    if header:
        lines.append(header)
        lines.append("")  # blank line
    for file_path in selected_files:
        lines.append(f"### {file_path}")
        lines.append("")  # blank line
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines.append(f.read())
        except Exception as e:
            lines.append(f"Error reading file: {e}")
        lines.append("")  # extra blank line
    if footer:
        lines.append(footer)
    return "\n".join(lines)

def build_content_only_text(file_paths):
    lines = []
    for file_path in file_paths:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines.append(f.read())
        except Exception as e:
            lines.append(f"Error reading file: {e}")
        lines.append("")
    return "\n".join(lines)

def count_tokens(text, encoding_name="cl100k_base"):
    try:
        encoding = tiktoken.get_encoding(encoding_name)
    except Exception as e:
        print(f"Error getting encoding: {e}")
        return len(text.split())
    tokens = encoding.encode(text)
    return len(tokens)

def count_tokens_in_file(filepath, encoding_name="cl100k_base"):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            text = f.read()
        return count_tokens(text, encoding_name)
    except Exception as e:
        return 0
    

# -------------------------------
# Core eADR Note Functions
# -------------------------------
def load_eadr_notes():
    """Load existing eADR notes from file"""
    notes_file = "eadr_notes.json"
    if os.path.exists(notes_file):
        try:
            with open(notes_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading eADR notes: {e}")
    return []

def save_eadr_note(note_text, project_name="Origin"):
    """Save a new eADR note with timestamp and project name"""
    notes = load_eadr_notes()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    new_note = {
        "timestamp": timestamp,
        "project": project_name,
        "note": note_text
    }
    
    notes.append(new_note)
    
    try:
        with open("eadr_notes.json", "w", encoding="utf-8") as f:
            json.dump(notes, f, indent=4)
        return True
    except Exception as e:
        print(f"Error saving eADR note: {e}")
        return False

def delete_eadr_note(note_index):
    """Delete a specific eADR note by its index"""
    notes = load_eadr_notes()
    
    if 0 <= note_index < len(notes):
        # Remove the note at the specified index
        deleted_note = notes.pop(note_index)
        
        try:
            with open("eadr_notes.json", "w", encoding="utf-8") as f:
                json.dump(notes, f, indent=4)
            return True, deleted_note
        except Exception as e:
            print(f"Error saving eADR notes after deletion: {e}")
            return False, None
    else:
        return False, None

# -------------------------------
# Rollback Functions
# -------------------------------
def parse_combined_file(filepath):
    """
    Parse a combined backup file and extract individual files with their paths and content.
    
    Returns:
        dict: A dictionary where keys are file paths and values are file contents
    """
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Split the content at the file headers
        # The file header pattern is: ### filepath
        file_blocks = re.split(r'^### (.+?)$', content, flags=re.MULTILINE)
        
        # file_blocks[0] will be any content before the first file header (like the overall header)
        # Then alternating path and content: [1]=path1, [2]=content1, [3]=path2, [4]=content2, etc.
        
        files_dict = {}
        for i in range(1, len(file_blocks), 2):
            if i+1 < len(file_blocks):
                file_path = file_blocks[i].strip()
                # Remove the blank line after the header if present
                file_content = file_blocks[i+1].lstrip('\n')
                files_dict[file_path] = file_content
        
        return files_dict
    
    except Exception as e:
        print(f"Error parsing combined file: {e}")
        return {}

def restore_file(file_path, content):
    """
    Restore a file to its original location with the provided content.
    
    Args:
        file_path (str): The path to the original file
        content (str): The content to write to the file
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Ensure the directory exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # Write the file
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        
        return True
    
    except Exception as e:
        print(f"Error restoring file {file_path}: {e}")
        return False

def get_file_diff(file_path, backup_content):
    """
    Get a diff between the current file and the backup content.
    
    Args:
        file_path (str): Path to the current file
        backup_content (str): Content from the backup
    
    Returns:
        str: Formatted diff or error message
    """
    try:
        # Read current file content
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                current_content = f.read()
        else:
            return "Current file does not exist - this would be a new file creation."
        
        # Generate diff
        current_lines = current_content.splitlines()
        backup_lines = backup_content.splitlines()
        
        diff = difflib.unified_diff(
            current_lines, backup_lines,
            fromfile=f"Current: {file_path}",
            tofile=f"Backup: {file_path}",
            lineterm=''
        )
        
        diff_text = '\n'.join(list(diff))
        if not diff_text:
            return "No differences found."
        
        return diff_text
    
    except Exception as e:
        return f"Error generating diff: {e}"

# -------------------------------
# Auto-Backup Configuration
# -------------------------------
class AutoBackupConfig:
    """Configuration class for auto-backup settings"""
    def __init__(self):
        self.enabled = False
        self.monitor_folders = []  # List of folders to monitor
        self.monitor_files = []    # List of individual files to monitor
        self.ignored_patterns = ["*.tmp", "*.bak", "*~"]  # File patterns to ignore
        self.min_token_change = 50  # Minimum token count change to trigger backup
        self.cooldown_minutes = 5   # Minimum time between auto-backups
        self.max_backups = 10       # Maximum number of auto-backups to keep
        self.notification_enabled = True  # Show notifications on backup
        self.last_backup_time = None  # Time of the last auto-backup
        self.file_hashes = {}  # Store file hashes to detect changes /Store (hash, token_count) tuples for files

    def to_dict(self):
        """Convert configuration to dictionary for saving"""
        return {
            "enabled": self.enabled,
            "monitor_folders": self.monitor_folders,
            "monitor_files": self.monitor_files,
            "ignored_patterns": self.ignored_patterns,
            "min_token_change": self.min_token_change,
            "cooldown_minutes": self.cooldown_minutes,
            "max_backups": self.max_backups,
            "notification_enabled": self.notification_enabled
        }

    def from_dict(self, config_dict):
        """Load configuration from dictionary"""
        self.enabled = config_dict.get("enabled", False)
        self.monitor_folders = config_dict.get("monitor_folders", [])
        self.monitor_files = config_dict.get("monitor_files", [])
        self.ignored_patterns = config_dict.get("ignored_patterns", ["*.tmp", "*.bak", "*~"])
        self.min_token_change = config_dict.get("min_token_change", 50)
        self.cooldown_minutes = config_dict.get("cooldown_minutes", 5)
        self.max_backups = config_dict.get("max_backups", 10)
        self.notification_enabled = config_dict.get("notification_enabled", True)

# -------------------------------
# Prompt Data Structures
# -------------------------------
class PromptRecord:
    """Represents a single prompt used with an LLM"""
    def __init__(self, prompt_text, llm_used="Unknown", description=""):
        self.id = str(uuid.uuid4())
        self.timestamp = datetime.now()
        self.prompt_text = prompt_text
        self.llm_used = llm_used
        self.description = description
        self.associated_files = []  # Files that this prompt was applied to
        self.file_changes = {}      # Map of file paths to token changes
        self.retroactive_notes = {} # Notes for retroactive associations
        self.source = "Unknown"     # Source of the prompt (Claude Desktop, Web Browser, etc.)
        
    def to_dict(self):
        """Convert to dictionary for storage"""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "prompt_text": self.prompt_text,
            "llm_used": self.llm_used,
            "description": self.description,
            "associated_files": self.associated_files,
            "file_changes": self.file_changes,
            "retroactive_notes": self.retroactive_notes
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create PromptRecord from dictionary"""
        record = cls("", "", "")
        record.id = data.get("id", str(uuid.uuid4()))
        
        # Parse timestamp
        timestamp_str = data.get("timestamp", "")
        try:
            # Handle multiple ISO format variations
            if 'T' in timestamp_str:
                # Full ISO format with T separator (2025-05-09T23:15:44.850257)
                record.timestamp = datetime.fromisoformat(timestamp_str)
            elif ' ' in timestamp_str:
                # Space-separated format (2025-05-09 23:15:44)
                record.timestamp = datetime.fromisoformat(timestamp_str)
            else:
                # Try to parse other formats
                formats = [
                    "%Y-%m-%d %H:%M:%S",
                    "%Y-%m-%d %H:%M:%S.%f",
                    "%Y-%m-%dT%H:%M:%S",
                    "%Y-%m-%dT%H:%M:%S.%f"
                ]
                parsed = False
                for fmt in formats:
                    try:
                        record.timestamp = datetime.strptime(timestamp_str, fmt)
                        parsed = True
                        break
                    except ValueError:
                        continue
                    
                if not parsed:
                    # If we couldn't parse it, use the original string but log a warning
                    print(f"Warning: Could not parse timestamp: {timestamp_str}")
                    record.timestamp = datetime.now()
        except (ValueError, TypeError) as e:
            print(f"Error parsing timestamp '{timestamp_str}': {e}")
            record.timestamp = datetime.now()
            
        record.prompt_text = data.get("prompt_text", "")
        record.llm_used = data.get("model", "Unknown")
        record.description = data.get("description", "")
        record.associated_files = data.get("files", [])
        record.file_changes = data.get("file_changes", {})
        record.retroactive_notes = data.get("retroactive_notes", {})
        
        return record

class PromptDatabase:
    """Manages a collection of prompt records"""
    def __init__(self):
        self.prompts = []
        self.active_prompt = None  # Currently active prompt
        
    def add_prompt(self, prompt_record):
        """Add a new prompt record"""
        self.prompts.append(prompt_record)
        self.active_prompt = prompt_record
        self.save()
        return prompt_record
    
    def get_prompt(self, prompt_id):
        """Get prompt by ID"""
        for prompt in self.prompts:
            if prompt.id == prompt_id:
                return prompt
        return None
    
    def get_recent_prompts(self, hours=24):
        """Get prompts from the last N hours"""
        cutoff = datetime.now() - timedelta(hours=hours)
        return [p for p in self.prompts if p.timestamp > cutoff]
    
    def get_prompts_for_file(self, file_path):
        """Get all prompts that affected a specific file"""
        return [p for p in self.prompts if file_path in p.associated_files]
    
    def associate_file_with_active_prompt(self, file_path, token_change=0):
        """Associate a file with the active prompt"""
        if self.active_prompt and file_path not in self.active_prompt.associated_files:
            self.active_prompt.associated_files.append(file_path)
            self.active_prompt.file_changes[file_path] = token_change
            self.save()
            return True
        return False
    
    def clear_active_prompt(self):
        """Clear the active prompt"""
        self.active_prompt = None
    
    def load(self):
        """Load prompts from storage, including Claude Desktop prompts"""
        prompts_loaded = False
        
        # Load from standard database file
        if os.path.exists("prompt_database.json"):
            try:
                with open("prompt_database.json", "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.prompts = [PromptRecord.from_dict(p) for p in data]
                prompts_loaded = True
            except Exception as e:
                print(f"Error loading prompt database: {e}")
        
        # Load from Claude Desktop prompts file
        claude_prompts_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "claude_prompts.json")
        if os.path.exists(claude_prompts_path):
            try:
                with open(claude_prompts_path, "r", encoding="utf-8") as f:
                    claude_data = json.load(f)
                
                # Convert Claude prompts to PromptRecord format
                for p in claude_data:
                    # Skip if this prompt ID already exists in our database
                    if any(existing.id == p.get("id") for existing in self.prompts):
                        continue
                    
                    # Create a new PromptRecord from the Claude prompt
                    record = PromptRecord(
                        prompt_text=p.get("prompt_text", ""),
                        llm_used=p.get("model", "Claude Desktop"),  # Use the model field or default to Claude Desktop
                        description=p.get("description", "")
                    )
                    record.id = p.get("id")  # Use the original ID
                    
                    # ADD THIS SECTION TO COPY FILES
                    if "files" in p and isinstance(p["files"], list):
                        record.associated_files = p["files"].copy()
                    
                    # Add to database
                    self.prompts.append(record)
                
                print(f"Loaded {len(claude_data)} prompts from Claude Desktop")
                prompts_loaded = True
            except Exception as e:
                print(f"Error loading Claude Desktop prompts: {e}")
        
        return prompts_loaded

    def save(self):
        """Save prompts to storage"""
        try:
            data = [p.to_dict() for p in self.prompts]
            with open("prompt_database.json", "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
            return True
        except Exception as e:
            print(f"Error saving prompt database: {e}")
            return False

# -------------------------------
# File Change Monitoring for Auto-Backup
# -------------------------------
class EnhancedFileChangeHandler(FileSystemEventHandler):
    """Enhanced handler for file system events with prompt awareness"""
    def __init__(self, app, config):
        self.app = app
        self.config = config
        self.pending_changes = set()
        super().__init__()

    def on_modified(self, event):
        """Called when a file is modified"""
        if event.is_directory:
            return
        
        # Check if this file should be monitored
        if not self._should_monitor_file(event.src_path):
            return
            
        # Add to pending changes to be processed
        self.pending_changes.add(event.src_path)
        self.app.log(f"Change detected in file: {event.src_path}")
        
        # Schedule processing if not already scheduled
        if not hasattr(self, '_processing_scheduled'):
            self._processing_scheduled = True
            self.app.master.after(1000, self._process_changes)  # 1-second delay
    
    def _should_monitor_file(self, file_path):
        """Check if the file should be monitored based on config"""
        # Check if file is directly monitored
        if file_path in self.config.monitor_files:
            return True
        
        # Check if file is in a monitored folder
        for folder in self.config.monitor_folders:
            if file_path.startswith(folder):
                # Check if the file matches any ignored pattern
                for pattern in self.config.ignored_patterns:
                    if self._matches_pattern(file_path, pattern):
                        return False
                return True
        
        return False
    
    def _matches_pattern(self, filename, pattern):
        """Check if a filename matches a pattern"""
        return fnmatch.fnmatch(os.path.basename(filename), pattern)
    
    def _process_changes(self):
        """Process all pending file changes with prompt awareness"""
        self._processing_scheduled = False
        
        if not self.pending_changes:
            return
            
        # Check cooldown period
        if self.config.last_backup_time:
            elapsed = datetime.now() - self.config.last_backup_time
            if elapsed < timedelta(minutes=self.config.cooldown_minutes):
                self.app.log(f"Cooldown period active. Next auto-backup available in {self.config.cooldown_minutes - elapsed.total_seconds()/60:.1f} minutes")
                return
        
        # Get the active prompt if any
        if hasattr(self.app, 'prompt_database') and self.app.prompt_database.active_prompt:
            # If there's an active prompt, associate changed files with it
            for file_path in self.pending_changes:
                # Calculate token change
                try:
                    # Get current tokens
                    current_tokens = count_tokens_in_file(file_path)
                    
                    # Associate with active prompt
                    self.app.prompt_database.associate_file_with_active_prompt(file_path, current_tokens)
                except Exception as e:
                    self.app.log(f"Error processing prompt association for {file_path}: {e}")
                
        significant_changes = self._check_for_significant_changes()
        
        if significant_changes:
            # Use the enhanced backup method if available
            if hasattr(self.app, 'trigger_auto_backup_with_prompts'):
                self.app.trigger_auto_backup_with_prompts(significant_changes)
            else:
                self.app.trigger_auto_backup(significant_changes)
            
        self.pending_changes.clear()
        
    def _check_for_significant_changes(self):
        """Check if changes are significant enough to trigger a backup"""
        significant_changes = []
        
        for file_path in self.pending_changes:
            try:
                # Calculate current hash and token count
                with open(file_path, "rb") as f:
                    content = f.read()
                current_hash = hashlib.md5(content).hexdigest()
                current_tokens = count_tokens_in_file(file_path)
                
                # Compare with stored hash and token count
                if file_path in self.config.file_hashes:
                    prev_hash, prev_tokens = self.config.file_hashes[file_path]
                    
                    if current_hash != prev_hash:
                        # Hash changed, check token difference
                        token_change = abs(current_tokens - prev_tokens)
                        
                        if token_change >= self.config.min_token_change:
                            self.app.log(f"Significant change detected in {file_path}: {token_change} tokens changed")
                            significant_changes.append((file_path, token_change))
                else:
                    # First time seeing this file, consider it a significant change
                    significant_changes.append((file_path, current_tokens))
                
                # Update stored hash and token count
                self.config.file_hashes[file_path] = (current_hash, current_tokens)
                
            except Exception as e:
                self.app.log(f"Error processing change for {file_path}: {e}")
        
        return significant_changes

# -------------------------------
# Main Application Class
# -------------------------------
class App:
    def __init__(self, master):
        self.master = master
        master.title("Project-to-LLM Prep Tool")
        self.profiles = load_profiles()
        self.current_profile = None

        self.folders = []
        self.all_files = []
        self.filtered_files = []
        self.backup_files = {}  # For storing parsed backup files

        self.allowed_extensions = ".py,.kt,.xml,.html,.js,.txt,.md,.json,.css,.bat,.db,.p12,.pem,.sh,.env,.R"
        self.min_tokens = 0

        # -------------------------------
        # Menu (Theme Dropdown)
        # -------------------------------
        menubar = tk.Menu(master)
        # Create a submenu for themes.
        theme_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Theme", menu=theme_menu)
        master.config(menu=menubar)

        # -------------------------------
        # Top Frame: Profile, Theme Dropdown, & Drag-n-Drop Simulation
        # -------------------------------
        top_frame = ttk.Frame(master)
        top_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Label(top_frame, text="Profile:").grid(row=0, column=0, sticky="w")
        self.profile_combo = ttk.Combobox(top_frame, values=list(self.profiles.keys()))
        self.profile_combo.grid(row=0, column=1, sticky="ew", padx=5)
        self.profile_combo.bind("<<ComboboxSelected>>", self.load_profile)
        top_frame.columnconfigure(1, weight=1)
        ttk.Button(top_frame, text="Save Profile", command=self.save_current_profile).grid(row=0, column=2, padx=5)
        ttk.Button(top_frame, text="New Profile", command=self.new_profile).grid(row=0, column=3, padx=5)
        # Theme Dropdown: populate with all available ttk themes.
        ttk.Label(top_frame, text="Theme:").grid(row=0, column=4, sticky="w", padx=(10,0))
        self.theme_combo = ttk.Combobox(top_frame, state="readonly")
        self.theme_combo.grid(row=0, column=5, padx=5)
        self.theme_combo.bind("<<ComboboxSelected>>", self.change_theme)
        # Drag-n-Drop simulation.
        self.dd_label = ttk.Label(top_frame, text="(Click here to add files/folders)", foreground="blue", cursor="hand2")
        self.dd_label.grid(row=1, column=0, columnspan=6, sticky="w", pady=(2,0))
        self.dd_label.bind("<Button-1>", self.simulate_drop)

        # -------------------------------
        # Paned Window: Left Controls & Right Notebook
        # -------------------------------
        self.paned = ttk.PanedWindow(master, orient=tk.HORIZONTAL)
        self.paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.control_frame = ttk.Frame(self.paned)
        self.paned.add(self.control_frame, weight=1)
        self.notebook = ttk.Notebook(self.paned)
        self.paned.add(self.notebook, weight=2)

        # -------------------------------
        # Left Controls
        # -------------------------------
        sel_frame = ttk.LabelFrame(self.control_frame, text="Selection")
        sel_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        ttk.Button(sel_frame, text="Add Folder", command=self.add_folder).grid(row=0, column=0, padx=2, pady=2)
        ttk.Button(sel_frame, text="Add File(s)", command=self.add_files).grid(row=0, column=1, padx=2, pady=2)
        ttk.Button(sel_frame, text="Scan Folders", command=self.scan_folders).grid(row=0, column=2, padx=2, pady=2)

        # Updated Filters with Ignore Folders field.
        filter_frame = ttk.LabelFrame(self.control_frame, text="Filters")
        filter_frame.grid(row=1, column=0, sticky="ew", padx=5, pady=5)
        # Extensions entry
        ttk.Label(filter_frame, text="Extensions (comma‑separated):").grid(row=0, column=0, sticky="w")
        self.ext_entry = ttk.Entry(filter_frame)
        self.ext_entry.insert(0, self.allowed_extensions)
        self.ext_entry.grid(row=0, column=1, sticky="ew", padx=5)
        # Min Tokens entry
        ttk.Label(filter_frame, text="Min Tokens:").grid(row=1, column=0, sticky="w")
        self.min_token_entry = ttk.Entry(filter_frame)
        self.min_token_entry.insert(0, str(self.min_tokens))
        self.min_token_entry.grid(row=1, column=1, sticky="ew", padx=5)
        # New: Ignored Folders entry
        ttk.Label(filter_frame, text="Ignore Folders (comma‑separated):").grid(row=2, column=0, sticky="w")
        self.ignore_entry = ttk.Entry(filter_frame)
        # Set a default ignored folder e.g. "node_modules & venv"
        self.ignore_entry.insert(0, "node_modules, __pycache__, Archive, archive, venv, ex")
        self.ignore_entry.grid(row=2, column=1, sticky="ew", padx=5)
        filter_frame.columnconfigure(1, weight=1)
        ttk.Button(filter_frame, text="Apply Filters", command=self.apply_filters).grid(row=3, column=0, columnspan=2, pady=2)

        opt_frame = ttk.LabelFrame(self.control_frame, text="Header / Footer")
        opt_frame.grid(row=2, column=0, sticky="ew", padx=5, pady=5)
        ttk.Label(opt_frame, text="Header:").grid(row=0, column=0, sticky="w")
        self.header_entry = ttk.Entry(opt_frame)
        self.header_entry.grid(row=0, column=1, sticky="ew", padx=5)
        ttk.Label(opt_frame, text="Footer:").grid(row=1, column=0, sticky="w")
        self.footer_entry = ttk.Entry(opt_frame)
        self.footer_entry.grid(row=1, column=1, sticky="ew", padx=5)
        opt_frame.columnconfigure(1, weight=1)
        self.header_entry.bind("<KeyRelease>", lambda event: self.update_preview())
        self.footer_entry.bind("<KeyRelease>", lambda event: self.update_preview())

        action_frame = ttk.Frame(self.control_frame)
        action_frame.grid(row=3, column=0, sticky="ew", padx=5, pady=5)
        ttk.Button(action_frame, text="Combine Scripts", command=self.combine_scripts).grid(row=0, column=0, padx=2)

        self.progress = ttk.Progressbar(self.control_frame, mode="determinate")
        self.progress.grid(row=4, column=0, sticky="ew", padx=5, pady=5)

        file_tree_frame = ttk.LabelFrame(self.control_frame, text="Selected Files")
        file_tree_frame.grid(row=5, column=0, sticky="nsew", padx=5, pady=5)
        self.file_tree = ttk.Treeview(file_tree_frame, columns=("path", "tokens"), show="headings")
        self.file_tree.heading("path", text="File Path")
        self.file_tree.heading("tokens", text="Tokens")
        self.file_tree.column("path", width=200)
        self.file_tree.column("tokens", width=80, anchor="e")
        self.file_tree.pack(fill=tk.BOTH, expand=True)
        ttk.Button(file_tree_frame, text="Remove Selected File(s)", command=self.remove_selected_files).pack(pady=2)

        folder_tree_frame = ttk.LabelFrame(self.control_frame, text="Selected Folders")
        folder_tree_frame.grid(row=6, column=0, sticky="nsew", padx=5, pady=5)
        self.folder_tree = ttk.Treeview(folder_tree_frame, columns=("folder", "tokens"), show="headings")
        self.folder_tree.heading("folder", text="Folder Path")
        self.folder_tree.heading("tokens", text="Tokens")
        self.folder_tree.column("folder", width=200)
        self.folder_tree.column("tokens", width=80, anchor="e")
        self.folder_tree.pack(fill=tk.BOTH, expand=True)
        ttk.Button(folder_tree_frame, text="Remove Selected Folder(s)", command=self.remove_selected_folders).pack(pady=2)

        self.control_frame.columnconfigure(0, weight=1)
        self.control_frame.rowconfigure(6, weight=1)

        self.initialize_eadr_notes_tab()        # Move this if wanted in a different spot

        # Then create the Preview tab
        self.preview_frame = ttk.Frame(self.notebook)
        self.preview_text = scrolledtext.ScrolledText(self.preview_frame, wrap="word")
        self.preview_text.pack(fill=tk.BOTH, expand=True)
        self.token_frame = ttk.Frame(self.preview_frame)
        self.token_frame.pack(fill=tk.X)
        self.token_with_label = ttk.Label(self.token_frame, text="Tokens (with headers): 0")
        self.token_with_label.pack(side=tk.LEFT, padx=5)
        self.token_without_label = ttk.Label(self.token_frame, text="Tokens (without headers): 0")
        self.token_without_label.pack(side=tk.LEFT, padx=5)
        self.notebook.add(self.preview_frame, text="Preview")

        self.log_text = scrolledtext.ScrolledText(self.notebook, wrap="word", foreground="red")
        self.notebook.add(self.log_text, text="Logs")

        # -------------------------------
        # Right Notebook Tabs
        # -------------------------------

        self.initialize_prompt_tracking_tab()
        self.initialize_auto_backup_tab()     
        self.initialize_browser_extension_tab()
        self.initialize_rollback_tab()
        self.add_proxy_button_to_prompt_tab()

        self.help_text = scrolledtext.ScrolledText(self.notebook, wrap="word")
        self.help_text.insert(tk.END, (
            "Usage Tips and Instructions:\n\n"
            "1. **Adding Items:**\n"
            "   - Click 'Add Folder' or 'Add File(s)', or click the '(Click here to add files/folders)' area.\n\n"
            "2. **Scanning Folders:**\n"
            "   - Use 'Scan Folders' to search folders for files matching the specified extensions.\n\n"
            "3. **Filtering:**\n"
            "   - Adjust the allowed extensions, minimum token count, and folders to ignore, then click 'Apply Filters'.\n\n"
            "4. **Preview & Token Counts:**\n"
            "   - The 'Preview' tab shows the combined text and live token counts (with and without extra headers).\n\n"
            "5. **Removing Items:**\n"
            "   - In the 'Selected Files' and 'Selected Folders' sections, select items and click the remove buttons.\n\n"
            "6. **Combining Scripts:**\n"
            "   - Click 'Combine Scripts' to generate a markdown file (saved in the 'backup' folder).\n\n"
            "7. **Profiles:**\n"
            "   - Save your current settings as a profile or create a new profile using the options at the top.\n\n"
            "8. **eADR Notes:**\n"
            "   - Add progress notes about your project using the eADR Notes tab.\n"
            "   - Notes are automatically created when you combine scripts.\n\n"
            "9. **Rollback:**\n"
            "   - Use the Rollback tab to restore files from a previous backup.\n"
            "   - Select a backup file, choose which files to restore, and review changes before committing.\n\n"
            "10. **Prompt Tracking:**\n"
            "   - Record LLM prompts used to generate or modify files.\n"
            "   - Associate prompts with files for complete project history.\n"
            "   - Use retroactive associations if you forgot to record prompts.\n\n"
            "11. **Auto-Backup:**\n"
            "   - Set up automatic backups when files change.\n"
            "   - Monitor specific files or folders.\n"
            "   - Configure backup frequency and other settings.\n\n"
            "Enjoy using this tool to prepare your project for LLM inputs!"
        ))
        self.help_text.config(state=tk.DISABLED)
        self.notebook.add(self.help_text, text="Help")

        self.about_text = scrolledtext.ScrolledText(self.notebook, wrap="word")
        self.about_text.insert(tk.END, (
            "About This Tool:\n\n"
            "Project-to-LLM Prep Tool\n"
            "Version 1.2\n\n"
            "Created by: Anthony Vigil\n"
            "Email: anthony.vigil@usf.edu\n\n"
            "Copyright © 2025 Anthony Vigil. All rights reserved.\n\n"
            "This tool was developed to help prepare code and project files for input into Large Language Models.\n\n"
            "Legal Notice: This software is provided 'as-is' without any express or implied warranty. "
            "In no event will the authors be held liable for any damages arising from the use of this software.\n\n"
            "Packages and Tools Used:\n"
            " - Python 3.x\n"
            " - Tkinter & ttk (for GUI development)\n"
            " - tiktoken (for GPT‑style token counting)\n"
            " - JSON (for configuration persistence)\n"
            " - difflib & re (for rollback functionality)\n"
            " - watchdog (for file change monitoring)\n\n"
            "For more information, please refer to the project's documentation or contact the author."
        ))
        self.about_text.config(state=tk.DISABLED)
        self.notebook.add(self.about_text, text="About")

        # -------------------------------
        # Set Default Theme and Populate Theme Dropdown
        # -------------------------------
        available_themes = self.master.tk.call("ttk::style", "theme", "names")
        self.theme_combo['values'] = available_themes
        self.set_theme(self.theme_combo.get() or available_themes[0])
        self.theme_combo.set(self.master.tk.call("ttk::style", "theme", "use"))

        # -------------------------------
        # Load Settings and Initialize Systems
        # -------------------------------
        self.prompt_database.load()
        self.load_auto_backup_settings()
        
        # -------------------------------
        # Command-Line Arguments
        # -------------------------------
        if len(sys.argv) > 1:
            for path in sys.argv[1:]:
                if os.path.isfile(path):
                    self.all_files.append(path)
                    self.log(f"Added via command-line: {path}")
                elif os.path.isdir(path):
                    self.folders.append(path)
                    self.scan_single_folder(path)
                    self.log(f"Added folder via command-line: {path}")
            self.apply_filters()

        # Refresh the UI  
        self.refresh_prompt_history()      

        # Initialize file watcher for Claude prompts
        claude_prompts_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "claude_prompts.json")
        self.claude_watcher = PromptFileWatcher(self, claude_prompts_path)
        
        # Start watching for changes
        self.claude_watcher.start()
        
        # Make sure to stop the watcher when the application closes
        master.protocol("WM_DELETE_WINDOW", self._on_close)

    def initialize_browser_extension_tab(self):
        """Initialize the Browser Extension tab in the notebook"""
        self.browser_ext_frame = ttk.Frame(self.notebook)
        
        # Server control section
        server_frame = ttk.LabelFrame(self.browser_ext_frame, text="Extension Server")
        server_frame.pack(fill=tk.X, padx=5, pady=5)
        
        server_control_frame = ttk.Frame(server_frame)
        server_control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Server status
        self.server_status_var = tk.StringVar(value="Inactive")
        self.server_status_frame = ttk.Frame(server_control_frame)
        self.server_status_frame.pack(side=tk.LEFT, padx=10)
        
        ttk.Label(self.server_status_frame, text="Server Status:").pack(side=tk.LEFT)
        self.server_status_label = ttk.Label(
            self.server_status_frame, 
            textvariable=self.server_status_var,
            foreground="red"
        )
        self.server_status_label.pack(side=tk.LEFT, padx=5)
        
        # Server control buttons
        self.start_server_btn = ttk.Button(
            server_control_frame,
            text="Start Server",
            command=self.start_extension_server
        )
        self.start_server_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_server_btn = ttk.Button(
            server_control_frame,
            text="Stop Server",
            command=self.stop_extension_server,
            state=tk.DISABLED
        )
        self.stop_server_btn.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            server_control_frame,
            text="Open Extension Settings",
            command=self.open_extension_settings
        ).pack(side=tk.RIGHT, padx=5)
        
        # Server info
        server_info_frame = ttk.Frame(server_frame)
        server_info_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(server_info_frame, text="Server URL:").pack(side=tk.LEFT)
        self.server_url_var = tk.StringVar(value="http://localhost:5000")
        ttk.Entry(server_info_frame, textvariable=self.server_url_var, width=30).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            server_info_frame,
            text="Check Status",
            command=self.check_server_status
        ).pack(side=tk.LEFT, padx=5)
        
        # Prompts section
        prompts_frame = ttk.LabelFrame(self.browser_ext_frame, text="Recorded Prompts")
        prompts_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create a paned window to split prompts list and details
        prompts_paned = ttk.PanedWindow(prompts_frame, orient=tk.HORIZONTAL)
        prompts_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Left side - prompts list
        prompts_list_frame = ttk.Frame(prompts_paned)
        
        # Create treeview with scrollbar
        prompts_tree_frame = ttk.Frame(prompts_list_frame)
        prompts_tree_frame.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        
        self.ext_prompts_tree = ttk.Treeview(
            prompts_tree_frame,
            columns=("date", "llm", "description"),
            show="headings"
        )
        
        self.ext_prompts_tree.heading("date", text="Date & Time")
        self.ext_prompts_tree.heading("llm", text="LLM")
        self.ext_prompts_tree.heading("description", text="Description")
        
        self.ext_prompts_tree.column("date", width=150)
        self.ext_prompts_tree.column("llm", width=100)
        self.ext_prompts_tree.column("description", width=250)
        
        self.ext_prompts_tree.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        
        # Scrollbar for prompts tree
        prompts_scrollbar = ttk.Scrollbar(prompts_tree_frame, orient="vertical", command=self.ext_prompts_tree.yview)
        prompts_scrollbar.pack(fill=tk.Y, side=tk.RIGHT)
        self.ext_prompts_tree.configure(yscrollcommand=prompts_scrollbar.set)
        
        # Buttons under tree
        prompts_button_frame = ttk.Frame(prompts_list_frame)
        prompts_button_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(
            prompts_button_frame,
            text="Refresh Prompts",
            command=self.refresh_extension_prompts
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            prompts_button_frame,
            text="Import All",
            command=self.import_all_prompts
        ).pack(side=tk.LEFT, padx=5)
        
        prompts_paned.add(prompts_list_frame, weight=1)
        
        # Right side - prompt details
        prompt_detail_frame = ttk.Frame(prompts_paned)
        
        # Prompt text
        prompt_text_frame = ttk.LabelFrame(prompt_detail_frame, text="Prompt Content")
        prompt_text_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.ext_prompt_text = scrolledtext.ScrolledText(prompt_text_frame, wrap=tk.WORD)
        self.ext_prompt_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # File association
        file_assoc_frame = ttk.LabelFrame(prompt_detail_frame, text="Associate with Files")
        file_assoc_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Radio buttons for selection mode
        self.file_selection_mode = tk.StringVar(value="current")
        
        ttk.Radiobutton(
            file_assoc_frame, 
            text="Use Current Selection", 
            variable=self.file_selection_mode,
            value="current"
        ).pack(anchor=tk.W, padx=5, pady=2)
        
        ttk.Radiobutton(
            file_assoc_frame, 
            text="Select Files Manually", 
            variable=self.file_selection_mode,
            value="manual"
        ).pack(anchor=tk.W, padx=5, pady=2)
        
        # Association buttons
        file_button_frame = ttk.Frame(file_assoc_frame)
        file_button_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(
            file_button_frame,
            text="Associate with Files",
            command=self.associate_prompt_with_files
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            file_button_frame,
            text="Import Selected Prompt",
            command=self.import_selected_prompt
        ).pack(side=tk.LEFT, padx=5)
        
        # Set as active prompt button
        ttk.Button(
            prompt_detail_frame,
            text="Set as Active Prompt",
            command=self.set_as_active_prompt
        ).pack(side=tk.RIGHT, padx=5, pady=5)
        
        prompts_paned.add(prompt_detail_frame, weight=2)
        
        # Bind events
        self.ext_prompts_tree.bind("<<TreeviewSelect>>", self.select_extension_prompt)
        
        # Add the tab to the notebook
        self.notebook.add(self.browser_ext_frame, text="Browser Extension")
        
        # Initialize server process variable
        self.server_process = None
        self.check_server_status()

    # Extension server management methods to add to the App class
    def start_extension_server(self):
        """Start the browser extension server"""
        if self.server_process is not None and self.server_process.poll() is None:
            messagebox.showinfo("Server Running", "The extension server is already running.")
            return
        
        try:
            # Determine the path to the server script
            script_dir = os.path.dirname(os.path.abspath(__file__))
            server_script = os.path.join(script_dir, "llm-prompt-recorder", "server", "app.py")
            
            if not os.path.exists(server_script):
                self.log(f"Server script not found at: {server_script}")
                
                # Try alternate locations
                alt_paths = [
                    os.path.join(script_dir, "server", "app.py"),
                    os.path.join(os.path.dirname(script_dir), "llm-prompt-recorder", "server", "app.py")
                ]
                
                for path in alt_paths:
                    if os.path.exists(path):
                        server_script = path
                        self.log(f"Found server script at: {server_script}")
                        break
                else:
                    raise FileNotFoundError(f"Could not find server script. Checked: {server_script} and alternates")
            
            # Start the server as a subprocess
            self.server_process = subprocess.Popen(
                [sys.executable, server_script],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Wait a bit for the server to start
            time.sleep(1)
            
            # Check if the server started successfully
            if self.server_process.poll() is not None:
                # Process has already terminated
                stdout, stderr = self.server_process.communicate()
                self.log(f"Server failed to start. Error: {stderr}")
                raise Exception(f"Server process failed: {stderr}")
            
            # Update UI
            self.server_status_var.set("Running")
            self.server_status_label.config(foreground="green")
            self.start_server_btn.config(state=tk.DISABLED)
            self.stop_server_btn.config(state=tk.NORMAL)
            
            # Start a thread to monitor the server output
            def monitor_server():
                for line in iter(self.server_process.stderr.readline, ''):
                    if line:
                        self.log(f"Server: {line.strip()}")
                
                for line in iter(self.server_process.stdout.readline, ''):
                    if line:
                        self.log(f"Server: {line.strip()}")
                
                # Process ended, update UI
                self.master.after_idle(self.update_server_status_stopped)
            
            threading.Thread(target=monitor_server, daemon=True).start()
            
            self.log("Extension server started successfully")
            messagebox.showinfo("Server Started", "The extension server is now running. You can use the browser extension to record prompts.")
            
        except Exception as e:
            self.log(f"Error starting server: {e}")
            messagebox.showerror("Error", f"Failed to start extension server:\n{e}")
            self.update_server_status_stopped()

    def stop_extension_server(self):
        """Stop the browser extension server"""
        if self.server_process is None or self.server_process.poll() is not None:
            messagebox.showinfo("Server Not Running", "The extension server is not running.")
            self.update_server_status_stopped()
            return
        
        try:
            # Try to terminate gracefully
            self.server_process.terminate()
            
            # Wait for process to terminate
            try:
                self.server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                # Force kill if it doesn't terminate
                self.server_process.kill()
                self.server_process.wait()
            
            self.log("Extension server stopped")
            messagebox.showinfo("Server Stopped", "The extension server has been stopped.")
            
        except Exception as e:
            self.log(f"Error stopping server: {e}")
            messagebox.showerror("Error", f"Failed to stop extension server:\n{e}")
        
        finally:
            self.update_server_status_stopped()

    def update_server_status_stopped(self):
        """Update UI elements when server is stopped"""
        self.server_status_var.set("Inactive")
        self.server_status_label.config(foreground="red")
        self.start_server_btn.config(state=tk.NORMAL)
        self.stop_server_btn.config(state=tk.DISABLED)
        self.server_process = None

    def check_server_status(self):
        """Check if the extension server is running"""
        try:
            # Get server URL from input
            server_url = self.server_url_var.get().strip()
            if not server_url:
                server_url = "http://localhost:5000"
            
            # Construct the ping URL
            ping_url = urljoin(server_url, '/ping')
            
            # Send a request with a short timeout
            response = requests.get(ping_url, timeout=1)
            
            if response.status_code == 200:
                data = response.json()
                
                # Update UI
                self.server_status_var.set("Running")
                self.server_status_label.config(foreground="green")
                self.start_server_btn.config(state=tk.DISABLED)
                self.stop_server_btn.config(state=tk.NORMAL)
                
                # Update log
                prompts_count = data.get('prompts_recorded', 0)
                self.log(f"Server is running. {prompts_count} prompts recorded.")
                
                return True
            else:
                self.server_status_var.set(f"Error: {response.status_code}")
                self.server_status_label.config(foreground="red")
                self.start_server_btn.config(state=tk.NORMAL)
                self.stop_server_btn.config(state=tk.DISABLED)
                
                self.log(f"Server error: HTTP {response.status_code}")
                return False
        
        except requests.exceptions.ConnectionError:
            # Server is not running
            self.server_status_var.set("Inactive")
            self.server_status_label.config(foreground="red")
            self.start_server_btn.config(state=tk.NORMAL)
            self.stop_server_btn.config(state=tk.DISABLED)
            
            self.log("Server is not running")
            return False
        
        except Exception as e:
            self.server_status_var.set(f"Error: {str(e)[:20]}...")
            self.server_status_label.config(foreground="red")
            
            self.log(f"Error checking server status: {e}")
            return False

    def open_extension_settings(self):
        """Open the browser extension settings page"""
        # For Chrome, Edge, Brave
        browsers = [
            "chrome://extensions/?id=",  # Chrome
            "edge://extensions/?id=",    # Edge
            "brave://extensions/?id="    # Brave
        ]
        
        messagebox.showinfo(
            "Open Extension Settings",
            "To access the extension settings, please:\n\n"
            "1. Open your browser's extensions page\n"
            "2. Find the 'LLM Prompt Recorder' extension\n"
            "3. Click on 'Details' or the settings icon\n\n"
            "Would you like to open the extensions page now?"
        )
        
        # Try to open the extensions page
        try:
            # Just open the extensions page (we don't know the extension ID)
            webbrowser.open("chrome://extensions/")
        except Exception:
            try:
                webbrowser.open("edge://extensions/")
            except Exception:
                try:
                    webbrowser.open("brave://extensions/")
                except Exception as e:
                    self.log(f"Error opening browser extensions page: {e}")
                    messagebox.showerror(
                        "Error",
                        "Failed to open the extensions page. Please open it manually in your browser."
                    )

    # Prompt management methods to add to the App class
    def refresh_extension_prompts(self):
        """Refresh the list of prompts from the extension server"""
        try:
            # Clear the current list
            for item in self.ext_prompts_tree.get_children():
                self.ext_prompts_tree.delete(item)
            
            # Check if server is running
            if not self.check_server_status():
                messagebox.showinfo("Server Not Running", "The extension server is not running. Please start it first.")
                return
            
            # Get server URL from input
            server_url = self.server_url_var.get().strip()
            if not server_url:
                server_url = "http://localhost:5000"
            
            # Construct the prompts URL
            prompts_url = urljoin(server_url, '/prompts')
            
            # Send a request
            response = requests.get(prompts_url, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('success', False):
                    prompts = data.get('prompts', [])
                    
                    # Sort prompts by timestamp (newest first)
                    prompts.sort(key=lambda p: p.get('timestamp', ''), reverse=True)
                    
                    # Add to treeview
                    for prompt in prompts:
                        timestamp = datetime.fromisoformat(prompt.get('timestamp')).strftime("%Y-%m-%d %H:%M")
                        llm_used = prompt.get('llm_used', 'Unknown')
                        description = prompt.get('description', 'No description')
                        
                        self.ext_prompts_tree.insert(
                            "", tk.END,
                            iid=prompt.get('id'),
                            values=(timestamp, llm_used, description),
                            tags=(prompt.get('id'),)
                        )
                    
                    self.log(f"Refreshed prompts from server. Found {len(prompts)} prompts.")
                else:
                    error = data.get('error', 'Unknown error')
                    self.log(f"Error retrieving prompts: {error}")
                    messagebox.showerror("Error", f"Failed to retrieve prompts:\n{error}")
            else:
                self.log(f"Server error: HTTP {response.status_code}")
                messagebox.showerror("Error", f"Server returned an error: HTTP {response.status_code}")
        
        except Exception as e:
            self.log(f"Error refreshing prompts: {e}")
            messagebox.showerror("Error", f"Failed to refresh prompts:\n{e}")

    def select_extension_prompt(self, event):
        """Handle selection of a prompt in the extension prompts tree"""
        selection = self.ext_prompts_tree.selection()
        if not selection:
            # Clear the display
            self.ext_prompt_text.delete("1.0", tk.END)
            return
        
        # Get the prompt ID
        prompt_id = selection[0]
        
        try:
            # Get server URL from input
            server_url = self.server_url_var.get().strip()
            if not server_url:
                server_url = "http://localhost:5000"
            
            # Construct the prompts URL
            prompts_url = urljoin(server_url, '/prompts')
            
            # Send a request
            response = requests.get(prompts_url, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('success', False):
                    prompts = data.get('prompts', [])
                    
                    # Find the selected prompt
                    for prompt in prompts:
                        if prompt.get('id') == prompt_id:
                            # Display the prompt content
                            self.ext_prompt_text.delete("1.0", tk.END)
                            
                            # Show prompt metadata
                            timestamp = datetime.fromisoformat(prompt.get('timestamp')).strftime("%Y-%m-%d %H:%M:%S")
                            self.ext_prompt_text.insert(tk.END, f"Date & Time: {timestamp}\n")
                            self.ext_prompt_text.insert(tk.END, f"LLM: {prompt.get('llm_used', 'Unknown')}\n")
                            self.ext_prompt_text.insert(tk.END, f"Description: {prompt.get('description', 'No description')}\n\n")
                            
                            # Show prompt text
                            self.ext_prompt_text.insert(tk.END, "Prompt Text:\n")
                            self.ext_prompt_text.insert(tk.END, prompt.get('prompt_text', 'No prompt text'))
                            
                            # Show associated files if any
                            associated_files = prompt.get('associated_files', [])
                            if associated_files:
                                self.ext_prompt_text.insert(tk.END, "\n\nAssociated Files:\n")
                                for file_path in associated_files:
                                    self.ext_prompt_text.insert(tk.END, f"- {file_path}\n")
                            
                            break
        
        except Exception as e:
            self.log(f"Error displaying prompt: {e}")
            self.ext_prompt_text.delete("1.0", tk.END)
            self.ext_prompt_text.insert(tk.END, f"Error displaying prompt: {e}")

    def import_selected_prompt(self):
        """Import the selected prompt from the extension into the prompt database"""
        selection = self.ext_prompts_tree.selection()
        if not selection:
            messagebox.showinfo("No Selection", "Please select a prompt to import.")
            return
        
        # Get the prompt ID
        prompt_id = selection[0]
        
        try:
            # Get server URL from input
            server_url = self.server_url_var.get().strip()
            if not server_url:
                server_url = "http://localhost:5000"
            
            # Construct the prompts URL
            prompts_url = urljoin(server_url, '/prompts')
            
            # Send a request
            response = requests.get(prompts_url, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('success', False):
                    prompts = data.get('prompts', [])
                    
                    # Find the selected prompt
                    for prompt in prompts:
                        if prompt.get('id') == prompt_id:
                            # Create a new prompt record
                            prompt_text = prompt.get('prompt_text', '')
                            llm_used = prompt.get('llm_used', 'Unknown LLM')
                            description = prompt.get('description', 'Imported from browser extension')
                            
                            # Check if this prompt already exists in the database
                            existing_prompt = None
                            for p in self.prompt_database.prompts:
                                if p.id == prompt_id:
                                    existing_prompt = p
                                    break
                            
                            if existing_prompt:
                                # Update the existing prompt if needed
                                if existing_prompt.prompt_text != prompt_text or existing_prompt.llm_used != llm_used:
                                    existing_prompt.prompt_text = prompt_text
                                    existing_prompt.llm_used = llm_used
                                    existing_prompt.description = description
                                    self.prompt_database.save()
                                    self.log(f"Updated existing prompt: {description}")
                                    messagebox.showinfo("Prompt Updated", f"The prompt '{description}' has been updated.")
                                else:
                                    self.log(f"Prompt already exists: {description}")
                                    messagebox.showinfo("Prompt Exists", f"The prompt '{description}' already exists in the database.")
                            else:
                                # Create a new prompt record
                                new_prompt = PromptRecord(prompt_text, llm_used, description)
                                new_prompt.id = prompt_id  # Use the same ID as the extension
                                
                                # Copy associated files if any
                                associated_files = prompt.get('associated_files', [])
                                for file_path in associated_files:
                                    new_prompt.associated_files.append(file_path)
                                
                                # Add to database
                                self.prompt_database.prompts.append(new_prompt)
                                self.prompt_database.save()
                                
                                self.log(f"Imported prompt: {description}")
                                messagebox.showinfo("Prompt Imported", f"The prompt '{description}' has been imported.")
                            
                            # Update the prompt tracking tab
                            self.refresh_prompt_history()
                            return
                    
                    # If we get here, the prompt wasn't found
                    messagebox.showerror("Error", "Could not find the selected prompt in the server response.")
                else:
                    error = data.get('error', 'Unknown error')
                    self.log(f"Error retrieving prompts: {error}")
                    messagebox.showerror("Error", f"Failed to retrieve prompts:\n{error}")
            else:
                self.log(f"Server error: HTTP {response.status_code}")
                messagebox.showerror("Error", f"Server returned an error: HTTP {response.status_code}")
        
        except Exception as e:
            self.log(f"Error importing prompt: {e}")
            messagebox.showerror("Error", f"Failed to import prompt:\n{e}")

    def import_all_prompts(self):
        """Import all prompts from the extension server into the prompt database"""
        try:
            # Check if server is running
            if not self.check_server_status():
                messagebox.showinfo("Server Not Running", "The extension server is not running. Please start it first.")
                return
            
            # Get server URL from input
            server_url = self.server_url_var.get().strip()
            if not server_url:
                server_url = "http://localhost:5000"
            
            # Construct the prompts URL
            prompts_url = urljoin(server_url, '/prompts')
            
            # Send a request
            response = requests.get(prompts_url, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('success', False):
                    prompts = data.get('prompts', [])
                    
                    # Track counts for reporting
                    imported_count = 0
                    updated_count = 0
                    unchanged_count = 0
                    
                    for prompt in prompts:
                        prompt_id = prompt.get('id')
                        prompt_text = prompt.get('prompt_text', '')
                        llm_used = prompt.get('llm_used', 'Unknown LLM')
                        description = prompt.get('description', 'Imported from browser extension')
                        
                        # Check if this prompt already exists in the database
                        existing_prompt = None
                        for p in self.prompt_database.prompts:
                            if p.id == prompt_id:
                                existing_prompt = p
                                break
                        
                        if existing_prompt:
                            # Update the existing prompt if needed
                            if existing_prompt.prompt_text != prompt_text or existing_prompt.llm_used != llm_used:
                                existing_prompt.prompt_text = prompt_text
                                existing_prompt.llm_used = llm_used
                                existing_prompt.description = description
                                updated_count += 1
                            else:
                                unchanged_count += 1
                        else:
                            # Create a new prompt record
                            new_prompt = PromptRecord(prompt_text, llm_used, description)
                            new_prompt.id = prompt_id  # Use the same ID as the extension
                            
                            # Copy associated files if any
                            associated_files = prompt.get('associated_files', [])
                            for file_path in associated_files:
                                new_prompt.associated_files.append(file_path)
                            
                            # Add to database
                            self.prompt_database.prompts.append(new_prompt)
                            imported_count += 1
                    
                    # Save changes
                    if imported_count > 0 or updated_count > 0:
                        self.prompt_database.save()
                    
                    # Log results
                    self.log(f"Import complete: {imported_count} imported, {updated_count} updated, {unchanged_count} unchanged")
                    
                    # Update the prompt tracking tab
                    self.refresh_prompt_history()
                    
                    # Show message
                    messagebox.showinfo(
                        "Import Complete",
                        f"Import complete:\n"
                        f"- {imported_count} prompts imported\n"
                        f"- {updated_count} prompts updated\n"
                        f"- {unchanged_count} prompts unchanged"
                    )
                else:
                    error = data.get('error', 'Unknown error')
                    self.log(f"Error retrieving prompts: {error}")
                    messagebox.showerror("Error", f"Failed to retrieve prompts:\n{error}")
            else:
                self.log(f"Server error: HTTP {response.status_code}")
                messagebox.showerror("Error", f"Server returned an error: HTTP {response.status_code}")
        
        except Exception as e:
            self.log(f"Error importing prompts: {e}")
            messagebox.showerror("Error", f"Failed to import prompts:\n{e}")

    def associate_prompt_with_files(self):
        """Associate the selected prompt with files"""
        selection = self.ext_prompts_tree.selection()
        if not selection:
            messagebox.showinfo("No Selection", "Please select a prompt to associate with files.")
            return
        
        # Get the prompt ID
        prompt_id = selection[0]
        
        # Get the files to associate
        files_to_associate = []
        
        if self.file_selection_mode.get() == "current":
            # Use the current selection
            files_to_associate = self.filtered_files
        else:
            # Manual selection
            filetypes = [("All files", "*.*")]
            selected_files = filedialog.askopenfilenames(title="Select Files to Associate", filetypes=filetypes)
            files_to_associate = list(selected_files)
        
        if not files_to_associate:
            messagebox.showinfo("No Files", "No files selected for association.")
            return
        
        try:
            # First, try to import the prompt if it's not already in our database
            # Get server URL from input
            server_url = self.server_url_var.get().strip()
            if not server_url:
                server_url = "http://localhost:5000"
            
            # Construct the prompts URL
            prompts_url = urljoin(server_url, '/prompts')
            
            # Send a request
            response = requests.get(prompts_url, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('success', False):
                    prompts = data.get('prompts', [])
                    
                    # Find the selected prompt
                    imported_prompt = None
                    for prompt in prompts:
                        if prompt.get('id') == prompt_id:
                            # Check if this prompt already exists in the database
                            existing_prompt = None
                            for p in self.prompt_database.prompts:
                                if p.id == prompt_id:
                                    existing_prompt = p
                                    break
                            
                            if existing_prompt:
                                # Use the existing prompt
                                imported_prompt = existing_prompt
                            else:
                                # Create a new prompt record
                                prompt_text = prompt.get('prompt_text', '')
                                llm_used = prompt.get('llm_used', 'Unknown LLM')
                                description = prompt.get('description', 'Imported from browser extension')
                                
                                new_prompt = PromptRecord(prompt_text, llm_used, description)
                                new_prompt.id = prompt_id  # Use the same ID as the extension
                                
                                # Copy associated files if any
                                associated_files = prompt.get('associated_files', [])
                                for file_path in associated_files:
                                    new_prompt.associated_files.append(file_path)
                                
                                # Add to database
                                self.prompt_database.prompts.append(new_prompt)
                                self.prompt_database.save()
                                
                                imported_prompt = new_prompt
                                self.log(f"Imported prompt: {description}")
                            
                            break
                    
                    if imported_prompt:
                        # Now associate the files with the prompt
                        new_associations = 0
                        for file_path in files_to_associate:
                            if file_path not in imported_prompt.associated_files:
                                imported_prompt.associated_files.append(file_path)
                                imported_prompt.file_changes[file_path] = 0  # Default token change
                                new_associations += 1
                        
                        if new_associations > 0:
                            # Save changes
                            self.prompt_database.save()
                            
                            # Log results
                            self.log(f"Associated {new_associations} files with prompt: {imported_prompt.description}")
                            
                            # Update the prompt tracking tab
                            self.refresh_prompt_history()
                            
                            # Show message
                            messagebox.showinfo(
                                "Association Complete",
                                f"Associated {new_associations} files with the prompt."
                            )
                        else:
                            messagebox.showinfo("No Changes", "All selected files are already associated with this prompt.")
                        
                        # Also update the server if possible
                        try:
                            for file_path in files_to_associate:
                                associate_url = urljoin(server_url, '/associate_prompt')
                                requests.post(associate_url, json={
                                    'prompt_id': prompt_id,
                                    'file_path': file_path
                                }, timeout=5)
                        except Exception as e:
                            self.log(f"Warning: Failed to update server associations: {e}")
                    else:
                        messagebox.showerror("Error", "Could not find the selected prompt in the server response.")
                else:
                    error = data.get('error', 'Unknown error')
                    self.log(f"Error retrieving prompts: {error}")
                    messagebox.showerror("Error", f"Failed to retrieve prompts:\n{error}")
            else:
                self.log(f"Server error: HTTP {response.status_code}")
                messagebox.showerror("Error", f"Server returned an error: HTTP {response.status_code}")
        
        except Exception as e:
            self.log(f"Error associating files: {e}")
            messagebox.showerror("Error", f"Failed to associate files:\n{e}")

    def add_proxy_button_to_prompt_tab(self):
        """Add a button to start the proxy recorder in the prompt tracking tab"""
        
        # Create a button frame if it doesn't exist
        if not hasattr(self, 'action_frame') or not self.action_frame:
            self.action_frame = ttk.Frame(self.prompt_frame)
            self.action_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Add proxy control section
        proxy_control_frame = ttk.LabelFrame(self.prompt_frame, text="Proxy Recorder")
        proxy_control_frame.pack(fill=tk.X, padx=5, pady=5, before=self.active_prompt_frame)
        
        # Status indicator
        self.proxy_status_var = tk.StringVar(value="Inactive")
        status_frame = ttk.Frame(proxy_control_frame)
        status_frame.pack(side=tk.LEFT, padx=10, pady=5)
        
        ttk.Label(status_frame, text="Status:").pack(side=tk.LEFT)
        self.proxy_status_label = ttk.Label(
            status_frame, 
            textvariable=self.proxy_status_var,
            foreground="red"
        )
        self.proxy_status_label.pack(side=tk.LEFT, padx=5)
        
        # Control buttons
        buttons_frame = ttk.Frame(proxy_control_frame)
        buttons_frame.pack(side=tk.RIGHT, padx=10, pady=5)
        
        self.start_proxy_btn = ttk.Button(
            buttons_frame,
            text="Start Proxy Recorder",
            command=self.start_proxy_recorder
        )
        self.start_proxy_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_proxy_btn = ttk.Button(
            buttons_frame,
            text="Stop Proxy Recorder",
            command=self.stop_proxy_recorder,
            state=tk.DISABLED
        )
        self.stop_proxy_btn.pack(side=tk.LEFT, padx=5)
        
        # Import button
        self.import_btn = ttk.Button(
            buttons_frame,
            text="Import From DB",
            command=self.import_from_sqlite_db
        )
        self.import_btn.pack(side=tk.LEFT, padx=5)      

    def start_proxy_recorder(self):
        """Start the proxy recorder server using existing scripts"""
        if hasattr(self, 'proxy_process') and self.proxy_process is not None and self.proxy_process.poll() is None:
            messagebox.showinfo("Proxy Running", "The proxy recorder is already running.")
            return
        
        try:
            # Determine the path to the start script
            script_dir = os.path.dirname(os.path.abspath(__file__))
            script_path = None
            
            if os.name == 'nt':  # Windows
                script_path = os.path.join(script_dir, "llm-proxy-recorder", "start_proxy.bat")
            else:  # Unix/Mac
                script_path = os.path.join(script_dir, "llm-proxy-recorder", "start_proxy.sh")
            
            if not os.path.exists(script_path):
                self.log(f"Start script not found at: {script_path}")
                
                # Try alternate locations
                if os.name == 'nt':
                    alt_paths = [
                        os.path.join(script_dir, "start_proxy.bat"),
                        os.path.join(os.path.dirname(script_dir), "llm-proxy-recorder", "start_proxy.bat")
                    ]
                else:
                    alt_paths = [
                        os.path.join(script_dir, "start_proxy.sh"),
                        os.path.join(os.path.dirname(script_dir), "llm-proxy-recorder", "start_proxy.sh")
                    ]
                
                for path in alt_paths:
                    if os.path.exists(path):
                        script_path = path
                        self.log(f"Found start script at: {script_path}")
                        break
                else:
                    raise FileNotFoundError(f"Could not find start script. Checked: {script_path} and alternates")
            
            # Make the script executable on Unix systems
            if os.name != 'nt' and os.path.exists(script_path):
                os.chmod(script_path, 0o755)
            
            # Start the script in a new window without capturing output
            if os.name == 'nt':
                # On Windows, use the start command to open in a new window
                self.proxy_process = subprocess.Popen(
                    ["start", "cmd", "/k", script_path],
                    shell=True,
                    close_fds=True
                )
            else:
                # On Unix/Mac, use terminal or x-terminal-emulator
                term_cmd = "x-terminal-emulator" if os.path.exists("/usr/bin/x-terminal-emulator") else "gnome-terminal"
                self.proxy_process = subprocess.Popen(
                    [term_cmd, "--", script_path],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            
            # Update UI
            self.proxy_status_var.set("Running")
            self.proxy_status_label.config(foreground="green")
            self.start_proxy_btn.config(state=tk.DISABLED)
            self.stop_proxy_btn.config(state=tk.NORMAL)
            
            self.log("Proxy recorder started successfully")
            messagebox.showinfo(
                "Proxy Started", 
                "Proxy recorder is now running on port 8080.\n\n"
                "Configure your browser or extension to use:\n"
                "Host: 127.0.0.1\nPort: 8080"
            )
            
        except Exception as e:
            self.log(f"Error starting proxy: {e}")
            messagebox.showerror("Error", f"Failed to start proxy recorder:\n{e}")
            self.update_proxy_status_stopped()

    def stop_proxy_recorder(self):
        """Try to stop the proxy recorder process by finding and killing mitmdump"""
        try:
            if os.name == 'nt':  # Windows
                # Find and kill mitmdump process
                subprocess.run(["taskkill", "/F", "/IM", "mitmdump.exe"], 
                            stdout=subprocess.DEVNULL, 
                            stderr=subprocess.DEVNULL)
                subprocess.run(["taskkill", "/F", "/IM", "mitmproxy.exe"], 
                            stdout=subprocess.DEVNULL, 
                            stderr=subprocess.DEVNULL)
            else:  # Unix/Mac
                # Find and kill mitmdump process
                subprocess.run(["pkill", "-f", "mitmdump"], 
                            stdout=subprocess.DEVNULL, 
                            stderr=subprocess.DEVNULL)
                subprocess.run(["pkill", "-f", "mitmproxy"], 
                            stdout=subprocess.DEVNULL, 
                            stderr=subprocess.DEVNULL)
            
            self.log("Proxy recorder stopped")
            messagebox.showinfo("Proxy Stopped", "The proxy recorder has been stopped.")
            
        except Exception as e:
            self.log(f"Error stopping proxy: {e}")
            messagebox.showinfo(
                "Stop Proxy Manually", 
                "Failed to stop proxy automatically. Please close the proxy terminal window manually."
            )
        
        finally:
            self.update_proxy_status_stopped()

    def update_proxy_status_stopped(self):
        """Update UI elements when proxy is stopped"""
        self.proxy_status_var.set("Inactive")
        self.proxy_status_label.config(foreground="red")
        self.start_proxy_btn.config(state=tk.NORMAL)
        self.stop_proxy_btn.config(state=tk.DISABLED)
        if hasattr(self, 'proxy_process'):
            self.proxy_process = None

    def import_from_sqlite_db(self):
        """Import prompts from SQLite database to JSON"""
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "llm-proxy-recorder", "prompts.db")
        json_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "claude_prompts.json")
        
        try:
            # Check if database exists
            if not os.path.exists(db_path):
                self.log(f"SQLite database not found at: {db_path}")
                messagebox.showinfo("Database Not Found", f"SQLite database not found at: {db_path}")
                return 0
                
            # Connect to SQLite database
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Get all prompts
            cursor.execute("SELECT * FROM prompts ORDER BY timestamp DESC")
            rows = cursor.fetchall()
            
            # Load existing JSON prompts
            existing_prompts = []
            if os.path.exists(json_path):
                with open(json_path, "r", encoding="utf-8") as f:
                    existing_prompts = json.load(f)
            
            # Get existing IDs for comparison
            existing_ids = set(p.get("id") for p in existing_prompts)
            
            # Add new prompts
            added_count = 0
            for row in rows:
                if row["id"] not in existing_ids:
                    # Get associated files
                    cursor.execute(
                        "SELECT file_path FROM file_associations WHERE prompt_id = ?", 
                        (row["id"],)
                    )
                    files = [r["file_path"] for r in cursor.fetchall()]
                    
                    # Create a new prompt entry
                    new_prompt = {
                        "id": row["id"],
                        "timestamp": row["timestamp"],
                        "prompt_text": row["prompt_text"],
                        "description": row["description"] or f"Prompt from {row['llm_name']}",
                        "model": row["llm_name"],  # Map llm_name to model field for JSON
                        "files": files
                    }
                    
                    existing_prompts.append(new_prompt)
                    added_count += 1
            
            # Save back to JSON
            if added_count > 0:
                with open(json_path, "w", encoding="utf-8") as f:
                    json.dump(existing_prompts, f, indent=4)
                
                self.log(f"Imported {added_count} prompts from SQLite database")
                messagebox.showinfo("Import Successful", f"Imported {added_count} prompts from SQLite database")
                
                # Reload the prompt database
                self.prompt_database.load()
                
                # Refresh the prompt history display
                self.refresh_prompt_history()
            else:
                self.log("No new prompts to import")
                messagebox.showinfo("Import", "No new prompts to import")
            
            conn.close()
            return added_count
        except Exception as e:
            self.log(f"Error importing from SQLite: {e}")
            messagebox.showerror("Import Error", f"Failed to import from SQLite:\n{e}")
            return 0              

    def set_as_active_prompt(self):
        """Set the selected prompt as the active prompt"""
        selection = self.ext_prompts_tree.selection()
        if not selection:
            messagebox.showinfo("No Selection", "Please select a prompt to set as active.")
            return
        
        # Get the prompt ID
        prompt_id = selection[0]
        
        # First, make sure the prompt is in our database
        prompt = None
        for p in self.prompt_database.prompts:
            if p.id == prompt_id:
                prompt = p
                break
        
        if not prompt:
            # Try to import it first
            try:
                self.import_selected_prompt()
                
                # Check again
                for p in self.prompt_database.prompts:
                    if p.id == prompt_id:
                        prompt = p
                        break
                
                if not prompt:
                    messagebox.showerror("Error", "Failed to import the prompt. Cannot set as active.")
                    return
            except Exception as e:
                self.log(f"Error importing prompt for activation: {e}")
                messagebox.showerror("Error", f"Failed to import the prompt:\n{e}")
                return
        
        # Set as active prompt
        self.prompt_database.active_prompt = prompt
        self.update_active_prompt_display()
        
        self.log(f"Set active prompt: {prompt.description}")
        messagebox.showinfo(
            "Active Prompt Set",
            f"The prompt has been set as active.\n\n"
            f"Any files modified now will be associated with this prompt."
        )            

    # -----------
    # eADR Notes Tab Initialization
    # -----------
    def initialize_eadr_notes_tab(self):
        """Initialize the eADR Notes tab in the notebook"""
        self.eadr_frame = ttk.Frame(self.notebook)
        
        # Project selection
        project_frame = ttk.Frame(self.eadr_frame)
        project_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Label(project_frame, text="Project:").pack(side=tk.LEFT, padx=5)
        self.project_entry = ttk.Entry(project_frame, width=20)
        self.project_entry.insert(0, "Origin")
        self.project_entry.pack(side=tk.LEFT, padx=5)
        
        # Note input area
        note_frame = ttk.LabelFrame(self.eadr_frame, text="New Note")
        note_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.note_text = scrolledtext.ScrolledText(note_frame, wrap="word", height=10)
        self.note_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        button_frame = ttk.Frame(note_frame)
        button_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(button_frame, text="Save Note", command=self.save_new_eadr_note).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Clear", command=lambda: self.note_text.delete("1.0", tk.END)).pack(side=tk.LEFT, padx=5)
        
        # Notes history
        history_frame = ttk.LabelFrame(self.eadr_frame, text="Note History")
        history_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.notes_treeview = ttk.Treeview(history_frame, columns=("timestamp", "project"), show="headings")
        self.notes_treeview.heading("timestamp", text="Date & Time")
        self.notes_treeview.heading("project", text="Project")
        self.notes_treeview.column("timestamp", width=150)
        self.notes_treeview.column("project", width=100)
        self.notes_treeview.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(history_frame, orient=tk.VERTICAL, command=self.notes_treeview.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.notes_treeview.configure(yscrollcommand=scrollbar.set)
        
        self.notes_treeview.bind("<<TreeviewSelect>>", self.display_selected_note)
        
        # Note display area
        display_frame = ttk.LabelFrame(self.eadr_frame, text="Note Content")
        display_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.display_text = scrolledtext.ScrolledText(display_frame, wrap="word", height=10)
        self.display_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.display_text.config(state=tk.DISABLED)
        
        # Add delete button for notes
        delete_button_frame = ttk.Frame(display_frame)
        delete_button_frame.pack(fill=tk.X, pady=2)
        self.delete_note_button = ttk.Button(delete_button_frame, text="Delete Selected Note", 
                                             command=self.delete_selected_note)
        self.delete_note_button.pack(side=tk.LEFT, padx=5)
        self.delete_note_button.config(state=tk.DISABLED)  # Disabled until a note is selected
        
        # Add the tab to the notebook
        self.notebook.add(self.eadr_frame, text="eADR Notes")
        
        # Load existing notes
        self.load_eadr_note_history()
    
    # -----------
    # Prompt Tracking Tab Initialization
    # -----------
    def initialize_prompt_tracking_tab(self):
        """Initialize the Prompt Tracking tab in the notebook"""
        self.prompt_frame = ttk.Frame(self.notebook)
        
        # Create the prompt database
        self.prompt_database = PromptDatabase()
        
        # Create the prompt entry area
        entry_frame = ttk.LabelFrame(self.prompt_frame, text="New Prompt")
        entry_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Description field
        ttk.Label(entry_frame, text="Description:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.prompt_description_var = tk.StringVar()
        description_entry = ttk.Entry(entry_frame, textvariable=self.prompt_description_var, width=40)
        description_entry.grid(row=0, column=1, sticky="ew", padx=5, pady=5)
        
        # LLM selection
        ttk.Label(entry_frame, text="LLM Used:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.llm_var = tk.StringVar(value="Claude")
        llm_combo = ttk.Combobox(entry_frame, textvariable=self.llm_var, values=["Claude", "GPT-4", "GPT-3.5", "Llama", "Other"])
        llm_combo.grid(row=1, column=1, sticky="ew", padx=5, pady=5)
        
        # Prompt text area
        ttk.Label(entry_frame, text="Prompt Text:").grid(row=2, column=0, sticky="nw", padx=5, pady=5)
        self.prompt_text = scrolledtext.ScrolledText(entry_frame, wrap="word", height=8)
        self.prompt_text.grid(row=2, column=1, sticky="ew", padx=5, pady=5)
        
        # File selection for association
        ttk.Label(entry_frame, text="Files to Use:").grid(row=3, column=0, sticky="nw", padx=5, pady=5)
        
        files_frame = ttk.Frame(entry_frame)
        files_frame.grid(row=3, column=1, sticky="ew", padx=5, pady=5)
        
        self.use_all_files_var = tk.BooleanVar(value=True)
        use_all_check = ttk.Checkbutton(files_frame, text="Use All Currently Selected Files", variable=self.use_all_files_var)
        use_all_check.pack(anchor="w")
        
        # Buttons
        button_frame = ttk.Frame(entry_frame)
        button_frame.grid(row=4, column=0, columnspan=2, padx=5, pady=5)
        
        ttk.Button(button_frame, text="Record Prompt", command=self.record_prompt).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Clear", command=self.clear_prompt_fields).pack(side=tk.LEFT, padx=5)
        
        # Active prompt indicator
        self.active_prompt_frame = ttk.LabelFrame(self.prompt_frame, text="Active Prompt")
        self.active_prompt_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.active_prompt_label = ttk.Label(self.active_prompt_frame, text="No active prompt", font=("", 10, "italic"))
        self.active_prompt_label.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(self.active_prompt_frame, text="Clear Active Prompt", command=self.clear_active_prompt).pack(side=tk.RIGHT, padx=10, pady=5)
        
        # Create notebook for prompt history and file associations
        history_notebook = ttk.Notebook(self.prompt_frame)
        history_notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Prompt history tab
        history_frame = ttk.Frame(history_notebook)
        history_notebook.add(history_frame, text="Prompt History")
        
        # Create treeview for prompt history
        columns = ("timestamp", "llm", "description", "files", "source")
        self.prompt_history_tree = ttk.Treeview(history_frame, columns=columns, show="headings")

        # Add the source column
        self.prompt_history_tree.heading("source", text="Source")
        self.prompt_history_tree.column("source", width=120)

        
        self.prompt_history_tree.heading("timestamp", text="Date & Time")
        self.prompt_history_tree.heading("llm", text="LLM")
        self.prompt_history_tree.heading("description", text="Description")
        self.prompt_history_tree.heading("files", text="Files")
        
        self.prompt_history_tree.column("timestamp", width=150)
        self.prompt_history_tree.column("llm", width=80)
        self.prompt_history_tree.column("description", width=250)
        self.prompt_history_tree.column("files", width=80)
        
        # Add scrollbar
        history_scrollbar = ttk.Scrollbar(history_frame, orient=tk.VERTICAL, command=self.prompt_history_tree.yview)
        history_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.prompt_history_tree.configure(yscrollcommand=history_scrollbar.set)
        self.prompt_history_tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Bind selection event
        self.prompt_history_tree.bind("<<TreeviewSelect>>", self.view_prompt_details)
        
        # File associations tab
        files_frame = ttk.Frame(history_notebook)
        history_notebook.add(files_frame, text="File Associations")
        
        # File selection
        file_select_frame = ttk.Frame(files_frame)
        file_select_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(file_select_frame, text="Select File:").pack(side=tk.LEFT, padx=5)
        self.file_association_var = tk.StringVar()
        self.file_combo = ttk.Combobox(file_select_frame, textvariable=self.file_association_var, width=50)
        self.file_combo.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        self.file_combo.bind("<<ComboboxSelected>>", self.show_file_prompts)
        
        # Refresh button
        ttk.Button(file_select_frame, text="Refresh", command=self.refresh_file_list).pack(side=tk.LEFT, padx=5)
        
        # Create treeview for file-related prompts
        self.file_prompts_tree = ttk.Treeview(files_frame, columns=columns, show="headings")
        
        for col in columns:
            self.file_prompts_tree.heading(col, text=self.prompt_history_tree.heading(col)["text"])
            self.file_prompts_tree.column(col, width=self.prompt_history_tree.column(col, "width"))
        
        # Add scrollbar
        file_scrollbar = ttk.Scrollbar(files_frame, orient=tk.VERTICAL, command=self.file_prompts_tree.yview)
        file_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.file_prompts_tree.configure(yscrollcommand=file_scrollbar.set)
        self.file_prompts_tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Bind selection event
        self.file_prompts_tree.bind("<<TreeviewSelect>>", self.view_prompt_details)
        
        # Prompt detail view
        detail_frame = ttk.LabelFrame(self.prompt_frame, text="Prompt Details")
        detail_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.prompt_detail_text = scrolledtext.ScrolledText(detail_frame, wrap="word")
        self.prompt_detail_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.prompt_detail_text.config(state=tk.DISABLED)
        
        # Action buttons
        action_frame = ttk.Frame(self.prompt_frame)
        action_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(action_frame, text="Set as Active Prompt", command=self.set_active_prompt).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="Export Prompt History", command=self.export_prompt_history).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="Retroactive Association", command=self.open_retroactive_association_dialog).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="Delete Selected Prompt", command=self.delete_prompt).pack(side=tk.RIGHT, padx=5)
        
        # Add the tab to the notebook
        self.notebook.add(self.prompt_frame, text="Prompt Tracking")
        
        # Populate the interface
        self.refresh_prompt_history()
        self.refresh_file_list()
        self.update_active_prompt_display()

    # -----------
    # Auto-Backup Tab Initialization
    # -----------
    def initialize_auto_backup_tab(self):
        """Initialize the Auto-Backup tab in the notebook"""
        self.auto_backup_frame = ttk.Frame(self.notebook)
        
        # Create configuration object
        self.auto_backup_config = AutoBackupConfig()
        
        # Top section: Enable/disable auto-backup
        control_frame = ttk.Frame(self.auto_backup_frame)
        control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.auto_backup_enabled_var = tk.BooleanVar(value=False)
        enable_check = ttk.Checkbutton(
            control_frame, 
            text="Enable Auto-Backup", 
            variable=self.auto_backup_enabled_var,
            command=self.toggle_auto_backup
        )
        enable_check.pack(side=tk.LEFT, padx=5)
        
        status_label = ttk.Label(control_frame, text="Status:")
        status_label.pack(side=tk.LEFT, padx=(20, 5))
        
        self.auto_backup_status_var = tk.StringVar(value="Inactive")
        self.auto_backup_status_label = ttk.Label(
            control_frame,
            textvariable=self.auto_backup_status_var,
            foreground="red"
        )
        self.auto_backup_status_label.pack(side=tk.LEFT)
        
        # Create notebook for settings and history
        settings_notebook = ttk.Notebook(self.auto_backup_frame)
        settings_notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Files & Folders tab
        files_frame = ttk.Frame(settings_notebook)
        settings_notebook.add(files_frame, text="Files & Folders")
        
        # Create a frame for monitored files
        monitored_files_frame = ttk.LabelFrame(files_frame, text="Monitored Files")
        monitored_files_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5, side=tk.LEFT)
        
        # Create treeview for monitored files
        self.monitored_files_tree = ttk.Treeview(monitored_files_frame, columns=("path",), show="headings")
        self.monitored_files_tree.heading("path", text="File Path")
        self.monitored_files_tree.column("path", width=300)
        
        # Add scrollbar
        files_scrollbar = ttk.Scrollbar(monitored_files_frame, orient=tk.VERTICAL, command=self.monitored_files_tree.yview)
        files_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.monitored_files_tree.configure(yscrollcommand=files_scrollbar.set)
        self.monitored_files_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Buttons for monitored files
        files_button_frame = ttk.Frame(monitored_files_frame)
        files_button_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(files_button_frame, text="Add Files", command=self.add_monitored_files).pack(side=tk.LEFT, padx=5)
        ttk.Button(files_button_frame, text="Remove Selected", command=self.remove_monitored_files).pack(side=tk.LEFT, padx=5)
        ttk.Button(files_button_frame, text="Add Current Selection", command=self.add_current_selection_to_monitoring).pack(side=tk.LEFT, padx=5)
        
        # Create a frame for monitored folders
        monitored_folders_frame = ttk.LabelFrame(files_frame, text="Monitored Folders")
        monitored_folders_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5, side=tk.RIGHT)
        
        # Create treeview for monitored folders
        self.monitored_folders_tree = ttk.Treeview(monitored_folders_frame, columns=("path",), show="headings")
        self.monitored_folders_tree.heading("path", text="Folder Path")
        self.monitored_folders_tree.column("path", width=300)
        
        # Add scrollbar
        folders_scrollbar = ttk.Scrollbar(monitored_folders_frame, orient=tk.VERTICAL, command=self.monitored_folders_tree.yview)
        folders_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.monitored_folders_tree.configure(yscrollcommand=folders_scrollbar.set)
        self.monitored_folders_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Buttons for monitored folders
        folders_button_frame = ttk.Frame(monitored_folders_frame)
        folders_button_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(folders_button_frame, text="Add Folder", command=self.add_monitored_folder).pack(side=tk.LEFT, padx=5)
        ttk.Button(folders_button_frame, text="Remove Selected", command=self.remove_monitored_folders).pack(side=tk.LEFT, padx=5)
        
        # Settings tab
        settings_frame = ttk.Frame(settings_notebook)
        settings_notebook.add(settings_frame, text="Settings")
        
        # Create settings form
        settings_form = ttk.Frame(settings_frame)
        settings_form.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Ignored patterns
        ttk.Label(settings_form, text="Ignored File Patterns (comma-separated):").grid(row=0, column=0, sticky="w", pady=5)
        self.ignored_patterns_var = tk.StringVar(value=",".join(self.auto_backup_config.ignored_patterns))
        ignored_entry = ttk.Entry(settings_form, textvariable=self.ignored_patterns_var, width=40)
        ignored_entry.grid(row=0, column=1, sticky="ew", padx=5, pady=5)
        
        # Minimum token change
        ttk.Label(settings_form, text="Minimum Token Change to Trigger Backup:").grid(row=1, column=0, sticky="w", pady=5)
        self.min_token_change_var = tk.IntVar(value=self.auto_backup_config.min_token_change)
        min_token_spin = ttk.Spinbox(settings_form, from_=1, to=1000, textvariable=self.min_token_change_var, width=10)
        min_token_spin.grid(row=1, column=1, sticky="w", padx=5, pady=5)
        
        # Cooldown period
        ttk.Label(settings_form, text="Cooldown Between Backups (minutes):").grid(row=2, column=0, sticky="w", pady=5)
        self.cooldown_var = tk.IntVar(value=self.auto_backup_config.cooldown_minutes)
        cooldown_spin = ttk.Spinbox(settings_form, from_=1, to=60, textvariable=self.cooldown_var, width=10)
        cooldown_spin.grid(row=2, column=1, sticky="w", padx=5, pady=5)
        
        # Maximum backups
        ttk.Label(settings_form, text="Maximum Auto-Backups to Keep:").grid(row=3, column=0, sticky="w", pady=5)
        self.max_backups_var = tk.IntVar(value=self.auto_backup_config.max_backups)
        max_backups_spin = ttk.Spinbox(settings_form, from_=1, to=100, textvariable=self.max_backups_var, width=10)
        max_backups_spin.grid(row=3, column=1, sticky="w", padx=5, pady=5)
        
        # Show notifications
        self.notification_var = tk.BooleanVar(value=self.auto_backup_config.notification_enabled)
        notification_check = ttk.Checkbutton(settings_form, text="Show Notifications When Backup Occurs", variable=self.notification_var)
        notification_check.grid(row=4, column=0, columnspan=2, sticky="w", pady=10)
        
        # Save settings button
        ttk.Button(settings_form, text="Save Settings", command=self.save_auto_backup_settings).grid(row=5, column=0, columnspan=2, pady=15)
        
        # Make the columns expandable
        settings_form.columnconfigure(1, weight=1)
        
        # History tab
        history_frame = ttk.Frame(settings_notebook)
        settings_notebook.add(history_frame, text="History")
        
        # Create treeview for backup history
        self.backup_history_tree = ttk.Treeview(
            history_frame, 
            columns=("timestamp", "files", "tokens", "prompt"), 
            show="headings"
        )
        self.backup_history_tree.heading("timestamp", text="Date & Time")
        self.backup_history_tree.heading("files", text="Files Changed")
        self.backup_history_tree.heading("tokens", text="Total Token Changes")
        self.backup_history_tree.heading("prompt", text="Has Prompt")
        
        self.backup_history_tree.column("timestamp", width=150)
        self.backup_history_tree.column("files", width=80)
        self.backup_history_tree.column("tokens", width=150)
        self.backup_history_tree.column("prompt", width=80)
        
        # Add scrollbar
        history_scrollbar = ttk.Scrollbar(history_frame, orient=tk.VERTICAL, command=self.backup_history_tree.yview)
        history_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.backup_history_tree.configure(yscrollcommand=history_scrollbar.set)
        self.backup_history_tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Bottom action buttons
        action_frame = ttk.Frame(self.auto_backup_frame)
        action_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(action_frame, text="Force Backup Now", command=self.force_auto_backup).pack(side=tk.RIGHT, padx=5)
        ttk.Button(action_frame, text="Refresh Status", command=self.refresh_auto_backup_status).pack(side=tk.RIGHT, padx=5)
        
        # Add the tab to the notebook
        self.notebook.add(self.auto_backup_frame, text="Auto-Backup")
        
        # Initialize the file monitor (we'll start it when enabled)
        self.file_observer = None
    
    # -----------
    # Rollback Tab Initialization
    # -----------
    def initialize_rollback_tab(self):
        """Initialize the Rollback tab in the notebook"""
        self.rollback_frame = ttk.Frame(self.notebook)
        
        # Top frame for selecting backup file
        select_frame = ttk.Frame(self.rollback_frame)
        select_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(select_frame, text="Backup File:").pack(side=tk.LEFT, padx=5)
        self.backup_path_var = tk.StringVar()
        backup_entry = ttk.Entry(select_frame, textvariable=self.backup_path_var, width=50)
        backup_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        ttk.Button(select_frame, text="Browse", command=self.browse_backup_file).pack(side=tk.LEFT, padx=5)
        ttk.Button(select_frame, text="Load", command=self.load_backup_file).pack(side=tk.LEFT, padx=5)
        
        # Create a paned window to divide the file list and preview
        rollback_paned = ttk.PanedWindow(self.rollback_frame, orient=tk.HORIZONTAL)
        rollback_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Left pane: file list with checkboxes
        files_frame = ttk.LabelFrame(rollback_paned, text="Files to Restore")
        
        # Create a frame for the treeview and scrollbar
        tree_frame = ttk.Frame(files_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create the treeview
        self.rollback_tree = ttk.Treeview(tree_frame, columns=("path", "status"), show="headings")
        self.rollback_tree.heading("path", text="File Path")
        self.rollback_tree.heading("status", text="Status")
        self.rollback_tree.column("path", width=300)
        self.rollback_tree.column("status", width=100)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.rollback_tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.rollback_tree.configure(yscrollcommand=scrollbar.set)
        self.rollback_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Add selection controls
        selection_frame = ttk.Frame(files_frame)
        selection_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(selection_frame, text="Select All", command=self.select_all_files).pack(side=tk.LEFT, padx=5)
        ttk.Button(selection_frame, text="Deselect All", command=self.deselect_all_files).pack(side=tk.LEFT, padx=5)
        ttk.Button(selection_frame, text="Toggle Selection", command=self.toggle_selection).pack(side=tk.LEFT, padx=5)
        
        # Add the files frame to the paned window
        rollback_paned.add(files_frame, weight=1)
        
        # Right pane: preview diff
        preview_frame = ttk.LabelFrame(rollback_paned, text="Diff Preview")
        
        self.diff_text = scrolledtext.ScrolledText(preview_frame, wrap="none")
        self.diff_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Add the preview frame to the paned window
        rollback_paned.add(preview_frame, weight=2)
        
        # Bind selection to show diff
        self.rollback_tree.bind("<<TreeviewSelect>>", self.show_file_diff)
        
        # Add bottom buttons
        button_frame = ttk.Frame(self.rollback_frame)
        button_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(button_frame, text="").pack(side=tk.LEFT, expand=True)
        ttk.Button(button_frame, text="Restore Selected Files", command=self.restore_selected_files).pack(side=tk.RIGHT, padx=5)
        
        # Add the tab to the notebook
        self.notebook.add(self.rollback_frame, text="Rollback")
        
    # -----------
    # Retroactive Prompt Association
    # -----------
    def open_retroactive_association_dialog(self):
        """Open a dialog to retroactively associate files with a prompt"""
        # Check if we have any prompts first
        if not self.prompt_database.prompts:
            messagebox.showinfo("No Prompts", "No prompts have been recorded yet. Please record a prompt first.")
            return
        
        # Create a dialog window
        dialog = tk.Toplevel(self.master)
        dialog.title("Retroactive Prompt Association")
        dialog.geometry("800x600")
        dialog.transient(self.master)
        dialog.grab_set()
        
        # Make the dialog resizable
        dialog.columnconfigure(0, weight=1)
        dialog.rowconfigure(1, weight=1)
        
        # Create the UI elements
        # 1. Prompt selection
        prompt_frame = ttk.LabelFrame(dialog, text="Select Prompt")
        prompt_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        
        # Prompt dropdown
        prompt_options = []
        for prompt in self.prompt_database.prompts:
            desc = prompt.description or "Untitled"
            date = prompt.timestamp.strftime("%Y-%m-%d %H:%M")
            prompt_options.append(f"{desc} ({date})")
        
        prompt_var = tk.StringVar()
        prompt_combo = ttk.Combobox(prompt_frame, textvariable=prompt_var, values=prompt_options, width=50)
        prompt_combo.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        if prompt_options:
            prompt_combo.current(0)
        
        # View prompt button
        view_button = ttk.Button(prompt_frame, text="View Prompt Details",
                                command=lambda: self.show_retroactive_prompt_details(dialog, prompt_combo.current()))
        view_button.grid(row=0, column=1, padx=10, pady=10)
        
        # 2. File selection
        files_frame = ttk.LabelFrame(dialog, text="Select Files to Associate")
        files_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        files_frame.columnconfigure(0, weight=1)
        files_frame.rowconfigure(0, weight=1)
        
        # Create a frame with both a treeview and file selection options
        file_selection_frame = ttk.Frame(files_frame)
        file_selection_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        file_selection_frame.columnconfigure(0, weight=1)
        file_selection_frame.rowconfigure(1, weight=1)
        
        # File source options
        source_frame = ttk.Frame(file_selection_frame)
        source_frame.grid(row=0, column=0, sticky="ew", pady=5)
        
        source_var = tk.StringVar(value="current")
        ttk.Radiobutton(source_frame, text="Use Current Selection", variable=source_var, value="current",
                       command=lambda: self.update_retroactive_file_list(file_tree, source_var.get())).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(source_frame, text="Use All Files", variable=source_var, value="all",
                       command=lambda: self.update_retroactive_file_list(file_tree, source_var.get())).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(source_frame, text="Select Files Manually", variable=source_var, value="manual",
                       command=lambda: self.update_retroactive_file_list(file_tree, source_var.get())).pack(side=tk.LEFT, padx=5)
        
        # File treeview with checkboxes
        file_tree = ttk.Treeview(file_selection_frame, columns=("path",), show="tree headings")
        file_tree.heading("#0", text="")
        file_tree.heading("path", text="File Path")
        file_tree.column("#0", width=50)
        file_tree.column("path", width=600)
        
        # Add scrollbar
        tree_scrollbar = ttk.Scrollbar(file_selection_frame, orient=tk.VERTICAL, command=file_tree.yview)
        tree_scrollbar.grid(row=1, column=1, sticky="ns")
        file_tree.configure(yscrollcommand=tree_scrollbar.set)
        file_tree.grid(row=1, column=0, sticky="nsew")
        
        # Populate the file tree with initial data
        self.update_retroactive_file_list(file_tree, source_var.get())
        
        # Add selection buttons
        select_frame = ttk.Frame(file_selection_frame)
        select_frame.grid(row=2, column=0, sticky="ew", pady=5)
        
        ttk.Button(select_frame, text="Select All",
                  command=lambda: self.retroactive_select_all_files(file_tree)).pack(side=tk.LEFT, padx=5)
        ttk.Button(select_frame, text="Deselect All",
                  command=lambda: self.retroactive_deselect_all_files(file_tree)).pack(side=tk.LEFT, padx=5)
        
        # Add manual file selection button (when in manual mode)
        add_files_button = ttk.Button(select_frame, text="Add Files...",
                                     command=lambda: self.retroactive_add_files(file_tree))
        add_files_button.pack(side=tk.LEFT, padx=5)
        
        # 3. Notes and token change
        notes_frame = ttk.LabelFrame(dialog, text="Association Details")
        notes_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=10)
        notes_frame.columnconfigure(1, weight=1)
        
        # Token change estimation
        ttk.Label(notes_frame, text="Estimated Token Change:").grid(row=0, column=0, sticky="w", padx=10, pady=5)
        token_var = tk.StringVar(value="Auto")
        token_options = ["Auto", "Minor (<50)", "Moderate (50-200)", "Major (>200)", "Custom"]
        token_combo = ttk.Combobox(notes_frame, textvariable=token_var, values=token_options, width=15)
        token_combo.grid(row=0, column=1, sticky="w", padx=10, pady=5)
        token_combo.current(0)
        
        # Custom token entry (initially hidden)
        custom_token_var = tk.IntVar(value=0)
        custom_token_frame = ttk.Frame(notes_frame)
        custom_token_frame.grid(row=1, column=0, columnspan=2, sticky="w", padx=10, pady=5)
        custom_token_frame.grid_remove()  # Hidden by default
        
        ttk.Label(custom_token_frame, text="Custom Token Change:").pack(side=tk.LEFT, padx=5)
        custom_token_entry = ttk.Spinbox(custom_token_frame, from_=-10000, to=10000, textvariable=custom_token_var, width=10)
        custom_token_entry.pack(side=tk.LEFT, padx=5)
        
        # Show/hide custom token entry based on selection
        def update_token_entry(*args):
            if token_var.get() == "Custom":
                custom_token_frame.grid()
            else:
                custom_token_frame.grid_remove()
        
        token_var.trace("w", update_token_entry)
        
        # Notes field
        ttk.Label(notes_frame, text="Notes:").grid(row=2, column=0, sticky="nw", padx=10, pady=5)
        notes_text = scrolledtext.ScrolledText(notes_frame, wrap=tk.WORD, width=50, height=4)
        notes_text.grid(row=2, column=1, sticky="ew", padx=10, pady=5)
        
        # 4. Action buttons
        button_frame = ttk.Frame(dialog)
        button_frame.grid(row=3, column=0, sticky="ew", padx=10, pady=10)
        button_frame.columnconfigure(1, weight=1)
        
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).grid(row=0, column=0, padx=5, pady=5)
        
        # Create the associate button with all necessary variables captured
        associate_button = ttk.Button(
            button_frame, text="Associate Files with Prompt",
            command=lambda: self.perform_retroactive_association(
                dialog, prompt_combo.current(), file_tree, token_var.get(), 
                custom_token_var.get(), notes_text.get("1.0", tk.END).strip()
            )
        )
        associate_button.grid(row=0, column=2, padx=5, pady=5)
        
        # Center the dialog on the parent window
        dialog.update_idletasks()
        width = dialog.winfo_width()
        height = dialog.winfo_height()
        x = self.master.winfo_x() + (self.master.winfo_width() // 2) - (width // 2)
        y = self.master.winfo_y() + (self.master.winfo_height() // 2) - (height // 2)
        dialog.geometry(f"+{x}+{y}")
        
        # Make dialog modal
        dialog.focus_set()
        dialog.wait_window()

    def update_retroactive_file_list(self, tree, source):
        """Update the file tree based on the selected source"""
        # Clear the tree
        for item in tree.get_children():
            tree.delete(item)
        
        # Populate based on source
        if source == "current":
            # Use current selection
            for file_path in self.filtered_files:
                item_id = tree.insert("", tk.END, text="", values=(file_path,))
                tree.insert(item_id, tk.END, text="✓", values=("",))  # Checkbox
                tree.item(item_id, open=True)  # Expand
        
        elif source == "all":
            # Use all files from monitored folders and files
            all_files = set(self.filtered_files)
            
            # Add files from monitored folders
            for folder in self.folders:
                for root, _, files in os.walk(folder):
                    for file in files:
                        file_path = os.path.join(root, file)
                        all_files.add(file_path)
            
            # Sort and add to tree
            for file_path in sorted(all_files):
                item_id = tree.insert("", tk.END, text="", values=(file_path,))
                tree.insert(item_id, tk.END, text="✓", values=("",))  # Checkbox
                tree.item(item_id, open=True)  # Expand
        
        elif source == "manual":
            # Start with empty tree for manual selection
            pass

    def retroactive_select_all_files(self, tree):
        """Select all files in the tree"""
        for item in tree.get_children():
            for child in tree.get_children(item):
                tree.item(child, text="✓")

    def retroactive_deselect_all_files(self, tree):
        """Deselect all files in the tree"""
        for item in tree.get_children():
            for child in tree.get_children(item):
                tree.item(child, text=" ")

    def retroactive_add_files(self, tree):
        """Add files manually to the tree"""
        filetypes = [("All files", "*.*")]
        selected = filedialog.askopenfilenames(title="Select File(s) to Associate", filetypes=filetypes)
        
        for file_path in selected:
            # Check if already in tree
            exists = False
            for item in tree.get_children():
                if tree.item(item, "values")[0] == file_path:
                    exists = True
                    break
            
            if not exists:
                item_id = tree.insert("", tk.END, text="", values=(file_path,))
                tree.insert(item_id, tk.END, text="✓", values=("",))  # Checkbox
                tree.item(item_id, open=True)  # Expand

    def show_retroactive_prompt_details(self, dialog, prompt_index):
        """Show details of the selected prompt in a popup"""
        if prompt_index < 0 or prompt_index >= len(self.prompt_database.prompts):
            return
        
        prompt = self.prompt_database.prompts[prompt_index]
        
        details_dialog = tk.Toplevel(dialog)
        details_dialog.title("Prompt Details")
        details_dialog.geometry("600x400")
        details_dialog.transient(dialog)
        details_dialog.grab_set()
        
        # Create UI
        details_frame = ttk.Frame(details_dialog, padding=10)
        details_frame.pack(fill=tk.BOTH, expand=True)
        
        # Info section
        info_frame = ttk.Frame(details_frame)
        info_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(info_frame, text=f"Description: {prompt.description or 'Untitled'}").pack(anchor="w")
        ttk.Label(info_frame, text=f"Date & Time: {prompt.timestamp.strftime('%Y-%m-%d %H:%M:%S')}").pack(anchor="w")
        ttk.Label(info_frame, text=f"LLM Used: {prompt.llm_used}").pack(anchor="w")
        
        # Prompt text
        text_frame = ttk.LabelFrame(details_frame, text="Prompt Text")
        text_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        prompt_text = scrolledtext.ScrolledText(text_frame, wrap=tk.WORD)
        prompt_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        prompt_text.insert(tk.END, prompt.prompt_text)
        prompt_text.config(state=tk.DISABLED)
        
        # Associated files
        if prompt.associated_files:
            files_frame = ttk.LabelFrame(details_frame, text="Currently Associated Files")
            files_frame.pack(fill=tk.BOTH, pady=10)
            
            files_text = scrolledtext.ScrolledText(files_frame, wrap=tk.WORD, height=5)
            files_text.pack(fill=tk.BOTH, padx=5, pady=5)
            
            for file_path in prompt.associated_files:
                files_text.insert(tk.END, f"• {file_path}\n")
            
            files_text.config(state=tk.DISABLED)
        
        # Close button
        ttk.Button(details_frame, text="Close", command=details_dialog.destroy).pack(pady=10)
        
        # Center the dialog
        details_dialog.update_idletasks()
        width = details_dialog.winfo_width()
        height = details_dialog.winfo_height()
        x = dialog.winfo_x() + (dialog.winfo_width() // 2) - (width // 2)
        y = dialog.winfo_y() + (dialog.winfo_height() // 2) - (height // 2)
        details_dialog.geometry(f"+{x}+{y}")

    def perform_retroactive_association(self, dialog, prompt_index, file_tree, token_option, custom_token, notes):
        """Perform the retroactive association of files with the prompt"""
        if prompt_index < 0 or prompt_index >= len(self.prompt_database.prompts):
            messagebox.showerror("Error", "Please select a valid prompt.")
            return
        
        prompt = self.prompt_database.prompts[prompt_index]
        
        # Get selected files
        selected_files = []
        for item in file_tree.get_children():
            file_path = file_tree.item(item, "values")[0]
            
            # Check if checkbox is selected
            for child in file_tree.get_children(item):
                if file_tree.item(child, "text") == "✓":
                    selected_files.append(file_path)
                    break
        
        if not selected_files:
            messagebox.showwarning("No Files Selected", "Please select at least one file to associate with the prompt.")
            return
        
        # Determine token change value
        token_change = 0
        if token_option == "Auto":
            # Use a default value or try to estimate
            token_change = 100  # Default moderate change
        elif token_option == "Minor (<50)":
            token_change = 25
        elif token_option == "Moderate (50-200)":
            token_change = 100
        elif token_option == "Major (>200)":
            token_change = 300
        elif token_option == "Custom":
            token_change = custom_token
        
        # Add files to prompt
        newly_added = 0
        for file_path in selected_files:
            if file_path not in prompt.associated_files:
                prompt.associated_files.append(file_path)
                prompt.file_changes[file_path] = token_change
                newly_added += 1
        
        # Save database
        self.prompt_database.save()
        
        # Log action
        if notes:
            # Add notes to prompt
            if not hasattr(prompt, 'retroactive_notes'):
                prompt.retroactive_notes = {}
            
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            prompt.retroactive_notes[timestamp] = {
                "files": selected_files,
                "token_change": token_change,
                "notes": notes
            }
            self.prompt_database.save()
            
            # Create an eADR note
            note_text = f"Retroactive Prompt Association\n\n"
            note_text += f"Prompt: {prompt.description or 'Untitled'}\n"
            note_text += f"Date: {timestamp}\n"
            note_text += f"Files associated: {len(selected_files)}\n\n"
            note_text += f"User Notes:\n{notes}\n\n"
            note_text += "Files:\n"
            for file_path in selected_files:
                note_text += f"- {file_path}\n"
            
            project = self.project_entry.get().strip() or "Origin"
            save_eadr_note(note_text, project)
            self.load_eadr_note_history()
        
        # Update UI
        self.refresh_prompt_history()
        self.refresh_file_list()
        
        # Show completion message
        messagebox.showinfo(
            "Association Complete", 
            f"Successfully associated {newly_added} new files with the prompt.\n"
            f"{len(selected_files) - newly_added} files were already associated."
        )
        
        # Close dialog
        dialog.destroy()
        
    # -----------
    # Prompt Tracking Methods
    # -----------
    def record_prompt(self):
        """Record a new prompt and set it as active"""
        prompt_text = self.prompt_text.get("1.0", tk.END).strip()
        if not prompt_text:
            messagebox.showwarning("Empty Prompt", "Please enter prompt text before recording.")
            return
        
        # Create new prompt record
        description = self.prompt_description_var.get().strip()
        llm_used = self.llm_var.get()
        
        prompt_record = PromptRecord(prompt_text, llm_used, description)
        
        # If "Use All Currently Selected Files" is checked, associate files now
        if self.use_all_files_var.get():
            for file_path in self.filtered_files:
                prompt_record.associated_files.append(file_path)
        
        # Add to database
        self.prompt_database.add_prompt(prompt_record)
        
        # Update UI
        self.log(f"Recorded new prompt: {description or 'Untitled'}")
        self.refresh_prompt_history()
        self.update_active_prompt_display()
        self.clear_prompt_fields()
        
        # Show confirmation
        messagebox.showinfo(
            "Prompt Recorded",
            "Prompt has been recorded and set as active.\n\n"
            "Any files modified now will be associated with this prompt."
        )

    def clear_prompt_fields(self):
        """Clear the prompt entry fields"""
        self.prompt_description_var.set("")
        self.prompt_text.delete("1.0", tk.END)

    def refresh_prompt_history(self):
        """Refresh the prompt history display"""
        # Clear existing items
        for item in self.prompt_history_tree.get_children():
            self.prompt_history_tree.delete(item)
        
        # Add prompts in reverse chronological order
        sorted_prompts = sorted(self.prompt_database.prompts, key=lambda p: p.timestamp, reverse=True)
        
        for prompt in sorted_prompts:
            timestamp_str = prompt.timestamp.strftime("%Y-%m-%d %H:%M")
            files_count = len(prompt.associated_files)
            
            # Determine the source based on multiple factors
            source = "Unknown"
            
            # Check if it's Claude Desktop
            if "Auto-recorded from Claude Desktop" in prompt.description:
                source = "Claude Desktop"
            elif prompt.description and "Claude Desktop" in prompt.description:
                source = "Claude Desktop"
            # Check if it's Claude web via proxy
            elif prompt.llm_used == "Claude" and ("via" in prompt.description or "proxy" in prompt.description.lower()):
                source = "Web Browser"
            # Check if it's ChatGPT
            elif "ChatGPT" in prompt.llm_used:
                source = "Web Browser"
            # If it's just Claude without other indicators, infer based on description
            elif prompt.llm_used == "Claude":
                # Check if there are MCP indicators
                if any(mcp_indicator in prompt.description.lower() for mcp_indicator in 
                    ["mcp", "auto-recorded", "claude desktop"]):
                    source = "Claude Desktop"
                else:
                    # Assume it's web-based Claude if description mentions web or proxy indicators
                    if any(web_indicator in prompt.description.lower() for web_indicator in 
                        ["web", "proxy", "browser", "captured", "via", "claude.ai"]):
                        source = "Web Browser"
                    else:
                        # Default for Claude is Desktop since that's more common in your setup
                        source = "Claude Desktop"
            else:
                # Handle other LLMs
                source = "Web Browser"  # Default for non-Claude prompts
            
            self.prompt_history_tree.insert(
                "", tk.END,
                iid=prompt.id,
                values=(timestamp_str, prompt.llm_used, prompt.description, files_count, source),
                tags=(prompt.id,)
            )

    def view_prompt_details(self, event):
        """Display details of the selected prompt"""
        # Get the tree that triggered the event
        tree = event.widget
        selection = tree.selection()
        
        if not selection:
            return
        
        # Get prompt ID from tree item
        prompt_id = tree.item(selection[0], "tags")[0]
        prompt = self.prompt_database.get_prompt(prompt_id)
        
        if not prompt:
            return
        
        # Update detail view
        self.prompt_detail_text.config(state=tk.NORMAL)
        self.prompt_detail_text.delete("1.0", tk.END)
        
        self.prompt_detail_text.insert(tk.END, f"Description: {prompt.description}\n")
        self.prompt_detail_text.insert(tk.END, f"Date & Time: {prompt.timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n")
        self.prompt_detail_text.insert(tk.END, f"LLM Used: {prompt.llm_used}\n\n")
        
        self.prompt_detail_text.insert(tk.END, "Associated Files:\n")
        for file_path in prompt.associated_files:
            change = prompt.file_changes.get(file_path, "Unknown")
            self.prompt_detail_text.insert(tk.END, f"- {file_path} (Token change: {change})\n")
        
        # Check for retroactive notes
        if hasattr(prompt, 'retroactive_notes') and prompt.retroactive_notes:
            self.prompt_detail_text.insert(tk.END, "\nRetroactive Associations:\n")
            for timestamp, note_data in prompt.retroactive_notes.items():
                self.prompt_detail_text.insert(tk.END, f"- {timestamp}: {len(note_data['files'])} files\n")
                self.prompt_detail_text.insert(tk.END, f"  Note: {note_data['notes']}\n")
        
        self.prompt_detail_text.insert(tk.END, "\nPrompt Text:\n")
        self.prompt_detail_text.insert(tk.END, prompt.prompt_text)
        
        self.prompt_detail_text.config(state=tk.DISABLED)

        self.prompt_detail_text.insert(tk.END, "Associated Files:\n")
        if prompt.associated_files:
            for file_path in prompt.associated_files:
                change = prompt.file_changes.get(file_path, "Unknown")
                self.prompt_detail_text.insert(tk.END, f"- {file_path} (Token change: {change})\n")
        else:
            self.prompt_detail_text.insert(tk.END, "No associated files\n")        

    def associate_files_with_prompt(self):
        """Associate files with the selected prompt"""
        # Get the selected prompt
        tree = self.prompt_history_tree
        selection = tree.selection()
        if not selection:
            messagebox.showinfo("No Selection", "Please select a prompt to associate files with.")
            return
        
        # Get the prompt ID
        prompt_id = tree.item(selection[0], "tags")[0]
        prompt = self.prompt_database.get_prompt(prompt_id)
        
        if not prompt:
            return
        
        # Ask user to select files
        filetypes = [("All files", "*.*")]
        selected_files = filedialog.askopenfilenames(title="Select Files to Associate", filetypes=filetypes)
        
        if not selected_files:
            return
        
        # Associate files with the prompt
        for file_path in selected_files:
            if file_path not in prompt.associated_files:
                prompt.associated_files.append(file_path)
                prompt.file_changes[file_path] = 0  # Default token change
        
        self.prompt_database.save()
        
        # Refresh the view
        self.view_prompt_details(None)
        
        messagebox.showinfo("Success", f"Associated {len(selected_files)} files with the prompt.")

    def refresh_file_list(self):
        """Refresh the list of files for associations"""
        # Collect all files from current selection and prompt database
        all_files = set()
        
        # Add current filtered files
        for file_path in self.filtered_files:
            all_files.add(file_path)
        
        # Add files from prompt database
        for prompt in self.prompt_database.prompts:
            for file_path in prompt.associated_files:
                all_files.add(file_path)
        
        # Update combobox
        self.file_combo['values'] = sorted(list(all_files))
        
        # If a file is already selected, keep it
        if self.file_association_var.get() not in all_files and all_files:
            self.file_association_var.set(next(iter(all_files)))
            self.show_file_prompts(None)

    def show_file_prompts(self, event=None):
        """Show prompts associated with the selected file"""
        file_path = self.file_association_var.get()
        if not file_path:
            return
        
        # Get prompts for this file
        file_prompts = self.prompt_database.get_prompts_for_file(file_path)
        
        # Clear existing items
        for item in self.file_prompts_tree.get_children():
            self.file_prompts_tree.delete(item)
        
        # Add prompts in reverse chronological order
        sorted_prompts = sorted(file_prompts, key=lambda p: p.timestamp, reverse=True)
        
        for prompt in sorted_prompts:
            timestamp_str = prompt.timestamp.strftime("%Y-%m-%d %H:%M")
            files_count = len(prompt.associated_files)
            
            self.file_prompts_tree.insert(
                "", tk.END,
                iid=prompt.id,
                values=(timestamp_str, prompt.llm_used, prompt.description, files_count),
                tags=(prompt.id,)
            )

    def set_active_prompt(self):
        """Set the selected prompt as active"""
        # Check which tree is active
        focused = self.prompt_frame.focus_get()
        
        if focused == self.prompt_history_tree:
            tree = self.prompt_history_tree
        elif focused == self.file_prompts_tree:
            tree = self.file_prompts_tree
        else:
            messagebox.showinfo("No Selection", "Please select a prompt to set as active.")
            return
        
        selection = tree.selection()
        if not selection:
            messagebox.showinfo("No Selection", "Please select a prompt to set as active.")
            return
        
        # Get prompt ID from tree item
        prompt_id = tree.item(selection[0], "tags")[0]
        prompt = self.prompt_database.get_prompt(prompt_id)
        
        if prompt:
            self.prompt_database.active_prompt = prompt
            self.update_active_prompt_display()
            self.log(f"Set active prompt: {prompt.description or 'Untitled'}")
            messagebox.showinfo(
                "Active Prompt Set",
                "Selected prompt has been set as active.\n\n"
                "Any files modified now will be associated with this prompt."
            )

    def clear_active_prompt(self):
        """Clear the active prompt"""
        if self.prompt_database.active_prompt:
            self.prompt_database.clear_active_prompt()
            self.update_active_prompt_display()
            self.log("Cleared active prompt")

    def update_active_prompt_display(self):
        """Update the active prompt display"""
        if self.prompt_database.active_prompt:
            prompt = self.prompt_database.active_prompt
            desc = prompt.description or "Untitled"
            timestamp = prompt.timestamp.strftime("%Y-%m-%d %H:%M")
            
            self.active_prompt_label.config(
                text=f"Active Prompt: {desc} ({timestamp}, {prompt.llm_used})",
                font=("", 10, "bold"),
                foreground="green"
            )
        else:
            self.active_prompt_label.config(
                text="No active prompt",
                font=("", 10, "italic"),
                foreground="black"
            )

    def export_prompt_history(self):
        """Export prompt history to a markdown file"""
        output_dir = "prompts"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"prompt_history_{timestamp}.md"
        output_file = os.path.join(output_dir, filename)
        
        try:
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(f"# Prompt History Export\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                
                # Sort prompts by date (newest first)
                sorted_prompts = sorted(self.prompt_database.prompts, key=lambda p: p.timestamp, reverse=True)
                
                for i, prompt in enumerate(sorted_prompts, 1):
                    f.write(f"## {i}. {prompt.description or 'Untitled Prompt'}\n\n")
                    f.write(f"- **Date & Time:** {prompt.timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"- **LLM Used:** {prompt.llm_used}\n")
                    f.write(f"- **ID:** {prompt.id}\n\n")
                    
                    f.write("### Prompt Text\n\n```\n")
                    f.write(prompt.prompt_text)
                    f.write("\n```\n\n")
                    
                    f.write("### Associated Files\n\n")
                    if prompt.associated_files:
                        for file_path in prompt.associated_files:
                            change = prompt.file_changes.get(file_path, "Unknown")
                            f.write(f"- `{file_path}` (Token change: {change})\n")
                    else:
                        f.write("No files associated with this prompt.\n")
                    
                    # Add retroactive notes if any
                    if hasattr(prompt, 'retroactive_notes') and prompt.retroactive_notes:
                        f.write("\n### Retroactive Associations\n\n")
                        for timestamp, note_data in prompt.retroactive_notes.items():
                            f.write(f"**{timestamp}**\n\n")
                            f.write(f"- Token Change: {note_data['token_change']}\n")
                            f.write(f"- Notes: {note_data['notes']}\n")
                            f.write("- Files:\n")
                            for file in note_data['files']:
                                f.write(f"  - `{file}`\n")
                    
                    f.write("\n---\n\n")
            
            self.log(f"Exported prompt history to {output_file}")
            messagebox.showinfo("Export Complete", f"Prompt history has been exported to:\n{output_file}")
            
        except Exception as e:
            self.log(f"Error exporting prompt history: {e}")
            messagebox.showerror("Export Error", f"Failed to export prompt history:\n{e}")

    def delete_prompt(self):
        """Delete the selected prompt"""
        # Check which tree is active
        focused = self.prompt_frame.focus_get()
        
        if focused == self.prompt_history_tree:
            tree = self.prompt_history_tree
        elif focused == self.file_prompts_tree:
            tree = self.file_prompts_tree
        else:
            return
        
        selection = tree.selection()
        if not selection:
            return
        
        # Confirm deletion
        confirm = messagebox.askyesno(
            "Confirm Deletion",
            "Are you sure you want to delete this prompt record?\nThis action cannot be undone."
        )
        
        if not confirm:
            return
        
        # Get prompt ID from tree item
        prompt_id = tree.item(selection[0], "tags")[0]
        
        # Remove from database
        for i, prompt in enumerate(self.prompt_database.prompts):
            if prompt.id == prompt_id:
                # Check if it's the active prompt
                if self.prompt_database.active_prompt and self.prompt_database.active_prompt.id == prompt_id:
                    self.prompt_database.clear_active_prompt()
                    self.update_active_prompt_display()
                
                # Remove the prompt
                self.prompt_database.prompts.pop(i)
                self.prompt_database.save()
                self.log(f"Deleted prompt: {prompt.description or 'Untitled'}")
                
                # Update UI
                self.refresh_prompt_history()
                self.show_file_prompts()
                
                # Clear detail view
                self.prompt_detail_text.config(state=tk.NORMAL)
                self.prompt_detail_text.delete("1.0", tk.END)
                self.prompt_detail_text.config(state=tk.DISABLED)
                
                return
            
    def _add_to_json_db(self, prompt_id, timestamp, prompt_text, llm_name, description, associated_files):
        """Add prompt to JSON database for backward compatibility"""
        try:
            # Log the file path being used
            logger.info(f"Adding prompt to JSON file: {self.json_path}")
            
            # Load existing prompts
            prompts = []
            if os.path.exists(self.json_path):
                with open(self.json_path, "r", encoding="utf-8") as f:
                    prompts = json.load(f)
            
            # Add new prompt
            new_prompt = {
                "id": prompt_id,
                "timestamp": timestamp,
                "prompt_text": prompt_text,
                "description": description or f"Prompt from {llm_name}",
                "model": llm_name,
                "files": associated_files
            }
            
            prompts.append(new_prompt)
            
            # Save back to file
            with open(self.json_path, "w", encoding="utf-8") as f:
                json.dump(prompts, f, indent=4)
            
            logger.info(f"Successfully added prompt {prompt_id} to JSON file")    
            return True
        except Exception as e:
            logger.error(f"Error adding to JSON database: {e}")
            return False            
    
    # -----------
    # Auto-Backup Methods
    # -----------
    def toggle_auto_backup(self):
        """Enable or disable auto-backup based on checkbox state"""
        enabled = self.auto_backup_enabled_var.get()
        
        if enabled:
            self.start_auto_backup_monitoring()
        else:
            self.stop_auto_backup_monitoring()
        
        # Update configuration
        self.auto_backup_config.enabled = enabled
        self.save_auto_backup_settings()
        
        # Update UI
        self.refresh_auto_backup_status()

    def start_auto_backup_monitoring(self):
        """Start the file observer for auto-backup"""
        if self.file_observer is not None:
            # Observer already running
            return
        
        try:
            # Create the event handler
            event_handler = EnhancedFileChangeHandler(self, self.auto_backup_config)
            
            # Create and start the observer
            self.file_observer = Observer()
            
            # Add watches for all monitored folders
            for folder_path in self.auto_backup_config.monitor_folders:
                if os.path.isdir(folder_path):
                    self.file_observer.schedule(event_handler, folder_path, recursive=True)
                    self.log(f"Monitoring folder: {folder_path}")
            
            # Add watches for parent directories of individual files
            for file_path in self.auto_backup_config.monitor_files:
                if os.path.isfile(file_path):
                    parent_dir = os.path.dirname(file_path)
                    if parent_dir:
                        self.file_observer.schedule(event_handler, parent_dir, recursive=False)
                        self.log(f"Monitoring file: {file_path}")
            
            # Start the observer
            self.file_observer.start()
            self.log("Auto-backup monitoring started")
            
            # Update the status
            self.auto_backup_status_var.set("Active")
            self.auto_backup_status_label.config(foreground="green")
            
        except Exception as e:
            self.log(f"Error starting auto-backup monitoring: {e}")
            messagebox.showerror("Error", f"Failed to start auto-backup monitoring:\n{e}")
            
            # Reset the UI
            self.auto_backup_enabled_var.set(False)
            self.auto_backup_status_var.set("Error")
            self.auto_backup_status_label.config(foreground="red")

    def stop_auto_backup_monitoring(self):
        """Stop the file observer for auto-backup"""
        if self.file_observer is None:
            # Observer not running
            return
        
        try:
            # Stop and join the observer
            self.file_observer.stop()
            self.file_observer.join()
            self.file_observer = None
            
            self.log("Auto-backup monitoring stopped")
            
            # Update the status
            self.auto_backup_status_var.set("Inactive")
            self.auto_backup_status_label.config(foreground="red")
            
        except Exception as e:
            self.log(f"Error stopping auto-backup monitoring: {e}")

    def refresh_auto_backup_status(self):
        """Update the auto-backup status display"""
        if self.file_observer and self.file_observer.is_alive():
            self.auto_backup_status_var.set("Active")
            self.auto_backup_status_label.config(foreground="green")
        else:
            self.auto_backup_status_var.set("Inactive")
            self.auto_backup_status_label.config(foreground="red")

    def add_monitored_files(self):
        """Add files to the auto-backup monitoring list"""
        filetypes = [("All files", "*.*")]
        selected = filedialog.askopenfilenames(title="Select File(s) to Monitor", filetypes=filetypes)
        
        for file_path in selected:
            if file_path not in self.auto_backup_config.monitor_files:
                self.auto_backup_config.monitor_files.append(file_path)
                self.monitored_files_tree.insert("", tk.END, values=(file_path,))
                self.log(f"Added {file_path} to monitored files")
        
        # If monitoring is active, restart it to apply changes
        if self.file_observer:
            self.stop_auto_backup_monitoring()
            self.start_auto_backup_monitoring()

    def remove_monitored_files(self):
        """Remove selected files from monitoring"""
        selected = self.monitored_files_tree.selection()
        
        for item in selected:
            file_path = self.monitored_files_tree.item(item, "values")[0]
            if file_path in self.auto_backup_config.monitor_files:
                self.auto_backup_config.monitor_files.remove(file_path)
                self.monitored_files_tree.delete(item)
                self.log(f"Removed {file_path} from monitored files")
        
        # If monitoring is active, restart it to apply changes
        if self.file_observer:
            self.stop_auto_backup_monitoring()
            self.start_auto_backup_monitoring()

    def add_monitored_folder(self):
        """Add a folder to the auto-backup monitoring list"""
        folder = filedialog.askdirectory(title="Select Folder to Monitor")
        
        if folder and folder not in self.auto_backup_config.monitor_folders:
            self.auto_backup_config.monitor_folders.append(folder)
            self.monitored_folders_tree.insert("", tk.END, values=(folder,))
            self.log(f"Added {folder} to monitored folders")
        
        # If monitoring is active, restart it to apply changes
        if self.file_observer:
            self.stop_auto_backup_monitoring()
            self.start_auto_backup_monitoring()

    def remove_monitored_folders(self):
        """Remove selected folders from monitoring"""
        selected = self.monitored_folders_tree.selection()
        
        for item in selected:
            folder_path = self.monitored_folders_tree.item(item, "values")[0]
            if folder_path in self.auto_backup_config.monitor_folders:
                self.auto_backup_config.monitor_folders.remove(folder_path)
                self.monitored_folders_tree.delete(item)
                self.log(f"Removed {folder_path} from monitored folders")
        
        # If monitoring is active, restart it to apply changes
        if self.file_observer:
            self.stop_auto_backup_monitoring()
            self.start_auto_backup_monitoring()

    def add_current_selection_to_monitoring(self):
        """Add the currently selected files to monitoring"""
        # Add individual files first
        for file_path in self.filtered_files:
            if file_path not in self.auto_backup_config.monitor_files:
                self.auto_backup_config.monitor_files.append(file_path)
                self.monitored_files_tree.insert("", tk.END, values=(file_path,))
        
        # Then add any selected folders
        for folder in self.folders:
            if folder not in self.auto_backup_config.monitor_folders:
                self.auto_backup_config.monitor_folders.append(folder)
                self.monitored_folders_tree.insert("", tk.END, values=(folder,))
        
        self.log(f"Added current selection to monitoring: {len(self.filtered_files)} files, {len(self.folders)} folders")
        
        # If monitoring is active, restart it to apply changes
        if self.file_observer:
            self.stop_auto_backup_monitoring()
            self.start_auto_backup_monitoring()

    def save_auto_backup_settings(self):
        """Save the auto-backup settings"""
        # Update the configuration object from UI values
        self.auto_backup_config.ignored_patterns = [p.strip() for p in self.ignored_patterns_var.get().split(",") if p.strip()]
        self.auto_backup_config.min_token_change = self.min_token_change_var.get()
        self.auto_backup_config.cooldown_minutes = self.cooldown_var.get()
        self.auto_backup_config.max_backups = self.max_backups_var.get()
        self.auto_backup_config.notification_enabled = self.notification_var.get()
        
        # Save to a settings file
        auto_backup_settings = self.auto_backup_config.to_dict()
        
        try:
            with open("auto_backup_settings.json", "w", encoding="utf-8") as f:
                json.dump(auto_backup_settings, f, indent=4)
            
            self.log("Auto-backup settings saved")
            
            # If active, restart monitoring to apply new settings
            if self.file_observer:
                self.stop_auto_backup_monitoring()
                self.start_auto_backup_monitoring()
                
        except Exception as e:
            self.log(f"Error saving auto-backup settings: {e}")
            messagebox.showerror("Error", f"Failed to save auto-backup settings:\n{e}")

    def load_auto_backup_settings(self):
        """Load auto-backup settings from file"""
        if os.path.exists("auto_backup_settings.json"):
            try:
                with open("auto_backup_settings.json", "r", encoding="utf-8") as f:
                    settings = json.load(f)
                
                # Update the configuration object
                self.auto_backup_config.from_dict(settings)
                
                # Update UI
                self.auto_backup_enabled_var.set(self.auto_backup_config.enabled)
                self.ignored_patterns_var.set(",".join(self.auto_backup_config.ignored_patterns))
                self.min_token_change_var.set(self.auto_backup_config.min_token_change)
                self.cooldown_var.set(self.auto_backup_config.cooldown_minutes)
                self.max_backups_var.set(self.auto_backup_config.max_backups)
                self.notification_var.set(self.auto_backup_config.notification_enabled)
                
                # Populate monitoring lists
                self.monitored_files_tree.delete(*self.monitored_files_tree.get_children())
                for file_path in self.auto_backup_config.monitor_files:
                    self.monitored_files_tree.insert("", tk.END, values=(file_path,))
                    
                self.monitored_folders_tree.delete(*self.monitored_folders_tree.get_children())
                for folder_path in self.auto_backup_config.monitor_folders:
                    self.monitored_folders_tree.insert("", tk.END, values=(folder_path,))
                
                self.log("Auto-backup settings loaded")
                
                # Start monitoring if enabled
                if self.auto_backup_config.enabled:
                    self.start_auto_backup_monitoring()
                
            except Exception as e:
                self.log(f"Error loading auto-backup settings: {e}")

    def trigger_auto_backup_with_prompts(self, changed_files):
        """Enhanced version of trigger_auto_backup that includes prompt information"""
        # Update the last backup time
        self.auto_backup_config.last_backup_time = datetime.now()
        
        # Check if there's an active prompt to associate with changes
        active_prompt_info = ""
        if self.prompt_database.active_prompt:
            prompt = self.prompt_database.active_prompt
            
            # Associate changed files with the active prompt
            for file_path, token_change in changed_files:
                if file_path not in prompt.associated_files:
                    prompt.associated_files.append(file_path)
                    prompt.file_changes[file_path] = token_change
            
            self.prompt_database.save()
            
            # Add prompt info to the header
            active_prompt_info = f"\nActive Prompt: {prompt.description or 'Untitled'} ({prompt.llm_used})"
        
        # Create a descriptive name for this auto-backup
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        total_changes = sum(change for _, change in changed_files)
        backup_name = f"auto_backup_{timestamp}_{len(changed_files)}files_{total_changes}tokens.md"
        
        # Get the current list of files
        files_to_backup = []
        for file_path, _ in changed_files:
            files_to_backup.append(file_path)
            
        # Also include any other monitored files
        for file_path in self.auto_backup_config.monitor_files:
            if file_path not in files_to_backup and os.path.isfile(file_path):
                files_to_backup.append(file_path)
        
        # Build the combined text with prompt information
        header = f"Auto-Backup generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        header += f"\nChanged files: {len(changed_files)}, Total token changes: {total_changes}"
        header += active_prompt_info
        
        # If there's an active prompt, include its text in the header
        if self.prompt_database.active_prompt:
            header += "\n\nPrompt Text:\n"
            header += self.prompt_database.active_prompt.prompt_text
        
        footer = "End of Auto-Backup"
        
        combined_text = build_combined_text(files_to_backup, header, footer)
        total_tokens = count_tokens(combined_text)
        
        # Ensure backup directory exists
        output_dir = "backup"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        output_file = os.path.join(output_dir, backup_name)
        
        try:
            # Write the backup file
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(combined_text)
                
            self.log(f"Auto-backup created: {output_file}")
            
            # Add to history
            prompt_info = "Yes" if self.prompt_database.active_prompt else "No"
            self.backup_history_tree.insert(
                "", 0, 
                values=(timestamp, len(changed_files), total_changes, prompt_info)
            )
            
            # Create an eADR note
            self.create_auto_backup_eadr_note_with_prompt(backup_name, changed_files, total_tokens)
            
            # Prune old backups if needed
            self.prune_old_auto_backups()
            
            # Show notification if enabled
            if self.auto_backup_config.notification_enabled:
                messagebox.showinfo(
                    "Auto-Backup Complete", 
                    f"Auto-backup has been created with {len(changed_files)} changed files.\nTotal tokens: {total_tokens:,}"
                )
                
            # Update prompt history if needed
            if self.prompt_database.active_prompt:
                self.refresh_prompt_history()
                self.refresh_file_list()
                
            return True
            
        except Exception as e:
            self.log(f"Error creating auto-backup: {e}")
            return False

    def create_auto_backup_eadr_note_with_prompt(self, backup_name, changed_files, total_tokens):
        """Create an eADR note for an auto-backup, including prompt information"""
        project = self.project_entry.get().strip() or "Origin"
        
        note_text = f"Auto-Backup Created: {backup_name}\n\n"
        note_text += f"Total files: {len(changed_files)}\n"
        note_text += f"Total tokens: {total_tokens:,}\n\n"
        
        # Add active prompt information if available
        if self.prompt_database.active_prompt:
            prompt = self.prompt_database.active_prompt
            note_text += f"Active Prompt: {prompt.description or 'Untitled'}\n"
            note_text += f"LLM Used: {prompt.llm_used}\n\n"
            note_text += "Prompt Text:\n"
            note_text += f"{prompt.prompt_text}\n\n"
        
        note_text += "Changed files:\n"
        for file_path, token_change in changed_files:
            note_text += f"- {file_path} ({token_change:+,} tokens)\n"
        
        if save_eadr_note(note_text, project):
            self.log(f"eADR note created for auto-backup: {backup_name}")
            self.load_eadr_note_history()

    def force_auto_backup(self):
        """Manually trigger an auto-backup with all monitored files"""
        # Collect all monitored files
        files_to_backup = []
        
        # Add individual monitored files
        for file_path in self.auto_backup_config.monitor_files:
            if os.path.isfile(file_path):
                files_to_backup.append(file_path)
        
        # Add files from monitored folders
        for folder in self.auto_backup_config.monitor_folders:
            if os.path.isdir(folder):
                for root, _, files in os.walk(folder):
                    for file in files:
                        # Skip files matching ignored patterns
                        skip = False
                        for pattern in self.auto_backup_config.ignored_patterns:
                            if fnmatch.fnmatch(file, pattern):
                                skip = True
                                break
                        
                        if not skip:
                            file_path = os.path.join(root, file)
                            files_to_backup.append(file_path)
        
        if not files_to_backup:
            messagebox.showinfo("No Files", "No files to backup. Please add files or folders to monitor first.")
            return
        
        # Create synthetic change records (file path and token count)
        changed_files = [(f, count_tokens_in_file(f)) for f in files_to_backup]
        
        # Trigger the backup
        success = self.trigger_auto_backup_with_prompts(changed_files)
        
        if success:
            messagebox.showinfo("Success", "Manual auto-backup completed successfully.")
        else:
            messagebox.showerror("Error", "Failed to create manual auto-backup. See log for details.")

    def prune_old_auto_backups(self):
        """Remove old auto-backups if over the maximum limit"""
        max_backups = self.auto_backup_config.max_backups
        backup_dir = "backup"
        
        if not os.path.exists(backup_dir):
            return
        
        # Get all auto-backup files
        auto_backups = []
        for filename in os.listdir(backup_dir):
            if filename.startswith("auto_backup_") and filename.endswith(".md"):
                filepath = os.path.join(backup_dir, filename)
                mod_time = os.path.getmtime(filepath)
                auto_backups.append((filepath, mod_time))
        
        # Sort by modification time (newest first)
        auto_backups.sort(key=lambda x: x[1], reverse=True)
        
        # Keep only the newest ones
        if len(auto_backups) > max_backups:
            for filepath, _ in auto_backups[max_backups:]:
                try:
                    os.remove(filepath)
                    self.log(f"Pruned old auto-backup: {os.path.basename(filepath)}")
                except Exception as e:
                    self.log(f"Error removing old auto-backup {filepath}: {e}")
    
    # -----------
    # Rollback Methods
    # -----------
    def browse_backup_file(self):
        """Open a file dialog to select a backup file"""
        backup_file = filedialog.askopenfilename(
            title="Select Backup File",
            filetypes=[("Markdown files", "*.md"), ("All files", "*.*")],
            initialdir="backup"
        )
        if backup_file:
            self.backup_path_var.set(backup_file)
            self.load_backup_file()

    def load_backup_file(self):
        """Load and parse the selected backup file"""
        backup_path = self.backup_path_var.get()
        if not backup_path or not os.path.exists(backup_path):
            messagebox.showerror("Error", "Please select a valid backup file.")
            return
        
        # Clear the treeview
        for item in self.rollback_tree.get_children():
            self.rollback_tree.delete(item)
        
        # Parse the backup file
        self.backup_files = parse_combined_file(backup_path)
        
        # Populate the treeview
        for file_path in self.backup_files:
            # Check if the file exists and has changes
            if os.path.exists(file_path):
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        current_content = f.read()
                    
                    if current_content == self.backup_files[file_path]:
                        status = "Unchanged"
                    else:
                        status = "Modified"
                except Exception:
                    status = "Error reading"
            else:
                status = "Missing"
            
            # Insert into treeview
            self.rollback_tree.insert("", tk.END, values=(file_path, status))
        
        # Log the action
        self.log(f"Loaded backup file: {backup_path} with {len(self.backup_files)} files.")

    def select_all_files(self):
        """Select all files in the rollback tree"""
        for item in self.rollback_tree.get_children():
            self.rollback_tree.selection_add(item)

    def deselect_all_files(self):
        """Deselect all files in the rollback tree"""
        for item in self.rollback_tree.selection():
            self.rollback_tree.selection_remove(item)

    def toggle_selection(self):
        """Toggle selection of files in the rollback tree"""
        all_items = self.rollback_tree.get_children()
        selected_items = self.rollback_tree.selection()
        
        for item in all_items:
            if item in selected_items:
                self.rollback_tree.selection_remove(item)
            else:
                self.rollback_tree.selection_add(item)

    def show_file_diff(self, event):
        """Show diff between selected file and its backup version"""
        selection = self.rollback_tree.selection()
        if not selection:
            return
        
        # Only show diff for the first selected item
        item_id = selection[0]
        file_path = self.rollback_tree.item(item_id, "values")[0]
        
        if file_path in self.backup_files:
            backup_content = self.backup_files[file_path]
            diff = get_file_diff(file_path, backup_content)
            
            self.diff_text.configure(state=tk.NORMAL)
            self.diff_text.delete("1.0", tk.END)
            
            # Set colors for the diff
            self.diff_text.tag_configure("addition", foreground="green")
            self.diff_text.tag_configure("deletion", foreground="red")
            self.diff_text.tag_configure("heading", foreground="blue")
            
            # Insert the diff with appropriate tags
            for line in diff.split('\n'):
                if line.startswith('+'):
                    self.diff_text.insert(tk.END, line + '\n', "addition")
                elif line.startswith('-'):
                    self.diff_text.insert(tk.END, line + '\n', "deletion")
                elif line.startswith('@@') or line.startswith('---') or line.startswith('+++'):
                    self.diff_text.insert(tk.END, line + '\n', "heading")
                else:
                    self.diff_text.insert(tk.END, line + '\n')
            
            self.diff_text.configure(state=tk.DISABLED)

    def restore_selected_files(self):
        """Restore the selected files from the backup"""
        selection = self.rollback_tree.selection()
        if not selection:
            messagebox.showinfo("Info", "No files selected for restore.")
            return
        
        # Get selected file paths
        selected_files = [self.rollback_tree.item(item, "values")[0] for item in selection]
        
        # Confirm restore
        confirm = messagebox.askquestion(
            "Confirm Restore",
            f"Are you sure you want to restore {len(selected_files)} files? This will overwrite the current versions.",
            icon="warning"
        )
        
        if confirm != "yes":
            return
        
        # Restore files
        success_count = 0
        error_count = 0
        error_files = []
        
        for file_path in selected_files:
            if file_path in self.backup_files:
                success = restore_file(file_path, self.backup_files[file_path])
                if success:
                    success_count += 1
                    self.log(f"Restored file: {file_path}")
                    
                    # Update the status in the treeview
                    for item in self.rollback_tree.get_children():
                        if self.rollback_tree.item(item, "values")[0] == file_path:
                            self.rollback_tree.item(item, values=(file_path, "Restored"))
                            break
                else:
                    error_count += 1
                    error_files.append(file_path)
                    self.log(f"Failed to restore file: {file_path}")
        
        # Show results
        if error_count == 0:
            messagebox.showinfo("Success", f"Successfully restored {success_count} files.")
        else:
            messagebox.showwarning(
                "Partial Success",
                f"Restored {success_count} files successfully.\n"
                f"Failed to restore {error_count} files.\n"
                f"See log for details."
            )
        
        # Create an eADR note for the rollback operation
        self.create_rollback_eadr_note(selected_files, success_count, error_count, error_files)

    def create_rollback_eadr_note(self, selected_files, success_count, error_count, error_files):
        """Create an eADR note for the rollback operation"""
        backup_path = self.backup_path_var.get()
        project = self.project_entry.get().strip() or "Origin"
        
        note_text = f"Rollback Operation Summary\n\n"
        note_text += f"Backup file: {backup_path}\n"
        note_text += f"Files selected for restore: {len(selected_files)}\n"
        note_text += f"Successfully restored: {success_count}\n"
        note_text += f"Failed to restore: {error_count}\n\n"
        
        note_text += "Restored files:\n"
        for file_path in selected_files:
            if file_path not in error_files:
                note_text += f"- {file_path}\n"
        
        if error_files:
            note_text += "\nFailed files:\n"
            for file_path in error_files:
                note_text += f"- {file_path}\n"
        
        if save_eadr_note(note_text, project):
            self.log(f"eADR note created for rollback operation")
            self.load_eadr_note_history()
    
    # -----------
    # eADR Notes Tab Methods
    # -----------
    def delete_selected_note(self):
        """Delete the currently selected note"""
        selection = self.notes_treeview.selection()
        if not selection:
            return
        
        item_id = selection[0]
        note_index = int(self.notes_treeview.item(item_id, "tags")[0])
        
        # Ask for confirmation
        confirm = messagebox.askyesno(
            "Confirm Deletion", 
            "Are you sure you want to delete this note? This action cannot be undone."
        )
        
        if confirm:
            success, deleted_note = delete_eadr_note(note_index)
            
            if success and deleted_note:
                self.log(f"Deleted note from {deleted_note['timestamp']} for project '{deleted_note['project']}'")
                self.load_eadr_note_history()
                messagebox.showinfo("Success", "Note deleted successfully.")
            else:
                messagebox.showerror("Error", "Failed to delete note.")

    def save_new_eadr_note(self):
        """Save a new eADR note and update the history"""
        note_text = self.note_text.get("1.0", tk.END).strip()
        if not note_text:
            messagebox.showwarning("Empty Note", "Please enter a note before saving.")
            return
        
        project = self.project_entry.get().strip() or "Origin"
        
        if save_eadr_note(note_text, project):
            self.log(f"eADR note saved for project: {project}")
            self.note_text.delete("1.0", tk.END)
            self.load_eadr_note_history()
            messagebox.showinfo("Success", "eADR note saved successfully.")
        else:
            messagebox.showerror("Error", "Failed to save eADR note.")

    def load_eadr_note_history(self):
        """Load and display the history of eADR notes"""
        # Clear existing items
        for item in self.notes_treeview.get_children():
            self.notes_treeview.delete(item)
        
        notes = load_eadr_notes()
        for i, note in enumerate(reversed(notes)):
            self.notes_treeview.insert("", tk.END, iid=str(i), values=(note["timestamp"], note["project"]), tags=(str(len(notes)-1-i),))
            
        # Disable delete button when reloading notes
        self.delete_note_button.config(state=tk.DISABLED)
        
        # Clear the display text
        self.display_text.config(state=tk.NORMAL)
        self.display_text.delete("1.0", tk.END)
        self.display_text.config(state=tk.DISABLED)

    def display_selected_note(self, event):
        """Display the content of the selected note"""
        selection = self.notes_treeview.selection()
        if not selection:
            self.delete_note_button.config(state=tk.DISABLED)
            return
        
        item_id = selection[0]
        note_index = self.notes_treeview.item(item_id, "tags")[0]
        
        notes = load_eadr_notes()
        if int(note_index) < len(notes):
            note = notes[int(note_index)]
            
            self.display_text.config(state=tk.NORMAL)
            self.display_text.delete("1.0", tk.END)
            self.display_text.insert(tk.END, f"Project: {note['project']}\n")
            self.display_text.insert(tk.END, f"Date & Time: {note['timestamp']}\n\n")
            self.display_text.insert(tk.END, note["note"])
            self.display_text.config(state=tk.DISABLED)
            
            # Enable the delete button since a note is selected
            self.delete_note_button.config(state=tk.NORMAL)

    # -----------
    # General UI Methods
    # -----------
    def set_theme(self, theme):
        style = ttk.Style()
        try:
            style.theme_use(theme)
            self.log(f"Theme changed to: {theme}")
        except Exception as e:
            self.log(f"Error setting theme {theme}: {e}")

    def change_theme(self, event):
        selected_theme = self.theme_combo.get()
        self.set_theme(selected_theme)

    # -----------
    # Logging Helper
    # -----------
    def log(self, message):
        timestamp = datetime.now().strftime('%H:%M:%S')
        self.log_text.insert(tk.END, f"{timestamp} - {message}\n")
        self.log_text.see(tk.END)

    # -----------
    # Profile Management
    # -----------
    def load_profile(self, event=None):
        prof_name = self.profile_combo.get()
        if prof_name in self.profiles:
            prof = self.profiles[prof_name]
            self.folders = prof.get("folders", [])
            self.all_files = prof.get("files", [])
            self.header_entry.delete(0, tk.END)
            self.header_entry.insert(0, prof.get("header", ""))
            self.footer_entry.delete(0, tk.END)
            self.footer_entry.insert(0, prof.get("footer", ""))
            self.ext_entry.delete(0, tk.END)
            self.ext_entry.insert(0, prof.get("allowed_extensions", self.allowed_extensions))
            self.min_token_entry.delete(0, tk.END)
            self.min_token_entry.insert(0, str(prof.get("min_tokens", self.min_tokens)))
            # If you decide to persist ignored folders in profiles, add similar logic here.
            self.log(f"Loaded profile '{prof_name}'.")
            self.apply_filters()
            self.current_profile = prof_name

    def save_current_profile(self):
        prof_name = self.profile_combo.get().strip()
        if not prof_name:
            messagebox.showerror("Error", "Please enter a valid profile name.")
            return
        self.profiles[prof_name] = {
            "folders": self.folders,
            "files": self.all_files,
            "header": self.header_entry.get(),
            "footer": self.footer_entry.get(),
            "allowed_extensions": self.ext_entry.get(),
            "min_tokens": int(self.min_token_entry.get() or 0)
            # You can also persist ignored folders if desired.
        }
        save_profiles(self.profiles)
        self.profile_combo['values'] = list(self.profiles.keys())
        self.log(f"Profile '{prof_name}' saved.")
        self.current_profile = prof_name

    def new_profile(self):
        new_prof = simpledialog.askstring("New Profile", "Enter new profile name:")
        if new_prof:
            self.profile_combo.set(new_prof)
            self.folders = []
            self.all_files = []
            self.header_entry.delete(0, tk.END)
            self.footer_entry.delete(0, tk.END)
            self.log(f"New profile '{new_prof}' created.")
            self.apply_filters()

    # -----------
    # Drag-n-Drop Simulation
    # -----------
    def simulate_drop(self, event):
        choice = messagebox.askquestion("Add Items", "Would you like to add files? (Click 'No' to add a folder)")
        if choice == "yes":
            self.add_files()
        else:
            self.add_folder()

    # -----------
    # File/Folder Selection and Scanning
    # -----------
    def add_folder(self):
        folder = filedialog.askdirectory(title="Select Folder")
        if folder and folder not in self.folders:
            self.folders.append(folder)
            self.log(f"Added folder: {folder}")
            self.scan_single_folder(folder)
            self.apply_filters()

    def scan_single_folder(self, folder):
        allowed = [ext.strip().lower() for ext in self.ext_entry.get().split(",") if ext.strip()]
        # Get ignored folder names from the UI entry (comma‑separated)
        ignored_folders = [name.strip() for name in self.ignore_entry.get().split(",") if name.strip()]
        for root, dirs, files in os.walk(folder):
            # Remove directories whose names match any in the ignored list.
            dirs[:] = [d for d in dirs if d not in ignored_folders]
            for f in files:
                ext = os.path.splitext(f)[1].lower()
                if allowed and ext not in allowed:
                    continue
                filepath = os.path.join(root, f)
                if filepath not in self.all_files:
                    self.all_files.append(filepath)
                    self.log(f"Found file: {filepath}")

    def add_files(self):
        filetypes = [("Supported files", "*.py *.kt *.xml *.html *.js *.txt *.md *.json *.css *.bat *.db *.p12 *.pem *.sh *.env *.R"), ("All files", "*.*")]
        selected = filedialog.askopenfilenames(title="Select File(s)", filetypes=filetypes)
        for file in selected:
            if file not in self.all_files:
                self.all_files.append(file)
                self.log(f"Added file: {file}")
        self.apply_filters()

    def scan_folders(self):
        def scan():
            self.progress["maximum"] = len(self.folders)
            count = 0
            for folder in self.folders:
                self.scan_single_folder(folder)
                count += 1
                self.progress["value"] = count
            self.apply_filters()
            self.progress["value"] = 0
            self.log("Folder scanning complete.")
        threading.Thread(target=scan, daemon=True).start()

    # -----------
    # Compute Folder Token Count
    # -----------
    def compute_folder_tokens(self, folder):
        allowed = [ext.strip().lower() for ext in self.ext_entry.get().split(",") if ext.strip()]
        # Get ignored folder names from the UI entry
        ignored_folders = [name.strip() for name in self.ignore_entry.get().split(",") if name.strip()]
        total = 0
        for root, dirs, files in os.walk(folder):
            # Remove directories matching any ignored folder.
            dirs[:] = [d for d in dirs if d not in ignored_folders]
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if allowed and ext not in allowed:
                    continue
                file_path = os.path.join(root, file)
                tokens = count_tokens_in_file(file_path)
                if tokens < self.min_tokens:
                    continue
                total += tokens
        return total

    # -----------
    # Filtering: Allowed Extensions, Min Token Count, & Ignored Folders
    # -----------
    def apply_filters(self):
        self.allowed_extensions = self.ext_entry.get()
        try:
            self.min_tokens = int(self.min_token_entry.get())
        except:
            self.min_tokens = 0
        allowed = [ext.strip().lower() for ext in self.allowed_extensions.split(",") if ext.strip()]
        self.filtered_files = []
        for item in self.file_tree.get_children():
            self.file_tree.delete(item)
        for file in self.all_files:
            ext = os.path.splitext(file)[1].lower()
            if allowed and ext not in allowed:
                continue
            tokens = count_tokens_in_file(file)
            if tokens < self.min_tokens:
                continue
            self.filtered_files.append(file)
            self.file_tree.insert("", tk.END, values=(file, f"{tokens:,}"))
        self.log(f"Filter applied: {len(self.filtered_files)} files shown.")

        for item in self.folder_tree.get_children():
            self.folder_tree.delete(item)
        for folder in self.folders:
            tokens = self.compute_folder_tokens(folder)
            self.folder_tree.insert("", tk.END, values=(folder, f"{tokens:,}"))
        self.log(f"{len(self.folders)} folders shown in folder list.")

        self.update_preview()

    # -----------
    # Real-Time Preview Update and Token Counts
    # -----------
    def update_preview(self):
        header = self.header_entry.get()
        footer = self.footer_entry.get()
        full_text = build_combined_text(self.filtered_files, header, footer)
        self.preview_text.delete("1.0", tk.END)
        self.preview_text.insert(tk.END, full_text)
        full_tokens = count_tokens(full_text)
        content_only_text = build_content_only_text(self.filtered_files)
        content_tokens = count_tokens(content_only_text)
        self.token_with_label.config(text=f"Tokens (with headers): {full_tokens:,}")
        self.token_without_label.config(text=f"Tokens (without headers): {content_tokens:,}")
        self.log(f"Preview updated. Total tokens (with headers): {full_tokens:,}; (without headers): {content_tokens:,}")

    # -----------
    # Combine Scripts
    # -----------
    def combine_scripts(self):
        if not self.filtered_files:
            messagebox.showerror("Error", "No files selected after filtering.")
            return
        header = self.header_entry.get()
        footer = self.footer_entry.get()
        combined_text = build_combined_text(self.filtered_files, header, footer)
        total_tokens = count_tokens(combined_text)
        output_dir = "backup"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"combined_scripts_{timestamp}_{total_tokens:,}tokens.md"
        filename = filename.replace(",", "")
        output_file = os.path.join(output_dir, filename)
        try:
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(combined_text)
            self.log(f"Combined file created: {output_file}")
            
            # Automatically create an eADR note with comprehensive information
            project = self.project_entry.get().strip() or "Origin"
            
            # Check if there's content in the New Note area, and use it if available
            user_note = self.note_text.get("1.0", tk.END).strip()
            
            # Start with user's note content if available
            if user_note:
                note_text = f"{user_note}\n\n--- Automatic Script Combination Information ---\n\n"
                # Clear the note text area since we've captured its content
                self.note_text.delete("1.0", tk.END)
            else:
                note_text = ""
                
            # Add the standard automatic note content
            note_text += f"Created combined file: '{filename}'\n"
            note_text += f"Total tokens: {total_tokens:,}\n\n"
            
            # Include folders information
            note_text += f"Folders used ({len(self.folders)}):\n"
            if self.folders:
                for folder in self.folders:
                    note_text += f"- {folder}\n"
            else:
                note_text += "- No folders were directly selected\n"
            
            # Include filter information
            note_text += f"\nFilter settings:\n"
            note_text += f"- Extensions: {self.allowed_extensions}\n"
            note_text += f"- Min tokens: {self.min_tokens}\n"
            note_text += f"- Ignored folders: {self.ignore_entry.get()}\n"
            
            # Include files information
            note_text += f"\nFiles included ({len(self.filtered_files)}):\n"
            for f in self.filtered_files:
                note_text += f"- {f}\n"
                
            if save_eadr_note(note_text, project):
                self.log(f"eADR note automatically created for combined scripts")
                self.load_eadr_note_history()
            
            messagebox.showinfo("Success", f"Combined file created:\n{output_file}")
        except Exception as e:
            self.log(f"Error writing output file: {e}")
            messagebox.showerror("Error", f"Failed to write output file:\n{e}")

    # -----------
    # Remove Selected Files
    # -----------
    def remove_selected_files(self):
        selected = self.file_tree.selection()
        if not selected:
            return
        for item in selected:
            file_path = self.file_tree.item(item, "values")[0]
            if file_path in self.all_files:
                self.all_files.remove(file_path)
            if file_path in self.filtered_files:
                self.filtered_files.remove(file_path)
            self.file_tree.delete(item)
            self.log(f"Removed file: {file_path}")
        self.apply_filters()

    # -----------
    # Remove Selected Folders
    # -----------
    def remove_selected_folders(self):
        selected = self.folder_tree.selection()
        if not selected:
            return
        for item in selected:
            folder_path = self.folder_tree.item(item, "values")[0]
            if folder_path in self.folders:
                self.folders.remove(folder_path)
            files_to_remove = [f for f in self.all_files if f.startswith(folder_path)]
            for f in files_to_remove:
                if f in self.all_files:
                    self.all_files.remove(f)
                if f in self.filtered_files:
                    self.filtered_files.remove(f)
            self.folder_tree.delete(item)
            self.log(f"Removed folder: {folder_path}")
        self.apply_filters()

    def _on_close(self):
        """Handle application close event"""
        # Stop the proxy server if running
        if hasattr(self, 'proxy_process') and self.proxy_process is not None and self.proxy_process.poll() is None:
            self.stop_proxy_server()

        # Stop the watcher
        if hasattr(self, 'claude_watcher'):
            self.claude_watcher.stop()
        
        # Close the application
        self.master.destroy()             

class PromptFileWatcher:
    """Watch for changes to prompt files and trigger UI updates"""
    
    def __init__(self, app, file_path, check_interval=2.0):
        """Initialize the file watcher
        
        Args:
            app: The main application instance
            file_path: Path to the claude_prompts.json file
            check_interval: How often to check for changes (in seconds)
        """
        self.app = app
        self.file_path = file_path
        self.check_interval = check_interval
        self.last_modified = self._get_last_modified()
        self.last_prompt_count = self._get_prompt_count()
        self.running = False
        self.thread = None
    
    def _get_last_modified(self):
        """Get the last modified time of the file"""
        try:
            if os.path.exists(self.file_path):
                return os.path.getmtime(self.file_path)
            return 0
        except Exception:
            return 0
    
    def _get_prompt_count(self):
        """Get the number of prompts in the file"""
        try:
            if os.path.exists(self.file_path):
                with open(self.file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return len(data)
            return 0
        except Exception:
            return 0
    
    def start(self):
        """Start watching for changes"""
        if self.running:
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._watch_loop, daemon=True)
        self.thread.start()
        self.app.log("Started watching for Claude prompt changes")
    
    def stop(self):
        """Stop watching for changes"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)
            self.thread = None
            self.app.log("Stopped watching for Claude prompt changes")
    
    def _watch_loop(self):
        """Main watching loop"""
        while self.running:
            try:
                current_modified = self._get_last_modified()
                current_count = self._get_prompt_count()
                
                # Check if file has been modified
                if current_modified > self.last_modified or current_count != self.last_prompt_count:
                    self.app.log(f"Detected changes in Claude prompts file ({current_count} prompts)")
                    
                    # Update our tracking values
                    self.last_modified = current_modified
                    self.last_prompt_count = current_count
                    
                    # Schedule UI update on the main thread
                    self.app.master.after(100, self._update_ui)
            except Exception as e:
                self.app.log(f"Error checking Claude prompts file: {e}")
            
            # Sleep before checking again
            time.sleep(self.check_interval)
    
    def _update_ui(self):
        """Update the UI with new prompts"""
        try:
            # Reload the prompt database
            self.app.prompt_database.load()
            
            # Refresh the prompt history view
            self.app.refresh_prompt_history()
            
            # Update the file list if it exists
            if hasattr(self.app, 'refresh_file_list'):
                self.app.refresh_file_list()
            
            self.app.log("Refreshed prompt history with new Claude prompts")
        except Exception as e:
            self.app.log(f"Error updating UI with new prompts: {e}")        

# -------------------------------
# Main
# -------------------------------
if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()



