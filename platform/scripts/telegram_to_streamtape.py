#!/usr/bin/env python3
"""Download a Beeha Telegram file link, upload it to Streamtape, and set an episode source.

Run from the repository root or platform directory. Credentials are read from the
environment; see platform/README.md for setup and an example.
"""
from __future__ import annotations

import argparse
import asyncio
import os
import re
import sqlite3
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlparse, parse_qs

import requests
from telethon import TelegramClient
from telethon.errors import RPCError

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "platform"))
from backend.app.database import SessionLocal  # noqa: E402
from backend.app.models import Anime, Episode, EpisodeSource, Language, Season  # noqa: E402
from sqlalchemy import select  # noqa: E402

FILE_SERVER_DB = Path(os.getenv("BEEHA_FILE_SERVER_DB", "~/bot_tell/beeha_file_server.sqlite3")).expanduser()
API_BASE = "https://api.streamtape.com"
DEFAULT_SESSION = Path.home() / ".local" / "state" / "beeha" / "telegram_streamtape"


def token_from_link(value: str) -> str:
    if "://" not in value:
        token = value.strip()
    else:
        parsed = urlparse(value)
        token = parse_qs(parsed.query).get("start", [""])[0]
    if not token or len(token) > 64 or not re.fullmatch(r"[A-Za-z0-9_-]+", token):
        raise ValueError("Expected a Beeha Telegram deeplink (with ?start=TOKEN) or token")
    return token


def deeplink_for_source(value: str, token: str) -> str:
    """Store a usable Telegram deeplink even when the CLI received only a token."""
    if "://" in value:
        return value.strip()
    bot_username = os.getenv("TELEGRAM_BOT_USERNAME", "beehaspacebot").strip().lstrip("@")
    if not re.fullmatch(r"[A-Za-z0-9_]{5,32}", bot_username):
        raise ValueError("TELEGRAM_BOT_USERNAME must be a valid Telegram bot username")
    return f"https://t.me/{bot_username}?start={token}"


def file_record(token: str) -> sqlite3.Row:
    if not FILE_SERVER_DB.is_file():
        raise FileNotFoundError(f"File-server database not found: {FILE_SERVER_DB}")
    with sqlite3.connect(f"file:{FILE_SERVER_DB}?mode=ro", uri=True) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM files WHERE token = ?", (token,)).fetchone()
    if row is None:
        raise ValueError(f"No Telegram file record for token {token!r}")
    if row["media_type"] not in {"video", "document", "animation"}:
        raise ValueError(f"Record is {row['media_type']!r}, not video/document media")
    return row


async def download_message(chat_id: int, message_id: int, output: Path) -> None:
    api_id = os.getenv("TELEGRAM_API_ID", "")
    api_hash = os.getenv("TELEGRAM_API_HASH", "")
    bot_token = os.getenv("BOT_TOKEN", "")
    if not (api_id and api_hash and bot_token):
        raise RuntimeError("Set TELEGRAM_API_ID, TELEGRAM_API_HASH, and BOT_TOKEN")
    configured_session = os.getenv("TELEGRAM_SESSION")
    legacy_session = Path("beeha_streamtape.session")
    session = Path(configured_session).expanduser() if configured_session else (
        Path("beeha_streamtape") if legacy_session.is_file() else DEFAULT_SESSION
    )
    session.parent.mkdir(parents=True, exist_ok=True)
    client = TelegramClient(str(session), int(api_id), api_hash)
    try:
        await client.start(bot_token=bot_token)
        message = await client.get_messages(chat_id, ids=message_id)
        if message is None or not message.media:
            raise ValueError(f"Telegram message {message_id} in {chat_id} has no media")
        result = await client.download_media(message, file=str(output))
        if not result or not output.is_file() or output.stat().st_size == 0:
            raise RuntimeError("Telegram did not return a downloadable media file")
    finally:
        await client.disconnect()


def streamtape_upload(path: Path, filename: str) -> str:
    login, key = os.getenv("STREAMTAPE_LOGIN", ""), os.getenv("STREAMTAPE_KEY", "")
    if not login or not key:
        raise RuntimeError("Set STREAMTAPE_LOGIN and STREAMTAPE_KEY")
    params = {"login": login, "key": key}
    folder = os.getenv("STREAMTAPE_FOLDER", "").strip()
    if folder:
        params["folder"] = folder
    response = requests.get(f"{API_BASE}/file/ul", params=params, timeout=60)
    response.raise_for_status()
    payload = response.json()
    if payload.get("status") != 200 or not payload.get("result", {}).get("url"):
        raise RuntimeError(f"Streamtape did not provide an upload URL: {payload.get('msg', payload)}")
    with path.open("rb") as video:
        uploaded = requests.post(
            payload["result"]["url"],
            files={"file1": (filename, video, "video/mp4")},
            timeout=(60, 3600),
        )
    uploaded.raise_for_status()
    result = uploaded.json()
    if result.get("status") != 200:
        raise RuntimeError(f"Streamtape upload failed: {result.get('msg', result)}")
    file_info = result.get("result")
    if isinstance(file_info, dict):
        file_id = file_info.get("id") or file_info.get("linkid")
    else:
        file_id = file_info if isinstance(file_info, str) else None
    if not file_id:
        raise RuntimeError(f"Upload succeeded but response contained no file ID: {result}")
    return f"https://streamtape.com/e/{file_id}/"


def check_credentials() -> None:
    """Fail early so missing credentials never waste a Telegram download."""
    required = {
        "TELEGRAM_API_ID": os.getenv("TELEGRAM_API_ID", ""),
        "TELEGRAM_API_HASH": os.getenv("TELEGRAM_API_HASH", ""),
        "BOT_TOKEN": os.getenv("BOT_TOKEN", ""),
        "STREAMTAPE_LOGIN": os.getenv("STREAMTAPE_LOGIN", ""),
        "STREAMTAPE_KEY": os.getenv("STREAMTAPE_KEY", ""),
    }
    missing = [name for name, value in required.items() if not value]
    if missing:
        raise RuntimeError(
            "Missing environment variable(s): " + ", ".join(missing)
            + ". Set them in your shell startup file; see the platform README."
        )
    try:
        int(required["TELEGRAM_API_ID"])
    except ValueError as exc:
        raise RuntimeError("TELEGRAM_API_ID must be a number") from exc


def update_episode_sources(
    episode_id: int,
    language_code: str,
    streamtape_url: str,
    telegram_url: str,
) -> dict[str, int]:
    """Create or refresh both playback sources together."""
    db = SessionLocal()
    try:
        episode = db.get(Episode, episode_id)
        if episode is None:
            raise ValueError(f"No catalog episode with id {episode_id}")
        language = db.scalar(select(Language).where(Language.code == language_code.lower()))
        if language is None:
            raise ValueError(f"Unknown language {language_code!r}; create it with manage_catalog.py language add")
        if language not in episode.season.anime.languages:
            episode.season.anime.languages.append(language)
        source_ids = {}
        for provider, url, priority in (
            ("streamtape", streamtape_url, 10),
            ("telegram", telegram_url, 20),
        ):
            existing = db.scalar(select(EpisodeSource).where(
                EpisodeSource.episode_id == episode_id,
                EpisodeSource.language_id == language.id,
                EpisodeSource.provider == provider,
            ).order_by(EpisodeSource.priority).limit(1))
            if existing:
                existing.url = url
                existing.active = True
                source_ids[provider] = existing.id
            else:
                source = EpisodeSource(
                    episode=episode,
                    language=language,
                    provider=provider,
                    url=url,
                    priority=priority,
                )
                db.add(source)
                db.flush()
                source_ids[provider] = source.id
        db.commit()
        return source_ids
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def validate_catalog_target(episode_id: int, language_code: str) -> None:
    db = SessionLocal()
    try:
        if db.get(Episode, episode_id) is None:
            raise ValueError(f"No catalog episode with id {episode_id}")
        if db.scalar(select(Language.id).where(Language.code == language_code.lower())) is None:
            raise ValueError(f"Unknown language {language_code!r}; create it with manage_catalog.py language add")
    finally:
        db.close()


def find_anime_episode(anime_query: str, season_number: int, episode_number: int) -> Episode:
    db = SessionLocal()
    try:
        anime_matches = db.scalars(select(Anime).where(
            (Anime.slug == anime_query) | (Anime.name.ilike(anime_query))
        )).all()
        if not anime_matches:
            raise ValueError(f"No anime found with slug or exact name {anime_query!r}")
        if len(anime_matches) != 1:
            matches = ", ".join(f"{anime.slug} ({anime.name})" for anime in anime_matches)
            raise ValueError(f"Anime name is ambiguous; use its slug: {matches}")
        anime = anime_matches[0]
        season = db.scalar(select(Season).where(
            Season.anime_id == anime.id,
            Season.season_number == season_number,
        ))
        if season is None:
            raise ValueError(f"{anime.name} has no season {season_number}")
        episode = db.scalar(select(Episode).where(
            Episode.season_id == season.id,
            Episode.episode_number == episode_number,
        ))
        if episode is None:
            raise ValueError(f"{anime.name} season {season_number} has no episode {episode_number}")
        return episode
    finally:
        db.close()


def list_anime_episodes(anime_query: str, season_number: int | None) -> None:
    db = SessionLocal()
    try:
        anime_matches = db.scalars(select(Anime).where(
            (Anime.slug == anime_query) | (Anime.name.ilike(anime_query))
        )).all()
        if not anime_matches:
            raise ValueError(f"No anime found with slug or exact name {anime_query!r}")
        if len(anime_matches) != 1:
            matches = ", ".join(f"{anime.slug} ({anime.name})" for anime in anime_matches)
            raise ValueError(f"Anime name is ambiguous; use its slug: {matches}")
        anime = anime_matches[0]
        query = select(Episode, Season).join(Season).where(Season.anime_id == anime.id)
        if season_number is not None:
            query = query.where(Season.season_number == season_number)
        rows = db.execute(query.order_by(Season.season_number, Episode.episode_number)).all()
        if not rows:
            print(f"No episodes found for {anime.name}")
            return
        print(f"{anime.name} [{anime.slug}]")
        for episode, season in rows:
            print(f"episode_id={episode.id}\tseason={season.season_number}\tepisode={episode.episode_number}\t{episode.title}")
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        epilog=(
            "Examples:\n"
            "  python scripts/telegram_to_streamtape.py lookup --anime dr_stone\n"
            "  python scripts/telegram_to_streamtape.py upload --anime dr_stone --episode 1 'https://t.me/bot?start=TOKEN'\n\n"
            "Credentials: TELEGRAM_API_ID, TELEGRAM_API_HASH, BOT_TOKEN, "
            "STREAMTAPE_LOGIN, STREAMTAPE_KEY. Optional: BEEHA_FILE_SERVER_DB, "
            "TELEGRAM_SESSION, TELEGRAM_BOT_USERNAME, STREAMTAPE_FOLDER."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    commands = parser.add_subparsers(dest="command", required=True)
    lookup = commands.add_parser("lookup", help="find catalog episodes by anime name or slug")
    lookup.add_argument("--anime", required=True, help="Exact anime name or catalog slug")
    lookup.add_argument("--season", type=int, help="Limit results to this season")
    upload = commands.add_parser("upload", help="upload a Telegram deeplink and attach it to an episode")
    upload.add_argument("deeplink", help="Telegram bot link (https://t.me/bot?start=TOKEN) or token")
    upload.add_argument("--anime", required=True, help="Exact anime name or catalog slug")
    upload.add_argument("--season", type=int, default=1, help="Season number (default: 1)")
    upload.add_argument("--episode", type=int, required=True, help="Episode number within the season")
    upload.add_argument("--language", default="ta", help="Existing catalog language code (default: ta)")
    args = parser.parse_args()
    if args.command == "lookup":
        try:
            list_anime_episodes(args.anime, args.season)
        except ValueError as exc:
            raise SystemExit(f"Error: {exc}") from exc
        return
    try:
        check_credentials()
        token = token_from_link(args.deeplink)
        record = file_record(token)
        episode = find_anime_episode(args.anime, args.season, args.episode)
        validate_catalog_target(episode.id, args.language)
        with tempfile.TemporaryDirectory(prefix="beeha-streamtape-") as tmp:
            path = Path(tmp) / Path(record["filename"]).name
            asyncio.run(download_message(int(record["storage_chat_id"]), int(record["storage_message_id"]), path))
            print(f"Downloaded {record['filename']} ({path.stat().st_size:,} bytes)", flush=True)
            stream_url = streamtape_upload(path, path.name)
        source_ids = update_episode_sources(
            episode.id,
            args.language,
            stream_url,
            deeplink_for_source(args.deeplink, token),
        )
        print(
            f"Updated {args.anime} S{args.season:02}E{args.episode:02} "
            f"(episode id {episode.id}): Streamtape source {source_ids['streamtape']}, "
            f"Telegram source {source_ids['telegram']}"
        )
    except (ValueError, FileNotFoundError, RuntimeError, requests.RequestException, RPCError) as exc:
        raise SystemExit(f"Error: {exc}") from exc


if __name__ == "__main__":
    main()
