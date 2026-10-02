# paper/summarize.py
"""Gemini-based text simplification for the paper feed's card description.

This is simplification, not summarization - a deliberate distinction. Summarizing condenses a
text into fewer words, dropping detail; simplifying rewrites the same information at a lower
reading level (plainer vocabulary, shorter sentences), keeping the content and level of detail
close to the original. The card's "Simpler" toggle needs the latter: something a non-expert can
actually read next to the raw abstract ("Original") without losing what the abstract says,
not a shorter version of it. `_SUMMARY_PROMPT`'s name predates this distinction being made
explicit but the prompt itself now asks for simplification.

When a paper has no abstract anywhere (OpenAlex/Semantic Scholar/Crossref all came up empty),
this falls back to downloading the paper's open-access PDF and simplifying its extracted text
instead of dropping the paper outright - in that case there's no "Original" abstract to show
alongside it either, and the frontend hides the toggle.

Uses langchain-google-genai rather than the raw google-generativeai SDK so the same LLM wrapper
can be reused by the per-paper chat agent (paper/chat.py).
"""
import asyncio
import json
import logging
import os
import tempfile
from typing import Dict, List, Optional

import aiohttp

from config import Config
import llm_usage
from paper.llm_text import response_text, response_tokens

config_instance = Config()
logger = logging.getLogger("paperbites.summarize")

# Cycled round-robin, one model per call, so each model's own separate free-tier quota absorbs
# part of the load instead of one model's 5-requests/minute cap gating the whole run. No
# verified guarantee every one of these model ids is live on a given account/API version - a
# model that 404s or otherwise errors is simply skipped in favor of the next one in the list
# (see summarize_text), so an invalid entry here just reduces the effective pool rather than
# breaking anything.
_MODEL_NAMES = [
    "gemini-3.5-flash",
    "gemini-3.5-flash-lite"
]
_MAX_SIMPLIFIED_WORDS = 300  # a ceiling, not a target - true simplification can run longer than the original
# Cap how much extracted PDF text goes into the prompt - full papers can be tens of thousands of
# words, and we only need enough to produce a good summary, not the whole document.
_PDF_TEXT_CHAR_LIMIT = 15000

_model_cycle_lock = asyncio.Lock()
_next_model_index = 0
_llm_cache: Dict[str, object] = {}


def _configured_model_names() -> List[str]:
    """api.gemini_models (a list, or a comma-separated string via PAPERBITES_GEMINI_MODELS)
    overrides the built-in list above, if set."""
    configured = config_instance.get("api.gemini_models")
    if not configured:
        return _MODEL_NAMES
    if isinstance(configured, str):
        return [name.strip() for name in configured.split(",") if name.strip()]
    return list(configured)


async def _next_model_name(models: List[str]) -> str:
    """Advance the shared round-robin position by one and return the model at that slot -
    concurrent summarize_text calls each get a different model instead of piling onto the same
    one."""
    global _next_model_index
    async with _model_cycle_lock:
        name = models[_next_model_index % len(models)]
        _next_model_index += 1
        return name

_SUMMARY_PROMPT = (
    "Rewrite the following research paper text in simpler language, at roughly an 8th-9th grade "
    "reading level. This is SIMPLIFICATION, not summarization: keep the same information, "
    "findings, numbers, and level of detail as the original - don't condense or drop content. "
    "Just replace jargon and technical terms with plain everyday words, and break up long or "
    "complex sentences into shorter ones. Stay under {max_words} words only because that's how "
    "much detail a typical abstract has to begin with, not as a target to hit by cutting things. "
    "Write flowing prose with no headers, bullet points, or preamble like 'This paper' - just "
    "the rewritten text itself.\n\n"
    "Title: {title}\n\n"
    "{source_label}:\n{text}"
)


def _get_llm_for_model(model_name: str):
    """Lazily build (and cache) the Gemini chat model for one model name. Returns None if no API
    key is configured, so callers can fall back to the raw abstract instead of hard-failing when
    Gemini isn't set up."""
    api_key = config_instance.get("api.gemini_key")
    if not api_key:
        return None
    if model_name not in _llm_cache:
        from langchain_google_genai import ChatGoogleGenerativeAI

        # The client's own retry loop (default 6, each sleeping on a 429) just stalls the run -
        # llm_usage.py already paces calls and handles 429s, so keep client retries minimal.
        max_retries = config_instance.get("api.gemini_max_retries")
        _llm_cache[model_name] = ChatGoogleGenerativeAI(
            model=model_name, google_api_key=api_key, temperature=0.3,
            max_retries=1 if max_retries is None else int(max_retries),
        )
    return _llm_cache[model_name]


async def _generate(
    models: List[str], payload, prompt_text: str, accept, label: str, rotate: bool = True,
    estimated_tokens: Optional[int] = None,
):
    """Call Gemini through the usage tracker (llm_usage.py), trying models until one yields an
    answer `accept` approves.

    Each attempt picks a model with budget left: one available now if any, else the one whose
    per-minute limit clears soonest (waiting for it), never one whose daily budget is spent. A
    model that errors is skipped for this call; a 429 from the API itself updates the tracker
    (a daily-quota error retires the model for the day). `accept(text)` turns the raw reply into
    the value to return, or None to try the next model (e.g. unparseable JSON). Returns None if
    nothing worked or every model is out of budget.
    """
    estimated = estimated_tokens or llm_usage.estimate_tokens(prompt_text)
    remaining = list(models)
    if rotate and remaining:
        first = await _next_model_name(remaining)
        remaining = [first] + [m for m in remaining if m != first]

    while remaining:
        model_name = llm_usage.tracker.choose(remaining, estimated)
        if model_name is None:
            return None  # every remaining model is out of budget for today
        remaining.remove(model_name)

        llm = _get_llm_for_model(model_name)
        if not llm:
            continue
        try:
            reservation = await llm_usage.tracker.acquire(model_name, estimated)
        except llm_usage.LLMQuotaExhausted:
            continue
        try:
            response = await llm.ainvoke(payload)
        except Exception as e:
            llm_usage.tracker.finish(reservation, None)
            if llm_usage.is_quota_error(e):
                llm_usage.tracker.note_api_quota_error(model_name, str(e))
            logger.warning(f"Gemini model '{model_name}' failed for {label}: {e}")
            continue

        llm_usage.tracker.finish(reservation, response_tokens(response))
        try:
            result = accept(response_text(response).strip())
        except Exception as e:
            logger.warning(f"Gemini model '{model_name}' gave an unusable reply for {label}: {e}")
            continue
        if result:
            return result

    return None


async def summarize_text(title: str, text: str, source_label: str = "Abstract") -> Optional[str]:
    """Summarize arbitrary paper text (abstract or full PDF text) into a <=200 word description.

    Tries each configured model in round-robin order, moving on immediately (no delay) on any
    failure - a rate limit, an invalid/unavailable model name, or anything else - so one model's
    free-tier cap or a bad model id doesn't stall or break the whole run. Gives up only once
    every model in the list has failed for this call.
    """
    if not config_instance.get("api.gemini_key") or not text:
        return None

    prompt = _SUMMARY_PROMPT.format(
        max_words=_MAX_SIMPLIFIED_WORDS,
        title=title,
        source_label=source_label,
        text=text[:_PDF_TEXT_CHAR_LIMIT],
    )

    return await _generate(
        _configured_model_names(), prompt, prompt, accept=lambda reply: reply or None, label=f"'{title}'"
    )


_SUMMARY_AND_CATEGORY_PROMPT = (
    "Rewrite the following research paper text in simpler language, at roughly an 8th-9th grade "
    "reading level, and classify it into exactly one category.\n\n"
    "Categories (pick exactly one): {categories}\n\n"
    "The rewrite is SIMPLIFICATION, not summarization: keep the same information, findings, "
    "numbers, and level of detail as the original - don't condense or drop content. Just replace "
    "jargon and technical terms with plain everyday words, and break up long or complex "
    "sentences into shorter ones. Stay under {max_words} words only because that's how much "
    "detail a typical abstract has to begin with, not as a target to hit by cutting things. "
    "Write flowing prose with no headers, bullet points, or preamble like 'This paper' - just "
    "the rewritten text itself.\n\n"
    'Respond with ONLY a JSON object of the exact form {{"summary": "...", "category": "..."}} - '
    "no markdown code fences, no other text. \"category\" must be exactly one of the category "
    "names listed above, spelled exactly as given.\n\n"
    "Title: {title}\n\n"
    "{source_label}:\n{text}"
)


async def summarize_and_classify(
    title: str, text: str, categories: List[str], source_label: str = "Abstract"
) -> Optional[Dict[str, str]]:
    """Summarize paper text and classify it into one of `categories` in a single Gemini call.

    Used for papers added outside the discovery feed (e.g. add-paper-by-citation), which don't
    already know their category the way a feed fetch (keyed to a search category) does - the
    category comes from the same read of the paper that produces the summary, rather than a
    second LLM call.

    Tries each configured model in round-robin order like summarize_text, moving on immediately
    on any failure. Returns None if Gemini isn't configured, every model fails, or a model's
    response can't be parsed into the expected {summary, category} shape with a valid category.
    """
    if not config_instance.get("api.gemini_key") or not text:
        return None

    prompt = _SUMMARY_AND_CATEGORY_PROMPT.format(
        categories=", ".join(categories),
        max_words=_MAX_SIMPLIFIED_WORDS,
        title=title,
        source_label=source_label,
        text=text[:_PDF_TEXT_CHAR_LIMIT],
    )

    def parse(raw: str) -> Optional[Dict[str, str]]:
        # Models occasionally wrap JSON in a ```json fence despite being told not to - strip
        # it rather than failing classification over formatting alone.
        if raw.startswith("```"):
            raw = raw.strip("`")
            if raw.lower().startswith("json"):
                raw = raw[4:]
        parsed = json.loads(raw)
        summary = (parsed.get("summary") or "").strip()
        category = (parsed.get("category") or "").strip()
        matched_category = next((c for c in categories if c.lower() == category.lower()), None)
        if summary and matched_category:
            return {"summary": summary, "category": matched_category}
        return None

    return await _generate(
        _configured_model_names(), prompt, prompt, accept=parse, label=f"summarize+classify '{title}'"
    )


async def summarize_and_classify_paper(
    session: aiohttp.ClientSession, paper: Dict, categories: List[str]
) -> Optional[Dict[str, str]]:
    """Same abstract-or-PDF-fallback source selection as summarize_paper(), but summarizing and
    classifying in one combined call. Used by paper/citation.py's add-paper flow."""
    title = paper.get("title") or "Untitled"
    abstract = (paper.get("abstract") or "").strip()

    if abstract:
        return await summarize_and_classify(title, abstract, categories, source_label="Abstract")

    url = paper.get("url")
    if not url:
        return None

    full_text = await _download_pdf_text(session, url)
    if not full_text:
        return None

    return await summarize_and_classify(title, full_text, categories, source_label="Full paper text")


# Prioritized by vision/OCR quality, not speed - the opposite tradeoff from _MODEL_NAMES above,
# which is tuned for cheap high-throughput bulk summarization. This is a single interactive
# user-triggered call (one photo, one result), so a fixed best-to-worst fallback order serves it
# better than round-robin load distribution: try the strongest vision model first, and only fall
# back to a weaker/cheaper one if it's unavailable or errors. No verified guarantee every model
# id here is live on a given account/API version - same as _MODEL_NAMES, an invalid or
# unavailable one is simply skipped in favor of the next.
_IMAGE_MODEL_NAMES = [
    "gemini-2.5-pro",
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
]


def _configured_image_model_names() -> List[str]:
    """api.gemini_image_models (a list, or a comma-separated string via
    PAPERBITES_GEMINI_IMAGE_MODELS) overrides the built-in list above, if set."""
    configured = config_instance.get("api.gemini_image_models")
    if not configured:
        return _IMAGE_MODEL_NAMES
    if isinstance(configured, str):
        return [name.strip() for name in configured.split(",") if name.strip()]
    return list(configured)


_IMAGE_CITATION_PROMPT = (
    "This image shows a research paper - its title page, a printed page, or a conference "
    "poster. Read whatever you can make out: the title, author names, and journal/venue/year if "
    "visible. Respond with ONLY a single-line plain-text citation-like string combining what you "
    "read (e.g. 'Author Name. Title of the paper. Journal Name, Year.') - no JSON, no markdown, "
    "no extra commentary, no preamble. If you cannot confidently read a title anywhere in the "
    "image, respond with exactly: NONE"
)
# Hard cap on how large an uploaded photo can be before we even try sending it to Gemini - a
# phone camera photo is typically 1-5MB; this just guards against something pathological.
_MAX_IMAGE_BYTES = 15 * 1024 * 1024


async def extract_citation_text_from_image(image_bytes: bytes, mime_type: str) -> Optional[str]:
    """Experimental vision-extraction fallback for the add-paper-by-photo flow: asks Gemini to
    read a title/authors/venue off a photographed paper page or poster and return them as a
    single citation-like string. The caller then resolves that string the same way a pasted
    citation is (paper/citation.py's search_citation()) - this function only replaces the "type
    or paste the citation" step, not the bibliographic matching after it.

    Deliberately skips QR-code decoding (unlike the ideal pipeline described in
    docs/TECHNICAL_SPEC.md) - reliable QR decoding needs a system zbar library this deployment
    doesn't assume is installed, so this only helps when Gemini can read the title/authors
    directly off the page, not when a poster's QR code is the only readable thing on it.

    Tries models in a fixed best-to-worst priority order (_IMAGE_MODEL_NAMES) rather than the
    round-robin used elsewhere in this module - see that list's own comment for why. A model
    that errors (including one that simply can't handle images) is skipped in favor of the next.
    """
    if not config_instance.get("api.gemini_key") or not image_bytes:
        return None
    if len(image_bytes) > _MAX_IMAGE_BYTES:
        logger.warning(f"Rejecting image scan: {len(image_bytes)} bytes exceeds the {_MAX_IMAGE_BYTES}-byte cap")
        return None

    import base64

    from langchain_core.messages import HumanMessage

    b64_image = base64.b64encode(image_bytes).decode("ascii")
    message = HumanMessage(content=[
        {"type": "text", "text": _IMAGE_CITATION_PROMPT},
        {"type": "image_url", "image_url": f"data:{mime_type};base64,{b64_image}"},
    ])

    def accept(reply: str) -> Optional[str]:
        return reply if reply and reply.upper() != "NONE" else None

    # Fixed best-to-worst order (rotate=False), but still budget-aware: a model whose daily
    # quota is spent is skipped in favor of the next.
    return await _generate(
        _configured_image_model_names(), [message], _IMAGE_CITATION_PROMPT,
        accept=accept, label="image citation extraction", rotate=False,
        estimated_tokens=2000,  # a photo costs far more than its (short) text prompt
    )


async def _download_pdf_text(session: aiohttp.ClientSession, url: str) -> Optional[str]:
    """Best-effort: download a PDF and extract its text layer.

    Deliberately skips OCR (unlike paper/extraction.py's video-pipeline path) - OCR needs a
    system Tesseract install and is slow, and this is only a fallback for the minority of papers
    with no abstract at all, so a PDF with no extractable text layer is simply skipped rather
    than dropped into a heavyweight OCR pass.
    """
    import fitz  # PyMuPDF - imported lazily, only needed on this no-abstract fallback path

    try:
        async with session.get(url) as response:
            if response.status != 200:
                return None
            content_type = response.headers.get("Content-Type", "")
            if "pdf" not in content_type.lower() and not url.lower().endswith(".pdf"):
                return None
            data = await response.read()
    except Exception as e:
        logger.debug(f"Error downloading PDF from '{url}': {e}")
        return None

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(data)
            tmp_path = tmp.name
        doc = fitz.open(tmp_path)
        text = "\n".join(page.get_text("text") for page in doc)
        doc.close()
        return text.strip() or None
    except Exception as e:
        logger.debug(f"Error extracting text from PDF '{url}': {e}")
        return None
    finally:
        if tmp_path:
            os.remove(tmp_path)


async def summarize_paper(session: aiohttp.ClientSession, paper: Dict) -> Optional[str]:
    """Summarize a paper's abstract, or fall back to its PDF full text if it has no abstract."""
    title = paper.get("title") or "Untitled"
    abstract = (paper.get("abstract") or "").strip()

    if abstract:
        return await summarize_text(title, abstract, source_label="Abstract")

    url = paper.get("url")
    if not url:
        return None

    full_text = await _download_pdf_text(session, url)
    if not full_text:
        return None

    return await summarize_text(title, full_text, source_label="Full paper text")
