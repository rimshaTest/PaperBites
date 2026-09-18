# cli.py
import argparse
import asyncio
import logging
import os
from typing import Dict, List, Optional
import time
import uuid
import json
import re

from config import Config
from utils.logging import setup_logging
from paper.latest import get_latest_papers, CATEGORIES
from db import upsert_papers

# The video-generation pipeline (PyMuPDF, pytesseract, moviepy, cloudinary, arxiv, scholarly)
# pulls in heavy/optional dependencies that aren't needed for the fetch-latest command, so
# those modules are imported lazily inside the functions that actually use them.


def sanitize_filename(title):
    """Replace invalid filename characters with underscores."""
    pattern = r'[^\w\-_]'
    return re.sub(pattern, '_', title)

async def process_paper(paper_info: Dict, output_dir: str, config: Config) -> Optional[Dict]:
    """
    Process a paper and upload video to cloudinary.
    
    Args:
        paper_info: Information about the paper (title, url, etc.)
        output_dir: Directory for output files
        config: Application configuration
        
    Returns:
        dict: Video metadata or None if failed
    """
    from paper.download import download_paper
    from paper.extraction import extract_text_from_pdf, extract_paper_sections
    from paper.summarize import summarize_paper
    from video.compose import VideoGenerator
    from video.visual import rate_limit
    from utils.cloudinary_storage import CloudinaryStorage

    logger = logging.getLogger("paperbites.cli")
    logger.info(f"Processing paper: {paper_info['title']}")

    # Check if API rate limit is exceeded
    if rate_limit.check():
        logger.error("Skipping paper due to API rate limit")
        return None

    # Create filename from title
    pdf_filename = os.path.join(
        config.get("paths.temp_dir"),
        sanitize_filename(paper_info["title"]) + ".pdf",
    )

    # Download PDF
    pdf_path = await download_paper(paper_info, pdf_filename)
    
    if not pdf_path:
        logger.error(f"Failed to download paper")
        return None
        
    # Extract text
    logger.info(f"Extracting text from PDF...")
    full_text = extract_text_from_pdf(
        pdf_path,
        use_ocr=True
    )
    
    if not full_text:
        logger.error(f"Failed to extract text from PDF")
        os.remove(pdf_filename)
        return None
        
    # Extract sections and summarize
    sections = extract_paper_sections(full_text)
    summary = summarize_paper(sections)
    
    # Add title to summary
    summary["title"] = paper_info["title"]
    
    # Generate video
    logger.info(f"Generating video...")
    video_generator = VideoGenerator(
        temp_dir=config.get("paths.temp_dir"),
        default_size=(
            config.get("video.formats.tiktok.width"),
            config.get("video.formats.tiktok.height")
        )
    )
    
    # Create output filename
    output_file = os.path.join(
        output_dir,
        sanitize_filename(paper_info["title"]) + ".mp4"
    )
    
    # Decide whether to use stock videos based on config
    use_stock_videos = config.get("video.use_stock_videos", True)
    
    video_path = video_generator.generate_video(
        summary,
        output_file=output_file,
        fps=config.get("video.fps", 30),
        use_stock_videos=use_stock_videos
    )
    
    if not video_path:
        logger.error("Failed to generate video")
        if os.path.exists(pdf_filename):
            os.remove(pdf_filename)
        return None
    
    logger.info(f"Uploading video to Cloudinary...")
    try:
        # Initialize cloudinary storage
        video_url = CloudinaryStorage().upload_video(video_path)
        
        if not video_url:
            logger.error("Failed to upload video to Cloudinary")
            # Continue with local file if upload fails
            video_url = f"file://{video_path}"
        
        logger.info(f"Video uploaded to Cloudinary: {video_url}")
            
    except Exception as e:
        logger.error(f"Error uploading to Cloudinary: {e}")
        # Continue with local file if upload fails
        video_url = f"file://{video_path}"
    
    # Create video metadata
    metadata = {
        "id": str(uuid.uuid4()),
        "title": summary["title"],
        "videoUrl": video_url,
        "summary": summary.get("summary", ""),
        "keywords": summary.get("keywords", []),
        "hashtags": summary.get("hashtags", ""),
        "key_insights": summary.get("key_insights", []),
        "paper_id": paper_info.get("id", ""),
        "url": paper_info.get("url", ""),
        "license": paper_info.get("license", ""),
        "authors": paper_info.get("authors", []),
        "timestamp": int(time.time()),
        "can_display_publicly": paper_info.get("can_display_publicly", False)
    }
    
    # Save metadata to a local JSON file
    metadata_file = os.path.join(
        output_dir,
        sanitize_filename(paper_info["title"]) + "_metadata.json"
    )
    
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)
        
    logger.info(f"Video metadata saved to {metadata_file}")
    
    # Clean up
    if os.path.exists(pdf_filename):
        os.remove(pdf_filename)
        
    return metadata

async def process_pdf(pdf_path: str, output_dir: str, config: Config) -> Optional[Dict]:
    """
    Process a local PDF file and upload video to cloudinary.
    
    Args:
        pdf_path: Path to PDF file
        output_dir: Directory for output files
        config: Application configuration
        
    Returns:
        dict: Video metadata or None if failed
    """
    logger = logging.getLogger("paperbites.cli")
    logger.info(f"Processing PDF: {pdf_path}")
    
    # Extract filename as title
    title = os.path.basename(pdf_path).replace(".pdf", "").replace("_", " ")
    
    # Create a paper_info dict
    paper_info = {
        "title": title,
        "url": f"file://{pdf_path}",
        "license": "unknown",  # Assume unknown license for local files
        "can_display_publicly": False  # Assume local PDFs aren't for public display
    }
    
    # Process similar to process_paper
    return await process_paper(paper_info, output_dir, config)

async def process_query(query: str, num_papers: int, output_dir: str, config: Config, public_only: bool = True, continue_on_error: bool = True) -> List[Dict]:
    """
    Search for papers and process them.
    
    Args:
        query: Search query
        num_papers: Number of papers to process
        output_dir: Directory for output files
        config: Application configuration
        public_only: Whether to only process papers that can be displayed publicly
        continue_on_error: Whether to continue processing other papers when one fails
        
    Returns:
        List[Dict]: List of video metadata
    """
    from paper.search import search_papers
    from video.visual import rate_limit

    logger = logging.getLogger("paperbites.cli")
    logger.info(f"Searching for papers: {query}")

    # Search for papers
    papers = await search_papers(
        query,
        max_papers=num_papers,
        open_access_only=config.get("paper_search.open_access_only", True),
        public_only=public_only
    )
    
    logger.info(f"Found {len(papers)} papers")
    
    if not papers:
        logger.warning(f"No papers found for query: {query}")
        return []
    
    # Process each paper
    videos = []
    for paper in papers:
        try:
            # Check if API rate limit is exceeded
            if rate_limit.check():
                logger.error("Stopping due to API rate limit")
                break
                
            metadata = await process_paper(paper, output_dir, config)
            if metadata:
                videos.append(metadata)
            elif not continue_on_error:
                logger.warning("Stopping paper processing due to failure")
                break
        except Exception as e:
            logger.error(f"Error processing paper: {e}")
            if not continue_on_error:
                logger.warning("Stopping paper processing due to exception")
                break
            
    return videos

async def process_id(paper_id: str, output_dir: str, config: Config) -> Optional[Dict]:
    """
    Process a paper by ID (arXiv ID, DOI, etc.).
    
    Args:
        paper_id: ID of the paper
        output_dir: Directory for output files
        config: Application configuration
        
    Returns:
        dict: Video metadata or None if failed
    """
    from paper.download import get_paper_by_id

    logger = logging.getLogger("paperbites.cli")
    logger.info(f"Processing paper with ID: {paper_id}")

    # Get paper information
    paper_info = await get_paper_by_id(paper_id)
    
    if not paper_info:
        logger.error(f"Could not find paper with ID: {paper_id}")
        return None
    
    return await process_paper(paper_info, output_dir, config)

async def fetch_latest_command(category: Optional[str], days: int, limit: int, sort_by: str = "date") -> int:
    """Fetch papers for one or all known categories and upsert them into MongoDB."""
    logger = logging.getLogger("paperbites.cli")
    categories = [category] if category else CATEGORIES
    total = 0

    for cat in categories:
        papers = await get_latest_papers(cat, days_back=days, limit=limit, sort_by=sort_by)
        written = upsert_papers(papers)
        total += written
        logger.info(f"'{cat}': fetched {len(papers)} papers, upserted {written}")

    return total


def main():
    """Main entry point for the CLI application."""
    # Set up argument parser
    parser = argparse.ArgumentParser(description="Convert research papers to TikTok videos")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Search command
    search_parser = subparsers.add_parser("search", help="Search for papers and convert them")
    search_parser.add_argument("query", help="Search query")
    search_parser.add_argument("--papers", "-p", help="Number of papers to process", type=int, default=1)
    search_parser.add_argument("--public-only", help="Only include papers that can be publicly displayed", 
                             action="store_true", default=True)
    search_parser.add_argument("--stop-on-error", help="Stop processing if any paper fails", 
                             action="store_true", default=False)
    search_parser.add_argument("--no-stock-videos", help="Don't use stock videos, only gradients", 
                             action="store_true", default=False)
    
    # ID command (replaces DOI command, works with arXiv IDs, DOIs, etc.)
    id_parser = subparsers.add_parser("id", help="Convert a paper by ID (arXiv ID, DOI, etc.)")
    id_parser.add_argument("id", help="ID of the paper")
    id_parser.add_argument("--no-stock-videos", help="Don't use stock videos, only gradients", 
                          action="store_true", default=False)
    
    # PDF command
    pdf_parser = subparsers.add_parser("pdf", help="Convert a local PDF paper")
    pdf_parser.add_argument("file", help="Path to PDF file")
    pdf_parser.add_argument("--no-stock-videos", help="Don't use stock videos, only gradients", 
                          action="store_true", default=False)
    
    # Fetch-latest command
    fetch_parser = subparsers.add_parser("fetch-latest", help="Fetch latest papers from free APIs into MongoDB")
    fetch_parser.add_argument("--category", help="Single category to fetch (default: all known categories)", default=None)
    fetch_parser.add_argument("--days", help="How many days back to look", type=int, default=7)
    fetch_parser.add_argument("--limit", help="Max papers per category per source", type=int, default=20)
    fetch_parser.add_argument(
        "--sort-by", help="'date' for the latest papers, 'citations' for the most-cited in the window",
        choices=["date", "citations"], default="date",
    )
    fetch_parser.add_argument("--config", "-c", help="Path to config file", default="config.json")

    # Common arguments
    for subparser in [search_parser, id_parser, pdf_parser]:
        subparser.add_argument("--config", "-c", help="Path to config file", default="config.json")
        subparser.add_argument("--output-dir", "-o", help="Output directory", default="videos")
        subparser.add_argument("--format", "-f", help="Video format (tiktok, instagram, youtube)", default="tiktok")
    
    # Parse arguments
    args = parser.parse_args()
    
    # Setup
    logger = setup_logging()
    config = Config(args.config)
    
    # Create necessary directories (not used by every command, e.g. fetch-latest)
    if hasattr(args, "output_dir"):
        os.makedirs(config.get("paths.temp_dir"), exist_ok=True)
        os.makedirs(args.output_dir, exist_ok=True)
    
    # Update config for stock videos
    if hasattr(args, 'no_stock_videos') and args.no_stock_videos:
        config.set("video.use_stock_videos", False)
    else:
        config.set("video.use_stock_videos", True)
    
    # Run command
    async def run():
        if args.command == "search":
            videos = await process_query(
                args.query, 
                args.papers, 
                args.output_dir, 
                config,
                public_only=args.public_only,
                continue_on_error=not args.stop_on_error
            )
            logger.info(f"Generated {len(videos)} videos")
            for video in videos:
                logger.info(f"  - {video['videoUrl']}")
        elif args.command == "id":
            metadata = await process_id(args.id, args.output_dir, config)
            if metadata:
                logger.info(f"Generated video: {metadata['videoUrl']}")
            else:
                logger.error("Failed to generate video")
        elif args.command == "pdf":
            metadata = await process_pdf(args.file, args.output_dir, config)
            if metadata:
                logger.info(f"Generated video: {metadata['videoUrl']}")
            else:
                logger.error("Failed to generate video")
        elif args.command == "fetch-latest":
            total = await fetch_latest_command(args.category, args.days, args.limit, sort_by=args.sort_by)
            logger.info(f"Upserted {total} papers total")
        else:
            parser.print_help()
    
    # Run the async event loop
    asyncio.run(run())

if __name__ == "__main__":
    main()