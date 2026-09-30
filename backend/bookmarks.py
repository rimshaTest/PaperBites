"""
Bookmark storage, scoped by authenticated user id (see auth.py). Backed by MongoDB's `bookmarks`
collection - one document per (user_id, video_id) pair - so bookmarks follow the account across
devices and survive concurrent writers, instead of the flat JSON file this used to be.

"video_id" is a legacy field name from before this app was paper-only; api_server.py's bookmark
routes and the frontend both still use it to mean "paper id", so it's kept as-is here rather than
renamed mid-migration.
"""
import time
from typing import Dict, List

import db


def list_bookmarks(user_id: str) -> List[Dict]:
    """Return this user's bookmark entries, most recently saved first."""
    cursor = db.get_db().bookmarks.find({"user_id": user_id}).sort("saved_at", -1)
    return [{"video_id": e["video_id"], "saved_at": e["saved_at"]} for e in cursor]


def is_bookmarked(user_id: str, video_id: str) -> bool:
    return db.get_db().bookmarks.find_one({"user_id": user_id, "video_id": video_id}) is not None


def add_bookmark(user_id: str, video_id: str) -> None:
    db.get_db().bookmarks.update_one(
        {"user_id": user_id, "video_id": video_id},
        {"$setOnInsert": {"saved_at": time.time()}},
        upsert=True,
    )


def remove_bookmark(user_id: str, video_id: str) -> None:
    db.get_db().bookmarks.delete_one({"user_id": user_id, "video_id": video_id})
