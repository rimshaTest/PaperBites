# video/visual.py
import os
import logging
import requests
import asyncio
import aiohttp
import random
import threading
import concurrent.futures
from typing import Optional, Tuple, List, Dict
import tempfile
from PIL import Image, ImageDraw, ImageFont
import numpy as np
from moviepy import ColorClip, ImageClip
from config import Config
import urllib.parse

logger = logging.getLogger("paperbites.visual")
config = Config()

# Get API key from config
pexels_key = config.get("api.pexels_key", os.environ.get("PEXELS_API_KEY"))

# Global thread pool executor for synchronous operations
thread_pool = concurrent.futures.ThreadPoolExecutor(max_workers=4)

# Track API rate limit
class RateLimit:
    """Class to track API rate limits and prevent excessive requests."""
    def __init__(self):
        self.exceeded = False
        self.remaining = 200  # Default hourly limit
        self.reset_time = None
        
    def update(self, headers):
        """Update rate limit info from response headers."""
        if 'X-Ratelimit-Remaining' in headers:
            self.remaining = int(headers.get('X-Ratelimit-Remaining', 200))
        if 'X-Ratelimit-Reset' in headers:
            self.reset_time = headers.get('X-Ratelimit-Reset')
        # If we're close to limit, log a warning
        if self.remaining < 10:
            logger.warning(f"API rate limit low: {self.remaining} requests remaining")
        
    def check(self):
        """Check if we've exceeded rate limits."""
        return self.exceeded
        
    def mark_exceeded(self):
        """Mark rate limit as exceeded."""
        self.exceeded = True
        logger.error("API rate limit exceeded! Stopping further requests.")

# Create global rate limit tracker
rate_limit = RateLimit()

def fetch_stock_image(keyword: str, output_path: str) -> Optional[str]:
    """
    Synchronous wrapper for fetch_stock_image_async.
    This version uses a synchronous requests library to avoid asyncio issues.
    
    Args:
        keyword: Search term for image
        output_path: Path to save image
        
    Returns:
        str: Path to downloaded image or None if download failed
    """
    # Check if we've exceeded rate limits
    if rate_limit.check():
        logger.warning("Skipping image fetch due to rate limit")
        return None
        
    api_key = pexels_key
    
    if not api_key:
        logger.error("No Pexels API key provided")
        return None
        
    try:
        # Perform synchronous request
        logger.info(f"Searching Pexels for: {keyword}")
        headers = {"Authorization": api_key}
        url = f"https://api.pexels.com/v1/search?query={urllib.parse.quote(keyword)}&per_page=5&orientation=portrait"
        
        response = requests.get(url, headers=headers, timeout=10)
        
        # Update rate limit info
        rate_limit.update(response.headers)
        
        if response.status_code == 429:
            # Rate limit exceeded
            rate_limit.mark_exceeded()
            logger.error("Rate limit exceeded on image search")
            return None
            
        if response.status_code != 200:
            logger.error(f"Failed to fetch stock image (HTTP {response.status_code})")
            return None
            
        data = response.json()
        if not data.get("photos"):
            logger.warning(f"No images found for keyword: {keyword}")
            return None
            
        # Select a random photo from the results
        photo = random.choice(data["photos"])
        image_url = photo["src"]["large"]
        
        # Download the image
        logger.info(f"Downloading image: {image_url}")
        image_response = requests.get(image_url, timeout=30)
        
        if image_response.status_code != 200:
            logger.error(f"Failed to download image (HTTP {image_response.status_code})")
            return None
            
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        
        # Save the image
        with open(output_path, "wb") as f:
            f.write(image_response.content)
            
        logger.info(f"Image downloaded: {output_path}")
        return output_path
    
    except Exception as e:
        logger.error(f"Error fetching stock image: {e}")
        return None

def _fetch_stock_video_sync(keyword: str, output_path: str) -> Optional[str]:
    """
    Synchronous implementation of stock video fetching.
    
    Args:
        keyword: Search term for video
        output_path: Path to save video
        
    Returns:
        str: Path to downloaded video or None if download failed
    """
    # Check if we've exceeded rate limits
    if rate_limit.check():
        logger.warning("Skipping video fetch due to rate limit")
        return None
        
    api_key = pexels_key
    
    if not api_key:
        logger.error("No Pexels API key provided")
        return None
        
    headers = {"Authorization": api_key}
    
    # URL encode the keyword
    encoded_keyword = urllib.parse.quote(keyword)
    url = f"https://api.pexels.com/videos/search?query={encoded_keyword}&per_page=5&orientation=portrait"
    
    try:
        logger.info(f"Searching Pexels for videos of: {keyword}")
        
        response = requests.get(url, headers=headers, timeout=10)
        
        # Update rate limit info
        rate_limit.update(response.headers)
        
        if response.status_code == 429:
            # Rate limit exceeded
            rate_limit.mark_exceeded()
            logger.error("Rate limit exceeded on video search")
            return None
            
        if response.status_code != 200:
            logger.warning(f"Failed to get videos (HTTP {response.status_code}): {keyword}")
            return None
            
        data = response.json()
        
        if not data.get("videos"):
            logger.warning(f"No videos found for keyword: {keyword}")
            return None
            
        # Choose a random video
        videos = data["videos"]
        if not videos:
            return None
            
        video = random.choice(videos)
        
        # Find the best quality video file that's not too large
        video_files = video["video_files"]
        video_files.sort(key=lambda x: x.get("height", 0), reverse=True)
        
        selected_file = None
        for file in video_files:
            file_size = file.get("file_size", float('inf'))
            if file_size < 20 * 1024 * 1024:  # 20MB limit
                selected_file = file
                break
                
        if not selected_file and video_files:
            selected_file = video_files[-1]  # Use the smallest one if all are large
            
        if not selected_file:
            logger.warning(f"No suitable video files found for: {keyword}")
            return None
            
        # Download the video
        logger.info(f"Downloading video: {selected_file['link']}")
        
        video_response = requests.get(selected_file["link"], timeout=30)
        if video_response.status_code != 200:
            logger.error(f"Failed to download video: HTTP {video_response.status_code}")
            return None
            
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        
        # Save the video
        with open(output_path, "wb") as f:
            f.write(video_response.content)
            
        logger.info(f"Video downloaded: {output_path} ({len(video_response.content) // (1024*1024)}MB)")
        return output_path
            
    except Exception as e:
        logger.error(f"Failed to fetch stock video: {e}")
        return None

def fetch_stock_video(keyword: str, output_path: str) -> Optional[str]:
    """
    Fetch a stock video using synchronous methods to avoid asyncio issues.
    
    Args:
        keyword: Search term for video
        output_path: Path to save video
        
    Returns:
        str: Path to downloaded video or None if download failed
    """
    try:
        # Submit the task to a thread pool to avoid blocking
        future = thread_pool.submit(_fetch_stock_video_sync, keyword, output_path)
        return future.result(timeout=60)  # Wait up to 60 seconds for result
    except concurrent.futures.TimeoutError:
        logger.error("Timeout while fetching stock video")
        return None
    except Exception as e:
        logger.error(f"Error in fetch_stock_video: {e}")
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
        
        # Make sure the directory exists
        os.makedirs(os.path.dirname(os.path.abspath(filename)), exist_ok=True)
        
        # Generate a unique temporary filename if the provided one isn't valid
        if not filename or not isinstance(filename, str):
            temp_dir = os.path.dirname(os.path.abspath(
                config.get("paths.temp_dir", "temp_assets")
            ))
            os.makedirs(temp_dir, exist_ok=True)
            filename = os.path.join(temp_dir, f"gradient_{random.randint(1000, 9999)}.mp4")
            logger.info(f"Generated temporary filename: {filename}")
        
        # Try the simplest approach first - a solid color clip
        try:
            solid_clip = ColorClip(
                size=(width, height), 
                color=color1,  # Use just the first color
                duration=duration
            )
            
            # Export as a video file with minimal settings
            solid_clip.write_videofile(
                filename, 
                fps=24, 
                codec="libx264",
                audio=False,
                preset="ultrafast",  # Fast encoding for placeholder
                logger=None  # Suppress moviepy logging
            )
            
            if os.path.exists(filename) and os.path.getsize(filename) > 0:
                logger.info(f"Solid color clip created: {filename}")
                return filename
                
        except Exception as e:
            logger.warning(f"Failed to create solid color clip: {e}")
            
            # Try creating a static image and convert to video as fallback
            try:
                # Create a gradient image
                gradient_img = Image.new('RGB', (width, height))
                draw = ImageDraw.Draw(gradient_img)
                
                # Draw a simple gradient
                for y in range(height):
                    # Calculate gradient ratio
                    ratio = y / height
                    # Linear interpolation between colors
                    r = int(color1[0] * (1 - ratio) + color2[0] * ratio)
                    g = int(color1[1] * (1 - ratio) + color2[1] * ratio)
                    b = int(color1[2] * (1 - ratio) + color2[2] * ratio)
                    draw.line([(0, y), (width, y)], fill=(r, g, b))
                
                # Save the gradient image
                gradient_img_path = filename.replace(".mp4", ".png")
                gradient_img.save(gradient_img_path)
                
                # Create a video from the image
                image_clip = ImageClip(gradient_img_path)
                image_clip = image_clip.set_duration(duration)
                
                # Save as video
                image_clip.write_videofile(
                    filename,
                    fps=24,
                    codec="libx264",
                    audio=False,
                    preset="ultrafast",
                    logger=None
                )
                
                # Clean up the temporary image
                try:
                    os.remove(gradient_img_path)
                except:
                    pass
                
                if os.path.exists(filename) and os.path.getsize(filename) > 0:
                    logger.info(f"Gradient image clip created: {filename}")
                    return filename
            except Exception as img_error:
                logger.warning(f"Failed to create gradient image clip: {img_error}")
        
        # If all attempts failed, create a simple solid color clip as final fallback
        fallback_path = os.path.join(
            config.get("paths.temp_dir", "temp_assets"),
            f"fallback_gradient_{random.randint(1000, 9999)}.mp4"
        )
        
        try:
            # Create a simple solid color array
            color_array = np.zeros((height, width, 3), dtype=np.uint8)
            color_array[:, :] = color1  # Fill with the first color
            
            # Create a clip from the solid color
            color_clip = ColorClip(size=(width, height), color=color_array)
            color_clip = color_clip.set_duration(duration)
            
            # Export with minimal settings
            color_clip.write_videofile(
                fallback_path,
                fps=24,
                codec="libx264", 
                audio=False,
                preset="ultrafast",
                logger=None
            )
            
            logger.info(f"Created fallback gradient clip: {fallback_path}")
            return fallback_path
        except Exception as fallback_error:
            logger.error(f"Failed to create fallback clip: {fallback_error}")
            return None
            
    except Exception as e:
        logger.error(f"Failed to create gradient clip: {e}")
        return None

def create_text_image(
    text: str,
    width: int,
    height: int,
    font_size: int = 40,
    bg_color: Tuple[int, int, int] = (25, 25, 112),
    text_color: Tuple[int, int, int] = (255, 255, 255),
    output_path: Optional[str] = None
) -> Optional[str]:
    """
    Create an image with text.
    
    Args:
        text: Text to display
        width: Image width
        height: Image height
        font_size: Font size
        bg_color: Background color
        text_color: Text color
        output_path: Path to save image (optional)
        
    Returns:
        str: Path to output file or None if creation failed
    """
    try:
        # Create a new image
        img = Image.new('RGB', (width, height), color=bg_color)
        draw = ImageDraw.Draw(img)
        
        # Try to load a font, fall back to default if not found
        try:
            # Search for fonts in common locations
            font_locations = [
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",  # Linux
                "/System/Library/Fonts/Helvetica.ttc",  # macOS
                "C:/Windows/Fonts/arial.ttf",  # Windows
            ]
            
            font = None
            for font_path in font_locations:
                if os.path.exists(font_path):
                    font = ImageFont.truetype(font_path, font_size)
                    break
                    
            if font is None:
                font = ImageFont.load_default()
        except Exception:
            font = ImageFont.load_default()
        
        # Wrap text to fit width
        words = text.split()
        lines = []
        current_line = []
        
        for word in words:
            test_line = ' '.join(current_line + [word])
            # Use getbbox for newer PIL versions, fallback to textlength
            try:
                bbox = draw.textbbox((0, 0), test_line, font=font)
                test_width = bbox[2] - bbox[0]
            except AttributeError:
                try:
                    test_width = draw.textlength(test_line, font=font)
                except AttributeError:
                    # For very old PIL versions
                    test_width = draw.textsize(test_line, font=font)[0]
            
            if test_width <= width - 40:  # Leave a small margin
                current_line.append(word)
            else:
                lines.append(' '.join(current_line))
                current_line = [word]
        
        if current_line:
            lines.append(' '.join(current_line))
        
        # Add ellipsis if text is too long
        max_lines = (height - 80) // (font_size + 10)  # Approximate number of lines that fit
        if len(lines) > max_lines:
            lines = lines[:max_lines-1] + ['...']
        
        # Draw text
        y_position = (height - (len(lines) * (font_size + 10))) // 2
        for line in lines:
            # Get line width for centering
            try:
                bbox = draw.textbbox((0, 0), line, font=font)
                line_width = bbox[2] - bbox[0]
            except AttributeError:
                try:
                    line_width = draw.textlength(line, font=font)
                except AttributeError:
                    # For very old PIL versions
                    line_width = draw.textsize(line, font=font)[0]
                    
            x_position = (width - line_width) // 2
            
            # Draw text with a small shadow for better visibility
            draw.text((x_position+2, y_position+2), line, font=font, fill=(0, 0, 0))
            draw.text((x_position, y_position), line, font=font, fill=text_color)
            
            y_position += font_size + 10
        
        # Save the image
        if output_path is None:
            output_path = tempfile.mktemp(suffix='.png')
            
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        img.save(output_path)
        
        return output_path
        
    except Exception as e:
        logger.error(f"Failed to create text image: {e}")
        return None