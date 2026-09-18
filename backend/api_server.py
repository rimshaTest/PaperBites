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

import bookmarks as bookmarks_store
import auth

# Directory where video metadata is stored
VIDEOS_DIR = os.environ.get("PAPERBITES_VIDEOS_DIR", "videos")


def get_authenticated_user_id(request) -> Optional[str]:
    """Resolve the requesting user from an 'Authorization: Bearer <token>' header."""
    header = request.headers.get("authorization", "")
    if not header.lower().startswith("bearer "):
        return None
    token = header[7:].strip()
    return auth.get_user_id_for_token(token)

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

async def list_bookmarked_videos(request):
    """Get full metadata for every video the current user has bookmarked."""
    user_id = get_authenticated_user_id(request)
    if not user_id:
        return JSONResponse({"detail": "Authentication required"}, status_code=401)

    entries = bookmarks_store.list_bookmarks(user_id)
    saved_at_by_id = {e["video_id"]: e["saved_at"] for e in entries}

    videos_by_id = {v["id"]: v for v in get_all_videos()}
    bookmarked_videos = [videos_by_id[vid] for vid in saved_at_by_id if vid in videos_by_id]
    bookmarked_videos.sort(key=lambda v: saved_at_by_id[v["id"]], reverse=True)

    return JSONResponse(bookmarked_videos)


async def add_bookmark(request):
    """Bookmark a video for the current user."""
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

    if not any(v.get("id") == video_id for v in get_all_videos()):
        return JSONResponse({"detail": "Video not found"}, status_code=404)

    bookmarks_store.add_bookmark(user_id, video_id)
    return JSONResponse({"status": "ok", "bookmarked": True}, status_code=201)


async def remove_bookmark(request):
    """Remove the current user's bookmark on a video."""
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
    Route("/api/videos", list_videos),
    Route("/api/videos/{video_id}", get_video),
    Route("/api/topics", get_topics),
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
    # Make sure the videos directory exists
    os.makedirs(VIDEOS_DIR, exist_ok=True)
    
    # Start the server
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)