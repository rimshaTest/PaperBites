# Security TODO

## Rotate leaked credentials (urgent)

`backend/config.json` is committed to git (not gitignored) and has been
pushed to GitHub since the "render and netlify set up" commit. It contains
live credentials in plaintext:

- **MongoDB Atlas** — `storage.mongodb.connection_string`
  (user `novelleapps_db_user`, cluster `paperbitescluster.0pwisgu.mongodb.net`)
- **Cloudinary** — `storage.cloudinary.api_key` / `api_secret`
- **Pexels** — `api.pexels_key`

Once a secret is committed and pushed, rotating it later doesn't undo the
exposure — anyone who cloned/viewed the repo already has the old value.
**Action needed (only doable from the account owner's dashboards):**

1. Rotate/reset the MongoDB Atlas database user's password.
2. Regenerate the Cloudinary API secret.
3. Regenerate the Pexels API key.
4. After rotating, update `backend/config.json` locally (or, better, move
   these to environment variables / an untracked `.env` file) and confirm
   `config.json` is added to `.gitignore` so this doesn't happen again.

## Open question: where are paper fetches actually written to MongoDB?

A pass over the full git history (`git log --all -p -- '*.py' | grep -i mongo`)
found no code — past or present, on any branch — that opens a MongoDB
connection or imports `pymongo.MongoClient`. `config.py`'s `Config` class
(which would read `config.json`) also isn't imported by `api_server.py`.
If paper fetches are being persisted to the `paperbites` Mongo database,
that write path lives outside this repository (a local script, a different
deployment, etc.) — worth tracking down before treating Mongo as this
repo's real datastore, e.g. before migrating auth/bookmarks off the current
JSON-file storage onto it.
