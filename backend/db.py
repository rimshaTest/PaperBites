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

    logger.info(f"Connected to MongoDB database '{db_name}'")
    return _db


def upsert_papers(papers):
    """Insert or update papers by (source, source_id). Returns the number of papers written."""
    db = get_db()
    written = 0

    for paper in papers:
        db.papers.update_one(
            {"source": paper["source"], "source_id": paper["source_id"]},
            {"$set": paper},
            upsert=True,
        )
        written += 1

    return written
