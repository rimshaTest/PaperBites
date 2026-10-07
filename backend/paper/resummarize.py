"""Upgrade papers that were stored without a real summary.

`fetch-latest --no-llm` (or `--continue-without-llm`, or a run with no Gemini key) stores a paper
with its abstract as the description and no embedding, labeled `description_source: "abstract"`.
This finds those papers and gives each a real plain-English summary (and an embedding, if it has
none), one at a time, saving each as it's done - so it can be interrupted and re-run freely, and
it goes through the same usage tracker and 503 cycling as every other Gemini call.
"""
import logging
from typing import Dict

logger = logging.getLogger("paperbites.resummarize")

# Same idea as paper/latest.py's LLM_FAILURE_LIMIT: this many failures in a row means stop
_FAILURE_LIMIT = 3


async def resummarize_papers(limit: int = 20, embed: bool = True) -> Dict[str, int]:
    """Summarize up to `limit` abstract-only papers (newest first). Returns counts:
    candidates, upgraded, embedded, failed, and stopped_reason (a string, only if it stopped early).
    """
    import db
    import llm_usage
    from paper.embeddings import embed_document_with_model, embedding_text
    from paper.summarize import _configured_model_names, summarize_text

    collection = db.get_db().papers
    query = {"description_source": "abstract", "abstract": {"$nin": [None, ""]}}
    cursor = collection.find(query, {"title": 1, "abstract": 1, "embedding": 1}).sort("published_date", -1)
    docs = list(cursor.limit(limit)) if limit and limit > 0 else list(cursor)

    result = {"candidates": len(docs), "upgraded": 0, "embedded": 0, "failed": 0}
    models = _configured_model_names()
    consecutive_failures = 0

    for doc in docs:
        if llm_usage.tracker.all_exhausted(models):
            result["stopped_reason"] = "daily Gemini quota spent on every model"
            break

        title = doc.get("title") or "Untitled"
        summary = await summarize_text(title, doc["abstract"])
        if not summary:
            result["failed"] += 1
            consecutive_failures += 1
            logger.warning(f"Couldn't summarize '{title[:60]}' ({consecutive_failures} in a row)")
            if consecutive_failures >= _FAILURE_LIMIT:
                result["stopped_reason"] = f"{consecutive_failures} papers in a row couldn't be summarized"
                break
            continue
        consecutive_failures = 0

        updates = {"description": summary, "description_source": "summary"}
        if embed and not doc.get("embedding"):
            embedded = await embed_document_with_model(embedding_text({"title": title, "description": summary}))
            if embedded:
                updates["embedding"], updates["embedding_model"] = embedded
                result["embedded"] += 1
        collection.update_one({"_id": doc["_id"]}, {"$set": updates})
        result["upgraded"] += 1
        logger.info(f"Summarized '{title[:70]}'")

    return result
