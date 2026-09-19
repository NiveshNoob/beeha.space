from pathlib import Path
import json

print("=" * 50)
print("Anime Site Generator v2")
print("=" * 50)

name = input("Anime Name: ").strip()
year = input("Release Year: ").strip()
status = input("Status (Completed/Ongoing): ").strip()
anilist_link = input("AniList Link: ").strip()
total_episodes = int(input("Total Episodes: "))

episodes = []

for episode in range(1, total_episodes + 1):
    print(f"\nEpisode {episode}")

    server1 = input("Server 1 URL: ").strip()
    server2 = input("Server 2 URL: ").strip()

    episodes.append({
        "episode": episode,
        "server1": server1,
        "server2": server2
    })

# --------------------------------------------------
# Paths
# --------------------------------------------------

base_dir = Path("data") / year
anime_dir = base_dir / name
episode_dir = anime_dir / "episodes"

anime_dir.mkdir(parents=True, exist_ok=True)
episode_dir.mkdir(exist_ok=True)

# --------------------------------------------------
# Year Metadata
# --------------------------------------------------

year_meta_file = base_dir / "meta.json"

year_data = []

if year_meta_file.exists():
    year_data = json.loads(
        year_meta_file.read_text(
            encoding="utf-8"
        )
    )

if name not in year_data:
    year_data.append(name)

year_meta_file.write_text(
    json.dumps(
        sorted(year_data),
        indent=4,
        ensure_ascii=False
    ),
    encoding="utf-8"
)

# --------------------------------------------------
# Anime Metadata
# --------------------------------------------------

anime_json = {
    "name": name,
    "released_date": year,
    "status": status,
    "anilist_link": anilist_link,
    "total_episodes": total_episodes,
    "episodes": episodes
}

(anime_dir / "anime.json").write_text(
    json.dumps(
        anime_json,
        indent=4,
        ensure_ascii=False
    ),
    encoding="utf-8"
)

# --------------------------------------------------
# Shared CSS
# --------------------------------------------------

(anime_dir / "style.css").write_text(
"""
:root{
    --bg:#0f1117;
    --card:#181c25;
    --accent:#7c5cff;
    --text:#ffffff;
}

*{
    margin:0;
    padding:0;
    box-sizing:border-box;
}

body{
    background:var(--bg);
    color:var(--text);
    font-family:Inter,sans-serif;
}

.container{
    max-width:1000px;
    margin:auto;
    padding:20px;
}

.card{
    background:var(--card);
    border-radius:16px;
    padding:16px;
    margin:12px 0;
}

.btn{
    background:var(--accent);
    color:white;
    border:none;
    padding:12px 18px;
    border-radius:12px;
    cursor:pointer;
    text-decoration:none;
    display:inline-block;
}

.episode-grid{
    display:grid;
    grid-template-columns:
        repeat(auto-fill,minmax(150px,1fr));
    gap:12px;
}
""",
encoding="utf-8"
)

# --------------------------------------------------
# Shared JS
# --------------------------------------------------

(anime_dir / "script.js").write_text( """ function setProvider(url){ document .getElementById("player") .src = url; } async function reportProblem( anime, episode ){ const reason = prompt( "Describe the problem:" ); if(!reason){ return; } try{ const response = await fetch( "/api/report", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ anime: anime, episode: episode, page: window.location.href, reason: reason }) } ); const data = await response.json(); if( response.ok && data.success ){ alert( "Report submitted. Thank you!" ); } else{ alert( "Failed to submit report." ); } } catch(error){ console.error(error); alert( "Failed to submit report." ); } } """, encoding="utf-8" )

# --------------------------------------------------
# Anime Index
# --------------------------------------------------

index_html = f"""
<!DOCTYPE html>
<html>
<head>

<meta charset="utf-8">

<meta
name="viewport"
content="width=device-width, initial-scale=1">

<title>{name}</title>

<link
rel="stylesheet"
href="style.css">

</head>

<body>

<div class="container">

<h1>{name}</h1>

<br>

<div class="card">

<p>Status: {status}</p>

<p>Year: {year}</p>

<br>

<a
class="btn"
target="_blank"
href="{anilist_link}">
AniList
</a>

</div>

<h2>Episodes</h2>

<br>

<div class="episode-grid">
"""

for ep in episodes:
    index_html += f"""
<a
class="btn"
href="episodes/{ep['episode']}.html">
Episode {ep['episode']}
</a>
"""

index_html += """
</div>

</div>

</body>
</html>
"""

(anime_dir / "index.html").write_text(
    index_html,
    encoding="utf-8"
)

# --------------------------------------------------
# Episode Pages
# --------------------------------------------------

for ep in episodes:

    ep_num = ep["episode"]

    html = f"""
<!DOCTYPE html>
<html>
<head>

<meta charset="utf-8">

<meta
name="viewport"
content="width=device-width, initial-scale=1">

<title>
Episode {ep_num}
</title>

<link
rel="stylesheet"
href="../style.css">

<script
src="../script.js">
</script>

<style>

body{{
    display:flex;
    flex-direction:column;
    height:100vh;
}}

iframe{{
    flex:1;
    width:100%;
    border:none;
}}

.controls{{
    padding:16px;
    display:flex;
    gap:10px;
    flex-wrap:wrap;
}}

</style>

</head>

<body>

<iframe
id="player"
src="{ep['server1']}"
allowfullscreen>
</iframe>

<div class="controls">

<button
class="btn"
onclick="setProvider('{ep['server1']}')">
Server 1
</button>

<button
class="btn"
onclick="setProvider('{ep['server2']}')">
Server 2
</button>

<button class="btn" onclick="reportProblem( '{name}', {ep_num} )"> ⚠ Report </button>

<a
class="btn"
href="{max(1, ep_num-1)}.html">
Previous
</a>

<a
class="btn"
href="{min(total_episodes, ep_num+1)}.html">
Next
</a>

</div>

</body>
</html>
"""

    (
        episode_dir /
        f"{ep_num}.html"
    ).write_text(
        html,
        encoding="utf-8"
    )

print()
print("=" * 50)
print("Generation Complete")
print("=" * 50)
print("Anime:", name)
print("Folder:", anime_dir)
