from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi import Body
import json
import os
import sqlite3
from pathlib import Path
from datetime import datetime

app = FastAPI()

ROOT = Path(__file__).parent

DB_FILE = ROOT / "visitors.db"

conn = sqlite3.connect(DB_FILE)
conn.execute("""
CREATE TABLE IF NOT EXISTS stats (
    id INTEGER PRIMARY KEY,
    visits INTEGER NOT NULL
)
""")

conn.execute(
    "INSERT OR IGNORE INTO stats (id, visits) VALUES (1, 0)"
)

conn.commit()
conn.close()

REPORT_DB = "reports.db"

conn = sqlite3.connect(REPORT_DB)

conn.execute("""
CREATE TABLE IF NOT EXISTS reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    anime TEXT,
    episode INTEGER,
    page TEXT,
    reason TEXT,
    created_at TEXT
)
""")

conn.commit()
conn.close()

def increment_visit():
    conn = sqlite3.connect(DB_FILE)

    conn.execute(
        "UPDATE stats SET visits = visits + 1 WHERE id = 1"
    )

    conn.commit()
    conn.close()


def get_visits():
    conn = sqlite3.connect(DB_FILE)

    count = conn.execute(
        "SELECT visits FROM stats WHERE id = 1"
    ).fetchone()[0]

    conn.close()

    return count


@app.middleware("http")
async def record_visit(request: Request, call_next):

    path = request.url.path

    if path in ["/", "/index.html"]:
        increment_visit()

    response = await call_next(request)

    return response


@app.get("/api/stats")
async def stats():

    return JSONResponse({
        "visits": get_visits()
    })

@app.post("/api/report")
async def report(data: dict = Body(...)):

    conn = sqlite3.connect(REPORT_DB)

    conn.execute(
        """
        INSERT INTO reports
        (
            anime,
            episode,
            page,
            reason,
            created_at
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            data.get("anime"),
            data.get("episode"),
            data.get("page"),
            data.get("reason"),
            datetime.utcnow().isoformat()
        )
    )

    conn.commit()
    conn.close()

    return {"success": True}

@app.get("/api/reports")
async def reports():

    conn = sqlite3.connect(REPORT_DB)

    rows = conn.execute(
        """
        SELECT *
        FROM reports
        ORDER BY id DESC
        """
    ).fetchall()

    conn.close()

    return rows


@app.get("/")
async def home():
    return FileResponse(ROOT / "index.html")


@app.get("/watch.html")
async def watch():
    return FileResponse(ROOT / "watch.html")


app.mount(
    "/data",
    StaticFiles(directory=ROOT / "data"),
    name="data"
)

app.mount(
    "/",
    StaticFiles(directory=ROOT, html=True),
    name="static"
)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=8080,
        reload=True
    )
