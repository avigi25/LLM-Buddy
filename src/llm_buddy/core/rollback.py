"""
File rollback utilities for LLM Buddy.

Parse combined backup files and restore individual files from them.
"""

import difflib
import logging
import os
import re

logger = logging.getLogger(__name__)

def parse_combined_file(filepath):
    """
    Parse a combined backup file and extract individual files.
    Detects dynamic markers to prevent markdown collision, with a fallback
    to legacy ### markers for older backups.

    Returns:
        dict: Mapping of file paths to file contents.
    """
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        # 1. Look for the dynamic marker declaration at the top of the file
        marker_match = re.search(r'^LLM_BUDDY_MARKER:\s*(.+)$', content, flags=re.MULTILINE)
        
        if not marker_match:
            # Legacy fallback: If no dynamic marker is found, assume it's an old backup using ###
            dynamic_marker = "###"
        else:
            dynamic_marker = marker_match.group(1).strip()

        # 2. Escape the dynamic marker just in case, and split the file blocks
        split_pattern = rf'^{re.escape(dynamic_marker)} (.+?)$'
        file_blocks = re.split(split_pattern, content, flags=re.MULTILINE)

        files_dict = {}
        for i in range(1, len(file_blocks), 2):
            if i + 1 < len(file_blocks):
                file_path = file_blocks[i].strip()
                file_content = file_blocks[i + 1]
                
                # 1. CLEAN THE TOP: Remove the 2 artificial newlines 
                # (1 from the marker line ending + 1 from the injected empty line)
                if file_content.startswith('\n\n'):
                    file_content = file_content[2:]
                elif file_content.startswith('\n'):
                    file_content = file_content[1:]
                    
                # 2. CLEAN THE BOTTOM: Remove the artificial trailing newlines
                is_last_block = (i + 1 == len(file_blocks) - 1)
                
                if not is_last_block:
                    # Middle blocks have '\n\n' injected between them
                    if file_content.endswith('\n\n'):
                        file_content = file_content[:-2]
                else:
                    # The very last block only has a single '\n' injected at EOF
                    if file_content.endswith('\n'):
                        file_content = file_content[:-1]

                files_dict[file_path] = file_content

        return files_dict
    except Exception as e:
        logger.error("Error parsing combined file: %s", e)
        return {}


def restore_file(file_path, content):
    """
    Restore a file to its original location with the provided content.

    Creates parent directories if they don't exist.
    """
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return True
    except Exception as e:
        logger.error("Error restoring file %s: %s", file_path, e)
        return False


def get_file_diff(file_path, backup_content):
    """
    Get a unified diff between the current file and backup content.

    Returns a formatted diff string, or a status message if files
    are identical or the current file doesn't exist.
    """
    try:
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                current_content = f.read()
        else:
            return "Current file does not exist - this would be a new file creation."

        current_lines = current_content.splitlines()
        backup_lines = backup_content.splitlines()

        diff = difflib.unified_diff(
            current_lines, backup_lines,
            fromfile=f"Current: {file_path}",
            tofile=f"Backup: {file_path}",
            lineterm='',
        )

        diff_text = '\n'.join(list(diff))
        if not diff_text:
            return "No differences found."
        return diff_text
    except Exception as e:
        return f"Error generating diff: {e}"


def diff_two_contents(content_a, content_b, label_a="File A", label_b="File B"):
    """
    Get a unified diff between two arbitrary text contents.

    Args:
        content_a: Text content of the first file.
        content_b: Text content of the second file.
        label_a: Display label for the first file (used in diff header).
        label_b: Display label for the second file (used in diff header).

    Returns:
        A formatted unified diff string, or a status message if identical.
    """
    try:
        lines_a = content_a.splitlines()
        lines_b = content_b.splitlines()

        diff = difflib.unified_diff(
            lines_a, lines_b,
            fromfile=label_a,
            tofile=label_b,
            lineterm='',
        )

        diff_text = '\n'.join(list(diff))
        if not diff_text:
            return "No differences found."
        return diff_text
    except Exception as e:
        return f"Error generating diff: {e}"


def read_file_content(file_path):
    """
    Read and return the text content of a file.

    Args:
        file_path: Path to the file to read.

    Returns:
        Tuple of (content_string, error_string). On success error is None;
        on failure content is None.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read(), None
    except Exception as e:
        return None, str(e)
