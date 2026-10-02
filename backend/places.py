"""
Offline place autocomplete for the Profile "location" field: cities, regions (states/provinces)
and countries, from the `geonamescache` and `pycountry` packages. No external API, key, or
network call - the index is built in memory on first use (~40k entries).

A place is identified by its display label ("Seattle, Washington, United States",
"Ontario, Canada", "Japan"). Labels carry only the levels we know, so a place doesn't need
every level - consistent with the form not requiring all parts of a location.
"""
import unicodedata
from typing import Dict, List, Optional

MAX_QUERY_LENGTH = 60
# Regions have no population in our data; this stands in so a state/province ranks below big
# cities and countries but above small towns when matches tie on how the name matches.
REGION_POP = 1_000_000

class PlacesUnavailable(RuntimeError):
    """The place-data packages aren't installed in this environment."""


_index: Optional[List[Dict]] = None
_by_label: Dict[str, Dict] = {}


def normalize(text: str) -> str:
    """Lowercase and strip accents so "Zurich" matches "Zürich"."""
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(c for c in decomposed if not unicodedata.combining(c)).lower().strip()


def is_alphabetic_label(text: str) -> bool:
    """Letters (any script), spaces, and the punctuation real place names use - nothing else."""
    return bool(text) and all(c.isalpha() or c in " .,'’-" for c in text)


def _build_index() -> List[Dict]:
    try:
        import geonamescache
        import pycountry
    except ImportError as e:
        raise PlacesUnavailable(
            f"{e}. Install the backend requirements: pip install -r requirements.txt"
        ) from e

    gc = geonamescache.GeonamesCache()
    entries: List[Dict] = []

    countries_by_iso = {}
    for country in gc.get_countries().values():
        countries_by_iso[country["iso"]] = country["name"]
        entries.append({
            "label": country["name"], "type": "country",
            "country": country["name"], "region": None, "city": None,
            "rank": 0, "pop": country.get("population", 0),
        })

    for sub in pycountry.subdivisions:
        if sub.parent_code is not None:  # top-level regions only (states, provinces)
            continue
        country_name = countries_by_iso.get(sub.country_code)
        if not country_name:
            continue
        entries.append({
            "label": f"{sub.name}, {country_name}", "type": "region",
            "country": country_name, "region": sub.name, "city": None,
            "rank": 1, "pop": REGION_POP,
        })

    us_states = {code: s["name"] for code, s in gc.get_us_states().items()}
    for city in gc.get_cities().values():
        country_name = countries_by_iso.get(city["countrycode"])
        if not country_name:
            continue
        region = us_states.get(city["admin1code"]) if city["countrycode"] == "US" else None
        label = ", ".join(p for p in (city["name"], region, country_name) if p)
        entries.append({
            "label": label, "type": "city",
            "country": country_name, "region": region, "city": city["name"],
            "rank": 2, "pop": city.get("population", 0),
        })

    for entry in entries:
        entry["norm"] = normalize(entry["label"])
        entry["norm_name"] = normalize(entry["city"] or entry["region"] or entry["country"])
    return entries


def _ensure_index() -> List[Dict]:
    global _index
    if _index is None:
        _index = _build_index()
        for entry in _index:
            # Several cities can share a label (two "Springfield, ..., US" rows); keep the
            # most populous so resolve() is deterministic.
            existing = _by_label.get(entry["norm"])
            if existing is None or entry["pop"] > existing["pop"]:
                _by_label[entry["norm"]] = entry
    return _index


def _public(entry: Dict) -> Dict:
    return {
        "label": entry["label"], "type": entry["type"],
        "city": entry["city"], "region": entry["region"], "country": entry["country"],
    }


def search(query: str, limit: int = 8) -> List[Dict]:
    """Places whose name starts with (or has a word starting with) the query, best first:
    name-prefix matches before later-word matches, then by importance (population; regions
    use a stand-in value)."""
    query = (query or "")[:MAX_QUERY_LENGTH]
    norm_query = normalize(query)
    if len(norm_query) < 2 or not is_alphabetic_label(query):
        return []

    scored = []
    for entry in _ensure_index():
        name = entry["norm_name"]
        if name.startswith(norm_query):
            tier = 0
        elif entry["norm"].startswith(norm_query):
            tier = 1
        elif any(word.startswith(norm_query) for word in name.split()):
            tier = 2
        else:
            continue
        scored.append((tier, -entry["pop"], entry["rank"], entry["label"], entry))

    scored.sort(key=lambda row: row[:4])
    seen, results = set(), []
    for *_, entry in scored:
        if entry["norm"] in seen:
            continue
        seen.add(entry["norm"])
        results.append(_public(entry))
        if len(results) >= max(1, min(limit, 10)):
            break
    return results


def resolve(label: str) -> Optional[Dict]:
    """The place with exactly this label, or None - used to confirm a saved location is a
    real place the user picked from the list, not free-typed text."""
    _ensure_index()
    entry = _by_label.get(normalize(label or ""))
    return _public(entry) if entry else None
