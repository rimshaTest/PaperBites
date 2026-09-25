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
import logging
from typing import List, Optional

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
        return await client.aembed_query(text)
    except Exception as e:
        logger.warning(f"Embedding a search query failed: {e}")
        return None


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
