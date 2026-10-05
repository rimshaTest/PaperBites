"""Embedding models: free-tier limits, budget-tracked cycling across models, per-vector model
tagging, title+description text, and model-aware search. Run from backend/."""
import asyncio
from types import SimpleNamespace

import mongomock
import pytest

import llm_usage
import paper.embeddings as E

A, B = "gemini-embedding-001", "gemini-embedding-2"
OVERLOAD = "503 UNAVAILABLE. high demand"


class FakeEmbedder:
    def __init__(self, vector, query_vector=None, failures=0, error=OVERLOAD):
        self.vector, self.query_vector = vector, query_vector or vector
        self.failures, self.error, self.calls, self.texts = failures, error, 0, []

    async def aembed_documents(self, texts):
        self.calls += 1
        self.texts += texts
        if self.calls <= self.failures:
            raise RuntimeError(self.error)
        return [self.vector]

    async def aembed_query(self, text):
        self.calls += 1
        if self.calls <= self.failures:
            raise RuntimeError(self.error)
        return self.query_vector


@pytest.fixture
def setup(monkeypatch):
    tracker = llm_usage.LLMUsageTracker(
        limits={A: llm_usage.Limits(rpm=100, tpm=10**9, rpd=1000), B: llm_usage.Limits(rpm=100, tpm=10**9, rpd=14_400)},
        get_db=lambda: mongomock.MongoClient().paperbites,
    )
    monkeypatch.setattr(llm_usage, "tracker", tracker)
    cfg = {"api.gemini_key": "key", "api.gemini_embedding_models": f"models/{A},{B}"}
    monkeypatch.setattr(E, "config_instance", SimpleNamespace(get=lambda k, d=None: cfg.get(k)))
    clients = {A: FakeEmbedder([1.0, 0.0, 0.0]), B: FakeEmbedder([0.0, 1.0])}
    monkeypatch.setattr(E, "_get_embeddings_client", lambda model=None: clients[llm_usage.model_key(model or A)])
    sleeps = []

    async def fake_sleep(seconds):
        sleeps.append(seconds)

    monkeypatch.setattr(E, "_lap_sleep", fake_sleep)
    return tracker, clients, sleeps


def run(coro):
    return asyncio.run(coro)


def test_default_free_tier_limits_match_the_rate_limit_page():
    d = llm_usage.DEFAULT_LIMITS
    for model in ("gemini-3.8-flash", "gemini-3.7-flash", "gemini-3.6-flash", "gemini-3.5-flash",
                  "gemini-3-flash-preview", "gemini-2.5-flash"):
        assert d[model] == llm_usage.Limits(rpm=5, tpm=250_000, rpd=20), model
    assert d["gemini-2.5-flash-lite"] == llm_usage.Limits(rpm=10, tpm=250_000, rpd=20)
    assert d["gemini-3.5-flash-lite"] == llm_usage.Limits(rpm=15, tpm=250_000, rpd=500)
    assert d["gemini-3.1-flash-lite"] == llm_usage.Limits(rpm=15, tpm=250_000, rpd=500)
    assert d[A] == llm_usage.Limits(rpm=100, tpm=30_000, rpd=1_000)
    assert d[B] == llm_usage.Limits(rpm=30, tpm=16_000, rpd=14_400)


def test_every_default_summarizer_model_has_a_limit():
    import paper.summarize as S
    for name in S._MODEL_NAMES:
        assert name in llm_usage.DEFAULT_LIMITS, name


def test_model_key_strips_the_models_prefix():
    assert llm_usage.model_key("models/gemini-embedding-001") == "gemini-embedding-001"
    assert llm_usage.model_key("gemini-3.5-flash") == "gemini-3.5-flash"


def test_embedding_text_is_title_plus_description():
    assert E.embedding_text({"title": " A Title ", "description": "The summary."}) == "A Title\n\nThe summary."
    assert E.embedding_text({"description": "Only this."}) == "Only this."


def test_embedding_is_tagged_with_the_model_and_counted(setup):
    tracker, clients, sleeps = setup
    vector, model = run(E.embed_document_with_model("Title\n\nBody"))
    assert vector == [1.0, 0.0, 0.0] and model == A
    assert clients[A].texts == ["Title\n\nBody"]
    assert {r["model"]: r["requests_today"] for r in tracker.report([A, B])}[A] == 1


def test_falls_through_to_the_next_model_when_one_is_spent_for_the_day(setup):
    tracker, clients, sleeps = setup
    tracker.set_daily_requests(A, 1000)
    vector, model = run(E.embed_document_with_model("text"))
    assert model == B and vector == [0.0, 1.0] and clients[A].calls == 0


def test_503_on_one_embedding_model_moves_to_the_next_without_waiting(setup):
    tracker, clients, sleeps = setup
    clients[A].failures = 1
    vector, model = run(E.embed_document_with_model("text"))
    assert model == B and sleeps == []
    assert {r["model"]: r["requests_today"] for r in tracker.report([A, B])}[A] == 0  # the 503 didn't count


def test_all_embedding_models_overloaded_waits_a_minute_then_continues(setup):
    tracker, clients, sleeps = setup
    clients[A].failures, clients[B].failures = 2, 2
    result = run(E.embed_document_with_model("text"))
    assert result is not None and sleeps == [60.0, 60.0]


def test_no_embedding_when_every_model_is_spent(setup):
    tracker, clients, sleeps = setup
    tracker.set_daily_requests(A, 1000)
    tracker.set_daily_requests(B, 14_400)
    assert run(E.embed_document_with_model("text")) is None


def test_no_api_key_means_no_embedding(setup, monkeypatch):
    monkeypatch.setattr(E, "config_instance", SimpleNamespace(get=lambda k, d=None: None))
    monkeypatch.setattr(E, "_get_embeddings_client", lambda model=None: None)
    assert run(E.embed_document_with_model("text")) is None


# ---- model-aware search --------------------------------------------------------------------
def test_search_compares_each_paper_only_with_a_query_from_its_own_model(setup):
    tracker, clients, sleeps = setup
    clients[A].query_vector = [1.0, 0.0, 0.0]
    clients[B].query_vector = [0.0, 1.0]
    docs = [
        {"title": "old", "embedding": [1.0, 0.0, 0.0]},                       # legacy: no model tag -> model A
        {"title": "a-far", "embedding": [0.0, 1.0, 0.0], "embedding_model": A},
        {"title": "b-near", "embedding": [0.0, 1.0], "embedding_model": B},
        {"title": "b-far", "embedding": [1.0, 0.0], "embedding_model": B},
    ]
    scored = run(E.score_documents("q", docs))
    order = [d["title"] for _, d in scored]
    assert set(order) == {"old", "a-far", "b-near", "b-far"}
    assert dict((d["title"], round(s, 2)) for s, d in scored) == {"old": 1.0, "a-far": 0.0, "b-near": 1.0, "b-far": 0.0}


def test_search_skips_papers_whose_model_cant_embed_the_query(setup):
    tracker, clients, sleeps = setup
    tracker.set_daily_requests(B, 14_400)  # B's quota is spent: its query can't be embedded
    docs = [
        {"title": "a", "embedding": [1.0, 0.0, 0.0], "embedding_model": A},
        {"title": "b", "embedding": [0.0, 1.0], "embedding_model": B},
    ]
    scored = run(E.score_documents("q", docs))
    assert [d["title"] for _, d in scored] == ["a"]  # b left out, not scored against the wrong space


def test_cosine_of_different_lengths_is_zero():
    assert E.cosine_similarity([1.0, 0.0], [1.0, 0.0, 0.0]) == 0.0


def test_backfill_embeds_title_and_description_and_records_the_model(setup, monkeypatch):
    tracker, clients, sleeps = setup
    import db
    database = mongomock.MongoClient().paperbites
    monkeypatch.setattr(db, "get_db", lambda: database)
    database.papers.insert_many([
        {"title": "Alpha", "description": "About alpha."},
        {"title": "Beta", "description": ""},  # nothing to embed
        {"title": "Done", "description": "x", "embedding": [9.0], "embedding_model": A},
    ])
    result = run(E.backfill_missing_embeddings())
    assert result == {"total_missing": 2, "embedded": 1, "skipped_no_description": 1, "failed": 0}
    stored = database.papers.find_one({"title": "Alpha"})
    assert stored["embedding"] == [1.0, 0.0, 0.0] and stored["embedding_model"] == A
    assert clients[A].texts == ["Alpha\n\nAbout alpha."]
