# video/voiceover.py
import os
import logging
import asyncio
from typing import Optional, Dict
from gtts import gTTS
from pydub import AudioSegment
import tempfile
import re

logger = logging.getLogger("paperbites.voiceover")

def clean_text_for_tts(text: str) -> str:
    """
    Clean and prepare text for text-to-speech.
    
    Args:
        text: Text to clean
        
    Returns:
        str: Cleaned text ready for TTS
    """
    # Remove URLs
    text = re.sub(r'https?://\S+', '', text)
    
    # Remove special characters that might cause issues
    text = re.sub(r'[^\w\s.,;?!\'"-]', ' ', text)
    
    # Replace multiple spaces with a single space
    text = re.sub(r'\s+', ' ', text)
    
    # Add pauses after sentences for more natural speech
    text = re.sub(r'\.(\s)', r'.\1\1', text)  # Add pause after periods
    text = re.sub(r'[!?](\s)', r'!\1\1', text)  # Add pause after exclamation/question marks
    
    # Fix common TTS pronunciation issues
    text = re.sub(r'(\d+)\.(\d+)', r'\1 point \2', text)  # Change decimal points to "point"
    
    return text.strip()

def create_voiceover(text: str, output_path: str, lang: str = 'en', slow: bool = False) -> Optional[str]:
    """
    Create audio narration from text using gTTS.
    
    Args:
        text: Text to convert to speech
        output_path: Path to save audio file
        lang: Language code
        slow: Whether to use slower speech rate
        
    Returns:
        str: Path to audio file or None if creation failed
    """
    try:
        logger.info(f"Creating voiceover with {len(text)} characters")
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        
        # Clean up text for better speech
        text = clean_text_for_tts(text)
        
        # Break text into manageable chunks if very long
        max_chars = 5000  # gTTS can sometimes fail with very long text
        if len(text) > max_chars:
            chunks = []
            for i in range(0, len(text), max_chars):
                end = min(i + max_chars, len(text))
                # Try to end at a sentence boundary
                if end < len(text):
                    last_period = text.rfind('. ', i, end)
                    if last_period > i:
                        end = last_period + 1
                chunks.append(text[i:end])
                
            # Create temporary files for each chunk
            temp_files = []
            for i, chunk in enumerate(chunks):
                temp_path = f"{output_path}.part{i}.mp3"
                tts = gTTS(text=chunk, lang=lang, slow=slow)
                tts.save(temp_path)
                temp_files.append(temp_path)
                
            # Combine chunks using pydub
            combined = AudioSegment.empty()
            for temp_file in temp_files:
                try:
                    segment = AudioSegment.from_mp3(temp_file)
                    combined += segment
                except Exception as e:
                    logger.error(f"Error processing audio chunk {temp_file}: {e}")
                    
            combined.export(output_path, format="mp3")
            
            # Clean up temp files
            for temp_file in temp_files:
                try:
                    os.remove(temp_file)
                except Exception:
                    pass  # Ignore errors in cleanup
        else:
            # Single file for shorter text
            tts = gTTS(text=text, lang=lang, slow=slow)
            tts.save(output_path)
        
        logger.info(f"Voiceover created: {output_path}")
        return output_path
        
    except Exception as e:
        logger.error(f"Failed to create voiceover: {e}")
        return None

async def create_voiceover_async(text: str, output_path: str, lang: str = 'en', slow: bool = False) -> Optional[str]:
    """
    Async wrapper for create_voiceover function.
    
    Args:
        text: Text to convert to speech
        output_path: Path to save audio file
        lang: Language code
        slow: Whether to use slower speech rate
        
    Returns:
        str: Path to audio file or None if creation failed
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: create_voiceover(text, output_path, lang, slow))

def get_audio_duration(audio_path: str) -> float:
    """
    Get the duration of an audio file in seconds.
    
    Args:
        audio_path: Path to audio file
        
    Returns:
        float: Duration in seconds
    """
    try:
        audio = AudioSegment.from_mp3(audio_path)
        return len(audio) / 1000.0  # Convert from ms to seconds
    except Exception as e:
        logger.error(f"Error getting audio duration: {e}")
        return 0.0

def create_segment_voiceovers(script: Dict[str, str], output_dir: str) -> Dict[str, Dict]:
    """
    Create separate voiceovers for each section of the script.
    
    Args:
        script: Dictionary with script sections
        output_dir: Directory to save audio files
        
    Returns:
        dict: Dictionary with paths and durations for each section
    """
    os.makedirs(output_dir, exist_ok=True)
    
    result = {}
    for section, text in script.items():
        if not text or not isinstance(text, str):
            continue
            
        output_path = os.path.join(output_dir, f"{section}.mp3")
        audio_path = create_voiceover(text, output_path)
        
        if audio_path:
            duration = get_audio_duration(audio_path)
            result[section] = {
                "path": audio_path,
                "duration": duration,
                "text": text
            }
    
    return result