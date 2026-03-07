"""Prompt business logic — no GUI imports.

Extracted from ``gui.mixin_prompts``.
"""

import os
from datetime import datetime
from typing import List, Optional, Tuple

from llm_buddy.core.eadr import save_eadr_note


def infer_source(prompt) -> str:
    """Heuristic to determine a prompt's origin.

    Parameters
    ----------
    prompt : PromptRecord
        Must have ``.description``, ``.llm_used``, and optionally
        ``.source`` attributes.
    """
    if hasattr(prompt, "source") and prompt.source:
        return prompt.source

    desc = (prompt.description or "").lower()
    llm = prompt.llm_used or ""

    if "auto-recorded from claude desktop" in desc:
        return "Claude Desktop"
    if "browser extension" in desc or "captured" in desc:
        return "Browser Extension"
    if "proxy" in desc:
        return "Proxy"
    if llm == "Claude" and any(
        k in desc for k in ("mcp", "auto-recorded", "claude desktop")
    ):
        return "Claude Desktop"
    if any(k in desc for k in ("web", "browser", "via", "claude.ai")):
        return "Browser Extension"
    if "ChatGPT" in llm or "Gemini" in llm or "Perplexity" in llm:
        return "Browser Extension"
    return "Manual"


def export_prompt_history(prompt_database, output_dir: str = "prompts") -> str:
    """Export prompt history to a markdown file.

    Returns the path to the written file.
    """
    os.makedirs(output_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(output_dir, f"prompt_history_{ts}.md")

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(
            f"# Prompt History Export\nGenerated: "
            f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        sorted_prompts = sorted(
            prompt_database.prompts,
            key=lambda p: p.timestamp, reverse=True)
        for i, prompt in enumerate(sorted_prompts, 1):
            f.write(
                f"## {i}. {prompt.description or 'Untitled Prompt'}\n\n")
            f.write(
                f"- **Date & Time:** "
                f"{prompt.timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"- **LLM Used:** {prompt.llm_used}\n")
            f.write(f"- **ID:** {prompt.id}\n\n")
            f.write("### Prompt Text (Input)\n\n```\n")
            f.write(prompt.prompt_text)
            f.write("\n```\n\n")
            response = getattr(prompt, "response_text", "") or ""
            if response:
                f.write("### Response (Output)\n\n```\n")
                f.write(response)
                f.write("\n```\n\n")
            f.write("### Associated Files\n\n")
            if prompt.associated_files:
                for fp in prompt.associated_files:
                    change = prompt.file_changes.get(fp, "Unknown")
                    f.write(f"- `{fp}` (Token change: {change})\n")
            else:
                f.write("No files associated with this prompt.\n")
            if (hasattr(prompt, "retroactive_notes")
                    and prompt.retroactive_notes):
                f.write("\n### Retroactive Associations\n\n")
                for rts, nd in prompt.retroactive_notes.items():
                    f.write(
                        f"**{rts}**\n\n"
                        f"- Token Change: {nd['token_change']}\n")
                    f.write(f"- Notes: {nd['notes']}\n- Files:\n")
                    for rf in nd["files"]:
                        f.write(f"  - `{rf}`\n")
            f.write("\n---\n\n")

    return output_file


def perform_retroactive_association(
    prompt_database,
    prompt_index: int,
    selected_files: List[str],
    token_option: str,
    custom_token: int,
    notes: str,
    project: str = "Origin",
) -> Tuple[int, int]:
    """Associate files retroactively with a prompt.

    Returns ``(newly_added, already_associated)`` counts.
    """
    if prompt_index < 0 or prompt_index >= len(prompt_database.prompts):
        raise IndexError("Invalid prompt index")

    prompt = prompt_database.prompts[prompt_index]

    token_map = {
        "Auto": 100,
        "Minor (<50)": 25,
        "Moderate (50-200)": 100,
        "Major (>200)": 300,
        "Custom": custom_token,
    }
    token_change = token_map.get(token_option, 100)

    newly_added = 0
    for fp in selected_files:
        if fp not in prompt.associated_files:
            prompt.associated_files.append(fp)
            prompt.file_changes[fp] = token_change
            newly_added += 1
    prompt_database.save()

    if notes:
        if not hasattr(prompt, "retroactive_notes"):
            prompt.retroactive_notes = {}
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        prompt.retroactive_notes[ts] = {
            "files": selected_files,
            "token_change": token_change,
            "notes": notes,
        }
        prompt_database.save()

        note_text = (
            f"Retroactive Prompt Association\n\n"
            f"Prompt: {prompt.description or 'Untitled'}\n"
            f"Date: {ts}\nFiles associated: {len(selected_files)}\n\n"
            f"User Notes:\n{notes}\n\nFiles:\n")
        for fp in selected_files:
            note_text += f"- {fp}\n"
        save_eadr_note(note_text, project)

    already = len(selected_files) - newly_added
    return newly_added, already
