"""
Profile data model, per the technical spec's "Profile Data Model" section: a two-tier split,
JSON-file backed like auth.py/bookmarks.py/interests.py, scoped by authenticated user id.

Tier 1 (cache-safe): coarse fields safe to use as a cache key for future shared "Simplest"
generation caching (not built yet - this just stores the fields that would drive it).

Tier 2 (sensitive-context): age, gender, sex, precise location, disabilities, chronic illnesses.
Deliberately kept in a separate file from Tier 1 (never merged into one record) and never used
as a cache key. Every read or write of Tier 2 data is appended to a separate audit log, and each
Tier 2 field carries its own two consent flags (used_for_personalization, used_for_feed_relevance)
rather than one blanket "sensitive data" toggle - a user can allow one use without the other.

Not implemented here: the age-gating/parental-consent flow the spec calls out as required before
collecting Tier 2 data from minor accounts. That's a distinct, much larger feature (guardian
identity/consent verification) that wasn't asked for in this pass - Tier 2 fields are collectible
by any account for now.
"""
import os
import json
import time
from typing import Dict, List, Optional

TIER1_FILE = os.environ.get("PAPERBITES_PROFILE_TIER1_FILE", "profile_tier1.json")
TIER2_FILE = os.environ.get("PAPERBITES_PROFILE_TIER2_FILE", "profile_tier2.json")
TIER2_AUDIT_FILE = os.environ.get("PAPERBITES_PROFILE_TIER2_AUDIT_FILE", "profile_tier2_audit.json")

# "general_interests" (not "interests") to keep this distinct from the feed-category interests
# in interests.py/api.interests - different concept, different consumer.
TIER1_FIELDS = {"field_of_study", "education_level", "general_interests", "location"}

TIER2_FIELDS = {
    "age", "gender", "sex", "location_precise",
    "mental_disabilities", "physical_disabilities", "chronic_illnesses",
}


def _load(path: str, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error reading {path}: {e}")
        return default


def _save(path: str, data) -> None:
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)


def get_tier1(user_id: str) -> Dict:
    """This user's cache-safe profile fields, or {} if they haven't set any."""
    return _load(TIER1_FILE, {}).get(user_id, {})


def set_tier1(user_id: str, fields: Dict) -> Dict:
    """Merge the given Tier 1 fields into this user's record. Raises ValueError on an unknown field."""
    unknown = set(fields) - TIER1_FIELDS
    if unknown:
        raise ValueError(f"Unknown Tier 1 field(s): {', '.join(sorted(unknown))}")

    data = _load(TIER1_FILE, {})
    data.setdefault(user_id, {}).update(fields)
    _save(TIER1_FILE, data)
    return data[user_id]


def _log_tier2_access(user_id: str, action: str, field_names) -> None:
    log = _load(TIER2_AUDIT_FILE, [])
    if not isinstance(log, list):
        log = []
    log.append({
        "user_id": user_id,
        "action": action,
        "fields": sorted(field_names),
        "timestamp": time.time(),
    })
    _save(TIER2_AUDIT_FILE, log)


def get_tier2(user_id: str) -> Dict:
    """This user's sensitive-context fields and per-field consent flags. Logs the read (only
    when there's actually data to read - an empty/never-set profile isn't an access)."""
    entry = _load(TIER2_FILE, {}).get(user_id, {"fields": {}, "consent": {}})
    if entry.get("fields"):
        _log_tier2_access(user_id, "read", entry["fields"].keys())
    return entry


def set_tier2(user_id: str, fields: Dict, consent: Dict) -> Dict:
    """Merge Tier 2 fields and their consent flags into this user's record, and audit-log the
    write. Raises ValueError on an unknown field."""
    unknown = set(fields) - TIER2_FIELDS
    if unknown:
        raise ValueError(f"Unknown Tier 2 field(s): {', '.join(sorted(unknown))}")

    data = _load(TIER2_FILE, {})
    entry = data.setdefault(user_id, {"fields": {}, "consent": {}})
    entry["fields"].update(fields)

    for field_name, flags in (consent or {}).items():
        entry["consent"][field_name] = {
            "used_for_personalization": bool((flags or {}).get("used_for_personalization", False)),
            "used_for_feed_relevance": bool((flags or {}).get("used_for_feed_relevance", False)),
        }

    _save(TIER2_FILE, data)
    if fields:
        _log_tier2_access(user_id, "write", fields.keys())
    return entry
