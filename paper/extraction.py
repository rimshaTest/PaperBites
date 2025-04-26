# paper/extraction.py
import fitz  # PyMuPDF
import pytesseract
from pdf2image import convert_from_path
import logging
import os
from typing import List, Dict, Optional

logger = logging.getLogger("paperbites.extraction")

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
                break

def extract_text_from_pdf(pdf_path: str, use_ocr: bool = True) -> str:
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
        
        # Extract text from each page
        for page_num, page in enumerate(doc):
            page_text = page.get_text("text")
            text += page_text + "\n\n"
            
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
        logger.info(f"Converting PDF to images for OCR...")
        images = convert_from_path(pdf_path)
        logger.info(f"Generated {len(images)} images from PDF")
        
        # Process images in batches to avoid memory issues
        text_parts = []
        for i, img in enumerate(images):
            if i % 5 == 0:
                logger.info(f"OCR processing page {i+1}/{len(images)}...")
            try:
                text_parts.append(pytesseract.image_to_string(img))
            except Exception as e:
                logger.error(f"OCR error on page {i+1}: {e}")
                
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
        "abstract": r"(?:abstract|summary)(?:\n|:|\s{2,})(.*?)(?:\n\n|\n[A-Z])",
        "introduction": r"(?:introduction|background)(?:\n|:|\s{2,})(.*?)(?:\n\n|\n[A-Z])",
        "methods": r"(?:methods|methodology|materials and methods)(?:\n|:|\s{2,})(.*?)(?:\n\n|\n[A-Z])",
        "results": r"(?:results|findings)(?:\n|:|\s{2,})(.*?)(?:\n\n|\n[A-Z])",
        "discussion": r"(?:discussion|conclusion|implications)(?:\n|:|\s{2,})(.*?)(?:\n\n|\n[A-Z])",
    }
    
    import re
    sections = {}
    for name, pattern in section_patterns.items():
        match = re.search(pattern, full_text, re.IGNORECASE | re.DOTALL)
        if match:
            sections[name] = match.group(1).strip()
    
    # If no sections were found, use the whole text
    if not sections:
        sections["full_text"] = full_text
        
    return sections