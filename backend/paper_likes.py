"""
Like storage, scoped by authenticated user id (see auth.py). Backed by MongoDB's `paper_likes`
collection - one document per (user_id, paper_id) pair, same shape as bookmarks.py.

A "like" is a simple heart-tap signal shown on paper cards, independent of bookmarking (saving a
paper for later) and of a confirmed read (paper_views.py) - a user can like a paper without ever
opening it.
"""
import time
from collections import Counter
from typing import Dict, List

import db


def is_liked(user_id: str, paper_id: str) -> bool:
    return db.get_db().paper_likes.find_one({"user_id": user_id, "paper_id": paper_id}) is not None


def add_like(user_id: str, paper_id: str) -> None:
    db.get_db().paper_likes.update_one(
        {"user_id": user_id, "paper_id": paper_id},
        {"$setOnInsert": {"liked_at": time.time()}},
        upsert=True,
    )


def remove_like(user_id: str, paper_id: str) -> None:
    db.get_db().paper_likes.delete_one({"user_id": user_id, "paper_id": paper_id})


def count_likes(paper_id: str) -> int:
    return len(list(db.get_db().paper_likes.find({"paper_id": paper_id}, {"_id": 1})))


def count_likes_bulk(paper_ids: List[str]) -> Dict[str, int]:
    """{paper_id: like_count} for every id in paper_ids that has at least one like. Filters in
    Python rather than a MongoDB $in query so this works the same against any paper_ids list
    size without relying on an index beyond the implicit one on _id."""
    if not paper_ids:
        return {}
    wanted = set(paper_ids)
    docs = db.get_db().paper_likes.find({}, {"paper_id": 1})
    return dict(Counter(doc["paper_id"] for doc in docs if doc["paper_id"] in wanted))


def list_liked_ids(user_id: str, paper_ids: List[str]) -> List[str]:
    """Which of paper_ids this user has liked - used to tag is_liked on a page of papers without
    a separate round trip per card."""
    if not user_id or not paper_ids:
        return []
    wanted = set(paper_ids)
    docs = db.get_db().paper_likes.find({"user_id": user_id}, {"paper_id": 1})
    return [doc["paper_id"] for doc in docs if doc["paper_id"] in wanted]
