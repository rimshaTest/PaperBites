"""Gemini usage tracking: RPM / TPM / RPD limits, persistence across runs, Pacific-day reset."""
import asyncio
import datetime

import mongomock
import pytest

import llm_usage
from llm_usage import LLMQuotaExhausted, LLMUsageTracker, Limits

FLASH = "gemini-3.5-flash"
LIMITS = {FLASH: Limits(rpm=5, tpm=250_000, rpd=20)}
NOON_PACIFIC = datetime.datetime(2026, 10, 2, 12, 0, tzinfo=datetime.timezone(datetime.timedelta(hours=-8))).timestamp()


class Clock:
    def __init__(self, now=NOON_PACIFIC):
        self.now = now

    def __call__(self):
        return self.now


def make(clock=None, database=None, limits=LIMITS):
    database = database if database is not None else mongomock.MongoClient().paperbites
    return LLMUsageTracker(clock=clock or Clock(), limits=dict(limits), get_db=lambda: database), database


def acquire_now(tracker, model=FLASH, tokens=1000):
    return asyncio.run(asyncio.wait_for(tracker.acquire(model, tokens), timeout=1))


def test_defaults_match_the_known_free_tier():
    assert llm_usage.DEFAULT_LIMITS[FLASH] == Limits(rpm=5, tpm=250_000, rpd=20)


def test_rpm_blocks_sixth_call_until_the_window_clears():
    clock = Clock()
    tracker, _ = make(clock)
    for _ in range(5):
        acquire_now(tracker)
        clock.now += 1
    status, wait = tracker.availability(FLASH, 1000)
    assert status == "wait" and 50 < wait <= 60
    clock.now += 60
    assert tracker.availability(FLASH, 1000)[0] == "ok"


def test_tpm_blocks_when_the_minute_is_out_of_tokens():
    tracker, _ = make()
    acquire_now(tracker, tokens=240_000)
    assert tracker.availability(FLASH, 20_000)[0] == "wait"
    assert tracker.availability(FLASH, 5_000)[0] == "ok"


def test_rpd_exhaustion_is_refused_and_reported():
    clock = Clock()
    tracker, _ = make(clock)
    for _ in range(20):
        acquire_now(tracker, tokens=100)
        clock.now += 61  # stay under the per-minute limit
    status, wait = tracker.availability(FLASH, 100)
    assert status == "exhausted" and wait > 0
    with pytest.raises(LLMQuotaExhausted):
        acquire_now(tracker)
    assert tracker.all_exhausted([FLASH])


def test_daily_count_survives_a_new_run():
    clock = Clock()
    first, database = make(clock)
    for _ in range(20):
        acquire_now(first, tokens=100)
        clock.now += 61
    second, _ = make(clock, database)  # a fresh process, same database
    assert second.availability(FLASH, 100)[0] == "exhausted"


def test_budget_resets_at_midnight_pacific():
    clock = Clock()
    tracker, _ = make(clock)
    for _ in range(20):
        acquire_now(tracker, tokens=100)
        clock.now += 61
    assert tracker.availability(FLASH)[0] == "exhausted"
    clock.now += 13 * 3600  # past midnight Pacific
    assert tracker.availability(FLASH)[0] == "ok"
    assert tracker.report()[0]["requests_today"] == 0


def test_finish_replaces_the_estimate_with_real_tokens():
    tracker, _ = make()
    reservation = acquire_now(tracker, tokens=1000)
    tracker.finish(reservation, 4321)
    row = [r for r in tracker.report() if r["model"] == FLASH][0]
    assert row["tokens_today"] == 4321 and row["tokens_last_minute"] == 4321


def test_api_daily_quota_error_exhausts_the_model():
    tracker, _ = make(limits={})  # no local limit configured at all
    tracker.note_api_quota_error("some-model", "429 ... GenerateRequestsPerDayPerProjectPerModel-FreeTier ...")
    assert tracker.availability("some-model")[0] == "exhausted"


def test_api_per_minute_error_starts_a_cooldown():
    tracker, _ = make()
    tracker.note_api_quota_error(FLASH, "429 ... PerMinute ... Please retry in 27.6s.")
    status, wait = tracker.availability(FLASH)
    assert status == "wait" and 27 < wait < 29


def test_choose_prefers_an_available_model_then_the_soonest():
    other = "gemini-3.5-flash-lite"
    clock = Clock()
    tracker, _ = make(clock, limits={FLASH: Limits(rpm=1), other: Limits(rpm=1)})
    acquire_now(tracker, FLASH)
    assert tracker.choose([FLASH, other], 100) == other
    clock.now += 10
    acquire_now(tracker, other)
    assert tracker.choose([FLASH, other], 100) == FLASH  # FLASH's window clears first


def test_unconfigured_model_is_counted_but_never_gated():
    tracker, _ = make(limits={})
    for _ in range(50):
        tracker.log_call("embed-model", 10)
    assert tracker.availability("embed-model")[0] == "ok"
    assert tracker.report(["embed-model"])[0]["requests_today"] == 50


def test_format_report_mentions_limits():
    tracker, _ = make()
    acquire_now(tracker)
    text = tracker.format_report()
    assert "gemini-3.5-flash" in text and "1/20 requests today" in text and "1/5 req" in text


def test_set_daily_requests_marks_prior_usage(monkeypatch):
    clock = Clock()
    tracker, database = make(clock)
    tracker.set_daily_requests(FLASH, 20)  # e.g. quota spent before tracking existed
    assert tracker.availability(FLASH)[0] == "exhausted"
    second, _ = make(clock, database)  # persisted for the next run
    assert second.availability(FLASH)[0] == "exhausted"
