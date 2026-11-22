"""
Red Flag Detection Module
------------------------
Demonstration safety module that identifies high-risk warning phrases in
both English and Tamil / Tanglish.

Safety Rule:
If any red flag phrase is detected, red_flag is set to True,
and priority MUST be set to 'see_now'. The AI is never allowed to lower this.
"""

# Red-flag keywords and phrases (English & Tamil/Tanglish)
RED_FLAGS = [
    # English terms
    "chest pain",
    "difficulty breathing",
    "difficult breathing",
    "can't breathe",
    "cannot breathe",
    "breathless",
    "shortness of breath",
    "fainted",
    "fainting",
    "unconscious",
    "heavy bleeding",
    "bleeding heavily",
    "bleeding a lot",
    "won't stop bleeding",
    "face swelling",
    "facial swelling",
    "eye swelling",
    "lip swelling",
    "throat swelling",
    "can't stand",
    "cannot stand",

    # Tamil / Tanglish warning terms
    "nenju vali",
    "nenju valikuthu",
    "nenjil vali",
    "moochu vida mudiyala",
    "moochu thinaral",
    "moochu kasta",
    "moochu",
    "moochi",
    "mayakkam",
    "mayangi vilunthen",
    "mayangi",
    "valipu"
]


def has_red_flag(note: str) -> bool:
    """
    Checks if a student visit note contains any emergency red-flag term.
    Case-insensitive matching across English and Tamil/Tanglish.

    Returns:
        bool: True if emergency phrase detected, False otherwise.
    """
    if not note:
        return False
    text = str(note).lower()
    return any(term in text for term in RED_FLAGS)


def get_detected_red_flags(note: str) -> list:
    """
    Returns list of matched red flag terms in the note (useful for UI badges).
    """
    if not note:
        return []
    text = str(note).lower()
    return [term for term in RED_FLAGS if term in text]
