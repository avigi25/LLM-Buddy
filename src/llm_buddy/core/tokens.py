"""
Token counting and text building utilities for LLM Buddy.
"""

import uuid
import logging

logger = logging.getLogger(__name__)

def build_combined_text(selected_files, header="", footer=""):
    """
    Build combined text from selected files with optional header/footer.

    Each file is preceded by a dynamically generated marker for identification
    to prevent markdown collision.
    """
    lines = []
    
    # Generate a unique 8-character ID for this specific backup
    session_id = uuid.uuid4().hex[:8]
    dynamic_marker = f"@§A_{session_id}@"
    
    # Declare the marker at the very top of the file so rollback can find it
    lines.append(f"LLM_BUDDY_MARKER: {dynamic_marker}")
    lines.append("")
    
    if header:
        lines.append(header)
        lines.append("")
        
    for file_path in selected_files:
        # Use the dynamic marker instead of ###
        lines.append(f"{dynamic_marker} {file_path}")
        lines.append("")
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines.append(f.read())
        except Exception as e:
            lines.append(f"Error reading file: {e}")
        lines.append("")
        
    if footer:
        lines.append(footer)
        
    return "\n".join(lines)


def build_content_only_text(file_paths):
    """Build combined text from files without headers."""
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
    """Count tokens in a text string using tiktoken."""
    try:
        import tiktoken
        encoding = tiktoken.get_encoding(encoding_name)
        return len(encoding.encode(text))
    except ImportError:
        logger.warning("tiktoken not installed, falling back to word count")
        return len(text.split())
    except Exception as e:
        logger.error("Error counting tokens: %s", e)
        return len(text.split())


def count_tokens_in_file(filepath, encoding_name="cl100k_base"):
    """Count tokens in a file."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            text = f.read()
        return count_tokens(text, encoding_name)
    except Exception:
        return 0
