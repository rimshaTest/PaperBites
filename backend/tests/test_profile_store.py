"""Storage-layer tests against an in-memory MongoDB (mongomock). Run from backend/."""
import os
import sys

import mongomock
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import db
import profile as profile_store
import profile_options as opts


@pytest.fixture(autouse=True)
def fake_db(monkeypatch):
    database = mongomock.MongoClient().paperbites
    monkeypatch.setattr(db, "get_db", lambda: database)
    return database


def test_set_tier1_stores_clean_values_and_derives_location():
    result = profile_store.set_tier1("u1", {
        "field_of_study": "Other", "field_of_study_other": " marine  biology ",
        "education_level": "Graduate", "general_interests": "genetics,  CRISPR",
        "location": "Seattle, Washington, United States",
        "location_country": "Mars",  # client-supplied derived field must be ignored
    })
    assert result["field_of_study_other"] == "marine biology"
    assert result["general_interests"] == "genetics, CRISPR"
    assert result["location_country"] == "United States" and result["location_region"] == "Washington"


def test_set_tier1_rejects_invalid_with_field_errors():
    with pytest.raises(profile_store.ProfileValidationError) as exc:
        profile_store.set_tier1("u1", {"general_interests": "x'; drop table t;--", "education_level": "Wizard"})
    assert set(exc.value.errors) == {"general_interests", "education_level"}
    assert profile_store.get_tier1("u1") == {}  # nothing partially saved


def test_set_tier1_unknown_field():
    with pytest.raises(ValueError):
        profile_store.set_tier1("u1", {"favorite_color": "blue"})


def test_set_tier2_and_retired_fields():
    out = profile_store.set_tier2("u1", {"birth_date": "1999-05-17", "gender": "Woman",
        "disability": {"status": opts.DISABILITY_YES, "conditions": ["Diabetes"]}},
        {"disability": {"used_for_feed_relevance": True}})
    assert out["fields"]["disability"]["conditions"] == ["Diabetes"]
    assert out["consent"]["disability"]["used_for_feed_relevance"] is True
    for retired in ("age", "mental_disabilities", "physical_disabilities", "chronic_illnesses"):
        with pytest.raises(ValueError):
            profile_store.set_tier2("u1", {retired: "x"}, {})


def test_set_tier2_invalid():
    with pytest.raises(profile_store.ProfileValidationError) as exc:
        profile_store.set_tier2("u1", {"birth_date": "1800-01-01"}, {})
    assert "birth_date" in exc.value.errors


def test_other_field_of_study_report():
    for i in range(12):
        profile_store.set_tier1(f"o{i}", {"field_of_study": "Other", "field_of_study_other": "Linguistics" if i % 2 == 0 else "Marine Biology"})
    for i in range(8):
        profile_store.set_tier1(f"p{i}", {"field_of_study": "Physics"})
    profile_store.set_tier1("n1", {"education_level": "Graduate"})  # no field of study: not counted
    report = profile_store.other_field_of_study_report(threshold_pct=5, min_users=5)
    assert report["users_with_field_of_study"] == 20
    assert report["other_count"] == 12 and report["other_percent"] == 60.0
    assert {g["name"] for g in report["other_groups"]} == {"Linguistics", "Marine Biology"}
    assert set(report["suggested_new_categories"]) == {"Linguistics", "Marine Biology"}
    strict = profile_store.other_field_of_study_report(threshold_pct=5, min_users=7)
    assert strict["suggested_new_categories"] == []  # 6 each < 7


def test_get_tier2_without_consent_flags_does_not_crash():
    profile_store.set_tier2("u9", {"gender": "Woman"}, {})  # no consent given -> no "consent" key stored
    out = profile_store.get_tier2("u9")
    assert out["fields"]["gender"] == "Woman" and out["consent"] == {}
    assert profile_store.get_tier2("never-set") == {"fields": {}, "consent": {}}
