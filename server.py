from __future__ import annotations

import json
import os
import sqlite3
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

from fastapi import Body, FastAPI, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
STATIC_DIR = ROOT / "static"
TEMPLATES_DIR = ROOT / "templates"
DATA_DIR.mkdir(parents=True, exist_ok=True)
VISITOR_DB = ROOT / "visitors.db"
REPORT_DB = ROOT / "reports.db"
ADMIN_TOKEN = os.getenv("BEEHA_ADMIN_TOKEN", "").strip()


def db_connect(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout = 10000")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    return conn


def init_databases() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    with db_connect(VISITOR_DB) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS stats (
                id INTEGER PRIMARY KEY,
                visits INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        conn.execute(
            "INSERT OR IGNORE INTO stats (id, visits) VALUES (1, 0)"
        )

    with db_connect(REPORT_DB) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                anime TEXT NOT NULL,
                episode INTEGER NOT NULL,
                page TEXT,
                reason TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_reports_created_at ON reports(created_at DESC)"
        )


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_databases()
    yield


app = FastAPI(
    title="Beeha",
    description="Beeha anime library API",
    version="2.0.0",
    lifespan=lifespan,
)

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/data", StaticFiles(directory=DATA_DIR), name="data")


class ReportRequest(BaseModel):
    anime: str = Field(min_length=1, max_length=300)
    episode: int = Field(ge=1, le=100000)
    page: str | None = Field(default=None, max_length=2000)
    reason: str = Field(min_length=1, max_length=2000)


def parse_meta_text(path: Path) -> dict[str, str]:
    meta: dict[str, str] = {}
    if not path.is_file():
        return meta

    for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        key, sep, value = line.partition(":")
        if not sep:
            continue
        meta[key.strip()] = value.strip().strip("\"'").rstrip(",")
    return meta


def read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else None
    except (OSError, json.JSONDecodeError):
        return None


def safe_path(*parts: str | int) -> Path:
    path = DATA_DIR.joinpath(*(str(part) for part in parts))
    try:
        path.resolve().relative_to(DATA_DIR.resolve())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid data path") from exc
    return path


def anime_from_folder(year: int, folder: Path) -> dict[str, Any] | None:
    if not folder.is_dir():
        return None

    anime_json_path = folder / "anime.json"
    data = read_json(anime_json_path)

    if data is None:
        meta = parse_meta_text(folder / "meta.txt")
        if not meta:
            return None
        data = meta

    name = str(data.get("name") or folder.name)
    released_date = str(data.get("released_date") or year)
    status_value = str(data.get("status") or "Unknown")

    raw_episodes = data.get("episodes")
    episodes: list[dict[str, Any]] = []
    if isinstance(raw_episodes, list):
        for raw in raw_episodes:
            if not isinstance(raw, dict):
                continue
            try:
                number = int(raw.get("episode"))
            except (TypeError, ValueError):
                continue
            if number < 1:
                continue
            episodes.append(
                {
                    "episode": number,
                    "server1": str(raw.get("server1") or ""),
                    "server2": str(raw.get("server2") or ""),
                }
            )
    episodes.sort(key=lambda item: item["episode"])

    # Prefer explicit total_episodes, otherwise infer from the stored episode list.
    try:
        total_episodes = int(data.get("total_episodes") or len(episodes))
    except (TypeError, ValueError):
        total_episodes = len(episodes)

    return {
        "name": name,
        "folder": folder.name,
        "year": year,
        "released_date": released_date,
        "status": status_value,
        "anilist_link": str(data.get("anilist_link") or ""),
        "alt_name": str(data.get("alt_name") or ""),
        "genre": str(data.get("genre") or ""),
        "studio": str(data.get("studio") or ""),
        "description": str(data.get("description") or ""),
        "type": str(data.get("type") or ""),
        "total_episodes": total_episodes,
        "episodes": episodes,
        "poster": f"/data/{year}/{quote(folder.name, safe='')}/photo.jpg",
        "poster_fallback": f"/data/{year}/{quote(folder.name, safe='')}/photo.webp",
    }


def discover_years() -> list[int]:
    years: list[int] = []
    if not DATA_DIR.is_dir():
        return years
    for child in DATA_DIR.iterdir():
        if not child.is_dir() or not child.name.isdigit():
            continue
        year = int(child.name)
        if 1900 <= year <= 3000:
            years.append(year)
    return sorted(years, reverse=True)


def discover_anime(year: int) -> list[dict[str, Any]]:
    year_dir = safe_path(year)
    if not year_dir.is_dir():
        return []

    result: list[dict[str, Any]] = []
    for folder in year_dir.iterdir():
        anime = anime_from_folder(year, folder)
        if anime:
            result.append(anime)
    result.sort(key=lambda item: item["name"].casefold())
    return result


def discover_all_anime() -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for year in discover_years():
        result.extend(discover_anime(year))
    result.sort(key=lambda item: (item["name"].casefold(), -item["year"]))
    return result


def public_anime(anime: dict[str, Any], include_episodes: bool = False) -> dict[str, Any]:
    payload = dict(anime)
    if not include_episodes:
        payload.pop("episodes", None)
    return payload


def increment_visits() -> None:
    with db_connect(VISITOR_DB) as conn:
        conn.execute("UPDATE stats SET visits = visits + 1 WHERE id = 1")


def get_visits() -> int:
    with db_connect(VISITOR_DB) as conn:
        row = conn.execute("SELECT visits FROM stats WHERE id = 1").fetchone()
        return int(row["visits"]) if row else 0


def check_admin(request: Request) -> None:
    if not ADMIN_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Admin reports are disabled. Set BEEHA_ADMIN_TOKEN on the server.",
        )
    supplied = request.headers.get("X-Admin-Token", "")
    if supplied != ADMIN_TOKEN:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")


@app.middleware("http")
async def visit_counter(request: Request, call_next):
    if request.url.path in {"/", "/index.html"}:
        increment_visits()
    return await call_next(request)


@app.get("/", response_class=HTMLResponse, name="home")
@app.get("/index.html", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(
    request=request,
    name="index.html",
)

@app.get("/watch", response_class=HTMLResponse, name="watch")
@app.get("/watch.html", response_class=HTMLResponse)
async def watch(request: Request):
    return templates.TemplateResponse(
    request=request,
    name="watch.html",
)

@app.get("/health")
async def health():
    return {"ok": True}


@app.get("/api/years")
async def years():
    values = discover_years()
    return {"years": values}


@app.get("/api/anime")
async def anime_list(
    year: int | None = Query(default=None, ge=1900, le=3000),
    search: str = Query(default="", max_length=200),
):
    items = discover_all_anime() if year is None else discover_anime(year)

    query = search.strip().casefold()
    if query:
        def matches(item: dict[str, Any]) -> tuple[int, dict[str, Any]]:
            fields = " ".join(
                str(item.get(key, ""))
                for key in (
                    "name", "alt_name", "genre", "studio", "description",
                    "status", "type", "released_date", "folder", "year",
                )
            ).casefold()
            name = str(item["name"]).casefold()
            score = 0
            if name == query:
                score += 1000
            if name.startswith(query):
                score += 500
            if query in name:
                score += 250
            if query in fields:
                score += 100
            return score, item

        ranked = [matches(item) for item in items]
        ranked = [(score, item) for score, item in ranked if score > 0]
        ranked.sort(key=lambda pair: (-pair[0], pair[1]["name"].casefold(), -pair[1]["year"]))
        items = [item for _, item in ranked]

    return {
        "items": [public_anime(item) for item in items],
        "total": len(items),
        "year": year,
        "search": search,
    }


@app.get("/api/ongoing")
async def ongoing_anime():
    """Return every anime whose status is marked as Ongoing."""
    items = [
        item
        for item in discover_all_anime()
        if str(item.get("status", "")).strip().casefold() == "ongoing"
    ]
    return {"items": [public_anime(item) for item in items], "total": len(items)}


@app.get("/api/anime/{year}/{anime_name:path}")
async def anime_detail(year: int, anime_name: str):
    if year < 1900 or year > 3000:
        raise HTTPException(status_code=404, detail="Anime not found")
    folder = safe_path(year, anime_name)
    if not folder.is_dir():
        raise HTTPException(status_code=404, detail="Anime not found")
    anime = anime_from_folder(year, folder)
    if anime is None:
        raise HTTPException(status_code=404, detail="Anime metadata not found")
    return public_anime(anime, include_episodes=True)


@app.get("/api/stats")
async def stats():
    return {"visits": get_visits()}


@app.post("/api/report")
async def report(data: ReportRequest = Body(...)):
    with db_connect(REPORT_DB) as conn:
        conn.execute(
            """
            INSERT INTO reports (anime, episode, page, reason, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                data.anime.strip(),
                data.episode,
                data.page,
                data.reason.strip(),
                datetime.now(timezone.utc).isoformat(),
            ),
        )
    return {"success": True}


@app.get("/api/reports")
async def reports(request: Request, limit: int = Query(default=100, ge=1, le=500)):
    check_admin(request)
    with db_connect(REPORT_DB) as conn:
        rows = conn.execute(
            """
            SELECT id, anime, episode, page, reason, created_at
            FROM reports
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return {"reports": [dict(row) for row in rows]}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("server:app", host="0.0.0.0", port=8080, reload=True)
