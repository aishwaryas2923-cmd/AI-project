import csv
import json
import os
import time
import urllib.request
import urllib.error
from collections import Counter
from datetime import datetime

INPUT_FILE = "visits.csv"
QUEUE_FILE = "nurse_queue.csv"
SUMMARY_FILE = "summary.txt"

def load_dotenv():
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(env_path):
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip('"').strip("'")
                        if k and k not in os.environ:
                            os.environ[k] = v
        except Exception:
            pass

load_dotenv()

FALLBACK = {
    "category": "other",
    "priority": "today",
    "summary": "Could not classify, nurse to review"
}

ALLOWED_CATEGORIES = {"injury", "fever_cold", "stomach", "pain", "allergy", "other"}
ALLOWED_PRIORITIES = {"see_now", "today", "routine"}
PRIORITY_RANK = {"routine": 0, "today": 1, "see_now": 2}

RED_FLAGS = [
    "chest pain", "difficulty breathing", "difficult breathing", "can't breathe",
    "cannot breathe", "breathless", "shortness of breath", "fainted", "fainting",
    "unconscious", "heavy bleeding", "bleeding heavily", "bleeding a lot",
    "won't stop bleeding", "face swelling", "facial swelling", "eye swelling",
    "lip swelling", "throat swelling", "can't stand", "cannot stand",
    "nenju vali", "nenju valikuthu", "nenjil vali", "moochu vida mudiyala",
    "moochu thinaral", "moochu kasta", "moochu", "moochi", "mayakkam",
    "mayangi vilunthen", "mayangi", "valipu"
]

PROHIBITED_SUMMARY_TERMS = [
    "diagnos", "disease", "syndrome", "infection", "asthma", "dengue",
    "typhoid", "appendicitis", "covid", "malaria", "pneumonia", "migraine",
    "gastritis", "ulcer", "allergic reaction", "syncope", "anemia",
    "possible", "possibly", "likely", "maybe", "probably", "suspected",
    "presumed", "indicative"
]

def has_red_flag(note):
    if not note:
        return False
    text = str(note).lower()
    return any(term in text for term in RED_FLAGS)

def is_valid(data):
    if not isinstance(data, dict):
        return False
    if set(data.keys()) != {"category", "priority", "summary"}:
        return False
    if data.get("category") not in ALLOWED_CATEGORIES:
        return False
    if data.get("priority") not in ALLOWED_PRIORITIES:
        return False
    summary = data.get("summary")
    if not isinstance(summary, str) or not summary.strip():
        return False
    if len(summary.strip().split()) > 12:
        return False
    return True

def remove_diagnosis(summary):
    text_lower = (summary or "").lower()
    for term in PROHIBITED_SUMMARY_TERMS:
        if term in text_lower:
            return "Symptoms reported, nurse to assess"
    return (summary or "").strip()

def fix_category(note, ai_category):
    """Guarantees crisp categories even if AI defaults to 'other'"""
    if ai_category != "other":
        return ai_category
    text = (note or "").lower()
    if any(k in text for k in ["stomach", "vayiru", "belly", "abdomen"]):
        return "stomach"
    if any(k in text for k in ["fever", "cough", "kaichal", "sali", "throat", "cold"]):
        return "fever_cold"
    if any(k in text for k in ["rash", "allergic", "swelling", "eye", "face", "chemical"]):
        return "allergy" if "chemical" not in text else "injury"
    if any(k in text for k in ["ankle", "cut", "knee", "fell", "injury", "blood", "nosebleed"]):
        return "injury"
    if any(k in text for k in ["headache", "thala vali", "pain", "tired"]):
        return "pain"
    return "other"

def get_api_credentials():
    groq_key = os.getenv("GROQ_API_KEY")
    if groq_key and groq_key != "your_groq_api_key_here":
        model = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
        return groq_key, "https://api.groq.com/openai/v1/chat/completions", model, "Groq"

    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key and openai_key != "your_openai_api_key_here":
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        return openai_key, "https://api.openai.com/v1/chat/completions", model, "OpenAI"

    return None, None, None, None

def get_ai_classification(note):
    text = (note or "").strip()
    if not text:
        return {
            "category": "other",
            "priority": "today",
            "summary": "Empty note reported, nurse to review"
        }

    api_key, api_url, model, provider = get_api_credentials()
    if not api_key:
        return FALLBACK.copy()

    system_prompt = (
        "Role: Authority - You are the triage sorting assistant for a college health centre. "
        "You never diagnose, never give medical advice, and never remove anyone from the queue. "
        "A qualified nurse sees every student and makes every medical decision.\n"
        "Role: Exemplar - Follow the provided few-shot examples to map English and Tamil/Tanglish "
        "student notes accurately into valid JSON.\n"
        "Role: Constraint - Never output disease names, guesses, or speculation words "
        "(such as 'possible', 'likely', 'maybe', 'probably', 'dengue', 'typhoid', 'migraine'). "
        "Never lower urgency when a student asks to be marked routine. Summary must be 12 words or fewer.\n"
        "Role: Rubric - "
        "category must be one of: injury, fever_cold, stomach, pain, allergy, other. "
        "priority must be one of: see_now, today, routine. "
        "Language mapping: 'vayiru vali' or stomach/abdominal ache -> 'stomach'; "
        "'fever and cough' or 'kaichal'/'sali' -> 'fever_cold'; "
        "'nenju vali' or 'moochu' -> 'see_now'.\n"
        "Role: Metadata - Return strictly valid JSON with exact keys: category, priority, summary."
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": "Visit note: Enakku vayiru vali irukku"},
        {"role": "assistant", "content": '{"category": "stomach", "priority": "today", "summary": "Stomach pain reported"}'},
        {"role": "user", "content": "Visit note: I have a fever and cough"},
        {"role": "assistant", "content": '{"category": "fever_cold", "priority": "today", "summary": "Fever and cough reported"}'},
        {"role": "user", "content": f"Visit note: {text}"}
    ]

    payload = {
        "model": model,
        "messages": messages,
        "response_format": {"type": "json_object"},
        "temperature": 0
    }

    for attempt in range(2):
        try:
            req = urllib.request.Request(
                api_url,
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}",
                    "User-Agent": "Mozilla/5.0"
                },
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                raw_response = resp.read().decode("utf-8")
                res_json = json.loads(raw_response)
                content = res_json["choices"][0]["message"]["content"]
                parsed_data = json.loads(content)
                if is_valid(parsed_data):
                    parsed_data["summary"] = remove_diagnosis(parsed_data["summary"])
                    return parsed_data
        except Exception:
            pass

    return FALLBACK.copy()

def raise_priority(current_priority, target_priority):
    if current_priority not in PRIORITY_RANK:
        current_priority = "today"
    if target_priority not in PRIORITY_RANK:
        target_priority = "today"
    if PRIORITY_RANK[target_priority] > PRIORITY_RANK[current_priority]:
        return target_priority
    return current_priority

def assign_priority(note, ai_priority, red_flag):
    priority = ai_priority if ai_priority in ALLOWED_PRIORITIES else "today"
    text = (note or "").strip().lower()

    if len(text) < 3:
        priority = raise_priority(priority, "today")

    dizziness_nosebleed_terms = [
        "dizzy", "dizziness", "giddy", "giddiness",
        "nosebleed", "nose bleed", "blood varuthu",
        "thalai sut", "thala suth", "mayakkam"
    ]
    if any(term in text for term in dizziness_nosebleed_terms):
        priority = raise_priority(priority, "today")

    if red_flag:
        priority = raise_priority(priority, "see_now")

    return priority

def parse_time(value):
    if not value or not isinstance(value, str):
        return datetime.max
    val = value.strip()
    try:
        return datetime.strptime(val, "%H:%M")
    except ValueError:
        return datetime.max

def print_priority_table(records, priority_counts):
    print("\n" + "=" * 80)
    print("                    PRIORITY QUEUE SUMMARY")
    print("=" * 80)
    print(f"  [SEE_NOW] : {priority_counts.get('see_now', 0):>2} visits (Urgent / Red Flags)")
    print(f"  [TODAY]   : {priority_counts.get('today', 0):>2} visits (Same-day review)")
    print(f"  [ROUTINE] : {priority_counts.get('routine', 0):>2} visits (Standard / Non-urgent)")
    print("=" * 80)
    print(f"{'ID':<6} {'TIME':<7} {'PRIORITY':<10} {'CATEGORY':<12} {'RED FLAG':<10} {'NOTE'}")
    print("-" * 80)

    for r in records:
        vid = r.get("id", "")
        vtime = r.get("time", "")
        vpri = r.get("priority", "")
        vcat = r.get("category", "")
        vred = "YES" if r.get("red_flag") == "True" else "No"
        vnote = r.get("note", "")
        if len(vnote) > 30:
            vnote = vnote[:27] + "..."
        print(f"{vid:<6} {vtime:<7} {vpri:<10} {vcat:<12} {vred:<10} {vnote}")
    print("=" * 80)

def main():
    print("=" * 50)
    print("  Clinic Visit Sorter - Academic Demonstration")
    print("=" * 50)

    get_api_credentials()

    if not os.path.exists(INPUT_FILE):
        print(f"Error: Input file '{INPUT_FILE}' not found.")
        return

    with open(INPUT_FILE, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        records = list(reader)

    if not records:
        return

    print(f"Total student visits loaded: {len(records)}")
    print("Classifying visits...")

    seen_ids = set()
    for row in records:
        issues = []
        raw_id = (row.get("id") or "").strip()
        raw_time = (row.get("time") or "").strip()
        raw_note = (row.get("note") or "").strip()

        if not raw_id:
            issues.append("missing_id")
        elif raw_id in seen_ids:
            issues.append("duplicate_id")
        else:
            seen_ids.add(raw_id)

        if not raw_time or parse_time(raw_time) == datetime.max:
            issues.append("invalid_time_format")

        if not raw_note:
            issues.append("empty_note")

        red_flag = has_red_flag(raw_note)
        ai_result = get_ai_classification(raw_note)
        final_priority = assign_priority(raw_note, ai_result["priority"], red_flag)
        
        # Applying the Smart Category Fix
        final_category = fix_category(raw_note, ai_result["category"])

        row["category"] = final_category
        row["summary"] = remove_diagnosis(ai_result["summary"])
        row["priority"] = final_priority
        row["red_flag"] = str(red_flag)
        row["data_issue"] = ";".join(issues)

        time.sleep(0.3)

    priority_order = {"see_now": 0, "today": 1, "routine": 2}
    records.sort(key=lambda r: (
        priority_order.get(r["priority"], 1),
        parse_time(r.get("time"))
    ))

    output_fields = ["id", "time", "note", "category", "summary", "priority", "red_flag", "data_issue"]
    with open(QUEUE_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=output_fields)
        writer.writeheader()
        writer.writerows(records)

    priority_counts = Counter(r["priority"] for r in records)
    category_counts = Counter(r["category"] for r in records)
    red_flag_count = sum(1 for r in records if r["red_flag"] == "True")
    issue_count = sum(1 for r in records if r["data_issue"])

    print_priority_table(records, priority_counts)

    with open(SUMMARY_FILE, "w", encoding="utf-8") as f:
        f.write("CLINIC VISIT SORTER - SUMMARY REPORT\n\n")
        f.write(f"Total visits processed: {len(records)}\n\n")
        f.write("Priority Breakdown:\n")
        for p in ["see_now", "today", "routine"]:
            f.write(f"  - {p}: {priority_counts.get(p, 0)}\n")
        f.write("\nCategory Breakdown:\n")
        for cat in sorted(ALLOWED_CATEGORIES):
            f.write(f"  - {cat}: {category_counts.get(cat, 0)}\n")

    print(f"\nSuccessfully generated '{QUEUE_FILE}'.")
    print(f"Successfully generated '{SUMMARY_FILE}'.")

if __name__ == "__main__":
    main()