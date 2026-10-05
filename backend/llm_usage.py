"""
Tracks and enforces Gemini free-tier usage per model: requests per minute (RPM), tokens per
minute (TPM) and requests per day (RPD).

Why this exists: the free tier is tiny (e.g. gemini-3.5-flash: 5 RPM, 250k TPM, 20 RPD) and a daily cap
that's hit mid-run used to turn into a flood of retries and silently degraded descriptions.
Every LLM call now goes through `tracker.acquire()` first, which waits out a per-minute limit,
refuses once a day's budget is spent, and counts the call. Daily counts are persisted in MongoDB
(`llm_usage` collection, one document per model per day) so they survive across runs - a second
`fetch-latest` the same day knows how much of the budget the first one used.

Limits are per model (text and embedding models alike). Defaults for known models are in DEFAULT_LIMITS; override or add models with
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


# Free-tier limits per model, read from Google AI Studio's rate-limit page (https://ai.dev/rate-limit).
# They change over time and differ by account/plan - check that page and override any entry with
# api.gemini_limits / PAPERBITES_GEMINI_LIMITS. Keys are model names without the "models/" prefix.
_FLASH = Limits(rpm=5, tpm=250_000, rpd=20)
DEFAULT_LIMITS: Dict[str, Limits] = {
    # Text-out models
    "gemini-3.8-flash": _FLASH,
    "gemini-3.7-flash": _FLASH,
    "gemini-3.6-flash": _FLASH,
    "gemini-3.5-flash": _FLASH,
    "gemini-3-flash-preview": _FLASH,
    "gemini-2.5-flash": _FLASH,
    "gemini-2.5-flash-lite": Limits(rpm=10, tpm=250_000, rpd=20),
    "gemini-3.5-flash-lite": Limits(rpm=15, tpm=250_000, rpd=500),
    "gemini-3.1-flash-lite": Limits(rpm=15, tpm=250_000, rpd=500),
    # Embedding models ("Other models")
    "gemini-embedding-001": Limits(rpm=100, tpm=30_000, rpd=1_000),
    "gemini-embedding-2": Limits(rpm=30, tpm=16_000, rpd=14_400),
}


def model_key(name: str) -> str:
    """The name limits and usage are tracked under: no "models/" prefix."""
    return name[len("models/"):] if name.startswith("models/") else name


class LLMQuotaExhausted(Exception):
    """Every configured model has used up its daily budget."""

    def __init__(self, seconds_until_reset: float = 0.0):
        hours = seconds_until_reset / 3600
        super().__init__(f"Daily LLM quota exhausted for all models; resets in about {hours:.1f}h")
        self.seconds_until_reset = seconds_until_reset


def _time_now() -> float:
    return time.time()


class SkipModel(Exception):
    """Raised by a call attempt to say "this model can't be used for this call" (not configured,
    unusable reply) without it counting as a server error."""


class LLMUnavailable(Exception):
    """Gemini keeps failing (outage, overload) even though quota remains."""


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

    def refund(self, reservation: Reservation) -> None:
        """Undo a reservation for a call that failed for a server-side reason (e.g. a 503): the
        request never ran, so it shouldn't count against the model's per-minute or daily budget."""
        window = self._windows.get(reservation.model)
        if window is not None and reservation.entry in window:
            window.remove(reservation.entry)
        date = pacific_date(reservation.started)
        tokens = reservation.entry[1]
        day = self._day(reservation.model, date)
        day["requests"] = max(0, day["requests"] - 1)
        day["tokens"] = max(0, day["tokens"] - tokens)
        self._persist(reservation.model, date, requests=-1, tokens=-tokens)

    def log_call(self, model: str, tokens: int = 0) -> None:
        """Count a call that isn't gated (e.g. embeddings) so it shows in the usage report."""
        now = self._clock()
        date = pacific_date(now)
        day = self._day(model, date)
        day["requests"] += 1
        day["tokens"] += tokens
        self._persist(model, date, requests=1, tokens=tokens)

    def set_daily_requests(self, model: str, requests: int) -> None:
        """Tell the tracker how many requests this model has already used today - for quota
        spent before tracking existed, or by another machine/project on the same key."""
        now = self._clock()
        date = pacific_date(now)
        self._day(model, date)["requests"] = requests
        self._persist(model, date, set_requests=requests)

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
        names = {model_key(m) for m in (models or [])} | {m for (m, d) in self._daily if d == date}
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


def is_transient_error(error: Exception) -> bool:
    """A temporary server-side failure worth retrying (overload, outage, timeout) - as opposed to
    a quota limit (handled by the tracker) or a permanent error like an unknown model name."""
    if isinstance(error, (asyncio.TimeoutError, TimeoutError, ConnectionError)):
        return True
    text = str(error).lower()
    return any(marker in text for marker in (
        "503", "unavailable", "high demand", "overloaded", "500 internal", "internal error",
        "504", "deadline_exceeded", "timed out", "timeout", "connection reset", "temporarily",
    ))


def is_quota_error(error: Exception) -> bool:
    text = str(error)
    return "429" in text or "RESOURCE_EXHAUSTED" in text


tracker = LLMUsageTracker()


async def cycle_models(
    models: List[str],
    estimated_tokens: int,
    attempt: Callable,
    label: str,
    *,
    lap_wait: float = 60.0,
    max_wait: Optional[float] = None,
    sleep: Optional[Callable] = None,
) -> Optional[Tuple[str, object]]:
    """Run `attempt(model)` against the first model that works, cycling through `models` (in
    preference order) with budget tracking. Used for every Gemini call - text and embeddings.

    `attempt(model)` does the request and returns (value, actual_tokens); a falsy value means the
    reply was unusable. Failures are handled by kind:
    - Overload / temporary server errors (503, timeouts): the call is refunded (it never ran, so
      it uses no budget) and the NEXT model is tried at once. When every model has been overloaded
      in a lap, wait `lap_wait` seconds and go around again - indefinitely unless `max_wait`
      (total seconds) is set.
    - Quota (429): the tracker is told; a daily-quota error retires that model for the day.
    - Anything else (an unknown model name, SkipModel, an unusable reply): that model is skipped
      for this call.
    Models are chosen by tracker.choose: one available now if any, else the one whose per-minute
    limit clears soonest, never one whose daily budget is spent. Returns (model, value), or None
    if nothing worked or every model is out of budget.
    """
    sleep = sleep or asyncio.sleep
    remaining = list(models)  # not permanently out for this call
    overloaded = set()  # transient-failed this lap; retried after the wait
    waited, lap = 0.0, 1

    while remaining:
        available = [m for m in remaining if m not in overloaded]
        if not available:
            if max_wait is not None and waited >= max_wait:
                logger.warning(f"Gemini stayed overloaded for {waited:.0f}s; giving up on {label}")
                return None
            logger.warning(f"All Gemini models are overloaded (lap {lap}); waiting {lap_wait:.0f}s, then retrying {label}")
            await sleep(lap_wait)
            waited += lap_wait
            overloaded.clear()
            lap += 1
            continue

        model = tracker.choose(available, estimated_tokens)
        if model is None:
            return None  # every available model is out of budget for today
        try:
            reservation = await tracker.acquire(model, estimated_tokens)
        except LLMQuotaExhausted:
            remaining.remove(model)
            continue

        logger.info(f"Calling Gemini model '{model}' for {label}")
        try:
            value, tokens = await attempt(model)
        except SkipModel:
            tracker.finish(reservation, None)
            remaining.remove(model)
            continue
        except Exception as e:
            if is_quota_error(e):
                tracker.finish(reservation, None)
                tracker.note_api_quota_error(model, str(e))
                logger.warning(f"Gemini model '{model}' hit a quota limit for {label}")
                remaining.remove(model)
            elif is_transient_error(e):
                tracker.refund(reservation)
                overloaded.add(model)
                logger.warning(f"Gemini model '{model}' is overloaded or unavailable for {label}; trying the next one")
            else:
                tracker.finish(reservation, None)
                logger.warning(f"Gemini model '{model}' failed for {label}: {e}")
                remaining.remove(model)
            continue

        tracker.finish(reservation, tokens)
        if value:
            return model, value
        remaining.remove(model)

    return None
