# paper/embeddings.py
"""Paper/query embeddings for semantic search, via Gemini's embedding API.

Scope, per explicit decision: embeddings are computed exactly once per paper, at ingestion
(fetch-latest or add-paper-by-citation/photo/URL) - never recomputed on a feed reload, a
bookmark, or any other view of an already-stored paper. That's one Gemini embedding call per
paper, ever. A search query is embedded once per search request (a deliberate, infrequent user
action), not automatically.

Interests stay a hard category exclusion (unchanged) rather than blending in embedding
similarity - semantic search is a separate, explicit action instead of an automatic feed rerank,
leaving room for a softer bounded interest-search later without touching the existing filter.

Uses langchain-google-genai's GoogleGenerativeAIEmbeddings (same package paper/summarize.py and
paper/chat.py already depend on for the chat/summarization models) rather than the raw
google-generativeai SDK, for the same reason those modules do: one dependency, consistent config.
"""
import asyncio
import logging
from typing import Dict, List, Optional

import llm_usage
from config import Config

config_instance = Config()
logger = logging.getLogger("paperbites.embeddings")

# Gemini's current unified embedding model. Overridable in case a newer one supersedes it or a
# deployment wants a specific version pinned - same override pattern as
# api.gemini_models/api.gemini_image_models.
_DEFAULT_EMBEDDING_MODEL = "models/gemini-embedding-001"

_embeddings_cache = {}


def _configured_embedding_model() -> str:
    return config_instance.get("api.gemini_embedding_model") or _DEFAULT_EMBEDDING_MODEL


def _get_embeddings_client():
    """Lazily build (and cache) the embeddings client. Returns None if no API key is configured,
    so callers degrade gracefully (no embedding stored/used) instead of hard-failing."""
    api_key = config_instance.get("api.gemini_key")
    if not api_key:
        return None

    model = _configured_embedding_model()
    if model not in _embeddings_cache:
        from langchain_google_genai import GoogleGenerativeAIEmbeddings

        _embeddings_cache[model] = GoogleGenerativeAIEmbeddings(model=model, google_api_key=api_key)
    return _embeddings_cache[model]


async def embed_document(text: str) -> Optional[List[float]]:
    """Embed a paper's text for storage - one API call, meant to be called exactly once per
    paper at ingestion. Uses the RETRIEVAL_DOCUMENT task type (langchain's embed_documents
    default) for asymmetric retrieval quality against later query embeddings.
    """
    text = (text or "").strip()
    client = _get_embeddings_client()
    if not client or not text:
        return None

    try:
        vectors = await client.aembed_documents([text])
        llm_usage.tracker.log_call(_configured_embedding_model(), len(text) // 4 + 1)
        return vectors[0] if vectors else None
    except Exception as e:
        logger.warning(f"Embedding a paper's text failed: {e}")
        return None


async def embed_query(text: str) -> Optional[List[float]]:
    """Embed a search query - RETRIEVAL_QUERY task type (langchain's embed_query default),
    asymmetric counterpart to embed_document() above."""
    text = (text or "").strip()
    client = _get_embeddings_client()
    if not client or not text:
        return None

    try:
        vector = await client.aembed_query(text)
        llm_usage.tracker.log_call(_configured_embedding_model(), len(text) // 4 + 1)
        return vector
    except Exception as e:
        logger.warning(f"Embedding a search query failed: {e}")
        return None


async def backfill_missing_embeddings(batch_size: int = 20) -> Dict[str, int]:
    """One-time (re-run-safe) backfill for papers already in MongoDB from before this app started
    computing embeddings at ingestion (see paper/latest.py's _apply_embeddings). That function
    only ever runs on papers a *fresh* fetch-latest call actually returns from the external APIs
    for its category/days_back window - a paper fetched before the embeddings feature existed, or
    one that has since aged outside every later fetch-latest run's window, never passes through
    it again and so never gets an `embedding` field, silently dropping out of semantic search
    (search_papers_semantically only looks at documents where `embedding` exists) without
    anything actually being broken. Safe to run repeatedly: it only touches documents still
    missing `embedding`, in small concurrent batches to stay within Gemini's embedding rate limit.
    """
    import db

    collection = db.get_db().papers
    docs = list(collection.find({"embedding": {"$exists": False}}, {"description": 1}))

    embedded = 0
    skipped_no_description = 0
    failed = 0

    async def embed_one(doc: Dict) -> None:
        nonlocal embedded, skipped_no_description, failed
        description = (doc.get("description") or "").strip()
        if not description:
            skipped_no_description += 1
            return
        vector = await embed_document(description)
        if vector:
            collection.update_one({"_id": doc["_id"]}, {"$set": {"embedding": vector}})
            embedded += 1
        else:
            failed += 1

    for i in range(0, len(docs), batch_size):
        batch = docs[i:i + batch_size]
        await asyncio.gather(*(embed_one(doc) for doc in batch))

    return {
        "total_missing": len(docs),
        "embedded": embedded,
        "skipped_no_description": skipped_no_description,
        "failed": failed,
    }


def cosine_similarity(a: List[float], b: List[float]) -> float:
    """Plain-Python cosine similarity. Brute-force over stored embeddings is fine at this app's
    corpus size (a fetch-latest feed, not a web-scale index) - no vector database/index needed
    yet. MongoDB Atlas's native $vectorSearch is a drop-in upgrade later if the corpus outgrows
    an in-process scan.
    """
    if not a or not b or len(a) != len(b):
        return 0.0

    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(y * y for y in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0

    return dot / (norm_a * norm_b)
