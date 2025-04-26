# video/visual.py
import os
import logging
import requests
from typing import Optional, Tuple
from moviepy import ColorClip
import numpy as np
from config import Config

config_instance = Config()

pexels_key = config_instance.get("api.pexels_key")

logger = logging.getLogger("paperbites.visual")

def fetch_stock_video(keyword: str, output_path: str, api_key: Optional[str] = pexels_key) -> Optional[str]:
    """
    Fetch a relevant stock video clip from Pexels.
    
    Args:
        keyword: Search term for video
        output_path: Path to save video
        api_key: Pexels API key
        
    Returns:
        str: Path to downloaded video or None if download failed
    """
    # Use environment variable if not provided
    api_key = api_key or os.environ.get("PEXELS_API_KEY")
    if not api_key:
        logger.error("No Pexels API key provided")
        return None
        
    headers = {"Authorization": api_key}
    params = {
        "query": keyword, 
        "per_page": 1, 
        "orientation": "portrait",  # For TikTok
        "size": "medium"
    }
    
    try:
        logger.info(f"Searching Pexels for: {keyword}")
        response = requests.get(
            "https://api.pexels.com/videos/search",
            headers=headers,
            params=params,
            timeout=10
        )
        response.raise_for_status()
        
        data = response.json()
        if not data.get("videos"):
            logger.warning(f"No videos found for keyword: {keyword}")
            return None
            
        # Find the best quality video file that's not too large
        video_files = data["videos"][0]["video_files"]
        
        # Sort by height (quality) descending
        video_files.sort(key=lambda x: x.get("height", 0), reverse=True)
        
        # Get the best quality under 20MB or the lowest quality if all are large
        selected_file = None
        for file in video_files:
            if file.get("file_size", float('inf')) < 20 * 1024 * 1024:  # 20MB
                selected_file = file
                break
                
        if not selected_file and video_files:
            selected_file = video_files[-1]  # Smallest file
            
        if not selected_file:
            logger.warning(f"No suitable video files found for: {keyword}")
            return None
            
        # Download the video
        logger.info(f"Downloading video: {selected_file['link']}")
        video_response = requests.get(selected_file["link"], stream=True, timeout=30)
        video_response.raise_for_status()
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        
        # Save the video
        with open(output_path, "wb") as f:
            for chunk in video_response.iter_content(chunk_size=8192):
                f.write(chunk)
                
        logger.info(f"Video downloaded: {output_path}")
        return output_path
        
    except Exception as e:
        logger.error(f"Failed to fetch stock video: {e}")
        return None

def create_gradient_clip(
    width: int, 
    height: int, 
    duration: float, 
    filename: str,
    color1: Tuple[int, int, int] = (25, 25, 112),  # Midnight Blue
    color2: Tuple[int, int, int] = (65, 105, 225)  # Royal Blue
) -> Optional[str]:
    """
    Create a gradient background video clip.
    
    Args:
        width: Video width
        height: Video height
        duration: Duration in seconds
        filename: Output file path
        color1: Gradient start color
        color2: Gradient end color
        
    Returns:
        str: Path to output file or None if creation failed
    """
    try:
        logger.info(f"Creating gradient clip: {width}x{height}, {duration}s")
        
        # Create gradient array
        gradient = np.zeros((height, width, 3), dtype=np.uint8)
        
        for y in range(height):
            # Calculate gradient ratio
            ratio = y / height
            # Linear interpolation between colors
            r = int(color1[0] * (1 - ratio) + color2[0] * ratio)
            g = int(color1[1] * (1 - ratio) + color2[1] * ratio)
            b = int(color1[2] * (1 - ratio) + color2[2] * ratio)
            gradient[y, :] = [r, g, b]
        
        # Create clip from gradient
        clip = ColorClip(size=(width, height), color=lambda t: gradient)
        clip = clip.set_duration(duration)
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(os.path.abspath(filename)), exist_ok=True)
        
        # Write video file
        clip.write_videofile(
            filename, 
            fps=24, 
            codec="libx264",
            audio=False,
            preset="ultrafast"  # Fast encoding for placeholder
        )
        
        logger.info(f"Gradient clip created: {filename}")
        return filename
        
    except Exception as e:
        logger.error(f"Failed to create gradient clip: {e}")
        return None