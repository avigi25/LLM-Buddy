"""Backup business logic — no GUI imports.

Extracted from ``gui.mixin_backup``.
"""

import fnmatch
import os
from datetime import datetime
from typing import List, Tuple

from llm_buddy.core.eadr import save_eadr_note
from llm_buddy.core.tokens import (
    build_combined_text,
    count_tokens,
    count_tokens_in_file,
)


def create_auto_backup(
    changed_files: List[Tuple[str, int]],
    monitor_files: List[str],
    active_prompt,
    prompt_database,
    output_dir: str = "backup",
) -> Tuple[bool, str]:
    """Create an auto-backup file.

    Returns ``(success, output_file_path)``.
    """
    active_prompt_info = ""
    if active_prompt:
        for fp, tc in changed_files:
            if fp not in active_prompt.associated_files:
                active_prompt.associated_files.append(fp)
                active_prompt.file_changes[fp] = tc
        prompt_database.save()
        active_prompt_info = (
            f"\nActive Prompt: "
            f"{active_prompt.description or 'Untitled'} "
            f"({active_prompt.llm_used})")

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    total_changes = sum(c for _, c in changed_files)
    backup_name = (
        f"auto_backup_{ts}_{len(changed_files)}files_"
        f"{total_changes}tokens.md")

    files_to_backup = [fp for fp, _ in changed_files]
    for fp in monitor_files:
        if fp not in files_to_backup and os.path.isfile(fp):
            files_to_backup.append(fp)

    header = (
        f"Auto-Backup generated on "
        f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        f"\nChanged files: {len(changed_files)}, "
        f"Total token changes: {total_changes}"
        f"{active_prompt_info}")
    if active_prompt:
        header += "\n\nPrompt Text:\n" + active_prompt.prompt_text

    combined_text = build_combined_text(
        files_to_backup, header, "End of Auto-Backup")
    total_tokens = count_tokens(combined_text)

    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, backup_name)

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(combined_text)

    return True, output_file


def build_backup_eadr_note(
    backup_name: str,
    changed_files: List[Tuple[str, int]],
    total_tokens: int,
    active_prompt=None,
) -> str:
    """Build the eADR note text for an auto-backup event."""
    note = (
        f"Auto-Backup Created: {backup_name}\n\n"
        f"Total files: {len(changed_files)}\n"
        f"Total tokens: {total_tokens:,}\n\n")
    if active_prompt:
        note += (
            f"Active Prompt: "
            f"{active_prompt.description or 'Untitled'}\n"
            f"LLM Used: {active_prompt.llm_used}\n\n"
            f"Prompt Text:\n{active_prompt.prompt_text}\n\n")
    note += "Changed files:\n"
    for fp, tc in changed_files:
        note += f"- {fp} ({tc:+,} tokens)\n"
    return note


def collect_force_backup_files(
    monitor_files: List[str],
    monitor_folders: List[str],
    ignored_patterns: List[str],
) -> List[Tuple[str, int]]:
    """Enumerate all monitored files with their token counts.

    Used by the "Force Backup Now" action.
    """
    files_to_backup: List[str] = []
    for fp in monitor_files:
        if os.path.isfile(fp):
            files_to_backup.append(fp)
    for folder in monitor_folders:
        if os.path.isdir(folder):
            for root, _, files in os.walk(folder):
                for fn in files:
                    skip = any(
                        fnmatch.fnmatch(fn, pat) for pat in ignored_patterns)
                    if not skip:
                        files_to_backup.append(os.path.join(root, fn))
    return [(fp, count_tokens_in_file(fp)) for fp in files_to_backup]


def prune_old_auto_backups(backup_dir: str, max_backups: int) -> List[str]:
    """Remove the oldest auto-backups beyond *max_backups*.

    Returns a list of deleted file paths.
    """
    if not os.path.exists(backup_dir):
        return []
    auto_backups = []
    for fn in os.listdir(backup_dir):
        if fn.startswith("auto_backup_") and fn.endswith(".md"):
            fp = os.path.join(backup_dir, fn)
            auto_backups.append((fp, os.path.getmtime(fp)))
    auto_backups.sort(key=lambda x: x[1], reverse=True)

    deleted = []
    for fp, _ in auto_backups[max_backups:]:
        try:
            os.remove(fp)
            deleted.append(fp)
        except Exception:
            pass
    return deleted
