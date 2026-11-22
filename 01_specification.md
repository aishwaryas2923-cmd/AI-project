# CLINIC VISIT SORTER – ONE-PAGE SPECIFICATION
**Course / Programme:** CIT AI-Native Engineering Programme · Semester 1 · Assessment 5  
**Domain:** Healthcare Administration / Clinic Queue Triage Support  
**Document:** Checkpoint 1 Specification  

---

## 1. System Overview & Problem Statement
At peak morning arrival times at the college health centre, 10 to 15 students frequently report within a 30-minute window and are traditionally seen strictly by arrival time. Consequently, a student presenting with high-acuity symptoms (e.g., acute chest pain, dyspnea, anaphylactic swelling) can be delayed behind students presenting for routine health certificates or mild colds.

**Clinic Visit Sorter** is a decision-support queue organization tool that ingests informal, unstructured student arrival notes (in English and Tamil/Tanglish), uses an LLM to categorize symptoms and propose initial review priorities, applies deterministic safety overrides, and presents a prioritized triage queue (`see_now` → `today` → `routine`) sorted by arrival time within each priority level.

---

## 2. Hard Boundaries: What the System Must NEVER Do
1. **Never Make a Medical Diagnosis:** The system must never guess, infer, or output disease names (e.g., "asthma", "angina", "COVID-19", "food poisoning"). Summaries must reflect reported symptoms only.
2. **Never Provide Medical Advice or Prescribe:** No treatment steps, first-aid advice, or medication suggestions may be generated.
3. **Never Remove Anyone from the Queue:** Every single student record in `visits.csv` must appear in the final queue. No dropping, deleting, or filtering out of records.
4. **Never Lower Priority Below Red-Flag or Safety Floors:** A deterministic red flag forces priority to `see_now`. The LLM or subsequent logic can *never* downgrade a red flag.
5. **Never Assume Machine Autonomy:** This is strictly an administrative queue organizer. A qualified human nurse conducts the physical triage, reviews original student notes, and makes 100% of medical and clinical decisions.

---

## 3. Input & Output Specifications
- **Input File:** `visits.csv` (CSV format with mandatory columns: `id`, `time`, `note`).
- **Output File 1:** `nurse_queue.csv` (Columns: `id,time,note,category,summary,priority,red_flag,data_issue`). Sorted: `see_now` (0) → `today` (1) → `routine` (2), then chronologically by `time`.
- **Output File 2:** `summary.txt` (Administrative metrics only: total visits, priority counts, category counts, hourly arrivals, red-flag count, data issue count. Contains **no** student notes or confidential text).

---

## 4. LLM Schema & Output Constraints
The LLM API must return valid JSON matching this exact structure:
```json
{
  "category": "injury | fever_cold | stomach | pain | allergy | other",
  "priority": "see_now | today | routine",
  "summary": "Reported symptoms only, maximum 12 words"
}
```
- **Category Taxonomy:** Exactly 6 allowed values: `injury`, `fever_cold`, `stomach`, `pain`, `allergy`, `other`.
- **Priority Taxonomy:** Exactly 3 allowed values: `see_now`, `today`, `routine`.
- **Summary Constraints:** Maximum 12 words. Purely observational (e.g., "Chest discomfort reported" instead of "Suspected heart attack").

---

## 5. Deterministic Safety Rules & Red-Flag Catalog
Before or after LLM classification, deterministic Python safety checks are enforced:
1. **Red-Flag Keywords:**
   - **English:** `chest pain`, `difficulty breathing`, `can't breathe`, `cannot breathe`, `breathless`, `shortness of breath`, `fainted`, `fainting`, `unconscious`, `heavy bleeding`, `bleeding a lot`, `won't stop bleeding`, `face swelling`, `lip swelling`, `eye swelling`, `can't stand`, `cannot stand`.
   - **Tamil / Tanglish:** `nenju vali`, `nenju valikuthu`, `nenjil vali`, `moochu vida mudiyala`, `moochu thinaral`, `moochu`, `moochi`, `mayakkam`, `mayangi vilunthen`, `mayangi`.
   - **Action:** If any term matches, `red_flag = True` and `priority = see_now`. Priority cannot be downgraded.
2. **Safety Floors:**
   - Mentions of dizziness or nosebleeds (`dizzy`, `nosebleed`, `blood varuthu`, `thala suth`) receive at least `today`.
   - Empty or very short notes (< 3 characters) default to `today`.
3. **No-Diagnosis Sanitization:**
   - Summaries containing diagnostic speculation (`possible`, `likely`, `suspected`, `diagnosed with`, disease names) are stripped and replaced with neutral, symptom-only phrasing.

---

## 6. Edge Cases & Resilience Strategy
- **API Failure / Rate Limit / Timeout:** Caught via `try...except`. Automatic single retry; if still failing, uses fallback: `{"category": "other", "priority": "today", "summary": "Could not classify, nurse to review"}`. Unknown is **never** routine.
- **Malformed LLM Output:** Schema validation verifies keys and allowed enums. Invalid schema triggers one retry, then fallback.
- **Corrupt / Missing Input Data:** Missing IDs, duplicate IDs, missing times, and unparseable timestamps are recorded in the `data_issue` column without halting program execution.
