# Security TODO

## Rotate leaked credentials (urgent)

`backend/config.json` is committed to git (not gitignored) and has been
pushed to GitHub since the "render and netlify set up" commit. Once a secret
is committed and pushed, rotating it later doesn't undo the exposure —
anyone who cloned/viewed the repo already has the old value, regardless of
whether the secret is still present in the current file.

- **MongoDB Atlas** — `storage.mongodb.connection_string`
  (user `novelleapps_db_user`, cluster `paperbitescluster.0pwisgu.mongodb.net`)
  — **still live in the current `backend/config.json`. Not yet rotated.**
- **Cloudinary** — `storage.cloudinary.api_key` / `api_secret` — removed
  from the current `backend/config.json` as part of removing the
  video-generation pipeline (Cloudinary was only used to host generated
  videos, which no longer exist). Still present in git history, so it must
  still be treated as exposed and rotated/revoked. The same key/secret pair
  was ALSO hardcoded in `frontend/config.ts` (from the same "render and
  netlify set up" commit) - that file was dead code (nothing imported it;
  its companion `cloudinaryService.tsx` no longer existed either) and has
  now been deleted, but it's a second place this exact secret leaked from,
  still in history either way.
- **Pexels** — `api.pexels_key` — **restored to the current
  `backend/config.json`.** It was removed in an earlier pass on the
  (incorrect) assumption it was only used by the video pipeline, but
  `paper/latest.py`'s `fetch_paper_image`/`_attach_images` uses it to fetch
  each paper's card thumbnail image - a live, non-video feature. Removing it
  had silently broken card images going forward (already-fetched papers
  keep whatever `image_url` they were stored with; new fetches would get
  none without this key). Still exposed via history either way, and now
  live in the current file too, so it still needs rotation.

**Action needed (only doable from the account owner's dashboards):**

1. Rotate/reset the MongoDB Atlas database user's password, then update the
   `connection_string` in `backend/config.json` (or, better, move it to an
   environment variable / an untracked `.env` file).
2. Revoke/regenerate the Cloudinary API secret (no code in this repo uses
   Cloudinary anymore, so once rotated there's nothing left to update here).
3. Regenerate the Pexels API key and update `api.pexels_key` in
   `backend/config.json` (this one IS still used, by the live paper-card
   image fetch - don't just delete it after rotating).
4. Confirm `backend/config.json` is added to `.gitignore` so a real
   connection string doesn't get committed again after rotation.

## Committed account data (urgent, new)

`backend/users.json` and `backend/sessions.json` were committed and pushed
(the "added profile and bookmark features with theme adherence" commit) -
neither had ever been in `.gitignore`. Both contain real, live data, not
placeholders:

- `users.json`: an actual account's email, PBKDF2 salt, and password hash
  (200,000 iterations - not trivial to crack, but a public hash is still
  worse than a private one, and the value is now permanently in git history
  regardless of what's in the current file).
- `sessions.json`: a **live, currently-valid bearer session token** for that
  account (30-day TTL from creation per `auth.py`'s `SESSION_TTL_SECONDS`) -
  anyone with this token can act as that account against the backend until
  it expires, no password needed.

`backend/interests.json` and `backend/bookmarks.json` were committed too;
lower severity (no credentials), but still real per-account data that
shouldn't be in git.

**Fixed in this pass:** all four files added to `backend/.gitignore` and
untracked (`git rm --cached`) - they stay on disk locally, just stop being
committed going forward. This does NOT undo the exposure already pushed.

**Action needed:**
1. Treat the exposed session token as compromised - log out and back in on
   that account (or otherwise invalidate the token in `sessions.json`) to
   get a fresh one; the old one otherwise remains valid until it naturally
   expires.
2. Consider changing that account's password, since the hash is now
   historically exposed - low urgency given PBKDF2/200k iterations, but
   cheap to do.
3. Nothing to do for `interests.json`/`bookmarks.json` beyond the
   `.gitignore` fix already made.

## MongoDB usage (resolved)

Paper fetches ARE written to MongoDB from this repo: `backend/db.py`
(`upsert_papers`, `get_all_papers`, `get_paper_by_id`) is called by
`backend/cli.py`'s `fetch-latest` command and read by
`backend/api_server.py`'s `/api/papers` routes, which now back the app's
primary paper feed. The earlier open question here (no code in this repo
importing `pymongo.MongoClient`) was answered once `main`'s "skeletal
additions" commit — which added `db.py` — was pulled into this branch.
