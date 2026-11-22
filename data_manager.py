"""
Data Manager Module
-------------------
Handles reading, validating, processing, and updating clinic visit records.
Guarantees robust error handling so bad data never crashes the application.
"""

import os
import csv
import re
from typing import List, Dict, Any, Tuple
from red_flags import has_red_flag
from classifier import classify_note
from priority import assign_priority, parse_time, sort_queue

DEFAULT_INPUT_FILE = "visits.csv"
DEFAULT_QUEUE_FILE = "nurse_queue.csv"


def validate_time_format(time_str: str) -> bool:
    """
    Validates whether the string conforms to standard HH:MM (24-hour) time.
    """
    if not time_str or not isinstance(time_str, str):
        return False
    time_str = time_str.strip()
    match = re.match(r"^([01]\d|2[0-3]):([0-5]\d)$", time_str)
    return bool(match)


def load_raw_visits(filepath: str = DEFAULT_INPUT_FILE) -> Tuple[List[Dict[str, str]], List[str]]:
    """
    Reads visits.csv dynamically.
    Returns:
        (records, error_messages)
    """
    if not os.path.exists(filepath):
        return [], [f"File '{filepath}' not found."]

    records = []
    try:
        with open(filepath, mode="r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            required = {"id", "time", "note"}
            if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
                return [], [f"File '{filepath}' must contain columns: id, time, note."]
            for row in reader:
                records.append({
                    "id": (row.get("id") or "").strip(),
                    "time": (row.get("time") or "").strip(),
                    "note": (row.get("note") or "").strip()
                })
    except Exception as e:
        return [], [f"Error reading '{filepath}': {str(e)}"]

    return records, []


def process_visits(records: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    """
    Processes all visit records:
    1. Validates ID, time format, and note content.
    2. Runs red-flag safety detection (English & Tamil/Tanglish).
    3. Requests AI classification (with automatic retry & fallback).
    4. Enforces priority assignment rules (red-flag override, dizziness guard).
    5. Flags data quality issues without dropping records.
    6. Sorts by priority and arrival time.
    """
    seen_ids = set()
    processed = []

    for row in records:
        issues = []
        raw_id = row.get("id", "").strip()
        raw_time = row.get("time", "").strip()
        raw_note = row.get("note", "").strip()

        # ID Validation
        if not raw_id:
            issues.append("missing_id")
        elif raw_id in seen_ids:
            issues.append(f"duplicate_id({raw_id})")
        else:
            seen_ids.add(raw_id)

        # Time Validation
        if not raw_time:
            issues.append("missing_time")
        elif not validate_time_format(raw_time):
            issues.append("invalid_time_format")

        # Note Validation
        if not raw_note:
            issues.append("empty_note")

        # Red-flag Detection
        red_flag = has_red_flag(raw_note)

        # AI Classification (Category, Priority, Summary)
        ai_res = classify_note(raw_note)

        # Final Priority Assignment (Rule-enforced)
        final_priority = assign_priority(raw_note, ai_res.get("priority"), red_flag)

        processed_row = {
            "id": raw_id,
            "time": raw_time,
            "note": raw_note,
            "category": ai_res.get("category", "other"),
            "summary": ai_res.get("summary", "Could not classify, nurse to review"),
            "priority": final_priority,
            "red_flag": "True" if red_flag else "False",
            "data_issue": ";".join(issues)
        }
        processed.append(processed_row)

    # Sort queue: see_now -> today -> routine, then arrival time
    return sort_queue(processed)


def save_nurse_queue(records: List[Dict[str, Any]], filepath: str = DEFAULT_QUEUE_FILE) -> bool:
    """
    Saves processed queue records to CSV.
    Columns: id, time, note, category, summary, priority, red_flag, data_issue
    """
    fields = ["id", "time", "note", "category", "summary", "priority", "red_flag", "data_issue"]
    try:
        with open(filepath, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            writer.writerows(records)
        return True
    except Exception as e:
        print(f"Error saving {filepath}: {e}")
        return False


def append_new_visit(student_id: str, visit_time: str, note: str, filepath: str = DEFAULT_INPUT_FILE) -> Tuple[bool, str]:
    """
    Appends a new student registration to visits.csv dynamically.
    """
    student_id = (student_id or "").strip()
    visit_time = (visit_time or "").strip()
    note = (note or "").strip()

    if not student_id:
        return False, "Student ID cannot be empty."
    if not visit_time or not validate_time_format(visit_time):
        return False, "Invalid arrival time. Must be HH:MM in 24-hr format."

    file_exists = os.path.exists(filepath)
    try:
        with open(filepath, mode="a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(["id", "time", "note"])
            writer.writerow([student_id, visit_time, note])
        return True, "Visit registered successfully."
    except Exception as e:
        return False, f"Failed to save visit: {str(e)}"
