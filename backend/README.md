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
python cli.py fetch-latest [--category "Physics"] [--days 7] [--limit 20] [--sort-by date|citations]
```

`fetch-latest` with no `--category` fetches all categories in `paper/latest.py`'s `CATEGORIES`
list. Semantic Scholar's anonymous rate limit is low and easy to exhaust across all 8 categories
in one run - set `PAPERBITES_SEMANTIC_SCHOLAR_KEY` in `.env` (free, see `.env.example`) if you
hit repeated rate-limit warnings. If `PAPERBITES_GEMINI_KEY` is set, description summarization
round-robins across several Gemini models (`paper/summarize.py`'s `_MODEL_NAMES`, overridable
via `PAPERBITES_GEMINI_MODELS`) so no single model's free-tier cap gates the whole run - a model
that's rate-limited or invalid is skipped immediately in favor of the next one, with no delay.

## API

All routes are under `/api`. Auth-required routes take `Authorization: Bearer <token>`.

**Papers**
- `GET /papers?category=&limit=&offset=` - the feed, newest first. When authenticated and the
  user has chosen interests, hard-filtered to papers whose categories match (see Interests below).
- `GET /papers/{id}` - a single paper.
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
  above couldn't resolve for manual admin review (`paper_reviews.py`), per the spec's fallback
  for when automated matching fails outright. No admin UI reads this queue yet - it's a flat
  JSON file, read by hand for now.

**Authors & journals**
- `GET /authors/{author_id}` - an author's name and every paper of theirs.
- `GET /journals/{journal_name}` - every paper published in that journal/venue.

**Auth**
- `POST /auth/signup` `{email, password}` → `{token, user}`
- `POST /auth/login` `{email, password}` → `{token, user}`
- `POST /auth/logout` (auth required)
- `GET /auth/me` (auth required) → `{user}`

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
- `PUT /profile/tier1` `{fields}` - cache-safe fields (`field_of_study`, `education_level`,
  `general_interests`, `location`).
- `PUT /profile/tier2` `{fields, consent}` - sensitive-context fields (`age`, `gender`, `sex`,
  `location_precise`, `mental_disabilities`, `physical_disabilities`, `chronic_illnesses`), each
  with its own `used_for_personalization`/`used_for_feed_relevance` consent flags. Every Tier 2
  read/write is appended to a separate audit log.

## Storage

MongoDB (`db.py`) holds the `papers` collection - the only real collection. Accounts, sessions,
bookmarks, interests, profile data, and pending manual-review submissions are all flat JSON files
(`auth.py`, `bookmarks.py`, `interests.py`, `profile.py`, `paper_reviews.py`), matching each
other's pattern rather than adding a second database. **These JSON files hold real account data
(password hashes, live session tokens) and must never be committed** - see `.gitignore` and
`SECURITY_TODO.md`.

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
