#!/usr/bin/env python3
"""
Unified Prompt Database for LLM Buddy
Provides a common interface for storing prompts from different sources
"""

import os
import json
import uuid
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from venv import logger

# Default paths
DB_DIR = os.path.dirname(os.path.abspath(__file__))
SQLITE_DB_PATH = os.path.join(DB_DIR, "prompts.db")
JSON_DB_PATH = os.path.join(DB_DIR, "..", "claude_prompts.json")

class PromptDatabase:
    """Unified database for storing prompts from various sources"""
    
    def __init__(self, sqlite_path: str = SQLITE_DB_PATH, json_path: str = JSON_DB_PATH):
        """Initialize the database"""
        self.sqlite_path = sqlite_path
        self.json_path = json_path
        self._initialize_db()
    
    def _initialize_db(self):
        """Initialize the SQLite database"""
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(self.sqlite_path), exist_ok=True)
        
        # Connect to SQLite DB
        conn = sqlite3.connect(self.sqlite_path)
        cursor = conn.cursor()
        
        # Create tables if they don't exist
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS prompts (
            id TEXT PRIMARY KEY,
            timestamp TEXT NOT NULL,
            source TEXT NOT NULL,
            llm_name TEXT NOT NULL,
            model_name TEXT,
            prompt_text TEXT NOT NULL,
            description TEXT,
            url TEXT,
            conversation_id TEXT,
            metadata TEXT
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS file_associations (
            prompt_id TEXT,
            file_path TEXT,
            token_change INTEGER DEFAULT 0,
            PRIMARY KEY (prompt_id, file_path),
            FOREIGN KEY (prompt_id) REFERENCES prompts(id)
        )
        ''')
        
        conn.commit()
        conn.close()
    
    def add_prompt(self, 
                prompt_text: str, 
                llm_name: str, 
                source: str = "unknown",
                model_name: Optional[str] = None, 
                description: Optional[str] = None,
                url: Optional[str] = None,
                conversation_id: Optional[str] = None,
                metadata: Optional[Dict[str, Any]] = None,
                associated_files: Optional[List[str]] = None) -> str:
        """
        Add a new prompt to the database
        
        Args:
            prompt_text: The text of the prompt
            llm_name: Name of the LLM (ChatGPT, Claude, etc.)
            source: Source of the prompt (mcp, proxy, browser_extension, etc.)
            model_name: Specific model used (GPT-4, Claude-3, etc.)
            description: Optional description of the prompt
            url: URL where the prompt was sent
            conversation_id: ID of the conversation for grouping
            metadata: Additional metadata as a dictionary
            associated_files: List of files associated with this prompt
            
        Returns:
            The ID of the newly created prompt
        """
        prompt_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        
        # Connect to SQLite DB
        conn = sqlite3.connect(self.sqlite_path)
        cursor = conn.cursor()
        
        # Insert into prompts table
        cursor.execute('''
        INSERT INTO prompts 
        (id, timestamp, source, llm_name, model_name, prompt_text, description, url, conversation_id, metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            prompt_id, 
            timestamp, 
            source,
            llm_name, 
            model_name, 
            prompt_text, 
            description, 
            url,
            conversation_id,
            json.dumps(metadata) if metadata else None
        ))
        
        # Insert file associations if provided
        if associated_files:
            for file_path in associated_files:
                cursor.execute('''
                INSERT INTO file_associations (prompt_id, file_path)
                VALUES (?, ?)
                ''', (prompt_id, file_path))
        
        conn.commit()
        conn.close()
        
        # Always update JSON for all sources
        self._add_to_json_db(prompt_id, timestamp, prompt_text, llm_name, description, associated_files or [], source)
        
        return prompt_id
    
    def _add_to_json_db(self, prompt_id, timestamp, prompt_text, llm_name, description, associated_files, source="Unknown"):
        """Add prompt to JSON database for backward compatibility"""
        try:
            # Load existing prompts
            prompts = []
            if os.path.exists(self.json_path):
                with open(self.json_path, "r", encoding="utf-8") as f:
                    prompts = json.load(f)
            
            # Add new prompt with source field
            new_prompt = {
                "id": prompt_id,
                "timestamp": timestamp,
                "prompt_text": prompt_text,
                "description": description or f"Prompt from {llm_name}",
                "model": llm_name,
                "files": associated_files,
                "source": source  # Include the source field
            }
            
            prompts.append(new_prompt)
            
            # Save back to file
            with open(self.json_path, "w", encoding="utf-8") as f:
                json.dump(prompts, f, indent=4)
            
            return True
        except Exception as e:
            logger.error(f"Error adding to JSON database: {e}")
            return False
    
    def associate_files_with_prompt(self, prompt_id: str, file_paths: List[str], token_change: int = 0) -> bool:
        """
        Associate files with a prompt
        
        Args:
            prompt_id: ID of the prompt
            file_paths: List of file paths to associate
            token_change: Optional token change count
            
        Returns:
            True if successful, False otherwise
        """
        try:
            conn = sqlite3.connect(self.sqlite_path)
            cursor = conn.cursor()
            
            for file_path in file_paths:
                cursor.execute('''
                INSERT OR REPLACE INTO file_associations (prompt_id, file_path, token_change)
                VALUES (?, ?, ?)
                ''', (prompt_id, file_path, token_change))
            
            conn.commit()
            conn.close()
            
            # Update JSON DB for backward compatibility
            self._update_json_associations(prompt_id, file_paths)
            
            return True
        except Exception as e:
            print(f"Error associating files: {e}")
            return False
    
    def _update_json_associations(self, prompt_id, file_paths):
        """Update file associations in the JSON database"""
        try:
            if not os.path.exists(self.json_path):
                return False
                
            with open(self.json_path, "r", encoding="utf-8") as f:
                prompts = json.load(f)
            
            for prompt in prompts:
                if prompt.get("id") == prompt_id:
                    # Update files list
                    existing_files = set(prompt.get("files", []))
                    for file_path in file_paths:
                        existing_files.add(file_path)
                    prompt["files"] = list(existing_files)
                    break
            
            with open(self.json_path, "w", encoding="utf-8") as f:
                json.dump(prompts, f, indent=4)
                
            return True
        except Exception as e:
            print(f"Error updating JSON associations: {e}")
            return False
    
    def get_prompt(self, prompt_id: str) -> Optional[Dict[str, Any]]:
        """Get a prompt by ID with its associated files"""
        try:
            conn = sqlite3.connect(self.sqlite_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Get prompt data
            cursor.execute('''
            SELECT * FROM prompts WHERE id = ?
            ''', (prompt_id,))
            
            prompt_row = cursor.fetchone()
            if not prompt_row:
                conn.close()
                return None
                
            prompt_data = dict(prompt_row)
            
            # Parse metadata JSON
            if prompt_data.get('metadata'):
                prompt_data['metadata'] = json.loads(prompt_data['metadata'])
            
            # Get associated files
            cursor.execute('''
            SELECT file_path, token_change FROM file_associations 
            WHERE prompt_id = ?
            ''', (prompt_id,))
            
            file_rows = cursor.fetchall()
            prompt_data['associated_files'] = [row['file_path'] for row in file_rows]
            prompt_data['file_changes'] = {row['file_path']: row['token_change'] for row in file_rows}
            
            conn.close()
            return prompt_data
        except Exception as e:
            print(f"Error getting prompt: {e}")
            return None
    
    def get_prompts(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Get recent prompts with pagination"""
        try:
            conn = sqlite3.connect(self.sqlite_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
            SELECT * FROM prompts 
            ORDER BY timestamp DESC
            LIMIT ? OFFSET ?
            ''', (limit, offset))
            
            prompts = []
            for row in cursor.fetchall():
                prompt_data = dict(row)
                
                # Parse metadata JSON
                if prompt_data.get('metadata'):
                    prompt_data['metadata'] = json.loads(prompt_data['metadata'])
                
                # Get associated files
                cursor.execute('''
                SELECT file_path, token_change FROM file_associations 
                WHERE prompt_id = ?
                ''', (prompt_data['id'],))
                
                file_rows = cursor.fetchall()
                prompt_data['associated_files'] = [row['file_path'] for row in file_rows]
                prompt_data['file_changes'] = {row['file_path']: row['token_change'] for row in file_rows}
                
                prompts.append(prompt_data)
            
            conn.close()
            return prompts
        except Exception as e:
            print(f"Error getting prompts: {e}")
            return []
    
    def search_prompts(self, 
                       search_text: Optional[str] = None, 
                       llm_name: Optional[str] = None,
                       source: Optional[str] = None,
                       file_path: Optional[str] = None,
                       start_date: Optional[str] = None,
                       end_date: Optional[str] = None,
                       limit: int = 100) -> List[Dict[str, Any]]:
        """
        Search prompts with various filters
        
        Args:
            search_text: Text to search for in prompt_text or description
            llm_name: Filter by LLM name
            source: Filter by source
            file_path: Filter by associated file path
            start_date: Filter by start date (ISO format)
            end_date: Filter by end date (ISO format)
            limit: Maximum number of results to return
            
        Returns:
            List of matching prompts
        """
        try:
            conn = sqlite3.connect(self.sqlite_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            query = '''
            SELECT DISTINCT p.* FROM prompts p
            '''
            
            params = []
            where_clauses = []
            
            # Join with file_associations if needed
            if file_path:
                query += '''
                LEFT JOIN file_associations fa ON p.id = fa.prompt_id
                '''
                where_clauses.append("fa.file_path LIKE ?")
                params.append(f"%{file_path}%")
            
            # Add search conditions
            if search_text:
                where_clauses.append("(p.prompt_text LIKE ? OR p.description LIKE ?)")
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
            
            # Combine WHERE clauses
            if where_clauses:
                query += " WHERE " + " AND ".join(where_clauses)
            
            # Add sorting and limit
            query += '''
            ORDER BY p.timestamp DESC
            LIMIT ?
            '''
            params.append(limit)
            
            cursor.execute(query, params)
            
            prompts = []
            for row in cursor.fetchall():
                prompt_data = dict(row)
                
                # Parse metadata JSON
                if prompt_data.get('metadata'):
                    prompt_data['metadata'] = json.loads(prompt_data['metadata'])
                
                # Get associated files
                cursor.execute('''
                SELECT file_path, token_change FROM file_associations 
                WHERE prompt_id = ?
                ''', (prompt_data['id'],))
                
                file_rows = cursor.fetchall()
                prompt_data['associated_files'] = [row['file_path'] for row in file_rows]
                prompt_data['file_changes'] = {row['file_path']: row['token_change'] for row in file_rows}
                
                prompts.append(prompt_data)
            
            conn.close()
            return prompts
        except Exception as e:
            print(f"Error searching prompts: {e}")
            return []
    
    def get_prompts_count(self) -> int:
        """Get the total number of prompts in the database"""
        try:
            conn = sqlite3.connect(self.sqlite_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM prompts")
            count = cursor.fetchone()[0]
            
            conn.close()
            return count
        except Exception as e:
            print(f"Error getting prompts count: {e}")
            return 0
            
    def import_from_json(self, json_path: Optional[str] = None) -> int:
        """
        Import prompts from JSON database (like claude_prompts.json)
        
        Args:
            json_path: Path to JSON file, uses default if None
            
        Returns:
            Number of prompts imported
        """
        try:
            json_file = json_path or self.json_path
            
            if not os.path.exists(json_file):
                return 0
                
            with open(json_file, "r", encoding="utf-8") as f:
                prompts = json.load(f)
            
            conn = sqlite3.connect(self.sqlite_path)
            cursor = conn.cursor()
            
            import_count = 0
            for prompt in prompts:
                # Check if prompt already exists
                cursor.execute("SELECT id FROM prompts WHERE id = ?", (prompt.get("id"),))
                if cursor.fetchone():
                    continue
                
                # Extract data from JSON format
                prompt_id = prompt.get("id")
                timestamp = prompt.get("timestamp")
                prompt_text = prompt.get("prompt_text", "")
                description = prompt.get("description", "")
                llm_name = prompt.get("model", "Claude")  # Default to Claude for backward compatibility
                files = prompt.get("files", [])
                
                # Insert into prompts table
                cursor.execute('''
                INSERT OR IGNORE INTO prompts 
                (id, timestamp, source, llm_name, prompt_text, description)
                VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    prompt_id, 
                    timestamp, 
                    "json_import",
                    llm_name, 
                    prompt_text, 
                    description
                ))
                
                # Insert file associations
                for file_path in files:
                    cursor.execute('''
                    INSERT OR IGNORE INTO file_associations (prompt_id, file_path)
                    VALUES (?, ?)
                    ''', (prompt_id, file_path))
                
                import_count += 1
            
            conn.commit()
            conn.close()
            
            return import_count
        except Exception as e:
            print(f"Error importing from JSON: {e}")
            return 0