from datetime import datetime
from pydantic import BaseModel, ConfigDict

class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

class LanguageOut(ORMModel):
    code: str
    name: str
    native_name: str

class GenreOut(ORMModel):
    name: str
    slug: str

class SourceOut(ORMModel):
    id: int
    language: LanguageOut
    provider: str
    url: str
    priority: int
    active: bool

class EpisodeOut(ORMModel):
    id: int
    episode_number: int
    title: str
    duration: int | None
    sources: list[SourceOut]

class SeasonOut(ORMModel):
    id: int
    season_number: int
    name: str
    episodes: list[EpisodeOut]

class AnimeOut(ORMModel):
    id: int
    name: str
    slug: str
    anilist_id: int | None
    anilist_url: str
    description: str
    japanese_name: str
    synonyms: str
    total_episodes: int
    year: int | None
    season: str
    status: str
    type: str
    age_rating: str
    studio: str
    poster_url: str
    banner_url: str
    popularity: int
    created_at: datetime
    updated_at: datetime
    languages: list[LanguageOut]
    genres: list[GenreOut]
    seasons: list[SeasonOut]

class CatalogOut(ORMModel):
    id: int
    name: str
    slug: str
    description: str
    year: int | None
    status: str
    type: str
    poster_url: str
    banner_url: str
    languages: list[LanguageOut]
    genres: list[GenreOut]

class MovieOut(CatalogOut):
    duration: int | None
    anilist_id: int | None
    anilist_url: str
    created_at: datetime
    updated_at: datetime

class ChapterOut(ORMModel):
    id: int
    chapter_number: int
    title: str
    languages: list[LanguageOut]

class MangaOut(CatalogOut):
    author: str
    artist: str
    anilist_id: int | None
    anilist_url: str
    created_at: datetime
    updated_at: datetime
    chapters: list[ChapterOut]

class SearchOut(BaseModel):
    anime: list[CatalogOut]
    movies: list[CatalogOut]
    manga: list[CatalogOut]

class DiscoveryOut(BaseModel):
    new_anime: list[AnimeOut]
    recently_added: list[AnimeOut]
    trending: list[AnimeOut]
    popular: list[AnimeOut]
    new_movies: list[MovieOut]
    new_manga: list[MangaOut]
