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


def test_client_retries_are_kept_low_so_429s_dont_stall_the_run(monkeypatch):
    pytest.importorskip("langchain_google_genai")
    monkeypatch.setattr(S, "_llm_cache", {})
    monkeypatch.setattr(S, "config_instance", SimpleNamespace(get=lambda k, d=None: "key" if k == "api.gemini_key" else None))
    assert S._get_llm_for_model(FLASH).max_retries == 1  # the library default is 6
    monkeypatch.setattr(S, "_llm_cache", {})
    monkeypatch.setattr(
        S, "config_instance",
        SimpleNamespace(get=lambda k, d=None: {"api.gemini_key": "key", "api.gemini_max_retries": 3}.get(k)),
    )
    assert S._get_llm_for_model(FLASH).max_retries == 3


# ---- overload (503) handling: cycle models, wait a minute per lap, keep going ---------------
OVERLOAD = "503 UNAVAILABLE. {'error': {'code': 503, 'message': 'This model is currently experiencing high demand.'}}"


class FlakyLLM:
    """Fails with `error` for the first `failures` calls, then answers."""

    def __init__(self, reply, failures=0, error=OVERLOAD, tokens=100):
        self.reply, self.failures, self.error, self.tokens, self.calls = reply, failures, error, tokens, 0

    async def ainvoke(self, payload):
        self.calls += 1
        if self.calls <= self.failures:
            raise RuntimeError(self.error)
        return SimpleNamespace(content=self.reply, usage_metadata={"total_tokens": self.tokens})


@pytest.fixture
def overload_setup(monkeypatch):
    tracker = llm_usage.LLMUsageTracker(
        limits={FLASH: llm_usage.Limits(rpm=100, tpm=10**9, rpd=20), LITE: llm_usage.Limits(rpm=100, tpm=10**9, rpd=500)},
        get_db=lambda: mongomock.MongoClient().paperbites,
    )
    monkeypatch.setattr(llm_usage, "tracker", tracker)
    monkeypatch.setattr(S, "config_instance", SimpleNamespace(get=lambda k, d=None: "key" if k == "api.gemini_key" else None))
    monkeypatch.setattr(S, "_configured_model_names", lambda: [FLASH, LITE])
    monkeypatch.setattr(S, "_next_model_index", 0)
    sleeps = []

    async def fake_sleep(seconds):
        sleeps.append(seconds)

    monkeypatch.setattr(S, "_backoff_sleep", fake_sleep)
    llms = {}
    monkeypatch.setattr(S, "_get_llm_for_model", lambda name: llms[name])
    return tracker, llms, sleeps


def test_503_on_one_model_moves_straight_to_the_next_without_waiting(overload_setup):
    tracker, llms, sleeps = overload_setup
    llms[FLASH] = FlakyLLM("Flash.", failures=1)
    llms[LITE] = FlakyLLM("Lite.")
    assert summarize() == "Lite."
    assert sleeps == []  # cycled to the next model immediately


def test_when_every_model_is_overloaded_it_waits_a_minute_per_lap_and_keeps_going(overload_setup):
    tracker, llms, sleeps = overload_setup
    llms[FLASH] = FlakyLLM("Flash.", failures=3)  # overloaded for 3 laps
    llms[LITE] = FlakyLLM("Lite.", failures=3)
    assert summarize() in ("Flash.", "Lite.")
    assert sleeps == [60.0, 60.0, 60.0]  # a flat minute after each full lap, never giving up


def test_overload_failures_dont_use_up_quota(overload_setup):
    tracker, llms, sleeps = overload_setup
    llms[FLASH] = FlakyLLM("Flash.", failures=2)
    llms[LITE] = FlakyLLM("Lite.", failures=2)
    summarize()
    used = {r["model"]: r["requests_today"] for r in tracker.report()}
    assert used[FLASH] + used[LITE] == 1  # only the call that actually succeeded counted


def test_overload_wait_is_configurable_and_can_give_up(overload_setup, monkeypatch):
    tracker, llms, sleeps = overload_setup
    llms[FLASH] = FlakyLLM("x", failures=10**6)
    llms[LITE] = FlakyLLM("x", failures=10**6)
    monkeypatch.setattr(S, "config_instance", SimpleNamespace(get=lambda k, d=None: {
        "api.gemini_key": "key", "api.gemini_overload_wait_seconds": 30, "api.gemini_overload_max_wait_seconds": 90,
    }.get(k)))
    assert summarize() is None
    assert sleeps == [30.0, 30.0, 30.0]  # 90s of waiting, then it gives up


def test_non_transient_error_drops_only_that_model(overload_setup):
    tracker, llms, sleeps = overload_setup
    llms[FLASH] = FlakyLLM("x", failures=10**6, error="404 NOT_FOUND model does not exist")
    llms[LITE] = FlakyLLM("Lite.")
    assert summarize() == "Lite."
    assert llms[FLASH].calls == 1 and sleeps == []  # not retried, no waiting


def test_quota_error_retires_the_model_but_overload_elsewhere_still_cycles(overload_setup):
    tracker, llms, sleeps = overload_setup
    llms[FLASH] = FlakyLLM("x", failures=10**6, error=DAILY_429)
    llms[LITE] = FlakyLLM("Lite.", failures=1)
    assert summarize() == "Lite."
    assert tracker.availability(FLASH)[0] == "exhausted"
    assert sleeps == [60.0]  # lite overloaded alone on the next lap


def test_is_transient_error_classification():
    assert llm_usage.is_transient_error(RuntimeError(OVERLOAD))
    assert llm_usage.is_transient_error(asyncio.TimeoutError())
    assert not llm_usage.is_transient_error(RuntimeError(DAILY_429))
    assert not llm_usage.is_transient_error(RuntimeError("404 NOT_FOUND"))
