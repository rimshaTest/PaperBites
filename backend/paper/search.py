# paper/search.py
import logging
import asyncio
import aiohttp
import arxiv
import urllib.parse
from scholarly import scholarly
from typing import List, Dict, Optional
import re
from config import Config

from utils.network import resilient_fetch
from paper.license import is_publicly_displayable

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

async def check_open_access(session: aiohttp.ClientSession, doi: str) -> Optional[Dict]:
    """
    Check if a paper has a free full-text version allowing commercial use.
    
    Args:
        session: aiohttp ClientSession
        doi: DOI of the paper
        
    Returns:
        dict: Paper information or None if not open access
    """
    if not doi:
        return None
        
    # Required for Unpaywall API
    email = config_instance.get("api.email")
    
    url = f"https://api.unpaywall.org/v2/{doi}?email={email}"
    
    try:
        data = await resilient_fetch(session, url)
        if not data or data.get("error"):
            return None

        # Check if open access
        if not data.get("is_oa", False):
            return None
            
        # Get the best OA location
        oa_location = data.get("best_oa_location")
        if not oa_location:
            return None

        # Get license information
        license_type = oa_location.get("license", "")
        
        # Get the URL to the full text
        pdf_url = oa_location.get("url_for_pdf")
        if not pdf_url:
            pdf_url = oa_location.get("url")
            
        if not pdf_url:
            return None
            
        # Check if license allows public display
        can_display_publicly = is_publicly_displayable(license_type)

        return {
            "title": data.get("title", "Unknown Title"),
            "doi": doi,
            "url": pdf_url,
            "license": license_type,
            "can_display_publicly": can_display_publicly,
            "authors": data.get("z_authors", []),
            "published_date": data.get("published_date")
        }
    except Exception as e:
        logger.error(f"Error checking open access: {e}")
        return None

async def search_arxiv(query: str, max_papers: int = 5) -> List[Dict]:
    """
    Search for papers on arXiv.
    
    Args:
        query: Search query
        max_papers: Maximum number of papers to return
        
    Returns:
        List[Dict]: List of paper information
    """
    if not query:
        query = "machine learning"  # Default query if none provided
        
    logger.info(f"Searching arXiv for: {query}")
    
    try:
        client = arxiv.Client()
        search = arxiv.Search(
            query=query,
            max_results=max_papers,
            sort_by=arxiv.SortCriterion.Relevance
        )
        
        results = []
        for result in client.results(search):
            # The default license for arXiv submissions allows redistribution
            # https://arxiv.org/help/license
            # But we should still check the specific license when available
            license_url = getattr(result, "license", "")
            license_type = "arXiv" if not license_url else license_url
            
            # Check if license allows public display
            can_display_publicly = is_publicly_displayable(license_type)
            
            paper_info = {
                "title": result.title,
                "authors": [str(author) for author in result.authors],
                "summary": result.summary,
                "url": result.pdf_url,
                "source": "arXiv",
                "id": result.entry_id.split("/")[-1],
                "published": result.published.strftime("%Y-%m-%d"),
                "license": license_type,
                "can_display_publicly": can_display_publicly,
                "doi": getattr(result, "doi", None)
            }
            results.append(paper_info)
            
        logger.info(f"Found {len(results)} papers using arXiv package")
        return results
    except Exception as e:
        logger.error(f"Error searching arXiv: {e}")
        return []

async def search_openalex(session: aiohttp.ClientSession, query: str, max_papers: int = 5) -> List[Dict]:
    """
    Search for papers using OpenAlex API.
    
    Args:
        session: aiohttp ClientSession
        query: Search query
        max_papers: Maximum number of papers to return
        
    Returns:
        List[Dict]: List of paper information
    """
    # Use the email from config for polite pool
    email = config_instance.get("api.email")
    
    logger.info(f"Searching OpenAlex for: {query}")
    
    # Create URL with polite pool parameter
    url = f"https://api.openalex.org/works?search={urllib.parse.quote(query)}&filter=is_oa:true&per_page={max_papers}"
    if email:
        url += f"&mailto={email}"
    
    try:
        async with session.get(url) as response:
            if response.status != 200:
                logger.error(f"OpenAlex API error: {response.status}")
                return []
                
            data = await response.json()
            results = []
            
            for item in data.get("results", []):
                # Check if open access
                is_oa = item.get("open_access", {}).get("is_oa", False)
                if not is_oa:
                    continue
                
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
                    continue
                
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
                
                paper_info = {
                    "title": item.get("title", "Unknown Title"),
                    "authors": authors,
                    "summary": item.get("abstract", ""),
                    "url": pdf_url,
                    "source": "OpenAlex",
                    "id": item.get("id", ""),
                    "doi": item.get("doi"),
                    "license": license_type,
                    "can_display_publicly": can_display_publicly,
                    "published": item.get("publication_date", "")
                }
                results.append(paper_info)
                
            logger.info(f"Found {len(results)} papers using OpenAlex API")
            return results
    except Exception as e:
        logger.error(f"Error searching OpenAlex: {e}")
        return []

async def search_semantic_scholar(session: aiohttp.ClientSession, query: str, max_papers: int = 5) -> List[Dict]:
    """
    Search for papers using Semantic Scholar API.
    
    Args:
        session: aiohttp ClientSession
        query: Search query
        max_papers: Maximum number of papers to return
        
    Returns:
        List[Dict]: List of paper information
    """
    logger.info(f"Searching Semantic Scholar for: {query}")
    
    url = f"https://api.semanticscholar.org/graph/v1/paper/search?query={urllib.parse.quote(query)}&limit={max_papers}&fields=title,authors,abstract,url,openAccessPdf,year,venue,publicationTypes,journal,externalIds"
    
    try:
        # Use semantic scholar API with appropriate headers
        headers = {"Accept": "application/json"}
        
        async with session.get(url, headers=headers) as response:
            if response.status != 200:
                logger.error(f"Semantic Scholar API error: {response.status}")
                return []
                
            data = await response.json()
            results = []
            
            for item in data.get("data", []):
                # Check if open access
                if not item.get("openAccessPdf", {}).get("url"):
                    continue
                
                # Get PDF URL
                pdf_url = item.get("openAccessPdf", {}).get("url")
                if not pdf_url:
                    continue
                
                # Get DOI if available
                doi = item.get("externalIds", {}).get("DOI")
                
                # Assume open access since it's from openAccessPdf
                # Default license for academic papers
                license_type = "open access"
                
                # Check if license allows public display
                can_display_publicly = is_publicly_displayable(license_type)
                
                # Extract authors
                authors = []
                for author in item.get("authors", []):
                    if "name" in author:
                        authors.append(author["name"])
                
                paper_info = {
                    "title": item.get("title", "Unknown Title"),
                    "authors": authors,
                    "summary": item.get("abstract", ""),
                    "url": pdf_url,
                    "source": "Semantic Scholar",
                    "id": item.get("paperId", ""),
                    "doi": doi,
                    "license": license_type,
                    "can_display_publicly": can_display_publicly,
                    "published": str(item.get("year", ""))
                }
                results.append(paper_info)
                
            logger.info(f"Found {len(results)} papers using Semantic Scholar API")
            return results
    except Exception as e:
        logger.error(f"Error searching Semantic Scholar: {e}")
        return []

async def search_papers(query: str, max_papers: int = 3, open_access_only: bool = True, public_only: bool = True) -> List[Dict]:
    """
    Search for research papers on a given topic across multiple sources.
    
    Args:
        query: Search query
        max_papers: Maximum number of papers to return
        open_access_only: Whether to only return open access papers
        public_only: Whether to only return papers that can be publicly displayed
        
    Returns:
        list: List of paper information dictionaries
    """
    logger.info(f"Searching for papers on: {query}")
    
    if not query:
        logger.info("No search query provided, using default query")
    
    # Calculate papers per source
    papers_per_source = max(2, max_papers)
    
    async with aiohttp.ClientSession() as session:
        # Search multiple sources in parallel
        results = await asyncio.gather(
            search_arxiv(query, papers_per_source),
            search_openalex(session, query, papers_per_source),
            search_semantic_scholar(session, query, papers_per_source)
        )
        
        # Combine results
        all_papers = []
        for source_papers in results:
            all_papers.extend(source_papers)
            
        # Enrich with DOI information if needed
        for paper in all_papers:
            if not paper.get("doi") and open_access_only:
                # Try Google Scholar to find DOI
                try:
                    title = paper.get("title", "")
                    if title:
                        # Limit to avoid getting blocked
                        scholarly.throttle(1, 10)
                        search_query = scholarly.search_pubs(title)
                        result = next(search_query, None)
                        if result and "pub_url" in result:
                            doi = extract_doi(result["pub_url"])
                            if doi:
                                paper["doi"] = doi
                except Exception as e:
                    logger.debug(f"Error searching Google Scholar: {e}")
        
        # Check open access status and enrich paper information
        if open_access_only:
            enriched_papers = []
            for paper in all_papers:
                if paper.get("doi"):
                    oa_info = await check_open_access(session, paper["doi"])
                    if oa_info:
                        # Update with open access information
                        paper.update(oa_info)
                        enriched_papers.append(paper)
                    else:
                        # Keep papers from our search results even if not found in Unpaywall
                        enriched_papers.append(paper)
                else:
                    # Keep papers even without DOI
                    enriched_papers.append(paper)
            
            all_papers = enriched_papers
        
        # Filter for public display if requested
        if public_only:
            all_papers = [p for p in all_papers if p.get("can_display_publicly", False)]
        
        # Remove duplicates (by DOI or title)
        unique_papers = []
        seen_dois = set()
        seen_titles = set()
        
        for paper in all_papers:
            doi = paper.get("doi")
            title = paper.get("title", "").lower()
            
            if doi and doi in seen_dois:
                continue
                
            if title in seen_titles:
                continue
                
            if doi:
                seen_dois.add(doi)
                
            seen_titles.add(title)
            unique_papers.append(paper)
        
        # Sort by relevance/recency and limit to max_papers
        result_papers = unique_papers[:max_papers]
        
        logger.info(f"Found {len(result_papers)} papers matching criteria")
        return result_papers