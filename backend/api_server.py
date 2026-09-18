from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
import uvicorn
import os
import json
import glob
from typing import List, Dict, Optional
from starlette.requests import Request
from bson import ObjectId
from bson.errors import InvalidId

from db import get_db
from paper.latest import CATEGORIES
from paper.chat import ask_about_paper
from paper.resolve import resolve_paper

# Directory where video metadata is stored
VIDEOS_DIR = os.environ.get("PAPERBITES_VIDEOS_DIR", "videos")

def get_all_videos():
    """Get metadata for all videos."""
    videos = []
    
    # Find all JSON metadata files
    metadata_files = glob.glob(os.path.join(VIDEOS_DIR, "*.json"))
    
    for metadata_file in metadata_files:
        try:
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
                # Only include videos that can be publicly displayed
                if metadata.get("can_display_publicly", False):
                    videos.append(metadata)
        except Exception as e:
            print(f"Error reading metadata from {metadata_file}: {e}")
    
    # Sort by timestamp (newest first)
    videos.sort(key=lambda x: x.get("timestamp", 0), reverse=True)
    
    return videos

async def list_videos(request):
    """Get a list of videos with optional filtering."""
    videos = get_all_videos()
    
    # Get query parameters
    limit = int(request.query_params.get("limit", "50"))
    offset = int(request.query_params.get("offset", "0"))
    keyword = request.query_params.get("keyword")
    public_only = request.query_params.get("public_only", "True").lower() == "true"
    
    # Filter by public display permissions
    if public_only:
        videos = [v for v in videos if v.get("can_display_publicly", False)]
    
    # Filter by keyword if provided
    if keyword:
        keyword = keyword.lower()
        filtered_videos = []
        
        for video in videos:
            # Check title
            if keyword in video.get("title", "").lower():
                filtered_videos.append(video)
                continue
                
            # Check keywords
            video_keywords = [k.lower() for k in video.get("keywords", [])]
            if any(keyword in k for k in video_keywords):
                filtered_videos.append(video)
                continue
                
            # Check summary
            if keyword in video.get("summary", "").lower():
                filtered_videos.append(video)
                continue
        
        videos = filtered_videos
    
    # Apply pagination
    paginated_videos = videos[offset:offset + limit]
    
    return JSONResponse(paginated_videos)

async def get_video(request):
    """Get metadata for a specific video."""
    video_id = request.path_params["video_id"]
    videos = get_all_videos()
    
    for video in videos:
        if video.get("id") == video_id:
            return JSONResponse(video)
    
    return JSONResponse({"detail": "Video not found"}, status_code=404)

async def get_topics(request):
    """Get a list of all topics/keywords across videos."""
    videos = get_all_videos()
    
    # Extract all keywords from videos
    all_keywords = []
    for video in videos:
        all_keywords.extend(video.get("keywords", []))
    
    # Count occurrences of each keyword
    from collections import Counter
    keyword_counts = Counter(all_keywords)
    
    # Return keywords with at least 2 occurrences, sorted by frequency
    popular_keywords = [kw for kw, count in keyword_counts.most_common() if count >= 2]
    
    return JSONResponse(popular_keywords)

def serialize_paper(paper: Dict) -> Dict:
    """Shape a stored paper document into the card format the frontend expects.

    Description is a <=200 word Gemini-generated plain-English summary of the paper (see
    paper/summarize.py), not the raw abstract - academic abstracts are dense and, for survey
    papers especially, long enough to feel cramped even with unlimited scroll room. Falls back to
    the raw abstract if summarization wasn't available when the paper was fetched.
    `relevance` is always "N/A" for now: there is no account system or profile-attribute
    collection built yet, so there is no real user info to personalize against.
    """
    categories = paper.get("categories") or []
    description = (paper.get("description") or paper.get("abstract") or "").strip()
    if not description:
        description = "No description available yet."

    return {
        "id": str(paper["_id"]),
        "title": paper.get("title", "Untitled"),
        "authors": paper.get("authors", []),
        "description": description,
        "citation_count": paper.get("citation_count", 0),
        "published_date": paper.get("published_date"),
        "journal": paper.get("journal"),
        "publication_type": paper.get("publication_type"),
        "is_open_access": paper.get("is_open_access"),
        "language": paper.get("language", "en"),
        "image_url": paper.get("image_url"),
        "url": paper.get("url"),
        "doi": paper.get("doi"),
        "category": categories[0] if categories else None,
        "relevance": "N/A",
    }


async def get_categories(request):
    """Get the fixed list of categories papers are fetched for."""
    return JSONResponse(CATEGORIES)


async def list_papers(request):
    """Get a list of latest papers, newest first, optionally filtered by category."""
    limit = int(request.query_params.get("limit", "20"))
    offset = int(request.query_params.get("offset", "0"))
    category = request.query_params.get("category")

    db = get_db()
    query = {"categories": category} if category else {}
    cursor = db.papers.find(query).sort("published_date", -1).skip(offset).limit(limit)

    papers =  JSONResponse([serialize_paper(paper) for paper in cursor])
    return papers

async def resolve_saved_paper(request):
    """Resolve a citation string or paper link/DOI into a full paper record and upsert it.

    Backs the "Saved" tab's add-by-citation-or-link flow. Returns the same serialized shape as
    GET /api/papers/{id} so the frontend can save its id locally right away. Route must be
    registered before /api/papers/{paper_id} - otherwise Starlette would match "resolve" as a
    paper_id there instead.
    """
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"detail": "Invalid JSON body"}, status_code=400)

    query = (body.get("query") or "").strip()
    if not query:
        return JSONResponse({"detail": "'query' is required"}, status_code=400)

    paper = await resolve_paper(query)
    if not paper:
        return JSONResponse(
            {"detail": "Could not find a paper matching that citation or link"}, status_code=404
        )

    db = get_db()
    db.papers.update_one(
        {"source": paper["source"], "source_id": paper["source_id"]},
        {"$set": paper},
        upsert=True,
    )
    stored = db.papers.find_one({"source": paper["source"], "source_id": paper["source_id"]})
    return JSONResponse(serialize_paper(stored))


async def get_paper(request):
    """Get a single paper by id."""
    paper_id = request.path_params["paper_id"]

    try:
        object_id = ObjectId(paper_id)
    except InvalidId:
        return JSONResponse({"detail": "Paper not found"}, status_code=404)

    db = get_db()
    paper = db.papers.find_one({"_id": object_id})

    if not paper:
        return JSONResponse({"detail": "Paper not found"}, status_code=404)

    return JSONResponse(serialize_paper(paper))


async def chat_about_paper(request):
    """Answer a question about a specific paper using the Gemini-backed chat agent.

    Body: {"question": str, "history": [{"role": "user"|"assistant", "content": str}, ...]}.
    History is optional and is entirely client-supplied - there is no server-side conversation
    state, so the client must resend prior turns to keep context across a multi-turn chat.
    """
    paper_id = request.path_params["paper_id"]

    try:
        object_id = ObjectId(paper_id)
    except InvalidId:
        return JSONResponse({"detail": "Paper not found"}, status_code=404)

    db = get_db()
    paper = db.papers.find_one({"_id": object_id})
    if not paper:
        return JSONResponse({"detail": "Paper not found"}, status_code=404)

    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"detail": "Invalid JSON body"}, status_code=400)

    question = (body.get("question") or "").strip()
    if not question:
        return JSONResponse({"detail": "'question' is required"}, status_code=400)
    history = body.get("history") or []

    answer = await ask_about_paper(paper, history, question)
    if answer is None:
        return JSONResponse({"detail": "Chat is not available right now"}, status_code=503)

    return JSONResponse({"answer": answer})


async def get_author(request):
    """Get an author's name and all of their papers currently in the database."""
    author_id = request.path_params["author_id"]

    db = get_db()
    papers = list(db.papers.find({"authors.id": author_id}).sort("published_date", -1))

    if not papers:
        return JSONResponse({"detail": "Author not found"}, status_code=404)

    name = None
    for paper in papers:
        for author in paper.get("authors", []):
            if author.get("id") == author_id:
                name = author.get("name")
                break
        if name:
            break

    return JSONResponse({
        "id": author_id,
        "name": name,
        "papers": [serialize_paper(paper) for paper in papers],
    })


async def get_journal(request):
    """Get all papers published in a given journal/conference (matched by exact name)."""
    journal_name = request.path_params["journal_name"]

    db = get_db()
    papers = list(db.papers.find({"journal": journal_name}).sort("published_date", -1))

    if not papers:
        return JSONResponse({"detail": "Journal not found"}, status_code=404)

    return JSONResponse({
        "name": journal_name,
        "papers": [serialize_paper(paper) for paper in papers],
    })


# Define routes
routes = [
    Route("/api/videos", list_videos),
    Route("/api/videos/{video_id}", get_video),
    Route("/api/topics", get_topics),
    Route("/api/categories", get_categories),
    Route("/api/papers", list_papers),
    Route("/api/papers/resolve", resolve_saved_paper, methods=["POST"]),
    Route("/api/papers/{paper_id}", get_paper),
    Route("/api/papers/{paper_id}/chat", chat_about_paper, methods=["POST"]),
    Route("/api/authors/{author_id}", get_author),
    Route("/api/journals/{journal_name}", get_journal),
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
    # Make sure the videos directory exists
    os.makedirs(VIDEOS_DIR, exist_ok=True)
    
    # Start the server
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)