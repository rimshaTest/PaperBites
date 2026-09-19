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
  still be treated as exposed and rotated/revoked.
- **Pexels** — `api.pexels_key` — same as Cloudinary: removed from the
  current file (was only used by the video pipeline), still exposed via
  history.

**Action needed (only doable from the account owner's dashboards):**

1. Rotate/reset the MongoDB Atlas database user's password, then update the
   `connection_string` in `backend/config.json` (or, better, move it to an
   environment variable / an untracked `.env` file).
2. Revoke/regenerate the Cloudinary API secret (no code in this repo uses
   Cloudinary anymore, so once rotated there's nothing left to update here).
3. Revoke/regenerate the Pexels API key (same — unused by any code now).
4. Confirm `backend/config.json` is added to `.gitignore` so a real
   connection string doesn't get committed again after rotation.

## MongoDB usage (resolved)

Paper fetches ARE written to MongoDB from this repo: `backend/db.py`
(`upsert_papers`, `get_all_papers`, `get_paper_by_id`) is called by
`backend/cli.py`'s `fetch-latest` command and read by
`backend/api_server.py`'s `/api/papers` routes, which now back the app's
primary paper feed. The earlier open question here (no code in this repo
importing `pymongo.MongoClient`) was answered once `main`'s "skeletal
additions" commit — which added `db.py` — was pulled into this branch.
