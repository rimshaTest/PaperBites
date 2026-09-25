"""Small text-cleaning helpers shared by ingestion (paper/latest.py) and the API layer
(api_server.py), so both newly-fetched and already-stored papers get clean text without
needing a re-fetch.
"""
import re

# Only strips "Abstract" at the very start of the string - never mid-sentence. \s* after \b
# already absorbs any run of blank lines/whitespace up to the next real content (JATS-derived
# text often has "Abstract" followed by several blank lines before the first section heading).
_LEADING_ABSTRACT_LABEL_RE = re.compile(r"^\s*abstract\b\s*[:.\-—–]?\s*", re.IGNORECASE)

_SECTION_LABEL_WORDS = (
    r"background|purpose|objectives?|aims?|introduction|summary|"
    r"methods?|methodology|materials\s+and\s+methods|"
    r"results?|findings?|conclusions?|discussion|significance|implications"
)

# A structured-abstract heading immediately followed by a colon, e.g. "Purpose: We test Y."
# (common in plain-text PubMed-style structured abstracts).
_INLINE_SECTION_LABEL_RE = re.compile(rf"\b({_SECTION_LABEL_WORDS})\s*:\s*", re.IGNORECASE)

# A structured-abstract heading sitting alone on its own line with no colon at all - what
# Crossref's <jats:title>Background</jats:title> becomes once XML tags are stripped, leaving
# just the word "Background" surrounded by blank lines. Requires the word to be on a line by
# itself (only horizontal whitespace before/after it on that line), so it's never mistaken for
# the same word appearing inside a sentence.
_STANDALONE_SECTION_LABEL_RE = re.compile(
    rf"(?:^|\n)[ \t]*({_SECTION_LABEL_WORDS})[ \t]*(?=\n|$)",
    re.IGNORECASE,
)


def clean_abstract(text: str) -> str:
    """Strip a leading "Abstract" label and structured-abstract section headers (inline, like
    "Purpose:", or standalone-on-their-own-line, like Crossref's JATS-derived "Background") from
    raw abstract text, collapsing it into one flowing paragraph instead of a labeled
    multi-section summary."""
    if not text:
        return ""

    text = text.strip()
    text = _LEADING_ABSTRACT_LABEL_RE.sub("", text, count=1)
    text = _STANDALONE_SECTION_LABEL_RE.sub("\n", text)
    text = _INLINE_SECTION_LABEL_RE.sub(" ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text
