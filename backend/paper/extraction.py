# paper/extraction.py
import fitz  # PyMuPDF
import pytesseract
from pdf2image import convert_from_path
import logging
import os
import re
from typing import List, Dict, Optional, Tuple
import concurrent.futures
from config import Config

logger = logging.getLogger("paperbites.extraction")
config = Config()

def configure_tesseract(tesseract_cmd_path: Optional[str] = None) -> None:
    """
    Configure Tesseract OCR with the correct path.
    
    Args:
        tesseract_cmd_path: Path to Tesseract executable
    """
    if tesseract_cmd_path:
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd_path
    elif os.name == 'nt':  # Windows
        default_paths = [
            r'C:\Program Files\Tesseract-OCR\tesseract.exe',
            r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe'
        ]
        for path in default_paths:
            if os.path.exists(path):
                pytesseract.pytesseract.tesseract_cmd = path
                logger.info(f"Using Tesseract from: {path}")
                break
    
    # Get from config
    config_path = config.get("paths.tesseract_cmd")
    if config_path and os.path.exists(config_path):
        pytesseract.pytesseract.tesseract_cmd = config_path
        logger.info(f"Using Tesseract from config: {config_path}")

def extract_text_from_pdf_page(page) -> str:
    """
    Extract text from a single PDF page.
    
    Args:
        page: PyMuPDF page object
        
    Returns:
        str: Extracted text
    """
    try:
        return page.get_text("text")
    except Exception as e:
        logger.error(f"Error extracting text from page: {e}")
        return ""

def extract_text_from_pdf(pdf_path: str, use_ocr: bool = False) -> str:
    """
    Extract text from PDF with OCR fallback.
    
    Args:
        pdf_path: Path to PDF file
        use_ocr: Whether to use OCR if text extraction fails
        
    Returns:
        str: Extracted text
    """
    try:
        # First try PyMuPDF (faster)
        doc = fitz.open(pdf_path)
        text = ""
        
        # Process pages in parallel for faster extraction
        with concurrent.futures.ThreadPoolExecutor() as executor:
            page_texts = list(executor.map(extract_text_from_pdf_page, doc))
            text = "\n\n".join(page_texts)
            
        # If we got meaningful text, return it
        if len(text.strip()) > 200:
            logger.info(f"Successfully extracted text from PDF using PyMuPDF")
            return text
            
        # If text extraction yielded too little text, fall back to OCR
        if use_ocr:
            logger.info(f"Text extraction yielded limited results, trying OCR...")
            return extract_text_with_ocr(pdf_path)
        else:
            return text
            
    except fitz.FileDataError:
        logger.error(f"Corrupt PDF file: {pdf_path}")
        if use_ocr:
            logger.info(f"Attempting OCR as fallback...")
            return extract_text_with_ocr(pdf_path)
        return ""
        
    except Exception as e:
        logger.error(f"PDF processing error ({type(e).__name__}): {e}")
        if use_ocr:
            logger.info(f"Attempting OCR as fallback...")
            return extract_text_with_ocr(pdf_path)
        return ""

def extract_text_with_ocr(pdf_path: str) -> str:
    """
    Extract text from PDF using OCR.
    
    Args:
        pdf_path: Path to PDF file
        
    Returns:
        str: Extracted text
    """
    try:
        # Make sure tesseract is configured
        configure_tesseract()
        
        logger.info(f"Converting PDF to images for OCR...")
        images = convert_from_path(pdf_path, dpi=300, first_page=1, last_page=15)  # Limit pages for speed
        logger.info(f"Generated {len(images)} images from PDF")
        
        # Process images in parallel to speed up OCR
        text_parts = []
        
        def process_image(img_data):
            idx, img = img_data
            try:
                text = pytesseract.image_to_string(img, lang='eng')
                logger.info(f"OCR completed for page {idx+1}")
                return text
            except Exception as e:
                logger.error(f"OCR error on page {idx+1}: {e}")
                return ""
        
        # Process images in parallel
        with concurrent.futures.ThreadPoolExecutor() as executor:
            results = executor.map(process_image, enumerate(images))
            text_parts = list(results)
                
        full_text = "\n\n".join(text_parts)
        logger.info(f"OCR extraction complete: {len(full_text)} characters extracted")
        return full_text
        
    except Exception as e:
        logger.error(f"OCR processing failed: {e}")
        return ""

def extract_paper_sections(full_text: str) -> Dict[str, str]:
    """
    Extract meaningful sections from research paper text.
    
    Args:
        full_text: Full text of paper
        
    Returns:
        dict: Dictionary of section name to section text
    """
    # Common section headers in research papers
    section_patterns = {
        "abstract": r"(?:abstract|summary)(?:\n|:|\s{2,})(.*?)(?:\n\n|\n[A-Z0-9][a-zA-Z0-9\s]*\n)",
        "introduction": r"(?:introduction|background)(?:\n|:|\s{2,})(.*?)(?:\n\n|\n[A-Z0-9][a-zA-Z0-9\s]*\n)",
        "methods": r"(?:methods|methodology|materials and methods|experimental setup)(?:\n|:|\s{2,})(.*?)(?:\n\n|\n[A-Z0-9][a-zA-Z0-9\s]*\n)",
        "results": r"(?:results|findings|observations)(?:\n|:|\s{2,})(.*?)(?:\n\n|\n[A-Z0-9][a-zA-Z0-9\s]*\n)",
        "discussion": r"(?:discussion|implications|conclusion)(?:\n|:|\s{2,})(.*?)(?:\n\n|\n[A-Z0-9][a-zA-Z0-9\s]*\n)",
        "conclusion": r"(?:conclusion|conclusions)(?:\n|:|\s{2,})(.*?)(?:\n\n|\n[A-Z0-9][a-zA-Z0-9\s]*\n)"
    }
    
    sections = {}
    for name, pattern in section_patterns.items():
        try:
            matches = re.finditer(pattern, full_text, re.IGNORECASE | re.DOTALL)
            for match in matches:
                # We'll take the first match for each section type
                if name not in sections:
                    text = match.group(1).strip()
                    # Only add if we have substantial content
                    if len(text) > 50:
                        sections[name] = text
                        break
        except Exception as e:
            logger.error(f"Error extracting {name} section: {e}")
    
    # If no sections were found, use the whole text
    if not sections:
        # Try to at least find an abstract
        abstract_match = re.search(r"abstract(?:\n|:|\s{2,})(.*?)(?:\n\n)", full_text, re.IGNORECASE | re.DOTALL)
        if abstract_match:
            sections["abstract"] = abstract_match.group(1).strip()
        
        # Add the full text
        sections["full_text"] = full_text
        
    # If we have multiple sections but no abstract, try to extract it from the beginning
    if "full_text" not in sections and "abstract" not in sections:
        # Try to extract an abstract from the first part of the paper
        first_1000 = full_text[:1000]
        abstract_match = re.search(r"abstract(?:\n|:|\s{2,})(.*?)(?:\n\n)", first_1000, re.IGNORECASE | re.DOTALL)
        if abstract_match:
            sections["abstract"] = abstract_match.group(1).strip()
    
    return sections

def clean_extracted_text(text: str) -> str:
    """
    Clean extracted text by removing excessive whitespace, fixing common OCR issues, etc.
    
    Args:
        text: Raw text to clean
        
    Returns:
        str: Cleaned text
    """
    # Replace multiple spaces/tabs with a single space
    text = re.sub(r'\s+', ' ', text)
    
    # Fix hyphenated words split across lines
    text = re.sub(r'(\w+)-\s+(\w+)', r'\1\2', text)
    
    # Fix common OCR errors
    text = text.replace('|', 'I')
    text = text.replace('1', 'I')
    
    # Remove reference markers like [1], [2,3], etc.
    text = re.sub(r'\[\d+(?:,\s*\d+)*\]', '', text)
    
    return text.strip()

def extract_main_content(pdf_path: str) -> Dict[str, str]:
    """
    Extract the main content from a PDF file.
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        dict: Dictionary with sections of the paper
    """
    logger.info(f"Extracting content from: {pdf_path}")
    
    # First try without OCR
    text = extract_text_from_pdf(pdf_path, use_ocr=False)
    
    # If we didn't get enough text, try with OCR
    if len(text) < 1000:
        logger.info(f"Initial extraction yielded insufficient text ({len(text)} chars). Using OCR...")
        text = extract_text_from_pdf(pdf_path, use_ocr=True)
    
    # Clean the extracted text
    text = clean_extracted_text(text)
    
    # Extract sections
    sections = extract_paper_sections(text)
    
    # If we don't have many sections, try OCR even if we got text before
    if len(sections) <= 2 and "full_text" in sections and not sections.get("abstract"):
        logger.info(f"Few sections found. Trying OCR for better extraction...")
        text = extract_text_with_ocr(pdf_path)
        text = clean_extracted_text(text)
        sections = extract_paper_sections(text)
    
    return sections