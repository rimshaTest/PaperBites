"""
The one place that answers "what paper categories do we pull?", shared by the /api/categories
route and by anything that needs to validate against it (e.g. the Profile "field of study"
dropdown), so changing the list in paper/latest.py changes every consumer at once.
"""
from typing import List

# Mirrors paper.latest.CATEGORIES. Importing that module pulls in its heavy fetch-pipeline
# dependencies (aiohttp, langdetect) just to read a static list - if those aren't installed
# in this deployment, fall back to this copy rather than failing on a trivial lookup.
_FALLBACK_CATEGORIES = [
    "Artificial Intelligence", "Medicine", "Physics", "Biology",
    "Psychology", "Climate Science", "Economics", "Neuroscience",
]


def current_categories() -> List[str]:
    try:
        from paper.latest import CATEGORIES
        return list(CATEGORIES)
    except ImportError as e:
        print(f"Falling back to hardcoded categories, paper.latest failed to import: {e}")
        return list(_FALLBACK_CATEGORIES)
