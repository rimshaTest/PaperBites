"""
Simple JSON-file-backed bookmark storage.

There's no user/account system yet, so bookmarks are scoped by a
client-generated "device_id" (an opaque random string the frontend
creates once and persists locally) rather than a real user id.
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


def list_bookmarks(device_id: str) -> List[Dict]:
    """Return this device's bookmark entries, most recently saved first."""
    data = _load()
    entries = data.get(device_id, [])
    return sorted(entries, key=lambda e: e.get("saved_at", 0), reverse=True)


def is_bookmarked(device_id: str, video_id: str) -> bool:
    return any(e["video_id"] == video_id for e in _load().get(device_id, []))


def add_bookmark(device_id: str, video_id: str) -> None:
    data = _load()
    entries = data.setdefault(device_id, [])
    if not any(e["video_id"] == video_id for e in entries):
        entries.append({"video_id": video_id, "saved_at": time.time()})
        _save(data)


def remove_bookmark(device_id: str, video_id: str) -> None:
    data = _load()
    entries = data.get(device_id)
    if not entries:
        return
    filtered = [e for e in entries if e["video_id"] != video_id]
    if len(filtered) != len(entries):
        data[device_id] = filtered
        _save(data)
