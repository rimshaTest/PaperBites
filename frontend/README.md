# PaperBites Frontend

A React Native (Expo Router) app for the PaperBites paper feed. There's no video *content*
feed anymore - the original TikTok-style video feed over generated summaries was fully removed
in favor of a swipeable card feed over real research papers. The only video left is a one-time
logo intro played on cold app start (`components/IntroVideo.js`).

## File structure

```
frontend/
├── app/                          # Screens (Expo Router - file-based routing)
│   ├── (tabs)/
│   │   ├── index.js              # Explore tab - renders PaperFeed
│   │   ├── visualizations.js     # Visualize tab - the paper-relationship bubble map
│   │   ├── add.js                # Center "+" tab - add a paper
│   │   ├── saved.js              # Saved tab (two columns on wide screens)
│   │   ├── profile.js            # Profile tab - stats, milestones, streak badge
│   │   └── interests.tsx         # Interests editor (not a tab itself - reachable from
│   │                              # Profile > Settings > Manage Feed)
│   ├── author/[id].js            # Every paper by one author
│   ├── journal/[name].js         # Every paper in one journal
│   ├── paper/[id].js             # Paper detail screen - "View Original Paper" here also
│   │                              # records the click for the Visualize tab's bubble map
│   ├── chat/[id].js              # Per-paper chat - NOT wired in, see "Known gaps" below
│   ├── login.js / signup.js      # Auth screens
│   ├── add-paper.js              # Add-a-paper modal, reached from the center "+" tab - citation, URL,
│   │                              # or (experimental) a camera/screenshot photo
│   ├── search.js                 # Semantic paper search modal, reached from the feed's search icon
│   ├── interests-onboarding.js   # One-time modal shown right after signup
│   ├── profile-details.js        # Tier 1/2 profile fields with per-field consent toggles
│   ├── settings.js               # Settings > Manage Feed > Interests
│   └── _layout.tsx               # Root Stack + AuthProvider + GestureHandlerRootView + the
│                                   # one-time IntroVideo overlay
├── components/
│   ├── PaperFeed.tsx             # The actual Home feed: full-screen paging cards, drag the
│   │                              # info panel up to expand and read the full description;
│   │                              # plays a whoosh sound on each page-to-page swipe
│   ├── PaperCard.js              # List-row card, used by the Saved tab and Search; fills its
│   │                              # parent's width (no fixed width)
│   ├── AchievementOverlay.js     # Celebration pop-up on milestone / streak-level events
│   └── IntroVideo.js             # Full-screen logo intro, played once on cold app start. Plays
│                                   # splash-video.mp4 on portrait screens and
│                                   # splash-video-landscape.mp4 on landscape ones, stretched to fill
├── hooks/
│   ├── useAuth.js                # Session context (signup/login/logout, persisted + re-
│   │                              # validated against the backend on mount)
│   ├── useTheme.js               # Light/dark theme (follows the OS, pinnable in Settings)
│   ├── useLike.js / useConfirmRead.js / useAchievements.js  # likes, confirmed reads, pop-ups
│   └── useStorage.js             # useFavoritePapers (account-scoped bookmarks) - also plays
│                                   # the bookmark confirm "ding" (assets/sounds/bookmark-ding.wav)
├── constants/
│   ├── theme.js                  # lightTheme / darkTheme color tokens - the single source of
│   │                              # colors; no hardcoded hex values in components
│   └── milestones.js             # Mirrors backend MILESTONES (1, 10, 25, 50, 100, 200)
├── assets/
│   ├── splash-video.mp4          # Portrait logo intro (IntroVideo.js)
│   ├── splash-video-landscape.mp4 # Landscape logo intro
│   ├── splash-static.png         # Poster frame shown while the video loads
│   └── sounds/
│       ├── bookmark-ding.wav     # Played once per bookmark add (not remove)
│       └── swipe-whoosh.wav      # Played on each Home feed page-to-page swipe
└── services/
    ├── api.js                    # REST client for every /api/* endpoint
    ├── auth.js                   # signup/login/logout/getMe
    └── storage.js                # AsyncStorage: auth session persistence, plus a few
                                    # device-local helpers (getInterests, isPaperSaved, etc.)
                                    # that are currently dead code - nothing imports them since
                                    # bookmarks/interests moved to the account-based backend
```

## Setup

```bash
npm install
npm start
```

Then open in Expo Go, an iOS/Android simulator, or a browser.

## Connecting to a backend

`services/api.js` picks a base URL in this order:
1. `EXPO_PUBLIC_API_URL` (set in a `.env` file, e.g. `EXPO_PUBLIC_API_URL=http://192.168.1.5:8000`
   - no trailing `/api`). This is the recommended way to point at your backend without editing
   code. Restart `expo start` after changing `.env` - it's only read at startup.
2. `http://localhost:8000/api` on web.
3. A hardcoded `TUNNEL_URL` (a Cloudflare quick tunnel) or `COMPUTER_IP` (your LAN IP) in
   `services/api.js`, for a physical device that can't reach `localhost`. Quick tunnel URLs are
   random and expire every time `cloudflared` restarts - update `TUNNEL_URL` (or better, use
   `.env` instead so you're not editing code each time) when it changes.

## Screens

- **Explore** (the feed): `PaperFeed` - under 900px wide, swipe vertically between papers and
  drag a card's info panel up to expand it; at 900px and wider the image sits on the left and the
  details in a scrolling panel on the right. Pull to refresh; paginates automatically; like,
  bookmark and share buttons sit over the image, and a "Trending" badge marks papers several
  people read this week. The search icon next to the "PaperBites" title opens **Search** (`search.js`): free-text semantic
  search over papers, ranked by meaning (Gemini embeddings) rather than exact keyword match.
- **Visualize**: a pannable bubble map (`visualizations.js`, `react-native-svg` + `d3-force`) of
  every paper you've clicked "View Original Paper" for on the paper detail screen - connected to
  each other by cosine similarity of their stored embeddings (backend's `paper/embeddings.py`),
  not by shared category tags. Two economics papers you've read cluster together; a paper that
  spans economics and biology bridges both clusters. Bubbles run a live physics simulation
  (d3-force: springs, collisions) that you can drag individually; drag the background to pan, tap
  a bubble to open the paper. Solid lines = similar content, dashed = shared category; bubble
  color = first category. A collapsible legend explains this. Empty until you've confirmed
  reading a few papers.
- **Profile**: the signed-in account, reading streak badge, papers-read count, milestone
  badges, favorite topics, and links to Profile Details and Settings - or a login/signup prompt
  when signed out. Streak and stats come from the server per account, so they match across
  devices pointed at the same backend.
- **Saved**: bookmarked papers, account-scoped (requires login); a tab again. The center "+"
  tab opens **Add a Paper**: paste a citation (MLA, APA, or any
  other style) or a link to the paper's page, tap the right match, and it's saved and
  auto-bookmarked - Gemini picks the category itself from the paper's text, same as it does for
  the paper's summary. If nothing matches, "Submit for manual review" queues it for a human to
  look at instead. The camera button next to the input (marked with a star - tap or hover it for
  an "Experimental feature" note) lets you photograph a title page/poster or pick an existing
  screenshot instead of typing; Gemini vision reads a citation off it server-side and searches
  with that.
- **Profile Details**: every field is optional and validated as you go (the server re-validates).
  Tier 1: field of study (dropdown of the current paper categories, fetched from the server, plus
  "Other" with a free-text box), education level (dropdown), general interests (comma-separated,
  letters and numbers only), and location (autocomplete over cities, regions and countries - you
  must pick a suggestion). Tier 2: date of birth (month / day / year dropdowns from 1920), gender,
  sex, and one combined disability checklist (conditions plus "None" and "Other") - each with its own
  "Personalize my feed with this" switch. Dropdowns use `components/Select.js` and the location box
  `components/PlaceAutocomplete.js`; client-side rules live in `utils/profileValidation.js`.
- **Settings > Manage Feed > Interests**: pick topics to hard-filter the Home feed to. Also
  shown once as a modal popup right after signup (Skip for now / Continue).
- **Author / Journal pages**: reached by tapping an author or journal name anywhere in the app.
- **Paper detail**: full description, DOI, categories, and a link to the original paper.

## Layout & theming conventions

- Read the window size with `useWindowDimensions()`, never `Dimensions.get` at module load, so
  layouts follow browser resizes and rotation. The wide-screen breakpoint is 900px.
- Read colors from `useTheme()`; add a token to `constants/theme.js` instead of hardcoding hex.
- Tab screens use `SafeAreaView edges={['top']}` and put bottom padding inside their scroll
  area so content clears the raised center button (and, on iOS, the floating tab bar).

## Known gaps

- The Visualize canvas size is computed once at load, so it doesn't resize with the window.

- `app/chat/[id].js` exists but isn't registered in `app/_layout.tsx`'s Stack, so it's
  unreachable - and it imports `chatAboutPaper` from `services/api.js`, which doesn't exist
  there. Both would need fixing to actually wire this up.
- `services/storage.js`'s `getInterests`/`saveInterests`/`isPaperSaved`/`savePaperId`/
  `unsavePaperId` are dead code (device-local versions from before interests/bookmarks moved to
  the account-based backend) - harmless, but worth removing in a cleanup pass.
- `assets/sounds/bookmark-ding.wav` and `swipe-whoosh.wav` are placeholder sounds synthesized
  programmatically (simple sine/noise envelopes), not produced sound design - swap them for
  real assets whenever you have some; same filenames/paths, no code changes needed.
