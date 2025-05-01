# utils/network.py
import aiohttp
import asyncio
import logging
from typing import Optional, Dict, Any
import os

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
                    logger.error(f"Client error: HTTP {response.status} for {url}")
                    error_text = await response.text()
                    logger.debug(f"Error response: {error_text[:500]}")
                    return None  # Don't retry client errors
                    
                else:
                    logger.warning(f"Server error: HTTP {response.status} for {url}, retrying...")
            
        except asyncio.TimeoutError:
            logger.warning(f"Request timed out: {url}")
            
        except Exception as e:
            logger.error(f"Request error ({type(e).__name__}): {e}")
        
        # Exponential backoff
        wait_time = backoff_factor ** retries
        logger.info(f"Waiting {wait_time:.2f}s before retry {retries+1}/{max_retries}")
        await asyncio.sleep(wait_time)
        retries += 1
    
    logger.error(f"Failed after {max_retries} retries: {url}")
    return None

async def download_file(
    session: aiohttp.ClientSession,
    url: str,
    filename: str,
    chunk_size: int = 8192,
    max_retries: int = 3,
    timeout: int = 60
) -> bool:
    """
    Download file from URL with progress tracking.
    
    Args:
        session: aiohttp ClientSession
        url: URL to download
        filename: Path to save the file
        chunk_size: Size of chunks for streaming download
        max_retries: Maximum number of retry attempts
        timeout: Request timeout in seconds
        
    Returns:
        bool: True if download successful, False otherwise
    """
    retries = 0
    
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(os.path.abspath(filename)), exist_ok=True)
    
    while retries < max_retries:
        try:
            logger.info(f"Downloading {url} to {filename} (attempt {retries + 1}/{max_retries})")
            
            total_size = 0
            async with session.get(url, timeout=timeout) as response:
                if response.status != 200:
                    logger.warning(f"Download failed with status {response.status}")
                    retries += 1
                    continue
                
                content_length = response.headers.get('Content-Length')
                if content_length:
                    content_length = int(content_length)
                    logger.info(f"File size: {content_length / 1024 / 1024:.2f} MB")
                
                with open(filename, 'wb') as f:
                    async for chunk in response.content.iter_chunked(chunk_size):
                        f.write(chunk)
                        total_size += len(chunk)
                        if content_length:
                            progress = min(100, total_size * 100 / content_length)
                            if total_size % (1024 * 1024) < chunk_size:  # Log every MB
                                logger.debug(f"Download progress: {progress:.1f}% ({total_size / 1024 / 1024:.2f} MB)")
            
            logger.info(f"Downloaded: {filename} ({total_size / 1024 / 1024:.2f} MB)")
            return True
            
        except asyncio.TimeoutError:
            logger.warning(f"Download timed out: {url}")
        except aiohttp.ClientPayloadError as e:
            logger.warning(f"Payload error: {e}, partial content may have been downloaded")
            # Check if file size is sufficient
            if os.path.exists(filename) and os.path.getsize(filename) > 10000:  # More than 10KB
                logger.info(f"Using partial download: {filename}")
                return True
        except Exception as e:
            logger.error(f"Error downloading {url}: {e}")
        
        # Exponential backoff
        wait_time = 2 ** retries
        logger.info(f"Waiting {wait_time}s before retry")
        await asyncio.sleep(wait_time)
        retries += 1
    
    logger.error(f"Failed to download {url} after {max_retries} attempts")
    
    # Delete partial file if it exists
    if os.path.exists(filename):
        try:
            os.remove(filename)
        except Exception:
            pass
            
    return False