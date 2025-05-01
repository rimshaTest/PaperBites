# paper/summarize.py
import logging
import re
import asyncio
from typing import Dict, List, Optional, Union, Tuple
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import sent_tokenize
from nltk.probability import FreqDist
from collections import Counter
from transformers import pipeline, AutoTokenizer, AutoModelForSeq2SeqLM
from config import Config

logger = logging.getLogger("paperbites.summarize")

# Initialize NLTK resources
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt', quiet=True)
    
try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords', quiet=True)

# Load config
config = Config()

# Initialize summarizer
summarizer = None
tokenizer = None
model = None

def initialize_summarizer(model_name: str = None) -> bool:
    """
    Initialize the summarization model.
    
    Args:
        model_name: Name of the pretrained model to use
    
    Returns:
        bool: True if initialization successful
    """
    global summarizer, tokenizer, model
    
    if summarizer is not None:
        return True
        
    if model_name is None:
        model_name = config.get("paper.summarizer.model", "facebook/bart-large-cnn")
    
    logger.info(f"Initializing summarizer model: {model_name}")
    try:
        summarizer = pipeline("summarization", model=model_name)
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
        logger.info("Summarizer initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize summarizer with {model_name}: {e}")
        
        # Try a fallback model
        try:
            fallback_model = "sshleifer/distilbart-cnn-12-6"
            logger.info(f"Trying fallback model: {fallback_model}")
            summarizer = pipeline("summarization", model=fallback_model)
            tokenizer = AutoTokenizer.from_pretrained(fallback_model)
            model = AutoModelForSeq2SeqLM.from_pretrained(fallback_model)
            logger.info("Fallback summarizer initialized successfully")
            return True
        except Exception as e2:
            logger.error(f"Failed to initialize fallback summarizer: {e2}")
            return False

def chunk_text(text: str, chunk_size: int = 1024) -> List[str]:
    """
    Split text into smaller chunks respecting sentence boundaries.
    
    Args:
        text: Text to split
        chunk_size: Maximum chunk size in characters
        
    Returns:
        list: List of text chunks
    """
    # Split into sentences
    try:
        sentences = sent_tokenize(text)
    except Exception as e:
        logger.warning(f"Error tokenizing into sentences: {e}")
        # Simple fallback using regex
        sentences = re.findall(r'[^.!?]+[.!?]', text)
        if not sentences:
            # Last resort: split by newlines
            sentences = text.split('\n')
        
    chunks, current_chunk = [], []
    current_length = 0

    for sentence in sentences:
        # If adding this sentence would exceed the chunk size, start a new chunk
        if current_length + len(sentence) > chunk_size and current_chunk:
            chunks.append(" ".join(current_chunk))
            current_chunk = []
            current_length = 0
            
        current_chunk.append(sentence)
        current_length += len(sentence) + 1  # +1 for space

    # Add the last chunk if it's not empty
    if current_chunk:
        chunks.append(" ".join(current_chunk))

    return chunks

def extract_keywords(text: str, top_n: int = 5) -> List[str]:
    """
    Extract key terms from text using term frequency.
    
    Args:
        text: Text to extract keywords from
        top_n: Number of keywords to extract
        
    Returns:
        list: List of keywords
    """
    try:
        stop_words = set(stopwords.words('english'))
        
        # Add custom stopwords relevant to academic papers
        custom_stops = {
            'et', 'al', 'fig', 'figure', 'table', 'eq', 'equation', 
            'ref', 'reference', 'cited', 'doi', 'journal', 'vol', 'volume',
            'pp', 'page', 'author', 'authors', 'paper', 'study', 'research',
            'method', 'methods', 'result', 'results', 'discussion', 'abstract',
            'introduction', 'conclusion'
        }
        stop_words.update(custom_stops)
        
        # Tokenize into words
        words = nltk.word_tokenize(text.lower())
        
        # Filter stop words and short words
        filtered_words = [w for w in words if w.isalpha() and len(w) > 3 and w not in stop_words]
        
        # Get frequency distribution
        fdist = FreqDist(filtered_words)
        
        # Extract keyphrases of 1-2 words
        words = [w for w, _ in fdist.most_common(top_n * 2)]
        
        # Try to find bigrams (two-word phrases)
        bigrams = []
        for i in range(len(words) - 1):
            w1 = words[i]
            w2 = words[i + 1]
            if f"{w1} {w2}" in text.lower():
                bigrams.append(f"{w1} {w2}")
        
        # Combine top single words and bigrams
        keywords = []
        for item in bigrams + words:
            if item not in keywords and len(keywords) < top_n:
                keywords.append(item)
        
        return keywords[:top_n]
    
    except Exception as e:
        logger.error(f"Error extracting keywords: {e}")
        # Fallback with simple word counting
        try:
            word_freq = Counter(re.findall(r'\b[a-z]{4,}\b', text.lower()))
            return [word for word, _ in word_freq.most_common(top_n)]
        except:
            return []

def rank_sentences(text: str, top_n: int = 3) -> List[str]:
    """
    Rank sentences by importance based on keyword frequency.
    
    Args:
        text: Text to analyze
        top_n: Number of sentences to return
        
    Returns:
        list: List of most important sentences
    """
    try:
        # Tokenize into sentences
        sentences = sent_tokenize(text)
        
        # Skip if too few sentences
        if len(sentences) <= top_n:
            return sentences
            
        # Get keywords
        keywords = extract_keywords(text, top_n=10)
        
        # Score sentences based on keyword presence
        sentence_scores = []
        for sentence in sentences:
            score = 0
            for keyword in keywords:
                if keyword.lower() in sentence.lower():
                    score += 1
            
            # Normalize by sentence length
            words = len(sentence.split())
            if 5 <= words <= 25:  # Prefer moderate length sentences
                score *= 1.5
                
            sentence_scores.append((sentence, score))
        
        # Sort sentences by score
        sentence_scores.sort(key=lambda x: x[1], reverse=True)
        
        # Return top sentences
        return [sentence for sentence, _ in sentence_scores[:top_n]]
        
    except Exception as e:
        logger.error(f"Error ranking sentences: {e}")
        # Fallback to first few sentences
        try:
            sentences = sent_tokenize(text)
            return sentences[:top_n]
        except:
            return text.split(".")[:top_n]

def format_hashtags(keywords: List[str]) -> str:
    """
    Format keywords into hashtags.
    
    Args:
        keywords: List of keywords
        
    Returns:
        str: Formatted hashtags
    """
    # Remove spaces and special characters
    hashtags = []
    for keyword in keywords:
        tag = re.sub(r'[^a-zA-Z0-9]', '', keyword)
        if tag:
            hashtags.append(f"#{tag}")
    
    return " ".join(hashtags)

def summarize_text(text: str, max_length: int = 150, min_length: int = 50) -> str:
    """
    Summarize text using the transformer model.
    
    Args:
        text: Text to summarize
        max_length: Maximum length of the summary in tokens
        min_length: Minimum length of the summary in tokens
        
    Returns:
        str: Summarized text
    """
    if not initialize_summarizer():
        logger.error("Failed to initialize summarizer")
        return ""
    
    try:
        # Split into chunks if needed
        if len(text) > 1024:
            chunks = chunk_text(text)
            summaries = []
            
            for chunk in chunks:
                if len(chunk) < 100:  # Skip very short chunks
                    continue
                    
                inputs = tokenizer(chunk, return_tensors="pt", max_length=1024, truncation=True)
                summary_ids = model.generate(
                    inputs["input_ids"], 
                    max_length=max_length,
                    min_length=min_length,
                    do_sample=False
                )
                summary = tokenizer.decode(summary_ids[0], skip_special_tokens=True)
                summaries.append(summary)
            
            return " ".join(summaries)
        else:
            # Process the whole text at once
            inputs = tokenizer(text, return_tensors="pt", max_length=1024, truncation=True)
            summary_ids = model.generate(
                inputs["input_ids"], 
                max_length=max_length,
                min_length=min_length,
                do_sample=False
            )
            return tokenizer.decode(summary_ids[0], skip_special_tokens=True)
            
    except Exception as e:
        logger.error(f"Error summarizing text: {e}")
        
        # Fallback to extractive summarization
        try:
            sentences = rank_sentences(text, top_n=3)
            return " ".join(sentences)
        except:
            # Last resort fallback
            return text[:max_length * 10]

def summarize_paper(sections: Dict[str, str]) -> Dict:
    """
    Summarize paper with weighted importance for different sections.
    
    Args:
        sections: Dictionary of paper sections
        
    Returns:
        dict: Summarized paper data
    """
    # Initialize summarizer if not already done
    if not initialize_summarizer():
        logger.warning("Could not initialize summarizer, using extractive summarization")
    
    # Define section weights and ideal summary lengths
    section_config = {
        "abstract": {"weight": 3.0, "ideal_length": 100},
        "introduction": {"weight": 1.5, "ideal_length": 80},
        "methods": {"weight": 0.8, "ideal_length": 50},
        "results": {"weight": 2.0, "ideal_length": 100},
        "discussion": {"weight": 2.0, "ideal_length": 80},
        "conclusion": {"weight": 2.5, "ideal_length": 80},
        "full_text": {"weight": 1.0, "ideal_length": 150}
    }
    
    # Create combined text for keyword extraction
    combined_text = ""
    for section in sections.values():
        combined_text += section + " "
    
    # Extract keywords and hashtags
    keywords = extract_keywords(combined_text, top_n=8)
    hashtags = format_hashtags(keywords)
    
    # Summarize each section
    section_summaries = {}
    for section_name, text in sections.items():
        if not text or len(text) < 50:
            continue
            
        config_item = section_config.get(section_name, section_config["full_text"])
        ideal_length = config_item["ideal_length"]
        
        try:
            # Use the transformer-based summarization for longer sections
            if len(text) > 300 and summarizer is not None:
                section_summary = summarize_text(
                    text,
                    max_length=ideal_length,
                    min_length=min(30, ideal_length // 2)
                )
            else:
                # Use extractive summarization for shorter sections
                top_sentences = rank_sentences(text, top_n=2)
                section_summary = " ".join(top_sentences)
                
            section_summaries[section_name] = section_summary
        
        except Exception as e:
            logger.error(f"Error summarizing {section_name}: {e}")
            # Use first few sentences as fallback
            sentences = sent_tokenize(text)
            section_summaries[section_name] = " ".join(sentences[:2])
    
    # Create the main summary
    main_summary = ""
    
    # Prioritize sections
    priority_sections = ["abstract", "introduction", "results", "conclusion", "discussion", "full_text"]
    for section in priority_sections:
        if section in section_summaries:
            main_summary += section_summaries[section] + " "
    
    # If still empty, use full text
    if not main_summary and "full_text" in sections:
        sentences = sent_tokenize(sections["full_text"])
        main_summary = " ".join(sentences[:5])
    
    # Truncate if too long
    if len(main_summary) > 500:  # Roughly 3-4 sentences
        sentences = sent_tokenize(main_summary)
        main_summary = " ".join(sentences[:4])
    
    # Extract key insights (important sentences)
    key_insights = rank_sentences(combined_text, top_n=3)
    
    # Format key insights to be more engaging
    formatted_insights = []
    for i, insight in enumerate(key_insights):
        # Clean up the insight
        insight = re.sub(r'\s+', ' ', insight).strip()
        # Make it shorter if it's too long
        if len(insight) > 100:
            words = insight.split()
            if len(words) > 20:
                insight = ' '.join(words[:20]) + "..."
        
        formatted_insights.append(insight)
    
    # Return results
    return {
        "summary": main_summary.strip(),
        "key_insights": formatted_insights,
        "keywords": keywords,
        "hashtags": hashtags
    }

def create_video_script(paper_info: Dict, summary: Dict) -> Dict:
    """
    Create an engaging script for the video based on the paper summary.
    
    Args:
        paper_info: Dictionary with paper metadata
        summary: Dictionary with summary data
    
    Returns:
        dict: Video script data
    """
    title = paper_info.get("title", "Research Paper")
    
    # Create an engaging intro
    intro = f"Today we're looking at an exciting research paper titled '{title}'. "
    
    if paper_info.get("authors"):
        if len(paper_info["authors"]) == 1:
            intro += f"This study by {paper_info['authors'][0]} "
        elif len(paper_info["authors"]) == 2:
            intro += f"This study by {paper_info['authors'][0]} and {paper_info['authors'][1]} "
        else:
            intro += f"This study by {paper_info['authors'][0]} and colleagues "
    
    if paper_info.get("year"):
        intro += f"published in {paper_info['year']} "
    
    # Add a compelling hook
    intro += "explores fascinating findings that could change how we understand this field. "
    
    # Main content from the summary
    main_content = summary.get("summary", "")
    
    # Highlight key insights
    insights_section = "Key takeaways from this research include: "
    for i, insight in enumerate(summary.get("key_insights", [])[:3]):
        insights_section += f"{i+1}) {insight} "
    
    # Conclusion
    conclusion = "This research contributes valuable insights to the field. "
    if paper_info.get("doi"):
        conclusion += f"For more details, check out the full paper using DOI: {paper_info['doi']}."
    
    # Put it all together
    script = {
        "title": title,
        "intro": intro,
        "main_content": main_content,
        "insights": insights_section,
        "conclusion": conclusion,
        "hashtags": summary.get("hashtags", ""),
        "keywords": summary.get("keywords", []),
        "full_script": f"{intro} {main_content} {insights_section} {conclusion}"
    }
    
    return script