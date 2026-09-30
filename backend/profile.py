"""
Profile data model, per the technical spec's "Profile Data Model" section: a two-tier split,
scoped by authenticated user id, backed by MongoDB's `profile_tier1`/`profile_tier2`/
`profile_tier2_audit` collections (one document per user, keyed by user_id; the audit collection
appends one document per read/write instead).

Tier 1 (cache-safe): coarse fields safe to use as a cache key for future shared "Simplest"
generation caching (not built yet - this just stores the fields that would drive it).

Tier 2 (sensitive-context): age, gender, sex, precise location, disabilities, chronic illnesses.
Deliberately kept in a separate collection from Tier 1 (never merged into one document) and never
used as a cache key. Every read or write of Tier 2 data is appended to a separate audit log, and
each Tier 2 field carries its own two consent flags (used_for_personalization,
used_for_feed_relevance) rather than one blanket "sensitive data" toggle - a user can allow one
use without the other.

Not implemented here: the age-gating/parental-consent flow the spec calls out as required before
collecting Tier 2 data from minor accounts. That's a distinct, much larger feature (guardian
identity/consent verification) that wasn't asked for in this pass - Tier 2 fields are collectible
by any account for now.
"""
import time
from typing import Dict

import db

# "general_interests" (not "interests") to keep this distinct from the feed-category interests
# in interests.py/api.interests - different concept, different consumer.
TIER1_FIELDS = {"field_of_study", "education_level", "general_interests", "location"}

TIER2_FIELDS = {
    "age", "gender", "sex", "location_precise",
    "mental_disabilities", "physical_disabilities", "chronic_illnesses",
}


def get_tier1(user_id: str) -> Dict:
    """This user's cache-safe profile fields, or {} if they haven't set any."""
    entry = db.get_db().profile_tier1.find_one({"_id": user_id})
    return entry["fields"] if entry else {}


def set_tier1(user_id: str, fields: Dict) -> Dict:
    """Merge the given Tier 1 fields into this user's record. Raises ValueError on an unknown field."""
    unknown = set(fields) - TIER1_FIELDS
    if unknown:
        raise ValueError(f"Unknown Tier 1 field(s): {', '.join(sorted(unknown))}")

    updates = {f"fields.{key}": value for key, value in fields.items()}
    collection = db.get_db().profile_tier1
    if updates:
        collection.update_one({"_id": user_id}, {"$set": updates}, upsert=True)
    entry = collection.find_one({"_id": user_id})
    return entry["fields"] if entry else {}


def _log_tier2_access(user_id: str, action: str, field_names) -> None:
    db.get_db().profile_tier2_audit.insert_one({
        "user_id": user_id,
        "action": action,
        "fields": sorted(field_names),
        "timestamp": time.time(),
    })


def get_tier2(user_id: str) -> Dict:
    """This user's sensitive-context fields and per-field consent flags. Logs the read (only
    when there's actually data to read - an empty/never-set profile isn't an access)."""
    entry = db.get_db().profile_tier2.find_one({"_id": user_id})
    result = entry if entry else {"fields": {}, "consent": {}}
    if result.get("fields"):
        _log_tier2_access(user_id, "read", result["fields"].keys())
    return {"fields": result["fields"], "consent": result["consent"]}


def set_tier2(user_id: str, fields: Dict, consent: Dict) -> Dict:
    """Merge Tier 2 fields and their consent flags into this user's record, and audit-log the
    write. Raises ValueError on an unknown field."""
    unknown = set(fields) - TIER2_FIELDS
    if unknown:
        raise ValueError(f"Unknown Tier 2 field(s): {', '.join(sorted(unknown))}")

    updates = {f"fields.{key}": value for key, value in fields.items()}
    for field_name, flags in (consent or {}).items():
        updates[f"consent.{field_name}"] = {
            "used_for_personalization": bool((flags or {}).get("used_for_personalization", False)),
            "used_for_feed_relevance": bool((flags or {}).get("used_for_feed_relevance", False)),
        }

    collection = db.get_db().profile_tier2
    if updates:
        collection.update_one({"_id": user_id}, {"$set": updates}, upsert=True)
    entry = collection.find_one({"_id": user_id}) or {}
    if fields:
        _log_tier2_access(user_id, "write", fields.keys())
    return {"fields": entry.get("fields", {}), "consent": entry.get("consent", {})}
