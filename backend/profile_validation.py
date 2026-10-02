"""
Server-side validation for the Profile Details form. This is the authoritative check - the app
runs the same kinds of checks for instant feedback, but anything a client sends is re-validated
here, since a client can always be bypassed.

Free-text fields are protected primarily by a character whitelist (letters, digits, spaces and
commas for interests; letters and a few name punctuation marks for locations), which already
rules out quotes, semicolons, comment markers and every other character an injection needs.
Storage goes through the MongoDB driver as parameterized documents (this is not a SQL database),
so the extra SQL-keyword pattern below is defense in depth, not the real protection. Free text
is additionally screened for gibberish and profanity, which are quality checks, not security
ones - the heuristics are deliberately conservative so real terms (acronyms like "CRISPR",
"fMRI", "DNA") are accepted.

All validators return (cleaned_value, error_message); error_message is None when valid.
"""
import datetime
import re
from typing import Any, Dict, List, Optional, Tuple

import places
import profile_options as opts
from categories import current_categories

INTERESTS_MAX_ITEMS = 10
INTERESTS_MAX_TOTAL_LENGTH = 200
INTEREST_MIN_LENGTH = 2
INTEREST_MAX_LENGTH = 40
OTHER_FIELD_MAX_LENGTH = 60

_VOWELS = set("aeiouy")
_KEYBOARD_MASHES = ("qwer", "asdf", "zxcv", "hjkl", "uiop", "wasd", "qaz", "wsx")
_SQL_PATTERN = re.compile(
    r"\b(select|insert|update|delete|drop|alter|truncate|exec|execute|union)\b"
    r".*\b(from|into|table|set|where|select|all|database)\b",
    re.IGNORECASE,
)

# Used only if the better-profanity package isn't installed in a deployment - far smaller than
# its list, so the package is the real check (it's in requirements.txt).
_FALLBACK_PROFANITY = {"fuck", "shit", "bitch", "asshole", "bastard", "cunt", "dick", "slut", "whore"}


def contains_profanity(text: str) -> bool:
    try:
        from better_profanity import profanity
        return bool(profanity.contains_profanity(text))
    except ImportError:
        words = re.findall(r"[a-z]+", text.lower())
        return any(w in _FALLBACK_PROFANITY for w in words)


def looks_like_gibberish(word: str) -> bool:
    """Conservative per-word check for keyboard mashing and random strings."""
    letters = "".join(c for c in word if c.isalpha())
    if not letters:
        return False  # digits-only tokens (e.g. "5") aren't gibberish
    if len(word) > 30:
        return True
    # Short all-caps tokens are acronyms (DNA, MRI, CRISPR); mixed case like "fMRI" also passes
    # the vowel test below only if it has a vowel, so allow a lowercase-prefixed acronym too.
    is_acronym = len(letters) <= 6 and (letters.isupper() or letters[1:].isupper())
    lower = letters.lower()
    if not is_acronym and len(lower) >= 3 and not (set(lower) & _VOWELS):
        return True
    if re.search(r"(.)\1{3,}", lower):  # aaaa
        return True
    if re.search(r"(.{2,3})\1{2,}", lower):  # ababab / abcabcabc
        return True
    if not is_acronym and re.search(r"[^aeiouy]{6,}", lower):  # long consonant runs
        return True
    return any(mash in lower for mash in _KEYBOARD_MASHES)


def _check_text_quality(text: str, label: str) -> Optional[str]:
    if _SQL_PATTERN.search(text):
        return f"{label} contains text that isn't allowed."
    if contains_profanity(text):
        return f"Please keep {label.lower()} free of profanity."
    for word in re.findall(r"[^\s,]+", text):
        if looks_like_gibberish(word):
            return f"\"{word}\" doesn't look like a real word."
    return None


def validate_choice(value: Any, options: List[str], label: str) -> Tuple[Optional[str], Optional[str]]:
    if value in (None, ""):
        return "", None
    if not isinstance(value, str) or value not in options:
        return None, f"Choose one of the listed options for {label.lower()}."
    return value, None


def validate_field_of_study(value: Any, other: Any) -> Tuple[Dict[str, str], Dict[str, str]]:
    """Returns ({field_of_study, field_of_study_other}, errors). "Other" requires the free-text
    name; picking anything else clears a stale "other" text."""
    errors: Dict[str, str] = {}
    if value in (None, ""):
        return {"field_of_study": "", "field_of_study_other": ""}, errors

    allowed = current_categories() + [opts.OTHER]
    if not isinstance(value, str) or value not in allowed:
        return {}, {"field_of_study": "Choose a field of study from the list."}

    if value != opts.OTHER:
        return {"field_of_study": value, "field_of_study_other": ""}, errors

    text = (other or "").strip() if isinstance(other, str) else ""
    text = re.sub(r"\s+", " ", text)
    if not text:
        return {}, {"field_of_study_other": "Tell us your field of study."}
    if not (INTEREST_MIN_LENGTH <= len(text) <= OTHER_FIELD_MAX_LENGTH):
        return {}, {"field_of_study_other": f"Use {INTEREST_MIN_LENGTH}-{OTHER_FIELD_MAX_LENGTH} characters."}
    if not all(c.isalpha() or c == " " for c in text):
        return {}, {"field_of_study_other": "Use letters and spaces only."}
    problem = _check_text_quality(text, "Field of study")
    if problem:
        return {}, {"field_of_study_other": problem}
    return {"field_of_study": opts.OTHER, "field_of_study_other": text}, errors


def validate_interests(value: Any) -> Tuple[Optional[str], Optional[str]]:
    """Comma-separated interests: letters, digits, spaces and commas only."""
    if value in (None, ""):
        return "", None
    if not isinstance(value, str):
        return None, "Interests must be text."
    text = value.strip()
    if len(text) > INTERESTS_MAX_TOTAL_LENGTH:
        return None, f"Keep interests under {INTERESTS_MAX_TOTAL_LENGTH} characters."
    if not all(c.isalnum() or c in " ," for c in text):
        return None, "Use letters, numbers, spaces and commas only."

    seen, items = set(), []
    for raw_item in text.split(","):
        item = re.sub(r"\s+", " ", raw_item).strip()
        if not item or item.lower() in seen:
            continue
        if not (INTEREST_MIN_LENGTH <= len(item) <= INTEREST_MAX_LENGTH):
            return None, f"Each interest should be {INTEREST_MIN_LENGTH}-{INTEREST_MAX_LENGTH} characters."
        seen.add(item.lower())
        items.append(item)

    if len(items) > INTERESTS_MAX_ITEMS:
        return None, f"List at most {INTERESTS_MAX_ITEMS} interests."
    cleaned = ", ".join(items)
    if cleaned:
        problem = _check_text_quality(cleaned, "Interests")
        if problem:
            return None, problem
    return cleaned, None


def validate_location(value: Any) -> Tuple[Optional[Dict[str, Optional[str]]], Optional[str]]:
    """The location must be a real place from the autocomplete index. Returns the resolved
    parts ({label, city, region, country}) so callers store what the server knows, not what
    the client claims."""
    if value in (None, ""):
        return {"label": "", "city": None, "region": None, "country": None}, None
    if not isinstance(value, str) or not places.is_alphabetic_label(value):
        return None, "Use letters only for your location."
    try:
        place = places.resolve(value)
    except places.PlacesUnavailable as e:
        # Missing optional place data shouldn't block saving a profile: accept the (already
        # letters-only) text as typed and log it, rather than failing the whole save.
        print(f"Place data unavailable, accepting location unverified: {e}")
        return {"label": value.strip(), "city": None, "region": None, "country": None}, None
    if not place:
        return None, "Pick a place from the suggestions."
    return place, None


def validate_birth_date(value: Any) -> Tuple[Optional[str], Optional[str]]:
    if value in (None, ""):
        return "", None
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return None, "Choose a valid birth date."
    try:
        parsed = datetime.date.fromisoformat(value)
    except ValueError:
        return None, "That date doesn't exist."
    if parsed.year < opts.MIN_BIRTH_YEAR:
        return None, f"Birth year must be {opts.MIN_BIRTH_YEAR} or later."
    if parsed > datetime.date.today():
        return None, "Birth date can't be in the future."
    return value, None


def validate_disability(value: Any) -> Tuple[Optional[Dict], Optional[str]]:
    """{conditions: [...], other: "..."}: a subset of the checklist (which includes "None" and
    "Other"). "None" can't be combined with anything else; "Other" requires a description."""
    empty = {"conditions": [], "other": ""}
    if value in (None, "", {}):
        return empty, None
    if not isinstance(value, dict):
        return None, "Choose from the list."
    conditions = value.get("conditions") or []
    other = value.get("other") or ""
    if not isinstance(conditions, list) or not all(isinstance(c, str) for c in conditions):
        return None, "Choose from the list."
    if any(c not in opts.DISABILITY_OPTIONS for c in conditions):
        return None, "Choose from the list."

    chosen = set(conditions)
    if opts.DISABILITY_NONE in chosen and len(chosen) > 1:
        return None, '"None" can\'t be combined with other choices.'

    cleaned_other = ""
    if opts.DISABILITY_OTHER in chosen:
        cleaned_other = re.sub(r"\s+", " ", other).strip() if isinstance(other, str) else ""
        if not cleaned_other:
            return None, "Describe your disability or condition."
        if not (INTEREST_MIN_LENGTH <= len(cleaned_other) <= OTHER_FIELD_MAX_LENGTH):
            return None, f"Use {INTEREST_MIN_LENGTH}-{OTHER_FIELD_MAX_LENGTH} characters."
        if not all(c.isalpha() or c in " -'" for c in cleaned_other):
            return None, "Use letters, spaces, hyphens and apostrophes only."
        problem = _check_text_quality(cleaned_other, "This answer")
        if problem:
            return None, problem

    ordered = [o for o in opts.DISABILITY_OPTIONS if o in chosen]  # canonical order, deduped
    return {"conditions": ordered, "other": cleaned_other}, None


def validate_tier1(fields: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, str]]:
    """Validate and normalize the Tier 1 fields present in `fields`. Returns (cleaned, errors);
    cleaned also carries the server-derived location_country / location_region."""
    cleaned: Dict[str, Any] = {}
    errors: Dict[str, str] = {}

    if "field_of_study" in fields or "field_of_study_other" in fields:
        result, errs = validate_field_of_study(fields.get("field_of_study"), fields.get("field_of_study_other"))
        cleaned.update(result)
        errors.update(errs)

    if "education_level" in fields:
        value, err = validate_choice(fields["education_level"], opts.EDUCATION_LEVELS, "Education level")
        if err:
            errors["education_level"] = err
        else:
            cleaned["education_level"] = value

    if "general_interests" in fields:
        value, err = validate_interests(fields["general_interests"])
        if err:
            errors["general_interests"] = err
        else:
            cleaned["general_interests"] = value

    if "location" in fields:
        place, err = validate_location(fields["location"])
        if err:
            errors["location"] = err
        else:
            cleaned["location"] = place["label"]
            cleaned["location_region"] = place["region"] or ""
            cleaned["location_country"] = place["country"] or ""

    return cleaned, errors


def validate_tier2(fields: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, str]]:
    cleaned: Dict[str, Any] = {}
    errors: Dict[str, str] = {}

    checks = {
        "birth_date": validate_birth_date,
        "gender": lambda v: validate_choice(v, opts.GENDERS, "Gender"),
        "sex": lambda v: validate_choice(v, opts.SEXES, "Sex"),
        "disability": validate_disability,
    }
    for key, check in checks.items():
        if key in fields:
            value, err = check(fields[key])
            if err:
                errors[key] = err
            else:
                cleaned[key] = value
    return cleaned, errors
