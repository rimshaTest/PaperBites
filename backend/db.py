# db.py
import logging

import pymongo

from config import Config

logger = logging.getLogger("paperbites.db")

_client = None
_db = None


def get_db():
    """Get the shared MongoDB database handle, connecting and creating indexes on first use."""
    global _client, _db
    if _db is not None:
        return _db

    config = Config()
    uri = config.get("storage.mongodb.connection_string")
    db_name = config.get("storage.mongodb.database_name", "paperbites")

    if not uri:
        raise RuntimeError("MongoDB connection string not configured (storage.mongodb.connection_string)")

    _client = pymongo.MongoClient(uri)
    _db = _client[db_name]

    _db.papers.create_index([("source", 1), ("source_id", 1)], unique=True)
    _db.papers.create_index([("categories", 1), ("published_date", -1)])
    _db.papers.create_index("authors.id")
    _db.papers.create_index("journal")

    _db.paper_reviews.create_index([("status", 1), ("submitted_at", -1)])
    _db.paper_reviews.create_index("user_id")

    _db.users.create_index("email", unique=True)
    _db.users.create_index("id", unique=True)
    # TTLs mirror auth.py's RESET_CODE_TTL_SECONDS (15 min) and SESSION_TTL_SECONDS (30 days) -
    # duplicated here as literals rather than imported, since auth.py imports this module and a
    # reverse import would be circular. Mongo's background TTL sweep is a backstop cleanup;
    # auth.py's own expiry checks on read are what actually enforce these windows.
    _db.password_resets.create_index("created_at", expireAfterSeconds=15 * 60)
    _db.sessions.create_index("created_at", expireAfterSeconds=30 * 24 * 60 * 60)
    _db.sessions.create_index("user_id")

    _db.bookmarks.create_index([("user_id", 1), ("video_id", 1)], unique=True)
    _db.profile_tier2_audit.create_index("user_id")

    logger.info(f"Connected to MongoDB database '{db_name}'")
    return _db


def upsert_paper(paper):
    """Insert or update one paper by (source, source_id)."""
    get_db().papers.update_one(
        {"source": paper["source"], "source_id": paper["source_id"]},
        {"$set": paper},
        upsert=True,
    )


def upsert_papers(papers):
    """Insert or update papers by (source, source_id). Returns the number of papers written."""
    written = 0
    for paper in papers:
        upsert_paper(paper)
        written += 1
    return written


def paper_is_stored(source, source_id):
    """True if this (source, source_id) is already stored with a non-empty description - used to
    skip re-enriching (and re-spending LLM quota on) papers a previous run already finished."""
    if not source or not source_id:
        return False
    doc = get_db().papers.find_one(
        {"source": source, "source_id": source_id}, {"description": 1}
    )
    return bool(doc and (doc.get("description") or "").strip())
