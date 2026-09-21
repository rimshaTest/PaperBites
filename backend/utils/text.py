"""Small text-cleaning helpers shared by ingestion (paper/latest.py) and the API layer
(api_server.py), so both newly-fetched and already-stored papers get clean text without
needing a re-fetch.
"""
import re

# Only strips "Abstract" at the very start of the string - never mid-sentence.
_LEADING_ABSTRACT_LABEL_RE = re.compile(r"^\s*abstract\b\s*[:.\-—–]?\s*", re.IGNORECASE)

# Structured-abstract section headers (common in medical/PubMed-style abstracts) - only matched
# when immediately followed by a colon, so ordinary prose like "the purpose of this study" is
# never touched.
_STRUCTURED_SECTION_LABEL_RE = re.compile(
    r"\b(background|purpose|objectives?|aims?|introduction|summary|"
    r"methods?|methodology|materials\s+and\s+methods|"
    r"results?|findings?|conclusions?|discussion|significance|implications)"
    r"\s*:\s*",
    re.IGNORECASE,
)


def clean_abstract(text: str) -> str:
    """Strip a leading "Abstract" label and inline structured-abstract section headers (e.g.
    "Purpose:", "Findings:") from raw abstract text, collapsing it into one flowing paragraph
    instead of a labeled multi-section summary."""
    if not text:
        return ""

    text = text.strip()
    text = _LEADING_ABSTRACT_LABEL_RE.sub("", text, count=1)
    text = _STRUCTURED_SECTION_LABEL_RE.sub(" ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text
