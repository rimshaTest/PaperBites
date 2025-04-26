# paper/search.py
import logging
import asyncio
import aiohttp
from scholarly import scholarly
from typing import List, Dict, Optional
import re
from config import Config

from utils.network import resilient_fetch

config_instance = Config()

logger = logging.getLogger("paperbites.search")

def extract_doi(pub_url: str) -> Optional[str]:
    """
    Extract DOI from a publication URL using regex.
    
    Args:
        pub_url: Publication URL
        
    Returns:
        str: Extracted DOI or None if not found
    """
    doi_match = re.search(r"10\.\d{4,9}/[-._;()/:A-Za-z0-9]+", pub_url)
    return doi_match.group(0) if doi_match else None

async def get_open_access_paper(session: aiohttp.ClientSession, doi: str) -> Optional[Dict]:
    """
    Check if a paper has a free full-text version allowing commercial use.
    
    Args:
        session: aiohttp ClientSession
        doi: DOI of the paper
        
    Returns:
        dict: Paper information or None if not open access
    """
    # Required for Unpaywall API
    email = config_instance.get("api.email")
    
    url = f"https://api.unpaywall.org/v2/{doi}?email={email}"
    
    try:
        data = await resilient_fetch(session, url)
        if not data or data.get("error"):
            return None

        oa_location = data.get("best_oa_location")
        if not oa_location:
            return None

        license_type = oa_location.get("license", "")
        if license_type and ("cc-by" in license_type.lower() or "cc0" in license_type.lower()):
            return {
                "title": data.get("title", "Unknown Title"),
                "doi": doi,
                "url": oa_location["url"],
                "license": license_type
            }
        return None
    except Exception as e:
        logger.error(f"Error checking open access: {e}")
        return None

async def search_papers(query: str, max_papers: int = 3, open_access_only: bool = True) -> List[Dict]:
    """
    Search for research papers on a given topic.
    
    Args:
        query: Search query
        max_papers: Maximum number of papers to return
        open_access_only: Whether to only return open access papers
        
    Returns:
        list: List of paper information dictionaries
    """
    logger.info(f"Searching for papers on: {query}")
    papers = []
    search_results = scholarly.search_pubs(query)
    
    async with aiohttp.ClientSession() as session:
        count = 0
        
        for result in search_results:
            if len(papers) >= max_papers:
                break
                
            # Extract paper details
            title = result.get("bib", {}).get("title", "Unknown Title")
            
            # Get DOI (either directly or from URL)
            doi = result.get("bib", {}).get("doi")
            if not doi and "pub_url" in result:
                doi = extract_doi(result["pub_url"])
                
            if not doi:
                logger.debug(f"Skipping paper without DOI: {title}")
                continue
                
            logger.info(f"Checking access for: {title}")
            
            # Check if paper is open access
            if open_access_only:
                paper_info = await get_open_access_paper(session, doi)
                if not paper_info:
                    logger.debug(f"Skipping non-open access paper: {title}")
                    continue
                    
                papers.append(paper_info)
            else:
                papers.append({
                    "title": title,
                    "doi": doi
                })
                
            count += 1
            
    logger.info(f"Found {len(papers)} papers matching criteria")
    return papers