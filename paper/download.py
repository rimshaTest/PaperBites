# paper/download.py
import logging
import aiohttp
import os
from typing import Optional
from config import Config

from utils.network import download_file

config_instance = Config()

logger = logging.getLogger("paperbites.download")

async def download_paper(session: aiohttp.ClientSession, url: str, filename: str) -> Optional[str]:
    """
    Download a paper from a URL.
    
    Args:
        session: aiohttp ClientSession
        url: URL to download from
        filename: Path to save the file
        
    Returns:
        str: Path to downloaded file or None if download failed
    """
    logger.info(f"Downloading paper from {url}")
    
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(os.path.abspath(filename)), exist_ok=True)
    
    # Download the file
    success = await download_file(session, url, filename)
    
    if success:
        logger.info(f"Downloaded: {filename}")
        return filename
    else:
        logger.error(f"Failed to download paper")
        return None

async def get_open_access_paper(session: aiohttp.ClientSession, doi: str) -> Optional[dict]:
    """
    Check if a paper has open access full text with appropriate license.
    
    Args:
        session: aiohttp ClientSession
        doi: DOI of the paper
        
    Returns:
        dict: Paper information or None if not open access
    """
    # Required for Unpaywall API
    email = config_instance.get("api.email")  # Replace with config value
    
    url = f"https://api.unpaywall.org/v2/{doi}?email={email}"
    logger.info(f"Checking open access for DOI: {doi}")
    
    try:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                if data.get("error"):
                    logger.warning(f"API error for DOI {doi}: {data['error']}")
                    return None
                    
                oa_location = data.get("best_oa_location")
                if not oa_location:
                    logger.debug(f"No open access location for DOI {doi}")
                    return None

                license_type = oa_location.get("license", "")
                url = oa_location.get("url")
                
                if not url:
                    logger.debug(f"No URL in open access location for DOI {doi}")
                    return None
                    
                # Check for CC-BY or CC0 license (allows commercial use)
                if license_type and ("cc-by" in license_type.lower() or "cc0" in license_type.lower()):
                    return {
                        "title": data.get("title", "Unknown Title"),
                        "doi": doi,
                        "url": url,
                        "license": license_type
                    }
                else:
                    logger.debug(f"License {license_type} not suitable for DOI {doi}")
                    return None
            else:
                logger.warning(f"HTTP {response.status} for DOI {doi}")
                return None
    except Exception as e:
        logger.error(f"Error checking open access for DOI {doi}: {e}")
        return None