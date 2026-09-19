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

The player uses the `server1` and `server2` URLs stored in `anime.json`.

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
