#!/usr/bin/env python3
"""Manage Beeha's SQLite catalog directly (run from platform/)."""
import argparse
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from backend.app.database import SessionLocal
from backend.app.models import (
    Anime, ChapterSource, Episode, EpisodeSource, Genre, Language, Manga,
    MangaChapter, Movie, MovieSource, Season,
)

def slugify(text):
    value = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().casefold()
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", value)).strip("-") or "untitled"

def get_language(db, code):
    item = db.scalar(select(Language).where(Language.code == code.strip().lower()))
    if item is None:
        raise ValueError(f"Unknown language code {code!r}; add it with: language add")
    return item

def get_or_create_genres(db, names):
    result = []
    for name in names:
        name = name.strip()
        if not name: continue
        slug = slugify(name)
        genre = db.scalar(select(Genre).where(Genre.slug == slug))
        if genre is None:
            genre = Genre(name=name, slug=slug)
            db.add(genre)
            db.flush()
        result.append(genre)
    return result

def csv(value):
    return [part.strip() for part in (value or "").split(",") if part.strip()]

def catalog_item(db, kind, slug):
    model = {"anime": Anime, "movie": Movie, "manga": Manga}[kind]
    item = db.scalar(select(model).where(model.slug == slug))
    if item is None: raise ValueError(f"No {kind} with slug {slug!r}")
    return item

def create_item(args, db):
    kind = args.kind
    slug = args.slug or slugify(args.name)
    model = {"anime": Anime, "movie": Movie, "manga": Manga}[kind]
    if db.scalar(select(model.id).where(model.slug == slug)):
        raise ValueError(f"{kind} slug {slug!r} already exists; use update")
    default_type = {"movie": "Movie", "manga": "Manga", "anime": "Anime"}[kind]
    fields = dict(name=args.name.strip(), slug=slug, year=args.year, status=args.status, type=args.type or default_type,
                  description=args.description, poster_url=args.poster_url, banner_url=args.banner_url)
    if kind == "anime":
        fields.update(studio=args.studio, total_episodes=args.total_episodes, age_rating=args.age_rating,
                      anilist_url=args.anilist_url, anilist_id=args.anilist_id, synonyms=args.synonyms)
    elif kind == "movie":
        fields.update(duration=args.duration, anilist_url=args.anilist_url, anilist_id=args.anilist_id)
    else:
        fields.update(author=args.author, artist=args.artist, anilist_url=args.anilist_url, anilist_id=args.anilist_id)
    item = model(**fields)
    item.languages = [get_language(db, code) for code in csv(args.languages)]
    item.genres = get_or_create_genres(db, csv(args.genres))
    db.add(item)
    db.commit()
    print(f"Created {kind}: {item.name} (/{kind}/title/{item.slug})")

def update_item(args, db):
    item = catalog_item(db, args.kind, args.slug)
    editable = {
        "anime": {"name", "year", "status", "type", "description", "poster_url", "banner_url", "studio", "total_episodes", "age_rating", "anilist_url", "anilist_id", "synonyms", "japanese_name", "season", "popularity"},
        "movie": {"name", "year", "status", "type", "description", "poster_url", "banner_url", "duration", "anilist_url", "anilist_id"},
        "manga": {"name", "year", "status", "type", "description", "poster_url", "banner_url", "author", "artist", "anilist_url", "anilist_id"},
    }[args.kind]
    values = {}
    for entry in args.set:
        key, sep, value = entry.partition("=")
        if not sep or key not in editable:
            raise ValueError(f"Invalid field {key!r}; editable fields: {', '.join(sorted(editable))}")
        if key in {"year", "total_episodes", "duration", "anilist_id", "popularity"}:
            value = int(value) if value else None
        values[key] = value
    for key, value in values.items(): setattr(item, key, value)
    if args.languages is not None: item.languages = [get_language(db, code) for code in csv(args.languages)]
    if args.genres is not None: item.genres = get_or_create_genres(db, csv(args.genres))
    db.commit()
    print(f"Updated {args.kind}: {item.name} ({item.slug})")

def add_episode(args, db):
    anime = catalog_item(db, "anime", args.anime)
    season = db.scalar(select(Season).where(Season.anime_id == anime.id, Season.season_number == args.season))
    if season is None:
        season = Season(anime=anime, season_number=args.season, name=args.season_name or f"Season {args.season}")
        db.add(season)
        db.flush()
    if db.scalar(select(Episode.id).where(Episode.season_id == season.id, Episode.episode_number == args.number)):
        raise ValueError(f"Episode {args.number} already exists in season {args.season}")
    episode = Episode(season=season, episode_number=args.number, title=args.title, duration=args.duration)
    db.add(episode)
    anime.total_episodes = max(anime.total_episodes, args.number)
    db.commit()
    print(f"Created episode {episode.episode_number} for {anime.slug} (id={episode.id})")

def add_source(args, db):
    language = get_language(db, args.language)
    if args.target == "episode":
        episode = db.get(Episode, args.id)
        if episode is None: raise ValueError(f"No episode id {args.id}")
        anime = episode.season.anime
        if language not in anime.languages: anime.languages.append(language)
        source = EpisodeSource(episode=episode, language=language, provider=args.provider, url=args.url,
                               priority=args.priority, active=not args.inactive)
    elif args.target == "movie":
        movie = db.scalar(select(Movie).where(Movie.slug == args.id))
        if movie is None: raise ValueError(f"No movie with slug {args.id!r}")
        source = MovieSource(movie=movie, language=language, provider=args.provider, url=args.url,
                             priority=args.priority, active=not args.inactive)
        if language not in movie.languages: movie.languages.append(language)
    else:
        chapter = db.get(MangaChapter, args.id)
        if chapter is None: raise ValueError(f"No chapter id {args.id}")
        source = ChapterSource(chapter=chapter, language=language, provider=args.provider, url=args.url,
                               priority=args.priority, active=not args.inactive)
        if language not in chapter.languages: chapter.languages.append(language)
        if language not in chapter.manga.languages: chapter.manga.languages.append(language)
    db.add(source)
    db.commit()
    print(f"Created {args.target} source (id={source.id}, provider={source.provider}, language={language.code})")

def add_chapter(args, db):
    manga = catalog_item(db, "manga", args.manga)
    if db.scalar(select(MangaChapter.id).where(MangaChapter.manga_id == manga.id, MangaChapter.chapter_number == args.number)):
        raise ValueError(f"Chapter {args.number} already exists for {manga.slug}")
    chapter = MangaChapter(manga=manga, chapter_number=args.number, title=args.title)
    chapter.languages = [get_language(db, code) for code in csv(args.languages)]
    for language in chapter.languages:
        if language not in manga.languages: manga.languages.append(language)
    db.add(chapter)
    db.commit()
    print(f"Created chapter {chapter.chapter_number} for {manga.slug} (id={chapter.id})")

def update_episode(args, db):
    episode = db.get(Episode, args.id)
    if episode is None: raise ValueError(f"No episode id {args.id}")
    if args.number is not None: episode.episode_number = args.number
    if args.title is not None: episode.title = args.title
    if args.duration is not None: episode.duration = args.duration
    db.commit()
    print(f"Updated episode id={episode.id} number={episode.episode_number}")

def update_source(args, db):
    model = {"episode": EpisodeSource, "movie": MovieSource, "chapter": ChapterSource}[args.target]
    source = db.get(model, args.id)
    if source is None: raise ValueError(f"No {args.target} source id {args.id}")
    if args.url is not None: source.url = args.url
    if args.provider is not None: source.provider = args.provider
    if args.priority is not None: source.priority = args.priority
    if args.language is not None:
        language = get_language(db, args.language)
        source.language = language
        if args.target == "episode":
            anime = source.episode.season.anime
            if language not in anime.languages: anime.languages.append(language)
        elif args.target == "movie":
            if language not in source.movie.languages: source.movie.languages.append(language)
        else:
            if language not in source.chapter.languages: source.chapter.languages.append(language)
            if language not in source.chapter.manga.languages: source.chapter.manga.languages.append(language)
    if args.active is not None: source.active = args.active
    db.commit()
    print(f"Updated {args.target} source id={source.id}")

def add_language(args, db):
    code = args.code.strip().lower()
    if db.scalar(select(Language.id).where(Language.code == code)):
        raise ValueError(f"Language code {code!r} already exists")
    item = Language(code=code, name=args.name.strip(), native_name=args.native_name.strip())
    db.add(item)
    db.commit()
    print(f"Added language {item.code}: {item.name} ({item.native_name})")

def list_items(args, db):
    model = {"anime": Anime, "movie": Movie, "manga": Manga}[args.kind]
    for item in db.scalars(select(model).order_by(model.name)):
        print(f"{item.slug}\t{item.name}\t{item.year or ''}\t{item.status}")

def parser():
    p = argparse.ArgumentParser(description=__doc__)
    commands = p.add_subparsers(dest="command", required=True)
    add = commands.add_parser("add", help="create anime, movie, or manga metadata")
    add.add_argument("kind", choices=("anime", "movie", "manga")); add.add_argument("--name", required=True)
    add.add_argument("--slug"); add.add_argument("--year", type=int); add.add_argument("--status", default="Unknown")
    add.add_argument("--type", default=""); add.add_argument("--description", default="")
    add.add_argument("--poster-url", default=""); add.add_argument("--banner-url", default="")
    add.add_argument("--languages", default=""); add.add_argument("--genres", default="")
    add.add_argument("--studio", default=""); add.add_argument("--total-episodes", type=int, default=0)
    add.add_argument("--age-rating", default=""); add.add_argument("--synonyms", default="")
    add.add_argument("--author", default=""); add.add_argument("--artist", default="")
    add.add_argument("--duration", type=int); add.add_argument("--anilist-url", default="")
    add.add_argument("--anilist-id", type=int); add.set_defaults(func=create_item)

    edit = commands.add_parser("update", help="modify metadata or language/genre assignments")
    edit.add_argument("kind", choices=("anime", "movie", "manga")); edit.add_argument("slug")
    edit.add_argument("--set", action="append", default=[], metavar="FIELD=VALUE")
    edit.add_argument("--languages", help="replace language codes, comma-separated")
    edit.add_argument("--genres", help="replace genre names, comma-separated")
    edit.set_defaults(func=update_item)

    episode = commands.add_parser("episode", help="add an episode and create its season if needed")
    episode.add_argument("--anime", required=True); episode.add_argument("--season", type=int, default=1)
    episode.add_argument("--season-name"); episode.add_argument("--number", type=int, required=True)
    episode.add_argument("--title", default=""); episode.add_argument("--duration", type=int)
    episode.set_defaults(func=add_episode)

    episode_edit = commands.add_parser("episode-update", help="modify an episode")
    episode_edit.add_argument("id", type=int); episode_edit.add_argument("--number", type=int)
    episode_edit.add_argument("--title"); episode_edit.add_argument("--duration", type=int)
    episode_edit.set_defaults(func=update_episode)

    source = commands.add_parser("source", help="add an episode or movie provider source")
    source.add_argument("target", choices=("episode", "movie", "chapter")); source.add_argument("--id", required=True, help="episode/chapter id or movie slug")
    source.add_argument("--language", required=True); source.add_argument("--provider", required=True)
    source.add_argument("--url", required=True); source.add_argument("--priority", type=int, default=100)
    source.add_argument("--inactive", action="store_true"); source.set_defaults(func=add_source)

    source_edit = commands.add_parser("source-update", help="modify a source URL, provider, language, priority, or status")
    source_edit.add_argument("target", choices=("episode", "movie", "chapter")); source_edit.add_argument("id", type=int)
    source_edit.add_argument("--url"); source_edit.add_argument("--provider"); source_edit.add_argument("--language")
    source_edit.add_argument("--priority", type=int)
    source_edit.add_argument("--active", action="store_true", default=None)
    source_edit.add_argument("--inactive", action="store_false", dest="active")
    source_edit.set_defaults(func=update_source)

    chapter = commands.add_parser("chapter", help="add a manga chapter")
    chapter.add_argument("--manga", required=True); chapter.add_argument("--number", type=int, required=True)
    chapter.add_argument("--title", default=""); chapter.add_argument("--languages", default="")
    chapter.set_defaults(func=add_chapter)

    language = commands.add_parser("language", help="add a language")
    language.add_argument("action", choices=("add",)); language.add_argument("--code", required=True)
    language.add_argument("--name", required=True); language.add_argument("--native-name", required=True)
    language.set_defaults(func=add_language)

    listing = commands.add_parser("list", help="list catalog records")
    listing.add_argument("kind", choices=("anime", "movie", "manga")); listing.set_defaults(func=list_items)
    return p


# OpenAI-compatible tool declarations and dispatcher for AI integrations.
AI_TOOLS = [
    {"type": "function", "function": {
        "name": "catalog_list",
        "description": "List catalog records by media kind.",
        "parameters": {"type": "object", "properties": {
            "kind": {"type": "string", "enum": ["anime", "movie", "manga"]}},
            "required": ["kind"], "additionalProperties": False},
    }},
    {"type": "function", "function": {
        "name": "catalog_add",
        "description": "Create an anime, movie, or manga catalog record.",
        "parameters": {"type": "object", "properties": {
            "kind": {"type": "string", "enum": ["anime", "movie", "manga"]},
            "name": {"type": "string"}, "year": {"type": ["integer", "null"]},
            "description": {"type": "string"}, "status": {"type": "string"},
            "languages": {"type": "array", "items": {"type": "string"}},
            "genres": {"type": "array", "items": {"type": "string"}}},
            "required": ["kind", "name"], "additionalProperties": False},
    }},
]

def execute_ai_tool(name, arguments):
    """Execute an AI tool using the same database functions as the CLI."""
    import contextlib
    import io
    from types import SimpleNamespace

    if not isinstance(arguments, dict):
        raise ValueError("Tool arguments must be an object")
    if name == "catalog_list":
        kind = arguments.get("kind")
        if set(arguments) != {"kind"} or kind not in ("anime", "movie", "manga"):
            raise ValueError("catalog_list requires kind: anime, movie, or manga")
        args, func = SimpleNamespace(kind=kind), list_items
    elif name == "catalog_add":
        allowed = {"kind", "name", "year", "description", "status", "languages", "genres"}
        if set(arguments) - allowed:
            raise ValueError("Unknown catalog_add argument")
        kind, name_value = arguments.get("kind"), arguments.get("name")
        if kind not in ("anime", "movie", "manga") or not isinstance(name_value, str) or not name_value.strip():
            raise ValueError("catalog_add requires valid kind and non-empty name")
        for key in ("languages", "genres"):
            if key in arguments and (not isinstance(arguments[key], list) or not all(isinstance(x, str) for x in arguments[key])):
                raise ValueError(f"{key} must be an array of strings")
        values = dict(arguments)
        values.update(slug=None, type="", poster_url="", banner_url="", studio="",
                      total_episodes=0, age_rating="", synonyms="", author="", artist="",
                      duration=None, anilist_url="", anilist_id=None)
        values["status"] = arguments.get("status", "Unknown")
        values["description"] = arguments.get("description", "")
        values["languages"] = ",".join(arguments.get("languages", []))
        values["genres"] = ",".join(arguments.get("genres", []))
        args, func = SimpleNamespace(**values), create_item
    else:
        raise ValueError(f"Unknown AI tool: {name}")

    output = io.StringIO()
    with SessionLocal() as db, contextlib.redirect_stdout(output):
        func(args, db)
    return output.getvalue().strip()

def run_tool_request():
    import json
    request = json.load(sys.stdin)
    result = execute_ai_tool(request.get("name"), request.get("arguments", {}))
    print(json.dumps({"result": result}, ensure_ascii=False))

def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--ai-tools", action="store_true", help="print OpenAI-compatible tool definitions as JSON")
    cli.add_argument("--tool-call", action="store_true", help="read a JSON tool request from stdin and execute it")
    options, remaining = cli.parse_known_args()
    if options.ai_tools:
        import json
        print(json.dumps(AI_TOOLS, ensure_ascii=False))
        return
    if options.tool_call:
        import json
        try:
            run_tool_request()
        except (ValueError, TypeError, SQLAlchemyError) as exc:
            print(json.dumps({"error": str(exc)}, ensure_ascii=False))
            raise SystemExit(2)
        return
    args = parser().parse_args(remaining)
    try:
        with SessionLocal() as db: args.func(args, db)
    except (ValueError, TypeError) as exc:
        parser().error(str(exc))
    except SQLAlchemyError as exc:
        parser().error(f"Database operation failed: {getattr(exc, 'orig', exc)}")

if __name__ == "__main__":
    main()
