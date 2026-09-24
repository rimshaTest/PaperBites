# PaperBites

PaperBites surfaces recent, open-access research papers as a swipeable, TikTok-style card
feed — title, authors, a plain-English description, and a link to the original paper — instead
of a video summary. It started as a video-generation app; that pipeline is now fully removed in
favor of this papers-first design (see `SECURITY_TODO.md` and each package's own README for the
detailed history).

## What's actually built

- **Home feed**: full-screen paging cards (`components/PaperFeed.tsx`) - drag the info panel up
  to expand it and read the full description; paginated with pull-to-refresh.
- **Papers pipeline**: `backend/cli.py fetch-latest` pulls recent open-access papers from
  Semantic Scholar, OpenAlex, and Crossref (with Unpaywall resolving a real open-access link for
  Crossref results), dedupes them, generates a plain-English description (Gemini, when
  configured, else falls back to the paper's cleaned abstract), and stores them in MongoDB.
- **Accounts**: email/password signup/login, session tokens (`backend/auth.py`).
- **Bookmarks**: account-scoped, not device-scoped (`backend/bookmarks.py`).
- **Interests**: pick topics once at signup (or later from Profile > Settings > Manage Feed) and
  the feed hard-filters to matching categories server-side.
- **Author & journal pages**: tap an author or journal name anywhere to see every paper by
  them / in it.
- **Profile data model**: optional, anonymized Tier 1 (cache-safe) and Tier 2 (sensitive-context)
  fields with per-field consent toggles, editable from Profile > Profile Details.
- **Card images**: a Pexels stock photo keyed on the paper's title, not AI/user-generated.
- **Add a paper by citation, URL, or photo**: paste a citation (MLA, APA, or any other style), a
  direct link to the paper's page (e.g. an open-access journal article), or - experimentally -
  photograph a title page/poster or pick a screenshot, from Saved > "+" (`frontend/app/add-paper.js`).
  A citation is fuzzy-matched against Crossref; a URL is scraped for its `citation_*` meta tags to
  find a DOI (or embedded directly in the URL itself), falling back to a bibliographic search on
  the page's title/authors if no DOI turns up anywhere; a photo is read by Gemini vision into a
  citation-like string first (no QR decoding), then resolved the same way. Either way, Unpaywall
  resolves a real open-access link, and confirming runs it through the same enrichment pipeline as
  the discovery feed before saving and auto-bookmarking it (`backend/paper/citation.py`). Its
  category isn't picked by the user - Gemini chooses it from the paper's own text in the same call
  that generates its summary, since (unlike a `fetch-latest` paper) it has no search-query
  category to start from. If nothing matches at all, the user can submit it for manual admin
  review instead (`backend/paper_reviews.py`).

## What's not built yet

Leveled reading (Original/Simpler/Simplest), screenshot/poster matching, the rating widget, and
the age-gating/parental-consent flow for Tier 2 profile data are all still unbuilt. A per-paper
chat screen (`frontend/app/chat/[id].js`) and its backend (`backend/paper/chat.py`) exist but
aren't wired into navigation or the API routes yet.

## Project structure

```
PaperBites/
├── backend/    # Python (Starlette) API + paper-fetching pipeline - see backend/README.md
└── frontend/   # React Native (Expo) app - see frontend/README.md
```

## Quick start

```bash
# Backend
cd backend
pip install -r requirements.txt
cp .env.example .env   # fill in your Mongo connection string, Pexels key, etc.
python api_server.py   # serves the API on :8000
python cli.py fetch-latest --days 14 --limit 20   # populate MongoDB with real papers

# Frontend (separate terminal)
cd frontend
npm install
npm start               # then open in Expo Go, a simulator, or a browser
```

See `backend/README.md` and `frontend/README.md` for full setup details, including how the
frontend reaches a backend that isn't `localhost` (a physical device, or a network with client
isolation).

## Security

`SECURITY_TODO.md` tracks credentials and account data that have been committed to this repo's
git history and need rotation. Read it before deploying this anywhere real.
