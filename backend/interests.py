"""
Simple JSON-file-backed interest storage, scoped by authenticated user id
(see auth.py) - mirrors bookmarks.py's pattern. A user's chosen topic
interests follow their account, not any one device, and are used by
api_server.py to boost matching papers in the discovery feed.
"""
import os
import json
from typing import Dict, List

INTERESTS_FILE = os.environ.get("PAPERBITES_INTERESTS_FILE", "interests.json")


def _load() -> Dict[str, List[str]]:
    if not os.path.exists(INTERESTS_FILE):
        return {}
    try:
        with open(INTERESTS_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error reading interests from {INTERESTS_FILE}: {e}")
        return {}


def _save(data: Dict[str, List[str]]) -> None:
    with open(INTERESTS_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def get_interests(user_id: str) -> List[str]:
    """Return this user's chosen interests, or [] if they haven't set any."""
    return _load().get(user_id, [])


def set_interests(user_id: str, interests: List[str]) -> None:
    """Replace this user's interests wholesale (the client always sends the full set)."""
    data = _load()
    data[user_id] = list(dict.fromkeys(interests))  # de-dupe, preserve order
    _save(data)
