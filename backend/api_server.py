from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
import uvicorn
import os
from typing import List, Dict, Optional

import bookmarks as bookmarks_store
import interests as interests_store
import auth


def _serialize_paper(doc: Dict) -> Dict:
    """Convert a MongoDB paper document into a JSON-safe dict with a plain string id."""
    doc = dict(doc)
    doc["id"] = str(doc.pop("_id"))
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


async def list_papers(request):
    """Get a list of papers, fetched via `cli.py fetch-latest` (no video generation).

    When the request is authenticated and the user has chosen interests, the feed is hard-filtered
    to only papers whose categories intersect those interests - a simpler stand-in for the
    embedding-based ranking described as future work in the technical spec. A user with no
    interests set (skipped onboarding, or hasn't visited Interests yet) sees everything,
    unfiltered.
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

    return JSONResponse(papers[offset:offset + limit])


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


async def get_paper(request):
    """Get a single paper by id."""
    paper = get_paper_by_id(request.path_params["paper_id"])
    if not paper:
        return JSONResponse({"detail": "Paper not found"}, status_code=404)
    return JSONResponse(paper)


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
    Route("/api/papers/{paper_id}", get_paper),
    Route("/api/authors/{author_id}", get_author),
    Route("/api/journals/{journal_name}", get_journal),
    Route("/api/categories", get_categories),
    Route("/api/interests", get_interests, methods=["GET"]),
    Route("/api/interests", set_interests, methods=["POST"]),
    Route("/api/bookmarks", list_bookmarked_videos, methods=["GET"]),
    Route("/api/bookmarks", add_bookmark, methods=["POST"]),
    Route("/api/bookmarks/{video_id}", remove_bookmark, methods=["DELETE"]),
    Route("/api/auth/signup", signup, methods=["POST"]),
    Route("/api/auth/login", login, methods=["POST"]),
    Route("/api/auth/logout", logout, methods=["POST"]),
    Route("/api/auth/me", get_me, methods=["GET"]),
]

# Set up middleware
middleware = [
  Middleware(CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
  )
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
