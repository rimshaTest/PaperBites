"""One-by-one fetch pipeline: each paper is enriched, validated and stored before the next one
starts, so an interrupted or quota-stopped run keeps everything finished. Run from backend/."""
import asyncio

import mongomock
import pytest

import cli
import db
import llm_usage
import paper.latest as L

FLASH = "gemini-3.5-flash"


@pytest.fixture
def database(monkeypatch):
    database = mongomock.MongoClient().paperbites
    monkeypatch.setattr(db, "get_db", lambda: database)
    return database


def candidates(n=5):
    return [
        {"source": "test", "source_id": f"id{i}", "title": f"Paper {i}", "abstract": f"abstract {i} " * 5,
         "published_date": "2026-09-01", "categories": ["Physics"]}
        for i in range(n)
    ]


@pytest.fixture
def pipeline(monkeypatch, database):
    """Stub the network/LLM steps; record which papers get 'enriched'."""
    calls = []
    cand = candidates()

    async def fake_find(category, days_back, limit, sort_by):
        return list(cand)

    async def fake_process(paper, category, **kw):
        calls.append(paper["source_id"])
        paper["description"] = "A plain-English summary of " + paper["title"]
        return paper

    monkeypatch.setattr(L, "find_candidate_papers", fake_find)
    monkeypatch.setattr(L, "process_candidate", fake_process)
    monkeypatch.setattr(cli, "CATEGORIES", ["Physics"])
    # No Gemini key -> the quota check is skipped unless a test turns it on
    monkeypatch.setattr(L, "config_instance", type("C", (), {"get": staticmethod(lambda k, d=None: None)})())
    return calls


def stored_ids(database):
    return sorted(d["source_id"] for d in database.papers.find({}))


def test_each_paper_is_stored_as_it_is_produced(pipeline, database):
    saved = asyncio.run(cli.fetch_latest_command("Physics", 7, 5))
    assert saved == 5 and stored_ids(database) == [f"id{i}" for i in range(5)]


def test_interrupted_run_keeps_papers_already_finished(pipeline, database, monkeypatch):
    original = L.process_candidate

    async def crash_on_fourth(paper, category, **kw):
        if paper["source_id"] == "id3":
            raise KeyboardInterrupt  # Ctrl+C / killed process
        return await original(paper, category, **kw)

    monkeypatch.setattr(L, "process_candidate", crash_on_fourth)
    with pytest.raises(KeyboardInterrupt):
        asyncio.run(cli.fetch_latest_command("Physics", 7, 5))
    assert stored_ids(database) == ["id0", "id1", "id2"]  # nothing lost to the crash


def test_rerun_skips_papers_already_stored_and_spends_no_work_on_them(pipeline, database):
    asyncio.run(cli.fetch_latest_command("Physics", 7, 5))
    pipeline.clear()
    saved = asyncio.run(cli.fetch_latest_command("Physics", 7, 5))
    assert saved == 0 and pipeline == []  # nothing re-enriched


def test_refresh_reprocesses_stored_papers(pipeline, database):
    asyncio.run(cli.fetch_latest_command("Physics", 7, 5))
    pipeline.clear()
    saved = asyncio.run(cli.fetch_latest_command("Physics", 7, 5, refresh=True))
    assert saved == 5 and len(pipeline) == 5


def test_a_paper_that_errors_is_skipped_and_the_run_continues(pipeline, database, monkeypatch):
    original = L.process_candidate

    async def fail_second(paper, category, **kw):
        if paper["source_id"] == "id1":
            raise ValueError("bad record")
        return await original(paper, category, **kw)

    monkeypatch.setattr(L, "process_candidate", fail_second)
    asyncio.run(cli.fetch_latest_command("Physics", 7, 5))
    assert stored_ids(database) == ["id0", "id2", "id3", "id4"]


def test_a_failed_store_does_not_end_the_run(pipeline, database, monkeypatch):
    real = db.upsert_paper

    def flaky(paper):
        if paper["source_id"] == "id2":
            raise RuntimeError("write failed")
        real(paper)

    monkeypatch.setattr(cli, "upsert_paper", flaky)
    saved = asyncio.run(cli.fetch_latest_command("Physics", 7, 5))
    assert saved == 4 and "id2" not in stored_ids(database)


def llm_configured(monkeypatch):
    """Gemini key present and one model with a healthy budget."""
    tracker = llm_usage.LLMUsageTracker(limits={FLASH: llm_usage.Limits(rpm=5, tpm=250_000, rpd=20)},
                                        get_db=lambda: mongomock.MongoClient().paperbites)
    monkeypatch.setattr(llm_usage, "tracker", tracker)
    import paper.summarize as S
    monkeypatch.setattr(S, "_configured_model_names", lambda: [FLASH])
    monkeypatch.setattr(L, "config_instance", type("C", (), {"get": staticmethod(lambda k, d=None: "key")})())
    return tracker


def exhausted_tracker(monkeypatch):
    llm_configured(monkeypatch).note_api_quota_error(FLASH, "429 GenerateRequestsPerDayPerProjectPerModel-FreeTier")


def test_run_stops_cleanly_when_the_daily_llm_quota_is_spent(pipeline, database, monkeypatch):
    exhausted_tracker(monkeypatch)
    saved = asyncio.run(cli.fetch_latest_command("Physics", 7, 5))
    assert saved == 0 and pipeline == []  # no paper stored with a raw-abstract description


def test_quota_stop_keeps_papers_finished_before_the_cap_hit(pipeline, database, monkeypatch):
    tracker = llm_configured(monkeypatch)
    original = L.process_candidate

    async def spend_quota_after_two(paper, category, **kw):
        result = await original(paper, category, **kw)
        if paper["source_id"] == "id1":
            tracker.note_api_quota_error(FLASH, "429 GenerateRequestsPerDayPerProjectPerModel-FreeTier")
        return result

    monkeypatch.setattr(L, "process_candidate", spend_quota_after_two)
    saved = asyncio.run(cli.fetch_latest_command("Physics", 7, 5))
    assert saved == 2 and stored_ids(database) == ["id0", "id1"]


def test_continue_without_llm_keeps_going(pipeline, database, monkeypatch):
    exhausted_tracker(monkeypatch)
    saved = asyncio.run(cli.fetch_latest_command("Physics", 7, 5, continue_without_llm=True))
    assert saved == 5


def test_validate_paper():
    good = {"source": "s", "source_id": "1", "title": "T", "description": "x" * 30}
    assert L.validate_paper(good) is None
    assert L.validate_paper({**good, "description": ""})
    assert L.validate_paper({**good, "description": "short"})
    assert L.validate_paper({**good, "title": ""})
    assert L.validate_paper({**good, "source_id": None})
    assert L.validate_paper({**good, "is_open_access": False})
    assert L.validate_paper({**good, "title": "x" * 2000})


def test_process_candidate_drops_papers_failing_validation(monkeypatch):
    async def noop(papers, *a, **k):
        return papers

    async def no_summary(papers):
        for p in papers:
            p["description"] = ""

    monkeypatch.setattr(L, "_fill_open_access_links", noop)
    monkeypatch.setattr(L, "_fill_missing_abstracts", noop)
    monkeypatch.setattr(L, "_apply_language_and_translation", noop)
    monkeypatch.setattr(L, "_apply_summaries", no_summary)
    paper = {"source": "s", "source_id": "1", "title": "T", "abstract": ""}
    assert asyncio.run(L.process_candidate(paper, "Physics")) is None


# ---- target count / search pool --------------------------------------------------------------
def test_limit_counts_new_papers_and_searches_a_wider_pool(monkeypatch, database):
    asked = {}
    cand = candidates(12)
    processed = []

    async def fake_find(category, days_back, limit, sort_by):
        asked["pool"] = limit
        return list(cand)

    async def fake_process(paper, category, **kw):
        processed.append(paper["source_id"])
        paper["description"] = "summary " * 5
        return paper

    monkeypatch.setattr(L, "find_candidate_papers", fake_find)
    monkeypatch.setattr(L, "process_candidate", fake_process)
    monkeypatch.setattr(cli, "CATEGORIES", ["Physics"])
    monkeypatch.setattr(L, "config_instance", type("C", (), {"get": staticmethod(lambda k, d=None: None)})())
    for c in cand[:3]:  # the three newest are already stored from an earlier run
        db.upsert_paper({**c, "description": "already summarized"})

    saved = asyncio.run(cli.fetch_latest_command("Physics", 7, 4, pool_factor=3))
    assert asked["pool"] == 12  # limit 4 x pool factor 3
    assert saved == 4 and processed == ["id3", "id4", "id5", "id6"]  # stored ones don't count; stops at 4
    assert "id7" not in processed


def test_dropped_candidates_dont_count_toward_the_limit(monkeypatch, database):
    cand = candidates(10)
    original_process = None

    async def fake_find(category, days_back, limit, sort_by):
        return list(cand)

    async def fake_process(paper, category, **kw):
        if int(paper["source_id"][2:]) % 2 == 0:
            return None  # e.g. Unpaywall can't confirm open access
        paper["description"] = "summary " * 5
        return paper

    monkeypatch.setattr(L, "find_candidate_papers", fake_find)
    monkeypatch.setattr(L, "process_candidate", fake_process)
    monkeypatch.setattr(cli, "CATEGORIES", ["Physics"])
    monkeypatch.setattr(L, "config_instance", type("C", (), {"get": staticmethod(lambda k, d=None: None)})())
    saved = asyncio.run(cli.fetch_latest_command("Physics", 7, 3))
    assert saved == 3 and stored_ids(database) == ["id1", "id3", "id5"]


# ---- rate-limited source circuit breaker ----------------------------------------------------
class _Resp:
    status = 429

    async def json(self, content_type=None):
        return {"retryAfter": 0}

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False


class _Session:
    def __init__(self):
        self.calls = 0

    def get(self, url, headers=None):
        self.calls += 1
        return _Resp()


def test_rate_limited_source_is_skipped_after_retries_run_out(monkeypatch):
    monkeypatch.setattr(L, "_source_blocked_until", {})
    session = _Session()
    assert asyncio.run(L._get_json_with_retry(session, "http://x", "Semantic Scholar", default_backoff=0)) is None
    first_calls = session.calls
    assert first_calls == 3  # initial try + 2 retries
    # The next category's request doesn't wait through the retries all over again
    assert asyncio.run(L._get_json_with_retry(session, "http://x", "Semantic Scholar", default_backoff=0)) is None
    assert session.calls == first_calls
    # ...and it's per source
    other = _Session()
    asyncio.run(L._get_json_with_retry(other, "http://x", "OpenAlex", default_backoff=0))
    assert other.calls == 3


def test_source_is_retried_after_the_cooldown(monkeypatch):
    monkeypatch.setattr(L, "_source_blocked_until", {})
    clock = {"now": 1000.0}
    monkeypatch.setattr(L, "_time_now", lambda: clock["now"])
    session = _Session()
    asyncio.run(L._get_json_with_retry(session, "http://x", "Semantic Scholar", default_backoff=0))
    calls = session.calls
    clock["now"] += L._RATE_LIMIT_COOLDOWN_SECONDS + 1
    asyncio.run(L._get_json_with_retry(session, "http://x", "Semantic Scholar", default_backoff=0))
    assert session.calls > calls


# ---- Gemini transiently down (503s), quota not spent ----------------------------------------
def _gemini_configured(monkeypatch):
    monkeypatch.setattr(L, "config_instance", type("C", (), {"get": staticmethod(lambda k, d=None: "key")})())
    import paper.summarize as S
    monkeypatch.setattr(S, "_configured_model_names", lambda: [FLASH])
    monkeypatch.setattr(llm_usage, "tracker", llm_usage.LLMUsageTracker(
        limits={FLASH: llm_usage.Limits(rpm=5, tpm=250_000, rpd=20)},
        get_db=lambda: mongomock.MongoClient().paperbites))


def test_papers_gemini_failed_to_summarize_are_not_stored_with_a_raw_abstract(monkeypatch, database):
    cand = candidates(5)
    seen = []

    async def fake_find(category, days_back, limit, sort_by):
        return list(cand)

    async def fake_process(paper, category, require_summary=False, **kw):
        seen.append(require_summary)
        if paper["source_id"] == "id1":
            raise L.SummaryUnavailable(paper["title"])  # every model 503'd for this one
        paper["description"] = "real summary " * 3
        return paper

    monkeypatch.setattr(L, "find_candidate_papers", fake_find)
    monkeypatch.setattr(L, "process_candidate", fake_process)
    monkeypatch.setattr(cli, "CATEGORIES", ["Physics"])
    _gemini_configured(monkeypatch)
    saved = asyncio.run(cli.fetch_latest_command("Physics", 7, 5))
    assert saved == 4 and stored_ids(database) == ["id0", "id2", "id3", "id4"]
    assert all(seen)  # summaries were required, so no silent abstract fallback


def test_run_stops_when_gemini_fails_several_papers_in_a_row(monkeypatch, database):
    cand = candidates(8)

    async def fake_find(category, days_back, limit, sort_by):
        return list(cand)

    async def always_fails(paper, category, require_summary=False, **kw):
        raise L.SummaryUnavailable(paper["title"])

    monkeypatch.setattr(L, "find_candidate_papers", fake_find)
    monkeypatch.setattr(L, "process_candidate", always_fails)
    monkeypatch.setattr(cli, "CATEGORIES", ["Physics"])
    _gemini_configured(monkeypatch)
    calls = []
    original = L.process_candidate

    async def counting(paper, category, **kw):
        calls.append(paper["source_id"])
        return await original(paper, category, **kw)

    monkeypatch.setattr(L, "process_candidate", counting)
    saved = asyncio.run(cli.fetch_latest_command("Physics", 7, 8))
    assert saved == 0 and len(calls) == L.LLM_FAILURE_LIMIT  # stopped, didn't grind through all 8


def test_process_candidate_refuses_abstract_fallback_when_summary_required(monkeypatch):
    async def noop(papers, *a, **k):
        return papers

    async def abstract_only(papers):
        for p in papers:
            p["description"] = p["abstract"]
            p["description_source"] = "abstract"

    monkeypatch.setattr(L, "_fill_open_access_links", noop)
    monkeypatch.setattr(L, "_fill_missing_abstracts", noop)
    monkeypatch.setattr(L, "_apply_language_and_translation", noop)
    monkeypatch.setattr(L, "_apply_summaries", abstract_only)

    async def embed_and_image(papers, *a):
        return None

    monkeypatch.setattr(L, "_apply_embeddings", embed_and_image)
    monkeypatch.setattr(L, "_attach_images", embed_and_image)
    paper = {"source": "s", "source_id": "1", "title": "T", "abstract": "A real abstract that is long enough."}
    with pytest.raises(L.SummaryUnavailable):
        asyncio.run(L.process_candidate(dict(paper), "Physics", require_summary=True))
    # without the requirement (no key, or --continue-without-llm) the abstract is accepted and labeled
    stored = asyncio.run(L.process_candidate(dict(paper), "Physics", require_summary=False))
    assert stored["description_source"] == "abstract"
