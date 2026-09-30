import re
import unicodedata
from typing import Type

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from ..database import get_db
from ..searching import normalize_search_text
from ..models import Anime, Episode, EpisodeSource, Genre, Language, Manga, MangaChapter, Movie, MovieSource, Season
from ..schemas import AnimeOut, ChapterOut, DiscoveryOut, GenreOut, LanguageOut, MangaOut, MovieOut, SearchOut, SeasonOut, SourceOut, EpisodeOut

router = APIRouter(prefix="/api")

def _list(model: Type, schema: Type, db: Session, language: str | None, genre: str | None, year: int | None, status: str | None, item_type: str | None, limit: int, offset: int, nested: bool = False, popular: bool = False):
    q = select(model)
    if nested:
        q = q.options(selectinload(model.seasons).selectinload(Season.episodes).selectinload(Episode.sources).selectinload(EpisodeSource.language), selectinload(model.languages), selectinload(model.genres))
    else:
        q = q.options(selectinload(model.languages), selectinload(model.genres))
    if language:
        q = q.join(model.languages).where(Language.code == language.casefold())
    if genre:
        q = q.join(model.genres).where(Genre.slug == genre.casefold())
    if year is not None: q = q.where(model.year == year)
    if status: q = q.where(model.status.ilike(status))
    if item_type: q = q.where(model.type.ilike(item_type))
    q = q.order_by(model.popularity.desc() if popular and hasattr(model, "popularity") else model.created_at.desc()).offset(offset).limit(limit)
    return [schema.model_validate(item) for item in db.scalars(q).unique().all()]

@router.get("/anime", response_model=list[AnimeOut])
def anime_list(language: str | None = None, genre: str | None = None, year: int | None = None, status: str | None = None, type: str | None = None, recently_added: bool = False, popular: bool = False, limit: int = Query(30, ge=1, le=100), offset: int = Query(0, ge=0), db: Session = Depends(get_db)):
    return _list(Anime, AnimeOut, db, language, genre, year, status, type, limit, offset, True, popular)

@router.get("/anime/{slug}", response_model=AnimeOut)
def anime_detail(slug: str, db: Session = Depends(get_db)):
    item = db.scalar(select(Anime).where(Anime.slug == slug).options(selectinload(Anime.languages), selectinload(Anime.genres), selectinload(Anime.seasons).selectinload(Season.episodes).selectinload(Episode.sources).selectinload(EpisodeSource.language)))
    if not item: raise HTTPException(404, "Anime not found")
    return item

@router.get("/anime/{slug}/seasons", response_model=list[SeasonOut])
def anime_seasons(slug: str, db: Session = Depends(get_db)):
    item = db.scalar(select(Anime).where(Anime.slug == slug).options(selectinload(Anime.seasons)))
    if not item: raise HTTPException(404, "Anime not found")
    return item.seasons

@router.get("/anime/{slug}/episodes", response_model=list[EpisodeOut])
def anime_episodes(slug: str, db: Session = Depends(get_db)):
    item = db.scalar(select(Anime.id).where(Anime.slug == slug))
    if not item: raise HTTPException(404, "Anime not found")
    return db.scalars(select(Episode).join(Season).where(Season.anime_id == item).options(selectinload(Episode.sources).selectinload(EpisodeSource.language)).order_by(Season.season_number, Episode.episode_number)).all()

@router.get("/episodes/{episode_id}/sources", response_model=list[SourceOut])
def episode_sources(episode_id: int, language: str | None = None, db: Session = Depends(get_db)):
    q = select(EpisodeSource).where(EpisodeSource.episode_id == episode_id, EpisodeSource.active.is_(True)).join(Language).options(selectinload(EpisodeSource.language)).order_by(EpisodeSource.priority)
    if language: q = q.where(Language.code == language.casefold())
    return db.scalars(q).all()

@router.get("/movies", response_model=list[MovieOut])
def movie_list(language: str | None = None, genre: str | None = None, year: int | None = None, status: str | None = None, type: str | None = None, limit: int = Query(30, ge=1, le=100), offset: int = Query(0, ge=0), db: Session = Depends(get_db)):
    return _list(Movie, MovieOut, db, language, genre, year, status, type, limit, offset)

@router.get("/movies/{slug}", response_model=MovieOut)
def movie_detail(slug: str, db: Session = Depends(get_db)):
    item = db.scalar(select(Movie).where(Movie.slug == slug).options(selectinload(Movie.languages), selectinload(Movie.genres)))
    if not item: raise HTTPException(404, "Movie not found")
    return item

@router.get("/movies/{slug}/sources", response_model=list[SourceOut])
def movie_sources(slug: str, language: str | None = None, db: Session = Depends(get_db)):
    q = select(MovieSource).join(Movie).join(Language).where(Movie.slug == slug, MovieSource.active.is_(True)).options(selectinload(MovieSource.language)).order_by(MovieSource.priority)
    if language: q = q.where(Language.code == language.casefold())
    return db.scalars(q).all()

@router.get("/manga", response_model=list[MangaOut])
def manga_list(language: str | None = None, genre: str | None = None, year: int | None = None, status: str | None = None, type: str | None = None, limit: int = Query(30, ge=1, le=100), offset: int = Query(0, ge=0), db: Session = Depends(get_db)):
    return _list(Manga, MangaOut, db, language, genre, year, status, type, limit, offset)

@router.get("/manga/{slug}", response_model=MangaOut)
def manga_detail(slug: str, db: Session = Depends(get_db)):
    item = db.scalar(select(Manga).where(Manga.slug == slug).options(selectinload(Manga.languages), selectinload(Manga.genres), selectinload(Manga.chapters).selectinload(MangaChapter.languages)))
    if not item: raise HTTPException(404, "Manga not found")
    return item

@router.get("/manga/{slug}/chapters", response_model=list[ChapterOut])
def manga_chapters(slug: str, db: Session = Depends(get_db)):
    item = db.scalar(select(Manga.id).where(Manga.slug == slug))
    if not item: raise HTTPException(404, "Manga not found")
    return db.scalars(select(MangaChapter).where(MangaChapter.manga_id == item).options(selectinload(MangaChapter.languages)).order_by(MangaChapter.chapter_number)).all()

@router.get("/languages", response_model=list[LanguageOut])
def languages(db: Session = Depends(get_db)):
    return db.scalars(select(Language).order_by(Language.name)).all()

@router.get("/genres", response_model=list[GenreOut])
def genres(db: Session = Depends(get_db)):
    return db.scalars(select(Genre).order_by(Genre.name)).all()

@router.get("/search", response_model=SearchOut)
def search(q: str = Query(min_length=1, max_length=200), limit: int = Query(20, ge=1, le=100), db: Session = Depends(get_db)):
    q = normalize_search_text(q)
    needle = f"%{q.strip()}%"
    return {
        "anime": db.scalars(select(Anime).where(or_(Anime.name.ilike(needle), Anime.synonyms.ilike(needle))).limit(limit)).all(),
        "movies": db.scalars(select(Movie).where(Movie.name.ilike(needle)).limit(limit)).all(),
        "manga": db.scalars(select(Manga).where(or_(Manga.name.ilike(needle), Manga.author.ilike(needle))).limit(limit)).all(),
    }

@router.get("/discovery", response_model=DiscoveryOut)
def discovery(db: Session = Depends(get_db)):
    return {
        "new_anime": _list(Anime, AnimeOut, db, None, None, None, None, None, 12, 0, True),
        "recently_added": db.scalars(select(Anime).order_by(Anime.created_at.desc()).limit(12)).all(),
        "trending": db.scalars(select(Anime).order_by(Anime.popularity.desc()).limit(12)).all(),
        "popular": db.scalars(select(Anime).order_by(Anime.popularity.desc()).limit(12)).all(),
        "new_movies": _list(Movie, MovieOut, db, None, None, None, None, None, 12, 0),
        "new_manga": _list(Manga, MangaOut, db, None, None, None, None, None, 12, 0),
    }
