# paper/citation.py
"""Add-a-paper-by-citation pipeline (docs/TECHNICAL_SPEC.md's "Add-Paper Ingestion Pipeline").

Two steps, matching the spec's confirm-dialog flow:
1. search_citation() sends a raw pasted citation (MLA, APA, or any other style) straight to
   Crossref's `query.bibliographic` fuzzy search and returns the top candidate matches. Crossref's
   bibliographic matching already tolerates format differences (punctuation, field order, "et
   al.", etc.) well enough that parsing the citation style first (e.g. via a library like
   anystyle) would be redundant complexity for the same result - the spec calls this out as an
   acceptable shortcut.
2. add_paper_from_citation() takes the one candidate the user confirmed and runs it through the
   same enrichment pipeline paper/latest.py's discovery feed uses (abstract fallback, language
   detection/translation, card image) - except the summary and category are produced together by
   one Gemini call (paper.summarize.summarize_and_classify_paper) rather than the user picking a
   category by hand: the discovery feed already knows a paper's category from the search query
   that found it, but a citation-added paper doesn't, so the same read that produces the summary
   also classifies it.
"""
import asyncio
import logging
import urllib.parse
from typing import Dict, List, Optional

import aiohttp

from config import Config
from paper.latest import (
    CATEGORIES,
    _HTTP_TIMEOUT,
    _apply_language_and_translation,
    _attach_images,
    _crossref_published_date,
    _fill_missing_abstracts,
    _get_json_with_retry,
    fetch_crossref_abstract,
    fetch_unpaywall_oa_location,
)
from paper.summarize import summarize_and_classify_paper

config_instance = Config()
logger = logging.getLogger("paperbites.citation")


async def search_citation(raw_citation: str, max_results: int = 5) -> List[Dict]:
    """Fuzzy-match a raw pasted citation against Crossref, returning candidate matches with a
    confirmed open-access link/status resolved via Unpaywall for each - so the confirm dialog can
    show whether a match is actually readable before the user picks it.
    """
    raw_citation = (raw_citation or "").strip()
    if not raw_citation:
        return []

    email = config_instance.get("api.email")
    url = (
        "https://api.crossref.org/works"
        f"?query.bibliographic={urllib.parse.quote(raw_citation)}"
        f"&rows={max_results}"
    )
    if email:
        url += f"&mailto={urllib.parse.quote(email)}"

    async with aiohttp.ClientSession(timeout=_HTTP_TIMEOUT) as session:
        data = await _get_json_with_retry(session, url, "Crossref")
        if not data:
            return []

        candidates = []
        for item in (data.get("message") or {}).get("items", [])[:max_results]:
            titles = item.get("title") or []
            if not titles:
                continue

            authors = []
            for a in item.get("author", []):
                name = " ".join(part for part in [a.get("given"), a.get("family")] if part)
                if name:
                    authors.append(name)

            journals = item.get("container-title") or []

            candidates.append({
                "doi": item.get("DOI"),
                "title": titles[0],
                "authors": authors,
                "journal": journals[0] if journals else None,
                "published_date": _crossref_published_date(item),
                "url": item.get("URL"),
                "is_open_access": None,
            })

        async def resolve(candidate: Dict) -> None:
            if not candidate["doi"]:
                candidate["is_open_access"] = False
                return
            location = await fetch_unpaywall_oa_location(session, candidate["doi"])
            if location:
                candidate["url"] = location["url"] or candidate["url"]
                candidate["is_open_access"] = True
            else:
                candidate["is_open_access"] = False

        await asyncio.gather(*(resolve(c) for c in candidates))

    return candidates


async def add_paper_from_citation(candidate: Dict) -> Dict:
    """Build a full paper record from a confirmed citation-search candidate and run it through
    the discovery feed's own enrichment pipeline, so it's stored and served identically to any
    other paper - except its category comes from the same Gemini read that produces its summary,
    not from the user. Raises ValueError on bad input (missing DOI, or a paper that ends up with
    no usable description/category from any source).
    """
    doi = (candidate or {}).get("doi")
    if not doi:
        raise ValueError("A DOI is required to add a paper by citation")

    async with aiohttp.ClientSession(timeout=_HTTP_TIMEOUT) as session:
        # fetch_crossref_abstract already strips JATS tags and runs clean_abstract().
        abstract = await fetch_crossref_abstract(session, doi) or ""

    paper = {
        "source": "crossref",
        "source_id": doi,
        "title": candidate.get("title") or "Untitled",
        "authors": [{"id": None, "name": name} for name in candidate.get("authors") or []],
        "abstract": abstract,
        "citation_count": 0,
        "published_date": candidate.get("published_date"),
        "categories": [],
        "journal": candidate.get("journal"),
        "publication_type": "journal",
        "is_open_access": candidate.get("is_open_access"),
        "doi": doi,
        "url": candidate.get("url"),
    }

    combined = [paper]
    combined = await _fill_missing_abstracts(combined)
    await _apply_language_and_translation(combined)

    async with aiohttp.ClientSession(timeout=_HTTP_TIMEOUT) as session:
        result = await summarize_and_classify_paper(session, paper, CATEGORIES)

    if result:
        paper["description"] = result["summary"]
        paper["categories"] = [result["category"]]
    else:
        # No Gemini key, or every model failed - fall back to the raw abstract like the
        # discovery feed does, and leave the paper uncategorized rather than guessing.
        paper["description"] = paper.get("abstract") or ""
        logger.warning(f"Could not classify category for '{paper['title']}' - saving uncategorized")

    if not paper.get("description"):
        raise ValueError("Could not generate a description for this paper (no abstract or full text available)")

    await _attach_images(combined, paper["categories"][0] if paper["categories"] else paper["title"])

    return paper
