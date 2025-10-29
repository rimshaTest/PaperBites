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

# Define routes
routes = [
    Route("/api/videos", list_videos),
    Route("/api/videos/{video_id}", get_video),
    Route("/api/topics", get_topics),
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