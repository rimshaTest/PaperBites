"""
Store of *confirmed* paper reads, scoped by authenticated user id - backed by MongoDB's
`paper_views` collection (one document per user, keyed by user_id, holding a list of read
entries), replacing the flat JSON file this used to be.

A "read" here means the user tapped "View Original Paper", left the app, came back, and answered
"Yes" to the Libby-style "Did you read this paper?" prompt (see api_server.py's
record_paper_view and the frontend's ReadConfirmationGate) - not just clicking the link. That
confirmed-read event is what feeds the Visualize tab's bubble map, per-topic reading stats, the
1st/5th/10th/25th/50th/100th read milestone badges, and the cross-user trending signal below.
"""
import time
from typing import Dict, List, Optional

import db

# Milestone badges shown on Profile once earned (frontend animates a pop-in celebration the
# moment one is newly crossed - see record_view's return value below).
MILESTONES = [1, 5, 10, 25, 50, 100]


def record_view(user_id: str, paper_id: str) -> Dict:
    """Record a confirmed read. Idempotent - confirming the same paper again doesn't duplicate
    the entry or change its original viewed_at. Returns the user's updated total confirmed-read
    count and whether this call actually added a new entry, so the caller can tell whether a
    milestone was *just* crossed (as opposed to re-confirming an already-read paper, which should
    never re-trigger a celebration).
    """
    collection = db.get_db().paper_views
    entry = collection.find_one({"_id": user_id})
    entries = entry["entries"] if entry else []

    is_new = not any(e["paper_id"] == paper_id for e in entries)
    if is_new:
        collection.update_one(
            {"_id": user_id},
            {"$push": {"entries": {"paper_id": paper_id, "viewed_at": time.time()}}},
            upsert=True,
        )
        total_read = len(entries) + 1
    else:
        total_read = len(entries)

    return {"is_new": is_new, "total_read": total_read}


def list_viewed_paper_ids(user_id: str) -> List[str]:
    """This user's confirmed-read paper ids, oldest first."""
    entry = db.get_db().paper_views.find_one({"_id": user_id})
    entries = entry["entries"] if entry else []
    return [e["paper_id"] for e in sorted(entries, key=lambda e: e.get("viewed_at", 0))]


def all_entries() -> List[List[Dict]]:
    """Every user's raw confirmed-read entries - used only for cross-user aggregates (trending),
    never exposed per-user through the API."""
    return [doc["entries"] for doc in db.get_db().paper_views.find({}, {"entries": 1})]


def milestone_reached(total_read: int, is_new: bool) -> Optional[int]:
    """Which milestone (if any) this read just crossed - None if it's not a new read, or the new
    total isn't one of the fixed milestone thresholds."""
    if is_new and total_read in MILESTONES:
        return total_read
    return None
