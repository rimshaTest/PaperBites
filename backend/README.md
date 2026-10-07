# PaperBites Backend

A Starlette (ASGI) API that fetches recent, open-access research papers from free academic APIs,
stores them in MongoDB, and serves them - along with accounts, bookmarks, interests, and profile
data - to the PaperBites mobile app.

There is no video-generation pipeline anymore. This backend used to convert papers into
narrated short-form videos (PDF download → OCR → summarize → compose video → upload to
Cloudinary); that entire pipeline (`video/`, `utils/cloudinary_storage.py`, the CLI's
`search`/`id`/`pdf` subcommands) was removed. The add-paper-by-citation feature (see API below)
uses `paper/citation.py`, which is new and reuses `paper/latest.py`'s Crossref/Unpaywall/
enrichment helpers directly rather than the older `paper/search.py` (Google Scholar-scraping-
based query search) - `search.py`, `download.py`, and `extraction.py` predate that pivot and
remain dormant; nothing currently calls them.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
```

Fill in `.env` with your own values (see `.env.example` for the full list - Mongo connection
string, Pexels/Gemini/Semantic Scholar API keys, contact email). Anything set in `.env`
overrides the matching value in `config.json` (see `config.py`'s `load_env()`); `config.json`'s
own copies of these are only a fallback for setups without a `.env` yet.

If you hit `ModuleNotFoundError: No module named 'langdetect'` on an older `pip`/`setuptools`,
pin `pip install "setuptools<60"` first, then retry - `langdetect`'s packaging predates modern
build isolation.

## Running

```bash
# Start the API server (serves on :8000)
python api_server.py

# Fetch/refresh papers into MongoDB - run this at least once before the app has anything to show
python cli.py fetch-latest [--category "Physics"] [--days 7] [--limit 20] [--search-pool 5] [--sort-by date|citations] [--refresh] [--continue-without-llm] [--no-llm]

# No Gemini at all (e.g. while it's having problems): same pipeline and stored format, but the
# description is the paper's own abstract and no embedding is made. Then, once Gemini is back:
python cli.py resummarize [--limit 20]      # real summaries + embeddings for those papers, one at a time

# Show today's Gemini usage per model against its limits (RPM / TPM / RPD)
python cli.py llm-usage
# Record quota already spent today (e.g. before tracking began), so no call is wasted finding out
python cli.py llm-usage --set-used gemini-3.5-flash 20
```

`fetch-latest` with no `--category` fetches all categories in `paper/latest.py`'s `CATEGORIES`
list. Semantic Scholar's anonymous rate limit is low and easy to exhaust across all 8 categories
in one run - set `PAPERBITES_SEMANTIC_SCHOLAR_KEY` in `.env` (free, see `.env.example`) if you
hit repeated rate-limit warnings. If `PAPERBITES_GEMINI_KEY` is set, description summarization
round-robins across several Gemini models (`paper/summarize.py`'s `_MODEL_NAMES`, overridable
via `PAPERBITES_GEMINI_MODELS`) so no single model's free-tier cap gates the whole run - a model
that's rate-limited or invalid is skipped immediately in favor of the next one, with no delay.
Each paper is also embedded exactly once here (`paper/embeddings.py`, one Gemini embedding call
per paper - not repeated on later reloads/views) for `GET /papers/search`'s semantic search.

**How `fetch-latest` runs.** Papers are processed one at a time: each is enriched (open-access
check, abstract, translation, Gemini summary, embedding, image), validated, and saved to MongoDB
before the next one starts, so a crash, Ctrl+C or quota stop keeps everything already finished.
Papers already stored (with a description) are skipped, so re-running resumes where you left off
and doesn't spend Gemini quota again; `--refresh` reprocesses them. `--limit` is the number of
*new* papers to save per category: stored and dropped candidates (not open access, no description)
don't count, so `--search-pool` (default 5) candidates are searched per paper wanted, and the run
stops once the limit is reached. A source that stays rate-limited (e.g. Semantic Scholar without a
key) is skipped for 10 minutes instead of being waited on for every category. When every Gemini model's
daily budget is spent the run stops with a message (rather than storing papers whose description
is just the raw abstract); `--continue-without-llm` overrides that.
**Overload (503) handling.** A 503 / timeout means Gemini is briefly overloaded, not out of quota, so
the run keeps trying instead of giving up: it moves to the next model immediately, and when every
model has been overloaded in one lap it waits 60 seconds and goes around again, indefinitely. These
failed attempts aren't counted against the per-minute or daily budget. Ctrl+C, a spent daily quota,
or the optional limit below are the only ways it stops. Tune with `api.gemini_overload_wait_seconds`
(default 60) and `api.gemini_overload_max_wait_seconds` (give up on a paper after this much total
waiting; default: never). Other errors (an unknown model name, an unusable reply) skip just that
model for the call.

If a paper still can't be summarized (every model failed for a non-overload reason, or the optional
max wait was reached), it is *not saved* - so it isn't stuck with a raw-abstract description - and
after 3 such papers in a row the run stops with a message. Papers saved without a real summary
(`--continue-without-llm`, or no API key) carry `description_source: "abstract"` so they can be
found and redone later with `python cli.py resummarize`. `fetch-latest --no-llm` skips Gemini
entirely (no key or quota needed) and stores every paper this way; papers with no abstract are
dropped, since there's nothing to describe them with.

**Embeddings.** Each paper's *title and description together* are embedded once at ingestion
(`paper/embeddings.py`), through the same usage tracker and the same cycling/503 handling as the
summarizer. Models are tried in `api.gemini_embedding_models` order (env
`PAPERBITES_GEMINI_EMBEDDING_MODELS`, comma-separated; default `gemini-embedding-001`). Vectors from
different embedding models can't be compared, so every stored paper records its `embedding_model`,
semantic search embeds the query once per model present and compares each paper only with its own
model's query vector, and the Visualize graph only links papers embedded by the same model. Papers
stored without an embedding (all embedding models spent or unavailable) can be filled in later with
`python cli.py backfill-embeddings`.

**Gemini usage tracking** (`llm_usage.py`). Every Gemini call is counted against per-model limits
- requests per minute, tokens per minute, requests per day - and a per-minute limit is waited
out, while a spent daily budget skips that model. Daily counts are saved in the `llm_usage`
collection so they carry across runs; the day resets at midnight Pacific, when Google resets
quotas. Built-in limits (free tier, from Google AI Studio's rate-limit page - check
https://ai.dev/rate-limit and override any of them, since they change): `gemini-3.8-flash`,
`gemini-3.7-flash`, `gemini-3.6-flash`, `gemini-3.5-flash`, `gemini-3-flash-preview` and
`gemini-2.5-flash` = 5 RPM / 250k TPM / 20 RPD each; `gemini-2.5-flash-lite` = 10 / 250k / 20;
`gemini-3.5-flash-lite` and `gemini-3.1-flash-lite` = 15 / 250k / 500; embeddings:
`gemini-embedding-001` = 100 / 30k / 1,000, `gemini-embedding-2` = 30 / 16k / 14,400. Each model has
its own quota, so the summarizer's default model list (`paper/summarize.py`) uses all of the text
models, full flash models first and the lite ones as overflow. Set others with
`api.gemini_limits` in config.json or `PAPERBITES_GEMINI_LIMITS` as JSON, e.g.
`{"gemini-3.5-flash-lite": {"rpm": 15, "tpm": 250000, "rpd": 500}}`. A model with no configured
limit is counted but not gated. A 429 from the API itself is also honored (a daily-quota error
retires the model for the day), and the Gemini client's own retries are kept low
(`api.gemini_max_retries`, default 1 instead of the library's 6) so a rate limit doesn't stall the run.

## API

All routes are under `/api`. Auth-required routes take `Authorization: Bearer <token>`.

**Papers**
- `GET /papers?category=&limit=&offset=` - the feed, newest first. When authenticated and the
  user has chosen interests, hard-filtered to papers whose categories match (see Interests below).
- `GET /papers/search?q=&limit=` - semantic search over papers embedded at ingestion
  (`paper/embeddings.py`), ranked by cosine similarity to the query. Brute-force in Python at
  this app's corpus size; unrelated to and not blended with the Interests hard filter above (see
  `paper/embeddings.py`'s module docstring for the scope decision behind that). A paper embedded
  before this feature existed (or one Gemini couldn't embed) is simply absent from results, not
  an error.
- `GET /papers/{id}` - a single paper.
- `POST /papers/{id}/view` (auth required) - records that the user clicked "View Original Paper"
  (`paper_views.py`) - the source data for the Visualizations tab's bubble map below.
- `GET /papers/viewed/graph` (auth required) - every paper the user has clicked through to read,
  connected pairwise by cosine similarity of their stored embeddings (≥0.75 - `paper/embeddings.py`,
  same helper `GET /papers/search` uses). → `{nodes: [{id, title, categories, journal}, ...],
  edges: [{source, target, similarity}, ...]}`. Embedding vectors never leave the server - only
  the resulting score per edge does.
- `GET /categories` - the fixed list of paper categories.
- `POST /papers/citation/search` `{citation}` (auth required) - resolves a raw pasted citation
  (MLA, APA, or any other style) OR a direct link to the paper's page (e.g. an open-access
  journal's article URL) into candidate matches, each with a confirmed open-access link resolved
  via Unpaywall. A citation is fuzzy-matched against Crossref; a URL is instead scraped for its
  `citation_*` `<meta>` tags (the Highwire/Google-Scholar metadata standard most publishers embed)
  to find a DOI - either from the tag itself or embedded directly in the URL - and looked up
  exactly against Crossref, falling back to a bibliographic search on the page's title/authors if
  no DOI can be found anywhere. → `{candidates: [{doi, title, authors, journal, published_date,
  url, is_open_access}, ...]}`
- `POST /papers/citation/confirm` (auth required) - takes one candidate from the search above,
  runs it through the same enrichment pipeline `fetch-latest` uses (abstract fallback,
  translation, card image), stores it, and auto-bookmarks it for the caller. Unlike
  `fetch-latest` (which already knows a paper's category from the search query that found it),
  this path has no category to start from - Gemini picks one from the fixed `/categories` list
  in the same call that generates the summary (`paper/summarize.py`'s
  `summarize_and_classify_paper`). A paper Gemini can't classify (no API key, or every model
  fails) is saved uncategorized rather than guessed. → the saved paper.
- `POST /papers/citation/review` `{input}` (auth required) - queues a citation/URL the search
  above couldn't resolve for manual admin review (`paper_reviews.py`, stored in MongoDB's
  `paper_reviews` collection), per the spec's fallback for when automated matching fails
  outright. No admin UI reads this queue yet - it's queried directly for now.
- `POST /papers/citation/scan` (auth required, multipart form with an `image` file) -
  **experimental**: extracts a citation from a photo of a paper's title page or a poster via
  Gemini vision (`paper/summarize.py`'s `extract_citation_text_from_image`), then resolves it
  exactly like the `/citation/search` above (so it also gets URL-embedded-DOI/meta-tag handling
  for free if the extracted text happens to be a URL). Tries a fixed, accuracy-first model order
  (`gemini-2.5-pro` → `gemini-2.5-flash` → `gemini-2.5-flash-lite`, overridable via
  `PAPERBITES_GEMINI_IMAGE_MODELS`) rather than the round-robin `fetch-latest` uses - this is one
  interactive photo per request, not bulk throughput, so read accuracy matters more than spreading
  load. No QR-code decoding - that would need a system `zbar` library this deployment doesn't
  assume is installed - so this only helps when Gemini can read the title/authors directly off
  the image. → `{candidates: [...], extracted:
  "<citation-like string>" | null}`

**Authors & journals**
- `GET /authors/{author_id}` - an author's name and every paper of theirs.
- `GET /journals/{journal_name}` - every paper published in that journal/venue.

**Auth**
- `POST /auth/signup` `{email, password}` → `{token, user}`
- `POST /auth/login` `{email, password}` → `{token, user}`
- `POST /auth/logout` (auth required)
- `POST /auth/forgot-password` / `POST /auth/reset-password` - emailed reset code flow
- `GET /auth/me` (auth required) → `{user}`

**Reading engagement** (auth required unless noted)
- `POST /papers/{paper_id}/view` - record a confirmed read (counted once per user per paper;
  feeds milestones and the streak).
- `POST /papers/{paper_id}/like` / `DELETE /papers/{paper_id}/like` - like or unlike a paper.
  `GET /papers/{paper_id}` returns `is_liked` only when called with the auth token.
- `GET /stats/reading` → `{total_read, by_category, milestones_reached, streak: {level, label}}`.
  Streak levels (`streaks.py`): The Practical Thinker → The Fact Collector → The Intellectual →
  The Scholar; +1 per consecutive read day, level up at +2, a single missed day is forgiven, two
  in a row cost a level. State is per user in MongoDB and "today" is the server's local date.
- `GET /papers` also tags a paper with `trending_category` when it has at least 2 confirmed
  reads in the past 7 days (one trending paper per category).
- `GET /papers/viewed/graph` - the user's read papers plus similarity edges for the Visualize tab.

**Bookmarks** (auth required)
- `GET /bookmarks` - full paper objects for everything the user has bookmarked.
- `POST /bookmarks` `{video_id}` - bookmark a paper (the field is still named `video_id` on
  disk and over the wire - a holdover from before the app pivoted from videos to papers, kept
  as-is to avoid a data migration).
- `DELETE /bookmarks/{video_id}`

**Interests** (auth required)
- `GET /interests` → `{interests: [...]}`
- `POST /interests` `{interests: [...]}` - replaces the user's chosen topics wholesale.

**Profile** (auth required)
- `GET /profile` → `{tier1, tier2}`
- `GET /profile/options` (no auth) - the answer sets for the Profile Details form: field of study
  (the live paper-category list plus "Other"), education levels, genders, sexes, and the disability
  question and condition checklist. The app builds its dropdowns from this, so nothing is hardcoded
  there.
- `GET /places/autocomplete?q=&limit=` (no auth) - city / region / country suggestions from an
  offline index (`places.py`: `geonamescache` + `pycountry`; no external API). Answers 503 if those
  packages aren't installed (`pip install -r requirements.txt`).
- `PUT /profile/tier1` `{fields}` - cache-safe fields: `field_of_study` (a current category or
  "Other"), `field_of_study_other` (required when "Other"), `education_level`, `general_interests`
  (comma-separated; letters, numbers, spaces and commas only), `location` (must be a place from the
  autocomplete index; `location_region` / `location_country` are derived server-side).
- `PUT /profile/tier2` `{fields, consent}` - sensitive-context fields: `birth_date` (YYYY-MM-DD,
  1920 or later, not in the future), `gender`, `sex`, `disability` (`{conditions, other}`: a subset of the
  checklist from `/profile/options`, which includes "None" - exclusive - and "Other", which requires
  the `other` description), `location_precise`. Each field has its own
  `used_for_personalization`/`used_for_feed_relevance` consent flags. Every Tier 2 read/write is
  appended to a separate audit log. The old `age`, `mental_disabilities`, `physical_disabilities`
  and `chronic_illnesses` fields are retired (no longer writable).
- Both PUTs validate every field (`profile_validation.py`) and answer 400 with
  `{detail, errors: {field: message}}`. Free text is screened for disallowed characters, SQL-style
  phrases, gibberish and profanity (`better-profanity`).
- `GET /admin/field-of-study-report` (admin key) - how many users chose "Other" for field of study
  and which "other" names are common enough to add as a new paper category (thresholds:
  `profile.other_category_threshold_percent`, default 5, and `profile.other_category_min_users`,
  default 10).

Run the backend tests with `pip install -r requirements-dev.txt` then `python -m pytest tests -q`
from `backend/` (they use `mongomock`; no database needed).

## Storage

MongoDB (`db.py`) holds two collections: `papers` and `paper_reviews` (`paper_reviews.py`'s
manual-review queue - a review is a review of a paper, so it's a document type alongside
`papers` rather than another flat JSON file). Accounts, sessions, bookmarks, interests, profile
data, and "viewed full paper" clicks are all flat JSON files instead (`auth.py`, `bookmarks.py`,
`interests.py`, `profile.py`, `paper_views.py`), matching each other's account-scoped pattern.
**These JSON files hold real account data (password hashes, live session tokens) and must never
be committed** - see `.gitignore` and `SECURITY_TODO.md`.

## Configuration

`config.py` merges, in order: hardcoded defaults → `config.json` → environment variables
(including a gitignored `.env`, loaded via `python-dotenv`). See `.env.example` for what to set.

## Not built

Leveled reading (Original/Simpler/Simplest generation and caching), the embedding-based
interest/relevance matching described as future work, screenshot/poster matching, the rating
widget, and age-gating/parental-consent for Tier 2 profile data. A
per-paper chat endpoint (`paper/chat.py`) exists but has no route registered in `api_server.py`
yet, and its frontend counterpart imports a function that doesn't exist in the frontend's API
client - both are dormant, not reachable.
