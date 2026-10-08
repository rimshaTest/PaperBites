"""Add-a-paper-by-photo: read as much as possible off a picture of a paper, then find it.

1. read_image() pulls everything legible from the image - title, authors, venue, year, DOI,
   abstract, other text. Gemini vision does the reading (paper.summarize.extract_image_details);
   if Gemini is unavailable or reads nothing, local OCR (Tesseract, if installed) supplies raw
   text instead, so a Gemini outage doesn't make the feature useless.
2. find_candidates() looks the paper up several ways and merges the results:
     a. an exact DOI lookup, if a DOI was readable (most reliable);
     b. papers already in the library, ranked by embedding similarity to what was read
        (paper.embeddings) - catches papers the app already has, however the page was cropped;
     c. a Crossref bibliographic search on the title/authors/venue (or, with only OCR text, the
        start of that text).
   Candidates come back in the same shape paper.citation.search_citation() returns, so the
   existing confirm-and-save flow is unchanged. Library matches carry in_library=True.
"""
import io
import json
import logging
import re
from typing import Dict, List, Optional

import aiohttp

logger = logging.getLogger("paperbites.photo_scan")

# Cosine similarity a stored paper must reach to be offered as a match. Title-vs-title (or title
# plus abstract) comparisons of the same paper score far above unrelated papers; this keeps
# loosely-related papers out of the list.
LIBRARY_MATCH_THRESHOLD = 0.72
MAX_LIBRARY_MATCHES = 3
# Newest stored papers considered for embedding comparison - keeps one scan's memory and
# comparison cost bounded as the library grows.
MAX_LIBRARY_SCAN = 3000
MAX_QUERY_CHARS = 500
EMBED_QUERY_CHARS = 2000

_DOI_RE = re.compile(r"10\.\d{4,9}/[-._;()/:A-Za-z0-9]+")
_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)


def clean_doi(value: Optional[str]) -> Optional[str]:
    """A DOI exactly as printed may carry a 'doi:' prefix, a doi.org URL, or trailing
    punctuation from the sentence it sat in; return the bare DOI, or None."""
    if not value:
        return None
    match = _DOI_RE.search(value)
    return match.group(0).rstrip(").,;:") if match else None


def parse_image_details(raw: Optional[str]) -> Dict:
    """Parse Gemini's reply into {title, authors, venue, year, doi, abstract, text}. Tolerates
    markdown fences and a reply that isn't JSON at all (the whole reply is then kept as `text`).
    Missing fields come back as ''/[] so callers never need to check types."""
    details = {"title": "", "authors": [], "venue": "", "year": "", "doi": None, "abstract": "", "text": ""}
    if not raw or not raw.strip():
        return details

    cleaned = _FENCE_RE.sub("", raw.strip()).strip()
    data = None
    try:
        data = json.loads(cleaned)
    except ValueError:
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start != -1 and end > start:
            try:
                data = json.loads(cleaned[start:end + 1])
            except ValueError:
                data = None

    if not isinstance(data, dict):
        details["text"] = cleaned
    else:
        def text(key):
            value = data.get(key)
            return re.sub(r"\s+", " ", value).strip() if isinstance(value, str) else ""

        authors = data.get("authors")
        if isinstance(authors, str):
            authors = [a.strip() for a in re.split(r",|;| and ", authors) if a.strip()]
        details["authors"] = [a.strip() for a in authors if isinstance(a, str) and a.strip()] if isinstance(authors, list) else []
        for key in ("title", "venue", "year", "abstract", "text"):
            details[key] = text(key)
        details["doi"] = clean_doi(data.get("doi") if isinstance(data.get("doi"), str) else None)

    # A DOI printed in the body text still counts
    if not details["doi"]:
        details["doi"] = clean_doi(" ".join([details["text"], details["abstract"]]))
    return details


def ocr_image_text(image_bytes: bytes) -> str:
    """Raw text from local OCR, or '' if Pillow/pytesseract/Tesseract aren't available or the
    image can't be read. Never raises - OCR is a best-effort fallback."""
    try:
        import pytesseract
        from PIL import Image
        from paper.extraction import configure_tesseract

        configure_tesseract()
        with Image.open(io.BytesIO(image_bytes)) as image:
            image = image.convert("L")  # grayscale OCRs better and is smaller
            return pytesseract.image_to_string(image, lang="eng") or ""
    except Exception as e:
        logger.info(f"Local OCR unavailable or failed ({type(e).__name__}): {e}")
        return ""


async def read_image(image_bytes: bytes, mime_type: str) -> Dict:
    """Read everything legible from the image. Returns the parse_image_details() dict plus
    `source`: "gemini", "ocr", or None if nothing could be read."""
    from paper.summarize import extract_image_details

    details = parse_image_details(await extract_image_details(image_bytes, mime_type))
    if details["title"] or details["doi"] or details["abstract"] or details["text"]:
        details["source"] = "gemini"
        return details

    text = ocr_image_text(image_bytes)
    details = parse_image_details(None)
    if text.strip():
        details["text"] = re.sub(r"\s+", " ", text).strip()
        details["doi"] = clean_doi(details["text"])
        details["source"] = "ocr"
        return details
    details["source"] = None
    return details


def citation_query(details: Dict) -> str:
    """One search string from what was read: title, first authors, venue, year; or, when no
    title was read (OCR-only), the start of the raw text."""
    if details.get("title"):
        parts = [details["title"], ", ".join(details.get("authors", [])[:3]), details.get("venue", ""), details.get("year", "")]
        return " ".join(p for p in parts if p)[:MAX_QUERY_CHARS]
    fallback = details.get("abstract") or details.get("text") or ""
    return fallback[:MAX_QUERY_CHARS].strip()


def embedding_query(details: Dict) -> str:
    """Text to embed for the library comparison: title and abstract when read (the same
    title+description shape stored papers are embedded from), else whatever text was read."""
    if details.get("title"):
        return "\n\n".join(p for p in (details["title"], details.get("abstract", "")) if p)[:EMBED_QUERY_CHARS]
    return (details.get("abstract") or details.get("text") or "")[:EMBED_QUERY_CHARS]


def _candidate_from_stored(doc: Dict) -> Dict:
    authors = [a.get("name") if isinstance(a, dict) else a for a in doc.get("authors") or []]
    return {
        "doi": doc.get("doi"),
        "title": doc.get("title"),
        "authors": [a for a in authors if a],
        "journal": doc.get("journal"),
        "published_date": doc.get("published_date"),
        "url": doc.get("url"),
        "is_open_access": doc.get("is_open_access"),
        "language": doc.get("language"),
        "in_library": True,
    }


async def library_matches(details: Dict) -> List[Dict]:
    """Stored papers most similar to what was read, by embedding similarity. Papers with no DOI
    are skipped - the confirm step identifies a paper by its DOI."""
    query = embedding_query(details)
    if len(query) < 10:
        return []
    try:
        import db
        from paper.embeddings import score_documents

        projection = {"title": 1, "authors": 1, "doi": 1, "journal": 1, "published_date": 1, "url": 1,
                      "is_open_access": 1, "language": 1, "embedding": 1, "embedding_model": 1}
        docs = list(
            db.get_db().papers.find({"embedding": {"$exists": True, "$ne": None}}, projection)
            .sort("published_date", -1).limit(MAX_LIBRARY_SCAN)
        )
        if not docs:
            return []
        scored = await score_documents(query, docs)
    except Exception as e:
        logger.warning(f"Library embedding match skipped: {type(e).__name__}: {e}")
        return []
    return [_candidate_from_stored(doc) for score, doc in scored if score >= LIBRARY_MATCH_THRESHOLD and doc.get("doi")][:MAX_LIBRARY_MATCHES]


def _merge(groups: List[List[Dict]], max_results: int) -> List[Dict]:
    """Concatenate candidate lists in priority order, dropping repeats (same DOI, else same
    title) so a paper found two ways appears once, at its highest-priority position."""
    seen, merged = set(), []
    for group in groups:
        for candidate in group:
            key = (candidate.get("doi") or "").lower() or (candidate.get("title") or "").strip().lower()
            if not key or key in seen:
                continue
            seen.add(key)
            merged.append(candidate)
    return merged[:max_results]


async def find_candidates(details: Dict, max_results: int = 6) -> List[Dict]:
    """Look the paper up every way we can (exact DOI, library embeddings, Crossref search) and
    return merged candidates, best first."""
    from paper.citation import _HTTP_TIMEOUT, _lookup_doi, _search_crossref_bibliographic

    by_doi: List[Dict] = []
    by_text: List[Dict] = []
    query = citation_query(details)

    async with aiohttp.ClientSession(timeout=_HTTP_TIMEOUT) as session:
        if details.get("doi"):
            try:
                found = await _lookup_doi(session, details["doi"])
                by_doi = [found] if found else []
            except Exception as e:
                logger.warning(f"DOI lookup failed for '{details['doi']}': {e}")
        if query:
            try:
                by_text = await _search_crossref_bibliographic(session, query, 5)
            except Exception as e:
                logger.warning(f"Crossref search failed: {e}")

    stored = await library_matches(details)
    return _merge([by_doi, stored, by_text], max_results)


async def scan_image(image_bytes: bytes, mime_type: str) -> Dict:
    """Whole flow. Returns {extracted, details, candidates}; `extracted` is the search string
    that was read (shown in the input box), or None if nothing could be read."""
    details = await read_image(image_bytes, mime_type)
    query = citation_query(details)
    if not (query or details.get("doi")):
        return {"extracted": None, "details": details, "candidates": []}
    candidates = await find_candidates(details)
    return {"extracted": query or details["doi"], "details": details, "candidates": candidates}
