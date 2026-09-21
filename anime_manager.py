#!/usr/bin/env python3
"""Manage Beeha's anime catalog and compare it with a separate watchlist.

Examples:
  python anime_manager.py list --query "attack"
  python anime_manager.py add "Example Anime" --year 2026 --status Ongoing
  python anime_manager.py update "Example Anime" --year 2026 --genre Fantasy
  python anime_manager.py delete "Example Anime" --year 2026 --yes
  python anime_manager.py watchlist add "Frieren: Beyond Journey's End"
  python anime_manager.py watchlist compare
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
DEFAULT_WATCHLIST = ROOT / "list.txt"
FIELDS = (
    "status", "anilist_link", "alt_name", "genre", "studio", "type", "description",
)


@dataclass(frozen=True)
class WatchlistItem:
    title: str
    year: str | None = None

    def display(self) -> str:
        return f"{self.title} | {self.year}" if self.year else self.title


def normalise(value: str) -> str:
    """Make title comparisons tolerant of case, punctuation, and curly quotes."""
    value = value.casefold().replace("’", "'")
    return re.sub(r"[^\w]+", "", value)


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Cannot read {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return value


def catalog() -> list[tuple[Path, dict[str, Any]]]:
    items: list[tuple[Path, dict[str, Any]]] = []
    if not DATA_DIR.exists():
        return items
    for path in DATA_DIR.glob("*/*/anime.json"):
        try:
            item = read_json(path)
        except ValueError as exc:
            print(f"Warning: {exc}", file=sys.stderr)
            continue
        item.setdefault("name", path.parent.name)
        item.setdefault("released_date", path.parent.parent.name)
        items.append((path, item))
    return sorted(items, key=lambda entry: (str(entry[1]["released_date"]), str(entry[1]["name"]).casefold()))


def matches(title: str, year: str | None = None) -> list[tuple[Path, dict[str, Any]]]:
    key = normalise(title)
    return [
        entry for entry in catalog()
        if normalise(str(entry[1]["name"])) == key
        and (year is None or str(entry[1]["released_date"]) == str(year))
    ]


def single_match(title: str, year: str | None) -> tuple[Path, dict[str, Any]]:
    found = matches(title, year)
    if not found:
        raise ValueError(f"No catalog entry found for {title!r}" + (f" in {year}." if year else "."))
    if len(found) > 1:
        choices = ", ".join(f"{item['name']} ({item['released_date']})" for _, item in found)
        raise ValueError(f"More than one entry matches. Pass --year. Matches: {choices}")
    return found[0]


def sync_year_index(year: str) -> None:
    directory = DATA_DIR / str(year)
    names = sorted((p.parent.name for p in directory.glob("*/anime.json")), key=str.casefold) if directory.exists() else []
    if not names:
        if directory.exists():
            (directory / "meta.json").unlink(missing_ok=True)
            (directory / "meta.txt").unlink(missing_ok=True)
            if not any(directory.iterdir()):
                directory.rmdir()
        return
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "meta.json").write_text(json.dumps(names, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (directory / "meta.txt").write_text("\n".join(names) + "\n", encoding="utf-8")


def write_anime(path: Path, item: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(item, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    meta = [f"name: {item['name']}", f"released_date: {item['released_date']}"]
    meta.extend(f"{key}: {item.get(key, '')}" for key in FIELDS)
    meta.append(f"total_episodes: {item['total_episodes']}")
    (path.parent / "meta.txt").write_text("\n".join(meta) + "\n", encoding="utf-8")


def episodes_from_args(args: argparse.Namespace) -> list[dict[str, Any]] | None:
    source = args.episodes if getattr(args, "episodes", None) else None
    if getattr(args, "episodes_file", None):
        source = Path(args.episodes_file).read_text(encoding="utf-8")
    if source is None:
        return None
    value = json.loads(source)
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise ValueError("Episodes must be a JSON array of objects.")
    return value


def command_list(args: argparse.Namespace) -> None:
    results = catalog()
    if args.year:
        results = [entry for entry in results if str(entry[1]["released_date"]) == str(args.year)]
    if args.query:
        query = normalise(args.query)
        results = [entry for entry in results if query in normalise(str(entry[1]["name"]))]
    for _, item in results:
        print(f"{item['released_date']}  {item['name']}  [{item.get('status', 'Unknown')}]  episodes: {item.get('total_episodes', 0)}")
    print(f"{len(results)} result(s)", file=sys.stderr)


def command_show(args: argparse.Namespace) -> None:
    _, item = single_match(args.title, args.year)
    print(json.dumps(item, indent=2, ensure_ascii=False))


def command_add(args: argparse.Namespace) -> None:
    if matches(args.title, args.year):
        raise ValueError("An entry with that title and year already exists; use update instead.")
    episodes = episodes_from_args(args) or []
    item: dict[str, Any] = {
        "name": args.title, "released_date": str(args.year), "status": args.status,
        "total_episodes": args.total_episodes if args.total_episodes is not None else len(episodes),
        "episodes": episodes,
    }
    item.update({field: getattr(args, field) or "" for field in FIELDS})
    path = DATA_DIR / str(args.year) / args.title / "anime.json"
    write_anime(path, item)
    sync_year_index(str(args.year))
    print(f"Added: {path.relative_to(ROOT)}")


def command_update(args: argparse.Namespace) -> None:
    path, item = single_match(args.title, args.year)
    old_year = str(item["released_date"])
    for field in FIELDS:
        value = getattr(args, field)
        if value is not None:
            item[field] = value
    if args.new_title:
        item["name"] = args.new_title
    if args.new_year:
        item["released_date"] = str(args.new_year)
    if args.total_episodes is not None:
        item["total_episodes"] = args.total_episodes
    episodes = episodes_from_args(args)
    if episodes is not None:
        item["episodes"] = episodes
        if args.total_episodes is None:
            item["total_episodes"] = len(episodes)
    new_path = DATA_DIR / str(item["released_date"]) / str(item["name"]) / "anime.json"
    if new_path != path and new_path.exists():
        raise ValueError(f"Cannot move entry: {new_path.parent} already exists.")
    if new_path != path:
        new_path.parent.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(path.parent), str(new_path.parent))
    write_anime(new_path, item)
    sync_year_index(old_year)
    sync_year_index(str(item["released_date"]))
    print(f"Updated: {new_path.relative_to(ROOT)}")


def command_delete(args: argparse.Namespace) -> None:
    path, item = single_match(args.title, args.year)
    if not args.yes:
        raise ValueError("Deletion needs --yes. This removes the anime folder and any image files within it.")
    year = str(item["released_date"])
    shutil.rmtree(path.parent)
    sync_year_index(year)
    print(f"Deleted: {item['name']} ({year})")


def watchlist_path(args: argparse.Namespace) -> Path:
    return Path(args.watchlist) if args.watchlist else DEFAULT_WATCHLIST


def load_watchlist(path: Path) -> list[WatchlistItem]:
    if not path.exists():
        return []
    entries: list[WatchlistItem] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # The suffix is optional so existing title-only list.txt files still work.
        title, separator, possible_year = line.rpartition(" | ")
        if separator and possible_year.isdigit() and len(possible_year) == 4:
            entries.append(WatchlistItem(title, possible_year))
        else:
            entries.append(WatchlistItem(line))
    return entries


def save_watchlist(path: Path, entries: list[WatchlistItem]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    unique = {(normalise(item.title), item.year): item for item in entries}
    ordered = sorted(unique.values(), key=lambda item: (item.year or "", item.title.casefold()))
    path.write_text("\n".join(item.display() for item in ordered) + "\n", encoding="utf-8")


def command_watchlist(args: argparse.Namespace) -> None:
    path = watchlist_path(args)
    entries = load_watchlist(path)
    if args.watch_command == "list":
        print("\n".join(item.display() for item in entries))
        return
    if args.watch_command == "add":
        item = WatchlistItem(args.title, args.year)
        key = (normalise(item.title), item.year)
        if key not in {(normalise(entry.title), entry.year) for entry in entries}:
            entries.append(item)
            save_watchlist(path, entries)
            print(f"Added to {path}: {item.display()}")
        else:
            print("Already present.")
        return
    if args.watch_command == "remove":
        remaining = [
            item for item in entries
            if not (normalise(item.title) == normalise(args.title) and (args.year is None or item.year == args.year))
        ]
        if len(remaining) == len(entries):
            raise ValueError(f"{args.title!r} is not in {path}.")
        save_watchlist(path, remaining)
        print(f"Removed from {path}: {args.title}")
        return
    selected = [item for item in entries if args.year is None or item.year == args.year]
    catalog_items = catalog()
    by_title = {normalise(str(item["name"])) for _, item in catalog_items}
    by_title_and_year = {
        (normalise(str(item["name"])), str(item["released_date"])) for _, item in catalog_items
    }
    present, missing = [], []
    for item in selected:
        available = (
            (normalise(item.title), item.year) in by_title_and_year
            if item.year else normalise(item.title) in by_title
        )
        (present if available else missing).append(item)
    print(f"Available ({len(present)}):")
    print("\n".join(f"  {item.display()}" for item in present) or "  None")
    print(f"\nNot available ({len(missing)}):")
    print("\n".join(f"  {item.display()}" for item in missing) or "  None")


def add_metadata_options(parser: argparse.ArgumentParser, *, update: bool = False) -> None:
    for field in FIELDS:
        parser.add_argument("--" + field.replace("_", "-"), dest=field, default=None if update else "")
    parser.add_argument("--total-episodes", type=int)
    parser.add_argument("--episodes", help="JSON episode array, e.g. '[{\"episode\":1,\"server1\":\"...\",\"server2\":\"\"}]'")
    parser.add_argument("--episodes-file", help="Path to a JSON file containing the episode array.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    listing = sub.add_parser("list", help="List catalog entries")
    listing.add_argument("--year")
    listing.add_argument("--query")
    listing.set_defaults(func=command_list)
    show = sub.add_parser("show", help="Show one entry as JSON")
    show.add_argument("title")
    show.add_argument("--year")
    show.set_defaults(func=command_show)
    add = sub.add_parser("add", help="Add an anime")
    add.add_argument("title")
    add.add_argument("--year", required=True)
    add_metadata_options(add)
    add.set_defaults(func=command_add, status="Unknown")
    update = sub.add_parser("update", help="Edit an anime")
    update.add_argument("title")
    update.add_argument("--year")
    update.add_argument("--new-title")
    update.add_argument("--new-year")
    add_metadata_options(update, update=True)
    update.set_defaults(func=command_update)
    delete = sub.add_parser("delete", help="Delete an anime and its folder")
    delete.add_argument("title")
    delete.add_argument("--year")
    delete.add_argument("--yes", action="store_true", help="Confirm deletion")
    delete.set_defaults(func=command_delete)
    watch = sub.add_parser("watchlist", help="Manage or compare the separate anime list")
    watch.add_argument("--watchlist", help="Alternative list file (default: list.txt)")
    watch_sub = watch.add_subparsers(dest="watch_command", required=True)
    for name in ("list", "compare"):
        child = watch_sub.add_parser(name)
        if name == "compare":
            child.add_argument("--year", help="Compare only watchlist entries tagged with this year")
        child.set_defaults(func=command_watchlist)
    for name in ("add", "remove"):
        child = watch_sub.add_parser(name)
        child.add_argument("title")
        child.add_argument("--year", help="Release year; stored with the watchlist entry")
        child.set_defaults(func=command_watchlist)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        args.func(args)
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
