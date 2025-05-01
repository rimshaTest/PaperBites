# paper/download.py
import logging
import aiohttp
import os
import re
from typing import Optional, Dict
import arxiv
from config import Config

from utils.network import download_file, resilient_fetch
from paper.license import is_publicly_displayable

config_instance = Config()

logger = logging.getLogger("paperbites.download")

async def download_paper(paper_info: Dict, filename: str) -> Optional[str]:
    """
    Download a paper from the information provided.
    
    Args:
        paper_info: Dictionary with paper information
        filename: Path to save the file
        
    Returns:
        str: Path to downloaded file or None if download failed
    """
    url = paper_info.get("url")
    if not url:
        logger.error(f"No URL provided for paper download")
        return None
        
    logger.info(f"Downloading paper from {url}")
    
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(os.path.abspath(filename)), exist_ok=True)
    
    # Download the file
    async with aiohttp.ClientSession() as session:
        success = await download_file(session, url, filename)
        
        if success:
            logger.info(f"Downloaded: {filename}")
            return filename
        else:
            logger.error(f"Failed to download paper")
            return None

async def get_paper_by_id(paper_id: str) -> Optional[Dict]:
    """
    Get information about a paper by its ID (arXiv ID, DOI, Semantic Scholar ID, etc.).
    
    Args:
        paper_id: ID of the paper
        
    Returns:
        dict: Paper information or None if not found
    """
    # Check if it's an arXiv ID (looks like 1234.56789v1 or 1234.56789)
    if re.match(r"\d{4}\.\d{4,5}(?:v\d+)?", paper_id):
        return await get_arxiv_paper(paper_id)
    
    # Check if it's a DOI
    if paper_id.startswith("10."):
        return await get_doi_paper(paper_id)
    
    # Check if it's a Semantic Scholar ID
    if paper_id.startswith("SS-"):
        # Extract the actual ID (remove the SS- prefix)
        ss_id = paper_id[3:]
        return await get_semantic_scholar_paper(ss_id)
    
    # Check if it might be an OpenAlex ID
    if paper_id.startswith("W"):
        return await get_openalex_paper(paper_id)
    
    # Unknown ID format
    logger.error(f"Unknown paper ID format: {paper_id}")
    return None

async def get_arxiv_paper(arxiv_id: str) -> Optional[Dict]:
    """
    Get information about a paper from arXiv.
    
    Args:
        arxiv_id: arXiv ID
        
    Returns:
        dict: Paper information or None if not found
    """
    logger.info(f"Getting paper from arXiv ID: {arxiv_id}")
    
    try:
        client = arxiv.Client()
        search = arxiv.Search(id_list=[arxiv_id])
        
        result = next(client.results(search), None)
        if not result:
            logger.error(f"Paper not found: {arxiv_id}")
            return None
            
        # The default license for arXiv submissions allows redistribution
        # https://arxiv.org/help/license
        # But we should still check the specific license when available
        license_url = getattr(result, "license", "")
        license_type = "arXiv" if not license_url else license_url
        
        # Check if license allows public display
        can_display_publicly = is_publicly_displayable(license_type)
        
        return {
            "title": result.title,
            "authors": [str(author) for author in result.authors],
            "summary": result.summary,
            "url": result.pdf_url,
            "source": "arXiv",
            "id": arxiv_id,
            "published": result.published.strftime("%Y-%m-%d"),
            "license": license_type,
            "can_display_publicly": can_display_publicly,
            "doi": getattr(result, "doi", None)
        }
    except Exception as e:
        logger.error(f"Error getting paper from arXiv: {e}")
        return None

async def get_doi_paper(doi: str) -> Optional[Dict]:
    """
    Get information about a paper by DOI using Unpaywall.
    
    Args:
        doi: DOI of the paper
        
    Returns:
        dict: Paper information or None if not found or not open access
    """
    logger.info(f"Checking open access for DOI: {doi}")
    
    # Required for Unpaywall API
    email = config_instance.get("api.email")
    
    async with aiohttp.ClientSession() as session:
        url = f"https://api.unpaywall.org/v2/{doi}?email={email}"
        
        try:
            data = await resilient_fetch(session, url)
            if not data or data.get("error"):
                logger.warning(f"API error for DOI {doi}: {data.get('error', 'Unknown error')}")
                return None
                
            # Check if it's open access
            if not data.get("is_oa", False):
                logger.debug(f"Not open access: {doi}")
                return None
                
            # Get the best OA location
            oa_location = data.get("best_oa_location")
            if not oa_location:
                logger.debug(f"No open access location: {doi}")
                return None
                
            # Get URL for PDF or HTML
            url = oa_location.get("url_for_pdf")
            if not url:
                url = oa_location.get("url")
                
            if not url:
                logger.debug(f"No URL in open access location: {doi}")
                return None
                
            # Get license information
            license_type = oa_location.get("license", "")
            
            # Check if license allows public display
            can_display_publicly = is_publicly_displayable(license_type)
            
            return {
                "title": data.get("title", "Unknown Title"),
                "doi": doi,
                "url": url,
                "license": license_type,
                "can_display_publicly": can_display_publicly,
                "authors": data.get("z_authors", []),
                "published_date": data.get("published_date")
            }
        except Exception as e:
            logger.error(f"Error checking open access for DOI {doi}: {e}")
            return None

async def get_semantic_scholar_paper(paper_id: str) -> Optional[Dict]:
    """
    Get information about a paper by Semantic Scholar ID.
    
    Args:
        paper_id: Semantic Scholar paper ID
        
    Returns:
        dict: Paper information or None if not found
    """
    logger.info(f"Getting paper from Semantic Scholar ID: {paper_id}")
    
    async with aiohttp.ClientSession() as session:
        url = f"https://api.semanticscholar.org/graph/v1/paper/{paper_id}?fields=title,authors,abstract,url,openAccessPdf,year,venue,publicationTypes,journal,externalIds"
        
        try:
            async with session.get(url) as response:
                if response.status != 200:
                    logger.error(f"Semantic Scholar API error: {response.status}")
                    return None
                    
                data = await response.json()
                
                # Check if open access
                if not data.get("openAccessPdf", {}).get("url"):
                    logger.debug(f"Not open access: {paper_id}")
                    return None
                
                # Get PDF URL
                pdf_url = data.get("openAccessPdf", {}).get("url")
                if not pdf_url:
                    logger.debug(f"No PDF URL: {paper_id}")
                    return None
                
                # Get DOI if available
                doi = data.get("externalIds", {}).get("DOI")
                
                # Assume open access since it's from openAccessPdf
                # Default license for academic papers
                license_type = "open access"
                
                # Check if license allows public display
                can_display_publicly = is_publicly_displayable(license_type)
                
                # Extract authors
                authors = []
                for author in data.get("authors", []):
                    if "name" in author:
                        authors.append(author["name"])
                
                return {
                    "title": data.get("title", "Unknown Title"),
                    "authors": authors,
                    "summary": data.get("abstract", ""),
                    "url": pdf_url,
                    "source": "Semantic Scholar",
                    "id": f"SS-{paper_id}",
                    "doi": doi,
                    "license": license_type,
                    "can_display_publicly": can_display_publicly,
                    "published": str(data.get("year", ""))
                }
        except Exception as e:
            logger.error(f"Error getting paper from Semantic Scholar: {e}")
            return None

async def get_openalex_paper(paper_id: str) -> Optional[Dict]:
    """
    Get information about a paper by OpenAlex ID.
    
    Args:
        paper_id: OpenAlex ID
        
    Returns:
        dict: Paper information or None if not found
    """
    logger.info(f"Getting paper from OpenAlex ID: {paper_id}")
    
    # Use the email from config for polite pool
    email = config_instance.get("api.email")
    
    async with aiohttp.ClientSession() as session:
        # Create URL with polite pool parameter
        url = f"https://api.openalex.org/works/{paper_id}"
        if email:
            url += f"?mailto={email}"
        
        try:
            async with session.get(url) as response:
                if response.status != 200:
                    logger.error(f"OpenAlex API error: {response.status}")
                    return None
                    
                item = await response.json()
                
                # Check if open access
                is_oa = item.get("open_access", {}).get("is_oa", False)
                if not is_oa:
                    logger.debug(f"Not open access: {paper_id}")
                    return None
                
                # Get PDF URL or landing page
                pdf_url = None
                for location in item.get("open_access", {}).get("oa_locations", []):
                    if location.get("url_for_pdf"):
                        pdf_url = location.get("url_for_pdf")
                        break
                
                if not pdf_url:
                    # Try getting the landing page as fallback
                    pdf_url = item.get("open_access", {}).get("oa_url")
                
                if not pdf_url:
                    logger.debug(f"No PDF URL: {paper_id}")
                    return None
                
                # Get license information
                license_type = "open access"  # Default value
                for location in item.get("open_access", {}).get("oa_locations", []):
                    if location.get("license"):
                        license_type = location.get("license")
                        break
                
                # Check if license allows public display
                can_display_publicly = is_publicly_displayable(license_type)
                
                # Extract authors
                authors = []
                for author in item.get("authorships", []):
                    if "author" in author and "display_name" in author["author"]:
                        authors.append(author["author"]["display_name"])
                
                return {
                    "title": item.get("title", "Unknown Title"),
                    "authors": authors,
                    "summary": item.get("abstract", ""),
                    "url": pdf_url,
                    "source": "OpenAlex",
                    "id": paper_id,
                    "doi": item.get("doi"),
                    "license": license_type,
                    "can_display_publicly": can_display_publicly,
                    "published": item.get("publication_date", "")
                }
        except Exception as e:
            logger.error(f"Error getting paper from OpenAlex: {e}")
            return None