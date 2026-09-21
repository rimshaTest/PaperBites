# paper/latest.py
"""Fetch the latest research papers from free, official APIs (Semantic Scholar, OpenAlex).

This is separate from paper/search.py's query-driven search, which does Unpaywall/license
enrichment for the video-generation pipeline. This module only surfaces metadata (title,
authors, abstract, citation count, link) for display as cards - no PDF hosting/redistribution -
so it does not need the open-access/license gating that search.py's pipeline requires.
"""
import asyncio
import datetime
import logging
import re
import urllib.parse
from typing import Dict, List, Optional

import aiohttp
from langdetect import DetectorFactory, LangDetectException, detect_langs

from config import Config
from paper.summarize import summarize_paper

# Every aiohttp call in this module uses this timeout - a slow/hanging third-party API
# should never be able to stall the whole fetch pipeline indefinitely. This matters especially
# for translation (below): an earlier version wrapped the synchronous `deep_translator` library
# in a thread-pool-based timeout, but that only bounded how long *this code* waited - it could
# not actually stop a genuinely stuck `requests` call from permanently occupying its worker
# thread, which (with a small worker pool) eventually wedged the whole pipeline. Calling
# MyMemory's plain HTTP API directly via aiohttp sidesteps that entirely: aiohttp's timeout is
# enforced by the event loop itself, not by hoping a worker thread cooperates.
_HTTP_TIMEOUT = aiohttp.ClientTimeout(total=15)

# langdetect's detection is non-deterministic run-to-run unless seeded.
DetectorFactory.seed = 0

config_instance = Config()
logger = logging.getLogger("paperbites.latest")

# Fixed list of categories, used both as search terms against the free APIs and as the
# topic list shown in the app's Interests screen.
CATEGORIES = [
    "Artificial Intelligence",
    "Medicine",
    "Physics",
    "Biology",
    "Psychology",
    "Climate Science",
    "Economics",
    "Neuroscience",
]


def _parse_date(value: Optional[str]) -> Optional[datetime.date]:
    if not value:
        return None
    try:
        return datetime.date.fromisoformat(value[:10])
    except ValueError:
        return None


def _is_plausible_recent_date(value: Optional[str], since: datetime.date) -> bool:
    """Reject missing/unparseable dates, dates before `since`, and future dates.

    Both OpenAlex and Semantic Scholar occasionally carry bogus far-future
    `publication_date` values (e.g. in-press placeholders), which would otherwise
    sort to the top of a "latest papers" feed.
    """
    parsed = _parse_date(value)
    if not parsed:
        return False
    return since <= parsed <= datetime.date.today()


async def _get_json_with_retry(
    session: aiohttp.ClientSession,
    url: str,
    source_name: str,
    headers: Optional[Dict[str, str]] = None,
    max_retries: int = 2,
    default_backoff: float = 15.0,
) -> Optional[Dict]:
    """GET a URL as JSON, retrying once or twice on 429 (both free APIs rate-limit anonymous traffic)."""
    for attempt in range(max_retries + 1):
        try:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    return await response.json()

                if response.status == 429 and attempt < max_retries:
                    body = await response.json(content_type=None)
                    wait_seconds = (body or {}).get("retryAfter", default_backoff)
                    logger.warning(
                        f"{source_name} rate-limited for '{url}', retrying in {wait_seconds}s "
                        f"(attempt {attempt + 1}/{max_retries})"
                    )
                    await asyncio.sleep(wait_seconds)
                    continue

                logger.error(f"{source_name} error {response.status} for '{url}'")
                return None
        except Exception as e:
            logger.error(f"Error fetching from {source_name}: {e}")
            return None

    return None


def _semantic_scholar_authors(item: Dict) -> List[Dict]:
    """Normalize Semantic Scholar authors into {id, name} - id is None if SS has no canonical author record."""
    authors = []
    for a in item.get("authors", []):
        name = a.get("name")
        if not name:
            continue
        author_id = a.get("authorId")
        authors.append({
            "id": f"semantic_scholar:{author_id}" if author_id else None,
            "name": name,
        })
    return authors


def _semantic_scholar_publication_type(item: Dict) -> str:
    """Normalize Semantic Scholar's publicationTypes list into 'journal' | 'conference' | 'other'."""
    types = item.get("publicationTypes") or []
    if "Conference" in types:
        return "conference"
    if "JournalArticle" in types:
        return "journal"
    return "other"


async def fetch_latest_semantic_scholar(category: str, since: datetime.date, limit: int) -> List[Dict]:
    """Search Semantic Scholar for recent, open-access, journal/conference papers in a category, newest first."""
    fields = (
        "title,authors.authorId,authors.name,abstract,citationCount,publicationDate,"
        "externalIds,url,openAccessPdf,venue,isOpenAccess,publicationTypes"
    )
    today = datetime.date.today()
    year_range = f"{since.year}-{today.year}"
    # Fetch more than `limit` since the open-access/journal-or-conference filter below narrows results.
    fetch_size = min(limit * 3, 100)
    url = (
        "https://api.semanticscholar.org/graph/v1/paper/search"
        f"?query={urllib.parse.quote(category)}&year={year_range}&limit={fetch_size}&fields={fields}"
    )

    # Unauthenticated requests share a very low, easy-to-exhaust rate limit; a free API key
    # (https://www.semanticscholar.org/product/api#api-key-form) raises it substantially.
    headers = {"Accept": "application/json"}
    api_key = config_instance.get("api.semantic_scholar_key")
    if api_key:
        headers["x-api-key"] = api_key

    async with aiohttp.ClientSession(timeout=_HTTP_TIMEOUT) as session:
        data = await _get_json_with_retry(session, url, "Semantic Scholar", headers=headers)

    if not data:
        return []

    results = []
    for item in data.get("data", []):
        if not _is_plausible_recent_date(item.get("publicationDate"), since):
            continue
        if not item.get("isOpenAccess"):
            continue

        publication_type = _semantic_scholar_publication_type(item)
        if publication_type == "other":
            continue

        authors = _semantic_scholar_authors(item)
        if not authors:
            continue

        results.append({
            "source": "semantic_scholar",
            "source_id": item.get("paperId", ""),
            "title": item.get("title") or "Untitled",
            "authors": authors,
            "abstract": item.get("abstract") or "",
            "citation_count": item.get("citationCount") or 0,
            "published_date": item.get("publicationDate"),
            "categories": [category],
            "journal": item.get("venue") or None,
            "publication_type": publication_type,
            "is_open_access": True,
            "doi": (item.get("externalIds") or {}).get("DOI"),
            "url": item.get("url") or (item.get("openAccessPdf") or {}).get("url"),
        })

    results.sort(key=lambda p: p.get("published_date") or "", reverse=True)
    return results[:limit]


def reconstruct_openalex_abstract(inverted_index: Optional[Dict[str, List[int]]]) -> str:
    """OpenAlex returns abstracts as {word: [positions]} instead of plain text - rebuild it."""
    if not inverted_index:
        return ""

    positions = []
    for word, indices in inverted_index.items():
        for index in indices:
            positions.append((index, word))

    positions.sort(key=lambda p: p[0])
    return " ".join(word for _, word in positions)


def _openalex_best_venue(item: Dict) -> Dict:
    """Find the best journal/conference venue for a work.

    OpenAlex's `primary_location` is often whichever host it indexed first - frequently a
    preprint repository like arXiv - even when the same work also has a real journal or
    conference publication listed among its other `locations`. Scan all locations (primary
    first) for one whose source type is journal/conference before giving up.
    """
    candidates = [item.get("primary_location")] + (item.get("locations") or [])
    for location in candidates:
        source = (location or {}).get("source") or {}
        if source.get("type") in ("journal", "conference"):
            return {"type": source["type"], "name": source.get("display_name")}
    return {"type": "other", "name": None}


async def fetch_latest_openalex(
    category: str, since: datetime.date, limit: int, sort_by: str = "date"
) -> List[Dict]:
    """Search OpenAlex for open-access, journal/conference papers in a category.

    `sort_by` is "date" (newest first - the normal "latest papers" feed) or "citations"
    (most-cited first within the date window - useful for testing/demoing the citation-count
    UI, since truly recent papers rarely have accumulated any citations yet).
    """
    email = config_instance.get("api.email")
    today = datetime.date.today()
    # Fetch more than `limit` since the open-access/journal-or-conference filter below narrows results.
    fetch_size = min(limit * 3, 100)
    sort_param = "cited_by_count:desc" if sort_by == "citations" else "publication_date:desc"
    url = (
        "https://api.openalex.org/works"
        f"?search={urllib.parse.quote(category)}"
        f"&filter=from_publication_date:{since.isoformat()},to_publication_date:{today.isoformat()},is_oa:true,type:article"
        f"&sort={sort_param}"
        f"&per_page={fetch_size}"
    )
    if email:
        url += f"&mailto={urllib.parse.quote(email)}"

    api_key = config_instance.get("api.openalex_key")
    if api_key:
        url += f"&api_key={urllib.parse.quote(api_key)}"

    async with aiohttp.ClientSession(timeout=_HTTP_TIMEOUT) as session:
        data = await _get_json_with_retry(session, url, "OpenAlex")

    if not data:
        return []

    results = []
    for item in data.get("results", []):
        if not _is_plausible_recent_date(item.get("publication_date"), since):
            continue
        if not (item.get("open_access") or {}).get("is_oa"):
            continue

        venue = _openalex_best_venue(item)
        if venue["type"] == "other":
            continue

        authors = []
        for a in item.get("authorships", []):
            author = a.get("author") or {}
            name = author.get("display_name")
            if not name:
                continue
            author_url = author.get("id") or ""
            author_id = author_url.rsplit("/", 1)[-1] if author_url else None
            authors.append({
                "id": f"openalex:{author_id}" if author_id else None,
                "name": name,
            })

        if not authors:
            continue

        results.append({
            "source": "openalex",
            "source_id": (item.get("id") or "").rsplit("/", 1)[-1],
            "title": item.get("title") or item.get("display_name") or "Untitled",
            "authors": authors,
            "abstract": reconstruct_openalex_abstract(item.get("abstract_inverted_index")),
            "citation_count": item.get("cited_by_count") or 0,
            "published_date": item.get("publication_date"),
            "categories": [category],
            "journal": venue["name"],
            "publication_type": venue["type"],
            "is_open_access": True,
            "doi": (item.get("doi") or "").replace("https://doi.org/", "") or None,
            "url": (item.get("open_access") or {}).get("oa_url") or item.get("id"),
        })

    return results[:limit]


_JATS_TAG_RE = re.compile(r"<[^>]+>")


def _crossref_date(item: Dict, key: str) -> Optional[str]:
    parts = ((item.get(key) or {}).get("date-parts") or [[None]])[0]
    if not parts or not parts[0]:
        return None
    year = parts[0]
    month = parts[1] if len(parts) > 1 else 1
    day = parts[2] if len(parts) > 2 else 1
    try:
        return datetime.date(year, month, day).isoformat()
    except ValueError:
        return None


def _crossref_published_date(item: Dict) -> Optional[str]:
    for key in ("published", "published-print", "published-online"):
        date = _crossref_date(item, key)
        if date:
            return date
    return None


async def fetch_latest_crossref(category: str, since: datetime.date, limit: int) -> List[Dict]:
    """Search Crossref for recent journal-article works in a category, newest first.

    Crossref's metadata coverage is broad but its per-work data is thinner than Semantic
    Scholar/OpenAlex (no reliable open-access flag, no author ids, and an abstract only some of
    the time) - it fills a different gap: works neither of those two has indexed yet.
    fetch_unpaywall_oa_location (below) resolves an actual open-access link for the DOIs this
    turns up, since Crossref's own `URL` field is usually just a doi.org redirect to the
    (often paywalled) publisher page.
    """
    email = config_instance.get("api.email")
    today = datetime.date.today()
    fetch_size = min(limit * 3, 100)
    url = (
        "https://api.crossref.org/works"
        f"?query.bibliographic={urllib.parse.quote(category)}"
        f"&filter=from-pub-date:{since.isoformat()},until-pub-date:{today.isoformat()},type:journal-article"
        f"&sort=published&order=desc&rows={fetch_size}"
    )
    if email:
        url += f"&mailto={urllib.parse.quote(email)}"

    async with aiohttp.ClientSession(timeout=_HTTP_TIMEOUT) as session:
        data = await _get_json_with_retry(session, url, "Crossref")

    if not data:
        return []

    results = []
    for item in (data.get("message") or {}).get("items", []):
        published_date = _crossref_published_date(item)
        if not _is_plausible_recent_date(published_date, since):
            continue

        titles = item.get("title") or []
        if not titles:
            continue

        authors = []
        for a in item.get("author", []):
            name = " ".join(part for part in [a.get("given"), a.get("family")] if part)
            if name:
                authors.append({"id": None, "name": name})
        if not authors:
            continue

        raw_abstract = item.get("abstract") or ""
        journals = item.get("container-title") or []

        results.append({
            "source": "crossref",
            "source_id": item.get("DOI", ""),
            "title": titles[0],
            "authors": authors,
            "abstract": _JATS_TAG_RE.sub("", raw_abstract).strip(),
            "citation_count": item.get("is-referenced-by-count") or 0,
            "published_date": published_date,
            "categories": [category],
            "journal": journals[0] if journals else None,
            "publication_type": "journal",
            "is_open_access": None,  # resolved by fetch_unpaywall_oa_location below
            "doi": item.get("DOI"),
            "url": item.get("URL"),
        })

    return results[:limit]


async def fetch_unpaywall_oa_location(session: aiohttp.ClientSession, doi: str) -> Optional[Dict]:
    """Look up a DOI's actual open-access link via Unpaywall.

    Used to upgrade a Crossref result's URL (usually just a doi.org redirect to the publisher's,
    often paywalled, page) to a real, freely-readable PDF/HTML link - the same service
    paper/download.py's get_doi_paper() uses for the citation-paste flow.
    """
    email = config_instance.get("api.email") or "user@example.com"
    url = f"https://api.unpaywall.org/v2/{urllib.parse.quote(doi, safe='')}?email={urllib.parse.quote(email)}"

    try:
        async with session.get(url) as response:
            if response.status != 200:
                return None
            data = await response.json()
    except Exception as e:
        logger.debug(f"Error fetching Unpaywall location for '{doi}': {e}")
        return None

    if not data.get("is_oa"):
        return None

    location = data.get("best_oa_location")
    if not location:
        return None

    return {"url": location.get("url_for_pdf") or location.get("url")}


async def _fill_open_access_links(papers: List[Dict]) -> None:
    """Resolve a confirmed open-access link via Unpaywall for any paper whose OA status is
    still unknown (Crossref results - Semantic Scholar/OpenAlex are already filtered to
    open-access-only at fetch time). A paper Unpaywall can't confirm as open access keeps
    whatever URL it already had rather than being dropped outright here - the caller decides
    whether to filter it out.
    """
    candidates = [p for p in papers if p.get("is_open_access") is None and p.get("doi")]
    if not candidates:
        return

    async with aiohttp.ClientSession(timeout=_HTTP_TIMEOUT) as session:
        async def resolve(paper: Dict) -> None:
            location = await fetch_unpaywall_oa_location(session, paper["doi"])
            if location:
                paper["url"] = location["url"] or paper.get("url")
                paper["is_open_access"] = True
            else:
                paper["is_open_access"] = False

        await asyncio.gather(*(resolve(p) for p in candidates))


def _dedupe(papers: List[Dict]) -> List[Dict]:
    seen_dois = set()
    seen_titles = set()
    unique = []

    for paper in papers:
        doi = paper.get("doi")
        title = (paper.get("title") or "").strip().lower()

        if doi and doi in seen_dois:
            continue
        if title and title in seen_titles:
            continue

        if doi:
            seen_dois.add(doi)
        if title:
            seen_titles.add(title)
        unique.append(paper)

    return unique


async def fetch_crossref_abstract(session: aiohttp.ClientSession, doi: str) -> Optional[str]:
    """Fall back to Crossref's metadata for an abstract when the primary source has none.

    Crossref abstracts (when present) are wrapped in JATS XML tags (e.g. <jats:p>...</jats:p>),
    so strip tags to get plain text.
    """
    url = f"https://api.crossref.org/works/{urllib.parse.quote(doi, safe='')}"

    try:
        async with session.get(url) as response:
            if response.status != 200:
                return None
            data = await response.json()
    except Exception as e:
        logger.debug(f"Error fetching Crossref abstract for '{doi}': {e}")
        return None

    raw_abstract = (data.get("message") or {}).get("abstract")
    if not raw_abstract:
        return None

    return _JATS_TAG_RE.sub("", raw_abstract).strip()


async def _fill_missing_abstracts(papers: List[Dict]) -> List[Dict]:
    """Fall back to Crossref for papers with no abstract.

    Doesn't drop papers that still have no abstract here - a paper's PDF full text is still a
    viable fallback for generating a description (see `_apply_summaries`), so the final "no
    description available from any source" drop happens after that fallback has had a chance.
    """
    async with aiohttp.ClientSession(timeout=_HTTP_TIMEOUT) as session:
        async def resolve(paper: Dict) -> Dict:
            if not paper.get("abstract") and paper.get("doi"):
                paper["abstract"] = await fetch_crossref_abstract(session, paper["doi"]) or ""
            return paper

        return await asyncio.gather(*(resolve(p) for p in papers))


_NON_ENGLISH_CONFIDENCE_THRESHOLD = 0.9


def _detect_language(paper: Dict) -> str:
    """Guess a paper's language from its title/abstract text.

    langdetect's plain detect() returns a best guess with no confidence score, and is prone to
    false positives on English academic text (acronyms, jargon, proper nouns) misread as another
    language. Require high confidence before accepting a non-English result; otherwise assume
    English, which is the overwhelmingly common case for indexed research papers.
    """
    text = f"{paper.get('title', '')} {paper.get('abstract', '')}".strip()
    if not text:
        return "en"
    try:
        best = detect_langs(text)[0]
    except LangDetectException:
        return "en"
    if best.lang != "en" and best.prob < _NON_ENGLISH_CONFIDENCE_THRESHOLD:
        return "en"
    return best.lang


_MYMEMORY_MAX_CHARS = 480  # MyMemory hard-rejects requests >= 500 chars; leave margin.

# Cap concurrent MyMemory requests - be polite to a free service, and avoid firing off dozens
# of simultaneous requests for a paper with a long, heavily-chunked abstract.
_mymemory_semaphore = asyncio.Semaphore(3)


def _split_into_chunks(text: str, max_len: int = _MYMEMORY_MAX_CHARS) -> List[str]:
    """Split text into <= max_len pieces, preferring sentence boundaries over mid-sentence word
    boundaries (MyMemory rejects long requests outright, and splitting mid-sentence loses some
    connective grammar in translation - packing whole sentences per chunk avoids that)."""
    sentences = re.split(r"(?<=[.!?])\s+", text)
    chunks: List[str] = []
    current = ""

    for sentence in sentences:
        pieces = [sentence] if len(sentence) <= max_len else sentence.split()
        for piece in pieces:
            candidate = f"{current} {piece}".strip()
            if len(candidate) > max_len and current:
                chunks.append(current)
                current = piece
            else:
                current = candidate

    if current:
        chunks.append(current)

    return chunks


async def _translate_chunk(
    session: aiohttp.ClientSession, text: str, source_lang: str, max_retries: int = 2
) -> Optional[str]:
    """Translate a single chunk (already within MyMemory's length limit) via its plain HTTP API.

    Called directly over aiohttp rather than through a translation library: MyMemory's raw API
    accepts plain ISO 639-1 codes directly (confirmed by testing - no locale-code mapping like
    'es-ES' is needed), and using aiohttp means the timeout is enforced by the event loop itself
    rather than hoping a background thread cooperates (see the module-level note on why an
    earlier thread-pool-wrapped approach could hang indefinitely).
    """
    email = config_instance.get("api.email")
    url = (
        "https://api.mymemory.translated.net/get"
        f"?q={urllib.parse.quote(text)}&langpair={source_lang}|en"
    )
    if email:
        url += f"&de={urllib.parse.quote(email)}"

    async with _mymemory_semaphore:
        for attempt in range(max_retries + 1):
            try:
                async with session.get(url) as response:
                    if response.status != 200:
                        raise RuntimeError(f"HTTP {response.status}")
                    data = await response.json(content_type=None)
                return (data.get("responseData") or {}).get("translatedText") or None
            except Exception as e:
                if attempt < max_retries:
                    await asyncio.sleep(1.5 * (attempt + 1))
                    continue
                logger.debug(f"Translation failed for language '{source_lang}' after retries: {e}")
                return None

    return None


async def _translate_to_english(
    session: aiohttp.ClientSession, text: Optional[str], source_lang: str
) -> Optional[str]:
    """Translate text to English via MyMemory (free, no API key). Returns original text on failure.

    MyMemory was chosen over the unofficial Google Translate endpoint after testing: Google's
    endpoint hard-limits to 5 requests/second and got our test IP rate-limited almost
    immediately under any real usage. MyMemory's free tier is meant for exactly this kind of
    programmatic use, but it hard-rejects any single request of 500+ characters, so abstracts
    need to be chunked and rejoined.
    """
    if not text:
        return text

    chunks = _split_into_chunks(text) if len(text) > _MYMEMORY_MAX_CHARS else [text]
    translated_chunks = []

    for chunk in chunks:
        translated = await _translate_chunk(session, chunk, source_lang)
        if translated is None:
            return text  # Any chunk failing after retries - bail out to the original text.
        translated_chunks.append(translated)

    return " ".join(translated_chunks)


async def _apply_language_and_translation(papers: List[Dict]) -> None:
    """Tag each paper with its language, translating title/journal/abstract to English if needed.

    Detects language from the actual title/abstract text rather than trusting a source-provided
    language field - OpenAlex's own `language` metadata turned out to be unreliable in testing
    (it mislabeled clearly-English titles as Afrikaans).

    Detection runs sequentially, not concurrently: langdetect draws from a shared, seeded
    DetectorFactory singleton that isn't thread-safe, and calling detect_langs() concurrently
    across threads was observed to corrupt its internal state and produce wrong results
    (clearly-English abstracts misdetected as Afrikaans). It's pure CPU-bound text analysis on
    already-fetched text, so running it sequentially costs negligible time. Translation, in
    contrast, is plain async I/O with no shared mutable state, so it's safe to run concurrently
    across papers (bounded by the semaphore in `_translate_chunk`).
    """
    non_english = []
    for paper in papers:
        paper["language"] = _detect_language(paper)
        if paper["language"] != "en":
            non_english.append(paper)

    if not non_english:
        return

    async with aiohttp.ClientSession(timeout=_HTTP_TIMEOUT) as session:
        async def translate_paper(paper: Dict) -> None:
            language = paper["language"]
            paper["title_original"] = paper["title"]
            paper["journal_original"] = paper.get("journal")

            paper["title"] = await _translate_to_english(session, paper["title"], language) or paper["title"]
            if paper.get("journal"):
                paper["journal"] = (
                    await _translate_to_english(session, paper["journal"], language) or paper["journal"]
                )
            paper["abstract"] = await _translate_to_english(session, paper["abstract"], language) or paper["abstract"]

        await asyncio.gather(*(translate_paper(p) for p in non_english))


async def _apply_summaries(papers: List[Dict]) -> None:
    """Generate each paper's UI description via Gemini in place.

    Summarizes the (already-translated, English) abstract into a <=200 word plain-English
    description; falls back to a summary of the PDF full text when there's no abstract at all.
    Falls back further to the raw abstract itself if Gemini is unavailable (no API key) or a
    call fails, so the pipeline degrades gracefully instead of hard-depending on the LLM. A
    paper that ends up with neither a summary nor a raw abstract gets `description = ""`, and is
    dropped by the caller.
    """
    async with aiohttp.ClientSession(timeout=_HTTP_TIMEOUT) as session:
        async def apply(paper: Dict) -> None:
            summary = await summarize_paper(session, paper)
            paper["description"] = summary or paper.get("abstract") or ""

        await asyncio.gather(*(apply(p) for p in papers))


async def fetch_paper_image(session: aiohttp.ClientSession, query: str) -> Optional[str]:
    """Fetch a stock photo URL from Pexels for a card image (no download - just the URL)."""
    api_key = config_instance.get("api.pexels_key")
    if not api_key:
        return None

    url = f"https://api.pexels.com/v1/search?query={urllib.parse.quote(query)}&per_page=1&orientation=portrait"

    try:
        async with session.get(url, headers={"Authorization": api_key}) as response:
            if response.status != 200:
                return None
            data = await response.json()
    except Exception as e:
        logger.debug(f"Error fetching Pexels image for '{query}': {e}")
        return None

    photos = data.get("photos") or []
    if not photos:
        return None
    return photos[0].get("src", {}).get("large")


async def _attach_images(papers: List[Dict], category: str) -> None:
    """Attach a card image to each paper in place, falling back to a category-level image on failure."""
    if not papers:
        return

    async with aiohttp.ClientSession(timeout=_HTTP_TIMEOUT) as session:
        category_image = None

        async def get_image(paper: Dict) -> Optional[str]:
            return await fetch_paper_image(session, paper["title"][:80])

        images = await asyncio.gather(*(get_image(p) for p in papers))

        for paper, image_url in zip(papers, images):
            if not image_url and category_image is None:
                category_image = await fetch_paper_image(session, category) or ""
            paper["image_url"] = image_url or category_image or None


async def get_latest_papers(
    category: str, days_back: int = 7, limit: int = 20, sort_by: str = "date"
) -> List[Dict]:
    """Fetch papers for a category from Semantic Scholar + OpenAlex + Crossref, deduped.

    Semantic Scholar and OpenAlex are filtered to open access at fetch time; Crossref's own
    open-access flag isn't reliable, so its results get a real open-access link resolved (or
    ruled out) via Unpaywall below before anything from it is kept.

    `sort_by="date"` (default) gives the normal "latest papers" feed. `sort_by="citations"`
    instead returns the most-cited papers within the date window - mainly useful for
    testing/demoing the citation-count UI, since truly recent papers have near-zero citations
    anywhere (OpenAlex, Semantic Scholar, or Google Scholar) regardless of source.
    """
    since = datetime.date.today() - datetime.timedelta(days=days_back)

    semantic_scholar_papers, openalex_papers, crossref_papers = await asyncio.gather(
        fetch_latest_semantic_scholar(category, since, limit),
        fetch_latest_openalex(category, since, limit, sort_by=sort_by),
        fetch_latest_crossref(category, since, limit),
    )

    combined = _dedupe(semantic_scholar_papers + openalex_papers + crossref_papers)
    if sort_by == "citations":
        combined.sort(key=lambda p: p.get("citation_count") or 0, reverse=True)
    else:
        combined.sort(key=lambda p: p.get("published_date") or "", reverse=True)
    combined = combined[:limit]

    await _fill_open_access_links(combined)
    before_oa_drop = len(combined)
    combined = [p for p in combined if p.get("is_open_access") is not False]
    if before_oa_drop != len(combined):
        logger.info(f"Dropped {before_oa_drop - len(combined)} Crossref paper(s) Unpaywall couldn't confirm as open access")

    combined = await _fill_missing_abstracts(combined)
    await _apply_language_and_translation(combined)
    await _apply_summaries(combined)

    before_drop = len(combined)
    combined = [p for p in combined if p.get("description")]
    if before_drop != len(combined):
        logger.info(f"Dropped {before_drop - len(combined)} paper(s) with no description available from any source")

    await _attach_images(combined, category)

    logger.info(f"Found {len(combined)} latest papers for '{category}'")
    return combined
