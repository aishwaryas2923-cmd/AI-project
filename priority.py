"""
Priority Assignment and Queue Sorting Module
-------------------------------------------
Enforces clinical queue organization safety rules:
1. Priority hierarchy: see_now (0) > today (1) > routine (2)
2. Red-flag override: Any red flag MUST receive 'see_now'. AI cannot lower this.
3. Dizziness & nosebleed safety: Must receive at least 'today' (upgraded if routine).
4. Missing / very short note safety: Must receive 'today' (never routine).
5. Unsure / Unknown: Always treated as 'today' (never routine).
6. Never lower a priority assigned by rules.
7. Stable sorting: Primary by priority rank, secondary by arrival time.
"""

from datetime import datetime

ALLOWED_PRIORITIES = {"see_now", "today", "routine"}

PRIORITY_RANK = {
    "see_now": 0,
    "today": 1,
    "routine": 2
}

DIZZINESS_NOSEBLEED_TERMS = [
    "dizzy", "dizziness", "giddy", "giddiness",
    "nosebleed", "nose bleed", "blood varuthu",
    "thalai sut", "thala suth", "mayakkam"
]


def parse_time(value):
    """
    Parses 'HH:MM' time string.
    Returns datetime object for sorting, or datetime.max for missing/invalid times.
    """
    if not value or not isinstance(value, str):
        return datetime.max
    val = value.strip()
    try:
        return datetime.strptime(val, "%H:%M")
    except ValueError:
        return datetime.max


def assign_priority(note: str, ai_priority: str, red_flag: bool) -> str:
    """
    Determines final review priority strictly following clinical safety rules:
    - Rule 1: Red flags ALWAYS get 'see_now'. The AI is never allowed to lower it.
    - Rule 2: Empty or very short notes (< 3 chars) get 'today'.
    - Rule 3: Dizziness and nosebleed cases must receive at least 'today'
              (if AI suggested 'routine', bump to 'today'; if AI said 'see_now', keep 'see_now').
    - Rule 4: Otherwise, if AI returned a valid priority, use it.
    - Rule 5: Fallback to 'today' if invalid or unknown. Never routine.
    """
    # Safety Rule 1: Red flag override
    if red_flag:
        return "see_now"

    text = (note or "").strip().lower()

    # Safety Rule 2: Empty or very short note
    if len(text) < 3:
        return "today"

    # Safety Rule 3: Dizziness and nosebleed guard
    if any(term in text for term in DIZZINESS_NOSEBLEED_TERMS):
        if ai_priority == "routine" or ai_priority not in ALLOWED_PRIORITIES:
            return "today"
        return ai_priority

    # Safety Rule 4 & 5: Validated AI priority or default today
    if ai_priority in ALLOWED_PRIORITIES:
        return ai_priority

    return "today"


def sort_queue(records: list) -> list:
    """
    Sorts patient records:
    1. By priority: see_now first, then today, then routine.
    2. Within each priority, chronologically by arrival time (HH:MM).
    Records are never removed.
    """
    return sorted(
        records,
        key=lambda r: (
            PRIORITY_RANK.get(r.get("priority"), 1),
            parse_time(r.get("time"))
        )
    )
