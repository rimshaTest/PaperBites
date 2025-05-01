from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
import os
import json
import glob
from typing import List, Dict, Optional
import uvicorn
import asyncio
from paper.search import search_papers
from paper.download import get_paper_by_id
from pydantic import BaseModel

app = FastAPI(title="PaperBites API", description="API for serving research paper videos")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development - restrict this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Directory where video metadata is stored
VIDEOS_DIR = os.environ.get("PAPERBITES_VIDEOS_DIR", "videos")

def get_all_videos() -> List[Dict]:
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

class PaperInfo(BaseModel):
    """Model for paper information."""
    id: Optional[str] = None
    title: str
    url: str
    authors: List[str] = []
    summary: Optional[str] = None
    license: Optional[str] = None
    can_display_publicly: bool = False

@app.get("/api/videos", response_model=List[Dict])
async def list_videos(
    limit: int = Query(50, gt=0, le=100),
    offset: int = Query(0, ge=0),
    keyword: Optional[str] = None,
    public_only: bool = Query(True, description="Only include videos that can be publicly displayed")
):
    """
    Get a list of videos with optional filtering.
    
    Args:
        limit: Maximum number of videos to return
        offset: Pagination offset
        keyword: Filter by keyword
        public_only: Only include videos that can be publicly displayed
    """
    videos = get_all_videos()
    
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
    
    return paginated_videos

@app.get("/api/videos/{video_id}", response_model=Dict)
async def get_video(video_id: str):
    """
    Get metadata for a specific video.
    
    Args:
        video_id: ID of the video
    """
    videos = get_all_videos()
    
    for video in videos:
        if video.get("id") == video_id:
            return video
    
    raise HTTPException(status_code=404, detail="Video not found")

@app.get("/api/topics", response_model=List[str])
async def get_topics():
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
    
    return popular_keywords

@app.get("/api/search", response_model=List[PaperInfo])
async def search_api(
    query: str,
    max_results: int = Query(10, gt=0, le=50),
    public_only: bool = Query(True, description="Only include papers that can be publicly displayed")
):
    """
    Search for papers from various sources.
    
    Args:
        query: Search query
        max_results: Maximum number of results to return
        public_only: Only include papers that can be publicly displayed
    """
    papers = await search_papers(
        query=query,
        max_papers=max_results,
        open_access_only=True,
        public_only=public_only
    )
    
    # Convert to response model format
    result = []
    for paper in papers:
        paper_info = PaperInfo(
            id=paper.get("id", None),
            title=paper.get("title", "Unknown Title"),
            url=paper.get("url", ""),
            authors=paper.get("authors", []),
            summary=paper.get("summary", None),
            license=paper.get("license", None),
            can_display_publicly=paper.get("can_display_publicly", False)
        )
        result.append(paper_info)
    
    return result

@app.get("/api/paper/{paper_id}", response_model=PaperInfo)
async def get_paper(paper_id: str):
    """
    Get information about a specific paper.
    
    Args:
        paper_id: ID of the paper (DOI, arXiv ID, etc.)
    """
    paper = await get_paper_by_id(paper_id)
    
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    
    return PaperInfo(
        id=paper.get("id", None),
        title=paper.get("title", "Unknown Title"),
        url=paper.get("url", ""),
        authors=paper.get("authors", []),
        summary=paper.get("summary", None),
        license=paper.get("license", None),
        can_display_publicly=paper.get("can_display_publicly", False)
    )

if __name__ == "__main__":
    # Make sure the videos directory exists
    os.makedirs(VIDEOS_DIR, exist_ok=True)
    
    # Start the server
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)