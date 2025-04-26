# video/compose.py
from moviepy import (
    AudioFileClip, VideoFileClip, TextClip, CompositeVideoClip, 
    concatenate_videoclips, ColorClip
)
import os
import logging
from typing import Dict, List, Tuple, Optional, Union, Callable

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
        text_clip = TextClip(
            text=wrapped_text,
            font_size=font_size,
            color=color,
            size=size,
            method="label" if self.font_path else None,
            text_align="center",
            font=self.font_path
        )
        
        # Add background if specified
        if bg_color:
            bg_clip = ColorClip(
                size=text_clip.size,
                color=bg_color if isinstance(bg_color, tuple) else self._parse_color(bg_color),
                duration=duration
            )
            text_clip = CompositeVideoClip([bg_clip, text_clip])
        
        # Apply animation effect
        # if animation == "fade":
        #     text_clip = text_clip.with_effects([]).fadeout(duration/4).fadein(duration/4)
        # elif animation == "slide":
        #     text_clip = text_clip.set_position(lambda t: ('center', size[1] + 50 - t * 100 if t < 0.5 else 'center'))
        # elif animation == "zoom":
        #     text_clip = text_clip.resize(lambda t: 1.5 - 0.5 * t)
        
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
    
    def generate_video(
        self,
        script: Dict,
        output_file: str = "output.mp4",
        width: Optional[int] = None,
        height: Optional[int] = None,
        fps: int = 30
    ) -> Optional[str]:
        """
        Generate complete video from script.
        
        Args:
            script: Dictionary with video content
            output_file: Output file path
            width: Video width
            height: Video height
            fps: Frames per second
            
        Returns:
            str: Path to output video or None if generation failed
        """
        from video.voiceover import create_voiceover
        from video.visual import fetch_stock_video, create_gradient_clip
        
        try:
            # Set video dimensions
            video_size = (
                width or self.default_size[0],
                height or self.default_size[1]
            )
            
            # Generate more relevant keyword searches based on content
            keywords = [
                {"text": script["title"], "duration": 3, "keyword": f"research {script['keywords'][0]}" if script.get('keywords') else "research"},
                {"text": script["summary"], "duration": 6, "keyword": f"science {script['keywords'][1]}" if script.get('keywords') and len(script['keywords']) > 1 else "science"},
                {"text": "\n".join(script["key_insights"]), "duration": 5, "keyword": f"data {script['keywords'][2]}" if script.get('keywords') and len(script['keywords']) > 2 else "data visualization"},
                {"text": script.get("hashtags", ""), "duration": 2, "keyword": "social media analytics"}
            ]
            
            # Generate voiceover
            logger.info(f"Generating voiceover...")
            voiceover_script = (
                f"{script['title']}. "
                f"{script['summary']} "
                f"Key insights include: {'. '.join(script['key_insights'])}."
            )
            
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
            word_counts = [len(section["text"].split()) for section in keywords]
            total_words = sum(word_counts)
            
            for i, words in enumerate(word_counts):
                # Calculate proportional duration
                prop_duration = (words / total_words) * total_duration
                keywords[i]["duration"] = prop_duration
                
            logger.info(f"Fetching video clips...")
            
            # Video clips with transitions
            clips = []
            
            for i, section in enumerate(keywords):
                # Skip empty sections
                if not section["text"].strip():
                    continue
                    
                # Get stock video
                video_path = fetch_stock_video(
                    section["keyword"],
                    os.path.join(self.temp_dir, f"clip_{i}.mp4")
                )
                
                if not video_path:
                    logger.warning(f"Using placeholder for {section['keyword']}")
                    # Create a gradient background as fallback
                    placeholder_path = os.path.join(self.temp_dir, f"placeholder_{i}.mp4")
                    create_gradient_clip(
                        width=video_size[0], 
                        height=video_size[1],
                        duration=section["duration"],
                        filename=placeholder_path
                    )
                    video_path = placeholder_path
                    
                # Load the video and set duration
                clips = []
                for i, section in enumerate(keywords):
                    video_clip = VideoFileClip(video_path)
                    video_clip = video_clip.without_audio()
                    video_clip = video_clip.resized(height=video_size[1])
                    video_clip = video_clip.with_duration(section["duration"])
                    clips.append(video_clip)

                # Combine with crossfade transitions
                video_clip = concatenate_videoclips(clips, method="compose")
                
                # Different animation for different sections
                animations = ["zoom", "fade", "slide", "fade"]
                
                # Text with animations
                text_clip = self.create_animated_text(
                    text=section["text"],
                    size=video_size,
                    duration=section["duration"],
                    animation=animations[i % len(animations)],
                    font_size=int(video_size[1] / 16),
                    color="white",
                    bg_color="rgba(0,0,0,0.5)" if i > 0 else None
                )
                
                composite = CompositeVideoClip([video_clip, text_clip])
                clips.append(composite)
                
            # Combine everything
            logger.info(f"Combining video clips...")
            final_video = concatenate_videoclips(clips, method="compose")
            final_video = final_video.set_audio(audio)
            
            # Add watermark
            watermark = (
                TextClip(
                    "AI Research Summary", 
                    fontsize=20, 
                    color='white',
                    bg_color="rgba(0,0,0,0.5)",
                    font=self.font_path,
                    size=(video_size[0], 30)
                )
                .set_position(("center", video_size[1] - 30))
                .set_duration(final_video.duration)
            )
            
            final_video = CompositeVideoClip([final_video, watermark])
            
            # Export with appropriate settings for TikTok
            logger.info(f"Rendering final video to {output_file}...")
            final_video.write_videofile(
                output_file,
                fps=fps,
                codec="libx264",
                audio_codec="aac",
                threads=4,
                preset="fast",
                ffmpeg_params=[
                    "-movflags", "+faststart",  # Optimize for web streaming
                    "-pix_fmt", "yuv420p"       # Compatible color format
                ]
            )
            
            logger.info(f"Video generation complete!")
            return output_file
            
        except Exception as e:
            logger.error(f"Video generation failed: {e}", exc_info=True)
            return None