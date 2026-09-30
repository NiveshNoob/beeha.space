from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from .api.catalog import router

app = FastAPI(title="Beeha Content API", version="3.0.0")
app.include_router(router)
FRONTEND = Path(__file__).resolve().parents[2] / "frontend"
LEGACY_DATA = Path(__file__).resolve().parents[3] / "data"
app.mount("/static", StaticFiles(directory=FRONTEND), name="static")
if LEGACY_DATA.is_dir():
    app.mount("/data", StaticFiles(directory=LEGACY_DATA), name="legacy-data")

@app.get("/", include_in_schema=False)
@app.get("/anime", include_in_schema=False)
@app.get("/anime/{language}", include_in_schema=False)
@app.get("/movie", include_in_schema=False)
@app.get("/movie/{language}", include_in_schema=False)
@app.get("/manga", include_in_schema=False)
@app.get("/manga/{language}", include_in_schema=False)
@app.get("/anime/title/{slug}", include_in_schema=False)
@app.get("/movie/title/{slug}", include_in_schema=False)
@app.get("/manga/title/{slug}", include_in_schema=False)
@app.get("/search", include_in_schema=False)
def frontend(language: str | None = None):
    return FileResponse(FRONTEND / "index.html")

@app.get("/health")
def health():
    return {"ok": True}
