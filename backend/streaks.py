"""
Reading-streak level shown on Profile as a badge, derived from confirmed paper reads
(paper_views.record_view calls record_read below on every *new* confirmed read).

Mechanics: a user gains a level for every 2 additional consecutive calendar days they read on,
and loses one level only after *two* consecutive days pass with no read - a single day off is
forgiven so one busy day doesn't wipe out a streak. This is deliberately not a pure function of
"current streak length": promotion and demotion are tracked as separate one-way transitions (see
_settle/record_read) so a demotion doesn't also erase the grace a user gets before it fires.

Concretely, `buffer` is progress within the current level: +1 per consecutive read day (promotes
and resets to 0 at +2), -1 per fully-elapsed missed day (demotes and resets to 0 at -2).
"""
import time
from datetime import date
from typing import Dict

import db

# Order matters - index is the level number. Reaching index N requires 2*N total consecutive
# reading days (2 for the first promotion, 2 more for the next, and so on); "The Practical
# Thinker" is the default badge everyone starts with, not something earned.
LEVELS = ["The Practical Thinker", "The Fact Collector", "The Intellectual", "The Scholar"]
MAX_LEVEL = len(LEVELS) - 1

_DEFAULT_STATE = {"level": 0, "buffer": 0, "last_read_date": None}


def _today() -> date:
    return date.fromtimestamp(time.time())


def _settle(state: Dict, today: date) -> Dict:
    """Apply decay for every full calendar day since the last read that has already elapsed
    with no read on it (days strictly between last_read_date and today - today itself is never
    "missed" yet). Two such days in a row cost one level; a single one only depletes the buffer
    without demoting."""
    last_read = state.get("last_read_date")
    if not last_read:
        return state

    last_read_date = date.fromisoformat(last_read)
    missed = (today - last_read_date).days - 1
    level = state.get("level", 0)
    buffer = state.get("buffer", 0)

    # Capped so a user absent for months doesn't cost more than fully bottoming out - once level
    # is back to 0 further missed days have nothing left to take.
    for _ in range(max(0, min(missed, MAX_LEVEL * 2))):
        buffer -= 1
        if buffer <= -2:
            level = max(0, level - 1)
            buffer = 0

    return {**state, "level": level, "buffer": buffer}


def record_read(user_id: str) -> Dict:
    """Update this user's streak state for a confirmed read happening today. Safe to call more
    than once for the same calendar day - a second read today doesn't advance the streak twice,
    matching how paper_views.record_view only counts a given paper once per user regardless."""
    collection = db.get_db().streaks
    state = collection.find_one({"_id": user_id}) or dict(_DEFAULT_STATE)
    today = _today()

    if state.get("last_read_date") == today.isoformat():
        return _to_public(state)

    state = _settle(state, today)

    last_read = state.get("last_read_date")
    consecutive = last_read is not None and (today - date.fromisoformat(last_read)).days == 1
    state["buffer"] = state.get("buffer", 0) + 1 if consecutive else 1
    if state["buffer"] >= 2 and state["level"] < MAX_LEVEL:
        state["level"] += 1
        state["buffer"] = 0
    state["last_read_date"] = today.isoformat()

    collection.update_one(
        {"_id": user_id},
        {"$set": {"level": state["level"], "buffer": state["buffer"], "last_read_date": state["last_read_date"]}},
        upsert=True,
    )
    return _to_public(state)


def get_streak(user_id: str) -> Dict:
    """This user's current streak badge, settling decay for any missed days since their last
    read even if they haven't read again since - so the badge reflects today, not their last
    visit."""
    collection = db.get_db().streaks
    state = collection.find_one({"_id": user_id})
    if not state:
        return _to_public(_DEFAULT_STATE)

    today = _today()
    settled = _settle(state, today)
    if settled["level"] != state.get("level") or settled["buffer"] != state.get("buffer"):
        collection.update_one(
            {"_id": user_id}, {"$set": {"level": settled["level"], "buffer": settled["buffer"]}}
        )
    return _to_public(settled)


def _to_public(state: Dict) -> Dict:
    level = state.get("level", 0)
    return {"level": level, "label": LEVELS[level]}
