# PaperBites App

A mobile application that displays research paper summaries in a TikTok-style interface. This app is designed to make academic research more accessible and engaging through short video summaries.

## Features

- Vertical swipeable interface similar to TikTok/Reels
- Auto-playing videos with summaries of research papers
- Direct links to original research papers via DOI
- Topic filtering by research interests
- Video favoriting and sharing capabilities
- Offline viewing support

## Project Structure

The project consists of two main parts:

1. **Backend** - Python-based system that:
   - Searches for and downloads research papers
   - Extracts text and summarizes content
   - Generates TikTok-style videos with narration

2. **Frontend** - React Native mobile app that:
   - Displays the videos in a swipeable interface
   - Allows users to interact with the content
   - Provides settings for customizing the experience

## Prerequisites

- Node.js (v14 or higher)
- npm or Yarn
- Expo CLI
- iOS or Android device/simulator

## Installation

### Setting up the frontend

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/paperbites.git
   cd paperbites/frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   # or with Yarn
   yarn install
   ```

3. Start the development server:
   ```bash
   npm start
   # or with Yarn
   yarn start
   ```

4. Follow the Expo instructions to open the app on your device or simulator.

### Connecting to the backend

The app is designed to connect to your PaperBites backend API. Edit the `API_URL` in `api/videoService.js` to point to your backend server.

For development purposes, the app includes mock data so you can test the interface without a backend connection.

## Usage

### Home Screen

The home screen displays a vertical feed of research paper videos. Swipe up and down to navigate between videos. Each video includes:

- Research paper title
- Brief summary
- Key insights
- Relevant keywords as hashtags
- Link to the original paper

### Controls

- Tap the center of the video to play/pause
- Like button to save your favorite videos
- Share button to share the video or paper
- Bookmark button to save for offline viewing

### Settings

The settings screen allows you to customize your experience:

- Toggle autoplay
- Enable/disable dark mode
- Set research interests to customize your feed
- Manage storage and clear cache

## Current Status (as of 2026-09-14)

### Paper-card feed (new direction, in progress)

The home feed is pivoting from generated videos to swipeable **paper cards** (title, authors, brief description, citation count), sourced from free academic APIs. The video pipeline below is deferred/experimental, not removed.

- **Fetching**: `backend/paper/latest.py` pulls recent papers from **Semantic Scholar** and **OpenAlex** (both free, no scraping) for a fixed list of categories (`CATEGORIES` in that file), with retry/backoff on rate limits and a fix for an OpenAlex data bug (bogus far-future publication dates were crowding out real recent papers - now bounded server-side).
- **Storage**: `backend/db.py` upserts fetched papers into MongoDB Atlas (`papers` collection, unique on `source`+`source_id`). Run `python cli.py fetch-latest [--category "..."] [--days N] [--limit N]` to populate/refresh it.
- **API**: `backend/api_server.py` now serves `GET /api/categories`, `GET /api/papers?category=&limit=&offset=`, and `GET /api/papers/{id}` — verified live against real MongoDB data. Descriptions are currently trimmed abstracts (a placeholder) until persona-tailored LLM descriptions are wired in per the approved plan.
- **Secrets**: MongoDB and OpenAlex credentials now live in `backend/.env` (gitignored), loaded via `python-dotenv` in `config.py`. Semantic Scholar's anonymous tier still rate-limits fairly aggressively; getting a free Semantic Scholar API key would help (OpenAlex already has one).
- **Not yet built**: real user accounts, the sign-up/onboarding wizard, and persona-tailored descriptions (all specced in the approved plan at `~/.claude/plans/rustling-scribbling-walrus.md`).

### Backend (Python) — legacy video pipeline (deferred)
- **Working end-to-end**: paper search (arXiv, OpenAlex, Semantic Scholar, Unpaywall, Google Scholar fallback), license/open-access checks, download, text extraction (PyMuPDF + OCR fallback), summarization (HuggingFace BART with extractive fallback), and video composition, all orchestrated via `backend/cli.py`.
- **Video generation is weakened**: voiceover uses free/low-quality gTTS; real stock visuals (Pexels) are implemented but **disabled by default**, so generated videos currently only get gradient-background text overlays. One dead code path in `video/compose.py` mixes MoviePy v1/v2 APIs.
- **API server**: `backend/api_server.py` still serves pre-generated video metadata (`/api/videos`, `/api/videos/{id}`, `/api/topics`) unchanged, alongside the new papers routes above. There is no endpoint to trigger video generation remotely — that only happens via the CLI.
- **No videos have been generated yet** in this environment, so those routes currently return empty results.
- **Storage**: Cloudinary upload is wired up and working; an S3 config block exists in `config.py` but no S3 module was ever implemented.
- 🔴 **Security**: `backend/config.json` (tracked in git) has a live MongoDB username/password, a Cloudinary secret, and a Pexels API key committed to git history. Rotate these and keep new secrets in `.env` only, as done for the new Mongo/OpenAlex credentials.

### Frontend (React Native / Expo)
- **Fixed**: the app used to crash on load because `services/cloudinaryService.tsx` imported the server-side Node Cloudinary SDK into client code. That file has been removed; the video feed now calls the working `services/api.js` REST client against the backend.
- **Fixed**: a routing conflict where a legacy `app/index.js` screen silently won the `/` route over the intended Expo Router tab navigator. The legacy screen was removed.
- **Restructured navigation**: three tabs — **Home** (swipeable video feed, filterable by selected interests), **Interests** (multi-select topics fetched from the backend, persisted locally), and **Profile** (shows session email, links to Settings, log out).
- **New Login screen** (`app/login.js`) matching a provided paper-themed design (parchment background, serif headings, yellow CTA, bordered inputs, Google/Apple buttons). Wired to a root-level auth gate in `app/_layout.tsx`.
  - 🔴 **No real backend authentication exists.** Login only validates email format/password length client-side and stores a session flag in `AsyncStorage`. Google/Apple buttons are non-functional placeholders. Anyone can "log in" with any well-formed email/password.
- **New Settings screen** (`app/settings.js`) finally gives the previously-unused `useAppSettings` hook a UI (autoplay, dark mode, push notifications, download quality).
- **Still orphaned / not linked from active navigation**: `app/search.js` and `app/topics.js` are reachable only via the Interests tab's search icon and topic chips (topics screen itself isn't linked from the tab bar anymore since it was folded into Interests) — functionally complete but worth revisiting for consistency.
- **Dev servers**: `.claude/launch.json` has configs for both `paperbites-frontend-web` (port 8081) and `paperbites-backend-api` (port 8000) for local preview.
- **Upgraded Expo SDK 53 → 57** (see below).

### Verified working (browser-tested)
Login → Home feed (fetches real backend data, correct empty state) → Interests (fetches real topics) → Profile → Settings, all with no crashes, using the actual backend API rather than mock/broken data sources.

### Expo SDK 53 → 57 migration (2026-09-14)

- Bumped `expo`, all `expo-*` packages, `react`/`react-dom` (19.2.3), `react-native` (0.86.3), and related native modules to their SDK 57-compatible versions; added `react-native-worklets` (now required by Reanimated 4.x).
- **Removed `expo-av`** (flagged unmaintained by `expo-doctor`) and migrated all real usages to `expo-video`'s current hook-based API (`useVideoPlayer` + `VideoView`, not the old `<Video>` component):
  - `components/VideoPlayer.js` was rewritten — it had actually been "half-migrated" already (importing from `expo-video` but still calling `expo-av`-style methods like `playAsync()`/`onPlaybackStatusUpdate` that don't exist in modern `expo-video`), so it was silently broken before this fix.
  - `components/VideoFeed.tsx`'s native video branch was extracted into a `NativeVideoCard` sub-component, since `useVideoPlayer` is a hook and can't be called inside `FlatList`'s `renderItem` directly.
- **Migrated off `@react-navigation/*` direct imports** (required as of SDK 56 — expo-router is no longer compatible with apps that import react-navigation directly) using the official `expo-codemod sdk-56-expo-router-react-navigation-replace` codemod, with one manual fix afterward (the codemod mis-rewrote `components/ui/TabBarBackground.ios.tsx`'s import into a malformed path).
- **Removed `newArchEnabled` from `app.json`** (New Architecture is on by default now, the field is invalid).
- **Switched `tsconfig.json`** from the outdated `@tsconfig/react-native` base (which sets a now-deprecated `moduleResolution`) to `expo/tsconfig.base`, matching the current Expo template. This surfaced a few real (pre-existing, template-original) strictness gaps — fixed `useThemeColor.ts` and `ParallaxScrollView.tsx`'s color-scheme handling (RN now allows a `colorScheme` of `'unspecified'`, not just `'light'`/`'dark'`) and `components/ui/IconSymbol.tsx`'s icon-name typing (the `expo-symbols` upgrade widened the type it was built on).
- **Cleanup directly motivated by the above**: deleted `App.js`, `components/VideoPlayer.tsx` (a confusing unused duplicate of `VideoPlayer.js` with mismatched internal naming), and `components/VideoSplashScreen.js` — all dead code whose only purpose was consuming the now-removed `expo-av`. Also deleted `frontend/paperbites-frontend/` (a fully duplicate, unreferenced Expo scaffold, previously flagged as cruft) since it started failing the stricter type check.
- **Verified**: `npx expo-doctor` passes (bar one pre-existing, unrelated asset issue — `assets/adaptive-icon.png` is actually a JPG despite its `.png` extension), `npx tsc --noEmit` is clean, and the full app was exercised in-browser end-to-end (login → Home → Interests → Profile → Settings) with no runtime errors.
- **Not verified**: the native `expo-video` code paths (`NativeVideoCard`, the rewritten `VideoPlayer.js`) — the web preview only exercises the HTML5 `<video>` branch, so these need a real iOS/Android device or simulator to confirm.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- This app was built using Expo and React Native
- Research papers are accessed through open-access APIs