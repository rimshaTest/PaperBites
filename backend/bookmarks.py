"""
Simple JSON-file-backed bookmark storage, scoped by authenticated user id
(see auth.py). Data is keyed by the opaque user id issued at signup, so
bookmarks follow the account rather than any one device.
"""
import os
import json
import time
from typing import Dict, List

BOOKMARKS_FILE = os.environ.get("PAPERBITES_BOOKMARKS_FILE", "bookmarks.json")


def _load() -> Dict[str, List[Dict]]:
    if not os.path.exists(BOOKMARKS_FILE):
        return {}
    try:
        with open(BOOKMARKS_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error reading bookmarks from {BOOKMARKS_FILE}: {e}")
        return {}


def _save(data: Dict[str, List[Dict]]) -> None:
    with open(BOOKMARKS_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def list_bookmarks(user_id: str) -> List[Dict]:
    """Return this user's bookmark entries, most recently saved first."""
    data = _load()
    entries = data.get(user_id, [])
    return sorted(entries, key=lambda e: e.get("saved_at", 0), reverse=True)


def is_bookmarked(user_id: str, video_id: str) -> bool:
    return any(e["video_id"] == video_id for e in _load().get(user_id, []))


def add_bookmark(user_id: str, video_id: str) -> None:
    data = _load()
    entries = data.setdefault(user_id, [])
    if not any(e["video_id"] == video_id for e in entries):
        entries.append({"video_id": video_id, "saved_at": time.time()})
        _save(data)


def remove_bookmark(user_id: str, video_id: str) -> None:
    data = _load()
    entries = data.get(user_id)
    if not entries:
        return
    filtered = [e for e in entries if e["video_id"] != video_id]
    if len(filtered) != len(entries):
        data[user_id] = filtered
        _save(data)
