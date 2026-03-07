"""Preview / combine-scripts logic — no GUI imports.

Extracted from ``gui.mixin_preview.combine_scripts`` (the eADR-note
construction part).
"""

import os
from typing import List


def build_combine_eadr_note(
    folders: List[str],
    filtered_files: List[str],
    allowed_extensions: str,
    min_tokens: int,
    ignored_folders: str,
    output_file: str,
    total_tokens: int,
    user_note: str = "",
) -> str:
    """Build the eADR note text for a combine-scripts operation.

    Returns the full note string (caller is responsible for calling
    ``save_eadr_note``).
    """
    if user_note:
        note_text = (
            f"{user_note}\n\n"
            "--- Automatic Script Combination Information ---\n\n"
        )
    else:
        note_text = ""

    filename_only = os.path.basename(output_file)
    note_text += f"Created combined file: '{filename_only}'\n"
    note_text += f"Total tokens: {total_tokens:,}\n\n"

    note_text += f"Folders used ({len(folders)}):\n"
    if folders:
        for folder in folders:
            note_text += f"- {folder}\n"
    else:
        note_text += "- No folders were directly selected\n"

    note_text += f"\nFilter settings:\n"
    note_text += f"- Extensions: {allowed_extensions}\n"
    note_text += f"- Min tokens: {min_tokens}\n"
    note_text += f"- Ignored folders: {ignored_folders}\n"

    note_text += f"\nFiles included ({len(filtered_files)}):\n"
    for f in filtered_files:
        note_text += f"- {f}\n"

    return note_text
