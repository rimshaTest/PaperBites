# video/compose.py
from moviepy import (
    AudioFileClip, VideoFileClip, TextClip, CompositeVideoClip, 
    concatenate_videoclips, ColorClip, ImageClip
)
import os
import logging
import random
from typing import Dict, List, Tuple, Optional, Union

logger = logging.getLogger("paperbites.video")

class VideoGenerator:
    """
    Generate TikTok-style videos from research paper content.
    """
    
    def __init__(
        self, 
        temp_dir: str = "temp_assets",
        font_path: Optional[str] = None,
        default_size: Tuple[int, int] = (1080, 1920)  # TikTok vertical by default
    ):
        """
        Initialize video generator.
        
        Args:
            temp_dir: Directory for temporary files
            font_path: Path to font file
            default_size: Default video dimensions (width, height)
        """
        self.temp_dir = temp_dir
        self.font_path = font_path or self._get_available_font()
        self.default_size = default_size
        
        # Create temp directory if it doesn't exist
        os.makedirs(self.temp_dir, exist_ok=True)
        
    def _get_available_font(self) -> Optional[str]:
        """Find an available font that works with MoviePy."""
        try:
            from PIL import ImageFont
            
            font_paths = [
                # Windows
                "arial.ttf",
                "Arial.ttf",
                "C:/Windows/Fonts/arial.ttf",
                # Linux
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                # MacOS
                "/Library/Fonts/Arial.ttf",
                "/System/Library/Fonts/Supplemental/Arial.ttf",
            ]
            
            for path in font_paths:
                if os.path.exists(path):
                    try:
                        ImageFont.truetype(path, 10)  # Test loading
                        return path
                    except Exception:
                        continue
        except Exception as e:
            logger.warning(f"Error loading fonts: {e}")
            
        # If no font found, use MoviePy's default
        return None
        
    def create_animated_text(
        self,
        text: str,
        size: Tuple[int, int],
        duration: float,
        animation: str = "fade",
        font_size: int = 40,
        color: str = "white",
        bg_color: Optional[str] = None,
        position: str = "center"
    ) -> TextClip:
        """
        Create text clip with animation effects.
        
        Args:
            text: Text content
            size: Size of the clip (width, height)
            duration: Duration in seconds
            animation: Animation type (fade, slide, zoom)
            font_size: Font size
            color: Text color
            bg_color: Background color
            position: Text position
            
        Returns:
            TextClip: Animated text clip
        """
        # Format text to improve readability
        import textwrap
        max_chars = int(size[0] / (font_size * 0.6))  # Approximate chars per line
        wrapped_text = "\n".join(textwrap.wrap(text, width=max_chars))
        
        # Create base text clip
        try:
            text_clip = TextClip(
                text=wrapped_text,
                font_size=font_size,
                color=color,
                size=size,
                method="label" if self.font_path else None,
                text_align="center",
                font=self.font_path
            )
        except Exception as e:
            logger.warning(f"Error creating text clip, falling back to basic method: {e}")
            # Fallback to basic method without custom font
            text_clip = TextClip(
                text=wrapped_text,
                font_size=font_size,
                color=color,
                size=size,
                method="label",
                text_align="center"
            )
        
        # Add background if specified
        if bg_color:
            bg_clip = ColorClip(
                size=text_clip.size,
                color=bg_color if isinstance(bg_color, tuple) else self._parse_color(bg_color),
                duration=duration
            )
            text_clip = CompositeVideoClip([bg_clip, text_clip])
        
        return text_clip.with_position(position).with_duration(duration)
    
    def _parse_color(self, color_string: str) -> Tuple[int, int, int, int]:
        """Parse color string to RGBA tuple."""
        import re
        # Handle rgba format
        rgba_match = re.match(r'rgba\((\d+),\s*(\d+),\s*(\d+),\s*([\d.]+)\)', color_string)
        if rgba_match:
            r, g, b, a = map(float, rgba_match.groups())
            return (int(r), int(g), int(b), int(a * 255))
        
        # Handle simple color names
        if color_string == "black":
            return (0, 0, 0, 255)
        elif color_string == "white":
            return (255, 255, 255, 255)
        
        # Default to semi-transparent black
        return (0, 0, 0, 128)
    
    def _create_title_background(self, width: int, height: int, duration: float, title: str) -> VideoFileClip:
        """
        Create a background for the title slide without using crop or subclip methods.
        
        Args:
            width: Video width
            height: Video height
            duration: Duration in seconds
            title: Title text for related visuals
            
        Returns:
            VideoFileClip: Background video clip
        """
        from video.visual import create_gradient_clip, fetch_stock_video, create_text_image
        
        # Skip stock videos completely to avoid compatibility issues
        # Just use gradient backgrounds which are more reliable
        logger.info("Using gradient background for title")
        gradient_path = create_gradient_clip(
            width=width,
            height=height,
            duration=duration,
            filename=os.path.join(self.temp_dir, "title_gradient.mp4")
        )
        
        if gradient_path and os.path.exists(gradient_path):
            try:
                # Load the gradient video
                background = VideoFileClip(gradient_path)
                # Set duration directly
                background = background.with_duration(duration)
                return background
            except Exception as e:
                logger.error(f"Error loading gradient video: {e}")
        
        # Fallback to solid color
        logger.info("Falling back to solid color background")
        return ColorClip(size=(width, height), color=(25, 25, 112)).with_duration(duration)
    
    def generate_video(
        self,
        script: Dict,
        output_file: str = "output.mp4",
        width: Optional[int] = None,
        height: Optional[int] = None,
        fps: int = 30,
        use_stock_videos: bool = False  # Default to False to avoid compatibility issues
    ) -> Optional[str]:
        """
        Generate complete video from script.
        
        Args:
            script: Dictionary with video content
            output_file: Output file path
            width: Video width
            height: Video height
            fps: Frames per second
            use_stock_videos: Whether to use stock videos (if False, only gradient backgrounds will be used)
            
        Returns:
            str: Path to output video or None if generation failed
        """
        from video.voiceover import create_voiceover
        
        try:
            # Set video dimensions
            video_size = (
                width or self.default_size[0],
                height or self.default_size[1]
            )
            
            # Generate more relevant keyword searches based on content
            title = script.get("title", "Research Paper")
            summary = script.get("summary", "")
            key_insights = script.get("key_insights", [])
            hashtags = script.get("hashtags", "")
            
            # Combine into segments
            key_insights_text = "\n".join(key_insights) if key_insights else "Key findings from this research"
            
            segments = [
                {"text": title, "duration": 5, "type": "title"},
                {"text": summary, "duration": 10, "type": "summary"},
                {"text": key_insights_text, "duration": 8, "type": "insights"},
                {"text": hashtags, "duration": 3, "type": "hashtags"}
            ]
            
            # Generate voiceover
            logger.info(f"Generating voiceover...")
            voiceover_script = f"{title}. {summary} Key insights include: {'. '.join(key_insights)}."
            
            voiceover_path = create_voiceover(
                voiceover_script, 
                os.path.join(self.temp_dir, "narration.mp3")
            )
            
            if not voiceover_path:
                logger.error("Failed to create voiceover")
                return None
                
            # Get audio duration to synchronize video
            audio = AudioFileClip(voiceover_path)
            total_duration = audio.duration
            
            # Adjust segment durations based on audio length
            word_counts = [len(section["text"].split()) for section in segments]
            total_words = max(1, sum(word_counts))  # Avoid division by zero
            
            for i, words in enumerate(word_counts):
                # Calculate proportional duration
                prop_duration = (words / total_words) * total_duration
                segments[i]["duration"] = max(3, prop_duration)  # Minimum 3 seconds per segment
                
            logger.info(f"Creating video segments...")
            
            # Create clips for each segment
            clips = []
            
            # Create background clips for all segments
            for i, segment in enumerate(segments):
                # Skip empty segments
                if not segment["text"].strip():
                    continue
                
                segment_duration = segment["duration"]
                
                # Create a background clip (gradient or color)
                try:
                    from video.visual import create_gradient_clip
                    # Use a different color for each segment type
                    if segment["type"] == "title":
                        color1, color2 = (25, 25, 112), (65, 105, 225)  # Blue
                    elif segment["type"] == "summary":
                        color1, color2 = (20, 60, 80), (40, 80, 130)  # Teal
                    elif segment["type"] == "insights":
                        color1, color2 = (50, 20, 80), (90, 40, 130)  # Purple
                    else:
                        color1, color2 = (70, 30, 30), (130, 50, 50)  # Red
                    
                    bg_path = create_gradient_clip(
                        width=video_size[0],
                        height=video_size[1],
                        duration=segment_duration,
                        filename=os.path.join(self.temp_dir, f"segment_{i}_bg.mp4"),
                        color1=color1,
                        color2=color2
                    )
                    
                    if bg_path and os.path.exists(bg_path):
                        background = VideoFileClip(bg_path)
                        background = background.with_duration(segment_duration)
                    else:
                        # Fallback to solid color
                        background = ColorClip(
                            size=video_size,
                            color=color1
                        ).with_duration(segment_duration)
                except Exception as e:
                    logger.warning(f"Error creating background for segment {i}: {e}")
                    # Fallback to solid color
                    background = ColorClip(
                        size=video_size,
                        color=(40, 40, 100)  # Medium blue
                    ).with_duration(segment_duration)
                
                # Create text overlay
                text_clip = self.create_animated_text(
                    text=segment["text"],
                    size=video_size,
                    duration=segment_duration,
                    font_size=int(video_size[1] / 20),
                    color="white",
                    bg_color="rgba(0,0,0,0.5)" if segment["type"] != "title" else None
                )
                
                # Combine background and text
                composite = CompositeVideoClip([background, text_clip])
                clips.append(composite)
            
            # Combine everything
            logger.info(f"Combining video clips...")
            final_video = concatenate_videoclips(clips, method="compose")
            
            # Add audio
            final_video = final_video.with_audio(audio)
            
            # Export with appropriate settings for TikTok
            logger.info(f"Rendering final video to {output_file}...")
            final_video.write_videofile(
                output_file,
                fps=fps,
                codec="libx264",
                audio_codec="aac",
                preset="medium",
                threads=2
            )
            
            logger.info(f"Video generation complete!")
            return output_file
            
        except Exception as e:
            logger.error(f"Video generation failed: {e}", exc_info=True)
            return None