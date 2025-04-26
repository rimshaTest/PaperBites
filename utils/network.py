# utils/network.py
import aiohttp
import asyncio
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger("paperbites.network")

async def resilient_fetch(
    session: aiohttp.ClientSession,
    url: str,
    method: str = "GET",
    json_response: bool = True,
    max_retries: int = 3,
    backoff_factor: float = 1.5,
    timeout: int = 30,
    **kwargs
) -> Optional[Any]:
    """
    Perform HTTP requests with automatic retries and exponential backoff.
    
    Args:
        session: aiohttp ClientSession
        url: URL to request
        method: HTTP method (GET, POST, etc.)
        json_response: Whether to parse response as JSON
        max_retries: Maximum number of retry attempts
        backoff_factor: Multiplier for exponential backoff
        timeout: Request timeout in seconds
        **kwargs: Additional arguments for session.request
        
    Returns:
        Response data or None if request failed
    """
    retries = 0
    while retries < max_retries:
        try:
            async with session.request(
                method, 
                url, 
                timeout=timeout,
                **kwargs
            ) as response:
                if response.status == 200:
                    if json_response:
                        return await response.json()
                    else:
                        return await response.read()
                        
                elif response.status == 429:  # Rate limited
                    retry_after = int(response.headers.get('Retry-After', backoff_factor ** retries))
                    logger.warning(f"Rate limited, waiting {retry_after}s before retry...")
                    await asyncio.sleep(retry_after)
                    
                elif response.status >= 400 and response.status < 500:
                    logger.error(f"Client error: HTTP {response.status}")
                    return None  # Don't retry client errors
                    
                else:
                    logger.warning(f"Server error: HTTP {response.status}, retrying...")
            
        except asyncio.TimeoutError:
            logger.warning(f"Request timed out, retrying...")
            
        except Exception as e:
            logger.error(f"Request error ({type(e).__name__}): {e}")
        
        # Exponential backoff
        wait_time = backoff_factor ** retries
        logger.info(f"Waiting {wait_time:.2f}s before retry {retries+1}/{max_retries}")
        await asyncio.sleep(wait_time)
        retries += 1
    
    logger.error(f"Failed after {max_retries} retries")
    return None

async def download_file(
    session: aiohttp.ClientSession,
    url: str,
    filename: str,
    chunk_size: int = 8192,
    max_retries: int = 3
) -> bool:
    """
    Download file from URL with progress tracking.
    
    Args:
        session: aiohttp ClientSession
        url: URL to download
        filename: Path to save the file
        chunk_size: Size of chunks for streaming download
        max_retries: Maximum number of retry attempts
        
    Returns:
        bool: True if download successful, False otherwise
    """
    try:
        response = await resilient_fetch(
            session, 
            url, 
            json_response=False, 
            max_retries=max_retries
        )
        
        if not response:
            return False
            
        with open(filename, 'wb') as f:
            f.write(response)
            
        logger.info(f"Downloaded: {filename}")
        return True
        
    except Exception as e:
        logger.error(f"Error downloading {url}: {e}")
        return False