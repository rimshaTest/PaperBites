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

# Embedding models, in preference order. Each has its own free-tier quota (llm_usage.DEFAULT_LIMITS),
# so listing more than one lets ingestion fall through to the next when one's budget is spent or
# it's overloaded. Override with api.gemini_embedding_models (comma-separated or a list; env
# PAPERBITES_GEMINI_EMBEDDING_MODELS) or the older single api.gemini_embedding_model.
#
# IMPORTANT: vectors from different models live in different spaces and can't be compared with
# each other (cosine_similarity returns 0 for different lengths, and is meaningless for equal
# lengths). So every stored vector records its `embedding_model`, and search / the Visualize graph
# only ever compare vectors made by the same model.
_DEFAULT_EMBEDDING_MODELS = ["models/gemini-embedding-001"]
_LEGACY_EMBEDDING_MODEL = "gemini-embedding-001"  # what papers embedded before the model was recorded used

_embeddings_cache = {}


def _configured_embedding_models() -> List[str]:
    configured = config_instance.get("api.gemini_embedding_models")
    if isinstance(configured, str):
        configured = [name.strip() for name in configured.split(",") if name.strip()]
    if configured:
        return list(configured)
    single = config_instance.get("api.gemini_embedding_model")
    return [single] if single else list(_DEFAULT_EMBEDDING_MODELS)


def _configured_embedding_model() -> str:
    """The preferred (first) embedding model."""
    return _configured_embedding_models()[0]


def _get_embeddings_client(model: Optional[str] = None):
    """Lazily build (and cache) the embeddings client for `model` (default: the preferred one).
    Returns None if no API key is configured, so callers degrade gracefully (no embedding
    stored/used) instead of hard-failing."""
    api_key = config_instance.get("api.gemini_key")
    if not api_key:
        return None

    model = model or _configured_embedding_model()
    if model not in _embeddings_cache:
        from langchain_google_genai import GoogleGenerativeAIEmbeddings

        # Client-side retries are kept minimal: llm_usage paces calls and handles 429/503 itself
        _embeddings_cache[model] = GoogleGenerativeAIEmbeddings(
            model=model if model.startswith("models/") else f"models/{model}", google_api_key=api_key,
        )
    return _embeddings_cache[model]


def embedding_text(paper: Dict) -> str:
    """What gets embedded for a paper: its title and its description together, so a search can
    match on either."""
    title = (paper.get("title") or "").strip()
    description = (paper.get("description") or "").strip()
    return f"{title}\n\n{description}".strip()


async def _lap_sleep(seconds: float) -> None:
    await asyncio.sleep(seconds)


def _lap_settings():
    wait = config_instance.get("api.gemini_overload_wait_seconds")
    cap = config_instance.get("api.gemini_overload_max_wait_seconds")
    return float(wait or 60.0), (float(cap) if cap is not None else None)


async def embed_document_with_model(text: str):
    """Embed a paper's text for storage and say which model made the vector: (vector, model_key)
    or None. One logical call per paper, meant to happen exactly once at ingestion. Goes through
    the usage tracker, falling through the configured embedding models (a spent daily budget or a
    503 on one moves to the next; all overloaded -> wait and go around again, like text calls).
    Uses the RETRIEVAL_DOCUMENT task type for asymmetric retrieval quality against later queries.
    """
    text = (text or "").strip()
    if not text or _get_embeddings_client() is None:
        return None

    configured = {llm_usage.model_key(m): m for m in _configured_embedding_models()}
    estimate = len(text) // 4 + 1

    async def attempt(model: str):
        client = _get_embeddings_client(configured[model])
        vectors = await client.aembed_documents([text])
        return (vectors[0] if vectors else None), estimate

    lap_wait, max_wait = _lap_settings()
    outcome = await llm_usage.cycle_models(
        list(configured), estimate, attempt, "a paper embedding", lap_wait=lap_wait, max_wait=max_wait,
        sleep=_lap_sleep,
    )
    if outcome is None:
        logger.warning("Embedding a paper's text failed (no embedding model available)")
        return None
    model, vector = outcome
    return vector, model


async def embed_document(text: str) -> Optional[List[float]]:
    """Just the vector from embed_document_with_model (callers that don't record the model)."""
    result = await embed_document_with_model(text)
    return result[0] if result else None


async def embed_query_with_model(text: str, model: str) -> Optional[List[float]]:
    """Embed a search query with one specific model - the one a stored paper's vector came from,
    so the two can be compared. RETRIEVAL_QUERY task type, asymmetric counterpart to documents.
    Budget-tracked; waits out a per-minute limit but gives up (None) if the model's day is spent."""
    text = (text or "").strip()
    key = llm_usage.model_key(model)
    configured = {llm_usage.model_key(m): m for m in _configured_embedding_models()}
    client = _get_embeddings_client(configured.get(key, key))
    if not client or not text:
        return None

    estimate = len(text) // 4 + 1
    try:
        reservation = await llm_usage.tracker.acquire(key, estimate)
    except llm_usage.LLMQuotaExhausted:
        return None
    try:
        vector = await client.aembed_query(text)
    except Exception as e:
        if llm_usage.is_transient_error(e):
            llm_usage.tracker.refund(reservation)
        else:
            llm_usage.tracker.finish(reservation, None)
            if llm_usage.is_quota_error(e):
                llm_usage.tracker.note_api_quota_error(key, str(e))
        logger.warning(f"Embedding a search query with '{key}' failed: {e}")
        return None
    llm_usage.tracker.finish(reservation, estimate)
    return vector


async def embed_query(text: str) -> Optional[List[float]]:
    """Embed a search query with the preferred model (see embed_query_with_model)."""
    return await embed_query_with_model(text, _configured_embedding_model())


def doc_embedding_model(doc: Dict) -> str:
    """Which model made a stored paper's vector (papers embedded before this was recorded were
    made with the original model)."""
    return doc.get("embedding_model") or _LEGACY_EMBEDDING_MODEL


async def score_documents(query: str, docs: List[Dict]) -> List:
    """Score `docs` (each with an `embedding`) against `query`, as [(similarity, doc)] best first.

    The query is embedded once per distinct embedding model present among the docs, and each doc
    is compared only to the query vector from its own model - vectors from different models
    can't be compared. A doc whose model can't embed the query right now (its quota is spent) is
    left out rather than scored against the wrong space."""
    by_model: Dict[str, List[Dict]] = {}
    for doc in docs:
        by_model.setdefault(llm_usage.model_key(doc_embedding_model(doc)), []).append(doc)

    scored = []
    for model, group in by_model.items():
        query_vector = await embed_query_with_model(query, model)
        if not query_vector:
            logger.warning(f"Skipping {len(group)} paper(s) embedded with '{model}': couldn't embed the query with it")
            continue
        scored.extend((cosine_similarity(query_vector, doc.get("embedding") or []), doc) for doc in group)
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return scored


async def backfill_missing_embeddings(batch_size: int = 20) -> Dict[str, int]:
    """One-time (re-run-safe) backfill for papers already in MongoDB that have no embedding -
    ones fetched before embeddings existed, that fell outside every later fetch window, or that
    were stored while the embedding models were unavailable. Embeds each paper's title and
    description, records which model made the vector, and only touches documents still missing
    `embedding`. Papers are embedded one at a time (the models' own rate limits are paced by the
    usage tracker), and each is saved as soon as it's done.
    """
    import db

    collection = db.get_db().papers
    docs = list(collection.find({"embedding": {"$exists": False}}, {"title": 1, "description": 1}))

    embedded = 0
    skipped_no_description = 0
    failed = 0

    for doc in docs:
        if not (doc.get("description") or "").strip():
            skipped_no_description += 1
            continue
        result = await embed_document_with_model(embedding_text(doc))
        if result:
            vector, model = result
            collection.update_one({"_id": doc["_id"]}, {"$set": {"embedding": vector, "embedding_model": model}})
            embedded += 1
        else:
            failed += 1

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
