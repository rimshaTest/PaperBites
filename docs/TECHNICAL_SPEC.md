# PaperBites — Technical Spec

2026-09-18 · @Someone · updated 2026-10-02 to reflect what's built

## Architecture Overview

Three-part pipeline:

1. **Ingestion** — citation parse or screenshot OCR/QR → bibliographic match via Crossref/OpenAlex/Semantic Scholar → Unpaywall for open-access full text.
2. **Storage** — paper record plus three content tiers (Original / Simpler / Simplest), cached at different granularities (below).
3. **Generation** — background job for Simpler at ingestion time; lazy, per-cluster job for Simplest on first request.

Profile data is split into two tiers (cache-safe vs. sensitive-context) that feed the generation and caching layers differently — detailed below.

## Reading-Level Generation: Triggers & Timing

| Level | Trigger | Model | Cache key |
| --- | --- | --- | --- |
| Original | At ingestion, synchronous | None (extraction/cleanup only) | `paper_id` |
| Simpler | At ingestion, background job, non-blocking | Cheap/fast — mechanical rewrite, no personalization reasoning | `paper_id` |
| Simplest | Lazily, on first request | Strongest available — must reason about relevant analogies | `paper_id + profile_signature` |

Original renders immediately so the paper feels like it "loaded instantly." Simpler is generated once per paper and reused by every future reader forever — eager generation is cheap because it pays off at ingestion time and benefits everyone downstream. Simplest can't be pre-generated (you don't know which clusters will ever request a given paper), so it stays lazy: first request per signature triggers generation, cache hit for everyone else sharing that signature after.

## Caching Strategy

`profile_signature` is built ONLY from cache-safe attributes (field of study, education level, broad interests, coarse location). Sensitive attributes never enter the cache key — they're used as ephemeral per-request context only, cached per-account at most, never shared across users (see Identity section for why: rare sensitive combinations shrink a cluster to size 1, which defeats caching and creates a re-identification risk).

**Invalidation**: if a paper's Original text is corrected or re-ingested, invalidate Simpler and all Simplest cache entries for that `paper_id`. If a user edits their cache-safe profile fields (e.g. changes major), their signature simply changes going forward — old cache entries just age out, no explicit invalidation needed.

## Profile Data Model

Two-tier split:

- **Tier 1 (cache-safe)**: field of study, education level, broad interests, coarse location (country/region). Drives `profile_signature` for shared Simplest caching.
- **Tier 2 (sensitive-context)**: birth date, gender, sex, precise location, and one combined disability field (`{status, conditions[]}`, using the voluntary self-ID wording of US job applications; replaces the old age, mental/physical disability and chronic-illness fields). Stored in a separate, more access-restricted table with its own audit trail. Used only as per-request generation context — never a cache key, never logged alongside full prompt/response pairs longer than needed for the request itself.

All fields optional; consent is opted into per category rather than one bundled form (see product doc).

**Validation and option lists.** The server is authoritative (`profile_validation.py`); the app mirrors the rules for instant feedback (`frontend/utils/profileValidation.js`). Answer sets come from `GET /api/profile/options` and are not hardcoded in the app; field of study is `categories.current_categories()` plus "Other", the same list the paper fetcher uses, so a new category appears in the form automatically. Free text uses a character whitelist (the real injection protection), plus a defense-in-depth SQL-phrase pattern, conservative gibberish heuristics (acronyms like CRISPR and fMRI pass) and profanity screening (`better-profanity`). Storage uses the MongoDB driver (not SQL). Failed saves return 400 `{detail, errors: {field: message}}`.

**Location** is validated against an offline index (`places.py`, built from `geonamescache` + `pycountry`; no third-party API at runtime). The server stores the resolved label and derives `location_region` / `location_country` itself. Because a city is finer than the "coarse location" Tier 1 is meant to hold, `profile_signature` should use `location_country` (optionally `location_region`) only, never the city. Non-US cities show as "City, Country"; the index does not carry non-US state names for cities.

**"Other" field of study.** `field_of_study = "Other"` requires `field_of_study_other` (letters and spaces). `GET /api/admin/field-of-study-report` (admin key) groups the "other" names case-insensitively and suggests any that are at least `profile.other_category_threshold_percent` (default 5) of users with a field of study and at least `profile.other_category_min_users` (default 10) users. Near-synonyms are counted separately and merged by hand.

**Consent is tracked per use, not per field**: each Tier 2 field carries two independent flags — `used_for_personalization` (Simplest analogy generation) and `used_for_feed_relevance` (surfacing matched content in the discovery feed). A user can enable one without the other.

## Identifiers & Pseudonymization

Do NOT derive an analytics/clustering ID from a hash of `user_id + account_creation_timestamp`. A deterministic hash is brute-forceable in practice if the input space is guessable (sequential or known user\_ids, narrow timestamp windows) — anyone with the hash function can hash every plausible pair and match it back. That's pseudonymization at best, and a weak one.

**Recommended**: generate a random opaque ID (UUIDv4 or 128-bit token) at account creation, stored as the join key for `profile_signature` and analytics — not derived from anything reversible. If deterministic re-derivation is genuinely needed, use HMAC with a server-side-only secret instead of a bare hash.

**Terms-of-service language** should say "pseudonymized" or "de-identified where feasible," not "anonymized." True anonymization is hard to guarantee once rare attribute combinations are retained (e.g. a specific chronic illness + narrow location + age can still be re-identifying — a k-anonymity concern independent of what the ID itself is called).

## Add-Paper Ingestion Pipeline

**Citation paste**: parse via a citation-parsing library (e.g. anystyle) or send the raw string directly to a bibliographic search API's fuzzy search (Crossref/OpenAlex/Semantic Scholar) — raw-string search may prove reliable enough to skip strict parsing, which is more robust than regex-based APA/MLA parsing.

**Screenshot/poster**:

1. Attempt QR code decode first — many posters link directly to a DOI or preprint, near-100% confidence when present.
2. Fall back to vision-model extraction of title/authors — more robust than OCR + heuristics for messy poster layouts.
3. Same bibliographic search + confirm dialog as the citation path.

Both paths converge on one confirm-dialog step before saving, showing the top 1-3 candidate matches. Once a DOI is known, check Unpaywall for an open-access full-text link.

When a screenshot/citation match fails, surface the specific reason (glare, blur, no visible title, unreadable QR, no confident bibliographic match) rather than a generic error, and let the user submit the image/citation for manual admin review if retries don't resolve it. Early on this is a short queue reviewed by hand; each reviewed case doubles as a data point for improving the matcher over time.

## Discovery & Relevance Matching

**Ingestion feed**: a scheduled job pulls recent open-access papers (via the same Crossref/OpenAlex/Unpaywall pipeline used for citation lookups) into a "Recent" feed from Phase 1 — unpersonalized, chronological/volume-based.

**Interest-matched ranking (Phase 2)**: embed each paper's topic and match against a user's cache-safe interests. Health/condition relevance uses cheap keyword/entity matching against the paper's text (e.g. disease name mentions) rather than embeddings. This only runs for a user who has opted their health data into feed personalization specifically — a separate consent from using the same field for Simplest analogy generation (see Profile Data Model).

## Feedback, Bookmarks & Feed Refresh

**Rating widget**: `ratings(user_id, paper_id, level [simpler|simplest], comprehensible [good|ok|bad], accurate [good|ok|bad], rater_familiar_with_field [bool], created_at)`. Surfaced as a corner prompt right after a Simpler/Simplest generation finishes. `rater_familiar_with_field` weights the accuracy signal rather than gatekeeping who can answer it — self-reported field-familiarity is a cheap proxy for domain expertise without needing to verify credentials or reach out to authors. This is the live version of the Eval plan check below — aggregate, familiarity-weighted ratings per paper/level become the ongoing quality signal instead of relying only on manual spot-checks.

**Experimental labeling**: served from a small config (e.g. `level_status: {simpler: "experimental", simplest: "experimental"}`) rather than hardcoded, so it can be turned off per level once ratings clear a bar — no app release needed.

**Bookmarks**: `bookmarks(user_id, paper_id, saved_at)`. Saved tab is a straight query by `user_id`, ordered by `saved_at desc`, independent of the papers table used for the discovery feed.

**Feed pull-to-refresh**: client discards its current feed cursor/cache and requests page 1 fresh from the discovery endpoint. No special server-side handling beyond normal pagination — it's the same request a cold feed load makes.

## Infra & Cost Controls

- **Model tiering**: cheap/fast model for Simpler (mechanical rewrite); best available model reserved for Simplest (personalized reasoning) and for vision-based poster/citation extraction (worth the cost — it's occasional and user-initiated, not run at scale per view).
- **Rate limiting**: cap Simplest generations per user per time window once public — it's the most expensive on-demand path, and needs protection against cost abuse via repeated profile changes to force cache misses.
- **Background jobs**: Simpler generation and OCR/matching run async, off the request path — never block the ingestion confirm-dialog response on them.

## Security & Compliance

Sensitive profile data (Tier 2) requires:

- Explicit opt-in consent per category.
- Data minimization at the prompt layer — send only what's needed for that specific generation call, not the full profile object.
- Storage separation with restricted access and an audit trail.
- A clear deletion path: deleting a sensitive field should also purge any residual per-user cached Simplest content derived from it.

Given GDPR-style special-category data is involved, plan for a documented lawful basis (consent) and a retention/deletion policy before public launch, not after.

## Navigation (5-tab bar)

**Built.** Bottom tabs, in order: Explore (`app/(tabs)/index.js` → `PaperFeed`), Visualize, a raised center **+** (`AddPaperTabButton`, opens `app/add.js`/the add-paper flow), Saved, Profile. Interests is a hidden tab route (`href: null`) reached from Settings. On iOS the tab bar floats over content (`position: absolute`), so screens add bottom padding from `useBottomTabBarHeight()`; on Android/web it is in normal layout flow.

**Not built (planned):**

- **Home (subscriptions)**. No "subscribe" concept exists: `author/[id].js` and `journal/[name].js` only list papers. Needs `subscriptions(user_id, target_type [author|journal], target_id, subscribed_at)` (same account-scoped pattern as `bookmarks.py`) and a Subscribe/Following toggle on both pages. **Open product decision**: does a Home card represent one subscribed *source* (a directory of who you follow) or one *new paper* from a subscription (a feed)? The source-directory reading is the default until confirmed; the feed reading needs a per-user "new since last visit" query across every subscription.
- **Notifications**. Needs a comments system first (`comments(id, paper_id, user_id, text, parent_comment_id, created_at)` plus create/list/reply routes), then `notifications(user_id, type [comment|reply|trending], payload, created_at, read_at)` and an unread badge. Notify on comments on saved papers, replies to the user's comments, and a weekly trending digest. The digest needs a scheduler (none exists; `cli.py` is run by hand) and a cross-user engagement aggregate over `paper_views`.
- **Explore search/filter/sort**. Search is a modal reached from the feed header's icon (`app/search.js`, `GET /api/papers/search`). A filter/sort popup (category, open access, sort by citations) is not built; `get_latest_papers` supports `sort_by=citations` but `GET /api/papers` does not expose it.

## Reading Engagement Backend (likes, reads, milestones, streaks, trending)

All state is per user in MongoDB, so every device sees the same values.

| Concern | Module | Notes |
| --- | --- | --- |
| Likes | `paper_likes.py` | One doc per (user, paper). `POST/DELETE /api/papers/{id}/like`. `GET /api/papers/{id}` needs the auth token to return whether the caller liked it, so the client must send it. |
| Confirmed reads | `paper_views.py` | `POST /api/papers/{id}/view`. Counted once per user per paper. |
| Milestones | `paper_views.MILESTONES` = 1, 10, 25, 50, 100, 200 | Mirrored in `frontend/constants/milestones.js`; keep the two in sync. |
| Streaks | `streaks.py` | Collection `streaks`, keyed by user id: `level`, `buffer`, `last_read_date`. +1 buffer per consecutive read day, level up at +2; −1 per fully missed day, level down at −2. `get_streak` applies decay for missed days when read, so the badge reflects today. "Today" is the **server's local date**. |
| Stats | `GET /api/stats/reading` | `total_read`, `by_category`, `milestones_reached`, `streak {level, label}`. |
| Trending | `api_server._trending_category_by_paper_id` | A paper is trending if it has ≥ 2 confirmed reads in the last 7 days; one per category (most read). |

The client never computes streaks or milestones itself; Profile renders the stats response. If two devices disagree, they are talking to different backends or databases (see Frontend Configuration), not computing differently.

## Visualize Graph

`GET /api/papers/viewed/graph` returns `{nodes, edges}` for papers the user has confirmed reading; edges come from cosine similarity of stored embeddings (`paper/embeddings.py`), computed server-side — raw embeddings never reach the client. The client (`visualizations.js`) adds weaker edges for shared categories (dashed), runs a live d3-force simulation (spring links, collision, repulsion), and renders with `react-native-svg`. Bubble color comes from a fixed palette hashed on the paper's first category. The legend lists the categories present. The canvas size is computed once at load from the window size (known gap: it does not resize with the window).

## Frontend Theming & Responsive Layout

- **Theme**: `constants/theme.js` defines `lightTheme` and `darkTheme` with the same tokens: `background`, `surface`, `text`, `textMuted`, `border`, `accent`, `danger`, plus `like`, `streak`, `onAccent`, and `serif`. Components read colors through `useTheme()` (follows the OS, overridable and persisted). Do not hardcode hex values in components; add a token instead. `constants/Colors.ts` was removed, and the Expo-template helpers (`useThemeColor`, `ThemedText`, `Collapsible`) now read from the same theme.
- **Responsive**: layout reads the live window size with `useWindowDimensions()`, never `Dimensions.get` at module load. Breakpoint **900px**. The feed card (`PaperFeed.tsx`) switches from a draggable bottom sheet to image-left / details-right. Saved switches to two columns. The feed header's content row spans the full width. Overlay controls are positioned from the **measured** header height (`onLayout`), because the header height differs by platform; `FlatList` gets `extraData` so cards re-render when it changes. Tab screens use `SafeAreaView edges={['top']}` only, since the tab bar already accounts for the bottom inset, and their scroll areas carry their own bottom padding so content clears the raised center button.
- **Intro video**: `components/IntroVideo.js` picks `splash-video.mp4` (portrait) or `splash-video-landscape.mp4` (landscape) from the window shape at start, sizes the player to the window with `contentFit="fill"`, skips the portrait-only poster on wide screens, and finishes on end, error (logged), or after a 6s safety timeout.

## Frontend Configuration & Known Issues

- **Backend URL** (`services/api.js`): `EXPO_PUBLIC_API_URL` if set, else `http://localhost:8000/api` on web, else a hardcoded Cloudflare quick-tunnel URL (changes every restart) or LAN IP on devices. A phone and a laptop can therefore reach **different backends**; prefer setting `EXPO_PUBLIC_API_URL` on both.
- **Secrets in the repo**: `backend/config.json` contains a MongoDB connection string with credentials. Rotate it and supply `PAPERBITES_MONGODB_URI` through the environment (the config loader already supports this). See `SECURITY_TODO.md`.
- **Streak mismatch across devices** has been seen once (phone showed level 0, laptop level 1). Streak state is server-side and keyed by user id, so the likely cause is two backends, not a client bug; unconfirmed.
- **Android text sizing**: chips sized to their text can clip on devices with a bold-text accessibility setting; the Interests chips use a trailing buffer to absorb it.

## Build Notes & Decisions

- **Licensing**: ingestion checks each paper's license via Crossref/OpenAlex metadata. Permissive licenses (e.g. CC-BY) cache Original in full; restrictive ones cache only an excerpt plus a link to the source, with generation done from a fetch-on-demand copy rather than a stored full text.
- **Quality control**: a per-summary "flag this" action ships at v1. Periodic manual spot-checks stand in for automated fact-checking until volume justifies investing in that.
- **Zero-confidence match**: explicit empty state ("couldn't confidently match — try a clearer photo, or enter title/DOI manually"), treated as a normal outcome, not an error.
- **Age-gating**: minors are allowed to sign up with a full profile, including sensitive fields — this requires a parental-consent flow before collecting Tier 2 (sensitive) data from minor accounts, per COPPA-equivalent requirements. Required v1 build item, not deferred.
- **Eval plan**: the rating widget (comprehension + accuracy, familiarity-weighted) is now the primary ongoing quality signal — supplement it early on by manually testing the same paper across 3-4 different profile signatures to confirm the analogies meaningfully diverge and stay accurate, before scaling personalization further.
