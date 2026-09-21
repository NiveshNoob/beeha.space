# Beeha — FastAPI version

This version keeps the Beeha visual design but moves the site to a proper FastAPI architecture.

## Structure

```text
beeha_fastapi/
├── server.py
├── generate.py
├── requirements.txt
├── data/
├── templates/
│   ├── index.html
│   └── watch.html
└── static/
    ├── style.css
    ├── watch.css
    ├── script.js
    └── watch.js
```

Your existing `data/` directory can stay beside these files. The server discovers anime from:

```text
data/<year>/<anime>/anime.json
```

It also supports the older `meta.txt` metadata format when `anime.json` is missing.

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

For Nushell:

```nu
.venv/bin/pip install -r requirements.txt
```

## Run

Development:

```bash
python server.py
```

or:

```bash
uvicorn server:app --host 0.0.0.0 --port 8080 --reload
```

Production-style single process:

```bash
uvicorn server:app --host 0.0.0.0 --port 8080
```

Open `http://127.0.0.1:8080/`.

## Add anime

```bash
python generate.py
```

## Manage catalog and watchlist

`anime_manager.py` provides non-interactive commands to add, edit, delete, query,
and list catalog entries. It uses `list.txt` as a separate watchlist and can show
which watchlist titles are not present in `data/`.

```bash
# Query the catalog
python anime_manager.py list --query "attack"
python anime_manager.py show "Solo Leveling" --year 2024

# Add or edit an entry
python anime_manager.py add "Example Anime" --year 2026 --status Ongoing --genre Fantasy
python anime_manager.py update "Example Anime" --year 2026 --total-episodes 12

# Deletion intentionally requires confirmation
python anime_manager.py delete "Example Anime" --year 2026 --yes

# Manage the separate watchlist (defaults to list.txt) and compare it with data/
python anime_manager.py watchlist add "Frieren: Beyond Journey's End" --year 2023
python anime_manager.py watchlist compare
python anime_manager.py watchlist compare --year 2023
```

Pass episode data with `--episodes` as a JSON array or `--episodes-file` as the
path to a JSON file. Run `python anime_manager.py --help` for all options.

Watchlist entries with a year are stored as `Anime Title | 2023`. They compare
against the matching catalog title and year; older entries without a year remain
compatible and compare by title only.

The generator updates JSON/text metadata only. It does **not** generate `index.html` or one HTML page per episode anymore. FastAPI serves the same `/watch` page dynamically.

## Important change

Old:

```text
data/2026/My Anime/episodes/1.html
```

New:

```text
/watch?year=2026&anime=My%20Anime&episode=1
```

The player uses the `server1` and `server2` URLs stored in `anime.json`. Use `"no"` (or leave both URLs empty) for an unreleased episode; its watch page will show **Releasing** instead of opening a player. Ongoing anime (where `status` is `Ongoing`) are available from `/api/ongoing`.

## Admin reports

Set a token before starting the server:

```bash
export BEEHA_ADMIN_TOKEN='change-this'
```

Then request reports with:

```text
X-Admin-Token: change-this
```

`/api/reports` is disabled until the token is configured, so reports are not publicly exposed.
