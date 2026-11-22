"""
Flask Application for Clinic Visit Sorter
----------------------------------------
Routes:
/            -> Dashboard with statistical cards, charts, and system status
/queue       -> Interactive Nurse Queue table with search, filter, and badge highlights
/register    -> Form to record and classify a new student visit dynamically
/reports     -> Reports summary view with export and download options
/download-csv-> Direct file download of nurse_queue.csv
/about       -> Architecture, safety principles, team context, and viva prep
"""

import os
from flask import Flask, render_template, request, redirect, url_for, flash, send_file, jsonify
from data_manager import (
    load_raw_visits,
    process_visits,
    save_nurse_queue,
    append_new_visit,
    DEFAULT_INPUT_FILE,
    DEFAULT_QUEUE_FILE
)
from reports import generate_metrics, write_summary_report, DEFAULT_SUMMARY_FILE
from classifier import check_api_status
from red_flags import has_red_flag

app = Flask(__name__)
app.secret_key = "clinic-visit-sorter-secret-key-for-session"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_PATH = os.path.join(BASE_DIR, DEFAULT_INPUT_FILE)
QUEUE_PATH = os.path.join(BASE_DIR, DEFAULT_QUEUE_FILE)
SUMMARY_PATH = os.path.join(BASE_DIR, DEFAULT_SUMMARY_FILE)

# In-memory cache for processed records to ensure fast page loads
CACHED_PROCESSED_RECORDS = []


def refresh_data(force: bool = False):
    """
    Reads visits.csv, runs processing & rules, writes nurse_queue.csv and summary.txt.
    """
    global CACHED_PROCESSED_RECORDS
    if not CACHED_PROCESSED_RECORDS or force:
        raw_records, errs = load_raw_visits(INPUT_PATH)
        if raw_records:
            CACHED_PROCESSED_RECORDS = process_visits(raw_records)
            save_nurse_queue(CACHED_PROCESSED_RECORDS, QUEUE_PATH)
            write_summary_report(CACHED_PROCESSED_RECORDS, SUMMARY_PATH)
        else:
            CACHED_PROCESSED_RECORDS = []
    return CACHED_PROCESSED_RECORDS


@app.context_processor
def inject_system_status():
    """Makes API connection status globally accessible in all templates."""
    return {"api_status": check_api_status()}


@app.route("/")
def dashboard():
    """
    Displays the executive clinical dashboard:
    - Dynamic KPI stat cards
    - Chart data (priority breakdown, category breakdown, hourly trends)
    - High-priority alert banner if red-flag visits exist
    """
    records = refresh_data()
    metrics = generate_metrics(records)
    return render_template(
        "dashboard.html",
        metrics=metrics,
        records=records
    )


@app.route("/queue")
def queue():
    """
    Nurse queue triage view:
    - Lists all patient records in clinical sorted order (see_now -> today -> routine)
    - Search by student ID
    - Filter by priority and category
    - Preserves exact original note
    """
    records = refresh_data()
    search_query = request.args.get("search", "").strip().lower()
    priority_filter = request.args.get("priority", "").strip().lower()
    category_filter = request.args.get("category", "").strip().lower()

    filtered = records
    if search_query:
        filtered = [r for r in filtered if search_query in r.get("id", "").lower() or search_query in r.get("note", "").lower()]
    if priority_filter and priority_filter != "all":
        filtered = [r for r in filtered if r.get("priority", "").lower() == priority_filter]
    if category_filter and category_filter != "all":
        filtered = [r for r in filtered if r.get("category", "").lower() == category_filter]

    return render_template(
        "queue.html",
        records=filtered,
        total_records=len(records),
        search_query=search_query,
        selected_priority=priority_filter,
        selected_category=category_filter
    )


@app.route("/register", methods=["GET", "POST"])
def register():
    """
    Student visit registration form:
    Appends the visit to visits.csv and updates the queue immediately.
    """
    if request.method == "POST":
        student_id = request.form.get("student_id", "").strip()
        visit_time = request.form.get("visit_time", "").strip()
        note = request.form.get("note", "").strip()

        success, msg = append_new_visit(student_id, visit_time, note, INPUT_PATH)
        if success:
            flash(f"Visit registered successfully for {student_id}!", "success")
            refresh_data(force=True)
            return redirect(url_for("queue"))
        else:
            flash(f"Error registering visit: {msg}", "danger")

    return render_template("register.html")


@app.route("/reports")
def reports():
    """
    Administrative reports view:
    - Formatted text summary preview
    - Metrics table
    - Direct download trigger for CSV
    """
    records = refresh_data()
    metrics = generate_metrics(records)

    summary_content = ""
    if os.path.exists(SUMMARY_PATH):
        with open(SUMMARY_PATH, "r", encoding="utf-8") as f:
            summary_content = f.read()

    return render_template(
        "reports.html",
        metrics=metrics,
        summary_content=summary_content
    )


@app.route("/download-csv")
def download_csv():
    """
    Direct download endpoint for nurse_queue.csv.
    """
    refresh_data()
    if os.path.exists(QUEUE_PATH):
        return send_file(
            QUEUE_PATH,
            as_attachment=True,
            download_name="nurse_queue.csv",
            mimetype="text/csv"
        )
    flash("Report file not found. Please refresh data.", "warning")
    return redirect(url_for("reports"))


@app.route("/refresh")
def force_refresh():
    """
    Triggers re-classification and sorting of all records.
    """
    refresh_data(force=True)
    flash("Queue and statistics refreshed successfully.", "info")
    return redirect(request.referrer or url_for("dashboard"))


@app.route("/about")
def about():
    """
    Project documentation, design rationale, safety constraints, and viva QA.
    """
    return render_template("about.html")


if __name__ == "__main__":
    refresh_data(force=True)
    app.run(debug=True, host="127.0.0.1", port=5000)
