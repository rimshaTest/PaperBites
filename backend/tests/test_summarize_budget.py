"""The summarizer goes through the usage tracker: counts calls, records real token usage, retires
a model whose daily quota the API reports spent, and falls back to the next model."""
import asyncio
from types import SimpleNamespace

import mongomock
import pytest

import llm_usage
import paper.summarize as S

FLASH, LITE = "gemini-3.5-flash", "gemini-3.5-flash-lite"
DAILY_429 = (
    "429 RESOURCE_EXHAUSTED. Quota exceeded for metric: generate_content_free_tier_requests, "
    "limit: 20 quotaId: GenerateRequestsPerDayPerProjectPerModel-FreeTier"
)


class FakeLLM:
    def __init__(self, reply=None, error=None, tokens=1234):
        self.reply, self.error, self.tokens, self.calls = reply, error, tokens, 0

    async def ainvoke(self, payload):
        self.calls += 1
        if self.error:
            raise RuntimeError(self.error)
        return SimpleNamespace(content=self.reply, usage_metadata={"total_tokens": self.tokens})


@pytest.fixture
def setup(monkeypatch):
    tracker = llm_usage.LLMUsageTracker(
        limits={FLASH: llm_usage.Limits(rpm=100, tpm=10**9, rpd=20), LITE: llm_usage.Limits(rpm=100, tpm=10**9, rpd=500)},
        get_db=lambda: mongomock.MongoClient().paperbites,
    )
    monkeypatch.setattr(llm_usage, "tracker", tracker)
    monkeypatch.setattr(S, "config_instance", SimpleNamespace(get=lambda k, d=None: "key" if k == "api.gemini_key" else d))
    monkeypatch.setattr(S, "_configured_model_names", lambda: [FLASH, LITE])
    monkeypatch.setattr(S, "_next_model_index", 0)
    llms = {FLASH: FakeLLM(reply="Flash summary."), LITE: FakeLLM(reply="Lite summary.")}
    monkeypatch.setattr(S, "_get_llm_for_model", lambda name: llms[name])
    return tracker, llms


def summarize():
    return asyncio.run(S.summarize_text("Title", "Some abstract text."))


def row(tracker, model):
    return next(r for r in tracker.report() if r["model"] == model)


def test_calls_are_counted_with_real_token_usage(setup):
    tracker, llms = setup
    assert summarize() == "Flash summary."
    assert row(tracker, FLASH)["requests_today"] == 1
    assert row(tracker, FLASH)["tokens_today"] == 1234


def test_daily_quota_error_falls_back_and_retires_the_model(setup):
    tracker, llms = setup
    llms[FLASH].error = DAILY_429
    assert summarize() == "Lite summary."
    assert tracker.availability(FLASH)[0] == "exhausted"
    flash_calls = llms[FLASH].calls
    assert summarize() == "Lite summary."
    assert llms[FLASH].calls == flash_calls  # not called again today


def test_returns_none_without_calling_when_every_model_is_spent(setup):
    tracker, llms = setup
    for model in (FLASH, LITE):
        tracker.note_api_quota_error(model, DAILY_429)
    assert summarize() is None
    assert llms[FLASH].calls == 0 and llms[LITE].calls == 0


def test_list_style_content_blocks_are_accepted(setup):
    tracker, llms = setup
    llms[FLASH].reply = [{"type": "text", "text": "Block summary."}]
    assert summarize() == "Block summary."


def test_classify_falls_through_on_unparseable_json(setup):
    tracker, llms = setup
    llms[FLASH].reply = "not json at all"
    llms[LITE].reply = '{"summary": "Good.", "category": "physics"}'
    result = asyncio.run(S.summarize_and_classify("T", "text", ["Physics", "Biology"]))
    assert result == {"summary": "Good.", "category": "Physics"}
