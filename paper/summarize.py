# paper/summarize.py
import logging
import re
from typing import Dict, List, Optional
import nltk
from nltk.corpus import stopwords
from sklearn.feature_extraction.text import TfidfVectorizer
from collections import Counter
from transformers import pipeline

logger = logging.getLogger("paperbites.summarize")

# Initialize NLTK resources
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')
    
try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')

# Initialize summarizer
summarizer = None

def initialize_summarizer(model_name: str = "facebook/bart-large-cnn") -> None:
    """
    Initialize the summarization model.
    
    Args:
        model_name: Name of the pretrained model to use
    """
    global summarizer
    if summarizer is None:
        logger.info(f"Initializing summarizer model: {model_name}")
        try:
            summarizer = pipeline("summarization", model=model_name)
        except Exception as e:
            logger.error(f"Failed to initialize summarizer: {e}")
            # Fallback to a smaller model
            try:
                logger.info("Trying fallback model: sshleifer/distilbart-cnn-12-6")
                summarizer = pipeline("summarization", model="sshleifer/distilbart-cnn-12-6")
            except Exception as e:
                logger.error(f"Failed to initialize fallback summarizer: {e}")
                raise

def chunk_text(text: str, chunk_size: int = 1024) -> List[str]:
    """
    Split text into smaller chunks while preserving sentence boundaries.
    
    Args:
        text: Text to split
        chunk_size: Maximum chunk size in characters
        
    Returns:
        list: List of text chunks
    """
    # Split into sentences
    sentences = nltk.sent_tokenize(text)
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
    Extract key terms from text using TF-IDF.
    
    Args:
        text: Text to extract keywords from
        top_n: Number of keywords to extract
        
    Returns:
        list: List of keywords
    """
    stop_words = set(stopwords.words('english'))
    
    # Add custom stopwords relevant to academic papers
    custom_stops = {'et', 'al', 'fig', 'figure', 'table', 'eq', 'equation', 'ref',
                    'reference', 'cited', 'doi', 'journal', 'vol', 'volume',
                    'pp', 'page', 'author', 'authors', 'paper', 'study'}
    stop_words.update(custom_stops)
    
    # Create vectorizer
    vectorizer = TfidfVectorizer(
        stop_words=list(stop_words),
        ngram_range=(1, 2),  # Allow single words and bigrams
        max_df=0.85,         # Ignore terms that appear in >85% of documents
        min_df=2             # Ignore terms that appear in fewer than 2 documents
    )
    
    try:
        # Split text into sentences to create a "document" for each sentence
        sentences = nltk.sent_tokenize(text)
        
        # Skip if too few sentences
        if len(sentences) < 2:
            # Fallback to simple word frequency for very short texts
            words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
            words = [w for w in words if w not in stop_words]
            word_freq = Counter(words)
            return [word for word, freq in word_freq.most_common(top_n)]
        
        # Fit vectorizer
        X = vectorizer.fit_transform(sentences)
        
        # Get feature names
        feature_names = vectorizer.get_feature_names_out()
        
        # Sum TF-IDF scores across sentences for each term
        tfidf_sums = X.sum(axis=0).A1
        
        # Get top terms
        top_indices = tfidf_sums.argsort()[-top_n:][::-1]
        keywords = [feature_names[i] for i in top_indices]
        
        return keywords
    except Exception as e:
        logger.error(f"Error extracting keywords: {e}")
        return []

def rank_sentences(text: str, top_n: int = 3) -> List[str]:
    """
    Rank sentences by importance based on term frequency.
    
    Args:
        text: Text to analyze
        top_n: Number of sentences to return
        
    Returns:
        list: List of most important sentences
    """
    try:
        # Tokenize into sentences
        sentences = nltk.sent_tokenize(text)
        
        # Skip if too few sentences
        if len(sentences) <= top_n:
            return sentences
            
        # Get word frequencies (exclude stopwords)
        stop_words = set(stopwords.words('english'))
        words = [word.lower() for word in nltk.word_tokenize(text) 
                if word.lower() not in stop_words and word.isalnum()]
        word_freq = Counter(words)
        
        # Score sentences based on word frequencies
        sentence_scores = []
        for sentence in sentences:
            score = 0
            for word in nltk.word_tokenize(sentence.lower()):
                if word in word_freq:
                    score += word_freq[word]
            # Normalize by sentence length to avoid bias towards longer sentences
            sentence_scores.append((sentence, score / (len(nltk.word_tokenize(sentence)) + 1)))
        
        # Sort sentences by score
        sentence_scores.sort(key=lambda x: x[1], reverse=True)
        
        # Return top sentences
        return [sentence for sentence, score in sentence_scores[:top_n]]
    except Exception as e:
        logger.error(f"Error ranking sentences: {e}")
        return sentences[:top_n] if sentences else []

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

def summarize_paper(sections: Dict[str, str], max_length: int = 150) -> Dict:
    """
    Summarize paper with weighted importance for different sections.
    
    Args:
        sections: Dictionary of paper sections
        max_length: Maximum length of summary
        
    Returns:
        dict: Summarized paper data
    """
    # Initialize summarizer if not already done
    if summarizer is None:
        initialize_summarizer()
        
    # Define section weights
    section_weights = {
        "abstract": 3.0,      # Abstract is already summarized
        "introduction": 1.5,  # Introduction provides context
        "methods": 0.5,       # Methods less important for general audience
        "results": 2.0,       # Results are crucial
        "discussion": 2.5,    # Discussion contains implications
        "conclusion": 3.0,    # Conclusion is important
        "full_text": 1.0      # Fallback for unsectioned text
    }
    
    # Calculate proportional summary length for each section
    total_weight = sum(section_weights.get(s, 0) for s in sections.keys())
    section_lengths = {}
    
    for section in sections:
        weight = section_weights.get(section, 1.0)
        # Ensure minimum length of 30 for each section
        section_lengths[section] = max(30, int(max_length * weight / total_weight))
    
    # Summarize each section
    section_summaries = {}
    for section_name, text in sections.items():
        try:
            # Skip if text is too short to summarize meaningfully
            if len(text) < 100:
                section_summaries[section_name] = text
                continue
                
            # Split into chunks if needed
            chunks = chunk_text(text)
            chunk_summaries = []
            
            for chunk in chunks:
                chunk_length = min(section_lengths[section_name], len(chunk) // 4)
                if chunk_length < 10:  # Too short to summarize
                    chunk_summaries.append(chunk)
                    continue
                    
                # Generate summary for this chunk
                summary = summarizer(
                    chunk, 
                    max_length=chunk_length, 
                    min_length=min(10, chunk_length),
                    do_sample=False
                )
                
                if summary:
                    chunk_summaries.append(summary[0]['summary_text'])
            
            # Combine chunk summaries
            section_summaries[section_name] = " ".join(chunk_summaries)
            
        except Exception as e:
            logger.error(f"Error summarizing {section_name}: {e}")
            # Use first few sentences as fallback
            sentences = nltk.sent_tokenize(text)
            num_sentences = min(3, len(sentences))
            section_summaries[section_name] = " ".join(sentences[:num_sentences])
    
    # Create combined summary with priority to abstract/introduction
    combined_summary = ""
    for section in ["abstract", "introduction", "results", "discussion", "conclusion", "full_text"]:
        if section in section_summaries:
            combined_summary += section_summaries[section] + " "
    
    # Limit to max_length if needed
    if len(combined_summary) > max_length * 10:  # Approximate character limit
        sentences = nltk.sent_tokenize(combined_summary)
        cumulative_length = 0
        final_sentences = []
        
        for sentence in sentences:
            cumulative_length += len(sentence)
            if cumulative_length <= max_length * 10:
                final_sentences.append(sentence)
            else:
                break
                
        combined_summary = " ".join(final_sentences)
    
    # Extract keywords from the summary
    keywords = extract_keywords(combined_summary)
    
    # Rank sentences to find key insights
    key_sentences = rank_sentences(combined_summary)
    
    # Return results
    return {
        "summary": combined_summary.strip(),
        "key_insights": key_sentences,
        "keywords": keywords,
        "hashtags": format_hashtags(keywords)
    }