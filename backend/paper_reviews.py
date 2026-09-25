"""
Queue of citations/URLs the automated add-paper search (paper/citation.py) couldn't resolve, for
manual admin review - docs/TECHNICAL_SPEC.md's fallback for the add-paper pipeline: "let the user
submit the image/citation for manual admin review if retries don't resolve it."

Stored as its own MongoDB document type (the `paper_reviews` collection, alongside `papers` in
db.py) rather than a flat JSON file like auth/bookmarks/interests/profile - those are
account-scoped runtime stores that predate this app's MongoDB usage, but a paper review is a
review of a paper, so it belongs next to `papers` as a real, queryable collection instead of
another ad hoc JSON file. Early on this is a short queue reviewed by hand (per the spec's own
build note); no admin UI reads this yet, but list_reviews() is here so one (or a human querying
the collection directly) has somewhere to start.
"""
from datetime import datetime, timezone
from typing import Dict, List, Optional

import db


def submit_review(user_id: str, raw_input: str) -> Dict:
    """Queue a citation or URL the automated search couldn't match, for manual admin review."""
    doc = {
        "user_id": user_id,
        "input": raw_input,
        "status": "pending",
        "submitted_at": datetime.now(timezone.utc).timestamp(),
    }
    result = db.get_db().paper_reviews.insert_one(doc)
    doc["id"] = str(result.inserted_id)
    doc.pop("_id", None)
    return doc


def list_reviews(status: Optional[str] = None) -> List[Dict]:
    """All submissions, optionally filtered by status ('pending', 'resolved', 'rejected'), most
    recently submitted first."""
    query = {"status": status} if status else {}
    cursor = db.get_db().paper_reviews.find(query).sort("submitted_at", -1)

    reviews = []
    for entry in cursor:
        entry["id"] = str(entry.pop("_id"))
        reviews.append(entry)
    return reviews
