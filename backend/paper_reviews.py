"""
Simple JSON-file-backed queue of citations/URLs the automated add-paper search (paper/citation.py)
couldn't resolve, for manual admin review - docs/TECHNICAL_SPEC.md's fallback for the add-paper
pipeline: "let the user submit the image/citation for manual admin review if retries don't
resolve it." Early on this is a short queue reviewed by hand (per the spec's own build note); no
admin UI reads this yet, but list_reviews() is here so one (or a human going through the JSON file
directly) has somewhere to start.
"""
import os
import json
import time
import uuid
from typing import Dict, List, Optional

REVIEWS_FILE = os.environ.get("PAPERBITES_PAPER_REVIEWS_FILE", "paper_reviews.json")


def _load() -> List[Dict]:
    if not os.path.exists(REVIEWS_FILE):
        return []
    try:
        with open(REVIEWS_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error reading paper reviews from {REVIEWS_FILE}: {e}")
        return []


def _save(data: List[Dict]) -> None:
    with open(REVIEWS_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def submit_review(user_id: str, raw_input: str) -> Dict:
    """Queue a citation or URL the automated search couldn't match, for manual admin review."""
    entries = _load()
    entry = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "input": raw_input,
        "status": "pending",
        "submitted_at": time.time(),
    }
    entries.append(entry)
    _save(entries)
    return entry


def list_reviews(status: Optional[str] = None) -> List[Dict]:
    """All submissions, optionally filtered by status ('pending', 'resolved', 'rejected'), most
    recently submitted first."""
    entries = _load()
    if status:
        entries = [e for e in entries if e.get("status") == status]
    return sorted(entries, key=lambda e: e.get("submitted_at", 0), reverse=True)
