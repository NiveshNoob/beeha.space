# Beeha content platform (isolated implementation)

This directory contains the next Beeha platform without replacing the current root-level site. Its FastAPI service uses one SQLAlchemy database (`platform/beeha.db` by default), with separate anime, movie, and manga tables. Languages, genres, episodes, seasons, chapters, and provider URLs are normalized into related tables. Public responses are assembled as nested Pydantic objects.

## Initialize and run

```sh
cd platform
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
python scripts/import_data.py
uvicorn backend.app.main:app --reload
```

Set `BEEHA_DATABASE_URL` to override the SQLite URL. `beeha.db` is the sole catalog database; the existing root `data/` JSON files remain untouched. Importing maps old `server1`/`server2` fields to generic provider source rows. Since those files do not record audio language, the importer associates them with the `und` (Unspecified) language instead of inventing a dub language. Source URLs are carried over as supplied; no extraction or bypass behavior is included.

Alembic migrations live in `backend/migrations`. `python scripts/import_data.py --source /path/to/data` imports or updates records by slug and episode number; malformed files are reported and skipped. Re-running is safe. No JSON data is deleted.

## Provider model

An episode or movie can have multiple source rows per language. `provider` is a free-form label such as `beeha` or `voe`; `priority` sorts preferred active sources first. A future Beeha server/CDN is another provider value and needs no schema change. Manga chapters have language assignments and optional generic chapter/page source rows.

## Languages and catalog additions

Add a language with `python scripts/manage_catalog.py language add --code bn --name Bengali --native-name বাংলা`. The initial seed set is `ta`, `en`, `hi`, `te`, `ml`, `kn`, plus `und` for legacy records with no known language.

## Add and edit catalog records

Run the database manager from `platform/`; it writes directly to `beeha.db` and does not modify the legacy JSON files:

```sh
# List existing anime
python scripts/manage_catalog.py list anime

# Add anime metadata, languages, and genres
python scripts/manage_catalog.py add anime --name "Example Anime" --year 2026 \
  --status Ongoing --languages ta,en --genres "Action, Fantasy"

# Edit metadata and replace language/genre assignments
python scripts/manage_catalog.py update anime example-anime \
  --set 'description=An updated summary' --set status=Completed \
  --languages ta,hi --genres "Action, Drama"

# Add an episode; the command prints its database ID
python scripts/manage_catalog.py episode --anime example-anime --season 1 \
  --number 1 --title "First Steps"

# Use the printed ID as --id to attach a language-specific provider
python scripts/manage_catalog.py source episode --id 123 --language ta \
  --provider beeha --url 'https://example.test/watch' --priority 1

# Create movie and manga records, then a chapter
python scripts/manage_catalog.py add movie --name "Example Film" --year 2026 --languages en,ta
python scripts/manage_catalog.py add manga --name "Example Manga" --author "A. Author" --languages en
python scripts/manage_catalog.py chapter --manga example-manga --number 1 --title "Beginning" --languages en

# Change a source or turn it off
python scripts/manage_catalog.py source-update episode 123 --url 'https://example.test/new' --priority 2
python scripts/manage_catalog.py source-update episode 123 --inactive
```

Use `python scripts/manage_catalog.py --help` for all commands. The root `anime_manager.py` still edits the original JSON source; run `python scripts/import_data.py` afterward to copy those changes into SQLite. CLI changes to `beeha.db` are immediately visible through the platform API and frontend.

## Upload a Telegram deeplink to Streamtape

`scripts/telegram_to_streamtape.py` looks up the deeplink token in the Telegram
file-server SQLite database, downloads the referenced storage message through
Telegram MTProto, uploads the file to Streamtape, and creates or updates the
episode's `streamtape` source in this catalog. You identify the target using its
anime name or slug, season number, and episode number.

Install its dependencies in the platform environment, then set credentials:

```bash
pip install -r requirements.txt
export TELEGRAM_API_ID='...'
export TELEGRAM_API_HASH='...'
export BOT_TOKEN='...'
export STREAMTAPE_LOGIN='...'
export STREAMTAPE_KEY='...'
```

List episode numbers first if you need to check which episodes exist:

```bash
python platform/scripts/telegram_to_streamtape.py lookup --anime 'Dr. Stone'
```

Then upload and attach the deeplink to that anime's episode:

```bash
python platform/scripts/telegram_to_streamtape.py upload 'https://t.me/your_bot?start=TOKEN' --anime 'Dr. Stone' --season 1 --episode 1 --language ta
```

`--season` defaults to `1`; `--language` defaults to `ta`. You can use the
catalog slug instead of the exact anime name.

The file-server database defaults to `~/bot_tell/beeha_file_server.sqlite3`;
override it with `BEEHA_FILE_SERVER_DB` if needed. `BEEHA_DATABASE_URL` continues
to choose the catalog database. Telegram credentials must belong to a bot that
can read the configured storage channel. The script writes a temporary local
copy during transfer and removes it when finished. An existing Streamtape
source for the same episode and language is updated in place.

## Rust helper

The optional `rust/search` PyO3 module contains a small text-normalization helper used by global search. Python search remains the fallback, so the service works without compiling Rust. Install Rust/Cargo and maturin (`pip install maturin`), activate the project virtual environment, then build/install from this directory with `maturin develop --manifest-path rust/search/Cargo.toml`.
