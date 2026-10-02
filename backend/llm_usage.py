"""
Tracks and enforces Gemini free-tier usage per model: requests per minute (RPM), tokens per
minute (TPM) and requests per day (RPD).

Why this exists: the free tier is tiny (gemini-3.5-flash: 5 RPM, 250k TPM, 20 RPD) and a daily cap
that's hit mid-run used to turn into a flood of retries and silently degraded descriptions.
Every LLM call now goes through `tracker.acquire()` first, which waits out a per-minute limit,
refuses once a day's budget is spent, and counts the call. Daily counts are persisted in MongoDB
(`llm_usage` collection, one document per model per day) so they survive across runs - a second
`fetch-latest` the same day knows how much of the budget the first one used.

Limits are per model. Defaults for known models are in DEFAULT_LIMITS; override or add models with
`api.gemini_limits` in config.json (or PAPERBITES_GEMINI_LIMITS as JSON), e.g.
{"gemini-3.5-flash-lite": {"rpm": 15, "tpm": 250000, "rpd": 500}}. A model with no configured
limit is never gated locally (the API's own 429s are still handled), only counted.

Google resets daily quotas at midnight Pacific time, so "a day" here is a Pacific calendar day.
"""
import asyncio
import datetime
import json
import logging
import os
import re
import time
from collections import deque
from typing import Callable, Deque, Dict, List, NamedTuple, Optional, Tuple

logger = logging.getLogger("paperbites.llm_usage")

WINDOW_SECONDS = 60.0
# Rough allowance for a reply when estimating a call's tokens before it's made.
EXPECTED_OUTPUT_TOKENS = 600


class Limits(NamedTuple):
    rpm: Optional[int] = None
    tpm: Optional[int] = None
    rpd: Optional[int] = None


DEFAULT_LIMITS: Dict[str, Limits] = {
    "gemini-3.5-flash": Limits(rpm=5, tpm=250_000, rpd=20),
}


class LLMQuotaExhausted(Exception):
    """Every configured model has used up its daily budget."""

    def __init__(self, seconds_until_reset: float = 0.0):
        hours = seconds_until_reset / 3600
        super().__init__(f"Daily LLM quota exhausted for all models; resets in about {hours:.1f}h")
        self.seconds_until_reset = seconds_until_reset


def _time_now() -> float:
    return time.time()


def estimate_tokens(text: str) -> int:
    """~4 characters per token, plus room for the reply. An estimate used only to pace calls;
    the real count from the response replaces it once known."""
    return len(text or "") // 4 + 1 + EXPECTED_OUTPUT_TOKENS


def pacific_date(now: float) -> str:
    """The Pacific calendar date for a Unix timestamp (when Google's daily quotas reset)."""
    try:
        from zoneinfo import ZoneInfo
        local = datetime.datetime.fromtimestamp(now, ZoneInfo("America/Los_Angeles"))
    except Exception:
        # No tz database (e.g. Windows without the tzdata package): approximate with a fixed
        # UTC-8 offset - off by an hour during daylight saving, which only moves the reset time.
        local = datetime.datetime.fromtimestamp(now, datetime.timezone(datetime.timedelta(hours=-8)))
    return local.strftime("%Y-%m-%d")


def seconds_until_pacific_reset(now: float) -> float:
    try:
        from zoneinfo import ZoneInfo
        tz = ZoneInfo("America/Los_Angeles")
    except Exception:
        tz = datetime.timezone(datetime.timedelta(hours=-8))
    local = datetime.datetime.fromtimestamp(now, tz)
    tomorrow = (local + datetime.timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return max(0.0, (tomorrow - local).total_seconds())


def _configured_limits() -> Dict[str, Limits]:
    """DEFAULT_LIMITS overlaid with api.gemini_limits / PAPERBITES_GEMINI_LIMITS."""
    limits = dict(DEFAULT_LIMITS)
    raw = None
    try:
        from config import Config
        raw = Config().get("api.gemini_limits")
    except Exception:
        pass
    raw = raw or os.getenv("PAPERBITES_GEMINI_LIMITS")
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except ValueError:
            logger.warning("PAPERBITES_GEMINI_LIMITS is not valid JSON; ignoring it")
            raw = None
    for model, values in (raw or {}).items():
        if isinstance(values, dict):
            limits[model] = Limits(
                rpm=values.get("rpm"), tpm=values.get("tpm"), rpd=values.get("rpd")
            )
    return limits


class Reservation(NamedTuple):
    model: str
    started: float
    estimated_tokens: int
    entry: list  # the [timestamp, tokens] row in the model's minute window, adjusted by finish()


class LLMUsageTracker:
    def __init__(self, clock: Callable[[], float] = time.time, limits: Optional[Dict[str, Limits]] = None,
                 get_db: Optional[Callable] = None):
        self._clock = clock
        self._limits = limits  # None -> resolved lazily from config
        self._get_db = get_db
        self._windows: Dict[str, Deque[list]] = {}
        self._daily: Dict[Tuple[str, str], Dict[str, int]] = {}
        self._cooldown_until: Dict[str, float] = {}
        self._lock = asyncio.Lock()
        self._warned_no_db = False

    # ---- configuration --------------------------------------------------------------------
    def limits_for(self, model: str) -> Limits:
        if self._limits is None:
            self._limits = _configured_limits()
        return self._limits.get(model, Limits())

    # ---- persistence ----------------------------------------------------------------------
    def _collection(self):
        try:
            if self._get_db is not None:
                return self._get_db().llm_usage
            import db
            return db.get_db().llm_usage
        except Exception as e:
            if not self._warned_no_db:
                logger.warning(f"LLM usage won't persist across runs (no database): {e}")
                self._warned_no_db = True
            return None

    def _day(self, model: str, date: str) -> Dict[str, int]:
        key = (model, date)
        if key not in self._daily:
            stored = {}
            collection = self._collection()
            if collection is not None:
                try:
                    stored = collection.find_one({"_id": f"{model}:{date}"}) or {}
                except Exception as e:
                    logger.warning(f"Couldn't read LLM usage for {model}: {e}")
            self._daily[key] = {
                "requests": int(stored.get("requests", 0)),
                "tokens": int(stored.get("tokens", 0)),
            }
        return self._daily[key]

    def _persist(self, model: str, date: str, requests: int = 0, tokens: int = 0, set_requests: Optional[int] = None):
        collection = self._collection()
        if collection is None:
            return
        update = {"$set": {"model": model, "date": date}}
        if set_requests is not None:
            update["$set"]["requests"] = set_requests
        inc = {}
        if requests and set_requests is None:
            inc["requests"] = requests
        if tokens:
            inc["tokens"] = tokens
        if inc:
            update["$inc"] = inc
        try:
            collection.update_one({"_id": f"{model}:{date}"}, update, upsert=True)
        except Exception as e:
            logger.warning(f"Couldn't save LLM usage for {model}: {e}")

    # ---- availability ---------------------------------------------------------------------
    def _window(self, model: str, now: float) -> Deque[list]:
        window = self._windows.setdefault(model, deque())
        while window and now - window[0][0] >= WINDOW_SECONDS:
            window.popleft()
        return window

    def availability(self, model: str, estimated_tokens: int = 0) -> Tuple[str, float]:
        """('ok', 0) if a call can go now, ('wait', seconds) if a per-minute limit has to clear
        first, ('exhausted', seconds_until_reset) if the day's request budget is spent."""
        now = self._clock()
        limits = self.limits_for(model)
        date = pacific_date(now)

        if limits.rpd is not None and self._day(model, date)["requests"] >= limits.rpd:
            return "exhausted", seconds_until_pacific_reset(now)

        wait = max(0.0, self._cooldown_until.get(model, 0.0) - now)
        window = self._window(model, now)
        if limits.rpm is not None and len(window) >= limits.rpm:
            wait = max(wait, WINDOW_SECONDS - (now - window[len(window) - limits.rpm][0]))
        if limits.tpm is not None and window:
            used = sum(tokens for _, tokens in window)
            if used + estimated_tokens > limits.tpm:
                # Wait until enough of the oldest calls age out of the minute window
                freed, needed = 0, used + estimated_tokens - limits.tpm
                for ts, tokens in window:
                    freed += tokens
                    if freed >= needed:
                        wait = max(wait, WINDOW_SECONDS - (now - ts))
                        break
                else:
                    wait = max(wait, WINDOW_SECONDS)
        return ("wait", wait + 0.05) if wait > 0 else ("ok", 0.0)

    def choose(self, models: List[str], estimated_tokens: int = 0) -> Optional[str]:
        """The best model to call now from `models` (already in preference order): one that's
        available immediately, else the one that frees up soonest, else None if all are spent
        for the day."""
        soonest: Optional[Tuple[float, str]] = None
        for model in models:
            status, wait = self.availability(model, estimated_tokens)
            if status == "ok":
                return model
            if status == "wait" and (soonest is None or wait < soonest[0]):
                soonest = (wait, model)
        return soonest[1] if soonest else None

    def all_exhausted(self, models: List[str]) -> bool:
        return bool(models) and all(self.availability(m)[0] == "exhausted" for m in models)

    # ---- acquiring and recording ----------------------------------------------------------
    async def acquire(self, model: str, estimated_tokens: int = 0) -> Reservation:
        """Wait out any per-minute limit, then count one request against `model`. Raises
        LLMQuotaExhausted if the model's daily budget is already spent."""
        while True:
            async with self._lock:
                status, wait = self.availability(model, estimated_tokens)
                if status == "exhausted":
                    raise LLMQuotaExhausted(wait)
                if status == "ok":
                    return self._reserve(model, estimated_tokens)
            logger.info(f"{model}: waiting {wait:.0f}s for a per-minute limit to clear")
            await asyncio.sleep(min(wait, 15.0))

    def _reserve(self, model: str, estimated_tokens: int) -> Reservation:
        now = self._clock()
        date = pacific_date(now)
        entry = [now, estimated_tokens]
        self._window(model, now).append(entry)
        day = self._day(model, date)
        day["requests"] += 1
        day["tokens"] += estimated_tokens
        self._persist(model, date, requests=1, tokens=estimated_tokens)
        return Reservation(model, now, estimated_tokens, entry)

    def finish(self, reservation: Reservation, actual_tokens: Optional[int] = None) -> None:
        """Replace the estimate with the real token count once the response is known."""
        if actual_tokens is None or actual_tokens == reservation.estimated_tokens:
            return
        delta = actual_tokens - reservation.estimated_tokens
        reservation.entry[1] = actual_tokens
        date = pacific_date(reservation.started)
        self._day(reservation.model, date)["tokens"] += delta
        self._persist(reservation.model, date, tokens=delta)

    def log_call(self, model: str, tokens: int = 0) -> None:
        """Count a call that isn't gated (e.g. embeddings) so it shows in the usage report."""
        now = self._clock()
        date = pacific_date(now)
        day = self._day(model, date)
        day["requests"] += 1
        day["tokens"] += tokens
        self._persist(model, date, requests=1, tokens=tokens)

    def note_api_quota_error(self, model: str, message: str) -> None:
        """React to the API itself reporting 429: a per-day quota error exhausts the model for
        the rest of the (Pacific) day even if our own count was off; a per-minute one just
        starts a cooldown (the API's suggested retry delay when it gives one)."""
        now = self._clock()
        text = (message or "").lower()
        if "perday" in text or "per day" in text:
            limits = self.limits_for(model)
            date = pacific_date(now)
            day = self._day(model, date)
            # Treat the budget as fully spent: our own count may be low (another machine or an
            # earlier run used quota we didn't see) and the model may have no configured limit.
            target = max(day["requests"], limits.rpd or 0, 1)
            day["requests"] = target
            self._persist(model, date, set_requests=target)
            self._limits = dict(self._limits if self._limits is not None else _configured_limits())
            self._limits[model] = Limits(rpm=limits.rpm, tpm=limits.tpm, rpd=target)
            logger.warning(f"{model}: the API reports its daily quota is used up")
            return
        match = re.search(r"retry in ([\d.]+)s", text)
        delay = float(match.group(1)) if match else 30.0
        self._cooldown_until[model] = now + delay

    # ---- reporting ------------------------------------------------------------------------
    def report(self, models: Optional[List[str]] = None) -> List[Dict]:
        now = self._clock()
        date = pacific_date(now)
        names = set(models or []) | {m for (m, d) in self._daily if d == date} | set(self._limits or _configured_limits())
        rows = []
        for model in sorted(names):
            limits = self.limits_for(model)
            day = self._day(model, date)
            window = self._window(model, now)
            rows.append({
                "model": model, "date": date,
                "requests_today": day["requests"], "rpd": limits.rpd,
                "tokens_today": day["tokens"],
                "requests_last_minute": len(window), "rpm": limits.rpm,
                "tokens_last_minute": sum(t for _, t in window), "tpm": limits.tpm,
            })
        return rows

    def format_report(self, models: Optional[List[str]] = None) -> str:
        lines = []
        for row in self.report(models):
            def frac(used, cap):
                return f"{used}/{cap}" if cap is not None else f"{used}/-"
            lines.append(
                f"{row['model']}: {frac(row['requests_today'], row['rpd'])} requests today, "
                f"{row['tokens_today']:,} tokens today "
                f"(last minute: {frac(row['requests_last_minute'], row['rpm'])} req, "
                f"{frac(row['tokens_last_minute'], row['tpm'])} tokens) [Pacific day {row['date']}]"
            )
        return "\n".join(lines)


def is_quota_error(error: Exception) -> bool:
    text = str(error)
    return "429" in text or "RESOURCE_EXHAUSTED" in text


tracker = LLMUsageTracker()
