"""File scanning, filtering, and token computation — no GUI imports."""

import os
from typing import List, Tuple

from llm_buddy.core.tokens import count_tokens_in_file


def scan_folder(
    folder: str,
    allowed_extensions: List[str],
    ignored_folders: List[str],
) -> List[str]:
    """Walk *folder* and return paths matching the extension/ignore filters.

    Parameters
    ----------
    folder : str
        Root directory to scan.
    allowed_extensions : list[str]
        Lowercase extensions including the dot (e.g. ``[".py", ".js"]``).
        An empty list means "accept all extensions".
    ignored_folders : list[str]
        Folder names to skip (e.g. ``["node_modules", "__pycache__"]``).

    Returns
    -------
    list[str]
        Absolute file paths found under *folder*.
    """
    found: List[str] = []
    for root, dirs, files in os.walk(folder):
        dirs[:] = [d for d in dirs if d not in ignored_folders]
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if allowed_extensions and ext not in allowed_extensions:
                continue
            found.append(os.path.join(root, f))
    return found


def filter_files(
    all_files: List[str],
    allowed_extensions: List[str],
    min_tokens: int,
) -> List[Tuple[str, int]]:
    """Filter *all_files* by extension and minimum token count.

    Returns a list of ``(path, token_count)`` tuples for files that pass.
    """
    result: List[Tuple[str, int]] = []
    for filepath in all_files:
        ext = os.path.splitext(filepath)[1].lower()
        if allowed_extensions and ext not in allowed_extensions:
            continue
        tokens = count_tokens_in_file(filepath)
        if tokens < min_tokens:
            continue
        result.append((filepath, tokens))
    return result


def compute_folder_tokens(
    folder: str,
    allowed_extensions: List[str],
    ignored_folders: List[str],
    min_tokens: int = 0,
) -> int:
    """Return the total token count of qualifying files under *folder*."""
    total = 0
    for root, dirs, files in os.walk(folder):
        dirs[:] = [d for d in dirs if d not in ignored_folders]
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if allowed_extensions and ext not in allowed_extensions:
                continue
            filepath = os.path.join(root, f)
            tokens = count_tokens_in_file(filepath)
            if tokens < min_tokens:
                continue
            total += tokens
    return total


def parse_extensions(raw: str) -> List[str]:
    """Parse a comma-separated extensions string into a normalised list.

    Example: ``".py, .js , .ts"`` → ``[".py", ".js", ".ts"]``
    """
    return [ext.strip().lower() for ext in raw.split(",") if ext.strip()]


def parse_ignored_folders(raw: str) -> List[str]:
    """Parse a comma-separated ignored-folders string into a list."""
    return [name.strip() for name in raw.split(",") if name.strip()]
