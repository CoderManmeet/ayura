"""
Words that may turn product copy into a medical or unproven claim (ROADMAP-AYURA Z4, L6).

Used as a SOFT warning in the admin area: the owner is shown which words to check, and the text
still saves. Nothing here decides what is legally allowed; that is the owner's professional's
call (ROADMAP L6, L7). The list errs on the side of asking.
"""

import re

CLAIM_WARNING_WORDS = (
    "cure", "cures", "cured", "treat", "treats", "treatment", "heal", "heals", "healing",
    "remedy", "medicine", "medicinal", "therapy", "therapeutic", "prevent", "prevents",
    "clinically", "clinically proven", "proven", "guaranteed", "100%", "permanent", "miracle",
    "chemical-free", "chemical free", "toxin-free", "organic", "natural", "ayurvedic",
    "dermatologist", "doctor", "acne", "eczema", "psoriasis", "dandruff", "hair fall", "hairfall",
    "hair loss", "regrow", "regrowth", "anti-ageing", "anti-aging", "reverses", "wrinkle-free",
    "whitening", "fairness", "infection", "fungal", "disease",
)

_PATTERNS = [(word, re.compile(rf"(?<![a-z0-9]){re.escape(word)}(?![a-z0-9])", re.IGNORECASE))
             for word in CLAIM_WARNING_WORDS]


def claim_warnings(*texts):
    """The listed words found in any of `texts`, each once, in list order."""
    blob = " ".join(text or "" for text in texts)
    return [word for word, pattern in _PATTERNS if pattern.search(blob)]
