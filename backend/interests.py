"""
Interest storage, scoped by authenticated user id (see auth.py) - mirrors bookmarks.py's pattern.
Backed by MongoDB's `interests` collection (one document per user, keyed by user_id). A user's
chosen topic interests follow their account, not any one device, and are used by api_server.py to
hard-filter the discovery feed.
"""
from typing import Dict, List

import db


def get_interests(user_id: str) -> List[str]:
    """Return this user's chosen interests, or [] if they haven't set any."""
    entry = db.get_db().interests.find_one({"_id": user_id})
    return entry["interests"] if entry else []


def set_interests(user_id: str, interests: List[str]) -> None:
    """Replace this user's interests wholesale (the client always sends the full set)."""
    deduped = list(dict.fromkeys(interests))  # de-dupe, preserve order
    db.get_db().interests.update_one(
        {"_id": user_id},
        {"$set": {"interests": deduped}},
        upsert=True,
    )
