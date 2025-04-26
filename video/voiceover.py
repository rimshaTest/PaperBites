# video/voiceover.py
import os
import logging
from gtts import gTTS
from typing import Optional

logger = logging.getLogger("paperbites.voiceover")

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
        text = text.replace('\n', ' ').strip()
        text = ' '.join(text.split())  # Remove multiple spaces
        
        # Break text into manageable chunks if very long
        max_chars = 5000  # gTTS can sometimes fail with very long text
        if len(text) > max_chars:
            chunks = []
            for i in range(0, len(text), max_chars):
                chunks.append(text[i:i+max_chars])
                
            # Create temporary files for each chunk
            temp_files = []
            for i, chunk in enumerate(chunks):
                temp_path = f"{output_path}.part{i}.mp3"
                tts = gTTS(text=chunk, lang=lang, slow=slow)
                tts.save(temp_path)
                temp_files.append(temp_path)
                
            # Combine chunks
            from pydub import AudioSegment
            combined = AudioSegment.empty()
            for temp_file in temp_files:
                combined += AudioSegment.from_mp3(temp_file)
                
            combined.export(output_path, format="mp3")
            
            # Clean up temp files
            for temp_file in temp_files:
                os.remove(temp_file)
        else:
            # Single file for shorter text
            tts = gTTS(text=text, lang=lang, slow=slow)
            tts.save(output_path)
        
        logger.info(f"Voiceover created: {output_path}")
        return output_path
    except Exception as e:
        logger.error(f"Failed to create voiceover: {e}")
        return None