#!/usr/bin/env python3
"""Idempotently import legacy data/<year>/<title>/anime.json records."""
import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.app.database import SessionLocal
from backend.app.models import Anime, Episode, EpisodeSource, Genre, Language, Season

LANGS = [("ta", "Tamil", "தமிழ்"), ("en", "English", "English"), ("hi", "Hindi", "हिन्दी"), ("te", "Telugu", "తెలుగు"), ("ml", "Malayalam", "മലയാളം"), ("kn", "Kannada", "ಕನ್ನಡ"), ("und", "Unspecified", "Unspecified")]

def slugify(text):
    value = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().casefold()
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", value)).strip("-") or "untitled"

def parse_anilist_id(url):
    match = re.search(r"anilist\.co/anime/(\d+)", url or "", re.I)
    return int(match.group(1)) if match else None

def clean_url(value):
    return "".join(ch for ch in str(value or "").strip() if ch.isprintable())

def validate(path):
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict): raise ValueError("root must be an object")
    name = str(value.get("name") or path.parent.name).strip()
    if not name: raise ValueError("name is empty")
    eps = value.get("episodes", [])
    if not isinstance(eps, list): raise ValueError("episodes must be an array")
    normalized, seen, warnings = [], set(), []
    for raw in eps:
        if not isinstance(raw, dict):
            warnings.append("ignored a non-object episode entry")
            continue
        try: number = int(raw.get("episode"))
        except (TypeError, ValueError):
            warnings.append(f"ignored episode with invalid number: {raw.get('episode')!r}")
            continue
        if number < 1 or number in seen:
            warnings.append(f"ignored episode number {number} (must be positive and unique)")
            continue
        seen.add(number)
        normalized.append((number, clean_url(raw.get("server1")), clean_url(raw.get("server2"))))
    return value, name, normalized, warnings

def import_files(source):
    files = sorted(source.glob("*/*/anime.json"))
    errors = imported = 0
    with SessionLocal() as db:
        for code, name, native in LANGS:
            if not db.query(Language).filter_by(code=code).first(): db.add(Language(code=code, name=name, native_name=native))
        db.flush()
        db.commit()
        unknown = db.query(Language).filter_by(code="und").one()
        for path in files:
            try:
                data, name, eps, warnings = validate(path)
                for warning in warnings:
                    print(f"WARNING {path}: {warning}", file=sys.stderr)
                try: year = int(str(data.get("released_date") or path.parent.parent.name)[:4])
                except ValueError: year = None
                slug = slugify(name)
                anime = db.query(Anime).filter_by(slug=slug).first()
                if anime is not None and anime.year not in (None, year):
                    slug = f"{slug}-{year or 'unknown'}"
                    anime = db.query(Anime).filter_by(slug=slug).first()
                if anime is None: anime = Anime(name=name, slug=slug); db.add(anime)
                anime.name, anime.year = name, year
                anime.status = str(data.get("status") or "Unknown")
                anime.type = str(data.get("type") or "")
                anime.anilist_url = str(data.get("anilist_link") or "")
                anime.anilist_id = parse_anilist_id(anime.anilist_url)
                anime.description = str(data.get("description") or "")
                anime.synonyms = str(data.get("alt_name") or "")
                anime.studio = str(data.get("studio") or "")
                anime.total_episodes = int(data.get("total_episodes") or len(eps))
                anime.poster_url = f"/data/{path.parent.parent.name}/{path.parent.name}/photo.jpg"
                if unknown not in anime.languages: anime.languages.append(unknown)
                for genre_name in filter(None, (g.strip() for g in str(data.get("genre") or "").split(","))):
                    genre = db.query(Genre).filter_by(slug=slugify(genre_name)).first()
                    if genre is None: genre = Genre(name=genre_name, slug=slugify(genre_name)); db.add(genre); db.flush()
                    if genre not in anime.genres: anime.genres.append(genre)
                db.flush()
                season = db.query(Season).filter_by(anime_id=anime.id, season_number=1).first()
                if season is None: season = Season(anime=anime, season_number=1, name="Season 1"); db.add(season); db.flush()
                for number, *urls in eps:
                    episode = db.query(Episode).filter_by(season_id=season.id, episode_number=number).first()
                    if episode is None: episode = Episode(season=season, episode_number=number); db.add(episode); db.flush()
                    for priority, url in enumerate(urls, start=1):
                        if not url or url.casefold() == "no": continue
                        host = (urlparse(url).hostname or "legacy").lower()
                        provider = host.removeprefix("www.").split(".")[0] or "legacy"
                        source_row = db.query(EpisodeSource).filter_by(episode_id=episode.id, language_id=unknown.id, provider=provider, url=url).first()
                        if source_row is None:
                            db.add(EpisodeSource(episode=episode, language=unknown, provider=provider, url=url, priority=priority * 10, active=True))
                        else:
                            source_row.priority = priority * 10
                            source_row.active = True
                db.commit()
                imported += 1
            except Exception as exc:
                errors += 1
                db.rollback()
                unknown = db.query(Language).filter_by(code="und").one()
                print(f"ERROR {path}: {exc}", file=sys.stderr)
    print(f"Imported/updated {imported}/{len(files)} anime; {errors} file error(s).")
    return errors

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=ROOT.parent / "data", help="Legacy data root (year/title/anime.json)")
    args = parser.parse_args()
    if not args.source.is_dir(): parser.error(f"source directory not found: {args.source}")
    raise SystemExit(1 if import_files(args.source) else 0)
