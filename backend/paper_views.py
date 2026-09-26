"""
Simple JSON-file-backed store of "View Original Paper" clicks (the external-link button on the
paper detail screen), scoped by authenticated user id - same pattern as bookmarks.py/interests.py.

This is the source data for the Visualizations tab's paper-relationship bubble map: every paper a
user has clicked through to read the full text of, connected to each other by embedding
similarity (see api_server.py's get_viewed_papers_graph and paper/embeddings.py).
"""
import os
import json
import time
from typing import Dict, List

PAPER_VIEWS_FILE = os.environ.get("PAPERBITES_PAPER_VIEWS_FILE", "paper_views.json")


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


def record_view(user_id: str, paper_id: str) -> None:
    """Record that a user clicked through to a paper's original source. Idempotent - clicking
    the same paper again doesn't create a duplicate entry or change its original viewed_at."""
    data = _load()
    entries = data.setdefault(user_id, [])
    if not any(e["paper_id"] == paper_id for e in entries):
        entries.append({"paper_id": paper_id, "viewed_at": time.time()})
        _save(data)


def list_viewed_paper_ids(user_id: str) -> List[str]:
    """This user's viewed paper ids, oldest first."""
    entries = _load().get(user_id, [])
    return [e["paper_id"] for e in sorted(entries, key=lambda e: e.get("viewed_at", 0))]
