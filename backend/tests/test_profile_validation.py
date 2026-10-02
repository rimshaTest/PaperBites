"""Run from backend/: python -m pytest tests -q   (no database needed)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import places
import profile_options as opts
import profile_validation as v
from categories import current_categories


# ---- field of study -------------------------------------------------------------------------
def test_field_of_study_accepts_every_current_category():
    for category in current_categories():
        cleaned, errors = v.validate_field_of_study(category, "")
        assert not errors and cleaned["field_of_study"] == category


def test_field_of_study_follows_category_list(monkeypatch):
    monkeypatch.setattr(v, "current_categories", lambda: ["Linguistics"])
    assert not v.validate_field_of_study("Linguistics", "")[1]
    assert v.validate_field_of_study("Physics", "")[1]


def test_field_of_study_other_requires_text():
    assert "field_of_study_other" in v.validate_field_of_study(opts.OTHER, "")[1]
    cleaned, errors = v.validate_field_of_study(opts.OTHER, "  Marine   biology ")
    assert not errors and cleaned == {"field_of_study": "Other", "field_of_study_other": "Marine biology"}


def test_field_of_study_other_cleared_when_not_other():
    cleaned, _ = v.validate_field_of_study("Physics", "leftover")
    assert cleaned["field_of_study_other"] == ""


def test_field_of_study_other_rejects_bad_text():
    for bad in ["drop table users", "q", "Marine1", "fuck", "asdfghjk"]:
        assert v.validate_field_of_study(opts.OTHER, bad)[1], bad


def test_field_of_study_rejects_unknown():
    assert v.validate_field_of_study("Astrology??", "")[1]


# ---- education ------------------------------------------------------------------------------
def test_education_levels():
    for level in opts.EDUCATION_LEVELS:
        assert v.validate_choice(level, opts.EDUCATION_LEVELS, "Education level")[1] is None
    assert v.validate_choice("Wizard", opts.EDUCATION_LEVELS, "Education level")[1]


# ---- interests ------------------------------------------------------------------------------
def test_interests_accepts_normal_and_acronyms():
    for ok in ["climate policy, genetics", "CRISPR, fMRI, DNA repair", "machine learning", "5G networks", ""]:
        assert v.validate_interests(ok)[1] is None, ok


def test_interests_normalizes_and_dedupes():
    assert v.validate_interests("genetics,  Genetics , climate   policy")[0] == "genetics, climate policy"


def test_interests_rejects_symbols_and_injection():
    for bad in ["x'; DROP TABLE users;--", "genetics!", "<script>", "a-b", "1=1 or", "name@x.com"]:
        assert v.validate_interests(bad)[1], bad


def test_interests_rejects_sql_phrases_even_if_charset_ok():
    assert v.validate_interests("select all from users")[1]
    assert v.validate_interests("union select password")[1]
    assert v.validate_interests("labor union history")[1] is None  # "union" alone is fine


def test_interests_rejects_gibberish():
    for bad in ["asdfghjkl", "qwertyuiop", "zzzzzzz", "bcdfgh", "ababababab", "xkcd qwxz"]:
        assert v.validate_interests(bad)[1], bad


def test_interests_rejects_profanity():
    assert v.validate_interests("fuck")[1]
    assert v.validate_interests("climate, shit science")[1]


def test_interests_limits():
    assert v.validate_interests("a" * 41)[1]
    assert v.validate_interests(", ".join(f"topic{i}x" for i in range(11)))[1]
    assert v.validate_interests("x" * 201)[1]


# ---- location -------------------------------------------------------------------------------
def test_places_autocomplete():
    labels = [p["label"] for p in places.search("seattle")]
    assert "Seattle, Washington, United States" in labels
    assert places.search("s") == []  # too short
    assert places.search("sea'ttle; drop") == []  # non-alphabetic query
    assert any(p["type"] == "country" and p["label"] == "Canada" for p in places.search("canad"))
    assert any(p["label"] == "Ontario, Canada" for p in places.search("ontar"))


def test_location_validation():
    place, err = v.validate_location("Seattle, Washington, United States")
    assert err is None and place["country"] == "United States" and place["region"] == "Washington"
    assert v.validate_location("Atlantis")[1]
    assert v.validate_location("Seattle1")[1]
    assert v.validate_location("")[1] is None


def test_tier1_derives_country_from_location():
    cleaned, errors = v.validate_tier1({"location": "Canada"})
    assert not errors and cleaned["location_country"] == "Canada" and cleaned["location_region"] == ""


# ---- birth date -----------------------------------------------------------------------------
def test_birth_date():
    assert v.validate_birth_date("1999-05-17")[1] is None
    assert v.validate_birth_date("1920-01-01")[1] is None
    assert v.validate_birth_date("1919-12-31")[1]
    assert v.validate_birth_date("2999-01-01")[1]
    assert v.validate_birth_date("2001-02-30")[1]
    assert v.validate_birth_date("17/05/1999")[1]
    assert v.validate_birth_date("")[1] is None


# ---- gender / sex / disability --------------------------------------------------------------
def test_tier2_choices():
    cleaned, errors = v.validate_tier2({"gender": "Woman", "sex": "Female"})
    assert not errors and cleaned == {"gender": "Woman", "sex": "Female"}
    assert v.validate_tier2({"gender": "robot"})[1]


def test_disability_checklist():
    cleaned, err = v.validate_disability({"conditions": ["Diabetes", "Autism"]})
    assert err is None and cleaned == {"conditions": ["Autism", "Diabetes"], "other": ""}  # canonical order
    assert v.validate_disability({"conditions": [opts.DISABILITY_NONE]})[1] is None
    assert v.validate_disability({})[0] == {"conditions": [], "other": ""}
    assert v.validate_disability({"conditions": ["Made up"]})[1]


def test_disability_none_is_exclusive():
    assert v.validate_disability({"conditions": [opts.DISABILITY_NONE, "Diabetes"]})[1]


def test_disability_other_needs_clean_text():
    other = opts.DISABILITY_OTHER
    cleaned, err = v.validate_disability({"conditions": [other, "Diabetes"], "other": "  Chronic  fatigue "})
    assert err is None and cleaned["other"] == "Chronic fatigue"
    for bad in ["", "x", "drop table users", "fuck", "asdfghjk", "abc123"]:
        assert v.validate_disability({"conditions": [other], "other": bad})[1], bad
    # text is dropped when Other isn't chosen
    assert v.validate_disability({"conditions": ["Diabetes"], "other": "ignored"})[0]["other"] == ""


def test_location_accepted_unverified_when_place_data_missing(monkeypatch):
    def boom(_label):
        raise places.PlacesUnavailable("no geonamescache")
    monkeypatch.setattr(places, "resolve", boom)
    place, err = v.validate_location("Seattle")
    assert err is None and place["label"] == "Seattle"
