"""Analytics data computation — no GUI imports.

Extracted from ``gui.mixin_analytics._compute_analytics_data``.
"""

import logging
from collections import Counter
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Token counting — same logic as the original mixin
try:
    import tiktoken
    _ENC = tiktoken.encoding_for_model("gpt-4")

    def _count_tokens(text: str) -> int:
        return len(_ENC.encode(text)) if text else 0
except Exception:
    _ENC = None

    def _count_tokens(text: str) -> int:  # type: ignore[misc]
        return len(text) // 4 if text else 0


def compute_analytics_data(
    prompts: list,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db=None,
) -> Dict[str, Any]:
    """Aggregate prompt data for the analytics dashboard.

    Parameters
    ----------
    prompts : list
        Iterable of PromptRecord objects (must have ``.timestamp``,
        ``.llm_used``, ``.prompt_text``, and optionally ``.response_text``).
    start_date, end_date : datetime | None
        Optional date-range filter.

    Returns
    -------
    dict
        Keys: prompts_by_date, llm_distribution, tokens_by_date,
        timeline_events, total_prompts, total_tokens, unique_llms,
        active_days, start_date, end_date.
    """
    filtered = list(prompts)
    if start_date:
        filtered = [p for p in filtered if p.timestamp >= start_date]
    if end_date:
        filtered = [p for p in filtered if p.timestamp <= end_date]

    # Prompts per day (bar chart)
    date_counter: Counter = Counter()
    for p in filtered:
        date_counter[p.timestamp.strftime("%Y-%m-%d")] += 1
    sorted_dates = sorted(date_counter.keys())
    prompts_by_date = [(d, date_counter[d]) for d in sorted_dates]

    # LLM distribution (pie chart)
    llm_counter: Counter = Counter()
    for p in filtered:
        llm_counter[p.llm_used] += 1
    llm_distribution = list(llm_counter.most_common())

    # Token usage by day (line chart)
    token_day: Counter = Counter()
    total_tokens = 0
    for p in filtered:
        tok = _count_tokens(p.prompt_text)
        tok += _count_tokens(getattr(p, "response_text", "") or "")
        total_tokens += tok
        token_day[p.timestamp.strftime("%Y-%m-%d")] += tok
    sorted_tok_dates = sorted(token_day.keys())
    tokens_by_date = [(d, token_day[d]) for d in sorted_tok_dates]

    # Activity timeline
    timeline_events: List[Dict[str, Any]] = []
    for p in filtered:
        label = p.description or p.llm_used or "Prompt"
        if len(label) > 50:
            label = label[:47] + "\u2026"
        timeline_events.append({
            "time": p.timestamp,
            "type": "prompt",
            "label": label,
        })

    # eADR notes on the timeline
    try:
        notes = db.get_eadr_notes() if db is not None else []
        for n in notes:
            try:
                ts = datetime.strptime(n.timestamp, "%Y-%m-%d %H:%M:%S")
                if start_date and ts < start_date:
                    continue
                if end_date and ts > end_date:
                    continue
                label = n.note or "Note"
                if len(label) > 50:
                    label = label[:47] + "\u2026"
                timeline_events.append({
                    "time": ts,
                    "type": "note",
                    "label": label,
                })
            except (ValueError, KeyError):
                pass
    except Exception:
        pass

    timeline_events.sort(key=lambda e: e["time"])

    # Summary stats
    unique_dates = set(p.timestamp.date() for p in filtered)
    unique_llms = len(set(p.llm_used for p in filtered))

    return {
        "prompts_by_date": prompts_by_date,
        "llm_distribution": llm_distribution,
        "tokens_by_date": tokens_by_date,
        "timeline_events": timeline_events,
        "total_prompts": len(filtered),
        "total_tokens": total_tokens,
        "unique_llms": unique_llms,
        "active_days": len(unique_dates),
        "start_date": start_date,
        "end_date": end_date,
    }


def parse_date(s: str) -> Optional[datetime]:
    """Parse a ``YYYY-MM-DD`` string into a datetime, or *None*."""
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d")
    except ValueError:
        return None


def fmt_tokens(n: int) -> str:
    """Format a token count with thousand separators."""
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n:,.0f}"
    return str(n)
