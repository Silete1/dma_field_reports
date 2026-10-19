"""Text normalisation and fuzzy matching for English and Arabic values.

Pure Python, no Odoo import, so it can be unit-tested on its own.
"""
import difflib
import re
import unicodedata

_ARABIC_DIACRITICS = re.compile("[ؐ-ًؚ-ٰٟۖ-ۭـ]")
_ARABIC_MAP = str.maketrans({
    "آ": "ا",  # alef madda -> alef
    "أ": "ا",  # alef hamza above -> alef
    "إ": "ا",  # alef hamza below -> alef
    "ٱ": "ا",  # alef wasla -> alef
    "ى": "ي",  # alef maqsura -> ya
    "ی": "ي",  # farsi ya -> ya
    "ة": "ه",  # ta marbuta -> ha
    "ک": "ك",  # keheh -> kaf
    "٠": "0", "١": "1", "٢": "2", "٣": "3", "٤": "4",
    "٥": "5", "٦": "6", "٧": "7", "٨": "8", "٩": "9",
})
_LIST_SPLIT = re.compile(r"\s*[,;،\n]\s*")


def clean(value):
    """Trim and collapse white space; None and blank become ''."""
    if value is None:
        return ""
    if not isinstance(value, str):
        value = str(value)
    value = value.replace(" ", " ").replace("‏", "").replace("‎", "")
    return " ".join(value.split())


def norm(value):
    """Matching key: case-folded, accents and Arabic variants unified, only letters and digits kept.

    'Al-Kasarah', 'alkasarah ' and 'AL KASARAH' share one key, and so do the
    spelling variants of the same Arabic word.
    """
    value = clean(value)
    if not value:
        return ""
    value = _ARABIC_DIACRITICS.sub("", value).translate(_ARABIC_MAP)
    value = unicodedata.normalize("NFKD", value)
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    return "".join(ch for ch in value.casefold() if ch.isalnum())


def split_multi(value):
    """Split a multi-select cell ('IED,ERW', 'IED ، ERW') into its clean parts, keeping order."""
    out = []
    for part in _LIST_SPLIT.split(clean(value)):
        part = clean(part)
        if part and part not in out:
            out.append(part)
    return out


def similarity(a, b):
    """0..1 similarity of two values, on their matching keys."""
    na, nb = norm(a), norm(b)
    if not na or not nb:
        return 0.0
    if na == nb:
        return 1.0
    ratio = difflib.SequenceMatcher(None, na, nb).ratio()
    # one key inside the other ('wra' in 'pmwra') counts as a strong hint
    if len(na) >= 3 and len(nb) >= 3 and (na in nb or nb in na):
        ratio = max(ratio, 0.75)
    return ratio


def best_matches(value, candidates, limit=3, cutoff=0.6):
    """Rank candidates (iterable of (key, label)) by similarity to value.

    Returns [(score, key, label)], best first, at most `limit`, above `cutoff`.
    """
    scored = []
    for key, label in candidates:
        score = similarity(value, label)
        if score >= cutoff:
            scored.append((score, key, label))
    scored.sort(key=lambda t: (-t[0], str(t[2])))
    return scored[:limit]
