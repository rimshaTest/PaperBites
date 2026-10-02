# PaperBites — Product Spec

2026-09-18 · @Someone · updated 2026-10-02 to reflect what's built

## Vision & People Outcome

People problem, stated plainly: "I hear about interesting research but can't get through the actual paper, and I don't trust the dumbed-down version someone else made of it."

Target user (v1): college students in intro-to-major courses who get handed a citation or paper and need to actually understand it, not just skim an abstract.

Success, if this is wildly successful: people routinely turn a citation or a photo of a paper/poster into something they can read, do so at a level that fits them, and come back to save a second paper within a week — not just "downloaded once."

## Build Status (as of 2026-10-02)

**Shipped**: accounts (signup, login, password reset); the discovery feed (swipe-up cards on phones, side-by-side image + details on wide screens); semantic search; add-a-paper by citation, link, or photo, with a confirm step and a manual-review fallback; bookmarks and the Saved tab; interests (hard filter on the feed); author and journal pages; tiered profile fields with per-field consent toggles; likes; confirmed reads, milestone badges, reading streaks and achievement pop-ups; a "Trending" badge; the Visualize bubble map; light/dark theme; a one-time logo intro video.

**Not built yet**: the Original / Simpler / Simplest reading-level toggle (the feed currently shows the original abstract with a plain-English description alongside), QR-code decoding for photos, the rating widget, comments and moderation, the parental-consent flow for minors, and the Home "subscriptions" tab and Notifications tab described in the technical spec.

The rest of this page mixes shipped behavior and planned behavior; use this list to tell which is which.

## MVP Scope & Phasing

1. **Phase 1 — core utility, with experimental personalization from day one.** Add-a-paper via citation paste or screenshot/poster scan → confirm dialog → saved card with Original, Simpler, and Simplest. Optional profile collection ships now too, powering Simplest — both the profile's use for personalization and the Simplest tier itself are labeled Experimental. An automated ingestion job pulls recent open-access papers on a schedule into a non-personalized "Recent" feed, so there's real content flowing from day one. Saved tab, bookmarks, and the rating widget ship alongside.
2. **Phase 2 — community & discovery.** Comments (tagged by reading level), moderation tooling, and the feed becomes interest-matched using the profile data already collected since Phase 1. Sequenced here because interest-matching needs a real paper topic-tagging pipeline and enough usage volume to feel good rather than sparse — not because the profile data doesn't exist yet.
3. **Phase 3 — experimental, deferred indefinitely.** Video generation / TikTok-style feed. Not competitive to build solo right now, and risks pulling focus from the core reading product.

## Reading-Level Toggle: Original / Simpler / Simplest

| Level | Feels like | Why |
| --- | --- | --- |
| Original | Instant | Extracted text, no generation needed |
| Simpler | Instant after first reader ever | Generated once per paper in the background at ingestion; shared by everyone |
| Simplest | Brief wait on first request per profile cluster, instant after | Personalized with analogies; generated lazily, then cached for that cluster |

If a user taps Simplest before their cluster's cache is warm, show a short "preparing your version" state rather than a spinner with no context — sets the right expectation instead of feeling broken. If a profile isn't filled out, Simplest falls back to a generic default rather than being blocked.

After a Simpler or Simplest version finishes generating, a small corner prompt asks two quick questions: was it comprehensible, and did it seem accurate — each rated Good / OK / Bad. Anyone can rate comprehension; for accuracy, raters are first asked "are you familiar with this field?" and that answer weights their rating rather than gatekeeping who can respond. Both Simpler and Simplest are labeled **Experimental** while this feedback loop is still validating quality; the label comes off once ratings and spot-checks show they're reliable.

## User Profile & Personalization

All fields optional, collected starting in Phase 1. Every field is entered through a constrained control and validated, so the data is clean enough to use:

- **Field of study**: a dropdown of the paper categories we currently pull, always in step with the live category list, plus **Other** with a free-text box. If "Other" answers for the same field reach a meaningful share of users (default: at least 5% of users who set a field of study, and at least 10 users), that field becomes a candidate new category to pull papers for. An admin report lists the common "other" names.
- **Education level**: High school, Undergraduate, Graduate, Post-doctoral, Professional / self-directed.
- **General interests**: free text, comma-separated, letters and numbers only (max 10), screened for SQL-style phrases, gibberish and profanity.
- **Location**: autocomplete over cities, states/regions and countries; the user must pick a suggestion, and doesn't need to give every part.
- **Date of birth**: month / day / year dropdowns, from 1920.
- **Gender, sex**: the standard voluntary self-identification options used on job applications, each with "prefer not to say".
- **Disability**: one combined checklist of conditions, as on the standard form (mental, physical and chronic conditions together), plus **None** (exclusive) and **Other** (with a short description). Leaving it blank means not answered.

Profile-driven personalization is labeled Experimental alongside Simplest itself.

**Consent**: opted into per sensitive category, not bundled into one blanket signup form. Plain-language purpose statement (e.g. "used only to tailor analogies to your background; pseudonymized, never shown to other users or used for ads").

**Use**: field of study, education level, and broad interests drive the shared Simplest cache cluster (see technical doc). Disability, illness, demographic, and precise-location fields are used only as per-request context for that individual's own Simplest generation — never shared or cached across users.

**Sensitive-field consent is split in two**: "use this to personalize my Simplest explanations" and "use this to personalize what's shown in my feed" are separate opt-ins, even though they may draw on the same field (e.g. a chronic illness). Feed relevance is a more exposed use of that data — visible content someone glancing at your phone could see — so it needs its own explicit consent, not one inherited from the analogy-generation opt-in.

## Adding Papers

Two entry points into one "Add a Paper" flow:

1. **Paste a citation** (APA/MLA/etc.) → match against Crossref/OpenAlex/Semantic Scholar → confirm dialog with candidate match(es) → user confirms → ingested.
2. **Screenshot or photo** of a paper or poster → check for a QR code first (many posters link straight to the paper) → fall back to extracting title/authors → same matching + confirm dialog.

Always confirm before saving — never auto-save on a guess. This matters more for posters specifically: they're more likely to represent unpublished or in-progress work with no clean DOI match, so "no confident match found" needs to be a designed, first-class outcome, not an error state.

When a screenshot/photo match fails, list the likely reasons (glare, blur, no visible title, unreadable QR code, no confident bibliographic match) so the user can retry with a better photo. If it still fails, let them submit the image plus any info they have for manual admin review — early on, this is just you reviewing a short queue, and each case doubles as a data point for improving the matcher.

## Comments & Discourse

Attach to the paper as a whole, not per reading-level — otherwise a single paper's discussion fragments into three separate silos. Reading level is a personal display toggle; the comment thread is shared.

Each comment carries a small tag showing which level its author read (Original / Simpler / Simplest) — visible context for why a reply might suddenly use jargon, and a natural, low-effort way for people to pick up field-specific language from those who already know it.

Because the profile may include sensitive health/disability data, moderation needs to explicitly guard against that becoming a harassment vector. Given the likely audience (e.g. people discussing chronic-illness research), reporting/moderation tooling should ship before public launch, not be added after something goes wrong.

## Interest-Based Discovery Feed

An automated job pulls recent open-access papers on a schedule from day one (Phase 1), feeding a non-personalized "Recent" feed. Interest-matched ranking — weighting papers by topic against a user's interests, including relevant health/condition mentions in the paper text where a user has opted their health data into feed personalization — lands in Phase 2, once there's a real topic-tagging pipeline and enough volume for "matched" to feel meaningfully different from "recent."

Cold start: new users with no saved papers and no filled profile need a fallback — an editorial/curated default set or a trending-within-app list, rather than an empty or random feed.

## Reading Engagement: Likes, Confirmed Reads, Milestones & Streaks

These reward real reading rather than scrolling, and they are all per account, so they match across a user's devices.

- **Likes**: a heart on every paper card, separate from saving. A user can like a paper without opening it. Cards show a like count.
- **Confirmed read**: a read only counts after the user opens the original paper and then confirms it ("Have you read this?"), or confirms directly from the card. Each paper counts once per user.
- **Milestone badges**: earned at 1, 10, 25, 50, 100 and 200 confirmed reads, shown on Profile. Reaching one triggers a celebratory pop-up.
- **Reading streak badge**: a level shown on Profile — The Practical Thinker → The Fact Collector → The Intellectual → The Scholar. Everyone starts as The Practical Thinker. Reading on 2 consecutive days earns a level. One day off is forgiven; two days in a row with no read costs a level.
- **Favorite topics**: Profile lists the categories the user has read most.
- **Trending badge**: a paper shows "Trending in <category>" when at least 2 people confirmed reading it in the past 7 days. There is one trending paper per category, the most-read.

## Visualize

A map of the papers the user has read, shown as bubbles on a pannable canvas. Closeness reflects how similar the papers' content is, not just shared tags. Solid lines link papers with similar content, dashed lines link papers sharing a category, thicker lines mean a stronger link, and bigger bubbles mean more links. Bubble color shows a paper's first category. A collapsible legend explains all of this. Bubbles can be dragged, and tapping one opens the paper. It stays empty until the user has read a few papers.

## Navigation & Layout

Bottom tab bar, left to right: **Explore** (the feed), **Visualize**, a raised **+** button (add a paper), **Saved**, **Profile**. Interests are managed from Settings (and offered once after signup). The planned Home (subscriptions) and Notifications tabs are described in the technical spec and are not built.

The app is responsive. Below 900px wide (phones, narrow windows) the feed uses swipe-up cards and lists are a single column. At 900px and wider (laptops, tablets in landscape) the feed shows the image on the left and details on the right, Saved shows two columns, and screens use the full window width. The logo intro plays a portrait video on tall screens and a landscape video on wide ones, stretched to fill the screen.

Light and dark themes follow the device setting, and the user can pin one in Settings.

## Saved Papers & Feed Interactions

Every paper card carries a bookmark/save control, independent of how it entered the app (added directly, or encountered in the discovery feed). Saved papers live in their own **Saved** tab — a personal library distinct from the discovery feed, since browsing shouldn't require keeping everything seen.

Pulling down on the discovery feed refetches new papers (standard pull-to-refresh) — an explicit way to force fresh content rather than waiting on the feed's normal caching/pagination.

## Privacy & Trust Commitments

Terms should say "pseudonymized," not "anonymized" — more accurate given the granularity of retained profile data (see technical doc, Identifiers). Commitments to state plainly:

- Sensitive fields (disabilities, illness, demographics) are optional and separately consented, never bundled into required signup.
- Never sold or shared with third parties.
- Minimized at the point of use — only sent to a generation call when relevant, not attached wholesale to every request.
- Never used as a shared cache/cluster key across users (see technical doc, Caching).
- Consent for sensitive fields is split by use: personalizing Simplest explanations vs. surfacing matched content in the feed are separate opt-ins, since the feed use is more exposed.

## Success Metrics by Stage

**PMF stage**: for now, track raw activity — total users, plus new comments and saves per week — as the headline signal. Once there's enough weekly volume to compute it meaningfully, add a retention cut (e.g. % of savers who save again within a week) alongside it, since activity alone can be moved by growth tactics without indicating the product is actually sticky.

**Growth stage**: expansion to new segments (e.g. high schoolers, patients researching a diagnosis) and depth of engagement — return visits, and how often people go past Simpler into Simplest.

## Scope Decisions & Notes

- **Age policy**: minors can sign up with a full profile, including sensitive fields. This requires a parental-consent flow for sensitive data collection before launch (COPPA-equivalent) — a required v1 build item, not a footnote.
- **Business model**: Original + Simpler free for everyone; Simplest capped at a fixed number of generations per month for free users, loosened later once real usage/cost patterns are understood.
- **Copyright/licensing**: license checked at ingestion via Crossref/OpenAlex metadata. Permissive licenses (e.g. CC-BY) cache Original in full; restrictive ones cache only an excerpt plus a link to the source.
- **Content trust**: a "flag this" control ships on every Simpler/Simplest card at v1. Periodic manual spot-checks against the original abstract stand in for full automated fact-checking until volume justifies building that.
- **Internationalization**: not built for at v1, but profile fields and summary text are kept as free-standing strings so it isn't a rewrite later.
- **Accessibility**: held to a real WCAG/screen-reader bar, given the disability data the app collects.
