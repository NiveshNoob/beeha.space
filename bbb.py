import json
import re

INPUT_FILE = "m.txt"
OUTPUT_FILE = "naruto.json"

episodes = []

with open(INPUT_FILE, "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()

        if not line or "->" not in line:
            continue

        match = re.match(r"(\d+)\s*->\s*([a-zA-Z0-9]+)", line)

        if not match:
            continue

        ep = int(match.group(1))
        code = match.group(2)

        episodes.append({
            "episode": ep,
            "server1": f"https://voe.sx/e/{code}",
            "server2": ""
        })

episodes.sort(key=lambda x: x["episode"])

anime = {
    "name": "Naruto",
    "released_date": "2002",
    "status": "Completed",
    "anilist_link": "https://anilist.co/anime/20/Naruto",
    "alt_name": "Naruto Classic",
    "genre": "Action, Adventure, Comedy, Fantasy",
    "studio": "Studio Pierrot",
    "type": "Anime",
    "description": "",
    "total_episodes": 220,
    "episodes": episodes
}

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(anime, f, indent=2, ensure_ascii=False)

print(f"Saved {len(episodes)} episodes to {OUTPUT_FILE}")
