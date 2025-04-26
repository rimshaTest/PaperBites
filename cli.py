# cli.py
import argparse
import asyncio
import logging
import os
from typing import Dict, List, Optional

from config import Config
from utils.logging import setup_logging
from paper.search import search_papers
from paper.download import download_paper
from paper.extraction import extract_text_from_pdf, extract_paper_sections
from paper.summarize import summarize_paper
from video.compose import VideoGenerator

async def process_doi(doi: str, output_dir: str, config: Config) -> Optional[str]:
    """
    Process a paper by DOI.
    
    Args:
        doi: DOI of the paper
        output_dir: Directory for output files
        config: Application configuration
        
    Returns:
        str: Path to generated video or None if failed
    """
    logger = logging.getLogger("paperbites.cli")
    logger.info(f"Processing DOI: {doi}")
    
    # Download paper
    from paper.download import get_open_access_paper, download_paper
    import aiohttp
    
    async with aiohttp.ClientSession() as session:
        paper_info = await get_open_access_paper(session, doi)
        if not paper_info:
            logger.error(f"Could not find open access version of {doi}")
            return None
            
        # Create filename from title
        import re
        pdf_filename = os.path.join(
            config.get("paths.temp_dir"),
            f"{re.sub(r'[^\w\-_]', '_', paper_info['title'])}.pdf"
        )
        
        # Download PDF
        if not await download_paper(session, paper_info['url'], pdf_filename):
            logger.error(f"Failed to download paper")
            return None
            
        # Extract text
        logger.info(f"Extracting text from PDF...")
        full_text = extract_text_from_pdf(
            pdf_filename,
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
            f"{re.sub(r'[^\w\-_]', '_', paper_info['title'])}.mp4"
        )
        
        video_path = video_generator.generate_video(
            summary,
            output_file=output_file,
            fps=config.get("video.fps", 30)
        )
        
        # Clean up
        if os.path.exists(pdf_filename):
            os.remove(pdf_filename)
            
        return video_path

async def process_pdf(pdf_path: str, output_dir: str, config: Config) -> Optional[str]:
    """
    Process a local PDF file.
    
    Args:
        pdf_path: Path to PDF file
        output_dir: Directory for output files
        config: Application configuration
        
    Returns:
        str: Path to generated video or None if failed
    """
    logger = logging.getLogger("paperbites.cli")
    logger.info(f"Processing PDF: {pdf_path}")
    
    # Extract filename as title
    import os
    title = os.path.basename(pdf_path).replace(".pdf", "").replace("_", " ")
    
    # Extract text
    logger.info(f"Extracting text from PDF...")
    full_text = extract_text_from_pdf(
        pdf_path,
        use_ocr=True
    )
    
    if not full_text:
        logger.error(f"Failed to extract text from PDF")
        return None
        
    # Extract sections and summarize
    sections = extract_paper_sections(full_text)
    summary = summarize_paper(sections)
    
    # Add title to summary
    summary["title"] = title
    
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
    import re
    output_file = os.path.join(
        output_dir,
        f"{re.sub(r'[^\w\-_]', '_', title)}.mp4"
    )
    
    video_path = video_generator.generate_video(
        summary,
        output_file=output_file,
        fps=config.get("video.fps", 30)
    )
    
    return video_path

async def process_query(query: str, num_papers: int, output_dir: str, config: Config) -> List[str]:
    """
    Search for papers and process them.
    
    Args:
        query: Search query
        num_papers: Number of papers to process
        output_dir: Directory for output files
        config: Application configuration
        
    Returns:
        List[str]: Paths to generated videos
    """
    logger = logging.getLogger("paperbites.cli")
    logger.info(f"Searching for papers: {query}")
    
    # Search for papers
    papers = await search_papers(
        query,
        max_papers=num_papers,
        open_access_only=config.get("paper_search.open_access_only", True)
    )
    
    logger.info(f"Found {len(papers)} papers")
    
    # Process each paper
    videos = []
    for paper in papers:
        video_path = await process_doi(paper["doi"], output_dir, config)
        if video_path:
            videos.append(video_path)
            
    return videos

def main():
    """Main entry point for the CLI application."""
    # Set up argument parser
    parser = argparse.ArgumentParser(description="Convert research papers to TikTok videos")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Search command
    search_parser = subparsers.add_parser("search", help="Search for papers and convert them")
    search_parser.add_argument("query", help="Search query")
    search_parser.add_argument("--papers", "-p", help="Number of papers to process", type=int, default=1)
    
    # DOI command
    doi_parser = subparsers.add_parser("doi", help="Convert a paper by DOI")
    doi_parser.add_argument("doi", help="DOI of the paper")
    
    # PDF command
    pdf_parser = subparsers.add_parser("pdf", help="Convert a local PDF paper")
    pdf_parser.add_argument("file", help="Path to PDF file")
    
    # Common arguments
    for subparser in [search_parser, doi_parser, pdf_parser]:
        subparser.add_argument("--config", "-c", help="Path to config file", default="config.json")
        subparser.add_argument("--output-dir", "-o", help="Output directory", default="videos")
        subparser.add_argument("--format", "-f", help="Video format (tiktok, instagram, youtube)", default="tiktok")
    
    # Parse arguments
    args = parser.parse_args()
    
    # Setup
    logger = setup_logging()
    config = Config(args.config)
    
    # Create necessary directories
    os.makedirs(config.get("paths.temp_dir"), exist_ok=True)
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Run command
    async def run():
        if args.command == "search":
            videos = await process_query(args.query, args.papers, args.output_dir, config)
            logger.info(f"Generated {len(videos)} videos")
            for video in videos:
                logger.info(f"  - {video}")
        elif args.command == "doi":
            video = await process_doi(args.doi, args.output_dir, config)
            if video:
                logger.info(f"Generated video: {video}")
            else:
                logger.error("Failed to generate video")
        elif args.command == "pdf":
            video = await process_pdf(args.file, args.output_dir, config)
            if video:
                logger.info(f"Generated video: {video}")
            else:
                logger.error("Failed to generate video")
        else:
            parser.print_help()
    
    # Run the async event loop
    asyncio.run(run())

if __name__ == "__main__":
    main()