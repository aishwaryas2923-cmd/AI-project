"""
AI Classification Module
------------------------
Integrates OpenAI / Groq API to classify clinic visit notes into:
- category: injury, fever_cold, stomach, pain, allergy, other
- priority: see_now, today, routine
- summary: max 12 words symptom summary (NO diagnosis)

Handles:
- Missing API key detection
- JSON schema validation
- 1-time automatic retry on invalid response or network hiccup
- Strict no-diagnosis enforcement (strips disease names/guesses)
- Fallback classification
"""

import os
import json
import urllib.request
import urllib.error
from typing import Tuple, Dict, Any

ALLOWED_CATEGORIES = {"injury", "fever_cold", "stomach", "pain", "allergy", "other"}
ALLOWED_PRIORITIES = {"see_now", "today", "routine"}

FALLBACK = {
    "category": "other",
    "priority": "today",
    "summary": "Could not classify, nurse to review"
}

# Words prohibited in summary to satisfy strict No-Diagnosis rule
DISEASE_AND_SPECULATION_TERMS = [
    "diagnos", "asthma", "dengue", "typhoid", "appendicitis", "covid", "malaria",
    "pneumonia", "migraine", "possible", "likely", "maybe", "probably", "suspected",
    "presumed", "indicative"
]


def load_env_file():
    """
    Reads key-value pairs from .env in the application root without requiring external packages.
    """
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


load_env_file()


def get_api_credentials() -> Tuple[str, str, str, str]:
    """
    Checks for configured AI providers in environment variables:
    1. GROQ_API_KEY
    2. OPENAI_API_KEY
    Returns (api_key, api_url, model, provider_name).
    """
    groq_key = os.getenv("GROQ_API_KEY")
    if groq_key and groq_key != "your_groq_api_key_here":
        model = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
        return groq_key, "https://api.groq.com/openai/v1/chat/completions", model, "Groq"

    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key and openai_key != "your_openai_api_key_here":
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        return openai_key, "https://api.openai.com/v1/chat/completions", model, "OpenAI"

    return None, None, None, None


def check_api_status() -> Dict[str, Any]:
    """
    Returns the current status of the AI API connection for UI badges and diagnostics.
    """
    api_key, _, model, provider = get_api_credentials()
    if not api_key:
        return {
            "configured": False,
            "provider": None,
            "model": None,
            "message": "API Key is missing. Running in safe rule-based Fallback mode."
        }
    masked = api_key[:6] + "..." + api_key[-4:] if len(api_key) > 10 else "***"
    return {
        "configured": True,
        "provider": provider,
        "model": model,
        "masked_key": masked,
        "message": f"Connected to {provider} ({model})"
    }


def validate_ai_response(data: Any) -> bool:
    """
    Validates the structure and constraints of the returned JSON:
    1. Must be dict
    2. Exactly keys: category, priority, summary
    3. category in ALLOWED_CATEGORIES
    4. priority in ALLOWED_PRIORITIES
    5. summary <= 12 words, non-empty string
    """
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


def sanitize_summary(summary: str, original_note: str) -> str:
    """
    Enforces the No-Diagnosis rule:
    If the summary includes disease names or guessing words, replaces it with
    a neutral symptom-based statement so that the system never offers a medical diagnosis.
    """
    text_lower = summary.lower()
    for word in DISEASE_AND_SPECULATION_TERMS:
        if word in text_lower:
            return "Symptoms reported, nurse to assess"
    return summary.strip()


def classify_note(note: str) -> Dict[str, str]:
    """
    Calls the AI API to classify a visit note.
    - Validates response format.
    - Retries once on invalid format or network timeout.
    - Falls back safely if API is missing or fails twice.
    """
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
        "Role: Authority - You are the primary clinical triage officer for a college health centre.\n"
        "Role: Exemplar - Examine input notes carefully and output valid JSON matching exact schema.\n"
        "Role: Constraint - Do NOT offer medical diagnoses or guesses (e.g. no 'appendicitis', 'dengue', 'migraine', 'possible', 'likely').\n"
        "Role: Rubric - \n"
        "  - category MUST be one of: injury, fever_cold, stomach, pain, allergy, other.\n"
        "  - priority MUST be one of: see_now, today, routine.\n"
        "  - summary MUST be 12 words or fewer describing symptoms only.\n"
        "  - Language Rules: 'vayiru vali' / 'stomach pain' -> category 'stomach'. 'nenju vali' / 'moochu' -> priority 'see_now'. 'thala vali' / 'kaichal' / 'sali' -> 'fever_cold' or 'pain'.\n"
        "Role: Metadata - Output JSON strictly."
    )

    examples = [
        {
            "role": "user",
            "content": "Visit note: Enakku vayiru vali irukku"
        },
        {
            "role": "assistant",
            "content": '{"category": "stomach", "priority": "today", "summary": "Abdominal pain reported"}'
        },
        {
            "role": "user",
            "content": "Visit note: Enakku nenju valikuthu moochu vida mudiyala"
        },
        {
            "role": "assistant",
            "content": '{"category": "pain", "priority": "see_now", "summary": "Chest pain and difficulty breathing"}'
        }
    ]

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(examples)
    messages.append({"role": "user", "content": f"Visit note: {text}"})

    payload = {
        "model": model,
        "messages": messages,
        "response_format": {"type": "json_object"},
        "temperature": 0
    }


    # Up to 2 attempts: 1 initial attempt + 1 retry
    for attempt in range(2):
        try:
            req = urllib.request.Request(
                api_url,
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
                },
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=12) as resp:
                raw_response = resp.read().decode("utf-8")
                res_json = json.loads(raw_response)
                content = res_json["choices"][0]["message"]["content"]
                parsed_data = json.loads(content)

                if validate_ai_response(parsed_data):
                    # Sanitize summary according to no-diagnosis rule
                    parsed_data["summary"] = sanitize_summary(parsed_data["summary"], text)
                    return parsed_data
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError,
                KeyError, IndexError, ValueError, TypeError, json.JSONDecodeError):
            continue

    return FALLBACK.copy()
