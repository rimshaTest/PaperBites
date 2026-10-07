"""fetch-latest --no-llm: same pipeline and stored shape, but no Gemini calls; resummarize upgrades
the abstract-only papers later. Run from backend/."""
import asyncio

import mongomock
import pytest

import cli
import db
import llm_usage
import paper.latest as L
import paper.resummarize as R


@pytest.fixture
def database(monkeypatch):
    database = mongomock.MongoClient().paperbites
    monkeypatch.setattr(db, "get_db", lambda: database)
    return database


def candidate(i, abstract="A reasonably long abstract about the findings of this study."):
    return {
        "source": "test", "source_id": f"id{i}", "title": f"Paper {i}", "abstract": abstract,
        "authors": [{"id": f"a{i}", "name": "Jane Doe"}], "published_date": "2026-09-0%d" % (i + 1),
        "categories": ["Physics"], "journal": "Nature", "doi": None, "url": "https://example.org/%d" % i,
        "is_open_access": True,
    }


@pytest.fixture
def pipeline(monkeypatch, database):
    """Real process_candidate / iter_latest_papers; network steps stubbed; Gemini made loud."""
    llm_calls = []

    async def fake_find(category, days_back, limit, sort_by):
        return [candidate(i) for i in range(4)] + [candidate(9, abstract="")]  # last has no abstract

    async def noop(papers, *a, **k):
        return papers

    async def no_image(papers, *a, **k):
        return None

    async def boom_summaries(papers):
        llm_calls.append("summaries")
        raise AssertionError("Gemini summary was called")

    async def boom_embeddings(papers):
        llm_calls.append("embeddings")
        raise AssertionError("Gemini embedding was called")

    monkeypatch.setattr(L, "find_candidate_papers", fake_find)
    monkeypatch.setattr(L, "_fill_open_access_links", noop)
    monkeypatch.setattr(L, "_fill_missing_abstracts", noop)
    monkeypatch.setattr(L, "_apply_language_and_translation", noop)
    monkeypatch.setattr(L, "_attach_images", no_image)
    monkeypatch.setattr(L, "_apply_summaries", boom_summaries)
    monkeypatch.setattr(L, "_apply_embeddings", boom_embeddings)
    monkeypatch.setattr(cli, "CATEGORIES", ["Physics"])
    # Gemini key present and quota fully spent: --no-llm must not care
    monkeypatch.setattr(L, "config_instance", type("C", (), {"get": staticmethod(lambda k, d=None: "key")})())
    tracker = llm_usage.LLMUsageTracker(get_db=lambda: mongomock.MongoClient().paperbites)
    monkeypatch.setattr(llm_usage, "tracker", tracker)
    import paper.summarize as S
    monkeypatch.setattr(S, "_configured_model_names", lambda: ["gemini-3.5-flash"])
    tracker.note_api_quota_error("gemini-3.5-flash", "429 GenerateRequestsPerDayPerProjectPerModel-FreeTier")
    return llm_calls


def test_no_llm_stores_papers_without_calling_gemini(pipeline, database):
    saved = asyncio.run(cli.fetch_latest_command("Physics", 7, 10, no_llm=True))
    assert pipeline == []  # neither summaries nor embeddings were attempted
    assert saved == 4  # the abstract-less paper has nothing to describe it, so it's dropped
    doc = database.papers.find_one({"source_id": "id0"})
    assert doc["description"] == doc["abstract"] and doc["description_source"] == "abstract"
    assert "embedding" not in doc
    # same stored shape as a normal fetch: authors, journal, categories, url, dates are all there
    for key in ("title", "authors", "journal", "categories", "url", "published_date", "source", "source_id"):
        assert doc.get(key), key


def test_without_no_llm_the_same_run_stops_on_the_spent_quota(pipeline, database):
    saved = asyncio.run(cli.fetch_latest_command("Physics", 7, 10))
    assert saved == 0 and database.papers.count_documents({}) == 0  # confirms the fixture really is exhausted


def test_no_llm_rerun_skips_stored_papers(pipeline, database):
    asyncio.run(cli.fetch_latest_command("Physics", 7, 10, no_llm=True))
    assert asyncio.run(cli.fetch_latest_command("Physics", 7, 10, no_llm=True)) == 0
    assert database.papers.count_documents({}) == 4


def test_cli_exposes_the_flag_and_the_resummarize_command(monkeypatch, capsys):
    for args in (["fetch-latest", "--help"], ["resummarize", "--help"]):
        monkeypatch.setattr("sys.argv", ["cli.py", *args])
        with pytest.raises(SystemExit) as exit_info:
            cli.main()
        assert exit_info.value.code == 0
        out = capsys.readouterr().out
    monkeypatch.setattr("sys.argv", ["cli.py", "fetch-latest", "--help"])
    with pytest.raises(SystemExit):
        cli.main()
    assert "--no-llm" in capsys.readouterr().out


# ---- resummarize ------------------------------------------------------------------------------
@pytest.fixture
def upgrade(monkeypatch, database):
    import paper.summarize as S
    import paper.embeddings as E
    monkeypatch.setattr(S, "_configured_model_names", lambda: ["gemini-3.5-flash"])
    tracker = llm_usage.LLMUsageTracker(get_db=lambda: mongomock.MongoClient().paperbites)
    monkeypatch.setattr(llm_usage, "tracker", tracker)
    calls = {"summaries": [], "embeds": []}

    async def fake_summarize(title, text, source_label="Abstract"):
        calls["summaries"].append(title)
        return f"Plain summary of {title}."

    async def fake_embed(text):
        calls["embeds"].append(text)
        return [0.1, 0.2], "gemini-embedding-001"

    monkeypatch.setattr(S, "summarize_text", fake_summarize)
    monkeypatch.setattr(E, "embed_document_with_model", fake_embed)
    database.papers.insert_many([
        {"title": "Abstract only", "abstract": "abs", "description": "abs", "description_source": "abstract", "published_date": "2026-09-02"},
        {"title": "Older abstract only", "abstract": "abs2", "description": "abs2", "description_source": "abstract", "published_date": "2026-08-01"},
        {"title": "Already good", "abstract": "x", "description": "A real summary", "description_source": "summary", "published_date": "2026-09-05"},
        {"title": "Old format", "abstract": "x", "description": "x", "published_date": "2026-09-06"},  # no label: left alone
    ])
    return tracker, calls


def test_resummarize_upgrades_only_abstract_only_papers(upgrade, database):
    result = asyncio.run(R.resummarize_papers(limit=10))
    assert result["candidates"] == 2 and result["upgraded"] == 2 and result["embedded"] == 2
    doc = database.papers.find_one({"title": "Abstract only"})
    assert doc["description"] == "Plain summary of Abstract only." and doc["description_source"] == "summary"
    assert doc["embedding"] == [0.1, 0.2] and doc["embedding_model"] == "gemini-embedding-001"
    assert database.papers.find_one({"title": "Already good"})["description"] == "A real summary"
    assert database.papers.find_one({"title": "Old format"})["description"] == "x"


def test_resummarize_embeds_title_plus_the_new_summary(upgrade, database):
    asyncio.run(R.resummarize_papers(limit=1))
    assert upgrade[1]["embeds"] == ["Abstract only\n\nPlain summary of Abstract only."]  # newest first


def test_resummarize_respects_limit_and_can_be_rerun(upgrade, database):
    assert asyncio.run(R.resummarize_papers(limit=1))["upgraded"] == 1
    assert asyncio.run(R.resummarize_papers(limit=1))["upgraded"] == 1
    assert asyncio.run(R.resummarize_papers(limit=1))["candidates"] == 0  # nothing left to do


def test_resummarize_stops_when_the_quota_is_spent(upgrade, database):
    tracker, calls = upgrade
    tracker.note_api_quota_error("gemini-3.5-flash", "429 GenerateRequestsPerDayPerProjectPerModel-FreeTier")
    result = asyncio.run(R.resummarize_papers(limit=10))
    assert result["upgraded"] == 0 and "quota" in result["stopped_reason"] and calls["summaries"] == []


def test_resummarize_stops_after_repeated_failures(upgrade, database, monkeypatch):
    import paper.summarize as S

    async def failing(title, text, source_label="Abstract"):
        return None

    monkeypatch.setattr(S, "summarize_text", failing)
    for i in range(5):
        database.papers.insert_one({"title": f"More {i}", "abstract": "a", "description": "a",
                                    "description_source": "abstract", "published_date": f"2026-07-0{i + 1}"})
    result = asyncio.run(R.resummarize_papers(limit=0))
    assert result["failed"] == 3 and "in a row" in result["stopped_reason"]
    assert database.papers.count_documents({"description_source": "abstract"}) == 7  # nothing was damaged
