from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"


def prompt_int(label: str, minimum: int = 1) -> int:
    while True:
        try:
            value = int(input(label).strip())
            if value >= minimum:
                return value
        except ValueError:
            pass
        print(f"Please enter a number >= {minimum}.")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def load_year_names(path: Path) -> list[str]:
    if not path.is_file():
        return []
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(value, list):
            return [str(item) for item in value]
    except (OSError, json.JSONDecodeError):
        pass
    return []


print("=" * 56)
print("Beeha FastAPI Anime Generator")
print("=" * 56)

name = input("Anime Name: ").strip()
year = prompt_int("Release Year: ", 1900)
status = input("Status (Completed/Ongoing): ").strip() or "Unknown"
anilist_link = input("AniList Link (optional): ").strip()
alt_name = input("Alternative Name (optional): ").strip()
genre = input("Genre (optional): ").strip()
studio = input("Studio (optional): ").strip()
anime_type = input("Type (TV/Movie/OVA/etc., optional): ").strip()
description = input("Description (optional): ").strip()
total_episodes = prompt_int("Total Episodes: ", 1)

episodes: list[dict[str, object]] = []
for episode in range(1, total_episodes + 1):
    print(f"\nEpisode {episode}")
    server1 = input("Server 1 URL: ").strip()
    server2 = input("Server 2 URL (optional): ").strip()
    episodes.append(
        {
            "episode": episode,
            "server1": server1,
            "server2": server2,
        }
    )

base_dir = DATA_DIR / str(year)
anime_dir = base_dir / name
anime_dir.mkdir(parents=True, exist_ok=True)

anime_data = {
    "name": name,
    "released_date": str(year),
    "status": status,
    "anilist_link": anilist_link,
    "alt_name": alt_name,
    "genre": genre,
    "studio": studio,
    "type": anime_type,
    "description": description,
    "total_episodes": total_episodes,
    "episodes": episodes,
}

(anime_dir / "anime.json").write_text(
    json.dumps(anime_data, indent=2, ensure_ascii=False),
    encoding="utf-8",
)

# Keep the simple text metadata format for compatibility with older Beeha data.
meta_lines = [
    f"name: {name}",
    f"released_date: {year}",
    f"status: {status}",
    f"anilist_link: {anilist_link}",
    f"alt_name: {alt_name}",
    f"genre: {genre}",
    f"studio: {studio}",
    f"type: {anime_type}",
    f"description: {description}",
    f"total_episodes: {total_episodes}",
]
write_text(anime_dir / "meta.txt", "\n".join(meta_lines))

# FastAPI discovers folders directly, but these indexes are retained for compatibility.
year_json = base_dir / "meta.json"
names = load_year_names(year_json)
if name not in names:
    names.append(name)
names = sorted(set(names), key=str.casefold)
year_json.write_text(json.dumps(names, indent=2, ensure_ascii=False), encoding="utf-8")
write_text(base_dir / "meta.txt", "\n".join(names))

print("\n" + "=" * 56)
print("Generation Complete")
print("=" * 56)
print("Anime :", name)
print("Folder:", anime_dir)
print("\nNo HTML episode files were generated.")
print("FastAPI now serves /watch?year=<year>&anime=<folder>&episode=<n>.")
