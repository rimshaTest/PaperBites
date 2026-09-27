from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
import uvicorn
import os
import time
from typing import List, Dict, Optional

import bookmarks as bookmarks_store
import interests as interests_store
import profile as profile_store
import paper_reviews as paper_reviews_store
import paper_views as paper_views_store
import auth
import email_sender
from rate_limit import RateLimitMiddleware
from monitoring import init_monitoring
from utils.text import clean_abstract

init_monitoring()


def _serialize_paper(doc: Dict) -> Dict:
    """Convert a MongoDB paper document into a JSON-safe dict with a plain string id.

    Also cleans `abstract`/`description` here (not just at ingestion in paper/latest.py) so
    papers stored before clean_abstract() existed display cleanly too, without needing a
    re-fetch: strips a leading "Abstract" label and inline structured-abstract section headers
    ("Purpose:", "Findings:", etc.).

    Papers fetched before the description/summarization step existed (or a source that never
    got a Gemini summary) may have no `description` field at all - fall back to the raw
    `abstract` here so every consumer of this API gets a usable description without each one
    having to remember the fallback itself.
    """
    doc = dict(doc)
    doc["id"] = str(doc.pop("_id"))
    doc.pop("embedding", None)  # a 768-float vector the client never uses - don't ship it
    if doc.get("abstract"):
        doc["abstract"] = clean_abstract(doc["abstract"])
    doc["description"] = clean_abstract(doc.get("description")) or doc.get("abstract", "")
    return doc


def get_all_papers(category: Optional[str] = None) -> List[Dict]:
    """Fetch papers (fetched via `cli.py fetch-latest`, no video generation involved) from
    MongoDB, newest first. Returns [] if MongoDB isn't reachable/configured rather than
    raising, so a broken DB doesn't take down the whole API - callers see an empty feed."""
    try:
        import db
        query = {"categories": category} if category else {}
        cursor = db.get_db().papers.find(query).sort("published_date", -1)
        return [_serialize_paper(doc) for doc in cursor]
    except Exception as e:
        print(f"Error reading papers from MongoDB: {e}")
        return []


def get_paper_by_id(paper_id: str) -> Optional[Dict]:
    try:
        import db
        from bson import ObjectId
        doc = db.get_db().papers.find_one({"_id": ObjectId(paper_id)})
        return _serialize_paper(doc) if doc else None
    except Exception as e:
        print(f"Error reading paper {paper_id} from MongoDB: {e}")
        return None


def get_papers_by_author(author_id: str) -> Optional[Dict]:
    """All papers by an author id (e.g. 'semantic_scholar:12345'), newest first."""
    try:
        import db
        cursor = db.get_db().papers.find({"authors.id": author_id}).sort("published_date", -1)
        papers = [_serialize_paper(doc) for doc in cursor]
        if not papers:
            return None
        name = next(
            (a["name"] for p in papers for a in p.get("authors", []) if a.get("id") == author_id),
            author_id,
        )
        return {"id": author_id, "name": name, "papers": papers}
    except Exception as e:
        print(f"Error reading author {author_id} from MongoDB: {e}")
        return None


def get_papers_by_journal(journal_name: str) -> Optional[Dict]:
    """All papers published in a given journal/venue, newest first."""
    try:
        import db
        cursor = db.get_db().papers.find({"journal": journal_name}).sort("published_date", -1)
        papers = [_serialize_paper(doc) for doc in cursor]
        if not papers:
            return None
        return {"name": journal_name, "papers": papers}
    except Exception as e:
        print(f"Error reading journal '{journal_name}' from MongoDB: {e}")
        return None


def get_authenticated_user_id(request) -> Optional[str]:
    """Resolve the requesting user from an 'Authorization: Bearer <token>' header."""
    header = request.headers.get("authorization", "")
    if not header.lower().startswith("bearer "):
        return None
    token = header[7:].strip()
    return auth.get_user_id_for_token(token)


# A paper only gets the "Trending" badge if more than one person actually confirmed reading it
# this week - a single lucky read isn't a trend. One trending paper per category, the most-read.
_TRENDING_WINDOW_DAYS = 7
_TRENDING_MIN_READS = 2


def _trending_category_by_paper_id(papers: List[Dict]) -> Dict[str, str]:
    """{paper_id: category} for the single most-confirmed-read paper in each category over the
    trailing week. Recomputed on every feed request rather than cached - fine at this app's
    read volume (a flat JSON scan), worth revisiting if that stops being true.
    """
    cutoff = time.time() - _TRENDING_WINDOW_DAYS * 86400
    read_counts: Dict[str, int] = {}
    for entries in paper_views_store.all_entries():
        for entry in entries:
            if entry.get("viewed_at", 0) >= cutoff:
                pid = entry["paper_id"]
                read_counts[pid] = read_counts.get(pid, 0) + 1

    if not read_counts:
        return {}

    categories_by_paper = {p["id"]: (p.get("categories") or []) for p in papers}

    best_per_category: Dict[str, tuple] = {}
    for paper_id, count in read_counts.items():
        if count < _TRENDING_MIN_READS:
            continue
        for category in categories_by_paper.get(paper_id, []):
            current = best_per_category.get(category)
            if not current or count > current[1]:
                best_per_category[category] = (paper_id, count)

    return {paper_id: category for category, (paper_id, _count) in best_per_category.items()}


async def list_papers(request):
    """Get a list of papers, fetched via `cli.py fetch-latest` (no video generation).

    When the request is authenticated and the user has chosen interests, the feed is hard-filtered
    to only papers whose categories intersect those interests - a deliberate hard exclusion, not
    a ranking signal (see search_papers_semantically below for the embedding-based feature
    instead). A user with no interests set (skipped onboarding, or hasn't visited Interests yet)
    sees everything, unfiltered.

    Each paper is also tagged `trending_category` (the category it's trending in, or null) - see
    _trending_category_by_paper_id above.
    """
    limit = int(request.query_params.get("limit", "50"))
    offset = int(request.query_params.get("offset", "0"))
    category = request.query_params.get("category")

    papers = get_all_papers(category)

    user_id = get_authenticated_user_id(request)
    if user_id:
        user_interests = set(interests_store.get_interests(user_id))
        if user_interests:
            papers = [p for p in papers if user_interests.intersection(p.get("categories") or [])]

    trending_by_paper = _trending_category_by_paper_id(papers)
    for p in papers:
        p["trending_category"] = trending_by_paper.get(p["id"])

    return JSONResponse(papers[offset:offset + limit])


async def search_papers_semantically(request):
    """Semantic search over papers embedded at ingestion (paper/embeddings.py), via cosine
    similarity. Brute-force in Python over every embedded paper - fine at this app's corpus
    size (a fetch-latest feed, not a web-scale index); MongoDB Atlas's native $vectorSearch is a
    drop-in upgrade later if that stops being true. The query is embedded once per request (a
    deliberate search action), separate from the hard interests filter above rather than
    blending into it.
    """
    query = (request.query_params.get("q") or "").strip()
    if not query:
        return JSONResponse({"detail": "q is required"}, status_code=400)

    limit = int(request.query_params.get("limit", "20"))

    try:
        from paper.embeddings import embed_query, cosine_similarity
    except ImportError as e:
        print(f"Semantic search unavailable, paper.embeddings failed to import: {e}")
        return JSONResponse({"detail": "Semantic search is temporarily unavailable"}, status_code=503)

    query_vector = await embed_query(query)
    if not query_vector:
        return JSONResponse({"detail": "Semantic search is temporarily unavailable"}, status_code=503)

    try:
        import db
        cursor = db.get_db().papers.find({"embedding": {"$exists": True}})
        scored = [
            (cosine_similarity(query_vector, doc.get("embedding") or []), doc)
            for doc in cursor
        ]
    except Exception as e:
        print(f"Error reading papers for semantic search from MongoDB: {e}")
        return JSONResponse([])

    scored.sort(key=lambda pair: pair[0], reverse=True)
    top_papers = [doc for _, doc in scored[:limit]]
    return JSONResponse([_serialize_paper(doc) for doc in top_papers])


async def get_interests(request):
    """Get the current user's chosen topic interests."""
    user_id = get_authenticated_user_id(request)
    if not user_id:
        return JSONResponse({"detail": "Authentication required"}, status_code=401)

    return JSONResponse({"interests": interests_store.get_interests(user_id)})


async def set_interests(request):
    """Replace the current user's chosen topic interests."""
    user_id = get_authenticated_user_id(request)
    if not user_id:
        return JSONResponse({"detail": "Authentication required"}, status_code=401)

    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"detail": "Invalid JSON body"}, status_code=400)

    interests = body.get("interests")
    if not isinstance(interests, list) or not all(isinstance(i, str) for i in interests):
        return JSONResponse({"detail": "interests must be a list of strings"}, status_code=400)

    interests_store.set_interests(user_id, interests)
    return JSONResponse({"interests": interests_store.get_interests(user_id)})


async def get_profile(request):
    """Get the current user's Tier 1 (cache-safe) and Tier 2 (sensitive-context) profile fields."""
    user_id = get_authenticated_user_id(request)
    if not user_id:
        return JSONResponse({"detail": "Authentication required"}, status_code=401)

    return JSONResponse({
        "tier1": profile_store.get_tier1(user_id),
        "tier2": profile_store.get_tier2(user_id),
    })


async def set_profile_tier1(request):
    """Update the current user's Tier 1 (cache-safe) profile fields."""
    user_id = get_authenticated_user_id(request)
    if not user_id:
        return JSONResponse({"detail": "Authentication required"}, status_code=401)

    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"detail": "Invalid JSON body"}, status_code=400)

    fields = body.get("fields")
    if not isinstance(fields, dict):
        return JSONResponse({"detail": "fields must be an object"}, status_code=400)

    try:
        updated = profile_store.set_tier1(user_id, fields)
    except ValueError as e:
        return JSONResponse({"detail": str(e)}, status_code=400)

    return JSONResponse({"tier1": updated})


async def set_profile_tier2(request):
    """Update the current user's Tier 2 (sensitive-context) profile fields and their per-field
    consent flags."""
    user_id = get_authenticated_user_id(request)
    if not user_id:
        return JSONResponse({"detail": "Authentication required"}, status_code=401)

    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"detail": "Invalid JSON body"}, status_code=400)

    fields = body.get("fields") or {}
    consent = body.get("consent") or {}
    if not isinstance(fields, dict) or not isinstance(consent, dict):
        return JSONResponse({"detail": "fields and consent must be objects"}, status_code=400)

    try:
        updated = profile_store.set_tier2(user_id, fields, consent)
    except ValueError as e:
        return JSONResponse({"detail": str(e)}, status_code=400)

    return JSONResponse({"tier2": updated})


async def get_paper(request):
    """Get a single paper by id."""
    paper = get_paper_by_id(request.path_params["paper_id"])
    if not paper:
        return JSONResponse({"detail": "Paper not found"}, status_code=404)
    return JSONResponse(paper)


async def record_paper_view(request):
    """Record that the current user *confirmed* reading this paper - called from the frontend's
    Libby-style "Did you read this paper?" prompt (shown when the app returns to the foreground
    after the user opened "View Original Paper"), not from the button tap itself. This is the
    source data for the Visualizations tab's bubble map (see get_viewed_papers_graph below),
    per-topic reading stats (get_reading_stats), and milestone badges.
    """
    user_id = get_authenticated_user_id(request)
    if not user_id:
        return JSONResponse({"detail": "Authentication required"}, status_code=401)

    paper_id = request.path_params["paper_id"]
    if not get_paper_by_id(paper_id):
        return JSONResponse({"detail": "Not found"}, status_code=404)

    result = paper_views_store.record_view(user_id, paper_id)
    milestone = paper_views_store.milestone_reached(result["total_read"], result["is_new"])
    return JSONResponse(
        {"status": "ok", "total_read": result["total_read"], "milestone_reached": milestone},
        status_code=201,
    )


async def get_reading_stats(request):
    """Per-topic reading stats for the current user (Profile screen): total confirmed reads,
    a breakdown by category, and which milestone badges have been earned so far."""
    user_id = get_authenticated_user_id(request)
    if not user_id:
        return JSONResponse({"detail": "Authentication required"}, status_code=401)

    paper_ids = paper_views_store.list_viewed_paper_ids(user_id)
    total_read = len(paper_ids)
    milestones_reached = [m for m in paper_views_store.MILESTONES if total_read >= m]

    if not paper_ids:
        return JSONResponse({"total_read": 0, "by_category": {}, "milestones_reached": milestones_reached})

    try:
        import db
        from bson import ObjectId

        object_ids = []
        for pid in paper_ids:
            try:
                object_ids.append(ObjectId(pid))
            except Exception:
                continue
        docs = db.get_db().papers.find({"_id": {"$in": object_ids}})
    except Exception as e:
        print(f"Error building reading stats from MongoDB: {e}")
        return JSONResponse({"total_read": total_read, "by_category": {}, "milestones_reached": milestones_reached})

    by_category: Dict[str, int] = {}
    for doc in docs:
        for category in doc.get("categories") or []:
            by_category[category] = by_category.get(category, 0) + 1

    return JSONResponse({
        "total_read": total_read,
        "by_category": by_category,
        "milestones_reached": milestones_reached,
    })


def _check_admin_key(request) -> bool:
    """Shared-secret check for the one-off /api/admin/* backfill endpoints below - these exist
    so a deployment without shell/SSH access to run cli.py's equivalent commands directly against
    its database can still trigger them over plain HTTP. Unconfigured (no PAPERBITES_ADMIN_KEY)
    means these routes always refuse, rather than defaulting to open."""
    from config import Config
    admin_key = Config().get("api.admin_key")
    if not admin_key:
        return False
    return request.headers.get("x-admin-key") == admin_key


async def admin_backfill_embeddings(request):
    """One-off: compute embeddings for papers already in MongoDB that predate semantic search.
    See paper/embeddings.py's backfill_missing_embeddings - same operation as
    `python cli.py backfill-embeddings`, exposed over HTTP for deployments without shell access
    to run that directly against their database. Requires the X-Admin-Key header to match
    PAPERBITES_ADMIN_KEY."""
    if not _check_admin_key(request):
        return JSONResponse({"detail": "Not found"}, status_code=404)

    from paper.embeddings import backfill_missing_embeddings
    result = await backfill_missing_embeddings()
    return JSONResponse(result)


async def admin_backfill_language(request):
    """One-off: re-check the language of papers already in MongoDB tagged 'en' but never
    translated, using the fixed title-first detection. See paper/latest.py's
    backfill_language_and_translation - same operation as `python cli.py backfill-language`,
    exposed over HTTP for deployments without shell access. Requires the X-Admin-Key header to
    match PAPERBITES_ADMIN_KEY."""
    if not _check_admin_key(request):
        return JSONResponse({"detail": "Not found"}, status_code=404)

    from paper.latest import backfill_language_and_translation
    result = await backfill_language_and_translation()
    return JSONResponse(result)


async def admin_diagnose_language(request):
    """Read-only: for papers still tagged 'en', show exactly what langdetect saw/decided for
    the title alone and for the combined title+abstract, so a paper that still looks wrong after
    backfill-language can be understood instead of guessed at. See paper/latest.py's
    diagnose_language. Requires the X-Admin-Key header to match PAPERBITES_ADMIN_KEY."""
    if not _check_admin_key(request):
        return JSONResponse({"detail": "Not found"}, status_code=404)

    limit = int(request.query_params.get("limit", "50"))
    from paper.latest import diagnose_language
    return JSONResponse(diagnose_language(limit=limit))


async def admin_list_non_english_papers(request):
    """Read-only: every paper currently tagged with a non-English language, showing both its
    translated title and title_original - confirms non-English papers exist and were actually
    translated, without checking documents one by one. See paper/latest.py's
    list_non_english_papers. Requires the X-Admin-Key header to match PAPERBITES_ADMIN_KEY."""
    if not _check_admin_key(request):
        return JSONResponse({"detail": "Not found"}, status_code=404)

    limit = int(request.query_params.get("limit", "50"))
    from paper.latest import list_non_english_papers
    return JSONResponse(list_non_english_papers(limit=limit))


# Papers connect on the bubble map only above this cosine-similarity threshold - high enough that
# an edge means "these are genuinely about similar things," not just "both are academic papers."
_GRAPH_SIMILARITY_THRESHOLD = 0.75


async def get_viewed_papers_graph(request):
    """Build the paper-relationship graph for every paper the current user has clicked "View
    Original Paper" for for the Visualizations tab: nodes are the papers themselves, edges
    connect pairs whose stored embeddings (paper/embeddings.py) are similar enough. Only the
    resulting similarity score is returned per edge - the embedding vectors themselves never
    leave the server, same as everywhere else in the API.
    """
    user_id = get_authenticated_user_id(request)
    if not user_id:
        return JSONResponse({"detail": "Authentication required"}, status_code=401)

    paper_ids = paper_views_store.list_viewed_paper_ids(user_id)
    if not paper_ids:
        return JSONResponse({"nodes": [], "edges": []})

    try:
        import db
        from bson import ObjectId
        from paper.embeddings import cosine_similarity

        object_ids = []
        for pid in paper_ids:
            try:
                object_ids.append(ObjectId(pid))
            except Exception:
                continue

        docs_by_id = {str(doc["_id"]): doc for doc in db.get_db().papers.find({"_id": {"$in": object_ids}})}
    except Exception as e:
        print(f"Error building viewed-papers graph from MongoDB: {e}")
        return JSONResponse({"nodes": [], "edges": []})

    nodes = []
    embeddings_by_id = {}
    for pid in paper_ids:
        doc = docs_by_id.get(pid)
        if not doc:
            continue
        nodes.append({
            "id": pid,
            "title": doc.get("title") or "Untitled",
            "categories": doc.get("categories") or [],
            "journal": doc.get("journal"),
        })
        if doc.get("embedding"):
            embeddings_by_id[pid] = doc["embedding"]

    embedded_ids = list(embeddings_by_id.keys())
    edges = []
    for i in range(len(embedded_ids)):
        for j in range(i + 1, len(embedded_ids)):
            a_id, b_id = embedded_ids[i], embedded_ids[j]
            similarity = cosine_similarity(embeddings_by_id[a_id], embeddings_by_id[b_id])
            if similarity >= _GRAPH_SIMILARITY_THRESHOLD:
                edges.append({"source": a_id, "target": b_id, "similarity": round(similarity, 3)})

    return JSONResponse({"nodes": nodes, "edges": edges})


async def get_author(request):
    """Get an author's name and every paper of theirs in PaperBites."""
    result = get_papers_by_author(request.path_params["author_id"])
    if not result:
        return JSONResponse({"detail": "Author not found"}, status_code=404)
    return JSONResponse(result)


async def get_journal(request):
    """Get every paper published in a given journal/venue."""
    result = get_papers_by_journal(request.path_params["journal_name"])
    if not result:
        return JSONResponse({"detail": "Journal not found"}, status_code=404)
    return JSONResponse(result)


# Mirrors paper.latest.CATEGORIES. Importing that module pulls in its heavy fetch-pipeline
# dependencies (aiohttp, langdetect) just to read a static list - if those aren't installed
# in this deployment, fall back to this copy rather than 500ing on a trivial lookup.
_FALLBACK_CATEGORIES = [
    "Artificial Intelligence", "Medicine", "Physics", "Biology",
    "Psychology", "Climate Science", "Economics", "Neuroscience",
]


async def get_categories(request):
    """Get the fixed list of paper categories used both for fetching and for filtering."""
    try:
        from paper.latest import CATEGORIES
        return JSONResponse(CATEGORIES)
    except ImportError as e:
        print(f"Falling back to hardcoded categories, paper.latest failed to import: {e}")
        return JSONResponse(_FALLBACK_CATEGORIES)


async def search_paper_by_citation(request):
    """Resolve a raw pasted citation (MLA, APA, or any other style) OR a direct link to the
    paper's page (e.g. an open-access journal article URL) into candidate matches for the
    confirm-dialog step of the add-paper-by-citation flow."""
    user_id = get_authenticated_user_id(request)
    if not user_id:
        return JSONResponse({"detail": "Authentication required"}, status_code=401)

    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"detail": "Invalid JSON body"}, status_code=400)

    citation = (body.get("citation") or "").strip()
    if not citation:
        return JSONResponse({"detail": "citation is required"}, status_code=400)

    try:
        from paper.citation import search_citation
    except ImportError as e:
        print(f"Citation search unavailable, paper.citation failed to import: {e}")
        return JSONResponse({"detail": "Citation search is temporarily unavailable"}, status_code=503)

    candidates = await search_citation(citation)
    return JSONResponse({"candidates": candidates})


# Cap the uploaded image at Gemini vision's own reasonable size - mirrors
# paper.summarize._MAX_IMAGE_BYTES so an oversized upload is rejected here (before ever reading
# the whole thing into memory) rather than only after it's already been buffered.
_MAX_SCAN_IMAGE_BYTES = 15 * 1024 * 1024


async def scan_paper_photo(request):
    """Experimental: extract a citation from a photo of a paper's title page or a poster (via
    Gemini vision), then resolve it the same way a pasted citation is. No QR-code decoding - see
    paper.summarize.extract_citation_text_from_image's docstring for why."""
    user_id = get_authenticated_user_id(request)
    if not user_id:
        return JSONResponse({"detail": "Authentication required"}, status_code=401)

    try:
        form = await request.form()
    except Exception:
        return JSONResponse({"detail": "Invalid form data"}, status_code=400)

    image = form.get("image")
    if image is None or not hasattr(image, "read"):
        return JSONResponse({"detail": "image is required"}, status_code=400)

    image_bytes = await image.read()
    if not image_bytes:
        return JSONResponse({"detail": "image is empty"}, status_code=400)
    if len(image_bytes) > _MAX_SCAN_IMAGE_BYTES:
        return JSONResponse({"detail": "image is too large"}, status_code=413)

    try:
        from paper.summarize import extract_citation_text_from_image
        from paper.citation import search_citation
    except ImportError as e:
        print(f"Photo scan unavailable, imports failed: {e}")
        return JSONResponse({"detail": "Scanning is temporarily unavailable"}, status_code=503)

    extracted = await extract_citation_text_from_image(image_bytes, image.content_type or "image/jpeg")
    if not extracted:
        return JSONResponse({"candidates": [], "extracted": None})

    candidates = await search_citation(extracted)
    return JSONResponse({"candidates": candidates, "extracted": extracted})


async def add_paper_by_citation(request):
    """Save the citation-search candidate the user confirmed as a real paper (running it through
    the same enrichment pipeline the discovery feed uses, including a Gemini-chosen category) and
    bookmark it for the current user."""
    user_id = get_authenticated_user_id(request)
    if not user_id:
        return JSONResponse({"detail": "Authentication required"}, status_code=401)

    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"detail": "Invalid JSON body"}, status_code=400)

    candidate = {
        "doi": body.get("doi"),
        "title": body.get("title"),
        "authors": body.get("authors") or [],
        "journal": body.get("journal"),
        "published_date": body.get("published_date"),
        "url": body.get("url"),
        "is_open_access": body.get("is_open_access"),
        "language": body.get("language"),
    }

    try:
        from paper.citation import add_paper_from_citation
    except ImportError as e:
        print(f"Adding papers unavailable, paper.citation failed to import: {e}")
        return JSONResponse({"detail": "Adding papers is temporarily unavailable"}, status_code=503)

    try:
        paper = await add_paper_from_citation(candidate)
    except ValueError as e:
        return JSONResponse({"detail": str(e)}, status_code=400)

    import db
    db.upsert_papers([paper])
    doc = db.get_db().papers.find_one({"source": paper["source"], "source_id": paper["source_id"]})
    saved = _serialize_paper(doc)

    bookmarks_store.add_bookmark(user_id, saved["id"])

    return JSONResponse(saved, status_code=201)


async def submit_paper_review(request):
    """Queue a citation/URL the automated search (above) couldn't match, for manual admin
    review - the spec's fallback for when add-paper matching fails outright."""
    user_id = get_authenticated_user_id(request)
    if not user_id:
        return JSONResponse({"detail": "Authentication required"}, status_code=401)

    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"detail": "Invalid JSON body"}, status_code=400)

    raw_input = (body.get("input") or "").strip()
    if not raw_input:
        return JSONResponse({"detail": "input is required"}, status_code=400)

    entry = paper_reviews_store.submit_review(user_id, raw_input)
    return JSONResponse({"status": "ok", "id": entry["id"]}, status_code=201)


async def list_bookmarked_videos(request):
    """Get full metadata for every paper the current user has bookmarked."""
    user_id = get_authenticated_user_id(request)
    if not user_id:
        return JSONResponse({"detail": "Authentication required"}, status_code=401)

    entries = bookmarks_store.list_bookmarks(user_id)
    saved_at_by_id = {e["video_id"]: e["saved_at"] for e in entries}

    bookmarked = []
    for content_id in saved_at_by_id:
        paper = get_paper_by_id(content_id)
        if paper:
            bookmarked.append(paper)
    bookmarked.sort(key=lambda item: saved_at_by_id[item["id"]], reverse=True)

    return JSONResponse(bookmarked)


async def add_bookmark(request):
    """Bookmark a paper for the current user."""
    user_id = get_authenticated_user_id(request)
    if not user_id:
        return JSONResponse({"detail": "Authentication required"}, status_code=401)

    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"detail": "Invalid JSON body"}, status_code=400)

    video_id = body.get("video_id")
    if not video_id:
        return JSONResponse({"detail": "video_id is required"}, status_code=400)

    if not get_paper_by_id(video_id):
        return JSONResponse({"detail": "Not found"}, status_code=404)

    bookmarks_store.add_bookmark(user_id, video_id)
    return JSONResponse({"status": "ok", "bookmarked": True}, status_code=201)


async def remove_bookmark(request):
    """Remove the current user's bookmark on a paper."""
    user_id = get_authenticated_user_id(request)
    if not user_id:
        return JSONResponse({"detail": "Authentication required"}, status_code=401)

    video_id = request.path_params["video_id"]
    bookmarks_store.remove_bookmark(user_id, video_id)
    return JSONResponse({"status": "ok", "bookmarked": False})


async def signup(request):
    """Create a new account and return a session token."""
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"detail": "Invalid JSON body"}, status_code=400)

    try:
        user = auth.create_user(body.get("email", ""), body.get("password", ""))
    except auth.AuthError as e:
        return JSONResponse({"detail": str(e)}, status_code=400)

    token = auth.create_session(user["id"])
    return JSONResponse({"token": token, "user": user}, status_code=201)


async def login(request):
    """Authenticate and return a session token."""
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"detail": "Invalid JSON body"}, status_code=400)

    try:
        user = auth.authenticate(body.get("email", ""), body.get("password", ""))
    except auth.AuthError as e:
        return JSONResponse({"detail": str(e)}, status_code=401)

    token = auth.create_session(user["id"])
    return JSONResponse({"token": token, "user": user})


async def logout(request):
    """Invalidate the current session token."""
    header = request.headers.get("authorization", "")
    if header.lower().startswith("bearer "):
        auth.delete_session(header[7:].strip())
    return JSONResponse({"status": "ok"})


async def forgot_password(request):
    """Request a password reset code. Always returns the same generic response whether or not
    the email is registered, so this endpoint can't be used to enumerate accounts."""
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"detail": "Invalid JSON body"}, status_code=400)

    email = (body.get("email") or "").strip()
    if email:
        code = auth.create_password_reset_code(email)
        if code:
            email_sender.send_password_reset_code(email, code)

    return JSONResponse({"status": "ok", "detail": "If that email is registered, a reset code has been sent."})


async def reset_password(request):
    """Consume a reset code (from forgot_password above) and set a new password."""
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"detail": "Invalid JSON body"}, status_code=400)

    try:
        auth.reset_password(
            body.get("email", ""),
            body.get("code", ""),
            body.get("new_password", ""),
        )
    except auth.AuthError as e:
        return JSONResponse({"detail": str(e)}, status_code=400)

    return JSONResponse({"status": "ok"})


async def get_me(request):
    """Return the currently authenticated user, if any."""
    user_id = get_authenticated_user_id(request)
    if not user_id:
        return JSONResponse({"detail": "Authentication required"}, status_code=401)

    user = auth.get_user_by_id(user_id)
    if not user:
        return JSONResponse({"detail": "Authentication required"}, status_code=401)

    return JSONResponse({"user": user})


# Define routes
routes = [
    Route("/api/papers", list_papers),
    # Must come before /api/papers/{paper_id} below - otherwise that pattern would match
    # "search" as a paper_id and shadow this route entirely.
    Route("/api/papers/search", search_papers_semantically),
    Route("/api/papers/viewed/graph", get_viewed_papers_graph),
    Route("/api/papers/{paper_id}", get_paper),
    Route("/api/papers/{paper_id}/view", record_paper_view, methods=["POST"]),
    Route("/api/stats/reading", get_reading_stats),
    Route("/api/admin/backfill-embeddings", admin_backfill_embeddings, methods=["POST"]),
    Route("/api/admin/backfill-language", admin_backfill_language, methods=["POST"]),
    Route("/api/admin/diagnose-language", admin_diagnose_language),
    Route("/api/admin/non-english-papers", admin_list_non_english_papers),
    Route("/api/authors/{author_id}", get_author),
    Route("/api/journals/{journal_name}", get_journal),
    Route("/api/categories", get_categories),
    Route("/api/papers/citation/search", search_paper_by_citation, methods=["POST"]),
    Route("/api/papers/citation/scan", scan_paper_photo, methods=["POST"]),
    Route("/api/papers/citation/confirm", add_paper_by_citation, methods=["POST"]),
    Route("/api/papers/citation/review", submit_paper_review, methods=["POST"]),
    Route("/api/interests", get_interests, methods=["GET"]),
    Route("/api/interests", set_interests, methods=["POST"]),
    Route("/api/profile", get_profile, methods=["GET"]),
    Route("/api/profile/tier1", set_profile_tier1, methods=["PUT"]),
    Route("/api/profile/tier2", set_profile_tier2, methods=["PUT"]),
    Route("/api/bookmarks", list_bookmarked_videos, methods=["GET"]),
    Route("/api/bookmarks", add_bookmark, methods=["POST"]),
    Route("/api/bookmarks/{video_id}", remove_bookmark, methods=["DELETE"]),
    Route("/api/auth/signup", signup, methods=["POST"]),
    Route("/api/auth/login", login, methods=["POST"]),
    Route("/api/auth/logout", logout, methods=["POST"]),
    Route("/api/auth/forgot-password", forgot_password, methods=["POST"]),
    Route("/api/auth/reset-password", reset_password, methods=["POST"]),
    Route("/api/auth/me", get_me, methods=["GET"]),
]

# Set up middleware
middleware = [
  Middleware(CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
  ),
  Middleware(RateLimitMiddleware),
]

# Create app
app = Starlette(
    debug=True,
    routes=routes,
    middleware=middleware
)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
