# PaperBites Frontend

A React Native (Expo Router) app for the PaperBites paper feed. There is no video playback
anywhere in this app anymore - the original TikTok-style video feed was fully removed in favor
of a swipeable card feed over real research papers.

## File structure

```
frontend/
├── app/                          # Screens (Expo Router - file-based routing)
│   ├── (tabs)/
│   │   ├── index.js              # Home tab - renders PaperFeed
│   │   ├── saved.js              # Saved tab - bookmarked papers
│   │   ├── profile.js            # Profile tab
│   │   └── interests.tsx         # Interests editor (not a tab itself - reachable from
│   │                              # Profile > Settings > Manage Feed)
│   ├── author/[id].js            # Every paper by one author
│   ├── journal/[name].js         # Every paper in one journal
│   ├── paper/[id].js             # Paper detail screen
│   ├── chat/[id].js              # Per-paper chat - NOT wired in, see "Known gaps" below
│   ├── login.js / signup.js      # Auth screens
│   ├── add-paper.js              # Add-a-paper-by-citation modal, reached from Saved > "+"
│   ├── interests-onboarding.js   # One-time modal shown right after signup
│   ├── profile-details.js        # Tier 1/2 profile fields with per-field consent toggles
│   ├── settings.js               # Settings > Manage Feed > Interests
│   └── _layout.tsx               # Root Stack + AuthProvider + GestureHandlerRootView
├── components/
│   ├── PaperFeed.tsx             # The actual Home feed: full-screen paging cards, drag the
│   │                              # info panel up to expand and read the full description
│   └── PaperCard.js              # Simpler list-row card, used by the Saved tab
├── hooks/
│   ├── useAuth.js                # Session context (signup/login/logout, persisted + re-
│   │                              # validated against the backend on mount)
│   └── useStorage.js             # useFavoritePapers (account-scoped bookmarks)
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

- **Home**: `PaperFeed` - swipe/page vertically between papers; drag a card's info panel up to
  expand it full-screen and read the description; pull to refresh; paginates automatically.
- **Saved**: bookmarked papers, account-scoped (requires login). The "+" button opens **Add a
  Paper**: paste a citation (MLA, APA, or any other style), tap the right Crossref match, and
  it's saved and auto-bookmarked - Gemini picks the category itself from the paper's text, same
  as it does for the paper's summary.
- **Profile**: shows the signed-in account, with links to Profile Details and Settings, or a
  login/signup prompt when signed out.
- **Profile Details**: Tier 1 (cache-safe: field of study, education level, general interests,
  location) and Tier 2 (sensitive: age, gender, sex, precise location, disabilities, chronic
  illnesses) fields, each Tier 2 field with its own two consent toggles.
- **Settings > Manage Feed > Interests**: pick topics to hard-filter the Home feed to. Also
  shown once as a modal popup right after signup (Skip for now / Continue).
- **Author / Journal pages**: reached by tapping an author or journal name anywhere in the app.
- **Paper detail**: full description, DOI, categories, and a link to the original paper.

## Known gaps

- `app/chat/[id].js` exists but isn't registered in `app/_layout.tsx`'s Stack, so it's
  unreachable - and it imports `chatAboutPaper` from `services/api.js`, which doesn't exist
  there. Both would need fixing to actually wire this up.
- `services/storage.js`'s `getInterests`/`saveInterests`/`isPaperSaved`/`savePaperId`/
  `unsavePaperId` are dead code (device-local versions from before interests/bookmarks moved to
  the account-based backend) - harmless, but worth removing in a cleanup pass.
