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
import re
import time
from typing import Dict, List

import db
import profile_options as opts
from profile_validation import validate_tier1, validate_tier2

# "general_interests" (not "interests") to keep this distinct from the feed-category interests
# in interests.py/api.interests - different concept, different consumer.
#
# The fields a client may set. location_region / location_country are derived server-side from
# the validated location (never taken from the client), and field_of_study_other holds the
# free-text name when field_of_study is "Other" (see other_field_of_study_report).
TIER1_FIELDS = {"field_of_study", "field_of_study_other", "education_level", "general_interests", "location"}
_TIER1_DERIVED = {"location_region", "location_country"}

# Writable Tier 2 fields. Replaced by newer fields and no longer writable (existing stored values
# stay readable but the app ignores them): age -> birth_date; mental_disabilities,
# physical_disabilities and chronic_illnesses -> the single combined "disability" field.
TIER2_FIELDS = {"birth_date", "gender", "sex", "disability", "location_precise"}
_TIER2_RETIRED = {"age", "mental_disabilities", "physical_disabilities", "chronic_illnesses"}


class ProfileValidationError(ValueError):
    """Raised with per-field messages ({field: message}) when submitted values fail validation."""

    def __init__(self, errors: Dict[str, str]):
        super().__init__("; ".join(errors.values()))
        self.errors = errors


def get_tier1(user_id: str) -> Dict:
    """This user's cache-safe profile fields, or {} if they haven't set any."""
    entry = db.get_db().profile_tier1.find_one({"_id": user_id})
    return entry["fields"] if entry else {}


def set_tier1(user_id: str, fields: Dict) -> Dict:
    """Merge the given Tier 1 fields into this user's record. Raises ValueError on an unknown field."""
    fields = {k: v for k, v in fields.items() if k not in _TIER1_DERIVED}
    unknown = set(fields) - TIER1_FIELDS
    if unknown:
        raise ValueError(f"Unknown Tier 1 field(s): {', '.join(sorted(unknown))}")

    cleaned, errors = validate_tier1(fields)
    if errors:
        raise ProfileValidationError(errors)

    updates = {f"fields.{key}": value for key, value in cleaned.items()}
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
    # .get with defaults: a document saved with fields but no consent flags (the user never
    # ticked a consent box) has no "consent" key at all.
    result = entry or {}
    fields = result.get("fields", {})
    if fields:
        _log_tier2_access(user_id, "read", fields.keys())
    return {"fields": fields, "consent": result.get("consent", {})}


def set_tier2(user_id: str, fields: Dict, consent: Dict) -> Dict:
    """Merge Tier 2 fields and their consent flags into this user's record, and audit-log the
    write. Raises ValueError on an unknown field."""
    unknown = set(fields) - TIER2_FIELDS
    if unknown:
        raise ValueError(f"Unknown Tier 2 field(s): {', '.join(sorted(unknown))}")

    cleaned, errors = validate_tier2(fields)
    if errors:
        raise ProfileValidationError(errors)
    fields = {**{k: v for k, v in fields.items() if k not in cleaned}, **cleaned}

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


def _normalize_other(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip().lower()


def other_field_of_study_report(threshold_pct: float = 5.0, min_users: int = 10) -> Dict:
    """How many users picked "Other" for field of study, and which "other" names are common
    enough to consider adding as a new paper category.

    Percentages are of users who set a field of study at all (not of every account, most of
    whom skip the optional profile). A name becomes a suggestion once at least `min_users`
    users gave it AND it's at least `threshold_pct` percent of users with a field of study -
    the minimum keeps a tiny early userbase from "suggesting" a category on one or two answers.
    Names are grouped case- and whitespace-insensitively only; near-synonyms ("Linguistics" vs
    "Language studies") are counted separately for now and can be merged by hand when reviewing."""
    entries = list(db.get_db().profile_tier1.find({"fields.field_of_study": {"$nin": [None, ""]}}))
    total = len(entries)

    by_field: Dict[str, int] = {}
    other_groups: Dict[str, int] = {}
    for entry in entries:
        fields = entry.get("fields", {})
        field = fields.get("field_of_study")
        by_field[field] = by_field.get(field, 0) + 1
        if field == opts.OTHER:
            name = _normalize_other(fields.get("field_of_study_other", ""))
            if name:
                other_groups[name] = other_groups.get(name, 0) + 1

    def pct(count: int) -> float:
        return round(100.0 * count / total, 1) if total else 0.0

    groups: List[Dict] = [
        {"name": name.title(), "count": count, "percent": pct(count)}
        for name, count in sorted(other_groups.items(), key=lambda kv: -kv[1])
    ]
    suggestions = [g["name"] for g in groups if g["count"] >= min_users and g["percent"] >= threshold_pct]
    return {
        "users_with_field_of_study": total,
        "by_field": by_field,
        "other_count": by_field.get(opts.OTHER, 0),
        "other_percent": pct(by_field.get(opts.OTHER, 0)),
        "other_groups": groups,
        "threshold_percent": threshold_pct,
        "min_users": min_users,
        "suggested_new_categories": suggestions,
    }
