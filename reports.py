"""
Reports Generation Module
-------------------------
Generates:
1. summary.txt: Text analytics file for clinic administration.
2. Analytics metrics dictionaries for the Flask Dashboard.
"""

import os
from collections import Counter
from typing import List, Dict, Any
from priority import parse_time
from classifier import ALLOWED_CATEGORIES

DEFAULT_SUMMARY_FILE = "summary.txt"


def generate_metrics(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Computes all analytical counts dynamically from processed records:
    - Total count
    - Priority breakdown (see_now, today, routine)
    - Category breakdown (injury, fever_cold, stomach, pain, allergy, other)
    - Hour-wise breakdown (09:00, 10:00, etc.)
    - Red flags and data issues count
    """
    total = len(records)
    priority_counts = Counter(r.get("priority", "today") for r in records)
    category_counts = Counter(r.get("category", "other") for r in records)

    # Hourly distribution
    hour_counts = Counter()
    for r in records:
        t_val = r.get("time", "")
        if ":" in t_val:
            hour_str = t_val.split(":")[0].strip().zfill(2) + ":00"
            hour_counts[hour_str] += 1
        else:
            hour_counts["Unknown"] += 1

    red_flag_count = sum(1 for r in records if r.get("red_flag") == "True")
    issue_count = sum(1 for r in records if r.get("data_issue"))

    # Ensure all standard categories and priorities exist in counts
    priority_data = {
        "see_now": priority_counts.get("see_now", 0),
        "today": priority_counts.get("today", 0),
        "routine": priority_counts.get("routine", 0)
    }

    category_data = {cat: category_counts.get(cat, 0) for cat in sorted(ALLOWED_CATEGORIES)}

    # Sorted hourly buckets
    sorted_hours = sorted(hour_counts.keys())
    hour_data = {h: hour_counts[h] for h in sorted_hours}

    return {
        "total": total,
        "see_now": priority_data["see_now"],
        "today": priority_data["today"],
        "routine": priority_data["routine"],
        "priority_distribution": priority_data,
        "category_distribution": category_data,
        "hourly_distribution": hour_data,
        "red_flag_count": red_flag_count,
        "issue_count": issue_count
    }


def write_summary_report(records: List[Dict[str, Any]], filepath: str = DEFAULT_SUMMARY_FILE) -> bool:
    """
    Writes formatted clinical summary report to summary.txt.
    Strictly excludes individual student notes for health privacy.
    """
    metrics = generate_metrics(records)
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("CLINIC VISIT SORTER - SUMMARY REPORT\n")
            f.write("====================================\n\n")
            f.write(f"Total visits processed: {metrics['total']}\n\n")

            f.write("Priority Breakdown:\n")
            for p in ["see_now", "today", "routine"]:
                f.write(f"  - {p}: {metrics['priority_distribution'].get(p, 0)}\n")

            f.write("\nCategory Breakdown:\n")
            for cat, cnt in metrics['category_distribution'].items():
                f.write(f"  - {cat}: {cnt}\n")

            f.write("\nVisits by Arrival Hour:\n")
            for hr, cnt in metrics['hourly_distribution'].items():
                f.write(f"  - {hr}: {cnt}\n")

            f.write("\nSafety & Data Quality:\n")
            f.write(f"  - Red-flag visits: {metrics['red_flag_count']}\n")
            f.write(f"  - Records with data issues: {metrics['issue_count']}\n\n")
            f.write("Academic Demonstration Disclaimer:\n")
            f.write("This tool assists with administrative queue prioritization only.\n")
            f.write("It does not provide diagnosis. Qualified nurses make all clinical decisions.\n")
        return True
    except Exception as e:
        print(f"Error writing summary report: {e}")
        return False
