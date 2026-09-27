"""
Simple JSON-file-backed store of *confirmed* paper reads, scoped by authenticated user id - same
pattern as bookmarks.py/interests.py.

A "read" here means the user tapped "View Original Paper", left the app, came back, and answered
"Yes" to the Libby-style "Did you read this paper?" prompt (see api_server.py's
record_paper_view and the frontend's ReadConfirmationGate) - not just clicking the link. That
confirmed-read event is what feeds the Visualize tab's bubble map, per-topic reading stats, the
1st/5th/10th/25th/50th/100th read milestone badges, and the cross-user trending signal below.
"""
import os
import json
import time
from typing import Dict, List, Optional

PAPER_VIEWS_FILE = os.environ.get("PAPERBITES_PAPER_VIEWS_FILE", "paper_views.json")

# Milestone badges shown on Profile once earned (frontend animates a pop-in celebration the
# moment one is newly crossed - see record_view's return value below).
MILESTONES = [1, 5, 10, 25, 50, 100]


def _load() -> Dict[str, List[Dict]]:
    if not os.path.exists(PAPER_VIEWS_FILE):
        return {}
    try:
        with open(PAPER_VIEWS_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error reading paper views from {PAPER_VIEWS_FILE}: {e}")
        return {}


def _save(data: Dict[str, List[Dict]]) -> None:
    with open(PAPER_VIEWS_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def record_view(user_id: str, paper_id: str) -> Dict:
    """Record a confirmed read. Idempotent - confirming the same paper again doesn't duplicate
    the entry or change its original viewed_at. Returns the user's updated total confirmed-read
    count and whether this call actually added a new entry, so the caller can tell whether a
    milestone was *just* crossed (as opposed to re-confirming an already-read paper, which should
    never re-trigger a celebration).
    """
    data = _load()
    entries = data.setdefault(user_id, [])
    is_new = not any(e["paper_id"] == paper_id for e in entries)
    if is_new:
        entries.append({"paper_id": paper_id, "viewed_at": time.time()})
        _save(data)
    return {"is_new": is_new, "total_read": len(entries)}


def list_viewed_paper_ids(user_id: str) -> List[str]:
    """This user's confirmed-read paper ids, oldest first."""
    entries = _load().get(user_id, [])
    return [e["paper_id"] for e in sorted(entries, key=lambda e: e.get("viewed_at", 0))]


def all_entries() -> List[List[Dict]]:
    """Every user's raw confirmed-read entries - used only for cross-user aggregates (trending),
    never exposed per-user through the API."""
    return list(_load().values())


def milestone_reached(total_read: int, is_new: bool) -> Optional[int]:
    """Which milestone (if any) this read just crossed - None if it's not a new read, or the new
    total isn't one of the fixed milestone thresholds."""
    if is_new and total_read in MILESTONES:
        return total_read
    return None
